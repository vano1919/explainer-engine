"""Blender blocking lab: the layout data is valid (pure Python) and, where Blender is installed, one frame renders."""

import copy

import pytest

from explainer_engine.lab import blender_blocking as bb


def test_layouts_valid_and_six_frames():
    assert bb.validate() == []
    assert len(bb.frame_names()) == 6
    assert {s["camera"]["lens"] for s in bb.LAYOUTS.values()} == {35, 50, 28}


def test_officer_stays_on_the_fire_step_and_only_the_arm_changes():
    spec = bb.LAYOUTS["S07_SH006"]["frames"]
    a, b = spec["start"]["officer"], spec["end"]["officer"]
    assert (a["pos"], a["z"], a["heading"]) == (b["pos"], b["z"], b["heading"])
    assert (a["pose"], b["pose"]) == ("stand", "arm_up")


def test_validate_catches_moved_heading_and_bad_lens():
    bad = copy.deepcopy(bb.LAYOUTS)
    bad["S07_SH006"]["frames"]["end"]["officer"]["heading"] = 200
    bad["S04_SH008"]["camera"]["lens"] = 85
    problems = bb.validate(bad)
    assert any("officer heading changes" in p for p in problems)
    assert any("lens 85" in p for p in problems)


def test_plan_view_written(tmp_path):
    out = bb.plan_view("S04_SH008", tmp_path / "plan.png")
    assert out.exists() and out.stat().st_size > 2000


def test_one_frame_renders(tmp_path):
    pytest.importorskip("bpy")
    report = bb.render(tmp_path, only=["S07_SH008_start"], size=(320, 180), samples=4, save_blend=False)
    png = tmp_path / "S07_SH008_start_blocking.png"
    assert png.exists()
    from PIL import Image
    im = Image.open(png)
    assert im.size == (320, 180) and len(set(im.convert("L").getdata())) > 20
    assert report["S07_SH008_start"]["lens_mm"] == 35
