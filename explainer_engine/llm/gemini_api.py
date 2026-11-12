"""The Gemini API (the Argon reviewer): monthly ceiling enforcement (`config/spend_caps.json`)
and opt-in structured JSON generation for `youtube_viewer_critic` (D-130).

Preserves the exact refusal contract on `complete()` when paid APIs are not explicitly enabled,
while providing `call_structured_json()` guarded by `reserve()` (the 80% stop of `$10.00/month`)
and `model_lifecycle_guard.assert_active_model()`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from explainer_engine.core import spend_caps
from explainer_engine.core.env_loader import load_project_env, redact_secrets_from_text
from explainer_engine.core.ledger import STOP_FRACTION
from explainer_engine.core.model_lifecycle_guard import ACTIVE_CANONICAL_MODELS, assert_active_model


class GeminiRefused(RuntimeError):
    """A Gemini API call was asked for that this repository does not allow yet or exceeds spend cap."""


def monthly_ceiling() -> float:
    return float(spend_caps.gemini_api()["max_usd"])


def reserve(estimate_usd: float, spent_month_usd: float) -> float:
    """The month's spend after this request, or GeminiRefused when it would pass 80 % of the ceiling (stop and ask)."""
    if estimate_usd < 0 or spent_month_usd < 0:
        raise GeminiRefused("a Gemini request cannot cost or have cost less than nothing")
    after = spent_month_usd + estimate_usd
    limit = monthly_ceiling() * STOP_FRACTION
    if after > limit + 1e-9:
        raise GeminiRefused(
            f"Gemini API: ${after:.2f} this month would pass {STOP_FRACTION:.0%} of the ${monthly_ceiling():g} ceiling "
            "(config/spend_caps.json gemini_api); stop and ask the creator"
        )
    return after


def complete(*_args, **_kwargs):
    raise GeminiRefused("the Gemini API client is not built yet: nothing may call it (docs/PROGRESS.md, D9 2026-10-30)")


def call_structured_json(
    system_prompt: str,
    user_payload_json: str,
    *,
    model: str | None = None,
    spent_month_usd: float = 0.0,
    estimate_usd: float = 0.04,
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """Execute an opt-in structured JSON call to Gemini (e.g. `gemini-4-argon` or `gemini-3.8-flash`)
    after reserving `estimate_usd` against `config/spend_caps.json` (`$10/month`, 80% stop).
    Requires `EXPLAINER_ENABLE_PAID_APIS=1` and `GEMINI_API_KEY`."""
    if os.environ.get("EXPLAINER_ENABLE_PAID_APIS", "0") != "1":
        raise GeminiRefused("Paid Gemini API is disabled by default; set EXPLAINER_ENABLE_PAID_APIS=1 to enable live calls.")

    reserve(estimate_usd, spent_month_usd)
    active_model = assert_active_model(model or ACTIVE_CANONICAL_MODELS["g2_viewer_critic"])
    load_project_env()
    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise GeminiRefused("GEMINI_API_KEY is not set in environment or env_config_v4.env.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_payload_json}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise GeminiRefused(f"Gemini API error ({active_model}): {redact_secrets_from_text(str(exc))}") from None

    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if "text" in part and part["text"].strip():
                return json.loads(part["text"])
    raise GeminiRefused(f"{active_model} returned no JSON text candidate.")
