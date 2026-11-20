
"""The creator's recorded word (``jobs/creator_ok.jsonl``): the second lock behind a model switch, an effort override, an
edit of a protected config file, a change of the channel voice (``channel_voice``, target = the voice id, P4b / VC-08) and the
admission of a free generator for a kind (``generator_admit``, target = ``<generator>:<kind>``, BP-162). Claude writes a line only from the creator's own message and quotes it; the hooks cannot
check the quote, they stop an unprompted change (design section 7)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from explainer_engine.governance import root_dir

FILE = Path("jobs") / "creator_ok.jsonl"
ACTIONS = ("model_switch", "effort_override", "protected_config", "channel_voice",
           "generator_admit",   # target = "<generator>:<kind>": the word behind an entry of assets/audio/generator_admission.json (BP-162)
           "stage_approval",   # target = "<episode>:<stage>:<input hash>": the word behind a REVIEW stage going on (episode/run.py approve)
           "cheapest_waive",    # target = one rule "CH-xx": his word breaks that cheapest-run rule for one run (D-133)
           "layer_waiver",      # target = one layer "L9": his word lets a stage's output go on although a validator of that layer FAILED on it (24 h)
           "layer_gate_mode")   # target = "fail_only" only: the audit trail of his word (2026-11-20 09:11) behind the soft layer gate; nothing reads it


_MSG_ID = re.compile(r"cmsg_[A-Za-z0-9]+")   # the form of a creator's message id (W1: \"x\" is no message id)


def _now() -> float:
    return time.time()


def add(action: str, target: str, message_id: str, quote: str, *, by: str = "creator", root=None, now: float | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError(action)
    if not (isinstance(message_id, str) and _MSG_ID.fullmatch(message_id)) or not quote.strip():
        raise ValueError("a recorded word needs the creator's message id (cmsg_...) and a quote")
    if action == "protected_config" and target == "*":
        raise ValueError("protected_config names one file; a wildcard would unlock the money caps too")
    if action == "cheapest_waive" and not re.fullmatch(r"CH-\d\d", target):
        raise ValueError("cheapest_waive names one rule CH-xx; a wildcard would waive every cheapest-run rule")
    if action == "layer_waiver" and not re.fullmatch(r"L\d{1,2}", target):
        raise ValueError("layer_waiver names one layer L1..L33; a wildcard would open every layer")
    if action == "layer_gate_mode" and target != "fail_only":
        raise ValueError("layer_gate_mode is fail_only: the strict layer gate no longer exists")
    if action == "stage_approval" and (target.count(":") < 2 or "*" in target):
        raise ValueError("stage_approval names one <episode>:<stage>:<input hash>; a wildcard would approve every stage")
    if action == "generator_admit" and "*" in target:
        raise ValueError("generator_admit names one <generator>:<kind>; a wildcard can never match an admission")
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
        if row.get("action") == action and row.get("target") in ((target, "*") if wildcard else (target,)) \
                and isinstance(row.get("message_id"), str) and _MSG_ID.fullmatch(row["message_id"]) \
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
