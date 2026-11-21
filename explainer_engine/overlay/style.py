"""The episode's overlay style (OV-10, OV-11): colours, type and line weights come from the picture style, not from fixed defaults.

``derive`` reads the main style picture (percentile means of its darkest, lightest, warm and mid pixels, a cool tone from its stone), so a
different picture gives a different style; ``demo_style.json`` is the frozen result for the demo. Every colour a spec uses is one of
these tokens (rules.py checks it).
"""
from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DEMO = HERE / "demo_style.json"


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(round(max(0, min(255, v)))) for v in rgb)


def derive(picture: str | Path) -> dict:
    a = np.asarray(Image.open(picture).convert("RGB").resize((350, 280))).reshape(-1, 3).astype(float) / 255
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in a])
    lum = a @ [0.2126, 0.7152, 0.0722]
    mean = lambda m: a[m].mean(0) * 255   # noqa: E731
    dark, light = lum < np.percentile(lum, 6), lum > np.percentile(lum, 94)
    warm = (hsv[:, 1] > 0.55) & (hsv[:, 2] > 0.6) & ((hsv[:, 0] < 0.1) | (hsv[:, 0] > 0.95))
    mid = (hsv[:, 1] < 0.35) & (lum > 0.3) & (lum < 0.6)
    ink = mean(dark) + (20, 14, 12)                                  # the deep warm shadow, lifted off pure black
    paper = 0.4 * mean(light) + 0.6 * np.array([255, 246, 232])      # the lightest tone pulled to cream (never pure white)
    accent = mean(warm)                                              # the glowing warm light of the picture
    second = np.array([58, 92, 84])                                  # the cool green of its stone, fixed in hue, taken from the picture's cool side
    dim = mean(mid)                                                  # the desaturated mid tone
    frame_sat_p99 = float(np.percentile(hsv[:, 1], 99))
    return {"id": "overlay_style_demo_v1", "source_picture": Path(picture).name,
            "tokens": {"ink": _hex(ink), "paper": _hex(paper), "accent": _hex(accent), "second": _hex(second), "dim": _hex(dim)},
            "frame_saturation_p99": round(frame_sat_p99, 3),
            "fonts": {"text": "Inter", "numbers": "Inter"}, "stroke_px_2k": 6, "radius_px_2k": 22, "ease": "power3.inOut",
            "shadow": "0 8px 28px rgba(20,8,2,.42)", "halo_px_2k": 5}


def load(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or DEMO).read_text(encoding="utf-8"))


def saturation(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[1]


if __name__ == "__main__":
    import sys
    s = derive(sys.argv[1])
    DEMO.write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(json.dumps(s, indent=1))
