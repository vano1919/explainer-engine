# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2 (Research Brief & Counterfactual/Historical Source Dossier Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/research/fan_brief.py`
# Target Module : explainer_engine/research/fan_brief.py
# Target Classes/Symbols : def _tokens(), def overlap(), def check(), def check_balance(), def template_flags()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this research subsystem module with `production_script/4` (`MASTER_MOLD.md` v2.1.0):
#    - Populate structured cast candidates (`character_id`, `name`, `living: bool`, `historical_era`, primary historical quote sources) so `CastRegistry` and `verify_voice_clearance` (`CD-06`) know deterministically whether a figure is a deceased historical character (`living=False`, eligible for `D-90` voicing) or a living person (`living=True`, banned under `D-62`/`PV-55`).
#    - Tag geographic entities with ISO-A3 country codes for `MapRenderer` (`ne_50m_admin_0_countries.geojson`, `D-96`) and tag tension-zone beat candidates (`cold_open` hook facts, `grounding` citations, `escalation` causal chains, `climax` turning point, `coda` payoff).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this research module outputs v2/v3 research briefs without `living: bool` cast metadata (`CD-06`), ISO-A3 map territory codes (`D-96`), or tension-zone beat classifications (`D-84`).
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Feeds `ScriptGenerator`, `CastRegistry`, and `MapRenderer` with structured, citation-backed inputs so `/4` scripts require zero manual patching.
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

"""Fan research brief and script balance for crossover episodes (creator rule 2026-10-16, P-123..P-125).

A crossover script starts from what the fans of both worlds actually discuss: their theories, what they ask for, the
crossovers that already exist, and each world's canon rules. ``check`` validates a brief (schema + depth + references +
originality of the premise); ``check_balance`` checks that a script's beats serve both a casual viewer and a hardcore
fan; ``template_flags`` lists stock phrases that make a script sound templated (flags for review, never auto-edits).

Run: ``python -m explainer_engine.research.fan_brief <brief.json>`` (exit 1 on any FAIL).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "fan_brief.schema.json"
# P-124 research depth
MIN_SOURCES, MIN_SOURCE_KINDS, MIN_THEORIES, MIN_DEMANDS, MIN_EXISTING, MIN_RULES_PER_WORLD = 6, 3, 5, 3, 3, 2
MIN_ONRAMPS, MIN_DEEP_CUTS = 3, 3
MAX_PREMISE_OVERLAP = 0.6          # P-125
MIN_CASUAL_SHARE, MIN_FAN_SHARE = 0.30, 0.30   # P-123
_STOP = {"the", "a", "an", "of", "in", "and", "vs", "versus", "what", "if", "would", "could", "to", "who", "is",
         "was", "with", "on", "how", "why", "happens", "happen", "when", "met", "meet", "into", "from"}
TEMPLATE_PHRASES = (
    "have you ever wondered", "in today's video", "let's dive in", "buckle up", "but here's the twist",
    "here's the thing", "you won't believe", "mind-blowing", "epic showdown", "ultimate showdown", "who would win",
    "smash that like", "without further ado", "so there you have it", "the answer may surprise you",
    "stay tuned", "let that sink in", "in a world where",
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if t not in _STOP}


def overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def check(brief: dict) -> list[dict]:
    findings: list[dict] = []

    def add(check_id: str, verdict: str, detail: str) -> None:
        findings.append({"check": check_id, "verdict": verdict, "detail": detail})

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(brief), key=lambda e: list(e.path))
    for err in errors:
        add("schema", "FAIL", f"{'/'.join(map(str, err.path)) or '(root)'}: {err.message}")
    if errors:
        return findings

    ids = [s["id"] for s in brief["sources"]]
    if len(set(ids)) != len(ids):
        add("source_ids_unique", "FAIL", "two sources share an id")
    known = set(ids)
    kinds = {s["kind"] for s in brief["sources"]}
    if len(brief["sources"]) < MIN_SOURCES or len(kinds) < MIN_SOURCE_KINDS:
        add("source_depth", "FAIL", f"{len(brief['sources'])} sources of {len(kinds)} kinds; need >= {MIN_SOURCES} "
            f"of >= {MIN_SOURCE_KINDS} kinds")
    for label, items, minimum in (("theories", brief["theories"], MIN_THEORIES),
                                  ("fan_demands", brief["fan_demands"], MIN_DEMANDS),
                                  ("existing_crossovers", brief["existing_crossovers"], MIN_EXISTING),
                                  ("casual_onramps", brief["casual_onramps"], MIN_ONRAMPS),
                                  ("deep_cuts", brief["deep_cuts"], MIN_DEEP_CUTS)):
        if len(items) < minimum:
            add(f"{label}_depth", "FAIL", f"{len(items)} {label}; need >= {minimum}")
    for item in brief["theories"] + brief["fan_demands"] + brief["canon_rules"]:
        for sid in item["source_ids"]:
            if sid not in known:
                add("dangling_source", "FAIL", f"'{item.get('summary') or item.get('rule')}'"[:70] + f" cites unknown {sid}")
    worlds = brief["worlds"]
    for world in worlds:
        n = sum(1 for r in brief["canon_rules"] if r["world"] == world)
        if n < MIN_RULES_PER_WORLD:
            add("canon_rules", "FAIL", f"{world}: {n} canon rules; need >= {MIN_RULES_PER_WORLD}")
    for r in brief["canon_rules"]:
        if r["world"] not in worlds:
            add("canon_world", "FAIL", f"canon rule for unknown world '{r['world']}'")
    premise = brief["our_angle"]["premise"]
    for ex in brief["existing_crossovers"]:
        score = overlap(premise, ex["title"] + " " + ex["angle"])
        if score > MAX_PREMISE_OVERLAP:
            add("premise_originality", "REVIEW", f"premise overlaps {score:.2f} with existing '{ex['title']}'")
    for phrase in template_flags(premise):
        add("premise_template", "REVIEW", f"premise uses a stock phrase: '{phrase}'")
    return findings


def check_balance(beats: list[dict]) -> list[dict]:
    """``beats``: [{"id", "audience": "casual"|"fan"|"both", ...}] from the script. P-123."""
    findings: list[dict] = []
    if not beats:
        return [{"check": "balance", "verdict": "FAIL", "detail": "no tagged beats"}]
    bad = [b.get("id", "?") for b in beats if b.get("audience") not in ("casual", "fan", "both")]
    if bad:
        findings.append({"check": "balance_tags", "verdict": "FAIL", "detail": f"untagged beats: {', '.join(bad)}"})
    n = len(beats)
    casual = sum(1 for b in beats if b.get("audience") in ("casual", "both")) / n
    fan = sum(1 for b in beats if b.get("audience") in ("fan", "both")) / n
    if casual < MIN_CASUAL_SHARE:
        findings.append({"check": "balance_casual", "verdict": "FAIL",
                         "detail": f"only {casual:.0%} of beats help a casual viewer (>= {MIN_CASUAL_SHARE:.0%})"})
    if fan < MIN_FAN_SHARE:
        findings.append({"check": "balance_fan", "verdict": "FAIL",
                         "detail": f"only {fan:.0%} of beats reward a fan (>= {MIN_FAN_SHARE:.0%})"})
    return findings


def template_flags(text: str) -> list[str]:
    low = text.lower()
    return [p for p in TEMPLATE_PHRASES if p in low]


if __name__ == "__main__":
    result = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for f in result:
        print(f["verdict"], f["check"], "-", f["detail"])
    print(f"{len(result)} finding(s)")
    raise SystemExit(1 if any(f["verdict"] == "FAIL" for f in result) else 0)
