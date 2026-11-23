"""Unit tests for multimodal perceptual QA module."""
from __future__ import annotations

import subprocess
from pathlib import Path
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.qa.perceptual_qa import (
    DefectRecord,
    SampledFrame,
    build_perceptual_qa_report,
    sample_video_frames,
)


def _make_test_mp4(path: Path, seconds: float = 2.0) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x180:rate=24",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True)
    return path


def test_sample_video_frames_extracts_temporal_samples(tmp_path: Path):
    vid = _make_test_mp4(tmp_path / "sample.mp4", seconds=2.0)
    frames = sample_video_frames(vid, tmp_path / "frames", count=3)
    assert len(frames) == 3
    assert frames[0].timestamp_s < frames[1].timestamp_s < frames[2].timestamp_s
    for fr in frames:
        assert Path(fr.path).exists()
        assert len(fr.sha256) == 64


def test_refuses_single_frame_video_certification(tmp_path: Path):
    with pytest.raises(ContractError):
        build_perceptual_qa_report(
            artifact_path="clip.mp4",
            reviewer_model="gemini-4-neon",
            sampled_frames=[SampledFrame(0, 0.0, "f0.png", "a" * 64)],
            visual_assessment={"ok": True},
            audio_assessment={"ok": True},
            editorial_assessment={"ok": True},
            technical_metrics={"passed": True},
        )


def test_open_high_defect_forces_fail_verdict(tmp_path: Path):
    frames = [
        SampledFrame(0, 0.2, "f0.png", "a" * 64),
        SampledFrame(1, 1.8, "f1.png", "b" * 64),
    ]
    out = tmp_path / "qa_report.json"
    rep = build_perceptual_qa_report(
        artifact_path="clip.mp4",
        reviewer_model="gemini-4-neon",
        sampled_frames=frames,
        visual_assessment={"composition": "good"},
        audio_assessment={"sync": "ok"},
        editorial_assessment={"pacing": "steady"},
        technical_metrics={"passed": True},
        defects=[
            DefectRecord("D-01", "visual", "high", "flicker artifact at 1.2s", "00:01.2", status="OPEN"),
        ],
        out_path=out,
    )
    assert rep["verdict"] == "FAIL"
    assert rep["open_high_defects"] == 1
    assert out.exists()
