"""Canonical Operational Skill Orchestrator for Explainer Engine.

Coordinates and executes active Skills across production stages with:
- Trigger-based stage selection (`select_by_triggers`)
- Dependency resolution (topological order, no duplicate execution)
- Conditional stage selection (no hardcoded 10/30/60 visual quota)
- Retired-skill refusal (prevents reviving Qwen/LoRA/Unreal routes)
- Fail-closed readiness check on unresolved `implementation_gaps`
- Real stage execution (`run_stage` / `run_plan`) wired to Python entrypoints
- Persistent skill participation ledger (`skill_execution_record.json`)
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib
import json
import uuid

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = Path(__file__).resolve().parent / "skill_registry.json"
SKILLS_DIR = ROOT / ".claude" / "skills"
UTC = datetime.timezone.utc

StageExecutor = Callable[[dict[str, Any]], dict[str, Any]]


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
    blocked_implementation_gaps: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return not self.blocked_missing_inputs and not self.blocked_implementation_gaps

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "stages": [asdict(s) for s in self.stages],
            "skipped_conditional": list(self.skipped_conditional),
            "blocked_missing_inputs": dict(self.blocked_missing_inputs),
            "blocked_implementation_gaps": dict(self.blocked_implementation_gaps),
        }


def load_registry(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_REGISTRY
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != "skill_registry/1":
        raise ContractError(f"Unsupported skill registry schema: {data.get('schema_version')!r}")
    return data


def _exec_blender_previs(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a blender_scene/1 spec; emit PASS only when real rendered reference frames exist on disk."""
    from explainer_engine.lab import scene_spec as SS

    spec_path = payload.get("scene_spec_path")
    if spec_path:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    else:
        spec = payload.get("scene_spec")
    if not isinstance(spec, dict):
        raise ContractError("S4_blender_previs requires scene_spec or scene_spec_path")
    SS.check_schema(spec)
    results = SS.validate_spec(spec)
    errors = [r for r in results if isinstance(r, dict) and str(r.get("status", "")).upper() == "FAIL"]
    if errors:
        raise ContractError(f"Blender previs spec validation failed: {errors}")
    rendered = [Path(p) for p in (payload.get("rendered_frames") or [])]
    if rendered and all(p.is_file() for p in rendered):
        return {
            "status": "PASS",
            "outputs": ["blender_reference_frames"],
            "scene_id": spec.get("scene_id", "unknown"),
            "rendered_count": len(rendered),
        }
    return {
        "status": "VALIDATED",
        "outputs": [],
        "scene_id": spec.get("scene_id", "unknown"),
        "notes": "Spec validated only; invoke explainer_engine.lab.scene_render to produce frames before PASS",
    }


def _exec_gemini_images(payload: dict[str, Any]) -> dict[str, Any]:
    """Record Gemini reference-image provenance manifest; emit PASS only when real decodable images & manifest exist."""
    from PIL import Image, UnidentifiedImageError

    out_path = payload.get("provenance_path")
    images = list(payload.get("images") or [])
    verified_records: list[dict[str, Any]] = []
    for raw_p in images:
        if not isinstance(raw_p, (str, Path)):
            continue
        p = Path(raw_p)
        if not p.is_file():
            raise ContractError(f"Reference image does not exist: {p}")
        try:
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im2:
                width, height = im2.size
        except (OSError, UnidentifiedImageError) as exc:
            raise ContractError(f"Reference image failed decode verification ({p}): {exc}") from exc
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        verified_records.append({"path": str(p), "width": width, "height": height, "sha256": digest})
    manifest = {
        "schema_version": "image_provenance/1",
        "mode": payload.get("generation_mode", "interactive_gemini_chat"),
        "images": [r["path"] for r in verified_records],
        "verified_assets": verified_records,
        "ts": datetime.datetime.now(UTC).isoformat(),
    }
    if out_path and verified_records:
        write_json_atomic(Path(out_path), manifest)
        return {
            "status": "PASS",
            "outputs": ["scene_images", "image_provenance"],
            "count": len(verified_records),
        }
    return {
        "status": "VALIDATED",
        "outputs": [],
        "count": len(verified_records),
        "notes": "No verified on-disk images + provenance_path supplied; cannot mark PASS",
    }


