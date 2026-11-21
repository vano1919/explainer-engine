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
# The two layouts the first mouth pod compares (the other thread, 2026-11-06 19:46 UTC): "A" = 4x2 cells of 512 px on a 2208x1120 canvas (about
# 2.5 MP, above Qwen's usual range: watch for failures), "B" = 4x2 cells of 304 px on a 1280x720 canvas (the size of the pilot's pictures).
# ONE constant picks the layout for everything here (``LAYOUT``); every function also takes ``layout=`` and ``cut_cells`` finds it from the
# image size, so the cutter does not depend on which one the pod drew. Margins centre the grid; sizes are multiples of 16.
LAYOUTS = {
    "A": {"size": (2208, 1120), "cell": (512, 512), "gutter": 32},
    "B": {"size": (1280, 720), "cell": (304, 304), "gutter": 16},
}
LAYOUT = "A"
CELL = LAYOUTS["A"]["cell"]                                              # layout A's numbers, kept as names for the first version's users
GUTTER = LAYOUTS["A"]["gutter"]
MARGIN = 32
SHEET_SIZE = LAYOUTS["A"]["size"]
IN_NAME = "{hero}__variants_in.png"
OUT_NAME = "{hero}__variants.png"
HEAD_SIDE = 2.2          # the head window is HEAD_SIDE x the face height (brow line to chin), square
STABLE = (0.0, 0.40)     # rows of the cell (fractions) used to align: hair and forehead do not move with a mouth or a blink
SCALES = tuple(np.round(np.arange(0.94, 1.0601, 0.01), 3))


def layout_of(layout: str | None = None, size: tuple[int, int] | None = None) -> dict:
    """The layout dict for a name, or found from an image size (w, h); default is the module constant ``LAYOUT``."""
    if size is not None:
        for name, L in LAYOUTS.items():
            if tuple(L["size"]) == tuple(size):
                return dict(L, name=name)
        raise ValueError(f"no variant-sheet layout is {size[0]}x{size[1]}; known: " + ", ".join(f"{n} {L['size'][0]}x{L['size'][1]}" for n, L in LAYOUTS.items()))
    return dict(LAYOUTS[layout or LAYOUT], name=layout or LAYOUT)


def _layout_of_cell(cell: np.ndarray) -> str:
    for name, L in LAYOUTS.items():
        if tuple(L["cell"]) == (cell.shape[1], cell.shape[0]):
            return name
    raise ValueError(f"no variant-sheet layout has {cell.shape[1]}x{cell.shape[0]} cells")


def cell_box(i: int, layout: str | None = None) -> tuple[int, int, int, int]:
    L = layout_of(layout)
    (W, H), (cw, ch), g = L["size"], L["cell"], L["gutter"]
    mx, my = (W - COLS * cw - (COLS - 1) * g) // 2, (H - ROWS * ch - (ROWS - 1) * g) // 2
    r, c = divmod(i, COLS)
    x0, y0 = mx + c * (cw + g), my + r * (ch + g)
    return x0, y0, x0 + cw, y0 + ch


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


def build_input_sheet(sheet_rgb: np.ndarray, feat: dict, layout: str | None = None) -> np.ndarray:
    """The hero's neutral head, upscaled to a cell, in all 8 cells on a flat grey ground: the picture Qwen is asked to vary."""
    import cv2
    L = layout_of(layout)
    x0, y0, s = head_window(feat, sheet_rgb.shape[:2])
    head = cv2.resize(sheet_rgb[y0:y0 + s, x0:x0 + s], L["cell"], interpolation=cv2.INTER_CUBIC)
    out = np.full((L["size"][1], L["size"][0], 3), 128, np.uint8)
    for i in range(len(ORDER)):
        a, b, c, d = cell_box(i, L["name"])
        out[b:d, a:c] = head
    return out


def cut_cells(sheet: np.ndarray, layout: str | None = None) -> dict[str, np.ndarray]:
    """The 8 cells; the layout is found from the image size unless named (a size that is no layout is an error)."""
    L = layout_of(layout) if layout else layout_of(size=(sheet.shape[1], sheet.shape[0]))
    if (sheet.shape[1], sheet.shape[0]) != tuple(L["size"]):
        raise ValueError(f"variant sheet is {sheet.shape[1]}x{sheet.shape[0]}, layout {L['name']} is {L['size'][0]}x{L['size'][1]}")
    out = {}
    for i, tag in enumerate(ORDER):
        a, b, c, d = cell_box(i, L["name"])
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
    m = max(8, round(h * 24 / 512))                                  # template margin, so shifts up to +-m px (~5 % of the cell) are searched
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


def cell_hole(feat: dict, layout: str | None = None) -> np.ndarray:
    """Bool mask in cell pixels of the parts that are allowed to differ (mouth/chin, both eyes)."""
    import cv2
    x0, y0, s = head_window(feat)
    sheet_h, sheet_w = 704, 1280
    m = np.maximum(moving_mask(feat, "mouth", (sheet_h, sheet_w)), moving_mask(feat, "blink", (sheet_h, sheet_w)))[y0:y0 + s, x0:x0 + s]
    cell = layout_of(layout)["cell"]
    hole = (cv2.resize(m, cell, interpolation=cv2.INTER_LINEAR) > 0.0).astype(np.uint8)
    k = max(5, round(cell[0] * 13 / 512) | 1)
    return cv2.dilate(hole, np.ones((k, k), np.uint8)) > 0       # the edges of a changed part spill a few px into the gradients


def check_cell(ref: np.ndarray, cell: np.ndarray, feat: dict, embed=None, layout: str | None = None) -> dict:
    """Align one cell to the neutral head and report {"identity", "reg_error_px", "score", "scale", "dx", "dy", "aligned"}."""
    a = align(ref, cell)
    hole = cell_hole(feat, layout or _layout_of_cell(cell))
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
