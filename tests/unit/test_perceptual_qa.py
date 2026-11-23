"""Unit tests for real multimodal perceptual QA (signal sanity + Gemini video/audio reviewer)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.qa import look_and_listen as LL
from explainer_engine.qa import observers as OBS
from explainer_engine.qa.perceptual_qa import (
    DefectRecord,
    SampledFrame,
    build_perceptual_qa_report,
    evaluate_clip_perceptual,
    sample_video_frames,
)


def _make_sine_mp4(path: Path, seconds: float = 2.0) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x180:rate=24",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True)
    return path


def _make_broadband_mp4(path: Path, seconds: float = 2.0) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=duration={seconds}:size=320x180:rate=24",
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.15:duration={seconds}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True)
    return path


def test_look_and_listen_and_observers_import_cleanly():
    assert hasattr(LL, "RECORD_SCHEMA")
    assert OBS is not None


def test_synthetic_pure_tone_clip_fails_signal_sanity(tmp_path: Path):
    vid = _make_sine_mp4(tmp_path / "synthetic_tone.mp4", seconds=2.0)
    rep = evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa", use_gemini=False)
    assert rep["verdict"] == "FAIL"
    ids = {d["defect_id"] for d in rep["defects"]}
    assert "SIG-AUD-SYNTHETIC-TONE" in ids


def test_gemini_multimodal_reviewer_receives_frames_and_audio_and_enforces_verdict(tmp_path: Path):
    vid = _make_broadband_mp4(tmp_path / "broadband.mp4", seconds=2.0)
    seen = {}

    def fake_gemini(url: str, body: dict) -> dict:
        parts = body["contents"][0]["parts"]
        mimes = [p["inline_data"]["mime_type"] for p in parts if "inline_data" in p]
        seen["mimes"] = mimes
        ans = {
            "visual_assessment": {"composition": "ok", "natural_motion": False, "motion_notes": "candle flame is frozen", "artifacts_or_distortions": "none"},
            "audio_assessment": {"natural_audio": True, "audio_notes": "ambience ok", "sync_and_continuity": "ok"},
            "editorial_assessment": {"cinematic_quality": "fail", "notes": "static flame"},
            "defects": [{"defect_id": "D-FLAME", "domain": "visual", "severity": "high", "description": "Flame does not flicker", "segment_ref": "00:01.0"}],
        }
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(ans)}]}}]}

    rep = evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa_mm", use_gemini=True, transport=fake_gemini)
    assert seen["mimes"].count("image/png") == 3
    assert "audio/wav" in seen["mimes"]
    assert rep["audio_inspection_mode"] == "direct_listening"
    assert rep["verdict"] == "FAIL"
    assert any(d["defect_id"] == "D-FLAME" for d in rep["defects"])


def test_refuses_single_frame_video_certification():
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
