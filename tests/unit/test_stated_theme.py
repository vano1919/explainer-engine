"""Tests for VAL-STATED-THEME from TASK_VAL_STATED_THEME.md section 7."""
import json

from explainer_engine.scripting import stated_theme as M

THEME = "courage is choosing to stay when you could run"
HERO = "Courage is choosing to stay here when you could simply run away"


def seg(sid, lines, scene=None, **kw):
    d = {"id": sid, "lines": lines}
    if scene is not None:
        d["scene"] = scene
    d.update(kw)
    return d


def doc(*segs, theme=THEME):
    d = {"drama": {"premise": "p"}, "segments": list(segs)}
    if theme:
        d["drama"]["theme"] = theme
    return d


N = lambda t: {"text": t}
C = lambda t, who="Ann": {"text": t, "speaker": who}
SCENE = {"place": "p", "present": ["Ann", "Bob"], "pov": "Ann", "want": "w", "obstacle_want": "Bob wants the gate shut"}
CLEAN = [C("Open the gate before they arrive tonight", "Ann"), C("The captain forbade it, you know that well", "Bob")]


def by(f, rule):
    return [x for x in f if x["rule"] == rule]


def test_clean_script_has_no_findings():
    assert M.check(doc(seg("S01", CLEAN, SCENE))) == []


def test_a_hero_stating_the_theme_is_review_sth01():
    f = by(M.check(doc(seg("S06", [C(HERO, "Ann"), C("Bob answers back loudly now", "Bob")], SCENE))), "STH-01")
    assert len(f) == 1 and f[0]["severity"] == "REVIEW"
    assert "Courage is choosing" in f[0]["detail"] and "REVIEW: a reading flag" in f[0]["detail"]


def test_moral_phrase_triggers_without_a_theme_sth01():
    f = M.check(doc(seg("S01", [C("Remember the lesson is that nobody ever walks alone through winter", "Ann"), C("Fine then, Bob said", "Bob")], SCENE), theme=None))
    assert by(f, "STH-01") and by(f, "STH-00")


def test_narrator_line_stating_the_theme_is_not_flagged():
    assert not by(M.check(doc(seg("S01", [N(HERO), N("The lesson is that nobody walks alone here at all")]))), "STH-01")


def test_short_line_below_min_words_is_not_flagged():
    assert not by(M.check(doc(seg("S01", [C("The lesson is clear", "Ann"), C("ok then", "Bob")], SCENE))), "STH-01")


def test_stated_by_the_only_voice_adds_sth02():
    f = M.check(doc(seg("S06", [C(HERO, "Ann"), N("Silence.")])))
    assert by(f, "STH-01") and by(f, "STH-02")
    f2 = M.check(doc(seg("S06", [C(HERO, "Ann"), C("Bob answers back loudly now", "Bob")])))
    assert by(f2, "STH-01") and not by(f2, "STH-02")


def test_obstacle_declared_but_one_speaker_is_review_sth03():
    f = by(M.check(doc(seg("S02", [C("Open the gate before they arrive tonight", "Ann"), N("Nothing.")], SCENE))), "STH-03")
    assert f and f[0]["severity"] == "REVIEW"


def test_a_reaction_beat_by_another_present_character_counts_as_opposition():
    lines = [dict(C("Open the gate before they arrive tonight", "Ann"), visual_beats=[{"kind": "expression", "who": "Bob"}])]
    assert not by(M.check(doc(seg("S02", lines, SCENE))), "STH-03")


def test_segment_without_scene_or_dialogue_is_skipped():
    assert M.check(doc(seg("S01", [N("Just narration of events"), N("More narration here")]))) == []


def test_severity_is_always_review_and_exit_code_is_zero(tmp_path):
    segs = [seg(f"S0{i}", [C(HERO, "Ann")], SCENE) for i in range(1, 6)]
    f = M.check(doc(*segs))
    assert len(f) >= 5 and {x["severity"] for x in f} == {"REVIEW"}
    p = tmp_path / "s.json"; p.write_text(json.dumps(doc(*segs)))
    assert M.main([str(p)]) == 0 and M.main([str(tmp_path / "none.json")]) == 2


def test_both_speaker_schemas_work():
    v3 = doc(seg("S06", [C(HERO, "Ann"), N("Silence.")], SCENE))
    v4 = doc(seg("S06", [{"text": HERO, "speaker_type": "character", "speaker_id": "Ann"},
                         {"text": "Silence.", "speaker_type": "narrator"}], SCENE))
    key = lambda f: sorted((x["rule"], x["where"]) for x in f)
    assert key(M.check(v3)) == key(M.check(v4)) and by(M.check(v4), "STH-01")


def test_missing_theme_is_not_run_not_a_pass():
    f = by(M.check(doc(seg("S01", CLEAN, SCENE), theme=None)), "STH-00")
    assert f and f[0]["severity"] == "NOT_RUN"


def test_theme_text_argument_and_controlling_idea_fallback():
    d = doc(seg("S06", [C(HERO, "Ann"), C("Bob answers back loudly now", "Bob")]), theme=None)
    assert by(M.check(d, theme_text=THEME), "STH-01")
    d["drama"]["controlling_idea"] = THEME
    assert by(M.check(d), "STH-01") and not by(M.check(d), "STH-00")


def test_where_uses_the_pv37_line_spelling():
    f = by(M.check(doc(seg("S06", [N("Intro line."), C(HERO, "Ann"), C("Bob answers back loudly now", "Bob")]))), "STH-01")
    assert f[0]["where"] == "S06#2"


def test_exempt_cold_open_and_shorts():
    assert not by(M.check(doc(seg("S01", [C(HERO, "Ann")], type="cold_open"))), "STH-01")
    d = doc(seg("S01", [C(HERO, "Ann")])); d["format"] = "short"
    assert M.check(d) == []


# ---- boundary test (2026-11-20 mutation spot-check: `>=` to `>` survived) ----

def test_sth01_fires_when_the_overlap_equals_theme_cover_min_exactly(tmp_path):
    theme = "courage persists"                                    # two content words
    line = "Courage rarely arrives when marching through winter storms"   # contains "courage" only: overlap 1/2
    assert len(M.content_words(line)) >= 6 and M.content_words(theme) & M.content_words(line) == {"courage"}
    assert len(M.content_words(theme)) == 2
    rules_file = tmp_path / "r.json"
    rules_file.write_text(json.dumps({"theme_cover_min": 0.5, "min_line_words": 6, "moral_phrases": []}))
    d = doc(seg("S01", [C(line, "Ann"), C("Bob answers back loudly now", "Bob")], SCENE), theme=theme)
    assert by(M.check(d, rules_path=rules_file), "STH-01")                        # exactly at the minimum: it states the theme
    rules_file.write_text(json.dumps({"theme_cover_min": 0.51, "min_line_words": 6, "moral_phrases": []}))
    assert not by(M.check(d, rules_path=rules_file), "STH-01")                    # just above the overlap: it does not
