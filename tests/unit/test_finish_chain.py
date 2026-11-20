"""W7: the finishing chain end to end on tiny synthetic clips: one join, one grade, the S14-S16 and S18 rows, nothing PASSes by default."""
from __future__ import annotations

import subprocess

import numpy as np
import pytest

from explainer_engine.finish import chain, ffwrap

pytestmark = pytest.mark.skipif(not ffwrap.available(), reason="ffmpeg or the vendored ffmpeg-skill is missing")


def _ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def test_chain_runs_and_reports_every_gate(tmp_path):
    for n, src in (("a", "testsrc2"), ("b", "testsrc")):
        _ff("-f", "lavfi", "-i", f"{src}=size=320x180:rate=24:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(tmp_path / f"{n}.mp4"))
    _ff("-f", "lavfi", "-i", "sine=frequency=220:duration=2", "-ar", "48000", "-ac", "2", str(tmp_path / "mix.wav"))
    words = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate("Two clips one path.".split())]
    key = np.full((36, 64, 3), 0.5, np.float32)
    r = chain.run_chain([tmp_path / "a.mp4", tmp_path / "b.mp4"], tmp_path / "mix.wav", tmp_path / "out", key_frame=key, words=words,
                        expected_frames=48)
    gates = {g["gate"]: g["status"] for g in r["verdict"]["gates"]}
    assert {"VAL-EDT-01", "VAL-CLR-01", "VAL-CLR-02", "VAL-QA-01", "VAL-QA-02", "VAL-QA-07", "VAL-QA-08", "VAL-SUB-01", "VAL-SUB-02"} <= set(gates)
    assert gates["VAL-CLR-02"] == "PASS" and gates["VAL-QA-02"] == "PASS" and gates["VAL-QA-08"] == "REVIEW"
    assert r["verdict"]["status"] != "PASS"            # a contact sheet nobody looked at is never a pass
    assert (tmp_path / "out" / "finish_chain.json").is_file() and (tmp_path / "out" / "master_graded_cc.mp4").is_file()


def test_chain_without_words_says_not_run_for_captions(tmp_path):
    _ff("-f", "lavfi", "-i", "testsrc=size=320x180:rate=24:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(tmp_path / "a.mp4"))
    _ff("-f", "lavfi", "-i", "sine=duration=1", "-ar", "48000", "-ac", "2", str(tmp_path / "mix.wav"))
    r = chain.run_chain([tmp_path / "a.mp4"], tmp_path / "mix.wav", tmp_path / "o", key_frame=np.full((8, 8, 3), 0.5, np.float32))
    assert {g["gate"]: g["status"] for g in r["verdict"]["gates"]}["VAL-SUB-01"] == "NOT_RUN"
