"""Benchmark CPU perception candidates on real Truce 1914 vertical-slice assets (Task 2 R2 Step 2 & 6, Decision 5).

Usage on the creator's PC:
    python -m scripts.benchmark_perception_cpu --episode episodes/ep_truce_1914 --shots S08_SH002 S02_SH008 S05_SH020

Compares:
1. Visual object/phrase grounding: ``IDEA-Research/grounding-dino-tiny`` vs. ``microsoft/Florence-2-base`` vs.
   deterministic SAM-mask + HSV geometry baseline.
2. Audio event classification: ``YAMNet`` vs. ``MIT/ast-finetuned-audioset-10-10-0.4593`` (+ optional ``CLAP``) vs.
   deterministic DSP spectral analyzer.
Writes ``episodes/<ep>/qa/perception_benchmark.json``.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic
from explainer_engine.production import perceive_picture as PP
from explainer_engine.qa import perceive_audio as PA


def benchmark_episode_slice(
    episode_root: Path,
    shot_ids: list[str],
    *,
    run_clap: bool = False,
) -> dict:
    root = Path(episode_root)
    script_path = root / "story" / "production_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8")) if script_path.is_file() else {}
    shots_by_id = {s["shot_id"]: s for s in (script.get("shots") or []) if isinstance(s, dict) and s.get("shot_id")}

    pics_json = root / "production" / "pictures.json"
    pics_map = json.loads(pics_json.read_text(encoding="utf-8")).get("pictures", {}) if pics_json.is_file() else {}

    visual_rows = []
    audio_rows = []

    for sid in shot_ids:
        shot = shots_by_id.get(sid, {"shot_id": sid})
        pic_rec = pics_map.get(f"{sid}_start") or {}
        pic_path = (root / pic_rec["file"]) if pic_rec.get("file") else (root / "pictures" / sid / "start_01.png")
        for det in ("auto", "grounding_dino_tiny", "florence2_base"):
            t0 = time.time()
            res = PP.perceive_picture(shot, script, picture=pic_path if pic_path.is_file() else None, detector=det)
            elapsed = round(time.time() - t0, 4)
            visual_rows.append({
                "shot_id": sid,
                "requested_detector": det,
                "actual_detector": res["provenance"]["detector_model"],
                "picture_found": pic_path.is_file(),
                "elapsed_s": elapsed,
                "sky_visible": res["environment"]["sky_visible"],
                "objects_count": len(res["objects"]),
                "vlm_detections_count": len(res.get("vlm_detections") or []),
            })

        wav_path = root / "audio" / "stems" / "sfx.wav"
        if wav_path.is_file():
            for clf in ("deterministic", "yamnet", "ast"):
                t0 = time.time()
                ares = PA.perceive_audio(
                    wav_path,
                    shot_id=sid,
                    expected_perspective=str((shot.get("director_brief") or {}).get("sound_perspective") or ""),
                    classifier=clf,
                    run_clap=run_clap,
                )
                elapsed = round(time.time() - t0, 4)
                audio_rows.append({
                    "shot_id": sid,
                    "requested_classifier": clf,
                    "actual_model": ares["model_used"],
                    "elapsed_s": elapsed,
                    "rms_dbfs": ares["dsp"]["rms_dbfs"],
                    "detected_events": ares["detected_events"][:3],
                    "clap_similarity": ares["clap_advisory_similarity"],
                })

    report = {
        "schema": "perception_benchmark/1.0",
        "episode": root.name,
        "shots": shot_ids,
        "visual_benchmarks": visual_rows,
        "audio_benchmarks": audio_rows,
    }
    out_path = root / "qa" / "perception_benchmark.json"
    write_json_atomic(out_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark CPU perception candidates on Truce vertical-slice assets.")
    ap.add_argument("--episode", type=Path, default=Path("episodes/ep_truce_1914"))
    ap.add_argument("--shots", nargs="+", default=["S08_SH002", "S02_SH008", "S05_SH020"])
    ap.add_argument("--clap", action="store_true", help="Also run optional CLAP audio-text similarity")
    args = ap.parse_args(argv)
    rep = benchmark_episode_slice(args.episode, list(args.shots), run_clap=args.clap)
    print(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
