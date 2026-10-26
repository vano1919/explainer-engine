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
    flat = np.asarray(L.panel_of(img, 3))
    assert flat.reshape(-1, 3).std(axis=0).max() < 1 and tuple(flat[0, 0]) == (200, 30, 30)  # the master's mean colour, no edges
    drift = Image.new("RGB", (2560, 1408), (9, 9, 9))
    back = L.paste_back(drift, master)
    assert np.asarray(L.panel_of(back, 0))[0, 0].tolist() == [200, 30, 30] and np.asarray(L.panel_of(back, 1))[0, 0].tolist() == [9, 9, 9]


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


# --- the runner (no model) -------------------------------------------------------------------------------------------------------

def _scenes_with_more():
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    from explainer_engine.training.pods.xworld_v2_scenes import load
    return R, [s for s in load(L.PODS / "stories" / "v2") if s["name"] in L.SCENES]


def test_every_row_has_a_prompt_with_the_card_text_and_m4_names_the_established_wide_panel():
    R, scenes = _scenes_with_more()
    for sc in scenes:
        for row in ("S2T", "S2E", "M2", "M4"):
            p = R.prompts(sc, row)
            assert X_cast(sc) in p and sc["place"] in p and p.count("panel:") == 4
        assert "established wide shot" in R.prompts(sc, "M4") and "established wide shot" not in R.prompts(sc, "M2")
        assert "Image 1 is this scene" in R.prompts(sc, "S2E") and "Image 1" not in R.prompts(sc, "S2T")
        for sid in L.SHOTS:
            assert R.prompts(sc, "S3cA", sid).startswith("xworld style") and R.prompts(sc, "S3cAB", sid)
            assert R.prompts(sc, "S1", sid)  # a shot without a face (rome s3, a crowd) falls back to the plain edit prompt


def X_cast(sc):
    return " ".join(f"{r}: {c['look']} {c['face']}" for r, c in sc["cast"].items())


def test_the_control_inputs_are_built_for_every_scene_without_a_model(tmp_path):
    R, scenes = _scenes_with_more()
    p2s = tmp_path / "p2s"; p2s.mkdir()
    for sc in scenes:
        Image.fromarray((np.random.default_rng(3).random((720, 1280, 3)) * 255).astype(np.uint8)).save(p2s / f"{sc['name']}_11_s0.png")
    est = lambda img: np.random.default_rng(4).random((90, 160))
    made = R.build_inputs({"rows": ["S3cA", "M2", "M4", "M5"]}, scenes, L.PODS / "stories" / "v2" / "sets", p2s, tmp_path / "in", est)
    for n in L.SCENES:
        for sid in L.SHOTS:
            assert (tmp_path / "in" / f"{n}_{sid}_depth.png").exists()
        assert Image.open(tmp_path / "in" / f"{n}_m2_control.png").size == (2560, 1408)
        assert Image.open(tmp_path / "in" / f"{n}_m4_mask.png").size == (2560, 1408)
        for sid in L.SMALL_MOVES[n]:
            assert Image.open(tmp_path / "in" / f"M5_{n}_{sid}_holes.png").mode == "L"
    assert len(made) == 2 * (4 + 4 + 2 + 3)  # per scene: 4 depths, 4 canvas files, 2 noise-fill M6 files, 3 for the one small move


def test_control_end_cuts_on_the_timestep_not_on_call_counts():
    class Tr:
        def __init__(self):
            self.seen = []

        def forward(self, *a, **kw):
            self.seen.append(kw.get("control_context_scale"))
    tr = Tr()
    ts = [1000, 1000, 900, 900, 600, 600, 400, 400]  # two calls per step here, but the cut must not depend on that
    with _run().ControlEnd(tr, 0.5) as ce:
        for t in ts:
            tr.forward(timestep=t, control_context_scale=1.0)
    assert tr.seen == [1.0] * 6 + [0.0] * 2 and ce.cut_t == 400 and ce.ok()
    assert tr.forward.__func__ is Tr.forward  # restored


def test_control_end_is_a_setup_fail_when_the_kwargs_are_not_seen():
    class Tr:
        def forward(self, *a, **kw):
            return None
    tr = Tr()
    with _run().ControlEnd(tr) as ce:
        for _ in range(4):
            tr.forward(1, 2)  # positional: nothing to read
    assert not ce.ok() and "ok=False" in ce.report()


