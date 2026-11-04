# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/entity_align.py`
# Target Module : explainer_engine/scripting/entity_align.py
# Target Classes/Symbols : def key(), def _edit(), def same(), def heard()
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

"""Names the reader says slightly differently (Blueprint P3): a small phonetic key so the word timings of a read can mark "Nay" as
the heard form of the written "Ney". stdlib only.

It is a reduced in-repo key, not Double Metaphone: no phonetic library is installed and a faithful port is several hundred lines
for one narrow need. The key is used ONLY inside an aligned replace span of equal length (``audio/scribe_words.align(entities=)``),
so a short key such as ``N`` can never match a word the alignment did not already put opposite the name.

    >>> key("Ney"), key("Nay"), key("Subutai"), key("Subotai")
    ('N', 'N', 'SBT', 'SBT')
"""

from __future__ import annotations

import re

VOWELS = "aeiou"
REWRITES = (("ph", "f"), ("ck", "k"), ("dg", "j"), ("q", "k"), ("x", "ks"), ("z", "s"))


def key(word: str) -> str:
    """The reduced phonetic key of one word: letters only; ph/ck/dg/q/x/z and soft c rewritten; a leading kn, gn or wr is n, n or r;
    gh dropped except at the start; the first letter kept, later vowels and any w, y or h after a vowel dropped, repeats collapsed."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    for pat, rep in (("kn", "n"), ("gn", "n"), ("wr", "r")):
        if w.startswith(pat):
            w = rep + w[len(pat):]
    for pat, rep in REWRITES:
        w = w.replace(pat, rep)
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    w = w[0] + w[1:].replace("gh", "")
    out, prev = [w[0]], w[0]
    for ch in w[1:]:
        after_vowel = prev in VOWELS
        prev = ch
        if ch in VOWELS or (ch in "wyh" and after_vowel):
            continue
        if ch != out[-1]:
            out.append(ch)
    return "".join(out).upper()


def _edit(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (ca != cb)))
        row = new
    return row[-1]


def same(a: str, b: str) -> bool:
    """Two spellings of one sound: equal keys, or keys one edit apart when both have at least three letters."""
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return False
    return ka == kb or (min(len(ka), len(kb)) >= 3 and _edit(ka, kb) <= 1)


def heard(text_words: list[str], heard_words: list[str], *, names: set[str] | frozenset = frozenset()) -> list[bool]:
    """For each written word opposite a heard word: the same word, or (when it is one of ``names``) the same sound."""
    low = {n.lower() for n in names}
    return [t.lower() == h.lower() or (t.lower() in low and same(t, h)) for t, h in zip(text_words, heard_words)]
