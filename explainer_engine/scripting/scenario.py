"""The approved short scenario comes before the script (PV-45, OR-15; creator 2026-10-19). stdlib only.

The creator reads a short scenario (the story in plain lines, the dialogue marked) and approves it before any production
script is written, so the final story is the one they liked. ``episode.scenario`` records that approval: the scenario file
next to the script, who approved it and when, and the file's sha256, so a scenario edited after the approval is caught.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

LEGACY = "production_script/1"  # written before the rule: a REVIEW, never a FAIL
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(doc: dict, base: Path | None = None) -> list[dict]:
    """``base`` is the episode folder; without it only the record is checked, not the file."""
    sev = "REVIEW" if doc.get("schema") == LEGACY else "FAIL"
    rec = doc["episode"].get("scenario")
    if not rec:
        return [{"rule": "PV-45", "severity": sev, "where": "episode.scenario",
                 "detail": "no approved scenario: send the creator a short scenario first and write the script only after "
                           "they approve it (OR-15); record file, approved_by, approved_at, sha256"}]
    out = []
    missing = [k for k in ("file", "approved_by", "approved_at", "sha256") if not str(rec.get(k, "")).strip()]
    if missing:
        out.append({"rule": "PV-45", "severity": sev, "where": "episode.scenario", "detail": f"empty: {missing}"})
    if rec.get("approved_at") and not DATE.match(rec["approved_at"]):
        out.append({"rule": "PV-45", "severity": sev, "where": "episode.scenario", "detail": "approved_at is YYYY-MM-DD"})
    if base is not None and rec.get("file"):
        path = base / rec["file"]
        if not path.exists():
            out.append({"rule": "PV-45", "severity": sev, "where": rec["file"], "detail": "the approved scenario file is missing"})
        elif rec.get("sha256") and sha256(path) != rec["sha256"]:
            out.append({"rule": "PV-45", "severity": sev, "where": rec["file"],
                        "detail": "the scenario changed after the approval: the creator approves the new version first"})
    return out
