"""How each speaking hero talks (PV-46, DW-11; creator 2026-10-19). stdlib only.

Every hero who speaks has ``cast.<id>.speech``: the manner and the vocabulary of their speech. A real person or a known
character talks the way they are generally known to talk (``basis: public``, with the sources that describe it); an invented
hero talks from their personality (``basis: personality``). The words are always our own: the manner is borrowed, never a
quote, a catchphrase of a film or series, or an imitation of an actor's voice (VC-02 stays the rule for voices).
"""

from __future__ import annotations

import re

LEGACY = "production_script/1"
BASES = ("public", "personality")
MIN_WORDS = 3  # signature words or turns of phrase a hero's lines draw on


def speakers(doc: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for seg in doc["segments"]:
        for ln in seg["lines"]:
            if ln.get("speaker"):
                out.setdefault(ln["speaker"], []).append(ln["text"])
    for sh in doc.get("shorts", []):
        for ln in sh.get("lines", []):
            if ln.get("speaker"):
                out.setdefault(ln["speaker"], []).append(ln["text"])
    return out


def check(doc: dict) -> list[dict]:
    sev = "REVIEW" if doc.get("schema") == LEGACY else "FAIL"
    out = []

    def f(where, detail, s=sev):
        out.append({"rule": "PV-46", "severity": s, "where": where, "detail": detail})

    for who, lines in speakers(doc).items():
        sp = doc.get("cast", {}).get(who, {}).get("speech")
        if not sp:
            f(who, f"{who} speaks but has no cast.{who}.speech: write the manner and vocabulary of their speech, from how they "
                   "are generally known to talk or, for an invented hero, from their personality (DW-11)")
            continue
        if sp.get("basis") not in BASES:
            f(who, f"speech.basis is one of {BASES}")
        if len(sp.get("style", "").split()) < 4:
            f(who, "speech.style says in a sentence how they talk (pace, register, sentence length, habits)")
        if len(sp.get("words", [])) < MIN_WORDS:
            f(who, f"speech.words lists at least {MIN_WORDS} words or turns of phrase typical of them")
        if sp.get("basis") == "public" and not sp.get("sources"):
            f(who, "a publicly known manner needs its sources (claim ids or URLs): how they are described, never a film "
                   "or actor portrayal copied")
        text = " ".join(lines).lower()
        for bad in sp.get("avoid", []):
            if re.search(r"\b" + re.escape(bad.lower()) + r"\b", text):
                f(who, f"{who} says {bad!r}, which their speech avoids", "REVIEW")
        # the fields existing is not the manner being used (the 2026-10-19 audit): on /3, a hero none of whose
        # signature words or phrases ever appears in their lines probably talks like everyone else
        words = sp.get("words", [])
        if doc.get("schema") == "production_script/3" and len(lines) >= 3 and words and not any(
                re.search(r"\b" + re.escape(w.lower()) + r"\b", text) for w in words):
            f(who, f"none of {who}'s signature words ({', '.join(words[:4])}...) appears in their {len(lines)} lines: "
                   "the written voice ignores the declared manner (DW-11)", "REVIEW")
    return out
