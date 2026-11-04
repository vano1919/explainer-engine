# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M8A (Governance, Hash-Pin & Gate Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/governance/records.py`
# Target Module : explainer_engine/governance/records.py
# Target Classes/Symbols : def _now(), def add(), def valid(), def last(), def find()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this governance module with `production_script/4` (`schemas/production_script_v4.schema.json`), `config/cloud_pins.json` (`xworld_v2` weight `0.7` per `CD-02`), `BP-170` static caps (`CD-03`), `CD-05` (`OPEN_PENDING_MEASUREMENT` two-stage RunPod telemetry gate), and `CD-06` (`D-90` deceased historical voice clearance vs `D-62` living-person ban). Ensure all governance status checks (`python -m explainer_engine.governance status --check`) validate `/4` schema hashes and Master Mold v2.1.0 artifact pins without false negatives.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this governance module was authored against the PR #119 baseline (`production_script/2` & `/3`) and does not include `production_script_v4.schema.json`, `mold_contract.py`, `bounded_timeline.py`, or the `CD-01..CD-06` locked creator decisions in its gate/manifest audit checks.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Keeps the cryptographic hash-pin, ledger, and gate state machine 100% synchronized with the Master Mold v2.1.0 code modules and `BATCH-M0..M8B` execution order.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] RunPod Pods Pricing & Per-Second Billing
#        URL: https://docs.runpod.io/pods/pricing
#        Rationale: Details per-second GPU billing for RTX PRO 6000 Blackwell ($1.89/hr Secure Cloud) and H200 SXM ($3.59/hr), requiring hard budget caps and empirical runtime measurement.
#    [2] RunPod Account Billing & Storage Costs
#        URL: https://docs.runpod.io/accounts-billing/billing
#        Rationale: Documents that stopped pods still incur container/volume storage charges until terminated (`runpodctl remove pod`), grounding D-78 / BP-148 auto-teardown.
#    [3] PyTorch torch.compile Tutorial & Cold-Start Behavior
#        URL: https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html
#        Rationale: Explains why compilation overhead is avoided (`compile_mode: none` for <=2 segments in cloud_pins.json) and why cold-start must be amortized.
#    [4] GitHub Docs — About Protected Branches
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
#        Rationale: Specifies required status checks (`quality`), PR-only merge enforcement, and branch protection rules required by GATE-EXT-MAIN-PROTECT.
#    [5] GitHub Docs — Managing Rulesets for a Repository
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
#        Rationale: Specifies ruleset protections preventing force-pushes, accidental branch deletion, and unreviewed merges into main.
#    [6] Python 3.12 What's New — PEP 701 Syntactic Formalization of f-strings
#        URL: https://docs.python.org/3/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
#        Rationale: Explains why nested double-quotes inside an f-string expression (`blind_check.py:36`) raise SyntaxError on Python 3.11 even though Python 3.12+ permits them.
# =============================================================================

"""The creator's recorded word (``jobs/creator_ok.jsonl``): the second lock behind a model switch, an effort override, an
edit of a protected config file, a change of the channel voice (``channel_voice``, target = the voice id, P4b / VC-08) and the
admission of a free generator for a kind (``generator_admit``, target = ``<generator>:<kind>``, BP-162). Claude writes a line only from the creator's own message and quotes it; the hooks cannot
check the quote, they stop an unprompted change (design section 7)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.governance import root_dir

FILE = Path("jobs") / "creator_ok.jsonl"
ACTIONS = ("model_switch", "effort_override", "protected_config", "channel_voice",
           "generator_admit")   # target = "<generator>:<kind>": the word behind an entry of assets/audio/generator_admission.json (BP-162)


def _now() -> float:
    return time.time()


def add(action: str, target: str, message_id: str, quote: str, *, by: str = "creator", root=None, now: float | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError(action)
    if not message_id or not quote.strip():
        raise ValueError("a recorded word needs the creator's message id and a quote")
    if action == "protected_config" and target == "*":
        raise ValueError("protected_config names one file; a wildcard would unlock the money caps too")
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