def test_round_with_end50_rows_and_row_scenes():
    cfg = {"rows": ["M2E50", "M4E50", "M4"], "seeds": [11], "row_scenes": {"M4": ["tent"]}}
    assert L.check_round(cfg) == []
    js = L.jobs(cfg)
    assert [(j["row"], j["scene"]) for j in js] == [("M2E50", "tent"), ("M2E50", "rome"), ("M4E50", "tent"), ("M4E50", "rome"), ("M4", "tent")]
    assert L.ROWS["M2E50"]["end"] == 0.5 and L.ROWS["M4E50"]["base"] == "M4"


def test_connected_fail_is_an_identity_cause():
    r = L.shot_result("M2", {"geometry": 0.9, "plate": 0.2, "grain_ok": True, "connected": False})
    assert r["fails"] == ["connected"] and not r["passed"]
    assert L.attribute("M2", r["fails"]) == "identity_reference"


def _run():
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    return R


def test_connectedness_and_style_bars_against_s2t():
    same = {"s1": [np.array([1.0, 0.0])], "s2": [np.array([1.0, 0.0])]}
    other = {"s1": [np.array([1.0, 0.0])], "s2": [np.array([0.0, 1.0])]}
    assert L.connectedness(same) == 1.0 and L.connectedness(other) == 0.0
    assert L.connectedness({"s1": [np.array([1.0, 0.0])], "s2": []}) is None
    assert L.connected_ok(0.6, 0.5) is True and L.connected_ok(0.4, 0.5) is False and L.connected_ok(None, 0.5) is None
    assert L.style_ok(0.46, 0.5) is True and L.style_ok(0.4, 0.5) is False


def test_noise_fill_is_not_flat_and_the_flat_fill_is_detected_as_copied():
    master = Image.new("RGB", (1280, 704), (120, 90, 60))
    img, mask = L.inpaint_canvas(master, fill="noise")
    under = np.asarray(img, float)[704:, :, :].reshape(-1, 3)
    assert under.std(axis=0).min() > 30  # no colour to copy under the mask
    assert np.asarray(mask)[704:, :].min() == 255 and np.asarray(mask)[:704, :704].max() == 0
    flat, _ = L.inpaint_canvas(master, fill="flat")
    assert L.fill_survived(np.asarray(flat), master) == 1.0  # the round 1 bug: a copied fill scores 1
    assert L.fill_survived(np.asarray(img), master) < 0.1


def test_round_two_rows_and_the_one_change_each_rule():
    cfg = {"round": 2, "rows": ["S2Tp", "S2Ep", "S2L", "M6"], "seeds": [11, 23], "scenes": ["tent", "rome"],
           "changes": [{"row": r, "cause": c, "change": "x", "expected": "y"} for r, c in
                       (("S2Tp", "prompt"), ("S2Ep", "prompt"), ("S2L", "strategy_limit"), ("M6", "strategy_setting"))]}
    assert L.check_round(cfg) == []
    assert len(L.jobs(cfg)) == 16  # 4 rows x 2 scenes x 2 seeds
    assert all(L.ROWS[r]["grid"] for r in cfg["rows"])


def test_round_two_prompts_put_the_behind_line_first_and_name_the_layout():
    R = _run()
    sc = {"name": "tent", "place": "A tent.", "cast": {"general": {"look": "tall", "face": "sharp"}},
          "shots": [{"id": "s1", "desc": "a general at a map, wide.", "size": "medium", "layout": "a camp bed on the left.",
                     "change": "", "faces": ["general"]}]}
    shots = sc["shots"]
    p = R.panels_behind(sc, shots)
    assert p.startswith("top-left panel: Behind and around the subject: a camp bed on the left.")
    assert p.count("camp bed") == 1  # moved, not duplicated
    s = R.S3.load_set(R.SETS_DIR / "tent.set.json")
    cam, lm = R.layout_words(s, "s2")
    assert cam == "close shot, eye angle" and lm and not any("(" in x for x in lm)  # names only, no colour


def test_a_factor_cell_is_a_row_and_the_l16_design_is_orthogonal():
    from explainer_engine.training.pods import xworld_v2_cells as K
    assert "X_g_e_1_0" in L.ROWS and "X_q_e_1_0" not in L.ROWS
    assert L.ROWS["X_p_s_0_1"]["grid"] is False and L.ROWS["X_g_c_1_0"]["grid"] is True
    cells = K.l16()
    assert len(cells) == 16 and len(set(cells)) == 16 and K.is_orthogonal(cells)
    left = K.design()
    assert len(left) == 15 and "X_g_n_0_0" not in left  # round 2's S2Tp
    assert K.draws(left) == (28, 64)  # pair cells draw s2 and s4 only
    cfg = {"round": 3, "rows": left[:2], "seeds": [11], "scenes": ["tent"],
           "changes": [{"row": r, "cause": "prompt", "change": "cell", "expected": "main effect"} for r in left[:2]]}
    assert L.check_round(cfg) == []
    js = L.jobs({"rows": ["X_p_e_0_0"], "seeds": [11], "scenes": ["tent"]})
    assert [j["shot"] for j in js] == ["s2", "s4"]  # a pair draws its two target shots (Opus plan 10), one picture per shot


