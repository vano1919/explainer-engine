# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/llm/token_stats.py`
# Target Module : explainer_engine/llm/token_stats.py
# Target Classes/Symbols : def load(), def measured(), def suggest(), def main()
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

"""Measured output sizes of real API calls, so max_tokens is a number we measured and not a guess (creator 2026-11-01).

    python -m explainer_engine.llm.token_stats                 # table per (model, effort, job/request)
    python -m explainer_engine.llm.token_stats suggest fable high 20000   # a max_tokens for an expected answer size

``usage.output`` of a ledger line counts thinking AND answer tokens, so it is the number that fills max_tokens.
A call that stopped on ``max_tokens`` is a lower bound only (the real need was higher).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[2] / "jobs" / "llm_ledger" / "calls.jsonl"
HEADROOM = 1.5                  # house: measured maximum x 1.5 (a call that hit the cap counts x 2 as a lower bound)
FLOOR = {"low": 8000, "medium": 16000, "high": 32000, "xhigh": 64000, "max": 64000}


def load(path: Path = LEDGER) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def measured(rows: list[dict]) -> dict[tuple, dict]:
    """(model, effort, job, request id) -> {calls, max_out, capped}; one entry per request id, tool turns folded in."""
    start = {r["uid"]: r for r in rows if r.get("ev") == "start"}
    out: dict[tuple, dict] = collections.defaultdict(lambda: {"calls": 0, "max_out": 0, "capped": 0})
    for r in rows:
        if r.get("ev") != "done" or "usage" not in r:
            continue
        s = start.get(r["uid"], {})
        key = (str(r.get("model", s.get("model", "?"))), r.get("effort"), s.get("job"), s.get("id"))
        e = out[key]
        e["calls"] += 1
        e["max_out"] = max(e["max_out"], r["usage"].get("output", 0))
        e["capped"] += r.get("stop") == "max_tokens"
    return dict(out)


def suggest(effort: str, expected_answer: int, rows: list[dict] | None = None, model: str | None = None) -> int:
    """max_tokens for one turn: the floor of the effort, or the largest measured need of that effort x HEADROOM,
    or the expected answer x 3 (thinking is about twice the answer at high), whichever is largest. Never below the answer."""
    best = 0
    for (m, eff, _job, _id), e in measured(rows if rows is not None else load()).items():
        if eff == effort and (model is None or model in m):
            best = max(best, int(e["max_out"] * (2.0 if e["capped"] else HEADROOM)))
    return max(FLOOR.get(effort, 32000), best, expected_answer * 3)


def main(argv: list[str]) -> int:
    if argv[:1] == ["suggest"] and len(argv) >= 4:
        print(suggest(argv[2], int(argv[3]), model=argv[1]))
        return 0
    for (m, eff, job, rid), e in sorted(measured(load()).items(), key=lambda kv: -kv[1]["max_out"]):
        print(f"{m:18} {str(eff):6} {str(job):18} {str(rid)[:22]:22} max_out={e['max_out']:6} calls={e['calls']} capped={e['capped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
