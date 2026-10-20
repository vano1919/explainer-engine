"""Rule consistency after merging PR #9 (scene rewrite, D-58) and PR #10 (sourced rules, D-59): narration, story, scenes
and Shorts text (rescan 2026-10-20, findings A R-13..R-29, B tables 1-3, C 3/4/9/10/12). One number, one home: every
threshold below is compared with ``sourced_rules.T`` and every severity with the registry entry, never with a literal, so
the creator's FAIL-or-REVIEW answer for the D-58 limits is a JSON-only switch."""

from __future__ import annotations

import copy
import re

import pytest

from explainer_engine.production import compile as C
from explainer_engine.production import editorial_gate as EG
from explainer_engine.production import shorts as SH
from explainer_engine.production import validate as V
from explainer_engine.qa import engagement as ENG
from explainer_engine.rights import ip_check
from explainer_engine.scripting import narration_lint as L
from explainer_engine.scripting import scene_lint as SC
from explainer_engine.scripting import story_lint as ST
from explainer_engine.standards import sourced_rules as SR
from test_production_script import mini
from test_scene_system import scene_doc, story_doc

WPM = SR.T("BP-01", "wpm_target")


def sev_of(rule_id: str) -> str:
    return SR.rule(rule_id).get("severity", "REVIEW")


def sc(doc, rule):
    return [f for f in SC.lint(doc) if f["rule"] == rule]


def pv(doc, rule, needle=""):
    return [f for f in V.check_script(doc, None) if f["rule"] == rule and needle in f["detail"]]


# --- the new registry entries ----------------------------------------------------------------------------------------------

def test_the_new_entries_are_registered_and_read():
    house = {"BP-16", "BP-70", "BP-71", "BP-72", "BP-77"}
    hypo = {"BP-17", "BP-18", "BP-73", "BP-74", "BP-75", "BP-76"}
    for rid in house:
        r = SR.rule(rid)
        assert r["status"] == "house" and r["decided"] and r["sources"], rid
    for rid in hypo:
        assert SR.rule(rid)["status"] == "hypothesis" and SR.rule(rid)["severity"] == "REVIEW", rid
    for rid in ("BP-70", "BP-71", "BP-72"):  # the creator, 2026-10-20: PR #9's limits stop an episode
        assert "2026-10-20" in SR.rule(rid)["decided"] and "D-58" in SR.rule(rid)["decided"]
    assert (L.ELLIPSES_PER_BEAT, L.ELLIPSES_FAIL_OVER) == (SR.T("BP-16", "ellipses_per_beat_max"), SR.T("BP-16", "ellipses_fail_over"))
    assert (L.WORDS_PER_QUESTION, L.WORDS_PER_INTERJECTION) == (SR.T("BP-17", "words_per_question"), SR.T("BP-17", "words_per_interjection"))
    assert L.WH_QUESTION_MAX_WORDS == SR.T("BP-18", "wh_question_max_words") and L.MAX_HOLD_S == SR.T("BP-10", "max_hold_s")
    assert (SC.MIN_EXCHANGE, SC.MIN_EXCHANGE_SPEAKERS) == (SR.T("BP-70", "min_exchange_lines"), SR.T("BP-70", "min_exchange_speakers"))
    assert SC.MAX_DISCLAIMER_SEGMENTS == SR.T("BP-71", "disclaimer_segments_max")
    assert (SC.MAX_TURN_WORDS, SC.SPEECH_WORDS, SC.MAX_SPEECHES) == tuple(SR.T("BP-72", k) for k in
                                                                       ("turn_words_max", "speech_words", "speeches_per_scene_max"))
    assert (SC.REVIEW_TURN_WORDS, SC.MAX_QA_CHAIN) == (SR.T("BP-73", "turn_words_review"), SR.T("BP-73", "qa_chain_max"))
    assert ST.MAX_UNANSWERED_QUESTIONS == SR.T("BP-74", "stacked_questions_min")
    assert list(ST.MIDPOINT_BAND) == SR.T("BP-75", "midpoint_share") and ST.MIDPOINT_MIN_SEGMENTS == SR.T("BP-75", "min_segments")
    assert ST.TURN_GAP_S == SR.T("BP-76", "turn_gap_s")
    assert (ip_check.MAX_QUOTES, ip_check.MAX_QUOTE_WORDS, ip_check.MAX_QUOTE_SENTENCES, ip_check.RECAP_REVIEW,
            ip_check.RECAP_FAIL) == tuple(SR.T("BP-77", k) for k in ("quotes_max", "quote_words_max", "quote_sentences_max",
                                                                      "recap_share_review", "recap_share_fail"))
    assert (EG.MIN_SCORE, EG.MIN_MEAN) == (3, 3.8)  # SCRIPTING_SPEC section 5: process constants, named once (not BP)


