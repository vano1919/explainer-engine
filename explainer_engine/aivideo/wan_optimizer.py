"""Gate G6/G7 3-Layer Visual & Audio Routing Orchestrator & Multi-Factor Zero-Cost Policy Engine (D-130 / v4.2).

Implements the Creator's unified v4.2 Visual & Audio Routing Architecture and Zero-Additional-Cost Policy:
1. 10% Info-Graphics, Tactical Maps, Troop Movements, Diagrams & Counters (`TACTILE_MAP` / `map_visualization`):
   - Routed to `PYTHON_INFO_GRAPHICS_RENDER` (`explainer_engine/infographics/python_map_and_chart_engine.py`).
   - Built deterministically in Python (24fps 1080p/2K MP4) in clean YouTube-docudrama style so numbers,
     troop movement vectors, and territorial areas are 100% accurate and never garbled by AI.
2. 30% Cinematic Image Animation (`COLLAGE_STILL` / `STILL_25D`):
   - Reuses existing high-quality generated images (`Reference_Library` and episode keyframes).
   - Under `zero_additional_cost_policy=True` (default when `verified_free_gemini_video_quota == 0`), routes
     to `PYTHON_25D_PARALLAX_ANIMATOR` (`explainer_engine/production/cinematic_image_animator.py`) at $0.00 cost.
   - Only uses `GOOGLE_VIDEO_API_ENGINE` (`gemini-omni-1.2-flash`) when a verified free quota exists or paid API is explicitly approved.
3. 60% Video Generation & Multi-Factor Complexity Router (`compute_multifactor_shot_routing`):
   - Never routes by duration alone! Evaluates 10 explicit factors:
     (1) motion complexity, (2) interacting character count, (3) camera movement complexity,
     (4) physical interactions, (5) environmental complexity, (6) continuity requirements (`FLF2V`, `frame[-5]`, `WAN_CONTROL`, `WAN_S2V`),
     (7) available reusable source images, (8) provider capability, (9) verified free quota / authorized credit balance,
     and (10) estimated cost under the Zero-Additional-Cost Policy.
4. Character Speech Routing Rule (`VC-T1-04` — `analyze_character_appearance_cadence`):
   - 1-scene or widely-spaced characters (`segment_gap >= 3`) route to `WAN_S2V_CHARACTER_SPEECH`.
   - Recurring characters across nearby scenes route to `ELEVENLABS_VOICE_SPINE`.
   - Narrator (`narrator_main`) uses locked ElevenLabs voice `'Odom - Deep, Resonant, Dramatic'` (`CcSJ2r3qw0XU9gJpEPyk`).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from explainer_engine.core.model_lifecycle_guard import ACTIVE_CANONICAL_MODELS, assert_active_model
from explainer_engine.infographics.python_map_and_chart_engine import classify_10pct_infographic_subtype

WAN_FPS = 24
WAN_SWEET_SPOT_SEC = 3.8
WAN_HARD_MAX_SEC = 5.0
WAN_ALLOWED_FRAME_COUNTS = (33, 49, 65, 81, 97, 113, 121)
CONTINUATION_OFFSET_FROM_END = 5  # Extract frame[-5] ONLY when chaining a continuous video take > 5.0s
WAN_SPEECH_MIN_SEGMENT_GAP = 3    # >= 3 segments apart -> route character speech to Wan

LOCKED_NARRATOR_VOICE_ID = "CcSJ2r3qw0XU9gJpEPyk"  # Odom - Deep, Resonant, Dramatic (valid for 730 days)
FALLBACK_NARRATOR_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ACTIVE_GOOGLE_VIDEO_MODEL = ACTIVE_CANONICAL_MODELS["g7_google_video_api"]

HIGH_MOTION_KEYWORDS = (
    "battle", "charge", "cavalry", "explosion", "erupt", "collapse", "fight", "clash",
    "sprint", "run", "panic", "flee", "storm", "shockwave", "bayonet", "salvo", "pyroclastic",
)
PHYSICAL_INTERACTION_KEYWORDS = (
    "strike", "clash", "grab", "throw", "fire", "load", "breach", "shatter", "collide",
    "embrace", "hand", "duel", "march", "gallop", "carry",
)
COMPLEX_ENVIRONMENT_KEYWORDS = (
    "volcano", "ash cloud", "pyroclastic", "thunderstorm", "blizzard", "sea storm",
    "burning city", "battlefield smoke", "avalanch", "flood",
)


def seconds_to_wan_frames(seconds: float, fps: int = WAN_FPS) -> int:
    """Snap a single Wan sub-clip duration (<= 5.0s) to the nearest valid `4k + 1` frame count."""
    clamped = max(1.4, min(float(seconds), WAN_HARD_MAX_SEC))
    raw_frames = int(round(clamped * fps))
    return min(WAN_ALLOWED_FRAME_COUNTS, key=lambda f: abs(f - raw_frames))


def evaluate_zero_cost_allowance_and_policy(
    verified_free_gemini_video_clips: int = 0,
    authorized_wan_credit_usd: float = 0.0,
    allow_paid_api_fallback: bool = False,
) -> Dict[str, Any]:
    """Verify free-tier vs. funded-credit vs. local zero-cost status (Section 5 Cost Policy).

    Official Google AI Studio / Gemini API pricing note:
    Standard Gemini API free tier covers text/multimodal reasoning tokens, NOT paid video generation
    endpoints (Veo / video generation bills per second unless an explicit promotional free clip quota is granted).
    Therefore `gemini_video_free_tier_default` is False unless `verified_free_gemini_video_clips > 0`.
    """
    return {
        "zero_additional_cost_enforced": not allow_paid_api_fallback,
        "gemini_video_free_tier_default": False,
        "verified_free_gemini_video_clips_remaining": max(0, int(verified_free_gemini_video_clips)),
        "authorized_wan_credit_usd_remaining": round(max(0.0, float(authorized_wan_credit_usd)), 4),
        "allow_paid_api_fallback": bool(allow_paid_api_fallback),
        "local_python_infographics_cost_usd": 0.0,
        "local_python_25d_animation_cost_usd": 0.0,
        "local_procedural_audio_cost_usd": 0.0,
    }


def compute_multifactor_shot_routing(
    shot: Dict[str, Any],
    available_reusable_images: List[str] | None = None,
    verified_free_gemini_video_clips: int = 0,
    authorized_wan_credit_usd: float = 0.0,
    allow_paid_api_fallback: bool = False,
) -> Dict[str, Any]:
    """Multi-factor shot complexity and cost-aware router (Section 4 & 5).

    Never routes by duration alone! Scores 10 factors:
    1. required_motion_complexity (0.0..1.0)
    2. interacting_character_count
    3. camera_movement_complexity (0.0..1.0)
    4. physical_interaction_score (0.0..1.0)
    5. environmental_complexity_score (0.0..1.0)
    6. character_continuity_requirement
    7. available_source_image_reused
    8. provider_capability
    9. verified_free_or_credit_status
    10. estimated_cost_usd & cost_classification
    """
    sid = str(shot.get("shot_id") or "S01_SH001")
    dur = float(shot.get("target_duration_seconds", 3.8))
    vtype = str(shot.get("visual_type") or "cinematic_video")
    gmode = str(shot.get("generation_mode") or "WAN_I2V")
    chars = list(shot.get("character_ids") or [])
    cam_move = str((shot.get("camera_spec") or {}).get("camera_move") or "static")
    needs_end = bool((shot.get("keyframe_plan") or {}).get("needs_end_frame"))
    has_control = gmode == "WAN_CONTROL" or shot.get("selective_control") is not None

    text_blob = " ".join([
        str(shot.get("narrative_purpose") or ""),
        str(shot.get("action_start_state") or ""),
        str(shot.get("action_end_state") or ""),
        str((shot.get("video_prompt") or {}).get("motion_prompt") or ""),
    ]).lower()

    # 1. Motion complexity
    high_motion_hits = sum(1 for k in HIGH_MOTION_KEYWORDS if k in text_blob)
    phys_hits = sum(1 for k in PHYSICAL_INTERACTION_KEYWORDS if k in text_blob)
    env_hits = sum(1 for k in COMPLEX_ENVIRONMENT_KEYWORDS if k in text_blob)
    cam_complex = 0.85 if cam_move in ("tracking_shot", "parallax_orbital") else (0.45 if cam_move != "static" else 0.15)
    char_factor = min(1.0, len(chars) * 0.35)

    motion_complexity_score = round(
        min(
            1.0,
            0.25 * min(1.0, high_motion_hits / 2.0)
            + 0.25 * min(1.0, phys_hits / 2.0)
            + 0.15 * min(1.0, env_hits / 2.0)
            + 0.20 * cam_complex
            + 0.15 * char_factor
            + (0.20 if needs_end or has_control else 0.0),
        ),
        3,
    )

    reusable_match = None
    if available_reusable_images:
        reusable_match = available_reusable_images[hash(sid) % len(available_reusable_images)]

    # Route 0: Cold-Open Teaser Reuse (teaser_of) -> Zero new generation, reuses later payoff clip!
    if shot.get("teaser_of"):
        return {
            "shot_id": sid,
            "layer": "COLD_OPEN_TEASER_REUSE",
            "selected_engine": "REUSE_TEASER_OF_PAYOFF_CLIP",
            "planned_cloud_engine": "REUSE_TEASER_OF_PAYOFF_CLIP",
            "fallback_engine": "REUSE_TEASER_OF_PAYOFF_CLIP",
            "teaser_of": shot.get("teaser_of"),
            "teaser_trim": shot.get("teaser_trim"),
            "requires_new_generation": False,
            "routed_by_duration_only": False,
            "factors": {
                "motion_complexity_score": motion_complexity_score,
                "interacting_character_count": len(chars),
                "camera_movement": cam_move,
                "physical_interactions": phys_hits > 0,
                "environmental_complexity": env_hits > 0,
                "continuity_requirements": {"needs_end_frame": needs_end, "has_control": has_control, "teaser_of": shot.get("teaser_of")},
                "reused_source_image": shot.get("teaser_of"),
            },
            "cost_classification": "LOCAL_ZERO_COST",
            "estimated_cost_usd": 0.0,
            "paid_api_invoked": False,
        }

    # Route 1: 10% Data-Driven Infographics -> Always Python
    if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
        return {
            "shot_id": sid,
            "layer": "10PCT_DATA_INFOGRAPHIC",
            "selected_engine": "PYTHON_INFO_GRAPHICS_RENDER",
            "fallback_engine": "PYTHON_INFO_GRAPHICS_RENDER",
            "routed_by_duration_only": False,
            "factors": {
                "motion_complexity_score": motion_complexity_score,
                "interacting_character_count": len(chars),
                "camera_movement": cam_move,
                "physical_interactions": phys_hits > 0,
                "environmental_complexity": env_hits > 0,
                "continuity_requirements": {"needs_end_frame": needs_end, "has_control": has_control},
                "reused_source_image": reusable_match,
            },
            "cost_classification": "LOCAL_ZERO_COST",
            "estimated_cost_usd": 0.0,
            "paid_api_invoked": False,
        }

    # Route 2: 30% Composed Illustration / Collage Still -> Python 2.5D Animator default, or Verified Free Gemini Video
    if vtype == "composed_illustration" or gmode in ("COLLAGE_STILL", "STILL_25D"):
        if verified_free_gemini_video_clips > 0:
            engine = "GEMINI_FREE_TIER_VIDEO_I2V"
            cost_class = "COVERED_BY_FREE_ALLOWANCE"
        else:
            engine = "PYTHON_25D_PARALLAX_ANIMATOR"
            cost_class = "LOCAL_ZERO_COST"
        return {
            "shot_id": sid,
            "layer": "30PCT_CINEMATIC_IMAGE_ANIMATION",
            "selected_engine": engine,
            "fallback_engine": "PYTHON_25D_PARALLAX_ANIMATOR",
            "routed_by_duration_only": False,
            "factors": {
                "motion_complexity_score": motion_complexity_score,
                "interacting_character_count": len(chars),
                "camera_movement": cam_move,
                "physical_interactions": phys_hits > 0,
                "environmental_complexity": env_hits > 0,
                "continuity_requirements": {"needs_end_frame": needs_end, "has_control": has_control},
                "reused_source_image": reusable_match,
            },
            "cost_classification": cost_class,
            "estimated_cost_usd": 0.0,
            "paid_api_invoked": False,
        }

    # Route 3: 60% Cinematic Video -> Multi-factor complexity + Zero-Additional-Cost evaluation
    needs_wan_heavy = (
        motion_complexity_score >= 0.45
        or len(chars) >= 2
        or phys_hits >= 1
        or needs_end
        or has_control
        or dur > WAN_HARD_MAX_SEC
    )
    est_wan_cost = round(0.035 * max(1, (2 if dur > WAN_HARD_MAX_SEC else 1)), 4)

    if needs_wan_heavy:
        if authorized_wan_credit_usd >= est_wan_cost:
            selected = "WAN_2_1_HEAVY_ACTION_ENGINE"
            cost_class = "COVERED_BY_AUTHORIZED_CREDIT_BALANCE"
            est_cost = 0.0  # covered by pre-existing authorized credit balance, $0 additional out-of-pocket charge
        elif allow_paid_api_fallback:
            selected = "WAN_2_1_HEAVY_ACTION_ENGINE"
            cost_class = "PAID_APPROVED"
            est_cost = est_wan_cost
        else:
            # Zero-additional-cost local execution mode: plan Wan spec + render local 2.5D high-motion proxy without charging card
            selected = "PYTHON_25D_PARALLAX_ANIMATOR_ZERO_COST_FALLBACK"
            cost_class = "LOCAL_ZERO_COST"
            est_cost = 0.0
    else:
        if verified_free_gemini_video_clips > 0:
            selected = "GEMINI_FREE_TIER_VIDEO_I2V"
            cost_class = "COVERED_BY_FREE_ALLOWANCE"
            est_cost = 0.0
        elif authorized_wan_credit_usd >= est_wan_cost:
            selected = "WAN_2_1_SINGLE_I2V_COVERED"
            cost_class = "COVERED_BY_AUTHORIZED_CREDIT_BALANCE"
            est_cost = 0.0
        else:
            selected = "PYTHON_25D_PARALLAX_ANIMATOR"
            cost_class = "LOCAL_ZERO_COST"
            est_cost = 0.0

    return {
        "shot_id": sid,
        "layer": "60PCT_CINEMATIC_VIDEO",
        "selected_engine": selected,
        "planned_cloud_engine": "WAN_2_1_HEAVY_ACTION_ENGINE" if needs_wan_heavy else "GEMINI_VIDEO_API_BATCH",
        "fallback_engine": "PYTHON_25D_PARALLAX_ANIMATOR",
        "routed_by_duration_only": False,
        "factors": {
            "motion_complexity_score": motion_complexity_score,
            "interacting_character_count": len(chars),
            "camera_movement": cam_move,
            "physical_interactions": phys_hits > 0,
            "environmental_complexity": env_hits > 0,
            "continuity_requirements": {
                "needs_end_frame": needs_end,
                "has_control": has_control,
                "requires_frame_minus_5_chain": dur > WAN_HARD_MAX_SEC,
            },
            "reused_source_image": reusable_match,
        },
        "cost_classification": cost_class,
        "estimated_cost_usd": est_cost,
        "paid_api_invoked": bool(allow_paid_api_fallback and est_cost > 0),
    }


def analyze_character_appearance_cadence(audio_lines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Analyze every character's speaking segments to decide between `WAN_S2V_CHARACTER_SPEECH`
    (for 1-scene or widely-spaced characters with gap >= 3 segments) and `ELEVENLABS_VOICE_SPINE`
    (for recurring characters across nearby scenes)."""
    by_char: Dict[str, List[int]] = {}
    for ln in audio_lines:
        if ln.get("speaker_type") != "character":
            continue
        spk = str(ln.get("speaker_id") or "")
        seg_str = str(ln.get("segment_id") or "S01")
        try:
            seg_num = int("".join(ch for ch in seg_str if ch.isdigit()) or "1")
        except ValueError:
            seg_num = 1
        by_char.setdefault(spk, []).append(seg_num)

    cadence_map: Dict[str, Dict[str, Any]] = {}
    for spk, seg_nums in by_char.items():
        unique_segs = sorted(set(seg_nums))
        total_lines = len(seg_nums)
        if len(unique_segs) <= 1:
            max_gap = 0
            use_wan_speech = True
            reason = f"Character {spk} speaks in only 1 segment (S{unique_segs[0]:02d}); routed to Wan native speech (VC-T1-04)"
        else:
            gaps = [b - a for a, b in zip(unique_segs, unique_segs[1:])]
            max_gap = max(gaps)
            if max_gap >= WAN_SPEECH_MIN_SEGMENT_GAP or (len(unique_segs) == 2 and unique_segs[1] - unique_segs[0] == 1 and total_lines <= 3):
                use_wan_speech = True
                reason = (
                    f"Character {spk} has isolated/distant appearances (segments={unique_segs}, max_gap={max_gap}, lines={total_lines}); "
                    "routed to Wan native speech (VC-T1-04)"
                )
            else:
                use_wan_speech = False
                reason = (
                    f"Character {spk} recurs across {len(unique_segs)} close segments ({unique_segs}, max_gap={max_gap}); "
                    "routed to ElevenLabs locked voice profile for cross-scene timbre consistency"
                )
        cadence_map[spk] = {
            "speaker_id": spk,
            "unique_segments": [f"S{n:02d}" for n in unique_segs],
            "unique_segments_count": len(unique_segs),
            "total_lines": total_lines,
            "max_segment_gap": max_gap,
            "use_wan_speech": use_wan_speech,
            "speech_engine": "WAN_S2V_CHARACTER_SPEECH" if use_wan_speech else "ELEVENLABS_VOICE_SPINE",
            "reason": reason,
        }
    return cadence_map


