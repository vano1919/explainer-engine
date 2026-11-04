# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2 (Research Brief & Counterfactual/Historical Source Dossier Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/research/hypotheses.py`
# Target Module : explainer_engine/research/hypotheses.py
# Target Classes/Symbols : def check()
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

"""Story hypotheses (docs/EPISODE_STANDARDS.md section 8): several different premises, researched fairly, before the treatment.

    python -m explainer_engine.research.hypotheses jobs/<slug>/research/story_hypotheses.json

Evidence and narrative potential are scored separately, and entertainment never compensates for missing evidence: the
selected premise needs an evidence score of at least 3 and supporting claims. Findings are FAIL (fix before the treatment)
or REVIEW (a person answers it). Exit code 1 on any FAIL.
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "story_hypotheses.schema.json"
MIN_HYPOTHESES = 3
MIN_EVIDENCE = 3
SAME_PREMISE = 0.75


def check(doc: dict) -> list[dict]:
    out: list[dict] = []

    def add(rule: str, sev: str, where: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    for err in errors:
        add("HY-0", "FAIL", "/".join(map(str, err.path)) or "(root)", err.message)
    if errors:
        return out
    hyps = {h["id"]: h for h in doc["hypotheses"]}
    if len(hyps) < MIN_HYPOTHESES:
        add("HY-1", "FAIL", "hypotheses", f"{len(hyps)} hypotheses; compare at least {MIN_HYPOTHESES} genuinely different ones")
    items = list(hyps.values())
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if difflib.SequenceMatcher(a=a["premise"].lower(), b=b["premise"].lower()).ratio() >= SAME_PREMISE:
                add("HY-1", "REVIEW", f"{a['id']}/{b['id']}", "two premises are near copies: make them really different")
    for h in items:
        if not h["evidence_for"]:
            add("HY-2", "FAIL" if h["id"] == doc["selected"]["id"] else "REVIEW", h["id"], "no supporting evidence listed")
        if not h["evidence_against"] and not h.get("counterarguments"):
            add("HY-2", "REVIEW", h["id"], "nothing against it was looked for (evidence_against or counterarguments)")
    sel = hyps.get(doc["selected"]["id"])
    if sel is None:
        add("HY-3", "FAIL", "selected", f"{doc['selected']['id']} is not one of the hypotheses")
        return out
    if sel["scores"]["evidence"] < MIN_EVIDENCE:
        add("HY-3", "FAIL", sel["id"], f"evidence score {sel['scores']['evidence']} < {MIN_EVIDENCE}: a good story does not "
            "make up for weak evidence")
    for h in items:
        if h is not sel and h["scores"]["evidence"] > sel["scores"]["evidence"] \
                and h["scores"]["narrative"] > sel["scores"]["narrative"]:
            add("HY-3", "REVIEW", sel["id"], f"{h['id']} scores higher on both evidence and narrative: say why it lost")
    jobs = [b["job"] for b in doc["selected"]["beats"]]
    if jobs[0] not in ("hook", "question"):
        add("HY-4", "REVIEW", "beats", "the beat sheet does not open on a hook or a question")
    if "payoff" not in jobs:
        add("HY-4", "FAIL", "beats", "the beat sheet has no payoff")
    for k, b in enumerate(doc["selected"]["beats"]):
        if b["job"] == "evidence" and not b.get("claims"):
            add("HY-4", "REVIEW", f"beat {k + 1}", "an evidence beat without claim ids")
    return out


if __name__ == "__main__":
    found = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for f in found:
        print(f["severity"], f["rule"], f["where"], "-", f["detail"])
    print(f"{len(found)} finding(s)")
    raise SystemExit(1 if any(f["severity"] == "FAIL" for f in found) else 0)
