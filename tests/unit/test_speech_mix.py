"""ICW-03: the speech-mix report (``qa/speech_mix.py``, ``speech_mix_report/1``; D-99, BP-105): narrator against voiced
character words, unvoiced lines kept apart, informational seconds from the spine, lip-sync coverage from film_shots/3, and
REVIEW findings only (KP-39 the band, KP-36 a seen line over BP-108's cap). It is a separate axis from the lane shares."""

from __future__ import annotations

import copy
import json

import pytest

import _lane_fixtures as LF
from _napoleon import NAPOLEON, cards_v3
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.qa import speech_mix as SM
from explainer_engine.scripting import film_shots as F
from explainer_engine.visual import lanes

REFS = {"script": {"path": "script.json", "sha256": "0" * 64}, "audio_spine": {"path": "audio/audio_spine.json",
        "sha256": "1" * 64}, "film_shots": {"path": "film_shots.json", "sha256": "2" * 64}}


def _script(lines: list[tuple[str | None, str, bool]]) -> dict:
    return {"schema": "production_script/1", "segments": [
        {"id": "S01", "lines": [dict({"text": t}, **({"speaker": w} if w else {}), **({} if v else {"voiced": False}))
                                for w, t, v in lines]}]}


def _spine(windows: list[tuple[int, float, float]]) -> dict:
    return {"words": [{"i": i, "line": k, "start_s": a, "end_s": b} for i, (k, a, b) in enumerate(windows)]}


def test_the_share_counts_audible_words_and_keeps_unvoiced_lines_apart():
    s = _script([(None, "one two three four five six seven", True), ("anna", "eight nine", True),
                 ("ivo", "a silent bubble here", False), (None, "ten", True)])
    doc = SM.report(s, refs=REFS, job_id="j")
    assert (doc["narrator_words"], doc["dialogue_words"], doc["unvoiced_words"]) == (8, 2, 4)
    assert doc["narrator_share_words"] == 0.8
    assert doc["narrator_share_seconds"] is None and doc["rule"] == "BP-105"
    assert set(doc["derived_from"]) == {"script"}


def test_seconds_come_from_the_spine_and_skip_unvoiced_lines():
    s = _script([(None, "a b", True), ("anna", "c", True), ("ivo", "d", False)])
    spine = _spine([(0, 0.0, 1.0), (0, 1.0, 3.0), (1, 3.0, 4.0), (2, 4.0, 9.0)])
    assert SM.seconds_share(s, spine) == 0.75
    doc = SM.report(s, refs=REFS, job_id="j", spine=spine)
    assert doc["narrator_share_seconds"] == 0.75 and "audio_spine" in doc["derived_from"]
    assert SM.seconds_share(s, None) is None


def test_a_spine_that_names_a_missing_line_is_a_contract_fault():
    with pytest.raises(ContractError):
        SM.seconds_share(_script([(None, "a", True)]), _spine([(3, 0.0, 1.0)]))


def test_the_report_never_stores_the_band():
    doc = SM.report(_script([(None, "a b c", True), ("anna", "d", True)]), refs=REFS, job_id="j")
    contracts.validate(doc)
    assert not {"band", "nominal", "target"} & set(doc)
    bad = dict(doc, band=[0.65, 0.75])
    with pytest.raises(ContractError):
        contracts.validate(bad)


def test_the_napoleon_episode_sits_inside_bp105s_band():
    cards = cards_v3()
    doc = SM.report(cards, refs=REFS, job_id="napoleon")
    lo, hi = F.NARRATOR_SHARE
    assert lo <= doc["narrator_share_words"] <= hi
    assert doc["narrator_share_words"] == pytest.approx(0.701, abs=0.001)
    assert SM.findings(doc) == []
    assert doc["lipsync_shots"] == sum(1 for s in cards["shots"] if s.get("lipsync"))
    assert doc["longest_voiced_cu_s"] <= F.DIALOGUE_SHOT_MAX_S


def test_a_share_outside_the_band_is_a_kp39_review_naming_the_nominal():
    doc = SM.report(_script([(None, "a b", True), ("anna", "c d e f", True)]), refs=REFS, job_id="j")
    found = SM.findings(doc)
    assert [f["rule"] for f in found] == ["KP-39"] and found[0]["severity"] == "REVIEW"
    assert f"{F.NARRATOR_NOMINAL:.0%}" in found[0]["detail"] and "never a silent rewrite" in found[0]["detail"]


def test_a_seen_line_over_the_dialogue_cap_is_a_kp36_review():
    shots = LF.council_drama()
    shots["shots"][1]["seconds"] = 9
    doc = SM.report(shots, refs=REFS, job_id="j")
    assert doc["longest_voiced_cu_s"] == 9
    assert "KP-36" in [f["rule"] for f in SM.findings(doc)]
    planned, _ = lanes.plan(shots)  # the planner's split brings it under the cap, words unchanged
    after = SM.report(planned, refs=REFS, job_id="j")
    assert after["longest_voiced_cu_s"] <= F.DIALOGUE_SHOT_MAX_S
    assert (after["narrator_words"], after["dialogue_words"]) == (doc["narrator_words"], doc["dialogue_words"])


def test_the_speech_mix_does_not_move_with_the_lane_plan():
    src = LF.battle_documentary()
    before = SM.report(src, refs=REFS, job_id="j")
    planned, _ = lanes.plan(copy.deepcopy(src))
    after = SM.report(planned, refs=REFS, job_id="j")
    for k in ("narrator_words", "dialogue_words", "unvoiced_words", "narrator_share_words"):
        assert before[k] == after[k]


def test_the_cli_writes_a_valid_report(tmp_path, capsys):
    out = tmp_path / "speech_mix_report.json"
    assert SM.main([str(NAPOLEON / "film_shots.json"), "--job-id", "napoleon", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    contracts.validate(doc)
    assert doc["job_id"] == "napoleon" and "narrator 70.1%" in capsys.readouterr().out
