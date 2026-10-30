"""Checkpointed job storage: one directory per job, one atomic JSON file per finished stage.

Two records live here. ``JobStore``: the stage artifacts of one pipeline run (``artifacts/NN_<stage key>.json`` +
``state.json``). ``EpisodeJob``: the episode's lifecycle (``job_manifest.json``, docs/CONTRACTS.md, CN-03..CN-06).

Layout of a ``JobStore``: ``<job_dir>/artifacts/NN_<stage key>.json`` + ``<job_dir>/state.json``. A failed job keeps everything it
produced, so a rerun resumes after the last saved stage. The stage list is passed in (the pipeline declares it);
nothing here knows which stages exist.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/artifacts.py
# changed: stage registry passed in (no hard-coded ARTIFACT_NAMES), every write atomic, NEEDS_REVIEW status,
# run naming moved to core/jobs.py

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError

logger = logging.getLogger(__name__)

STATE_NAME = "state.json"
LOG_NAME = "job.log"
STATES = ("RUNNING", "COMPLETED", "FAILED", "NEEDS_REVIEW")


def replace_file(tmp: Path, path: Path, attempts: int = 20) -> None:
    """Atomic replace that tolerates a reader: on Windows os.replace fails with "Access is denied" while another
    process has the target open for a moment."""
    for attempt in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05)


def write_text_atomic(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    replace_file(tmp, path)  # a crash mid-write never leaves a torn file
    return path


def write_json_atomic(path: Path, payload: object) -> Path:
    return write_text_atomic(path, json.dumps(payload, indent=2, ensure_ascii=False))


@dataclass(frozen=True)
class Stage:
    number: int
    key: str
    title: str

    @property
    def file_name(self) -> str:
        return f"{self.number:02d}_{self.key}.json"


class JobStore:
    """Owns one job directory. ``stages`` is the pipeline's declared stage list."""

    def __init__(self, job_dir: Path, stages: list[Stage]) -> None:
        numbers = [s.number for s in stages]
        if len(set(numbers)) != len(numbers) or len({s.key for s in stages}) != len(stages):
            raise ValueError("stage numbers and keys must be unique")
        self.job_dir = Path(job_dir)
        self.artifacts_dir = self.job_dir / "artifacts"
        self.stages = {s.number: s for s in sorted(stages, key=lambda s: s.number)}

    def stage(self, number: int) -> Stage:
        if number not in self.stages:
            raise KeyError(f"unknown stage {number}")
        return self.stages[number]

    def has(self, number: int) -> bool:
        return (self.artifacts_dir / self.stage(number).file_name).exists()

    def completed_prefix(self) -> list[int]:
        """The stages saved without a gap from the first one: what a resume may reuse."""
        done = []
        for number in self.stages:
            if not self.has(number):
                break
            done.append(number)
        return done

    def save(self, number: int, payload: dict, *, quiet: bool = False) -> Path:
        """``quiet`` is for mid-stage progress checkpoints (no "done" line, state unchanged)."""
        stage = self.stage(number)
        path = write_json_atomic(self.artifacts_dir / stage.file_name, payload)
        if not quiet:
            logger.info("[%d/%d] %s done - %s", number, len(self.stages), stage.title, path.name)
            state = self.read_state()
            if state:  # only jobs started through set_state track progress
                done = sorted(set(state.get("completed_stages") or []) | {number})
                self.set_state(state.get("status") or "RUNNING", completed_stages=done)
        return path

    def load(self, number: int) -> dict:
        return json.loads((self.artifacts_dir / self.stage(number).file_name).read_text(encoding="utf-8"))

    def read_state(self) -> dict:
        path = self.job_dir / STATE_NAME
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def set_state(self, status: str, **fields: object) -> dict:
        """Merge-update state.json atomically: status, current_stage, completed_stages, error, cost ledger..."""
        if status not in STATES:
            raise ValueError(f"unknown job status {status!r}")
        state = self.read_state()
        now = datetime.now().isoformat(timespec="seconds")
        state.setdefault("started", now)
        state.update(fields)
        state["status"] = status
        state["updated"] = now
        write_json_atomic(self.job_dir / STATE_NAME, state)
        return state

    def write_output(self, name: str, payload: dict) -> Path:
        return write_json_atomic(self.job_dir / name, payload)

    def write_text(self, name: str, text: str) -> Path:
        return write_text_atomic(self.job_dir / name, text)


