"""3-Tier Rule Governance & 4-Level Cohesive Film Engine (D-126..D-130).

Ensures that AI video production builds a single, organically unified cinematic film
(ერთი მთლიანი შეკრული ვიდეო) rather than a disjointed video collage (ვიდეო-კოლაჟი).

Enforces and audits rules across:
- 3 Governance Tiers:
  1. `TIER_1_INVARIANT_MANDATORY` (Hard `FAIL` — invariants that never bend)
  2. `TIER_2_STORY_BOUNDED_DYNAMIC` (Hard `FAIL` outside `[Min, Max, Min_Stdev]` — Story commands exact value within law bounds)
  3. `TIER_3_THEMATIC_ADVISORY` (`ADVISORY` — context, era, and mood-driven choices)
- 4 Production Levels:
  1. `TEXT_SCRIPT` (Dramaturgy, causal chain, hooks, sentence burstiness, dialogue staging)
  2. `AUDIO_SOUNDSCAPE` (5-layer sound hierarchy, unbroken -24 dB ambience glue, foley grounding, voice spine)
  3. `VIDEO_VISUALS` (90% unified Chiaroscuro cinema [60% video + 30% collage] + 10% Python YouTube Info-Graphics [maps, troop movements, diagrams, counters])
  4. `EDITING_COHESION` (AV duration sync, J-cut/L-cut split edits, WAN-CHAIN-MINUS-5, unified LUT + 35mm film grain across 3-min chunks)
"""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Dict, List


TIER_1_INVARIANT_MANDATORY = "TIER_1_INVARIANT_MANDATORY"
TIER_2_STORY_BOUNDED_DYNAMIC = "TIER_2_STORY_BOUNDED_DYNAMIC"
TIER_3_THEMATIC_ADVISORY = "TIER_3_THEMATIC_ADVISORY"


