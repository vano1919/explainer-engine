"""Centralized Secure .env & Drive Credential Loader & Alias Normalizer (D-128 / D-130).

Loads `env_config_v4.env` or `.env` from Google Drive (`Explainer_Engine_V4_Main`) or local workspace
without ever logging or exposing secret values, and maps all user-provided keys
(`GEMINI_API_KEY`, `ELEVENLABS_API`, `FAL_KEY`, `BFL_API_kay`, `MODAL_TOKEN_ID`,
`MODAL_TOKEN_SECRET`, `RUNPOD_API_KEY`, `HYPERSTACK_API_KEY`, `HF_TOKEN`, etc.)
to the canonical environment variable names expected by every worker module.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List


CANONICAL_ALIASES: Dict[str, List[str]] = {
    "GEMINI_API_KEY": ["GOOGLE_API_KEY", "BANANA_API_KEY", "NANO_BANANA_API_KEY"],
    "GOOGLE_API_KEY": ["GEMINI_API_KEY"],
    "ELEVENLABS_API": ["ELEVENLABS_API_KEY", "XI_API_KEY"],
    "ELEVENLABS_API_KEY": ["ELEVENLABS_API", "XI_API_KEY"],
    "BFL_API_kay": ["BFL_API_KEY"],
    "BFL_API_KEY": ["BFL_API_kay"],
    "FAL_KEY": ["FAL_API_KEY"],
    "HF_TOKEN": ["HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
}

# Locked Narrator Voice ID (ElevenLabs 'Odom - Deep, Resonant, Dramatic', active for 730-day notice window)
LOCKED_NARRATOR_VOICE_ID = "CcSJ2r3qw0XU9gJpEPyk"
LOCKED_NARRATOR_VOICE_NAME = "Odom - Deep, Resonant, Dramatic"
FALLBACK_NARRATOR_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George - Deep British Storyteller backup

_URL_KEY_REGEX = re.compile(r"([?&](?:key|api_key|token)=)([^&\s\"']+)", re.I)


def redact_secrets_from_text(text: str) -> str:
    """Redact any query-string `?key=...` or known environment secret values from logs/errors."""
    if not text:
        return ""
    sanitized = _URL_KEY_REGEX.sub(r"\1[REDACTED]", str(text))
    for key_name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ELEVENLABS_API_KEY",
        "FAL_KEY",
        "BFL_API_KEY",
        "MODAL_TOKEN_SECRET",
        "RUNPOD_API_KEY",
        "HYPERSTACK_API_KEY",
        "HF_TOKEN",
    ):
        secret_val = os.environ.get(key_name, "").strip()
        if len(secret_val) >= 8 and secret_val in sanitized:
            sanitized = sanitized.replace(secret_val, f"[REDACTED_{key_name}]")
    return sanitized


def load_project_env(env_path: Path | str | None = None) -> Dict[str, bool]:
    """Load `env_config_v4.env`, `.env`, or `vault_secrets.json` from Google Drive or repo root into `os.environ`.
    Returns a boolean presence map only (never secret values)."""
    explicit = Path(env_path) if env_path else None
    candidates = [
        explicit,
        Path("/content/drive/MyDrive/Explainer_Engine_V4_Main/env_config_v4.env"),
        Path("/content/drive/MyDrive/Explainer_Engine_V4_Main/.env"),
        Path.cwd() / "env_config_v4.env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / "env_config_v4.env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    loaded_file = None
    for cand in candidates:
        if cand and cand.exists() and cand.is_file():
            loaded_file = cand
            for raw_line in cand.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and v:
                    os.environ.setdefault(k, v)
            break

    # Also check vault_secrets.json on Drive if present
    vault_candidates = [
        Path("/content/drive/MyDrive/Explainer_Engine_V4_Main/vault_secrets.json"),
        Path.cwd() / "vault_secrets.json",
    ]
    for vc in vault_candidates:
        if vc.exists() and vc.is_file():
            try:
                vdata = json.loads(vc.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(vdata, dict):
                    for k, v in vdata.items():
                        if isinstance(k, str) and isinstance(v, str) and v.strip():
                            os.environ.setdefault(k.strip(), v.strip())
                    if loaded_file is None:
                        loaded_file = vc
            except Exception:
                pass
            break

    # Apply alias normalization so both `ELEVENLABS_API` and `ELEVENLABS_API_KEY` work seamlessly
    for src_key, target_keys in CANONICAL_ALIASES.items():
        val = os.environ.get(src_key)
        if val:
            for tk in target_keys:
                os.environ.setdefault(tk, val)

    tracked_keys = [
        "GEMINI_API_KEY",
        "ELEVENLABS_API_KEY",
        "FAL_KEY",
        "BFL_API_KEY",
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "RUNPOD_API_KEY",
        "HYPERSTACK_API_KEY",
        "HF_TOKEN",
    ]
    return {
        "env_file_found": loaded_file is not None,
        **{k: bool(os.environ.get(k)) for k in tracked_keys},
    }
