"""Contact sheet of rendered layout clips: one row per clip, one thumbnail per view with camera, lens and seconds.

``python -m explainer_engine.lab.scene_sheet <spec_dir> <render_root> <out.png>`` where ``<render_root>/<scene_id>/`` holds
the output of ``scene_render`` (views/, report.json). Free, PIL only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.lab import scene_spec as ss

THUMB = (320, 176)


def contact_sheet(spec_dir: Path, render_root: Path, out: Path) -> Path:
    from PIL import Image, ImageDraw  # noqa: PLC0415
    series = ss.load_series(spec_dir)
    rows = [(spec, json.loads((render_root / spec["scene_id"] / "report.json").read_text(encoding="utf-8")))
            for clips in series.values() for spec in clips]
    cols = max(len(r["views"]) for _, r in rows)
    head = 34
    sheet = Image.new("RGB", (cols * (THUMB[0] + 6) + 6, len(rows) * (THUMB[1] + head + 6) + 6), (28, 28, 30))
    d = ImageDraw.Draw(sheet)
    for ri, (spec, rep) in enumerate(rows):
        y = 6 + ri * (THUMB[1] + head + 6)
        d.text((8, y + 2), f"{spec['scene_id']} ({spec['place']}), {rep['status']}, "
                           f"{rep['video']['frames']} frames, {len(rep['views'])} views", fill=(240, 240, 240))
        for ci, v in enumerate(rep["views"]):
            x = 6 + ci * (THUMB[0] + 6)
            im = Image.open(render_root / spec["scene_id"] / v["png"]).convert("RGB").resize(THUMB)
            sheet.paste(im, (x, y + head))
            lens = round(ss.cam_start(ss.camera_by_id(spec, v["camera"]))["lens"])
            d.text((x + 2, y + 18), f"{v['view']}: {v['camera']} {lens} mm {v['seconds']:.2f} s", fill=(200, 200, 140))
    sheet.save(out)
    return out


if __name__ == "__main__":
    print(contact_sheet(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
