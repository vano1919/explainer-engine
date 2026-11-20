"""Tests for VAL-SHIFT-LINE-ID, written from TASK_VAL_SHIFT_LINE_ID.md section 7 (not from Gemini's code).
Real story_lint."""
import json

import pytest

from explainer_engine.scripting import shift_line_id as M


def seg(sid, lines, shift="safe -> hunted", shift_line=None, function="turn", **extra):
    d = {"function": function, "stakes": "x"}
    if shift is not None:
        d["shift"] = shift
    if shift_line is not None:
        d["shift_line"] = shift_line
    return dict({"id": sid, "lines": lines, "drama": d}, **extra)


def doc(*segs):
    return {"drama": {"premise": "p"}, "segments": list(segs)}


NARR = lambda t: {"text": t}
CHAR = lambda t, who="Ann": {"text": t, "speaker": who}


def rules(findings, rule):
    return [f for f in findings if f["rule"] == rule]


def ok_doc():
    return doc(
        seg("S01", [NARR("The pass was quiet."), CHAR("We are hunted now, run.")], "safe -> hunted", "S01#2"),
        seg("S02", [NARR("Snow fell."), CHAR("The gate opened for them at last."), NARR("They walked in.")],
            "locked -> gate opened", "S02#2"),
        seg("S03", [NARR("The end.")], "x -> y", None, function="button"),
    )


def test_ok_script_has_no_findings():
    assert M.check(ok_doc()) == []


def test_missing_shift_line_is_review_and_fail_under_strict_sl01():
    d = doc(seg("S01", [NARR("a"), NARR("b")], "safe -> hunted", None))
    f = rules(M.check(d), "SL-01")
    assert [x["severity"] for x in f] == ["REVIEW"]
    assert [x["severity"] for x in rules(M.check(d, strict=True), "SL-01")] == ["FAIL"]
    d2 = doc(seg("S01", [NARR("a"), NARR("b")], "safe -> hunted", []))
    assert rules(M.check(d2), "SL-01")


def test_all_three_id_schemes_resolve():
    lines = [{"text": "one"}, {"text": "hunted by the guards", "id": "L-9", "speaker": "A"},
             {"text": "three", "shot_id": "SH012"}]
    idx = M.line_index({"id": "S05", "lines": lines})
    assert idx["L-9"][0] == 2 and idx["S05#3"][0] == 3 and idx["SH012"][0] == 3
    for ref in ("L-9", "S05#2", "SH012"):
        d = doc(seg("S05", lines, "safe -> hunted", ref))
        assert not rules(M.check(d), "SL-02"), ref


def test_list_of_two_ids_works():
    lines = [{"text": "a b c"}, {"text": "hunted down", "speaker": "A", "shots": [{"id": "SH012"}]},
             {"text": "hunted again", "speaker": "A", "shot_id": "SH013"}]
    d = doc(seg("S05", lines, "safe -> hunted", ["SH012", "SH013"]))
    assert M.check(d) == []


def test_id_from_another_segment_fails_sl02_and_names_it():
    a = seg("S06", [CHAR("x"), CHAR("hunted here")], "a -> hunted", "SH021")
    a["lines"][1]["shot_id"] = "SH021"
    b = seg("S07", [CHAR("y"), CHAR("hunted too")], "a -> hunted", "SH021")
    f = rules(M.check(doc(a, seg("S08", [CHAR("q"), CHAR("hunted")], "a -> hunted", "SH021"))), "SL-02")
    assert f and f[0]["severity"] == "FAIL" and "S06" in f[0]["detail"]
    f2 = rules(M.check(doc(a, b)), "SL-02")
    assert f2 and "S06" in f2[0]["detail"]


def test_unknown_id_fails_sl02():
    f = rules(M.check(doc(seg("S01", [CHAR("a"), CHAR("b")], "x -> y", "NOPE"))), "SL-02")
    assert f and f[0]["severity"] == "FAIL"


def test_same_line_in_two_segments_fails_sl03():
    lines = lambda: [{"text": "start"}, {"text": "hunted now", "speaker": "A", "shot_id": "SH099"}]
    d = doc(seg("S01", lines(), "a -> hunted", "SH099"), seg("S02", lines(), "a -> hunted", "SH099"))
    f = rules(M.check(d), "SL-03")
    assert f and all(x["severity"] == "FAIL" for x in f)


def test_first_line_with_a_before_state_is_review_sl04():
    d = doc(seg("S01", [CHAR("we are hunted"), CHAR("b")], "safe -> hunted", "S01#1"))
    assert rules(M.check(d), "SL-04")


def test_empty_text_line_is_review_sl04():
    d = doc(seg("S01", [CHAR("x"), {"text": "  ", "speaker": "A"}], "safe -> hunted", "S01#2"))
    f = rules(M.check(d), "SL-04")
    assert f and f[0]["severity"] == "REVIEW"


def test_narrator_only_turn_in_a_dialogue_segment_is_review_sl05():
    d = doc(seg("S01", [CHAR("hello there"), NARR("They were hunted at dawn.")], "safe -> hunted", "S01#2"))
    f = rules(M.check(d), "SL-05")
    assert f and f[0]["severity"] == "REVIEW"


