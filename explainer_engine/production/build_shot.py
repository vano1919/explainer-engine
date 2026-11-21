"""build_shot: one still picture + a shot spec -> one finished clip (depth -> 2.5D parallax + camera move + living effects + the episode film's finish).

One command for the pieces that used to live apart: ``fx25d/depth_metres.py`` (Depth-Anything V2 Small, cached .npy), ``fx25d/living.py``
(2.5D parallax, fire, snow, mist, sky, 2D smoke; the owner's five camera moves), the episode film (``episode_film.py``: its ``map.style_preset``
names ``maps/maplibre_lane/styles/<name>.json``, whose ``finish`` block (tint, vignette, grain) and ``font`` are the one look of the episode, applied
to photos exactly as the map page applies it to maps). CPU only, nothing paid. Every frame is a pure function of its number.

Spec (JSON, paths relative to the spec file):
  {"id": "S01_SH001", "kind": "photo", "photo": "S01_SH001.jpeg", "film_file": "episode_film.json", "seconds": 6.0,
   "camera": {"move": "truck_zoom_in", "dir": 1},                  # REQUIRED; one of the five moves (no orbit, no static)
   "depth_range": {"near_m": 2.5, "far_m": 60.0},                  # optional; ASSUMED metres, see fx25d/depth_metres.py
   "living": {"fires": [], "smoke": [], "sway_trees": [], "sway_cloth": [], "candles": [], "persons": [], "wind": [1, 0],
              "snow": 0.7, "mist": 0.25, "sky_amp": 0.6, "person_mask": "mask.png"},   # all optional, picture coordinates 1376x768
   "caption": {"text": "...", "t0": 0.5, "t1": 4.0}}               # optional; set in the film preset's font
A plume with ``avoid: true`` needs person zones (``persons`` polygons or ``person_mask``); its share on people is measured at checkpoints and the
shot FAILS above the limit of ``qa/plume_zones`` (a hypothesis limit, not the owner's number). A "kind": "map" spec is handed to the map lane.

usage: python -m explainer_engine.production.build_shot spec.json out.mp4 [--cache-dir DIR] [--workdir DIR]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from explainer_engine import episode_film
from explainer_engine.fx25d import living as LV
from explainer_engine.fx25d.depth_metres import DEFAULT_FAR_M, DEFAULT_NEAR_M, ensure_depth

STYLES = Path(__file__).resolve().parents[1] / "maps" / "maplibre_lane" / "styles"
LIVING_DEFAULT = dict(fires=[], smoke=[], sway_trees=[], sway_cloth=[], candles=[], persons=[], wind=(1.0, 0.0), snow=0.7, mist=0.25, sky_amp=0.6)
PLUME_CHECKPOINTS = 6
LIVING_KEYS = set(LIVING_DEFAULT) | {"person_mask"}


class BuildShotError(ValueError):
    """The spec or its inputs are wrong; nothing was rendered."""


def load_spec(path) -> dict:
    p = Path(path).resolve()
    try:
        spec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildShotError(f"cannot read spec {p}: {exc}") from exc
    spec["_dir"] = str(p.parent)
    return spec


def validate_spec(spec: dict) -> list[str]:
    problems: list[str] = []
    if spec.get("kind", "photo") not in ("photo", "map"):
        problems.append("kind must be 'photo' or 'map'")
    if spec.get("kind", "photo") == "map":
        from explainer_engine.production import build_map_shot
        try:
            build_map_shot.check_spec(spec)
        except ValueError as exc:
            problems.append(str(exc))
        return problems
    for key in ("id", "photo", "film_file", "seconds", "camera"):
        if key not in spec:
            problems.append(f"missing {key!r}")
    if not isinstance(spec.get("seconds", 1), (int, float)) or spec.get("seconds", 1) <= 0:
        problems.append("seconds must be a positive number")
    if "camera" in spec:
        try:
            LV.check_camera(spec["camera"])
        except ValueError as exc:
            problems.append(str(exc))
    bad = set(spec.get("living", {})) - LIVING_KEYS
    if bad:
        problems.append(f"unknown living keys: {sorted(bad)}")
    dr = spec.get("depth_range", {})
    if dr and not (0 < dr.get("near_m", DEFAULT_NEAR_M) < dr.get("far_m", DEFAULT_FAR_M)):
        problems.append("depth_range needs 0 < near_m < far_m")
    return problems


def _resolve(spec: dict, key: str) -> Path:
    p = Path(spec[key])
    return p if p.is_absolute() else Path(spec["_dir"]) / p


def film_finish(film_path: Path) -> dict:
    """The episode film's finish block and font, through its map style preset (the one look, creator 2026-11-20)."""
    film = episode_film.load_episode_film(str(film_path))
    name = episode_film.block(film, "map").get("style_preset")
    if not name:
        raise BuildShotError("the episode film has no map.style_preset: it names the look of the episode")
    preset_file = STYLES / f"{name}.json"
    if not preset_file.exists():
        raise BuildShotError(f"style preset {name!r} not found in {STYLES}")
    preset = json.loads(preset_file.read_text(encoding="utf-8"))
    if preset.get("draft") or not str(preset.get("font", "")).strip():
        raise BuildShotError(f"style preset {name!r} is a draft or has no font: a person finishes it first")
    for k in ("tint", "grain", "vignette"):
        if k not in preset.get("finish", {}):
            raise BuildShotError(f"style preset {name!r} finish has no {k!r}")
    return dict(film_id=episode_film.film_id(film), preset=name, font=preset["font"], finish=preset["finish"])


