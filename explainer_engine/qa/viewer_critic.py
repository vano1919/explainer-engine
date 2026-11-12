"""Clean-Room YouTube Viewer Critic Integration (`youtube_viewer_critic`, D-130).

Implements the clean-room architecture specified in `YOUTUBE_VIEWER_CRITIC_AGENT_PROMPT_2026-11-11.md`:
1. `build_sanitized_viewer_packet(script_doc)`:
   - Extracts ONLY what a real YouTube viewer hears and sees on screen.
   - Strips all internal rule IDs (`DR-T1-01`, `KP-00`, `YT-00`), database identifiers (`loc_`, `char_`, `S01_SH001`),
     style anchor tokens, LoRA names, and engine routing flags (`WAN_I2V`, `GEMINI_LIGHT_VIDEO_I2V`, etc.).
2. `assert_zero_internal_leakage(packet)`:
   - Hard fail-closed guard that scans the serialized JSON packet and raises `ViewerCriticLeakageError`
     if any internal rule code, database ID, or pipeline token leaked into the critic's input.
3. `evaluate_script_with_viewer_critic(script_doc, ...)`:
   - Runs at Gate G2 in **Advisory Mode** alongside deterministic `script-critic`.
   - Uses live Gemini (`gemini-4-argon` / `gemini-3.8-flash`) when `use_live_gemini=True` and
     `EXPLAINER_ENABLE_PAID_APIS=1`, or runs a deterministic viewer-experience heuristic simulator offline.
   - Validates both input and output against `viewer_review_packet.schema.json` and `viewer_critic_report.schema.json`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import jsonschema

from explainer_engine.llm import gemini_api

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
PACKET_SCHEMA_PATH = SCHEMA_DIR / "viewer_review_packet.schema.json"
REPORT_SCHEMA_PATH = SCHEMA_DIR / "viewer_critic_report.schema.json"


class ViewerCriticLeakageError(RuntimeError):
    """Raised when internal rule IDs, database keys, or engine tokens leak into viewer_review_packet."""


# Strict blacklist patterns that must NEVER appear in the clean-room viewer packet
_LEAKAGE_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "internal_3tier_rule_id",
        re.compile(r"\b(?:DR|DL|CM|ED|LT|CL|MP|WN|FX|MS|VC|PK)-T[123]-\d{2}\b"),
    ),
    (
        "internal_linter_rule_id",
        re.compile(r"\b(?:BP|ST|SC|KP|PV|AL|SD|MO|UR|RG|OR|YT|CF)-(?:V4-)?[A-Z0-9\-]{2,}\b"),
    ),
    (
        "internal_db_identifier",
        re.compile(r"\b(?:loc_[a-z0-9_]+|char_[a-z0-9_]+|prop_[a-z0-9_]+|S(?:0[1-9]|1[0-6])_(?:SH|L)[0-9]{3})\b"),
    ),
    (
        "internal_pipeline_token",
        re.compile(
            r"\b(?:WAN_I2V|WAN_FLF2V|WAN_CONTROL|WAN_S2V|GEMINI_LIGHT_VIDEO_I2V|WAN_2_1_HEAVY_ACTION_ENGINE|"
            r"BATCH_ANIMATED_PHOTO_CLIP|PYTHON_INFO_GRAPHICS_RENDER|world_bible|style_anchor_token|"
            r"video_engine_tier|chain_from_prev_frame_offset|xworld_v2)\b"
        ),
    ),
]

_RAW_ID_CLEANER = re.compile(r"\b(?:loc_|char_|prop_)[a-z0-9_]+\b|\bS(?:0[1-9]|1[0-6])_(?:SH|L)[0-9]{3}\b")

VIEWER_CRITIC_SYSTEM_PROMPT = """You are a brutally honest, hyper-observant YouTube Viewer & Retention Critic watching a historical docudrama episode for the first time.
You do NOT know any internal production rules or codebase schemas. You judge ONLY what you see and hear as a real viewer:
1. Packaging & Click Intrigue: Would you click this Title + Thumbnail in a crowded feed?
2. First 30 Seconds Survival: Does the opening immediately hook your curiosity and visual attention without slow throat-clearing?
3. Mid-Video Boredom & Drop-Off Zones: Where does your attention wander because the narration feels like a textbook or the visuals feel repetitive?
4. Clarity & Immersion: Are there moments where you get confused about who is acting, where we are on the map, or why the stakes matter?
Return ONLY valid JSON matching schema 'viewer_critic_report/1'."""


def _sanitize_viewer_text(text: str, style_token: str = "") -> str:
    """Strip internal style anchor tokens and raw database IDs from viewer-facing descriptions."""
    cleaned = str(text or "")
    if style_token:
        cleaned = re.sub(re.escape(style_token), "", cleaned, flags=re.I)
    cleaned = _RAW_ID_CLEANER.sub("subject", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    return cleaned


def build_sanitized_viewer_packet(
    script_doc: Dict[str, Any],
    packaging_candidates: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """Transform `production_script.json` into a clean-room `viewer_review_packet/1` dict."""
    wb = script_doc.get("world_bible") or {}
    style_token = str(wb.get("style_anchor_token") or "")
    title = _sanitize_viewer_text(str(script_doc.get("title") or "Historical Docudrama Episode"), style_token)
    premise = _sanitize_viewer_text(str(script_doc.get("what_if_premise") or ""), style_token)

    audio_lines = script_doc.get("audio_lines") or []
    line_map = {l.get("line_id"): l for l in audio_lines if l.get("line_id")}
    shots = script_doc.get("shots") or []

    if not packaging_candidates:
        packaging_candidates = [
            {
                "title": title,
                "thumbnail_concept": f"High-contrast dramatic moment from {title}",
                "thumbnail_text_overlay": title.split(":")[0][:28].upper(),
            }
        ]

    viewer_beats: List[Dict[str, Any]] = []
    cursor_sec = 0.0
    for idx, sh in enumerate(shots, start=1):
        dur = float(sh.get("target_duration_seconds", 3.8))
        al_ids = sh.get("audio_line_ids") or []
        lines_for_shot = [line_map[lid] for lid in al_ids if lid in line_map]
        spoken = " ".join(_sanitize_viewer_text(str(l.get("text", "")), style_token) for l in lines_for_shot).strip()
        first_spk = lines_for_shot[0].get("speaker_type") if lines_for_shot else "silent_beat"
        speaker_role = (
            "narrator"
            if first_spk == "narrator"
            else ("historical_character" if first_spk == "character" else "silent_visual_beat")
        )

        vtype = sh.get("visual_type", "cinematic_video")
        gmode = sh.get("generation_mode", "WAN_I2V")
        if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
            v_format = "youtube_data_map_or_chart"
        elif vtype == "composed_illustration" or gmode in ("COLLAGE_STILL", "STILL_25D"):
            v_format = "animated_archival_still"
        else:
            v_format = "cinematic_moving_scene"

        visual_desc = _sanitize_viewer_text(
            f"{sh.get('action_start_state', '')}. {sh.get('action_end_state', '')}",
            style_token,
        )
        cam_spec = sh.get("camera_spec") or {}
        cam_feel = f"{cam_spec.get('shot_size', 'medium')} framing, {cam_spec.get('camera_move', 'steady')} camera"

        viewer_beats.append({
            "beat_index": idx,
            "start_sec": round(cursor_sec, 2),
            "end_sec": round(cursor_sec + dur, 2),
            "duration_sec": round(dur, 2),
            "speaker_role": speaker_role,
            "spoken_narration": spoken,
            "on_screen_visual_experience": visual_desc or "Dramatic historical visual beat",
            "visual_format": v_format,
            "camera_feel": cam_feel,
            "heard_atmosphere": _sanitize_viewer_text(str(sh.get("lighting_and_time") or "Tense historical atmosphere"), style_token),
        })
        cursor_sec += dur

    packet = {
        "schema": "viewer_review_packet/1",
        "episode_id": str(script_doc.get("episode_id") or "ep_unknown"),
        "title": title,
        "what_if_premise": premise,
        "target_duration_seconds": round(cursor_sec, 2) if cursor_sec > 0 else float(script_doc.get("target_duration_seconds", 720)),
        "packaging_candidates": packaging_candidates,
        "viewer_beats": viewer_beats,
    }
    assert_zero_internal_leakage(packet)
    validate_viewer_packet_schema(packet)
    return packet


def assert_zero_internal_leakage(packet: Dict[str, Any]) -> None:
    """Fail-closed scanner ensuring zero internal rule IDs, DB keys, or engine tokens appear in `packet`."""
    serialized = json.dumps(packet, ensure_ascii=False)
    for category, pattern in _LEAKAGE_PATTERNS:
        m = pattern.search(serialized)
        if m:
            raise ViewerCriticLeakageError(
                f"Clean-room violation ({category}): internal token {m.group(0)!r} leaked into viewer_review_packet!"
            )


def validate_viewer_packet_schema(packet: Dict[str, Any]) -> None:
    schema = json.loads(PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=packet, schema=schema)


def validate_viewer_report_schema(report: Dict[str, Any]) -> None:
    schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)


def _simulate_viewer_critic_offline(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic viewer retention & boredom simulator for offline unit tests and zero-spend preflight."""
    beats = packet.get("viewer_beats") or []
    dropoff_risks: List[Dict[str, Any]] = []
    confusion_points: List[Dict[str, Any]] = []
    robotic_tells: List[Dict[str, Any]] = []

    # Check opening 30s grip
    opening_beats = [b for b in beats if b["start_sec"] < 30.0]
    first_dur = opening_beats[0]["duration_sec"] if opening_beats else 5.0
    opening_has_question_or_stakes = any("?" in b["spoken_narration"] or len(b["spoken_narration"].split()) >= 5 for b in opening_beats[:2])
    cold_open_grip = 9.0 if (first_dur <= 3.8 and opening_has_question_or_stakes) else 6.2

    # Detect isolated 1-beat character interruptions vs real multi-beat played scenes
    for idx_b, b in enumerate(beats):
        if b["speaker_role"] == "historical_character":
            prev_role = beats[idx_b - 1]["speaker_role"] if idx_b > 0 else "narrator"
            next_role = beats[idx_b + 1]["speaker_role"] if idx_b + 1 < len(beats) else "narrator"
            if prev_role != "historical_character" and next_role != "historical_character":
                confusion_points.append({
                    "timestamp_sec": b["start_sec"],
                    "confused_question": "Why did a character suddenly shout one isolated line out of nowhere without a scene or reply?",
                    "suggested_clarification": "Either keep this beat in the narrator voice or build a real multi-turn played scene with a clear setup and response.",
                })

    # Scan for long slow beats or monotonous runs
    for b in beats:
        if b["duration_sec"] > 7.5:
            dropoff_risks.append({
                "start_sec": b["start_sec"],
                "end_sec": b["end_sec"],
                "risk_level": "MEDIUM",
                "viewer_symptom": "Visual hold feels lingering; casual viewers may scrub ahead.",
                "plain_language_fix": "Split this beat with a tighter reaction cut or data callout.",
            })
        words = b["spoken_narration"].split()
        if len(words) > 26:
            robotic_tells.append({
                "timestamp_sec": b["start_sec"],
                "tell_description": "Long, dense spoken clause sounds like a written essay rather than spoken storytelling.",
                "humanizing_rewrite_hint": "Break into a short 5-word punchy sentence followed by the consequence.",
            })

    formats = {b["visual_format"] for b in beats}
    visual_variety = 9.2 if len(formats) >= 3 else (7.8 if len(formats) == 2 else 5.5)
    overall = round(
        (8.8 + cold_open_grip + 8.7 + visual_variety + 8.6 + 8.5) / 6.0 * 10.0,
        1,
    )
    verdict = "PASS" if overall >= 75.0 else ("NEEDS_REVISION" if overall >= 60.0 else "REJECT")

    report = {
        "schema": "viewer_critic_report/1",
        "episode_id": packet["episode_id"],
        "execution_mode": "offline_heuristic_simulator",
        "verdict": verdict,
        "overall_score_100": overall,
        "click_probability": "HIGH" if overall >= 80.0 else "MEDIUM",
        "first_30s_survival_probability": round(min(0.95, cold_open_grip / 10.0), 2),
        "predicted_30s_retention_pct": round(min(92.0, cold_open_grip * 9.0), 1),
        "predicted_average_view_duration_pct": round(min(78.0, overall * 0.68), 1),
        "scores": {
            "packaging_intrigue": 8.8,
            "cold_open_grip": cold_open_grip,
            "narrative_momentum": 8.7,
            "visual_variety_and_clarity": visual_variety,
            "emotional_immersion": 8.6,
            "ending_payoff": 8.5,
        },
        "dropoff_risk_timestamps": dropoff_risks[:5],
        "confusion_points": confusion_points[:5],
        "robotic_ai_tells_detected": robotic_tells[:5],
        "top_3_highest_leverage_fixes": [
            "Keep the first 3.5 seconds visually urgent and tied directly to the thumbnail promise.",
            "Use the 10% Python data maps and counters whenever troop numbers or territorial shifts are mentioned.",
            "Alternate short 4-6 word punchy spoken beats after complex historical explanations.",
        ],
    }
    validate_viewer_report_schema(report)
    return report


def evaluate_script_with_viewer_critic(
    script_doc: Dict[str, Any],
    *,
    packaging_candidates: List[Dict[str, str]] | None = None,
    use_live_gemini: bool = False,
    spent_month_usd: float = 0.0,
) -> Dict[str, Any]:
    """Run the clean-room `youtube_viewer_critic` evaluation at Gate G2 (Advisory mode by default)."""
    packet = build_sanitized_viewer_packet(script_doc, packaging_candidates=packaging_candidates)
    if use_live_gemini:
        raw_report = gemini_api.call_structured_json(
            system_prompt=VIEWER_CRITIC_SYSTEM_PROMPT,
            user_payload_json=json.dumps(packet, ensure_ascii=False),
            spent_month_usd=spent_month_usd,
        )
        raw_report.setdefault("schema", "viewer_critic_report/1")
        raw_report.setdefault("episode_id", packet["episode_id"])
        raw_report["execution_mode"] = "live_gemini_api"
        validate_viewer_report_schema(raw_report)
        return raw_report

    return _simulate_viewer_critic_offline(packet)
