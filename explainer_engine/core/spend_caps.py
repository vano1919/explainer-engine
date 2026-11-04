# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/spend_caps.py`
# Target Module : explainer_engine/core/spend_caps.py
# Target Classes/Symbols : class OverCeiling (methods: ), def load(), def episode_ceiling(), def allowance(), def paid_test(), def casting_credits_max(), def gemini_api(), def runpod(), def check_caps()
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

"""The creator's money ceilings from ``config/spend_caps.json`` (D-56): one file, read by the run ledger and the pod manager.
A run ledger may hold lower caps than the file, never higher; ``$EXPLAINER_SPEND_CAPS`` points at another file (tests)."""

from __future__ import annotations

import json
import os
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "spend_caps.json"


# TODO [CLAUDE-CLASS-SYNC: OverCeiling] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `OverCeiling` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class OverCeiling(ValueError):
    """A cap or a pod asks for more than the creator's ceiling."""


def load() -> dict:
    p = Path(os.environ.get("EXPLAINER_SPEND_CAPS") or PATH)
    return json.loads(p.read_text(encoding="utf-8"))


def episode_ceiling(service: str) -> float | None:
    return load().get("per_episode", {}).get(service)


def allowance(name: str) -> dict:
    """A tool's own spending allowance (``allowances.<name>``: service, per_run): a ceiling inside the run's cap of that
    service, spent without asking first (the QA loop's re-reads, the creator 2026-10-20). Missing = no allowance."""
    a = load().get("allowances", {}).get(name)
    if not isinstance(a, dict) or "service" not in a or "per_run" not in a:
        raise OverCeiling(f"no allowance {name!r} in config/spend_caps.json: spending needs the creator's yes")
    return a


def paid_test(name: str) -> dict[str, float]:
    """One paid test's caps (``paid_tests.<name>``, the ``*_usd`` lines: service -> ceiling). Refuses a test that is not in the
    file and a section whose tests together pass ``total_usd``."""
    tests = load().get("paid_tests", {})
    t = tests.get(name) if not name.startswith("_") else None
    if not isinstance(t, dict):
        raise OverCeiling(f"no paid test {name!r} in config/spend_caps.json: a paid test needs the creator's yes and its line")
    total = sum(float(v) for row in tests.values() if isinstance(row, dict) for k, v in row.items() if k.endswith("_usd"))
    if total > float(tests.get("total_usd", 0)) + 1e-9:
        raise OverCeiling(f"paid tests add up to {total:g} USD, above their total_usd {tests.get('total_usd')} (config/spend_caps.json)")
    return {k: float(v) for k, v in t.items() if k.endswith("_usd")}


def casting_credits_max() -> float:
    """The ElevenLabs credits one casting session may spend (``casting.casting_credits_max``, the creator 2026-10-30)."""
    v = load().get("casting", {}).get("casting_credits_max")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no casting_credits_max in config/spend_caps.json: casting spends nothing without the creator's number")
    return float(v)


def gemini_api() -> dict:
    """The Gemini API line (``gemini_api``: max_usd per calendar month). Missing or not a positive number = refused."""
    g = load().get("gemini_api")
    v = g.get("max_usd") if isinstance(g, dict) else None
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no gemini_api max_usd in config/spend_caps.json: the Gemini API spends nothing without the creator's line")
    return g


def runpod() -> dict:
    return load()["runpod"]


def check_caps(caps: dict) -> dict:
    """Fill a run's missing caps from the file and refuse any cap above it."""
    out = dict(caps)
    for service, ceiling in load().get("per_episode", {}).items():
        if service not in out:
            out[service] = ceiling
        elif out[service] > ceiling + 1e-9:
            raise OverCeiling(f"{service} cap {out[service]} is above the creator's ceiling {ceiling} (config/spend_caps.json)")
    return out
