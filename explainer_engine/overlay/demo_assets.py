"""Pictures of the demo: the three existing photos (no new generation), their faces (YuNet) and a calm map.

M1 and M3 are the bake-off inputs, C1 is ``ltx_scene_test/start_c1.png``; all are put on one 2752x1548 (16:9) canvas. Nothing is made
by a paid service. ``subject`` is the main object box (normalised), added to the faces.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

PLAN = Path("/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12")
PHOTOS = {
    "M1": dict(path=PLAN / "bakeoff_report/in/M1.jpg", subject=[(0.30, 0.28, 0.64, 1.0)]),
    "M3": dict(path=PLAN / "bakeoff_report/in/M3.jpg", subject=[(0.20, 0.26, 0.52, 0.97)]),
    "C1": dict(path=PLAN / "ltx_scene_test/start_c1.png", subject=[(0.15, 0.0, 0.97, 0.62)]),
}
SW, SH = 2752, 1548
YUNET = "/tmp/claude-0/yunet/face_detection_yunet_2023mar.onnx"


def prepared(pid: str) -> Image.Image:
    im = Image.open(PHOTOS[pid]["path"]).convert("RGB")
    w, h = im.size
    nw = min(w, round(h * 16 / 9))
    nh = min(h, round(w * 9 / 16))
    box = ((w - nw) // 2, (h - nh) // 2, (w - nw) // 2 + nw, (h - nh) // 2 + nh)
    return im.crop(box).resize((SW, SH), Image.LANCZOS)


def faces(img: Image.Image) -> list[tuple[float, float, float, float]]:
    import cv2
    arr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(YUNET, "", (arr.shape[1], arr.shape[0]), 0.6, 0.3, 5000)
    _, res = det.detect(arr)
    out = []
    for r in (res if res is not None else []):
        x, y, w, h = r[:4]
        out.append((float(max(0.0, x / SW)), float(max(0.0, y / SH)), float(min(1.0, (x + w) / SW)), float(min(1.0, (y + h) / SH))))
    return out


def calm(img: Image.Image) -> np.ndarray:
    """Detail energy map (96x54, 0..1): gradient magnitude of the blurred luminance; low = a calm zone."""
    g = np.asarray(img.convert("L").resize((384, 216), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
    gy, gx = np.gradient(g)
    e = np.hypot(gx, gy)
    e = Image.fromarray(np.uint8(np.clip(e * 6, 0, 255))).resize((96, 54), Image.BOX)
    return np.asarray(e, dtype=np.float32) / 255.0


def info(pid: str, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{pid}.json"
    if f.exists():
        d = json.loads(f.read_text())
        d["calm"] = np.load(cache / f"{pid}_calm.npy")
        return d
    img = prepared(pid)
    img.save(cache / f"{pid}.png")
    c = calm(img)
    np.save(cache / f"{pid}_calm.npy", c)
    d = dict(id=pid, faces=faces(img), subject=PHOTOS[pid]["subject"], size=[SW, SH], source=str(PHOTOS[pid]["path"]))
    f.write_text(json.dumps(d, indent=1))
    d["calm"] = c
    return d