def test_severity_is_a_json_switch(monkeypatch):
    """Each registered check takes its severity from the registry: flipping the JSON flips the finding."""
    long_turn = scene_doc()
    long_turn["segments"][0]["lines"][3]["text"] = " ".join(["word"] * (SC.MAX_TURN_WORDS + 5)) + "."
    no_exchange = scene_doc()
    no_exchange["segments"][0]["lines"].insert(2, {"text": "The room waits."})
    no_exchange["segments"][0]["lines"].insert(4, {"text": "Nobody breathes."})
    ellipses = "Could they survive?... No... tools... But night is coming.\n"
    for rid, case in (("BP-72", lambda: sc(long_turn, "SC-09")), ("BP-70", lambda: [f for f in sc(no_exchange, "SC-05") if "BP-70" in f["detail"]]),
                      ("BP-16", lambda: [f for f in L.lint(ellipses) if f["rule"] == "N-03"])):
        assert case() and case()[0]["severity"] == sev_of(rid), rid
        flipped = "REVIEW" if sev_of(rid) == "FAIL" else "FAIL"
        monkeypatch.setitem(SR.rule(rid), "severity", flipped)
        assert case()[0]["severity"] == flipped, rid
        monkeypatch.undo()


# --- C-4: one press-release lexicon (BP-15) for N-14 and SC-07, narrator lines only -------------------------------------------

PROBE = ["The game is set to release this winter.", "The release date is November 19.", "Rockstar announced it in May.",
         "The trailer shows a beach.", "Coming November, the city opens.", "It comes out on November 19.",
         "The game is now available.", "As reported by the press, the map is huge.", "It launches worldwide in the fall."]


@pytest.mark.parametrize("line", PROBE)
def test_n14_and_sc07_read_one_lexicon(line):
    n14 = [f for f in L.lint("Could they survive the night? But it gets cold.\n" + line + "\n") if f["rule"] == "N-14"]
    d = scene_doc()
    d["segments"][0]["lines"][0]["text"] = line
    sc07 = sc(d, "SC-07")
    assert n14 and sc07, line  # the probe of the rescan: each list used to miss the other's phrases
    assert n14[0]["severity"] == sc07[0]["severity"] == sev_of("BP-15")
    assert L.press_release(line)


def test_a_hero_may_name_the_date_inside_a_scene():
    d = scene_doc()
    d["segments"][0]["lines"][1]["text"] = "Then say it. The frost comes out on the nineteenth?"  # Capone, to Enzo
    assert not sc(d, "SC-07") and not [f for f in L.doc_findings(d) if f["rule"] == "N-14"]
    d["segments"][0]["lines"][0]["text"] = "The frost comes out on the nineteenth."  # the narrator says it
    assert [f for f in L.doc_findings(d) if f["rule"] == "N-14"]


def test_validate_lints_narrator_lines_only_and_keeps_the_old_contract_on_earlier_schemas():
    d = mini()
    d["segments"][1]["lines"][0]["text"] = "Then Einstein says it comes out on Friday."
    assert [f for f in pv(d, "PV-12", "N-14") if f["severity"] == sev_of("BP-15")]
    d["segments"][1]["lines"][0]["speaker"] = "einstein"  # the same words in a hero's mouth
    assert not pv(d, "PV-12", "N-14")
    d = mini()
    d["segments"][1]["lines"][0]["text"] = "Then the council announced the plan."  # a pattern, not a phrase
    assert not pv(d, "PV-12", "N-14")  # /1 and /2 keep their contract (D-58); the patterns bind from /3 on


# --- C-3: one pace definition (BP-01, heard pace) -----------------------------------------------------------------------------

def test_every_estimate_uses_bp01_heard_pace():
    assert ST.WORDS_PER_S * 60 == WPM and ENG.WPM == WPM and V.SHORT_WPM == WPM
    assert SR.T("BP-12", "words_per_s") * 60 == pytest.approx(WPM, abs=0.01)
    d = mini()
    read = V.estimated_words(d)
    heard = V.heard_wpm(read)
    spoken = sum(1 for w in read["words"] if re.search(r"[A-Za-z0-9]", w["w"]))
    assert heard == pytest.approx(spoken / read["duration"] * 60)
    assert heard < sum(d["voice"]["pace_wpm"]) / 2  # the pauses make the heard pace slower than the speaking rate
    found = pv(d, "PV-52 BP-01")
    assert bool(found) == (not SR.T("BP-01", "wpm_min") <= heard <= SR.T("BP-01", "wpm_max"))
    assert all(f["severity"] == sev_of("BP-01") for f in found)  # a hypothesis: REVIEW


