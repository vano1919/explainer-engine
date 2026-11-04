# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/llm/cite_check.py`
# Target Module : explainer_engine/llm/cite_check.py
# Target Classes/Symbols : def _norm(), def _listed(), def check(), def strip(), def main()
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

"""J3/J6 citation check (OR-24, invariant 5): a rule may cite only a URL that the same response's web_search_tool_result blocks returned.

    python -m explainer_engine.llm.cite_check ANSWER.md ANSWER.sources.json   # prints the unlisted URLs, exit 1 when there are any

Limits: only http(s) URLs are seen; the Batch path (20+ requests) writes no sources, so a batch job cannot be checked.

``check`` returns (cited, unlisted); ``strip`` removes every bullet or table row that carries an unlisted URL (the rule is dropped,
never repaired from memory).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

URL = re.compile(r"https?://[^\s)\]>\"'|]+")


def _norm(u: str) -> str:
    return u.rstrip(".,;:*").rstrip("/")


def _listed(u: str, known: set[str]) -> bool:
    """Exact only, plus the one real case: URL's own closing ``)`` (a Wikipedia title) which the URL pattern stops at."""
    return u in known or u + ")" in known


def check(text: str, sources: list[str]) -> tuple[list[str], list[str]]:
    known = {_norm(s) for s in sources}
    cited = sorted({_norm(u) for u in URL.findall(text)})
    return cited, [u for u in cited if not _listed(u, known)]


def strip(text: str, sources: list[str]) -> tuple[str, int]:
    """Drop the lines that cite an unlisted URL; returns the kept text and the number of dropped lines."""
    known = {_norm(s) for s in sources}
    kept, dropped = [], 0
    for line in text.splitlines():
        if any(not _listed(_norm(u), known) for u in URL.findall(line)):
            dropped += 1
        else:
            kept.append(line)
    return "\n".join(kept) + "\n", dropped


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    text = Path(a[0]).read_text(encoding="utf-8")
    cited, bad = check(text, json.loads(Path(a[1]).read_text(encoding="utf-8")))
    print(json.dumps({"cited": len(cited), "unlisted": bad}, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
