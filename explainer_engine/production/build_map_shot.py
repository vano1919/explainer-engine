"""Map shots for build_shot: a spec with ``"kind": "map"`` goes to the offline MapLibre lane (``maps/maplibre_lane/render.py``) with the episode
film's map style (``truce_cold`` etc.: colours, front line, HUD, font, finish) and the owner's five camera moves; the output is a 1280x720 / 24 fps
mp4 like the photo shots, so ``build_episode`` can cut them together. Tiles come from ``--tile-dir`` / ``$EXPLAINER_MAP_TILES`` (one-time free
download: ``maps/maplibre_lane/fetch_tiles.py``). Needs playwright + a Chromium (``$EXPLAINER_CHROMIUM``) and the vendored maplibre-gl files.
The front line of a spec is whatever its ``line_geojson`` holds; ``examples/maps/truce_front_1914/`` has a minimal one traced from the public-domain
West Point map (``maps/trace_front_1914.py``, approximate, not a claim source).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np


# the look of the episode's photos laid over the flat map page (owner 2026-11-21: "not in the film style"): warm cream highlights, cool shadows, a little less
# colour, lifted blacks, paper fibre and stains, vignette, a stronger per-frame grain. Spec key "film_post" overrides single values; "film_post": false switches it off.
FILM_POST = dict(desat=0.22, lift=0.035, warm=(0.90, 0.955, 1.02), cool=(1.04, 1.0, 0.95), paper=0.20, stains=0.10, vignette=0.38, grain=0.55)
ARROW_DEFAULT_COLOR = "#2a3138"


def _hex_bgr(h):
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def _paper(h, w, seed=7):
    import cv2
    rs = np.random.RandomState(seed)
    fib = cv2.GaussianBlur(rs.rand(h, w).astype(np.float32), (0, 0), 1.1) - 0.5
    fib = fib / (fib.std() + 1e-6)
    low = cv2.resize(rs.rand(9, 16).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    low = (low - low.mean()) / (low.std() + 1e-6)
    return fib, low


def _arrow_points(path, spec, f, size):
    from explainer_engine.maps import maplibre_spec as MS
    from explainer_engine.maps.maplibre_lane.render import _lonlat_to_pixel
    cam = MS.camera_state(spec, f)
    return [_lonlat_to_pixel(lo, la, tuple(cam["center"]), cam["zoom"], size) for lo, la in path]


def _draw_arrows(img, spec, f, fps, size):
    """Animated arrows (spec "arrows"): each grows along its geo path between t[0] and t[1] (smoothstep), then stays; the head follows the tip."""
    import cv2
    arrows = spec.get("arrows") or []
    if not arrows:
        return img
    t = f / fps
    k = size[0] / 1280.0
    SS = 2
    layer = np.zeros((size[1] * SS, size[0] * SS, 4), np.float32)
    for a in arrows:
        t0, t1 = a["t"]
        u = min(1.0, max(0.0, (t - t0) / max(1e-6, t1 - t0)))
        u = u * u * (3 - 2 * u)
        if u <= 0:
            continue
        pts = np.array(_arrow_points(a["path"], spec, f, size), np.float32) * SS
        seg = np.hypot(*np.diff(pts, axis=0).T)
        total = float(seg.sum())
        want = total * u
        out, acc = [pts[0]], 0.0
        for i, sl in enumerate(seg):
            if acc + sl >= want:
                r = (want - acc) / max(sl, 1e-6)
                out.append(pts[i] + (pts[i + 1] - pts[i]) * r)
                break
            out.append(pts[i + 1]); acc += sl
        poly = np.array(out, np.float32)
        if len(poly) < 2:
            continue
        w = float(a.get("width", 9)) * k * SS
        col = _hex_bgr(a.get("color", ARROW_DEFAULT_COLOR))
        cas = (235, 238, 240)
        for width, c in ((w + 5 * SS, cas), (w, col)):
            cv2.polylines(layer, [poly.astype(np.int32)], False, (*[v / 255 for v in c], 1.0), int(round(width)), cv2.LINE_AA)
        d = poly[-1] - poly[max(0, len(poly) - 2)]
        d = d / (np.hypot(*d) + 1e-6)
        n = np.array([-d[1], d[0]], np.float32)
        L, Wd = 4.2 * w, 2.4 * w
        tip = poly[-1] + d * L * 0.6
        head = np.array([tip, poly[-1] - d * L * 0.4 + n * Wd, poly[-1] - d * L * 0.4 - n * Wd], np.int32)
        if u > 0.06:
            cv2.fillPoly(layer, [head + 0], (*[v / 255 for v in cas], 1.0), cv2.LINE_AA)
            inner = np.array([poly[-1] + d * L * 0.45, poly[-1] - d * L * 0.3 + n * Wd * 0.72, poly[-1] - d * L * 0.3 - n * Wd * 0.72], np.int32)
            cv2.fillPoly(layer, [inner], (*[v / 255 for v in col], 1.0), cv2.LINE_AA)
    layer = cv2.resize(layer, size, interpolation=cv2.INTER_AREA)
    al = layer[..., 3:4]
    return img * (1 - al * 0.92) + layer[..., :3] * al * 0.92


def _film(img, f, cfg, paper_fib, paper_low, vig):
    import cv2
    g = img.mean(axis=2, keepdims=True)
    img = img * (1 - cfg["desat"]) + g * cfg["desat"]
    img = cfg["lift"] + img * (1 - cfg["lift"])
    lum = np.clip(g, 0, 1)
    warm, cool = np.array(cfg["warm"], np.float32), np.array(cfg["cool"], np.float32)
    img = img * (cool * (1 - lum) + warm * lum)
    img = img * (1 - cfg["paper"] * 0.35 * paper_fib[..., None] / 3 - cfg["stains"] * 0.4 * (paper_low[..., None] / 3))
    img = img * (1 - cfg["vignette"] * vig[..., None])
    rs = np.random.RandomState(f + 101)
    n = cv2.GaussianBlur(rs.normal(0.5, 0.2, img.shape[:2]).astype(np.float32), (0, 0), 0.7)[..., None]
    ov = np.where(img < 0.5, 2 * img * n, 1 - 2 * (1 - img) * (1 - n))
    img = img * (1 - cfg["grain"]) + ov * cfg["grain"]
    return np.clip(img, 0, 1)


def post(in_mp4, out_mp4, spec, film_post=True) -> dict:
    """Arrows + the photos' film look over the lane's render. Every frame is a pure function of its number."""
    import cv2
    from explainer_engine.production.build_shot import vignette_map
    cap = cv2.VideoCapture(str(in_mp4))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    cfg = dict(FILM_POST, **(film_post if isinstance(film_post, dict) else {}))
    fib, low = _paper(h, w)
    vig = vignette_map(h, w)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(out_mp4)], stdin=subprocess.PIPE)
    f = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        img = fr.astype(np.float32) / 255.0
        img = _draw_arrows(img, spec, f, fps, (w, h))
        if film_post:
            img = _film(img, f, cfg, fib, low, vig)
        enc.stdin.write((img * 255 + 0.5).astype(np.uint8).tobytes())
        f += 1
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("ffmpeg failed in map post")
    return dict(frames=f, arrows=len(spec.get("arrows") or []), film_post=cfg if film_post else None)


class MapShotError(ValueError):
    """The map spec would silently degrade (static camera, no film): refused before anything is rendered."""


def check_spec(raw: dict) -> None:
    """build_shot's map path fails loudly where the lane itself would fall back: a missing camera is a STATIC map (owner: five moves, no static), a missing film is no
    episode look. ``arrows`` need a valid ``t`` window and a path of at least two points."""
    from explainer_engine.maps import maplibre_spec as MS
    problems = []
    cam = raw.get("camera")
    if not isinstance(cam, dict) or cam.get("move") not in MS.ALLOWED_CAMERA_MOVES:
        problems.append(f"camera with one of {MS.ALLOWED_CAMERA_MOVES} is required (a map without it would be static)")
    if not raw.get("film_file"):
        problems.append("film_file is required (the map takes its look only from the episode film)")
    for i, a in enumerate(raw.get("arrows") or []):
        if len(a.get("path", [])) < 2 or not (isinstance(a.get("t"), list) and len(a["t"]) == 2 and a["t"][0] < a["t"][1]):
            problems.append(f"arrows[{i}] needs a path of 2+ points and t=[t0, t1] with t0 < t1")
    if problems:
        raise MapShotError("; ".join(problems))


def build(spec_path, out_mp4, workdir=None, tile_dir=None) -> dict:
    from explainer_engine.maps.maplibre_lane import render

    tiles = tile_dir or os.environ.get("EXPLAINER_MAP_TILES")
    if not tiles:
        raise ValueError("map shot: give --tile-dir or set EXPLAINER_MAP_TILES (offline tiles from maplibre_lane/fetch_tiles.py)")
    spec_path = Path(spec_path).resolve()
    check_spec(json.loads(spec_path.read_text(encoding="utf-8")))
    if workdir:
        Path(workdir).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="map_shot_", dir=str(workdir) if workdir else None))   # own folder per shot: parallel builds never share frames
    own = True
    from explainer_engine.maps import maplibre_spec as MS
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    try:
        base = work / "lane.mp4"
        info = render.render_shot(str(spec_path), str(base), str(tiles), str(work))
        fp = raw.get("film_post", True)
        lane_spec = MS.load_shot_spec(spec_path)
        lane_spec["arrows"] = raw.get("arrows")
        post_info = post(base, out_mp4, lane_spec, fp if fp is not False else False)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    log = dict(id=spec_path.stem, kind="map", out=str(out_mp4), render=info, post=post_info)
    Path(out_mp4).with_suffix(".render_log.json").write_text(json.dumps(log, indent=1, default=str), encoding="utf-8")
    return log
