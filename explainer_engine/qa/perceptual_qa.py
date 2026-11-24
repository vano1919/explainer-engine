"""Multimodal Perceptual QA workflow combining 3-layer deterministic, perceptual, and editorial review.

Enforces honest, fail-closed quality reporting:
- Layer 1 (Deterministic Technical): multi-point temporal frame sampling (default >= 8 frames across
  clip duration with timestamps, SHA-256 hashes, and explicit uninspected-gap reporting), frozen-frame
  detection, ``technical_gate.check_no_melt`` residual motion/drift checks, and original-channel stereo
  audio analysis (RMS, peak clipping, spectral tone concentration, stereo balance).
- Layer 2 (Multimodal Perceptual): opt-in Gemini vision+audio review (``use_gemini=False`` by default)
  authenticating strictly via the ``x-goog-api-key`` header (never URL query strings), redacting keys
  from exceptions/logs, checking ``spend_caps.gemini_api()`` before live calls, and validating strict
  boolean/enum JSON schema (safety blocks, empty candidates, or malformed JSON yield ``NEEDS_REVIEW``).
- Layer 3 (Editorial & Creator Sign-Off): separates ``technical_status``, ``perceptual_status``,
  ``editorial_status``, and ``creator_signoff_status`` (always ``PENDING`` until explicit owner sign-off).
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from explainer_engine.core import spend_caps as SC
from explainer_engine.core import spend_ledger as SL
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import technical_gate as TG

UTC = datetime.UTC
DEFAULT_GEMINI_QA_MODEL = "gemini-2.5-flash"
DEFAULT_FRAME_COUNT = 8
ESTIMATED_GEMINI_QA_CALL_USD = 0.05

MULTIMODAL_QA_PROMPT = """You are the strict Visual, Audio, and Editorial Perceptual QA Reviewer for a cinematic historical docudrama engine.
You have been given temporal video frames from across the clip AND the clip's actual audio track.
Inspect both carefully for:
- visual melt, warping, anatomical morphing (faces, hands, weapons, uniforms), background swimming, flicker, or frozen static frames;
- natural speech/ambience/SFX versus synthetic tones, hum, buzz, clipping, or dead silence;
- lip-sync / audio-visual continuity and cinematic editorial quality.
Answer ONLY with valid JSON matching this exact schema (use real JSON booleans true/false):
{
  "visual_assessment": {
    "composition": "brief observation",
    "natural_motion": true,
    "melt_or_warp_detected": false,
    "motion_notes": "state whether subjects/environment move naturally or show melt/warp/static freeze",
    "artifacts_or_distortions": "none or concrete description"
  },
  "audio_assessment": {
    "natural_audio": true,
    "audio_notes": "state whether you hear natural speech/ambience/SFX or synthetic tones/buzz/silence",
    "sync_and_continuity": "brief observation"
  },
  "editorial_assessment": {
    "cinematic_quality": "pass",
    "notes": "does this feel like directed cinema or a mechanical slideshow/test tone?"
  },
  "defects": [
    {"defect_id": "D-01", "domain": "visual", "severity": "high", "description": "...", "segment_ref": "00:00.0"}
  ]
}"""

VALID_DOMAINS = frozenset({"visual", "audio", "editorial", "technical"})
VALID_SEVERITIES = frozenset({"high", "medium", "low"})
VALID_EDITORIAL_STATES = frozenset({"pass", "fail", "needs_review"})


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


def _redact_secret(text: str, secret: str | None) -> str:
    cleaned = re.sub(r"([?&]key=)[^&\s\"']+", r"\1[REDACTED]", text)
    if secret and len(secret) >= 6:
        cleaned = cleaned.replace(secret, "[REDACTED]")
    return cleaned


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
    p = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    return float(p.stdout.strip())


def sample_video_frames(
    video_path: Path,
    out_dir: Path,
    count: int = DEFAULT_FRAME_COUNT,
) -> list[SampledFrame]:
    """Extract evenly spaced temporal sample frames across the full clip duration."""
    if count < 2:
        raise ContractError("Video perceptual inspection requires at least 2 temporal frames (never frame 0 alone)")
    if not video_path.exists():
        raise ContractError(f"Video file not found: {video_path}")
    duration = probe_duration_s(video_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [round(duration * (0.05 + 0.90 * i / (count - 1)), 3) for i in range(count)]
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
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        frames.append(SampledFrame(index=i, timestamp_s=ts, path=str(out_png), sha256=_sha256(out_png)))
    return frames


def compute_uninspected_coverage(frames: list[SampledFrame], duration_s: float | None = None) -> dict[str, Any]:
    """Explicitly report temporal gaps between sampled frames so coverage is never overstated."""
    if not frames:
        return {"sampled_count": 0, "max_gap_s": duration_s or 0.0, "uninspected_leading_s": duration_s or 0.0, "uninspected_trailing_s": 0.0}
    ts = sorted(f.timestamp_s for f in frames)
    gaps = [round(ts[i + 1] - ts[i], 4) for i in range(len(ts) - 1)]
    leading = round(max(0.0, ts[0]), 4)
    trailing = round(max(0.0, (duration_s - ts[-1]) if duration_s is not None else 0.0), 4)
    return {
        "sampled_count": len(frames),
        "first_timestamp_s": ts[0],
        "last_timestamp_s": ts[-1],
        "max_gap_s": max(gaps) if gaps else 0.0,
        "uninspected_leading_s": leading,
        "uninspected_trailing_s": trailing,
        "coverage_note": f"Sampled {len(frames)} discrete frames; intervals up to {max(gaps) if gaps else 0.0:.3f}s between frames were not visually inspected.",
    }


def extract_audio_wav(video_path: Path, out_wav: Path) -> Path | None:
    """Extract PCM16 WAV preserving original channel count (including stereo) for accurate acoustic measurement."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        str(out_wav),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    if p.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 100:
        return None
    return out_wav


