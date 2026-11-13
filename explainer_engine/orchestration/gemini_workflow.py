#!/usr/bin/env python3
"""10-Gate Creator-Approved Production Workflow for Explainer Engine.

Integrates all existing explainer_engine research, sourced rules (BP-01..BP-170),
story/scene/narration/shot/motion/audio linters, Reference Library management,
parallel 10%/30%/60% visual pipelines, Wan 2.2 control & dialogue cost-quality rules,
and 3-minute chunked final assembly.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

@dataclass(frozen=True)
class GateSpec:
    gate_id: str
    order: int
    title_ka: str
    title_en: str
    engine_modules: List[str]
    sourced_rules: List[str]
    deliverables: List[str]
    requires_creator_approval: bool = True


TEN_GATE_PIPELINE: List[GateSpec] = [
    GateSpec(
        gate_id="G0_REFERENCE_LIBRARY",
        order=0,
        title_ka="ეტაპი 0: ვიზუალური სტილის შერჩევა და Reference Library-ს შექმნა",
        title_en="Gate 0: Style Selection & Persistent Reference Library",
        engine_modules=[
            "explainer_engine.assets",
            "explainer_engine.design",
            "explainer_engine.qa.keyframe_gate",
        ],
        sourced_rules=["D-80", "D-96", "D-123", "BP-167"],
        deliverables=[
            "reference_library/style_bible.json",
            "reference_library/anchors/character_turnarounds/",
            "reference_library/anchors/environment_lighting/",
            "reference_library/anchors/map_diagram_templates/",
        ],
    ),
    GateSpec(
        gate_id="G1_GENERAL_STORY",
        order=1,
        title_ka="ეტაპი 1: თემა -> კვლევა და ზოგადი ისტორია (Short Scenario)",
        title_en="Gate 1: Topic -> Research Dossier & General Story Scenario",
        engine_modules=[
            "explainer_engine.standards",
            "explainer_engine.scripting.variant_plan",
        ],
        sourced_rules=["OR-15", "OR-31", "ST-01", "ST-09", "BP-74", "BP-75"],
        deliverables=[
            "01_story/episode_rules.json",
            "01_story/claim_map.json",
            "01_story/general_story_scenario.md",
        ],
    ),
    GateSpec(
        gate_id="G2_NARRATIVE_SCRIPT",
        order=2,
        title_ka="ეტაპი 2: სრული ისტორიისა და დიალოგების სცენარი (Narrative Script)",
        title_en="Gate 2: Full Narrative & Character Dialogue Script",
        engine_modules=[
            "explainer_engine.scripting.story_lint",
            "explainer_engine.scripting.scene_lint",
            "explainer_engine.scripting.narration_lint",
            "explainer_engine.scripting.syllables",
            "explainer_engine.qa.engagement",
        ],
        sourced_rules=["ST-01..ST-19", "SC-01..SC-12", "D-84", "D-95", "BP-01", "BP-70..BP-73", "BP-87", "BP-88"],
        deliverables=[
            "02_script/narrative_script.md",
            "02_script/critic_review.json",
        ],
    ),
    GateSpec(
        gate_id="G3_VISUAL_AND_AUDIO_SCRIPT",
        order=3,
        title_ka="ეტაპი 3: ვიზუალის და აუდიოს დეტალური სცენარი (Visual & Audio Storyboard)",
        title_en="Gate 3: Visual Shot-by-Shot & Audio/SFX/Music Script",
        engine_modules=[
            "explainer_engine.production.validate",
            "explainer_engine.production.beats",
            "explainer_engine.scripting.shot_prompt_lint",
            "explainer_engine.edit.board",
            "explainer_engine.edit.motion_lint",
            "explainer_engine.audio.layers",
        ],
        sourced_rules=["KP-01..KP-62", "PV-01..PV-48", "MO-01..MO-07", "AL-01..AL-04", "D-97", "D-98"],
        deliverables=[
            "03_storyboard/production_script.json",
            "03_storyboard/visual_and_audio_script.md",
            "03_storyboard/asset_manifest.json",
        ],
    ),
    GateSpec(
        gate_id="G4_SFX_AMBIENCE_MUSIC",
        order=4,
        title_ka="ეტაპი 4: ხმოვანი ეფექტების (ნაბიჯები, გარემო) და მუსიკალური მელოდიების გენერაცია",
        title_en="Gate 4: SFX (Footsteps, Foley), Ambience Beds & Musical Melodies",
        engine_modules=[
            "explainer_engine.audio.layers",
            "explainer_engine.production.validate",
        ],
        sourced_rules=["AL-01..AL-04", "BP-54", "BP-62", "BP-65"],
        deliverables=[
            "04_audio_fx/sfx_pack/",
            "04_audio_fx/ambience_beds/",
            "04_audio_fx/music_stems/",
            "04_audio_fx/audio_fx_preview_mix.mp3",
        ],
    ),
    GateSpec(
        gate_id="G5_ALL_STILL_ASSETS_AND_KEYFRAMES",
        order=5,
        title_ka="ეტაპი 5: ყველა ფოტო-ასეტის გენერაცია (10% რუკები/დიაგრამები, 30% ფოტო-კოლაჟი, 60% ვიდეოს ფოტო-კადრები)",
        title_en="Gate 5: Full Visual Asset Generation (10% Maps/Diagrams, 30% layered collage Collage Stills, 60% Video Keyframes)",
        engine_modules=[
            "explainer_engine.maps",
            "explainer_engine.production.graphics",
            "explainer_engine.imagegen.plan",
            "explainer_engine.imagegen.routing",
            "explainer_engine.qa.keyframe_gate",
            "explainer_engine.qa.frame_review",
        ],
        sourced_rules=["KP-01..KP-62", "PP-01..PP-09", "D-97", "D-123"],
        deliverables=[
            "05_assets/10pct_maps_and_diagrams/",
            "05_assets/30pct_collage_stills/",
            "05_assets/60pct_video_keyframes/",
            "05_assets/contact_sheets_review.pdf",
        ],
    ),
    GateSpec(
        gate_id="G6_ELEVENLABS_VOICE_AND_SPINE",
        order=6,
        title_ka="ეტაპი 6: გმირების ხმების შერჩევა და ElevenLabs აუდიოს გენერაცია",
        title_en="Gate 6: Character Voice Casting & ElevenLabs Audio Spine Generation",
        engine_modules=[
            "explainer_engine.audio.casting",
            "explainer_engine.audio.voice_check",
            "explainer_engine.audio.scribe_words",
            "explainer_engine.production.timing",
        ],
        sourced_rules=["BP-01", "BP-105", "PV-20", "OR-19"],
        deliverables=[
            "06_voice/character_voice_candidates.json",
            "06_voice/narration_and_dialogue_master.wav",
            "06_voice/words.json",
            "06_voice/timed_script.json",
        ],
    ),
    GateSpec(
        gate_id="G7_PARALLEL_10_30_60_RENDER",
        order=7,
        title_ka="ეტაპი 7: პარალელური წარმოება (Thread A: 10% + 30% აწყობა | Thread B: 60% Wan 2.2 ვიდეო გენერაცია)",
        title_en="Gate 7: Parallel Track Execution (Thread A: 10% Helper + 30% layered collage Stills | Thread B: 60% Wan 2.2 Video Clips)",
        engine_modules=[
            "explainer_engine.production.graphics",
            "explainer_engine.edit.visual_compensator",
            "explainer_engine.aivideo.shotplan",
            "explainer_engine.aivideo.wan_runner",
            "explainer_engine.cloud.modal_run",   # the zip's modal_v4_worker was not ported (v4.3 P0.4); P6 adds the Wan adapter
        ],
        sourced_rules=["D-97", "D-98", "D-121", "D-123", "BP-109"],
        deliverables=[
            "07_renders/track_a_10pct_helpers/",
            "07_renders/track_a_30pct_25d_stills/",
            "07_renders/track_b_60pct_wan_clips/",
            "07_renders/render_telemetry.json",
        ],
    ),
    GateSpec(
        gate_id="G8_CHUNKED_3MIN_ASSEMBLY",
        order=8,
        title_ka="ეტაპი 8: საბოლოო მონტაჟი 3-წუთიანი ნაწილებით (Chunk 1..4) და დადასტურება",
        title_en="Gate 8: Final Assembly in ~3-Minute Review Chunks (0-3m, 3-6m, 6-9m, 9-12m)",
        engine_modules=[
            "explainer_engine.production.assemble",
            "explainer_engine.production.sample",
            "explainer_engine.qa.scorecard",
            "explainer_engine.qa.review_bundle",
        ],
        sourced_rules=["OR-19", "D-67", "BP-167", "BP-168", "PV-21..PV-36"],
        deliverables=[
            "08_assembly/chunk_01_00m_to_03m.mp4",
            "08_assembly/chunk_02_03m_to_06m.mp4",
            "08_assembly/chunk_03_06m_to_09m.mp4",
            "08_assembly/chunk_04_09m_to_12m.mp4",
            "08_assembly/final_master_12min.mp4",
            "08_assembly/qa_scorecard.json",
        ],
    ),
]


WAN22_CAPABILITY_MATRIX: Dict[str, object] = {
    "native_fps": 24,
    "optimal_clip_seconds": {
        "Wan2.2-I2V-A14B": {"sweet_spot_sec": 4.0, "max_clean_sec": 5.0, "frames_at_24fps": "81-121 frames"},
        "Wan2.2-FLF2V-14B (First-Last-Frame)": {"sweet_spot_sec": 4.0, "max_clean_sec": 5.0, "frames_at_24fps": "81-121 frames"},
        "Wan2.2-Fun-Control-14B (Depth/Canny/OpenPose)": {"sweet_spot_sec": 4.0, "max_clean_sec": 5.0, "frames_at_24fps": "81-121 frames"},
    },
    "hard_ceiling_rule": (
        "Never generate a single Wan 2.2 clip longer than 5.0-6.0 seconds (121-145 frames). "
        "Beyond 5 seconds, identity drift, background warping, and motion decay increase sharply. "
        "For a 12-second scene, chain 2-3 cuts (e.g., Wide Establisher 4s -> OTS Medium 4s -> Close-Up Reaction 4s) "
        "using FLF2V or multi-angle keyframes from the same anchor."
    ),
    "dialogue_rendering_policy": {
        "default_rule": "DO NOT use audio-driven lip-sync video generation for short turns (< 6s). Route speech through audio_lines[] over OTS / reaction / subtle posture movement (WAN_I2V or WAN_FLF2V with mouth closed or off-axis).",
        "when_rendered_lipsync_is_allowed": (
            "Use rendered lip-sync (Wan-S2V / InfiniteTalk / Fun-Control face region) ONLY when: "
            "(1) A single character delivers a pivotal dramatic monologue >= 8-12 seconds where cutting away weakens dramatic tension, "
            "(2) The character's face is in Medium Close-Up (MCU), AND "
            "(3) Cost/quality benchmark confirms 0 face-melt artifacts and lower cost than multi-angle shot-reverse-shot keyframes."
        ),
    },
}


def chunk_bounds_for_duration(total_seconds: float = 720.0, chunk_seconds: float = 180.0) -> List[Dict[str, float]]:
    """Split a 12-minute (720s) episode into ~3-minute (180s) approval chunks."""
    chunks: List[Dict[str, float]] = []
    start = 0.0
    idx = 1
    while start < total_seconds - 1e-6:
        end = min(total_seconds, start + chunk_seconds)
        chunks.append({
            "chunk_index": idx,
            "start_sec": round(start, 2),
            "end_sec": round(end, 2),
            "duration_sec": round(end - start, 2),
        })
        start = end
        idx += 1
    return chunks


if __name__ == "__main__":
    import json
    print(json.dumps({
        "gates": [asdict(g) for g in TEN_GATE_PIPELINE],
        "wan22_matrix": WAN22_CAPABILITY_MATRIX,
        "chunks_12min": chunk_bounds_for_duration(720.0, 180.0),
    }, indent=2, ensure_ascii=False))
