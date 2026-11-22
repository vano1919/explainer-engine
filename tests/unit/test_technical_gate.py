import json
import shutil
import subprocess
from types import SimpleNamespace

import numpy as np
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
        "sharpness": 0.05,
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
    ("sharpness", 0.019),
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
    problems = tg.check_photo({"width": 1280, "height": 720, "sharpness": 0.05})
    assert problems
    assert any("width" in p for p in problems)
    assert any("height" in p for p in problems)


def test_load_limits_has_expected_keys():
    limits = tg.load_limits()
    assert set(limits) == {"option", "filters", "video", "audio", "photo"}
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


def test_sharpness_flat_gray_is_near_zero():
    flat = np.full((64, 64), 128, dtype=np.uint8)
    assert tg.sharpness_from_gray(flat) == 0.0


def test_sharpness_near_black_flat_returns_zero():
    near_black = np.full((64, 64), 1, dtype=np.uint8)
    assert tg.sharpness_from_gray(near_black) == 0.0


def test_sharpness_checkerboard_exceeds_flat():
    flat = np.full((64, 64), 128, dtype=np.uint8)
    checker = np.zeros((64, 64), dtype=np.uint8)
    checker[::2, ::2] = 200
    checker[1::2, 1::2] = 200
    assert tg.sharpness_from_gray(checker) > tg.sharpness_from_gray(flat)


def test_sharpness_invariant_to_brightness_scaling():
    bright = np.zeros((64, 64), dtype=np.float64)
    bright[::2, ::2] = 255.0
    bright[1::2, 1::2] = 255.0
    dark = bright * 0.05
    assert tg.sharpness_from_gray(dark) == pytest.approx(tg.sharpness_from_gray(bright), rel=1e-3)


def test_parse_blackdetect_sums_seconds():
    text = (
        "[blackdetect @ 0x1] black_start:1.0 black_end:2.5 black_duration:1.5\n"
        "[blackdetect @ 0x1] black_start:4.0 black_end:5.0 black_duration:1.0\n"
    )
    assert tg._parse_blackdetect(text, 10.0) == pytest.approx(2.5)


def test_parse_blackdetect_dangling_start_closes_at_duration():
    assert tg._parse_blackdetect("black_start:9.0", 10.0) == pytest.approx(1.0)


def test_parse_freezedetect_sums_seconds():
    text = (
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 0\n"
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_duration: 2.0\n"
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_end: 2.0\n"
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 5.0\n"
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_duration: 1.5\n"
        "[freezedetect @ 0x1] lavfi.freezedetect.freeze_end: 6.5\n"
    )
    assert tg._parse_freezedetect(text, 10.0) == pytest.approx(3.5)


def test_parse_freezedetect_dangling_start_closes_at_duration():
    assert tg._parse_freezedetect("freeze_start: 7.0", 10.0) == pytest.approx(3.0)


def test_check_video_black_half_fails():
    problems = tg.check_video(_video_metrics(black_frame_ratio=0.5))
    assert len(problems) == 1
    assert "black_frame_ratio" in problems[0]


def test_check_video_no_black_passes():
    assert tg.check_video(_video_metrics(black_frame_ratio=0.0)) == []


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are required",
)
def test_measure_video_fills_filter_keys(tmp_path):
    video = tmp_path / "tiny.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24:duration=2",
         "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    metrics = tg.measure_video(str(video))
    assert metrics["black_frame_ratio"] == 0.0
    assert metrics["frozen_frame_ratio"] is not None
    assert metrics["sharpness"] is not None
    assert isinstance(metrics["sharpness"], float)
    assert metrics["sharpness"] >= 0.0


def test_load_limits_filters_block_and_filter_strings():
    limits = tg.load_limits()
    assert limits["filters"]["freezedetect"]["d"] == 0.5
    black, freeze = tg._filter_strings()
    # chosen strings: the numbers come from the JSON filters block formatted from their float values, so pix_th 0.10
    # is written as "0.1" and the blackdetect string is exactly "blackdetect=d=0.1:pix_th=0.1"
    assert black == "blackdetect=d=0.1:pix_th=0.1"
    assert freeze == "freezedetect=n=0.003:d=0.5"


def test_measure_video_uses_filter_strings(monkeypatch):
    monkeypatch.setattr(tg.shutil, "which", lambda name: name)
    probe = {
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "avg_frame_rate": "24/1", "bit_rate": "5000000"}],
        "format": {"duration": "5.0"},
    }

    def fake_run(cmd, *args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps(probe), stderr="")

    seen = []
    monkeypatch.setattr(tg.subprocess, "run", fake_run)
    monkeypatch.setattr(tg, "_ffmpeg_filter_seconds", lambda path, vf, parser, duration: seen.append(vf) or 0.0)
    monkeypatch.setattr(tg, "measure_video_sharpness", lambda path, samples=8: 0.05)
    tg.measure_video("clip.mp4")
    assert seen == ["blackdetect=d=0.1:pix_th=0.1", "freezedetect=n=0.003:d=0.5"]


def _no_melt_metrics(**overrides):
    metrics = {"residual_motion_per_frame": 0.01, "residual_drift": 0.05}
    metrics.update(overrides)
    return metrics


def test_check_no_melt_passes_below_limits():
    assert tg.check_no_melt(_no_melt_metrics()) == []


@pytest.mark.parametrize("key,value", [
    ("residual_motion_per_frame", 0.06),
    ("residual_drift", 0.25),
])
def test_check_no_melt_each_limit_violated_separately(key, value):
    problems = tg.check_no_melt(_no_melt_metrics(**{key: value}))
    assert len(problems) == 1
    assert key in problems[0]


@pytest.mark.parametrize("key", ["residual_motion_per_frame", "residual_drift"])
def test_check_no_melt_missing_key_fails_closed(key):
    metrics = _no_melt_metrics()
    metrics.pop(key)
    problems = tg.check_no_melt(metrics)
    assert len(problems) == 1
    assert f"missing metric {key}" in problems[0]


def test_check_video_animated_without_no_melt_fails_closed():
    problems = tg.check_video(_video_metrics(animated=True))
    assert any("missing metric" in p for p in problems)


def test_check_video_animated_absent_is_unchanged():
    assert tg.check_video(_video_metrics()) == []


def test_measure_video_zero_duration_raises(monkeypatch):
    # PY-01: a zero-length video has no black or freeze ratio to measure; it must be rejected, not divided by zero.
    import json as _json
    import subprocess as _sp

    monkeypatch.setattr(tg.shutil, "which", lambda name: "/usr/bin/" + name)
    payload = {"streams": [{"codec_type": "video", "width": 1920, "height": 1080}], "format": {"duration": "0.0"}}
    monkeypatch.setattr(tg.subprocess, "run", lambda *a, **k: _sp.CompletedProcess(a, 0, _json.dumps(payload), ""))
    with pytest.raises(RuntimeError, match="zero"):
        tg.measure_video("zero.mp4")


def test_black_interval_open_at_clip_end_is_counted_to_duration():
    # PY-01 acceptance: black_start 9.0 in a 10.0 s clip gives 1.0 s of black.
    assert tg._parse_blackdetect("black_start:9.0", 10.0) == pytest.approx(1.0)
