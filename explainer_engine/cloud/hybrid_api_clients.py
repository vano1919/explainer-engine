"""Executable Selective Hybrid API Escalation Clients (Sync-3 4K Lip-Sync, Seedance 2.5, ElevenLabs v4).

Called ONLY when ``hybrid_escalation_router.route_drama_shot`` triggers surgical API fallback
(e.g., sharp >=40° profile close-up, beard/hand mouth occlusion, >4 visual references, or hero voice),
strictly gated by ``EpisodeBudgetGuard`` (SQLite WAL $10.00 episode cap).

Supports ``dry_run=True`` for $0.00 end-to-end launcher verification and CI testing. ElevenLabs speech has the dry
run only: its live path is the ElevenLabs connector, never a REST client of this package (D8).
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from explainer_engine.cloud.modal_cinema_studio import EpisodeBudgetGuard


def _require_env(var_name: str) -> str:
    val = os.environ.get(var_name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required API credential environment variable: {var_name}")
    return val


def run_sync3_lipsync_escalation(
    *,
    job_id: str,
    video_url: str,
    audio_url: str,
    duration_s: float,
    budget_guard: EpisodeBudgetGuard,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Invoke Sync Labs Sync-3 (4K native lip-sync) for hard profile/occlusion close-ups."""
    est_usd = round(max(0.15, float(duration_s) * 0.09), 4)
    resv = budget_guard.reserve(job_id=job_id, category="api_lipsync", provider="sync_3_api_4k", estimated_usd=est_usd)
    payload = {
        "model": "sync-3",
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url},
        ],
        "options": {"sync_mode": "cut_off", "output_format": "mp4"},
    }
    if dry_run:
        budget_guard.settle(job_id, actual_usd=0.0)
        return {
            "status": "DRY_RUN_OK",
            "provider": "sync_3_api_4k",
            "job_id": job_id,
            "estimated_live_usd": est_usd,
            "checkpoint_reached": resv["checkpoint_reached"],
            "payload": payload,
        }

    api_key = _require_env("SYNC_LABS_API_KEY")
    req = urllib.request.Request(
        "https://api.sync.so/v2/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    budget_guard.settle(job_id, actual_usd=est_usd)
    return {"status": "SUBMITTED", "provider": "sync_3_api_4k", "job_id": job_id, "response": data}


def run_seedance25_video_escalation(
    *,
    job_id: str,
    prompt: str,
    reference_urls: list[str],
    duration_s: float,
    aspect_ratio: str = "16:9",
    draft_mode: bool = True,
    budget_guard: EpisodeBudgetGuard,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Invoke Seedance 2.5 API (Draft 480p -> 1080p) for complex >4-reference scenes."""
    rate_per_s = 0.04 if draft_mode else 0.10
    est_usd = round(max(0.20, float(duration_s) * rate_per_s), 4)
    resv = budget_guard.reserve(job_id=job_id, category="api_video", provider="seedance_2_5_api", estimated_usd=est_usd)
    payload = {
        "model": "seedance-2.5",
        "prompt": prompt.strip(),
        "references": reference_urls[:50],
        "duration_s": round(float(duration_s), 2),
        "aspect_ratio": aspect_ratio,
        "resolution": "480p" if draft_mode else "1080p",
    }
    if dry_run:
        budget_guard.settle(job_id, actual_usd=0.0)
        return {
            "status": "DRY_RUN_OK",
            "provider": "seedance_2_5_api",
            "job_id": job_id,
            "estimated_live_usd": est_usd,
            "checkpoint_reached": resv["checkpoint_reached"],
            "payload": payload,
        }

    api_key = _require_env("SEEDANCE_API_KEY")
    endpoint = os.environ.get("SEEDANCE_API_ENDPOINT", "https://api.byteplus.com/v1/video/generations")
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    budget_guard.settle(job_id, actual_usd=est_usd)
    return {"status": "SUBMITTED", "provider": "seedance_2_5_api", "job_id": job_id, "response": data}


def run_elevenlabs_v4_tts(
    *,
    job_id: str,
    text: str,
    voice_id: str,
    out_wav: Path,
    turbo: bool = True,
    budget_guard: EpisodeBudgetGuard,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Plan Voice-First character dialogue for ElevenLabs v4 / v4 Turbo ($0.08 / $0.04 per 1K chars).

    Only the dry run works here. Speech is bought through the ElevenLabs connector, its hook and ledger (D8, the
    creator's answer of 2026-10-29), so a live call is refused before anything is reserved.
    """
    if not dry_run:
        raise RuntimeError(
            "Live ElevenLabs speech is not called from this package: use the ElevenLabs connector (its hook and "
            "ledger, D8). Nothing was reserved."
        )
    chars = max(1, len(text.strip()))
    rate_per_1k = 0.04 if turbo else 0.08
    est_usd = round((chars / 1000.0) * rate_per_1k, 4)
    resv = budget_guard.reserve(job_id=job_id, category="api_tts", provider="elevenlabs_v4", estimated_usd=est_usd)
    model_id = "eleven_v4_turbo" if turbo else "eleven_v4"
    payload = {
        "text": text.strip(),
        "model_id": model_id,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.80},
    }
    budget_guard.settle(job_id, actual_usd=0.0)
    return {
        "status": "DRY_RUN_OK",
        "provider": model_id,
        "job_id": job_id,
        "out_wav": str(out_wav),
        "estimated_live_usd": est_usd,
        "checkpoint_reached": resv["checkpoint_reached"],
        "payload": payload,
    }


__all__ = [
    "run_elevenlabs_v4_tts",
    "run_seedance25_video_escalation",
    "run_sync3_lipsync_escalation",
]
