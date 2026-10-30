"""The AI register (P3, RG-01..RG-05, BP-140 FAIL tier, BP-114 soft tier): what fails, what only reviews, what is exempt, and that
every committed script is clean at the FAIL tier (a regression baseline: the list must not catch the channel's own writing)."""

from __future__ import annotations

import copy
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from explainer_engine.production import validate
from explainer_engine.scripting import film_shots, narration_lint
from explainer_engine.scripting import register_lint as RL
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted(ROOT.glob("examples/**/production_script.json"))


def rules(found, rule=None):
    return [f for f in found if rule is None or f["rule"] == rule]


def test_a_tier_one_word_fails_and_cites_the_house_rule():
    found = RL.findings("The khan did not delve into the plan. He rode.")
    assert [f["severity"] for f in rules(found, "RG-01")] == ["FAIL"] and "BP-140" in found[0]["detail"]
    assert SR.rule("BP-140")["status"] == "house" and SR.level("BP-140") == "FAIL"


@pytest.mark.parametrize("text", ["It delves deeper.", "The plan was underscored by fear.", "A tapestry of alliances.", "Notably, he left.",
                                  "Moreover, the guns were late."])
def test_inflections_and_the_sentence_initial_connector_are_hits(text):
    assert rules(RL.findings(text), "RG-01"), text


def test_the_connector_only_counts_at_the_start_of_a_sentence():
    assert not rules(RL.findings("He said moreover, nothing."), "RG-01")
    assert rules(RL.findings("It was cold. Furthermore, the food ran out."), "RG-01")


def test_the_registry_is_the_only_home_of_the_words():
    words = SR.T("BP-140", "register_words")
    assert "delve" in words and "revolutionary" not in words and "boasts" not in words  # soft tier: Napoleon's period, a hero may boast
    assert "revolutionary" in SR.T("BP-114", "lexicon")
    assert not rules(RL.findings("The revolutionary army marched."), "RG-01")


def test_a_name_in_the_middle_of_a_sentence_is_not_the_register_but_a_capital_at_the_start_is():
    assert not rules(RL.findings("The ship Renowned left at dawn."), "RG-01")
    assert rules(RL.findings("Renowned for his speed, he rode."), "RG-01")


def test_a_literal_use_needs_an_allow_entry_with_a_reason_and_a_note_that_covers_it():
    line = "The steppe was a flat landscape."
    allow = [{"term": "landscape", "reason": "literal", "note": "S03: the steppe as terrain"}]
    assert rules(RL.findings(line, where="S04 line 1"), "RG-01")
    assert not rules(RL.findings(line, where="S03 line 2", allow=allow), "RG-01")
    assert rules(RL.findings(line, where="S04 line 2", allow=allow), "RG-01")
    assert not rules(RL.findings(line, where="S04 line 2", allow=[dict(allow[0], note="all lines of the script")]), "RG-01")


def test_an_allow_entry_without_a_reason_or_a_note_fails_and_does_not_exempt():
    for bad in ({"term": "landscape", "reason": "literal", "note": ""}, {"term": "landscape", "reason": "because", "note": "all"},
                {"term": "landscape", "reason": "literal"}):
        found = RL.findings("A flat landscape.", where="S01 line 1", allow=[bad])
        assert [f["severity"] for f in rules(found, "RG-05")] == ["FAIL"] and rules(found, "RG-01"), bad


def test_a_quotation_inside_a_line_that_cites_a_claim_is_exempt():
    doc = {"schema": "production_script/3", "segments": [{"id": "S01", "lines": [
        {"text": 'The memoir calls him "a pivotal figure" of the age.', "claims": ["C-01"]},
        {"text": 'Another memoir calls him "a pivotal figure" too.'}]}]}
    found = RL.doc_findings(doc)
    assert [f["where"] for f in rules(found, "RG-01")] == ["S01 line 2"]


def test_soft_hits_review_only_over_the_limit():
    one = "He had a sense of dread. " + "The horse ran. " * 30
    assert not rules(RL.findings(one), "RG-02")
    two = "He had a sense of dread. Overall the plan was robust. " + "The horse ran. " * 30
    assert [f["severity"] for f in rules(RL.findings(two), "RG-02")] == ["REVIEW"]
    assert SR.level("BP-114") == "REVIEW"


