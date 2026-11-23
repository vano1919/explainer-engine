"""Multimodal Perceptual QA workflow combining signal sanity checks with real visual + audio AI review.

Enforces honest, fail-closed quality reporting:
- Video clips MUST be inspected via multi-point temporal frame sampling (never frame 0 alone).
- Local signal checks catch frozen/static frames and synthetic pure-tone/buzz audio before sign-off.
- Real multimodal inspection (`invoke_gemini_multimodal_qa`) sends BOTH temporal frames and the actual
  audio clip to a vision+audio capable Gemini model (`GEMINI_API_KEY`) so the reviewer actually sees
  motion and hears audio.
- Open high-severity defects block PASS and track corrective actions cleanly.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

UTC = datetime.timezone.utc
DEFAULT_GEMINI_QA_MODEL = "gemini-2.5-flash"

MULTIMODAL_QA_PROMPT = """You are the strict Visual, Audio, and Editorial Perceptual QA Reviewer for a cinematic historical docudrama engine.
You have been given temporal video frames from across the clip AND the clip's actual audio track.
Inspect both carefully and answer ONLY with valid JSON:
{
  "visual_assessment": {
    "composition": "brief observation",
    "natural_motion": true | false,
    "motion_notes": "state whether subjects/fire/environment actually move or if it is a static zoom/frozen still",
    "artifacts_or_distortions": "none or concrete description"
  },
  "audio_assessment": {
    "natural_audio": true | false,
    "audio_notes": "state whether you hear natural speech/ambience/SFX or synthetic tones/buzz/silence",
    "sync_and_continuity": "brief observation"
  },
  "editorial_assessment": {
    "cinematic_quality": "pass | fail | needs_review",
    "notes": "does this feel like directed cinema or a mechanical slideshow/test tone?"
  },
  "defects": [
    {"defect_id": "D-01", "domain": "visual|audio|editorial", "severity": "high|medium|low", "description": "...", "segment_ref": "00:00.0"}
  ]
}"""


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


def extract_audio_wav(video_path: Path, out_wav: Path) -> Path | None:
    """Extract mono 16kHz WAV track for acoustic inspection and multimodal model upload."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
        str(out_wav),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 100:
        return None
    return out_wav


def analyze_clip_signals(frames: list[SampledFrame], wav_path: Path | None) -> tuple[dict[str, Any], list[DefectRecord]]:
    """Deterministic signal sanity check catching frozen video, silence, and synthetic pure-tone audio."""
    defects: list[DefectRecord] = []
    arrs = [np.asarray(Image.open(f.path).convert("L"), dtype=np.float32) / 255.0 for f in frames]
    diffs = [float(np.abs(arrs[i + 1] - arrs[i]).mean()) for i in range(len(arrs) - 1)]
    mean_frame_diff = float(np.mean(diffs)) if diffs else 0.0

    if mean_frame_diff < 0.002:
        defects.append(
            DefectRecord(
                defect_id="SIG-VID-FROZEN",
                domain="visual",
                severity="high",
                description=f"Clip appears visually frozen across sampled frames (mean_frame_diff={mean_frame_diff:.5f}).",
                segment_ref=f"{frames[0].timestamp_s}s-{frames[-1].timestamp_s}s",
            )
        )

    audio_rms = 0.0
    spectral_top3_ratio = 0.0
    if wav_path is None or not wav_path.exists():
        defects.append(
            DefectRecord(
                defect_id="SIG-AUD-MISSING",
                domain="audio",
                severity="high",
                description="No readable audio stream found in clip.",
                segment_ref="full_clip",
            )
        )
    else:
        with wave.open(str(wav_path), "rb") as wf:
            raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        if raw.size > 0:
            audio_rms = float(np.sqrt(np.mean(raw * raw)))
            spec = np.abs(np.fft.rfft(raw)) ** 2
            total_energy = float(spec.sum()) or 1e-12
            top3 = float(np.sort(spec)[-3:].sum())
            spectral_top3_ratio = top3 / total_energy
        if audio_rms < 1e-4:
            defects.append(
                DefectRecord(
                    defect_id="SIG-AUD-SILENT",
                    domain="audio",
                    severity="high",
                    description=f"Audio track is effectively silent (rms={audio_rms:.6f}).",
                    segment_ref="full_clip",
                )
            )
        elif spectral_top3_ratio > 0.65:
            defects.append(
                DefectRecord(
                    defect_id="SIG-AUD-SYNTHETIC-TONE",
                    domain="audio",
                    severity="high",
                    description=f"Audio spectrum is concentrated in <=3 pure frequencies (top3_ratio={spectral_top3_ratio:.3f}); synthetic tone/hum detected instead of natural speech/SFX.",
                    segment_ref="full_clip",
                )
            )

    metrics = {
        "passed": len(defects) == 0,
        "mean_frame_diff": round(mean_frame_diff, 5),
        "audio_rms": round(audio_rms, 5),
        "audio_spectral_top3_ratio": round(spectral_top3_ratio, 4),
    }
    return metrics, defects


