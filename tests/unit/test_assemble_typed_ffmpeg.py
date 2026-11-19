"""W7: assemble.py's join and mux go through finish/ffwrap (typed ffmpeg-skill calls); no hand-written concat string remains."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from explainer_engine.finish import ffwrap
from explainer_engine.production import assemble as A

SRC = (Path(__file__).resolve().parents[2] / "explainer_engine" / "production" / "assemble.py").read_text(encoding="utf-8")


def test_no_concat_demuxer_string_is_left_in_assemble():
    assert '"concat"' not in SRC and "list.txt" not in SRC


def test_the_only_ffmpeg_arguments_left_are_the_frame_pipes_and_measurements():
    # raw frames from numpy to an encoder (no typed tool takes stdin frames) and ffprobe/ffmpeg readers: nothing that joins or muxes
    calls = re.findall(r'\["(ffmpeg|ffprobe)", ([^\]]{0,160})', SRC)
    for tool, rest in calls:
        assert "concat" not in rest and "-map" not in rest, (tool, rest)


def test_episode_master_join_uses_ffwrap_and_keeps_the_picture_frame_exact(tmp_path, monkeypatch):
    seen = []

    def fake(tool, args, **kw):
        seen.append((tool, [str(a) for a in args]))
        Path(args[args.index("-o") + 1]).write_bytes(b"mp4")
        return {"summary": {}}

    monkeypatch.setattr(A.ffwrap, "run", fake)
    work = tmp_path / "w"
    work.mkdir()
    for i in range(2):
        (work / f"c_{i:04d}.mp4").write_bytes(b"x")
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    A.ffwrap.join_with_audio([work / "c_0000.mp4", work / "c_0001.mp4"], audio, tmp_path / "m.mp4", **A._audio_args())
    assert [t for t, _ in seen] == ["join", "audio"]
    assert "--transition" in seen[0][1] and seen[0][1][seen[0][1].index("--transition") + 1] == "none" and "--copy" in seen[0][1]
    assert seen[1][1][seen[1][1].index("--replace") + 1] == str(audio)


@pytest.mark.skipif(not ffwrap.available(), reason="ffmpeg or the vendored ffmpeg-skill is missing")
def test_real_join_keeps_the_frame_count(tmp_path):
    for n in "ab":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=24:duration=1", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-an", str(tmp_path / f"{n}.mp4")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=duration=2", str(tmp_path / "m.wav")], check=True)
    ffwrap.join_with_audio([tmp_path / "a.mp4", tmp_path / "b.mp4"], tmp_path / "m.wav", tmp_path / "o.mp4", **A._audio_args())
    n, _w, _h = A.clip_info(tmp_path / "o.mp4")
    assert n == 48