def inventory(living: dict) -> dict:
    inv = {k: (list(v) if isinstance(v, list) else v) for k, v in LIVING_DEFAULT.items()}
    for k, v in living.items():
        if k != "person_mask":
            inv[k] = tuple(v) if k in ("wind",) else v
    for p in inv["fires"]:
        p["box"] = tuple(p["box"]); p["src"] = tuple(p["src"])
    for p in inv["smoke"]:
        p["src"] = tuple(p["src"])
    inv["persons"] = [[tuple(pt) for pt in poly] for poly in inv["persons"]]
    return inv


# ---- the episode film's finish, as page.html applies it to a map: tint (multiply), grain (overlay, new pattern every frame), vignette
def _hex_bgr(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32) / 255.0


def apply_finish(img: np.ndarray, finish: dict, frame_no: int, vig_map: np.ndarray | None = None) -> np.ndarray:
    import cv2

    out = img
    t = finish["tint"]
    if t["opacity"] > 0:
        out = out * (1 - t["opacity"]) + out * _hex_bgr(t["color"]) * t["opacity"]
    g = finish["grain"]
    if g["opacity"] > 0:
        rs = np.random.RandomState(frame_no + 1)
        n = cv2.GaussianBlur(rs.normal(0.5, 0.22, img.shape[:2]).astype(np.float32), (0, 0), 0.8)[..., None]
        ov = np.where(out < 0.5, 2 * out * n, 1 - 2 * (1 - out) * (1 - n))
        out = out * (1 - g["opacity"]) + ov * g["opacity"]
    if float(finish["vignette"]) > 0 and vig_map is not None:
        out = out * (1 - float(finish["vignette"]) * vig_map[..., None])
    return np.clip(out, 0, 1).astype(np.float32)


def vignette_map(h: int, w: int) -> np.ndarray:
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    return np.clip((r - 0.45) / 0.55, 0, 1) ** 2


def font_file(font_stack: str) -> str:
    """The first family of the preset's CSS font stack that this machine has (fc-match); the render log names it."""
    for fam in [f.strip().strip("'\"") for f in font_stack.split(",")]:
        try:
            r = subprocess.run(["fc-match", fam, "--format=%{family}|%{file}"], capture_output=True, text=True, timeout=10)
            got_fam, _, path = r.stdout.partition("|")
            if path and fam.lower() in got_fam.lower():
                return path
        except (OSError, subprocess.SubprocessError):
            break
    raise BuildShotError(f"none of the fonts {font_stack!r} is installed")


