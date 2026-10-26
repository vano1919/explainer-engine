"""The P2S reference test: the grid, the image naming in the prompt, the three-image limit, the weight order."""
from pathlib import Path

from explainer_engine.training.pods import xworld_v2_p2s as P
from explainer_engine.training.pods import xworld_v2_p2s_sheet as S
from explainer_engine.training.pods.xworld_v2_scenes import load

PODS = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods"


def _jobs():
    return P.jobs([s for s in load(PODS / "stories" / "v2") if s["name"] in P.SCENES])


def test_the_grid_is_two_scenes_four_sheets_and_sixty_four_cells():
    j = _jobs()
    assert sum(x["kind"] == "master" for x in j) == 2 and sum(x["kind"] == "sheet" for x in j) == 4
    cells = [x for x in j if x["kind"] in P.REFS]
    assert len(cells) == 2 * len(P.REFS) * len(P.CFGS) * len(P.WEIGHTS) * 4 == 32
    assert {x["cfg"] for x in cells} == set(P.CFGS) and {x["weight"] for x in cells} == set(P.WEIGHTS)


def test_p2s_names_the_images_by_position_and_never_passes_more_than_three():
    j = _jobs()
    assert max(len(x["refs"]) for x in j) <= P.MAX_IMAGES
    p2s = [x for x in j if x["kind"] == "P2S" and len(x["refs"]) > 1]
    assert p2s and all("Image 1 is the master frame" in x["prompt"] and "Image 2 is the model sheet of" in x["prompt"] for x in p2s)
    assert all(x["refs"] == [x["refs"][0]] for x in j if x["kind"] == "P2F")  # master only


def test_the_cells_come_in_weight_order_so_the_lora_weight_changes_once():
    w = [x["weight"] for x in _jobs() if x["kind"] in P.REFS]
    assert w == sorted(w, reverse=True)


def test_the_sheet_has_a_row_per_cell_plus_the_reference_row():
    rows = S.rows_of(_jobs(), "tent")
    assert len(rows) == 1 + 2 * len(P.CFGS) * len(P.WEIGHTS) and rows[0][0].startswith("master")


def test_the_pod_script_passes_the_pod_lint():
    from explainer_engine.cloud import runpod
    assert runpod.lint_pod_script((PODS / "xworld_v2_p2s.sh").read_text(encoding="utf-8")) == []


def test_close_and_medium_prompts_drop_out_of_frame_parts_and_state_the_background_and_who_is_in_an_over_the_shoulder_shot():
    from explainer_engine.training.pods.xworld_v2_scenes import frame_desc, frame_extras
    scs = {s["name"]: s for s in load(PODS / "stories" / "v2")}
    rome, tent = scs["rome"], scs["tent"]
    close = next(s for s in rome["shots"] if s["size"] == "close")
    assert "sandals" in close["desc"] and "sandals" not in frame_desc(close) and "balconies" in frame_extras(rome, close)
    assert "sandals" in rome["shots"][0]["desc"] and frame_desc(rome["shots"][0]) == rome["shots"][0]["desc"]  # wide keeps it
    ots = tent["shots"][1]
    extra = frame_extras(tent, ots)
    assert "Exactly two people" in extra and "bicorne" in extra and "riding boots" not in extra
    j = [x for x in P.jobs([tent, rome]) if x["kind"] in P.REFS]
    assert all("sandals" not in x["prompt"] and "riding boots" not in x["prompt"] for x in j if x["shot"] in {"s1", "s2"})
