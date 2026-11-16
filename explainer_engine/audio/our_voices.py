"""Our own voices for the character dialogue (owner decision 2026-11-16: ElevenLabs, not the LTX clip voice; Python item 6).

This module is the PLAN, the CACHE and the COST GUARD. It contains no network client: ``generate`` takes an injected ``client``
(``client.synthesize(job) -> bytes of a WAV``) and refuses to run without the owner's explicit approval, so importing or
testing it can never spend money. Nothing here generates audio on its own; the real ElevenLabs client is added only on the
owner's separate word and a cost estimate.

* ``jobs(spec)``: one job per dialogue line of ``audio/our_voices_spec.json`` with its deterministic cache key
  ``sha256(canonical_json({text, voice_id, model_id, language_code, settings, sample_rate_hz}))`` (the spec's formula).
* ``estimate(jobs)``: credits (1 per character) and USD.
* ``guard(jobs, approved)``: OwnerApprovalRequired without approval; OverCeiling when the plan passes the casting ceiling
  (``config/spend_caps.json`` casting.casting_credits_max) or its 80 % stop (core/spend_caps).
* ``generate(...)``: per-line checkpoint: a line whose cached WAV is valid is skipped (resume without re-billing); the ledger
  file is written after every line, atomically; a failure stops the run with the finished lines kept.
* ``dialogue_wav(...)``: the cached WAV of a line when valid, else None (the mixer keeps the LTX clip audio for that line).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from explainer_engine.core import spend_caps

SAMPLE_RATE_HZ = 48000
MIN_WAV_BYTES = 10240
STOP_FRACTION = 0.8
CREDITS_PER_CHARACTER = 1
USD_PER_CREDIT = 0.23 / 1038   # the spec's single-pass estimate: 1,038 credits ~ $0.23 (an estimate, not a price list)


class OwnerApprovalRequired(RuntimeError):
    """Paid voice generation needs the owner's explicit word (and a cost estimate); nothing was generated."""


def load_spec(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cache_key(text: str, voice_id: str, model_id: str, language_code: str, settings: dict) -> str:
    canon = json.dumps({"text": text, "voice_id": voice_id, "model_id": model_id, "language_code": language_code,
                        "settings": settings, "sample_rate_hz": SAMPLE_RATE_HZ}, sort_keys=True, ensure_ascii=False)
    # json.dumps' default separators on purpose: this is the form the spec's 39 stored keys were made with
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def jobs(spec: dict) -> list[dict]:
    """One job per dialogue line. ``key`` is recomputed here; ``key_matches_spec`` says whether the spec's stored key agrees."""
    profiles = spec.get("voice_profiles") or {}
    out = []
    for ln in spec.get("dialogue_lines") or []:
        prof = profiles.get(ln.get("speaker_id")) or {}
        settings = ln.get("settings") or prof.get("settings") or {}
        voice = ln.get("voice_id") or prof.get("elevenlabs_voice_id") or ""
        model = ln.get("model_id") or prof.get("model_id") or ""
        lang = ln.get("language_code") or prof.get("language_code") or "en"
        key = cache_key(ln["text"], voice, model, lang, settings)
        out.append({"line_id": ln["line_id"], "shot_id": ln.get("shot_id"), "speaker_id": ln.get("speaker_id"), "text": ln["text"],
                    "voice_id": voice, "model_id": model, "language_code": lang, "settings": settings, "key": key,
                    "key_matches_spec": ln.get("cache_key_sha256") in (None, key),
                    "credits": len(ln["text"]) * CREDITS_PER_CHARACTER,
                    "relpath": f"{ln['line_id']}_{key[:16]}.wav"})
    return out


def estimate(planned: list[dict]) -> dict:
    credits = sum(j["credits"] for j in planned)
    return {"lines": len(planned), "credits": credits, "usd_estimate": round(credits * USD_PER_CREDIT, 3)}


def guard(planned: list[dict], approved: bool, ceiling: float | None = None) -> dict:
    """Refuse unless the owner approved, and refuse a plan above the casting ceiling or its 80 % stop. Returns the estimate."""
    if not approved:
        raise OwnerApprovalRequired("generating our voices spends ElevenLabs credits: it needs the owner's explicit approval "
                                    f"and a cost estimate ({estimate(planned)}); nothing was generated")
    ceiling = spend_caps.casting_credits_max() if ceiling is None else float(ceiling)
    est = estimate(planned)
    if est["credits"] > ceiling * STOP_FRACTION + 1e-9:
        raise spend_caps.OverCeiling(f"the plan needs {est['credits']} credits, above the 80 % stop ({ceiling * STOP_FRACTION:g}) "
                                     f"of the casting ceiling {ceiling:g} (config/spend_caps.json)")
    return est


def _valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= MIN_WAV_BYTES
    except OSError:
        return False


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def dialogue_wav(job: dict, cache_dir: Path | str) -> Path | None:
    p = Path(cache_dir) / job["relpath"]
    return p if _valid(p) else None


def generate(planned: list[dict], client, cache_dir: Path | str, ledger_file: Path | str, approved: bool,
             ceiling: float | None = None) -> dict:
    """Synthesize the lines that have no valid cached WAV. The ledger (a JSON file) is rewritten after EVERY line so a stop,
    a crash or an API error loses nothing that was paid for. Raises OwnerApprovalRequired / OverCeiling before any call."""
    todo = [j for j in planned if dialogue_wav(j, cache_dir) is None]
    guard(todo, approved, ceiling)
    ledger_path = Path(ledger_file)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else {"lines": {}, "credits_spent": 0}
    done = skipped = 0
    for j in planned:
        if dialogue_wav(j, cache_dir) is not None:
            skipped += 1
            continue
        wav = client.synthesize(j)
        if len(wav) < MIN_WAV_BYTES:
            raise ValueError(f"line {j['line_id']}: the voice client returned {len(wav)} bytes, too short to be a read")
        _atomic_write(Path(cache_dir) / j["relpath"], wav)
        ledger["lines"][j["line_id"]] = {"key": j["key"], "credits": j["credits"], "path": j["relpath"]}
        ledger["credits_spent"] = sum(v["credits"] for v in ledger["lines"].values())
        _atomic_write(ledger_path, json.dumps(ledger, indent=1, ensure_ascii=False).encode("utf-8"))
        done += 1
    return {"generated": done, "cached": skipped, "credits_spent": ledger["credits_spent"]}
