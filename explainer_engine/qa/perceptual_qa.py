"""Multimodal Perceptual QA workflow combining technical checks with visual, audio, and editorial review.

Enforces honest, fail-closed quality reporting:
- Video clips MUST be inspected via multi-point temporal frame sampling (never frame 0 alone).
- Audio inspection records whether audio was directly listened to or verified via technical fallback.
- Open high-severity defects block PASS and track corrective actions cleanly.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

UTC = datetime.timezone.utc


@dataclass(frozen=True)
class SampledFrame:
    index: int
    timestamp_s: float
    path: str
    sha256: str


@dataclass(frozen=True)
class DefectRecord:
    defect_id: str
    domain: str  # "visual" | "audio" | "editorial" | "technical"
    severity: str  # "high" | "medium" | "low"
    description: str
    segment_ref: str
    status: str = "OPEN"  # "OPEN" | "FIXED" | "WAIVED"
    corrective_action: str = ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_duration_s(media_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def sample_video_frames(video_path: Path, out_dir: Path, count: int = 3) -> list[SampledFrame]:
    """Extract evenly spaced temporal sample frames across the full clip duration."""
    if count < 2:
        raise ContractError("Video perceptual inspection requires at least 2 temporal frames (never frame 0 alone)")
    if not video_path.exists():
        raise ContractError(f"Video file not found: {video_path}")
    duration = probe_duration_s(video_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Sample from 10% to 90% of duration to avoid black fade-in/fade-out edges
    timestamps = [round(duration * (0.1 + 0.8 * i / (count - 1)), 3) for i in range(count)]
    frames: list[SampledFrame] = []
    for i, ts in enumerate(timestamps):
        out_png = out_dir / f"{video_path.stem}_frame_{i:02d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{ts:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(out_png),
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        frames.append(SampledFrame(index=i, timestamp_s=ts, path=str(out_png), sha256=_sha256(out_png)))
    return frames


def build_perceptual_qa_report(
    *,
    artifact_path: str,
    reviewer_model: str,
    sampled_frames: list[SampledFrame],
    visual_assessment: dict[str, Any],
    audio_assessment: dict[str, Any],
    editorial_assessment: dict[str, Any],
    technical_metrics: dict[str, Any],
    defects: list[DefectRecord] | None = None,
    audio_inspection_mode: str = "waveform_and_loudness_fallback",
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Assemble a fail-closed multimodal perceptual QA report."""
    if len(sampled_frames) < 2:
        raise ContractError("Perceptual QA report requires >= 2 temporal frames for video evaluation")
    if audio_inspection_mode not in ("direct_listening", "waveform_and_loudness_fallback", "not_applicable"):
        raise ContractError(f"Invalid audio_inspection_mode: {audio_inspection_mode!r}")

    defect_list = list(defects or [])
    open_high = [d for d in defect_list if d.severity == "high" and d.status == "OPEN"]
    tech_pass = bool(technical_metrics.get("passed", False))

    if open_high or not tech_pass:
        verdict = "FAIL"
    elif any(d.status == "OPEN" for d in defect_list):
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "PASS"

    report = {
        "schema_version": "perceptual_qa_report/1",
        "timestamp": datetime.datetime.now(UTC).isoformat(),
        "artifact_path": artifact_path,
        "reviewer_model": reviewer_model,
        "verdict": verdict,
        "temporal_frames_inspected": [asdict(f) for f in sampled_frames],
        "audio_inspection_mode": audio_inspection_mode,
        "technical_metrics": technical_metrics,
        "visual_assessment": visual_assessment,
        "audio_assessment": audio_assessment,
        "editorial_assessment": editorial_assessment,
        "defects": [asdict(d) for d in defect_list],
        "open_high_defects": len(open_high),
    }
    if out_path is not None:
        write_json_atomic(out_path, report)
    return report