def test_st13_counts_seconds_at_the_heard_pace():
    # cold_open is not a turn, so the four segments before the resolution run together
    words = int(SR.T("BP-76", "turn_gap_s") * WPM / 60 / 4) + 5
    found = [f for f in ST.lint(story_doc(["cold_open", "escalation", "escalation", "escalation", "resolution"], words))
             if f["rule"] == "ST-13"]
    assert found and found[0]["severity"] == sev_of("BP-76") and f"{WPM:g} wpm" in found[0]["detail"]
    words = int(SR.T("BP-76", "turn_gap_s") * WPM / 60 / 4) - 5
    assert not [f for f in ST.lint(story_doc(["cold_open", "escalation", "escalation", "escalation", "resolution"], words))
                if f["rule"] == "ST-13"]


# --- C-9: BP-11 word cap AND hook time --------------------------------------------------------------------------------------

def _short(hook, body=("But the fire dies fast.",), last="Watch the full video."):
    return {"id": "SH01", "hook": hook, "style": "fact_bomb",
            "lines": [{"text": hook}] + [{"text": b} for b in body] + [{"text": last}],
            "shots": [{"at": hook.split()[0], "picture": "valley", "crop_x": 0.5}, {"at": "the", "picture": "camp", "crop_x": 0.5}]}


def test_bp11_hook_time_is_the_tighter_bound_and_both_are_checked():
    cap, done = SR.T("BP-11", "hook_max_words"), SR.T("BP-11", "hook_done_by_s")
    assert cap * 60 / WPM > done and "tighter" in SR.rule("BP-11")["statement"]  # 14 words cannot be said in 3 s at 170 wpm
    d = mini()
    long_hook = " ".join(["Could"] + ["they"] * (cap - 2) + ["survive?"])  # inside the word cap, over the time
    d["shorts"] = [_short(long_hook)]
    assert not pv(d, "PV-28", "at most")  # the word cap holds
    timed = pv(d, "PV-28", "hook ends")
    assert timed and timed[0]["severity"] == "REVIEW"  # an estimate; the real read decides
    assert V.hook_end_s(d, d["shorts"][0]) > done
    d["shorts"] = [_short("Could they survive?")]
    assert not pv(d, "PV-28", "hook ends") and V.hook_end_s(d, d["shorts"][0]) <= done


def test_the_real_read_stops_on_a_late_hook_end():
    text = "Could they really survive the whole long frozen night out there with no fire at all".split()
    words = [{"w": w, "s": 0.1 + 0.3 * k, "e": 0.35 + 0.3 * k} for k, w in enumerate(text)]
    ok = SH.hook_timing(words, 3)  # "Could they really" ends at 0.95 s
    assert ok["severity"] == "PASS"
    late = SH.hook_timing(words, len(words))  # 16 words end at 4.85 s
    assert late["hook_end_s"] > SH.HOOK_DONE_BY_S and late["severity"] == sev_of("BP-11") and "BP-11" in late["detail"]
    assert SH.HOOK_DONE_BY_S == SR.T("BP-11", "hook_done_by_s")


# --- C-10: one Short duration, BP-12's statement says what its thresholds compute --------------------------------------------

def test_one_short_duration_everywhere():
    d = mini()
    sh = _short("Could they survive the night?", ("But the fire dies fast. " + " ".join(["word"] * 40),))
    from explainer_engine.production import beats as BEATS
    sd = BEATS.short_doc(C.compile_doc(dict(d, shorts=[sh])), sh)
    read = V.short_words(sd)
    assert read["duration"] == pytest.approx(V.short_seconds(sh), abs=0.01)
    assert read["words"][-1]["e"] <= read["duration"]
    assert V.short_seconds(sh) == pytest.approx(sum(len(x["text"].split()) for x in sh["lines"]) / WPM * 60)


def test_bp12_statement_matches_its_thresholds():
    wps, slack = SR.T("BP-12", "words_per_s"), SR.T("BP-12", "slack")
    text = SR.rule("BP-12")["statement"]
    for lo, hi in SR.T("BP-12", "bands_s"):
        assert re.search(rf"{lo}-{hi} s (is )?about {round(lo * wps * (1 - slack))}-{round(hi * wps * (1 + slack))} words", text)
    assert [(round(a), round(b)) for a, b in V.SHORT_WORD_BANDS] == [(38, 93), (115, 234)]


# --- narration holds and ellipses (BP-10, BP-16), hook forms (BP-03) ---------------------------------------------------------

