"""Canonical Skill Orchestrator for Explainer Engine.

Coordinates active Skills across production stages with:
- Dependency resolution (topological order, no duplicate execution)
- Conditional stage selection (no hardcoded 10/30/60 visual quota)
- Retired-skill refusal (prevents reviving Qwen/LoRA/Unreal routes)
- Missing-input detection before stage execution
- Requirement -> Skill -> Python module correspondence audit
- Persistent skill participation ledger (`skill_execution_record.json`)
"""
from __future__ import annotations

import datetime
import importlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = Path(__file__).resolve().parent / "skill_registry.json"
SKILLS_DIR = ROOT / ".claude" / "skills"
UTC = datetime.timezone.utc


@dataclass(frozen=True)
class PlannedStage:
    stage_id: str
    name: str
    order: int
    skills: list[str]
    python_modules: list[str]
    missing_inputs: list[str]
    implementation_gaps: list[str]


@dataclass
class OrchestrationPlan:
    stages: list[PlannedStage] = field(default_factory=list)
    skipped_conditional: list[str] = field(default_factory=list)
    blocked_missing_inputs: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return not self.blocked_missing_inputs

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "stages": [asdict(s) for s in self.stages],
            "skipped_conditional": list(self.skipped_conditional),
            "blocked_missing_inputs": dict(self.blocked_missing_inputs),
        }


def load_registry(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_REGISTRY
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != "skill_registry/1":
        raise ContractError(f"Unsupported skill registry schema: {data.get('schema_version')!r}")
    return data


class SkillOrchestrator:
    """Selects, validates, and tracks Skill execution across pipeline stages."""

    def __init__(self, registry_path: Path | None = None, skills_dir: Path | None = None) -> None:
        self.registry = load_registry(registry_path)
        self.skills_dir = skills_dir or SKILLS_DIR
        self._stages: dict[str, dict[str, Any]] = {s["stage_id"]: s for s in self.registry["stages"]}
        self._retired: set[str] = set(self.registry.get("retired_skills", []))

    def assert_not_retired(self, skill_name: str) -> None:
        if skill_name in self._retired:
            raise ContractError(f"Skill {skill_name!r} is retired and cannot be activated in active workflows")

    def select_plan(
        self,
        requested_stages: list[str] | None = None,
        *,
        context: dict[str, Any] | None = None,
        available_artifacts: set[str] | list[str] | None = None,
        completed_stages: set[str] | list[str] | None = None,
    ) -> OrchestrationPlan:
        ctx = dict(context or {})
        available = set(available_artifacts or ())
        completed = set(completed_stages or ())

        targets = list(requested_stages) if requested_stages else list(self._stages.keys())
        for sid in targets:
            if sid not in self._stages:
                raise ContractError(f"Unknown stage_id: {sid!r}")

        # Expand transitive dependencies
        needed: set[str] = set()
        stack = list(targets)
        while stack:
            sid = stack.pop()
            if sid in needed:
                continue
            needed.add(sid)
            for dep in self._stages[sid].get("dependencies", []):
                if dep not in needed:
                    stack.append(dep)

        ordered = sorted((self._stages[s] for s in needed), key=lambda x: x["order"])
        plan = OrchestrationPlan()
        produced = set(available)

        for st in ordered:
            sid = st["stage_id"]
            if sid in completed:
                produced.update(st.get("expected_outputs", []))
                continue
            if st.get("conditional"):
                ckey = st.get("condition_key")
                if ckey and not ctx.get(ckey, False):
                    plan.skipped_conditional.append(sid)
                    continue
            for sk in st.get("skills", []):
                self.assert_not_retired(sk)
            missing = [inp for inp in st.get("required_inputs", []) if inp not in produced]
            if missing:
                plan.blocked_missing_inputs[sid] = missing
            plan.stages.append(
                PlannedStage(
                    stage_id=sid,
                    name=st["name"],
                    order=st["order"],
                    skills=list(st.get("skills", [])),
                    python_modules=list(st.get("python_modules", [])),
                    missing_inputs=missing,
                    implementation_gaps=list(st.get("implementation_gaps", [])),
                )
            )
            produced.update(st.get("expected_outputs", []))

        return plan

    def audit_correspondence(self) -> dict[str, Any]:
        """Verify Skill directories exist on disk and mapped Python modules are importable."""
        missing_skill_dirs: list[str] = []
        missing_python_modules: list[str] = []
        documented_gaps: dict[str, list[str]] = {}
        checked_skills: set[str] = set()
        checked_modules: set[str] = set()

        for st in self.registry["stages"]:
            for sk in st.get("skills", []):
                self.assert_not_retired(sk)
                if sk not in checked_skills:
                    checked_skills.add(sk)
                    if not (self.skills_dir / sk).is_dir():
                        missing_skill_dirs.append(sk)
            for mod in st.get("python_modules", []):
                if mod not in checked_modules:
                    checked_modules.add(mod)
                    try:
                        importlib.import_module(mod)
                    except Exception:
                        missing_python_modules.append(mod)
            if st.get("implementation_gaps"):
                documented_gaps[st["stage_id"]] = list(st["implementation_gaps"])

        return {
            "ok": not missing_skill_dirs and not missing_python_modules,
            "active_skills_count": len(checked_skills),
            "python_modules_count": len(checked_modules),
            "missing_skill_dirs": sorted(missing_skill_dirs),
            "missing_python_modules": sorted(missing_python_modules),
            "documented_gaps": documented_gaps,
        }

    def record_execution(
        self,
        ledger_path: Path,
        *,
        stage_id: str,
        skills_used: list[str],
        inputs: list[str],
        outputs: list[str],
        status: str,
        notes: str = "",
    ) -> dict[str, Any]:
        if stage_id not in self._stages:
            raise ContractError(f"Unknown stage_id: {stage_id!r}")
        for sk in skills_used:
            self.assert_not_retired(sk)
        records: list[dict[str, Any]] = []
        if ledger_path.exists():
            records = json.loads(ledger_path.read_text(encoding="utf-8")).get("executions", [])
        entry = {
            "ts": datetime.datetime.now(UTC).isoformat(),
            "stage_id": stage_id,
            "skills_used": list(skills_used),
            "inputs": list(inputs),
            "outputs": list(outputs),
            "status": status,
            "notes": notes,
        }
        records.append(entry)
        payload = {"schema_version": "skill_execution_record/1", "executions": records}
        write_json_atomic(ledger_path, payload)
        return entry
