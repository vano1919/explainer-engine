"""Word timings for a narration that is not Kokoro's (ElevenLabs, D-39): a speech-to-text word list with times
(ElevenLabs Scribe: ``{"text", "start", "end"[, "type"]}``) aligned to the script text -> ``words.json``.

    python -m explainer_engine.audio.scribe_words --script narration.txt --transcript scribe.json --out words.json

The written words are kept (with their punctuation, which the cut rules read, UR-12); only the times come from the
transcript. Normalised word sequences are matched with difflib: equal runs take the transcript's times, same-length
replacements map one to one, other spans are shared out by length and every word left without a heard time is
interpolated from its neighbours; those words carry ``"estimated": true``. A lone dash or ellipsis token is attached to
the word before it. Coverage = share of script words with a heard (not estimated) time; below ``MIN_COVERAGE`` the
report says REVIEW. Not forced alignment: the times are the recogniser's word boundaries.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

MIN_COVERAGE = 0.97
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_LONE_MARK = re.compile(r"^[—–\-…\.]+$")
_TAG = re.compile(r"\[[^\]\n]*\]\s*")


def strip_tags(text: str) -> str:
    """The text without ElevenLabs v3/v4 audio tags (``[curious]``, ``[pause]``): tags are directions, not words."""
    return "\n".join(re.sub(r"  +", " ", _TAG.sub("", line)).strip() for line in text.splitlines())


def number_words(n: int) -> list[str]:
    """English words for 0 <= n < 10**9 ("12000" -> twelve thousand)."""
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    for size, name in ((10 ** 6, "million"), (1000, "thousand")):
        if n >= size:
            return number_words(n // size) + [name] + (number_words(n % size) if n % size else [])
    raise ValueError(n)


def norm(token: str) -> list[str]:
    """Comparable form of one token: lower case, no punctuation, digits spelled out (may give several words)."""
    t = token.lower().replace("’", "'")
    digits = t.replace(",", "").rstrip(".?!;:")
    money = digits.startswith("$")  # "$17,500" is read "seventeen thousand five hundred dollars"
    if money:
        digits = digits[1:]
    if re.fullmatch(r"\d+(st|nd|rd|th)?", digits):
        n = int(re.match(r"\d+", digits).group())
        if n < 10 ** 9:
            return number_words(n) + (["dollars"] if money else [])
    out = []
    for part in re.split(r"[-\u2010\u2011]+", t):  # "tech-savviness" is heard as two words
        part = re.sub(r"[^a-z0-9']+", "", part).strip("'")
        if part:
            out.append(_us_spelling(part))
    return out


_UK = ((re.compile(r"our(s|ed|ing|ite|ites|able)?$"), r"or\1"), (re.compile(r"(?<=[a-z]{3})is(e|es|ed|ing|ation)$"), r"iz\1"),
       (re.compile(r"^licence(s|d)?$"), r"license\1"), (re.compile(r"^defence(s)?$"), r"defense\1"))
_OUR_KEEP = {"our", "ours", "four", "fours", "hour", "hours", "pour", "pours", "tour", "tours", "your", "yours", "sour",
             "flour", "dour", "detour", "contour", "devour", "devours", "scour", "amour"}


def _us_spelling(word: str) -> str:
    """One spelling for comparison: the script may be British ("favour", "realises") and the recogniser writes American."""
    if word in _OUR_KEEP or len(word) < 5:
        return word
    for pat, rep in _UK:
        word = pat.sub(rep, word)
    return word


def script_tokens(text: str) -> list[dict]:
    """Written words with their paragraph; a lone dash/ellipsis joins the word before it."""
    out: list[dict] = []
    paras = [p.strip() for p in strip_tags(text).splitlines() if p.strip()]
    for i, p in enumerate(paras):
        for tok in p.split():
            if _LONE_MARK.match(tok) and out and out[-1]["para"] == i:
                out[-1]["w"] += " " + tok
                continue
            out.append({"w": tok, "para": i})
    return out


def transcript_words(data) -> list[dict]:
    """Scribe output (a dict with ``words`` or a list) -> spoken words only, with float times."""
    words = data.get("words", data) if isinstance(data, dict) else data
    out = []
    for w in words:
        if w.get("type", "word") != "word":
            continue
        text = str(w.get("text", w.get("word", ""))).strip()
        if text:
            out.append({"text": text, "start": float(w["start"]), "end": float(w["end"])})
    return out


def align(text: str, heard: list[dict], duration: float | None = None) -> dict:
    """``{"words": [...], "coverage": x, "status": PASS|REVIEW, "unmatched": [...]}`` (times in seconds)."""
    written = script_tokens(text)
    a, a_owner = [], []  # normalised script words -> index of the written token
    for i, w in enumerate(written):
        for n in norm(w["w"]):
            a.append(n)
            a_owner.append(i)
    b, b_owner = [], []
    for j, h in enumerate(heard):
        for n in norm(h["text"]):
            b.append(n)
            b_owner.append(j)
    times: list[list | None] = [None] * len(written)  # [start, end, estimated]

    def give(ai: int, s: float, e: float, est: bool) -> None:
        k = a_owner[ai]
        if times[k] is None:
            times[k] = [s, e, est]
        else:  # a written token spelled as several words ("1,200"): widen it
            times[k][0], times[k][1] = min(times[k][0], s), max(times[k][1], e)
            times[k][2] = times[k][2] or est

    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and a1 - a0 == b1 - b0):
            for k in range(a1 - a0):
                h = heard[b_owner[b0 + k]]
                give(a0 + k, h["start"], h["end"], op != "equal")
        elif op == "replace":
            s, e = heard[b_owner[b0]]["start"], heard[b_owner[b1 - 1]]["end"]
            step = (e - s) / (a1 - a0)
            for k in range(a1 - a0):
                give(a0 + k, s + k * step, s + (k + 1) * step, True)
    # words never heard: between the neighbours' times
    end_of_audio = duration if duration is not None else (heard[-1]["end"] if heard else 0.0)
    i = 0
    while i < len(times):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        s = times[i - 1][1] if i > 0 else 0.0
        e = times[j][0] if j < len(times) else end_of_audio
        step = max(e - s, 0.0) / (j - i)
        for k in range(i, j):
            times[k] = [s + (k - i) * step, s + (k - i + 1) * step, True]
        i = j
    words, unmatched = [], []
    for w, (s, e, est) in zip(written, times):
        item = {"w": w["w"], "s": round(s, 3), "e": round(e, 3), "para": w["para"]}
        if est:
            item["estimated"] = True
            unmatched.append(w["w"])
        words.append(item)
    coverage = 1.0 - len(unmatched) / len(written) if written else 0.0
    return {"words": words, "coverage": round(coverage, 4), "status": "PASS" if coverage >= MIN_COVERAGE else "REVIEW",
            "unmatched": unmatched}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--script", required=True)
    p.add_argument("--transcript", required=True, help="Scribe JSON (words with start/end)")
    p.add_argument("--out", required=True)
    p.add_argument("--duration", type=float, help="audio length in seconds (default: last heard word)")
    p.add_argument("--voice", default="")
    a = p.parse_args(argv)
    heard = transcript_words(json.loads(Path(a.transcript).read_text(encoding="utf-8")))
    res = align(Path(a.script).read_text(encoding="utf-8"), heard, a.duration)
    duration = a.duration if a.duration is not None else (heard[-1]["end"] if heard else 0.0)
    Path(a.out).write_text(json.dumps({
        "source": "ElevenLabs Scribe word times aligned to the script by explainer_engine.audio.scribe_words "
                  f"(coverage {res['coverage']}, {res['status']})",
        "voice": a.voice, "duration": round(duration, 3), "coverage": res["coverage"], "words": res["words"]},
        indent=0), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("coverage", "status", "unmatched")}, indent=1))
    return 0 if res["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
