"""ICW-06 scene builder (roadmap 10.1, 11, 12.4): the six camera rigs sampled into LINEAR keys, the cast checked against the
library, blender_scene_manifest/1 from a bpy report, the six benchmark shots as valid shot_spec/2 documents, BP-108's cap on a
lip-synced shot. No Blender: the bpy report is written here."""
import json
import math

import pytest

from explainer_engine.assets import library as L
from explainer_engine.blender import benchmark_shots as BS
from explainer_engine.blender import characters as C
from explainer_engine.blender import rigs
from explainer_engine.blender import scene_builder as SB
from explainer_engine.core import contracts
from explainer_engine.core import shot_cache
from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

from test_characters import fake_cast


def cam(rig, start=((0, -5, 1.5), 0, 0), end=((2, -3, 1.5), 10, -5), ease="linear"):
    pose = lambda p: {"pos": list(p[0]), "yaw_deg": p[1], "pitch_deg": p[2]}  # noqa: E731
    return {"rig": rig, "start": pose(start), "end": pose(end), "lens_mm": 35, "ease": ease}


def test_eases_run_zero_to_one_and_smoothstep_is_symmetric():
    for e in SB.EASES:
        assert SB.ease(e, 0) == 0 and SB.ease(e, 1) == 1
        assert all(SB.ease(e, a / 10) <= SB.ease(e, (a + 1) / 10) for a in range(10))
    assert SB.ease("ease_in_out", 0.25) == pytest.approx(1 - SB.ease("ease_in_out", 0.75))
    assert SB.ease("ease_in", 0.5) < 0.5 < SB.ease("ease_out", 0.5)
    with pytest.raises(ValueError):
        SB.ease("bounce", 0.5)


def test_angles_invert_forward():
    for yaw, pitch in ((0, 0), (62, -8), (-140, 20), (179, 0)):
        assert SB.angles(SB.forward(yaw, pitch)) == pytest.approx((yaw, pitch), abs=1e-6)
    assert SB.forward(0, 0) == pytest.approx((0, 1, 0)) and SB.forward(90, 0) == pytest.approx((-1, 0, 0), abs=1e-12)


def test_every_rig_keys_frame_zero_every_fourth_and_the_last_from_start_to_end():
    for rig in SB.RIGS:
        p = SB.camera_path(cam(rig), 48)
        assert [k["frame"] for k in p] == list(range(0, 48, SB.KEY_EVERY)) + [47]
        assert p[0]["pos"] == pytest.approx([0, -5, 1.5])
        if rig not in ("static", "orbit"):
            assert p[-1]["pos"] == pytest.approx([2, -3, 1.5])
    static = SB.camera_path(cam("static"), 48)
    assert all(k["pos"] == static[0]["pos"] and k["yaw_deg"] == 0 for k in static)
    rail = SB.camera_path(cam("rail"), 48)
    assert {k["yaw_deg"] for k in rail} == {0} and {k["pitch_deg"] for k in rail} == {0}  # a rail keeps the start's heading
    push = SB.camera_path(cam("push"), 48)
    assert push[-1]["yaw_deg"] == pytest.approx(10) and push[-1]["pitch_deg"] == pytest.approx(-5)
    one = SB.camera_path(cam("push"), 1)
    assert [k["frame"] for k in one] == [0]
    with pytest.raises(ContractError):
        SB.camera_path(cam("crane"), 48)


