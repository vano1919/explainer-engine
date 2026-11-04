# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/labels.py`
# Target Module : explainer_engine/core/labels.py
# Target Classes/Symbols : def v(), def plain(), def plain_tree()
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

"""Labelled values: every parameter that is a choice (not a fact) carries an evidence label.

A labelled value is ``{"value": ..., "status": <label>, "note": "..."}``. QA reads the labels; reports show them.

Labels:
  sourced              taken from an official or primary source (the note names it and its access date)
  measured             measured by us on our own output or hardware
  engineering_default  a working default with no evidence either way (sample rates, chunk sizes, file names)
  hypothesis           an untested idea about the viewer experience, to be tested
  playback_dependent   depends on the viewer's device and room
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/labels.py
# changed: label vocabulary for the explainer channel (directive: observed/measured/inference/hypothesis)

from __future__ import annotations

LABELS = ("sourced", "measured", "engineering_default", "hypothesis", "playback_dependent")


def v(value, status: str, note: str = "") -> dict:
    """A labelled value."""
    if status not in LABELS:
        raise ValueError(f"unknown evidence label {status!r}")
    return {"value": value, "status": status, "note": note}


def plain(node):
    """The value of a labelled value; anything else unchanged."""
    return node["value"] if isinstance(node, dict) and "value" in node else node


def plain_tree(node):
    """Like ``plain``, through nested blocks: a dict of labelled values becomes a dict of values."""
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    if isinstance(node, dict):
        return {k: plain_tree(x) for k, x in node.items()}
    if isinstance(node, list):
        return [plain_tree(x) for x in node]
    return node
