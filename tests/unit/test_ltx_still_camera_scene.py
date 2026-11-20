"""The still-camera LTX scene of 2026-11-20 (paid item 1, "how alive can a picture look"): the committed plan the GO names."""
import json
from pathlib import Path

from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
from explainer_engine.training.pods.ltx import scene_run as S

SCENE = Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/ltx/scenes/ltx_still_camera_2026-11-20.json"
MOVES = ("pan", "zoom in", "push in", "dolly", "tilt", "tracking", "handheld", "orbit")


def _scene():
    return json.loads(SCENE.read_text(encoding="utf-8"))


def test_three_cuts_of_five_seconds_each_from_its_own_picture():
    sc = _scene()
    assert sc["schema"] == "ltx_scene_test/2" and len(sc["shots"]) == 3
    assert {s["seconds"] for s in sc["shots"]} == {5.0}
    assert len({s["picture"] for s in sc["shots"]}) == 3 and len({s["seed"] for s in sc["shots"]}) == 3


def test_the_camera_is_locked_and_nobody_speaks():
    for s in _scene()["shots"]:
        p = s["motion_prompt"]
        assert p.startswith("Static locked-off camera"), s["shot_id"]
        assert p.rstrip().split("Sound:")[0].rstrip().endswith("Nobody speaks."), s["shot_id"]
        assert s["line"] is None
        # the only camera words allowed are the ones that deny a move
        assert not any(w in p.lower().replace("never moves, zooms, pans or tilts", "") for w in MOVES), s["shot_id"]


def test_snow_is_only_on_the_one_shot_that_carries_it_as_a_test_element():
    snowy = [s["shot_id"] for s in _scene()["shots"] if "snow" in s["motion_prompt"].lower()]
    assert snowy == ["still_s07sh006"]
    assert "added_test_element" in _scene()["shots"][0]


def test_the_worst_case_stays_under_the_items_one_dollar_and_the_ledger_reserves_under_80_percent():
    sc, launch = _scene(), L.load_launch()
    assert sc["budget"]["total_usd"] == 1.0 and S.budget_problems(sc, launch) == []
    assert launch["caps"]["run_usd"] <= 0.8 * sc["ledger"]["caps"]["modal_ltx"] + 1e-9
