"""HF-5 (Truce 1914 assembly, FL-408, FL-409, TD-306): ``voice.compose`` lowers a loud clip to the read's level (the clamp
holds only for boosts) and keeps the sound after a clip's last measured span at full level; the report says what it did."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from explainer_engine.videolane import voice as VV

RATE = VV.RATE


def _wav(path: Path, x: np.ndarray) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def _tone(seconds: float, amp: float) -> np.ndarray:
    n = int(seconds * RATE)
    return (amp * np.sin(2 * np.pi * 220 * np.arange(n) / RATE)).astype(np.float32)


def _timing(frames=48):
    return {"fps": 24, "total_frames": 24 * 4 + frames, "inserts": [{"shot_id": "C1", "at_read_frame": 48, "frames": frames}],
            "shots": {"C1": {"start_frame": 48}}}


def _db(x) -> float:
    return 20 * np.log10(float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) + 1e-9)


def test_a_clip_15_db_over_the_read_lands_at_the_reads_level(tmp_path):
    read = _wav(tmp_path / "read.wav", _tone(4.0, 0.05))                      # about -29 dBFS rms
    clip = _wav(tmp_path / "clip.wav", _tone(2.0, 0.05 * 10 ** (15 / 20)))   # 15 dB louder
    rep = VV.compose(_timing(), read, {"C1": {"path": str(clip), "speech": [[0.0, 2.0]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 4.0]])
    lay = next(p for p in rep["laid"] if p["what"] == "clip")
    assert abs(lay["gain_db"] + 15.0) < 0.2 and lay["boost_clamped"] is False      # no -12 dB floor (FL-408)
    y = VV.read_mono(tmp_path / "v.wav")
    mid = y[int(2.5 * RATE):int(3.5 * RATE)]                                      # inside the clip, clear of the fades
    assert abs(_db(mid) - _db(y[:RATE])) < 0.5


def test_a_boost_is_still_clamped_and_says_so(tmp_path):
    read = _wav(tmp_path / "read.wav", _tone(4.0, 0.2))
    clip = _wav(tmp_path / "clip.wav", _tone(2.0, 0.2 * 10 ** (-20 / 20)))    # 20 dB under the read
    rep = VV.compose(_timing(), read, {"C1": {"path": str(clip), "speech": [[0.0, 2.0]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 4.0]])
    lay = next(p for p in rep["laid"] if p["what"] == "clip")
    assert lay["gain_db"] == VV.GAIN_MAX_DB and lay["boost_clamped"] is True and lay["wanted_gain_db"] > VV.GAIN_MAX_DB


def test_the_sound_after_the_last_measured_span_keeps_full_level(tmp_path):
    read = _wav(tmp_path / "read.wav", _tone(4.0, 0.05))
    clip = _wav(tmp_path / "clip.wav", _tone(2.0, 0.05))
    # the detector says the line ends at 1.2 s; the clip still speaks to 1.5 s and to the shot's end
    rep = VV.compose(_timing(), read, {"C1": {"path": str(clip), "speech": [[0.2, 1.2]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 4.0]])
    y = VV.read_mono(tmp_path / "v.wav")
    at = lambda s: float(np.abs(y[int((2.0 + s) * RATE) - 480:int((2.0 + s) * RATE) + 480]).max())   # the shot starts at 2.0 s
    assert at(1.5) > 0.045                                                          # 0.3 s after the span: full level
    assert at(1.5) > 0.9 * at(0.7)
    assert "peak_dbfs" in rep and rep["peak_dbfs"] < 0.0
