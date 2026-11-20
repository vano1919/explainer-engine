"""qa/lipsync.py (BP-133, SyncNet adapter): the logic runs on a fake runner, no torch needed."""
import json
import os
import sys
from pathlib import Path

import pytest

from explainer_engine.qa import lipsync as LS


def tracks(*pairs, frames=120):
    return lambda path: {"fps": 25, "tracks": [{"offset_frames": o, "offset_ms": 40 * o, "conf": c, "frames": frames} for o, c in pairs]}


@pytest.fixture
def conf(monkeypatch):
    monkeypatch.setattr(LS, "tolerances", lambda: {"conf_min": 3.0, "min_track_frames": None})


def run(runner, speaking=True, path="a.mp4"):
    return LS.lipsync_clip(path, speaking, runner=runner)


@pytest.mark.parametrize("off,ms", [(0, 0), (1, 40), (2, 80), (-2, -80)])
def test_offsets_within_limit_pass(conf, off, ms):
    r = run(tracks((off, 9.0)))
    assert r["status"] == "PASS" and r["value"] == ms


@pytest.mark.parametrize("off", [3, -3])
def test_ls02_over_limit_is_review(conf, off):
    r = run(tracks((off, 9.0)))
    assert r["status"] == "FAIL" and r["value"] == 40 * off
    assert r["detail"].startswith("REVIEW: LS-02") and "hypothesis" in r["detail"]


def test_limit_comes_from_the_registry(conf, monkeypatch):
    assert LS.review_frames() == 2
    assert run(tracks((2, 9.0)))["status"] == "PASS"
    monkeypatch.setattr(LS, "review_frames", lambda: 0)
    assert run(tracks((1, 9.0)))["status"] == "FAIL"


def test_ls03_conf_null_is_not_run():
    assert LS.tolerances()["conf_min"] is None
    r = run(tracks((0, 50.0)))
    assert r["status"] == "NOT_RUN" and r["value"] is None and "LS-03" in r["detail"]


def test_ls03_low_confidence_is_not_run_never_pass_or_fail(conf):
    r = run(tracks((5, 1.0)))
    assert r["status"] == "NOT_RUN" and "LS-03" in r["detail"]


def test_ls01_no_tracks_is_not_run(conf):
    assert run(lambda p: {"tracks": [], "fps": 25})["detail"].startswith("LS-01")
    assert run(lambda p: None)["status"] == "NOT_RUN"


def test_not_a_speaking_shot_is_not_run(conf):
    for sp in (False, None):
        r = LS.lipsync_clip("a.mp4", sp, runner=tracks((0, 9.0)))
        assert r["status"] == "NOT_RUN" and "not a speaking shot" in r["detail"]


def test_sidecar_marks_speaking(conf, tmp_path):
    clip = tmp_path / "s.mp4"
    clip.write_bytes(b"x")
    (tmp_path / "s.lipsync.json").write_text(json.dumps({"speaking": True}))
    assert LS.lipsync_clip(clip, runner=tracks((0, 9.0)))["status"] == "PASS"


def test_ls04_two_tracks_verdict_from_trusted_one(conf):
    r = run(tracks((1, 9.0), (5, 1.0)))
    assert r["status"] == "PASS" and r["value"] == 40
    assert "track 1" in r["detail"] and "track 2" in r["detail"]


def test_ls04_worst_trusted_offset_decides(conf):
    r = run(tracks((0, 9.0), (3, 4.0)))
    assert r["status"] == "FAIL" and "LS-02" in r["detail"] and r["value"] == 0


def test_missing_checkout_is_not_run(monkeypatch, tmp_path):
    monkeypatch.delenv("SYNCNET_DIR", raising=False)
    monkeypatch.setattr(LS, "ROOT", tmp_path)
    r = LS.lipsync_clip("a.mp4", True)
    assert r["status"] == "NOT_RUN" and "checkout" in r["detail"]


def test_checkout_without_weights_is_not_run(monkeypatch, tmp_path):
    for f in ("SyncNetInstance.py", "run_pipeline.py"):
        (tmp_path / f).write_text("")
    monkeypatch.setenv("SYNCNET_DIR", str(tmp_path))
    r = LS.lipsync_clip("a.mp4", True)
    assert r["status"] == "NOT_RUN" and "weights" in r["detail"]


def test_measure_uses_injected_runner():
    assert LS.measure_lipsync("a.mp4", runner=tracks((1, 2.0)))["tracks"][0]["offset_ms"] == 40


def test_tolerance_file_marks_hypotheses():
    doc = json.loads(LS.TOLERANCES.read_text(encoding="utf-8"))
    for k in ("conf_min", "min_track_frames"):
        assert doc[k]["kind"] == "hypothesis" and "not binding until the owner has seen it" in doc[k]["note"]


def test_main_exit_codes(conf, monkeypatch, capsys):
    monkeypatch.setattr(LS, "measure_lipsync", lambda p, runner=None: tracks((3, 9.0))(p))
    assert LS.main(["clip", "a.mp4", "--speaking"]) == 1
    monkeypatch.setattr(LS, "measure_lipsync", lambda p, runner=None: tracks((0, 9.0))(p))
    assert LS.main(["clip", "a.mp4", "--speaking"]) == 0
    assert LS.main(["clip", "a.mp4"]) == 0                      # not speaking: NOT_RUN, exit 0
    def boom(p, runner=None):
        raise ValueError("bad file")
    monkeypatch.setattr(LS, "measure_lipsync", boom)
    assert LS.main(["clip", "a.mp4", "--speaking"]) == 2


def test_kinds():
    assert ".mp4" in LS.lipsync_clip.kinds


def _example():
    d = os.environ.get("SYNCNET_DIR")
    ex = Path(d or "") / "data" / "example.avi"
    return ex if d and ex.is_file() and (Path(d) / "data" / "syncnet_v2.model").is_file() else None


needs_install = pytest.mark.skipif(_example() is None, reason="no SyncNet checkout with weights and data/example.avi (set SYNCNET_DIR)")


@needs_install
def test_real_install_readme_example():
    res = LS.measure_lipsync(_example())
    assert res["tracks"] and abs(res["tracks"][0]["offset_frames"] - 3) <= 1   # README: offset 3, "approximately"


@needs_install
def test_real_install_sign_with_known_shifts(tmp_path):
    """Sound delayed by 3 frames (120 ms) lowers the offset by 3; sound advanced by 3 raises it by 3: positive = sound before picture."""
    import subprocess
    ex = _example()
    base = LS.measure_lipsync(ex)["tracks"][0]["offset_frames"]
    for name, af, delta in (("late.avi", "adelay=120:all=1", -3), ("early.avi", "atrim=start=0.12,asetpts=PTS-STARTPTS", 3)):
        out = tmp_path / name
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ex), "-i", str(ex), "-map", "0:v", "-map", "1:a", "-af", af, "-c:v", "copy", str(out)], check=True)
        assert LS.measure_lipsync(out)["tracks"][0]["offset_frames"] == base + delta
