"""The picture-like archetypes of the visual compensator: 6 weapon and material cutaway, 8 parallax tableau, 9 primary-source
dossier card (without the stamp, D-61). Free, drawn by code, a pure function of (spec, frame) and the PNGs the spec names.

The parallax tableau cuts a picture into four depth planes by its depth map (``production/depth.py`` makes one, Depth-Anything V2
Small on the CPU) and moves them against each other in a slow dolly; a matte of the subject (BiRefNet or any other, made elsewhere)
cleans the nearest plane when the spec names one. Without a matte the planes are cut by depth alone.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.maps import draw as D
from explainer_engine.maps.timeline import Timeline, progress

ARCHETYPES = ("WEAPON_AND_MATERIAL_CUTAWAY", "PARALLAX_25D_TABLEAU", "PRIMARY_SOURCE_DOSSIER_CARD")
OPS = {
    "WEAPON_AND_MATERIAL_CUTAWAY": {"peel": "layers", "heat": "overlays", "crack": "overlays", "particles": "overlays"},
    "PARALLAX_25D_TABLEAU": {"dolly": "tableau"},
    "PRIMARY_SOURCE_DOSSIER_CARD": {"focus": "doc", "underline": "lines"},
}
PLANES = 4
TONES = {"teal": "mechanism_teal", "blue": "support_blue", "coral": "answer_coral", "amber": "uncertain_amber", "grey": "grey_mid",
         "kit": "kit_card", "paper": "paper"}


def _targets(payload: dict, key: str) -> set[str]:
    if key in ("tableau", "doc"):
        return {key}
    return {x["id"] for x in payload.get(key, [])}


def validate_payload(spec: dict) -> list[dict]:
    out, p, iid, arch = [], spec["payload"], spec["item_id"], spec["archetype_id"]

    def bad(where: str, detail: str, rule: str = "CN-01") -> None:
        out.append({"rule": rule, "severity": "FAIL", "where": f"{iid}.{where}", "detail": detail})

    for e in spec["events"]:
        key = OPS[arch].get(e["op"])
        if key is None:
            bad(f"events.{e['id']}", f"op {e['op']!r} is not one of {sorted(OPS[arch])} for {arch}")
        elif e.get("target") not in _targets(p, key):
            bad(f"events.{e['id']}", f"{e['op']} has no target {e.get('target')!r}")
    if arch == "WEAPON_AND_MATERIAL_CUTAWAY":
        for ly in p.get("layers", []):
            if len(ly.get("points", [])) < 3:
                bad(f"layers.{ly.get('id')}", "a layer is a polygon of at least three points (0..1 of the frame)")
        if not p.get("layers"):
            bad("layers", "a cutaway has layers")
    elif arch == "PARALLAX_25D_TABLEAU":
        if not p.get("picture") or not p.get("depth"):
            bad("payload", "a tableau needs picture and depth (PNG files of the job)")
    else:
        if "stamp" in p or "stamps" in p:
            bad("payload", "a dossier card carries no HISTORICAL FACT / COUNTERFACTUAL stamp: claim status lives in the claim map (D-61, SC-11)", "CMP-15")
        if not p.get("lines"):
            bad("lines", "a dossier card has lines")
    return out


def asset_findings(spec: dict, base_dir: Path | None) -> list[dict]:
    """The PNGs of a tableau exist (FAIL: it could not be drawn); only checked when the job folder is known, like the contract's other folder checks."""
    if spec["archetype_id"] != "PARALLAX_25D_TABLEAU":
        return []
    out = []
    for key in ("picture", "depth", "matte"):
        ref = spec["payload"].get(key)
        if ref and base_dir is not None and not (Path(base_dir) / ref).exists():
            out.append({"rule": "CN-01", "severity": "FAIL", "where": f"{spec['item_id']}.{key}", "detail": f"{ref} does not exist"})
    return out


# --- 6 cutaway ------------------------------------------------------------------------------------------------------------------