def test_orbit_circles_the_pivot_and_always_faces_it():
    pivot = [0, 0, 1.5]
    p = SB.camera_path(cam("orbit", start=((-3, -3, 1.5), -45, 0), end=((3, -3, 1.5), 45, 0)), 48, pivot=pivot)
    radii = [math.hypot(k["pos"][0], k["pos"][1]) for k in p]
    assert max(radii) - min(radii) < 1e-6
    for k in p:
        f = SB.forward(k["yaw_deg"], k["pitch_deg"])
        to = [pivot[i] - k["pos"][i] for i in range(3)]
        n = math.sqrt(sum(x * x for x in to))
        assert sum(f[i] * to[i] / n for i in range(3)) == pytest.approx(1.0, abs=1e-9)
    assert p[len(p) // 2]["pos"][1] < -4.2  # it swings around (through -y), not straight across
    assert p[-1]["pos"] == pytest.approx([3, -3, 1.5])


def test_the_dramatic_curve_bows_off_the_straight_line_and_ends_on_the_end_pose():
    straight = SB.camera_path(cam("push", ease="ease_in_out"), 49)
    curve = SB.camera_path(cam("dramatic_curve", ease="ease_in_out"), 49)
    mid = len(curve) // 2
    d = math.dist(curve[mid]["pos"], straight[mid]["pos"])
    assert d > 0.1 and curve[-1]["pos"] == pytest.approx(straight[-1]["pos"])


def test_camera_job_is_linear_keys_on_the_sampled_poses():
    path = SB.camera_path(cam("dolly"), 9)
    job = SB.camera_job(path, 35, 4.0)
    assert job["interp"] == "LINEAR" and [k["frame"] for k in job["keys"]] == [0, 4, 8]
    k = job["keys"][1]
    f = SB.forward(path[1]["yaw_deg"], path[1]["pitch_deg"])
    assert [k["look_at"][i] - k["location"][i] for i in range(3)] == pytest.approx([x * SB.LOOK_M for x in f])
    assert "keys" not in SB.camera_job(SB.camera_path(cam("static"), 1), 35, 4.0)


def _s1(cues):
    plan = BS.plans(None)["S1"]
    return plan, BS.spec_for("S1", plan, cues=cues)


def test_builder_places_the_cast_and_refuses_a_swapped_asset_or_a_missing_member(tmp_path, monkeypatch):
    _, cpaths = fake_cast(tmp_path, monkeypatch)
    plan, spec = _s1(None)
    b = SB.SceneBuilder(cpaths)
    sc, path = b.build(spec, cast=plan["cast"])
    names = [o["name"] for o in sc["objects"]]
    assert names == ["speaker_a", "speaker_b"] and sc["frames_total"] == 48 and sc["camera"]["interp"] == "LINEAR"
    assert sc["objects"][0]["location"] == spec["scene"]["characters"][0]["position"]
    assert path[0]["pos"] == spec["scene"]["camera"]["start"]["pos"]
    bad = json.loads(json.dumps(spec))
    bad["scene"]["characters"][0]["asset"] = {"id": "model.ubc_superhero_female",
                                              "sha256": L.get("model.ubc_superhero_female")["sha256"]}
    with pytest.raises(ContractError, match="the character ink_test_m is"):
        b.build(bad, cast=plan["cast"])
    with pytest.raises(ContractError, match="no entry in the cast table"):
        b.build(spec, cast={"speaker_a": plan["cast"]["speaker_a"]})
    lip = json.loads(json.dumps(spec))
    lip["performance"]["lipsync"] = True
    with pytest.raises(ContractError, match="no cast member has lip-sync"):
        b.build(lip, cast=plan["cast"])


CUES = {"metadata": {"duration": 3.0},
        "mouthCues": [{"start": 0.0, "end": 1.0, "value": "X"}, {"start": 1.0, "end": 1.2, "value": "B"},
                      {"start": 1.2, "end": 1.5, "value": "D"}, {"start": 1.5, "end": 1.7, "value": "F"},
                      {"start": 1.7, "end": 1.9, "value": "C"}, {"start": 1.9, "end": 3.0, "value": "X"}]}


def test_the_six_benchmark_shots_are_valid_master_specs_with_their_own_keys(tmp_path):
    cues = tmp_path / "line.rhubarb.json"
    cues.write_text(json.dumps(CUES), encoding="utf-8")
    ls = rigs.LipSync(24)
    lip = ls.plan(cues, BS.FRAMES, offset_s=0.5)
    plans = BS.plans(lip)
    assert tuple(plans) == BS.SHOTS
    keys = set()
    for sid, plan in plans.items():
        spec = BS.spec_for(sid, plan, cues=cues)
        assert [f for f in contracts.errors(spec) if f["severity"] == "FAIL"] == [], sid
        assert spec["clock"] == {"fps": 24, "frames": 48, "start_frame": 0} and spec["frame"]["width"] == 2560
        keys.add(shot_cache.key(spec))
    rigs_used = {sid: p["camera"]["rig"] for sid, p in plans.items()}
    assert rigs_used == {"S1": "push", "S2": "orbit", "S3": "dolly", "S4": "rail", "S5": "dolly", "S6": "push"}
    s1, s6 = BS.spec_for("S1", plans["S1"], cues=cues), BS.spec_for("S6", plans["S6"], cues=cues)
    assert s1["performance"]["lipsync"] and s1["performance"]["dialogue_cover"] == "on_screen"
    assert s6["render"] == {"profile": "cycles_hero", "samples": 64, "motion_blur": False, "denoise": True, "output": "png_seq"}
    assert BS.spec_for("S5", plans["S5"])["lane"] == "STILL_3D" and len(plans["S3"]["cast"]) == 18
    assert sum(1 for m in plans["S3"]["cast"].values() if m["to"]) == 9  # the near line advances
    assert len(keys) == 6


def test_a_lip_synced_shot_obeys_bp108_and_shows_the_busiest_window(tmp_path):
    cap = SR.T("BP-108", "dialogue_shot_max_s")
    ls = rigs.LipSync(24)
    ls.plan(CUES, round(cap * 24))
    with pytest.raises(ValueError, match="BP-108"):
        ls.plan(CUES, round(cap * 24) + 1)
    off = ls.busiest(CUES, 24)
    assert 0.5 <= off <= 1.25  # the window holds the speech between 1.0 and 1.9 s, not the leading silence
    plan = ls.plan(CUES, 24, offset_s=off)
    assert set(plan["shapes"]) > {"X"} and plan["offset_s"] == off


def test_manifest_from_the_bpy_report_validates(tmp_path, monkeypatch):
    _, cpaths = fake_cast(tmp_path, monkeypatch)
    plan, spec = _s1(None)
    b = SB.SceneBuilder(cpaths)
    _, path = b.build(spec, cast=plan["cast"])
    sdir = tmp_path / shot_cache.key(spec)
    sdir.mkdir()
    (sdir / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    ids = C.asset_ids("ink_test_m", "costume.mco_male_ranger")
    (sdir / "bpy_report.json").write_text(json.dumps({
        "blender_version": "5.2.3", "objects": {"MESH": 20, "ARMATURE": 2, "LIGHT": 1, "CAMERA": 1, "EMPTY": 2},
        "characters": {"speaker_a": {"id": "ink_test_m", "costume": "costume.mco_male_ranger", "assets": ids}},
        "bounds": [{"object": "speaker_a", "min": [-1.2, 0.5, 0.0], "max": [-0.7, 1.2, 1.8]}]}), encoding="utf-8")
    m = b.manifest(spec, sdir, path)
    assert m["schema"] == "blender_scene_manifest/1" and m["cache_key"] == shot_cache.key(spec)
    assert m["objects"] == {"total": 26, "meshes": 20, "armatures": 2, "lights": 1, "cameras": 1}
    got = {a["id"] for a in m["assets"]}
    assert set(ids) <= got and "material.ph_brick_wall_001" in got
    assert m["camera_path"] == path and "glb" in m["import_settings"]
    assert m["spec"]["sha256"] == L.sha256_file(sdir / "spec.json")
