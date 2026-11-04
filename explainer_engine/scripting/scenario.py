# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/scenario.py`
# Target Module : explainer_engine/scripting/scenario.py
# Target Classes/Symbols : def sha256(), def check()
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

"""The approved short scenario comes before the script (PV-45, OR-15; creator 2026-10-19). stdlib only.

The creator reads a short scenario (the story in plain lines, the dialogue marked) and approves it before any production
script is written, so the final story is the one they liked. ``episode.scenario`` records that approval: the scenario file
next to the script, who approved it and when, and the file's sha256, so a scenario edited after the approval is caught.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

LEGACY = "production_script/1"  # written before the rule: a REVIEW, never a FAIL
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(doc: dict, base: Path | None = None) -> list[dict]:
    """``base`` is the episode folder; without it only the record is checked, not the file."""
    sev = "REVIEW" if doc.get("schema") == LEGACY else "FAIL"
    rec = doc["episode"].get("scenario")
    if not rec:
        return [{"rule": "PV-45", "severity": sev, "where": "episode.scenario",
                 "detail": "no approved scenario: send the creator a short scenario first and write the script only after "
                           "they approve it (OR-15); record file, approved_by, approved_at, sha256"}]
    out = []
    missing = [k for k in ("file", "approved_by", "approved_at", "sha256") if not str(rec.get(k, "")).strip()]
    if missing:
        out.append({"rule": "PV-45", "severity": sev, "where": "episode.scenario", "detail": f"empty: {missing}"})
    if rec.get("approved_at") and not DATE.match(rec["approved_at"]):
        out.append({"rule": "PV-45", "severity": sev, "where": "episode.scenario", "detail": "approved_at is YYYY-MM-DD"})
    if base is not None and rec.get("file"):
        path = base / rec["file"]
        if not path.exists():
            out.append({"rule": "PV-45", "severity": sev, "where": rec["file"], "detail": "the approved scenario file is missing"})
        elif rec.get("sha256") and sha256(path) != rec["sha256"]:
            out.append({"rule": "PV-45", "severity": sev, "where": rec["file"],
                        "detail": "the scenario changed after the approval: the creator approves the new version first"})
    return out
