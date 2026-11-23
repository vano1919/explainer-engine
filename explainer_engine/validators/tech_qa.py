"""Technical QA of a rendered file (final plan S16, W2): fps, frame count, black picture, frozen picture, silence and the audio/video
start offset, measured with ffprobe and ffmpeg's blackdetect / freezedetect / silencedetect (BP-211, BP-54). Every row is NOT_RUN when
ffmpeg or ffprobe is absent (or the stream it needs is), never a pass."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("VAL-QA-01", "VAL-QA-02", "VAL-QA-03", "VAL-QA-04", "VAL-QA-05", "VAL-QA-06")


def tools_present() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(path) -> dict:
    """ffprobe: ``fps``, ``frames`` (counted), ``duration_s``, ``video_start_s``, ``audio_start_s`` (None without that stream)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    doc = json.loads(out)
    v = next((s for s in doc["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in doc["streams"] if s["codec_type"] == "audio"), None)
    res = {"fps": float(Fraction(v["r_frame_rate"])) if v else None,
           "frames": int(v["nb_read_frames"]) if v and v.get("nb_read_frames") not in (None, "N/A") else None,
           "duration_s": float(doc["format"].get("duration") or 0.0),
           "video_start_s": float(v.get("start_time") or 0.0) if v else None,
           "audio_start_s": float(a.get("start_time") or 0.0) if a else None}
    return res


def _run_filters(path, vf: str, af: str | None) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", vf]
    if af:
        cmd += ["-af", af]
    return subprocess.run(cmd + ["-f", "null", "-"], capture_output=True, text=True).stderr


def _intervals(stderr: str, start_re: str, dur_re: str, total: float) -> list[tuple[float, float]]:
    """(start, duration) pairs; a start without a duration runs to the end of the file."""
    starts = [float(x) for x in re.findall(start_re, stderr)]
    durs = [float(x) for x in re.findall(dur_re, stderr)]
    out = []
    for i, s in enumerate(starts):
        out.append((s, durs[i] if i < len(durs) else max(0.0, total - s)))
    return out


def findings(path, info: dict | None = None) -> dict:
    """The black, frozen and silent intervals of a file, with BP-211's detectors: ``{black, frozen, silent}`` lists of (start, s)."""
    info = info or probe(path)
    t = {k: C.T("BP-211", k) for k in ("black_min_s", "black_pix_th", "freeze_min_s", "freeze_noise_db", "silence_min_s", "silence_noise_db")}
    if None in t.values():
        raise KeyError("BP-211 thresholds missing")
    vf = f"blackdetect=d={t['black_min_s']}:pix_th={t['black_pix_th']},freezedetect=n={t['freeze_noise_db']}dB:d={t['freeze_min_s']}"
    af = f"silencedetect=n={t['silence_noise_db']}dB:d={t['silence_min_s']}" if info["audio_start_s"] is not None else None
    err = _run_filters(path, vf, af)
    total = info["duration_s"]
    return {"black": _intervals(err, r"black_start:([\d.]+)", r"black_duration:([\d.]+)", total),
            "frozen": _intervals(err, r"freeze_start: ([\d.]+)", r"freeze_duration: ([\d.]+)", total),
            "silent": _intervals(err, r"silence_start: ([\d.]+)", r"silence_duration: ([\d.]+)", total)
            if info["audio_start_s"] is not None else None}


def check_file(path, expected: dict | None = None) -> list[dict]:
    """The six rows. ``expected``: ``{"fps": 24, "frames": 1440}`` from the episode manifest (a missing key is NOT_RUN for that row)."""
    gates = RULE_IDS
    if not tools_present():
        return [G.row(g, None, "NOT_RUN: ffmpeg/ffprobe is not installed") for g in gates]
    if not Path(path).is_file():
        return [G.row(g, None, f"NOT_RUN: {path} does not exist") for g in gates]
    expected = expected or {}
    try:
        info = probe(path)
        found = findings(path, info)
    except (subprocess.CalledProcessError, KeyError, ValueError) as exc:
        return [G.row(g, None, f"NOT_RUN: the file could not be measured ({type(exc).__name__}: {exc})") for g in gates]
    rows = []
    if expected.get("fps") is None or info["fps"] is None:
        rows.append(G.row("VAL-QA-01", None, "NOT_RUN: no expected fps or no video stream"))
    else:
        rows.append(G.row("VAL-QA-01", abs(info["fps"] - float(expected["fps"])) < 1e-3, f"{info['fps']:.3f} fps; expected {expected['fps']}",
                          info["fps"], level=G.FAIL))
    if expected.get("frames") is None or info["frames"] is None:
        rows.append(G.row("VAL-QA-02", None, "NOT_RUN: no expected frame count or none counted"))
    else:
        rows.append(G.row("VAL-QA-02", info["frames"] == int(expected["frames"]), f"{info['frames']} frames; expected {expected['frames']}",
                          info["frames"], level=G.FAIL))
    for gate, key, what in (("VAL-QA-03", "black", "black picture"), ("VAL-QA-04", "frozen", "frozen picture"),
                            ("VAL-QA-05", "silent", "silence")):
        iv = found[key]
        if iv is None:
            rows.append(G.row(gate, None, f"NOT_RUN: no audio stream to look for {what}"))
        else:
            rows.append(C.check(gate, not iv, "BP-211", f"{len(iv)} stretch(es) of {what}: {[(round(a, 2), round(b, 2)) for a, b in iv[:6]]}"
                                if iv else f"no {what} of the length BP-211 names", iv[:20]))
    early, late = C.T("BP-54", "early_max_ms"), C.T("BP-54", "late_max_ms")
    if info["audio_start_s"] is None or info["video_start_s"] is None:
        rows.append(G.row("VAL-QA-06", None, "NOT_RUN: the file lacks an audio or a video stream"))
    elif early is None or late is None:
        rows.append(C.missing_threshold("VAL-QA-06", "BP-54", "early_max_ms/late_max_ms"))
    else:
        off_ms = (info["audio_start_s"] - info["video_start_s"]) * 1000   # negative: the sound starts early
        rows.append(C.check("VAL-QA-06", -early <= off_ms <= late, "BP-54", f"audio starts {off_ms:+.0f} ms from the picture "
                            f"(window -{early}..+{late})", off_ms))
    return rows
