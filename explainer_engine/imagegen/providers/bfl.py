# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/providers/bfl.py`
# Target Module : explainer_engine/imagegen/providers/bfl.py
# Target Classes/Symbols : class BFL (methods: __init__, _request)
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

"""Black Forest Labs API: FLUX 3 Image Klein (and FLUX 3 Image) through the async task endpoint. stdlib only.

Read 2026-10-22 from docs.bfl.ml (flux_3/flux3_image_klein.md, api-reference/utility/generate-an-image-with-flux-3-klein,
api-reference/utility/get-result.md, api_integration/integration_guidelines.md): ``POST https://api.bfl.ai/v1/flux-3-image-klein``
with header ``x-key``; body ``prompt``, ``images`` (1-10 http URLs or base64, the first sets the output size and is the
picture being edited), ``aspect_ratio``, ``resolution`` (768sq, 1k, 1.5k, 2k, 4k), ``seed``, ``output_format`` (jpeg | png),
``safety_tolerance`` 0-7, ``steps`` 1-16; the answer carries ``id``, ``polling_url`` and ``cost`` (credits, 1 credit = $0.01).
Poll ONLY the returned ``polling_url`` until ``status`` is Ready (others: Pending, Reasoning, Generating, Request Moderated,
Content Moderated, No Card Generated, Error, Task not found); the signed picture URL expires after 10 minutes, so it is
downloaded at once. 24 concurrent requests at most; 402 = no credits; 429 = back off.
Prices (docs, 2026-10-22; text-to-image and editing cost the same): Klein 768sq $0.008, 1k $0.009, 1.5k $0.011, 2k $0.014,
4k $0.036; FLUX 3 Image 1k $0.041, 1.5k $0.048, 2k $0.100 (release notes; 4k $0.607 not offered here).
Licence: outputs of the hosted API under BFL's terms; the open weights are the Kommunity License (US$5M revenue ceiling,
derivatives clause ambiguous) and are not what this adapter uses.
"""
from __future__ import annotations

import time

from explainer_engine.imagegen.providers.base import ImageProvider, ProviderError, data_uri

BASE = "https://api.bfl.ai/v1"
ENDPOINTS = {"flux-3-image-klein": "flux-3-image-klein", "flux-3-image": "flux-3-image"}
DONE = ("Ready",)
FAILED = ("Error", "Failed", "Request Moderated", "Content Moderated", "No Card Generated", "Task not found")
CREDIT_USD = 0.01


# TODO [CLAUDE-CLASS-SYNC: BFL] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `BFL` (methods: __init__, _request) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class BFL(ImageProvider):
    name = "bfl"
    service = "bfl_usd"
    key_env = "BFL_API_KEY"
    PRICES_CHECKED = "2026-10-22"
    PRICES = {"flux-3-image-klein": {"768sq": 0.008, "1k": 0.009, "1.5k": 0.011, "2k": 0.014, "4k": 0.036},
              "flux-3-image": {"1k": 0.041, "1.5k": 0.048, "2k": 0.100}}
    MAX_REFS = {"flux-3-image-klein": 10, "flux-3-image": 10}
    VERSIONS = {"flux-3-image-klein": "flux-3-image-klein (released 2026-10-15)", "flux-3-image": "flux-3-image (2026-10-01)"}

    def __init__(self, root, *, poll_s: float = 1.0, max_wait_s: float = 300.0, sleep=time.sleep, **kw):
        super().__init__(root, **kw)
        self.poll_s, self.max_wait_s, self.sleep = poll_s, max_wait_s, sleep

    def _request(self, prompt, *, model, size, refs, seed, extra):
        if self.run is None:  # N-02: the paid call never runs outside a ledger (a cache hit in generate() never gets here)
            raise ProviderError("refused: BFL paid call without a ledger run (D-56)")
        body = {"prompt": prompt, "resolution": size, "output_format": "png", "safety_tolerance": int(extra.get("safety_tolerance", 2))}
        if extra.get("aspect_ratio"):
            body["aspect_ratio"] = extra["aspect_ratio"]
        if refs:
            body["images"] = [data_uri(r) for r in refs]
        if seed is not None:
            body["seed"] = int(seed)
        first = self._json("POST", f"{BASE}/{ENDPOINTS[model]}", body, headers={"x-key": self.key()})
        poll = first.get("polling_url")
        if not poll:
            raise ProviderError(f"bfl: no polling_url in the answer: {str(first)[:200]}")
        meta = {"task_id": first.get("id"), "seed": seed}
        if first.get("cost") is not None:
            meta["usd_settled"] = round(float(first["cost"]) * CREDIT_USD, 4)
        waited = 0.0
        while True:
            state = self._json("GET", poll, None, headers={"x-key": self.key()})
            status = state.get("status")
            if status in DONE:
                break
            if status in FAILED:
                raise ProviderError(f"bfl: task {meta['task_id']} ended as {status}: {str(state.get('details') or '')[:200]}")
            if waited >= self.max_wait_s:
                raise ProviderError(f"bfl: task {meta['task_id']} still {status} after {waited:.0f} s")
            self.sleep(self.poll_s)
            waited += self.poll_s
        if state.get("cost") is not None:
            meta["usd_settled"] = round(float(state["cost"]) * CREDIT_USD, 4)
        result = state.get("result") or {}
        url = result.get("sample") if isinstance(result, dict) else None
        if isinstance(result, dict) and result.get("seed") is not None:
            meta["seed"] = result["seed"]
        if not url:
            raise ProviderError(f"bfl: Ready without a picture URL (result keys: {sorted(result) if isinstance(result, dict) else type(result).__name__})")
        return self._download(url), meta
