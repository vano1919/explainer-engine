"""Registering connector-generated sounds into the library (D-61): conversion, loop defaults, source and licence record."""

from __future__ import annotations

import shutil

import numpy as np
import pytest

from explainer_engine.audio import register, sfx_library


def _wav(path, seconds=0.4, rate=16000, channels=1):
    import wave
    t = np.arange(int(seconds * rate)) / rate
    mono = (np.sin(2 * np.pi * 330 * t) * 0.4 * 32767).astype(np.int16)
    data = np.repeat(mono[:, None], channels, axis=1).reshape(-1) if channels > 1 else mono
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())
    return path


def test_register_mono_wav_music_defaults_to_loop(tmp_path):
    src = _wav(tmp_path / "take.wav")
    entry = register.register(src, root=tmp_path / "lib", name="heist_tension", take=1, category="music",
                              tags=["tense", "heist"], model="eleven_music_v2_5", prompt="tense heist bed", cost_usd=0.5)
    assert entry["loop"] is True
    assert entry["source"] == {"kind": "elevenlabs", "model": "eleven_music_v2_5", "prompt": "tense heist bed",
                               "cost_usd_estimate": 0.5}
    assert entry["review"]["human"] == "not_listened"
    assert sfx_library.validate(tmp_path / "lib") == []
    assert [m["id"] for m in sfx_library.find(tmp_path / "lib", tags=["heist"])] == ["heist_tension__v1"]


def test_register_foley_defaults_to_one_shot(tmp_path):
    src = _wav(tmp_path / "hit.wav")
    entry = register.register(src, root=tmp_path / "lib", name="door_slam", take=1, category="foley", tags=["door"])
    assert entry["loop"] is False


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg converts non-mono input")
def test_register_converts_stereo_through_ffmpeg(tmp_path):
    src = _wav(tmp_path / "stereo.wav", channels=2)
    entry = register.register(src, root=tmp_path / "lib", name="wide_bed", take=1, category="music", tags=["bed"])
    samples, rate = sfx_library.read_wav(tmp_path / "lib" / entry["file"])
    assert rate == 16000 and len(samples) > 0
