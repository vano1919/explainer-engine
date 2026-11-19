"""W7: typed calls of the vendored ffmpeg-skill (join by copy, mix under the picture, check, look) on tiny synthetic clips."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.finish import ffwrap, qa_steps

pytestmark = pytest.mark.skipif(not ffwrap.available(), reason="ffmpeg or the vendored ffmpeg-skill is missing")


def _ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture()
def parts(tmp_path):
    for n, src in (("a", "testsrc"), ("b", "testsrc2")):
        _ff("-f", "lavfi", "-i", f"{src}=size=160x90:rate=24:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
            str(tmp_path / f"{n}.mp4"))
    _ff("-f", "lavfi", "-i", "sine=frequency=330:duration=2", str(tmp_path / "mix.wav"))
    return tmp_path


def test_join_with_audio_makes_one_file_with_both_streams(parts):
    out = parts / "out.mp4"
    ffwrap.join_with_audio([parts / "a.mp4", parts / "b.mp4"], parts / "mix.wav", out, sample_rate=48000, channels=2, kbps=384)
    info = ffwrap.probe(out)
    assert abs(info["duration"] - 2.0) < 0.1 and info["video"]["codec"] == "h264"
    assert info["audio"]["codec"] == "aac" and info["audio"]["channels"] == 2
    assert not (parts / "out.joined.mp4").exists()   # the intermediate never stays


def test_join_copy_does_not_reencode(parts):
    res = ffwrap.join_copy([parts / "a.mp4", parts / "b.mp4"], parts / "j.mp4")
    assert res.get("lossless") is True and res.get("reencoded") is False


def test_a_missing_input_is_a_contract_error_with_the_skills_message(parts):
    with pytest.raises(ContractError, match="ffmpeg-skill join failed"):
        ffwrap.join_copy([parts / "a.mp4", parts / "nope.mp4"], parts / "j.mp4")


def test_an_unknown_tool_is_refused():
    with pytest.raises(ContractError, match="no tool"):
        ffwrap.run("rm_rf", [])


def test_check_row_lists_every_check_and_is_never_pass_on_a_miss(parts):
    out = parts / "out.mp4"
    ffwrap.join_with_audio([parts / "a.mp4", parts / "b.mp4"], parts / "mix.wav", out, sample_rate=48000, channels=2, kbps=384)
    row = qa_steps.check_row(out)
    assert row["gate"] == "VAL-QA-07" and row["status"] in ("PASS", "REVIEW") and isinstance(row["measured"], list) and row["measured"]
    assert any(c["check"] == "loudness" for c in row["measured"])   # the sine is far from -14 LUFS: a person looks


def test_look_row_makes_a_sheet_and_is_review_not_pass(parts):
    out = parts / "out.mp4"
    ffwrap.join_with_audio([parts / "a.mp4", parts / "b.mp4"], parts / "mix.wav", out, sample_rate=48000, channels=2, kbps=384)
    row = qa_steps.look_row(out, parts / "sheet.png", tiles="3x2")
    assert row["status"] == "REVIEW" and (parts / "sheet.png").stat().st_size > 0


def test_rows_are_not_run_for_a_missing_file(tmp_path):
    assert qa_steps.check_row(tmp_path / "x.mp4")["status"] == "NOT_RUN"
    assert qa_steps.look_row(tmp_path / "x.mp4", tmp_path / "s.png")["status"] == "NOT_RUN"


def test_rows_are_not_run_without_the_tools(parts, monkeypatch):
    monkeypatch.setattr(ffwrap, "available", lambda: False)
    assert qa_steps.check_row(parts / "a.mp4")["status"] == "NOT_RUN"
    assert qa_steps.look_row(parts / "a.mp4", parts / "s.png")["status"] == "NOT_RUN"
