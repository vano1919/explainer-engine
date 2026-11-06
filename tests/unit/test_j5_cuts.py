from explainer_engine.blender import j5_cuts as C


def test_the_current_dialogue_has_a_reason_for_every_cut():
    assert C.lint(C.SEQUENCE) == []


def test_the_same_man_only_closer_is_flagged_as_a_jump():
    problems = C.lint(C.SEQUENCE_4E)
    assert len(problems) == 1 and "S2_ots_h2_to_h1 -> S4_close_up_h1" in problems[0] and "jump" in problems[0]


def test_another_angle_of_the_same_hero_is_allowed_with_a_size_step_and_a_swap_of_sides_is_not():
    a = {"name": "a", "subject": "H1", "view": "left34", "size": "medium"}
    ok = {"name": "b", "subject": "H1", "view": "front", "size": "close"}
    assert C.lint([a, ok]) == []
    assert "full step" in C.lint([a, dict(ok, size="medium")])[0]
    assert "jump" in C.lint([a, dict(ok, view="left34")])[0]
    swapped = [dict(a, sides=("H2", "H1")), dict(ok, sides=("H1", "H2"))]
    assert any("180-degree" in p for p in C.lint(swapped))
    assert "motivation" in C.lint([a, {"name": "c", "subject": "H2", "view": "right34", "size": "medium"}])[0]


def test_the_thresholds_come_from_the_registry_and_the_plan_check_gates_generation():
    from explainer_engine.standards import sourced_rules as SR
    assert C.ANGLE_MIN_DEG == SR.T("BP-176", "angle_min_deg") == 30 and SR.rule("BP-176")["status"] == "binding"
    assert C.plan_check(C.SEQUENCE) == []
    bad = [dict(s) for s in C.SEQUENCE]
    bad[0]["size"] = "medium"
    assert any("wide two-shot" in p for p in C.plan_check(bad))
    bad = [dict(s) for s in C.SEQUENCE]
    bad[1]["eyeline"] = {"H2": "left", "H1": "left"}
    assert any("H2 looks left" in p for p in C.plan_check(bad))
    bad = [dict(s) for s in C.SEQUENCE]
    del bad[2]["eyeline"]
    assert "missing eyeline" in C.plan_check(bad)[0]
    assert C.plan_check([]) == ["the plan is empty"]
    assert any("jump" in p for p in C.plan_check(C.SEQUENCE_4E))
