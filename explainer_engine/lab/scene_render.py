"""Render a blender_scene/1 spec: 241-frame grey layout video, one PNG per view, plan.png and report.json (free, CPU).

Run from the repo root (it starts Blender itself when ``bpy`` is not importable)::

    python -m explainer_engine.lab.scene_render <spec.json> <out_dir> [--samples 8] [--frames A:B] [--blender PATH]

``--frames A:B`` renders only that frame range into ``<out_dir>/frames`` (frames that already exist are skipped), so a
long render can run in chunks and resume; without it the whole clip is rendered and then assembled. Exit codes:
0 PASS, 1 REVIEW (hypothesis thresholds ask for a look), 2 FAIL (a hard limit broke).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT_STR = str(Path(__file__).resolve().parents[2])
if REPO_ROOT_STR not in sys.path:          # Blender's own Python does not see the repo otherwise
    sys.path.insert(0, REPO_ROOT_STR)

from explainer_engine.lab import scene_spec as ss  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PSNR_MIN_DB = 30.0       # V7: the view PNG and the same frame decoded from the mp4 must be the same picture


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_file(out_dir: Path, n: int) -> Path:
    return out_dir / "frames" / f"f_{n:04d}.png"


# ------------------------------------------------------------------------------------------------ inside Blender

def render_frames(spec: dict, out_dir: Path, samples: int, a: int, b: int) -> dict:
    """Runs where ``bpy`` exists: build the scene, check the projection against Blender, render frames a..b."""
    from explainer_engine.lab import blender_lib as bl  # noqa: PLC0415
    bpy = bl.bb._bpy()
    sc = bl.build_scene(spec, samples)
    gap = bl.blender_projection_check(spec, sorted({c["frame_in"] for c in spec["cuts"]} | {spec["clip_frames"] - 1}))
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out_dir / "frames" / "f_")
    sc.render.use_overwrite = False
    sc.frame_start, sc.frame_end = a, b
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    if a == 0 and b == spec["clip_frames"] - 1:
        bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "layout.blend"))
    return {"blender": bpy.app.version_string, "samples": samples, "projection_gap_px": round(gap, 3), "range": [a, b],
            "render_seconds": round(time.time() - t0, 1)}


def _inner_main(argv: list[str]) -> int:
    spec_path, out, samples, a, b = argv
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))   # validated by the caller (Blender has no jsonschema)
    out_dir = Path(out)
    info = render_frames(spec, out_dir, int(samples), int(a), int(b))
    (out_dir / f"inner_{a}_{b}.json").write_text(json.dumps(info), encoding="utf-8")
    return 0


# ------------------------------------------------------------------------------------------------ outside

def _blender_bin(explicit: str | None) -> str:
    for cand in (explicit, os.environ.get("BLENDER"), shutil.which("blender"), "/tmp/bl/b/blender"):
        if cand and Path(cand).exists() or (cand and shutil.which(cand)):
            return cand
    raise FileNotFoundError("Blender not found: pass --blender PATH or set BLENDER")


def run_blender(spec_path: Path, out_dir: Path, samples: int, a: int, b: int, blender: str | None) -> dict:
    exe = _blender_bin(blender)
    env = dict(os.environ, PYTHONPATH=f"{REPO_ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    cmd = [exe, "--background", "--factory-startup", "--python", str(Path(__file__).resolve()), "--",
           "--inner", str(spec_path), str(out_dir), str(samples), str(a), str(b)]
    subprocess.run(cmd, check=True, env=env)
    if not (out_dir / f"inner_{a}_{b}.json").exists():       # Blender exits 0 even when the script raised
        raise RuntimeError("Blender finished without writing its result: see its output above")
    return json.loads((out_dir / f"inner_{a}_{b}.json").read_text(encoding="utf-8"))


def encode(out_dir: Path, fps: int, video: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                    str(out_dir / "frames" / "f_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "14",
                    "-preset", "medium", "-movflags", "+faststart", str(video)], check=True)


def probe_frames(video: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames,width,height,r_frame_rate", "-of", "json", str(video)],
                         check=True, capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"frames": int(s["nb_read_frames"]), "width": s["width"], "height": s["height"],
            "fps": int(num) / int(den)}


def psnr(a: Path, b: Path) -> float:
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    x = np.asarray(Image.open(a).convert("RGB"), dtype="float64")
    y = np.asarray(Image.open(b).convert("RGB"), dtype="float64")
    if x.shape != y.shape:
        return 0.0
    mse = float(((x - y) ** 2).mean())
    return 99.0 if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def view_pngs(spec: dict, out_dir: Path, video: Path) -> tuple[list[dict], dict]:
    """One PNG per view = the view's first frame; V7 compares it with the same frame decoded from the video."""
    views, bad = [], []
    (out_dir / "views").mkdir(exist_ok=True)
    for i, cut in enumerate(spec["cuts"], 1):
        src = frame_file(out_dir, cut["frame_in"])
        dst = out_dir / "views" / f"view{i}_{cut['camera']}.png"
        shutil.copyfile(src, dst)
        dec = out_dir / "views" / f".decoded{i}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf",
                        f"select=eq(n\\,{cut['frame_in']})", "-vframes", "1", str(dec)], check=True)
        db = psnr(dst, dec)
        dec.unlink()
        if sha256(dst) != sha256(src) or db < PSNR_MIN_DB:
            bad.append(f"view{i} frame {cut['frame_in']}: psnr {db:.1f} dB")
        views.append({"view": i, "camera": cut["camera"], "frame": cut["frame_in"],
                      "seconds": round((cut["frame_out"] - cut["frame_in"]) / spec["fps"], 3),
                      "png": str(dst.relative_to(out_dir)), "sha256": sha256(dst), "psnr_db_vs_video": round(db, 1)})
    res = ss._res("V7", "FAIL", f"view PNG differs from the video frame: {bad}") if bad else \
        ss._res("V7", "PASS", f"{len(views)} view PNGs are the video's frames (psnr >= {PSNR_MIN_DB} dB)")
    return views, res


