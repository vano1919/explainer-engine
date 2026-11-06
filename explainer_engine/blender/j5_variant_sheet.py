"""Variant sheets for the J5 faces (the creator, 2026-11-06 19:41 UTC: "one picture, the part's variants as a sheet, not a HD picture per
variant"; decision D-119). ONE Qwen picture per hero holds the 8 variants of the part that moves (6 Rhubarb mouth shapes A-F and 2 blink
frames) in a grid, every cell the same face; free Python cuts the cells, aligns each to the J5 card by translation and scale (no warp),
takes the mouth or eye area through a feathered mask and swaps it on the Rhubarb cue times.

The layout is ONE constant, imported by the pod job that asks Qwen and by this cutter: ``ORDER``, ``COLS``, ``ROWS``, ``CELL``, ``GUTTER``,
``MARGIN``, the file names. The input sheet (``build_input_sheet``) holds the hero's neutral head, upscaled, in all 8 cells; Qwen is asked to
change only the part named per cell.

Checks per cell (``check_cell``): ``reg_error_px`` = what is left of the shift after alignment (phase correlation of the stable upper
face, sub-pixel), ``score`` = the template score of the alignment, and ``identity`` = cosine of a gradient-orientation descriptor of the
face OUTSIDE the moving parts against the neutral head. The descriptor is a PROXY (no face-embedding model is installed here): it catches a
redrawn or drifted face, it is not an identity model; ``check_cell(..., embed=fn)`` takes a real embedder (DINO/CLIP) when one is wired.
"""
from __future__ import annotations

import numpy as np

ORDER = ("A", "B", "C", "D", "E", "F", "blink_half", "blink_full")      # reading order, left to right, top to bottom
COLS, ROWS = 4, 2
CELL = (512, 512)                                                        # px, a square window on the head
GUTTER = 32
MARGIN = 32
SHEET_SIZE = (2 * MARGIN + COLS * CELL[0] + (COLS - 1) * GUTTER, 2 * MARGIN + ROWS * CELL[1] + (ROWS - 1) * GUTTER)   # 2208 x 1120, both /16
IN_NAME = "{hero}__variants_in.png"
OUT_NAME = "{hero}__variants.png"
HEAD_SIDE = 2.2          # the head window is HEAD_SIDE x the face height (brow line to chin), square
STABLE = (0.0, 0.40)     # rows of the cell (fractions) used to align: hair and forehead do not move with a mouth or a blink
SCALES = tuple(np.round(np.arange(0.94, 1.0601, 0.01), 3))


def cell_box(i: int) -> tuple[int, int, int, int]:
    r, c = divmod(i, COLS)
    x0 = MARGIN + c * (CELL[0] + GUTTER)
    y0 = MARGIN + r * (CELL[1] + GUTTER)
    return x0, y0, x0 + CELL[0], y0 + CELL[1]


def face_height(feat: dict) -> float:
    return feat["chin_y"] - min(e[1] - e[3] / 2 for e in feat["eyes"])


def head_window(feat: dict, shape=(704, 1280)) -> tuple[int, int, int]:
    """(x0, y0, side) of the square head window in sheet pixels; the same rule cuts the input and puts a cell back."""
    fh = face_height(feat)
    side = int(round(HEAD_SIDE * fh))
    cx = (sum(e[0] for e in feat["eyes"]) / len(feat["eyes"]) + feat["mouth"][0]) / 2
    cy = min(e[1] - e[3] / 2 for e in feat["eyes"]) + fh * 0.5
    x0 = int(round(min(max(cx - side / 2, 0), shape[1] - side)))
    y0 = int(round(min(max(cy - side / 2, 0), shape[0] - side)))
    return x0, y0, side


