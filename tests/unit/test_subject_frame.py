"""Owner-approved Python item 3: subject-frame integrity + 2.5D motion envelope (qa/subject_frame.py)."""
import json
from pathlib import Path

from explainer_engine.qa import subject_frame as SF
from explainer_engine.qa.gates import NOT_RUN, PASS, REVIEW

SCRIPT = Path(__file__).resolve().parents[2] / "episodes" / "ep_truce_1914" / "story" / "production_script.json"


def _shot(sid):
    return next(s for s in json.loads(SCRIPT.read_text(encoding="utf-8"))["shots"] if s["shot_id"] == sid)


def test_s08_sh002_no_longer_zooms_onto_a_part():
    assert [r["status"] for r in SF.crop_rows(_shot("S08_SH002"))] == [PASS]


def test_the_old_1_35_cutin_on_s08_sh002_is_a_review():
    shot = _shot("S08_SH002")
    shot["split_plan"]["parts"][1]["framing"] = {"crop": 1.35, "focus": [0.5, 0.45]}
    r = SF.crop_rows(shot)[0]
    assert r["status"] == REVIEW and r["measured"] == ["S08_SH002b"]


def test_declared_intentional_crop_regions_pass():
    shot = _shot("S08_SH002")
    shot["crop_policy"] = {"policy": "preserve_required_subject_regions", "intentional_crop_regions": ["hands"]}
    shot["split_plan"]["parts"][1]["framing"] = {"crop": 1.35, "focus": [0.5, 0.45]}
    assert SF.crop_rows(shot)[0]["status"] == PASS


def test_a_shot_without_crop_policy_gets_no_row():
    assert SF.crop_rows({"shot_id": "X"}) == []


def test_motion_envelope():
    ok = SF.envelope_rows("A", {"drift_pct": 2.0, "scale_pct": 1.0, "parallax_pct": 1.0, "velocity_pct_per_s": 0.2})[0]
    bad = SF.envelope_rows("A", {"drift_pct": 6.0, "parallax_pct": 2.5})[0]
    none = SF.envelope_rows("A", None)[0]
    assert ok["status"] == PASS and bad["status"] == REVIEW and set(bad["measured"]) == {"drift_pct", "parallax_pct"}
    assert none["status"] == NOT_RUN