def plan_png(spec: dict, path: Path, size=(1100, 1100)) -> Path:
    """Top-down plan of the whole clip: tracks (start filled, end ring), every camera with its view wedge."""
    from PIL import Image, ImageDraw  # noqa: PLC0415
    pts = [c["pos"][:2] for c in spec["cameras"]]
    for p in spec["people"]:
        pts += [k["pos"] for k in p["track"]]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    pad = 3.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    scale = min((size[0] - 120) / (x1 - x0), (size[1] - 100) / (y1 - y0))

    def px(x, y):
        return 60 + (x - x0) * scale, size[1] - 50 - (y - y0) * scale
    img = Image.new("RGB", size, (245, 245, 242))
    d = ImageDraw.Draw(img)
    palette = [(40, 40, 160), (160, 60, 120), (30, 130, 90), (170, 110, 20), (90, 60, 160)]
    for i, cut in enumerate(spec["cuts"]):
        cam = ss.camera_by_id(spec, cut["camera"])
        col = palette[i % len(palette)]
        cx, cy = cam["pos"][:2]
        half = math.degrees(math.atan(ss.SENSOR_WIDTH_MM / 2 / cam["lens"]))
        for sgn in (-1, 1):
            hx = math.sin(math.radians(cam["heading"] + sgn * half))
            hy = math.cos(math.radians(cam["heading"] + sgn * half))
            d.line([px(cx, cy), px(cx + hx * 8, cy + hy * 8)], fill=col, width=1)
        bx, by = px(cx, cy)
        d.ellipse([bx - 7, by - 7, bx + 7, by + 7], fill=col)
        t0, t1 = cut["frame_in"] / spec["fps"], cut["frame_out"] / spec["fps"]
        d.text((bx + 11, by - 6), f"{i + 1}: {cam['id']} {cam['lens']} mm  {t0:.1f}-{t1:.1f} s", fill=col)
    for p in spec["people"]:
        colour = (190, 150, 60) if p["side"] == "british" else (70, 110, 150)
        keys = sorted(p["track"], key=lambda k: k["frame"])
        d.line([px(*k["pos"]) for k in keys], fill=colour, width=3)
        sx, sy = px(*keys[0]["pos"])
        ex, ey = px(*keys[-1]["pos"])
        d.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=colour)
        d.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], outline=colour, width=3)
        d.text((sx + 12, sy - 6), f"{p['id']} start", fill=(60, 60, 60))
        d.text((ex + 12, ey - 6), f"{p['id']} end", fill=(60, 60, 60))
    d.text((20, 14), f"{spec['scene_id']} plan (top-down, y up the page): filled = start, ring = end, "
                     f"coloured wedges = the five cameras", fill=(30, 30, 30))
    img.save(path)
    return path