def plan_story_driven_shot_render(shot: Dict[str, Any], fps: int = WAN_FPS) -> Dict[str, Any]:
    """Translate a story-driven shot duration (1.2s to 10.0s) into its exact render specification."""
    dur = float(shot.get("target_duration_seconds", 3.8))
    gmode = shot.get("generation_mode", "WAN_I2V")
    vtype = shot.get("visual_type", "cinematic_video")

    if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
        return {
            "shot_id": shot.get("shot_id"),
            "story_duration_sec": dur,
            "render_category": "PYTHON_INFO_GRAPHICS_RENDER",
            "requires_frame_minus_5_chain": False,
            "sub_clips": [{
                "clip_index": 0,
                "duration_sec": dur,
                "frames": int(round(dur * fps)),
                "animation_mode": "python_youtube_infographic_24fps",
                "infographic_subtype": classify_10pct_infographic_subtype(shot),
                "parallax_preset": (shot.get("video_prompt") or {}).get("parallax_preset") or "zoom_focus",
            }],
        }

    if vtype == "composed_illustration" or gmode in ("COLLAGE_STILL", "STILL_25D"):
        return {
            "shot_id": shot.get("shot_id"),
            "story_duration_sec": dur,
            "render_category": "GOOGLE_VIDEO_COLLAGE_ANIMATION",
            "zero_cost_local_engine": "PYTHON_25D_PARALLAX_ANIMATOR",
            "requires_frame_minus_5_chain": False,
            "sub_clips": [{
                "clip_index": 0,
                "duration_sec": dur,
                "frames": int(round(dur * fps)),
                "animation_mode": "python_25d_or_verified_free_gemini_24fps",
                "model": assert_active_model(ACTIVE_GOOGLE_VIDEO_MODEL),
                "parallax_preset": (shot.get("video_prompt") or {}).get("parallax_preset") or "dolly_in",
            }],
        }

    if dur <= WAN_HARD_MAX_SEC:
        return {
            "shot_id": shot.get("shot_id"),
            "story_duration_sec": dur,
            "render_category": "SINGLE_VIDEO_TAKE",
            "requires_frame_minus_5_chain": False,
            "sub_clips": [{"clip_index": 0, "duration_sec": dur, "wan_frames": seconds_to_wan_frames(dur, fps=fps)}],
        }

    clip_a_frames = 113  # 4.71s
    overlap_sec = CONTINUATION_OFFSET_FROM_END / fps
    rem_sec = max(1.5, dur - (clip_a_frames / fps) + overlap_sec)
    clip_b_frames = seconds_to_wan_frames(rem_sec, fps=fps)
    splice_spec = compute_continuation_splice_spec(clip_a_frames, clip_b_frames, offset_from_end=CONTINUATION_OFFSET_FROM_END, fps=fps)
    return {
        "shot_id": shot.get("shot_id"),
        "story_duration_sec": dur,
        "render_category": "WAN_CHAIN_MINUS_5_OVERLAP",
        "requires_frame_minus_5_chain": True,
        "splice_spec": splice_spec,
        "sub_clips": [
            {"clip_index": 0, "wan_frames": clip_a_frames, "role": "primary_take"},
            {"clip_index": 1, "wan_frames": clip_b_frames, "role": "frame_minus_5_continuation"},
        ],
    }


