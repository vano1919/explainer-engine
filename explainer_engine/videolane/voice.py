"""The voice track of an episode with clip-spoken shots (VL-13, docs/VIDEO_LANE.md): the narrator's read, split where the
clock inserted a clip-timed shot (``timing.inserts``), with each LTX clip's own speech laid on its shot's frames. This one file
is the ``narration`` the stem renderer (``audio/stems.render``) ducks the music and the bed under, so:

* the LTX dialogue is heard once (the read never speaks a clip-spoken line, ``timing.read_order``; this track carries the
  clip's line exactly where its picture is), never twice;
* the bed and the music duck under the dialogue as under the narrator (BP-52: ducking, never muting), and keep running
  across the cuts (the bed belongs to the place, ``episode/sound_plan``);
* every clip's speech is set to the read's speech level (LTX speakers differ by up to 9 dB, W1), and the clip's own track
  between its lines stays in, 15 dB down (``scene_join.BETWEEN_LINES_DB``): LTX's room and effects colour the gap, the bed
  carries it, and each clip's own track fades in and out over BP-191's ``clip_fade_s`` at its cuts.

The sound files belong to the AV thread (``scene_join``, ``stems``); this module only reads their helpers.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

RATE = 48000
CLIP_FADE_S = float(np.mean(SR.T("BP-191", "clip_fade_s")))
SEAM_FADE_S = float(SR.T("BP-188", "seam_fade_s"))   # FA-13: the de-click minimum at every read piece and clip edge
GAIN_MAX_DB = 12.0          # engineering default: a clip quieter than this under the read is a bad take, not a level to fix


def read_mono(path: Path, rate: int = RATE) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def write_mono(path: Path, x: np.ndarray, rate: int = RATE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def _rms_db(x: np.ndarray) -> float:
    return 20 * np.log10(float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) + 1e-9) if len(x) else -120.0


def speech_level(x: np.ndarray, spans, rate: int = RATE) -> float:
    parts = [x[int(a * rate):int(b * rate)] for a, b in spans or []]
    parts = [p for p in parts if len(p)]
    return _rms_db(np.concatenate(parts)) if parts else _rms_db(x)


def compose(timing: dict, read: Path | None, clip_audio: dict, out: Path, *, read_speech=None) -> dict:
    """Write the voice track. ``clip_audio``: ``{shot_id: {"path": trimmed clip, "speech": [[s, e]]}}`` for every inserted
    shot. Returns what was laid where (the report the QA reads to prove the line is heard once)."""
    from explainer_engine.production.scene_join import between_lines_gain
    fps = int(timing["fps"])
    total = int(round(timing["total_frames"] / fps * RATE))
    y = np.zeros(total, np.float32)
    x = read_mono(read) if read else np.zeros(0, np.float32)
    ref_db = speech_level(x, read_speech) if len(x) else -20.0
    inserts = sorted(timing.get("inserts") or [], key=lambda i: i["at_read_frame"])
    # the read in pieces: read frame r -> episode frame r + (frames inserted before r)
    cuts = [0] + [i["at_read_frame"] for i in inserts] + [None]
    shift, laid = 0, []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        sa = int(round(a / fps * RATE))
        sb = len(x) if b is None else min(len(x), int(round(b / fps * RATE)))
        if sb > sa:
            d = int(round((a + shift) / fps * RATE))
            piece = x[sa:sb][: max(0, total - d)].copy()
            # FA-13 / BP-188: a de-click fade on each edge where the read was split for a clip (never on the read's own ends)
            f = min(len(piece) // 2, int(SEAM_FADE_S * RATE))
            if f and k > 0:
                piece[:f] *= np.linspace(0, 1, f, dtype=np.float32)
            if f and b is not None:
                piece[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
            y[d:d + len(piece)] += piece
            laid.append({"what": "read", "read_s": [round(sa / RATE, 3), round(sb / RATE, 3)],
                         "at_s": round(d / RATE, 3)})
        if k < len(inserts):
            shift += int(inserts[k]["frames"])
    for ins in inserts:
        sid = ins["shot_id"]
        c = clip_audio.get(sid)
        if c is None:
            raise ContractError(f"{sid}: a clip-timed shot without its clip sound")
        start = int(round(timing["shots"][sid]["start_frame"] / fps * RATE))
        n = int(round(int(ins["frames"]) / fps * RATE))
        a = read_mono(Path(c["path"]))[:n]
        if len(a) < n:
            a = np.pad(a, (0, n - len(a)))
        spans = c.get("speech") or []
        gain_db = max(-GAIN_MAX_DB, min(GAIN_MAX_DB, ref_db - speech_level(a, spans))) if spans else 0.0
        a = a * (10 ** (gain_db / 20)) * between_lines_gain(len(a), spans, RATE)
        k = min(len(a) // 2, int(max(CLIP_FADE_S, SEAM_FADE_S) * RATE))
        if k:
            r = np.linspace(0, 1, k, dtype=np.float32)
            a[:k] *= r
            a[-k:] *= r[::-1]
        y[start:start + n] += a[: max(0, total - start)]
        laid.append({"what": "clip", "shot_id": sid, "at_s": round(start / RATE, 3), "seconds": round(n / RATE, 3),
                     "gain_db": round(gain_db, 2), "speech": spans})
    write_mono(out, y)
    return {"path": str(out), "seconds": round(total / RATE, 4), "read_level_db": round(ref_db, 2), "laid": laid}
