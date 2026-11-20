"""blender_scene/1: schema, validators V1-V9 (pure Python) and, where Blender exists, one tiny frame rendered."""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from explainer_engine.lab import scene_spec as ss

SPEC_DIR = Path(ss.__file__).parent / "specs" / "t0"
SPEC = SPEC_DIR / "t0_a1.json"


@pytest.fixture()
def spec():
    return ss.load_spec(SPEC)


def status(results, vid):
    return next(r["status"] for r in results if r["id"] == vid)


def test_t0_spec_passes_every_validator(spec):
    results = ss.validate_spec(spec)
    assert ss.summarize(results) == "PASS", results
    assert [c["frame_out"] - c["frame_in"] for c in spec["cuts"]] == [48] * 5   # 5 views x 2.0 s = frames 0..240
    assert spec["clip_frames"] == 241 and spec["size"] == [1280, 704]


def test_all_t0_clips_and_both_chains_pass():
    series = ss.load_series(SPEC_DIR)
    assert sorted(series) == ["t0_a", "t0_b"] and all(len(v) == 3 for v in series.values())
    for clips in series.values():
        for clip in clips:
            assert ss.summarize(ss.validate_spec(clip)) == "PASS", clip["scene_id"]
            assert clip["clip_frames"] == 241 and clip["size"] == [1280, 704] and len(clip["cuts"]) in (5, 6)
            assert all(0.8 <= (c["frame_out"] - c["frame_in"]) / 24 <= 2.0 for c in clip["cuts"])
        assert [r["status"] for r in ss.validate_series(clips)] == ["PASS", "PASS"]
    assert {clips[0]["place"] for clips in series.values()} == {"no_mans_land", "german_trench"}


def test_schema_refuses_unknown_field_and_wrong_place(spec):
    bad = copy.deepcopy(spec)
    bad["place"] = "moon"
    with pytest.raises(ss.SceneSpecError):
        ss.check_schema(bad)
    bad = copy.deepcopy(spec)
    bad["extra"] = 1
    with pytest.raises(ss.SceneSpecError):
        ss.check_schema(bad)


def test_v3_view_longer_than_two_seconds_fails(spec):
    bad = copy.deepcopy(spec)
    bad["cuts"][0]["frame_out"] = bad["cuts"][1]["frame_in"] = 50       # 50 frames = 2.08 s
    assert status(ss.validate_spec(bad), "V3") == "FAIL"


def test_v3_view_shorter_than_point_eight_fails():
    s = ss.load_spec(SPEC)
    s["cuts"][0]["frame_out"] = s["cuts"][1]["frame_in"] = 10
    assert status(ss.validate_spec(s), "V3") == "FAIL"


def test_v4_static_person_that_moves_fails_and_a_run_is_flagged(spec):
    bad = copy.deepcopy(spec)
    bad["people"][0]["static"] = True
    assert status(ss.validate_spec(bad), "V4") == "FAIL"
    run = copy.deepcopy(spec)
    run["people"][1]["track"][1]["frame"] = 60                           # 13 m in 2.5 s
    assert status(ss.validate_spec(run), "V4") == "REVIEW"


def test_v5_lens_outside_the_list_fails(spec):
    bad = copy.deepcopy(spec)
    bad["cameras"][0]["lens"] = 100
    assert status(ss.validate_spec(bad), "V5") == "FAIL"


def test_v6_frame_count_and_size_rules(spec):
    bad = copy.deepcopy(spec)
    bad["size"] = [1280, 720]
    assert status(ss.validate_spec(bad), "V6") == "FAIL"
    bad = copy.deepcopy(spec)
    bad["clip_frames"] = 240
    bad["cuts"][-1]["frame_out"] = 239
    assert status(ss.validate_spec(bad), "V6") == "FAIL"


def test_v1_far_person_is_flagged_for_review(spec):
    bad = copy.deepcopy(spec)
    bad["cuts"][3]["focus"] = ["german"]                                 # the wide shot: german is ~110 px tall
    assert status(ss.validate_spec(bad), "V1") == "REVIEW"


def test_v1_person_behind_the_camera_is_not_in_frame(spec):
    bad = copy.deepcopy(spec)
    bad["cuts"][1]["focus"] = ["german"]                                 # german stands behind that camera
    assert status(ss.validate_spec(bad), "V1") == "REVIEW"


def test_v2_overlap_is_flagged(spec):
    bad = copy.deepcopy(spec)
    for person in bad["people"]:
        for k in person["track"]:
            k["pos"][0] = 0.0                                            # both on the wide camera's own line
    assert status(ss.validate_spec(bad), "V2") == "REVIEW"


def test_v9_tail_must_be_calm_and_long_enough(spec):
    bad = copy.deepcopy(spec)
    bad["people"][1]["track"][2]["frame"] = 230                          # german still walking at the end
    bad["people"][1]["track"][2]["pos"] = [0.5, 19.0]
    bad["people"][1]["track"][1]["frame"] = 200
    bad["people"][1]["track"][1]["pos"] = [0.5, 24.0]
    assert status(ss.validate_spec(bad), "V9") == "REVIEW"
    short = copy.deepcopy(spec)
    short["cuts"][-2]["frame_out"] = short["cuts"][-1]["frame_in"] = 225   # last view 0.63 s
    res = ss.validate_spec(short)
    assert status(res, "V9") == "FAIL"


def test_v8_chain_needs_same_last_and_first_view(spec):
    nxt = copy.deepcopy(spec)
    nxt.pop("new_photo", None)
    nxt["cuts"][0]["camera"] = spec["cuts"][-1]["camera"]
    nxt["people"][0]["track"][0]["pos"] = spec["people"][0]["track"][-1]["pos"]
    nxt["people"][1]["track"][0]["pos"] = spec["people"][1]["track"][-1]["pos"]
    nxt["people"][1]["track"][0]["pose"] = "hands_open"
    assert ss.validate_chain(spec, nxt)["status"] == "PASS"
    drift = copy.deepcopy(nxt)
    drift["people"][0]["track"][0]["pos"] = [3.0, 3.0]
    assert ss.validate_chain(spec, drift)["status"] == "FAIL"
    drift["new_photo"] = True
    assert ss.validate_chain(spec, drift)["status"] == "PASS"


def test_cuts_must_tile_the_clip(spec):
    bad = copy.deepcopy(spec)
    bad["cuts"][2]["frame_in"] = 100
    assert status(ss.validate_spec(bad), "STRUCT") == "FAIL"


def test_projection_matches_the_picture_geometry(spec):
    cam = ss.camera_state(spec, spec["cuts"][0], 0)
    m = ss.measure_person(cam, (1280, 704), ss.person_state(spec["people"][0], 0))
    assert 355 < m["height_px"] < 370 and m["in_frame"]                  # measured 363 px, the rendered frame agrees


def _blender():
    return os.environ.get("BLENDER") or shutil.which("blender")


def test_one_tiny_frame_renders(tmp_path, spec):
    exe = _blender()
    if not exe:
        pytest.skip("Blender not installed")
    from explainer_engine.lab import scene_render as sr
    small = copy.deepcopy(spec)
    small["size"] = [320, 192]
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(small), encoding="utf-8")
    info = sr.run_blender(p, tmp_path, 2, 0, 0, exe)
    assert info["projection_gap_px"] < 1.5
    from PIL import Image
    im = Image.open(sr.frame_file(tmp_path, 0))
    assert im.size == (320, 192) and len(set(im.convert("L").getdata())) > 20
