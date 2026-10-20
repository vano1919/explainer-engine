"""The voice alteration layer (docs/AUDIO_SYSTEM.md, D-38): blend math, spec rules, and the timing contract."""

from __future__ import annotations

import copy
import shutil

import numpy as np
import pytest

from explainer_engine.audio import voice_layer as V

SR = 24000
SPEC = {"version": 1, "id": "test_voice", "base": "am_michael", "blend": [{"voice": "bm_george", "weight": 0.3}],
        "speed": 1.05, "pitch": {"semitones": -1.0, "formant": "preserved"},
        "tone": {"warmth_db": 2.0, "brightness_db": -1.0, "deess": 0.3}, "rvc": None}
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def voiced(seconds=3.0, f0=120.0, bursts=((0.4, 0.9), (1.3, 1.9), (2.2, 2.7))):
    """A harmonic 'voice' with a slow vibrato in three bursts of speech separated by silence."""
    t = np.arange(int(seconds * SR)) / SR
    phase = 2 * np.pi * (f0 * t + 2.0 * np.sin(2 * np.pi * 4 * t) / (2 * np.pi * 4))
    x = sum(np.sin(k * phase) / k for k in range(1, 12))
    env = np.zeros_like(t)
    for a, b in bursts:
        m = (t >= a) & (t < b)
        env[m] = np.minimum(1.0, np.minimum(t[m] - a, b - t[m]) / 0.03)
    return (0.4 * x * env / np.max(np.abs(x))).astype(np.float32)


def test_blend_is_a_normalised_weighted_mean_and_deterministic():
    a, b = np.ones((4, 1, 8), np.float32), np.full((4, 1, 8), 3.0, np.float32)
    out = V.blend_style([a, b], [0.75, 0.25])
    assert np.allclose(out, 1.5) and out.dtype == np.float32
    assert np.array_equal(out, V.blend_style([a, b], [3, 1]))  # weights are normalised
    assert np.array_equal(V.blend_style([a], [0.5]), a)
    with pytest.raises(ValueError):
        V.blend_style([a, b], [1.0])
    with pytest.raises(ValueError):
        V.blend_style([a, b], [-0.1, 1.1])
    with pytest.raises(ValueError):
        V.blend_style([a, np.ones((4, 1, 7), np.float32)], [1, 1])


def test_narrator_style_keeps_the_larger_share_on_the_base():
    styles = {"am_michael": np.zeros((2, 1, 4), np.float32), "bm_george": np.ones((2, 1, 4), np.float32)}
    out = V.narrator_style(styles.__getitem__, SPEC)
    assert np.allclose(out, 0.3)


def test_a_good_spec_validates_and_each_rule_is_enforced():
    assert V.validate_voice_spec(SPEC) == []
    cases = {
        "weight": lambda s: s["blend"][0].update(weight=0.6),
        "total": lambda s: s["blend"].append({"voice": "am_onyx", "weight": 0.3}),
        "pitch": lambda s: s["pitch"].update(semitones=-3.0),
        "twice": lambda s: s["blend"][0].update(voice="am_michael"),
        "extra key": lambda s: s.update(vibe="gritty"),
        "voice id": lambda s: s.update(base="not a voice"),
        "rvc without a licence": lambda s: s.update(rvc={"model": "x.pth", "speaker_consent": True}),
        "rvc without consent": lambda s: s.update(rvc={"model": "x.pth", "licence": "commercial_written",
                                                       "speaker_consent": False}),
    }
    for name, mutate in cases.items():
        spec = copy.deepcopy(SPEC)
        mutate(spec)
        assert V.validate_voice_spec(spec), name
    ok = copy.deepcopy(SPEC)
    ok["rvc"] = {"model": "x.pth", "licence": "own_training_data", "speaker_consent": True}
    assert V.validate_voice_spec(ok) == []


def test_the_committed_voice_specs_are_valid():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "assets" / "audio" / "voices"
    specs = sorted(root.glob("*.json"))
    assert specs, "no committed voice spec"
    for p in specs:
        V.load_voice_spec(p)


def test_measure_finds_the_pitch_of_a_synthetic_voice():
    m = V.measure(voiced(f0=120.0), SR, words=6)
    assert abs(m["f0_median_hz"] - 120.0) / 120.0 < 0.03
    assert m["f0_spread_st"] < 1.0 and m["wpm"] == pytest.approx(120.0)


@needs_ffmpeg
def test_pitch_shift_lowers_the_pitch_and_keeps_the_length_and_onsets():
    x = voiced()
    y = V.pitch_shift(x, SR, -2.0, "preserved")
    assert len(y) == len(x)
    ratio = V.measure(y, SR)["f0_median_hz"] / V.measure(x, SR)["f0_median_hz"]
    assert ratio == pytest.approx(2 ** (-2 / 12), rel=0.04)
    check = V.timing_preserved(x, y, SR)
    assert check["ok"], check


@needs_ffmpeg
def test_alter_returns_altered_audio_and_a_report_when_the_contract_holds():
    x = voiced()
    y, report = V.alter(x, SR, SPEC)
    assert report["used"] == "altered" and report["timing"]["ok"]
    assert len(y) == len(x) and not np.array_equal(x, y) and np.max(np.abs(y)) <= 0.97 + 1e-6


def test_timing_check_catches_a_stretch_a_shift_and_passes_identity():
    x = voiced()
    assert V.timing_preserved(x, x.copy(), SR)["ok"]
    stretched = np.interp(np.linspace(0, len(x) - 1, int(len(x) * 1.03)), np.arange(len(x)), x).astype(np.float32)
    assert not V.timing_preserved(x, stretched, SR)["ok"]  # 3 % longer = 90 ms over 3 s
    shifted = np.concatenate([np.zeros(int(0.05 * SR), np.float32), x])[:len(x)]
    assert V.timing_preserved(x, shifted, SR)["lag_ms"] == pytest.approx(50.0, abs=2.0)
    assert not V.timing_preserved(x, shifted, SR)["ok"]


def test_alter_falls_back_to_the_base_audio_when_the_contract_breaks(monkeypatch):
    x = voiced()
    monkeypatch.setattr(V, "pitch_shift", lambda a, sr, st, f: np.concatenate([np.zeros(int(0.08 * sr), np.float32), a])[:len(a)])
    y, report = V.alter(x, SR, SPEC)
    assert report["used"] == "base" and not report["timing"]["ok"] and np.array_equal(y, x)
    with pytest.raises(ValueError):
        V.alter(x, SR, SPEC, strict=False)


def test_shape_voice_keeps_the_length_and_warmth_adds_low_energy():
    x = voiced()
    y = V.shape_voice(x, SR, warmth_db=4.0)
    assert len(y) == len(x)
    spec_x, spec_y = np.abs(np.fft.rfft(x)), np.abs(np.fft.rfft(y))
    low = np.fft.rfftfreq(len(x), 1 / SR) < 200
    assert spec_y[low].sum() > 1.2 * spec_x[low].sum()


def test_wav_round_trip(tmp_path):
    x = voiced(1.0)
    V.write_wav(tmp_path / "a.wav", x, SR)
    y, sr = V.read_wav(tmp_path / "a.wav")
    assert sr == SR and len(y) == len(x) and np.max(np.abs(x - y)) < 1e-3
