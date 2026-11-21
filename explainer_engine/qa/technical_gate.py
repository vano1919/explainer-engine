"""Objective technical gates for video, photo and audio. Every check is a pure function over measured numbers, so tests
need no media. The owner's taste is not checked here."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

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


def measure_video(path: str) -> dict:
    """Measure width, height, fps and bitrate with ffprobe. Black/frozen frame ratios and sharpness need ffmpeg filters
    and stay None, so check_video fails closed unless the caller supplies them."""
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
    bit_rate = stream.get("bit_rate") or data.get("format", {}).get("bit_rate")
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": _rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate")),
        "bitrate_kbps": int(bit_rate) / 1000 if bit_rate else None,
        "black_frame_ratio": None,
        "frozen_frame_ratio": None,
        "sharpness": None,
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
