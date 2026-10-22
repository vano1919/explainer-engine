"""The existing Gemini client behind the provider interface, so the pilot and the paint flow see one shape."""
from __future__ import annotations

import time
from pathlib import Path

from explainer_engine.imagegen import gemini as G
from explainer_engine.imagegen.providers.base import ImageProvider, ProviderError, Result


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
            raise ProviderError(f"gemini: {exc}") from None
        data = Path(p).read_bytes()
        cost = self.estimate(model, size, 1, len(refs))
        self.spent = self.client.spent
        return Result(data, model, model, None, cost, None, round(time.time() - t0, 2), meta={"synthid": True})
