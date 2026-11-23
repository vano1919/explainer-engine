"""Perfectly Normal for WP-Q1's C4 faces: fetch the pinned extension zip, check it, unpack its asset ``.blend``.

Perfectly Normal 0.0.3 (Seth Trowbridge, GPL-3.0-or-later, Blender's official platform) ships its four "Manip Verts" Geometry
Nodes groups in ``assets/perfectly_normal.blend``. ``bpy/render_shot.perfectly_normal`` appends them as data (no add-on code
runs) and stacks (Re)create -> Tweak (Converge) -> Apply on the cast. The pin is ``blender_extensions.perfectly_normal`` of
``config/cloud_pins.json``; the licence row is ``assets/licence_sources.json`` perfectly_normal.

    python -m explainer_engine.blender.face_normals [--dir D]     # prints the .blend path for $EE_PERFECTLY_NORMAL_BLEND
"""
from __future__ import annotations

import argparse
import json
import urllib.request
import zipfile
from pathlib import Path

from explainer_engine.blender.camera_rigs import CACHE, PINS, sha256_file
from explainer_engine.core.errors import ConfigError

KEY = "perfectly_normal"
MEMBER = "assets/perfectly_normal.blend"


def pin() -> dict:
    try:
        return json.loads(PINS.read_text(encoding="utf-8"))["blender_extensions"][KEY]
    except (KeyError, FileNotFoundError) as exc:
        raise ConfigError(f"config/cloud_pins.json has no blender_extensions.{KEY} pin") from exc


def ensure(cache: Path | None = None, *, download=None) -> Path:
    """The extension's asset .blend, unpacked next to the pinned zip; a zip whose sha256 differs from the pin is refused."""
    p = pin()
    folder = Path(cache or CACHE) / p["sha256"]
    path = folder / f"{KEY}-{p['version']}.zip"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        if download is not None:
            download(p["url"], tmp)
        else:
            req = urllib.request.Request(p["url"], headers={"User-Agent": "explainer-engine/1"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:   # noqa: S310 (a pinned https url)
                f.write(r.read())
        tmp.replace(path)
    got = sha256_file(path)
    if got != p["sha256"]:
        path.unlink(missing_ok=True)
        raise ConfigError(f"{KEY}: sha256 {got} differs from the pin {p['sha256']}")
    blend = folder / "perfectly_normal.blend"
    if not blend.exists():
        with zipfile.ZipFile(path) as z:
            blend.write_bytes(z.read(MEMBER))
    return blend


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=None)
    a = ap.parse_args(argv)
    print(ensure(Path(a.dir) if a.dir else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