def _cutaway(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink = spec["payload"], (*D.rgb("ink"), 255)
    c.rect(0, 0, c.w, c.h, fill=(*D.rgb("night"), 255))
    for ly in p["layers"]:
        ev = [e for e in tl.events if e.op == "peel" and e.target == ly["id"] and e.start <= f]
        u = D.ease_in_out(progress(ev[-1], f)) if ev else 0.0
        dx, dy = ly.get("peel", [0.0, -0.3])
        pts = [((x + dx * u) * c.w, (y + dy * u) * c.h) for x, y in ly["points"]]
        alpha = int(255 * (1 - 0.92 * u))
        base = D.rgb(TONES.get(ly.get("tone", "kit"), "kit_card"))
        c.polygon(pts, fill=(*base, alpha), outline=(*D.rgb("ink"), alpha), width=c.h * 0.006)
    for ov in p.get("overlays", []):
        ev = [e for e in tl.events if e.target == ov["id"] and e.start <= f]
        if not ev:
            continue
        u = D.ease_in_out(progress(ev[-1], f))
        x, y = ov["at"][0] * c.w, ov["at"][1] * c.h
        if ov["kind"] == "heat":
            r = ov.get("radius", 0.2) * c.h
            for k in range(14, 0, -1):
                t = k / 14
                col = D.blend(D.rgb("uncertain_amber"), D.rgb("answer_coral"), 1 - t)
                c.circle(x, y, r * t * (0.4 + 0.6 * u), fill=(*col, int(26 * u + 6 * (1 - t))))
        elif ov["kind"] == "crack":
            to = ov.get("to", [ov["at"][0] + 0.2, ov["at"][1]])
            rng = D.seeded("crack", spec["item_id"], ov["id"])
            n = 14
            pts = [(x + (to[0] * c.w - x) * k / n + (rng.uniform(-1, 1) * c.h * 0.02 if 0 < k < n else 0.0),
                    y + (to[1] * c.h - y) * k / n + (rng.uniform(-1, 1) * c.h * 0.02 if 0 < k < n else 0.0)) for k in range(n + 1)]
            part = D.polyline_prefix(pts, u)
            c.line(part, ink, c.h * 0.012)
            c.line(part, (*D.rgb("paper"), 255), c.h * 0.005)
        elif ov["kind"] == "particles":
            rng = D.seeded("particles", spec["item_id"], ov["id"])
            for _ in range(ov.get("count", 40)):
                ang, speed, size = rng.uniform(0, 2 * math.pi), rng.uniform(0.05, 0.25), rng.uniform(0.004, 0.012)
                k = u * speed * c.h
                c.circle(x + math.cos(ang) * k, y + math.sin(ang) * k + u * u * c.h * 0.05, size * c.h,
                         fill=(*D.rgb("uncertain_amber"), int(255 * (1 - u) ** 0.7)))


# --- 8 parallax tableau ---------------------------------------------------------------------------------------------------------

def _stamp(path: Path) -> int:
    return path.stat().st_mtime_ns


@lru_cache(maxsize=4)
def _planes(picture: str, depth: str, matte: str | None, stamps: tuple, w: int, h: int):
    """The picture and the plane masks at the frame's size, read and cut once per item (a frame only moves them). The stamps are the
    files' modification times, so a changed file is read again; nothing cached is ever written to."""
    pic = Image.open(picture).convert("RGB").resize((w, h), Image.BICUBIC)
    d = np.asarray(Image.open(depth).convert("L").resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0
    m = None
    if matte:
        m = np.asarray(Image.open(matte).convert("L").resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0
    return pic, plane_masks(d, m)


def plane_masks(depth: np.ndarray, matte: np.ndarray | None = None) -> list[np.ndarray]:
    """``PLANES`` masks, far to near: plane k holds every pixel at or nearer than the (k/PLANES) quantile of the depth, with a
    soft edge; the first is everything, so a moved plane never leaves a hole behind it. The nearest is cut by the matte."""
    masks = []
    for k in range(PLANES):
        if k == 0:
            m = np.ones_like(depth)
        else:
            t = float(np.quantile(depth, k / PLANES))
            m = D.smoothstep(t - 0.02, t + 0.02, depth).astype(np.float32)
        masks.append(m)
    if matte is not None:
        masks[-1] = masks[-1] * matte
    return masks


def _tableau(c: D.Canvas, spec: dict, tl: Timeline, f: float, base_dir: Path) -> None:
    p = spec["payload"]
    w, h = c.w * c.ss, c.h * c.ss
    files = [Path(base_dir) / p[k] for k in ("picture", "depth")] + ([Path(base_dir) / p["matte"]] if p.get("matte") else [])
    pic, masks = _planes(str(files[0]), str(files[1]), str(files[2]) if len(files) > 2 else None, tuple(_stamp(f_) for f_ in files), w, h)
    ev = tl.of("dolly")
    start, span = (ev[0].start, ev[0].frames) if ev else (0, max(1, tl.duration - 1))
    u = D.ease_in_out(min(max((f - start) / span, 0.0), 1.0))
    dolly = p.get("dolly", {})
    scale, dx = dolly.get("scale", 1.08), dolly.get("dx", 0.012)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    for k in range(PLANES):
        near = k / (PLANES - 1)
        s = 1.0 + (scale - 1.0) * u * (0.3 + 0.7 * near) + 0.015 * (1 - near)   # the far plane is a touch large: its edge never shows
        shift = dx * w * u * (near - 0.5) * 2
        cx, cy = w / 2, h / 2
        # PIL maps output -> source: x_src = (x - cx - shift) / s + cx
        coeffs = (1 / s, 0, cx - (cx + shift) / s, 0, 1 / s, cy - cy / s)
        layer = pic.transform((w, h), Image.AFFINE, coeffs, Image.BICUBIC).convert("RGBA")
        alpha = Image.fromarray((masks[k] * 255 + 0.5).astype(np.uint8), "L").transform((w, h), Image.AFFINE, coeffs, Image.BICUBIC)
        layer.putalpha(alpha)
        out.alpha_composite(layer)
    c.replace(out)
    dust = p.get("dust")
    if dust:
        rng = D.seeded("dust", spec["item_id"], dust.get("seed", 0))
        for _ in range(dust.get("count", 40)):
            x0, y0, v, r = rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.01, 0.05), rng.uniform(0.002, 0.006)
            t = f / max(1, tl.duration)
            c.circle(((x0 + 0.02 * math.sin(6.28 * (t + y0))) % 1.0) * c.w, ((y0 - v * t * 4) % 1.0) * c.h, r * c.h,
                     fill=(*D.rgb("paper"), 90))


# --- 9 dossier card -------------------------------------------------------------------------------------------------------------

def _dossier(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> Image.Image:
    p, ink = spec["payload"], (*D.rgb("ink"), 255)
    w, h = c.w, c.h
    flat = D.Canvas(w, h, (*D.rgb("night"),), c.ss)
    cw, ch = w * 0.62, h * 0.78
    x0, y0 = (w - cw) / 2, (h - ch) / 2
    flat.rect(x0, y0, x0 + cw, y0 + ch, fill=(*D.blend(D.rgb("paper"), D.rgb("kit_card"), 0.18), 255), outline=ink, width=h * 0.006, radius=h * 0.01)
    lines = p["lines"]
    size = h * 0.07
    widest = max(flat.text_width(ln["text"] if isinstance(ln, dict) else ln, size) for ln in lines)
    size = size * min(1.0, cw * 0.86 / widest)
    y = y0 + ch * 0.14
    step = ch * 0.72 / max(len(lines), 1)
    for i, ln in enumerate(lines):
        text = ln["text"] if isinstance(ln, dict) else ln
        flat.text((x0 + cw * 0.06, y + step * i), text, size, ink, anchor="lm")
        ev = [e for e in tl.events if e.op == "underline" and isinstance(ln, dict) and e.target == ln["id"] and e.start <= f]
        if ev:
            u = D.ease_in_out(progress(ev[-1], f))
            tw = flat.text_width(text, size)
            flat.rect(x0 + cw * 0.06, y + step * i + size * 0.55, x0 + cw * 0.06 + tw * u, y + step * i + size * 0.7, fill=(*D.rgb("answer_coral"), 255))
    if p.get("source"):
        flat.text((x0 + cw * 0.06, y0 + ch * 0.93), p["source"], h * 0.035, (*D.rgb("grey_mid"), 255), anchor="lm")
    img = flat.image().convert("RGB")
    squeeze = math.sin(math.radians(p.get("tilt_deg", 14))) * 0.28 * h
    quad = (0, -squeeze, 0, h + squeeze, w, h, w, 0)       # the left edge nearer: taller than the right
    tilted = img.transform((w, h), Image.QUAD, quad, Image.BICUBIC)
    ev = tl.of("focus")
    u = D.ease_in_out(progress(ev[0], f)) if ev else 1.0
    radius = (1 - u) * h * p.get("rack_blur", 0.012)
    if radius > 0.3:
        tilted = tilted.filter(ImageFilter.GaussianBlur(radius))
    return tilted


def render_frame(spec: dict, tl: Timeline, f: int, ss: int = D.SS, base_dir: Path | None = None) -> Image.Image:
    c = D.Canvas(spec["width"], spec["height"], None, ss)
    arch = spec["archetype_id"]
    if arch == "WEAPON_AND_MATERIAL_CUTAWAY":
        _cutaway(c, spec, tl, f)
    elif arch == "PARALLAX_25D_TABLEAU":
        _tableau(c, spec, tl, f, base_dir)
    else:
        return _dossier(c, spec, tl, f)
    return c.image().convert("RGB")
