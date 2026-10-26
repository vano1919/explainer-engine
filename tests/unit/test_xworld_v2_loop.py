import numpy as np
import pytest
from PIL import Image

from explainer_engine.training.pods import xworld_v2_loop as L
from explainer_engine.training.pods import xworld_v2_s3 as S3

ROUND1 = {"round": 1, "rows": ["S1", "S2T", "S2E", "S3cA", "S3cAB", "M2", "M4", "M5"]}


def test_round_one_draws_the_68_pictures_of_the_plan_and_m5_only_the_small_moves():
    j = L.jobs(ROUND1)
    assert len(j) == 68
    per = {}
    for x in j:
        per[x["row"]] = per.get(x["row"], 0) + 1
    assert per == {"S1": 16, "S2T": 4, "S2E": 4, "S3cA": 16, "S3cAB": 16, "M2": 4, "M4": 4, "M5": 4}
    assert {x["shot"] for x in j if x["row"] == "M5"} == {"s2"}
    assert all((x["kind"] == "grid") == L.ROWS[x["row"]]["grid"] for x in j)


def test_a_round_config_refuses_two_changes_on_one_row_an_unknown_cause_and_a_round_two_row_without_its_change():
    ch = {"row": "M4", "cause": "prompt", "change": "prop list", "expected": "props ok"}
    assert L.check_round({**ROUND1}) == []
    two = {"round": 2, "rows": ["M4"], "changes": [ch, {**ch, "cause": "passes"}]}
    assert any("two changes on row M4" in b for b in L.check_round(two))
    assert any("no known cause" in b for b in L.check_round({"round": 2, "rows": ["M4"], "changes": [{**ch, "cause": "luck"}]}))
    assert any("no recorded change" in b for b in L.check_round({"round": 2, "rows": ["M4", "M2"], "changes": [ch]}))
    assert any("unknown row" in b for b in L.check_round({"rows": ["S9"]}))
    assert L.check_round({"round": 2, "rows": ["M4"], "changes": [ch]}) == []
    with pytest.raises(ValueError):
        L.dry({"round": 2, "rows": ["M4"], "changes": [ch, ch]}, "/tmp/unused")


def test_the_two_by_two_control_canvas_holds_each_cameras_depth_in_its_own_panel_with_no_seam(tmp_path):
    ds = [Image.new("RGB", (1280, 720), (40 * i + 20,) * 3) for i in range(4)]
    c = L.control_canvas(ds)
    assert c.size == (2560, 1408) and all(v % 64 == 0 for v in c.size)
    for i in range(4):
        a = np.asarray(L.panel_of(c, i))
        assert a.shape == (704, 1280, 3) and abs(a.mean() - (40 * i + 20)) < 2 and a.std() < 2
    seam = np.asarray(c)[:, 1275:1285].astype(int)  # across the vertical middle: the two panels, no gutter colour between them
    assert set(np.unique(seam)) <= {20, 60, 100, 140}  # no gutter or blend colour, only the panels' own values


def test_the_inpaint_canvas_keeps_the_master_in_panel_one_and_masks_the_other_three():
    master = Image.new("RGB", (1280, 720), (200, 30, 30))
    img, mask = L.inpaint_canvas(master)
    m = np.asarray(mask)
    assert m[:704, :1280].max() == 0 and (m[:704, 1280:] == 255).all() and (m[704:] == 255).all()
    assert abs(np.asarray(L.panel_of(img, 0))[..., 0].mean() - 200) < 2


def test_set_files_agree_with_their_masters_at_s0_and_a_moved_landmark_is_caught():
    for n in L.SCENES:
        s = S3.load_set(L.PODS / "stories" / "v2" / "sets" / f"{n}.set.json")
        assert L.s0_agreement(s, L.load_marks(n))["ok"], n
    s = S3.load_set(L.PODS / "stories" / "v2" / "sets" / "tent.set.json")
    s["people"][1]["pos"] = [-1.5, 3.2]
    r = L.s0_agreement(s, L.load_marks("tent"))
    assert not r["ok"] and any("general" in p for p in r["problems"])


def test_s0_depth_spearman_is_checked_against_a_master_depth():
    s = S3.load_set(L.PODS / "stories" / "v2" / "sets" / "tent.set.json")
    _, t, _ = S3.render(s, S3.camera(s, s["shots"]["s0"]), 160, 90)
    assert L.s0_agreement(s, L.load_marks("tent"), 1.0 / t)["spearman"] > 0.99
    flipped = L.s0_agreement(s, L.load_marks("tent"), t)
    assert not flipped["ok"] and flipped["spearman"] < 0