def moving_mask(feat: dict, kind: str, shape=(704, 1280)) -> np.ndarray:
    """Soft mask (0..1, exactly 0 outside) of the mouth/chin or both eyes in sheet pixels; the features are CENTRE coordinates."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.zeros(shape, np.float32)
    if kind == "mouth":
        cx, cy, mw, _line, jaw = feat["mouth"]
        ell = [(cx, cy + jaw * 0.5, mw * 0.85 + 6, max(14.0, jaw * 2.5))]
    else:
        ell = [(cx, cy, ew * 0.8 + 4, eh * 1.4 + 3) for cx, cy, ew, eh in feat["eyes"]]
    for cx, cy, ax, ay in ell:
        r = np.sqrt(((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2)
        m = np.maximum(m, np.clip((1.0 - r) * min(ax, ay) / 3.0, 0.0, 1.0))
    return m


def build_input_sheet(sheet_rgb: np.ndarray, feat: dict) -> np.ndarray:
    """The hero's neutral head, upscaled to a cell, in all 8 cells on a flat grey ground: the picture Qwen is asked to vary."""
    import cv2
    x0, y0, s = head_window(feat, sheet_rgb.shape[:2])
    head = cv2.resize(sheet_rgb[y0:y0 + s, x0:x0 + s], CELL, interpolation=cv2.INTER_CUBIC)
    out = np.full((SHEET_SIZE[1], SHEET_SIZE[0], 3), 128, np.uint8)
    for i in range(len(ORDER)):
        a, b, c, d = cell_box(i)
        out[b:d, a:c] = head
    return out


def cut_cells(sheet: np.ndarray) -> dict[str, np.ndarray]:
    if sheet.shape[1] != SHEET_SIZE[0] or sheet.shape[0] != SHEET_SIZE[1]:
        raise ValueError(f"variant sheet is {sheet.shape[1]}x{sheet.shape[0]}, expected {SHEET_SIZE[0]}x{SHEET_SIZE[1]}")
    out = {}
    for i, tag in enumerate(ORDER):
        a, b, c, d = cell_box(i)
        out[tag] = sheet[b:d, a:c].copy()
    return out


def _gray(a: np.ndarray) -> np.ndarray:
    return (a[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32))


