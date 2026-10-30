"""The creator's recorded word (``jobs/creator_ok.jsonl``): the second lock behind a model switch, an effort override, an
edit of a protected config file and a change of the channel voice (``channel_voice``, target = the voice id, P4b / VC-08). Claude writes a line only from the creator's own message and quotes it; the hooks cannot
check the quote, they stop an unprompted change (design section 7)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.governance import root_dir

FILE = Path("jobs") / "creator_ok.jsonl"
ACTIONS = ("model_switch", "effort_override", "protected_config", "channel_voice")


def _now() -> float:
    return time.time()


def add(action: str, target: str, message_id: str, quote: str, *, by: str = "creator", root=None, now: float | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError(action)
    if not message_id or not quote.strip():
        raise ValueError("a recorded word needs the creator's message id and a quote")
    if action == "protected_config" and target == "*":
        raise ValueError("protected_config names one file; a wildcard would unlock the money caps too")
    row = {"action": action, "target": target, "message_id": message_id, "by": by, "quote": quote[:300],
           "at": now if now is not None else _now()}
    path = root_dir(root) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def valid(action: str, target: str, minutes: float, *, root=None, now: float | None = None, wildcard: bool = True) -> bool:
    """True when a record for this action whose target is ``target`` (or ``*`` when ``wildcard``) is younger than ``minutes``."""
    path = root_dir(root) / FILE
    if not path.exists():
        return False
    now = now if now is not None else _now()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("action") == action and row.get("target") in ((target, "*") if wildcard else (target,)) and row.get("message_id") \
                and 0 <= now - float(row.get("at", 0)) <= minutes * 60:
            return True
    return False


def last(action: str, target: str, *, root=None) -> dict | None:
    """The newest record of this action for ``target`` (or ``*``), valid or not."""
    path = root_dir(root) / FILE
    rows = []
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("action") == action and row.get("target") in (target, "*"):
            rows.append(row)
    return rows[-1] if rows else None


def find(action: str, target: str, message_id: str, *, minutes: float | None = None, root=None, now: float | None = None) -> dict | None:
    """The record of this action for exactly ``target`` (no wildcard) that carries ``message_id`` and, when ``minutes`` is
    given, is younger than that: the check that a ``creator_ref`` handed to code names a word the creator recently gave.
    The file is plain JSONL like the other actions' (no hash chain): this is as strong as they are, not tamper-evident."""
    path = root_dir(root) / FILE
    now = now if now is not None else _now()
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("action") == action and row.get("target") == target and row.get("message_id") == message_id \
                and (minutes is None or 0 <= now - float(row.get("at", 0)) <= minutes * 60):
            return row
    return None
