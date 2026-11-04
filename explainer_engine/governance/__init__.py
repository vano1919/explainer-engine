# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M8A (Governance, Hash-Pin & Gate Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/governance/__init__.py`
# Target Module : explainer_engine/governance/__init__.py
# Target Classes/Symbols : def root_dir(), def load(), def validate()
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

"""Model and process governance in code (P0b, D-84): the one config (``config/model_routing.json``, D7), the creator's recorded
word, the hooks that lint what instructions cannot enforce, the phase/decision/routing-log files under ``docs/blueprint``.
stdlib only; every check fails open in the hooks (a broken check must not lock a session), loudly in the tests."""
from __future__ import annotations

import json
import os
from pathlib import Path

from explainer_engine.core.errors import ContractError

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path("config") / "model_routing.json"
BLUEPRINT = Path("docs") / "blueprint"
LEVELS = ("S0", "S1", "S2", "S3", "S4")
OWNERS = ("creator", "claude")


def root_dir(root: Path | str | None = None) -> Path:
    """The repo the hooks act on: an explicit root, else $CLAUDE_PROJECT_DIR, else this checkout."""
    if root:
        return Path(root)
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env and (Path(env) / CONFIG).exists() else ROOT


def load(root: Path | str | None = None) -> dict:
    cfg = json.loads((root_dir(root) / CONFIG).read_text(encoding="utf-8"))
    validate(cfg)
    return cfg


def validate(cfg: dict) -> None:
    """Structural checks of ``config/model_routing.json``; raises ContractError listing every problem."""
    errs: list[str] = []
    models, efforts = cfg.get("models", {}), cfg.get("efforts", [])
    for key in ("models", "efforts", "classes", "code", "escalation", "critics", "spawners", "fable_story_stages", "agents",
                "owner", "model_switch", "protected_files", "usage", "reminder"):
        if key not in cfg:
            errs.append(f"missing key {key}")
    if errs:
        raise ContractError("; ".join(errs))
    if set(models) != {"haiku", "sonnet", "opus", "fable"}:
        errs.append("models must be haiku, sonnet, opus, fable")
    if efforts != ["low", "medium", "high", "xhigh", "max"]:
        errs.append("efforts must be low..max in order")
    ids = set()
    for c in cfg["classes"]:
        if c["id"] in ids:
            errs.append(f"duplicate class {c['id']}")
        ids.add(c["id"])
        if not set(c["models"]) <= set(models):
            errs.append(f"class {c['id']}: unknown model")
        if not set(c["efforts"]) <= set(efforts):
            errs.append(f"class {c['id']}: unknown effort")
        if not c["level"].startswith("S"):
            errs.append(f"class {c['id']}: level")
        if "fable" in c["models"] and "code" in c["id"]:
            errs.append(f"class {c['id']}: fable never for code")
    ceiling = efforts.index(cfg["code"]["effort_ceiling"]) if cfg["code"]["effort_ceiling"] in efforts else None
    if ceiling is None:
        errs.append("code.effort_ceiling")
    for name, a in cfg["agents"].items():
        if a["role"] not in ("main", "critic", "stage", "stage-story"):
            errs.append(f"agent {name}: role")
        if a["model"] not in models or a["effort"] not in efforts:
            errs.append(f"agent {name}: model/effort")
        if a["role"] != "stage-story" and a["model"] == "fable":
            errs.append(f"agent {name}: fable only on a story stage")
        if ceiling is not None and efforts.index(a["effort"]) > ceiling:
            errs.append(f"agent {name}: effort above the code ceiling")
    crit = cfg["critics"]
    for n in crit["names"]:
        a = cfg["agents"].get(n)
        if not a or a["role"] != "critic" or a["model"] != crit["model"] or a["effort"] != crit["effort"]:
            errs.append(f"critic {n}: must be {crit['model']}/{crit['effort']}")
    for n in cfg["spawners"]:
        if cfg["agents"].get(n, {}).get("role") != "main":
            errs.append(f"spawner {n}: must be a main agent")
    if not set(cfg["fable_story_stages"]["stages"]) <= set(cfg["agents"]):
        errs.append("fable_story_stages: unknown agent")
    if cfg["owner"].get("default") != "creator":
        errs.append("owner.default must be creator")
    if errs:
        raise ContractError("; ".join(errs))
