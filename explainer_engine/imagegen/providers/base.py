"""The provider interface (D-70 stage D). stdlib only.

An adapter knows its models (price per picture by size, reference limit, version string), prices a request BEFORE it is
sent (``estimate``), reserves the money on the run ledger (``core.ledger.Run``) when one is given, caches by request so a
paid picture is never bought twice (``cache_key``), and returns a ``Result`` with the bytes, the seed the provider reports,
the settled cost when the provider states one, and the wall-clock. Keys come from environment variables only and are never
printed. A request that was sent and got no answer raises ``ChargeUncertain`` (never retried, never refunded: the provider
may have billed it) exactly as ``imagegen.gemini`` does.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from explainer_engine.imagegen.gemini import ChargeUncertain, GeminiError, _timed_out, _write_atomic  # noqa: F401


class ProviderError(RuntimeError):
    pass


class AccountError(ProviderError):
    """The account cannot be used at all (bad key, no balance, locked): every later request would fail the same way."""


@dataclass
class Result:
    data: bytes
    model: str
    model_version: str
    seed: int | None
    usd_estimated: float
    usd_settled: float | None  # what the provider itself reported, when it does
    seconds: float
    cached: bool = False
    meta: dict = field(default_factory=dict)


def cache_key(provider: str, model: str, prompt: str, size: str, refs: list[bytes], seed: int | None, extra: dict | None = None) -> str:
    h = hashlib.sha256()
    h.update(json.dumps([provider, model, prompt, size, seed, extra or {}], sort_keys=True).encode())
    for r in refs:
        h.update(hashlib.sha256(r).digest())
    return h.hexdigest()[:32]


def data_uri(png: bytes) -> str:
    kind = "image/png" if png[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return f"data:{kind};base64," + base64.b64encode(png).decode()


class ImageProvider:
    """Subclasses set ``name``, ``service`` (the ledger line), ``PRICES`` {model: {size: usd}}, ``MAX_REFS`` {model: n},
    ``VERSIONS`` {model: version string} and implement ``_request``; everything else is shared."""
    name = ""
    service = ""
    key_env = ""
    PRICES: dict[str, dict[str, float]] = {}
    MAX_REFS: dict[str, int] = {}
    VERSIONS: dict[str, str] = {}
    PRICES_CHECKED = ""

    def __init__(self, root: Path, *, run=None, cache_dir: Path | None = None, http=None, timeout: float = 180.0, key: str | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        env = os.environ.get("EXPLAINER_IMAGE_CACHE")
        self.cache = Path(cache_dir) if cache_dir else Path(env) if env else self.root / "cache"
        self.run = run
        self.http = http or self._http
        self.timeout = timeout
        self._key = key
        self.spent = 0.0

    # --- money ---------------------------------------------------------------------------------------------------
    def price(self, model: str, size: str) -> float:
        try:
            return self.PRICES[model][size]
        except KeyError:
            raise ProviderError(f"{self.name}: no price for {model} at {size} (known: {self.PRICES.get(model, {})})") from None

    def estimate(self, model: str, size: str, count: int = 1, refs: int = 0) -> float:
        return round(self.price(model, size) * count, 4)

    def max_refs(self, model: str) -> int:
        return self.MAX_REFS.get(model, 0)

    def version(self, model: str) -> str:
        return self.VERSIONS.get(model, "")

    # --- the key never leaves the process --------------------------------------------------------------------------
    def key(self) -> str:
        k = self._key or os.environ.get(self.key_env, "")
        if not k:
            raise ProviderError(f"{self.name}: {self.key_env} is not set")
        return k

    def _http(self, method: str, url: str, body: dict | None, headers: dict) -> tuple[int, bytes]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if _timed_out(exc):
                raise ChargeUncertain(f"{self.name}: no answer within {self.timeout:.0f} s; the charge is uncertain") from None
            raise ProviderError(f"{self.name}: {exc}") from None

    def _json(self, method: str, url: str, body: dict | None = None, *, headers: dict | None = None, ok=(200,)) -> dict:
        status, raw = self.http(method, url, body, headers or {})
        if status == 402:
            raise AccountError(f"{self.name}: HTTP 402, no credits left on the account; nothing more is sent")
        if status in (401, 403):
            raise AccountError(f"{self.name}: HTTP {status} (key or account): {raw[:200].decode('utf-8', 'replace')}")
        if status == 429:
            raise ProviderError(f"{self.name}: HTTP 429 rate limited; try again later")
        if status not in ok:
            raise ProviderError(f"{self.name}: HTTP {status}: {raw[:300].decode('utf-8', 'replace')}")
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            raise ProviderError(f"{self.name}: not JSON: {raw[:120]!r}") from None

    def _download(self, url: str) -> bytes:
        status, raw = self.http("GET", url, None, {})
        if status != 200 or not raw:
            raise ProviderError(f"{self.name}: picture download failed (HTTP {status})")
        return raw

    # --- one picture ---------------------------------------------------------------------------------------------
    def _request(self, prompt: str, *, model: str, size: str, refs: list[bytes], seed: int | None, extra: dict) -> tuple[bytes, dict]:
        """Send one request and return (picture bytes, provider meta incl. optional 'seed' and 'usd_settled')."""
        raise NotImplementedError

    def generate(self, name: str, prompt: str, *, model: str, size: str, refs: list[bytes] | None = None, seed: int | None = None,
                 extra: dict | None = None) -> Result:
        refs, extra = list(refs or []), dict(extra or {})
        if model not in self.PRICES:
            raise ProviderError(f"{self.name}: unknown model {model!r}; known: {sorted(self.PRICES)}")
        if len(refs) > self.max_refs(model):
            raise ProviderError(f"{self.name}: {len(refs)} references; {model} takes at most {self.max_refs(model)}")
        cost = self.estimate(model, size, 1, len(refs))
        key = cache_key(self.name, model, prompt, size, refs, seed, extra)
        cached = self.cache / f"{key}.png"
        out = self.root / f"{name}.png"
        if cached.exists():
            out.write_bytes(cached.read_bytes())
            meta = json.loads(cached.with_suffix(".json").read_text(encoding="utf-8")) if cached.with_suffix(".json").exists() else {}
            self._log({"name": name, "model": model, "size": size, "usd": 0.0, "cached": True})
            return Result(out.read_bytes(), model, self.version(model), meta.get("seed", seed), 0.0, 0.0, 0.0, cached=True, meta=meta)
        if self.run is not None:
            self.run.reserve(self.service, cost, item=name)
        t0 = time.time()
        try:
            data, meta = self._request(prompt, model=model, size=size, refs=refs, seed=seed, extra=extra)
        except ChargeUncertain:
            raise
        except ProviderError:
            if self.run is not None:
                self.run.refund(self.service, cost)
            raise
        seconds = round(time.time() - t0, 2)
        settled = meta.get("usd_settled")
        if settled is not None and self.run is not None:
            self.run.settle(self.service, name, float(settled))
        _write_atomic(cached, data)
        _write_atomic(cached.with_suffix(".json"), json.dumps({**meta, "model": model, "version": self.version(model)}).encode())
        _write_atomic(out, data)
        self.spent += float(settled) if settled is not None else cost
        self._log({"name": name, "model": model, "size": size, "usd": cost, "usd_settled": settled, "seconds": seconds,
                   "seed": meta.get("seed", seed), "cached": False, "prompt": prompt[:200]})
        return Result(data, model, self.version(model), meta.get("seed", seed), cost, settled, seconds, meta=meta)

    def edit(self, name: str, prompt: str, *, model: str, size: str, refs: list[bytes], seed: int | None = None, extra: dict | None = None) -> Result:
        """An edit is a generation whose first reference is the picture being changed (every candidate works this way)."""
        if not refs:
            raise ProviderError(f"{self.name}: an edit needs the picture to edit as its first reference")
        return self.generate(name, prompt, model=model, size=size, refs=refs, seed=seed, extra={**(extra or {}), "edit": True})

    def _log(self, row: dict) -> None:
        with (self.root / "spend_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"provider": self.name, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), **row}) + "\n")
