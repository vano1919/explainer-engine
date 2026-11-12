"""Encode one map shot as a clip (moved out of ``maps/render.py`` by v4.3 P0.4, 2026-11-12: CMP-14 keeps the map renderers
free of subprocess and clients; the frames come from ``maps.render.render_frame``, FFmpeg encodes them here). P4 reworks it."""
from __future__ import annotations

import numpy as np

from explainer_engine.maps import geo, plate
from explainer_engine.maps.render import build_episode_gis_map_spec, render_frame


def render_episode_gis_map_clip(
    shot: dict,
    out_mp4_path,
    cache_dir,
    keyframes_out_dir=None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> dict:
    """Render a 24fps 1080p GIS + DEM Shaded-Relief map clip for a map shot (`S01_SH008`, `S02_SH001`, `S02_SH010`)
    using `maps/geo.py`, `maps/plate.py`, `maps/render.py`, `maps/camera.py`, and `maps/timeline.py`."""
    import hashlib
    import subprocess
    from pathlib import Path
    from explainer_engine.maps import timeline as TL

    out_mp4_path = Path(out_mp4_path)
    out_mp4_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    sid = str(shot.get("shot_id") or "S01_SH008")
    dur_s = float(shot.get("target_duration_seconds", 4.0))
    total_frames = max(fps, int(round(dur_s * fps)))

    # Pre-render and cache a high-resolution letterless DEM shaded-relief master plate for the theatre region
    temp_spec, _ = build_episode_gis_map_spec(shot, width=width, height=height, total_frames=total_frames)
    cam_start = temp_spec["payload"]["camera"]["start"]
    plate_view_obj = geo.View(cam_start["lon"], cam_start["lat"], cam_start["span_km"] * 1.35, width, height)
    cached_plate_path = plate.save_plate(plate_view_obj, cache_dir, shaded_relief=True)

    spec, spine = build_episode_gis_map_spec(
        shot,
        width=width,
        height=height,
        total_frames=total_frames,
        plate_ref=cached_plate_path.name,
        plate_view={"lon": plate_view_obj.lon, "lat": plate_view_obj.lat, "span_km": plate_view_obj.span_km},
    )
    tl, clock = TL.build(spec, spine, trigger_word_index=0, duration_frames=total_frames)

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-b:v", "5500k", "-maxrate", "7500k", "-bufsize", "11000k",
            "-pix_fmt", "yuv420p",
            str(out_mp4_path),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None

    first_img = None
    last_img = None
    for f_idx in range(total_frames):
        # Use ss=1 for fast streaming over the high-res cached DEM plate
        im = render_frame(spec, tl, clock, f_idx, ss=1, base_dir=cache_dir)
        if f_idx == 0:
            first_img = im
        if f_idx == total_frames - 1:
            last_img = im
        proc.stdin.write(np.asarray(im, dtype=np.uint8).tobytes())

    proc.stdin.close()
    proc.wait(timeout=90)

    start_png_path = None
    end_png_path = None
    if keyframes_out_dir is not None and first_img is not None and last_img is not None:
        kdir = Path(keyframes_out_dir)
        kdir.mkdir(parents=True, exist_ok=True)
        start_png_path = kdir / f"{sid}_gis_start.png"
        end_png_path = kdir / f"{sid}_gis_end.png"
        first_img.save(start_png_path)
        last_img.save(end_png_path)

    return {
        "status": "generated",
        "provider": "gis_shaded_relief_map_engine",
        "cost_usd": 0.0,
        "shot_id": sid,
        "cached_plate_path": str(cached_plate_path),
        "cached_plate_spec_hash": plate.spec_hash(plate_view_obj, shaded_relief=True),
        "start_keyframe_path": str(start_png_path) if start_png_path else None,
        "end_keyframe_path": str(end_png_path) if end_png_path else None,
        "duration_sec": dur_s,
        "fps": fps,
        "resolution": [width, height],
        "total_frames": total_frames,
        "path": str(out_mp4_path),
        "bytes": out_mp4_path.stat().st_size if out_mp4_path.exists() else 0,
        "output_sha256": hashlib.sha256(out_mp4_path.read_bytes()).hexdigest() if out_mp4_path.exists() else "",
    }


def render_action_map_clip(shot: dict, script: dict, episode: dict, out_mp4_path, width: int = 1920, height: int = 1080,
                           fps: int = 24, spine=None, keyframes_out_dir=None) -> dict:
    """A ``map_action`` shot (v4.3 P4): the real-relief plate in the episode's map look, the action layer on its words.

    ``episode`` is the episode.json document (``places``, ``map_look``). Frames are a pure function of the plan and the frame
    number (``maps/actions.py``); FFmpeg encodes them here (CMP-14 keeps the renderers free of subprocess)."""
    import hashlib
    import subprocess
    from pathlib import Path
    from explainer_engine.maps import actions as MA

    out = Path(out_mp4_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    look = episode.get("map_look") or {}
    p = MA.plan(shot, script, episode.get("places") or {}, fps, spine)
    base = MA.card_base(width, height, look) if p["card"] else MA.Plate(p, width, height, look)
    tmp = out.with_name(out.stem + ".part.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
                             "-r", str(fps), "-i", "-", "-frames:v", str(p["frames"]), "-c:v", "libx264", "-preset", "medium",
                             "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    first = last = None
    for f in range(p["frames"]):
        im = MA.render_frame(p, f, base, width, height, look)
        if f == 0:
            first = im
        last = im
        proc.stdin.write(np.asarray(im, dtype=np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait(timeout=600) != 0:
        raise RuntimeError(f"ffmpeg failed on {shot.get('shot_id')}")
    tmp.replace(out)
    keys = {}
    if keyframes_out_dir is not None:
        kd = Path(keyframes_out_dir)
        kd.mkdir(parents=True, exist_ok=True)
        for name, im in (("start", first), ("end", last)):
            keys[name] = str(kd / f"{p['shot_id']}_map_{name}.png")
            im.save(keys[name])
    upsample = None
    if not p["card"]:
        raster_km = 111.32 / 60.0       # Natural Earth SR_HR: 1/60 degree a pixel at the equator
        upsample = round(max(base.upsample(MA.camera(p, f), raster_km) for f in range(p["frames"])), 2)
    return {"status": "generated", "provider": "python_action_map", "cost_usd": 0.0, "shot_id": p["shot_id"],
            "relief_upsample_max": upsample,
            "card": p["card"], "word_basis": p["basis"], "actions": [{k: a[k] for k in ("kind", "word", "start", "end")} for a in p["actions"]],
            "total_frames": p["frames"], "fps": fps, "resolution": [width, height], "path": str(out),
            "start_keyframe_path": keys.get("start"), "end_keyframe_path": keys.get("end"),
            "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
