# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/caption_review.py`
# Target Module : explainer_engine/training/pods/caption_review.py
# Target Classes/Symbols : def trim(), def clean(), def review()
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

"""LT-74 caption review, the automatic half (D-80, OR-21): runs on the pod's captions.jsonl before Claude reads them.

* a description cut off by the token limit is trimmed to its last full sentence;
* a character name the VL model let through becomes a plain role ("the old scientist"), studio names go;
* style words (cartoon, animated, drawn ...) go: the trigger carries the look (LT-13);
* a change line gets its "Change from the previous shot:" prefix back when the model wrote its own label;
* what stays broken (too short or too long, no change line) is kept with ``drop: true`` and a reason, never deleted.
Every row keeps its ``raw`` text, so the eye review and the morning report can see each edit.

    python -m explainer_engine.training.pods.caption_review <captions.jsonl> <captions_reviewed.jsonl> <report.json>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PREFIX = "Change from the previous shot:"
ROLES = [(r"\b(Rick Sanchez|Rick)\b", "the old scientist"), (r"\b(Morty Smith|Morty)\b", "the boy"),
         (r"\bSummer\b", "the teenage girl"), (r"\bBeth\b", "the woman"), (r"\bJerry\b", "the man"),
         (r"\b(Mr\.? )?Meeseeks\b", "the blue creature"), (r"\b(Sanchez|Smith)\b", ""), (r"\b(Adult Swim|Cartoon Network)\b", "")]
STYLE = re.compile(r"\b(cartoon|animated|animation|anime|illustration|illustrated|hand-drawn|drawn|2D|cel[- ]shaded)\b ?",
                   re.I)
WORDS = (30, 130)  # a description outside this after trimming is dropped (the prompt asked 50-90)


def trim(text):
    """The text up to its last full sentence when the model stopped mid-sentence; a one-sentence line (a change line)
    keeps its words and gets its full stop."""
    t = text.strip()
    if re.search(r"[.!?][\"')’]?$", t):
        return t
    cut = max(t.rfind(". "), t.rfind("! "), t.rfind("? "))
    return t[:cut + 1] if cut > 0 else t.rstrip(",;: ") + "."


def clean(row):
    """The reviewed row: text edited, ``raw`` kept, ``drop`` + ``review`` reasons."""
    t = row["text"]
    for pat, role in ROLES:
        t = re.sub(pat, role, t)
    t = STYLE.sub("", t)
    t = re.sub(r"\s{2,}", " ", trim(t)).strip()
    t = re.sub(r"\s+([,.])", r"\1", t)
    t = re.sub(r"(^|[.!?] )the ", lambda m: m.group(1) + "The ", t)
    why = []
    if row["kind"] == "change":
        if not t.startswith(PREFIX):
            head, _, rest = t.partition(":")
            t = f"{PREFIX} {rest.strip()}" if rest and len(head.split()) <= 6 else t
            why.append("prefix")
        if not t.startswith(PREFIX) or len(t.split()) < 7:
            why.append("no change line")
    else:
        n = len(t.split())
        if not WORDS[0] <= n <= WORDS[1]:
            why.append(f"words {n}")
    return {**row, "text": t, "raw": row["text"], "drop": any(w != "prefix" for w in why), "review": why}


def review(src, dst, report):
    rows = {}
    for line in Path(src).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r  # a resumed pod may write an id twice: the last one wins
    out = [clean(r) for r in rows.values()]
    Path(dst).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    words = [len(r["text"].split()) for r in out if r["kind"] == "describe" and not r["drop"]]
    rep = {"rows": len(out), "edited": sum(r["text"] != r["raw"] for r in out), "dropped": sum(r["drop"] for r in out),
           "kinds": dict(Counter(r["kind"] for r in out)), "reasons": dict(Counter(w for r in out for w in r["review"])),
           "describe_words": [min(words), sum(words) // len(words), max(words)] if words else None}
    Path(report).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    print(json.dumps(review(*sys.argv[1:4]), indent=1))
