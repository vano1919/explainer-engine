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
