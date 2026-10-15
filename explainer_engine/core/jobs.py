"""Job-directory naming and cleanup.

Layout: ``<jobs>/<slug>/job-<NNN>_<YYYY-mm-dd_HHMM>[_from-<MMM>-redo<K>]``
- NNN is a per-episode sequence, so "job 7" means the same thing in logs, in conversation and on disk;
- the suffix records where a resumed job came from.

Cleanup keeps the newest ``keep`` jobs of an episode and deletes the rest, except protected jobs: the current one,
jobs with a ``KEEP`` file, jobs recorded as published under ``channel/``, jobs holding a final render or a review
bundle, and jobs active in the last 10 minutes. Cleanup only ever deletes job directories (known-safe artifacts).
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/housekeeping.py
# changed: run- -> job-, protects final.mp4 / review_bundle / NEEDS_REVIEW, legacy adoption removed

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_JOB = re.compile(r"^job-(\d{3,})_")
_ACTIVE_SECONDS = 600
_PROTECT_FILES = ("KEEP", "final.mp4", "review_bundle", "audio.wav")


def job_seq(path: Path) -> int | None:
    match = _JOB.match(Path(path).name)
    return int(match.group(1)) if match else None


def next_job_dir(jobs_root: Path, slug: str, *, resume_from: Path | None = None, redo_from: int | None = None,
                 now: datetime | None = None) -> Path:
    episode_dir = Path(jobs_root) / slug
    seqs = [s for s in (job_seq(p) for p in episode_dir.glob("job-*")) if s is not None] if episode_dir.is_dir() else []
    seq = max(seqs, default=0) + 1
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M")
    name = f"job-{seq:03d}_{stamp}"
    if resume_from is not None:
        source = job_seq(Path(resume_from))
        name += f"_from-{source:03d}" if source is not None else "_from-unknown"
        if redo_from:
            name += f"-redo{redo_from}"
    return episode_dir / name


def _published_jobs(channel_dir: Path) -> set[str]:
    names = set()
    for record in Path(channel_dir).glob("*/video.json"):
        try:
            names.add(Path(json.loads(record.read_text(encoding="utf-8")).get("job_dir") or "").name)
        except (OSError, ValueError):
            continue
    return names


def protected_reason(job_dir: Path, published: set[str]) -> str:
    log = job_dir / "job.log"
    if log.exists() and time.time() - log.stat().st_mtime < _ACTIVE_SECONDS:
        return "active (log written in the last 10 minutes)"
    state_path = job_dir / "state.json"
    if state_path.exists():
        try:
            status = json.loads(state_path.read_text(encoding="utf-8")).get("status")
        except ValueError:
            status = None
        if status == "NEEDS_REVIEW":
            return "waiting for review"
        if status == "RUNNING" and log.exists() and time.time() - log.stat().st_mtime < 3 * _ACTIVE_SECONDS:
            return "still RUNNING"
    for name in _PROTECT_FILES:
        if (job_dir / name).exists():
            return f"has {name}"
    if job_dir.name in published:
        return "published (channel/)"
    return ""


def clean_jobs(jobs_root: Path, slug: str, *, keep: int = 3, current: Path | None = None,
               channel_dir: Path = Path("channel"), dry_run: bool = False) -> list[Path]:
    """Delete all but the newest ``keep`` jobs of one episode (protected jobs are never deleted and do not count
    toward ``keep``). Returns what was (or would be) removed."""
    episode_dir = Path(jobs_root) / slug
    if keep <= 0 or not episode_dir.is_dir():
        return []
    published = _published_jobs(channel_dir)
    jobs = sorted((p for p in episode_dir.glob("job-*") if p.is_dir() and job_seq(p) is not None), key=job_seq,
                  reverse=True)
    removable = []
    kept = 0
    for job in jobs:
        if current is not None and job.resolve() == Path(current).resolve():
            continue
        reason = protected_reason(job, published)
        if reason:
            logger.info("clean: keeping %s (%s)", job.name, reason)
            continue
        if kept < keep - (1 if current is not None else 0):
            kept += 1
            continue
        removable.append(job)
    for job in removable:
        logger.info("clean: %s %s", "would remove" if dry_run else "removing", job)
        if not dry_run:
            shutil.rmtree(job, ignore_errors=False)
    return removable
