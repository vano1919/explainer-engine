"""Migrate legacy film_shots/2..3 or production_script/1..4 JSON files to production_script.schema.json v4.0.0 (TODO-16)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jsonschema

PHASE_FOR_SEG_INDEX = (
    "Z1", "Z1", "Z1",
    "Z2", "Z2", "Z2",
    "Z3", "Z3", "Z3", "Z3",
    "Z4", "Z4", "Z4", "Z4",
    "Z5", "Z5",
)


def migrate_to_v4(legacy_doc: dict, *, episode_id: str | None = None) -> dict:
    """Convert a legacy production_script or film_shots dict into a valid v4.0.0 production_script dict."""
    if legacy_doc.get("schema_version") == "4.0.0":
        return legacy_doc

    ep = legacy_doc.get("episode") or {}
    raw_slug = episode_id or ep.get("id") or legacy_doc.get("job_id") or "migrated_episode"
    clean_slug = re.sub(r"[^a-z0-9_]+", "_", raw_slug.lower()).strip("_")
    if not clean_slug.startswith("ep_"):
        clean_slug = f"ep_{clean_slug}"

    title = ep.get("title") or legacy_doc.get("title") or "Historical Counterfactual Episode"
    premise = (
        (ep.get("distinct") or {}).get("premise")
        or legacy_doc.get("what_if_premise")
        or f"Counterfactual historical analysis for {title}."
    )
    style_token = "Luminescent Chiaroscuro and Tactile Mythic Realism historical docudrama"

    characters = []
    for cid, cinfo in (legacy_doc.get("cast") or {}).items():
        clean_cid = f"char_{re.sub(r'[^a-z0-9_]+', '_', cid.lower()).strip('_')}"
        characters.append(
            {
                "character_id": clean_cid,
                "name": (cinfo.get("names") or [cid])[0] if isinstance(cinfo, dict) else str(cid),
                "historical_role": "Historical Figure",
                "fixed_appearance_prompt": f"{style_token}, period portrait of {cid} in historical attire",
                "costume_continuity_notes": "Consistent historical period uniform",
                "reference_sheet_path": f"02_keyframes/assets/{clean_cid}_turnaround.png",
            }
        )
    if not characters:
        characters.append(
            {
                "character_id": "char_protagonist",
                "name": "Historical Protagonist",
                "historical_role": "Commander",
                "fixed_appearance_prompt": f"{style_token}, historical commander in period uniform with crisp ink contours",
                "costume_continuity_notes": "Standard period coat",
                "reference_sheet_path": "02_keyframes/assets/char_protagonist_turnaround.png",
            }
        )

    locations = [
        {
            "location_id": "loc_primary_setting",
            "name": "Primary Historical Setting",
            "era_and_geography": "Historical Theatre",
            "fixed_environment_prompt": f"{style_token}, period architecture and atmospheric terrain",
            "lighting_palette": "Dramatic chiaroscuro period lighting",
            "anchor_image_path": "02_keyframes/assets/loc_primary_setting_anchor.png",
        }
    ]
    props = [
        {
            "prop_id": "prop_chronicle_map",
            "name": "Campaign Map",
            "fixed_prop_prompt": " Inked parchment campaign map on oak table",
            "anchor_image_path": "02_keyframes/assets/prop_chronicle_map_anchor.png",
        }
    ]

    raw_segs = legacy_doc.get("segments") or [{"id": "S01", "beat": title, "lines": [{"text": premise}], "shots": []}]
    segments_v4 = []
    audio_lines_v4 = []
    shots_v4 = []
    phases_map: dict[str, list[str]] = {}

    for idx, seg in enumerate(raw_segs[:16]):
        sid = f"S{idx + 1:02d}"
        pid = PHASE_FOR_SEG_INDEX[min(idx, len(PHASE_FOR_SEG_INDEX) - 1)]
        phases_map.setdefault(pid, []).append(sid)

        prev_sid = f"S{idx:02d}" if idx > 0 else None
        next_sid = f"S{idx + 2:02d}" if idx < min(len(raw_segs), 16) - 1 else None

        seg_lines = seg.get("lines") or [{"text": seg.get("beat", premise)}]
        seg_line_ids = []
        seg_dur = 0.0
        for l_idx, ln in enumerate(seg_lines, start=1):
            lid = f"{sid}_L{l_idx:03d}"
            seg_line_ids.append(lid)
            txt = ln.get("text", "Historical narration line.") if isinstance(ln, dict) else str(ln)
            est_dur = max(5.0, round(len(txt.split()) / 2.5, 1))
            seg_dur += est_dur
            is_char = bool(isinstance(ln, dict) and ln.get("speaker"))
            audio_lines_v4.append(
                {
                    "line_id": lid,
                    "segment_id": sid,
                    "speaker_type": "character" if is_char else "narrator",
                    "speaker_id": characters[0]["character_id"] if is_char else "narrator_main",
                    "addressee_id": None,
                    "delivery_direction": "measured documentary delivery",
                    "text": txt,
                    "register_type": "dramatized_in_scene_speech" if is_char else "verified_historical_fact",
                    "citation_ids": ["CITE-01"],
                    "estimated_duration_seconds": est_dur,
                    "requires_visible_lipsync": False,
                }
            )

        segments_v4.append(
            {
                "segment_id": sid,
                "phase_id": pid,
                "title": seg.get("beat") or seg.get("title") or f"Segment {sid}",
                "narrative_purpose": seg.get("purpose") or f"Advance counterfactual causal chain in {sid}.",
                "target_duration_seconds": max(10.0, seg_dur),
                "factual_status": "actual_history" if idx < 3 else ("divergence_point" if idx == 3 else "counterfactual_consequence"),
                "cause_from_segment_id": prev_sid,
                "effect_to_segment_id": next_sid,
            }
        )

        shots_v4.append(
            {
                "shot_id": f"{sid}_SH001",
                "segment_id": sid,
                "target_duration_seconds": min(12.0, max(5.0, seg_dur)),
                "narrative_purpose": f"Visual coverage for {sid} narrative beat.",
                "visual_type": "cinematic_video",
                "generation_mode": "WAN_I2V",
                "location_id": "loc_primary_setting",
                "character_ids": [characters[0]["character_id"]],
                "prop_ids": ["prop_chronicle_map"],
                "audio_line_ids": seg_line_ids,
                "action_start_state": "Commander stands over campaign map table",
                "action_end_state": "Commander traces route across the map",
                "camera_spec": {
                    "shot_size": "medium",
                    "vertical_angle": "eye_level_0",
                    "horizontal_azimuth_deg": 0,
                    "camera_move": "slow_push_in",
                    "multiangle_token": None,
                },
                "screen_composition": {
                    "foreground": "Campaign map table",
                    "midground": "Commander in period uniform",
                    "background": "Candlelit headquarters tent",
                    "screen_direction_notes": "180-degree axis preserved",
                },
                "lighting_and_time": "Warm lantern chiaroscuro",
                "continuity_refs": {"reuse_location_anchor": True, "inherit_from_previous_shot_id": None},
                "keyframe_plan": {
                    "needs_start_frame": True,
                    "needs_end_frame": False,
                    "start_frame_source": "new_master_anchor",
                    "end_frame_reason": None,
                },
                "image_prompt": {
                    "start_frame_prompt": f"{style_token}. Medium eye-level shot of commander at campaign map table in headquarters tent.",
                    "end_frame_prompt": None,
                    "negative_prompt": "photorealistic, 3D CGI, extra fingers, watermark, text banner",
                },
                "video_prompt": {
                    "motion_prompt": "Subject: Commander smoothly traces the route on the parchment map. Camera: slow push-in.",
                    "primary_action_count": 1,
                    "camera_move_count": 1,
                    "parallax_preset": None,
                },
                "selective_control": None,
                "transition_out": "hard_cut",
            }
        )

    phases_v4 = [
        {
            "phase_id": pid,
            "title": f"Phase {pid}",
            "target_window": "0:00-2:00",
            "segment_ids": sids,
            "narrative_objective": f"Execute narrative objective for phase {pid}.",
        }
        for pid, sids in phases_map.items()
    ]

    v4_doc = {
        "schema_version": "4.0.0",
        "episode_id": clean_slug,
        "title": title if len(title) >= 5 else f"{title} Episode",
        "what_if_premise": premise if len(premise) >= 15 else f"{premise} (counterfactual historical premise)",
        "target_duration_seconds": 720,
        "fps": 24,
        "audio_balance_target": {
            "narrator_ratio_min": 0.70,
            "narrator_ratio_max": 0.80,
            "dialogue_ratio_min": 0.20,
            "dialogue_ratio_max": 0.30,
        },
        "visual_mix_target": {
            "cinematic_video_target": 0.60,
            "composed_illustration_target": 0.30,
            "map_visualization_target": 0.10,
        },
        "historical_dossier_ref": f"jobs/{clean_slug}/01_script/research_dossier.md",
        "world_bible": {
            "style_anchor_token": style_token,
            "characters": characters,
            "locations": locations,
            "props": props,
        },
        "phases": phases_v4,
        "segments": segments_v4,
        "audio_lines": audio_lines_v4,
        "shots": shots_v4,
    }
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(v4_doc, schema)
    return v4_doc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Migrate a legacy script or shot spec to production_script.schema.json v4.0.0")
    p.add_argument("input", help="Path to legacy JSON file")
    p.add_argument("--out", required=True, help="Output path for v4.0.0 production_script.json")
    args = p.parse_args(argv)
    src = json.loads(Path(args.input).read_text(encoding="utf-8"))
    migrated = migrate_to_v4(src)
    Path(args.out).write_text(json.dumps(migrated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Migrated {args.input} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
