"""Model lifecycle guard (D-130; v4.3 plan P3.8): retired models are blocked, paid calls need a freshly checked model.

The lists live as dated data in ``config/model_lifecycle.json`` (each entry: its source and the day it was checked). The
archive's names were never checked against a vendor page, so they carry ``checked: null``: a retired name still blocks (blocking
is safe), but no paid call may use a model whose entry is unchecked or older than ``max_check_age_days`` on the day of the run
(``assert_fresh_for_paid_run``). The plan's words: "No model name is trusted from the zip."
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, Tuple

DATA_PATH = Path(__file__).resolve().parents[2] / "config" / "model_lifecycle.json"


class RetiredModelBlockedError(RuntimeError):
    """Raised when code attempts to invoke a retired or shut-down model endpoint."""


class ModelCheckStale(RuntimeError):
    """A paid call names a model whose lifecycle entry is missing, unsourced, unchecked or too old."""


def load(path: Path = DATA_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


_DATA = load()
RETIRED_MODELS_REGISTRY: Dict[str, Dict[str, str]] = _DATA["retired"]
ACTIVE_CANONICAL_MODELS: Dict[str, str] = _DATA["canonical"]
ALLOWED_ACTIVE_MODEL_IDS: Tuple[str, ...] = tuple(_DATA["active"])
MAX_CHECK_AGE_DAYS: int = int(_DATA["max_check_age_days"])


def assert_active_model(model_id: str) -> str:
    """Validate that `model_id` is not retired or shut down. Returns `model_id` if active."""
    cleaned = str(model_id or "").strip()
    if not cleaned:
        raise RetiredModelBlockedError("Empty model_id passed to assert_active_model().")
    if cleaned in RETIRED_MODELS_REGISTRY:
        info = RETIRED_MODELS_REGISTRY[cleaned]
        raise RetiredModelBlockedError(
            f"BLOCKED RETIRED MODEL {cleaned!r} (shut down {info['shutdown_date']}): "
            f"{info['reason']} Use active replacement {info['replacement']!r}."
        )
    return cleaned


def resolve_or_migrate_model(model_id: str) -> str:
    """Return active replacement if `model_id` is in `RETIRED_MODELS_REGISTRY`, else validate and return."""
    cleaned = str(model_id or "").strip()
    if cleaned in RETIRED_MODELS_REGISTRY:
        return RETIRED_MODELS_REGISTRY[cleaned]["replacement"]
    return assert_active_model(cleaned)


def assert_fresh_for_paid_run(model_id: str, today: date | None = None, data: dict | None = None) -> str:
    """Before a PAID call: the model is not retired, is listed as active with a vendor URL, and was checked at most
    ``max_check_age_days`` ago. Raises ``ModelCheckStale`` otherwise (re-read the vendor page and date the entry)."""
    d = data or _DATA
    cleaned = str(model_id or "").strip()
    if cleaned in d["retired"]:
        raise RetiredModelBlockedError(f"{cleaned!r} is listed as retired (replacement {d['retired'][cleaned].get('replacement')!r})")
    entry = d["active"].get(cleaned)
    if entry is None:
        raise ModelCheckStale(f"{cleaned!r} is not in config/model_lifecycle.json 'active'; check the vendor page first")
    if not str(entry.get("source", "")).startswith("https://") or not entry.get("checked"):
        raise ModelCheckStale(f"{cleaned!r} was never checked against a vendor page ({entry.get('source')}); no paid call")
    age = ((today or date.today()) - date.fromisoformat(entry["checked"])).days
    if age > int(d["max_check_age_days"]):
        raise ModelCheckStale(f"{cleaned!r} was checked {entry['checked']} ({age} days ago, more than "
                              f"{d['max_check_age_days']}); re-read {entry['source']} and date the entry before a paid call")
    return cleaned
