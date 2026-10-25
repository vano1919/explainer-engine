"""Rule consistency after the PR #9 / PR #10 merge, picture / motion / visual-beat group (2026-10-20, D-59).

One number, one home: every threshold the beat, motion, board, shot-plan, continuity, accent, bubble and palette checks
enforce is read from the sourced rules (docs/SOURCED_RULES.md), each registered check takes its severity from its rule (a
JSON-only switch), a visual beat counts as a change on screen for BP-40 / BP-41 / BP-45 (the default of 2026-10-20), and
the binding rules win where an older number governed the same quantity (BP-33's flicker floor, BP-40's still limits for
MO-01, BP-03's hook forms for UR-01, BP-27's hold for bubbles, BP-45 for a Short's pace)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.design import palette
from explainer_engine.edit import board as B
from explainer_engine.edit import motion_lint as ML
from explainer_engine.edit import shot_rules as R
from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import accents as ACC
from explainer_engine.production import beats as BEATS
from explainer_engine.production import continuity
from explainer_engine.production import fill_holds as F
from explainer_engine.production import validate as V
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def sev(bp: str) -> str:
    return SR.rule(bp)["severity"]


# --- one number, one home ------------------------------------------------------------------------------------------------

def test_the_beat_numbers_are_the_registrys():
    assert (BEATS.GAP_OK_3, BEATS.GAP_FAIL_3) == (SR.T("BP-36", "gap_review_s"), SR.T("BP-36", "gap_fail_s"))
    assert (BEATS.TARGET, BEATS.GAP_OK, BEATS.GAP_FAIL, BEATS.MEAN_OK) == tuple(
        SR.T("BP-36", k) for k in ("v2_target_s", "v2_gap_review_s", "v2_gap_fail_s", "v2_mean_max_s"))
    assert (BEATS.FACE_OK_3, BEATS.FACE_FAIL_3) == (SR.T("BP-37", "gap_review_s"), SR.T("BP-37", "gap_fail_s"))
    assert BEATS.FACE_FLICKER == SR.T("BP-33", "hold_min_s")  # the binding floor wins over the old 0.7 s (BP-33)
    assert BEATS.MAX_WORDS == SR.T("BP-38", "max_words") == ML.MAX_WORDS  # VB-04 and MO-05 share one cap
    assert list(BEATS.BARS) == SR.T("BP-38", "bars")
    assert (BEATS.CUE_COVER, BEATS.CUE_MIN_GAP) == (SR.T("BP-39", "cover_s"), SR.T("BP-39", "min_gap_s"))
    assert (BEATS.CUE_REPEAT_WINDOW, BEATS.CUE_REPEAT_FAIL) == (SR.T("BP-80", "window_s"), SR.T("BP-80", "fail_count"))
    assert (BEATS.CUE_PER_MIN_OK, BEATS.CUE_PER_MIN_FAIL, BEATS.CUE_BURST) == (
        SR.T("BP-81", "per_min_review"), SR.T("BP-81", "per_min_fail"), SR.T("BP-81", "burst_max"))
    assert BEATS.EMPHASIS_CUES == set(SR.T("BP-81", "emphasis_cues"))
    assert (BEATS.MAX_SAME_RUN, BEATS.MAX_WORD_SHARE, BEATS.MAX_OVERLAYS) == (
        SR.T("BP-82", "same_kind_run_max"), SR.T("BP-82", "word_share_max"), SR.T("BP-82", "overlays_max"))


def test_the_motion_board_and_shot_plan_numbers_are_the_registrys():
    assert (ML.HOOK_WINDOW, ML.HOOK_MAX_GAP, ML.MAX_GAP) == (
        SR.T("BP-40", "hook_window_s"), SR.T("BP-40", "hook_max_still_s"), SR.T("BP-40", "body_review_still_s"))
    assert (ML.WINDOW, ML.MIN_KINDS, ML.MAX_PLAIN_RUN, ML.TEXT_MIN_GAP, ML.HOLD_SIMILAR, ML.MAX_SIMILAR_RUN,
            ML.HOLD_CV) == tuple(SR.T("BP-83", k) for k in ("window_s", "kinds_min", "plain_run_max", "text_min_gap_s",
                                                            "hold_similar", "similar_run_max", "hold_cv_min"))
    assert "alive_share_min" not in SR.rule("BP-83")["thresholds"]  # MO-06 is reported only (D-64)
    assert (B.MIN_SHOT, B.MIN_INSERT) == (SR.T("BP-84", "min_shot_s"), SR.T("BP-84", "min_insert_s"))
    assert F.MIN_PART == B.MIN_SHOT and F.PULL_FROM == SR.T("BP-20", "push_default_max")
    assert F.PUSH_TO <= SR.T("BP-20", "push_default_max") and F.PULL_TO >= SR.T("BP-20", "scale_min")
    assert (BUB.MAX_WORDS, BUB.MAX_CHARS) == (SR.T("BP-38", "max_words"), SR.T("BP-84", "bubble_chars_per_line"))  # D-64
    assert R.DURATIONS == {k: tuple(SR.T("BP-85", f"{k.lower()}_shot_s")) for k in "ABC"}
    assert (R.FIRST_WINDOW, R.FIRST_SLACK, R.FIRST_MIN_SHOTS, R.FIRST_SOUND, R.C_PULL_MAX, R.DISSOLVE_SHARE, R.EDGE,
            R.FACELESS_SHARE, R.MIN_STAKES_WORDS) == tuple(SR.T("BP-85", k) for k in (
                "first_window_s", "first_slack_s", "first_min_shots", "first_sound_s", "c_pull_max", "dissolve_share_max",
                "cut_edge_s", "faceless_share_max", "stakes_words_min"))
    assert list(R.A_ZOOM) == SR.T("BP-85", "a_zoom") and R.HOOK_FORMS == set(SR.T("BP-03", "hook_forms"))
    assert not hasattr(R, "HOOK_SECONDS")  # the superseded "question by 5 s" (BP-03)
    assert continuity.SAME_ZOOM == SR.T("BP-30", "same_framing_zoom_tol")
    assert ACC.PUNCH_ZOOM == pytest.approx(SR.T("BP-20", "punch_max") - 1.0)
    assert ACC.SHAKE_S == min(SR.T("BP-24", "house_decay_s"), SR.T("BP-24", "decay_max_s"))
    assert ACC.SHAKE_AMP == min(SR.T("BP-24", "house_amplitude_h"), SR.T("BP-24", "amplitude_max_h"))
    assert (palette.TEXT_MIN, palette.LARGE_TEXT_MIN) == (SR.T("BP-28", "contrast_min"), SR.T("BP-28", "contrast_large_min"))
    assert (V.TICK_MAX_DB, V.MAX_CROSSFADE) == (SR.T("BP-86", "tick_max_db"), SR.T("BP-86", "crossfade_max_s"))


def test_the_schema_zoom_window_is_bp20s():
    """A JSON Schema cannot read the registry: this pins its camera-move window to BP-20."""
    schema = json.loads((ROOT / "explainer_engine/schemas/production_script.schema.json").read_text(encoding="utf-8"))
    found = []

    def walk(node):
        if isinstance(node, dict):
            if {"z0", "z1"} <= set(node) and isinstance(node["z0"], dict) and "maximum" in node["z0"]:
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    assert found
    for props in found:
        for k in ("z0", "z1"):
            assert props[k]["maximum"] == SR.T("BP-20", "scale_max") and props[k]["minimum"] == SR.T("BP-20", "scale_min")


def test_the_house_numbers_name_their_decision_and_severities_are_valid():
    for bp in ("BP-36", "BP-37", "BP-38", "BP-39", "BP-80", "BP-81", "BP-84", "BP-85", "BP-86"):
        r = SR.rule(bp)
        assert r["status"] == "house" and r["decided"] and r["sources"], bp
    for bp in ("BP-82", "BP-83"):
        assert SR.rule(bp)["status"] == "hypothesis" and sev(bp) == "REVIEW"


# --- severities come from the registry: a JSON-only switch ---------------------------------------------------------------

def _cues(seq):
    return [{"sound": s, "start": t, "end": t + 0.1, "segment": "S01", "line": 1, "kind": "text",
             "start_frame": int(t * 30)} for s, t in seq]


def _cue_find(cues, duration=60.0):
    out: list = []
    BEATS._cue_findings({"duration": duration, "audio": {"cues": cues, "sfx": [], "music": [], "beds": []}},
                        {"schema": BEATS.SCENE_SCHEMA}, [], out)
    return out


def test_registered_checks_follow_the_registry_severity(monkeypatch):
    names = ["tick", "blip", "tap", "pop"]
    dense = _cues([(names[i % 4], 0.3 + i * 1.0) for i in range(15)])  # 15 a minute
    found = [f for f in _cue_find(dense) if f["rule"].endswith("VB-11") and "a minute" in f["detail"]]
    assert found and found[0]["severity"] == sev("BP-81")
    flipped = json.loads(json.dumps(SR.load()))
    for r in flipped["rules"]:
        if r["id"] in ("BP-81", "BP-84", "BP-85"):
            r["severity"] = "REVIEW"
    monkeypatch.setattr(SR, "load", lambda: flipped)
    found = [f for f in _cue_find(dense) if f["rule"].endswith("VB-11") and "a minute" in f["detail"]]
    assert found and found[0]["severity"] == "REVIEW"  # the creator's answer flips in JSON only
    short = [{"id": "SH001", "picture": "p", "start": 0.0, "end": 1.0, "cut_legal": True, "at": "x", "text": "", "bubbles": [],
              "accents": []}, {"id": "SH002", "picture": "q", "start": 1.0, "end": 9.0, "cut_legal": True, "at": "y",
                               "text": "", "bubbles": [], "accents": []}]
    f = [x for x in B.check({"pictures": {"p": {}, "q": {}}, "heroes": {}, "_event_times": {}},
                            {"shots": short, "duration": 9.0}) if x["rule"] == "RHYTHM-2"]
    assert f and f[0]["severity"] == "REVIEW"


# --- C-1: a visual beat is a change on screen (BP-40, BP-41) -------------------------------------------------------------

def _shot(k, a, b, pic):
    return {"id": f"SH{k:03d}", "picture": pic, "start": float(a), "end": float(b), "cut_legal": True, "at": "x", "text": "",
            "bubbles": [], "accents": []}


def _expr(t, who):
    return {"kind": "expression", "start": t, "end": t + 1.0, "who": who, "expression": "worried", "segment": "S02",
            "line": 1}


def test_a_dialogue_held_on_one_picture_with_a_face_change_a_line_passes_bp40():
    """The C-1 case (rescan e2e 'base'): a /3 dialogue scene in the first 30 s held on its scene picture, an expression change
    on every line (VB-02 asks for it), no reframe on a clock and no camera punch. With the beats counted it meets BP-40."""
    shots = [_shot(1, 0, 4, "valley"), _shot(2, 4, 8.5, "camp"), _shot(3, 8.5, 13, "valley"), _shot(4, 13, 17.5, "camp"),
             _shot(5, 17.5, 22.1, "valley"), _shot(6, 22.1, 40.0, "duo")]
    beats = [_expr(t, who) for t, who in ((23.0, "franklin"), (25.6, "einstein"), (28.4, "franklin"), (31.0, "einstein"),
                                          (33.7, "franklin"), (36.2, "einstein"), (38.5, "franklin"))]
    board = {"pictures": {p: {} for p in ("valley", "camp", "duo")}, "heroes": {}, "_event_times": {}}
    bare = [x for x in B.check(board, {"shots": shots, "duration": 40.0}) if x["rule"] == "RHYTHM-3"]
    assert bare and bare[0]["severity"] == sev("BP-40")  # the merged tree's verdict without the beats
    timed = {"shots": shots, "duration": 40.0, "visual_beats": beats}
    assert not [x for x in B.check(board, timed) if x["rule"] in ("RHYTHM-3", "BP-41")]
    assert set(B.change_times(shots, 40.0, timed)) >= {b["start"] for b in beats}
    # the same events the motion lint counts: MO-01 and RHYTHM-3 measure one thing
    ml = {"shots": [dict(s, segment="S02", motion={"kind": "hold"}) for s in shots], "duration": 40.0, "visual_beats": beats}
    assert set(t for t, _ in ML.events(ml)) | {40.0} == set(B.change_times(shots, 40.0, timed))
    assert not [x for x in ML.check(ml) if x["rule"] == "MO-01"]


def test_board_findings_on_a_timed_script_see_the_beats_visuals_and_cards():
    shots = [_shot(1, 0, 40.0, "duo")]
    for s in shots:
        s["segment"] = "S01"
    timed = {"shots": shots, "duration": 40.0, "pictures": {"duo": {}}, "events": {},
             "visual_beats": [{"kind": "label", "start": t} for t in (4.0, 8.0, 12.0, 16.0, 20.0, 24.0)],
             "visuals": [{"start": 28.0}], "cards": [{"start": 32.0}]}
    found = [f for f in V.board_findings(timed, {"cast": {}}) if "RHYTHM-3" in f["rule"] or "BP-41" in f["rule"]]
    assert found == []
    timed["visual_beats"] = []
    assert [f for f in V.board_findings(timed, {"cast": {}}) if "RHYTHM-3" in f["rule"]]


def test_fill_holds_counts_the_beats_too():
    """fill_holds asks board.change_times with the timed script, so a stretch the beats fill gets no re-frame."""
    src = (ROOT / "explainer_engine/production/fill_holds.py").read_text(encoding="utf-8")
    assert "B.change_times(shots, timed[\"duration\"], timed)" in src


# --- R-05 / BP-40: MO-01 is section-aware ---------------------------------------------------------------------------------

def _ml(spans):
    shots = [dict(_shot(k + 1, a, b, f"p{k}"), segment="S01", motion={"kind": "hold"}) for k, (a, b) in enumerate(spans)]
    return {"shots": shots, "duration": float(spans[-1][1])}


def test_mo01_reads_bp40_by_section():
    hook = _ml([(0, 4), (4, 10.5), (10.5, 14), (14, 18), (18, 22), (22, 26), (26, 30), (30, 34)])
    mo = [f for f in ML.check(hook) if f["rule"] == "MO-01"]
    assert len(mo) == 1 and "in the hook" in mo[0]["detail"]  # 6.5 s inside the first 30 s
    body = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24), (24, 28), (28, 32)]
    nine = _ml(body + [(32, 41), (41, 45)])
    assert not [f for f in ML.check(nine) if f["rule"] == "MO-01"]  # the old flat 5 s flagged this
    long = _ml(body + [(32, 53), (53, 57)])
    mo = [f for f in ML.check(long) if f["rule"] == "MO-01"]
    assert len(mo) == 1 and "in the body" in mo[0]["detail"]


# --- R-04: VB-01 /3 nested inside BP-40; R-07 / C-11 the Shorts follow BP-45 -----------------------------------------------

def test_vb01_does_not_run_on_a_short_and_short_events_count_beats():
    from test_short_beats import short_doc_with_beats

    d = short_doc_with_beats()
    sd = BEATS.short_doc(d, d["shorts"][0])
    assert BEATS.is_short(sd) and not BEATS.is_short(d)
    two = copy.deepcopy(d)
    two["shorts"][0]["shots"] = two["shorts"][0]["shots"][:2]  # 2 shots in about 10 s: 2 events every 10 s without beats
    found = [f for f in V.check_script(two) if f["rule"] == "PV-34" and "visual events every 10 s" in f["detail"]]
    assert found == []  # the Short's 8 beats count (SS-09, BP-45)
    for ln in two["shorts"][0]["lines"]:
        ln.pop("visual_beats", None)
    found = [f for f in V.check_script(two) if f["rule"] == "PV-34" and f["where"] == "SH01"
             and "visual events every 10 s" in f["detail"]]
    assert found and found[0]["severity"] == sev("BP-45")


# --- R-11: bubbles hold BP-27's time ---------------------------------------------------------------------------------------

def test_bubbles_read_bp27():
    n = int(SR.T("BP-38", "max_words"))  # a bubble is an accent of BP-38's words (BP-84, D-64; was 14 words)
    words = " ".join(["word"] * n)
    need = max(SR.T("BP-27", "hold_min_s"), SR.T("BP-27", "s_per_word") * n)
    assert BUB.check_bubbles([{"text": words, "start": 0.0, "end": need}]) == []
    f = BUB.check_bubbles([{"text": words, "start": 0.0, "end": 0.3 * n + 0.01}])  # the superseded max(1.4, 0.3 n)
    assert [x["rule"] for x in f] == ["BUBBLE-2"] and f[0]["severity"] == sev("BP-27")
    f = BUB.check_bubbles([{"text": words + " more", "start": 0.0, "end": 9.0}])
    assert [x["rule"] for x in f] == ["BUBBLE-1"] and f[0]["severity"] == sev("BP-84")


# --- PV-29 (BP-86) -----------------------------------------------------------------------------------------------------------

def test_tick_and_crossfade_read_bp86():
    music = [{"track": "theme", "start": 0.0, "end": 20.0, "gain_db": -18},
             {"track": "clockwork_loop", "start": 20.0 - SR.T("BP-86", "crossfade_max_s") - 0.5, "end": 40.0,
              "gain_db": SR.T("BP-86", "tick_max_db") + 1}]
    f = V.music_findings(music)
    assert len(f) == 2 and {x["severity"] for x in f} == {sev("BP-86")}


# --- the board CLI on a production script -----------------------------------------------------------------------------------

def test_board_cli_explains_a_production_script(tmp_path, capsys):
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps({"schema": "production_script/3", "segments": []}), encoding="utf-8")
    words = tmp_path / "words.json"
    words.write_text(json.dumps({"words": [], "duration": 1.0}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        B.main([str(script), str(words)])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "not a storyboard" in err and "production time" in err
