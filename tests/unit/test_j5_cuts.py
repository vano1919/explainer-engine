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


def test_punch_in_is_a_declared_jump_with_a_bounded_scale_and_spacing_and_a_reuse_names_an_earlier_shot():
    a = {"name": "a", "subject": "H1", "view": "left34", "size": "medium", "start": 0.0}
    p1 = {"name": "p1", "subject": "H1", "view": "left34", "size": "medium", "cut": "punch_in", "scale": 1.10, "start": 3.0}
    p2 = dict(p1, name="p2", start=7.0)
    assert C.lint([a, p1, p2]) == []
    assert "outside" in C.lint([a, dict(p1, scale=1.4)])[0]
    assert "closer than" in C.lint([a, p1, dict(p2, start=4.0)])[0]
    assert "same subject" in C.lint([a, dict(p1, view="front")])[0]
    undeclared = dict(p1)
    del undeclared["cut"]
    assert "jump" in C.lint([a, undeclared])[0]                                      # without the declaration it is the flagged jump
    plan = [dict(s) for s in C.SEQUENCE]
    plan.append(dict(plan[1], name="S5_reuse_h1", reuse_of="S2_ots_h2_to_h1", motivation="the commander speaks again"))
    assert C.plan_check(plan) == []
    plan[-1]["reuse_of"] = "nope"
    assert any("EARLIER" in p for p in C.plan_check(plan))


def test_a_declared_axial_cut_in_needs_a_wide_to_close_step():
    wide = {"name": "w", "subject": "H1", "view": "left34", "size": "wide"}
    close = {"name": "c", "subject": "H1", "view": "left34", "size": "close", "cut": "axial"}
    assert C.lint([wide, close]) == []
    assert "jump" in C.lint([wide, dict(close, size="medium")])[0]              # medium from the same side is still the flagged jump
    assert "jump" in C.lint([wide, {k: v for k, v in close.items() if k != "cut"}])[0]
