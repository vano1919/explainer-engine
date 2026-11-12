"""Backgrounds of the demo shots, drawn by Python (OV-10: the overlay's look comes from the episode picture; the map plate is tinted
with the same tokens, OV-24: a solid background is a relief plate or a style card, never a flat colour).

``photo`` shots push the picture with ``camera.cam``; ``map`` shots push the plate with ``camera.plate_affine``; ``card`` shots are the
episode photo darkened, blurred and given the film's grain (a style card). Frames go to one ffmpeg through a pipe.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.maps import geo, plate, relief
from explainer_engine.maps import draw as D
from explainer_engine.overlay import camera as CAM
from explainer_engine.overlay import demo_assets as A

W, H, FPS = CAM.W, CAM.H, 24


def hexrgb(h: str) -> tuple[int, int, int]:
    n = int(h[1:], 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def blend(a, b, t):
    return tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b))


def style_colours(tokens: dict):
    paper, ink, second, dim = (hexrgb(tokens[k]) for k in ("paper", "ink", "second", "dim"))
    sea = blend(second, paper, 0.50)
    base = {"sea": sea, "land": blend(paper, hexrgb(tokens["accent"]), 0.10), "coast": blend(ink, paper, 0.15), "river": blend(sea, paper, 0.35),
            "border": blend(dim, ink, 0.25), "lake": blend(sea, paper, 0.12)}
    return lambda look=None: dict(base)


def map_plate(view: dict, size: tuple[int, int], tokens: dict, out: Path, ss: int = 2) -> Path:
    """A relief plate tinted with the style tokens (the repo's plate module, its colour function swapped for this call only)."""
    old = plate.colours
    plate.colours = style_colours(tokens)
    try:
        im = plate.render_plate(geo.View(view["lon"], view["lat"], view["span_km"], size[0], size[1]), ss=ss, shaded_relief=relief.raster_path().exists())
    finally:
        plate.colours = old
    im.save(out)
    return out


def card_source(pid: str, cache: Path) -> Image.Image:
    """The style card: the photo darkened and blurred with a soft vignette."""
    im = Image.open(cache / f"{pid}.png").convert("RGB").filter(ImageFilter.GaussianBlur(26))
    a = np.asarray(im, np.float32) * 0.42
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    r = np.hypot((xx / a.shape[1] - 0.5) * 1.1, (yy / a.shape[0] - 0.5))
    a *= (1.0 - 0.55 * np.clip(r - 0.25, 0, 1))[..., None]
    return Image.fromarray(np.uint8(np.clip(a, 0, 255)))


def writer(out: Path, crf: int = 12) -> subprocess.Popen:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", str(out)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render(shot: dict, spec: dict, out: Path, cache: Path, tokens: dict) -> dict:
    """Write the background video of one shot; returns {kind, plate} for the compositor."""
    n = spec["frames"]
    proc = writer(out)
    meta: dict = {"bg": shot.get("bg") or "photo"}
    if shot.get("bg") == "map":
        pp = map_plate(shot["view"], (W, H), tokens, out.with_suffix(".plate.png"))
        src, aff = Image.open(pp).convert("RGB"), lambda f: CAM.plate_affine(spec["world_k"], f, n, W, H)
        meta["plate"] = str(pp)
    elif shot.get("bg") == "card":
        src = card_source(shot["photo"], cache).resize((CAM.W, CAM.H), Image.BICUBIC) if False else card_source(shot["photo"], cache)
        sw, sh = src.size
        push = (1.0, 1.05, 0.5, 0.5)
        aff = lambda f: CAM.affine(CAM.cam(push, f, n), sw, sh)
    else:
        src = Image.open(cache / f"{shot['photo']}.png").convert("RGB")
        sw, sh = src.size
        push = tuple(shot["push"])
        aff = lambda f: CAM.affine(CAM.cam(push, f, n), sw, sh)
    try:
        for f in range(n):
            fr = src.transform((W, H), Image.AFFINE, aff(f), resample=Image.BICUBIC)
            proc.stdin.write(fr.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg background writer failed")
    return meta
