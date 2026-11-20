"""ffmpeg observer (OB-1): decode check, black / frozen / silent stretches, audio offset, loudness, PySceneDetect cut list.

Reuses ``validators/tech_qa`` (BP-211, BP-54 thresholds from the registry). NOT_RUN (a record with that verdict, never a pass)
when ffmpeg/ffprobe is missing or the file cannot be measured; a missing PySceneDetect leaves the cut list NOT_RUN in the answers
while the other measurements still decide.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from explainer_engine.qa import observe as OB
from explainer_engine.qa import status as ST
from explainer_engine.validators import tech_qa as TQ


def _decode_errors(path: Path) -> str:
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True).stderr.strip()


def _loudness(path: Path) -> float | None:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(m[-1]) if m else None


def _cuts(path: Path) -> list[float] | None:
    """Scene-cut times (s) from PySceneDetect's ContentDetector; None when the library is not installed."""
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        return None
    return [round(a.get_seconds(), 2) for a, _ in detect(str(path), ContentDetector())[1:]]


def _iv(rows, key):
    return rows[key] if rows and rows.get(key) else []


def observe(root: Path, shot: str, kind: str, path: str, expected: dict | None = None, scenes: bool = True) -> dict:
    """The ``ffmpeg`` record of the file at ``path`` (relative to the episode folder, or absolute). ``expected``:
    ``{"fps": 24, "frames": 72}`` from the shot card or manifest (a missing key is not checked)."""
    root = Path(root)
    p = Path(path) if Path(path).is_absolute() else root / path
    if not TQ.tools_present():
        return OB.build(root, shot, kind, "ffmpeg", path, verdict=ST.NOT_RUN, note="NOT_RUN: ffmpeg/ffprobe is not installed")
    answers: dict = {}
    defects: list[dict] = []
    err = _decode_errors(p)
    answers["decode"] = "clean" if not err else err[:300]
    if err:
        defects.append({"code": "TECH-DECODE", "where": "file", "severity": "major", "note": err[:200]})
    if kind != "clip":
        return OB.build(root, shot, kind, "ffmpeg", path, questions=["does the file decode?"], answers=answers, defects=defects)
    expected = expected or {}
    try:
        info = TQ.probe(p)
        rows = {r["gate"]: r for r in TQ.check_file(p, expected)}   # BP-211 / BP-54 numbers stay in validators/tech_qa
    except Exception as exc:   # an unreadable file is a NOT_RUN of the detectors, the decode row above already says why
        return OB.build(root, shot, kind, "ffmpeg", path, answers=answers, defects=defects, verdict=ST.NOT_RUN,
                        note=f"NOT_RUN: the file could not be measured ({type(exc).__name__}: {exc})")
    answers.update({"fps": info["fps"], "frames": info["frames"], "duration_s": info["duration_s"]})
    if info["audio_start_s"] is not None and info["video_start_s"] is not None:
        answers["audio_offset_ms"] = round((info["audio_start_s"] - info["video_start_s"]) * 1000)
    # (gate, code, severity of a miss, whether the row carries intervals)
    for gate, code, sev, iv in (("VAL-QA-01", "TECH-FPS", "major", False), ("VAL-QA-02", "TECH-FRAMES", "major", False),
                                ("VAL-QA-03", "TECH-BLACK", "major", True), ("VAL-QA-04", "TECH-FREEZE", "minor", True),
                                ("VAL-QA-05", "TECH-SILENCE", "info", True), ("VAL-QA-06", "TECH-OFFSET", "minor", False)):
        row = rows[gate]
        if row["status"] in ("PASS", "NOT_RUN"):
            continue
        spans = row["measured"] if iv and isinstance(row["measured"], list) else [None]
        for sp in spans:
            where = f"t={sp[0]:.2f}-{sp[0] + sp[1]:.2f}s" if sp else "file"
            defects.append({"code": code, "where": where, "severity": sev, "note": row["detail"][:200]})
    answers["has_audio"] = info["audio_start_s"] is not None
    if info["audio_start_s"] is not None:
        answers["integrated_lufs"] = _loudness(p)
    cuts = _cuts(p) if scenes else None
    answers["scene_cuts"] = "NOT_RUN: PySceneDetect is not installed" if cuts is None else cuts
    for t in cuts or []:
        defects.append({"code": "TECH-CUT", "where": f"t={t:.2f}s", "severity": "minor", "note": "a cut inside one generated clip"})
    return OB.build(root, shot, kind, "ffmpeg", path, questions=["decodes?", "black/frozen/silent stretches?", "audio offset?", "cuts?"],
                    answers=answers, defects=defects)
