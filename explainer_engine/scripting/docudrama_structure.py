"""Cinematic YouTube docudrama structural validator replacing hardcoded 60/10/30 visual quotas.

Enforces three core creative-engineering laws:
1. Dramatic Showcase Scenes (2-3 real 60-120s LTX scenes per full episode):
   Prevents shallow 1-line throwaway dialogue ("წამოძახებები") by requiring dramatic LTX scenes
   to sustain multi-turn cinematic beats (60-120s, >= 4 dialogue turns or sustained dramatic action)
   while reserving MapLibre maps (``map_action``) and 2.5D living stills (``still_25d``) for
   analytical and narrated segments.
2. YouTube Visual Bridges Richness:
   Prevents flat or visually static narration by requiring visual bridges (kinetic typography
   callouts, date/location lower-thirds, archival quote highlights, stat counters, split-screens,
   or tactical map overlays) during extended narration segments.
3. Post-Assembly Visual-Aware Sound Spotting:
   Verifies that final foley/SFX cues were spotted against the assembled video cut (using exact
   visual event timestamps rather than only pre-visual script estimates), with library-first
   sourcing and priced ElevenLabs fallback for missing takes.
"""
from __future__ import annotations

from typing import Any

DRAMATIC_SCENE_MIN_S = 60.0
DRAMATIC_SCENE_MAX_S = 120.0
FULL_EPISODE_MIN_DRAMATIC_SCENES = 2
FULL_EPISODE_MAX_DRAMATIC_SCENES = 3
MIN_TURNS_PER_DRAMATIC_SCENE = 4
NARRATION_BRIDGE_MAX_GAP_S = 20.0

VALID_VISUAL_BRIDGE_KINDS = frozenset(
    {
        "kinetic_callout",
        "date_location_card",
        "archival_quote_highlight",
        "stat_counter",
        "split_screen_comparison",
        "tactical_map_overlay",
        "document_zoom_highlight",
    }
)


