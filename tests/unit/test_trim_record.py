"""qa/trim_record.py (OR-V56) and qa/audio_present.py."""
import json
import subprocess

import pytest

from explainer_engine.qa import audio_present as AP
from explainer_engine.qa import trim_record as TR


def plan(tmp_path, *shots):
    f = tmp_path / "edit_plan.json"
    f.write_text(json.dumps({"shots": [dict(id=f"S{i}", clip_length_s=c, shot_length_s=s, trim_s=t) for i, (c, s, t) in enumerate(shots, 1)]}))
    return f


def test_limit_is_the_owner_number_marked_house():
    assert TR.trim_max_s() == 0.33
    assert json.loads(TR.TOLERANCES.read_text())["trim_max_s"]["kind"] == "house"


def test_pass_at_exactly_the_limit_and_at_zero(tmp_path):
    r = TR.trim_record(plan(tmp_path, (5.33, 5.0, 0.33), (4.0, 4.0, 0.0)))
    assert r["status"] == "PASS" and r["value"] == 0.33


def test_tr03_over_limit(tmp_path):
    r = TR.trim_record(plan(tmp_path, (5.34, 5.0, 0.34)))
    assert r["status"] == "FAIL" and "TR-03" in r["detail"] and "TR-04" not in r["detail"]


def test_tr02_clip_shorter_than_shot(tmp_path):
    r = TR.trim_record(plan(tmp_path, (4.9, 5.0, -0.1)))
    assert r["status"] == "FAIL" and "TR-02" in r["detail"] and "TR-03" not in r["detail"]


def test_tr04_recorded_trim_differs(tmp_path):
    r = TR.trim_record(plan(tmp_path, (5.2, 5.0, 0.1)))
    assert r["status"] == "FAIL" and "TR-04" in r["detail"] and "TR-03" not in r["detail"]


def test_tr01_missing_field_and_not_a_plan_are_not_run(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"shots": [{"id": "S1", "clip_length_s": 5}]}))
    assert TR.trim_record(f)["status"] == "NOT_RUN" and "TR-01" in TR.trim_record(f)["detail"]
    f.write_text(json.dumps({"other": 1}))
    assert TR.trim_record(f)["status"] == "NOT_RUN"


def clip(tmp_path, name, audio):
    f = tmp_path / name
    src = ["-f", "lavfi", "-i", "color=c=black:s=64x64:d=1:r=25"]
    if audio:
        src += ["-f", "lavfi", "-i", "sine=d=1"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", *src, "-shortest", str(f)], check=True)
    return f


def test_audio_present_pass_and_fail(tmp_path):
    assert AP.audio_present(clip(tmp_path, "a.mp4", True))["status"] == "PASS"
    r = AP.audio_present(clip(tmp_path, "v.mp4", False))
    assert r["status"] == "FAIL" and r["value"] == 0


def test_audio_present_unreadable_raises(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(RuntimeError):
        AP.audio_present(bad)
    with pytest.raises(FileNotFoundError):
        AP.audio_present(tmp_path / "none.mp4")


def test_audio_present_main_exit_codes(tmp_path):
    assert AP.main([str(clip(tmp_path, "a.mp4", True))]) == 0
    assert AP.main([str(clip(tmp_path, "v.mp4", False))]) == 1
    assert AP.main([str(tmp_path / "none.mp4")]) == 2
