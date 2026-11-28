"""Owner requirements registry loader and coverage validator for ``governance/layer_gate.py``."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("docs") / "layers" / "owner_requirements.json"


def load(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load owner requirements from ``docs/layers/owner_requirements.json`` if present."""
    path = Path(root) / REGISTRY_PATH
    if not path.is_file():
        return [], []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"OR-READ: cannot parse {REGISTRY_PATH}: {exc}"]
    if isinstance(raw, dict):
        entries = raw.get("entries", [])
    elif isinstance(raw, list):
        entries = raw
    else:
        return [], [f"OR-SCHEMA: {REGISTRY_PATH} must be a JSON object or list"]
    if not isinstance(entries, list):
        return [], [f"OR-SCHEMA: {REGISTRY_PATH} entries must be a list"]
    return [e for e in entries if isinstance(e, dict)], []


def check_registry(entries: list[dict[str, Any]], root: Path) -> list[str]:
    """Validate structure and unique IDs of owner requirement registry entries."""
    _ = root
    errs: list[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(entries):
        rid = entry.get("id")
        if not isinstance(rid, str) or not rid.strip():
            errs.append(f"OR-ID: entry[{idx}] missing non-empty id")
            continue
        if rid in seen:
            errs.append(f"OR-DUP: duplicate owner requirement id {rid!r}")
        seen.add(rid)
        if not isinstance(entry.get("text"), str) or not entry["text"].strip():
            errs.append(f"OR-TEXT: entry {rid!r} missing non-empty text")
    return errs


def missing(entries: list[dict[str, Any]]) -> list[str]:
    """Return error codes for active owner requirements marked unresolved or missing evidence."""
    errs: list[str] = []
    for entry in entries:
        if entry.get("status", "active") == "active" and entry.get("missing_evidence"):
            errs.append(f"OR-MISSING: owner requirement {entry.get('id')!r} lacks evidence")
    return errs


def check_cover(rec: dict[str, Any], layer: str, entries: list[dict[str, Any]], root: Path) -> list[str]:
    """Verify every active owner requirement bound to ``layer`` is referenced in ``rec``."""
    _ = root
    errs: list[str] = []
    bound = [
        e for e in entries
        if e.get("status", "active") == "active" and layer in (e.get("layers") or [])
    ]
    if not bound:
        return errs
    rec_ids = {
        r.get("id")
        for r in (rec.get("requirements") or [])
        if isinstance(r, dict) and isinstance(r.get("id"), str)
    }
    for e in bound:
        rid = e.get("id")
        if rid and rid not in rec_ids:
            errs.append(f"OR-COVER: layer {layer} does not cover active owner requirement {rid!r}")
    return errs