def align(ref: np.ndarray, cell: np.ndarray) -> dict:
    """Translation and scale (no warp) that bring ``cell`` onto ``ref``: a template search on the stable upper face over ``SCALES``,
    refined to sub-pixel by a parabola; returns {"scale", "dx", "dy", "score", "reg_error_px", "aligned"}."""
    import cv2
    g0, g1 = _gray(ref), _gray(cell)
    h = g0.shape[0]
    r0, r1 = int(STABLE[0] * h), int(STABLE[1] * h)
    m = 24                                                           # template margin, so shifts up to +-m px are searched
    tpl = g0[r0 + m:r1, m:-m].astype(np.float32)
    best = None
    for sc in SCALES:
        M = np.array([[sc, 0, (1 - sc) * h / 2], [0, sc, (1 - sc) * h / 2]], np.float32)
        gs = cv2.warpAffine(g1, M, (g1.shape[1], g1.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        res = cv2.matchTemplate(gs[r0:r1 + m].astype(np.float32), tpl, cv2.TM_CCOEFF_NORMED)   # +-m px around the expected place only
        _, mx, _, loc = cv2.minMaxLoc(res)
        if best is None or mx > best[0]:
            best = (mx, sc, loc, res)
    score, sc, loc, res = best
    x, y = loc

    def sub(v, lo, mid, hi):
        d = lo - 2 * mid + hi
        return 0.0 if abs(d) < 1e-9 else 0.5 * (lo - hi) / d
    sx = sub(0, res[y, x - 1], res[y, x], res[y, x + 1]) if 0 < x < res.shape[1] - 1 else 0.0
    sy = sub(0, res[y - 1, x], res[y, x], res[y + 1, x]) if 0 < y < res.shape[0] - 1 else 0.0
    dx, dy = m - (x + sx), m - (y + sy)                       # shift to apply after scaling about the centre
    A = np.array([[sc, 0, (1 - sc) * h / 2 + dx], [0, sc, (1 - sc) * h / 2 + dy]], np.float32)
    aligned = cv2.warpAffine(cell, A, (cell.shape[1], cell.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    ga = _gray(aligned)[r0:r1, m:-m]
    (rx, ry), _ = cv2.phaseCorrelate(g0[r0:r1, m:-m].astype(np.float64), ga.astype(np.float64))
    return {"scale": float(sc), "dx": float(dx), "dy": float(dy), "score": float(score), "reg_error_px": float(np.hypot(rx, ry)),
            "aligned": aligned}


def descriptor(a: np.ndarray, hole: np.ndarray | None = None) -> np.ndarray:
    """Gradient-orientation histograms on a 6x6 grid (the proxy for identity); ``hole`` (bool, cell size) zeroes the moving parts."""
    import cv2
    g = _gray(a)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag, ang = np.hypot(gx, gy), (np.arctan2(gy, gx) % np.pi)
    if hole is not None:
        mag = np.where(hole, 0.0, mag)
    h, w = g.shape
    feats = []
    for r in range(6):
        for c in range(6):
            sl = (slice(r * h // 6, (r + 1) * h // 6), slice(c * w // 6, (c + 1) * w // 6))
            hist, _ = np.histogram(ang[sl], bins=8, range=(0, np.pi), weights=mag[sl])
            feats.append(hist)
    v = np.concatenate(feats).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def cell_hole(feat: dict) -> np.ndarray:
    """Bool mask in cell pixels of the parts that are allowed to differ (mouth/chin, both eyes)."""
    import cv2
    x0, y0, s = head_window(feat)
    sheet_h, sheet_w = 704, 1280
    m = np.maximum(moving_mask(feat, "mouth", (sheet_h, sheet_w)), moving_mask(feat, "blink", (sheet_h, sheet_w)))[y0:y0 + s, x0:x0 + s]
    hole = (cv2.resize(m, CELL, interpolation=cv2.INTER_LINEAR) > 0.0).astype(np.uint8)
    return cv2.dilate(hole, np.ones((13, 13), np.uint8)) > 0       # the edges of a changed part spill a few px into the gradients


def check_cell(ref: np.ndarray, cell: np.ndarray, feat: dict, embed=None) -> dict:
    """Align one cell to the neutral head and report {"identity", "reg_error_px", "score", "scale", "dx", "dy", "aligned"}."""
    a = align(ref, cell)
    hole = cell_hole(feat)
    emb = embed or (lambda im: descriptor(im, hole))
    e0, e1 = emb(ref), emb(a["aligned"])
    a["identity"] = float(np.dot(e0, e1) / (np.linalg.norm(e0) * np.linalg.norm(e1) + 1e-9))
    return a


def variant_sheets(sheet_rgb: np.ndarray, aligned: dict[str, np.ndarray], feat: dict) -> dict[str, np.ndarray]:
    """{tag: the hero sheet with that variant's mouth (A-F) or eyes (blinks) put in}: each aligned cell is shrunk back to the head window
    in sheet pixels and composited through the feathered mask; every pixel outside the mask is the sheet's own."""
    import cv2
    x0, y0, s = head_window(feat, sheet_rgb.shape[:2])
    out = {}
    for tag, cell in aligned.items():
        kind = "blink" if tag.startswith("blink") else "mouth"
        m = moving_mask(feat, kind, sheet_rgb.shape[:2])
        win = cv2.resize(cell, (s, s), interpolation=cv2.INTER_AREA).astype(np.float32)
        full = sheet_rgb.copy()
        mm = m[y0:y0 + s, x0:x0 + s]
        base = sheet_rgb[y0:y0 + s, x0:x0 + s].astype(np.float32)
        mixed = base * (1 - mm[..., None]) + win * mm[..., None]
        sel = mm > 0
        reg = full[y0:y0 + s, x0:x0 + s]
        reg[sel] = np.clip(np.rint(mixed[sel]), 0, 255).astype(np.uint8)
        out[tag] = full
    return out


def blend_sheet(base: np.ndarray, variants: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """The sheet at one frame: the weighted mix of the variant sheets (``j5_face.cue_weights``, 55 ms cross-fade; A is the base when asked)."""
    acc = np.zeros(base.shape, np.float32)
    tot = sum(weights.values()) or 1.0
    for k, w in weights.items():
        acc += (variants[k] if k in variants else base).astype(np.float32) * (w / tot)
    return np.clip(np.rint(acc), 0, 255).astype(np.uint8)
