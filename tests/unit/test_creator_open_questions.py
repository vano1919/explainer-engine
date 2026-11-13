"""The creator's open questions Q1..Q7 of the Fable audit 2026-11-13 are switches with Fable's defaults until he answers
(config/creator_open_questions.json); each switch is read where it acts."""
from __future__ import annotations

import json

import pytest

from explainer_engine.core import open_questions as OQ
from explainer_engine.core.errors import ConfigError

DEFAULTS = {"Q1": "REVIEW", "Q2": "off", "Q3": "REVIEW", "Q4": "supported", "Q5": "prompt_description", "Q6": "keep_open",
            "Q7": "frame"}


def test_every_question_has_fables_default_and_a_reader_that_exists():
    data = OQ.load()
    assert set(data["questions"]) == set(DEFAULTS)
    for qid, want in DEFAULTS.items():
        q = data["questions"][qid]
        assert OQ.value(qid) == want and q["answered"] is None, qid
        if q["read_by"]:
            src = (OQ.PATH.parents[1] / q["read_by"]).read_text(encoding="utf-8")
            assert f'"{qid}"' in src, f"{q['read_by']} does not read {qid}"


def test_an_unknown_value_or_question_refuses(tmp_path):
    data = OQ.load()
    data["questions"]["Q1"]["value"] = "MAYBE"
    p = tmp_path / "q.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ConfigError, match="not one of"):
        OQ.value("Q1", p)
    with pytest.raises(ConfigError, match="not an open question"):
        OQ.value("Q9")


def test_q1_bp56_follows_the_registry_until_the_creator_answers(monkeypatch):
    from explainer_engine.episode import cue_sheet as CS
    assert CS.bp56_level() == "REVIEW"          # FA-12: the registry's REVIEW (it was FAIL)
    monkeypatch.setattr(OQ, "value", lambda qid, path=OQ.PATH: "FAIL" if qid == "Q1" else DEFAULTS[qid])
    assert CS.bp56_level() == "FAIL"
    rows = [{"start_s": 0.0, "end_s": 2.0, "layer": "spot", "class": "impact", "asset_id": f"a{k}"} for k in range(3)]
    assert CS.overlap_rows(rows)[0]["status"] == "FAIL"


def test_q7_the_video_share_is_a_review_row_on_toba():
    from pathlib import Path
    from explainer_engine.episode import run as RUN
    doc = json.loads((Path(__file__).resolve().parents[2] / "episodes/ep_toba/story/production_script.json").read_text("utf-8"))
    row = RUN._video_share_row(doc)
    assert row["gate"] == "video_share_against_target" and row["status"] == "REVIEW" and "Q7 = frame" in row["detail"]
