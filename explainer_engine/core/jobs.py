# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/jobs.py`
# Target Module : explainer_engine/core/jobs.py
# Target Classes/Symbols : def job_seq(), def next_job_dir(), def _published_jobs(), def protected_reason(), def clean_jobs()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
