from types import SimpleNamespace

import pytest

from explainer_engine.qa import technical_gate as tg


def _video_metrics(**overrides):
    metrics = {
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "bitrate_kbps": 5000,
        "black_frame_ratio": 0.0,
        "frozen_frame_ratio": 0.0,
        "sharpness": 0.6,
    }
    metrics.update(overrides)
    return metrics


def _audio_metrics(**overrides):
    metrics = {
        "lufs": -15.0,
        "true_peak_db": -2.0,
        "clipped_ratio": 0.0,
        "speech_to_noise_db": 25.0,
        "silence_ratio": 0.1,
    }
    metrics.update(overrides)
    return metrics


def test_video_metrics_passing_all_limits_is_empty():
    assert tg.check_video(_video_metrics()) == []


@pytest.mark.parametrize("key,value", [
    ("width", 1919),
    ("height", 1079),
    ("fps", 23.0),
    ("fps", 61.0),
    ("bitrate_kbps", 3999),
    ("black_frame_ratio", 0.03),
    ("frozen_frame_ratio", 0.06),
    ("sharpness", 0.49),
])
def test_video_each_limit_violated_separately(key, value):
    assert len(tg.check_video(_video_metrics(**{key: value}))) == 1


def test_video_missing_metric_names_it():
    metrics = _video_metrics()
    metrics.pop("sharpness")
    problems = tg.check_video(metrics)
    assert len(problems) == 1
    assert "sharpness" in problems[0]


def test_audio_lufs_too_low_fails():
    problems = tg.check_audio(_audio_metrics(lufs=-20.0))
    assert len(problems) == 1
    assert "lufs" in problems[0]


def test_audio_lufs_in_range_passes():
    assert tg.check_audio(_audio_metrics(lufs=-15.0)) == []


def test_audio_true_peak_too_high_fails():
    problems = tg.check_audio(_audio_metrics(true_peak_db=-0.5))
    assert len(problems) == 1
    assert "true_peak_db" in problems[0]


def test_audio_missing_lufs_fails_closed():
    metrics = _audio_metrics()
    metrics.pop("lufs")
    problems = tg.check_audio(metrics)
    assert len(problems) == 1
    assert "lufs" in problems[0]


def test_photo_1280x720_fails():
    problems = tg.check_photo({"width": 1280, "height": 720, "sharpness": 0.6})
    assert problems
    assert any("width" in p for p in problems)
    assert any("height" in p for p in problems)


def test_load_limits_has_expected_keys():
    limits = tg.load_limits()
    assert set(limits) == {"option", "video", "audio", "photo"}
    assert limits["video"]["min_width"] == 1920
    assert limits["audio"]["max_silence_ratio"] == 0.4
    assert limits["photo"]["min_height"] == 1080


def test_measure_video_requires_ffprobe(monkeypatch):
    monkeypatch.setattr(tg.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        tg.measure_video("missing.mp4")


def test_measure_audio_uses_argument_list(monkeypatch):
    monkeypatch.setattr(tg.shutil, "which", lambda name: name)
    calls = []
    stderr = "Integrated loudness:\n  I: -15.0 LUFS\n\nTrue peak:\n  Peak: -2.0 dBFS\n"

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr=stderr)

    monkeypatch.setattr(tg.subprocess, "run", fake_run)
    metrics = tg.measure_audio("voice.wav")
    assert metrics["lufs"] == -15.0
    assert metrics["true_peak_db"] == -2.0
    assert calls
    cmd, kwargs = calls[0]
    assert isinstance(cmd, list)
    assert kwargs.get("shell") is not True