def _exec_ltx_video(payload: dict[str, Any]) -> dict[str, Any]:
    """Select the LTX worker route (MODAL1); emit PASS only when an ingested video_clip_record/1 exists on disk."""
    from explainer_engine.episode.router import select_ltx_worker

    shot = payload.get("shot") or {}
    worker = select_ltx_worker(shot)
    rec_path = payload.get("clip_record_path")
    if rec_path and Path(rec_path).is_file():
        rec = json.loads(Path(rec_path).read_text(encoding="utf-8"))
        rec_status = str(rec.get("status") or "").upper()
        if rec.get("schema") == "video_clip_record/1" and rec_status == "PASS":
            clip_ref = rec.get("clip_path") or rec.get("path") or rec.get("video_path")
            if clip_ref:
                clip_p = Path(clip_ref)
                if not clip_p.is_file() or clip_p.stat().st_size == 0:
                    raise ContractError(f"video_clip_record/1 clip file missing or empty: {clip_p}")
                expected_sha = rec.get("sha256")
                if expected_sha:
                    actual_sha = hashlib.sha256(clip_p.read_bytes()).hexdigest()
                    if actual_sha != expected_sha:
                        raise ContractError(
                            f"video_clip_record/1 SHA-256 mismatch for {clip_p}: expected {expected_sha}, got {actual_sha}"
                        )
            return {"status": "PASS", "outputs": ["ltx_video_clips"], "worker": worker, "clip_record_path": str(rec_path)}
    return {
        "status": "PLANNED",
        "outputs": [],
        "worker": worker,
        "notes": "Worker selected only; run approved Modal LTX launch + videolane.ingest before PASS",
    }


def _exec_perceptual_qa(payload: dict[str, Any]) -> dict[str, Any]:
    """Invoke the real perceptual_qa module on the target media clip."""
    from explainer_engine.qa import perceptual_qa as PQA

    video_path = payload.get("video_path")
    if not video_path:
        raise ContractError("S10_qa_and_delivery requires video_path")
    report = PQA.evaluate_clip_perceptual(
        Path(video_path),
        out_dir=Path(payload.get("qa_out_dir", Path(video_path).parent / "qa")),
        use_gemini=bool(payload.get("use_gemini", False)),
        reviewer_model=str(payload.get("reviewer_model", PQA.DEFAULT_GEMINI_QA_MODEL)),
    )
    return {"status": report["verdict"], "outputs": ["technical_qa_report", "perceptual_qa_report"], "report": report}


