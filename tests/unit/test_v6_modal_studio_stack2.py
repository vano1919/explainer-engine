"""Unit tests for Stack 2 Modal Cinema Studio, Hybrid Escalation Router, OTIO Exporter, and Drama MVP POC."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.cloud.modal_cinema_studio import (
    EpisodeBudgetGuard,
    build_comfy_latentsync16_graph,
    build_comfy_seedvr2_graph,
    build_comfy_wan22_distilled_graph,
    estimate_modal_job_cost,
)
from explainer_engine.edit.otio_exporter import export_episode_otio
from explainer_engine.episode.mvp_drama_poc import build_stack2_drama_mvp_plan
from explainer_engine.videolane.hybrid_escalation_router import route_drama_shot


def test_episode_budget_guard_enforces_10usd_cap_and_8usd_checkpoint() -> None:
    guard = EpisodeBudgetGuard(episode_id="ep_01", cap_usd=10.00)
    assert guard.checkpoint_usd == 8.00

    r1 = guard.reserve(job_id="j1", category="modal_gpu", provider="L40S", estimated_usd=5.50)
    assert r1["checkpoint_reached"] is False
    r2 = guard.reserve(job_id="j2", category="api_lipsync", provider="sync_3", estimated_usd=3.00)
    assert r2["checkpoint_reached"] is True
    assert guard.remaining_usd == 1.50

    with pytest.raises(RuntimeError, match="hard budget cap exceeded"):
        guard.reserve(job_id="j3", category="api_video", provider="seedance_2_5", estimated_usd=2.00)

    s1 = guard.settle("j1", actual_usd=4.00)
    assert s1["committed_usd"] == 7.00
    assert estimate_modal_job_cost("L40S", 3600.0) > 1.95


def test_comfy_graph_guards_nvfp4_latentsync_pad_and_seedvr2_batch() -> None:
    # Wan 2.2 Low-Noise NVFP4 MUST fail closed
    with pytest.raises(ValueError, match="NVFP4/FP4 on Wan 2.2 Low-Noise"):
        build_comfy_wan22_distilled_graph(
            prompt="Cinematic beach dawn",
            start_image_name="plate.png",
            low_noise_dtype="nvfp4",
        )
    g_wan = build_comfy_wan22_distilled_graph(prompt="Cinematic beach dawn", start_image_name="plate.png")
    assert g_wan["nodes"]["2"]["inputs"]["weight_dtype"] == "fp8_e4m3fn_fast"

    # LatentSync 1.6 MUST enforce >= 0.5s trailing silence
    with pytest.raises(ValueError, match="trailing silence padding"):
        build_comfy_latentsync16_graph(video_name="v.mp4", padded_audio_wav_name="a.wav", tail_silence_s=0.2)
    g_ls = build_comfy_latentsync16_graph(video_name="v.mp4", padded_audio_wav_name="a.wav", tail_silence_s=0.6)
    assert g_ls["nodes"]["3"]["inputs"]["resolution"] == 512

    # SeedVR2 MUST enforce batch_size = 4n+1 >= 5
    with pytest.raises(ValueError, match="batch_size = 4n\\+1 >= 5"):
        build_comfy_seedvr2_graph(input_video_name="v.mp4", batch_size=4)
    g_vr = build_comfy_seedvr2_graph(input_video_name="v.mp4", batch_size=9)
    assert g_vr["nodes"]["2"]["inputs"]["batch_size"] == 9


def test_hybrid_escalation_router_frontal_vs_profile_and_vertical_guard() -> None:
    # Frontal close-up stays on cheap Open Modal (LTX-2.5 A2V + LatentSync 1.6)
    d_front = route_drama_shot(
        {"shot_id": "s1", "duration_s": 5.0, "has_dialogue": True, "shot_scale": "close_up", "face_yaw_deg": 12.0},
        remaining_budget_usd=10.0,
    )
    assert d_front.escalated_to_api is False
    assert d_front.video_engine == "ltx_2_5_a2v_modal"
    assert d_front.lipsync_engine == "latentsync_1_6_modal_l40s"

    # Sharp profile + occlusion surgically escalates ONLY lip-sync to Sync-3 API
    d_prof = route_drama_shot(
        {
            "shot_id": "s2",
            "duration_s": 5.0,
            "has_dialogue": True,
            "shot_scale": "close_up",
            "face_yaw_deg": 55.0,
            "has_mouth_occlusion": True,
        },
        remaining_budget_usd=10.0,
    )
    assert d_prof.escalated_to_api is True
    assert d_prof.lipsync_engine == "sync_3_api_4k"
    assert "profile_yaw=55deg" in d_prof.escalation_reason

    # 9:16 vertical skips Phantom-Wan-14B and routes to LTX-2.5 Native Portrait
    d_vert = route_drama_shot(
        {"shot_id": "s3", "duration_s": 5.0, "aspect_ratio": "9:16", "requested_phantom": True},
        remaining_budget_usd=10.0,
    )
    assert d_vert.video_engine == "ltx_2_5_native_portrait_modal"
    assert any("Phantom-Wan-14B skipped" in w for w in d_vert.warnings)


def test_otio_exporter_and_stack2_mvp_plan(tmp_path: Path) -> None:
    plan = build_stack2_drama_mvp_plan(out_dir=tmp_path, episode_cap_usd=10.00)
    assert plan["budget"]["cap_usd"] == 10.00
    assert plan["budget"]["committed_usd"] < 2.00  # MVP stays well below $3-$5 target!
    assert len(plan["routed_shots"]) == 5

    otio_p = Path(plan["otio_timeline"])
    assert otio_p.is_file()
    data = json.loads(otio_p.read_text(encoding="utf-8"))
    assert data["OTIO_SCHEMA"] == "Timeline.1"
    track_names = [t["name"] for t in data["tracks"]["children"]]
    assert track_names == ["V1_Master", "A1_Dialogue", "A2_Narrator", "A3_Foley_SFX", "A4_Music_Score"]
    assert data["metadata"]["nvenc_av1_safe_export"]["keyframe_interval_frames"] == 1

    # Direct standalone export check
    out2 = export_episode_otio(
        episode_name="direct_test",
        video_shots=[{"shot_id": "v1", "duration_s": 4.0, "video_path": "v1.mp4"}],
        out_otio=tmp_path / "direct.otio",
    )
    assert out2.is_file()
