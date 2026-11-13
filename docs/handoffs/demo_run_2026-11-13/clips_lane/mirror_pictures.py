"""FL-311 (audit round 4): the script puts Thomas screen LEFT and Friedrich screen RIGHT in every two-hero shot; these 18
pictures show them the other way round. Mirror each left-to-right (none carries lettering, audit); no model call, free.
Usage: python mirror_pictures.py <final_scene_frames json> <pictures dir> <out dir>"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

FLIP = ("S04_SH009 S04_SH013 S05_SH005 S05_SH007 S05_SH008 S05_SH010 S05_SH011 S05_SH012 S05_SH013 S05_SH018 S06_SH002 S06_SH003 "
        "S06_SH007 S06_SH008 S06_SH010 S06_SH011 S07_SH002 S07_SH003").split()
frames = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["frames"]
pics, out = Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
for shot in FLIP:
    v = frames[shot + "_start"]
    src = Path(v["file"]) if v["file"].startswith("/") else pics / v["file"]
    ImageOps.mirror(Image.open(src).convert("RGB")).save(out / f"{shot}_start_mirror.png")
    print(shot, src.name)