def test_narrator_turn_in_a_narration_segment_is_fine():
    d = doc(seg("S01", [NARR("It was quiet."), NARR("They were hunted at dawn.")], "safe -> hunted", "S01#2"))
    assert not rules(M.check(d), "SL-05")


def test_after_state_missing_from_the_line_is_review_sl06():
    d = doc(seg("S01", [CHAR("a"), CHAR("Nothing relevant happens here at all"), CHAR("Or here either")],
                "safe -> hunted", "S01#2"))
    assert rules(M.check(d), "SL-06")


def test_after_state_in_the_next_line_passes_with_window_1():
    d = doc(seg("S01", [CHAR("a"), CHAR("The door shut quietly behind them"), CHAR("Now they are hunted")],
                "safe -> hunted", "S01#2"))
    assert not rules(M.check(d), "SL-06")


def test_shift_without_an_arrow_is_review_sl06():
    d = doc(seg("S01", [CHAR("a"), CHAR("b c d")], "safe to hunted", "S01#2"))
    f = rules(M.check(d), "SL-06")
    assert f and f[0]["severity"] == "REVIEW"


def test_parse_shift():
    for a in ("->", "→", "=>", "—>"):
        assert M.parse_shift(f"safe {a} hunted") == ("safe", "hunted")
    assert M.parse_shift("no arrow") is None


def test_button_segment_is_exempt():
    assert M.check(doc(seg("S01", [NARR("x")], "a -> b", None, function="button"))) == []


def test_no_drama_block_is_skipped_not_raised():
    assert M.check({"segments": [{"id": "S01", "lines": [{"text": "x"}]}]}) == []
    assert M.check({}) == [] and M.check({"segments": [{"id": "S01"}, "junk", {"drama": {"shift": "a -> b"}}]}) is not None


def test_script_a_shape():
    s2 = seg("S02", [NARR("They wait."), NARR("Nothing.")], "calm -> panic", None)
    s5 = seg("S05", [CHAR("x"), {"text": "hunted by the lines", "speaker": "A", "shot_id": "SH012"},
                     {"text": "hunted again", "speaker": "B", "shot_id": "SH013"}], "safe -> hunted", ["SH012", "SH013"])
    f = M.check(doc(s2, s5))
    assert [x["where"] for x in rules(f, "SL-01")] == ["S02"] and not [x for x in f if x["where"].startswith("S05")]


def test_main_exit_codes(tmp_path, capsys):
    fail = tmp_path / "f.json"; fail.write_text(json.dumps(doc(seg("S01", [CHAR("a"), CHAR("b")], "x -> y", "NOPE"))))
    rev = tmp_path / "r.json"; rev.write_text(json.dumps(doc(seg("S01", [CHAR("a"), CHAR("b")], "x -> y", None))))
    assert M.main([str(fail)]) == 1 and M.main([str(rev)]) == 0 and M.main([str(tmp_path / "nope.json")]) == 2
    assert M.main([str(rev), "--strict"]) == 1


def test_existing_st03_is_unchanged():
    import copy
    from test_story_engine import storied
    from explainer_engine.scripting import story_lint as SL
    d = storied()
    before = json.dumps(SL.lint(copy.deepcopy(d)), sort_keys=True)
    M.check(d)
    assert json.dumps(SL.lint(copy.deepcopy(d)), sort_keys=True) == before


def test_findings_quote_the_line_and_address():
    d = doc(seg("S01", [CHAR("a"), CHAR("Nothing relevant happens here at all")], "safe -> hunted", "S01#2"))
    f = rules(M.check(d), "SL-06")[0]
    assert "S01#2" in f["detail"] and "Nothing relevant" in f["detail"] and f["where"] == "S01#2"


# ---- boundary tests (2026-11-20 mutation spot-check: these two survived the first test set) ----

def test_sl06_overlap_exactly_at_the_minimum_is_not_flagged_and_just_above_it_is(tmp_path):
    """SL-06 flags overlap strictly BELOW the minimum; the rules file is injected so the score can be made exact."""
    after_state, line_text = "gate opened", "The gate is shut"      # content-word overlap is exactly 0.5
    d = doc(seg("S01", [NARR("a"), CHAR(line_text)], f"locked -> {after_state}", "S01#2"))
    assert M._overlap_score(after_state, line_text) == 0.5

    def rules_file(minimum):
        p = tmp_path / f"r{minimum}.json"
        p.write_text(json.dumps({"after_overlap_min": minimum, "neighbour_window": 0}))
        return p
    assert not rules(M.check(d, rules_path=rules_file(0.5)), "SL-06")          # equal: not below the minimum
    assert rules(M.check(d, rules_path=rules_file(0.51)), "SL-06")             # just above the score: flagged
    assert not rules(M.check(d, rules_path=rules_file(0.49)), "SL-06")


def test_sl01_empty_shift_line_is_fail_under_strict_and_review_otherwise():
    d = doc(seg("S01", [NARR("a"), NARR("b")], "safe -> hunted", []))
    assert [x["severity"] for x in rules(M.check(d), "SL-01")] == ["REVIEW"]
    f = rules(M.check(d, strict=True), "SL-01")
    assert [x["severity"] for x in f] == ["FAIL"] and "empty" in f[0]["detail"]