# --- the episode lifecycle (docs/CONTRACTS.md "The lifecycle", job_manifest/1) --------------------------------------------
MANIFEST = "job_manifest.json"
LIFECYCLE = ("CREATED", "RESEARCHED", "VARIANT_CHOSEN", "SCENARIO_APPROVED", "SCRIPT_APPROVED", "STORYBOARDED", "BUDGET_RESERVED",
             "SAMPLE_APPROVED", "AUDIO_TIMED", "ASSETS", "ASSEMBLED", "QA_PASSED", "REVIEW_APPROVED", "STAGED_UNLISTED",
             "PUBLISHED_PUBLIC")
TERMINAL = ("FAILED_PREFLIGHT", "FAILED_QA_ESCALATED", "ABORTED_SPEND_CAP", "CANCELLED_BY_CREATOR")
# the approval kinds that may open a gated state; a state not listed here is entered on the stage's own checks (machine)
GATES = {"RESEARCHED": {"machine"}, "VARIANT_CHOSEN": {"creator"}, "SCENARIO_APPROVED": {"creator"}, "SCRIPT_APPROVED": {"creator"},
         "STORYBOARDED": {"machine"}, "BUDGET_RESERVED": {"creator", "planner"}, "SAMPLE_APPROVED": {"creator"},
         "AUDIO_TIMED": {"machine"}, "ASSETS": {"machine"}, "ASSEMBLED": {"machine"}, "QA_PASSED": {"machine"},
         "REVIEW_APPROVED": {"creator"}, "STAGED_UNLISTED": {"machine"}, "PUBLISHED_PUBLIC": {"creator"}}


def _span(a: str, b: str) -> tuple[str, ...]:
    return LIFECYCLE[LIFECYCLE.index(a):LIFECYCLE.index(b) + 1]


# name -> (the states it may leave, the state it returns to)
BACK_PATHS = {
    "variant_changed": (("VARIANT_CHOSEN", "SCENARIO_APPROVED"), "RESEARCHED"),
    "scenario_changed": (_span("SCENARIO_APPROVED", "REVIEW_APPROVED"), "VARIANT_CHOSEN"),
    "words_changed": (_span("SCRIPT_APPROVED", "REVIEW_APPROVED"), "SCENARIO_APPROVED"),
    "storyboard_changed": (_span("STORYBOARDED", "QA_PASSED"), "SCRIPT_APPROVED"),
    "plan_changed": (("BUDGET_RESERVED",), "STORYBOARDED"),
    "retime": (("ASSETS", "ASSEMBLED", "QA_PASSED"), "AUDIO_TIMED"),
    "repair": (("ASSEMBLED", "QA_PASSED"), "ASSETS"),
    "post_review_fix": (("REVIEW_APPROVED", "STAGED_UNLISTED"), "ASSETS"),
}
CLEARS_RESERVATION = {"words_changed", "scenario_changed", "variant_changed", "storyboard_changed", "plan_changed"}
CREATOR_ONLY_BACK = {"post_review_fix"}
_JOB_DIR = re.compile(r"(?:^|/)jobs/(?!_)[^/]+/job-[^/]+")
ROOT = Path(__file__).resolve().parents[2]


def shot_cache_root() -> Path:
    """The shot cache's folder (core/shot_cache.py): a cached render may be recorded as an artifact of a job."""
    import os
    return Path(os.environ.get("EXPLAINER_SHOT_CACHE") or ROOT / "jobs" / "_cache" / "shots")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    return contracts.sha256_file(path)


