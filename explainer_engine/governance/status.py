# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M8A (Governance, Hash-Pin & Gate Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/governance/status.py`
# Target Module : explainer_engine/governance/status.py
# Target Classes/Symbols : def _json(), def phases(), def cards(), def log(), def append_log(), def check_phases(), def check_cards(), def check_log(), def missing_log(), def _cell(), def render_phases(), def render_cards(), def _splice(), def render_status(), def write_status(), def check_all()
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

"""The Blueprint phase table, the decision cards and the routing log as repo files (``docs/blueprint``): validators and the
renderer of the generated blocks of ``docs/blueprint/STATUS.md``."""
from __future__ import annotations

import json
import re
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_text_atomic
from explainer_engine.governance import BLUEPRINT, LEVELS, OWNERS, load, root_dir

STATES = ("todo", "doing", "review", "done", "blocked")
DONE_STATES = ("review", "done")
CREATOR_NAMES = ("ვანო", "creator")
PHASES_MARK = ("<!-- generated:phases -->", "<!-- /generated:phases -->")
CARDS_MARK = ("<!-- generated:cards -->", "<!-- /generated:cards -->")


def _json(root, name: str):
    return json.loads((root_dir(root) / BLUEPRINT / name).read_text(encoding="utf-8"))


def phases(root=None) -> list[dict]:
    return _json(root, "phases.json")["phases"]


def cards(root=None) -> list[dict]:
    return _json(root, "decision_queue.json")["cards"]


def log(root=None) -> list[dict]:
    path = root_dir(root) / BLUEPRINT / "routing_log.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_log(row: dict, root=None) -> None:
    path = root_dir(root) / BLUEPRINT / "routing_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def check_phases(rows: list[dict]) -> list[str]:
    errs, ids = [], {r["id"] for r in rows}
    for r in rows:
        if r["state"] not in STATES:
            errs.append(f"{r['id']}: state {r['state']}")
        for d in r["depends_on"]:
            if d not in ids:
                errs.append(f"{r['id']}: depends on unknown {d}")
        if r["state"] in DONE_STATES and not r.get("pr"):
            errs.append(f"{r['id']}: {r['state']} without a PR")
    return errs


def check_cards(rows: list[dict]) -> list[str]:
    """owner on every card; a creator card is answered only by him (or by Claude on his recorded delegation)."""
    errs, seen = [], set()
    for c in rows:
        i = c.get("id", "?")
        if i in seen:
            errs.append(f"{i}: duplicate id")
        seen.add(i)
        for k in ("question", "options", "reason", "owner"):
            if not c.get(k):
                errs.append(f"{i}: missing {k}")
        if c.get("owner") not in OWNERS:
            errs.append(f"{i}: owner must be creator or claude")
            continue
        a = c.get("answer")
        if not a or a.get("pending"):
            continue
        by = a.get("by")
        if not a.get("reason"):
            errs.append(f"{i}: answer without a reason")
        if c["owner"] == "creator" and by not in CREATOR_NAMES and not (a.get("delegated_by") in CREATOR_NAMES):
            errs.append(f"{i}: creator-owned card answered by {by!r} without his delegation")
        if c["owner"] == "claude" and c.get("level", "S2") in ("S3", "S4") and not c.get("reviewed_by"):
            errs.append(f"{i}: claude-owned {c['level']} card without reviewed_by")
    return errs


def check_log(rows: list[dict], log_rows: list[dict], cfg: dict) -> list[str]:
    errs = []
    for n, l in enumerate(log_rows, 1):
        kind = l.get("kind")
        if kind in ("phase", "plan"):
            if l.get("level") not in LEVELS:
                errs.append(f"log {n}: level")
            if not l.get("model") or not l.get("effort") or not l.get("result"):
                errs.append(f"log {n}: model/effort/result")
        elif kind == "switch":
            if not l.get("to"):
                errs.append(f"log {n}: switch without target")
        else:
            errs.append(f"log {n}: kind {kind!r}")
        if kind == "phase" and not l.get("phase"):
            errs.append(f"log {n}: phase line without phase")
    have = {l.get("phase") for l in log_rows if l.get("kind") == "phase"}
    for r in rows:
        if r["state"] in DONE_STATES and r["id"] not in have:
            errs.append(f"{r['id']}: {r['state']} without a routing_log line")
    return errs


def missing_log(root=None) -> list[str]:
    return [r["id"] for r in phases(root) if r["state"] in DONE_STATES
            and r["id"] not in {l.get("phase") for l in log(root) if l.get("kind") == "phase"}]


def _cell(s) -> str:
    return str(s if s not in (None, "") else "—").replace("|", "/").replace("\n", " ")


def render_phases(rows: list[dict]) -> str:
    out = ["| ID | Title | Depends on | Routing | Wave | Thread | PR | State | Waits for |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| " + " | ".join([r["id"], _cell(r["title"]), _cell(", ".join(r["depends_on"])), _cell(r["routing"]),
                                       _cell(r["wave"]), _cell(r.get("thread")), _cell(r.get("pr")), r["state"],
                                       _cell(r.get("waits"))]) + " |")
    return "\n".join(out)


def render_cards(rows: list[dict]) -> str:
    out = ["| ID | Owner | Question | Answer |", "|---|---|---|---|"]
    for c in rows:
        a = c.get("answer")
        ans = "open" if not a or a.get("pending") else f"{a.get('label') or ''} ({a.get('by')}{', delegated by ' + a['delegated_by'] if a.get('delegated_by') else ''})"
        out.append(f"| {c['id']} | {c['owner']} | {_cell(c['question'])} | {_cell(ans)} |")
    return "\n".join(out)


def _splice(text: str, mark: tuple[str, str], body: str) -> str:
    a, b = mark
    if a not in text or b not in text:
        raise ContractError(f"STATUS.md lacks {a} ... {b}")
    head, rest = text.split(a, 1)
    _, tail = rest.split(b, 1)
    return f"{head}{a}\n{body}\n{b}{tail}"


def render_status(root=None) -> str:
    path = root_dir(root) / BLUEPRINT / "STATUS.md"
    text = path.read_text(encoding="utf-8")
    text = _splice(text, PHASES_MARK, render_phases(phases(root)))
    return _splice(text, CARDS_MARK, render_cards(cards(root)))


def write_status(root=None) -> Path:
    return write_text_atomic(root_dir(root) / BLUEPRINT / "STATUS.md", render_status(root))


def check_all(root=None) -> list[str]:
    cfg = load(root)
    errs = check_phases(phases(root)) + check_cards(cards(root)) + check_log(phases(root), log(root), cfg)
    path = root_dir(root) / BLUEPRINT / "STATUS.md"
    if not path.exists() or render_status(root) != path.read_text(encoding="utf-8"):
        errs.append("STATUS.md generated blocks are stale: run `python -m explainer_engine.governance status --write`")
    return errs
