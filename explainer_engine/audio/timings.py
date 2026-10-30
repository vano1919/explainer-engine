"""RETIRED by D-39 (2026-10-16, ElevenLabs is the narrator):
Kokoro code kept for provenance (docs/PROVENANCE.md) and for audio/timings consumers; never a production read.

When every written word and every phoneme is spoken, from Kokoro's own phoneme timings (a clip's
``<job>.timings.json``: ``[[phoneme, start, end], ...]`` in seconds). stdlib only.

The phonemizer does not keep word counts ("AWS" is one phoneme word, "S3" two, "2.5" three), so words are matched
sentence by sentence (sentence marks are anchors when both sides have the same number), one to one when a sentence
has as many phoneme words as written words, else by expected length snapped to the nearest phoneme-word boundary.
A clip without timings is shared out by length (``estimate``); callers mark such words ``estimated``.
This is a heuristic, not forced alignment.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/timings.py
# changed: kept phoneme_words/align/estimate/readers; build_words/write_words (TMR program layout) removed,
# the explainer timeline builds its own words file (Phase 5)

from __future__ import annotations

import json
import re
import wave
from pathlib import Path

SENTENCE_MARKS = ".?!"
_MARKS = ".?!,;:—…\"“”()"
_WORD_END = re.compile(r"[.?!][\"'”’)\]]*$")


def read_timings(path: Path) -> list[list] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, list) and data else None


def wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return None


def phoneme_words(timings: list[list]) -> list[dict]:
    """[{start, end, n, phones, sentence_end}] per phoneme word (split at spaces; marks close a word)."""
    words: list[dict] = []
    cur: list[list] = []

    def close(mark: str | None = None) -> None:
        nonlocal cur
        if cur:
            words.append({"start": cur[0][1], "end": cur[-1][2], "n": len(cur), "phones": cur, "sentence_end": False})
            cur = []
        if mark and words and mark in SENTENCE_MARKS:
            words[-1]["sentence_end"] = True

    for ph, s, e in timings:
        if ph == " ":
            close()
        elif ph in _MARKS:
            close(ph)
        else:
            cur.append([ph, float(s), float(e)])
    close()
    return words


def expected_phonemes(word: str) -> float:
    """A rough phoneme count for a written word (only ratios matter)."""
    core = re.sub(r"[^\w.%]", "", word).strip(".")
    if not core:
        return 1.0
    n = 0.0
    for ch in core:
        if ch.isdigit():
            n += 3.0
        elif ch == ".":
            n += 4.0  # "point"
        elif ch == "%":
            n += 7.0
    letters = [c for c in core if c.isalpha()]
    if len(letters) >= 2 and all(c.isupper() for c in letters):
        n += 2.5 * len(letters)  # an acronym is spelled out
    else:
        n += 0.85 * len(letters)
    return max(1.0, n)


def _sentences(items: list, is_end) -> list[list]:
    out, cur = [], []
    for item in items:
        cur.append(item)
        if is_end(item):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _time_at(pwords: list[dict], pos: float) -> float:
    """The time at phoneme position ``pos`` (0..sum n) inside a run of phoneme words."""
    acc = 0.0
    for w in pwords:
        if pos < acc + w["n"]:  # a boundary belongs to the next word: its start, not the gap before it
            k = min(w["n"] - 1, max(0, int(pos - acc)))
            ph = w["phones"][k]
            frac = min(1.0, max(0.0, pos - acc - k))
            return ph[1] + (ph[2] - ph[1]) * frac
        acc += w["n"]
    return pwords[-1]["end"]


def _match(texts: list[str], pwords: list[dict]) -> list[tuple[float, float]]:
    """(start, end) per written word of one sentence."""
    if not pwords:
        return []
    if len(texts) == len(pwords):
        return [(w["start"], w["end"]) for w in pwords]
    weights = [expected_phonemes(t) for t in texts]
    total_w = sum(weights)
    total_n = sum(w["n"] for w in pwords)
    bounds = [0]
    for w in pwords:
        bounds.append(bounds[-1] + w["n"])
    starts, acc = [], 0.0
    for t, wt in zip(texts, weights):
        pos = acc / total_w * total_n
        near = min(bounds[:-1], key=lambda b: abs(b - pos))
        if abs(near - pos) <= 0.5 * wt / total_w * total_n and (not starts or near > starts[-1]):
            pos = float(near)
        starts.append(pos)
        acc += wt
    times = [_time_at(pwords, p) for p in starts]
    out = []
    for i, a in enumerate(times):
        b = times[i + 1] if i + 1 < len(times) else pwords[-1]["end"]
        out.append((a, max(a, b)))
    return out


def align(text: str, timings: list[list]) -> list[dict]:
    """[{w, s, e}] for every written word of ``text`` (clip-relative seconds)."""
    texts = text.split()
    pwords = phoneme_words(timings)
    if not texts or not pwords:
        return []
    t_sent = _sentences(texts, lambda t: bool(_WORD_END.search(t)))
    p_sent = _sentences(pwords, lambda w: w["sentence_end"])
    pairs = list(zip(t_sent, p_sent)) if len(t_sent) == len(p_sent) else [(texts, pwords)]
    out = []
    for ts, ps in pairs:
        for t, (a, b) in zip(ts, _match(ts, ps)):
            out.append({"w": t, "s": round(a, 3), "e": round(b, 3)})
    return out


def estimate(text: str, seconds: float) -> list[dict]:
    """Words shared out by length over ``seconds`` (a clip without timings)."""
    texts = text.split()
    weights = [len(t) + 0.4 for t in texts]
    total = sum(weights) or 1.0
    out, a = [], 0.0
    for t, w in zip(texts, weights):
        b = a + seconds * w / total
        out.append({"w": t, "s": round(a, 3), "e": round(b, 3)})
        a = b
    return out