def test_n15_a_narration_hold_over_bp10_and_the_dialogue_silence_is_a_scene_device():
    d = mini()
    d["segments"][0]["lines"][0]["pause_after"] = SR.T("BP-10", "max_hold_s") + 0.5
    found = [f for f in L.doc_findings(d) if f["rule"] == "N-15"]
    assert found and found[0]["severity"] == sev_of("BP-10")
    d["segments"][0]["lines"][0]["speaker"] = "einstein"  # a scripted silence inside a scene
    assert not [f for f in L.doc_findings(d) if f["rule"] == "N-15"]
    assert [f for f in pv(mini(), "PV-12") if "N-15" in f["detail"]] == []


def test_n03_ellipses_from_bp16():
    two = "Could they survive... the night... alone? But it gets cold.\n"
    three = "Could they... survive... the night... alone? But it gets cold.\n"
    assert [f["severity"] for f in L.lint(two) if f["rule"] == "N-03"] == ["REVIEW"]
    assert [f["severity"] for f in L.lint(three) if f["rule"] == "N-03"] == [sev_of("BP-16")]


def test_n01_reads_the_hook_forms_of_bp03():
    assert L.HOOK_FORMS == tuple(SR.T("BP-03", "hook_forms"))
    assert set(L.HOOK_FORMS) <= set(L._HOOK_TESTS)
    assert L.hook_form("Could they survive?") == "question" and L.hook_form("No tools.") == "cold_open"


# --- engagement: ENG-3 chart beats (BP-08), ENG-5 the answer's place (BP-04), ENG-8 end screen (BP-43) ----------------------

def _seg(i, text, **kw):
    return {"id": f"S{i:02d}", "lines": [{"text": text}], **kw}


def test_eng3_counts_a_chart_or_text_beat_with_the_number():
    seg = _seg(2, "It took 30 seconds.")
    doc = {"episode": {"id": "x"}, "segments": [_seg(1, "Could they survive?"), seg]}
    assert [f for f in ENG.check(doc) if f["rule"] == "ENG-3"]
    seg["lines"][0]["visual_beats"] = [{"at": "30 seconds", "kind": "chart", "why": "counts it", "chart": "counter", "values": [30]}]
    assert not [f for f in ENG.check(doc) if f["rule"] == "ENG-3"]
    seg["lines"][0]["visual_beats"] = [{"at": "30 seconds", "kind": "text", "why": "shows it", "text": "30 S"}]
    assert not [f for f in ENG.check(doc) if f["rule"] == "ENG-3"]


def test_eng5_the_central_answer_waits_for_the_last_tenth():
    share = SR.T("BP-04", "answer_after_share")
    body = "They walk on. " * 30
    early = {"episode": {"id": "x"}, "segments": [_seg(1, "Could they survive?"), _seg(2, body),
                                                 _seg(3, "Yes they do. " * 30, drama={"function": "resolution", "turn": "but"})]}
    found = [f for f in ENG.check(early) if f["rule"] == "ENG-5"]
    assert found and found[0]["severity"] == sev_of("BP-04") and found[0]["where"] == "S03"
    n = int(len(body.split()) * 2 * share / (1 - share)) + 10
    late = copy.deepcopy(early)
    late["segments"][1]["lines"][0]["text"] = "They walk on. " * (n // 3)
    late["segments"][2]["lines"][0]["text"] = "Yes they do."
    assert not [f for f in ENG.check(late) if f["rule"] == "ENG-5"]


def test_eng8_narration_runs_on_under_the_end_screen():
    need = SR.T("BP-43", "end_screen_narration_min_s")
    short_tail = {"episode": {"id": "x"}, "segments": [_seg(1, "Could they survive?"), _seg(2, "They walk on. " * 40),
                                                      _seg(3, "Which coin? That is the next episode.")]}
    found = [f for f in ENG.check(short_tail) if f["rule"] == "ENG-8" and "end screen" in f["detail"]]
    assert found and found[0]["severity"] == sev_of("BP-43") and ENG.END_SCREEN_MIN_S == need
    reps = int(need * WPM / 60 / 3) + 2
    long_tail = copy.deepcopy(short_tail)
    long_tail["segments"][2]["lines"][0]["text"] = "That is the next episode. " + "They walk on. " * reps + "Which coin?"
    assert not [f for f in ENG.check(long_tail) if f["rule"] == "ENG-8"]


# --- rights limits (BP-77) --------------------------------------------------------------------------------------------------

def test_rights_limits_take_bp77s_verdict():
    assert ip_check.LIMIT_VERDICT == sev_of("BP-77")
