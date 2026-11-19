
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

# Step 0.4c (D-139, the creator's own message of 2026-11-19 14:32 Georgia time): the plan thread, not the creator, approves
# the file list and a few protected files. A record `by: plan_thread` counts ONLY for a file in the config key
# `plan_thread_approvable`, never for the files below, never for governance code, and it needs a reason, the plan thread's
# message id and the creator's delegation id from `plan_thread_delegation` in the config. These lists are in code on purpose:
# a config edit cannot widen what the plan thread may approve.
PLAN_THREAD = "plan_thread"
NEVER_PLAN_THREAD = frozenset({
    "config/spend_caps.json", "config/model_routing.json", "config/channel_voices.json", "assets/audio/generator_admission.json",
    "explainer_engine/cloud/cheapest.py", "explainer_engine/cloud/cheapest.json", "explainer_engine/training/pods/ltx/launch.json",
})
NEVER_PLAN_THREAD_PREFIXES = ("explainer_engine/governance/",)
QUALITY_YML = ".github/workflows/quality.yml"


def plan_thread_may_approve(target: str, root=None) -> bool:
    """True when ``target`` is in the config's ``plan_thread_approvable`` and not on the code-level never list."""
    from explainer_engine import governance
    if target in NEVER_PLAN_THREAD or target.startswith(NEVER_PLAN_THREAD_PREFIXES) or "*" in target:
        return False
    try:
        listed = governance.load(root).get("plan_thread_approvable") or []
    except Exception:
        return False
    return target in listed


def _delegation_id(root=None) -> str | None:
    from explainer_engine import governance
    try:
        return (governance.load(root).get("plan_thread_delegation") or {}).get("message_id")
    except Exception:
        return None


def quality_yml_problems(old: str, new: str) -> list[str]:
    """What a plan-thread record may NOT approve in ``.github/workflows/quality.yml``: fewer steps or commands than before,
    a new ``continue-on-error``, a new deselect, ``-k`` filter or skip marker. Any such change needs the creator's own word."""
    import re
    def steps(t): return len(re.findall(r"^\s*-\s+name:", t, re.M)), len(re.findall(r"^\s*run:", t, re.M))
    def marks(t): return len(re.findall(r"continue-on-error|--deselect|(?<![\w-])-k\s|--ignore|pytest\.mark\.skip|-m\s+[\"']?not\s", t))
    out = []
    (so, ro), (sn, rn) = steps(old), steps(new)
    if sn < so or rn < ro:
        out.append(f"removes a workflow step or command ({so}->{sn} steps, {ro}->{rn} run lines)")
    if marks(new) > marks(old):
        out.append("adds continue-on-error, a deselect, a -k/-m filter or a skip marker")
    return out
ACTIONS = ("model_switch", "effort_override", "protected_config", "channel_voice",
           "generator_admit",   # target = "<generator>:<kind>": the word behind an entry of assets/audio/generator_admission.json (BP-162)
           "cheapest_waive")    # target = one rule "CH-xx": his word breaks that cheapest-run rule for one run (D-133)


def _now() -> float:
    return time.time()


def add(action: str, target: str, message_id: str, quote: str, *, by: str = "creator", root=None, now: float | None = None,
        reason: str = "", delegation_ref: str = "") -> dict:
    if action not in ACTIONS:
        raise ValueError(action)
    if by not in ("creator", PLAN_THREAD):
        raise ValueError(f"by must be creator or {PLAN_THREAD}")
    if by == PLAN_THREAD:
        if action != "protected_config":
            raise ValueError("the plan thread approves only protected_config (the file list and the approvable files)")
        if not plan_thread_may_approve(target, root):
            raise ValueError(f"{target} is not plan-thread approvable (config plan_thread_approvable; never spend_caps, "
                             "model_routing, channel_voices, cheapest, launch.json or governance code)")
        if not reason.strip():
            raise ValueError("a plan-thread approval needs a reason")
        if not delegation_ref or delegation_ref != _delegation_id(root):
            raise ValueError("a plan-thread approval needs the creator's delegation id (config plan_thread_delegation)")
    if not message_id or not quote.strip():
        raise ValueError("a recorded word needs the creator's message id and a quote")
    if action == "protected_config" and target == "*":
        raise ValueError("protected_config names one file; a wildcard would unlock the money caps too")
    if action == "cheapest_waive" and not re.fullmatch(r"CH-\d\d", target):
        raise ValueError("cheapest_waive names one rule CH-xx; a wildcard would waive every cheapest-run rule")
    if action == "generator_admit" and "*" in target:
        raise ValueError("generator_admit names one <generator>:<kind>; a wildcard can never match an admission")
    row = {"action": action, "target": target, "message_id": message_id, "by": by, "quote": quote[:300],
           "at": now if now is not None else _now()}
    if by == PLAN_THREAD:
        row["reason"] = reason.strip()[:300]
        row["delegation_ref"] = delegation_ref
    path = root_dir(root) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def valid(action: str, target: str, minutes: float, *, root=None, now: float | None = None, wildcard: bool = True,
          include_plan_thread: bool = True) -> bool:
    """True when a record for this action whose target is ``target`` (or ``*`` when ``wildcard``) is younger than ``minutes``.
    A plan-thread record counts only for a plan-thread-approvable ``protected_config`` file (``include_plan_thread``)."""
    path = root_dir(root) / FILE
    if not path.exists():
        return False
    now = now if now is not None else _now()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("by") == PLAN_THREAD and not (include_plan_thread and action == "protected_config"
                                                 and plan_thread_may_approve(str(row.get("target")), root)):
            continue
        if row.get("action") == action and row.get("target") in ((target, "*") if wildcard else (target,)) and row.get("message_id") \
                and 0 <= now - float(row.get("at", 0)) <= minutes * 60:
            return True
    return False


def protected_refusal(rel: str, minutes: float, *, root=None, old: str | None = None, new: str | None = None,
                      via_shell: bool = False) -> str | None:
    """None when a write to protected ``rel`` is allowed: the creator's fresh record, or a plan-thread record for an approvable
    file (for quality.yml also a diff that passes ``quality_yml_problems``; a shell write cannot be diffed, so it needs the
    creator). Else the reason it is refused."""
    if valid("protected_config", rel, minutes, root=root, wildcard=False, include_plan_thread=False):
        return None
    if valid("protected_config", rel, minutes, root=root, wildcard=False, include_plan_thread=True):
        if rel != QUALITY_YML:
            return None
        if via_shell or old is None or new is None:
            return f"{rel}: a plan-thread record cannot approve a write whose diff cannot be checked (use Edit or Write, or the creator's word)"
        probs = quality_yml_problems(old, new)
        return None if not probs else f"{rel}: a plan-thread record cannot approve this change ({'; '.join(probs)}); it needs the creator's own word"
    return f"{rel} changes only on the creator's recorded word (or, for an approvable file, the plan thread's recorded approval)"


def plan_thread_audit(*, root=None) -> list[dict]:
    """Every plan-thread record (path, reason, approver message, time): the audit lines the PR body lists."""
    path = root_dir(root) / FILE
    out = []
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("by") == PLAN_THREAD:
            out.append(row)
    return out


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
        if row.get("by") == PLAN_THREAD:
            continue                                  # a creator_ref names the creator's word, never the plan thread's
        if row.get("action") == action and row.get("target") == target and row.get("message_id") == message_id \
                and (minutes is None or 0 <= now - float(row.get("at", 0)) <= minutes * 60):
            return row
    return None