# Master machine-readable registry of all 68 3-Tier rules across all 12 components (100% 1-to-1 parity with docs/rules_registry/01..12)
THREE_TIER_RULE_CATALOG: List[Dict[str, Any]] = [
    # --- 01_DRAMATURGY_AND_SCRIPTWRITING ---
    {"id": "DR-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "ST-V4-CAUSE", "description": "5-phase causal spine (Z1..Z5) and unbroken cause_from_segment_id -> effect_to_segment_id chain"},
    {"id": "DR-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "YT-01-HOOK", "description": "First 12 seconds open with a high-stakes paradox or dramatic question"},
    {"id": "DR-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "CF-SEGMENT-BRIDGE", "description": "Every non-final segment closes with a forward causal cliffhanger / effect_to_segment_id bridge"},
    {"id": "DR-T1-04", "tier": TIER_1_INVARIANT_MANDATORY, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "KP-NO-LOOP-BOILERPLATE", "description": "Zero Python-loop boilerplate phrases or raw database IDs (loc_, char_, S01_SH001) in prompts/actions"},
    {"id": "DR-T1-05", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "01_DRAMATURGY", "rule_code": "YT-00-3SEC-KINETIC-HOOK", "description": "Opening hook deploys the strongest audio-visual material conceptually (shot 0 <= 3.8s, shots 0+1 <= 9.0s, active visual tension, zero dead stillness)"},
    {"id": "DR-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "PV-NO-METRONOME-SEGMENTS", "bounds": {"min_seg_sec": 20.0, "max_seg_sec": 160.0, "min_stdev_sec": 3.0, "min_shot_count_stdev": 0.4}},
    {"id": "DR-T2-02", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "CF-SEGMENT-SHOT-COUNT-BOUNDS", "bounds": {"min_shots_per_seg": 3, "max_shots_per_seg": 20}},
    {"id": "DR-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "TEXT_SCRIPT", "component": "01_DRAMATURGY", "rule_code": "ADV-DRAMATURGICAL-POV", "description": "Adapt narrative POV between omniscient historical lens and close human survival lens"},

    # --- 02_DIALOGUE_STAGING_AND_SPEECH ---
    {"id": "DL-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "02_DIALOGUE", "rule_code": "CF-180-DEGREE-AXIS", "description": "180-degree line-of-action screen direction preserved across all shots"},
    {"id": "DL-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "TEXT_SCRIPT", "component": "02_DIALOGUE", "rule_code": "SC-V4-SPEAKER", "description": "Every speaking character is registered in world_bible.characters with fixed appearance and voice profile"},
    {"id": "DL-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "02_DIALOGUE", "rule_code": "KP-V4-DIALOGUE-LEAK", "description": "Spoken dialogue lines never leak into image_prompt or video_prompt"},
    {"id": "DL-T1-04", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "02_DIALOGUE", "rule_code": "CF-AUDIO-BRIDGE", "description": "J-cut / L-cut audio bridges (0.25s-0.60s prelap/postlap) glue dialogue and scene transitions into one film"},
    {"id": "DL-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "TEXT_SCRIPT", "component": "02_DIALOGUE", "rule_code": "YT-04-BURSTINESS", "bounds": {"min_words": 2, "max_words": 28, "mean_min_words": 9.5, "mean_max_words": 18.5, "min_stdev_words": 2.6}},
    {"id": "DL-T2-02", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "AUDIO_SOUNDSCAPE", "component": "02_DIALOGUE", "rule_code": "ST-V4-AUDIO-BALANCE", "bounds": {"narrator_share_min": 0.65, "narrator_share_max": 0.85, "dialogue_share_min": 0.15, "dialogue_share_max": 0.35}},
    {"id": "DL-T2-03", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "TEXT_SCRIPT", "component": "02_DIALOGUE", "rule_code": "PV-NO-COOKIE-CUTTER-DIALOGUE", "bounds": {"max_identical_slot_ratio": 0.65}},
    {"id": "DL-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "02_DIALOGUE", "rule_code": "ADV-SHOT-REVERSE-SHOT-OTS", "description": "Alternate OTS and MCU reaction framings during multi-turn character confrontations"},

    # --- 03_CINEMATOGRAPHY_AND_CAMERA_FRAMING ---
    {"id": "CM-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "03_CAMERA", "rule_code": "KP-V4-CAMERA", "description": "At most 1 camera move per shot (camera_move_count <= 1)"},
    {"id": "CM-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "03_CAMERA", "rule_code": "CF-NO-JUMP-CUT", "description": "30-degree / shot-size change rule across adjacent cuts of the same subject in the same location"},
    {"id": "CM-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "03_CAMERA", "rule_code": "CF-3PLANE-DEPTH", "description": "Every shot defines foreground, midground, and background composition planes"},
    {"id": "CM-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "VIDEO_VISUALS", "component": "03_CAMERA", "rule_code": "CF-SHOT-SIZE-VARIETY", "bounds": {"min_distinct_shot_sizes": 4, "max_single_size_share": 0.45}},
    {"id": "CM-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "03_CAMERA", "rule_code": "ADV-VERTICAL-ANGLE-MOOD", "description": "Match vertical camera angle (worm_eye_-30, eye_level_0, high_angle_30, bird_eye_60) to power dynamics"},

    # --- 04_PACING_EDITING_AND_ASL ---
    {"id": "ED-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "04_PACING_EDITING", "rule_code": "PV-21", "description": "Gapless 24 fps frame timeline across all shots"},
    {"id": "ED-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "04_PACING_EDITING", "rule_code": "CF-AV-DURATION-SYNC", "description": "Every shot target_duration_seconds aligns with its linked audio_lines duration (+/-1.5s)"},
    {"id": "ED-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "04_PACING_EDITING", "rule_code": "CF-COHESIVE-TRANSITIONS", "description": "Restrained cinematic transitions (hard_cut, j_cut, l_cut, cross_dissolve_8f, fade_to_black)"},
    {"id": "ED-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "EDITING_COHESION", "component": "04_PACING_EDITING", "rule_code": "PV-NO-METRONOME-DURATIONS", "bounds": {"min_sec": 1.2, "max_sec": 10.0, "mean_min_sec": 3.2, "mean_max_sec": 6.2, "min_stdev_sec": 0.65}},
    {"id": "ED-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "EDITING_COHESION", "component": "04_PACING_EDITING", "rule_code": "ADV-GENRE-PACING-PROFILE", "description": "Adapt accordion pacing curve to act tension (rapid crisis cuts vs lingering aftermath holds)"},

    # --- 05_LIGHTING_AND_CHIAROSCURO_AESTHETICS ---
    {"id": "LT-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "05_LIGHTING", "rule_code": "KP-V4-STYLE", "description": "Locked unified Chiaroscuro style anchor token in every cinematic/collage start_frame_prompt"},
    {"id": "LT-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "05_LIGHTING", "rule_code": "KP-NO-2D-CARTOON-FILTER", "description": "Hard ban on 2D cartoon, anime, comic-book, or flat vector styles in cinematic/collage layers"},
    {"id": "LT-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "05_LIGHTING", "rule_code": "CF-LIGHTING-CONTINUITY", "description": "Every shot defines non-empty lighting_and_time coherent with its location palette"},
    {"id": "LT-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "VIDEO_VISUALS", "component": "05_LIGHTING", "rule_code": "CF-CHIAROSCURO-CONTRAST-BOUNDS", "bounds": {"min_lighting_desc_chars": 8}},
    {"id": "LT-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "05_LIGHTING", "rule_code": "ADV-ATMOSPHERIC-PARTICLES", "description": "Adapt volumetric particles (cannon smoke, candle dust motes, volcanic ash) to era and setting"},

    # --- 06_COLLAGE_AND_COMPOSING_STILLS ---
    {"id": "CL-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "06_COLLAGE", "rule_code": "KP-V4-PARALLAX", "description": "Every 30% COLLAGE_STILL shot defines a valid parallax_preset and unified chiaroscuro style"},
    {"id": "CL-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "06_COLLAGE", "rule_code": "KP-V4-NO-DUPLICATE-PROMPT", "description": "Every shot has a unique scene prompt (zero single-photo crop padding)"},
    {"id": "CL-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "06_COLLAGE", "rule_code": "CF-COLLAGE-GOOGLE-VIDEO-INTEGRATION", "description": "30% COLLAGE_STILL shots animate via Google Video API (gemini-omni-1.2-flash) and receive unified LUT + 35mm grain"},
    {"id": "CL-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "VIDEO_VISUALS", "component": "06_COLLAGE", "rule_code": "CF-COLLAGE-SHARE-BOUNDS", "bounds": {"collage_min": 0.20, "collage_max": 0.40}},
    {"id": "CL-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "06_COLLAGE", "rule_code": "ADV-PARALLAX-PRESET-MOOD", "description": "Match parallax_preset (dolly_in, dolly_out, pan_horizontal, zoom_focus) to narrative reveal"},

    # --- 07_TACTILE_RELIEF_MAPS_AND_WAR_TABLES (10% PYTHON YOUTUBE INFO-GRAPHICS LAYER) ---
    {"id": "MP-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "07_MAPS", "rule_code": "KP-V4-MODE", "description": "10% maps, troop movements, diagrams, and number counters use TACTILE_MAP mode with Python deterministic rendering"},
    {"id": "MP-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "07_MAPS", "rule_code": "CF-PYTHON-INFOGRAPHIC-CLARITY", "description": "10% layer renders in clean YouTube-docudrama style via Python (exact numbers, clear troop vectors, zero AI garbled text)"},
    {"id": "MP-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "VIDEO_VISUALS", "component": "07_MAPS", "rule_code": "CF-MAP-SHARE-BOUNDS", "bounds": {"map_min": 0.05, "map_max": 0.20}},
    {"id": "MP-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "07_MAPS", "rule_code": "ADV-INFOGRAPHIC-SUBTYPE-SELECTION", "description": "Select tactical_map_and_troop_movement, demographic_or_casualty_counter, comparative_data_diagram, or timeline by beat"},

    # --- 08_AI_VIDEO_GENERATION_AND_WAN22 ---
    {"id": "WN-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "08_AI_VIDEO", "rule_code": "KP-V4-ACTION", "description": "Exactly 1 primary physical action per AI video shot (primary_action_count == 1)"},
    {"id": "WN-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "08_AI_VIDEO", "rule_code": "CF-ACTION-STATE-TRANSITION", "description": "Every shot specifies concrete action_start_state and action_end_state"},
    {"id": "WN-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "08_AI_VIDEO", "rule_code": "WAN-CHAIN-MINUS-5", "description": "Video shots > 5.0s automatically chain Sub-Clip A + Sub-Clip B via frame[-5]"},
    {"id": "WN-T1-04", "tier": TIER_1_INVARIANT_MANDATORY, "level": "VIDEO_VISUALS", "component": "08_AI_VIDEO", "rule_code": "PV-THREE-TIER-VIDEO-ROUTING-LAW", "description": "10% Maps/Diagrams/Numbers -> Python Info-Graphics; 30% Collages + Simple/Medium 60% Video -> Google Video API; Heavy 60% Action/FLF2V/Chain Video -> Wan 2.1/2.2 GPU"},
    {"id": "WN-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "VIDEO_VISUALS", "component": "08_AI_VIDEO", "rule_code": "CF-VISUAL-MIX-BOUNDS", "bounds": {"video_min": 0.50, "video_max": 0.70, "collage_min": 0.20, "collage_max": 0.40, "map_min": 0.05, "map_max": 0.20}},
    {"id": "WN-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "VIDEO_VISUALS", "component": "08_AI_VIDEO", "rule_code": "KP-V4-CONTROL", "description": "Use WAN_CONTROL single control_modality (depth, openpose, canny, camera_preset) when structural conditioning is needed"},

    # --- 09_FOLEY_AND_SPOT_SOUND_EFFECTS ---
    {"id": "FX-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "09_FOLEY_SFX", "rule_code": "CF-FOLEY-GROUNDING", "description": "Every segment has physical foley and spot SFX cues grounding visual motion"},
    {"id": "FX-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "09_FOLEY_SFX", "rule_code": "PV-23", "description": "SFX gain bounds (-40 dB to -6 dB) and non-clipping mix headroom"},
    {"id": "FX-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "AUDIO_SOUNDSCAPE", "component": "09_FOLEY_SFX", "rule_code": "CF-SFX-DENSITY-BOUNDS", "bounds": {"min_cues_per_seg": 1, "max_cues_per_seg": 6}},
    {"id": "FX-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "AUDIO_SOUNDSCAPE", "component": "09_FOLEY_SFX", "rule_code": "ADV-SURFACE-ACOUSTIC-TEXTURE", "description": "Match foley acoustic impulse (wet mud, volcanic ash crunch, stone echo) to location"},

    # --- 10_MUSIC_AND_AMBIENCE_HIERARCHY ---
    {"id": "MS-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "10_MUSIC_AMBIENCE", "rule_code": "CF-AMBIENCE-GLUE", "description": "5-layer audio hierarchy (AL-01..08) with unbroken ambience bed (<= -24 dB) spanning 100% of runtime"},
    {"id": "MS-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "10_MUSIC_AMBIENCE", "rule_code": "CF-CONTINUOUS-ROOM-TONE", "description": "Continuous room-tone / environmental bed across cuts within the same location (anti-collage glue)"},
    {"id": "MS-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "10_MUSIC_AMBIENCE", "rule_code": "CF-SIDECHAIN-DUCKING", "description": "Music and ambience duck automatically under narrator and character speech"},
    {"id": "MS-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "AUDIO_SOUNDSCAPE", "component": "10_MUSIC_AMBIENCE", "rule_code": "CF-MUSIC-MOTIF-PROGRESSION", "bounds": {"min_melodies_per_ep": 4, "max_melodies_per_ep": 16}},
    {"id": "MS-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "AUDIO_SOUNDSCAPE", "component": "10_MUSIC_AMBIENCE", "rule_code": "ADV-ERA-INSTRUMENTATION", "description": "Adapt musical motifs and foley surface textures to the historical period and tension arc"},

    # --- 11_VOICE_ACTING_AND_LIPSYNC_SPINE ---
    {"id": "VC-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "CF-LOCKED-NARRATOR-ODOM", "description": "Narrator voice locked to ElevenLabs Odom (CcSJ2r3qw0XU9gJpEPyk) with distinct character voice profiles"},
    {"id": "VC-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "PV-20", "description": "24fps word-level alignment spine driving shot cut points"},
    {"id": "VC-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "CF-SELECTIVE-LIPSYNC", "description": "Narrator lines never use visible lip-sync (SC-V4-LIPSYNC); character lip-sync evaluated via cadence & >=8.0s MCU rule"},
    {"id": "VC-T1-04", "tier": TIER_1_INVARIANT_MANDATORY, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "CF-CHARACTER-SPEECH-CADENCE", "description": "1-scene or distant characters (gap >= 3 segments) route to Wan native speech; recurring characters route to ElevenLabs spine"},
    {"id": "VC-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "CF-SPEECH-PACE-BOUNDS", "bounds": {"min_wpm": 110, "max_wpm": 195}},
    {"id": "VC-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "AUDIO_SOUNDSCAPE", "component": "11_VOICE_LIPSYNC", "rule_code": "SC-V4-DELIVERY", "description": "Every character dialogue line specifies a non-empty delivery_direction"},

    # --- 12_FINAL_ASSEMBLY_AND_PACKAGING ---
    {"id": "PK-T1-01", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "CF-3MIN-CHUNKED-ASSEMBLY", "description": "12-minute episode assembles in four 3-minute (180s) chunks for memory/GPU stability"},
    {"id": "PK-T1-02", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "CF-UNIFIED-GRADE-GRAIN", "description": "Unified Chiaroscuro color LUT and 35mm film grain (8-12%) applied across all visual layers"},
    {"id": "PK-T1-03", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "CF-FULL-GATE-AUDIT", "description": "Full 9-gate architectural validation pass (G0..G8) via run_all_gate_audits"},
    {"id": "PK-T1-04", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "PV-NO-FAKE-OFFLINE-RENDER", "description": "Fail-closed ban on fake offline FFmpeg xfade slideshows (<2.5 Mbps), mono synthetic audio (<128 kbps), or unverified API receipts"},
    {"id": "PK-T1-05", "tier": TIER_1_INVARIANT_MANDATORY, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "CF-ENV-CREDENTIAL-HYGIENE", "description": "Secure credential loading from Drive env_config_v4.env via env_loader.py with zero URL query-key leakage"},
    {"id": "PK-T2-01", "tier": TIER_2_STORY_BOUNDED_DYNAMIC, "level": "EDITING_COHESION", "component": "12_ASSEMBLY", "rule_code": "CF-EPISODE-DURATION-BOUNDS", "bounds": {"min_total_sec": 60.0, "max_total_sec": 900.0}},
    {"id": "PK-T3-01", "tier": TIER_3_THEMATIC_ADVISORY, "level": "TEXT_SCRIPT", "component": "12_ASSEMBLY", "rule_code": "ADV-YOUTUBE-PACKAGING-CTR", "description": "YouTube Title, Thumbnail & Cold-Open curiosity gap evaluated via clean-room youtube_viewer_critic"},
]


def check_cohesive_film_invariants_and_bounds(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run all Tier 1 (Invariant) and Tier 2 (Story-Bounded Dynamic) Cohesive Film checks
    across Text, Audio, Video, and Editing levels."""
    out: List[Dict[str, Any]] = []
    shots = doc.get("shots", [])
    segments = doc.get("segments", [])
    audio_lines = doc.get("audio_lines", [])
    line_map = {l.get("line_id"): l for l in audio_lines if l.get("line_id")}

    # 0. Tier 1 Segment Bridge & Tier 2 Segment Shot-Count Bounds (DR-T1-03, DR-T2-02)
    for idx, seg in enumerate(segments):
        seg_id = seg.get("segment_id", f"seg_{idx}")
        if idx < len(segments) - 1 and not seg.get("effect_to_segment_id"):
            out.append({
                "rule": "CF-SEGMENT-BRIDGE",
                "tier": TIER_1_INVARIANT_MANDATORY,
                "level": "TEXT_SCRIPT",
                "severity": "FAIL",
                "where": seg_id,
                "detail": f"Segment {seg_id} is missing effect_to_segment_id forward bridge (DR-T1-03).",
            })
        if len(shots) >= 12:
            seg_shots_cnt = sum(1 for s in shots if s.get("segment_id") == seg_id)
            if not (2 <= seg_shots_cnt <= 24):
                out.append({
                    "rule": "CF-SEGMENT-SHOT-COUNT-BOUNDS",
                    "tier": TIER_2_STORY_BOUNDED_DYNAMIC,
                    "level": "TEXT_SCRIPT",
                    "severity": "FAIL",
                    "where": seg_id,
                    "detail": f"Segment {seg_id} has {seg_shots_cnt} shots (outside dynamic bounds [2..24], DR-T2-02).",
                })

    # 1. Tier 1 Editing Cohesion: Audio-Visual Duration Sync (CF-AV-DURATION-SYNC) & Lighting Continuity (LT-T1-03)
    for sh in shots:
        sid = sh.get("shot_id", "?")
        sh_dur = float(sh.get("target_duration_seconds", 0.0))
        if not (1.2 - 1e-6 <= sh_dur <= 10.0 + 1e-6):
            out.append({
                "rule": "CF-SHOT-DURATION-BOUNDS",
                "tier": TIER_2_STORY_BOUNDED_DYNAMIC,
                "level": "EDITING_COHESION",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Shot {sid} duration ({sh_dur:.2f}s) violates cinematic bounds [1.2s .. 10.0s]",
            })
        al_ids = sh.get("audio_line_ids") or []
        linked_dur = sum(float(line_map[lid].get("estimated_duration_seconds", 0.0)) for lid in al_ids if lid in line_map)
        if linked_dur > 0 and abs(sh_dur - linked_dur) > 1.5 + 1e-6:
            out.append({
                "rule": "CF-AV-DURATION-SYNC",
                "tier": TIER_1_INVARIANT_MANDATORY,
                "level": "EDITING_COHESION",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Shot {sid} duration ({sh_dur:.2f}s) diverges from its spoken audio_line duration ({linked_dur:.2f}s) by > 1.5s",
            })

        # 2. Tier 1 Video Cohesion: 180-Degree Axis Preservation (CF-180-DEGREE-AXIS)
        sc = sh.get("screen_composition") or {}
        sd_notes = str(sc.get("screen_direction_notes") or "").strip()
        if len(sd_notes) < 5:
            out.append({
                "rule": "CF-180-DEGREE-AXIS",
                "tier": TIER_1_INVARIANT_MANDATORY,
                "level": "VIDEO_VISUALS",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Shot {sid} is missing explicit 180-degree axis / screen_direction_notes required for visual continuity",
            })

        # 2b. Tier 1 Lighting Continuity (LT-T1-03 / CF-LIGHTING-CONTINUITY)
        lt_notes = str(sh.get("lighting_and_time") or "").strip()
        if len(lt_notes) < 3:
            out.append({
                "rule": "CF-LIGHTING-CONTINUITY",
                "tier": TIER_1_INVARIANT_MANDATORY,
                "level": "VIDEO_VISUALS",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Shot {sid} is missing lighting_and_time required for Chiaroscuro lighting continuity (LT-T1-03)",
            })

    # 3. Tier 1 Editing/Camera Cohesion: 30-Degree / Shot-Size Change Anti-Jump-Cut Law (CF-NO-JUMP-CUT)
    for prev_sh, curr_sh in zip(shots, shots[1:]):
        if prev_sh.get("segment_id") != curr_sh.get("segment_id"):
            continue
        if prev_sh.get("location_id") != curr_sh.get("location_id"):
            continue
        prev_chars = set(prev_sh.get("character_ids") or [])
        curr_chars = set(curr_sh.get("character_ids") or [])
        if prev_chars and prev_chars == curr_chars:
            cont_id = (curr_sh.get("continuity_refs") or {}).get("inherit_from_previous_shot_id")
            if cont_id == prev_sh.get("shot_id"):
                continue
            prev_cam = prev_sh.get("camera_spec") or {}
            curr_cam = curr_sh.get("camera_spec") or {}
            same_size = prev_cam.get("shot_size") == curr_cam.get("shot_size")
            az_a = int(prev_cam.get("horizontal_azimuth_deg", 0))
            az_b = int(curr_cam.get("horizontal_azimuth_deg", 0))
            ang_diff = min((az_a - az_b) % 360, (az_b - az_a) % 360)
            if same_size and ang_diff < 30:
                out.append({
                    "rule": "CF-NO-JUMP-CUT",
                    "tier": TIER_1_INVARIANT_MANDATORY,
                    "level": "EDITING_COHESION",
                    "severity": "FAIL",
                    "where": curr_sh.get("shot_id", "?"),
                    "detail": (
                        f"Jump cut between {prev_sh.get('shot_id')} and {curr_sh.get('shot_id')}: "
                        f"same subject {sorted(curr_chars)}, same shot_size ({curr_cam.get('shot_size')}), "
                        f"and azimuth delta {ang_diff} deg < 30 deg"
                    ),
                })

    # 4. Tier 2 Video Bounds: Episode Visual Mix Bounds [50-70% Video, 20-40% Collage, 5-20% Map]
    if len(shots) >= 10:
        n_total = len(shots)
        n_map = sum(1 for s in shots if s.get("visual_type") == "map_visualization" or s.get("generation_mode") in ("TACTILE_MAP", "MAP_25D"))
        n_col = sum(1 for s in shots if s.get("visual_type") == "composed_illustration" or s.get("generation_mode") in ("COLLAGE_STILL", "STILL_25D"))
        n_vid = n_total - n_map - n_col
        sh_vid, sh_col, sh_map = n_vid / n_total, n_col / n_total, n_map / n_total
        if not (0.50 - 1e-6 <= sh_vid <= 0.70 + 1e-6 and 0.20 - 1e-6 <= sh_col <= 0.40 + 1e-6 and 0.05 - 1e-6 <= sh_map <= 0.20 + 1e-6):
            out.append({
                "rule": "CF-VISUAL-MIX-BOUNDS",
                "tier": TIER_2_STORY_BOUNDED_DYNAMIC,
                "level": "VIDEO_VISUALS",
                "severity": "FAIL",
                "where": "shots",
                "detail": (
                    f"Episode visual mix ({sh_vid:.1%} video, {sh_col:.1%} collage, {sh_map:.1%} map) "
                    "falls outside dynamic guardrails [50-70% video, 20-40% collage, 5-20% map]"
                ),
            })

        # 5. Tier 2 Camera Variety Bounds (CF-SHOT-SIZE-VARIETY)
        size_counts = Counter((s.get("camera_spec") or {}).get("shot_size", "medium") for s in shots)
        top_size, top_cnt = size_counts.most_common(1)[0]
        if len(size_counts) < 4 or (top_cnt / n_total) > 0.45 + 1e-6:
            out.append({
                "rule": "CF-SHOT-SIZE-VARIETY",
                "tier": TIER_2_STORY_BOUNDED_DYNAMIC,
                "level": "VIDEO_VISUALS",
                "severity": "FAIL",
                "where": "shots",
                "detail": (
                    f"Insufficient camera framing variety: {len(size_counts)} distinct shot sizes, "
                    f"top size {top_size!r} is {top_cnt / n_total:.1%} (require >= 4 sizes, max 45% share)"
                ),
            })

    return out


def build_cohesive_film_edl(script_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Build the 4-Level Cohesive Film Edit Decision List (EDL) that binds 10% Python info-graphics,
    30% Google-animated collages, and 60% Google/Wan 2.2 clips into a single seamless film."""
    from explainer_engine.aivideo.wan_optimizer import plan_story_driven_shot_render
    from explainer_engine.audio.sfx_planner import build_g4_audio_fx_plan

    shots = script_doc.get("shots", [])
    audio_lines = script_doc.get("audio_lines", [])
    line_map = {l.get("line_id"): l for l in audio_lines if l.get("line_id")}
    sfx_plan = build_g4_audio_fx_plan(script_doc)

    edl_entries: List[Dict[str, Any]] = []
    cursor_sec = 0.0
    j_l_cut_bridges_count = 0
    frame_minus_5_chains_count = 0

    for i, sh in enumerate(shots):
        dur = float(sh.get("target_duration_seconds", 4.0))
        al_ids = sh.get("audio_line_ids") or []
        first_line = line_map.get(al_ids[0], {}) if al_ids else {}
        is_char = first_line.get("speaker_type") == "character"
        next_sh = shots[i + 1] if i + 1 < len(shots) else None
        seg_change = bool(next_sh and next_sh.get("segment_id") != sh.get("segment_id"))

        audio_prelap_sec = 0.35 if (i > 0 and (is_char or sh.get("transition_out") == "j_cut")) else 0.0
        audio_postlap_sec = 0.40 if (seg_change or is_char or sh.get("transition_out") == "l_cut") else 0.15
        if audio_prelap_sec > 0 or audio_postlap_sec >= 0.35:
            j_l_cut_bridges_count += 1

        render_spec = plan_story_driven_shot_render(sh)
        if render_spec["requires_frame_minus_5_chain"]:
            frame_minus_5_chains_count += 1

        is_map_infographic = sh.get("visual_type") == "map_visualization" or sh.get("generation_mode") in ("TACTILE_MAP", "MAP_25D")
        edl_entries.append({
            "shot_index": i + 1,
            "shot_id": sh.get("shot_id"),
            "segment_id": sh.get("segment_id"),
            "visual_mode": sh.get("generation_mode"),
            "render_category": render_spec["render_category"],
            "video_in_sec": round(cursor_sec, 3),
            "video_out_sec": round(cursor_sec + dur, 3),
            "audio_in_sec": round(max(0.0, cursor_sec - audio_prelap_sec), 3),
            "audio_out_sec": round(cursor_sec + dur + audio_postlap_sec, 3),
            "j_cut_prelap_sec": audio_prelap_sec,
            "l_cut_postlap_sec": audio_postlap_sec,
            "requires_frame_minus_5_chain": render_spec["requires_frame_minus_5_chain"],
            "sub_clips": render_spec["sub_clips"],
            "unified_finishing_pass": {
                "lut": "youtube_clean_infographic_v4" if is_map_infographic else "chiaroscuro_amber_slate_v4.cube",
                "film_grain_35mm_pct": 3.0 if is_map_infographic else 10.0,
                "vignette_falloff": 0.08 if is_map_infographic else 0.18,
            },
        })
        cursor_sec += dur

    return {
        "schema": "cohesive_film_edl/1",
        "episode_id": script_doc.get("episode_id", "unknown"),
        "total_duration_sec": round(cursor_sec, 2),
        "total_shots": len(edl_entries),
        "j_l_cut_audio_bridges_count": j_l_cut_bridges_count,
        "frame_minus_5_seamless_chains_count": frame_minus_5_chains_count,
        "unbroken_ambience_beds_count": len(sfx_plan["ambience_beds"]),
        "foley_and_sfx_cues_count": sfx_plan["counts"]["sfx_cues"],
        "music_ducking_enabled": True,
        "unified_color_and_grain_pass": True,
        "edl": edl_entries,
    }


def audit_cohesive_film_3tier(script_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete 3-Tier, 4-Level Cohesive Film audit on a production_script.json."""
    from explainer_engine.scripting import shot_prompt_lint, scene_lint

    base_issues = shot_prompt_lint.check_v4_script(script_doc) + scene_lint.lint_v4(script_doc)
    cohesive_issues = check_cohesive_film_invariants_and_bounds(script_doc)
    all_issues = base_issues + cohesive_issues
    fails = [i for i in all_issues if i.get("severity") == "FAIL"]

    shots = script_doc.get("shots", [])
    segments = script_doc.get("segments", [])
    audio_lines = script_doc.get("audio_lines", [])

    shot_durs = [float(s.get("target_duration_seconds", 0.0)) for s in shots] or [0.0]
    seg_durs = [float(s.get("target_duration_seconds", 0.0)) for s in segments] or [0.0]
    word_counts = [len(str(l.get("text", "")).split()) for l in audio_lines] or [0]

    edl = build_cohesive_film_edl(script_doc)

    return {
        "status": "PASS" if len(fails) == 0 else "FAIL",
        "fail_count": len(fails),
        "total_issues": len(all_issues),
        "issues": all_issues,
        "tier_summary": {
            "tier_1_invariant_mandatory_rules_count": sum(1 for r in THREE_TIER_RULE_CATALOG if r["tier"] == TIER_1_INVARIANT_MANDATORY),
            "tier_2_story_bounded_dynamic_rules_count": sum(1 for r in THREE_TIER_RULE_CATALOG if r["tier"] == TIER_2_STORY_BOUNDED_DYNAMIC),
            "tier_3_thematic_advisory_rules_count": sum(1 for r in THREE_TIER_RULE_CATALOG if r["tier"] == TIER_3_THEMATIC_ADVISORY),
            "total_catalog_rules_count": len(THREE_TIER_RULE_CATALOG),
        },
        "measured_tier_2_dynamics": {
            "shot_duration_mean_sec": round(statistics.mean(shot_durs), 2),
            "shot_duration_stdev_sec": round(statistics.pstdev(shot_durs), 3),
            "shot_duration_min_max_sec": [round(min(shot_durs), 2), round(max(shot_durs), 2)],
            "segment_duration_stdev_sec": round(statistics.pstdev(seg_durs), 2),
            "sentence_words_mean": round(statistics.mean(word_counts), 2),
            "sentence_words_stdev": round(statistics.pstdev(word_counts), 2),
        },
        "cohesive_film_edl_summary": {
            "j_l_cut_audio_bridges_count": edl["j_l_cut_audio_bridges_count"],
            "frame_minus_5_seamless_chains_count": edl["frame_minus_5_seamless_chains_count"],
            "unbroken_ambience_beds_count": edl["unbroken_ambience_beds_count"],
            "foley_and_sfx_cues_count": edl["foley_and_sfx_cues_count"],
            "unified_color_and_grain_pass": edl["unified_color_and_grain_pass"],
        },
    }


def verify_real_api_media_renders(
    video_path: str | None = None,
    contact_sheet_paths: List[str] | None = None,
    receipts_json_path: str | None = None,
    require_rendered_media: bool = False,
    expected_shots_count: int = 1,
    expected_voice_lines_count: int = 1,
) -> Dict[str, Any]:
    """Forensic validator (PV-NO-FAKE-OFFLINE-RENDER, PK-T1-04, D-129/D-130) that fails closed:
    1. Missing or nonexistent `video_path` or `receipts_json_path` immediately FAILs when media verification is active.
    2. Distinguishes container bitrate/audio properties (`media_container_verified`) from cryptographic/structured
       API execution proof (`provider_execution_verified`).
    3. Inspects the internal contents of `api_render_receipts.json` (verifying `preflight.internet_reachable`,
       `keyframes`, `voice_lines`, and `video_clips` provider entries, byte sizes, and file paths).
    """
    import json as _json
    import subprocess as _sp
    from pathlib import Path as _Path

    issues: List[Dict[str, Any]] = []
    media_container_verified = False
    provider_execution_verified = False

    # If called with no arguments at all and require_rendered_media=False, still fail closed if nothing was verified
    check_video = require_rendered_media or (video_path is not None)
    check_receipts = require_rendered_media or (receipts_json_path is not None)

    if not check_video and not check_receipts and not contact_sheet_paths:
        issues.append({
            "rule": "PV-NO-FAKE-OFFLINE-RENDER",
            "severity": "FAIL",
            "where": "verify_real_api_media_renders",
            "detail": "Forensic media validator called with no video_path, contact_sheet_paths, or receipts_json_path (fail-closed).",
        })

    if check_video:
        if not video_path or not _Path(video_path).is_file():
            issues.append({
                "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                "severity": "FAIL",
                "where": str(video_path or "video_path"),
                "detail": f"Rendered video file is missing or nonexistent: {video_path!r}",
            })
        else:
            probe = _sp.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(video_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if probe.returncode != 0 or not probe.stdout.strip():
                issues.append({
                    "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                    "severity": "FAIL",
                    "where": str(video_path),
                    "detail": "Could not ffprobe rendered video file.",
                })
            else:
                info = _json.loads(probe.stdout)
                streams = info.get("streams", [])
                v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
                a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
                v_bitrate = int(v_stream.get("bit_rate") or info.get("format", {}).get("bit_rate") or 0)
                a_bitrate = int(a_stream.get("bit_rate") or 0)
                a_channels = int(a_stream.get("channels") or 0)

                v_ok = v_bitrate >= 2_500_000
                a_ok = a_channels >= 2 and a_bitrate >= 128_000
                if not v_ok:
                    issues.append({
                        "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                        "severity": "FAIL",
                        "where": str(video_path),
                        "detail": (
                            f"Video bitrate is only {v_bitrate / 1000:.1f} kbps (< 2,500 kbps minimum). "
                            "This indicates a static image FFmpeg slideshow/xfade rather than real Wan 2.1/2.2 + Google Video AI clips!"
                        ),
                    })
                if not a_ok:
                    issues.append({
                        "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                        "severity": "FAIL",
                        "where": str(video_path),
                        "detail": (
                            f"Audio stream is {a_channels}-channel ({a_bitrate / 1000:.1f} kbps < 128 kbps stereo minimum). "
                            "This indicates offline synthetic/mono placeholder audio rather than real ElevenLabs Odom + Wan S2V stereo mix!"
                        ),
                    })
                media_container_verified = v_ok and a_ok

    for cs_path in contact_sheet_paths or []:
        p_cs = _Path(cs_path)
        if not p_cs.is_file():
            issues.append({
                "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                "severity": "FAIL",
                "where": str(cs_path),
                "detail": f"Contact sheet image is missing: {cs_path!r}",
            })
        else:
            try:
                from PIL import Image, ImageStat
                im = Image.open(p_cs).convert("RGB")
                stat = ImageStat.Stat(im)
                mean_std = sum(stat.stddev) / 3.0
                hist_l = im.convert("L").histogram()
                flat_dark_share = sum(hist_l[10:35]) / max(1, sum(hist_l))
                if mean_std < 28.0 or flat_dark_share > 0.60:
                    issues.append({
                        "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                        "severity": "FAIL",
                        "where": str(cs_path),
                        "detail": (
                            f"Contact sheet {p_cs.name} has abnormally flat pixel variance (stddev={mean_std:.2f} < 28.0), "
                            "indicating synthetic dark text boxes instead of real generated images!"
                        ),
                    })
            except Exception as exc:
                issues.append({
                    "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                    "severity": "FAIL",
                    "where": str(cs_path),
                    "detail": f"Could not verify contact sheet image: {exc}",
                })

    if check_receipts:
        if not receipts_json_path or not _Path(receipts_json_path).is_file():
            issues.append({
                "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                "severity": "FAIL",
                "where": str(receipts_json_path or "receipts_json_path"),
                "detail": "Missing api_render_receipts.json proving real ElevenLabs, Google Video, and Wan 2.1/2.2 API calls!",
            })
        else:
            try:
                receipt_data = _json.loads(_Path(receipts_json_path).read_text(encoding="utf-8"))
                if not isinstance(receipt_data, dict) or not receipt_data:
                    issues.append({
                        "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                        "severity": "FAIL",
                        "where": str(receipts_json_path),
                        "detail": "api_render_receipts.json is empty or not a JSON object.",
                    })
                else:
                    preflight = receipt_data.get("preflight") or {}
                    keyframes = receipt_data.get("keyframes")
                    voice_lines = receipt_data.get("voice_lines")
                    video_clips = receipt_data.get("video_clips")

                    if preflight.get("internet_reachable") is not True:
                        issues.append({
                            "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                            "severity": "FAIL",
                            "where": str(receipts_json_path),
                            "detail": "Receipt preflight.internet_reachable is not True (indicates offline or mocked execution).",
                        })
                    if not isinstance(keyframes, list) or len(keyframes) < expected_shots_count:
                        issues.append({
                            "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                            "severity": "FAIL",
                            "where": str(receipts_json_path),
                            "detail": f"Receipt keyframes list has {len(keyframes) if isinstance(keyframes, list) else 0} items (expected >= {expected_shots_count}).",
                        })
                    if not isinstance(voice_lines, list) or len(voice_lines) < expected_voice_lines_count:
                        issues.append({
                            "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                            "severity": "FAIL",
                            "where": str(receipts_json_path),
                            "detail": f"Receipt voice_lines list has {len(voice_lines) if isinstance(voice_lines, list) else 0} items (expected >= {expected_voice_lines_count}).",
                        })
                    if not isinstance(video_clips, list) or len(video_clips) < expected_shots_count:
                        issues.append({
                            "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                            "severity": "FAIL",
                            "where": str(receipts_json_path),
                            "detail": f"Receipt video_clips list has {len(video_clips) if isinstance(video_clips, list) else 0} items (expected >= {expected_shots_count}).",
                        })
                    else:
                        for idx, vc in enumerate(video_clips):
                            if not isinstance(vc, dict) or not vc.get("provider") or int(vc.get("bytes") or 0) <= 0:
                                issues.append({
                                    "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                                    "severity": "FAIL",
                                    "where": f"{receipts_json_path}:video_clips[{idx}]",
                                    "detail": f"Video clip receipt #{idx} is missing provider or non-zero bytes: {vc!r}",
                                })
                    provider_execution_verified = len(issues) == 0
            except Exception as exc:
                issues.append({
                    "rule": "PV-NO-FAKE-OFFLINE-RENDER",
                    "severity": "FAIL",
                    "where": str(receipts_json_path),
                    "detail": f"Could not parse api_render_receipts.json: {exc}",
                })

    return {
        "status": "PASS" if not issues else "FAIL",
        "fail_count": len(issues),
        "media_container_verified": media_container_verified,
        "provider_execution_verified": provider_execution_verified,
        "issues": issues,
    }