class SkillOrchestrator:
    """Selects, validates, executes, and tracks Skills across pipeline stages."""

    def __init__(self, registry_path: Path | None = None, skills_dir: Path | None = None) -> None:
        self.registry = load_registry(registry_path)
        self.skills_dir = skills_dir or SKILLS_DIR
        self._stages: dict[str, dict[str, Any]] = {s["stage_id"]: s for s in self.registry["stages"]}
        self._retired: set[str] = set(self.registry.get("retired_skills", []))
        self._executors: dict[str, StageExecutor] = {
            "S4_blender_previs": _exec_blender_previs,
            "S5_gemini_images": _exec_gemini_images,
            "S6_ltx_video": _exec_ltx_video,
            "S10_qa_and_delivery": _exec_perceptual_qa,
        }

    def register_executor(self, stage_id: str, fn: StageExecutor) -> None:
        if stage_id not in self._stages:
            raise ContractError(f"Unknown stage_id: {stage_id!r}")
        self._executors[stage_id] = fn

    def assert_not_retired(self, skill_name: str) -> None:
        if skill_name in self._retired:
            raise ContractError(f"Skill {skill_name!r} is retired and cannot be activated in active workflows")

    def select_by_triggers(
        self,
        triggers: list[str] | set[str],
        *,
        context: dict[str, Any] | None = None,
        available_artifacts: set[str] | list[str] | None = None,
        completed_stages: set[str] | list[str] | None = None,
        allow_gaps: bool = False,
    ) -> OrchestrationPlan:
        """Select all stages matching any active trigger string and expand their dependencies."""
        trig_set = set(triggers)
        matched = [
            st["stage_id"]
            for st in self.registry["stages"]
            if trig_set.intersection(st.get("triggers", []))
        ]
        if not matched:
            raise ContractError(f"No pipeline stages matched triggers: {sorted(trig_set)}")
        # Automatically enable conditional stages explicitly matched by a trigger
        ctx = dict(context or {})
        for sid in matched:
            ckey = self._stages[sid].get("condition_key")
            if ckey and ckey not in ctx:
                ctx[ckey] = True
        return self.select_plan(
            requested_stages=matched,
            context=ctx,
            available_artifacts=available_artifacts,
            completed_stages=completed_stages,
            allow_gaps=allow_gaps,
        )

    def select_plan(
        self,
        requested_stages: list[str] | None = None,
        *,
        context: dict[str, Any] | None = None,
        available_artifacts: set[str] | list[str] | None = None,
        completed_stages: set[str] | list[str] | None = None,
        allow_gaps: bool = False,
    ) -> OrchestrationPlan:
        ctx = dict(context or {})
        available = set(available_artifacts or ())
        completed = set(completed_stages or ())

        targets = list(requested_stages) if requested_stages else list(self._stages.keys())
        for sid in targets:
            if sid not in self._stages:
                raise ContractError(f"Unknown stage_id: {sid!r}")

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
            gaps = list(st.get("implementation_gaps", []))
            if gaps and not allow_gaps:
                plan.blocked_implementation_gaps[sid] = gaps
            plan.stages.append(
                PlannedStage(
                    stage_id=sid,
                    name=st["name"],
                    order=st["order"],
                    skills=list(st.get("skills", [])),
                    python_modules=list(st.get("python_modules", [])),
                    missing_inputs=missing,
                    implementation_gaps=gaps,
                )
            )
            produced.update(st.get("expected_outputs", []))

        return plan

    def run_stage(
        self,
        stage_id: str,
        payload: dict[str, Any],
        *,
        ledger_path: Path | None = None,
        allow_gaps: bool = False,
    ) -> dict[str, Any]:
        """Execute a single stage through its registered Python executor and persist the ledger entry."""
        if stage_id not in self._stages:
            raise ContractError(f"Unknown stage_id: {stage_id!r}")
        st = self._stages[stage_id]
        gaps = list(st.get("implementation_gaps", []))
        if gaps and not allow_gaps:
            raise ContractError(f"Stage {stage_id} blocked by unresolved implementation_gaps: {gaps}")
        for sk in st.get("skills", []):
            self.assert_not_retired(sk)
        if stage_id not in self._executors:
            raise ContractError(f"No executable Python handler registered for stage {stage_id!r}")
        res = self._executors[stage_id](payload)
        raw_status = str(res.get("status") or "NOT_RUN").upper()
        actual_outputs = list(res.get("outputs") or [])
        if ledger_path is not None:
            self.record_execution(
                ledger_path,
                stage_id=stage_id,
                skills_used=list(st.get("skills", [])),
                inputs=list(st.get("required_inputs", [])),
                outputs=actual_outputs,
                status=raw_status,
                notes=str(res.get("notes", "")),
            )
        return res

    def _plan_fingerprint(self, plan: OrchestrationPlan, stage_payloads: dict[str, dict[str, Any]]) -> str:
        blob = {
            "stages": [s.stage_id for s in plan.stages],
            "registry_version": self.registry.get("schema_version"),
            "registry_stages": {s.stage_id: self._stages[s.stage_id] for s in plan.stages},
            "payloads": {s.stage_id: stage_payloads.get(s.stage_id, {}) for s in plan.stages},
        }
        return hashlib.sha256(json.dumps(blob, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def run_plan(
        self,
        plan: OrchestrationPlan,
        stage_payloads: dict[str, dict[str, Any]],
        *,
        ledger_path: Path | None = None,
        checkpoint_path: Path | None = None,
        allow_gaps: bool = False,
    ) -> dict[str, Any]:
        """Execute all ready stages in topological order with hash-bound crash-safe checkpoint persistence."""
        if not plan.ready and not (allow_gaps and not plan.blocked_missing_inputs):
            raise ContractError(
                f"Plan is not ready: missing_inputs={plan.blocked_missing_inputs}, "
                f"implementation_gaps={plan.blocked_implementation_gaps}"
            )
        for st in plan.stages:
            st_meta = self._stages[st.stage_id]
            if st_meta.get("execution_category") == "not_implemented":
                raise ContractError(f"Stage {st.stage_id!r} is marked not_implemented and cannot be executed")
            if st.stage_id not in self._executors:
                raise ContractError(f"Pre-run refusal: no executable Python handler registered for stage {st.stage_id!r}")
        plan_hash = self._plan_fingerprint(plan, stage_payloads)
        done_stages: set[str] = set()
        results: dict[str, Any] = {}
        if checkpoint_path and checkpoint_path.exists():
            cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if cp.get("plan_hash") == plan_hash:
                done_stages = set(cp.get("completed_stages", []))
                results = dict(cp.get("results", {}))

        status_rank = {"FAIL": 4, "ERROR": 4, "NEEDS_REVIEW": 3, "REVIEW": 3, "NOT_RUN": 2, "PLANNED": 1, "VALIDATED": 1, "PASS": 0}
        worst_status = "PASS"

        for st in plan.stages:
            if st.stage_id in done_stages:
                prev_st = str((results.get(st.stage_id) or {}).get("status", "PASS")).upper()
                if status_rank.get(prev_st, 3) > status_rank.get(worst_status, 0):
                    worst_status = prev_st
                continue
            res = self.run_stage(
                st.stage_id,
                stage_payloads.get(st.stage_id, {}),
                ledger_path=ledger_path,
                allow_gaps=allow_gaps,
            )
            results[st.stage_id] = res
            st_status = str(res.get("status") or "NOT_RUN").upper()
            if st_status != "PASS":
                halted_status = "FAIL" if st_status in ("FAIL", "ERROR") else (st_status if st_status in status_rank else "NEEDS_REVIEW")
                if checkpoint_path:
                    write_json_atomic(
                        checkpoint_path,
                        {
                            "plan_hash": plan_hash,
                            "completed_stages": sorted(done_stages),
                            "results": results,
                            "failed_stage": st.stage_id if halted_status == "FAIL" else None,
                            "halted_stage": st.stage_id,
                        },
                    )
                out_halt = {
                    "status": halted_status,
                    "halted_stage": st.stage_id,
                    "completed_stages": sorted(done_stages),
                    "results": results,
                }
                if halted_status == "FAIL":
                    out_halt["failed_stage"] = st.stage_id
                return out_halt
            done_stages.add(st.stage_id)
            if checkpoint_path:
                write_json_atomic(
                    checkpoint_path,
                    {"plan_hash": plan_hash, "completed_stages": sorted(done_stages), "results": results, "failed_stage": None},
                )

        return {"status": worst_status, "completed_stages": sorted(done_stages), "results": results}

    def audit_correspondence(self, *, allow_gaps: bool = False) -> dict[str, Any]:
        """Verify Skill directories exist, Python modules import, and fail closed on unresolved gaps."""
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

        gaps_ok = allow_gaps or not documented_gaps
        return {
            "ok": (not missing_skill_dirs) and (not missing_python_modules) and gaps_ok,
            "active_skills_count": len(checked_skills),
            "python_modules_count": len(checked_modules),
            "missing_skill_dirs": sorted(missing_skill_dirs),
            "missing_python_modules": sorted(missing_python_modules),
            "documented_gaps": documented_gaps,
            "registered_executors": sorted(self._executors.keys()),
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
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lf:
            if fcntl is not None:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                records: list[dict[str, Any]] = []
                if ledger_path.exists():
                    records = json.loads(ledger_path.read_text(encoding="utf-8")).get("executions", [])
                entry = {
                    "run_id": uuid.uuid4().hex[:12],
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
            finally:
                if fcntl is not None:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
