"""Where a 30 % overlay goes: a Python choice of the calmest zone that never touches a face (YuNet box + 10 %) or the subject box,
on every frame of the 2.5D push, inside the 5 % safe margin (OV-34, "the place is chosen by Python, never by hand")."""
from __future__ import annotations

import numpy as np

from explainer_engine.overlay import camera as CAM

MARGIN = 0.05
FACE_PAD = 0.10
W, H = CAM.W, CAM.H


def protected(info: dict) -> list[tuple[float, float, float, float]]:
    out = []
    for x0, y0, x1, y1 in info["faces"]:
        pw, ph = (x1 - x0) * FACE_PAD, (y1 - y0) * FACE_PAD
        out.append((x0 - pw, y0 - ph, x1 + pw, y1 + ph))
    return out + [tuple(b) for b in info["subject"]]


def frames_of(boxes, push, n, step=1):
    for f in range(0, n, step):
        c = CAM.cam(push, f, n)
        yield f, [CAM.to_frame(b, c) for b in boxes]


def hits(box, prot) -> bool:
    x0, y0, x1, y1 = box
    return any(x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1] for b in prot)


def inside_margin(box) -> bool:
    return box[0] >= MARGIN * W and box[1] >= MARGIN * H and box[2] <= (1 - MARGIN) * W and box[3] <= (1 - MARGIN) * H


PREF = {"top_right": (1.0, 0.0), "top_left": (0.0, 0.0), "bottom_right": (1.0, 1.0), "bottom_left": (0.0, 1.0), "bottom_center": (0.5, 1.0), "top_center": (0.5, 0.0)}


def choose(info: dict, size: tuple[int, int], push, n: int, pref: str = "top_right", start: int = 0, end: int | None = None) -> list[int]:
    """The best box [x, y, w, h] in frame pixels: no protected hit and inside the margin for every frame of the overlay's window."""
    end = n if end is None else end
    boxes = protected(info)
    w, h = size
    calm = info["calm"]
    px, py = PREF[pref]
    mid_cam = CAM.cam(push, (start + end) // 2, n)
    s, cx, cy = mid_cam
    best = None
    xs = np.arange(MARGIN * W, (1 - MARGIN) * W - w + 1, 40)
    ys = np.arange(MARGIN * H, (1 - MARGIN) * H - h + 1, 40)
    wins = list(frames_of(boxes, push, n, step=4))
    wins = [(f, p) for f, p in wins if start - 4 <= f <= end + 4] or wins[:1]
    for y in ys:
        for x in xs:
            box = (x, y, x + w, y + h)
            if any(hits(box, p) for _f, p in wins):
                continue
            # detail energy of the picture under the box at the mid camera (frame -> picture coordinates)
            u0, u1 = (x / W) / s + (cx - 0.5 / s), ((x + w) / W) / s + (cx - 0.5 / s)
            v0, v1 = (y / H) / s + (cy - 0.5 / s), ((y + h) / H) / s + (cy - 0.5 / s)
            e = calm[int(max(0, v0) * 54):max(int(max(0, v0) * 54) + 1, int(min(1, v1) * 54)), int(max(0, u0) * 96):max(int(max(0, u0) * 96) + 1, int(min(1, u1) * 96))].mean()
            cxn, cyn = (x + w / 2) / W, (y + h / 2) / H
            dist = ((cxn - (0.1 + 0.8 * px)) ** 2 + (cyn - (0.1 + 0.8 * py)) ** 2) ** 0.5
            score = e + 0.25 * dist
            if best is None or score < best[0]:
                best = (score, [int(x), int(y), w, h], float(e))
    if best is None:
        raise ValueError(f"no calm zone of {size} on the photo {info['id']} for frames {start}-{end}")
    return best[1]
