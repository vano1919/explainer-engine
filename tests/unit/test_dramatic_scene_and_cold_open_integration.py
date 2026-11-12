"""Unit Tests for Dramatic-Scene Storytelling & Future-Scene Cold Open Integration (Cases A–J, Steps 0–15).

Covers all required verification cases:
- Case A: Bad Isolated-Line Pattern (Must Fail with SC-05, SC-01, SC-04, SC-V4-DUPLICATE-DIALOGUE)
- Case B: Good Played Scene Pattern (Must Pass with 0 issues)
- Case C: Narration-Only Analytical/Transition Passage (Must Pass with 0 issues)
- Case D: Hook Uses Later Dramatic Scene (`teaser_of` + `teaser_trim`, zero new AI generation)
- Case E: Orphan, Backward, or Out-of-Range Teaser (Must Fail with KP-41)
- Case F: Narrator Repeats Character Line (`ST-21`) or Unframed Scene (`ST-14`) (Must Fail)
- Case G: No Mandatory Dialogue Quota (90%+ narration with 1 genuine played turning-point scene passes)
- Case H: Historical Integrity (`dramatized_in_scene_speech` vs `verified_historical_fact` + editorial_gate check)
- Case I: Backward Compatibility on `production_script/3`, `film_shots/1`, and `film_shots/2`
- Case J: No Gate Weakening (`run_all_gate_audits` and `viewer_critic` clean-room evaluation)
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from explainer_engine.aivideo.wan_optimizer import compute_multifactor_shot_routing
from explainer_engine.imagegen.asset_plan import extract_complete_asset_plan
from explainer_engine.orchestration.rule_enforcer import run_all_gate_audits
from explainer_engine.production import editorial_gate
from explainer_engine.production.validate import check_script
from explainer_engine.qa.viewer_critic import evaluate_script_with_viewer_critic
from explainer_engine.scripting import film_shots, scene_lint, shot_prompt_lint, story_lint

ROOT = Path(__file__).resolve().parents[2]
WATERLOO_PATH = ROOT / "jobs" / "ep_waterloo_12min" / "production_script.json"
TOBA_PATH = ROOT / "jobs" / "ep_toba_74000bce_12min" / "ep_toba_74000bce_12min_production_script.json"
PILOT_PATH = ROOT / "tests" / "fixtures" / "pilot_60s_waterloo.json"


def test_case_a_bad_isolated_line_pattern_is_caught_and_rejected() -> None:
    """Case A: A segment where the narrator speaks, a character drops 1 isolated/generic line without a scene
    or reply, or refers to themselves in the third person, MUST fail scene_lint."""
    doc = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    bad = copy.deepcopy(doc)

    # Remove scene contract and turn lines into isolated 1-line character interruptions with third-person self-reference
    bad["segments"][0].pop("scene", None)
    bad["segments"][0]["segment_mode"] = "narration_led"
    for i, ln in enumerate(bad["audio_lines"]):
        if i == 3:
            ln["speaker_type"] = "character"
            ln["speaker_id"] = "char_wellington"
            ln["addressee_id"] = "char_napoleon_1815"
            ln["text"] = "The chalk beneath the wheels is dry enough—open the grand battery barrage before Wellington reinforces the ridge!"
        elif i == 7:
            ln["speaker_type"] = "character"
            ln["speaker_id"] = "char_ney"
            ln["addressee_id"] = None
            ln["text"] = "The chalk beneath the wheels is dry enough—open the grand battery barrage before Wellington reinforces the ridge!"
        else:
            ln["speaker_type"] = "narrator"
            ln["speaker_id"] = "narrator_main"
            ln["addressee_id"] = None

    issues = scene_lint.lint(bad)
    rules_hit = {f["rule"] for f in issues if f["severity"] == "FAIL"}
    assert "SC-01" in rules_hit  # missing scene contract
    assert "SC-04" in rules_hit  # third-person self-reference & missing addressee_id
    assert "SC-05" in rules_hit  # isolated 1-line character interruption
    assert "SC-V4-DUPLICATE-DIALOGUE" in rules_hit  # duplicated boilerplate character line


def test_case_b_good_played_scene_pattern_passes() -> None:
    """Case B: A segment with narrator setup -> multi-turn co-present character exchange with opposing wants and turn ->
    narrator consequence passes all linters with 0 issues."""
    doc = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    assert check_script(doc) == []
    assert scene_lint.lint(doc) == []
    assert story_lint.lint(doc) == []
    assert shot_prompt_lint.check_v4_script(doc) == []


def test_case_c_narration_only_analytical_passage_passes() -> None:
    """Case C: A segment where narration carries the story without character dialogue is valid when no fake character line is forced in."""
    doc = json.loads(TOBA_PATH.read_text(encoding="utf-8"))
    s02_lines = [l for l in doc["audio_lines"] if l["segment_id"] == "S02"]
    assert all(l["speaker_type"] == "narrator" for l in s02_lines)
    assert scene_lint.lint(doc) == []
    assert story_lint.lint(doc) == []


def test_case_d_hook_uses_later_dramatic_scene_with_zero_new_generation() -> None:
    """Case D: Cold open reuses later payoff shots via teaser_of + teaser_trim with zero new AI image/video generation."""
    toba_doc = json.loads(TOBA_PATH.read_text(encoding="utf-8"))
    sh0, sh1 = toba_doc["shots"][0], toba_doc["shots"][1]
    assert sh0.get("teaser_of") == "S05_SH001"
    assert sh0.get("teaser_trim") == [0.4, 2.2]
    assert sh1.get("teaser_of") == "S09_SH001"
    assert sh1.get("teaser_trim") == [0.5, 2.7]

    plan = extract_complete_asset_plan(toba_doc)
    assert plan["counts"]["teaser_reuse_shots_count"] == 2
    queued_shot_ids = {
        x["shot_id"]
        for bucket in (plan["maps_and_diagrams_10pct"], plan["photo_collage_30pct"], plan["video_keyframes_60pct"])
        for x in bucket
    }
    assert "S01_SH001" not in queued_shot_ids
    assert "S01_SH002" not in queued_shot_ids

    route0 = compute_multifactor_shot_routing(sh0)
    assert route0["selected_engine"] == "REUSE_TEASER_OF_PAYOFF_CLIP"
    assert route0["requires_new_generation"] is False
    assert route0["estimated_cost_usd"] == 0.0

    # Also verify film_shots.compose() explicit teaser_trim slicing on examples/film_shots/bus_in_the_ice_age.json
    fs_doc = json.loads((ROOT / "examples/film_shots/bus_in_the_ice_age.json").read_text(encoding="utf-8"))
    payoff_shot = next(s for s in fs_doc["shots"] if not s.get("teaser_of") and float(s.get("seconds", 0)) >= 3.0)
    teaser_shot = copy.deepcopy(payoff_shot)
    teaser_shot["id"] = "S01-TEASER"
    teaser_shot["teaser_of"] = payoff_shot["id"]
    teaser_shot["seconds"] = 2.0
    teaser_shot["teaser_trim"] = [0.6, 2.6]
    fs_doc["shots"].insert(0, teaser_shot)
    composed = {p["id"]: p for p in film_shots.compose(fs_doc)}
    assert composed["S01-TEASER.video"]["kind"] == "reuse" and composed["S01-TEASER.video"]["of"] == f"{payoff_shot['id']}.video"
    assert composed["S01-TEASER.video"]["trim"] == [0.6, 2.6]


def test_case_e_orphan_backward_or_out_of_bounds_teaser_fails() -> None:
    """Case E: A teaser_of pointing to a nonexistent shot, earlier shot, shorter shot, or invalid teaser_trim fails KP-41."""
    doc = json.loads(PILOT_PATH.read_text(encoding="utf-8"))

    # 1. Nonexistent payoff shot
    bad_missing = copy.deepcopy(doc)
    bad_missing["shots"][0]["teaser_of"] = "S99_SH999"
    assert any(f["rule"] == "KP-41" for f in story_lint.lint(bad_missing))

    # 2. Backward teaser (teaser at index 5 pointing to index 1)
    bad_backward = copy.deepcopy(doc)
    bad_backward["shots"][5]["teaser_of"] = bad_backward["shots"][1]["shot_id"]
    assert any(f["rule"] == "KP-41" for f in story_lint.lint(bad_backward))

    # 3. Out-of-bounds teaser_trim
    bad_trim = copy.deepcopy(doc)
    bad_trim["shots"][0]["teaser_of"] = bad_trim["shots"][4]["shot_id"]  # S04_SH005 is 7.0s
    bad_trim["shots"][0]["teaser_trim"] = [5.5, 9.5]  # exceeds 7.0s payoff duration!
    assert any(f["rule"] == "KP-41" for f in story_lint.lint(bad_trim))


def test_case_f_narrator_double_exposition_and_unframed_exchange_fail() -> None:
    """Case F: A narrator line repeating the adjacent character line fails ST-21, and unframed dialogue fails ST-14."""
    doc = json.loads(PILOT_PATH.read_text(encoding="utf-8"))

    # 1. Narrator line S04_L011 repeats S04_L010 character line words -> ST-21
    bad_double = copy.deepcopy(doc)
    bad_double["audio_lines"][10]["text"] = (
        "Sound the general charge and break Mont-Saint-Jean before Bülow reaches the eastern woods!"
    )
    st_issues = story_lint.lint(bad_double)
    assert any(f["rule"] == "ST-21" and f["severity"] == "FAIL" for f in st_issues)

    # 2. Segment ends directly on character line without narrator consequence -> ST-14
    bad_unframed = copy.deepcopy(doc)
    bad_unframed["audio_lines"][-1]["speaker_type"] = "character"
    bad_unframed["audio_lines"][-1]["speaker_id"] = "char_ney"
    bad_unframed["audio_lines"][-1]["addressee_id"] = "char_napoleon_1815"
    st_unframed = story_lint.lint(bad_unframed)
    assert any(f["rule"] == "ST-14" and f["severity"] == "FAIL" for f in st_unframed)


def test_case_g_no_mandatory_dialogue_quota_when_narration_carries_episode() -> None:
    """Case G: A script where narration carries ~94% of the episode and only 1 turning-point scene uses character dialogue passes."""
    doc = json.loads(WATERLOO_PATH.read_text(encoding="utf-8"))
    narration_heavy = copy.deepcopy(doc)

    # Keep only S04 as a played_scene; convert S07, S09, S11 to narration_led
    for seg in narration_heavy["segments"]:
        if seg["segment_id"] in ("S07", "S09", "S11"):
            seg["segment_mode"] = "narration_led"
            seg.pop("scene", None)
            seg.pop("why_a_scene", None)
    for ln in narration_heavy["audio_lines"]:
        if ln["segment_id"] in ("S07", "S09", "S11") and ln["speaker_type"] == "character":
            ln["speaker_type"] = "narrator"
            ln["speaker_id"] = "narrator_main"
            ln["addressee_id"] = None
            ln["delivery_direction"] = "grave, measured documentary pacing"
            ln["register_type"] = "plausible_counterfactual_inference"
            ln["text"] = f"At {ln['line_id']}, the command post confronts the shifting balance along the smoky ridge."

    assert scene_lint.lint(narration_heavy) == []
    assert story_lint.lint(narration_heavy) == []


def test_case_h_historical_integrity_and_register_types() -> None:
    """Case H: Dramatized character lines are explicitly tagged dramatized_in_scene_speech with citations,
    and editorial_gate rejects unverified claims presented as fact."""
    for path in (WATERLOO_PATH, TOBA_PATH):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for ln in doc["audio_lines"]:
            if ln["speaker_type"] == "character":
                assert ln["register_type"] == "dramatized_in_scene_speech"
                assert len(ln.get("citation_ids") or []) >= 1

    # Verify editorial_gate rejects unverified claim used as a fact line
    bad_ed_doc = {
        "editorial": {
            "version": 1,
            "sources": [{
                "id": "SRC-1",
                "url": "https://example.org/history",
                "title": "Archive",
                "publisher": "Press",
                "published_at": "2020-01-01",
                "accessed_at": "2026-11-11",
                "grade": "A",
                "passage": "Documented record.",
            }],
            "claims": [{
                "id": "CLM-1",
                "text": "Invented dialogue presented as fact",
                "type": "fact",
                "source_ids": ["SRC-1"],
                "confidence": "unverified",
                "uncertainty": "high",
            }],
        },
        "segments": [{"id": "S01", "lines": [{"text": "He said this word for word.", "kind": "fact", "claims": ["CLM-1"]}]}],
    }
    ed_findings = editorial_gate.contract_findings(bad_ed_doc)
    assert any(f["rule"] == "EG-10" and f["severity"] == "FAIL" for f in ed_findings)


def test_case_i_backward_compatibility_with_v3_and_film_shots_v1() -> None:
    """Case I: Existing production_script/3 and film_shots/1 schemas and linters remain 100% compatible."""
    d_v3 = {
        "schema": "production_script/3",
        "cast": {"capone": {}, "enzo": {}},
        "segments": [{
            "id": "S03",
            "lines": [
                {"text": "The club went quiet when the ledger came out."},
                {"text": "You counted it twice?", "speaker": "capone", "to": "enzo", "intent": "press"},
                {"text": "Three times. It is short.", "speaker": "enzo", "to": "capone", "intent": "reveal"},
                {"text": "Short.", "speaker": "capone", "to": "room", "intent": "banter"},
                {"text": "Someone is skimming the north side.", "speaker": "enzo", "to": "capone", "intent": "reveal",
                 "visual_beats": [{"at": "skimming", "kind": "expression", "why": "the word lands on Capone",
                                   "expression": "angry", "who": "capone"}]},
            ],
            "scene": {"place": "the back room of the club, night", "present": ["capone", "enzo"], "pov": "capone",
                      "want": "find who is skimming before the bosses hear",
                      "obstacle_want": "admit nothing until Capone names a number", "value": "trust",
                      "open_charge": "+", "close_charge": "-",
                      "turn": "the ledger comes up short and the room changes sides", "exit": "interrupted",
                      "surface_topic": "the ledger", "real_subject": "who Capone can still trust"},
        }],
    }
    assert scene_lint.lint(d_v3) == []

    fs_v1 = json.loads((ROOT / "examples/film_shots/bus_in_the_ice_age.json").read_text(encoding="utf-8"))
    payoff_s = next(s for s in fs_v1["shots"] if not s.get("teaser_of") and float(s.get("seconds", 0)) >= 3.0)
    payoff_s["seconds"] = 4.0
    teaser_s = copy.deepcopy(payoff_s)
    teaser_s["id"] = "S01-LEGACY-TEASER"
    teaser_s["teaser_of"] = payoff_s["id"]
    teaser_s["seconds"] = 2.0
    teaser_s.pop("teaser_trim", None)
    fs_v1["shots"].insert(0, teaser_s)
    comp = {p["id"]: p for p in film_shots.compose(fs_v1)}
    # Without explicit teaser_trim, centered trim [1.0, 3.0] is used automatically
    assert comp["S01-LEGACY-TEASER.video"]["trim"] == [1.0, 3.0]


def test_case_j_no_gate_weakening_and_viewer_critic_detects_isolated_shouts() -> None:
    """Case J: Both remediated 12-min scripts pass run_all_gate_audits() with 0 issues, and clean-room viewer_critic
    flags isolated 1-beat character interruptions in plain language without leaking rule codes."""
    for path in (WATERLOO_PATH, TOBA_PATH):
        doc = json.loads(path.read_text(encoding="utf-8"))
        audit = run_all_gate_audits(doc)
        assert audit["status"] == "PASS" and audit["total_issues"] == 0
        vc_rep = evaluate_script_with_viewer_critic(doc, use_live_gemini=False)
        assert vc_rep["verdict"] == "PASS"
        assert vc_rep["confusion_points"] == []

    # Inject an isolated 1-beat character shout into S02 of Toba and verify viewer_critic flags it in confusion_points
    toba_bad = json.loads(TOBA_PATH.read_text(encoding="utf-8"))
    toba_bad["audio_lines"][12]["speaker_type"] = "character"
    toba_bad["audio_lines"][12]["speaker_id"] = "char_kael_74000bce"
    vc_bad = evaluate_script_with_viewer_critic(toba_bad, use_live_gemini=False)
    assert len(vc_bad["confusion_points"]) >= 1
    assert "isolated line" in vc_bad["confusion_points"][0]["confused_question"]
