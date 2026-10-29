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
