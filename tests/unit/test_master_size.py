"""Master pixel size against the declared size (OR-E02)."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from explainer_engine.core import delivery
from explainer_engine.qa import master_size as ms

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe missing")


def make(path, w, h, audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=0.1:r=24"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_default_is_the_delivery_frame(tmp_path):
    w, h = delivery.size()
    res = ms.check_master_size(make(tmp_path / "m.mp4", w, h))
    assert res["status"] == "PASS" and res["value"] == f"{w}x{h}"


def test_wrong_size_fails_with_both_sizes(tmp_path):
    res = ms.check_master_size(make(tmp_path / "m.mp4", 1920, 1080))
    w, h = delivery.size()
    assert res["status"] == "FAIL" and "1920x1080" in res["detail"] and f"{w}x{h}" in res["detail"]


def test_a_declared_size_replaces_the_default(tmp_path):
    f = make(tmp_path / "m.mp4", 640, 360)
    for declared in ((640, 360), [640, 360], "640x360"):
        assert ms.check_master_size(f, declared)["status"] == "PASS"
    assert ms.check_master_size(f, (1280, 720))["status"] == "FAIL"


def test_missing_file_and_audio_only_are_not_run(tmp_path):
    assert ms.check_master_size(tmp_path / "none.mp4")["status"] == "NOT_RUN"
    wav = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.1", str(wav)], check=True)
    res = ms.check_master_size(wav, (640, 360))
    assert res["status"] == "NOT_RUN" and res["value"] is None and "no video stream" in res["detail"]


def test_not_a_media_file_is_not_run(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    assert ms.check_master_size(junk, (640, 360))["status"] == "NOT_RUN"


def test_bad_declared_size_raises(tmp_path):
    f = make(tmp_path / "m.mp4", 64, 64)
    for bad in ("big", (1, 2, 3), (0, 10), (True, 10)):
        with pytest.raises(ValueError):
            ms.check_master_size(f, bad)