def _default_gemini_http(url: str, body: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def invoke_gemini_multimodal_qa(
    frames: list[SampledFrame],
    wav_path: Path | None,
    *,
    model: str = DEFAULT_GEMINI_QA_MODEL,
    api_key: str | None = None,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send real temporal frames + audio WAV inline to Gemini multimodal API for visual+audio QA."""
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and transport is None:
        raise ContractError("GEMINI_API_KEY is not set: cannot run live multimodal perceptual QA")

    parts: list[dict[str, Any]] = [{"text": MULTIMODAL_QA_PROMPT}]
    for fr in frames:
        b64 = base64.b64encode(Path(fr.path).read_bytes()).decode("ascii")
        parts.append({"text": f"Frame {fr.index} at {fr.timestamp_s}s:"})
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
    if wav_path and wav_path.exists():
        ab64 = base64.b64encode(wav_path.read_bytes()).decode("ascii")
        parts.append({"text": "Clip audio track (WAV):"})
        parts.append({"inline_data": {"mime_type": "audio/wav", "data": ab64}})

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key or 'TEST'}"
    raw = (transport or _default_gemini_http)(url, body)
    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


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
    audio_inspection_mode: str = "direct_listening",
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Assemble a fail-closed multimodal perceptual QA report."""
    if len(sampled_frames) < 2:
        raise ContractError("Perceptual QA report requires >= 2 temporal frames for video evaluation")
    if audio_inspection_mode not in ("direct_listening", "waveform_and_loudness_fallback", "not_applicable"):
        raise ContractError(f"Invalid audio_inspection_mode: {audio_inspection_mode!r}")

    defect_list = list(defects or [])
    if visual_assessment.get("natural_motion") is False and not any(d.domain == "visual" and d.severity == "high" for d in defect_list):
        defect_list.append(
            DefectRecord("VIS-NO-NATURAL-MOTION", "visual", "high", str(visual_assessment.get("motion_notes", "No natural motion")), "full_clip")
        )
    if audio_assessment.get("natural_audio") is False and not any(d.domain == "audio" and d.severity == "high" for d in defect_list):
        defect_list.append(
            DefectRecord("AUD-UNNATURAL", "audio", "high", str(audio_assessment.get("audio_notes", "Unnatural audio")), "full_clip")
        )

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


def evaluate_clip_perceptual(
    video_path: Path,
    *,
    out_dir: Path,
    frame_count: int = 3,
    use_gemini: bool = False,
    reviewer_model: str = DEFAULT_GEMINI_QA_MODEL,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run full frame extraction + audio extraction + signal sanity + optional live Gemini multimodal review."""
    frames = sample_video_frames(video_path, out_dir / "frames", count=frame_count)
    wav_path = extract_audio_wav(video_path, out_dir / f"{video_path.stem}_audio.wav")
    sig_metrics, sig_defects = analyze_clip_signals(frames, wav_path)

    if use_gemini:
        mm = invoke_gemini_multimodal_qa(frames, wav_path, model=reviewer_model, transport=transport)
        vis = mm.get("visual_assessment") or {}
        aud = mm.get("audio_assessment") or {}
        ed = mm.get("editorial_assessment") or {}
        mm_defects = [
            DefectRecord(
                defect_id=str(d.get("defect_id", f"MM-{i}")),
                domain=str(d.get("domain", "visual")),
                severity=str(d.get("severity", "high")),
                description=str(d.get("description", "")),
                segment_ref=str(d.get("segment_ref", "full_clip")),
            )
            for i, d in enumerate(mm.get("defects") or [])
        ]
        all_defects = sig_defects + mm_defects
        mode = "direct_listening" if wav_path is not None else "not_applicable"
        model_label = reviewer_model
    else:
        vis = {"natural_motion": sig_metrics["mean_frame_diff"] >= 0.002, "signal_only": True}
        aud = {"natural_audio": sig_metrics["audio_spectral_top3_ratio"] <= 0.65 and sig_metrics["audio_rms"] >= 1e-4, "signal_only": True}
        ed = {"cinematic_quality": "needs_review" if sig_metrics["passed"] else "fail", "note": "Pass --gemini for multimodal eye+ear review"}
        all_defects = sig_defects
        mode = "waveform_and_loudness_fallback"
        model_label = "signal_sanity_only"

    return build_perceptual_qa_report(
        artifact_path=str(video_path),
        reviewer_model=model_label,
        sampled_frames=frames,
        visual_assessment=vis,
        audio_assessment=aud,
        editorial_assessment=ed,
        technical_metrics=sig_metrics,
        defects=all_defects,
        audio_inspection_mode=mode,
        out_path=out_dir / "perceptual_qa_report.json",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.perceptual_qa")
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--gemini", action="store_true", help="invoke live Gemini multimodal video+audio QA")
    ap.add_argument("--model", default=DEFAULT_GEMINI_QA_MODEL)
    a = ap.parse_args(argv)
    rep = evaluate_clip_perceptual(a.video, out_dir=a.out.parent, frame_count=a.frames, use_gemini=a.gemini, reviewer_model=a.model)
    write_json_atomic(a.out, rep)
    print(json.dumps({"verdict": rep["verdict"], "open_high_defects": rep["open_high_defects"], "out": str(a.out)}))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
