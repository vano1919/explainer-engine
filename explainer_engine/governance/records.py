"""The creator's recorded word (``jobs/creator_ok.jsonl``): the second lock behind a model switch, an effort override and an
edit of a protected config file. Claude writes a line only from the creator's own message and quotes it; the hooks cannot
check the quote, they stop an unprompted change (design section 7)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.governance import root_dir

FILE = Path("jobs") / "creator_ok.jsonl"
ACTIONS = ("model_switch", "effort_override", "protected_config")


def _now() -> float:
    return time.time()


def add(action: str, target: str, message_id: str, quote: str, *, by: str = "creator", root=None, now: float | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError(action)
    if not message_id or not quote.strip():
        raise ValueError("a recorded word needs the creator's message id and a quote")
    row = {"action": action, "target": target, "message_id": message_id, "by": by, "quote": quote[:300],
           "at": now if now is not None else _now()}
    path = root_dir(root) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def valid(action: str, target: str, minutes: float, *, root=None, now: float | None = None) -> bool:
    """True when a record for this action whose target is ``target`` or ``*`` is younger than ``minutes``."""
    path = root_dir(root) / FILE
    if not path.exists():
        return False
    now = now if now is not None else _now()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("action") == action and row.get("target") in (target, "*") and row.get("message_id") \
                and 0 <= now - float(row.get("at", 0)) <= minutes * 60:
            return True
    return False
