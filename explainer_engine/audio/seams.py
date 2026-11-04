# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/seams.py`
# Target Module : explainer_engine/audio/seams.py
# Target Classes/Symbols : def lufs(), def duration(), def plan(), def findings(), def chain(), def main()
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

"""Seams between read chunks (ED-01): the chunks of one read come back at different loudness (Episode 1: -33.5 to -27.9 LUFS,
a 5.6 dB spread that showed as jumps at the joins, worst in Day 1). Every chunk is brought to the median gated loudness
before the join and gets a short fade at both edges inside its silence, so a join adds no click and no word moves.
Needs ffmpeg (loudness measure, gain, fades).

BP-59 (the gate): after levelling the chunks stay within ``chunk_spread_db_max`` of each other and no join steps more than
``join_step_lu_max``; a chunk that would need more than ``MAX_GAIN_DB`` of correction is a finding, never a silent boost.

    python -m explainer_engine.audio.seams chunk1.mp3 chunk2.mp3 ...    # the plan as JSON; exit 1 on a FAIL
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

EDGE_FADE = 0.03  # seconds of fade at each chunk edge (inside the silence the voice leaves there)
MAX_SPREAD_DB = float(SR.T("BP-59", "chunk_spread_db_max"))  # ED-01 / BP-59: chunk loudness spread allowed after levelling
JOIN_STEP_LU_MAX = float(SR.T("BP-59", "join_step_lu_max"))  # BP-59: no join steps more than this
MAX_GAIN_DB = 6.0  # the largest correction applied; a chunk needing more is reported (BP-59), never boosted further


def lufs(path: Path) -> float:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", err)
    if not m:
        raise RuntimeError(f"no loudness for {path}")
    return float(m[-1])


def duration(path: Path) -> float:
    """Seconds as the decoder yields them: the join (and every offset ``words`` lays on it) uses decoded samples. ffprobe's
    container duration of an MP3 counts the encoder delay and padding (~25 ms a file), so 22 spliced takes drifted the
    word timings 0.5-0.7 s late by the end of the titans read (2026-10-21)."""
    if Path(path).suffix.lower() == ".wav":
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                              str(path)], capture_output=True, text=True, check=True).stdout
        return float(out.strip())
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return len(raw) / 2 / 48000


def plan(paths: list[Path]) -> dict:
    """Per chunk: measured loudness, the gain that brings it to the median, and the report of the spread."""
    loud = [lufs(p) for p in paths]
    target = statistics.median(loud)
    gains = [max(-MAX_GAIN_DB, min(MAX_GAIN_DB, target - x)) for x in loud]
    after = [x + g for x, g in zip(loud, gains)]
    rep = {"target_lufs": round(target, 2), "before": [round(x, 2) for x in loud], "gains_db": [round(g, 2) for g in gains],
           "spread_before_db": round(max(loud) - min(loud), 2), "spread_after_db": round(max(after) - min(after), 2)}
    rep["findings"] = findings(rep, paths)
    return rep


def findings(rep: dict, paths: list[Path] | None = None) -> list[dict]:
    """BP-59 on a plan: the spread after levelling, each join's step, and any chunk the clamp could not bring to target."""
    sev = SR.rule("BP-59").get("severity", "REVIEW")
    out = []
    names = [Path(p).name for p in paths] if paths else [f"chunk {k}" for k in range(len(rep["before"]))]
    after = [b + g for b, g in zip(rep["before"], rep["gains_db"])]
    if rep["spread_after_db"] > MAX_SPREAD_DB:
        out.append({"rule": "BP-59", "severity": sev, "where": "chunks",
                    "detail": f"chunk loudness spread {rep['spread_after_db']} dB after levelling (at most {MAX_SPREAD_DB:g})"})
    for k in range(1, len(after)):
        step = abs(after[k] - after[k - 1])
        if step > JOIN_STEP_LU_MAX:
            out.append({"rule": "BP-59", "severity": sev, "where": f"{names[k - 1]} -> {names[k]}",
                        "detail": f"join steps {step:.2f} LU (at most {JOIN_STEP_LU_MAX:g}): re-read or re-level the chunk"})
    for k, (b, g) in enumerate(zip(rep["before"], rep["gains_db"])):
        if abs(rep["target_lufs"] - b) > MAX_GAIN_DB + 1e-6:
            out.append({"rule": "BP-59", "severity": sev, "where": names[k],
                        "detail": f"{b} LUFS needs {rep['target_lufs'] - b:+.1f} dB; the clamp applied {g:+.1f}: re-read it"})
    return out


def chain(k: int, path: Path, gain_db: float, gap_s: float) -> str:
    """ffmpeg filter for one chunk: mono 48 kHz, levelled, edges faded, then the gap's silence."""
    d = duration(path)
    f = min(EDGE_FADE, d / 4)
    return (f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,volume={gain_db:.3f}dB,"
            f"afade=t=in:d={f},afade=t=out:st={max(0.0, d - f):.4f}:d={f},apad=pad_dur={gap_s}[a{k}]")


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print(__doc__)
        return 2
    rep = plan(paths)
    print(json.dumps(rep, indent=1))
    for f in rep["findings"]:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    return 1 if any(f["severity"] == "FAIL" for f in rep["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
