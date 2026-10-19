"""Is a rendered file a YouTube Short? (creator 2026-10-19: "the Shorts uploaded as videos, fix the code so it never happens")

YouTube makes an upload a Short from the file alone: square or vertical and at most three minutes (YouTube Help 15424877,
read 2026-10-19); the API has no Shorts flag. Our Shorts are 1080x1920 (9:16), so anything else is a render fault. A Short is
reached at ``youtube.com/shorts/<id>``; a ``youtu.be`` link opens even a Short in the ordinary player, which is how the
2026-10-19 uploads looked like videos although YouTube served all ten as Shorts.

    python -m explainer_engine.qa.short_format <SH01.mp4> [...]    # exit 1 on a FAIL
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MAX_SECONDS = 180.0
ASPECT = (9, 16)
SHORTS_LINK = "https://www.youtube.com/shorts/{id}"


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = (d.get("streams") or [{}])[0]
    rot = next((abs(int(x.get("rotation", 0))) for x in s.get("side_data_list") or [] if "rotation" in x), 0)
    w, h = int(s.get("width", 0)), int(s.get("height", 0))
    if rot in (90, 270):
        w, h = h, w
    return {"width": w, "height": h, "seconds": float(d.get("format", {}).get("duration", 0))}


def check(info: dict) -> list[dict]:
    """FAILs for a file YouTube would not treat as a Short, or that is not our 9:16 frame."""
    out = []
    w, h, sec = info["width"], info["height"], info["seconds"]
    if not (w and h) or w > h:
        out.append({"rule": "SF-01", "severity": "FAIL", "detail": f"{w}x{h} is horizontal: YouTube makes it a video"})
    elif w * ASPECT[1] != h * ASPECT[0]:
        out.append({"rule": "SF-02", "severity": "FAIL", "detail": f"{w}x{h} is not 9:16 (the Short frame is 1080x1920)"})
    if not 0 < sec <= MAX_SECONDS:
        out.append({"rule": "SF-03", "severity": "FAIL", "detail": f"{sec:.1f} s: a Short is at most {MAX_SECONDS:g} s"})
    return out


def main(argv: list[str] | None = None) -> int:
    bad = 0
    for p in argv if argv is not None else sys.argv[1:]:
        info = probe(Path(p))
        found = check(info)
        bad += bool(found)
        print(f"{'FAIL' if found else 'PASS'} {p}: {info['width']}x{info['height']}, {info['seconds']:.1f} s"
              + "".join(f"\n  {f['rule']} {f['detail']}" for f in found))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
