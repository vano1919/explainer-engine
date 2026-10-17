"""Seams between read chunks (ED-01): the chunks of one read come back at different loudness (Episode 1: -33.5 to -27.9 LUFS,
a 5.6 dB spread that showed as jumps at the joins, worst in Day 1). Every chunk is brought to the median gated loudness
before the join and gets a short fade at both edges inside its silence, so a join adds no click and no word moves.
Needs ffmpeg (loudness measure, gain, fades)."""
from __future__ import annotations

import re
import statistics
import subprocess
from pathlib import Path

EDGE_FADE = 0.03  # seconds of fade at each chunk edge (inside the silence the voice leaves there)
MAX_SPREAD_DB = 1.5  # ED-01: chunk loudness spread allowed after levelling
MAX_GAIN_DB = 6.0  # a chunk that needs more than this is reported, not silently boosted further


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
    return {"target_lufs": round(target, 2), "before": [round(x, 2) for x in loud], "gains_db": [round(g, 2) for g in gains],
            "spread_before_db": round(max(loud) - min(loud), 2), "spread_after_db": round(max(after) - min(after), 2)}


def chain(k: int, path: Path, gain_db: float, gap_s: float) -> str:
    """ffmpeg filter for one chunk: mono 48 kHz, levelled, edges faded, then the gap's silence."""
    d = duration(path)
    f = min(EDGE_FADE, d / 4)
    return (f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,volume={gain_db:.3f}dB,"
            f"afade=t=in:d={f},afade=t=out:st={max(0.0, d - f):.4f}:d={f},apad=pad_dur={gap_s}[a{k}]")
