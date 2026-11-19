"""Owner-approved Python item 5: section beds + ambience continuity across cuts (WARN mode until calibrated)."""
import json
from pathlib import Path

import numpy as np

from explainer_engine.audio import mix_check as MC
from explainer_engine.episode import sound_plan as SP
from explainer_engine.qa.gates import FAIL, NOT_RUN, PASS, REVIEW

PLAN = Path(__file__).resolve().parents[2] / "episodes" / "ep_truce_1914" / "audio" / "sound_plan.json"


def _plan():
    return json.loads(PLAN.read_text(encoding="utf-8"))


def _bed(level_before, level_after, sr=48000, seconds=2.0):
    rng = np.random.default_rng(1)
    n = int(sr * seconds)
    return np.concatenate([rng.standard_normal(n) * level_before, rng.standard_normal(n) * level_after]).astype(np.float32)


def test_old_plan_without_section_beds_gets_no_rows():
    assert SP.section_bed_rows({"beds": []}) == []


def test_the_truce_plan_keeps_continuous_beds_and_reports_audibility_as_not_verified():
    rows = {r["gate"]: r for r in SP.section_bed_rows(_plan())}
    assert rows["SECTION_BED_CONTINUITY"]["status"] == PASS
    assert rows["SOUND_BED_AUDIBILITY_REVIEW"]["status"] == NOT_RUN


def test_a_hard_bridge_replaces_the_sound_and_is_a_review():
    plan = _plan()
    plan["bridges"][0].update({"crossfade_frames": 0, "crossfade_seconds": 0, "silence_intent": "none"})
    r = {x["gate"]: x for x in SP.section_bed_rows(plan)}["SECTION_BED_CONTINUITY"]
    assert r["status"] == REVIEW and r["measured"]["bridges"]


def test_a_section_without_a_continuous_bed_is_a_review():
    plan = _plan()
    plan["section_beds"][0]["continuous"] = False
    assert {x["gate"]: x for x in SP.section_bed_rows(plan)}["SECTION_BED_CONTINUITY"]["status"] == REVIEW


def test_a_steady_bed_across_a_cut_passes():
    assert MC.ambience_continuity_rows(_bed(0.05, 0.05), [2.0])[0]["status"] == PASS


def test_a_7_db_ambience_jump_is_a_review_in_warn_mode_and_a_fail_once_calibrated():
    amb = _bed(0.02, 0.02 * 10 ** (7 / 20))
    assert MC.bed_jump_band(MC.ambience_jump_db(amb, 2.0)) == "FAIL"
    warn = MC.ambience_continuity_rows(amb, [2.0])[0]
    hard = MC.ambience_continuity_rows(amb, [2.0], calibrated=True)[0]
    assert warn["status"] == REVIEW and hard["status"] == FAIL and "NOT_VERIFIED" in warn["detail"]


def test_no_measurable_cut_is_not_run():
    assert MC.ambience_continuity_rows(np.zeros(10, np.float32), [99.0])[0]["status"] == NOT_RUN
