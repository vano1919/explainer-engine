"""W2: technical QA validators on tiny synthetic media made in the test (nothing committed); NOT_RUN when ffmpeg is absent."""
from __future__ import annotations

import subprocess

import pytest

from explainer_engine.qa import gates as G
from explainer_engine.validators import tech_qa as T

needs_ffmpeg = pytest.mark.skipif(not T.tools_present(), reason="ffmpeg/ffprobe not installed")


def _make(path, video: str, audio: str | None, seconds: int = 4, rate: int = 24):
    spec = f"color=c=black:s=64x64:r={rate}:d={seconds}" if video == "black" else f"{video}=size=64x64:rate={rate}:duration={seconds}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", spec]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"{audio}:duration={seconds}"]
    cmd += ["-pix_fmt", "yuv420p", "-c:v", "libx264"] + (["-c:a", "aac", "-shortest"] if audio else []) + [str(path)]
    subprocess.run(cmd, check=True)
    return path


def _by(rows):
    return {r["gate"]: r["status"] for r in rows}


@needs_ffmpeg
def test_a_clean_file_passes_every_row(tmp_path):
    f = _make(tmp_path / "ok.mp4", "testsrc", "sine=frequency=440")
    rows = T.check_file(f, {"fps": 24, "frames": 96})
    assert _by(rows) == {g: G.PASS for g in T.RULE_IDS}, rows


@needs_ffmpeg
def test_wrong_fps_and_frame_count_block(tmp_path):
    f = _make(tmp_path / "ok.mp4", "testsrc", "sine=frequency=440")
    got = _by(T.check_file(f, {"fps": 30, "frames": 100}))
    assert got["VAL-QA-01"] == G.FAIL and got["VAL-QA-02"] == G.FAIL


@needs_ffmpeg
def test_black_frozen_and_silent_are_found(tmp_path):
    f = _make(tmp_path / "bad.mp4", "black", "anullsrc=r=44100:cl=mono", seconds=4)
    got = _by(T.check_file(f, {"fps": 24, "frames": 96}))
    assert got["VAL-QA-03"] == G.REVIEW and got["VAL-QA-04"] == G.REVIEW and got["VAL-QA-05"] == G.REVIEW


@needs_ffmpeg
def test_expected_values_missing_are_not_run_and_no_audio_is_not_run(tmp_path):
    f = _make(tmp_path / "mute.mp4", "testsrc", None)
    got = _by(T.check_file(f))
    assert got["VAL-QA-01"] == G.NOT_RUN and got["VAL-QA-02"] == G.NOT_RUN
    assert got["VAL-QA-05"] == G.NOT_RUN and got["VAL-QA-06"] == G.NOT_RUN       # no audio stream
    assert got["VAL-QA-03"] == G.PASS


@needs_ffmpeg
def test_an_audio_video_offset_outside_the_window_blocks(tmp_path):
    f = tmp_path / "late.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=24:duration=3", "-itsoffset", "0.5",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", str(f)],
                   check=True)
    assert _by(T.check_file(f, {"fps": 24}))["VAL-QA-06"] == G.FAIL      # BP-54 is binding: 500 ms late is BLOCK


def test_without_ffmpeg_every_row_is_not_run(monkeypatch, tmp_path):
    monkeypatch.setattr(T.shutil, "which", lambda _: None)
    rows = T.check_file(tmp_path / "x.mp4", {"fps": 24})
    assert [r["status"] for r in rows] == [G.NOT_RUN] * len(T.RULE_IDS) and {r["gate"] for r in rows} == set(T.RULE_IDS)


def test_a_missing_file_is_not_run(tmp_path):
    if not T.tools_present():
        pytest.skip("ffmpeg/ffprobe not installed")
    assert {r["status"] for r in T.check_file(tmp_path / "nope.mp4")} == {G.NOT_RUN}
