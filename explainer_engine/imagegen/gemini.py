# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/gemini.py`
# Target Module : explainer_engine/imagegen/gemini.py
# Target Classes/Symbols : def ref_limits(), def _write_atomic(), class GeminiError (methods: ), class ChargeUncertain (methods: ), def _timed_out(), def price(), def estimate(), def cache_key(), def open_batches(), class GeminiClient (methods: __init__, _http, _log, generate, _batch_http, submit_batch, poll_batch, collect_batch)
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

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/imagegen.py (GeminiImages, PRICES), reshaped
"""Gemini picture client (D-41): references, a price table, a budget guard, a cache and a spend log. stdlib only.

Gemini is for reusable channel assets and B hero-acting shots by the routing table (VISUAL_WORLD_ARCHITECTURE section 6).
Nothing is sent without ``estimate`` passing the cap; every call is logged to ``spend_log.jsonl``; the key comes from the
``GEMINI_API_KEY`` environment variable and is never printed.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
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
# Batch tier: half price, the answer comes back in minutes to hours (ai.google.dev/gemini-api/docs/pricing, 2026-10-17)
BATCH_PRICES = {
    "gemini-nano-banana-2.1": {"1K": 0.0168, "2K": 0.0252, "4K": 0.0567},
    "gemini-3.1-flash-lite-image": {"1K": 0.0168},
    "gemini-3.1-flash-image": {"0.5K": 0.022, "1K": 0.034, "2K": 0.050, "4K": 0.076},
    "gemini-3-pro-image": {"1K": 0.067, "2K": 0.067, "4K": 0.12},
}
BATCH_URL = "https://generativelanguage.googleapis.com/v1beta/"
BATCH_MAX_BYTES = 18_000_000  # inline requests must stay under 20 MB
REFERENCE_USD = 0.0011  # one input picture at the Pro rate (the dearest listed)
MAX_REFERENCES = 14
# Reference slots per model (ai.google.dev/gemini-api/docs/image-generation, read 2026-10-22; the page's table was read as
# text, its column order inferred): "characters" = faces the model keeps consistent, the rest are object (or style) images.
# A model not listed keeps MAX_REFERENCES and no face limit beyond it.
REF_LIMITS = {
    "gemini-3-pro-image": {"total": 14, "objects": 6, "characters": 5, "style": 3},
    "gemini-nano-banana-2.1": {"total": 14, "objects": 10, "characters": 4},
    "gemini-3.1-flash-image": {"total": 14, "objects": 10, "characters": 4},
    "gemini-3.1-flash-lite-image": {"total": 14, "objects": 14, "characters": 0},
}


def ref_limits(model: str) -> dict:
    return REF_LIMITS.get(model, {"total": MAX_REFERENCES, "objects": MAX_REFERENCES, "characters": MAX_REFERENCES})
JUDGE_USD = 0.0015  # one vision answer (judge)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# TODO [CLAUDE-CLASS-SYNC: GeminiError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `GeminiError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class GeminiError(RuntimeError):
    pass


# TODO [CLAUDE-CLASS-SYNC: ChargeUncertain] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `ChargeUncertain` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class ChargeUncertain(GeminiError):
    """The paid request was sent but no answer came back (a timeout): the provider may have generated and billed it. Never
    retried and never refunded; the item is recorded as a failure with this cause (audit 2026-10-19 H3)."""


def _timed_out(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", exc)
    return isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError) or "timed out" in str(reason).lower()


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


def open_batches(root: Path) -> dict[str, str]:
    """{item: batch file} for every batch under ``<root>/batches`` that is not settled yet (submitted and not collected, or
    a submit whose answer was lost). ``paint`` never sends these items again (audit 2026-10-19 H2)."""
    out = {}
    for f in sorted((Path(root) / "batches").glob("*.json")):
        meta = json.loads(f.read_text())
        if not meta.get("settled"):
            for item in meta.get("items", []):
                out[item] = f.name
    return out


# TODO [CLAUDE-CLASS-SYNC: GeminiClient] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `GeminiClient` (methods: __init__, _http, _log, generate, _batch_http, submit_batch, poll_batch, collect_batch, judge) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class GeminiClient:
    def __init__(self, root: Path, *, key: str | None = None, cap_usd: float, post=None, timeout: float = 180.0,
                 retries: int = 3, run=None, cache_dir: Path | None = None):
        self.run = run  # core.ledger.Run: charges are reserved there before the call (OR-02)
        self.root = Path(root)
        # one cache for every episode and output folder (EXPLAINER_IMAGE_CACHE), so a paid picture is never bought twice
        env = os.environ.get("EXPLAINER_IMAGE_CACHE")
        self.cache = Path(cache_dir) if cache_dir else Path(env) if env else self.root / "cache"
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
                if _timed_out(exc):  # the request may have been generated and billed: a retry could pay twice
                    raise ChargeUncertain(f"{model}: no answer within {self.timeout:.0f} s; the charge is uncertain") from None
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
        cached = self.cache / f"{key}.png"
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
        except ChargeUncertain:
            raise  # the reservation stays: the provider may have billed it
        except GeminiError:
            if self.run is not None:
                self.run.refund("gemini_usd", cost)
            raise
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and str(inline.get("mimeType") or inline.get("mime_type") or "").startswith("image/"):
                    raw = base64.b64decode(inline["data"])
                    _write_atomic(cached, raw)  # a torn cache file would be served as a hit forever
                    _write_atomic(out, raw)
                    self.spent += cost
                    self._log({"name": name, "model": model, "size": size, "usd": cost, "cached": False,
                               "prompt": prompt[:200]})
                    return out
        reason = (data.get("promptFeedback") or {}).get("blockReason") or "no picture in the answer"
        self._log({"name": name, "model": model, "usd": 0.0, "failed": reason})
        raise GeminiError(f"{model}: {reason}")

    # --- batch tier (half price, asynchronous) ----------------------------------------------------------------------
    def _batch_http(self, method: str, url: str, body: dict | None = None) -> dict:
        if not self.key:
            raise GeminiError("GEMINI_API_KEY is not set")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method,
                                         headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
        last = None
        for attempt in range(1, self.retries + 2):  # a big answer (several 2K pictures, 50+ MB) can be cut off by the proxy
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as exc:
                raise GeminiError(f"batch HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from None
            except (http.client.IncompleteRead, ConnectionError, TimeoutError, urllib.error.URLError) as exc:
                last = exc
                if method != "GET":  # never repeat a POST: it could submit (and charge) a second batch
                    raise GeminiError(f"batch request failed: {exc!r}") from None
                time.sleep(min(2.0 * attempt, 6.0))
        raise GeminiError(f"batch answer could not be read after {self.retries + 1} tries: {last!r}")

    def submit_batch(self, items: list[dict], *, model: str, size: str = "2K", aspect: str = "16:9") -> str:
        """items: [{name, prompt, refs: [bytes]}]. Reserves the batch price, sends ONE batch, records it on disk at once
        (so a stop loses nothing: ``collect_batch`` can be called later, even from another run). Returns the batch name."""
        http = getattr(self, "batch_post", None) or self._batch_http
        reqs, total = [], 0
        for it in items:
            refs = it.get("refs") or []
            parts = [{"text": it["prompt"]}] + [
                {"inlineData": {"mimeType": "image/jpeg" if r[:2] == b"\xff\xd8" else "image/png",
                                "data": base64.b64encode(r).decode()}} for r in refs]
            total += sum(len(r) for r in refs) * 4 // 3 + len(it["prompt"])
            it.setdefault("cache_key", cache_key(it["prompt"], model, size, aspect, refs))
            reqs.append({"request": {"contents": [{"parts": parts}],
                                     "generationConfig": {"responseModalities": ["IMAGE"],
                                                          "imageConfig": {"aspectRatio": aspect, "imageSize": size}}},
                         "metadata": {"key": it["name"]}})
        if total > BATCH_MAX_BYTES:
            raise GeminiError(f"batch of {total} bytes passes the inline limit; split it")
        cost = round(sum(BATCH_PRICES[model][size] + len(it.get("refs") or []) * REFERENCE_USD for it in items), 4)
        if self.run is not None:
            self.run.reserve("gemini_usd", cost, item=f"batch:{items[0]['name']}+{len(items)}")
        elif self.spent + cost > self.cap * 0.8 + 1e-9:
            raise GeminiError(f"stop: {self.spent + cost:.3f} USD would pass 80 % of the {self.cap} cap")
        d = self.root / "batches"
        d.mkdir(parents=True, exist_ok=True)
        meta = {"model": model, "size": size, "cost": cost, "items": [i["name"] for i in items],
                "keys": {i["name"]: i["cache_key"] for i in items}}
        # written BEFORE the POST: if the answer is lost, these items count as submitted and are never sent again
        pending = d / f"submitting_{meta['keys'][items[0]['name']]}.json"
        pending.write_text(json.dumps({**meta, "name": None, "state": "SUBMITTING"}))
        try:
            res = http("POST", f"{BATCH_URL}models/{model}:batchGenerateContent",
                       {"batch": {"display_name": f"ep-{items[0]['name']}-{len(items)}",
                                  "input_config": {"requests": {"requests": reqs}}}})
        except GeminiError:
            pending.unlink()
            if self.run is not None:
                self.run.refund("gemini_usd", cost)
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:  # sent, no answer: maybe accepted; never repeated
            raise ChargeUncertain(f"batch submit: {exc}; {pending.name} keeps these items from being sent again") from None
        name = res.get("name") or (res.get("batch") or {}).get("name")
        if not name:
            pending.unlink()
            if self.run is not None:
                self.run.refund("gemini_usd", cost)
            raise GeminiError(f"batch not accepted: {str(res)[:200]}")
        self.spent += cost
        (d / (name.replace("/", "_") + ".json")).write_text(json.dumps({**meta, "name": name}))
        pending.unlink()
        self._log({"batch": name, "model": model, "size": size, "usd": cost, "items": len(items)})
        return name

    def poll_batch(self, name: str) -> dict:
        """{state, done, results: {item: bytes | error}} - the state field and the result place differ between pages of the
        docs, so both known shapes are read."""
        http = getattr(self, "batch_post", None) or self._batch_http
        res = http("GET", BATCH_URL + name)
        state = res.get("state") or (res.get("metadata") or {}).get("state") or ""
        done = bool(res.get("done")) or state.endswith(("SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"))
        inl = ((res.get("response") or {}).get("inlinedResponses") or (res.get("dest") or {}).get("inlinedResponses")
               or (res.get("metadata") or {}).get("output", {}).get("inlinedResponses") or {})
        rows = inl.get("inlinedResponses", inl) if isinstance(inl, dict) else inl
        results: dict = {}
        for row in rows or []:
            key = (row.get("metadata") or {}).get("key")
            if row.get("error"):
                results[key] = str((row["error"] or {}).get("message", row["error"]))
                continue
            for cand in (row.get("response") or {}).get("candidates") or []:
                for part in (cand.get("content") or {}).get("parts") or []:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and str(inline.get("mimeType") or inline.get("mime_type") or "").startswith("image/"):
                        results[key] = base64.b64decode(inline["data"])
            results.setdefault(key, "no picture in the answer")
        return {"state": state, "done": done, "results": results}

    def collect_batch(self, name: str, *, wait_s: float = 0.0, poll_s: float = 30.0) -> dict:
        """Poll (up to wait_s), write every finished picture as ``<root>/<item>.png`` and return {item: Path | error text}.
        A picture that failed gets its price back (the provider does not charge a failed batch request)."""
        t0 = time.time()
        while True:
            st = self.poll_batch(name)
            if st["done"] or time.time() - t0 >= wait_s:
                break
            time.sleep(poll_s)
        meta_file = self.root / "batches" / (name.replace("/", "_") + ".json")
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        out: dict = {}
        for item, val in st["results"].items():
            if isinstance(val, bytes):
                p = self.root / f"{item}.png"
                _write_atomic(p, val)
                key = (meta.get("keys") or {}).get(item)
                if key:
                    _write_atomic(self.cache / f"{key}.png", val)
                out[item] = p
            else:
                out[item] = val
        if st["done"] and meta and not meta.get("settled"):
            bad = [i for i in meta["items"] if i not in out or not isinstance(out[i], Path)]
            if bad and self.run is not None:
                each = meta["cost"] / max(1, len(meta["items"]))
                self.run.refund("gemini_usd", round(each * len(bad), 4))
            meta["settled"] = True
            meta_file.write_text(json.dumps(meta))
        return {"state": st["state"], "done": st["done"], "items": out}

    def judge(self, image: bytes, question: str, *, model: str = "gemini-3.8-flash", images: list[bytes] | None = None) -> str:
        """A vision answer as text (input price about $0.0015 per picture at $0.75 per million input tokens). Paid, so it is
        reserved in the run ledger like a picture (audit 2026-10-19 H3); without a ledger the client's own cap applies.
        ``images``: more pictures after the first (a scene's master frame for the continuity review, D-69), each priced."""
        more = list(images or [])
        usd = JUDGE_USD * (1 + len(more))
        if self.run is not None:
            self.run.reserve("gemini_usd", usd, item=f"judge:{hashlib.sha256(image).hexdigest()[:12]}")
        elif self.spent + usd > self.cap * 0.8 + 1e-9:
            raise GeminiError(f"stop: {self.spent + usd:.4f} USD would pass 80 % of the {self.cap} cap")
        parts = [{"text": question}] + [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(b).decode()}}
                                        for b in [image] + more]
        data = self.post(model, {"contents": [{"parts": parts}],
                                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                if "text" in part:
                    self.spent += usd
                    return part["text"]
        raise GeminiError(f"{model}: no text answer")