def test_structure_densities_review_narration_but_never_a_heros_speech():
    filler = "The horse ran. " * 80
    tells = "He was tired, cold, and hungry. " * 4
    assert rules(RL.findings(filler + tells), "RG-03")
    doc = {"schema": "production_script/3", "segments": [{"id": "S01", "lines": [
        {"speaker": "murat", "text": "Cold, wet, and angry. " * 6}]}]}
    assert not rules(RL.doc_findings(doc), "RG-03")
    pivots = "It's not fear. It's hunger. " * 3 + filler
    assert rules(RL.findings(pivots), "RG-03") and not rules(RL.findings(filler), "RG-03")


def test_a_summarising_opener_or_closer_reviews():
    doc = {"schema": "production_script/3", "segments": [
        {"id": "S01", "lines": [{"text": "Overall, the march began well."}, {"text": "Then the rain came."}]},
        {"id": "S02", "lines": [{"text": "The guns sank."}, {"text": "In conclusion, nobody won."}]}]}
    found = rules(RL.doc_findings(doc), "RG-04")
    assert {f["where"] for f in found} == {"S01", "S02"} and all(f["severity"] == "REVIEW" for f in found)


def test_the_lexicon_goes_stale_after_recheck_days():
    checked = date.fromisoformat(SR.T("BP-140", "checked_on"))
    assert RL.stale(checked + timedelta(days=SR.T("BP-140", "recheck_days"))) is None
    late = RL.stale(checked + timedelta(days=SR.T("BP-140", "recheck_days") + 1))
    assert late and late["severity"] == "REVIEW"


def test_narration_lint_reports_it_as_n16_and_n17():
    found = narration_lint.lint("Why did he stop? Because the khan delved into the maps.\nHe had a sense of dread. Overall, robust.")
    assert [f["rule"] for f in found if f["rule"] in ("N-16", "N-17")][:1] == ["N-16"]
    assert any(f["rule"] == "N-16" and f["severity"] == "FAIL" for f in found)
    assert not any(f["rule"] in ("N-16", "N-17") for f in narration_lint.lint("Why did he stop?", register=False))


def test_film_shots_check_reads_the_cards_text_as_kp46():
    doc = json.loads((ROOT / "examples/napoleon_vs_genghis/film_shots.json").read_text(encoding="utf-8"))
    assert not [f for f in film_shots.check(doc) if f["rule"].startswith("KP-46")]
    bad = copy.deepcopy(doc)
    sh = next(s for s in bad["shots"] if s.get("narration"))
    sh["narration"] = "A tapestry of fear spread through the camp."
    found = [f for f in film_shots.check(bad) if f["rule"].startswith("KP-46")]
    assert found and found[0]["severity"] == "FAIL" and found[0]["rule"] == "KP-46 RG-01"


def test_the_validator_reports_it_as_pv61_on_a_production_script():
    doc = json.loads((ROOT / "examples/titans_from_zero/production_script.json").read_text(encoding="utf-8"))
    folder = [ROOT / "examples/titans_from_zero/pictures"]
    base = [f for f in validate.check_script(doc, picture_dirs=folder) if f["rule"].startswith("PV-61")]
    assert base == []
    seg = next(s for s in doc["segments"] if any(not ln.get("speaker") for ln in s["lines"]))
    ln = next(ln for ln in seg["lines"] if not ln.get("speaker"))
    ln["text"] = "He delved into it. " + ln["text"]
    found = [f for f in validate.check_script(doc, picture_dirs=folder) if f["rule"].startswith("PV-61")]
    assert found and found[0]["severity"] == "FAIL"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.parent.name)
def test_no_committed_script_trips_the_fail_tier(path):
    """Baseline (2026-10-30): the 32 words and the openers occur 0 times in every committed production script."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert [f for f in RL.doc_findings(doc, allow=RL.load_allow(path)) if f["severity"] == "FAIL"] == []


def test_the_napoleon_draft_is_clean_at_the_fail_tier():
    text = (ROOT / "examples/napoleon_vs_genghis/script.md").read_text(encoding="utf-8")
    assert [f for f in RL.findings(text) if f["severity"] == "FAIL"] == []
    doc = json.loads((ROOT / "examples/napoleon_vs_genghis/film_shots.json").read_text(encoding="utf-8"))
    assert [f for f in RL.film_shots_findings(doc) if f["severity"] == "FAIL"] == []
