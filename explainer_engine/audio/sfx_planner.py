"""Gate G4 SFX (Footsteps, Foley), Ambience Beds, Musical Melodies & Shot Sound-Design Metadata Planner (D-124 / v4.3).

Integrates directly with `explainer_engine.audio.layers` (`AL-01..AL-04`) and sourced rules:
- `BP-54`: Picture-synced SFX (footsteps, hooves, cannon, doors, parchment) land at 0ms offset (never early).
- `BP-62`: Musical melodies fade in over 1.0s and fade out over 2.0s (`MUSIC_FADE_IN`, `MUSIC_FADE_OUT`).
- `BP-65`: Ambience beds sit at or below `MAX_BED_DB` (-24 dB under speech) and cover the full segment.
- Section 7.4 Shot Sound-Design Metadata (`build_shot_sound_design_metadata`):
  Populates `environment`, `weather`, `surface`, `physical_actions`, `sound_events`, `event_timestamps`,
  `sound_source` (`existing_asset` | `licensed_local` | `procedural` | `model_audio`),
  `spatial_context` (`indoor` | `outdoor` | `close` | `medium` | `distant`),
  `continuity_group`, `suggested_intensity`, and `mixing_priority` for every shot.
- V4.3 Episode-First Era-Gated Sound Taxonomy:
  Replaces unsafe substring matching (`"mount"` in `"Mount Toba"`, `"spear"` -> `sword_metal_clash`)
  with word-boundary regexes (`CAVALRY_REGEX`, `METAL_CLASH_REGEX`, `LITHIC_WEAPON_REGEX`) and deterministic
  `ERA_COMPATIBILITY_TABLE` filtering so prehistoric episodes never receive cavalry hooves, metallic sword clashes,
  cannon salvos, or vellum parchment/London exchange beds.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple
from explainer_engine.audio import layers as L

FOOTSTEP_KEYWORDS = ("walk", "march", "step", "run", "advance", "retreat", "corridor", "cobblestone", "mud", "flee", "trek", "sprint", "stride")
CAVALRY_KEYWORDS = ("horse", "horses", "cavalry", "dragoon", "cuirassier", "gallop", "galloping", "horseback", "hooves", "saddle")
COMBAT_KEYWORDS = ("cannon", "battery", "artillery", "fire", "gun", "bayonet", "explosion", "breach", "erupt", "volcan", "caldera", "pyroclastic", "shockwave")
METAL_CLASH_KEYWORDS = ("sword", "swords", "saber", "sabre", "steel", "clash", "bayonet", "rapier", "cutlass", "armor")
LITHIC_WEAPON_KEYWORDS = ("spear", "spears", "flint", "obsidian", "microlith", "stone_tip", "bow", "arrow", "stone_tool", "knapping", "stone_blade")
PAPER_LEDGER_KEYWORDS = ("map", "ledger", "bond", "scroll", "dispatch", "letter", "divider", "coin", "gold", "counter", "timeline")
FIRE_KEYWORDS = ("fire", "torch", "candle", "ember", "hearth", "magma", "lava", "burn", "ash")
WATER_KEYWORDS = ("sea", "ocean", "ship", "wave", "river", "harbor", "lake", "water")

FOOTSTEP_REGEX = re.compile(r"\b(walk|walks|walking|march|marching|step|steps|stepping|run|running|advance|retreat|corridor|cobblestone|mud|flee|fleeing|trek|trekking|sprint|stride|crouch|crawl)\b", re.IGNORECASE)
CAVALRY_REGEX = re.compile(r"\b(horse|horses|cavalry|dragoon|dragoons|cuirassier|cuirassiers|gallop|galloping|horseback|hooves|saddle|bridle)\b", re.IGNORECASE)
VOLCANIC_REGEX = re.compile(r"\b(erupt|eruption|volcan|volcano|volcanic|caldera|pyroclastic|shockwave|magma|vent|plume|supervolcano|toba)\b", re.IGNORECASE)
ARTILLERY_REGEX = re.compile(r"\b(cannon|cannons|battery|artillery|musket|gunfire|howitzer|salvo|bombardment)\b", re.IGNORECASE)
METAL_CLASH_REGEX = re.compile(r"\b(sword|swords|saber|sabre|bayonet|rapier|cutlass|steel_blade|armor_plate|broadsword|metal_clash)\b", re.IGNORECASE)
LITHIC_WEAPON_REGEX = re.compile(r"\b(spear|spears|flint|obsidian|microlith|stone_tip|bow|arrow|stone_tool|knapping|stone_blade|hafted)\b", re.IGNORECASE)
PAPER_LEDGER_REGEX = re.compile(r"\b(map|ledger|bond|scroll|dispatch|letter|divider|coin|gold|counter|timeline)\b", re.IGNORECASE)
FIRE_REGEX = re.compile(r"\b(fire|torch|candle|ember|embers|hearth|magma|lava|burn|burning|ash|cinder)\b", re.IGNORECASE)
WATER_REGEX = re.compile(r"\b(sea|ocean|ship|wave|waves|river|harbor|lake|water|monsoon|shore|wadi)\b", re.IGNORECASE)

SOUND_EVENT_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "volcanic_explosion_debris": {"category": "natural_cataclysm", "generator_key": "volcanic_explosion_debris"},
    "distant_cannon_salvo": {"category": "gunpowder_warfare", "generator_key": "volcanic_explosion_debris"},
    "sword_metal_clash": {"category": "metallic_weapons", "generator_key": "sword_metal_clash"},
    "stone_lithic_strike": {"category": "prehistoric_lithic_foley", "generator_key": "footstep_stone"},
    "horse_hooves_gallop": {"category": "equestrian_cavalry", "generator_key": "horse_hooves_gallop"},
    "footstep_stone": {"category": "human_locomotion", "generator_key": "footstep_stone"},
    "footstep_dirt": {"category": "human_locomotion", "generator_key": "footstep_dirt"},
    "footstep_grass": {"category": "human_locomotion", "generator_key": "footstep_grass"},
    "footstep_snow": {"category": "human_locomotion", "generator_key": "footstep_snow"},
    "fire_crackle_bed": {"category": "natural_elements", "generator_key": "fire_crackle_bed"},
    "wind_howl": {"category": "natural_elements", "generator_key": "wind_howl"},
    "rain_downpour": {"category": "natural_elements", "generator_key": "rain_downpour"},
    "cloth_rustle": {"category": "human_foley", "generator_key": "cloth_rustle"},
    "page_flip": {"category": "paper_parchment_foley", "generator_key": "page_flip"},
    "stone_tablet_slide": {"category": "cartographic_reveal", "generator_key": "footstep_stone"},
}

ERA_COMPATIBILITY_TABLE: Dict[str, Dict[str, Any]] = {
    "prehistoric_pleistocene": {
        "forbidden_events": (
            "horse_hooves_gallop",
            "cavalry_movement",
            "sword_metal_clash",
            "distant_cannon_salvo",
            "cannon_shot",
            "musket_volley",
            "wax_seal_stamp",
            "page_flip",
            "vellum_parchment_and_brass_compass",
            "london_exchange_hall_murmur_bed",
        ),
        "replacements": {
            "horse_hooves_gallop": "footstep_dirt",
            "sword_metal_clash": "stone_lithic_strike",
            "distant_cannon_salvo": "volcanic_explosion_debris",
            "page_flip": "stone_tablet_slide",
        },
    },
    "ancient_classical": {
        "forbidden_events": ("distant_cannon_salvo", "cannon_shot", "musket_volley"),
        "replacements": {"distant_cannon_salvo": "sword_metal_clash"},
    },
    "medieval": {
        "forbidden_events": ("distant_cannon_salvo", "cannon_shot", "musket_volley"),
        "replacements": {"distant_cannon_salvo": "sword_metal_clash"},
    },
    "napoleonic_1815": {
        "forbidden_events": (),
        "replacements": {},
    },
    "modern_20th_century": {
        "forbidden_events": ("sword_metal_clash",),
        "replacements": {"sword_metal_clash": "volcanic_explosion_debris"},
    },
}


def infer_historical_period(shot_or_script: Dict[str, Any], default_period: str | None = None) -> str:
    """Infer canonical historical period from shot or script metadata."""
    if default_period:
        return default_period
    explicit = str(shot_or_script.get("historical_period") or "").strip().lower()
    if explicit:
        if any(k in explicit for k in ("pleistocene", "prehistoric", "74000", "74,000", "paleolithic", "stone_age", "toba")):
            return "prehistoric_pleistocene"
        return explicit
    ep_id = str(shot_or_script.get("episode_id") or "").lower()
    text_probe = " ".join([
        ep_id,
        str(shot_or_script.get("location_id") or ""),
        str(shot_or_script.get("narrative_purpose") or ""),
        str(shot_or_script.get("action_start_state") or ""),
    ]).lower()
    if any(k in text_probe for k in ("toba", "74,000", "74000", "pleistocene", "prehistoric", "sumatra", "shinfa", "jwalapuram", "pinnacle_point", "forager", "obsidian", "microlith")):
        return "prehistoric_pleistocene"
    return "napoleonic_1815"


def filter_sound_events_for_era(
    sound_events: Sequence[str],
    historical_period: str = "prehistoric_pleistocene",
) -> Tuple[List[str], List[Dict[str, str]]]:
    """Filter or replace sound events that violate `ERA_COMPATIBILITY_TABLE` for `historical_period`."""
    rules = ERA_COMPATIBILITY_TABLE.get(historical_period, {"forbidden_events": (), "replacements": {}})
    forbidden = set(rules.get("forbidden_events", ()))
    replacements = dict(rules.get("replacements", {}))
    kept: List[str] = []
    blocked_log: List[Dict[str, str]] = []
    for ev in sound_events:
        if ev in forbidden:
            repl = replacements.get(ev)
            blocked_log.append({
                "blocked_event": ev,
                "historical_period": historical_period,
                "replacement": repl or "dropped",
            })
            if repl and repl not in kept:
                kept.append(repl)
        else:
            if ev not in kept:
                kept.append(ev)
    if not kept:
        kept.append("wind_howl")
    return kept, blocked_log


def build_shot_sound_design_metadata(
    shot: Dict[str, Any],
    shot_start_sec: float = 0.0,
    has_existing_audio_pack: bool = True,
    historical_period: str | None = None,
) -> Dict[str, Any]:
    """Build the canonical Section 7.4 `sound_design` metadata object for a single shot."""
    sid = str(shot.get("shot_id") or "S01_SH001")
    seg_id = str(shot.get("segment_id") or "S01")
    loc_id = str(shot.get("location_id") or "loc_default")
    dur = float(shot.get("target_duration_seconds", 4.0))
    shot_size = str((shot.get("camera_spec") or {}).get("shot_size") or "medium_wide")
    era = infer_historical_period(shot, default_period=historical_period)
    is_prehistoric = era == "prehistoric_pleistocene"

    text_blob = " ".join([
        str(shot.get("narrative_purpose") or ""),
        str(shot.get("action_start_state") or ""),
        str(shot.get("action_end_state") or ""),
        str(shot.get("lighting_and_time") or ""),
        loc_id,
    ]).lower()

    # 1. Indoor vs Outdoor & Environment classification
    is_indoor = any(k in text_blob for k in ("interior", "room", "hall", "chamber", "tent", "cave", "shelter", "vault", "library", "palace", "overhang"))
    if VOLCANIC_REGEX.search(text_blob) or "ash" in text_blob:
        environment = "volcanic_caldera_and_ash_plains"
    elif not is_prehistoric and any(k in text_blob for k in ("battle", "ridge", "field", "trench", "front")):
        environment = "battlefield_exterior"
    elif WATER_REGEX.search(text_blob):
        environment = "coastal_or_maritime"
    elif is_indoor:
        environment = "limestone_cave_or_rock_shelter" if is_prehistoric else "stone_or_timber_interior"
    else:
        environment = "open_wilderness_exterior"

    # 2. Weather
    if VOLCANIC_REGEX.search(text_blob) or "ash" in text_blob:
        weather = "volcanic_ash_storm_and_wind"
    elif any(k in text_blob for k in ("rain", "storm", "downpour", "thunder", "monsoon")):
        weather = "heavy_rain_and_wind"
    elif any(k in text_blob for k in ("snow", "frost", "winter", "blizzard", "glacial")):
        weather = "freezing_wind_and_snow"
    elif is_indoor:
        weather = "enclosed_draft"
    else:
        weather = "high_altitude_wind"

    # 3. Surface
    if any(k in text_blob for k in ("snow", "ice", "frost")):
        surface = "snow"
    elif any(k in text_blob for k in ("stone", "cobble", "rock", "basalt", "marble", "cave", "obsidian", "flint", "cliff")):
        surface = "stone"
    elif any(k in text_blob for k in ("grass", "forest", "meadow", "jungle", "savanna")):
        surface = "grass"
    else:
        surface = "dirt"

    # 4. Physical actions, sound events & timestamps (using word-boundary regexes + era compatibility table)
    physical_actions: List[str] = []
    raw_sound_events: List[str] = []
    event_timestamps: List[float] = []

    if VOLCANIC_REGEX.search(text_blob) or (not is_prehistoric and ARTILLERY_REGEX.search(text_blob)):
        physical_actions.append("volcanic_pyroclastic_rupture" if is_prehistoric else "volcanic_or_artillery_rupture")
        raw_sound_events.append("volcanic_explosion_debris")
        event_timestamps.append(round(shot_start_sec + min(0.25, dur * 0.15), 3))

    if LITHIC_WEAPON_REGEX.search(text_blob):
        physical_actions.append("prehistoric_lithic_tool_or_spear_craft")
        raw_sound_events.append("stone_lithic_strike")
        event_timestamps.append(round(shot_start_sec + min(0.35, dur * 0.22), 3))
    elif METAL_CLASH_REGEX.search(text_blob):
        physical_actions.append("weapon_or_metal_impact")
        raw_sound_events.append("sword_metal_clash")
        event_timestamps.append(round(shot_start_sec + min(0.45, dur * 0.25), 3))

    if CAVALRY_REGEX.search(text_blob):
        physical_actions.append("cavalry_movement")
        raw_sound_events.append("horse_hooves_gallop")
        event_timestamps.append(round(shot_start_sec + 0.12, 3))

    if FOOTSTEP_REGEX.search(text_blob):
        physical_actions.append(f"footsteps_on_{surface}")
        raw_sound_events.append(f"footstep_{surface}")
        event_timestamps.append(round(shot_start_sec + 0.18, 3))

    if FIRE_REGEX.search(text_blob):
        physical_actions.append("fire_and_ember_convection")
        raw_sound_events.append("fire_crackle_bed")
        event_timestamps.append(round(shot_start_sec + 0.05, 3))

    if PAPER_LEDGER_REGEX.search(text_blob) or shot.get("generation_mode") in ("TACTILE_MAP", "MAP_25D"):
        physical_actions.append("cartographic_data_reveal")
        raw_sound_events.append("stone_tablet_slide" if is_prehistoric else "page_flip")
        event_timestamps.append(round(shot_start_sec + 0.05, 3))

    sound_events, blocked_era_events = filter_sound_events_for_era(raw_sound_events, historical_period=era)
    if blocked_era_events:
        physical_actions = [a for a in physical_actions if a != "cavalry_movement" and (not is_prehistoric or a != "weapon_or_metal_impact")]

    if not physical_actions:
        physical_actions.append("atmospheric_camera_drift")
    if not raw_sound_events:
        sound_events = ["wind_howl" if not is_indoor else "cloth_rustle"]
        event_timestamps = [round(shot_start_sec + 0.10, 3)]
    else:
        event_timestamps = event_timestamps[:len(sound_events)]
        while len(event_timestamps) < len(sound_events):
            event_timestamps.append(round(shot_start_sec + 0.10, 3))

    # 5. Spatial context
    if shot_size in ("close_up", "extreme_close_up", "medium_close_up"):
        distance_tag = "close"
    elif shot_size in ("extreme_wide", "wide", "top_down_map"):
        distance_tag = "distant"
    else:
        distance_tag = "medium"
    spatial_context = f"{'indoor' if is_indoor else 'outdoor'}_{distance_tag}"

    # 6. Continuity group: consecutive shots in the same location or environment share an unbroken ambience bed
    continuity_group = f"amb_group_{loc_id}_{'indoor' if is_indoor else 'outdoor'}"

    return {
        "shot_id": sid,
        "segment_id": seg_id,
        "historical_period": era,
        "environment": environment,
        "weather": weather,
        "surface": surface,
        "physical_actions": physical_actions,
        "sound_events": sound_events,
        "blocked_era_events": blocked_era_events,
        "event_timestamps": event_timestamps,
        "sound_source": "existing_asset" if has_existing_audio_pack else "procedural",
        "spatial_context": spatial_context,
        "continuity_group": continuity_group,
        "suggested_intensity": "high" if VOLCANIC_REGEX.search(text_blob) or ARTILLERY_REGEX.search(text_blob) else ("low" if is_indoor else "medium"),
        "mixing_priority": "duck_under_narration_and_dialogue",
    }


def build_g4_audio_fx_plan(script_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the Gate G4 SFX, Footsteps, Ambience, Musical Melody & Shot Sound-Design manifest from production_script.json."""
    segments = script_doc.get("segments", [])
    shots = script_doc.get("shots", [])
    era = infer_historical_period(script_doc)
    is_prehistoric = era == "prehistoric_pleistocene"

    sfx_cues: List[Dict[str, Any]] = []
    ambience_beds: List[Dict[str, Any]] = []
    music_melodies: List[Dict[str, Any]] = []
    shot_sound_design_map: Dict[str, Dict[str, Any]] = {}
    blocked_era_events_total: List[Dict[str, str]] = []

    t_cursor = 0.0
    for idx_sh, sh in enumerate(shots):
        dur = float(sh.get("target_duration_seconds", 4.0))
        shot_id = sh.get("shot_id", "?")
        seg_id = sh.get("segment_id", "?")
        text_blob = " ".join([
            str(sh.get("narrative_purpose", "")),
            str(sh.get("action_start_state", "")),
            str(sh.get("action_end_state", "")),
        ]).lower()

        sd_meta = build_shot_sound_design_metadata(sh, shot_start_sec=t_cursor, historical_period=era)
        shot_sound_design_map[shot_id] = sd_meta
        blocked_era_events_total.extend(sd_meta.get("blocked_era_events", []))

        # Anti-repetition variant index (1, 2, 3) so adjacent shots never play the exact same sample without variation
        variant_idx = (idx_sh % 3) + 1

        if FOOTSTEP_REGEX.search(text_blob):
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_FOOTSTEPS",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "footsteps_foley",
                "sound": f"footstep_{sd_meta['surface']}_v{variant_idx}",
                "generator_key": f"footstep_{sd_meta['surface']}",
                "variant_seed": variant_idx,
                "pitch_jitter": round(1.0 + ((idx_sh % 5) - 2) * 0.025, 4),
                "start_sec": round(t_cursor + 0.15, 3),
                "duration_sec": round(min(2.5, dur - 0.2), 3),
                "gain_db": -14.0,
                "offset_ms": 0,  # BP-54: never early
            })
        if LITHIC_WEAPON_REGEX.search(text_blob):
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_LITHIC",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "prehistoric_lithic_foley",
                "sound": f"stone_lithic_strike_v{variant_idx}",
                "generator_key": "footstep_stone",
                "variant_seed": variant_idx,
                "pitch_jitter": round(1.0 + ((idx_sh % 4) - 1.5) * 0.03, 4),
                "start_sec": round(t_cursor + 0.22, 3),
                "duration_sec": round(min(1.6, dur - 0.2), 3),
                "gain_db": -14.5,
                "offset_ms": 0,
            })
        if not is_prehistoric and CAVALRY_REGEX.search(text_blob):
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_HOOVES",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "cavalry_foley",
                "sound": f"horse_hooves_and_tack_v{variant_idx}",
                "generator_key": "horse_hooves_gallop",
                "variant_seed": variant_idx,
                "pitch_jitter": round(1.0 + ((idx_sh % 3) - 1) * 0.03, 4),
                "start_sec": round(t_cursor + 0.10, 3),
                "duration_sec": round(min(3.0, dur - 0.2), 3),
                "gain_db": -13.0,
                "offset_ms": 0,
            })
        if VOLCANIC_REGEX.search(text_blob) or (not is_prehistoric and ARTILLERY_REGEX.search(text_blob)):
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_{'VOLCANIC' if is_prehistoric else 'CANNON'}",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "volcanic_cataclysm_impact" if is_prehistoric else "battlefield_impact",
                "sound": f"volcanic_pyroclastic_roar_v{variant_idx}" if is_prehistoric else f"distant_cannon_salvo_and_smoke_v{variant_idx}",
                "generator_key": "volcanic_explosion_debris",
                "variant_seed": variant_idx,
                "pitch_jitter": round(1.0 + ((idx_sh % 4) - 1.5) * 0.03, 4),
                "start_sec": round(t_cursor + 0.25, 3),
                "duration_sec": 2.0,
                "gain_db": -12.0,
                "offset_ms": 0,
            })
        if PAPER_LEDGER_REGEX.search(text_blob) or sh.get("generation_mode") in ("TACTILE_MAP", "MAP_25D"):
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_MAP_REVEAL",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "cartographic_reveal_foley",
                "sound": f"tectonic_stone_horizon_sweep_v{variant_idx}" if is_prehistoric else f"vellum_parchment_and_brass_compass_v{variant_idx}",
                "generator_key": "wind_howl" if is_prehistoric else "page_flip",
                "variant_seed": variant_idx,
                "pitch_jitter": 1.0,
                "start_sec": round(t_cursor + 0.05, 3),
                "duration_sec": 1.5,
                "gain_db": -15.0,
                "offset_ms": 0,
            })
        if not any(c["shot_id"] == shot_id for c in sfx_cues):
            gen_key = sd_meta["sound_events"][0]
            mapped_gen_key = SOUND_EVENT_TAXONOMY.get(gen_key, {}).get("generator_key", gen_key)
            sfx_cues.append({
                "cue_id": f"SFX_{shot_id}_ENV_FOLEY",
                "shot_id": shot_id,
                "segment_id": seg_id,
                "category": "environmental_foley",
                "sound": f"{gen_key}_v{variant_idx}",
                "generator_key": mapped_gen_key,
                "variant_seed": variant_idx,
                "pitch_jitter": round(1.0 + ((idx_sh % 3) - 1) * 0.02, 4),
                "start_sec": round(t_cursor + 0.12, 3),
                "duration_sec": round(min(2.0, dur - 0.15), 3),
                "gain_db": -16.0,
                "offset_ms": 0,
            })
        t_cursor += dur

    # Build continuous ambience beds grouped by continuity_group across consecutive shots + segment beds
    seg_cursor = 0.0
    for idx, seg in enumerate(segments):
        sdur = float(seg.get("target_duration_seconds", 60.0))
        sid = seg.get("segment_id", f"S{idx+1:02d}")
        fstatus = seg.get("factual_status", "actual_history")
        if is_prehistoric:
            bed_sound = "prehistoric_volcanic_ash_wind_bed" if idx % 2 == 0 else "pleistocene_monsoon_and_river_bed"
        else:
            bed_sound = "rain_and_wind_battlefield_bed" if idx % 2 == 0 else "london_exchange_hall_murmur_bed"
        ambience_beds.append({
            "bed_id": f"BED_{sid}",
            "segment_id": sid,
            "continuity_group": f"seg_continuity_{idx // 2}",
            "sound": bed_sound,
            "start_sec": round(seg_cursor, 3),
            "end_sec": round(seg_cursor + sdur, 3),
            "crossfade_sec": 0.65,
            "gain_db": float(L.MAX_BED_DB),  # BP-65 cap (-24 dB)
        })
        melody_mood = {
            "actual_history": "cello_tension_ostinato_d_minor",
            "divergence_point": "brass_and_timpani_turning_point_motif",
            "counterfactual_consequence": "driving_strings_escalation_melody",
            "historical_reflection": "solemn_piano_and_low_strings_resolution",
        }.get(fstatus, "cello_tension_ostinato_d_minor")
        music_melodies.append({
            "music_id": f"MELODY_{sid}",
            "segment_id": sid,
            "motif": melody_mood,
            "start_sec": round(seg_cursor, 3),
            "end_sec": round(seg_cursor + sdur, 3),
            "fade_in_s": 1.0,   # BP-62
            "fade_out_s": 2.0,  # BP-62
            "duck_under_speech_db": -18.0,
        })
        seg_cursor += sdur

    return {
        "schema": "g4_audio_fx_plan/2",
        "episode_id": script_doc.get("episode_id", "unknown"),
        "historical_period": era,
        "status": "AWAITING_CREATOR_G4_APPROVAL",
        "sourced_rules_enforced": ["AL-01..AL-04", "BP-53", "BP-54", "BP-57", "BP-62", "BP-65", "BP-116..BP-122"],
        "wan_video_native_audio_note": "Wan 2.1/2.2 I2V/FLF2V generate silent video clips; 100% of environmental ambience and spot foley are provided by this continuous sound-design layer.",
        "counts": {
            "sfx_cues": len(sfx_cues),
            "ambience_beds": len(ambience_beds),
            "music_melodies": len(music_melodies),
            "shots_with_sound_design_metadata": len(shot_sound_design_map),
            "blocked_anachronistic_events": len(blocked_era_events_total),
        },
        "blocked_era_events": blocked_era_events_total,
        "shot_sound_design": shot_sound_design_map,
        "sfx_cues": sfx_cues,
        "ambience_beds": ambience_beds,
        "music_melodies": music_melodies,
    }
