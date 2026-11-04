# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/providers/fal.py`
# Target Module : explainer_engine/imagegen/providers/fal.py
# Target Classes/Symbols : def _mp(), class Fal (methods: __init__, _headers, _request)
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

"""fal.ai queue API: Seedream 4.5 (text-to-image, and the edit endpoint with up to 10 input pictures) and Qwen-Image-Edit-2511
(an editor, 1-3 inputs). stdlib only.

Read 2026-10-22 from fal.ai/docs/model-apis/model-endpoints/queue and the two model pages: ``POST https://queue.fal.run/
<endpoint_id>`` with ``Authorization: Key <FAL_KEY>``; the answer carries ``request_id``, ``status_url``, ``response_url``
(use THESE: a hand-built URL with the full endpoint path answers 405); poll ``status_url`` until ``COMPLETED`` (IN_QUEUE,
IN_PROGRESS before it), then GET ``response_url`` -> ``images[].url`` (+ ``seed`` on Qwen). Inputs: ``prompt``,
``image_urls`` (public URLs or base64 data URIs), ``image_size`` (an enum or {width, height}), ``num_images``, ``seed``,
``enable_safety_checker``, ``output_format`` (Qwen), ``sync_mode``. Seedream custom sizes must be 1920-4096 a side.
Prices (fal pages, 2026-10-22): Seedream 4.5 $0.04 per picture; Qwen-Image-Edit-2511 $0.03 per megapixel (a 1920x1080
picture is 2.07 MP = $0.062; a 1024x1024 one $0.031). Licences: Seedream "commercial use via fal partner agreement" (BytePlus
terms unread); Qwen-Image-Edit-2511 Apache-2.0.
"""
from __future__ import annotations

import time

from explainer_engine.imagegen.providers.base import ImageProvider, ProviderError, data_uri

QUEUE = "https://queue.fal.run"
ENDPOINTS = {"seedream-4.5": "fal-ai/bytedance/seedream/v4.5/edit", "seedream-4.5-t2i": "fal-ai/bytedance/seedream/v4.5/text-to-image",
             "qwen-image-edit-2511": "fal-ai/qwen-image-edit-2511"}
SIZES = {"1K": (1024, 1024), "1K_wide": (1344, 768), "2K": (2048, 2048), "2K_wide": (2560, 1440), "4K_wide": (3840, 2160)}
QWEN_USD_PER_MP = 0.03


def _mp(size: str) -> float:
    w, h = SIZES[size]
    return w * h / 1e6


# TODO [CLAUDE-CLASS-SYNC: Fal] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `Fal` (methods: __init__, _headers, _request) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class Fal(ImageProvider):
    name = "fal"
    service = "fal_usd"
    key_env = "FAL_KEY"
    PRICES_CHECKED = "2026-10-22"
    PRICES = {"seedream-4.5": {"2K_wide": 0.04, "2K": 0.04, "4K_wide": 0.04},
              "seedream-4.5-t2i": {"2K_wide": 0.04, "2K": 0.04, "4K_wide": 0.04},  # fal/pricing lists Seedream 4.5 at $0.04 a picture; the t2i page shows no price of its own
              "qwen-image-edit-2511": {s: round(_mp(s) * QWEN_USD_PER_MP, 4) for s in SIZES}}
    MAX_REFS = {"seedream-4.5": 10, "seedream-4.5-t2i": 0, "qwen-image-edit-2511": 3}
    VERSIONS = {"seedream-4.5": "bytedance/seedream/v4.5/edit", "seedream-4.5-t2i": "bytedance/seedream/v4.5/text-to-image",
                "qwen-image-edit-2511": "fal-ai/qwen-image-edit-2511"}

    def __init__(self, root, *, poll_s: float = 2.0, max_wait_s: float = 600.0, sleep=time.sleep, **kw):
        super().__init__(root, **kw)
        self.poll_s, self.max_wait_s, self.sleep = poll_s, max_wait_s, sleep

    def _headers(self):
        return {"Authorization": f"Key {self.key()}"}

    def _request(self, prompt, *, model, size, refs, seed, extra):
        if model != "seedream-4.5-t2i" and not refs:
            raise ProviderError(f"fal: {model} is an edit endpoint and needs at least one input picture")
        w, h = SIZES[size]
        body = {"prompt": prompt, "image_size": {"width": w, "height": h}, "num_images": 1, "enable_safety_checker": True}
        if refs:
            body["image_urls"] = [data_uri(r) for r in refs]
        if seed is not None:
            body["seed"] = int(seed)
        if model == "qwen-image-edit-2511":
            body["output_format"] = "png"
            if extra.get("negative_prompt"):
                body["negative_prompt"] = extra["negative_prompt"]
        first = self._json("POST", f"{QUEUE}/{ENDPOINTS[model]}", body, headers=self._headers(), ok=(200, 201, 202))
        status_url, result_url = first.get("status_url"), first.get("response_url")
        if not (status_url and result_url):
            raise ProviderError(f"fal: no status_url/response_url in the answer: {str(first)[:200]}")
        meta = {"request_id": first.get("request_id"), "seed": seed}
        waited = 0.0
        while True:
            state = self._json("GET", status_url, None, headers=self._headers())
            status = state.get("status")
            if status == "COMPLETED":
                if state.get("error"):
                    raise ProviderError(f"fal: request {meta['request_id']} failed: {str(state.get('error'))[:200]}")
                break
            if status not in ("IN_QUEUE", "IN_PROGRESS"):
                raise ProviderError(f"fal: request {meta['request_id']} in unknown state {status!r}")
            if waited >= self.max_wait_s:
                raise ProviderError(f"fal: request {meta['request_id']} still {status} after {waited:.0f} s")
            self.sleep(self.poll_s)
            waited += self.poll_s
        res = self._json("GET", result_url, None, headers=self._headers())
        images = res.get("images") or []
        if not images or not images[0].get("url"):
            raise ProviderError(f"fal: no picture in the result (keys: {sorted(res)})")
        if res.get("seed") is not None:
            meta["seed"] = res["seed"]
        if res.get("has_nsfw_concepts"):
            meta["nsfw_flags"] = res["has_nsfw_concepts"]
        return self._download(images[0]["url"]), meta
