"""Fill dead holds (RHYTHM-3) with re-framed shots of the picture already on screen.

The creator's rule (2026-10-16): something must change on screen at least every 9 s, and the fix for a long hold is never a faster
voice. A re-frame is the same picture with a different move (a push in, a pull out, a pan) cut on the start of a spoken line, so
it costs no new picture. The tool times the script on a read (the real ``words.json`` or the estimated one), finds the first gap
longer than ``max_gap``, cuts a re-frame at the legal line start nearest the middle of the gap, and repeats until none is left.
Gaps with no legal cut are returned, never forced.
"""

from __future__ import annotations

import copy

from explainer_engine.edit import board as B
from explainer_engine.production import script as S
from explainer_engine.production import timing as T

MAX_GAP = 8.0   # below the board's 9 s so a read a little slower than measured still passes
MIN_PART = 2.8  # each side of a cut stays above MIN_SHOT


def alt_motion(prev: dict) -> dict:
    if prev.get("kind") == "push" and prev.get("z1", 1.0) > prev.get("z0", 1.0):
        return {"kind": "push", "z0": 1.10, "z1": 1.04}
    return {"kind": "push", "z0": 1.0, "z1": 1.07}


def _phrase(toks: list[dict], t_new: int, lo: int, hi: int) -> str | None:
    for k in range(2, 8):
        words = [toks[i]["w"] for i in range(t_new, min(t_new + k, hi))]
        phrase = " ".join(words)
        if S.find_phrase(toks, phrase, lo, hi) == t_new:
            return phrase
    return None


def fill_holds(doc: dict, words_doc: dict, max_gap: float = MAX_GAP, min_part: float = MIN_PART) -> tuple[dict, list[dict], list[dict]]:
    """(new doc, inserted shots, gaps that could not be filled)."""
    doc = copy.deepcopy(doc)
    toks = S.tokens(doc)
    spans = S.segment_spans(toks, len(doc["segments"]))
    words = words_doc["words"]
    starts = [i for i in range(len(toks)) if i == 0 or (toks[i]["seg"], toks[i]["line"]) != (toks[i - 1]["seg"], toks[i - 1]["line"])]
    inserted, stuck = [], []
    skip: set[tuple[float, float]] = set()
    for _ in range(400):
        timed = T.time_script(doc, words_doc)
        shots = timed["shots"]
        changes = sorted({s["start"] for s in shots} | {b["start"] for s in shots for b in s["bubbles"]} | {timed["duration"]})
        gap = next(((a, b) for a, b in zip(changes, changes[1:]) if b - a > max_gap and (a, b) not in skip), None)
        if gap is None:
            break
        a, b = gap
        mid = (a + b) / 2
        cands = []
        wmap, _ = T.word_map(toks, words)
        for t in starts:
            wi = wmap[t]
            if wi is None:
                continue
            cut, legal = B.cut_before(words, wi)
            if legal and a + min_part <= cut <= b - min_part:
                cands.append((abs(cut - mid), t, cut))
        prev = max((s for s in shots if s["start"] <= a + 1e-6), key=lambda s: s["start"])
        done = False
        for _, t, cut in sorted(cands):
            si = toks[t]["seg"]
            lo, hi = spans[si]
            phrase = _phrase(toks, t, prev["token"] + 1 if toks[prev["token"]]["seg"] == si else lo, hi)
            if not phrase:
                continue
            seg_shots = doc["segments"][si]["shots"]
            first_seq = next(k for k, s in enumerate(shots) if s["segment"] == doc["segments"][si]["id"])
            pos = 0
            while pos < len(seg_shots) and shots[first_seq + pos]["token"] < t:
                pos += 1
            new = {"at": phrase, "type": prev["type"] if not prev.get("insert") else "B", "motion": alt_motion(prev["motion"]),
                   "picture": prev["picture"], "reuse": "reframe"}
            seg_shots.insert(pos, new)
            inserted.append({"segment": doc["segments"][si]["id"], "at": phrase, "picture": prev["picture"], "start": cut})
            done = True
            break
        if not done:
            skip.add(gap)
            stuck.append({"from": a, "to": b, "why": "no legal line start leaves 2.8 s on each side"})
    return doc, inserted, stuck