def draw_caption(img: np.ndarray, text: str, font_path: str) -> np.ndarray:
    from PIL import Image, ImageDraw, ImageFont

    h, w = img.shape[:2]
    pil = Image.fromarray((img[..., ::-1] * 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    f = ImageFont.truetype(font_path, int(h * 0.05))
    tw = d.textlength(text, font=f)
    x, y = (w - tw) / 2, h * 0.88
    d.text((x + 2, y + 2), text, font=f, fill=(0, 0, 0))
    d.text((x, y), text, font=f, fill=(245, 242, 235))
    return np.asarray(pil, dtype=np.float32)[..., ::-1] / 255.0


def build_photo_shot(spec: dict, out_mp4: str, cache_dir: str | Path = "jobs/_depth_cache", workdir: str | Path | None = None) -> dict[str, Any]:
    problems = validate_spec(spec)
    if problems:
        raise BuildShotError("; ".join(problems))
    photo = _resolve(spec, "photo")
    if not photo.exists():
        raise BuildShotError(f"photo not found: {photo}")
    fin = film_finish(_resolve(spec, "film_file"))
    dr = spec.get("depth_range", {})
    near, far = dr.get("near_m", DEFAULT_NEAR_M), dr.get("far_m", DEFAULT_FAR_M)
    depth_npy = ensure_depth(photo, cache_dir, near, far)
    living = spec.get("living", {})
    pmask = living.get("person_mask")
    pmask = str(_resolve({"p": pmask, "_dir": spec["_dir"]}, "p")) if pmask else None
    shot = LV.Shot(spec["id"], float(spec["seconds"]), False, True, pic=str(photo), depth=str(depth_npy), inventory=inventory(living),
                   person_mask=pmask, camera=spec["camera"])
    cap = spec.get("caption")
    cap_font = font_file(fin["font"]) if cap else None
    out = Path(out_mp4)
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{LV.W}x{LV.H}", "-r", str(LV.FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    vig = vignette_map(LV.H, LV.W)
    marks = {int(round(i * (shot.n - 1) / (PLUME_CHECKPOINTS - 1))) for i in range(PLUME_CHECKPOINTS)}
    plume_checks: list[dict] = []
    has_plume = any(s.get("avoid") for s in shot.inv["smoke"])
    for f in range(shot.n):
        frame = shot.render(f).astype(np.float32) / 255.0      # living.render gives BGR uint8
        if has_plume and f in marks:
            from explainer_engine.qa import plume_zones as PZ
            t = f / LV.FPS
            a = shot.parallax(shot.plume_a, t)
            pm = shot.parallax(shot.pmask_f, t) > 0.5
            r = PZ.plume_in_person_share(a, pm)
            plume_checks.append(dict(frame=f, status=r["status"], person_share=r["value"]))
        frame = apply_finish(frame, fin["finish"], f, vig)
        if cap and cap["t0"] <= f / LV.FPS < cap["t1"]:
            frame = draw_caption(frame, cap["text"], cap_font)
        enc.stdin.write((np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        raise BuildShotError("ffmpeg failed")
    log = dict(id=spec["id"], kind="photo", photo=str(photo), out=str(out), seconds=shot.secs, frames=shot.n, fps=LV.FPS, size=[LV.W, LV.H],
               camera=shot.camera, film_id=fin["film_id"], style_preset=fin["preset"], font=fin["font"], font_file=cap_font,
               depth=dict(file=str(depth_npy), model="depth-anything-v2-small", near_m=near, far_m=far, metric="ASSUMED (relative model, fixed near/far range)"),
               edge=shot.edge, plume_checks=plume_checks, effects=sorted(k for k in ("fires", "smoke", "sway_trees", "sway_cloth", "candles") if shot.inv[k]) + ["snow", "mist", "sky"])
    bad = [c for c in plume_checks if c["status"] != "PASS"]
    log["plume_ok"] = not bad
    (out.with_suffix(".render_log.json")).write_text(json.dumps(log, indent=1), encoding="utf-8")
    if bad:
        raise BuildShotError(f"smoke plume check failed or not run at {len(bad)} checkpoints (see {out.with_suffix('.render_log.json')})")
    return log


def build_shot(spec_path, out_mp4, cache_dir="jobs/_depth_cache", workdir=None, tile_dir=None) -> dict[str, Any]:
    spec = load_spec(spec_path)
    if spec.get("kind", "photo") == "map":
        from explainer_engine.production import build_map_shot
        return build_map_shot.build(spec_path, out_mp4, workdir, tile_dir)
    return build_photo_shot(spec, out_mp4, cache_dir, workdir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.build_shot")
    ap.add_argument("spec"); ap.add_argument("out"); ap.add_argument("--cache-dir", default="jobs/_depth_cache"); ap.add_argument("--workdir"); ap.add_argument("--tile-dir")
    a = ap.parse_args(argv)
    try:
        log = build_shot(a.spec, a.out, a.cache_dir, a.workdir, a.tile_dir)
    except ValueError as exc:
        print(f"build_shot: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: log[k] for k in ("id", "kind", "out") if k in log}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
