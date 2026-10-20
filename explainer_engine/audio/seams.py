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
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


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
