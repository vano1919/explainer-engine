"""Scribe word times aligned to the script (D-39): words.json keeps the written words and their punctuation."""

from __future__ import annotations

from explainer_engine.audio import scribe_words as S
from explainer_engine.edit import shot_rules

TEXT = "Could they survive... the Stone Age? No tools.\nAnd night — is coming."


def heard(words, gap=0.1, length=0.3):
    out, t = [], 0.2
    for w in words:
        out.append({"text": w, "start": round(t, 3), "end": round(t + length, 3), "type": "word"})
        t += length + gap
    return out


def test_exact_transcript_keeps_written_words_and_times():
    h = heard("Could they survive the Stone Age No tools And night is coming".split())
    res = S.align(TEXT, h)
    assert res["coverage"] == 1.0 and res["status"] == "PASS"
    ws = res["words"]
    assert [w["w"] for w in ws][:3] == ["Could", "they", "survive..."]
    assert ws[0]["s"] == h[0]["start"] and ws[-1]["e"] == h[-1]["end"]
    assert ws[-1]["para"] == 1 and ws[0]["para"] == 0
    assert "night —" in [w["w"] for w in ws]  # the lone dash joins the word before it


def test_ellipsis_and_dash_are_cut_marks():
    h = heard("Could they survive the Stone Age No tools And night is coming".split(), gap=0.3)
    ws = S.align(TEXT, h)["words"]
    marks = [m for _, _, m in shot_rules.pauses_from_words(ws)]
    assert "." in marks and "—" in marks  # "survive..." ends in ".", "night —" in "—"


def test_a_dropped_word_is_interpolated_and_flagged():
    h = heard("Could they survive the Stone Age No tools And night coming".split())  # "is" not heard
    res = S.align(TEXT, h)
    is_word = next(w for w in res["words"] if w["w"] == "is")
    assert is_word.get("estimated") and res["unmatched"] == ["is"]
    night = next(w for w in res["words"] if w["w"] == "night —")
    coming = next(w for w in res["words"] if w["w"] == "coming.")
    assert night["e"] <= is_word["s"] <= is_word["e"] <= coming["s"]
    assert res["status"] == "REVIEW"  # 11 of 12 = 92 % < 97 %


def test_numbers_match_both_ways():
    assert S.number_words(12000) == ["twelve", "thousand"]
    assert S.number_words(1999) == ["one", "thousand", "nine", "hundred", "ninety", "nine"]
    res = S.align("Twelve thousand years ago.", heard(["12,000", "years", "ago."]))
    assert res["coverage"] == 1.0
    res = S.align("About 100 scientists.", heard(["About", "one", "hundred", "scientists"]))
    assert res["coverage"] == 1.0 and res["words"][1]["w"] == "100"


def test_transcript_reader_skips_spacing_and_accepts_a_list():
    data = {"words": [{"text": "Hi", "start": 0, "end": 0.2, "type": "word"},
                      {"text": " ", "start": 0.2, "end": 0.3, "type": "spacing"},
                      {"text": "there", "start": 0.3, "end": 0.6}]}
    assert [w["text"] for w in S.transcript_words(data)] == ["Hi", "there"]
    assert len(S.transcript_words(data["words"])) == 2
