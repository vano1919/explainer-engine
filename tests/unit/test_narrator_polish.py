"""The narrator's standard polish (2026-11-01): the chain is fixed, adds bass, keeps the length, does not clip."""
import shutil
import subprocess

import numpy as np
import pytest

from explainer_engine.audio import narrator_polish as NP
from explainer_engine.audio import voice_check as VC
from explainer_engine.audio.voice_layer import read_wav, write_wav


def test_the_chain_is_the_creators_agreed_one():
    assert NP.CHAIN == ("volume=-0.6dB,highpass=f=60,afftdn=nr=8:nf=-50,bass=g=12:f=150:w=0.7,"
                        "equalizer=f=300:t=q:w=1:g=-2,alimiter=limit=0.95")


def test_the_channel_narrator_is_odom_and_oxley_is_retired():
    reg = VC.load_registry()
    assert VC.channel_voice(reg)["voice_id"] == "CcSJ2r3qw0XU9gJpEPyk"
    assert [v["status"] for v in reg["voices"] if v["voice_id"] == "NOpBlnGInO9m6vDvFkFC"] == ["retired"]
    assert VC.registry_errors(reg) == []


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_polish_lifts_the_bass_keeps_the_length_and_does_not_clip(tmp_path):
    sr = 24000
    t = np.arange(sr * 2) / sr
    x = (0.1 * np.sin(2 * np.pi * 110 * t) + 0.1 * np.sin(2 * np.pi * 2000 * t)).astype(np.float32)
    src, dst = tmp_path / "in.wav", tmp_path / "out.wav"
    write_wav(src, x, sr)
    NP.polish(src, dst)
    y, sr2 = read_wav(dst)
    assert sr2 == sr and abs(len(y) - len(x)) <= sr // 30
    spec_x, spec_y = np.abs(np.fft.rfft(x)), np.abs(np.fft.rfft(y[:len(x)]))
    k = int(110 * len(x) / sr)
    assert spec_y[k - 2:k + 3].max() > 2 * spec_x[k - 2:k + 3].max()  # 110 Hz is lifted well above 6 dB
    assert np.abs(y).max() <= 0.96


def test_a_failing_ffmpeg_is_a_config_error(tmp_path):
    from explainer_engine.core.errors import ConfigError
    with pytest.raises(ConfigError):
        NP.polish(tmp_path / "missing.wav", tmp_path / "o.wav")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_polish_in_place_keeps_the_length_and_reports_the_chain(tmp_path):
    sr = 24000
    x = (0.1 * np.sin(2 * np.pi * 110 * np.arange(sr) / sr)).astype(np.float32)
    wav = tmp_path / "narration.wav"
    write_wav(wav, x, sr)
    rep = NP.polish_in_place(wav)
    assert rep["chain"] == NP.CHAIN and abs(rep["seconds_after"] - rep["seconds_before"]) <= 1 / 30
    assert not (tmp_path / "narration.polish.wav").exists()
    y, _ = read_wav(wav)
    assert np.abs(y).max() > np.abs(x).max()  # the bass shelf made the 110 Hz tone louder

