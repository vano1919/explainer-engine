# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/imagegen.py (GeminiImages, PRICES), reshaped
"""Gemini picture client (D-41): references, a price table, a budget guard, a cache and a spend log. stdlib only.

Gemini is for reusable channel assets and B hero-acting shots by the routing table (VISUAL_WORLD_ARCHITECTURE section 6).
Nothing is sent without ``estimate`` passing the cap; every call is logged to ``spend_log.jsonl``; the key comes from the
``GEMINI_API_KEY`` environment variable and is never printed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PRICES_CHECKED = "2026-10-16"
# USD per output picture (Google's standard-tier list prices, ai.google.dev/gemini-api/docs/pricing, 2026-10-16)
PRICES = {
    "gemini-3-pro-image": {"1K": 0.134, "2K": 0.134, "4K": 0.24},
    "gemini-nano-banana-2.1": {"1K": 0.0336, "2K": 0.0504, "4K": 0.113},
    "gemini-3.1-flash-image": {"0.5K": 0.045, "1K": 0.067, "2K": 0.101, "4K": 0.151},
    "gemini-3.1-flash-lite-image": {"1K": 0.0336},
}
REFERENCE_USD = 0.0011  # one input picture at the Pro rate (the dearest listed)
MAX_REFERENCES = 14


class GeminiError(RuntimeError):
    pass


def price(model: str, size: str) -> float:
    try:
        return PRICES[model][size]
    except KeyError:
        raise GeminiError(f"no list price for {model} at {size}; known: {PRICES}") from None


def estimate(model: str, size: str, count: int, references: int = 0) -> float:
    if references > MAX_REFERENCES:
        raise GeminiError(f"at most {MAX_REFERENCES} reference pictures per request")
    return round(count * (price(model, size) + references * REFERENCE_USD), 4)


def cache_key(prompt: str, model: str, size: str, aspect: str, refs: list[bytes]) -> str:
    h = hashlib.sha256(json.dumps([prompt, model, size, aspect]).encode())
    for r in refs:
        h.update(hashlib.sha256(r).digest())
    return h.hexdigest()[:24]


class GeminiClient:
    def __init__(self, root: Path, *, key: str | None = None, cap_usd: float, post=None, timeout: float = 180.0,
                 retries: int = 3, run=None):
        self.run = run  # core.ledger.Run: charges are reserved there before the call (OR-02)
        self.root = Path(root)
        self.key = key or os.environ.get("GEMINI_API_KEY", "")
        self.cap = cap_usd
        self.post = post or self._http
        self.timeout, self.retries = timeout, retries
        self.spent = 0.0
        self.root.mkdir(parents=True, exist_ok=True)

    def _http(self, model: str, body: dict) -> dict:
        if not self.key:
            raise GeminiError("GEMINI_API_KEY is not set")
        request = urllib.request.Request(API_URL.format(model=model), data=json.dumps(body).encode(),
                                         headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
        delay = 4.0
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:300]
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.retries and "limit: 0" not in detail:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise GeminiError(f"{model}: HTTP {exc.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < self.retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise GeminiError(f"{model}: {exc}") from None
        raise GeminiError(f"{model}: no answer")

    def _log(self, row: dict) -> None:
        with (self.root / "spend_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def generate(self, name: str, prompt: str, *, model: str, size: str = "2K", aspect: str = "16:9",
                 refs: list[bytes] | None = None) -> Path:
        """One picture, from the cache when the same request was paid before. Refuses past the cap (80 % stops the run)."""
        refs = refs or []
        out = self.root / f"{name}.png"
        key = cache_key(prompt, model, size, aspect, refs)
        cached = self.root / "cache" / f"{key}.png"
        if cached.exists():
            out.write_bytes(cached.read_bytes())
            self._log({"name": name, "model": model, "size": size, "usd": 0.0, "cached": True})
            return out
        cost = estimate(model, size, 1, len(refs))
        if self.spent + cost > self.cap * 0.8 + 1e-9:
            raise GeminiError(f"stop: {self.spent + cost:.3f} USD would pass 80 % of the {self.cap} cap; ask the creator")
        parts = [{"text": prompt}] + [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(r).decode()}}
                                       for r in refs]
        cfg = {"aspectRatio": aspect, "imageSize": size}
        body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": cfg}}
        if self.run is not None:
            self.run.reserve("gemini_usd", cost, item=name)
        try:
            data = self.post(model, body)
        except GeminiError:
            if self.run is not None:
                self.run.refund("gemini_usd", cost)
            raise
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and str(inline.get("mimeType") or inline.get("mime_type") or "").startswith("image/"):
                    raw = base64.b64decode(inline["data"])
                    cached.parent.mkdir(parents=True, exist_ok=True)
                    cached.write_bytes(raw)
                    out.write_bytes(raw)
                    self.spent += cost
                    self._log({"name": name, "model": model, "size": size, "usd": cost, "cached": False,
                               "prompt": prompt[:200]})
                    return out
        reason = (data.get("promptFeedback") or {}).get("blockReason") or "no picture in the answer"
        self._log({"name": name, "model": model, "usd": 0.0, "failed": reason})
        raise GeminiError(f"{model}: {reason}")

    def judge(self, image: bytes, question: str, *, model: str = "gemini-3.8-flash") -> str:
        """A vision answer as text (input price about $0.0015 per picture at $0.75 per million input tokens)."""
        parts = [{"text": question}, {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(image).decode()}}]
        data = self.post(model, {"contents": [{"parts": parts}],
                                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                if "text" in part:
                    self.spent += 0.0015
                    return part["text"]
        raise GeminiError(f"{model}: no text answer")
