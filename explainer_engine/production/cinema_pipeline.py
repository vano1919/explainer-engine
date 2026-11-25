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
from explainer_engine.finish.cinema_grade import DEFAULT_CINEMA_GRADE, CinemaGradeSpec
from explainer_engine.maps.cinema_map import render_cinema_map_clip
from explainer_engine.orchestration.claude_simulator import ClaudeSimulator
from explainer_engine.overlay import bridge_compiler as BC
from explainer_engine.production.cinema_25d import render_cinema_25d_clip
from explainer_engine.qa import cinema_gates as CG
from explainer_engine.qa import identity_lock as IL


def assemble_cinema_film(
    film_spec: dict[str, Any],
    work_dir: Path,
    out_mp4: Path,
    *,
    repo_root: Path,
    grade_spec: CinemaGradeSpec = DEFAULT_CINEMA_GRADE,
) -> dict[str, Any]:
    """Render, assemble, sound-design, and QA a complete multi-scene documentary film with zero manual hacks."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    width = int(film_spec.get("width", 1280))
    height = int(film_spec.get("height", 720))
    fps = int(film_spec.get("fps", 24))
    xfade_s = float(film_spec.get("xfade_s", 0.45))

    sim = ClaudeSimulator(repo_root)
    state_path = work_dir / "production_state.json"
    sm = ProductionStateMachine(state_path, episode_id=str(film_spec["episode_id"]))

    # Record script stage via simulator pre-write check
    spec_file = work_dir / "film_spec.json"
    sim.check_write(spec_file)
    spec_file.write_text(json.dumps(film_spec, indent=2) + "\n", encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[spec_file])

    # 1. Render every shot (2.5D or Cinema Map)
    clip_paths: list[Path] = []
    clip_durations: list[float] = []
    shot_windows: list[dict[str, Any]] = []
    all_sfx_cues: list[dict[str, Any]] = []
    render_reports: list[dict[str, Any]] = []

    cursor_s = 0.0
    for idx, shot in enumerate(film_spec["shots"]):
        sid = str(shot["shot_id"])
        kind = str(shot["kind"])
        dur_s = float(shot["duration_s"])
        clip_p = work_dir / "clips" / f"{idx:02d}_{sid}.mp4"
        sim.check_write(clip_p)

        if kind == "map":
            rep = render_cinema_map_clip(shot["map_spec"], clip_p, width=width, height=height, fps=fps, grade_spec=grade_spec)
            for ev in rep["sfx_events"]:
                all_sfx_cues.append(
                    {
                        "cue_id": ev["cue_id"],
                        "sfx": ev["sfx"],
                        "timestamp_s": round(cursor_s + float(ev["offset_s"]), 3),
                        "gain_db": float(ev.get("gain_db", -4.0)),
                    }
                )
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
                "ambience_gain_db": float(shot.get("ambience_gain_db", -4.0)),
                "start_s": round(start_t, 3),
                "end_s": round(end_t, 3),
            }
        )
        if idx > 0:
            all_sfx_cues.append(
                {
                    "cue_id": f"transition_{idx:02d}",
                    "sfx": "cinematic_whoosh",
                    "timestamp_s": round(max(0.0, start_t - 0.15), 3),
                    "gain_db": -6.5,
                }
            )
        cursor_s = end_t - xfade_s if idx < len(film_spec["shots"]) - 1 else end_t

    total_dur_s = round(cursor_s, 3)

    # 2. Stitch all clips with smooth documentary cross-dissolves (xfade)
    xfade_mp4 = work_dir / "stitched_xfade.mp4"
    sim.check_bash(f"ffmpeg xfade stitch -> {xfade_mp4.name}")
    if len(clip_paths) == 1:
        xfade_mp4 = clip_paths[0]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for cp in clip_paths:
            cmd += ["-i", str(cp)]
        filters: list[str] = []
        prev_lbl = "[0:v]"
        offset = clip_durations[0] - xfade_s
        for i in range(1, len(clip_paths)):
            out_lbl = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
            filters.append(f"{prev_lbl}[{i}:v]xfade=transition=fade:duration={xfade_s:.3f}:offset={offset:.3f}{out_lbl}")
            prev_lbl = out_lbl
            offset += clip_durations[i] - xfade_s
        cmd += [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            str(xfade_mp4),
        ]
        subprocess.run(cmd, check=True)

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

    # 4. Build scene-locked 48kHz stereo soundscape (per-shot ambience + map-action SFX + pyloudnorm -14 LUFS)
    audio_wav = work_dir / "master_48k_stereo.wav"
    audio_rep = build_scene_locked_soundscape(
        shot_windows,
        audio_wav,
        sfx_cues=all_sfx_cues,
        total_duration_s=total_dur_s,
        music_bed=film_spec.get("music_bed", "doc_strings_tense"),
        music_gain_db=float(film_spec.get("music_gain_db", -12.5)),
        target_lufs=-14.0,
        true_peak_ceiling_db=-1.2,
        report_path=work_dir / "audio_timeline_report.json",
    )

    # 5. Mux final MP4 (48kHz 2-ch stereo AAC 192k + stream-copied video)
    sim.check_bash(f"ffmpeg mux final -> {out_mp4.name}")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(bridged_mp4), "-i", str(audio_wav),
            "-c:v", "copy", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(out_mp4),
        ],
        check=True,
    )

    # 6. Automated Cinema QA Gates (Static-Shot + Mid-Frame Tear + Audio-Scene Consistency + Identity Lock)
    static_qa = CG.check_no_static_shots(out_mp4, shot_windows)
    tear_qa = CG.check_no_midframe_tears(out_mp4)
    audio_qa = CG.check_audio_scene_consistency(audio_rep)

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
        and all(r["status"] == "PASS" for r in id_results)
    )
    sim.check_stop(state_path, ["script"])
    sim.save_audit(work_dir / "claude_simulator_audit.json")

    summary = {
        "episode_id": film_spec["episode_id"],
        "output_mp4": str(out_mp4),
        "total_duration_s": total_dur_s,
        "resolution": [width, height],
        "fps": fps,
        "all_cinema_qa_passed": all_qa_ok,
        "static_shot_qa": static_qa,
        "midframe_tear_qa": tear_qa,
        "audio_scene_qa": audio_qa,
        "identity_lock_qa": id_results,
        "audio_report": audio_rep,
        "render_reports": render_reports,
        "claude_simulator_hooks_checked": len(sim.audit_events),
    }
    (work_dir / "film_build_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def build_contact_sheet(
    video_path: Path,
    out_png: Path,
    *,
    num_frames: int = 16,
    cols: int = 4,
    banner: str = "",
) -> Path:
    """Extract evenly spaced temporal frames across a video into a labeled high-res Contact Sheet."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = total / max(1.0, fps)
    times = [round(dur * (i + 0.5) / num_frames, 2) for i in range(num_frames)]
    thumbs: list[tuple[float, Image.Image]] = []
    for ts in times:
        idx = max(0, min(max(0, total - 1), int(round(ts * fps))))
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, bgr = cap.read()
        if ok and bgr is not None:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            thumbs.append((ts, Image.fromarray(rgb).resize((480, 270), Image.LANCZOS)))
    cap.release()

    rows = (len(thumbs) + cols - 1) // cols
    top_h = 44 if banner else 12
    sheet = Image.new("RGB", (cols * 492 + 12, rows * 296 + top_h + 12), (16, 18, 22))
    dr = ImageDraw.Draw(sheet)
    if banner:
        dr.text((18, 14), banner, fill=(246, 238, 218))
    for i, (ts, im) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x, y = 12 + c * 492, top_h + r * 296
        sheet.paste(im, (x, y + 20))
        dr.text((x + 6, y + 2), f"t={ts:.2f}s", fill=(224, 216, 198))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png
