"""Episode-First End-to-End Production Runner (`explainer_engine/episode/production_runner.py`, v4.3).

Executes the complete isolated production pipeline for an episode (`episodes/<episode_id>/`):
1. Enforces `EpisodeContext` & `EpisodeResolver` path and era isolation (`zero cross-episode asset leakage`).
2. Performs Paid-Service & Cost Preflight (`$0.00` local execution when using existing episode assets + GIS/2.5D engines).
3. Renders GIS + DEM Shaded-Relief map clips (`maps/plate.py` + `maps/render.py`) for map shots.
4. Renders the still_25d shots with the layered 2.5D renderer and its motion imitation (`production/layers25d.py`, plan P5).
5. Plans `ED-04`-compliant transitions (`edit/cinematic_transitions.py`).
6. Renders all 5 separate 48kHz stereo audio stems (`narration.wav`, `music.wav`, `ambience.wav`, `sfx.wav`, `mix.wav`)
   and runs independent narration dropout & stem continuity audits (`audio/dropouts.py`, `audio/sound_director.py`).
7. Assembles the frame-accurate master MP4 (`renders/final/<episode_id>_master.mp4`), extracts a 25-shot
   verification contact sheet (`qa/contact_sheets/<episode_id>_contact_sheet.jpg`), and writes
   `production/production_manifest.json` and `qa/acceptance_report.json`.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from explainer_engine.audio import acoustics, dropouts, sound_director
from explainer_engine.audio.environmental_sound_design import render_continuous_environmental_soundscape
from explainer_engine.episode.acceptance import gates as acceptance_gates
from explainer_engine.episode.validate import check_episode_ids
from explainer_engine.audio.sfx_planner import build_g4_audio_fx_plan
from explainer_engine.edit.cinematic_transitions import (
    plan_episode_cinematic_transitions,
    render_transition_frame_pair,
)
from explainer_engine.episode.context import (
    EpisodeContext,
    EpisodeResolver,
    load_episode_context,
    validate_asset_compatibility,
)
from explainer_engine.production.map_clip import render_episode_gis_map_clip
from explainer_engine.production import layers25d as L25


def _read_wav_mono_and_stereo(wav_path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        stereo = raw.reshape(-1, n_ch) if n_ch > 1 else np.stack([raw, raw], axis=1)
        mono = stereo.mean(axis=1)
    return mono, stereo, sr


def audit_rendered_audio_stems(
    stems_dir: Path,
    script_doc: Dict[str, Any],
    fps: int = 24,
) -> Dict[str, Any]:
    """Run quantitative continuity, RMS/peak dBFS, and mid-word dropout checks across all 5 audio stems."""
    stem_names = ("narration", "music", "ambience", "sfx", "mix")
    loaded_mono: Dict[str, np.ndarray] = {}
    loaded_stereo: Dict[str, np.ndarray] = {}
    metrics: Dict[str, Any] = {}
    sr = 48000

    for name in stem_names:
        p = stems_dir / f"{name}.wav"
        if not p.is_file():
            raise FileNotFoundError(f"Missing required audio stem: {p}")
        mono, stereo, sr = _read_wav_mono_and_stereo(p)
        loaded_mono[name] = mono
        loaded_stereo[name] = stereo
        rms_val = float(acoustics.rms_db(mono.astype(np.float64)))
        peak_val = float(20.0 * math.log10(float(np.max(np.abs( stereo ))) + 1e-12))
        metrics[name] = {
            "path": str(p),
            "sample_rate_hz": sr,
            "channels": int(stereo.shape[1]),
            "duration_sec": round(len(mono) / sr, 3),
            "rms_dbfs": round(rms_val, 2),
            "peak_dbfs": round(peak_val, 2),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }

    # Build synthetic word spine from audio_lines to verify independent narration stem continuity across all 25 spoken lines
    words: List[Dict[str, Any]] = []
    for ln in script_doc.get("audio_lines", []):
        s_sec = float(ln.get("start_sec", 0.0))
        e_sec = float(ln.get("end_sec", s_sec + float(ln.get("estimated_duration_seconds", 4.0))))
        active_end_sec = max(s_sec + 0.20, e_sec - 0.14)
        words.append({
            "word": str(ln.get("line_id") or "line"),
            "start_frame": int(round(s_sec * fps)),
            "end_frame": int(round(active_end_sec * fps)),
        })

    total_frames = int(round(sum(float(s.get("target_duration_seconds", 4.0)) for s in script_doc.get("shots", [])) * fps))
    spine = {"fps": fps, "total_frames": total_frames, "words": words}
    manifest = {
        "fps": fps,
        "total_frames": total_frames,
        "scenes": [{"scene": "S01", "start_frame": 0, "end_frame": total_frames, "acoustic": "outdoor", "entry": "butt", "ir_seed": acoustics.seed_of("S01")}],
        "beds": [{"id": "rt01", "scene": "S01", "kind": "room_tone", "ref": "rt", "gain_db": -38.0, "start_frame": 0, "end_frame": total_frames}],
        "music": [],
        "spots": [],
        "vacuums": [],
        "dialogue": [],
    }

    sd_findings = sound_director._check_stems(manifest, spine, loaded_stereo, {}, (0.5, 1.5))

    # Measure active-speech narration RMS and check for mid-line dropouts
    nar_mono = loaded_mono["narration"]
    line_audits: List[Dict[str, Any]] = []
    mid_line_dropouts = 0
    for ln in script_doc.get("audio_lines", []):
        s_sec = float(ln.get("start_sec", 0.0))
        e_sec = float(ln.get("end_sec", s_sec + 4.0))
        active_end = max(s_sec + 0.2, e_sec - 0.14)
        a_i = int(round(s_sec * sr))
        b_i = min(len(nar_mono), int(round(active_end * sr)))
        seg = nar_mono[a_i:b_i]
        seg_rms = float(acoustics.rms_db(seg.astype(np.float64)))
        d_scan = dropouts.scan(seg, sr, min_run=0.05, loud_db=-45.0)
        n_cuts = len(d_scan["cut_into_sound"])
        mid_line_dropouts += n_cuts
        line_audits.append({
            "line_id": ln.get("line_id"),
            "shot_id": ln.get("shot_id"),
            "start_sec": s_sec,
            "end_sec": e_sec,
            "active_rms_dbfs": round(seg_rms, 2),
            "mid_line_dropouts": n_cuts,
        })

    return {
        "stems": metrics,
        "spoken_lines_audited": len(line_audits),
        "mid_line_narration_dropouts": mid_line_dropouts,
        "sound_director_stem_findings": [f for f in sd_findings if f["rule"] == "SD-02"],
        "line_audits": line_audits,
    }


def assemble_episode_master_video(
    shot_records: List[Dict[str, Any]],
    transition_plans: List[Dict[str, Any]],
    master_audio_wav: Path,
    out_mp4_path: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> Dict[str, Any]:
    """Assemble all rendered shot clips with exact frame durations, apply transition bridges on boundary frames,
    and mux with the 48kHz stereo master mix WAV."""
    out_mp4_path = Path(out_mp4_path)
    out_mp4_path.parent.mkdir(parents=True, exist_ok=True)
    silent_video_path = out_mp4_path.with_name(out_mp4_path.stem + "_video_only.mp4")

    def _decode_clip(rec_item: Dict[str, Any]) -> np.ndarray:
        cpath = Path(rec_item["clip_path"])
        n_frames = int(rec_item["total_frames"])
        raw = subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-i", str(cpath),
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{width}x{height}",
                "-frames:v", str(n_frames),
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, height, width, 3).copy()
        if len(arr) < n_frames:
            pad = np.repeat(arr[-1:], n_frames - len(arr), axis=0)
            arr = np.concatenate([arr, pad], axis=0)
        return arr[:n_frames]

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(silent_video_path),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    total_written_frames = 0
    cur_frames = _decode_clip(shot_records[0])
    for idx in range(len(shot_records) - 1):
        nxt_frames = _decode_clip(shot_records[idx + 1])
        t_plan = transition_plans[idx]
        t_type = t_plan["transition_type"]
        t_frames = int(t_plan.get("transition_frames", 0))
        if t_type != "hard_cut_with_jl_bridge" and t_frames > 0:
            half_a = min(t_frames // 2, len(cur_frames) // 4)
            half_b = min(t_frames - half_a, len(nxt_frames) // 4)
            total_t = half_a + half_b
            if total_t >= 2:
                tail_a = cur_frames[-half_a:].copy() if half_a > 0 else cur_frames[-1:].copy()
                head_b = nxt_frames[:half_b].copy() if half_b > 0 else nxt_frames[:1].copy()
                zoom_xy = t_plan.get("zoom_target_xy") or [0.5, 0.5]
                for k in range(total_t):
                    u = (k + 1) / (total_t + 1)
                    src_a_im = Image.fromarray(tail_a[min(k, len(tail_a) - 1)], mode="RGB")
                    src_b_im = Image.fromarray(head_b[min(k, len(head_b) - 1)], mode="RGB")
                    blended_im = render_transition_frame_pair(
                        src_a_im, src_b_im, transition_type=t_type, progress_u=u, zoom_target_xy=zoom_xy
                    )
                    blended_arr = np.asarray(blended_im, dtype=np.uint8)
                    if k < half_a:
                        cur_frames[len(cur_frames) - half_a + k] = blended_arr
                    else:
                        nxt_frames[k - half_a] = blended_arr
        proc.stdin.write(cur_frames.tobytes())
        total_written_frames += len(cur_frames)
        cur_frames = nxt_frames
    proc.stdin.write(cur_frames.tobytes())
    total_written_frames += len(cur_frames)
    proc.stdin.close()
    proc.wait(timeout=180)

    # Mux video with master 48kHz stereo WAV
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(silent_video_path),
            "-i", str(master_audio_wav),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
            "-shortest",
            str(out_mp4_path),
        ],
        check=True,
    )
    if silent_video_path.exists():
        silent_video_path.unlink()

    return {
        "master_mp4_path": str(out_mp4_path),
        "total_frames": total_written_frames,
        "duration_sec": round(total_written_frames / fps, 3),
        "bytes": out_mp4_path.stat().st_size,
        "sha256": hashlib.sha256(out_mp4_path.read_bytes()).hexdigest(),
    }


def generate_master_video_contact_sheet(
    master_mp4_path: Path,
    shot_records: List[Dict[str, Any]],
    out_jpg_path: Path,
    cols: int = 5,
    thumb_w: int = 384,
    thumb_h: int = 216,
) -> Path:
    """Extract midpoint frames directly from the rendered `master_mp4_path` for every shot and build an annotated contact sheet."""
    out_jpg_path = Path(out_jpg_path)
    out_jpg_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(shot_records)
    rows = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 36)), (14, 16, 20))
    draw = ImageDraw.Draw(sheet)

    for idx, rec in enumerate(shot_records):
        mid_s = 0.5 * (float(rec["start_sec"]) + float(rec["end_sec"]))
        raw = subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-ss", f"{mid_s:.3f}",
                "-i", str(master_mp4_path),
                "-frames:v", "1",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{thumb_w}x{thumb_h}",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        if len(raw) == thumb_w * thumb_h * 3:
            im = Image.frombytes("RGB", (thumb_w, thumb_h), raw)
        else:
            im = Image.new("RGB", (thumb_w, thumb_h), (40, 20, 20))
        r, c = divmod(idx, cols)
        x0, y0 = c * thumb_w, r * (thumb_h + 36)
        sheet.paste(im, (x0, y0))
        label = f"{rec['shot_id']} ({rec['start_sec']:.1f}-{rec['end_sec']:.1f}s) [{rec['generation_mode']}]"
        draw.text((x0 + 6, y0 + thumb_h + 8), label[:46], fill=(235, 228, 210))

    sheet.save(out_jpg_path, quality=92)
    return out_jpg_path


def run_episode_production(
    episode_dir: Path | str,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    script_rel_path: str = "story/production_script.json",
    force_rerender_clips: bool = False,
    narration_path: Path | str | None = None,
) -> Dict[str, Any]:
    """Execute the complete Episode-First V4.3 production pipeline for any `episode_dir`.

    ``narration_path`` is the episode's read (a file inside the folder); without it the sound step draws a formant
    placeholder and the acceptance report FAILs ``narration_is_a_real_read`` (EP-03, plan F4). The acceptance report is
    measured (``episode/acceptance.py``): no gate is a literal, and the map count and the length come from the script."""
    t0 = time.time()
    episode_dir = Path(episode_dir).resolve()
    ctx = load_episode_context(episode_dir)
    resolver = EpisodeResolver(ctx)

    script_path = resolver.resolve_path(script_rel_path)
    script_doc = json.loads(script_path.read_text(encoding="utf-8"))
    shots = script_doc.get("shots", [])

    # 1. Phase 6 Cost & Isolation Preflight
    preflight_report = {
        "episode_id": ctx.episode_id,
        "historical_period": ctx.era_id,
        "total_shots": len(shots),
        "map_shots_count": sum(1 for s in shots if s.get("visual_type") == "map_visualization"),
        "cinematic_25d_shots_count": sum(1 for s in shots if s.get("visual_type") != "map_visualization"),
        "external_paid_api_calls": 0,
        "estimated_cost_usd": 0.0,
        "isolation_findings": check_episode_ids(episode_dir),
    }
    preflight_report["isolation_verified"] = not preflight_report["isolation_findings"]
    if narration_path is not None:
        narration_path = resolver.resolve_path(narration_path)
    resolver.resolve_path("qa/cost_and_isolation_preflight.json").write_text(
        json.dumps(preflight_report, indent=2), encoding="utf-8"
    )

    # 2. Render each shot clip (GIS Shaded-Relief Maps + 2.5D Multi-Axis Prehistoric Keyframe Clips)
    shot_clips_dir = resolver.resolve_path("production/shot_clips")
    map_clips_dir = resolver.resolve_path("production/map_clips")
    dem_cache_dir = resolver.resolve_path("assets/maps/dem")
    map_renders_dir = resolver.resolve_path("assets/maps/renders")
    shot_clips_dir.mkdir(parents=True, exist_ok=True)
    map_clips_dir.mkdir(parents=True, exist_ok=True)
    dem_cache_dir.mkdir(parents=True, exist_ok=True)
    map_renders_dir.mkdir(parents=True, exist_ok=True)

    shot_records: List[Dict[str, Any]] = []
    t_cursor = 0.0

    for sh in shots:
        sid = sh["shot_id"]
        dur_s = float(sh.get("target_duration_seconds", 4.0))
        start_s = round(t_cursor, 3)
        end_s = round(t_cursor + dur_s, 3)
        t_cursor = end_s

        # Validate shot metadata against EpisodeContext
        ok_shot, reason_shot = validate_asset_compatibility(
            ctx,
            {
                "asset_id": sid,
                "episode_scope": sh.get("episode_scope", ctx.episode_id),
                "historical_period": sh.get("historical_period", ctx.era_id),
                "era_tags": sh.get("era_tags", []),
            },
        )
        if not ok_shot:
            raise ValueError(reason_shot)

        if sh.get("visual_type") == "map_visualization" or sh.get("generation_mode") == "MAP_25D":
            out_clip = map_clips_dir / f"{sid}.mp4"
            start_png = map_renders_dir / f"{sid}_gis_start.png"
            end_png = map_renders_dir / f"{sid}_gis_end.png"
            if out_clip.is_file() and out_clip.stat().st_size > 10000 and start_png.is_file():
                cached_plates = sorted(dem_cache_dir.glob("relief-plate-*.png"))
                cp_path = cached_plates[0] if cached_plates else start_png
                res = {
                    "provider": "gis_shaded_relief_map_engine",
                    "total_frames": max(fps, int(round(dur_s * fps))),
                    "start_keyframe_path": str(start_png),
                    "end_keyframe_path": str(end_png),
                    "cached_plate_path": str(cp_path),
                    "cached_plate_spec_hash": cp_path.stem.split("-")[-1],
                    "output_sha256": hashlib.sha256(out_clip.read_bytes()).hexdigest(),
                }
            else:
                res = render_episode_gis_map_clip(
                    shot=sh,
                    out_mp4_path=out_clip,
                    cache_dir=dem_cache_dir,
                    keyframes_out_dir=map_renders_dir,
                    width=width,
                    height=height,
                    fps=fps,
                )
            # Also copy clip to shot_clips_dir for unified manifest indexing
            unified_clip = shot_clips_dir / f"{sid}.mp4"
            if unified_clip != out_clip:
                unified_clip.write_bytes(out_clip.read_bytes())
            shot_records.append({
                "shot_id": sid,
                "segment_id": sh.get("segment_id"),
                "visual_type": "map_visualization",
                "generation_mode": "GIS_DEM_SHADED_RELIEF_MAP",
                "provider": res["provider"],
                "start_sec": start_s,
                "end_sec": end_s,
                "duration_sec": dur_s,
                "total_frames": res["total_frames"],
                "source_start_keyframe": res["start_keyframe_path"],
                "source_end_keyframe": res["end_keyframe_path"],
                "cached_plate_path": res["cached_plate_path"],
                "cached_plate_spec_hash": res["cached_plate_spec_hash"],
                "clip_path": str(out_clip),
                "output_sha256": res["output_sha256"],
            })
        else:
            start_kf_rel = sh.get("start_keyframe_rel") or f"assets/generated/images/{sid}_start.jpg"
            end_kf_rel = sh.get("end_keyframe_rel")
            start_kf_path = resolver.resolve_path(start_kf_rel)
            end_kf_path = resolver.resolve_path(end_kf_rel) if end_kf_rel else None
            out_clip = shot_clips_dir / f"{sid}.mp4"

            report_path = out_clip.with_suffix(".25d.json")
            if (not force_rerender_clips) and out_clip.is_file() and report_path.is_file():
                res = json.loads(report_path.read_text(encoding="utf-8"))   # the clip and its measured report
            else:
                res = L25.render_clip(sh, start_kf_path, out_clip, width=width, height=height, fps=fps,
                                      end_picture=end_kf_path, script=script_doc)
                report_path.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
            shot_records.append({
                "shot_id": sid,
                "segment_id": sh.get("segment_id"),
                "visual_type": sh.get("visual_type", "cinematic_scene"),
                "generation_mode": "LAYERED_25D_MOTION_IMITATION",
                "provider": res["provider"],
                "camera": res["camera"],
                "effects": res["effects"],
                "families": res["families"],
                "gates_25d": res["gates"]["status"],
                "start_sec": start_s,
                "end_sec": end_s,
                "duration_sec": dur_s,
                "total_frames": res["total_frames"],
                "source_start_keyframe": str(start_kf_path),
                "source_end_keyframe": str(end_kf_path) if end_kf_path else None,
                "clip_path": str(out_clip),
                "output_sha256": res["output_sha256"],
            })

    # 3. Plan ED-04 Compliant Transitions
    transition_plans = plan_episode_cinematic_transitions(script_doc, fps=fps, allow_decorative_wipes=False)
    transitions_path = resolver.resolve_path("editing/transition_plan.json")
    transitions_path.parent.mkdir(parents=True, exist_ok=True)
    transitions_path.write_text(json.dumps(transition_plans, indent=2), encoding="utf-8")

    # 4. Render 5 Continuous 48kHz Stereo Audio Stems & Audit Stems
    stems_dir = resolver.resolve_path("audio/stems")
    master_mix_wav = resolver.resolve_path(f"audio/{ctx.episode_id}_master_mix.wav")
    audio_res = render_continuous_environmental_soundscape(
        script_doc=script_doc,
        out_wav_path=master_mix_wav,
        existing_audio_pack_path=narration_path,  # None -> a formant placeholder, FAILed by the acceptance report
        transition_plans=transition_plans,
        stems_output_dir=stems_dir,
    )
    stem_audit = audit_rendered_audio_stems(stems_dir=stems_dir, script_doc=script_doc, fps=fps)
    stem_audit_path = resolver.resolve_path("qa/audio_stem_audit.json")
    stem_audit_path.write_text(json.dumps(stem_audit, indent=2), encoding="utf-8")

    # 5. Assemble Final Master Video (1920x1080, 24fps, 120.0s, 48kHz stereo)
    master_mp4_path = resolver.resolve_path(f"renders/final/{ctx.episode_id}_master.mp4")
    video_res = assemble_episode_master_video(
        shot_records=shot_records,
        transition_plans=transition_plans,
        master_audio_wav=stems_dir / "mix.wav",
        out_mp4_path=master_mp4_path,
        width=width,
        height=height,
        fps=fps,
    )

    # 6. Extract 25-Shot Verification Contact Sheet from Rendered Master MP4
    contact_sheet_path = resolver.resolve_path(f"qa/contact_sheets/{ctx.episode_id}_contact_sheet.jpg")
    generate_master_video_contact_sheet(
        master_mp4_path=master_mp4_path,
        shot_records=shot_records,
        out_jpg_path=contact_sheet_path,
    )

    # 7. Write Production Manifest & the measured acceptance report (EP-03)
    elapsed_s = round(time.time() - t0, 2)
    acceptance = acceptance_gates(
        root=episode_dir, script=script_doc, shot_records=shot_records, transition_plans=transition_plans,
        audio=audio_res, stem_audit=stem_audit, video=video_res, fps=fps,
        forbidden_tokens=sorted(ctx.forbidden_semantic_tokens), narration_source=audio_res.get("narration_source"),
        paid_calls=None,
    )

    manifest_doc = {
        "schema": "episode_production_manifest/4.3",
        "episode_id": ctx.episode_id,
        "title": ctx.title,
        "historical_period": ctx.era_id,
        "render_elapsed_sec": elapsed_s,
        "master_video": video_res,
        "contact_sheet_path": str(contact_sheet_path),
        "audio_summary": {
            "stems_dir": str(stems_dir),
            "stem_metrics": stem_audit["stems"],
            "spoken_lines_count": stem_audit["spoken_lines_audited"],
            "mid_line_narration_dropouts": stem_audit["mid_line_narration_dropouts"],
            "sound_director_stem_findings": stem_audit["sound_director_stem_findings"],
            "music_duck_depth_db": audio_res["music_duck_depth_db"],
            "ambience_duck_depth_db": audio_res["ambience_duck_depth_db"],
        },
        "transitions_summary": {
            "total_cuts": len(transition_plans),
            "hard_cuts_count": sum(1 for p in transition_plans if p["transition_type"] == "hard_cut_with_jl_bridge"),
            "map_zoom_through_count": sum(1 for p in transition_plans if p["transition_type"] == "map_to_location_zoom_through"),
            "cross_dissolve_count": sum(1 for p in transition_plans if p["transition_type"] == "cross_dissolve_8f"),
            "smoke_wipe_count": sum(1 for p in transition_plans if p["transition_type"] == "atmospheric_smoke_ash_wipe"),
            "ed04_all_compliant": all(p["ed04_compliant"] for p in transition_plans),
        },
        "shots": shot_records,
        "acceptance": acceptance,
        "all_gates_passed": acceptance["status"] == "PASS",
    }

    manifest_path = resolver.resolve_path("production/production_manifest.json")
    manifest_path.write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")
    qa_report_path = resolver.resolve_path("qa/acceptance_report.json")
    qa_report_path.write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")

    return manifest_doc
