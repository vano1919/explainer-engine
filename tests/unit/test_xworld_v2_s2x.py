from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.training.pods import xworld_v2_s2x as X
from explainer_engine.training.pods.xworld_v2_scenes import load

PODS = Path(X.__file__).parent
MORE = PODS / "stories" / "v2" / "more"


def _scenes():
    return [X.with_continuation(s, MORE) for s in load(PODS / "stories" / "v2") if s["name"] in X.SCENES]


def test_twelve_grids_two_scenes_two_seeds_three_grids_and_g2e_points_at_its_own_grid_1():
    j = X.jobs(_scenes())
    assert len(j) == 12 and {x["seed"] for x in j} == {11, 23} and {x["grid"] for x in j} == set(X.GRIDS)
    for x in j:
        assert (x["ref"] is not None) == (x["grid"] == "g2e")
        if x["ref"]:
            assert x["ref"] == x["name"].replace("_g2e", "_g1")


def test_grid_size_and_panel_size_are_multiples_of_64_and_the_grid_is_two_panels_wide():
    assert X.GRID_W == 2 * X.PANEL_W and X.GRID_H == 2 * X.PANEL_H
    assert all(v % 64 == 0 for v in (X.GRID_W, X.GRID_H, X.PANEL_W, X.PANEL_H))


def test_cast_and_place_text_are_identical_character_for_character_in_all_three_prompts():
    for sc in _scenes():
        a, b, c = X.grid_prompt(sc, 0), X.grid_prompt(sc, 1), X.edit_prompt(sc)
        for role, cast in sc["cast"].items():
            for p in (a, b, c):
                assert f"{role}: {cast['look']} {cast['face']}" in p
        assert all(sc["place"] in p for p in (a, b, c))
        assert X.cast_text(sc) in a and X.cast_text(sc) in b and X.cast_text(sc) in c
        assert c.count("Image 1 is this scene") == 1 and "Image 1" not in a + b


def test_every_continuation_shot_carries_the_cards_face_text_and_names_size_and_angle_and_the_behind_sentence():
    for sc in _scenes():
        extra = sc["shots"][X.PANELS:]
        assert [s["id"] for s in extra] == ["s5", "s6", "s7", "s8"]
        for s in extra:
            for r in s["faces"]:
                assert sc["cast"][r]["look"] in s["desc"] and sc["cast"][r]["face"] in s["desc"]
            assert s["size"] in ("wide", "medium", "close") and s["layout"]
        assert "Exactly two people are in the frame" in X.grid_prompt(sc, 1)  # s8 is over the shoulder
        assert X.grid_prompt(sc, 1).count("panel:") == 4


def test_the_continuation_contains_no_new_cast_and_close_shots_drop_the_footwear():
    for sc in _scenes():
        for s in sc["shots"][X.PANELS:]:
            assert set(s["faces"]) <= set(sc["cast"])
    for sc in _scenes():
        close = [s for s in sc["shots"] if s["size"] == "close"]
        assert close and all("boots" not in X.frame_desc(s) and "sandals" not in X.frame_desc(s) for s in close)


def test_the_identity_report_separates_same_person_from_another_and_handles_missing_faces():
    rng = np.random.default_rng(0)
    a, b = (lambda v: v / np.linalg.norm(v))(rng.normal(size=16)), (lambda v: v / np.linalg.norm(v))(rng.normal(size=16))
    emb = {("g1", 0): [a], ("g1", 1): [a], ("g2t", 0): [a], ("g2e", 0): [b]}
    r = X.identity_report(emb)
    assert r["within_g1"] == 1.0 and r["cross_g2t"] == 1.0 and r["cross_g2e"] < 0.9
    assert X.identity_report({})["within_g1"] is None


def test_sheet_and_grain_build_from_whatever_panels_exist(tmp_path):
    for g, col in (("g1", 60), ("g2t", 120)):
        for k in range(X.PANELS):
            Image.fromarray(np.full((704, 1280, 3), col + k, np.uint8)).save(tmp_path / f"tent_11_{g}_p{k}.png")
    made = X.sheet(tmp_path)
    assert [p.name for p in made] == ["s2x_sheet_tent_11.jpg"] and made[0].exists()
    r = X.grain(tmp_path, "tent", 11)
    assert set(r["mean"]) == {"g1", "g2t"} and set(r["ratio"]) == {"g2t"}
    res = X.measure(tmp_path)
    assert res["panels"]["tent_11_g1"] == 4 and (tmp_path / "s2x_measures.json").exists()