def analyze_clip_signals(
    frames: list[SampledFrame],
    wav_path: Path | None,
    *,
    duration_s: float | None = None,
) -> tuple[dict[str, Any], list[DefectRecord]]:
    """Deterministic signal sanity check catching frozen video, melt/warp drift, silence, clipping, and pure tones."""
    defects: list[DefectRecord] = []
    arrs = [np.asarray(Image.open(f.path).convert("L"), dtype=np.float32) / 255.0 for f in frames]
    diffs = [float(np.abs(arrs[i + 1] - arrs[i]).mean()) for i in range(len(arrs) - 1)]
    mean_frame_diff = float(np.mean(diffs)) if diffs else 0.0

    # Estimate residual motion / drift for technical_gate.check_no_melt
    residual_motion_per_frame = float(np.max(diffs)) if diffs else 0.0
    residual_drift = float(np.abs(arrs[-1] - arrs[0]).mean()) if len(arrs) >= 2 else 0.0
    melt_problems = TG.check_no_melt(
        {
            "residual_motion_per_frame": residual_motion_per_frame,
            "residual_drift": residual_drift,
        }
    )
    for mp in melt_problems:
        defects.append(
            DefectRecord(
                defect_id="SIG-VID-MELT",
                domain="visual",
                severity="high",
                description=f"Deterministic no-melt check failed: {mp}",
                segment_ref=f"{frames[0].timestamp_s}s-{frames[-1].timestamp_s}s",
            )
        )

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
    peak_dbfs = -120.0
    clipping_samples = 0
    spectral_top3_ratio = 0.0
    audio_channels = 0
    audio_sample_rate = 0
    stereo_balance_db: float | None = None

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
            audio_channels = wf.getnchannels()
            audio_sample_rate = wf.getframerate()
            raw_i16 = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2")
        if raw_i16.size > 0:
            raw = raw_i16.astype(np.float32) / 32768.0
            clipping_samples = int(np.sum(np.abs(raw_i16) >= 32767))
            peak = float(np.max(np.abs(raw)))
            peak_dbfs = round(20.0 * math.log10(peak), 2) if peak > 1e-9 else -120.0
            if audio_channels >= 2 and raw.size >= audio_channels:
                framed = raw[: (raw.size // audio_channels) * audio_channels].reshape(-1, audio_channels)
                mono = framed.mean(axis=1)
                left_rms = float(np.sqrt(np.mean(framed[:, 0] ** 2))) + 1e-9
                right_rms = float(np.sqrt(np.mean(framed[:, 1] ** 2))) + 1e-9
                stereo_balance_db = round(20.0 * math.log10(left_rms / right_rms), 2)
            else:
                mono = raw
            audio_rms = float(np.sqrt(np.mean(mono * mono)))
            spec = np.abs(np.fft.rfft(mono)) ** 2
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
        if clipping_samples > 10:
            defects.append(
                DefectRecord(
                    defect_id="SIG-AUD-CLIPPING",
                    domain="audio",
                    severity="medium",
                    description=f"Audio clipping detected ({clipping_samples} full-scale samples, peak={peak_dbfs} dBFS).",
                    segment_ref="full_clip",
                )
            )

    metrics = {
        "passed": not any(d.severity == "high" for d in defects),
        "mean_frame_diff": round(mean_frame_diff, 5),
        "residual_motion_per_frame": round(residual_motion_per_frame, 5),
        "residual_drift": round(residual_drift, 5),
        "no_melt_passed": len(melt_problems) == 0,
        "audio_channels": audio_channels,
        "audio_sample_rate": audio_sample_rate,
        "audio_rms": round(audio_rms, 5),
        "audio_peak_dbfs": peak_dbfs,
        "audio_clipping_samples": clipping_samples,
        "audio_stereo_balance_db": stereo_balance_db,
        "audio_spectral_top3_ratio": round(spectral_top3_ratio, 4),
        "temporal_coverage": compute_uninspected_coverage(frames, duration_s=duration_s),
    }
    return metrics, defects


def _default_gemini_http(
    url: str,
    body: dict[str, Any],
    *,
    api_key: str,
    timeout: float = 120.0,
) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = _redact_secret(exc.read().decode("utf-8", errors="replace"), api_key)
        raise ContractError(f"Gemini multimodal QA HTTP {exc.code}: {err_body[:300]}") from None
    except Exception as exc:
        raise ContractError(f"Gemini multimodal QA transport error: {_redact_secret(str(exc), api_key)}") from None


def validate_multimodal_response(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Strictly validate Gemini JSON payload; return (validated_dict, error_reason)."""
    if not isinstance(payload, dict):
        return None, "Response is not a JSON object"
    vis = payload.get("visual_assessment")
    aud = payload.get("audio_assessment")
    ed = payload.get("editorial_assessment")
    if not isinstance(vis, dict) or not isinstance(aud, dict) or not isinstance(ed, dict):
        return None, "Missing visual_assessment, audio_assessment, or editorial_assessment object"
    if not isinstance(vis.get("natural_motion"), bool):
        return None, "visual_assessment.natural_motion must be a real boolean"
    if "melt_or_warp_detected" in vis and not isinstance(vis.get("melt_or_warp_detected"), bool):
        return None, "visual_assessment.melt_or_warp_detected must be a real boolean"
    if not isinstance(aud.get("natural_audio"), bool):
        return None, "audio_assessment.natural_audio must be a real boolean"
    cq = str(ed.get("cinematic_quality", "")).lower()
    if cq not in VALID_EDITORIAL_STATES:
        return None, f"editorial_assessment.cinematic_quality invalid: {cq!r}"
    raw_defects = payload.get("defects", [])
    if not isinstance(raw_defects, list):
        return None, "defects must be a list"
    for item in raw_defects:
        if not isinstance(item, dict):
            return None, "each defect entry must be an object"
        if str(item.get("domain", "")).lower() not in VALID_DOMAINS:
            return None, f"invalid defect domain: {item.get('domain')!r}"
        if str(item.get("severity", "")).lower() not in VALID_SEVERITIES:
            return None, f"invalid defect severity: {item.get('severity')!r}"
    return payload, None


def _parse_gemini_envelope(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Handle Gemini safety blocks, empty candidates, and malformed JSON as NEEDS_REVIEW reasons."""
    prompt_fb = raw.get("promptFeedback") or {}
    if prompt_fb.get("blockReason"):
        return None, f"Gemini prompt blocked: {prompt_fb['blockReason']}"
    candidates = raw.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None, "Gemini returned zero candidates"
    cand = candidates[0]
    finish_reason = str(cand.get("finishReason") or "")
    if finish_reason.upper() in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
        return None, f"Gemini candidate blocked (finishReason={finish_reason})"
    parts = ((cand.get("content") or {}).get("parts")) or []
    text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    if not text:
        return None, "Gemini candidate returned empty text"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"Gemini returned malformed JSON: {exc.msg}"
    return validate_multimodal_response(parsed)


def invoke_gemini_multimodal_qa(
    frames: list[SampledFrame],
    wav_path: Path | None,
    *,
    model: str = DEFAULT_GEMINI_QA_MODEL,
    api_key: str | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Send temporal frames + audio WAV inline to Gemini multimodal API using x-goog-api-key header."""
    if transport is not None:
        # Custom transport is strictly isolated for offline test mocks: never forward real API keys
        key = "MOCK_TEST_KEY"
    else:
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ContractError("GEMINI_API_KEY is not set: cannot run live multimodal perceptual QA")

    # Enforce spend cap before any live API call
    reserved_item: str | None = None
    if transport is None:
        gem_cap = float(SC.gemini_api()["max_usd"])
        reserved_item = f"perceptual_qa_{datetime.datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}"
        SL.reserve(
            "gemini_api",
            reserved_item,
            ESTIMATED_GEMINI_QA_CALL_USD,
            cap_usd=gem_cap,
            why=f"multimodal perceptual QA ({model})",
            ledger_path=ledger_path,
        )

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
    # Security: NEVER pass API key in the URL query string.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key or "TEST"}

    if transport is not None:
        try:
            raw = transport(url, body, headers)
        except TypeError:
            raw = transport(url, body)
    else:
        try:
            raw = _default_gemini_http(url, body, api_key=key or "")
        finally:
            if reserved_item is not None:
                SL.settle("gemini_api", reserved_item, ESTIMATED_GEMINI_QA_CALL_USD, ledger_path=ledger_path)

    validated, err = _parse_gemini_envelope(raw)
    if validated is None:
        return {
            "_review_error": err,
            "visual_assessment": {"natural_motion": None, "notes": err},
            "audio_assessment": {"natural_audio": None, "notes": err},
            "editorial_assessment": {"cinematic_quality": "needs_review", "notes": err},
            "defects": [],
        }
    return validated


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
    """Assemble a fail-closed 3-layer multimodal perceptual QA report."""
    if len(sampled_frames) < 2:
        raise ContractError("Perceptual QA report requires >= 2 temporal frames for video evaluation")
    if audio_inspection_mode not in ("direct_listening", "waveform_and_loudness_fallback", "not_applicable"):
        raise ContractError(f"Invalid audio_inspection_mode: {audio_inspection_mode!r}")

    defect_list = list(defects or [])
    if visual_assessment.get("natural_motion") is False and not any(d.domain == "visual" and d.severity == "high" for d in defect_list):
        defect_list.append(
            DefectRecord("VIS-NO-NATURAL-MOTION", "visual", "high", str(visual_assessment.get("motion_notes", "No natural motion")), "full_clip")
        )
    if visual_assessment.get("melt_or_warp_detected") is True and not any(d.defect_id == "VIS-MELT-WARP" for d in defect_list):
        defect_list.append(
            DefectRecord("VIS-MELT-WARP", "visual", "high", str(visual_assessment.get("artifacts_or_distortions", "Melt or warp detected")), "full_clip")
        )
    if audio_assessment.get("natural_audio") is False and not any(d.domain == "audio" and d.severity == "high" for d in defect_list):
        defect_list.append(
            DefectRecord("AUD-UNNATURAL", "audio", "high", str(audio_assessment.get("audio_notes", "Unnatural audio")), "full_clip")
        )

    open_high = [d for d in defect_list if d.severity == "high" and d.status == "OPEN"]
    tech_pass = bool(technical_metrics.get("passed", False))
    signal_only = (
        bool(visual_assessment.get("signal_only"))
        or bool(audio_assessment.get("signal_only"))
        or reviewer_model == "signal_sanity_only"
    )
    missing_bool_eval = (
        visual_assessment.get("natural_motion") is None
        or audio_assessment.get("natural_audio") is None
    )
    editorial_state = str(editorial_assessment.get("cinematic_quality", "")).lower()
    if editorial_state == "pass" and not signal_only and not missing_bool_eval:
        editorial_status = "PASS"
    elif editorial_state == "fail":
        editorial_status = "FAIL"
    else:
        editorial_status = "NEEDS_REVIEW"

    technical_status = "PASS" if tech_pass else "FAIL"
    if open_high or not tech_pass or editorial_status == "FAIL":
        verdict = "FAIL"
        perceptual_status = "FAIL"
    elif signal_only or missing_bool_eval or editorial_status == "NEEDS_REVIEW" or any(d.status == "OPEN" for d in defect_list):
        verdict = "NEEDS_REVIEW"
        perceptual_status = "NEEDS_REVIEW"
    else:
        verdict = "PASS"
        perceptual_status = "PASS"

    report = {
        "schema_version": "perceptual_qa_report/2",
        "timestamp": datetime.datetime.now(UTC).isoformat(),
        "artifact_path": artifact_path,
        "reviewer_model": reviewer_model,
        "verdict": verdict,
        "technical_status": technical_status,
        "perceptual_status": perceptual_status,
        "editorial_status": editorial_status,
        "creator_signoff_status": "PENDING",
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
    frame_count: int = DEFAULT_FRAME_COUNT,
    use_gemini: bool = False,
    reviewer_model: str = DEFAULT_GEMINI_QA_MODEL,
    transport: Callable[..., dict[str, Any]] | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Run full frame extraction + audio extraction + signal sanity + optional live Gemini multimodal review."""
    duration_s = probe_duration_s(video_path)
    frames = sample_video_frames(video_path, out_dir / "frames", count=frame_count)
    wav_path = extract_audio_wav(video_path, out_dir / f"{video_path.stem}_audio.wav")
    sig_metrics, sig_defects = analyze_clip_signals(frames, wav_path, duration_s=duration_s)

    if use_gemini:
        mm = invoke_gemini_multimodal_qa(
            frames,
            wav_path,
            model=reviewer_model,
            transport=transport,
            ledger_path=ledger_path,
        )
        vis = mm.get("visual_assessment") or {}
        aud = mm.get("audio_assessment") or {}
        ed = mm.get("editorial_assessment") or {}
        mm_defects = [
            DefectRecord(
                defect_id=str(d.get("defect_id", f"MM-{i}")),
                domain=str(d.get("domain", "visual")).lower(),
                severity=str(d.get("severity", "high")).lower(),
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
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--frames", type=int, default=DEFAULT_FRAME_COUNT)
    ap.add_argument("--gemini", action="store_true", help="opt-in paid Gemini multimodal review")
    ap.add_argument("--model", default=DEFAULT_GEMINI_QA_MODEL)
    args = ap.parse_args(argv)
    out = args.out_dir or (args.video.parent / "qa")
    rep = evaluate_clip_perceptual(
        args.video,
        out_dir=out,
        frame_count=args.frames,
        use_gemini=args.gemini,
        reviewer_model=args.model,
    )
    print(json.dumps({"verdict": rep["verdict"], "technical_status": rep["technical_status"], "perceptual_status": rep["perceptual_status"], "editorial_status": rep["editorial_status"], "creator_signoff_status": rep["creator_signoff_status"], "report": str(out / "perceptual_qa_report.json")}))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
