"""qa/audio_present.py on its own: a finished master must carry an audio stream (the first tests live in test_trim_record.py;
these were added after the 2026-11-20 mutation spot-check, where the reported stream count was not checked against two)."""
from __future__ import annotations

import shutil
import subprocess

import pytest

from explainer_engine.qa import audio_present as AP

FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg and ffprobe")


def clip(tmp_path, name, audio_streams):
    f = tmp_path / name
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1:r=25"]
    for i in range(audio_streams):
        cmd += ["-f", "lavfi", "-i", f"sine=f={220 * (i + 1)}:d=1"]
    cmd += ["-map", "0:v"] + [a for i in range(audio_streams) for a in ("-map", f"{i + 1}:a")] + ["-shortest", str(f)]
    subprocess.run(cmd, check=True)
    return f


@needs_ffmpeg
@pytest.mark.parametrize("n", [1, 2])
def test_value_is_the_number_of_audio_streams(tmp_path, n):
    r = AP.audio_present(clip(tmp_path, f"a{n}.mkv", n))
    assert r["status"] == "PASS" and r["value"] == n and f"{n} audio stream" in r["detail"]


@needs_ffmpeg
def test_a_video_only_master_fails_with_zero(tmp_path):
    r = AP.audio_present(clip(tmp_path, "v.mp4", 0))
    assert r["status"] == "FAIL" and r["value"] == 0 and "no audio stream" in r["detail"]


@needs_ffmpeg
def test_a_file_ffprobe_cannot_read_raises_never_passes(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(RuntimeError, match="ffprobe could not read"):
        AP.audio_present(bad)
    with pytest.raises(FileNotFoundError):
        AP.audio_present(tmp_path / "none.mp4")


def test_a_missing_ffprobe_is_not_run_never_a_pass(tmp_path, monkeypatch):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"x")

    def no_ffprobe(*a, **k):
        raise FileNotFoundError("ffprobe")
    monkeypatch.setattr(AP.subprocess, "run", no_ffprobe)
    r = AP.audio_present(f)
    assert r["status"] == "NOT_RUN" and r["value"] is None and "ffprobe is missing" in r["detail"]


def test_ffprobe_is_asked_for_audio_streams_only(tmp_path, monkeypatch):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"x")
    seen = {}

    class R:
        returncode, stdout, stderr = 0, b'{"streams": [{"codec_name": "aac"}, {"codec_name": "opus"}]}', b""

    def fake(cmd, **k):
        seen["cmd"] = cmd
        return R()
    monkeypatch.setattr(AP.subprocess, "run", fake)
    r = AP.audio_present(f)
    cmd = seen["cmd"]
    assert cmd[cmd.index("-select_streams") + 1] == "a"
    assert r["status"] == "PASS" and r["value"] == 2


def test_kinds_and_main_exit_codes_without_ffmpeg(tmp_path, monkeypatch, capsys):
    assert ".mp4" in AP.audio_present.kinds and ".json" not in AP.audio_present.kinds
    monkeypatch.setattr(AP, "audio_present", lambda p: {"status": "FAIL", "value": 0, "detail": "the master has no audio stream"} if "v" in str(p)
                        else {"status": "PASS", "value": 2, "detail": "2 audio stream(s)"})
    assert AP.main(["a.mp4"]) == 0 and AP.main(["v.mp4"]) == 1 and AP.main(["a.mp4", "v.mp4"]) == 1
    out = capsys.readouterr().out
    assert "PASS" in out and "FAIL" in out
