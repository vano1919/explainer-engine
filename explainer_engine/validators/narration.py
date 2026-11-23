"""Narration validators (final plan S3, W2). Input: the production script's audio lines / segments.

Words per line (BP-06), the hook inside BP-11's seconds, the twist sentence's estimated length (BP-115, ``scripting/syllables``),
and the critic rows CRAFT-SCR-02 / CRAFT-SCR-06 (field presence, REVIEW).
"""
from __future__ import annotations

import re

from explainer_engine.qa import gates as G
from explainer_engine.scripting import register_lint
from explainer_engine.scripting import syllables
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-SCR-02", "CRAFT-SCR-03", "CRAFT-SCR-06", "VAL-NAR-01", "VAL-NAR-02")
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")


def _words(text: str) -> int:
    return len(_WORD.findall(text))


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def words_per_line(lines: list[dict]) -> list[dict]:
    """VAL-NAR-01 (BP-06): no sentence of a narrator line over max_words (REVIEW) or hard_max_words (BLOCK when BP-06 allows it)."""
    mx, hard = C.T("BP-06", "max_words"), C.T("BP-06", "hard_max_words")
    if mx is None or hard is None:
        return [C.missing_threshold("VAL-NAR-01", "BP-06", "max_words/hard_max_words")]
    rows = []
    for ln in lines:
        if ln.get("speaker_type", "narrator") != "narrator":
            continue
        n = max((_words(s) for s in _sentences(ln.get("text", ""))), default=0)
        gate = f"VAL-NAR-01:{ln.get('line_id', '?')}"
        if n > hard:
            rows.append(G.row(gate, False, f"{n} words in one sentence; over {hard} (BP-06): split it", n, level=C.level("BP-06")))
        else:
            rows.append(G.row(gate, n <= mx, f"{n} words in the longest sentence (BP-06: at most {mx})", n, level=G.REVIEW))
    return rows or [G.row("VAL-NAR-01", None, "NOT_RUN: no narrator line")]


def hook_seconds(lines: list[dict]) -> dict:
    """VAL-NAR-02 (BP-11): the first narrator sentence is read, by the syllable estimator, inside hook_done_by_s."""
    limit = C.T("BP-11", "hook_done_by_s")
    if limit is None:
        return C.missing_threshold("VAL-NAR-02", "BP-11", "hook_done_by_s")
    first = next((ln for ln in lines if ln.get("speaker_type", "narrator") == "narrator" and ln.get("text", "").strip()), None)
    if first is None:
        return G.row("VAL-NAR-02", None, "NOT_RUN: no narrator line, so no hook to time")
    sentence = _sentences(first["text"])[0]
    s = syllables.seconds(sentence)
    # BP-11 is a Shorts rule (binding); the plan borrows its 3 s for the long video's hook, so a miss here is REVIEW, never BLOCK
    return G.row("VAL-NAR-02", s <= limit, f"the hook ({_words(sentence)} words) is estimated at {s:.2f} s; limit {limit} s (BP-11's number)",
                 s, level=G.REVIEW)


def twist_sentence(segments: list[dict]) -> list[dict]:
    """CRAFT-SCR-03 (code, BP-115): each segment's ``twist`` sentence (or the segment's ``twist_sentence``) lands inside twist_max_s
    by the syllable estimator. A segment that names no twist is NOT_RUN, not a pass."""
    limit = C.T("BP-115", "twist_max_s")
    if limit is None:
        return [C.missing_threshold("CRAFT-SCR-03", "BP-115", "twist_max_s")]
    rows = []
    for seg in segments:
        t = seg.get("twist_sentence") or seg.get("twist")
        gate = f"CRAFT-SCR-03:{seg.get('segment_id', '?')}"
        if not t:
            rows.append(G.row(gate, None, "NOT_RUN: the segment names no twist sentence"))
            continue
        s = syllables.seconds(t)
        rows.append(C.check(gate, s <= limit, "BP-115", f"twist estimated at {s:.2f} s; at most {limit} s", s))
    return rows or [G.row("CRAFT-SCR-03", None, "NOT_RUN: no segment")]


def ai_tells(text: str) -> dict:
    """CRAFT-SCR-02 (critic): the structural AI tells (stacked triplets, 'not just X but Y', em-dash chains) are counted by
    ``register_lint.densities``; a person judges them."""
    d = register_lint.densities(text)
    return C.critic("CRAFT-SCR-02", "BP-114", [] if text.strip() else ["narration text"],
                    "no structural AI tells (triplets, sentence-initial 'Imagine', question opener in every segment, em-dash chains)",
                    d)


def no_double_exposition(lines: list[dict], shots: list[dict]) -> dict:
    """CRAFT-SCR-06 (critic): every narrator line sits in a shot that has a picture description to compare it with."""
    by_line = {lid: s for s in shots for lid in s.get("audio_line_ids") or []}
    miss = []
    for ln in lines:
        s = by_line.get(ln.get("line_id"))
        prompt = ((s or {}).get("image_prompt") or {}).get("start_frame_prompt") if s else None
        if ln.get("speaker_type", "narrator") == "narrator" and not (prompt or (s or {}).get("narrative_information")):
            miss.append(ln.get("line_id", "?"))
    return C.critic("CRAFT-SCR-06", "KP-20", [f"shot card for line {i}" for i in miss[:10]],
                    "the narration never describes what the picture already shows")


def validate(script: dict) -> list[dict]:
    lines, shots = script.get("audio_lines") or [], script.get("shots") or []
    text = " ".join(l.get("text", "") for l in lines if l.get("speaker_type", "narrator") == "narrator")
    return [*words_per_line(lines), hook_seconds(lines), *twist_sentence(script.get("segments") or []), ai_tells(text),
            no_double_exposition(lines, shots)]
