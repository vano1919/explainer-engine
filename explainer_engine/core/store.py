"""Checkpointed job storage: one directory per job, one atomic JSON file per finished stage.

Layout: ``<job_dir>/artifacts/NN_<stage key>.json`` + ``<job_dir>/state.json``. A failed job keeps everything it
produced, so a rerun resumes after the last saved stage. The stage list is passed in (the pipeline declares it);
nothing here knows which stages exist.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/artifacts.py
# changed: stage registry passed in (no hard-coded ARTIFACT_NAMES), every write atomic, NEEDS_REVIEW status,
# run naming moved to core/jobs.py

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
