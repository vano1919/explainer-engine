"""The S3 layout test: ray caster, camera rules, set-file check, prompt builder, the s0 agreement with the master's text."""
import math
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.training.pods import xworld_v2_s3 as S
from explainer_engine.training.pods.xworld_v2_scenes import load

PODS = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods"
SCENES = PODS / "stories" / "v2"


def _set(name):
    return S.load_set(SCENES / "sets" / f"{name}.set.json")


def _box_set(boxes, kind="exterior"):
    s = {"scene": "t", "kind": kind, "objects": [{"id": f"b{i}", "shape": "box", "min": lo, "max": hi, "label": f"box {i}",
                                                    "color": [200, 60, 50]} for i, (lo, hi) in enumerate(boxes)],
         "people": [], "axis": [], "shots": {}}
    if kind == "interior":
        s["room"] = {"min": [-3, -3, 0], "max": [3, 3, 3]}
    return s


def test_a_box_straight_ahead_is_hit_at_its_distance_and_a_box_behind_it_is_hidden():
    cam = {"pos": np.array([0, 0, 1.0]), "look_at": np.array([0, 10, 1.0]), "vfov": 45}
    s = _box_set([([-1, 5, 0], [1, 6, 2]), ([-1, 8, 0], [1, 9, 2])])
    ident, t, _ = S.render(s, cam, 64, 36)
    assert ident[18, 32] == 0 and abs(t[18, 32] - 5.0) < 0.05
    assert not (ident == 1).any()


def test_room_walls_are_hit_from_inside():
    s = _box_set([], kind="interior")
    cam = {"pos": np.array([0, 0, 1.5]), "look_at": np.array([0, 3, 1.5]), "vfov": 45}
    ident, t, _ = S.render(s, cam, 64, 36)
    assert abs(t[18, 32] - 3.0) < 0.05 and ident[18, 32] == -2
    down = {"pos": np.array([0, 0, 1.5]), "look_at": np.array([0, 1.0, 0.0]), "vfov": 45}
    assert S.render(s, down, 64, 36)[0][18, 32] == -3  # the floor


def test_close_up_head_fills_a_third_to_a_half_of_the_frame_and_the_camera_stays_in_the_room():
    s = _set("tent")
    cam = S.camera(s, s["shots"]["s2"])
    p = next(p for p in s["people"] if p["id"] == "napoleon")
    d = float(np.linalg.norm(cam["pos"][:2] - np.array(p["pos"])))
    visible = 2 * d * math.tan(math.radians(cam["vfov"]) / 2)
    assert 0.35 <= 0.24 / visible <= 0.60
    lo, hi = np.array(s["room"]["min"]), np.array(s["room"]["max"])
    for spec in s["shots"].values():
        pos = S.camera(s, spec)["pos"]
        assert (pos > lo).all() and (pos < hi).all()


def test_side_b_is_the_other_side_of_the_axis_from_side_a():
    s = _set("tent")
    pos = {x["id"]: np.array(x["pos"]) for x in s["people"]}
    ax = pos["general"] - pos["napoleon"]
    def side(spec):
        v = S.camera(s, spec)["pos"][:2] - pos["general"]
        return np.sign(ax[0] * v[1] - ax[1] * v[0])
    a = side({"subject": "general", "size": "medium", "side": "A"})
    b = side({"subject": "general", "size": "medium", "side": "B"})
    assert a != 0 and a == -b


def test_set_files_pass_the_schema_check_and_a_bad_one_fails():
    for n in S.SCENES:
        _set(n)
    s = _box_set([([1, 1, 1], [0, 2, 2])])
    s["shots"] = {}
    with pytest.raises(ValueError):
        S.check_set(s)
    t = _set("tent"); t["people"][0]["pos"] = [9, 9]
    with pytest.raises(ValueError):
        S.check_set(t)


def test_the_prompt_names_image_2_lists_only_visible_objects_left_to_right_and_uses_three_images_at_most():
    for name in S.SCENES:
        sc = next(x for x in load(SCENES) if x["name"] == name)
        s = _set(name)
        for shot in sc["shots"][1:]:
            ident, _, _ = S.render(s, S.camera(s, s["shots"][shot["id"]]), 320, 180)
            for v in ("S1", "S3d", "S3b"):
                prompt, refs = S.shot_prompt(sc, shot, s, ident, v)
                assert len(refs) <= 3 and refs[0] == "master"
                marker = {"S1": None, "S3d": "grey depth sketch", "S3b": "coloured blockout"}[v]
                assert (marker in prompt) if marker else ("Image 2 is a" not in prompt)
                assert ("layout" in refs) == (v != "S1")
            vis = [o["id"] for o, _ in S.visible(s, ident, "objects")]
            text = S.shot_prompt(sc, shot, s, ident, "S3d")[0]
            sentence = text[text.index("Image 2 is a grey"):text.index("Image 2 is only a guide")]  # the layout sentence only
            assert all(o["id"] in vis or o["label"] not in sentence for o in s["objects"])


def test_s0_of_the_tent_puts_the_table_in_the_centre_third_and_the_entrance_in_the_right_third():
    s = _set("tent")
    ident, _, _ = S.render(s, S.camera(s, s["shots"]["s0"]), 320, 180)
    ids = [o["id"] for o in s["objects"]]
    cx = lambda k: np.where(ident == ids.index(k))[1].mean() / 320
    assert 1 / 3 < cx("table") < 2 / 3 and cx("entrance") > 2 / 3 and cx("bed") < 1 / 3


def test_spearman_of_a_monotone_pair_is_one_and_of_a_reversed_pair_minus_one():
    x = np.arange(100.0)
    assert S.spearman(x, x ** 3) > 0.999 and S.spearman(x, -x) < -0.999


def test_pod_script_runs_s3_last_and_keeps_the_vault_check():
    sh = (PODS / "xworld_v2_p2s.sh").read_text(encoding="utf-8")
    assert "xworld_v2_s3.py" in sh and sh.index("xworld_v2_s2.py") < sh.index("xworld_v2_s3.py") < sh.index("vault")


def test_score_correlates_an_estimated_depth_with_the_rendered_layout_of_its_shot(tmp_path):
    from PIL import Image
    s = _set("tent")
    ident, tmap, shade = S.render(s, S.camera(s, s["shots"]["s1"]), 160, 90)
    np.save(tmp_path / "tent_s1_t.npy", tmap)
    Image.new("RGB", (160, 90)).save(tmp_path / "tent_s1_S3d.png")
    truth = 1.0 / tmap
    good = S.score(tmp_path, estimator=lambda img: np.nan_to_num(truth, nan=0.0))
    bad = S.score(tmp_path, estimator=lambda img: -np.nan_to_num(truth, nan=0.0))
    assert good["tent_s1_S3d.png"] > 0.99 and bad["tent_s1_S3d.png"] < -0.99