def test_cell_prompts_refs_and_the_grey_copy_check():
    R = _run()
    from explainer_engine.training.pods import xworld_v2_cells as K
    from explainer_engine.training.pods.xworld_v2_scenes import load
    sc = next(s for s in load(R.__file__.rsplit("/", 1)[0] + "/stories/v2") if s["name"] == "tent")
    g = R.cell_prompt(sc, K.parse("X_g_n_1_1"))
    assert "Camera:" in g and "exactly one" in g and g.count("-left panel:") + g.count("-right panel:") + g.count("bottom-left panel:") + g.count("bottom-right panel:") >= 4 and "Behind and around the subject" in g
    assert "Camera:" not in R.cell_prompt(sc, K.parse("X_g_n_0_0"))
    pair = R.cell_prompt(sc, K.parse("X_p_c_0_1"), "s4")
    assert "left panel:" in pair and "right panel:" in pair and "grey" in pair and "exactly one" in pair
    master = Image.new("RGB", (1280, 704), (90, 70, 50))
    sheets = [Image.new("RGB", (64, 64)), Image.new("RGB", (64, 64))]
    assert R.cell_refs(K.parse("X_g_n_0_0"), master, sheets) == []
    assert len(R.cell_refs(K.parse("X_g_e_0_0"), master, sheets)) == 1
    assert len(R.cell_refs(K.parse("X_g_s_0_0"), master, sheets)) == 2
    ps = R.cell_refs(K.parse("X_p_s_0_0"), master, sheets)
    assert len(ps) == 3 and ps[0].size == (2560, 704)  # the pair canvas is Image 1 (at most three images)
    cv = R.cell_refs(K.parse("X_g_c_0_0"), master, sheets)[0]
    assert cv.size == (2560, 1408) and np.asarray(cv)[900, 1900].tolist() == [128, 128, 128]
    grey = Image.new("RGB", (2560, 704), (128, 128, 128)); grey.paste(master, (0, 0))
    assert L.grey_copied(grey, "p") > 0.99
    assert L.grey_copied(np.random.default_rng(1).integers(0, 255, (704, 2560, 3), dtype=np.uint8), "p") < 0.05


def test_heldout_ship_scene_and_no_scene_words_in_templates():
    """General logic (ვანო 2026-10-26): the held-out place loads, and no scene's own words sit in the method code."""
    import json
    import re
    from pathlib import Path
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    base = Path(R.__file__).resolve().parent
    ship = json.loads((base / "stories/v2/heldout/ship.json").read_text(encoding="utf-8"))
    st = json.loads((base / "stories/v2/sets/ship.set.json").read_text(encoding="utf-8"))
    assert ship["name"] == st["scene"] == "ship" and len(ship["shots"]) == 5
    assert {p["id"] for p in st["people"]} == set(ship["cast"])
    assert [r["name"] for r in R.load_scenes(base / "stories/v2")].count("ship") == 1
    code = " ".join((base / f).read_text(encoding="utf-8").lower() for f in ("xworld_v2_loop_run.py", "xworld_v2_cells.py", "xworld_v2_dirs.py"))
    for word in ("colosseum", "fountain", "baker", "legionary", "boulder", "napoleon", "lighthouse", "mast", "crates"):
        assert not re.search(r"\b" + word + r"\b", code), word


