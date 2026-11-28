"""Unified Cinema Film Pipeline — assembles full documentary films via ClaudeSimulator + ProductionStateMachine.

Drives every shot through:
- ``cinema_25d.render_cinema_25d_clip`` (Depth Anything V2 ONNX zero-tear continuous parallax)
- ``cinema_map.render_cinema_map_clip`` (Natural Earth NE1+SR shaded relief + synced SFX events)
- ``bridge_compiler`` (Liberation Serif auto-sized fade-in/out visual bridges)
- ``scene_soundscape.build_scene_locked_soundscape`` (per-shot environment ambience + CC0 SFX + pyloudnorm -14 LUFS)
- ``cinema_gates`` + ``identity_lock`` + ``ClaudeSimulator`` governance hooks
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from explainer_engine.audio.scene_soundscape import build_scene_locked_soundscape
from explainer_engine.core.execution_gateway import ProductionStateMachine
from explainer_engine.edit.trim import probe_duration_s, trim_clip_bp187
from explainer_engine.finish.cinema_grade import DEFAULT_CINEMA_GRADE, CinemaGradeSpec, grade_and_upscale_video_2k
from explainer_engine.maps.cinema_map import render_cinema_map_clip
from explainer_engine.orchestration.claude_simulator import ClaudeSimulator
from explainer_engine.overlay import bridge_compiler as BC
from explainer_engine.production.cinema_25d import render_cinema_25d_clip
from explainer_engine.qa import cinema_gates as CG
from explainer_engine.qa import identity_lock as IL


def _extract_wav_48k_stereo(src_mp4: Path, out_wav: Path) -> Path | None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(src_mp4),
            "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav),
        ],
        capture_output=True,
        check=False,
    )
    return out_wav if proc.returncode == 0 and out_wav.is_file() and out_wav.stat().st_size > 100 else None


def assemble_cinema_film(
    film_spec: dict[str, Any],
    work_dir: Path,
    out_mp4: Path,
    *,
    repo_root: Path,
    grade_spec: CinemaGradeSpec = DEFAULT_CINEMA_GRADE,
    reuse_cached_clips: bool = False,
) -> dict[str, Any]:
    """Render, assemble, sound-design, and QA a complete hybrid (LTX + 2.5D + Map) 2K documentary film."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    width = int(film_spec.get("width", 2560))
    height = int(film_spec.get("height", 1440))
    fps = int(film_spec.get("fps", 24))
    xfade_s = float(film_spec.get("xfade_s", 0.35))

    sim = ClaudeSimulator(repo_root)
    state_path = work_dir / "production_state.json"
    sm = ProductionStateMachine(state_path, episode_id=str(film_spec["episode_id"]))

    spec_file = work_dir / "film_spec.json"
    sim.check_write(spec_file)
    spec_file.write_text(json.dumps(film_spec, indent=2) + "\n", encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[spec_file])

    # 1. Render or conform every shot (ltx_video, 25d, or map) to exact (width, height, fps) under one 35mm cinema grade
    clip_paths: list[Path] = []
    clip_durations: list[float] = []
    shot_windows: list[dict[str, Any]] = []
    all_sfx_cues: list[dict[str, Any]] = []
    diegetic_tracks: list[dict[str, Any]] = []
    narration_tracks: list[dict[str, Any]] = list(film_spec.get("narration_tracks") or [])
    render_reports: list[dict[str, Any]] = []
    route_seconds: dict[str, float] = {"ltx_video": 0.0, "25d": 0.0, "map": 0.0}

    cursor_s = 0.0
    for idx, shot in enumerate(film_spec["shots"]):
        sid = str(shot["shot_id"])
        kind = str(shot["kind"])
        clip_p = work_dir / "clips" / f"{idx:02d}_{sid}.mp4"
        sim.check_write(clip_p)

        cached_ok = reuse_cached_clips and clip_p.is_file() and clip_p.stat().st_size > 10000
        if kind == "map":
            dur_s = float(shot["duration_s"])
            sfx_cache = clip_p.with_suffix(".sfx.json")
            if cached_ok:
                cached_evs: list[dict[str, Any]] = []
                if sfx_cache.is_file():
                    cached_evs = json.loads(sfx_cache.read_text(encoding="utf-8"))
                else:
                    # Fallback reconstruct from map_spec actions if sfx cache missing
                    cached_evs = [{"cue_id": f"{sid}_reveal", "sfx": "parchment_unfold", "offset_s": 0.15, "gain_db": -5.0}]
                    for a_i, act in enumerate(shot.get("map_spec", {}).get("actions") or []):
                        ak = act.get("kind", "")
                        t_s = float(act.get("start_s", 0.5))
                        if ak == "route_arrow":
                            cached_evs.append({"cue_id": f"{sid}_arrow_{a_i}", "sfx": "ink_arrow_sweep", "offset_s": t_s, "gain_db": -4.0})
                        elif ak == "pin":
                            cached_evs.append({"cue_id": f"{sid}_pin_{a_i}", "sfx": "camp_pin_stamp", "offset_s": t_s, "gain_db": -3.5})
                        elif ak == "pulse":
                            cached_evs.append({"cue_id": f"{sid}_pulse_{a_i}", "sfx": "troop_march_pulse", "offset_s": t_s, "gain_db": -5.0})
                rep: dict[str, Any] = {"status": "PASS", "cached": True, "duration_s": dur_s, "sfx_events": cached_evs}
            else:
                rep = render_cinema_map_clip(shot["map_spec"], clip_p, width=width, height=height, fps=fps, grade_spec=grade_spec)
                sfx_cache.write_text(json.dumps(rep["sfx_events"], indent=2) + "\n", encoding="utf-8")
            for ev in rep["sfx_events"]:
                all_sfx_cues.append(
                    {
                        "cue_id": ev["cue_id"],
                        "sfx": ev["sfx"],
                        "timestamp_s": round(cursor_s + float(ev["offset_s"]), 3),
                        "gain_db": float(ev.get("gain_db", -4.0)),
                    }
                )
        elif kind == "ltx_video":
            raw_ltx = Path(shot["ltx_clip_path"])
            trimmed_p = work_dir / "clips" / f"{idx:02d}_{sid}_trimmed.mp4"
            if cached_ok:
                dur_s = probe_duration_s(clip_p)
                rep = {"status": "PASS", "cached": True, "duration_s": round(dur_s, 3)}
            else:
                trim_rep = trim_clip_bp187(
                    raw_ltx,
                    trimmed_p,
                    has_dialogue=bool(shot.get("has_dialogue", True)),
                    tail_s=float(shot.get("bp187_tail_s", 0.42)),
                    min_duration_s=float(shot.get("min_duration_s", 2.2)),
                    max_duration_s=float(shot.get("duration_s", 5.5)),
                    start_offset_s=float(shot.get("start_offset_s", 0.0)),
                    fps=fps,
                )
                grade_rep = grade_and_upscale_video_2k(
                    trimmed_p,
                    clip_p,
                    width=width,
                    height=height,
                    fps=fps,
                    grain_strength=int(shot.get("grain_strength", 4)),
                )
                dur_s = probe_duration_s(clip_p)
                rep = {"status": "PASS", "trim": trim_rep, "grade_2k": grade_rep, "duration_s": round(dur_s, 3)}
            # Extract LTX native diegetic speech/foley audio for multi-track broadcast mix
            d_wav = _extract_wav_48k_stereo(clip_p, work_dir / "diegetic" / f"{idx:02d}_{sid}.wav")
            if d_wav is not None:
                diegetic_tracks.append(
                    {
                        "label": sid,
                        "wav_path": str(d_wav),
                        "start_s": round(cursor_s, 3),
                        "duration_s": round(dur_s, 3),
                        "gain_db": float(shot.get("diegetic_gain_db", 1.0 if shot.get("has_dialogue") else -2.5)),
                        "counts_as_speech": bool(shot.get("has_dialogue", False)),
                        "rehearsal_tts": False,
                    }
                )
        else:
            dur_s = float(shot["duration_s"])
            if cached_ok:
                rep = {"status": "PASS", "cached": True, "duration_s": dur_s}
            else:
                rep = render_cinema_25d_clip(
                    Path(shot["image_path"]),
                    clip_p,
                    duration_s=dur_s,
                    width=width,
                    height=height,
                    fps=fps,
                    camera_move=str(shot.get("camera_move", "push_left")),
                    parallax_strength=float(shot.get("parallax_strength", 0.030)),
                    zoom_delta=float(shot.get("zoom_delta", 0.075)),
                    atmosphere=str(shot.get("atmosphere", "dust")),
                    warm_flicker=bool(shot.get("warm_flicker", False)),
                    grade_spec=grade_spec,
                )

        # Optional per-shot narrator track binding
        if shot.get("narration_wav"):
            narration_tracks.append(
                {
                    "label": f"narr_{sid}",
                    "wav_path": str(shot["narration_wav"]),
                    "start_s": round(cursor_s + float(shot.get("narration_offset_s", 0.25)), 3),
                    "gain_db": float(shot.get("narration_gain_db", 2.0)),
                    "counts_as_speech": True,
                    "rehearsal_tts": True,
                }
            )

        route_seconds[kind] = round(route_seconds.get(kind, 0.0) + dur_s, 3)
        render_reports.append({"shot_id": sid, "kind": kind, **rep})
        clip_paths.append(clip_p)
        clip_durations.append(dur_s)

        start_t = cursor_s
        end_t = start_t + dur_s
        shot_windows.append(
            {
                "shot_id": sid,
                "kind": kind,
                "scene_environment": str(shot["scene_environment"]),
                "ambience_gain_db": float(shot.get("ambience_gain_db", -11.0)),
                "start_s": round(start_t, 3),
                "end_s": round(end_t, 3),
            }
        )
        if idx > 0 and bool(shot.get("transition_whoosh", kind == "map")):
            all_sfx_cues.append(
                {
                    "cue_id": f"transition_{idx:02d}",
                    "sfx": "cinematic_whoosh",
                    "timestamp_s": round(max(0.0, start_t - 0.12), 3),
                    "gain_db": -7.5,
                }
            )
        # Use clean hard cuts on LTX dialogue cuts (or subtle xfade on 2.5D/map transitions)
        seg_xfade = xfade_s if idx < len(film_spec["shots"]) - 1 else 0.0
        cursor_s = end_t - seg_xfade

    total_dur_s = round(cursor_s, 3)
    cut_times_s = [w["start_s"] for w in shot_windows[1:]]

    # 2. Stitch all video clips with smooth documentary cross-dissolves (xfade)
    def _stitch_batch(paths: list[Path], durs: list[float], dst: Path, *, preset: str = "veryfast") -> float:
        if len(paths) == 1:
            return durs[0]
        offset_end = sum(durs) - xfade_s * (len(paths) - 1)
        if reuse_cached_clips and dst.is_file() and dst.stat().st_size > 100000:
            return round(offset_end, 3)
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for cp in paths:
            cmd += ["-i", str(cp)]
        filters: list[str] = []
        for i in range(len(paths)):
            filters.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={fps},format=yuv420p[s{i}]")
        prev_lbl = "[s0]"
        offset = durs[0] - xfade_s
        for i in range(1, len(paths)):
            out_lbl = f"[v{i}]" if i < len(paths) - 1 else "[vout]"
            filters.append(f"{prev_lbl}[s{i}]xfade=transition=fade:duration={xfade_s:.3f}:offset={offset:.3f}{out_lbl}")
            prev_lbl = out_lbl
            offset += durs[i] - xfade_s
        tmp_dst = dst.with_name(dst.stem + ".part.mp4")
        cmd += [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            str(tmp_dst),
        ]
        subprocess.run(cmd, check=True)
        tmp_dst.replace(dst)
        return round(offset + xfade_s, 3)

    xfade_mp4 = work_dir / "stitched_xfade.mp4"
    sim.check_bash(f"ffmpeg xfade stitch -> {xfade_mp4.name}")
    has_bridges = bool(film_spec.get("bridges"))
    xfade_preset = "ultrafast" if has_bridges else "veryfast"
    if len(clip_paths) == 1:
        xfade_mp4 = clip_paths[0]
    elif len(clip_paths) <= 6:
        _stitch_batch(clip_paths, clip_durations, xfade_mp4, preset=xfade_preset)
    else:
        chunk_paths: list[Path] = []
        chunk_durs: list[float] = []
        chunk_size = 5
        for ci in range(0, len(clip_paths), chunk_size):
            sub_p = clip_paths[ci : ci + chunk_size]
            sub_d = clip_durations[ci : ci + chunk_size]
            if len(sub_p) == 1:
                chunk_paths.append(sub_p[0])
                chunk_durs.append(sub_d[0])
            else:
                ch_mp4 = work_dir / f"stitched_chunk_{ci // chunk_size:02d}.mp4"
                ch_dur = _stitch_batch(sub_p, sub_d, ch_mp4, preset="ultrafast")
                chunk_paths.append(ch_mp4)
                chunk_durs.append(ch_dur)
        _stitch_batch(chunk_paths, chunk_durs, xfade_mp4, preset=xfade_preset)

    # 3. Composite visual bridges (auto-sized Liberation Serif fade overlays)
    bridges = list(film_spec.get("bridges") or [])
    if bridges:
        ov_spec = BC.compile_bridges_to_overlay_spec(
            bridges,
            style_bible={"visual_bible": {"accent_hex": str(film_spec.get("accent_hex", "#A6382E")), "typography": "Liberation Serif"}},
            fps=fps,
            size=(width, height),
            episode_duration_s=total_dur_s,
        )
        bridged_mp4 = work_dir / "stitched_bridged.mp4"
        BC.composite_bridges_onto_video(xfade_mp4, ov_spec, bridged_mp4, work_dir=work_dir / "bridge_work")
    else:
        bridged_mp4 = xfade_mp4

    # 4. Build scene-locked 48kHz stereo soundscape (narrator + diegetic + ambience + SFX + ducking + -14 LUFS)
    audio_wav = work_dir / "master_48k_stereo.wav"
    audio_rep = build_scene_locked_soundscape(
        shot_windows,
        audio_wav,
        sfx_cues=all_sfx_cues,
        narration_tracks=narration_tracks,
        diegetic_tracks=diegetic_tracks,
        total_duration_s=total_dur_s,
        music_bed=film_spec.get("music_bed", "doc_strings_tense"),
        music_gain_db=float(film_spec.get("music_gain_db", -14.0)),
        duck_db=float(film_spec.get("duck_db", -11.5)),
        target_lufs=-14.0,
        true_peak_ceiling_db=-1.2,
        report_path=work_dir / "audio_timeline_report.json",
    )

    # 5. Mux final MP4 (48kHz 2-ch stereo AAC 256k + stream-copied video + faststart)
    sim.check_bash(f"ffmpeg mux final -> {out_mp4.name}")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(bridged_mp4), "-i", str(audio_wav),
            "-c:v", "copy", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "256k",
            "-movflags", "+faststart", "-shortest",
            str(out_mp4),
        ],
        check=True,
    )

    # 6. Automated L3 Cinema QA Gates
    static_qa = CG.check_no_static_shots(out_mp4, shot_windows)
    tear_qa = CG.check_no_midframe_tears(out_mp4)
    audio_qa = CG.check_audio_scene_consistency(audio_rep)
    color_qa = CG.check_cross_cut_color_parity(out_mp4, cut_times_s)
    delivery_qa = CG.check_master_delivery_specs(
        out_mp4, expected_width=width, expected_height=height, expected_fps=float(fps), audio_report=audio_rep
    )

    id_results: list[dict[str, Any]] = []
    for pair in film_spec.get("identity_pairs") or []:
        id_results.append(
            IL.check_cross_scene_identity(
                Path(pair["reference_image"]),
                Path(pair["candidate_image"]),
                character_id=str(pair["character_id"]),
                mandatory=True,
            )
        )

    all_qa_ok = (
        static_qa["status"] == "PASS"
        and tear_qa["status"] == "PASS"
        and audio_qa["status"] == "PASS"
        and color_qa["status"] == "PASS"
        and delivery_qa["status"] == "PASS"
        and all(r["status"] == "PASS" for r in id_results)
    )
    sim.check_stop(state_path, ["script"])
    sim.save_audit(work_dir / "claude_simulator_audit.json")

    sum_route = max(1e-6, sum(route_seconds.values()))
    route_mix = {k: round(v / sum_route, 3) for k, v in route_seconds.items()}

    summary = {
        "episode_id": film_spec["episode_id"],
        "output_mp4": str(out_mp4),
        "total_duration_s": total_dur_s,
        "resolution": [width, height],
        "fps": fps,
        "route_seconds": route_seconds,
        "route_mix": route_mix,
        "all_cinema_qa_passed": all_qa_ok,
        "delivery_forensics_qa": delivery_qa,
        "static_shot_qa": static_qa,
        "midframe_tear_qa": tear_qa,
        "audio_scene_qa": audio_qa,
        "color_parity_qa": color_qa,
        "identity_lock_qa": id_results,
        "audio_report": audio_rep,
        "render_reports": render_reports,
        "claude_simulator_hooks_checked": len(sim.audit_events),
    }
    (work_dir / "film_build_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _ascii_safe(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-").encode("ascii", "replace").decode("ascii")


