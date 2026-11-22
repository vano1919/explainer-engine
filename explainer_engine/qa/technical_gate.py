"""Objective technical gates for video, photo and audio. Every check is a pure function over measured numbers, so tests
need no media. The owner's taste is not checked here."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

_CONFIG = "technical_gate.json"
_VIDEO_KEYS = ("width", "height", "fps", "bitrate_kbps", "black_frame_ratio", "frozen_frame_ratio", "sharpness")
_AUDIO_KEYS = ("lufs", "true_peak_db", "clipped_ratio", "speech_to_noise_db", "silence_ratio")
_PHOTO_KEYS = ("width", "height", "sharpness")


def load_limits(path: str | Path | None = None) -> dict:
    """Load the provisional limits; by default the JSON beside this module."""
    p = Path(path) if path is not None else Path(__file__).with_name(_CONFIG)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _missing(metrics: dict, keys: tuple[str, ...]) -> list[str]:
    return [f"missing metric {k}" for k in keys if k not in metrics or metrics[k] is None]


def check_video(metrics: dict) -> list[str]:
    limits = load_limits()["video"]
    problems = _missing(metrics, _VIDEO_KEYS)
    if problems:
        return problems
    if metrics["width"] < limits["min_width"]:
        problems.append(f"width below minimum {limits['min_width']}")
    if metrics["height"] < limits["min_height"]:
        problems.append(f"height below minimum {limits['min_height']}")
    if metrics["fps"] < limits["fps_min"] or metrics["fps"] > limits["fps_max"]:
        problems.append(f"fps outside [{limits['fps_min']}, {limits['fps_max']}]")
    if metrics["bitrate_kbps"] < limits["min_bitrate_kbps"]:
        problems.append(f"bitrate_kbps below minimum {limits['min_bitrate_kbps']}")
    if metrics["black_frame_ratio"] > limits["max_black_frame_ratio"]:
        problems.append(f"black_frame_ratio above maximum {limits['max_black_frame_ratio']}")
    if metrics["frozen_frame_ratio"] > limits["max_frozen_frame_ratio"]:
        problems.append(f"frozen_frame_ratio above maximum {limits['max_frozen_frame_ratio']}")
    if metrics["sharpness"] < limits["min_sharpness"]:
        problems.append(f"sharpness below minimum {limits['min_sharpness']}")
    return problems


def check_audio(metrics: dict) -> list[str]:
    limits = load_limits()["audio"]
    problems = _missing(metrics, _AUDIO_KEYS)
    if problems:
        return problems
    if metrics["lufs"] < limits["lufs_min"] or metrics["lufs"] > limits["lufs_max"]:
        problems.append(f"lufs outside [{limits['lufs_min']}, {limits['lufs_max']}]")
    if metrics["true_peak_db"] > limits["true_peak_max_db"]:
        problems.append(f"true_peak_db above maximum {limits['true_peak_max_db']}")
    if metrics["clipped_ratio"] > limits["max_clipped_samples_ratio"]:
        problems.append(f"clipped_ratio above maximum {limits['max_clipped_samples_ratio']}")
    if metrics["speech_to_noise_db"] < limits["min_speech_to_noise_db"]:
        problems.append(f"speech_to_noise_db below minimum {limits['min_speech_to_noise_db']}")
    if metrics["silence_ratio"] > limits["max_silence_ratio"]:
        problems.append(f"silence_ratio above maximum {limits['max_silence_ratio']}")
    return problems


def check_photo(metrics: dict) -> list[str]:
    limits = load_limits()["photo"]
    problems = _missing(metrics, _PHOTO_KEYS)
    if problems:
        return problems
    if metrics["width"] < limits["min_width"]:
        problems.append(f"width below minimum {limits['min_width']}")
    if metrics["height"] < limits["min_height"]:
        problems.append(f"height below minimum {limits['min_height']}")
    if metrics["sharpness"] < limits["min_sharpness"]:
        problems.append(f"sharpness below minimum {limits['min_sharpness']}")
    return problems


def _float_match(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text, re.S)
    return float(m.group(1)) if m else None


def _rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        num, den = value.split("/", 1)
        return float(num) / float(den) if float(den) else None
    except (ValueError, ZeroDivisionError):
        return None


def sharpness_from_gray(gray) -> float:
    """Scale-invariant sharpness of a grayscale frame: variance of the Laplacian (frame scaled to 0..1) divided by the
    variance of the frame itself (also 0..1). Frames with standard deviation below 2/255 are treated as flat and return
    0.0."""
    arr = np.asarray(gray, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    norm = arr / 255.0
    std = float(norm.std())
    if std < 2.0 / 255.0:
        return 0.0
    return float(cv2.Laplacian(norm, cv2.CV_64F).var()) / (std * std)


def _parse_blackdetect(text: str, total_duration: float) -> float:
    """Sum the black seconds reported by ffmpeg's blackdetect filter. A dangling black_start is closed at
    ``total_duration`` (a run that lasts to the end of the stream)."""
    total = 0.0
    pending: float | None = None
    for line in text.splitlines():
        if "black_start:" not in line and "black_duration:" not in line and "black_end:" not in line:
            continue
        duration = _float_match(r"black_duration:\s*(-?\d+(?:\.\d+)?)", line)
        if duration is not None:
            total += duration
            pending = None
            continue
        start = _float_match(r"black_start:\s*(-?\d+(?:\.\d+)?)", line)
        end = _float_match(r"black_end:\s*(-?\d+(?:\.\d+)?)", line)
        if start is not None and end is not None:
            total += end - start
            pending = None
        elif start is not None:
            pending = start
        elif end is not None and pending is not None:
            total += end - pending
            pending = None
    if pending is not None:
        total += total_duration - pending
    return total


def _parse_freezedetect(text: str, total_duration: float) -> float:
    """Sum the frozen seconds reported by ffmpeg's freezedetect filter. A dangling freeze_start is closed at
    ``total_duration`` (a run that lasts to the end of the stream)."""
    total = 0.0
    pending: float | None = None
    for line in text.splitlines():
        duration = _float_match(r"freeze_duration:\s*(-?\d+(?:\.\d+)?)", line)
        if duration is not None:
            total += duration
            pending = None
            continue
        start = _float_match(r"freeze_start:\s*(-?\d+(?:\.\d+)?)", line)
        end = _float_match(r"freeze_end:\s*(-?\d+(?:\.\d+)?)", line)
        if start is not None and end is not None:
            total += end - start
            pending = None
        elif start is not None:
            pending = start
        elif end is not None and pending is not None:
            total += end - pending
            pending = None
    if pending is not None:
        total += total_duration - pending
    return total


def _ffmpeg_filter_seconds(path: str, vf: str, parser, duration: float) -> float:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH")
    cmd = ["ffmpeg", "-v", "info", "-i", path, "-vf", vf, "-an", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")
    return parser(proc.stderr, duration)


def measure_video_sharpness(path: str, samples: int = 8) -> float:
    """Median contrast-normalised sharpness over up to ``samples`` frames sampled evenly across the video."""
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise RuntimeError("cv2 could not open the video")
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            n = min(samples, frame_count)
            idxs = [int(i * (frame_count - 1) / max(n - 1, 1)) for i in range(n)]
        else:
            idxs = list(range(samples))
        values = []
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            values.append(sharpness_from_gray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
    finally:
        cap.release()
    if not values:
        raise RuntimeError("cv2 could not decode any frame for sharpness")
    return float(np.median(values))


def measure_video(path: str) -> dict:
    """Measure width, height, fps and bitrate with ffprobe, black/frozen frame ratios with ffmpeg filters and
    contrast-normalised sharpness with cv2. Ratios are clamped to [0, 1]."""
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe not found on PATH")
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if stream is None:
        raise RuntimeError("no video stream found")
    duration = data.get("format", {}).get("duration")
    if duration is None:
        raise RuntimeError("ffprobe did not report a duration")
    duration = float(duration)
    if duration < 1e-6:
        raise RuntimeError("video duration is zero")
    bit_rate = stream.get("bit_rate") or data.get("format", {}).get("bit_rate")
    black_seconds = _ffmpeg_filter_seconds(path, "blackdetect=d=0.1:pix_th=0.10", _parse_blackdetect, duration)
    frozen_seconds = _ffmpeg_filter_seconds(path, "freezedetect=n=0.003:d=0.5", _parse_freezedetect, duration)
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": _rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate")),
        "bitrate_kbps": int(bit_rate) / 1000 if bit_rate else None,
        "black_frame_ratio": min(max(black_seconds / duration, 0.0), 1.0),
        "frozen_frame_ratio": min(max(frozen_seconds / duration, 0.0), 1.0),
        "sharpness": measure_video_sharpness(path),
    }


def measure_audio(path: str) -> dict:
    """Measure integrated loudness and true peak with ffmpeg (ebur128 plus volumedetect). Clipped ratio, speech-to-noise
    and silence ratio stay None unless the caller computes them; check_audio then fails closed."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true,volumedetect",
           "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")
    text = proc.stderr
    return {
        "lufs": _float_match(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS", text),
        "true_peak_db": _float_match(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", text),
        "clipped_ratio": None,
        "speech_to_noise_db": None,
        "silence_ratio": None,
    }
