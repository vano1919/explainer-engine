from explainer_engine.blender import j5_minute as M, j5_montage as L
from explainer_engine.standards import sourced_rules as SR


def _plan():
    return [dict(s) for s in M.PLAN]


def test_the_minute_plan_is_60_seconds_has_no_fail_and_only_reports_the_lane_shares():
    assert abs(L.runtime(M.PLAN) - 60.0) < 0.01
    problems = M.check()
    assert not [p for p in problems if p.startswith("FAIL")]
    assert all("(BP-109)" in p for p in problems), problems          # the cards-only route cannot reach 60/30/10 yet; reported, not hidden
    assert len({s["subject"] for s in M.PLAN if s["subject"].startswith("H")}) == 3 and len({s["scene"] for s in M.PLAN}) == 5


def test_the_thresholds_come_from_the_registry_as_hypotheses():
    for rid in ("BP-179", "BP-180", "BP-181"):
        assert SR.rule(rid)["status"] == "hypothesis" and SR.severity(rid) == "REVIEW"
    assert L.DISSOLVE == (0.5, 2.0) and L.MOVE == (1.04, 1.25)


def test_each_rule_catches_its_fault():
    p = _plan()
    p[5]["cut"], p[5]["transition_s"] = "dissolve", 1.0                    # a dissolve inside the tent
    assert any("dissolve inside one scene" in x for x in L.lint_montage(p))
    p = _plan(); p[4]["transition_s"] = 3.0
    assert any("dissolve of 3 s" in x for x in L.lint_montage(p))
    p = _plan(); p[1]["motion"] = {}
    assert any("no motion" in x for x in L.lint_montage(p))
    p = _plan(); p[10]["motion"] = {"kind": "parallax", "layers": 2}
    assert any("depth layers" in x for x in L.lint_montage(p))
    p = _plan(); p[4]["size"], p[4]["establishing"] = "close", False
    assert any("establishing" in x for x in L.lint_montage(p))
    p = _plan(); p[6]["luma"] = 40
    assert any("brightness" in x for x in L.lint_montage(p))
    p = _plan(); p[1]["seconds"] = 7.0
    assert any("held 7 s" in x for x in L.lint_montage(p))
    p = _plan(); p[11]["cut"] = "match"
    assert any("match_tag" in x for x in L.lint_montage(p))
    p = _plan(); p[12]["reuse_of"] = "nope"
    assert any("reuse_of" in x for x in L.lint_montage(p))
    p = _plan(); p[3]["direction"] = "left"
    assert any("screen direction" in x for x in L.lint_montage(p)) is False   # M3 has a motivation; the flip is only flagged without one
    p[3]["motivation"] = ""
    assert any("screen direction" in x for x in L.lint_montage(p))
    p = _plan(); p[8]["seconds"] = 5.0; p[7]["subject"] = "H1"; p[7]["view"] = "left34"; p[7]["size"] = "medium"  # the same man at the same angle again
    assert any("jump" in x for x in L.lint_montage(p))