def _sample_pil_frames(video_path: Path, times_s: list[float], thumb_size: tuple[int, int]) -> list[Image.Image | None]:
    """Single-pass sequential frame sampler avoiding slow H.264 random seeks on 2K video."""
    import cv2

    if not times_s:
        return []
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    idxs = [max(0, min(max(0, total - 1), int(round(t * fps)))) for t in times_s]
    wanted = set(idxs)
    max_idx = max(wanted) if wanted else 0
    decoded: dict[int, Image.Image] = {}
    cur = 0
    while cur <= max_idx:
        if not cap.grab():
            break
        if cur in wanted:
            ok, bgr = cap.retrieve()
            if ok and bgr is not None:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                decoded[cur] = Image.fromarray(rgb).resize(thumb_size, Image.Resampling.LANCZOS)
        cur += 1
    cap.release()
    return [decoded.get(i) for i in idxs]


def build_contact_sheet(
    video_path: Path,
    out_png: Path,
    *,
    num_frames: int = 24,
    cols: int = 4,
    banner: str = "",
) -> Path:
    """Extract evenly spaced temporal frames across a video into a labeled high-res Contact Sheet."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = total / max(1.0, fps)
    cap.release()

    times = [round(dur * (i + 0.5) / num_frames, 2) for i in range(num_frames)]
    ims = _sample_pil_frames(video_path, times, (480, 270))
    thumbs = [(ts, im) for ts, im in zip(times, ims, strict=True) if im is not None]

    rows = max(1, (len(thumbs) + cols - 1) // cols)
    top_h = 44 if banner else 12
    sheet = Image.new("RGB", (cols * 492 + 12, rows * 296 + top_h + 12), (16, 18, 22))
    dr = ImageDraw.Draw(sheet)
    if banner:
        dr.text((18, 14), _ascii_safe(banner), fill=(246, 238, 218))
    for i, (ts, im) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x, y = 12 + c * 492, top_h + r * 296
        sheet.paste(im, (x, y + 20))
        dr.text((x + 6, y + 2), f"t={ts:.2f}s", fill=(224, 216, 198))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def build_per_shot_strips(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    out_png: Path,
    *,
    banner: str = "L4 Per-Shot Temporal Strips (0%, 25%, 50%, 75%, 100%)",
) -> Path:
    """L4 visual QA: build 5-frame temporal strip (0/25/50/75/100%) per shot to catch prop drift or freezes."""
    tw, th = 320, 180
    n_shots = len(shot_windows)
    sheet = Image.new("RGB", (5 * (tw + 8) + 16, n_shots * (th + 28) + 52), (14, 16, 20))
    dr = ImageDraw.Draw(sheet)
    dr.text((14, 14), _ascii_safe(banner), fill=(245, 236, 215))

    fracs = (0.08, 0.28, 0.50, 0.72, 0.90)
    all_times: list[float] = []
    for sw in shot_windows:
        st, en = float(sw["start_s"]), float(sw["end_s"])
        dur = max(0.1, en - st)
        for fr in fracs:
            all_times.append(st + dur * fr)
    ims = _sample_pil_frames(video_path, all_times, (tw, th))

    for row_i, sw in enumerate(shot_windows):
        st, en = float(sw["start_s"]), float(sw["end_s"])
        y = 46 + row_i * (th + 28)
        dr.text(
            (14, y),
            _ascii_safe(f"{sw.get('shot_id')} [{sw.get('kind')}] {st:.1f}s-{en:.1f}s ({sw.get('scene_environment')})"),
            fill=(210, 205, 190),
        )
        for col_i in range(len(fracs)):
            im = ims[row_i * len(fracs) + col_i]
            if im is not None:
                sheet.paste(im, (12 + col_i * (tw + 8), y + 18))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def build_cut_boundary_sheet(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    out_png: Path,
    *,
    banner: str = "L4 Cut-Boundary Comparison Sheet (Last Clean Frame of Shot N vs First Clean Frame of Shot N+1)",
    xfade_s: float = 0.40,
) -> Path:
    """L4 visual QA: pair last clean frame of Shot N next to first clean post-dissolve frame of Shot N+1."""
    tw, th = 480, 270
    cuts = list(range(len(shot_windows) - 1))
    sheet = Image.new("RGB", (2 * tw + 36, max(1, len(cuts)) * (th + 30) + 52), (14, 16, 20))
    dr = ImageDraw.Draw(sheet)
    dr.text((14, 14), _ascii_safe(banner), fill=(245, 236, 215))

    all_times: list[float] = []
    for ci in cuts:
        b = shot_windows[ci + 1]
        cut_t = float(b["start_s"])
        all_times.extend([max(0.0, cut_t - 0.12), cut_t + xfade_s + 0.14])
    ims = _sample_pil_frames(video_path, all_times, (tw, th))

    for row_i, ci in enumerate(cuts):
        a, b = shot_windows[ci], shot_windows[ci + 1]
        cut_t = float(b["start_s"])
        y = 46 + row_i * (th + 30)
        dr.text(
            (14, y),
            _ascii_safe(f"Cut {ci+1}: {a['shot_id']} ({a['kind']}) -> {b['shot_id']} ({b['kind']}) @ t={cut_t:.2f}s"),
            fill=(218, 212, 196),
        )
        for col_i in range(2):
            im = ims[row_i * 2 + col_i]
            if im is not None:
                sheet.paste(im, (12 + col_i * (tw + 12), y + 20))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def build_audio_timeline_chart(audio_report: dict[str, Any], out_png: Path) -> Path:
    """L4 ears-on visual telemetry: render per-shot ambience, narrator/dialogue, SFX markers, and RMS/LUFS curve."""
    w, h = 1600, 460
    img = Image.new("RGB", (w, h), (16, 18, 24))
    dr = ImageDraw.Draw(img)
    dur = max(1.0, float(audio_report.get("duration_s", 1.0)))
    lufs = audio_report.get("integrated_lufs", 0.0)
    peak = audio_report.get("peak_dbfs", 0.0)
    dr.text(
        (20, 14),
        f"L4 Audio Timeline | Integrated: {lufs} LUFS | Peak: {peak} dBFS | Narrator: {audio_report.get('narrator_s', 0)}s | Dialogue: {audio_report.get('dialogue_s', 0)}s",
        fill=(245, 236, 215),
    )

    def x_of(t: float) -> int:
        return int(140 + (w - 180) * max(0.0, min(1.0, t / dur)))

    # Lane 1: Scene Environments + RMS bars
    dr.text((16, 62), "Ambience/RMS", fill=(180, 195, 210))
    for s in audio_report.get("shots") or []:
        x0, x1 = x_of(float(s["start_s"])), x_of(float(s["end_s"]))
        col = (44, 72, 92) if s.get("kind") == "map" else ((92, 58, 44) if s.get("kind") == "ltx_video" else (52, 78, 62))
        dr.rectangle([x0, 56, max(x0 + 2, x1 - 2), 130], fill=col, outline=(120, 130, 145))
        dr.text((x0 + 4, 60), f"{s.get('shot_id')}", fill=(240, 235, 225))
        dr.text((x0 + 4, 78), f"{s.get('scene_environment')}", fill=(205, 210, 215))
        dr.text((x0 + 4, 96), f"{s.get('rms_dbfs')}dB | {s.get('spectral_centroid_hz')}Hz", fill=(185, 220, 195))

    # Lane 2: Speech (Narrator vs Diegetic Dialogue)
    dr.text((16, 175), "Narrator /", fill=(235, 200, 130))
    dr.text((16, 195), "Dialogue", fill=(235, 140, 120))
    for tr in audio_report.get("speech_tracks") or []:
        x0 = x_of(float(tr["start_s"]))
        x1 = x_of(float(tr["start_s"]) + float(tr["duration_s"]))
        is_narr = tr.get("role") == "narrator"
        y0, y1 = (160, 205) if is_narr else (215, 260)
        col = (195, 145, 65) if is_narr else (175, 78, 68)
        dr.rectangle([x0, y0, max(x0 + 3, x1), y1], fill=col, outline=(245, 235, 220))
        dr.text((x0 + 4, y0 + 12), f"{tr.get('label')}", fill=(20, 20, 24))

    # Lane 3: Synced CC0 SFX Markers
    dr.text((16, 305), "CC0 SFX Cues", fill=(150, 215, 225))
    dr.line([(140, 320), (w - 40, 320)], fill=(80, 90, 105), width=2)
    for i, c in enumerate(audio_report.get("sfx_cues") or []):
        x = x_of(float(c["timestamp_s"]))
        y_off = 285 if i % 2 == 0 else 335
        dr.line([(x, 308), (x, 332)], fill=(115, 225, 235), width=2)
        dr.text((x + 3, y_off), f"{c.get('sfx')}@{c.get('timestamp_s')}s", fill=(160, 230, 240))

    # Time axis ticks
    for sec in range(0, int(dur) + 1, max(1, int(dur // 12))):
        x = x_of(float(sec))
        dr.line([(x, 405), (x, 418)], fill=(160, 165, 175), width=1)
        dr.text((x - 8, 424), f"{sec}s", fill=(190, 195, 205))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    return out_png
