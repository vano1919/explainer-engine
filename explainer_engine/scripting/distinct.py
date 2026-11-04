# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/distinct.py`
# Target Module : explainer_engine/scripting/distinct.py
# Target Classes/Symbols : def _words(), def similarity(), def check()
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

"""Episode distinctness (PV-38; audit 2026-10-19 Q4). stdlib only.

YouTube's inauthentic-content policy (Help 1311392, opened 2026-10-19) names "videos where characters are put in the same
situation over and over again with the same outcome". A recurring format is allowed; a repeated premise with the same
outcome is not. Each production script states ``episode.distinct`` (premise, question, outcome, mechanism: what is new), and
this check compares it with every approved episode in ``docs/episodes.json``. It only REVIEWs: the creator decides what is
new enough.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "docs" / "episodes.json"
FIELDS = ("premise", "question", "outcome", "mechanism")
SIMILAR = 0.6  # word-sequence similarity of premise + outcome above which two episodes read as the same situation


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def similarity(a: dict, b: dict) -> float:
    def key(e):
        return _words(e.get("premise", "") + " " + e.get("outcome", ""))
    return difflib.SequenceMatcher(a=key(a), b=key(b), autojunk=False).ratio()


def check(doc: dict, registry: Path = REGISTRY) -> list[dict]:
    out = []
    ep = doc["episode"]
    mine = ep.get("distinct")
    if not mine:
        return [{"rule": "PV-38", "severity": "REVIEW", "where": "episode.distinct",
                 "detail": "say the premise, question, outcome and what is new (mechanism), so the series cannot repeat itself"}]
    missing = [f for f in FIELDS if not str(mine.get(f, "")).strip()]
    if missing:
        out.append({"rule": "PV-38", "severity": "REVIEW", "where": "episode.distinct", "detail": f"empty: {missing}"})
    others = json.loads(registry.read_text(encoding="utf-8"))["episodes"] if registry.exists() else []
    for other in others:
        if other["id"] == ep["id"]:
            continue
        r = similarity(mine, other)
        if r >= SIMILAR:
            out.append({"rule": "PV-38", "severity": "REVIEW", "where": other["id"],
                        "detail": f"premise and outcome {r:.0%} like {other['id']}: the same situation with the same outcome "
                                  "is inauthentic content (Help 1311392); change the situation, the outcome or both"})
        elif _words(mine.get("mechanism", "")) and _words(mine.get("mechanism", "")) == _words(other.get("mechanism", "")):
            out.append({"rule": "PV-38", "severity": "REVIEW", "where": other["id"], "detail": "the same mechanism as " + other["id"]})
    return out