class EpisodeJob:
    """One episode's lifecycle in ``<job_dir>/job_manifest.json``. Every change validates the whole manifest first and
    writes it atomically; a refused move raises ContractError and leaves the file as it was (CN-03)."""

    def __init__(self, job_dir: Path, manifest: dict) -> None:
        self.job_dir = Path(job_dir)
        self.manifest = manifest

    # --- opening ------------------------------------------------------------------------------------------------------
    @classmethod
    def _new(cls, job_dir: Path, *, job_id: str, episode_slug: str, ledger: str, fps: int, state: str, reason: str, path: str,
             approvals: dict, dossier_sha256: str | None, budget_reservation_id: str | None) -> "EpisodeJob":
        now = _now()
        manifest = {"schema": "job_manifest/1", "job_id": job_id, "episode_slug": episode_slug, "created": now, "fps": fps,
                    "state": state, "state_since": now,
                    "history": [{"from": None, "to": state, "at": now, "path": path, "reason": reason,
                                 "approval": approvals.get(state)}],
                    "source_dossier_sha256": dossier_sha256, "ledger": ledger, "budget_reservation_id": budget_reservation_id,
                    "approvals": dict(approvals), "artifacts": {}, "distribution_packages": [], "reopen_to": None}
        return cls(job_dir, manifest)

    @classmethod
    def create(cls, job_dir: Path | str, *, job_id: str, episode_slug: str, ledger: str, fps: int,
               reason: str = "job created") -> "EpisodeJob":
        """A new episode job: always CREATED. Any later state is reached by ``move`` (or, for a job that already exists, ``adopt``)."""
        job_dir = Path(job_dir)
        if (job_dir / MANIFEST).exists():
            raise ContractError(f"{job_dir / MANIFEST} exists: open it, never create over it")
        job = cls._new(job_dir, job_id=job_id, episode_slug=episode_slug, ledger=ledger, fps=fps, state="CREATED", reason=reason,
                       path="forward", approvals={}, dossier_sha256=None, budget_reservation_id=None)
        job._save()
        return job

    @classmethod
    def adopt(cls, job_dir: Path | str, *, state: str, reason: str, approvals: dict[str, dict], dossier: Path | str | None = None,
              reservation_id: str | None = None, **create_args) -> "EpisodeJob":
        """An existing episode folder gets its manifest at a state its owner states (history path ``adopted``). Adopting is no way
        round the gates (CN-04, CN-06): ``approvals`` holds the right approval of EVERY gated state from the first step up to
        ``state``, each bound to a sha256 where a person approved; the research dossier file is named and hashed (CN-05); a state
        past BUDGET_RESERVED names a reservation the ledger holds. A terminal state is never adopted (nothing could reopen it)."""
        job_dir = Path(job_dir)
        if state not in LIFECYCLE[:-1]:
            raise ContractError(f"cannot adopt into {state!r}: adopt a state of the forward path before the public click (CN-06)")
        if (job_dir / MANIFEST).exists():
            raise ContractError(f"{job_dir / MANIFEST} exists: open it, never adopt over it")
        reached = LIFECYCLE[1:LIFECYCLE.index(state) + 1]
        for s in reached:
            cls._check_approval(GATES[s], approvals.get(s), f"adopt into {state}: the gate {s}", bind=True)
        extra = sorted(set(approvals) - set(reached))
        if extra:
            raise ContractError(f"adopt into {state}: approvals for states not reached: {extra}")
        digest = None
        if reached:
            if dossier is None or not Path(dossier).exists():
                raise ContractError(f"adopt into {state} names the research dossier file (dossier=)")
            digest = _sha256_file(Path(dossier))
        job = cls._new(job_dir, state=state, reason=reason, path="adopted", approvals=approvals, dossier_sha256=digest,
                       budget_reservation_id=reservation_id if "BUDGET_RESERVED" in reached else None, **create_args)
        if "BUDGET_RESERVED" in reached and not (reservation_id and job._reserved(reservation_id)):
            raise ContractError(f"adopt into {state} names a reservation the ledger holds: {reservation_id!r}")
        job._save()
        return job

    @classmethod
    def open(cls, job_dir: Path | str) -> "EpisodeJob":
        job_dir = Path(job_dir)
        manifest = json.loads((job_dir / MANIFEST).read_text(encoding="utf-8"))
        contracts.validate(manifest)
        return cls(job_dir, manifest)

    @property
    def state(self) -> str:
        return self.manifest["state"]

    # --- writing ------------------------------------------------------------------------------------------------------
    def _save(self, manifest: dict | None = None) -> None:
        manifest = self.manifest if manifest is None else manifest
        contracts.validate(manifest)
        write_json_atomic(self.job_dir / MANIFEST, manifest)
        self.manifest = manifest

    def _row(self, m: dict, to: str, path: str, reason: str, approval: dict | None) -> None:
        now = _now()
        m["history"].append({"from": m["state"], "to": to, "at": now, "path": path, "reason": reason, "approval": approval})
        m["state"], m["state_since"] = to, now

    @staticmethod
    def _check_approval(kind_needed: set[str], approval: dict | None, where: str, bind: bool = False) -> None:
        """``bind``: a person's approval of a gate names the sha256 of what was approved (CN-04)."""
        if approval is None:
            raise ContractError(f"{where} needs an approval of kind {sorted(kind_needed)}")
        if approval.get("kind") not in kind_needed:
            raise ContractError(f"{where} needs an approval of kind {sorted(kind_needed)}, not {approval.get('kind')!r}")
        if approval["kind"] in ("creator", "planner") and not (approval.get("by") and approval.get("ref")):
            raise ContractError(f"{where}: a {approval['kind']} approval says who (by) and where (ref)")
        if bind and approval["kind"] in ("creator", "planner") and not approval.get("sha256"):
            raise ContractError(f"{where}: a {approval['kind']} approval binds the sha256 of what was approved (CN-04)")

    def _reserved(self, reservation_id: str) -> bool:
        path = self.job_dir / self.manifest["ledger"]
        if not path.exists():
            return False
        return reservation_id in json.loads(path.read_text(encoding="utf-8")).get("reserved", {})

    def move(self, to: str, *, reason: str, approval: dict | None = None, dossier: Path | str | None = None,
             reservation_id: str | None = None) -> None:
        """The next forward state, and only that one (CN-03). A gated state needs its approval (CN-04); RESEARCHED fixes the
        dossier hash (CN-05); BUDGET_RESERVED names an item the ledger holds; PUBLISHED_PUBLIC is the creator's own click (CN-06)."""
        m = json.loads(json.dumps(self.manifest))
        cur = m["state"]
        if cur not in LIFECYCLE or to not in LIFECYCLE or LIFECYCLE.index(to) != LIFECYCLE.index(cur) + 1:
            raise ContractError(f"{cur} -> {to} is not the next step of the lifecycle")
        self._check_approval(GATES[to], approval, to, bind=True)
        if to == "RESEARCHED":
            if dossier is None:
                raise ContractError("RESEARCHED fixes the research dossier: pass dossier=<file>")
            digest = _sha256_file(Path(dossier))
            if m["source_dossier_sha256"] not in (None, digest):
                raise ContractError("the dossier is already fixed for this job; another dossier is another job (CN-05)")
            m["source_dossier_sha256"] = digest
        if to == "BUDGET_RESERVED":
            if not reservation_id or not self._reserved(reservation_id):
                raise ContractError(f"BUDGET_RESERVED needs a reservation the ledger holds ({m['ledger']}): {reservation_id!r}")
            m["budget_reservation_id"] = reservation_id
        m["approvals"][to] = approval
        self._row(m, to, "forward", reason, approval)
        self._save(m)

    def back(self, path: str, *, reason: str, approval: dict | None = None) -> None:
        """A named way back (CN-03); anything else is refused. The creator's own word is needed after approval #2."""
        if path not in BACK_PATHS:
            raise ContractError(f"{path!r} is not a named back path: {sorted(BACK_PATHS)}")
        sources, to = BACK_PATHS[path]
        m = json.loads(json.dumps(self.manifest))
        if m["state"] not in sources:
            raise ContractError(f"back path {path} leaves {list(sources)}, not {m['state']}")
        if path in CREATOR_ONLY_BACK:
            self._check_approval({"creator"}, approval, path)
        if path in CLEARS_RESERVATION:
            m["budget_reservation_id"] = None
        for state in LIFECYCLE[LIFECYCLE.index(to) + 1:]:  # what was approved beyond the return point is approved again
            m["approvals"].pop(state, None)
        self._row(m, to, path, reason, approval)
        self._save(m)

    def abort(self, terminal: str, *, reason: str) -> None:
        if terminal not in TERMINAL:
            raise ContractError(f"{terminal!r} is not a terminal state: {TERMINAL}")
        m = json.loads(json.dumps(self.manifest))
        if m["state"] not in LIFECYCLE[:-1]:
            raise ContractError(f"{m['state']} cannot be aborted")
        m["reopen_to"] = m["state"]
        self._row(m, terminal, "abort", reason, None)
        self._save(m)

    def reopen(self, *, reason: str, approval: dict) -> None:
        """Leave a terminal state, back to where it was left; only the creator's word does it."""
        m = json.loads(json.dumps(self.manifest))
        if m["state"] not in TERMINAL:
            raise ContractError(f"{m['state']} is not a terminal state")
        self._check_approval({"creator"}, approval, "reopen")
        to = m["reopen_to"]
        m["reopen_to"] = None
        self._row(m, to, "reopen", reason, approval)
        self._save(m)

    # --- artifacts (CN-05: nothing crosses from another job or another dossier) ----------------------------------------------
    def record_artifact(self, key: str, path: Path | str, schema: str | None = None) -> dict:
        path = Path(path)
        resolved = (path if path.is_absolute() else self.job_dir / path).resolve()
        job_root = self.job_dir.resolve()
        if job_root not in resolved.parents and resolved != job_root:
            inside_job = _JOB_DIR.search(resolved.as_posix())
            if inside_job:
                raise ContractError(f"{resolved} is inside another job's folder: nothing crosses between jobs (CN-05)")
            outside = [(ROOT / "assets").resolve(), shot_cache_root().resolve()]  # the asset library and the shot cache
            if not any(o in resolved.parents for o in outside):
                raise ContractError(f"{resolved} is neither in this job, the asset library nor the shot cache (CN-05)")
        if not resolved.exists():
            raise ContractError(f"{resolved} does not exist")
        m = json.loads(json.dumps(self.manifest))
        try:
            rel = resolved.relative_to(job_root).as_posix()
        except ValueError:
            rel = resolved.as_posix()
        row = {"path": rel, "sha256": _sha256_file(resolved), "schema": schema, "dossier_sha256": m["source_dossier_sha256"]}
        m["artifacts"][key] = row
        self._save(m)
        return row

    def check_artifact(self, key: str) -> None:
        row = self.manifest["artifacts"].get(key)
        if row is None:
            raise ContractError(f"no artifact {key!r} recorded")
        if row["dossier_sha256"] != self.manifest["source_dossier_sha256"]:
            raise ContractError(f"{key} was made under another research dossier (CN-05)")
        path = Path(row["path"])
        path = path if path.is_absolute() else self.job_dir / path
        if not path.exists() or _sha256_file(path) != row["sha256"]:
            raise ContractError(f"{key} changed or vanished since it was recorded (CN-05)")
