# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/fill_holds.py`
# Target Module : explainer_engine/production/fill_holds.py
# Target Classes/Symbols : def alt_motion(), def _phrase(), def _move_definition(), def drop_short_shots(), def fill_holds()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Fill dead holds (RHYTHM-3) with re-framed shots of the picture already on screen.

The creator's rule (2026-10-16): something must change on screen often enough, and the fix for a long hold is never a faster
voice. How often is BP-40 (docs/SOURCED_RULES.md, section-aware): inside the hook window a still of at most hook_max_still_s,
in the body at most body_review_still_s. A re-frame is the same picture with a different move (a push in, a pull out, a pan)
cut on the start of a spoken line, so it costs no new picture. The tool times the script on a read (the real ``words.json`` or
the estimated one), finds the first still longer than its section allows (a cut, a bubble, an accent, a data visual, a card
or a visual beat ends a still, ``board.change_times``, so a stretch the beats already fill gets no filler), cuts a re-frame at the legal line start nearest the middle of the gap, and
repeats until none is left. Gaps with no legal cut are returned, never forced.
"""

from __future__ import annotations

import copy

from explainer_engine.edit import board as B
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.standards import sourced_rules as SR

MAX_GAP = B.BODY_REVIEW  # BP-40: the body's limit; inside the hook window B.HOOK_STILL applies (board.still_too_long)
HOOK_GAP = B.HOOK_STILL
MIN_PART = B.MIN_SHOT  # each side of a cut stays at or above the board's shot floor (BP-84)
PULL_FROM = float(SR.T("BP-20", "push_default_max"))  # a re-frame pull starts at the default push cap (BP-20) ...
PULL_TO, PUSH_TO = 1.04, 1.07  # ... and eases out to here; a re-frame push goes from 1.0 to PUSH_TO (inside BP-20)


def alt_motion(prev: dict) -> dict:
    if prev.get("kind") == "push" and prev.get("z1", 1.0) > prev.get("z0", 1.0):
        return {"kind": "pull", "z0": PULL_FROM, "z1": PULL_TO}  # it shrinks: a pull (continuity.chain reads kind)
    return {"kind": "push", "z0": 1.0, "z1": PUSH_TO}


def _phrase(toks: list[dict], t_new: int, lo: int, hi: int) -> str | None:
    for k in range(2, 8):
        words = [toks[i]["w"] for i in range(t_new, min(t_new + k, hi))]
        phrase = " ".join(words)
        if S.find_phrase(toks, phrase, lo, hi) == t_new:
            return phrase
    return None


def _move_definition(doc: dict, gone: dict) -> None:
    """A dropped shot that defined its picture inline hands the definition to the next shot that uses the picture, so the
    later references keep resolving (PV-03; audit 2026-10-19 M3). A picture nobody uses any more simply goes."""
    pic = gone.get("picture") if "at" in gone else gone  # the dropped shot, or its inline picture itself
    if not isinstance(pic, dict):
        return
    for seg in doc["segments"]:
        for sh in seg["shots"]:
            if sh.get("picture") == pic["id"]:
                sh["picture"] = pic
                return


def drop_short_shots(doc: dict, words_doc: dict, min_s: float = B.MIN_SHOT) -> tuple[dict, list[dict]]:
    """Remove shots shorter than the board allows (RHYTHM-2): the shot before it holds on instead (a segment's first shot, which
    must start on the segment's first word, loses the shot after it). ``fill_holds`` then cuts any hold this makes too long."""
    doc = copy.deepcopy(doc)
    dropped = []
    for _ in range(200):
        timed = T.time_script(doc, words_doc)
        shots = timed["shots"]
        bad = next((k for k, s in enumerate(shots) if s["duration"] < (B.MIN_INSERT if s.get("insert") else min_s) - 1e-9), None)
        if bad is None:
            break
        s = shots[bad]
        seg = next(x for x in doc["segments"] if x["id"] == s["segment"])
        first_of_segment = seg["shots"] and seg["shots"][0]["at"] == s["at"]
        victim = bad + 1 if first_of_segment else bad
        if victim >= len(shots):
            break
        v = shots[victim]
        vseg = next(x for x in doc["segments"] if x["id"] == v["segment"])
        if vseg["shots"][0]["at"] == v["at"] and victim != bad:
            break  # would remove another segment's opening picture: leave for a human
        k = next(j for j, x in enumerate(vseg["shots"]) if x["at"] == v["at"])  # only this shot, not every shot with that phrase
        gone = vseg["shots"].pop(k)
        _move_definition(doc, gone)
        dropped.append({"segment": v["segment"], "at": v["at"], "picture": v["picture"], "duration": v["duration"]})
    return doc, dropped


def fill_holds(doc: dict, words_doc: dict, max_gap: float = MAX_GAP, min_part: float = MIN_PART,
               hook_gap: float = HOOK_GAP) -> tuple[dict, list[dict], list[dict]]:
    """(new doc, inserted shots, gaps that could not be filled). ``max_gap`` is the body's limit, ``hook_gap`` the hook
    window's (BP-40)."""
    doc = copy.deepcopy(doc)
    toks = S.tokens(doc)
    spans = S.segment_spans(toks, len(doc["segments"]))
    words = words_doc["words"]
    # a cut may go after any punctuated word (a line end, a full stop inside a line, a comma); the board checks it is legal
    starts = [i for i in range(len(toks)) if i == 0 or (toks[i]["seg"], toks[i]["line"]) != (toks[i - 1]["seg"], toks[i - 1]["line"])
              or toks[i - 1]["w"].rstrip("\"'”’)")[-1:] in ".?!…,;:—"]
    inserted, stuck = [], []
    skip: set[tuple[float, float]] = set()
    for _ in range(400):
        timed = T.time_script(doc, words_doc)
        shots = timed["shots"]
        changes = B.change_times(shots, timed["duration"], timed)
        gap = next(((a, b) for a, b in zip(changes, changes[1:]) if B.still_too_long(a, b, hook_gap, max_gap) and (a, b) not in skip),
                   None)
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
        # a cut never separates a shot from its own speech bubbles: it goes after the last bubble phrase of the shot
        seg_i = toks[prev["token"]]["seg"]
        spec = next((x for x in doc["segments"][seg_i]["shots"] if x["at"] == prev["at"]), {})
        anchors = [S.find_phrase(toks, b[k], prev["token"], spans[seg_i][1]) for b in spec.get("bubbles", []) for k in ("at", "until") if b.get(k)]
        floor = max([x for x in anchors if x is not None], default=-1) + 4
        cands = [c for c in cands if c[1] > floor]
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
            stuck.append({"from": a, "to": b, "why": f"no legal cut leaves {min_part:g} s on each side"})
    return doc, inserted, stuck
