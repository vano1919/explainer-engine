"""Encode one map shot as a clip (moved out of ``maps/render.py`` by v4.3 P0.4, 2026-11-12: CMP-14 keeps the map renderers
free of subprocess and clients; the frames come from ``maps.render.render_frame``, FFmpeg encodes them here). P4 reworks it."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic
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


def _resolve_spine(shot: dict, spine, out_path: Path):
    if spine is not None:
        return spine
    if shot.get("spine") or shot.get("word_spine"):
        return shot.get("spine") or shot.get("word_spine")
    sid = str(shot.get("shot_id") or "")
    if not sid:
        return None
    for parent in (out_path.parent, *out_path.parents):
        sp_file = parent / "production" / "spines" / f"{sid}.json"
        if sp_file.is_file():
            doc = json.loads(sp_file.read_text(encoding="utf-8"))
            return doc.get("words") or doc.get("spine") if isinstance(doc, dict) else doc
        tm_file = parent / "audio" / "timing.json"
        if tm_file.is_file():
            from explainer_engine.episode import timing as ET
            doc = ET.load_clock(tm_file)
            sp = (doc.get("spines") or {}).get(sid)
            if sp:
                return [{"word": w["word"], "start_frame": w["start_frame"]} for w in sp]
    return None


def _resolve_prev_end_view(shot: dict, prev_end_view, script: dict | None = None, cache_dir: Path | None = None):
    cand = prev_end_view if prev_end_view is not None else shot.get("prev_end_view")
    if cand is False or shot.get("inherit_camera") is False:
        return None
    if isinstance(cand, (str, Path)):
        p = Path(cand)
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    if isinstance(cand, dict) and {"lon", "lat", "span_km"} <= set(cand):
        return {"lon": float(cand["lon"]), "lat": float(cand["lat"]), "span_km": float(cand["span_km"])}
    if script is not None and cache_dir is not None:
        sid = shot.get("shot_id")
        shots = script.get("shots") or []
        for idx, s in enumerate(shots):
            if s.get("shot_id") == sid and idx > 0:
                prev_s = shots[idx - 1]
                is_prev_map = (
                    prev_s.get("route") == "map_action"
                    or prev_s.get("visual_type") == "map_visualization"
                    or prev_s.get("generation_mode") in ("TACTILE_MAP", "MAP_25D")
                )
                loc_a = prev_s.get("location_id") or prev_s.get("place")
                loc_b = shot.get("location_id") or shot.get("place")
                same_loc = (loc_a == loc_b) if (loc_a is not None or loc_b is not None) else True
                if is_prev_map and same_loc:
                    prev_sid = prev_s.get("shot_id")
                    ev_file = Path(cache_dir) / f"{prev_sid}_end_view.json"
                    if ev_file.is_file():
                        doc = json.loads(ev_file.read_text(encoding="utf-8"))
                        if isinstance(doc, dict) and {"lon", "lat", "span_km"} <= set(doc):
                            return {"lon": float(doc["lon"]), "lat": float(doc["lat"]), "span_km": float(doc["span_km"])}
                break
    return None


def render_action_map_clip(
    shot: dict,
    script: dict,
    episode: dict,
    out_mp4_path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    spine=None,
    keyframes_out_dir=None,
    cache_dir=None,
    prev_end_view: dict | str | Path | None = None,
) -> dict:
    """A ``map_action`` shot (v4.3 P4): the real-relief plate in the episode's map look, the action layer on its words.

    ``episode`` is the episode.json document (``places``, ``map_look``, ``historical_period``). Persists
    ``<cache>/<shot_id>_end_view.json`` (``lon``, ``lat``, ``span_km`` at the last frame) and chains from ``prev_end_view``
    when provided (M3, M4, M7)."""
    import hashlib
    import subprocess
    from explainer_engine.maps import actions as MA

    out = Path(out_mp4_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cdir = Path(cache_dir) if cache_dir is not None else out.parent
    cdir.mkdir(parents=True, exist_ok=True)

    from explainer_engine.maps import plate
    scene_obj = next(
        (sc for sc in (script.get("scenes") or []) if isinstance(sc, dict) and sc.get("scene_id") == shot.get("scene_id")),
        shot.get("scene") if isinstance(shot.get("scene"), dict) else None,
    )
    look = plate.resolve_scene_map_look(episode.get("map_look"), scene=scene_obj, shot=shot)
    period = episode.get("historical_period") or episode.get("period") or script.get("historical_period")
    if period is not None:
        look.setdefault("period", period)

    resolved_spine = _resolve_spine(shot, spine, out)
    resolved_prev = _resolve_prev_end_view(shot, prev_end_view, script=script, cache_dir=cdir)
    shot_for_plan = dict(shot)
    if period is not None and "period" not in shot_for_plan:
        shot_for_plan["period"] = period

    p = MA.plan(shot_for_plan, script, episode.get("places") or {}, fps, resolved_spine, prev_end_view=resolved_prev)
    base = MA.card_base(width, height, look) if p["card"] else MA.Plate(p, width, height, look)
    tmp = out.with_name(out.stem + ".part.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
                             "-r", str(fps), "-i", "-", "-frames:v", str(p["frames"]), "-c:v", "libx264", "-preset", "medium",
                             "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    from explainer_engine.standards import sourced_rules as SR
    size = tuple(SR.T("BP-164", "analysis_size"))
    still_diff = float(SR.T("BP-164", "frozen_diff_max"))
    max_static_s = float(SR.T("BP-147", "static_flag_s"))
    still_max = int(round(max_static_s * fps))
    first = last = prev = None
    run = longest = 0
    for f in range(p["frames"]):
        im = MA.render_frame(p, f, base, width, height, look)
        if f == 0:
            first = im
        last = im
        small = np.asarray(im.convert("L").resize(size), dtype=np.float32)
        if prev is not None and float(np.abs(small - prev).mean()) < still_diff:
            run += 1
            longest = max(longest, run + 1)
        else:
            run = 0
        prev = small
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
    end_view = None
    end_view_path = None
    if not p["card"]:
        raster_km = 111.32 / 60.0       # Natural Earth SR_HR: 1/60 degree a pixel at the equator
        upsample = round(max(base.upsample(MA.camera(p, f), raster_km) for f in range(p["frames"])), 2)
        ev = MA.camera(p, p["frames"] - 1)
        end_view = {"lon": float(ev["lon"]), "lat": float(ev["lat"]), "span_km": float(ev["span_km"])}
        end_view_path = cdir / f"{p['shot_id']}_end_view.json"
        write_json_atomic(end_view_path, end_view)
        if out.parent != cdir:
            write_json_atomic(out.parent / f"{p['shot_id']}_end_view.json", end_view)
    from explainer_engine.qa import gates as G
    first_action = min((a["start"] for a in p["actions"]), default=None)
    rows = [G.row("map_has_actions", bool(p["actions"]), f"{len(p['actions'])} action(s) on their words (RT-03)",
                  len(p["actions"])),
            G.row("map_not_standing_still", longest <= still_max,
                  f"longest still stretch {longest} frames ({longest / max(1, fps):.2f} s; CMP-08 / BP-147 max_static_s: "
                  f"{max_static_s:g} s = {still_max} frames); the first action starts at frame {first_action}",
                  longest, level=SR.level("BP-147")),
            G.row("map_routes_follow_the_land", not p["path_findings"], f"{len(p['path_findings'])} route finding(s) of map "
                  "law 2 on the via-waypoint splines (maps/paths.validate, CMP-02)",
                  [x["detail"] for x in p["path_findings"]][:5], level=G.REVIEW)]
    return {"status": "generated", "provider": "python_action_map", "cost_usd": 0.0, "shot_id": p["shot_id"],
            "gates": G.verdict(rows), "relief_upsample_max": upsample,
            "scene_grade_profile": look.get("scene_grade_profile"),
            "keyframe_timeline": p.get("keyframe_timeline", []),
            "card": p["card"], "word_basis": p["basis"], "spine_basis": p["spine_basis"],
            "end_view": end_view, "end_view_path": str(end_view_path) if end_view_path else None,
            "actions": [{k: a[k] for k in ("kind", "word", "start", "end", "event_id")} | {"decision": a["audio"]["decision"], "keyframe_frames": a.get("keyframe_frames"), "keyframe_seconds": a.get("keyframe_seconds")}
                        for a in p["actions"]],
            "longest_still_frames": longest, "dense": p["dense"],
            "total_frames": p["frames"], "fps": fps, "resolution": [width, height], "path": str(out),
            "start_keyframe_path": keys.get("start"), "end_keyframe_path": keys.get("end"),
            "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
