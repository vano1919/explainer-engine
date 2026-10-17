"""The episode rulebook (docs/EPISODE_STANDARDS.md, ES-01..ES-18, D-45): checks, gates, stamps, briefs."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from explainer_engine import production_gate as G
from explainer_engine.production import paint
from explainer_engine.standards import rulebook as R
from explainer_engine.standards.__main__ import main as cli

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/episode_rules/episode_rules.json"
TODAY = date(2026, 10, 17)


def rules() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def fails(found, rule=None):
    return [f for f in found if f["severity"] == "FAIL" and (rule is None or f["rule"] == rule)]


def write(tmp_path: Path, doc: dict, script: str | None = "{}") -> tuple[Path, Path]:
    path = tmp_path / "episode_rules.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    sp = tmp_path / "production_script.json"
    if script is not None:
        sp.write_text(script, encoding="utf-8")
    return path, sp


def test_the_sample_rulebook_is_clean_at_every_checkpoint():
    for cp in R.CHECKPOINTS:
        assert fails(R.check(rules(), cp, today=TODAY)) == [], cp


def test_schema_refuses_unknown_fields_and_bad_status():
    doc = rules()
    doc["extra"] = 1
    doc["risks"][0]["status"] = "MAYBE"
    assert {f["rule"] for f in fails(R.check(doc, today=TODAY))} == {"ES-01"}


def test_a_heuristic_is_never_mandatory():
    doc = rules()
    doc["rules"][4]["strength"] = "mandatory"  # ER-05 is backed by a creative heuristic only
    assert fails(R.check(doc, today=TODAY), "ES-03")


def test_stale_policy_source_is_reviewed_then_blocks_paid_steps():
    later = date(2027, 6, 1)
    assert [f for f in R.check(rules(), "final", today=later) if f["rule"] == "ES-02"][0]["severity"] == "REVIEW"
    assert fails(R.check(rules(), "paid_assets", today=later), "ES-02")


def test_non_pass_needs_evidence_and_a_reason_not_a_keyword():
    doc = rules()
    doc["risks"][2]["rationale"] = "copyright"
    assert fails(R.check(doc, today=TODAY), "ES-04")
    del doc["risks"][2]["mitigation"]
    assert "mitigation" in fails(R.check(doc, today=TODAY), "ES-04")[0]["detail"]


def test_block_is_removed_before_final_and_does_not_block_the_topic():
    doc = rules()
    doc["risks"][2].update(status="BLOCK")
    assert [f["severity"] for f in R.check(doc, "provisional", today=TODAY) if f["rule"] == "ES-06"] == ["REVIEW"]
    assert fails(R.check(doc, "final", today=TODAY), "ES-06")
    doc["risks"][2]["removed"] = True
    assert not fails(R.check(doc, "final_qa", today=TODAY))  # the element goes, the episode stays


def test_review_needs_a_decision_before_paid_assets_and_adapt_is_applied():
    doc = rules()
    doc["risks"][1].update(status="REVIEW", evidence="licence page unclear on monetised use",
                           rationale="the licence names streaming but not monetised video on a platform",
                           mitigation="ask the library or pick a CC0 track", dependencies=["music"])
    assert not fails(R.check(doc, "script_lock", today=TODAY), "ES-07")
    assert fails(R.check(doc, "paid_assets", today=TODAY), "ES-07")
    doc["risks"][1]["decision"] = {"by": "creator", "date": "2026-10-17", "answer": "use the CC0 track instead"}
    assert not fails(R.check(doc, "paid_assets", today=TODAY), "ES-07")
    del doc["risks"][2]["resolved"]  # an image ADAPT: may wait for the asset step, not for the money
    assert not fails(R.check(doc, "script_lock", today=TODAY), "ES-07")
    assert fails(R.check(doc, "paid_assets", today=TODAY), "ES-07")


def test_fictional_historical_figures_pass_but_realistic_harm_does_not():
    doc = rules()
    assert not fails(R.check(doc, "final", today=TODAY), "ES-08")  # Caesar as our caricature: no disclosure
    p = doc["risks"][0]["person"]
    p.update(realistic=True, implies_endorsement=True)
    found = fails(R.check(doc, "final", today=TODAY), "ES-08")
    assert {f["check"] for f in found} == {"person_realistic_harm", "disclosure"}


def test_a_living_persons_voice_needs_consent():
    doc = rules()
    doc["risks"][0]["person"].update(name="A living actor", living=True, voice_imitated=True)
    assert fails(R.check(doc, today=TODAY), "ES-08")
    doc["risks"][0].update(status="REVIEW", evidence="voice requested by the script",
                           rationale="the script asks for a recognisable living actor's voice for one line",
                           mitigation="a library voice described by its sound (PV-10)", dependencies=["voice"])
    assert not fails(R.check(doc, today=TODAY), "ES-08")


def test_licences_unknown_or_unlicensed_are_never_cleared():
    doc = rules()
    doc["risks"][1]["license"]["basis"] = "unknown"
    assert fails(R.check(doc, today=TODAY), "ES-09")
    doc = rules()
    doc["risks"][2].update(status="PASS")
    assert fails(R.check(doc, today=TODAY), "ES-09")
    doc = rules()
    doc["risks"][1]["license"]["verified"] = "not_verified"
    assert not fails(R.check(doc, "paid_assets", today=TODAY), "ES-09")
    assert fails(R.check(doc, "final_qa", today=TODAY), "ES-09")


def test_an_exception_is_argued_in_a_relevant_jurisdiction_and_decided():
    doc = rules()
    doc["risks"][2].update(source_type="third_party_unlicensed", status="REVIEW",
                           exception={"jurisdiction": "GB", "provision": "fair dealing, quotation", "analysis": "short"})
    found = fails(R.check(doc, "paid_assets", today=TODAY), "ES-10")
    assert {f["check"] for f in found} == {"exception_scope", "exception_thin", "exception_decision"}


def test_notices_cannot_claim_to_create_permission():
    doc = rules()
    doc["platform"]["metadata"]["notices"] = [{"text": "No copyright infringement intended.",
                                               "purpose": "makes the use legal"}]
    found = [f for f in R.check(doc, today=TODAY) if f["rule"] == "ES-11"]
    assert {(f["check"], f["severity"]) for f in found} == {("protective_notice", "REVIEW"), ("notice_purpose", "FAIL")}
    doc["platform"]["metadata"]["notices"] = [{"text": "Unofficial fan analysis. Not affiliated with or endorsed by the "
                                               "rights holders.", "purpose": "prevents confusion about the source (RR-08)"}]
    assert not [f for f in R.check(doc, today=TODAY) if f["rule"] == "ES-11"]


def test_placeholder_credits_are_fine_while_planning_not_at_final_qa():
    doc = rules()
    doc["platform"]["metadata"]["credits"].append({"text": "Photo: <owner> (TBD)", "placeholder": True})
    assert not fails(R.check(doc, "paid_assets", today=TODAY))
    assert fails(R.check(doc, "final_qa", today=TODAY), "ES-12")


def test_reading_someone_elses_text_fails_originality():
    doc = rules()
    doc["platform"]["reuse_risk"]["reads_external_text"] = True
    assert fails(R.check(doc, today=TODAY), "ES-13")


def test_a_lookalike_of_an_earlier_episode_is_reviewed():
    earlier = rules()
    earlier["episode_id"] = "roman_pay_old"
    doc = rules()
    found = [f for f in R.check(doc, today=TODAY, previous=[earlier]) if f["rule"] == "ES-14"]
    assert {f["check"] for f in found} >= {"same_central_question", "same_mechanism"}
    assert all(f["severity"] == "REVIEW" for f in found)  # a person decides; the code never blocks creativity


def test_jurisdiction_must_be_confirmed_and_risks_stay_in_scope():
    doc = rules()
    doc["jurisdictions"]["confirmed_by_creator"] = False
    doc["risks"][1]["jurisdictions"] = ["FR"]
    found = R.check(doc, today=TODAY)
    assert [f["severity"] for f in found if f["check"] == "jurisdictions"] == ["REVIEW"]
    assert fails(found, "ES-15")


def test_franchise_items_need_the_rights_manifest_and_merge_ip_check(tmp_path):
    doc = rules()
    doc["risks"].append({"id": "RK-04", "element": "a crossover premise of two fantasy franchises", "category": "franchise",
                         "source_type": "reference_only", "status": "PASS"})
    assert fails(R.check(doc, "script_lock", today=TODAY), "ES-17")
    doc["execution"]["rights_manifest"] = "rights_manifest.json"
    path, sp = write(tmp_path, doc)
    (tmp_path / "rights_manifest.json").write_text(json.dumps(
        {"schema": "explainer.rights_manifest", "version": 1, "episode_id": "x", "uses_third_party_fiction": True}))
    assert any(f["check"].startswith("ip_check.") for f in fails(R.gate(path, "provisional", sp, today=TODAY)))


def test_every_role_gets_instructions_and_a_brief():
    doc = rules()
    del doc["execution"]["roles"]["music"]
    assert [f["severity"] for f in R.check(doc, "provisional", today=TODAY) if f["rule"] == "ES-18"] == ["REVIEW"]
    assert fails(R.check(doc, "final", today=TODAY), "ES-18")
    text = R.brief(rules(), "image")
    assert "Caesar as our caricature" in text and "ER-02" in text and "ER-03" not in text
    assert "drawn coin c01" in text and "a scientist explains in a cave" in text
    with pytest.raises(ValueError):
        R.brief(rules(), "lawyer")


def test_stamps_are_tied_to_the_script_and_go_stale_when_it_changes(tmp_path):
    path, sp = write(tmp_path, rules())
    assert fails(R.gate(path, "script_lock", sp, today=TODAY), "ES-16")
    R.stamp(path, "script_lock", by="test", scope="whole rulebook", script=sp, today=TODAY)
    assert fails(R.gate(path, "script_lock", sp, today=TODAY)) == []
    sp.write_text('{"changed": true}', encoding="utf-8")
    assert [f["check"] for f in fails(R.gate(path, "script_lock", sp, today=TODAY))] == ["stale_check"]
    doc = R.load(path)
    doc["rulebook_version"] = 2
    path.write_text(json.dumps(doc), encoding="utf-8")
    R.stamp(path, "script_lock", by="test", scope="RK-03 only: the coin shot moved", script=sp, today=TODAY)
    assert fails(R.gate(path, "script_lock", sp, today=TODAY)) == []


def test_a_stamp_never_replaces_a_review(tmp_path):
    doc = rules()
    doc["risks"][2]["status"] = "BLOCK"
    path, sp = write(tmp_path, doc)
    with pytest.raises(ValueError, match="cannot stamp"):
        R.stamp(path, "final", by="test", scope="x", script=sp, today=TODAY)
    assert R.load(path)["checks"] == []


def test_render_is_generated_from_the_json():
    text = R.render(rules())
    assert text.startswith("<!-- generated") and "| RK-03 |" in text and "Disclosure required: no" in text


def test_cli_check_and_brief(capsys):
    assert cli(["check", str(FIXTURE), "--at", "final"]) == 0
    assert cli(["brief", str(FIXTURE), "--role", "metadata"]) == 0
    assert "ES-11" in capsys.readouterr().out
    assert cli(["baseline"]) == 0


def test_policy_baseline_sources_are_dated_and_logged():
    text = (ROOT / "docs/MARKET_RESEARCH.md").read_text(encoding="utf-8")
    for b in R.baseline()["sources"]:
        assert b["url"].startswith("https://") and date.fromisoformat(b["checked"])
        assert b["kind"] in ("law", "platform_policy", "provider_terms")
        assert f"| {b['verified_in']} |" in text, b["id"]


def test_production_gate_shows_the_rulebook_row(tmp_path):
    path, sp = write(tmp_path, rules(), script=None)
    assert {r["gate"]: r for r in G.gates(tmp_path, tmp_path / "look.json")}["R"]["status"] == "PASS"
    path.unlink()
    sp.write_text("{}", encoding="utf-8")
    rows = {r["gate"]: r for r in G.gates(tmp_path, tmp_path / "look.json")}
    assert rows["R"]["status"] == "WAIT" and "episode-standards-director" in rows["R"]["next"]


def test_paint_refuses_paid_pictures_without_a_passing_rulebook(tmp_path, monkeypatch, capsys):
    script = tmp_path / "production_script.json"
    script.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(paint.S, "load", lambda p: {"picture_dirs": []})
    monkeypatch.setattr(paint, "jobs_of", lambda doc: [{"id": "p1", "refs": [], "prompt": "x"}])

    def no_call(*a, **k):
        raise AssertionError("no paid call may start")

    monkeypatch.setattr(paint, "GeminiClient", no_call)
    monkeypatch.setattr(paint, "run_batch", no_call)
    args = [str(script), "--run", str(tmp_path / "run.json"), "--out", str(tmp_path / "pics")]
    assert paint.main(args) == 4 and "no episode_rules.json" in capsys.readouterr().out
    (tmp_path / "episode_rules.json").write_text(json.dumps(rules()), encoding="utf-8")
    assert paint.main(args) == 4 and "paid_assets" in capsys.readouterr().out  # not stamped yet


def test_the_new_agent_and_docs_are_wired():
    agent = (ROOT / ".claude/agents/episode-standards-director.md").read_text(encoding="utf-8")
    assert agent.startswith("---\nname: episode-standards-director\ndescription: ")
    orch = (ROOT / ".claude/agents/orchestrator.md").read_text(encoding="utf-8")
    assert "episode-standards-director" in orch and "paid_assets" in orch and "final_qa" in orch
    assert "| OR-10 |" in (ROOT / "docs/ORCHESTRATION.md").read_text(encoding="utf-8")
    assert "EPISODE_STANDARDS" in (ROOT / "docs/INDEX.md").read_text(encoding="utf-8")


def test_channel_defaults_are_confirmed_and_match_the_default_jurisdictions():
    ch = R.baseline()["channel"]
    assert ch["jurisdictions"] == ["US", "GE"] and ch["audience_market"] == "US" and ch["elevenlabs_plan"] == "Creator"
    assert set(ch["jurisdictions"]) <= set(rules()["jurisdictions"]["relevant"])
