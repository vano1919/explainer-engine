"""The narration, Shorts, engagement, scorecard and speed checks read their numbers from the sourced rules registry
(docs/SOURCED_RULES.md; the creator's audit of 2026-10-19): BP-01..BP-15 and BP-42..BP-46. Every new finding is covered
and every threshold is compared with ``sourced_rules.T`` instead of a copied number."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from explainer_engine.finish import speed
from explainer_engine.production import shorts as SH
from explainer_engine.production import validate as V
from explainer_engine.qa import engagement, scorecard
from explainer_engine.scripting import narration_lint as L
from explainer_engine.standards import sourced_rules as SR
from test_production_script import mini

OPEN = "Could they survive the Stone AGE? No tools. But night is coming.\n"


def found(text, rule, severity=None):
    return [f for f in L.lint(text) if f["rule"] == rule and (severity is None or f["severity"] == severity)]


def pv(doc, rule, needle="", sev=None):
    return [f for f in V.check_script(doc, None) if f["rule"] == rule and needle in f["detail"] and (sev is None or f["severity"] == sev)]


# --- narration_lint -------------------------------------------------------------------------------------------------------

def test_narration_lint_numbers_come_from_the_registry():
    assert L.MAX_SENTENCE_WORDS == SR.T("BP-06", "max_words") and L.HARD_MAX_SENTENCE_WORDS == SR.T("BP-06", "hard_max_words")
    assert L.MEDIAN_SENTENCE_WORDS == SR.T("BP-06", "median_max") and L.MAX_COLD_OPEN_WORDS == SR.T("BP-03", "max_cold_open_words")
    assert L.CONTRACT_WORDS == SR.T("BP-04", "contract_words") and L.YOU_PER_WORDS == SR.T("BP-07", "you_per_words")
    assert L.PASSIVE_SHARE_MAX == SR.T("BP-07", "passive_share_max")
    assert L.BANNED_CONTRACTIONS == {c.lower() for c in SR.T("BP-07", "banned_contractions")}
    assert L.NUMERALS_PER_SENTENCE == SR.T("BP-08", "numerals_per_sentence_max")
    assert L.PRESS_PHRASES == [p.lower() for p in SR.T("BP-15", "phrases")]


def test_n01_the_four_hook_forms_pass_a_greeting_fails_anything_else_is_review():
    """BP-03: a question, a cold-open line, a claim with a number or a preview; never a greeting or branding."""
    tail = " But night is coming.\n"
    assert not found("Could they survive?" + tail, "N-01")
    assert not found("No tools." + tail, "N-01")  # a cold open inside the word cap
    assert not found("In 1931 two men walked out of the camp and never came back to the valley." + tail, "N-01")
    assert not found("You'll see what happens when the fire goes out on the first night of the camp." + tail, "N-01")
    long = " ".join(["word"] * (SR.T("BP-03", "max_cold_open_words") + 1)) + "." + tail
    assert found(long, "N-01", "REVIEW") and not found(long, "N-01", "FAIL")
    for greeting in ("Welcome back to the channel.", "Hi everyone.", "In this video we test a hundred geniuses.",
                     "Today we look at the Stone Age.", "Don't forget to subscribe."):
        assert found(greeting + tail, "N-01", "FAIL"), greeting
    assert found("What happens to them in the Stone Age?" + tail, "N-01", "REVIEW")  # the wh-question advice stays


def test_n05_sentence_length_bands_and_the_median():
    """BP-06: over max_words REVIEW, over hard_max_words FAIL, a high median one REVIEW for the whole text."""
    review = " ".join(["word"] * (SR.T("BP-06", "max_words") + 1)) + "."
    fail = " ".join(["word"] * (SR.T("BP-06", "hard_max_words") + 1)) + "."
    assert found(OPEN + review + "\n", "N-05", "REVIEW") and not found(OPEN + review + "\n", "N-05", "FAIL")
    assert found(OPEN + fail + "\n", "N-05", "FAIL")
    medium = " ".join(["word"] * (SR.T("BP-06", "median_max") + 2)) + "."
    text = "Could they survive? " + " ".join([medium] * 9) + "\n"
    med = [f for f in found(text, "N-05", "REVIEW") if f["where"] == "-"]
    assert len(med) == 1 and "median" in med[0]["detail"]
    assert not [f for f in found(OPEN, "N-05") if f["where"] == "-"]


def test_n11_the_thirty_second_contract_needs_a_question_or_a_turn():
    """BP-04: the first contract_words words carry a '?' or a turn word."""
    flat = "No tools. " + "They walk on. " * (SR.T("BP-04", "contract_words") // 3 + 5) + "\n"
    assert found(flat, "N-11", "REVIEW")
    assert not found("No tools. Until the sun sets. " + "They walk on. " * 40 + "\n", "N-11")
    assert not found(OPEN, "N-11")


def test_n12_spoken_register():
    """BP-07: no -'ve contractions, passive share, 'you' to one listener."""
    assert found(OPEN + "They would've frozen. But then?\n", "N-12", "REVIEW")
    assert found(OPEN + "They would’ve frozen. But then?\n", "N-12", "REVIEW")  # a curly apostrophe too
    passive = OPEN + "The camp was built by Newton. The fire was lit by Franklin. The pot was made by hand. But why?\n"
    assert [f for f in found(passive, "N-12") if "passive" in f["detail"]]
    assert not [f for f in found(OPEN + "Newton builds the camp. Franklin lights the fire. But why?\n", "N-12") if "passive" in f["detail"]]
    gap = OPEN + ("They walk on. " * (SR.T("BP-07", "you_per_words") // 3 + 5)) + "But then?\n"
    you = [f for f in found(gap, "N-12") if "'you'" in f["detail"]]
    assert len(you) == 1  # one finding per text, not per window
    spoken = OPEN + ("You walk on. " * (SR.T("BP-07", "you_per_words") // 3 + 5)) + "But then?\n"
    assert not [f for f in found(spoken, "N-12") if "'you'" in f["detail"]]


def test_n13_one_numeral_per_sentence():
    assert found(OPEN + "In 1931, 2 men paid 17,500 dollars. But why?\n", "N-13", "REVIEW")
    assert not found(OPEN + "In 1931 two men paid a fortune. But why?\n", "N-13")


def test_n14_press_release_lines_fail():
    for phrase in SR.T("BP-15", "phrases")[:4]:
        assert found(OPEN + f"The game {phrase} 26 May. But why?\n", "N-14", "FAIL"), phrase
    assert not found(OPEN + "The game drops in May. But why?\n", "N-14")


# --- validate: PV-12, PV-52 BP-01, PV-28, PV-34 ---------------------------------------------------------------------------

def test_pv12_forwards_narration_reviews_as_reviews():
    d = mini()
    d["segments"][0]["lines"][-1]["text"] = "The rule works well."  # a closed beat: N-02, REVIEW
    assert pv(d, "PV-12", "N-02", "REVIEW")
    assert not pv(d, "PV-12", "N-02", "FAIL")


def test_pv52_pace_band_from_bp01():
    d = mini()
    d["voice"]["pace_wpm"] = [SR.T("BP-01", "wpm_min") - 10, SR.T("BP-01", "wpm_max")]
    assert pv(d, "PV-52 BP-01", "", "REVIEW")
    d["voice"]["pace_wpm"] = [SR.T("BP-01", "wpm_min"), SR.T("BP-01", "wpm_max")]
    assert not pv(d, "PV-52 BP-01")
    assert V.SHORT_WPM == SR.T("BP-01", "wpm_target")


def _short(hook, body, last="But the full video shows who wins.", style="fact_bomb"):
    return {"id": "SH01", "hook": hook, "style": style, "lines": [{"text": hook}] + [{"text": b} for b in body] + [{"text": last}],
            "shots": [{"at": hook.split()[0], "picture": "valley", "crop_x": 0.5}, {"at": "the", "picture": "fire", "crop_x": 0.5}]}


def test_pv28_word_budget_bands_from_bp12():
    d = mini()
    (lo1, hi1), (lo2, hi2) = V.SHORT_WORD_BANDS
    assert lo1 == pytest.approx(SR.T("BP-12", "bands_s")[0][0] * SR.T("BP-12", "words_per_s") * (1 - SR.T("BP-12", "slack")))
    d["shorts"] = [_short("Could they survive the night?", ["But the fire dies fast. " + " ".join(["word"] * int(hi1 - 20))])]
    assert not pv(d, "PV-28", "BP-12")
    other = sum(len(l["text"].split()) for k, l in enumerate(d["shorts"][0]["lines"]) if k != 1) + 5
    d["shorts"][0]["lines"][1]["text"] = "But the fire dies fast. " + " ".join(["word"] * (int((hi1 + lo2) / 2) - other))  # between the bands
    assert pv(d, "PV-28", "BP-12", "REVIEW")
    d["shorts"][0]["lines"][1]["text"] = "But the fire dies fast. " + " ".join(["word"] * int(lo2 + 10))  # the long band
    assert not pv(d, "PV-28", "BP-12")


def test_pv28_hook_cap_statement_review_and_signoff_fail():
    d = mini()
    d["shorts"] = [_short("Could they survive the night?", ["But the fire dies fast."])]
    assert not pv(d, "PV-28", "BP-11") and not pv(d, "PV-28", "BP-44")
    sh = d["shorts"][0]
    sh["hook"] = sh["lines"][0]["text"] = " ".join(["word"] * (SR.T("BP-11", "hook_max_words") + 1)) + "?"
    assert pv(d, "PV-28", "BP-11", "FAIL")
    sh["hook"] = sh["lines"][0]["text"] = "They failed on the first night."
    assert pv(d, "PV-28", "SH-04", "REVIEW") and not pv(d, "PV-28", "SH-04", "FAIL")
    sh["lines"][-1]["text"] = "Thanks for watching, and subscribe."
    assert pv(d, "PV-28", "BP-44", "FAIL")
    d["shorts"] = [_short("Could they survive the night?", ["The fire dies fast.", "Nobody moves."], last="Watch the full video.")]
    assert pv(d, "PV-28", "BP-44", "REVIEW") and not pv(d, "PV-28", "BP-44", "FAIL")  # lines 2-3 without a promise marker


def test_pv28_readability_from_bp46():
    d = mini()
    d["shorts"] = [_short("Could they survive the night?", ["But the fire dies fast."], last="Watch the full video.")]
    assert not pv(d, "PV-28", "BP-46")
    d["shorts"][0]["lines"][1]["text"] = " ".join(["but"] * (SR.T("BP-46", "line_words_max") + 1)) + "."
    assert pv(d, "PV-28", "BP-46", "REVIEW")
    d["shorts"][0]["lines"][1]["text"] = "But the administrative reorganisation of the metropolitan infrastructure was unprecedented."
    assert [f for f in pv(d, "PV-28", "BP-46", "REVIEW") if "grade" in f["detail"]]
    assert V.fk_grade("The cat sat. The dog ran.") < SR.T("BP-46", "grade_max")
    assert V.syllables("fire") == 1 and V.syllables("table") == 2 and V.syllables("banana") == 3


def test_pv34_short_still_and_event_numbers_from_bp45():
    assert V.SHORT_EVENTS_PER_10S == SR.T("BP-45", "events_per_10s_min") and V.SHORT_MAX_STILL_S == SR.T("BP-45", "max_still_s")
    d = mini()
    sh = _short("Could they survive the night?", ["But the fire dies fast. " + " ".join(["word"] * 60)])
    sh["shots"] = sh["shots"][:1]  # one picture over ~25 s
    d["shorts"] = [sh]
    assert pv(d, "PV-34", "BP-45", "REVIEW")


# --- engagement: ENG-7, ENG-8 ---------------------------------------------------------------------------------------------

def _seg(i, *lines, job="explanation"):
    return {"id": f"S{i:02d}", "job": job, "lines": [{"text": t} for t in lines]}


def test_eng7_forward_pointing_cadence_from_bp42():
    assert engagement.LONG_BEAT_WORDS == round(SR.T("BP-01", "wpm_target") * 100 / 60)
    flat = " ".join(["They walk on and on."] * 20)  # 100 words
    n = int(SR.T("BP-42", "review_gap_s") / 60 * SR.T("BP-01", "wpm_target") / 100) + 2
    doc = {"episode": {"id": "x"}, "segments": [_seg(1, "Could they survive?", job="hook")]
           + [_seg(k + 2, flat) for k in range(n)] + [_seg(n + 2, "So who wins?", job="payoff")]}
    rules = {(f["rule"], f["where"]) for f in engagement.check(doc)}
    assert ("ENG-7", f"S{n + 2:02d}") in rules
    doc["segments"][n // 2 + 1]["lines"].append({"text": "But wait."})
    assert not [f for f in engagement.check(doc) if f["rule"] == "ENG-7"]


def test_eng8_abrupt_ending_from_bp43():
    doc = {"episode": {"id": "x"}, "segments": [_seg(1, "Could they survive?", job="hook"),
                                                 _seg(2, "They walk on. " * 30), _seg(3, "The coins changed.", job="payoff")]}
    f = [x for x in engagement.check(doc) if x["rule"] == "ENG-8"]
    assert f and f[0]["severity"] == "REVIEW" and "neither" in f[0]["detail"]
    doc["segments"][2]["lines"] = [{"text": "Which coin? That is the next episode."}]
    assert not [x for x in engagement.check(doc) if x["rule"] == "ENG-8"]
    doc["segments"][2]["lines"] = [{"text": f"{SR.T('BP-43', 'lexicon')[0].capitalize()}: the coins changed. Which coin?"}]
    f = [x for x in engagement.check(doc) if x["rule"] == "ENG-8"]
    assert f and f[0]["severity"] == "FAIL"


# --- scorecard, speed, shorts ---------------------------------------------------------------------------------------------

def test_scorecard_pace_band_from_bp01():
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_target")) == "PASS"
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_min") - 1) == "REVIEW"
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_fail_below") - 1) == "FAIL"
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_fail_above") + 1) == "FAIL"
    w = [{"w": f"w{i}" + ("." if i % 6 == 5 else ""), "s": i * 0.35, "e": i * 0.35 + 0.3} for i in range(60)]
    shot = {"id": "s1", "type": "A", "start": 0.0, "end": 21.0, "transition": "cut", "emotion": "tension", "beat": "hook", "phase": "d",
            "sentences": [0], "motion": {"kind": "static", "z0": 1.0, "z1": 1.0}, "picture": "p", "palette": [], "face": "none",
            "stakes": "x y z w v u t"}
    row = scorecard.score([shot], w, "Is it? yes.", {"cast": [], "style_suffix": ""})[0]
    assert f"{SR.T('BP-01', 'wpm_min')}-{SR.T('BP-01', 'wpm_max')}" in row["evidence"][0] and "BP-01" in row["evidence"][0]


def test_speed_rates_and_ceiling_from_bp02(tmp_path):
    assert speed.RATES == tuple(SR.T("BP-02", "rates")) and speed.MAX_RATE == SR.T("BP-02", "max_tempo")
    with pytest.raises(ValueError, match="BP-02"):
        speed.retime(tmp_path / "in.mp4", tmp_path / "out.mp4", SR.T("BP-02", "max_tempo") + 0.1)


def test_shorts_tempo_hook_timing_captions_and_safe_zone():
    assert SH.MAX_TEMPO == SR.T("BP-02", "max_tempo") and SH.DEFAULT_TEMPO == SR.T("BP-02", "rates")[0]
    assert SH.audio_chain(SH.DEFAULT_TEMPO).startswith("silenceremove=") and f"atempo={SH.DEFAULT_TEMPO}" in SH.audio_chain(SH.DEFAULT_TEMPO)
    assert "atempo" not in SH.audio_chain(1.0)
    late = [{"w": "Could", "s": SR.T("BP-11", "first_word_by_s") + 0.4, "e": 2.0}, {"w": "they?", "s": 2.1, "e": 2.4}]
    assert SH.hook_timing(late)["severity"] == "FAIL" and "BP-11" in SH.hook_timing(late)["detail"]
    early = [{"w": "Could", "s": 0.3, "e": 0.6}, {"w": "they?", "s": 0.7, "e": 1.0}]
    assert SH.hook_timing(early)["severity"] == "PASS"
    words = [{"w": f"w{i}", "s": i * 0.1, "e": i * 0.1 + 0.08} for i in range(12)]  # 3-word blocks every 0.3 s: too fast
    rep = SH.caption_report(words)
    assert rep["severity"] == "REVIEW" and rep["blocks"] == 4 and rep["words_per_block_max"] <= SR.T("BP-13", "block_words_max")
    assert "BP-13" in rep["detail"]
    zone = SH.safe_zone_report()
    assert zone["safe_y_px"] == SR.T("BP-29", "safe_y_px") and zone["severity"] == "REVIEW" and "BP-29" in zone["detail"]