def evaluate_dialogue_render_route(
    audio_line: Dict[str, Any],
    shot: Dict[str, Any],
    modal_gpu_sec_cost_usd: float = 0.0008,
    cadence_info: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Decide whether a character dialogue turn uses Wan native speech/lip-sync or ElevenLabs + multi-cut."""
    dur = float(audio_line.get("estimated_duration_seconds", 3.8))
    is_char = audio_line.get("speaker_type") == "character"
    shot_size = (shot.get("camera_spec") or {}).get("shot_size", "medium_wide")

    gemini_img_cost_usd = 0.039
    num_standard_cuts = max(1, int(round(dur / 3.0)))
    multi_cut_cost_usd = round(num_standard_cuts * (gemini_img_cost_usd + 42.0 * modal_gpu_sec_cost_usd), 4)
    lipsync_pass_cost_usd = round(gemini_img_cost_usd + (dur * 14.0 + 25.0) * modal_gpu_sec_cost_usd, 4)

    wan_by_cadence = bool(is_char and cadence_info and cadence_info.get("use_wan_speech"))
    wan_by_monologue = bool(
        is_char
        and dur >= 8.0
        and shot_size in ("medium_close_up", "close_up")
        and lipsync_pass_cost_usd <= multi_cut_cost_usd * 0.85
    )
    qualifies = wan_by_cadence or wan_by_monologue

    return {
        "line_id": audio_line.get("line_id"),
        "shot_id": shot.get("shot_id"),
        "speaker_id": audio_line.get("speaker_id"),
        "duration_sec": dur,
        "use_rendered_lipsync": qualifies,
        "speech_generation_engine": "WAN_S2V_CHARACTER_SPEECH" if qualifies else "ELEVENLABS_VOICE_SPINE",
        "recommended_mode": (
            "WAN_S2V_LIPSYNC"
            if qualifies
            else ("WAN_FLF2V" if shot.get("keyframe_plan", {}).get("needs_end_frame") else "WAN_I2V")
        ),
        "multi_cut_cost_usd": multi_cut_cost_usd,
        "lipsync_pass_cost_usd": lipsync_pass_cost_usd,
        "savings_ratio": round(1.0 - (lipsync_pass_cost_usd / max(multi_cut_cost_usd, 1e-6)), 3),
        "reason": (
            cadence_info["reason"]
            if wan_by_cadence and cadence_info
            else (
                "Long MCU monologue (>=8s) where single lip-sync pass saves >=15% GPU cost"
                if wan_by_monologue
                else "Recurring character in short turn (<8s): ElevenLabs voice spine + cinematic cut"
            )
        ),
    }


def plan_parallel_g7_threads(
    script_doc: Dict[str, Any],
    google_test_medium_complexity: bool = True,
    verified_free_gemini_video_clips: int = 0,
    authorized_wan_credit_usd: float = 0.0,
    allow_paid_api_fallback: bool = False,
) -> Dict[str, Any]:
    """Partition an approved script into the Creator's 3-Layer Visual Routing Plan (D-130)
    with full multi-factor scoring and Zero-Additional-Cost policy enforcement."""
    active_google_vid = assert_active_model(ACTIVE_GOOGLE_VIDEO_MODEL)
    audio_lines = script_doc.get("audio_lines", [])
    audio_map = {l["line_id"]: l for l in audio_lines if l.get("line_id")}
    cadence_map = analyze_character_appearance_cadence(audio_lines)
    cost_policy = evaluate_zero_cost_allowance_and_policy(
        verified_free_gemini_video_clips=verified_free_gemini_video_clips,
        authorized_wan_credit_usd=authorized_wan_credit_usd,
        allow_paid_api_fallback=allow_paid_api_fallback,
    )

    thread_a_10pct_maps: List[Dict[str, Any]] = []
    thread_a_30pct_animated_collage: List[Dict[str, Any]] = []
    thread_b_gemini_video_simple: List[Dict[str, Any]] = []
    thread_b_wan_complex: List[Dict[str, Any]] = []

    for sh in script_doc.get("shots", []):
        sid = sh["shot_id"]
        dur = float(sh.get("target_duration_seconds", 3.8))
        vtype = sh.get("visual_type", "cinematic_video")
        gmode = sh.get("generation_mode", "WAN_I2V")
        al_ids = sh.get("audio_line_ids") or []
        spoken_txt = " ".join(str(audio_map[lid].get("text", "")) for lid in al_ids if lid in audio_map)

        mf_route = compute_multifactor_shot_routing(
            sh,
            verified_free_gemini_video_clips=verified_free_gemini_video_clips,
            authorized_wan_credit_usd=authorized_wan_credit_usd,
            allow_paid_api_fallback=allow_paid_api_fallback,
        )

        if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
            thread_a_10pct_maps.append({
                "shot_id": sid,
                "segment_id": sh["segment_id"],
                "duration_sec": dur,
                "engine": "PYTHON_INFO_GRAPHICS_RENDER",
                "infographic_subtype": classify_10pct_infographic_subtype(sh, spoken_text=spoken_txt),
                "style_contract": "youtube_docudrama_clean_infographic",
                "parallax_preset": (sh.get("video_prompt") or {}).get("parallax_preset", "zoom_focus"),
                "motion_prompt": (sh.get("video_prompt") or {}).get("motion_prompt", ""),
                "multifactor_routing": mf_route,
            })
        elif vtype == "composed_illustration" or gmode in ("COLLAGE_STILL", "STILL_25D"):
            thread_a_30pct_animated_collage.append({
                "shot_id": sid,
                "segment_id": sh["segment_id"],
                "duration_sec": dur,
                "engine": "GEMINI_LIGHT_VIDEO_I2V",
                "zero_cost_default_engine": "PYTHON_25D_PARALLAX_ANIMATOR",
                "active_execution_engine": mf_route["selected_engine"],
                "model": active_google_vid,
                "style_contract": "unified_cinematic_chiaroscuro",
                "light_motion_type": "multi_plane_depth_and_atmospheric_motion",
                "animation_layers": ["python_25d_parallax", "chiaroscuro_firelight_pulse", "atmospheric_ash_particles"],
                "parallax_preset": (sh.get("video_prompt") or {}).get("parallax_preset", "dolly_in"),
                "motion_prompt": (sh.get("video_prompt") or {}).get("motion_prompt", ""),
                "multifactor_routing": mf_route,
            })
        else:
            al = audio_map.get(al_ids[0], {}) if al_ids else {}
            spk_id = str(al.get("speaker_id") or "")
            dial_eval = evaluate_dialogue_render_route(al, sh, cadence_info=cadence_map.get(spk_id))
            render_plan = plan_story_driven_shot_render(sh)

            needs_end = bool((sh.get("keyframe_plan") or {}).get("needs_end_frame"))
            has_control = gmode == "WAN_CONTROL" or sh.get("selective_control") is not None
            has_overlap_chain = render_plan["requires_frame_minus_5_chain"]
            uses_wan_speech = dial_eval["use_rendered_lipsync"]

            # Multi-factor complexity check (not duration alone!)
            high_motion = mf_route["factors"]["motion_complexity_score"] >= 0.55 or mf_route["factors"]["physical_interactions"]
            is_heavy_wan = (
                has_overlap_chain
                or has_control
                or uses_wan_speech
                or (needs_end and not google_test_medium_complexity)
                or (high_motion and not google_test_medium_complexity)
            )

            job_entry = {
                "shot_id": sid,
                "segment_id": sh["segment_id"],
                "story_duration_sec": dur,
                "duration_sec": min(dur, WAN_HARD_MAX_SEC),
                "wan_frames": seconds_to_wan_frames(dur),
                "video_engine": "WAN_2_1_HEAVY_ACTION_ENGINE" if is_heavy_wan else "GEMINI_VIDEO_API_BATCH",
                "zero_cost_execution_engine": mf_route["selected_engine"],
                "model": "fal-ai/wan-flf2v" if (is_heavy_wan and needs_end) else ("fal-ai/wan-i2v" if is_heavy_wan else active_google_vid),
                "wan_complexity_tier": (
                    "WAN_2_1_COMPLEX_OVERLAP_FLF2V"
                    if is_heavy_wan
                    else ("GOOGLE_VIDEO_MEDIUM_TEST" if needs_end else "GOOGLE_VIDEO_SIMPLE_I2V")
                ),
                "requires_frame_minus_5_chain": has_overlap_chain,
                "needs_end_frame_flf2v": needs_end,
                "has_controlnet": has_control,
                "sub_clips": render_plan["sub_clips"],
                "wan_mode": dial_eval["recommended_mode"],
                "use_rendered_lipsync": uses_wan_speech,
                "speech_generation_engine": dial_eval["speech_generation_engine"],
                "dialogue_cost_eval": dial_eval,
                "multifactor_routing": mf_route,
                "motion_prompt": (sh.get("video_prompt") or {}).get("motion_prompt", ""),
            }
            if is_heavy_wan:
                thread_b_wan_complex.append(job_entry)
            else:
                thread_b_gemini_video_simple.append(job_entry)

    all_b_jobs = thread_b_gemini_video_simple + thread_b_wan_complex
    return {
        "schema": "g7_parallel_execution_plan/2",
        "episode_id": script_doc.get("episode_id", "unknown"),
        "cost_policy": cost_policy,
        "narrator_voice": {
            "voice_id": LOCKED_NARRATOR_VOICE_ID,
            "name": "Odom - Deep, Resonant, Dramatic",
            "notice_period_days_remaining": 730,
            "status": "ACTIVE_FOR_2_YEARS",
            "fallback_voice_id": FALLBACK_NARRATOR_VOICE_ID,
        },
        "character_speech_routing": cadence_map,
        "thread_a_10pct_and_30pct": {
            "maps_10pct_jobs": thread_a_10pct_maps,
            "collage_30pct_jobs": thread_a_30pct_animated_collage,
            "all_stills_converted_to_animated_clips": True,
            "total_thread_a_jobs": len(thread_a_10pct_maps) + len(thread_a_30pct_animated_collage),
        },
        "thread_b_60pct_wan_modal": {
            "gemini_video_simple_jobs": thread_b_gemini_video_simple,
            "gemini_video_simple_count": len(thread_b_gemini_video_simple),
            "wan_complex_planned_jobs": thread_b_wan_complex,
            "wan_complex_planned_count": len(thread_b_wan_complex),
            "wan_jobs": all_b_jobs,
            "total_thread_b_jobs": len(all_b_jobs),
        },
    }


def compute_continuation_splice_spec(
    prev_clip_frames: int,
    next_clip_frames: int,
    offset_from_end: int = CONTINUATION_OFFSET_FROM_END,
    fps: int = WAN_FPS,
) -> Dict[str, Any]:
    """Compute the exact frame index to extract from `prev_clip` and the FFmpeg trim point for seamless splicing."""
    if prev_clip_frames <= offset_from_end + 4:
        raise ValueError(f"prev_clip_frames ({prev_clip_frames}) too short for offset_from_end={offset_from_end}")
    anchor_frame_idx = prev_clip_frames - offset_from_end
    prev_trim_frames = anchor_frame_idx
    dropped_tail_frames = prev_clip_frames - prev_trim_frames
    combined_frames = prev_trim_frames + next_clip_frames
    return {
        "rule": "WAN-CHAIN-MINUS-5",
        "offset_from_end": offset_from_end,
        "prev_clip_total_frames": prev_clip_frames,
        "extracted_start_frame_index_0based": anchor_frame_idx,
        "extracted_start_frame_time_sec": round(anchor_frame_idx / fps, 4),
        "prev_clip_play_frames_before_splice": prev_trim_frames,
        "prev_clip_play_duration_sec": round(prev_trim_frames / fps, 4),
        "prev_clip_dropped_tail_frames": dropped_tail_frames,
        "next_clip_total_frames": next_clip_frames,
        "combined_seamless_frames": combined_frames,
        "combined_seamless_duration_sec": round(combined_frames / fps, 4),
    }


def extract_continuation_frame_minus_5(
    video_path: str,
    out_image_path: str,
    offset_from_end: int = CONTINUATION_OFFSET_FROM_END,
) -> Dict[str, Any]:
    """Extract the 5th frame from the end (`frame[-5]`) of a rendered video clip via ffprobe + ffmpeg."""
    import subprocess as _sp
    probe = _sp.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=nb_read_frames,r_frame_rate",
            "-of", "json", str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    stream_info = json.loads(probe.stdout)["streams"][0]
    total_frames = int(stream_info["nb_read_frames"])
    num, den = map(int, str(stream_info.get("r_frame_rate", "24/1")).split("/"))
    fps = int(round(num / max(den, 1)))
    spec = compute_continuation_splice_spec(total_frames, total_frames, offset_from_end=offset_from_end, fps=fps)
    target_idx = spec["extracted_start_frame_index_0based"]
    _sp.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_path),
            "-vf", rf"select=eq(n\,{target_idx})",
            "-vframes", "1",
            str(out_image_path),
        ],
        check=True,
    )
    return dict(spec, video_path=str(video_path), out_image_path=str(out_image_path))
