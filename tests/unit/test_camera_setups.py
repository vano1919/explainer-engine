"""WP-Q7 camera grammar (roadmap 10.1): the six named setups resolve to a lens, a pose and a focus; the framed point lands on the
setup's thirds target; a setup's f-stop is inside the DoF range; the shot_spec/2 enum, the scene job and the pinned Add Camera
Rigs extension agree. No Blender: the bpy side is checked by blender/camera_smoke.py (CI) against the pinhole used here."""
import json

import pytest

from explainer_engine.blender import benchmark_shots as BS
from explainer_engine.blender import camera_rigs as R
from explainer_engine.blender import camera_setups as C
from explainer_engine.blender import scene_builder as SB
from explainer_engine.core import contracts
from explainer_engine.core.errors import ConfigError, ContractError


SUBJ = {"a": {"pos": [-1.2, 2.0, 0.0]}, "b": {"pos": [1.0, 2.5, 0.0]}}


def spec_s1():
    return BS.spec_for("S5", BS.plans(None)["S5"])


SIX = ["establishing_wide", "low_angle_hero_cu", "ots_a", "ots_b", "profile_two_shot", "push_in_reveal"]


def test_the_six_setups_and_the_shot_reverse_shot_sequence():
    assert C.names() == SIX
    assert C.sequence("shot_reverse_shot") == ["ots_a", "ots_b"]
    with pytest.raises(ContractError):
        C.get("dutch_angle")
    with pytest.raises(ContractError):
        C.sequence("montage")


def test_the_schema_enum_is_the_setup_table():
    schema = json.loads((C.Path(C.__file__).parents[1] / "schemas" / "shot_spec.schema.json").read_text(encoding="utf-8"))
    enum = schema["$defs"]["v2"]["properties"]["scene"]["properties"]["camera"]["properties"]["setup"]["enum"]
    assert sorted(enum) == SIX


@pytest.mark.parametrize("name", SIX)
def test_every_setup_resolves_to_lens_pose_focus_and_the_thirds(name):
    r = C.resolve(name, SUBJ)
    cam, spec = r["camera"], C.get(name)
    assert cam["lens_mm"] == spec["lens_mm"] and cam["setup"] == name and cam["rig"] in SB.RIGS and cam["ease"] in SB.EASES
    assert cam["rig_kind"] in C.RIG_KINDS and len(r["focus_at"]) == 3
    for which in ("start", "end"):
        assert set(cam[which]) == {"pos", "yaw_deg", "pitch_deg"}
        assert C.thirds_error(r, which=which) <= r["tolerance"]
    assert r["tolerance"] <= 0.03


@pytest.mark.parametrize("name", SIX)
def test_a_setups_fstop_is_inside_the_dof_range(name):
    f = C.get(name)["fstop"]
    assert C.load()["fstop_min"] <= f <= C.load()["fstop_max"]
    assert C.check_camera(C.resolve(name, SUBJ)["camera"]) == []


def test_shot_reverse_shot_looks_at_each_other_from_behind_each():
    a, b = C.resolve("ots_a", SUBJ), C.resolve("ots_b", SUBJ)
    assert a["target"][:2] == pytest.approx(SUBJ["b"]["pos"][:2]) and b["target"][:2] == pytest.approx(SUBJ["a"]["pos"][:2])
    # the camera of ots_a stands on A's side of B, the reverse stands on B's side of A
    pa, pb = a["camera"]["start"]["pos"], b["camera"]["start"]["pos"]
    assert pa[0] < SUBJ["b"]["pos"][0] and pb[0] > SUBJ["a"]["pos"][0]
    assert abs(((a["camera"]["start"]["yaw_deg"] - b["camera"]["start"]["yaw_deg"]) % 360) - 180) < 1e-3   # looking at each other


def test_a_low_angle_hero_cu_looks_up_and_a_long_lens_blurs_more_than_the_wide():
    hero, wide = C.resolve("low_angle_hero_cu", SUBJ)["camera"], C.resolve("establishing_wide", SUBJ)["camera"]
    assert hero["start"]["pitch_deg"] > 5 and hero["start"]["pos"][2] < 0.8
    assert hero["lens_mm"] > wide["lens_mm"] and hero["fstop"] < wide["fstop"]


def test_the_moves_move_and_the_still_setups_do_not():
    for name in ("establishing_wide", "low_angle_hero_cu", "push_in_reveal", "profile_two_shot"):
        c = C.resolve(name, SUBJ)["camera"]
        assert c["start"] != c["end"], name
    for name in ("ots_a", "ots_b"):
        c = C.resolve(name, SUBJ)["camera"]
        assert c["rig"] == "static" and c["start"] == c["end"]
    crane = C.resolve("establishing_wide", SUBJ)["camera"]
    assert crane["rig_kind"] == "crane" and crane["end"]["pos"][2] > crane["start"]["pos"][2]