def build_report(spec: dict, spec_path: Path, out_dir: Path, inner: list[dict], seconds: float) -> dict:
    video = out_dir / "layout.mp4"
    results = ss.validate_spec(spec)
    probe = probe_frames(video)
    issues = []
    if probe["frames"] != spec["clip_frames"]:
        issues.append(f"video has {probe['frames']} frames, spec says {spec['clip_frames']}")
    if (probe["width"], probe["height"]) != tuple(spec["size"]):
        issues.append(f"video is {probe['width']}x{probe['height']}")
    if probe["fps"] != spec["fps"]:
        issues.append(f"video fps {probe['fps']}")
    results = [r for r in results if r["id"] != "V6"] + [
        ss._res("V6", "FAIL", "; ".join(issues)) if issues else
        ss._res("V6", "PASS", f"video: {probe['frames']} frames, {probe['width']}x{probe['height']}, {probe['fps']:g} fps "
                              f"(8k+1, size divisible by 64)")]
    views, v7 = view_pngs(spec, out_dir, video)
    results.append(v7)
    gap = max(i["projection_gap_px"] for i in inner)
    results.append(ss._res("PROJ", "FAIL" if gap > 1.5 else "PASS",
                           f"pure-Python projection vs Blender camera: worst gap {gap} px"))
    results.append(ss._res("V8", "PASS", "single clip: nothing to chain (checked by validate_chain on two clips)"))
    results.sort(key=lambda r: r["id"])
    measured = [{"camera": c["camera"], "frame_in": c["frame_in"], "frame_out": c["frame_out"], "focus": c["focus"],
                 "samples": ss.measure_cut(spec, c)} for c in spec["cuts"]]
    report = {
        "scene_id": spec["scene_id"], "spec_sha256": sha256(spec_path), "status": ss.summarize(results),
        "blender": inner[0]["blender"], "samples": inner[0]["samples"], "render_seconds": round(sum(i["render_seconds"] for i in inner), 1),
        "wall_seconds": round(seconds, 1), "video": {"file": "layout.mp4", "sha256": sha256(video), **probe,
                                                     "seconds": round(spec["clip_frames"] / spec["fps"], 3)},
        "views": views, "validators": results, "measured": measured,
        "thresholds": {"min_focus_height_frac": ss.MIN_FOCUS_HEIGHT_FRAC, "max_overlap": ss.MAX_OVERLAP,
                       "max_walk_speed": ss.MAX_WALK_SPEED, "view_s": [ss.VIEW_MIN_S, ss.VIEW_MAX_S]},
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--inner":
        return _inner_main(argv[1:])
    if len(argv) < 2:
        print(__doc__)
        return 3
    spec_path, out_dir = Path(argv[0]).resolve(), Path(argv[1]).resolve()
    samples, rng, blender = 8, None, None
    it = iter(argv[2:])
    for a in it:
        if a == "--samples":
            samples = int(next(it))
        elif a == "--frames":
            rng = tuple(int(v) for v in next(it).split(":"))
        elif a == "--blender":
            blender = next(it)
    spec = ss.load_spec(spec_path)
    pre = ss.validate_spec(spec)
    if ss.summarize(pre) == "FAIL":
        print(json.dumps(pre, indent=1))
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    last = spec["clip_frames"] - 1
    a, b = rng or (0, last)
    inner = run_blender(spec_path, out_dir, samples, a, b, blender)
    if rng and (a, b) != (0, last):
        print(json.dumps(inner))
        return 0
    inner_all = [json.loads(p.read_text()) for p in sorted(out_dir.glob("inner_*.json"))]
    missing = [n for n in range(last + 1) if not frame_file(out_dir, n).exists()]
    if missing:
        print(f"{len(missing)} frames still missing, e.g. {missing[:5]}")
        return 2
    encode(out_dir, spec["fps"], out_dir / "layout.mp4")
    plan_png(spec, out_dir / "plan.png")
    report = build_report(spec, spec_path, out_dir, inner_all, time.time() - t0)
    print(json.dumps({"status": report["status"], "validators": {r["id"]: r["status"] for r in report["validators"]}}))
    return {"PASS": 0, "REVIEW": 1, "FAIL": 2}[report["status"]]


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(main(args))
