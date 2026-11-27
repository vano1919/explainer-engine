"""Minimal $3-$5 Stack-2 Dramatic Dialogue MVP/POC Planner & Stress-Test Builder.

Builds a deterministic, zero-waste 25-second dramatic dialogue POC (2 characters, 16:9 master +
9:16 vertical teaser) under the $10.00 episode cap, combining:
- 3x3 Contact Sheet keyframe plan (zero chopped low-res sub-crops)
- Voice-First TTS + Modal LTX-2.5 / Wan 2.2 / LatentSync 1.6 + surgical Sync-3 escalation on 1 profile close-up
- Mandatory 6-shot Lip-Sync QA Stress-Test checklist
- OpenTimelineIO (.otio) timeline export for free DaVinci Resolve / Kdenlive
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from explainer_engine.cloud.modal_cinema_studio import EpisodeBudgetGuard, generate_modal_app_spec
from explainer_engine.edit.otio_exporter import export_episode_otio
from explainer_engine.videolane.hybrid_escalation_router import route_drama_shot


def build_stack2_drama_mvp_plan(
    *,
    episode_id: str = "whatif_island_mvp_01",
    out_dir: Path,
    episode_cap_usd: float = 10.00,
) -> dict[str, Any]:
    """Compile the complete $3-$5 Stack-2 MVP/POC execution manifest and .otio timeline."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    guard = EpisodeBudgetGuard(episode_id=episode_id, cap_usd=episode_cap_usd)

    raw_shots = [
        {
            "shot_id": "s01_beach_establish_narr",
            "scene_id": "S01_COVE",
            "duration_s": 5.0,
            "aspect_ratio": "16:9",
            "shot_scale": "wide",
            "has_dialogue": False,
            "video_path": "renders/s01_beach_establish_narr.mp4",
        },
        {
            "shot_id": "s02_char_a_closeup_frontal_dlg",
            "scene_id": "S01_COVE",
            "duration_s": 5.5,
            "aspect_ratio": "16:9",
            "shot_scale": "close_up",
            "has_dialogue": True,
            "face_yaw_deg": 10.0,
            "has_mouth_occlusion": False,
            "video_path": "renders/s02_char_a_closeup_frontal_dlg.mp4",
        },
        {
            "shot_id": "s03_char_b_profile_beard_dlg",
            "scene_id": "S01_COVE",
            "duration_s": 5.0,
            "aspect_ratio": "16:9",
            "shot_scale": "close_up",
            "has_dialogue": True,
            "face_yaw_deg": 55.0,
            "has_mouth_occlusion": True,
            "video_path": "renders/s03_char_b_profile_beard_dlg.mp4",
        },
        {
            "shot_id": "s04_two_shot_confrontation_dlg",
            "scene_id": "S01_COVE",
            "duration_s": 5.0,
            "aspect_ratio": "16:9",
            "shot_scale": "medium",
            "has_dialogue": True,
            "speaker_count": 2,
            "face_yaw_deg": 20.0,
            "video_path": "renders/s04_two_shot_confrontation_dlg.mp4",
        },
        {
            "shot_id": "s05_vertical_teaser_9x16_dlg",
            "scene_id": "S01_COVE",
            "duration_s": 4.5,
            "aspect_ratio": "9:16",
            "shot_scale": "medium_close_up",
            "has_dialogue": True,
            "face_yaw_deg": 15.0,
            "requested_phantom": True,
            "video_path": "renders/s05_vertical_teaser_9x16_dlg.mp4",
        },
    ]

    routed: list[dict[str, Any]] = []
    for sh in raw_shots:
        dec = route_drama_shot(sh, remaining_budget_usd=guard.remaining_usd)
        guard.reserve(
            job_id=dec.shot_id,
            category="api_lipsync" if dec.escalated_to_api else "modal_gpu",
            provider=dec.lipsync_engine or dec.video_engine,
            estimated_usd=dec.estimated_cost_usd,
        )
        routed.append({**sh, **dec.to_dict()})

    otio_path = export_episode_otio(
        episode_name=episode_id,
        video_shots=[r for r in routed if r["aspect_ratio"] == "16:9"],
        out_otio=out_dir / f"{episode_id}.otio",
        dialogue_stems=[
            {
                "shot_id": "s02_char_a_closeup_frontal_dlg",
                "audio_path": "audio/s02_char_a_dlg.wav",
                "start_s": 5.0,
                "duration_s": 5.5,
                "j_cut_prelap_s": 0.35,
            },
            {
                "shot_id": "s03_char_b_profile_beard_dlg",
                "audio_path": "audio/s03_char_b_dlg.wav",
                "start_s": 10.5,
                "duration_s": 5.0,
                "l_cut_postlap_s": 0.30,
            },
        ],
        narrator_stems=[
            {"shot_id": "s01_narr", "audio_path": "audio/narr_intro.wav", "start_s": 0.4, "duration_s": 4.2},
        ],
        foley_stems=[
            {"shot_id": "surf_bed", "audio_path": "audio/foley_waves.wav", "start_s": 0.0, "duration_s": 20.5},
        ],
        music_stems=[
            {"shot_id": "score_01", "audio_path": "audio/acestep_tension.wav", "start_s": 0.0, "duration_s": 20.5, "gain_db": -18.0},
        ],
        fps=24.0,
        aspect_ratio="16:9",
    )

    manifest = {
        "schema": "stack2_drama_mvp_plan/1",
        "episode_id": episode_id,
        "modal_studio": generate_modal_app_spec(episode_cap_usd=episode_cap_usd),
        "budget": guard.summary(),
        "routed_shots": routed,
        "otio_timeline": str(otio_path),
        "mandatory_6shot_lipsync_qa": [
            "1. Frontal close-up real-speed + muted frame-by-frame teeth check",
            "2. Head turn 0->45->90 deg profile continuity",
            "3. Plosives (P/B/M) with visible teeth & >=0.5s audio tail silence",
            "4. Beard/mustache jaw-line stability",
            "5. Hand/prop occlusion across mouth (Sync-3 escalation verified)",
            "6. Two-speaker shot (MultiTalk Label RoPE speaker isolation)",
        ],
    }
    (out_dir / f"{episode_id}_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


__all__ = ["build_stack2_drama_mvp_plan"]