def test_setups_scale_with_the_cast_and_follow_the_bearing():
    near = C.resolve("push_in_reveal", SUBJ)["camera"]["start"]["pos"]
    big = C.resolve("push_in_reveal", SUBJ, head_m=0.48, eye_m=3.2)["camera"]["start"]["pos"]
    assert abs(big[1] - SUBJ["a"]["pos"][1]) == pytest.approx(2 * abs(near[1] - SUBJ["a"]["pos"][1]), rel=0.01)
    turned = C.resolve("push_in_reveal", SUBJ, bearing_deg=90)
    assert turned["camera"]["start"]["pos"][0] > SUBJ["a"]["pos"][0] and C.thirds_error(turned) < 0.03   # looks along -X: stands at +X


def test_a_setup_needs_its_subjects():
    with pytest.raises(ContractError):
        C.resolve("ots_a", {"a": SUBJ["a"]})
    with pytest.raises(ContractError):
        C.resolve("ots_a", {"a": SUBJ["a"], "b": SUBJ["a"]})   # the same spot: no axis
    with pytest.raises(ContractError):
        C.resolve("low_angle_hero_cu", {"b": SUBJ["b"]})


def test_framing_is_a_pinhole_with_the_centre_at_one_half():
    cam = {"lens_mm": 36.0, "start": {"pos": [0, 0, 0], "yaw_deg": 0.0, "pitch_deg": 0.0}}
    assert C.framing(cam, [0, 10, 0]) == pytest.approx((0.5, 0.5))
    assert C.framing(cam, [5, 10, 0])[0] == pytest.approx(1.0)        # on a 36 mm lens on a 36 mm sensor the edge is at x/depth = 0.5
    assert C.framing(cam, [-5, 10, 0])[0] == pytest.approx(0.0)
    assert C.framing(cam, [0, 10, 10])[1] > 0.5
    with pytest.raises(ContractError):
        C.framing(cam, [0, -5, 0])


def test_check_camera_names_the_problems():
    assert C.check_camera({"lens_mm": 35, "setup": "nope"}) == ["unknown camera setup 'nope'"]
    assert any("lens" in p for p in C.check_camera({"lens_mm": 35, "setup": "ots_a"}))
    assert any("f-stop" in p for p in C.check_camera({"lens_mm": 50, "fstop": 0.5}))
    assert any("rig kind" in p for p in C.check_camera({"lens_mm": 50, "rig_kind": "jib"}))


def test_a_shot_spec_may_name_setup_fstop_and_rig_kind_and_nothing_else_new():
    spec = spec_s1()
    spec["scene"]["camera"].update(C.resolve("ots_a", SUBJ)["camera"])
    assert [f for f in contracts.errors(spec) if f["severity"] == "FAIL"] == []
    spec["scene"]["camera"]["setup"] = "dutch_angle"
    assert [f for f in contracts.errors(spec) if f["severity"] == "FAIL"]
    spec["scene"]["camera"].update(setup="ots_a", rig_kind="jib")
    assert [f for f in contracts.errors(spec) if f["severity"] == "FAIL"]


def test_the_scene_job_carries_the_rig_the_aperture_and_the_focus_target(tmp_path):
    r = C.resolve("ots_a", SUBJ)
    path = SB.camera_path(r["camera"], 9)
    plain = SB.camera_job(path, 50, 4.0)
    assert "rig_kind" not in plain and "fstop" not in plain
    with pytest.raises(ContractError):   # a rig without the extension zip is refused, never silently the bare camera
        SB.camera_job(path, 50, 4.0, rig_kind="dolly")
    job = SB.camera_job(path, 50, 4.0, fstop=2.8, rig_kind="dolly", focus_at=r["focus_at"], extension=str(tmp_path / "x.zip"))
    assert job["fstop"] == 2.8 and job["rig_kind"] == "dolly" and job["focus_at"] == r["focus_at"] and job["extension"].endswith("x.zip")


def test_the_extension_pin_is_a_verified_download(tmp_path, monkeypatch):
    p = R.pin()
    assert p["licence"] == "SPDX:GPL-3.0-or-later" and len(p["sha256"]) == 64 and p["url"].startswith("https://extensions.blender.org/")
    payload = b"zip bytes"
    import hashlib
    monkeypatch.setattr(R, "pin", lambda: {**p, "sha256": hashlib.sha256(payload).hexdigest()})
    got = R.ensure(tmp_path, download=lambda url, dest: dest.write_bytes(payload))
    assert got.read_bytes() == payload and got.parent.name == hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(R, "pin", lambda: {**p, "sha256": "0" * 64})
    with pytest.raises(ConfigError):   # a file that is not the pinned one is refused and removed
        R.ensure(tmp_path / "other", download=lambda url, dest: dest.write_bytes(payload))
    assert not list((tmp_path / "other").rglob("*.zip"))
