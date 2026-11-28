"""Executable CLI Launcher for Stack-2 Modal Serverless Cinema Pipeline ($10 Cap + Hybrid Escalation + OTIO).

Run directly from Windows PowerShell or Linux bash::

    python -m explainer_engine.cli.stack2_runner \\
        --episode-id whatif_island_mvp_01 \\
        --out-dir jobs/whatif_island_mvp_01 \\
        --cap-usd 10.0 \\
        --dry-run \\
        --run-qa-smoke

Executes the full end-to-end Stack-2 control plane:
1. Initializes persistent SQLite WAL ``EpisodeBudgetGuard`` (default $10.00 hard cap, $8.00 checkpoint).
2. Slices an approved 3x3 Contact Sheet into 9 border-trimmed 16-bit PNG panels (if provided, or
   generates a synthetic 3x3 calibration sheet in ``--dry-run`` mode).
3. Routes every dramatic shot (16:9 + native 9:16) via ``hybrid_escalation_router``.
4. Builds & saves validated Headless ComfyUI v0.28.0+ API JSON graphs (Wan 2.2 Distilled FP8,
   LatentSync 1.6 with >=0.5s silence padding, native SeedVR2 batch=4n+1>=5).
5. Pads dialogue WAVs via FFmpeg (``>=0.6s`` trailing silence) and dry-runs/executes surgical
   Sync-3 / Seedance 2.5 / ElevenLabs v4 API escalations.
6. Exports free-NLE ``.otio`` timeline (4 isolated audio stems + J/L-cuts + C2PA + NVENC AV1 safe config).
7. Runs real OpenCV/FFmpeg QA smoke checks (``check_mouth_motion_sync``, ``check_acting_dynamics_and_freeze``,
   ``validate_native_keyframe_plates``) when ``--run-qa-smoke`` is set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import soundfile as sf

from explainer_engine.cloud.hybrid_api_clients import (
    run_elevenlabs_v4_tts,
    run_sync3_lipsync_escalation,
)
from explainer_engine.cloud.modal_cinema_studio import (
    DEFAULT_EPISODE_BUDGET_CAP_USD,
    EpisodeBudgetGuard,
    build_comfy_latentsync16_graph,
    build_comfy_seedvr2_graph,
    build_comfy_wan22_distilled_graph,
    pad_audio_for_latentsync,
)
from explainer_engine.edit.otio_exporter import export_episode_otio
from explainer_engine.episode.mvp_drama_poc import build_stack2_drama_mvp_plan
from explainer_engine.qa.cinema_gates import (
    check_acting_dynamics_and_freeze,
    check_mouth_motion_sync,
)
from explainer_engine.studio.contact_sheet_slicer import slice_contact_sheet_3x3
from explainer_engine.videolane.multishot_scene_director import validate_native_keyframe_plates


def _create_synthetic_3x3_sheet(out_path: Path) -> Path:
    """Create a crisp 3840x2160 calibration 3x3 contact sheet with thin black gutters for dry-run tests."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = np.zeros((2160, 3840, 3), dtype=np.uint8)
    cw, ch = 3840 // 3, 2160 // 3
    rng = np.random.default_rng(42)
    for r in range(3):
        for c in range(3):
            idx = r * 3 + c
            y0, y1 = r * ch + 4, (r + 1) * ch - 4
            x0, x1 = c * cw + 4, (c + 1) * cw - 4
            tone = (40 + idx * 14, 55 + idx * 10, 75 + idx * 12)
            cell = np.full((y1 - y0, x1 - x0, 3), tone, dtype=np.uint8)
            noise = rng.integers(-8, 9, size=cell.shape, dtype=np.int16)
            cell = np.clip(cell.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            cv2.circle(cell, ((x1 - x0) // 2, (y1 - y0) // 2), 90 + idx * 5, (210, 185, 155), -1)
            canvas[y0:y1, x0:x1] = cell
    cv2.imwrite(str(out_path), canvas)
    return out_path


def _run_local_qa_smoke(work_dir: Path, panel_paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Run real FFmpeg WAV padding + OpenCV dynamic/mouth-sync/plate-diversity QA checks locally ($0.00)."""
    qa_dir = work_dir / "qa_smoke"
    qa_dir.mkdir(parents=True, exist_ok=True)

    # 1. Real WAV creation + FFmpeg >=0.6s LatentSync silence padding
    sr = 16000
    t = np.linspace(0.0, 1.0, sr, endpoint=False, dtype=np.float32)
    raw_wav = qa_dir / "sample_dialogue_raw.wav"
    sig = (0.25 * np.sin(2.0 * np.pi * 650.0 * t)).astype(np.float32)
    sf.write(str(raw_wav), sig, sr)
    padded_wav = pad_audio_for_latentsync(raw_wav, qa_dir / "sample_dialogue_padded.wav", tail_silence_s=0.60)
    pad_data, pad_sr = sf.read(str(padded_wav), dtype="float32")
    padded_dur_s = round(len(pad_data) / float(pad_sr), 3)

    # 2. Real synthetic dynamic clip (moving actor, still mouth for narrator-over shot) -> QA checks
    smoke_mp4 = qa_dir / "smoke_dynamic_narr.mp4"
    rng = np.random.default_rng(11)
    bg = rng.integers(35, 65, size=(180, 320, 3), dtype=np.uint8)
    vw = cv2.VideoWriter(str(smoke_mp4), cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (320, 180))  # type: ignore[attr-defined]
    for i in range(36):
        fr = bg.copy()
        # Two moving foreground actors on left & right sides (>20% frame coverage, outside center mouth ROI x=115..204)
        lx = 34 + int((i % 12) * 4)
        rx = 286 - int((i % 12) * 4)
        cv2.rectangle(fr, (lx - 26, 20), (lx + 26, 170), (205, 175, 145), -1)
        cv2.rectangle(fr, (rx - 26, 20), (rx + 26, 170), (165, 95, 85), -1)
        vw.write(fr)
    vw.release()

    acting_res = check_acting_dynamics_and_freeze(smoke_mp4, max_freeze_s=0.85, min_residual_subject_flow=0.08)
    # The synthetic clip has no face to detect: the gate measures a fixed box over the still centre of the frame
    mouth_res = check_mouth_motion_sync(smoke_mp4, has_dialogue=False, face_boxes=[[128.0, 50.0, 64.0, 64.0]] * 36)
    plate_res = validate_native_keyframe_plates(
        [
            {
                "shot_id": f"shot_{p['panel_index']:02d}",
                "route": "ltx_video",
                "plate_sha256": p["sha256"],
                "plate_width": p["width"],
                "plate_height": p["height"],
            }
            for p in panel_paths[:4]
        ]
    )

    all_ok = (
        padded_dur_s >= 1.55
        and acting_res["status"] == "PASS"
        and mouth_res["status"] == "PASS"
        and plate_res["status"] == "PASS"
    )
    return {
        "status": "PASS" if all_ok else "FAIL",
        "padded_wav": str(padded_wav),
        "padded_wav_duration_s": padded_dur_s,
        "acting_freeze_gate": acting_res,
        "mouth_motion_gate": mouth_res,
        "plate_diversity_gate": plate_res,
    }


def run_stack2_pipeline(
    *,
    episode_id: str,
    out_dir: Path,
    cap_usd: float = DEFAULT_EPISODE_BUDGET_CAP_USD,
    contact_sheet_path: Path | None = None,
    dry_run: bool = True,
    run_qa_smoke: bool = False,
) -> dict[str, Any]:
    """Execute the end-to-end Stack-2 pipeline (SQLite WAL budget, 3x3 slice, routing, ComfyUI JSONs, OTIO, QA)."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger_db = out_dir / f"{episode_id}_spend_ledger.sqlite3"
    guard = EpisodeBudgetGuard(episode_id=episode_id, cap_usd=cap_usd, db_path=ledger_db)

    # 1. Contact Sheet 3x3 Slicing (16-bit PNGs)
    sheet_src = contact_sheet_path
    if sheet_src is None and dry_run:
        sheet_src = _create_synthetic_3x3_sheet(out_dir / "inputs" / f"{episode_id}_contact_sheet_3x3.png")
    slice_manifest: dict[str, Any] | None = None
    if sheet_src is not None:
        slice_manifest = slice_contact_sheet_3x3(
            sheet_src,
            out_dir / "plates_16bit",
            prefix=episode_id,
            target_width=1280,
            target_height=720,
            save_16bit_png=True,
        )

    # 2. Build Stack-2 MVP routed shot plan + .otio
    mvp = build_stack2_drama_mvp_plan(episode_id=episode_id, out_dir=out_dir, episode_cap_usd=cap_usd)

    # 3. Generate validated ComfyUI v0.28.0+ API JSON graphs per shot
    graphs_dir = out_dir / "comfy_graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    generated_graphs: list[str] = []
    api_calls: list[dict[str, Any]] = []

    for idx, sh in enumerate(mvp["routed_shots"]):
        sid = str(sh["shot_id"])
        plate_name = (
            Path(slice_manifest["panels"][idx % 9]["path"]).name
            if slice_manifest is not None
            else f"{sid}_plate.png"
        )
        if sh["video_engine"] == "wan_2_2_14b_distilled_fp8_modal":
            g = build_comfy_wan22_distilled_graph(
                prompt=f"35mm cinema scene {sid}, natural camera motion, motivated lighting",
                start_image_name=plate_name,
                width=1280,
                height=720,
                steps=6,
            )
            gp = graphs_dir / f"{sid}_wan22.json"
            gp.write_text(json.dumps(g, indent=2) + "\n", encoding="utf-8")
            generated_graphs.append(str(gp))

        if sh.get("tts_engine") == "elevenlabs_v4_turbo":
            api_calls.append(
                run_elevenlabs_v4_tts(
                    job_id=f"{sid}_tts",
                    text="We stay on this island until the tide turns, or nobody leaves alive.",
                    voice_id="odom_hero_voice",
                    out_wav=out_dir / "audio" / f"{sid}_dlg.wav",
                    turbo=True,
                    budget_guard=guard,
                    dry_run=dry_run,
                )
            )

        if sh.get("lipsync_engine") == "latentsync_1_6_modal_l40s":
            g_ls = build_comfy_latentsync16_graph(
                video_name=f"{sid}.mp4",
                padded_audio_wav_name=f"{sid}_dlg_padded.wav",
                tail_silence_s=0.60,
            )
            gp_ls = graphs_dir / f"{sid}_latentsync16.json"
            gp_ls.write_text(json.dumps(g_ls, indent=2) + "\n", encoding="utf-8")
            generated_graphs.append(str(gp_ls))
        elif sh.get("lipsync_engine") == "sync_3_api_4k":
            api_calls.append(
                run_sync3_lipsync_escalation(
                    job_id=f"{sid}_sync3",
                    video_url=f"https://example.invalid/{sid}.mp4",
                    audio_url=f"https://example.invalid/{sid}_dlg.wav",
                    duration_s=float(sh["duration_s"]),
                    budget_guard=guard,
                    dry_run=dry_run,
                )
            )

    # Native ComfyUI SeedVR2 2K upscale graph (batch_size=5 = 4*1+1)
    g_vr = build_comfy_seedvr2_graph(input_video_name=f"{episode_id}_rough_cut.mp4", target_height=1440, batch_size=5)
    gp_vr = graphs_dir / f"{episode_id}_seedvr2_2k.json"
    gp_vr.write_text(json.dumps(g_vr, indent=2) + "\n", encoding="utf-8")
    generated_graphs.append(str(gp_vr))

    # 4. Also export native 9:16 vertical .otio teaser alongside 16:9 master .otio
    vert_shots = [sh for sh in mvp["routed_shots"] if sh["aspect_ratio"] == "9:16"]
    vert_otio = export_episode_otio(
        episode_name=f"{episode_id}_vertical_9x16",
        video_shots=vert_shots,
        out_otio=out_dir / f"{episode_id}_vertical_9x16.otio",
        fps=30.0,
        aspect_ratio="9:16",
    )

    # 5. Optional real local QA smoke execution
    qa_report: dict[str, Any] | None = None
    if run_qa_smoke:
        qa_report = _run_local_qa_smoke(out_dir, slice_manifest["panels"] if slice_manifest else [])

    report = {
        "schema": "stack2_runner_report/1",
        "episode_id": episode_id,
        "dry_run": dry_run,
        "ledger_db": str(ledger_db),
        "budget_summary": guard.summary(),
        "contact_sheet_panels": slice_manifest["panel_count"] if slice_manifest else 0,
        "comfy_graphs_generated": len(generated_graphs),
        "comfy_graphs": generated_graphs,
        "api_escalation_calls": api_calls,
        "otio_master_16x9": mvp["otio_timeline"],
        "otio_teaser_9x16": str(vert_otio),
        "qa_smoke": qa_report,
    }
    report_path = out_dir / f"{episode_id}_run_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stack-2 Modal Cinema Studio CLI Runner ($10 Episode Cap)")
    parser.add_argument("--episode-id", default="whatif_island_mvp_01")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cap-usd", type=float, default=DEFAULT_EPISODE_BUDGET_CAP_USD)
    parser.add_argument("--contact-sheet", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run full pipeline with $0.00 API/GPU spend")
    parser.add_argument("--run-qa-smoke", action="store_true", help="Execute local FFmpeg/OpenCV QA smoke gates")
    args = parser.parse_args(argv)

    rep = run_stack2_pipeline(
        episode_id=args.episode_id,
        out_dir=args.out_dir,
        cap_usd=args.cap_usd,
        contact_sheet_path=args.contact_sheet,
        dry_run=bool(args.dry_run),
        run_qa_smoke=bool(args.run_qa_smoke),
    )
    print(json.dumps({"status": "OK", "report_path": rep["report_path"], "qa_smoke": (rep["qa_smoke"] or {}).get("status")}, indent=2))
    if rep["qa_smoke"] is not None and rep["qa_smoke"]["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