def validate_docudrama_structure(
    episode_plan: dict[str, Any],
    *,
    is_full_episode: bool = True,
) -> dict[str, Any]:
    """Validate dramatic scene structure, route allocation, and visual bridges without 60/10/30 quotas."""
    issues: list[dict[str, Any]] = []
    scenes = list(episode_plan.get("scenes") or [])
    dramatic_scenes = [s for s in scenes if s.get("scene_role") == "dramatic_showcase"]

    if is_full_episode and not (
        FULL_EPISODE_MIN_DRAMATIC_SCENES <= len(dramatic_scenes) <= FULL_EPISODE_MAX_DRAMATIC_SCENES
    ):
        issues.append(
            {
                "code": "DOCU-SCENE-COUNT",
                "severity": "FAIL",
                "detail": (
                    f"Full docudrama episode requires {FULL_EPISODE_MIN_DRAMATIC_SCENES}-"
                    f"{FULL_EPISODE_MAX_DRAMATIC_SCENES} dramatic LTX scenes (60-120s each); "
                    f"found {len(dramatic_scenes)}."
                ),
            }
        )

    for sc in dramatic_scenes:
        sid = str(sc.get("scene_id", "unknown"))
        dur = float(sc.get("duration_s", 0.0))
        turns = int(sc.get("dialogue_turns", 0))
        route = str(sc.get("primary_route", ""))
        if not (DRAMATIC_SCENE_MIN_S <= dur <= DRAMATIC_SCENE_MAX_S):
            issues.append(
                {
                    "code": "DOCU-SCENE-DURATION",
                    "severity": "FAIL",
                    "scene_id": sid,
                    "detail": (
                        f"Dramatic scene {sid} is {dur:.1f}s; must be {DRAMATIC_SCENE_MIN_S:.0f}-"
                        f"{DRAMATIC_SCENE_MAX_S:.0f}s (no shallow throwaway fragments)."
                    ),
                }
            )
        if turns < MIN_TURNS_PER_DRAMATIC_SCENE:
            issues.append(
                {
                    "code": "DOCU-NO-THROWAWAY-LINES",
                    "severity": "FAIL",
                    "scene_id": sid,
                    "detail": (
                        f"Dramatic scene {sid} has only {turns} dialogue turn(s); requires >= "
                        f"{MIN_TURNS_PER_DRAMATIC_SCENE} turns to form a real cinematic scene."
                    ),
                }
            )
        if route != "video":
            issues.append(
                {
                    "code": "DOCU-DRAMATIC-ROUTE",
                    "severity": "FAIL",
                    "scene_id": sid,
                    "detail": f"Dramatic showcase scene {sid} must use primary_route='video' (LTX), got {route!r}.",
                }
            )

    # Non-dramatic scenes should use map_action or still_25d (never waste LTX GPU budget on throwaway narration)
    for sc in scenes:
        if sc.get("scene_role") == "dramatic_showcase":
            continue
        sid = str(sc.get("scene_id", "unknown"))
        route = str(sc.get("primary_route", ""))
        if route == "video":
            issues.append(
                {
                    "code": "DOCU-LTX-BUDGET-LEAK",
                    "severity": "FAIL",
                    "scene_id": sid,
                    "detail": (
                        f"Non-dramatic scene {sid} uses LTX 'video' route; reserve LTX for 1-2 min dramatic "
                        "showcase scenes and use 'map_action' or 'still_25d' for narration/analysis."
                    ),
                }
            )
        elif route not in ("map_action", "still_25d"):
            issues.append(
                {
                    "code": "DOCU-NON-DRAMATIC-ROUTE",
                    "severity": "FAIL",
                    "scene_id": sid,
                    "detail": f"Non-dramatic scene {sid} has invalid primary_route {route!r}; expected 'map_action' or 'still_25d'.",
                }
            )
        dur = float(sc.get("duration_s", 0.0))
        bridges = [b for b in (sc.get("visual_bridges") or []) if isinstance(b, dict)]
        for b in bridges:
            kind = str(b.get("kind", ""))
            if kind not in VALID_VISUAL_BRIDGE_KINDS:
                issues.append(
                    {
                        "code": "DOCU-BRIDGE-KIND",
                        "severity": "FAIL",
                        "scene_id": sid,
                        "detail": f"Unknown visual bridge kind {kind!r} in scene {sid}.",
                    }
                )
        if dur >= NARRATION_BRIDGE_MAX_GAP_S:
            min_needed = max(1, int(dur // NARRATION_BRIDGE_MAX_GAP_S))
            if len(bridges) < min_needed:
                issues.append(
                    {
                        "code": "DOCU-BRIDGE-DENSITY",
                        "severity": "FAIL",
                        "scene_id": sid,
                        "detail": (
                            f"Narration scene {sid} ({dur:.1f}s) has {len(bridges)} visual bridge(s); "
                            f"YouTube docudrama pacing requires >= {min_needed} bridge(s) "
                            f"(>= 1 per {NARRATION_BRIDGE_MAX_GAP_S:.0f}s)."
                        ),
                    }
                )
            ts_list = sorted(float(b["timestamp_s"]) for b in bridges if isinstance(b.get("timestamp_s"), (int, float)))
            if ts_list:
                points = [0.0, *ts_list, dur]
                max_gap = max(points[i + 1] - points[i] for i in range(len(points) - 1))
                if max_gap > NARRATION_BRIDGE_MAX_GAP_S + 1e-6:
                    issues.append(
                        {
                            "code": "DOCU-BRIDGE-GAP",
                            "severity": "FAIL",
                            "scene_id": sid,
                            "detail": f"Narration scene {sid} has a {max_gap:.1f}s gap without a visual bridge (max {NARRATION_BRIDGE_MAX_GAP_S:.0f}s).",
                        }
                    )

    return {
        "status": "PASS" if not issues else "FAIL",
        "dramatic_scene_count": len(dramatic_scenes),
        "total_scenes": len(scenes),
        "issues": issues,
    }


def validate_post_assembly_spotting(spotting_record: dict[str, Any]) -> dict[str, Any]:
    """Validate that final SFX/foley spotting was performed against the assembled visual cut."""
    issues: list[str] = []
    if spotting_record.get("based_on_assembled_video") is not True:
        issues.append("Post-assembly sound spotting must inspect the assembled video cut (based_on_assembled_video=True).")
    if not spotting_record.get("assembled_video_sha256") or len(str(spotting_record.get("assembled_video_sha256"))) != 64:
        issues.append("Post-assembly sound spotting must pin the 64-char SHA-256 of the assembled video cut.")
    cues = list(spotting_record.get("cues") or [])
    for idx, cue in enumerate(cues):
        src = str(cue.get("source", ""))
        if src not in ("free_library", "elevenlabs_approved", "clip_native_audio"):
            issues.append(f"cue[{idx}] has invalid audio source {src!r} (no procedural placeholders in final mix).")
        if src == "elevenlabs_approved" and not cue.get("approval_or_ledger_ref"):
            issues.append(f"cue[{idx}] uses paid ElevenLabs SFX without approval_or_ledger_ref.")
        if cue.get("visual_timestamp_s") is None:
            issues.append(f"cue[{idx}] missing visual_timestamp_s anchored to an on-screen visual event.")
    return {"status": "PASS" if not issues else "FAIL", "cue_count": len(cues), "issues": issues}
