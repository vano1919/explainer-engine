"""Owner-approved Python item 4: the episode's own declared visual-mix band (advisory) and locked shots in the lane planner."""
import copy
import json
from pathlib import Path

from explainer_engine.episode import router
from explainer_engine.qa.gates import PASS, REVIEW

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json"


def _script():
    return json.loads(SCRIPT.read_text(encoding="utf-8"))


def test_a_script_with_a_declared_band_is_judged_against_it_as_a_review():
    rows = router.mix_gate_rows(_script())
    assert [r["gate"] for r in rows] == ["route_mix_60_30_10"] and "declared band" in rows[0]["detail"]
    assert rows[0]["status"] in (PASS, REVIEW)      # never FAIL: advisory
    assert rows[0]["measured"]["locked_shots"] > 0


def test_a_video_heavy_truce_mix_is_a_review_not_a_fail_and_names_eligible_conversions():
    sc = _script()
    for s in sc["shots"]:
        s["route"] = "video"
    r = router.mix_gate_rows(sc)[0]
    assert r["status"] == REVIEW and "outside band" in r["detail"]
    assert all(sid not in {s["shot_id"] for s in sc["shots"] if s.get("locked_shot")} for sid in r["measured"]["eligible_conversions"])


def test_a_script_without_a_declared_band_keeps_bp109_and_its_fail():
    sc = _script()
    sc.pop("visual_mix_band")
    r = router.mix_gate_rows(sc)[0]
    assert r["gate"] == "route_mix_60_30_10" and "BP-109" in r["detail"] and "declared band" not in r["detail"]



def test_the_lane_planner_keeps_a_locked_shot_in_its_lane():
    import _lane_fixtures as LF
    from explainer_engine.visual import lanes

    doc = LF.battle_documentary()
    base, _ = lanes.plan(copy.deepcopy(doc))
    moved = [s for s, b in zip(doc["shots"], base["shots"]) if s.get("lane") != b.get("lane")]
    assert moved, "the fixture must contain a shot the planner moves, or the test proves nothing"
    locked = copy.deepcopy(doc)
    for s in locked["shots"]:
        if s["id"] == moved[0]["id"]:
            s["locked_shot"] = True
    after, _ = lanes.plan(locked)
    row = next(s for s in after["shots"] if s["id"] == moved[0]["id"])
    assert row["lane"] == moved[0]["lane"]
