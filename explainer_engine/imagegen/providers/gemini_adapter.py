# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/providers/gemini_adapter.py`
# Target Module : explainer_engine/imagegen/providers/gemini_adapter.py
# Target Classes/Symbols : class Gemini (methods: __init__, estimate, generate)
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

"""The existing Gemini client behind the provider interface, so the pilot and the paint flow see one shape."""
from __future__ import annotations

import time
from pathlib import Path

from explainer_engine.imagegen import gemini as G
from explainer_engine.imagegen.providers.base import AccountError, ImageProvider, ProviderError, Result


# TODO [CLAUDE-CLASS-SYNC: Gemini] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `Gemini` (methods: __init__, estimate, generate) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class Gemini(ImageProvider):
    name = "gemini"
    service = "gemini_usd"
    key_env = "GEMINI_API_KEY"
    PRICES_CHECKED = G.PRICES_CHECKED
    PRICES = G.PRICES
    MAX_REFS = {m: G.MAX_REFERENCES for m in G.PRICES}
    VERSIONS = {m: m for m in G.PRICES}

    def __init__(self, root: Path, *, run=None, cache_dir=None, client=None, **kw):
        super().__init__(root, run=run, cache_dir=cache_dir, **kw)
        self.client = client or G.GeminiClient(self.root, cap_usd=1e9, run=run, cache_dir=self.cache)

    def estimate(self, model, size, count=1, refs=0):
        return round(G.estimate(model, size, count, refs), 4)

    def generate(self, name, prompt, *, model, size, refs=None, seed=None, extra=None) -> Result:
        refs = list(refs or [])
        if seed is not None:
            raise ProviderError("gemini: the API takes no seed")
        t0 = time.time()
        try:
            p = self.client.generate(name, prompt, model=model, size=size, refs=refs, aspect=(extra or {}).get("aspect_ratio", "16:9"))
        except G.ChargeUncertain:
            raise
        except G.GeminiError as exc:
            if any(f"HTTP {c}" in str(exc) for c in (401, 402, 403)):  # depleted prepay or a bad key: every later call fails alike
                raise AccountError(f"gemini: {exc}") from None
            raise ProviderError(f"gemini: {exc}") from None
        data = Path(p).read_bytes()
        cost = self.estimate(model, size, 1, len(refs))
        self.spent = self.client.spent
        return Result(data, model, model, None, cost, None, round(time.time() - t0, 2), meta={"synthid": True})
