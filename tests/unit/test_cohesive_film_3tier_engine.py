"""Unit tests for the 3-Tier Rule Governance & 4-Level Cohesive Film Engine (D-126).

Tests:
1. Tier 1 Invariant Mandatory Laws across Text, Audio, Video, and Editing (including CF-NO-JUMP-CUT,
   CF-AV-DURATION-SYNC, CF-180-DEGREE-AXIS, WAN-CHAIN-MINUS-5, J/L-Cut audio bridges, unbroken ambience).
2. Tier 2 Story-Bounded Dynamic Laws (Accordion Pacing shot duration bounds + stdev, sentence burstiness,
   unequal segment lengths, episode visual mix [50-70% / 20-40% / 5-20%], shot size variety).
3. Tier 3 Thematic Advisory catalog completeness across all 12 rulebook components.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from explainer_engine.orchestration.cohesive_film_engine import (
    THREE_TIER_RULE_CATALOG,
    TIER_1_INVARIANT_MANDATORY,
    TIER_2_STORY_BOUNDED_DYNAMIC,
    TIER_3_THEMATIC_ADVISORY,
    audit_cohesive_film_3tier,
    build_cohesive_film_edl,
    check_cohesive_film_invariants_and_bounds,
)

ROOT = Path(__file__).resolve().parents[2]

def _need(path: Path) -> Path:
    """The Waterloo 12-minute script came with neither the v4.2 nor the v4.3 archive (v4.3 P0.4, 2026-11-12): a test that reads
    it says so instead of failing on a missing file; restore ``jobs/ep_waterloo_12min/production_script.json`` to run it."""
    import pytest
    if not Path(path).exists():
        pytest.skip(f"missing input {Path(path).relative_to(Path(__file__).resolve().parents[2])} (not in the v4.3 archive)")
    return Path(path)



def test_12_rulebook_files_and_3tier_catalog_exist() -> None:
    reg_dir = ROOT / "docs/rules_registry"
    md_files = sorted(p.name for p in reg_dir.glob("*.md"))
    assert len(md_files) == 13  # 00_MASTER_INDEX + 01..12 component rulebooks
    for f in md_files[1:]:
        txt = (reg_dir / f).read_text(encoding="utf-8")
        assert "TIER_1_INVARIANT_MANDATORY" in txt
        assert "TIER_2_STORY_BOUNDED_DYNAMIC" in txt
        assert "TIER_3_THEMATIC_ADVISORY" in txt

    tiers = {r["tier"] for r in THREE_TIER_RULE_CATALOG}
    assert tiers == {TIER_1_INVARIANT_MANDATORY, TIER_2_STORY_BOUNDED_DYNAMIC, TIER_3_THEMATIC_ADVISORY}
    levels = {r["level"] for r in THREE_TIER_RULE_CATALOG}
    assert levels == {"TEXT_SCRIPT", "AUDIO_SOUNDSCAPE", "VIDEO_VISUALS", "EDITING_COHESION"}


def test_organic_episode_passes_full_3tier_cohesive_film_audit_and_builds_edl() -> None:
    ep12 = json.loads(_need(ROOT / "jobs/ep_waterloo_12min/production_script.json").read_text(encoding="utf-8"))
    report = audit_cohesive_film_3tier(ep12)
    assert report["status"] == "PASS", f"Unexpected issues: {report['issues']}"
    assert report["fail_count"] == 0

    dyn = report["measured_tier_2_dynamics"]
    assert 3.2 <= dyn["shot_duration_mean_sec"] <= 6.2
    assert dyn["shot_duration_stdev_sec"] >= 0.65
    assert dyn["segment_duration_stdev_sec"] >= 3.0
    assert dyn["sentence_words_stdev"] >= 2.8

    edl_sum = report["cohesive_film_edl_summary"]
    assert edl_sum["j_l_cut_audio_bridges_count"] >= 20
    assert edl_sum["frame_minus_5_seamless_chains_count"] >= 10
    assert edl_sum["unbroken_ambience_beds_count"] >= 1
    assert edl_sum["unified_color_and_grain_pass"] is True


def test_jump_cut_and_av_desync_and_visual_mix_violations_caught() -> None:
    pilot = json.loads((ROOT / "tests/fixtures/pilot_60s_waterloo.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(pilot)

    # 1. Trigger CF-NO-JUMP-CUT: make shot 1 and shot 2 have identical location, character, shot_size, and azimuth
    broken["shots"][1]["segment_id"] = broken["shots"][0]["segment_id"]
    broken["shots"][1]["location_id"] = broken["shots"][0]["location_id"]
    broken["shots"][1]["character_ids"] = ["char_napoleon"]
    broken["shots"][0]["character_ids"] = ["char_napoleon"]
    broken["shots"][1]["camera_spec"]["shot_size"] = broken["shots"][0]["camera_spec"]["shot_size"]
    broken["shots"][1]["camera_spec"]["horizontal_azimuth_deg"] = broken["shots"][0]["camera_spec"]["horizontal_azimuth_deg"]
    broken["shots"][1]["continuity_refs"]["inherit_from_previous_shot_id"] = None

    # 2. Trigger CF-AV-DURATION-SYNC: make shot 0 duration 8.0s while its audio_line is 2.5s
    broken["shots"][0]["target_duration_seconds"] = 8.0

    # 3. Trigger CF-180-DEGREE-AXIS: clear screen_direction_notes on shot 2
    broken["shots"][2]["screen_composition"]["screen_direction_notes"] = ""

    issues = check_cohesive_film_invariants_and_bounds(broken)
    rules_hit = {i["rule"] for i in issues}
    assert "CF-NO-JUMP-CUT" in rules_hit
    assert "CF-AV-DURATION-SYNC" in rules_hit
    assert "CF-180-DEGREE-AXIS" in rules_hit
