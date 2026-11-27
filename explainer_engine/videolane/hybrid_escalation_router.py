"""Selective Hybrid Escalation Router (Stack 2: 85-90% Open Modal + 10-15% Surgical API Fallback).

Designed for drama-first episodes & "What If" miniseries (80%+ real dramatic scenes, heavy close-up
dialogue, supporting both 16:9 widescreen and native 9:16 vertical 1080x1920 @ 30fps):
- **Never bans close-ups**: routes frontal/three-quarter dialogue to cheap Modal ``LTX-2.5 A2V`` /
  ``InfiniteTalk`` / ``LatentSync 1.6`` (~$0.05-$0.12/shot), and escalates ONLY hard shots
  (sharp >=40° profile, beard/hand/mic occlusion, 4K hero close-up, or QA retry) to ``Sync-3`` API.
- **Native 9:16 Portrait Protection**: automatically avoids ``Phantom-Wan-14B`` on vertical 9:16
  shots (trained on 24fps horizontal) and routes vertical shots to ``LTX-2.5 Native Portrait`` or
  ``Seedance 2.5`` 9:16.
- **Episode Budget Awareness**: checks remaining USD inside the $10.00 episode cap before authorizing
  any paid API escalation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VALID_ASPECT_RATIOS = frozenset({"16:9", "9:16"})


@dataclass(slots=True)
class ShotRouteDecision:
    shot_id: str
    aspect_ratio: str
    video_engine: str
    lipsync_engine: str | None
    tts_engine: str | None
    escalated_to_api: bool
    escalation_reason: str
    estimated_cost_usd: float
    modal_gpu: str | None
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_drama_shot(
    shot: dict[str, Any],
    *,
    remaining_budget_usd: float = 10.00,
    prefer_elevenlabs_v4: bool = True,
) -> ShotRouteDecision:
    """Route a single dramatic shot across Open Modal (L40S/H100) and surgical API fallback."""
    sid = str(shot.get("shot_id") or "shot_01")
    ar = str(shot.get("aspect_ratio") or "16:9").strip()
    if ar not in VALID_ASPECT_RATIOS:
        raise ValueError(f"Unsupported aspect_ratio {ar!r}; expected one of {sorted(VALID_ASPECT_RATIOS)}")

    dur_s = max(2.0, float(shot.get("duration_s", 5.0)))
    has_dialogue = bool(shot.get("has_dialogue") or shot.get("spoken_line"))
    speaker_count = int(shot.get("speaker_count", 1 if has_dialogue else 0))
    scale = str(shot.get("shot_scale") or "medium").strip().lower().replace("-", "_").replace(" ", "_")
    face_yaw_deg = abs(float(shot.get("face_yaw_deg", 0.0)))
    has_occlusion = bool(shot.get("has_mouth_occlusion", False))
    requires_4k_cu = bool(shot.get("requires_native_4k_closeup", False))
    prior_qa_failed = bool(shot.get("prior_lipsync_qa_failed", False))
    ref_count = int(shot.get("reference_count", 1))
    complexity = str(shot.get("shot_complexity") or "standard").strip().lower()
    is_long_monologue = has_dialogue and dur_s > 15.0

    warnings: list[str] = []
    escalated = False
    reason = "open_modal_default"

    # 1. TTS selection (Voice-First)
    tts_engine: str | None = None
    tts_cost = 0.0
    if has_dialogue:
        if prefer_elevenlabs_v4 and remaining_budget_usd >= 0.50:
            tts_engine = "elevenlabs_v4_turbo"
            tts_cost = 0.015  # ~350 chars @ $0.04/1K
        else:
            tts_engine = "qwen3_tts_modal_l4"
            tts_cost = 0.004

    # 2. Primary Video Engine Selection
    modal_gpu: str | None = "L40S"
    if ar == "9:16":
        if ref_count > 4 and remaining_budget_usd >= 1.20:
            video_engine = "seedance_2_5_api_9x16"
            escalated = True
            reason = f"vertical_multi_ref ({ref_count} refs > 4)"
            vid_cost = round(dur_s * 0.10, 3)
            modal_gpu = None
        else:
            video_engine = "ltx_2_5_native_portrait_modal"
            vid_cost = round(dur_s * 0.016, 3)
            if bool(shot.get("requested_phantom")):
                warnings.append("Phantom-Wan-14B skipped on 9:16 vertical (horizontal-only); routed to LTX-2.5 Native Portrait")
    else:
        if (ref_count > 4 or complexity == "extreme_action") and remaining_budget_usd >= 1.50:
            video_engine = "seedance_2_5_api" if ref_count > 4 else "kling_3_0_omni_api"
            escalated = True
            reason = f"multi_ref_{ref_count}" if ref_count > 4 else "extreme_action_physics"
            vid_cost = round(dur_s * (0.10 if ref_count > 4 else 0.125), 3)
            modal_gpu = None
        elif has_dialogue and speaker_count >= 2:
            video_engine = "multitalk_modal_l40s"
            vid_cost = round(dur_s * 0.018, 3)
        elif is_long_monologue:
            video_engine = "infinitetalk_modal_l40s"
            vid_cost = round(dur_s * 0.018, 3)
            if dur_s > 60.0:
                warnings.append("Disable FusionX LoRA on InfiniteTalk >60s to prevent color drift")
        elif has_dialogue:
            video_engine = "ltx_2_5_a2v_modal"
            vid_cost = round(dur_s * 0.016, 3)
        else:
            video_engine = "wan_2_2_14b_distilled_fp8_modal"
            vid_cost = round(dur_s * 0.010, 3)

    # 3. Lip-Sync Refinement / Surgical Sync-3 Escalation
    lipsync_engine: str | None = None
    ls_cost = 0.0
    if has_dialogue:
        hard_lipsync_trigger = (
            face_yaw_deg >= 40.0
            or has_occlusion
            or requires_4k_cu
            or prior_qa_failed
        )
        if hard_lipsync_trigger and remaining_budget_usd >= (vid_cost + tts_cost + 0.60):
            lipsync_engine = "sync_3_api_4k"
            ls_cost = round(dur_s * 0.09, 3)
            escalated = True
            triggers = []
            if face_yaw_deg >= 40.0:
                triggers.append(f"profile_yaw={face_yaw_deg:.0f}deg")
            if has_occlusion:
                triggers.append("mouth_occlusion")
            if requires_4k_cu:
                triggers.append("native_4k_closeup")
            if prior_qa_failed:
                triggers.append("prior_qa_retry")
            reason = "sync3_escalation:" + "+".join(triggers)
        elif scale in {"close_up", "extreme_close_up", "medium_close_up"} or face_yaw_deg <= 35.0:
            lipsync_engine = "latentsync_1_6_modal_l40s"
            ls_cost = round(dur_s * 0.012, 3)

    total_est = round(vid_cost + tts_cost + ls_cost, 4)
    return ShotRouteDecision(
        shot_id=sid,
        aspect_ratio=ar,
        video_engine=video_engine,
        lipsync_engine=lipsync_engine,
        tts_engine=tts_engine,
        escalated_to_api=escalated,
        escalation_reason=reason,
        estimated_cost_usd=total_est,
        modal_gpu=modal_gpu,
        warnings=warnings,
    )


__all__ = ["ShotRouteDecision", "VALID_ASPECT_RATIOS", "route_drama_shot"]