def test_reprojecting_into_the_same_camera_keeps_the_picture_and_a_sideways_step_shifts_it_and_leaves_holes():
    s = S3.load_set(L.PODS / "stories" / "v2" / "sets" / "tent.set.json")
    cam = S3.camera(s, s["shots"]["s0"])
    ident, t, _ = S3.render(s, cam, 160, 90)
    rgb = (np.random.default_rng(1).random((90, 160, 3)) * 255).astype(np.uint8)
    same, holes = L.reproject(rgb, 1.0 / t, cam, cam, t)
    assert holes.mean() < 0.25 and (same[~holes] == rgb[~holes]).mean() > 0.6
    step = {**cam, "pos": np.asarray(cam["pos"]) + np.array([0.6, 0, 0])}
    moved, holes2 = L.reproject(rgb, 1.0 / t, cam, step, t)
    assert holes2.mean() > holes.mean()


def test_ssim_is_one_for_a_frozen_plate_and_low_for_a_new_background():
    rng = np.random.default_rng(2)
    a = Image.fromarray((rng.random((144, 256, 3)) * 255).astype(np.uint8))
    b = Image.fromarray((rng.random((144, 256, 3)) * 255).astype(np.uint8))
    assert L.plate_ssim(a, a) > 0.99 and L.plate_ssim(a, b) < L.PLATE_MAX
    people = np.zeros((144, 256), bool); people[:, :100] = True
    assert L.plate_ssim(a, a, people) > 0.99


def test_landmark_order_match_on_a_synthetic_case():
    exp = ["bed", "table", "pole", "entrance"]
    assert L.order_match(exp, ["bed", "table", "pole", "entrance"]) == 1.0
    assert L.order_match(exp, ["entrance", "pole", "table", "bed"]) == 0.25
    assert L.order_match(exp, ["bed", "chair", "pole", "entrance"]) == 0.75  # chair is not in the vocabulary: ignored
    assert L.order_match([], ["bed"]) is None


def test_a_shot_passes_only_when_geometry_plate_and_grain_were_measured_and_nothing_failed():
    ok = {"geometry": 0.8, "plate": 0.3, "grain_ok": True, "order": 0.9}
    assert L.shot_result("S3cA", ok)["passed"]
    assert L.shot_result("S3cA", {**ok, "geometry": 0.7})["fails"] == ["geometry"]  # control rows need 0.75
    assert L.shot_result("S2T", {**ok, "geometry": 0.7})["passed"]  # the others 0.6
    assert L.shot_result("S1", {**ok, "plate": 0.95})["fails"] == ["plate"]
    assert not L.shot_result("S2T", {"geometry": 0.9, "plate": 0.2})["passed"]  # grain not measured
    assert L.shot_result("S2T", {**ok, "props_ok": False})["fails"] == ["props"]


def test_attribution_follows_the_plans_order_first_match_wins():
    assert L.attribute("S3cA", ["geometry", "plate"], s0_ok=False) == "3d_code"
    assert L.attribute("S3cA", ["geometry"]) == "strategy_setting"
    assert L.attribute("S2T", ["geometry", "props"]) == "strategy_limit"
    assert L.attribute("S1", ["plate", "geometry"]) == "strategy_limit"  # geometry comes before the plate in the plan
    assert L.attribute("S1", ["plate"]) == "frozen_plate"
    assert L.attribute("M2", ["props"]) == "prompt" and L.attribute("M2", ["props"], prompt_rounds_failed=2) == "reference"
    assert L.attribute("M2", ["people"]) == "identity_reference" and L.attribute("M2", ["grain"]) == "passes"
    assert L.attribute("M2", []) is None


def test_the_stop_rule_success_no_progress_and_max_rounds():
    r = lambda n, c, eye=None: {"round": n, "rows": {"M4": {11: c, 23: c}}, "eye_winner": eye}
    assert L.stop([r(1, 7, "M4")])[0] == "success"
    assert L.stop([r(1, 7)])[0] == "go_on"  # the eye has not chosen it
    assert L.stop([r(1, 6, "M4")])[0] == "go_on"
    assert L.stop([r(1, 3), r(2, 3), r(3, 3), r(4, 3)])[0] == "no_progress"
    assert L.stop([r(1, 3), r(2, 4), r(3, 4), r(4, 4)])[0] == "max_rounds"
    assert L.stop([r(1, 3), r(2, 3)])[0] == "go_on"


def test_the_attribution_file_has_one_line_per_failure_and_dry_writes_the_job_list(tmp_path):
    md = L.attribution_md(1, [{"row": "S1", "scene": "tent", "seed": 11, "shot": "s1", "fails": ["plate", "geometry"], "cause": "strategy_limit"}])
    assert md.count("| S1 |") == 2 and "strategy_limit" in md
    n = len(L.dry(ROUND1, tmp_path))
    assert n == 68 and (tmp_path / "jobs.json").exists()
