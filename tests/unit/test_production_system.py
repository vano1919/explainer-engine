"""D-52 and the master-prompt system: Gemini batch tiers, the ElevenLabs gate hook, script rules PV-39..PV-42, the
engagement gate, story hypotheses, the shared audio targets and the disclosure fields."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from explainer_engine.imagegen import routing
from explainer_engine.imagegen.gemini import BATCH_PRICES
from explainer_engine.production import paint
from explainer_engine.production import script as S
from explainer_engine.production import validate as V
from explainer_engine.qa import engagement, scorecard, targets
from explainer_engine.research import hypotheses as HY
from explainer_engine.standards import hook
from explainer_engine.standards import rulebook as R

ROOT = Path(__file__).resolve().parents[2]
EP1 = ROOT / "examples/stone_age/ep1_v1/production_script.json"
RULES = ROOT / "tests/fixtures/episode_rules/episode_rules.json"
TODAY = date(2026, 10, 17)


# --- pictures: Gemini batch tier only, three tiers (D-52) ---

def test_tiers_route_to_batch_prices_and_unknown_tiers_fail():
    assert routing.route("standard") == ("gemini-nano-banana-2.1", "2K")
    assert routing.batch_cost("draft") == BATCH_PRICES["gemini-nano-banana-2.1"]["1K"] == 0.0168
    assert routing.batch_cost("premium") == BATCH_PRICES["gemini-3-pro-image"]["2K"]
    assert routing.tier_of({}) == "standard"
    with pytest.raises(ValueError):
        routing.route("4k_please")


def test_a_gemini_plan_takes_its_model_and_size_from_the_tier(tmp_path, monkeypatch, capsys):
    """D-52 tiers survive the per-batch provider choice (D-50): `paint plan --tier` picks the routed model and size."""
    from test_production_script import compiled
    doc = compiled()
    script = tmp_path / "production_script.json"
    S.save(doc, script)
    for tier in sorted(routing.TIERS):
        assert paint.main(["plan", str(script), "--out", str(tmp_path / "pics"), "--id", f"B_{tier}", "--provider", "gemini",
                           "--tier", tier, "--batch", "--purpose", "test"]) == 0
        plan = json.loads((tmp_path / "pics" / "plans" / f"B_{tier}.json").read_text())
        assert (plan["model"], plan["size"]) == routing.route(tier) and plan["batch"]
    with pytest.raises(SystemExit):  # Gemini without a tier or a model is refused: there is no default
        paint.main(["plan", str(script), "--out", str(tmp_path / "pics"), "--id", "X", "--provider", "gemini"])


# --- ElevenLabs gate hook ---

def _ep(tmp_path: Path, rules: dict | None = None, cfg: dict | None = None) -> Path:
    (tmp_path / ".claude").mkdir(exist_ok=True)
    ep = tmp_path / "ep"
    ep.mkdir(exist_ok=True)
    if rules is not None:
        (ep / "episode_rules.json").write_text(json.dumps(rules), encoding="utf-8")
        (ep / "production_script.json").write_text("{}", encoding="utf-8")
    if cfg is not None:
        (tmp_path / ".claude/active_episode.json").write_text(json.dumps(cfg), encoding="utf-8")
    return tmp_path


def test_hook_refuses_pictures_and_four_takes_and_lets_estimates_through(tmp_path):
    root = _ep(tmp_path)
    assert "D-52" in hook.decide("mcp__ElevenLabs__creative_generate_image", {}, root)
    assert "D-52" in hook.decide("mcp__ElevenLabs__creative_generate_in_flow", {"node_type": "image-generation"}, root)
    assert hook.decide("mcp__ElevenLabs__creative_generate_speech", {"estimate_only": True}, root) is None
    assert hook.decide("mcp__ElevenLabs__creative_list_voices", {}, root) is None
    assert "EL-10" in hook.decide("mcp__ElevenLabs__creative_generate_speech", {"prompt": "x"}, root)
    assert "active episode" in hook.decide("mcp__ElevenLabs__creative_generate_speech", {"generations_count": 1}, root)


def test_hook_runs_the_rulebook_gate_and_logs_overrides(tmp_path):
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    root = _ep(tmp_path, rules, {"episode": "ep"})
    call = {"generations_count": 1, "node_type": "music"}
    assert "paid_assets" in hook.decide("mcp__ElevenLabs__creative_generate_in_flow", call, root)  # not stamped yet
    R.stamp(root / "ep/episode_rules.json", "paid_assets", by="t", scope="all", script=root / "ep/production_script.json")
    assert hook.decide("mcp__ElevenLabs__creative_generate_in_flow", call, root) is None
    _ep(tmp_path, None, {"episode": "nowhere", "override": "creator: three voice auditions, 2026-10-17"})
    assert hook.decide("mcp__ElevenLabs__creative_generate_speech", {"generations_count": 1}, root) is None
    assert "voice auditions" in (root / "jobs/gate_overrides.jsonl").read_text(encoding="utf-8")


def test_hook_main_prints_a_deny_decision(tmp_path, monkeypatch, capsys):
    _ep(tmp_path)
    event = {"cwd": str(tmp_path), "tool_name": "mcp__ElevenLabs__creative_generate_video", "tool_input": {}}
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(event)))
    assert hook.main() == 0
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny" and out["hookEventName"] == "PreToolUse"


def test_settings_wire_the_hook_to_the_connector():
    cfg = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    entry = cfg["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "mcp__ElevenLabs__creative_.*"
    assert "explainer_engine.standards.hook" in entry["hooks"][0]["command"]


# --- production script rules for rulebook-era scripts ---

def _ep1() -> dict:
    return S.load(EP1)


def test_old_scripts_keep_their_rules_and_new_scripts_get_pv32_to_35():
    doc = _ep1()
    assert not [f for f in V.check_script(copy.deepcopy(doc)) if f["rule"] in ("PV-39", "PV-40", "PV-41", "PV-42")]
    new = copy.deepcopy(doc)
    new["episode"]["rulebook"] = "episode_rules.json"
    rules = {f["rule"] for f in V.rulebook_era_findings(new)}
    assert {"PV-39", "PV-42"} <= rules  # no beat jobs, shots without purpose


def test_pv32_beat_jobs_and_pv33_premium_needs_a_reason():
    doc = _ep1()
    doc["episode"]["rulebook"] = "episode_rules.json"
    for seg in doc["segments"]:
        seg["job"] = "explanation"
    doc["segments"][0]["job"], doc["segments"][-1]["job"] = "hook", "payoff"
    assert not [f for f in V.rulebook_era_findings(doc) if f["rule"] == "PV-39"]
    pics, _ = S.pictures(doc)
    painted = [p for p in pics.values() if p.get("uses") and not p.get("file")]
    if not painted:
        pytest.skip("episode 1 has no unpainted pictures left")
    lib_or_inline = painted[0]["id"]
    for seg in doc["segments"]:
        for sh in seg["shots"]:
            if isinstance(sh["picture"], dict) and sh["picture"]["id"] == lib_or_inline:
                sh["picture"]["tier"] = "premium"
    if lib_or_inline in doc.get("library", {}):
        doc["library"][lib_or_inline]["tier"] = "premium"
    assert any(f["rule"] == "PV-40" and f["severity"] == "FAIL" for f in V.rulebook_era_findings(doc))


# --- engagement gate ---

def _seg(i, job, *lines):
    return {"id": f"S{i:02d}", "job": job, "lines": [{"text": t} for t in lines]}


def test_engagement_names_the_weak_beats():
    doc = {"episode": {"id": "x"}, "graphics": [{"segment": "S03"}], "segments": [
        _seg(1, "hook", "Rome paid its soldiers in salt."),
        _seg(2, "explanation", "A legionary earned 225 denarii a year."),
        _seg(3, "explanation", "That bought 900 loaves of bread every year."),
        _seg(4, "explanation", "Rome paid its soldiers in salt, they say."),
        _seg(5, "transition", "And then the coins changed.")]}
    found = engagement.check(doc, {"identity": {"central_question": "Was a legionary rich?"}})
    rules = {(f["rule"], f["where"]) for f in found}
    assert ("ENG-1", "S01") in rules                       # no question in the opening
    assert ("ENG-2", "S04") in rules                       # three explanations in a row
    assert ("ENG-3", "S02") in rules and ("ENG-3", "S03") not in rules  # S03 has a data visual
    assert ("ENG-4", "S04") in rules                       # repeats the opening line
    assert ("ENG-5", "S05") in rules                       # never returns to the question
    assert all(f["severity"] == "REVIEW" for f in found)  # a person decides
    assert "Does the ending deliver" in engagement.report(doc)


# --- story hypotheses ---

def _hyp(i, ev, nar, premise):
    return {"id": f"H{i}", "premise": premise, "question": "q?", "audience_reason": "r", "stakes": "s", "surprise": "s",
            "payoff": "p", "evidence_for": ["C-01"], "evidence_against": ["C-02"], "uncertainties": ["u"],
            "visual_opportunities": ["v"], "rights_risks": [], "scores": {"evidence": ev, "narrative": nar}}


def _hyps(selected="H1", ev1=4):
    return {"schema": "explainer.story_hypotheses", "version": 1, "episode_id": "x",
            "hypotheses": [_hyp(1, ev1, 3, "a legionary's purse priced in bread across five eras"),
                           _hyp(2, 3, 4, "why Roman pay collapsed under debasement in the third century"),
                           _hyp(3, 2, 5, "a soldier time-travels to buy a modern car with his salary")],
            "selected": {"id": selected, "why": "best supported",
                         "beats": [{"job": "hook", "what": "salt?"}, {"job": "evidence", "what": "pay", "claims": ["C-01"]},
                                   {"job": "payoff", "what": "verdict"}]}}


def test_hypotheses_are_compared_and_evidence_is_never_traded_for_story():
    assert HY.check(_hyps()) == []
    found = HY.check(_hyps(selected="H3"))
    assert any(f["rule"] == "HY-3" and f["severity"] == "FAIL" for f in found)  # narrative 5 cannot carry evidence 2
    doc = _hyps(ev1=2)
    doc["selected"]["id"] = "H1"
    assert any(f["rule"] == "HY-3" for f in HY.check(doc))
    doc = _hyps()
    doc["hypotheses"] = doc["hypotheses"][:2]
    assert any(f["rule"] == "HY-1" and f["severity"] == "FAIL" for f in HY.check(doc))
    doc = _hyps()
    doc["selected"]["beats"][-1]["job"] = "reveal"
    assert any(f["rule"] == "HY-4" and f["severity"] == "FAIL" for f in HY.check(doc))


# --- one set of audio targets ---

def test_audio_targets_are_shared_and_never_looser_than_before():
    assert targets.loudness_verdict(-14.6) == "PASS"       # Episode 1's 720p v2
    assert targets.loudness_verdict(-15.5) == "REVIEW"
    assert targets.loudness_verdict(-12.5) == "FAIL"       # P-90 allowed range ends at -13
    assert targets.true_peak_verdict(-0.8) == "FAIL"
    assert targets.gap_verdict(-20, -33) == "FAIL" and targets.gap_verdict(-20, -34) == "PASS"
    assert targets.loudnorm("short") == targets.loudnorm("long") == "loudnorm=I=-14:TP=-1.5:LRA=9"
    for path in ("explainer_engine/production/assemble.py", "explainer_engine/production/shorts.py"):
        assert "loudnorm=I=" not in (ROOT / path).read_text(encoding="utf-8"), path


def test_scorecard_reads_the_shared_targets():
    w = [{"w": f"w{i}" + ("." if i % 6 == 5 else ""), "s": i * 0.4, "e": i * 0.4 + 0.3} for i in range(60)]
    shots = [{"id": "s1", "type": "A", "start": 0.0, "end": 6.0, "transition": "cut", "emotion": "tension", "beat": "hook",
              "phase": "d", "sentences": [0], "motion": {"kind": "static", "z0": 1.0, "z1": 1.0}, "picture": "p",
              "palette": [], "face": "none", "stakes": "x y z w v u t"}]
    look = {"cast": [], "style_suffix": ""}
    good = {"voice_rms_db": -20, "bed_rms_db": -40, "music_rms_db": -40, "lufs": -14.2, "true_peak": -1.2}
    row2 = scorecard.score(shots, w, "Is it? yes.", look, audio=good, sound_events=[])[1]
    assert row2["status"] == "PASS" and any("-15 to -13" in e for e in row2["evidence"])
    for bad in ({"lufs": -12.0}, {"true_peak": -0.5}, {"music_rms_db": -30}):
        assert scorecard.score(shots, w, "Is it? yes.", look, audio={**good, **bad}, sound_events=[])[1]["status"] == "FAIL"


# --- disclosure ---

def test_disclosure_follows_declared_ai_uses_and_names_the_upload_action():
    doc = json.loads(RULES.read_text(encoding="utf-8"))
    doc["platform"]["disclosure"]["ai_uses"] = ["ideation_or_script", "stylised_imagery", "synthetic_voice"]
    assert not [f for f in R.check(doc, "final_qa", today=TODAY) if f["rule"] == "ES-08"]
    doc["platform"]["disclosure"]["ai_uses"].append("realistic_scene_never_happened")
    assert any(f["check"] == "disclosure_uses" for f in R.check(doc, today=TODAY))
    doc["platform"]["disclosure"].update(required=True, reason="a realistic storm over a real city")
    assert [f["severity"] for f in R.check(doc, "final_qa", today=TODAY) if f["check"] == "disclosure_action"] == ["FAIL"]
    doc["platform"]["disclosure"]["upload_action"] = "Studio upload flow, Attributes, AI use: Yes"
    assert not [f for f in R.check(doc, "final_qa", today=TODAY) if f["rule"] == "ES-08"]


# --- D-53: filler pictures may come from Canva (PV-43) ---

def _filler_doc(job="explanation"):
    doc = copy.deepcopy(json.loads(EP1.read_text(encoding="utf-8")))
    seg = doc["segments"][1]
    seg["job"] = job
    pid = "canva_plate_1"
    doc.setdefault("library", {})[pid] = {"subject": "empty shore at dusk", "engine": "canva", "people": False}
    seg["shots"][0] = {"at": seg["shots"][0]["at"], "type": "A", "motion": seg["shots"][0]["motion"], "picture": pid}
    return doc, pid


def test_importance_is_computed_and_a_lone_plate_in_an_explanation_is_filler():
    from explainer_engine.imagegen import importance
    doc, pid = _filler_doc()
    assert importance.classify(doc)[pid] == {"filler": True, "why_not": []}


def test_importance_cannot_be_declared_by_the_script():
    from explainer_engine.imagegen import importance
    doc, pid = _filler_doc(job="reveal")
    doc["library"][pid]["heroes"] = ["newton"]
    doc["library"][pid]["filler"] = True      # a self-declared flag is ignored
    res = importance.classify(doc)[pid]
    assert not res["filler"] and any("heroes" in w for w in res["why_not"]) and any("reveal" in w for w in res["why_not"])


def test_canva_is_refused_until_the_terms_are_verified_and_never_for_important_pictures(monkeypatch):
    doc, pid = _filler_doc()
    monkeypatch.setattr(R, "baseline", lambda: {"channel": {"canva_terms_verified": False}})
    found = V.canva_findings(doc)
    assert any(f["rule"] == "PV-43" and "not verified" in f["detail"] for f in found)
    monkeypatch.setattr(R, "baseline", lambda: {"channel": {"canva_terms_verified": True}})
    assert not [f for f in V.canva_findings(doc) if f["severity"] == "FAIL"]
    doc["library"][pid]["heroes"] = ["newton"]
    assert any(f["where"] == pid and "not filler" in f["detail"] for f in V.canva_findings(doc))


def test_canva_share_is_capped_and_other_engines_are_untouched(monkeypatch):
    monkeypatch.setattr(R, "baseline", lambda: {"channel": {"canva_terms_verified": True}})
    doc = json.loads(EP1.read_text(encoding="utf-8"))
    assert V.canva_findings(doc) == []
    doc, pid = _filler_doc()
    used = len(S.pictures(doc)[0])
    assert any("come from Canva" in f["detail"] for f in V.canva_findings(doc)) == (1 / used > 0.30)


def test_paint_leaves_canva_pictures_out_of_the_gemini_jobs():
    from explainer_engine.production import compile as C
    doc, pid = _filler_doc()
    assert pid not in [j["id"] for j in paint.to_paint(doc)] and pid in C.canva_pending(doc)


def test_the_creator_has_confirmed_the_canva_terms_in_the_baseline():
    ch = R.baseline()["channel"]
    assert ch["canva_terms_verified"] is True and "creator" in ch["canva_terms_note"]
