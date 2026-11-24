"""Post-Assembly Visual-Aware Sound Spotting and Audio Transition A/B Verification.

Workflow (Section 8):
1. Inspect an actual assembled preview video on disk via temporal frame-difference peaks to
   propose measured visual event timestamps.
2. Pin the 64-character SHA-256 of the assembled preview video into ``spotting_record/1``.
3. Automatically invalidate the spotting record if the assembled video changes on disk.
4. Provide objective A/B audio transition measurement (hard cut vs 30ms anti-pop crossfade)
   measuring peak sample discontinuity at the cut boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.scripting.docudrama_structure import validate_post_assembly_spotting

SPOTTING_SCHEMA = "post_assembly_spotting/1"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Video file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_visual_event_timestamps(
    preview_video: Path,
    work_dir: Path,
    *,
    sample_fps: float = 4.0,
    diff_threshold: float = 0.04,
) -> list[dict[str, Any]]:
    """Sample frames from ``preview_video`` and locate visual cut/motion spikes for SFX spotting."""
    if not preview_video.is_file():
        raise ContractError(f"Preview video not found: {preview_video}")
    frames_dir = work_dir / "spotting_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("f_*.png"):
        old.unlink()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(preview_video),
            "-vf",
            f"fps={sample_fps},scale=160:90",
            str(frames_dir / "f_%04d.png"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    frame_files = sorted(frames_dir.glob("f_*.png"))
    if len(frame_files) < 2:
        return []

    arrs = [np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0 for p in frame_files]
    events: list[dict[str, Any]] = []
    for idx in range(len(arrs) - 1):
        delta = float(np.abs(arrs[idx + 1] - arrs[idx]).mean())
        if delta >= diff_threshold:
            ts = round((idx + 1) / sample_fps, 3)
            events.append({"visual_timestamp_s": ts, "frame_delta": round(delta, 4), "suggested_cue": "impact_or_transition"})
    return events


def build_spotting_record(
    preview_video: Path,
    cues: list[dict[str, Any]],
    *,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Assemble and validate a SHA-256-pinned post-assembly sound spotting record."""
    video_sha = sha256_file(preview_video)
    record: dict[str, Any] = {
        "schema_version": SPOTTING_SCHEMA,
        "based_on_assembled_video": True,
        "assembled_video_path": str(preview_video),
        "assembled_video_sha256": video_sha,
        "cues": list(cues),
    }
    validation = validate_post_assembly_spotting(record)
    record["validation"] = validation
    if out_path is not None:
        write_json_atomic(out_path, record)
    return record


def is_spotting_fresh(record: dict[str, Any], preview_video: Path) -> bool:
    """Return True iff the spotting record still matches the exact SHA-256 of ``preview_video`` on disk."""
    if not preview_video.is_file():
        return False
    return str(record.get("assembled_video_sha256", "")) == sha256_file(preview_video)


def measure_audio_cut_ab(
    wav_a: Path,
    wav_b: Path,
    out_dir: Path,
    *,
    fade_ms: float = 30.0,
) -> dict[str, Any]:
    """Compare hard-cut join vs ``fade_ms`` crossfade objectively by measuring boundary sample jump."""
    if not wav_a.is_file() or not wav_b.is_file():
        raise ContractError("Both wav_a and wav_b must exist for audio cut A/B comparison")
    with wave.open(str(wav_a), "rb") as wa:
        sr_a, ch_a = wa.getframerate(), wa.getnchannels()
        sig_a = np.frombuffer(wa.readframes(wa.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    with wave.open(str(wav_b), "rb") as wb:
        sr_b, ch_b = wb.getframerate(), wb.getnchannels()
        sig_b = np.frombuffer(wb.readframes(wb.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if sr_a != sr_b or ch_a != ch_b:
        raise ContractError(f"Audio format mismatch: ({sr_a}, {ch_a}) vs ({sr_b}, {ch_b})")

    if ch_a > 1:
        sig_a = sig_a.reshape(-1, ch_a).mean(axis=1)
        sig_b = sig_b.reshape(-1, ch_b).mean(axis=1)

    hard_cut = np.concatenate([sig_a, sig_b])
    boundary_idx = len(sig_a)
    hard_jump = float(abs(hard_cut[boundary_idx] - hard_cut[boundary_idx - 1])) if boundary_idx > 0 and boundary_idx < len(hard_cut) else 0.0

    fade_n = max(1, min(int(sr_a * fade_ms / 1000.0), len(sig_a) // 2, len(sig_b) // 2))
    ramp_out = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
    ramp_in = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
    faded = np.concatenate([sig_a[:-fade_n], sig_a[-fade_n:] * ramp_out + sig_b[:fade_n] * ramp_in, sig_b[fade_n:]])
    faded_window = faded[max(0, boundary_idx - fade_n - 1) : min(len(faded), boundary_idx + 2)]
    faded_jump = float(np.max(np.abs(np.diff(faded_window)))) if len(faded_window) > 1 else 0.0

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, arr in (("ab_hard_cut.wav", hard_cut), ("ab_fade_30ms.wav", faded)):
        pcm = np.clip(arr * 32767.0, -32768, 32767).astype("<i2")
        with wave.open(str(out_dir / name), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr_a)
            wf.writeframes(pcm.tobytes())

    return {
        "fade_ms": fade_ms,
        "hard_cut_boundary_jump": round(hard_jump, 5),
        "faded_boundary_max_step": round(faded_jump, 5),
        "pop_reduction_ratio": round((hard_jump - faded_jump) / hard_jump, 4) if hard_jump > 1e-6 else 0.0,
        "hard_cut_wav": str(out_dir / "ab_hard_cut.wav"),
        "faded_wav": str(out_dir / "ab_fade_30ms.wav"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.audio.post_assembly_spotting")
    ap.add_argument("preview_video", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--work-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    work = args.work_dir or (args.out.parent / "spotting_work")
    events = detect_visual_event_timestamps(args.preview_video, work)
    cues = [{"source": "free_library", "visual_timestamp_s": e["visual_timestamp_s"], "cue": e["suggested_cue"]} for e in events]
    rec = build_spotting_record(args.preview_video, cues, out_path=args.out)
    print(json.dumps({"status": rec["validation"]["status"], "cues": len(cues), "video_sha256": rec["assembled_video_sha256"]}, indent=2))
    return 0 if rec["validation"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
