"""Automatic Speech & Action End-Point Trimmer (BP-187: 0.35-0.50s post-speech tail trim).

Eliminates dead 6-8 second pauses at the end of LTX-2.5 clips by measuring the short-time RMS
energy envelope of the clip's audio stream (with optional voice-bandpass emphasis 250-3400 Hz),
locating the final active speech/action beat, and trimming to ``speech_end_s + tail_s`` while
enforcing frame alignment at 24 fps and safe minimum durations.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_FPS = 24
DEFAULT_TAIL_S = 0.42
MIN_BP187_TAIL_S = 0.30
MAX_BP187_TAIL_S = 0.60


def probe_duration_s(media_path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        text=True,
    ).strip()
    return float(out)


def detect_speech_end_s(
    media_path: Path,
    *,
    sample_rate: int = 16000,
    window_ms: int = 50,
    voice_bandpass: bool = True,
    threshold_db_below_peak: float = 18.0,
    abs_floor_dbfs: float = -38.0,
) -> dict[str, Any]:
    """Detect the final active speech/action timestamp (seconds) from a clip's audio track."""
    p = Path(media_path)
    dur_s = probe_duration_s(p)
    af = "highpass=f=250,lowpass=f=3400" if voice_bandpass else "anull"
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(p),
        "-vn",
        "-af",
        af,
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0 or not proc.stdout:
        return {
            "duration_s": round(dur_s, 3),
            "speech_end_s": round(dur_s, 3),
            "peak_dbfs": -99.0,
            "has_activity": False,
        }

    samples = np.frombuffer(proc.stdout, dtype="<i2").astype(np.float64) / 32768.0
    win = max(1, int(sample_rate * window_ms / 1000.0))
    n_wins = samples.size // win
    if n_wins == 0:
        return {
            "duration_s": round(dur_s, 3),
            "speech_end_s": round(dur_s, 3),
            "peak_dbfs": -99.0,
            "has_activity": False,
        }

    frames = samples[: n_wins * win].reshape(n_wins, win)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    rms_db = 20.0 * np.log10(np.maximum(rms, 1e-9))
    peak_db = float(np.max(rms_db))
    thresh_db = max(abs_floor_dbfs, peak_db - threshold_db_below_peak)

    active = np.where(rms_db >= thresh_db)[0]
    if active.size == 0 or peak_db < abs_floor_dbfs:
        return {
            "duration_s": round(dur_s, 3),
            "speech_end_s": round(min(dur_s, 3.0), 3),
            "peak_dbfs": round(peak_db, 2),
            "has_activity": False,
        }

    # Require sustained activity (>= 2 contiguous windows = 100ms) to ignore lone breath pops
    last_idx = int(active[-1])
    for idx in reversed(active.tolist()):
        if idx > 0 and rms_db[idx - 1] >= thresh_db - 3.0:
            last_idx = idx
            break
    speech_end_s = min(dur_s, (last_idx + 1) * (window_ms / 1000.0))
    return {
        "duration_s": round(dur_s, 3),
        "speech_end_s": round(float(speech_end_s), 3),
        "peak_dbfs": round(peak_db, 2),
        "threshold_dbfs": round(thresh_db, 2),
        "has_activity": True,
    }


def trim_clip_bp187(
    src_mp4: Path,
    out_mp4: Path,
    *,
    has_dialogue: bool = True,
    tail_s: float = DEFAULT_TAIL_S,
    min_duration_s: float = 2.0,
    max_duration_s: float = 6.0,
    start_offset_s: float = 0.0,
    fps: int = DEFAULT_FPS,
) -> dict[str, Any]:
    """Automatically trim dead post-speech / post-action tails per BP-187 (0.35-0.50s tail)."""
    src = Path(src_mp4)
    dst = Path(out_mp4)
    dst.parent.mkdir(parents=True, exist_ok=True)

    det = detect_speech_end_s(src, voice_bandpass=has_dialogue)
    orig_dur = float(det["duration_s"])
    tail = max(MIN_BP187_TAIL_S, min(MAX_BP187_TAIL_S, float(tail_s)))

    if has_dialogue and det["has_activity"]:
        target_end = float(det["speech_end_s"]) + tail
    else:
        target_end = min(orig_dur, start_offset_s + max_duration_s)

    target_dur = max(min_duration_s, min(max_duration_s, target_end - start_offset_s, orig_dur - start_offset_s))
    # Quantize to exact 24 fps frame boundaries
    n_frames = max(int(round(min_duration_s * fps)), int(round(target_dur * fps)))
    exact_dur = round(n_frames / float(fps), 4)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{start_offset_s:.4f}",
            "-t",
            f"{exact_dur:.4f}",
            "-i",
            str(src),
            "-vf",
            f"fps={fps}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "256k",
            str(dst),
        ],
        check=True,
    )
    actual_tail = round(max(0.0, (start_offset_s + exact_dur) - float(det["speech_end_s"])), 3)
    return {
        "input_path": str(src),
        "output_path": str(dst),
        "original_duration_s": round(orig_dur, 3),
        "start_offset_s": round(start_offset_s, 3),
        "speech_end_s": det["speech_end_s"],
        "trimmed_duration_s": exact_dur,
        "trimmed_removed_s": round(max(0.0, orig_dur - exact_dur), 3),
        "post_speech_tail_s": actual_tail,
        "bp187_pass": (not has_dialogue) or (actual_tail <= MAX_BP187_TAIL_S + 0.05),
    }