def test_round_3a_extras_turnaround_sketch_paintover():
    """Round 3a: the +dir/+sk/+dsk cells, the direction views, the sketch, the shaded plate, stages and the PO rows (no model)."""
    from pathlib import Path
    from PIL import Image
    from explainer_engine.training.pods import xworld_v2_cells as K
    from explainer_engine.training.pods import xworld_v2_dirs as D
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    from explainer_engine.training.pods import xworld_v2_s3 as S3
    base = Path(R.__file__).resolve().parent / "stories/v2"
    assert K.parse("X_g_n_0_0+dsk")["E"] == "dsk" and K.parse("X_g_n_0_0")["E"] == "" and K.parse("X_g_n_0_0+zzz") is None
    assert K.is_orthogonal(K.l16())  # the extras are not part of the L16
    scs = {s["name"]: s for s in R.load_scenes(base)}
    for name in ("tent", "rome", "ship", "tundra"):
        s = S3.load_set(base / f"sets/{name}.set.json")
        S3.check_set(s)
        lm = D.view_landmarks(s)
        assert len(lm) == 4 and lm[0], name  # the master direction always shows something
        assert [D.view_index(s, "s0")] == [0]
        sk = D.sketch_canvas(s, ("s0", "s1", "s2", "s3"), (320, 176))
        assert sk.size == (640, 352)
        plate = D.shaded_plate(s, "s2", 160, 88)
        assert plate.size == (160, 88) and np.asarray(plate).std() > 1  # not a flat picture
        assert D.turnaround_prompt(scs[name], s, "xworld style").count("panel, the view") == 4
    sc = scs["rome"]
    c = K.parse("X_g_n_0_0+dsk")
    p = R.cell_prompt(sc, c)
    assert "Image 1 is a 2x2 picture of the same empty place" in p and "Image 2 is a plain line sketch" in p
    assert "Image 2 is a 2x2 picture" in R.cell_prompt(sc, K.parse("X_g_e_0_0+dir"))  # the reference image comes first
    img = Image.new("RGB", (64, 36))
    assert len(R.cell_refs(c, img, [], [img, img])) == 2
    with pytest.raises(ValueError):
        R.cell_refs(K.parse("X_g_e_0_0+dsk"), img, [], [img, img, img])
    cfg = {"stages": [{"rows": ["TURN"], "scenes": ["rome"], "seeds": [11]},
                      {"rows": ["PO55", "X_g_n_0_0+dir"], "scenes": ["rome", "ship"], "seeds": [11], "last_scenes": ["ship"]}]}
    js = L.jobs(cfg)
    assert [(j["row"], j["scene"], j["shot"]) for j in js] == [("TURN", "rome", None), ("PO55", "rome", "s2"), ("PO55", "rome", "s4"),
                                                               ("X_g_n_0_0+dir", "rome", None), ("PO55", "ship", "s2"), ("PO55", "ship", "s4"), ("X_g_n_0_0+dir", "ship", None)]
    pp, roles = R.po_people_prompt(sc, R.shot_of(sc, "s2"), R.sets_of(sc))
    assert roles == ["baker"] and "Image 1 is the empty place" in pp and "model sheet of baker" in pp and "percent of its height" in pp
    assert "no people" in R.po_plate_prompt(sc, R.shot_of(sc, "s2"))


def test_layout_words_carry_no_debug_colour():
    """Round 2 finding (2026-10-26): S2L named the ray-cast colours ("the Colosseum (yellow)") and the picture drew purple houses and a yellow pole."""
    from pathlib import Path
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    from explainer_engine.training.pods import xworld_v2_s3 as S3
    base = Path(R.__file__).resolve().parent / "stories/v2"
    for name in ("tent", "rome", "ship", "tundra"):
        s = S3.load_set(base / f"sets/{name}.set.json")
        for sid in s["shots"]:
            cam, lm = R.layout_words(s, sid)
            text = (cam + " " + ", ".join(lm)).lower()
            assert not any(c in text for c in S3.COLOR_WORDS), (name, sid, text)


def test_round_3b_backdrop_per_panel_and_config():
    """Round 3b: +dpl cuts the turnaround picture into one empty backdrop per panel by the shot's direction; the config loads and its jobs are valid."""
    import json
    from pathlib import Path
    from PIL import Image
    from explainer_engine.training.pods import xworld_v2_cells as K
    from explainer_engine.training.pods import xworld_v2_dirs as D
    from explainer_engine.training.pods import xworld_v2_loop_run as R
    from explainer_engine.training.pods import xworld_v2_s3 as S3
    base = Path(R.__file__).resolve().parent / "stories/v2"
    assert K.parse("X_g_n_0_0+dpl")["E"] == "dpl"
    s = S3.load_set(base / "sets/rome.set.json")
    ids = ("s1", "s2", "s3", "s4")
    turn = Image.new("RGB", (2 * D.PANEL[0], 2 * D.PANEL[1]), (10, 20, 30))
    g = D.plate_grid(turn, s, ids)
    assert g.size == (2 * D.PANEL[0], 2 * D.PANEL[1])
    for sid in ids:
        i, l, t, r, b = D._crop_box(s, sid)
        assert 0 <= i < 4 and 0 <= l < r <= D.PANEL[0] and 0 <= t < b <= D.PANEL[1]
    words = D.plate_words(s, ids, 1)
    assert words.startswith("Image 1 is a 2x2 picture of the EMPTY backdrop") and "ADD the people" in words
    cfg = json.loads((Path(R.__file__).resolve().parent / "loop/round_3b.json").read_text(encoding="utf-8"))
    for st in cfg["stages"]:
        for row in st["rows"]:
            assert row in cfg["rows"]
