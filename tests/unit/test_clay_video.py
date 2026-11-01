"""WP-1c: the clay layout clips for LTX-2.5's Layout-To-Render IC-LoRA (explainer_engine/edit/clay_video.py)."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.edit import clay_video as C

SPECS = Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/p12/clay/clay_specs.json"


def _spec(**kw):
    s = {"id": "t", "seconds": 1.0, "fps": 24, "width": 192, "height": 128,
         "camera": [{"t": 0, "pos": [0, 1.6, -5], "look": [0, 1.0, 0], "fov": 50}],
         "room": {"floor_y": 0, "back_z": 4, "half_width": 6, "height": 4},
         "objects": [{"id": "man", "shape": "figure", "size": [0.6, 1.8, 0.4],
                      "keys": [{"t": 0, "pos": [-1, 0, 0]}, {"t": 1, "pos": [1, 0, 0]}]},
                     {"id": "table", "shape": "box", "size": [1.5, 0.8, 1.0], "keys": [{"t": 0, "pos": [0, 0, 1.5]}]},
                     {"id": "pole", "shape": "cylinder", "size": [0.1, 4, 0.1], "keys": [{"t": 0, "pos": [0, 0, 3]}]}]}
    s.update(kw)
    return s


def test_frame_counts_snap_to_8k_plus_1():
    assert [C.snap_frames(n) for n in (1, 8, 9, 16, 17, 121, 125)] == [1, 1, 9, 9, 17, 121, 121]
    assert C.frame_count({"seconds": 5.0, "fps": 24}) == 121
    with pytest.raises(ValueError):
        C.snap_frames(0)


def test_check_spec_names_what_the_lora_cannot_take():
    assert C.check_spec(_spec()) == []
    bad = _spec(width=1000, camera=[], objects=[{"id": "x", "shape": "sphere", "keys": []}])
    problems = " | ".join(C.check_spec(bad))
    assert "divide by 64" in problems and "no camera keys" in problems
    assert "sphere" in problems and "x: no keys" in problems
    with pytest.raises(ValueError):
        C.render(bad, Path("unused.mp4"))


def test_keys_ease_and_hold_missing_fields():
    keys = [{"t": 0, "pos": [0, 0, 0], "yaw": 10}, {"t": 2, "pos": [2, 0, 0]}]
    assert C._at(keys, -1, "pos", None) == [0, 0, 0]
    assert C._at(keys, 1, "pos", None) == pytest.approx([1, 0, 0])
    assert C._at(keys, 0.5, "pos", None)[0] < 0.5            # smoothstep is slow at the start
    assert C._at(keys, 3, "pos", None) == [2, 0, 0]
    assert C._at(keys, 1.5, "yaw", 0) == 10                  # yaw not keyed again: held


def test_frames_are_pure_grey_and_objects_move():
    s = _spec()
    a, a2, b = (np.asarray(C.render_frame(s, i)) for i in (0, 0, 24))
    assert a.shape == (128, 192, 3)
    assert (a == a2).all()                                   # a pure function of (spec, frame)
    assert (a[..., 0] == a[..., 1]).all() and (a[..., 1] == a[..., 2]).all()   # grey clay only
    assert (a != b).any()                                    # the figure walked


def test_room_never_paints_over_objects():
    """The floor's centroid lies near the camera; drawn by depth it covered the figures (fixed: room first)."""
    s = _spec(objects=[{"id": "man", "shape": "figure", "size": [0.6, 1.8, 0.4], "keys": [{"t": 0, "pos": [0, 0, 0]}]}])
    img = np.asarray(C.render_frame(s, 0))[..., 0]
    empty = np.asarray(C.render_frame(_spec(objects=[]), 0))[..., 0]
    assert (img != empty).sum() > 200


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="needs ffmpeg")
def test_render_writes_an_h264_clip_of_8k_plus_1_frames(tmp_path):
    out = tmp_path / "clip.mp4"
    facts = C.render(_spec(), out)
    assert facts["frames"] == 25 and out.exists() and not out.with_suffix(".part.mp4").exists()
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,nb_read_frames,codec_name,r_frame_rate", "-of", "json", str(out)],
        capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert (probe["width"], probe["height"], int(probe["nb_read_frames"])) == (192, 128, 25)
    assert probe["codec_name"] == "h264" and probe["r_frame_rate"] == "24/1"


def test_p12_specs_are_usable_and_static_camera():
    shots = json.loads(SPECS.read_text(encoding="utf-8"))["shots"]
    assert set(shots) == {"tent_s0", "tent_s3", "tent_s4"}
    for sid, s in shots.items():
        assert s["id"] == sid and C.check_spec(s) == []
        assert (s["width"], s["height"], s["fps"]) == (1920, 1088, 24)
        assert C.frame_count(s) == 121
        assert len(s["camera"]) == 1                          # KP-04: these three shots keep the camera still
    assert C.load_spec(f"{SPECS}#tent_s3")["id"] == "tent_s3"
    with pytest.raises(SystemExit):
        C.load_spec(f"{SPECS}#nope")
