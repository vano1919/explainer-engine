"""Free checks of every new-world picture before Claude's look and ვანო's pick (ვანო 2026-10-26 12:30 Tbilisi: "check every
picture while generating, give it a score, find what is wrong, throw it away and generate it again").

Each picture gets measured numbers and a verdict with reasons; a FAIL is redrawn with the next seed:
  background  person / object: the outer 6 % border is plain warm off-white (light, low saturation, low spread)
  show_hues   the training show's signature hues (sky cyan, lime green: light and saturated) stay a small share
  palette     share of coloured pixels near the agreed palette (sheet.CORE) is high enough
  clip        zero-shot CLIP (training.embed): when the wrong-kind prompt comes close to the right one (a person in a place,
              a hand or person with an object, two people where one stands) the picture is REVIEW, never PASS by itself;
              clip_style ("flat ink cartoon" vs photo / 3D / watercolour / oil) is recorded only: on the 16 approved
              samples it was negative for all of them, so it cannot gate
Calibrated 2026-10-26 on the 16 approved samples (all PASS: palette at 50 >= 0.81, border std <= 24.4) against the
napoleon_tent pictures in the show's colours (palette at 50 down to 0.2). Claude then looks at every sheet; the numbers only
pre-sort. The limits are written into every report row.
"""
from __future__ import annotations

import colorsys

import numpy as np

PALETTE = {"navy": (31, 45, 92), "crimson": (176, 32, 46), "gold": (226, 178, 48), "ochre": (204, 118, 44),
           "forest": (46, 105, 58), "burgundy": (112, 30, 48), "cream": (240, 228, 204), "charcoal": (40, 38, 40),
           "skin": (226, 172, 132), "wood": (140, 90, 50), "stone": (150, 140, 125), "sky": (60, 80, 140)}
LIMITS = {"border_light": 200, "border_sat": 0.22, "border_std": 30.0, "show_hues": 0.06, "palette": 0.6, "palette_dist": 50,
          "clip_kind": 0.02}
CLIP = {
    "person": (["one cartoon person standing alone on a plain background"],
               ["two people standing together", "a crowd of people", "a landscape scene with buildings"]),
    "place": (["an empty cartoon place with no people"], ["a cartoon person standing in a place", "a group of people"]),
    "object": (["a single cartoon object on a plain background"], ["a cartoon person holding an object", "a human hand"]),
}
STYLE_TEXT = (["a flat 2D cartoon drawing with bold black ink outlines"],
              ["a photograph", "a 3D render", "a watercolour painting", "an oil painting"])


def _rgb(path, size=256):
    from PIL import Image
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB").resize((size, size)), dtype=np.float32)


def border(a, frac=0.06):
    n = max(1, int(a.shape[0] * frac))
    b = np.concatenate([a[:n].reshape(-1, 3), a[-n:].reshape(-1, 3), a[:, :n].reshape(-1, 3), a[:, -n:].reshape(-1, 3)])
    mx, mn = b.max(1), b.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return {"border_light": float(b.mean()), "border_sat": float(sat.mean()), "border_std": float(b.std(0).mean())}


def hues(a):
    px = a.reshape(-1, 3) / 255.0
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[::7]])
    h, s, v = hsv[:, 0] * 360, hsv[:, 1], hsv[:, 2]
    coloured = s > 0.25
    show = coloured & (v > 0.6) & (((h > 170) & (h < 200)) | ((h > 75) & (h < 110)))
    return {"show_hues": float(show.mean())}


def palette(a):
    px = a.reshape(-1, 3)[::5]
    pal = np.array(list(PALETTE.values()), dtype=np.float32)
    d = np.sqrt(((px[:, None, :] - pal[None]) ** 2).sum(-1)).min(1)
    return {"palette": float((d < LIMITS["palette_dist"]).mean())}


def clip_scores(paths, kinds):
    from explainer_engine.training import embed
    ims = embed.images(paths)
    out = []
    for v, kind in zip(ims, kinds):
        good, bad = CLIP[kind]
        g = float(np.max(embed.texts(good) @ v)); b = float(np.max(embed.texts(bad) @ v))
        sg = float(np.max(embed.texts(STYLE_TEXT[0]) @ v)); sb = float(np.max(embed.texts(STYLE_TEXT[1]) @ v))
        out.append({"clip_kind": round(g - b, 4), "clip_style": round(sg - sb, 4)})
    return out


def verdict(kind, m):
    why = []
    if kind in ("person", "object"):
        if m["border_light"] < LIMITS["border_light"] or m["border_sat"] > LIMITS["border_sat"] or \
                m["border_std"] > LIMITS["border_std"]:
            why.append("background not plain off-white")
    if m["show_hues"] > LIMITS["show_hues"]:
        why.append("too much of the show's cyan/lime")
    if m["palette"] < LIMITS["palette"]:
        why.append("colours off the palette")
    if why:
        return "FAIL", why
    if m.get("clip_kind", 1) < LIMITS["clip_kind"]:
        return "REVIEW", [{"person": "maybe not one person alone", "place": "maybe people in the place",
                           "object": "maybe a person or hand with the object"}[kind]]
    return "PASS", []


def score(rows, with_clip=True):
    """rows: [{name, path, kind}] -> the same rows with measures, score 0-100, verdict and reasons."""
    ms = []
    for r in rows:
        a = _rgb(r["path"])
        m = {**border(a), **hues(a), **palette(a)}
        ms.append(m)
    if with_clip and rows:
        for m, c in zip(ms, clip_scores([r["path"] for r in rows], [r["kind"] for r in rows])):
            m.update(c)
    out = []
    for r, m in zip(rows, ms):
        v, why = verdict(r["kind"], m)
        pts = 100 - 30 * len(why) * (v == "FAIL") - 15 * (v == "REVIEW")
        out.append({**r, **{k: round(x, 4) for k, x in m.items()}, "score": max(pts, 0), "verdict": v, "why": why,
                    "limits": LIMITS})
    return out
