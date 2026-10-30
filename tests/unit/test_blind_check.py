"""KG-23..KG-27: the blind description is compared with the scene contract by code (ვანო 2026-10-25 16:27 Tbilisi)."""

from explainer_engine.qa import blind_check as bc

CARD = {"id": "S01-01.first", "kind": "keyframe",
        "people": [{"tag": "a lanky bald old man", "where": "left"}, {"tag": "a wiry tired nurse", "where": "right"}],
        "things": [{"name": "yellow bus", "plural": "yellow buses", "count": 1}],
        "absent": ["city", "a paved road"], "relations": ["the bus is stuck nose-down in a snowdrift"]}
# D-80: the live spec is empty. These tests keep the spec MECHANICS honest (items answered yes / no / ?) with a neutral fixture that
# describes no look; the earlier spec text is gone from the code.
OLD = {k: "mechanics fixture item, not a style" for k in ("line", "figures", "colour", "texture", "detail", "light")}
STYLE_OK = {k: "yes" for k in OLD}


def cmp(card, d, scene=""):
    return bc.compare(card, d, scene, spec=OLD)


def verdict(score, style):
    return bc.style_verdict(score, style, spec=OLD)


def desc(**kw):
    d = {"people": [{"look": "bald old man, round glasses", "where": "left"}, {"look": "nurse, white cap", "where": "right"}],
         "animals": [], "things": [{"name": "yellow bus", "count": 1, "where": "center_back"}],
         "text": False, "overlays": False, "floating": [], "anatomy": [], "style": dict(STYLE_OK), "uncertain": []}
    d.update(kw)
    return d


def test_a_matching_description_passes():
    assert cmp(CARD, desc())["status"] == "PASS"


def test_a_second_small_bus_far_away_fails_the_count():
    # the 2.1 style LoRA sample of 2026-10-25: one bus asked, a second small one in the background
    r = cmp(CARD, desc(things=[{"name": "yellow bus", "count": 1, "where": "left"},
                                      {"name": "small school bus", "count": 1, "where": "right_back"}]))
    assert r["status"] == "FAIL" and r["fails"][0]["got"] == 2


def test_an_absent_city_named_by_a_synonym_fails():
    r = cmp(CARD, desc(things=[{"name": "yellow bus", "count": 1, "where": "left"},
                                      {"name": "city skyline", "count": 1, "where": "back"}]))
    assert any(f["what"] == "absent city" for f in r["fails"])


def test_a_question_mark_is_a_review_with_a_second_look_not_a_pass():
    r = cmp(CARD, desc(things=[{"name": "yellow bus", "count": "?", "where": "left"}],
                              uncertain=["a shape behind the hill may be a second bus"]))
    assert r["status"] == "REVIEW" and len(r["reviews"]) == 2
    assert "far background" in bc.second_look(r["reviews"][0])


def test_style_no_fails_and_style_question_reviews():
    assert cmp(CARD, desc(style={**STYLE_OK, "line": "no"}))["status"] == "FAIL"
    assert cmp(CARD, desc(style={**STYLE_OK, "texture": "?"}))["status"] == "REVIEW"


def test_style_verdict_needs_the_score_and_the_eye():
    assert verdict(0.68, STYLE_OK) == "PASS"
    assert verdict(0.68, {**STYLE_OK, "texture": "no"}) == "FAIL"    # flat vector frames scored 0.56-0.69
    assert verdict(0.44, STYLE_OK) == "FAIL"                          # step 750 of the 2.1 LoRA
    assert verdict(0.60, {**STYLE_OK, "light": "?"}) == "REVIEW"


def test_wrong_number_of_people_floating_and_anatomy_fail():
    assert cmp(CARD, desc(people=[{"look": "old man", "where": "left"}]))["status"] == "FAIL"
    assert cmp(CARD, desc(floating=["a bird in mid-air with no wings spread"]))["status"] == "FAIL"
    assert cmp(CARD, desc(anatomy=["six fingers on the nurse's hand"]))["status"] == "FAIL"


def test_the_rules_hide_the_prompt_and_list_every_style_item():
    rules = bc.DESCRIBE_RULES
    assert "NOT told what the picture was meant to show" in rules
    for k in OLD:                                               # a spec renders its items when one is given
        assert f'"{k}"' in bc.describe_rules(OLD)
    assert "style" not in rules.split("Answer with JSON only:")[1] and "Answer each style item" not in rules   # live spec is empty


def test_a_floating_thing_named_in_the_scene_text_is_meant_to_float_and_a_zero_count_is_a_review():
    sc = "an astronaut falls past a rocket, sparks and steam from the engine"
    r = cmp(CARD, desc(floating=["steam from the engine", "a floating lamp"]), scene=sc)
    assert [f["what"] for f in r["fails"]] == ["floating: a floating lamp"]
    r = cmp(CARD, desc(things=[]), scene=sc)
    assert r["status"] == "REVIEW" and r["reviews"][0]["got"] == 0


def test_the_cast_counts_foreground_people_and_animal_characters_not_far_scenery():
    two = {"people": [{}, {}]}
    monkey = desc(people=[{"look": "explorer", "where": "left"}], animals=[{"name": "monkey", "count": 1, "where": "right"}])
    assert cmp(two, monkey)["status"] == "PASS"
    far = desc(people=[{"look": "vendor", "where": "left"}, {"look": "child", "where": "right"},
                       {"look": "shopper", "where": "right_back"}])
    assert cmp(two, far)["status"] == "PASS"
    assert cmp(two, desc(people=[{"where": "left"}, {"where": "center"}, {"where": "right"}]))["status"] == "FAIL"


def test_style_is_suspended_by_d80():
    """The earlier spec was measured on the banned look; until the creator rates xworld_v2 the live spec is empty, a result is
    never a silent PASS, and the DINOv2 score (0.557, calibrated on the banned look) decides nothing in either direction."""
    assert bc.STYLE_SUSPENDED is True and bc.STYLE_SPEC == {}
    r = bc.compare(CARD, desc(style={}))
    assert r["status"] != "PASS" and r["status"] == "REVIEW"
    assert [x["code"] for x in r["reviews"]] == ["KG-23"] and "D-80" in r["reviews"][0]["what"]
    assert bc.style_verdict(0.9, {}) == "REVIEW" and bc.style_verdict(0.1, {}) == "REVIEW"
    assert bc.style_verdict(0.9, STYLE_OK) == "REVIEW"           # an eye answer about the retired items does not lift it either
    fail = bc.compare(CARD, desc(people=[{"look": "old man", "where": "left"}], style={}))
    assert fail["status"] == "FAIL" and any(x["code"] == "KG-23" for x in fail["reviews"])   # a hard mismatch is still a FAIL


def test_the_live_module_carries_no_text_of_the_banned_look():
    """OR-34: nothing from the old era is used. The earlier spec (measured on the banned look) is gone from the live module; only the
    suspended flag and the empty spec remain, and the mechanics' tests use a neutral fixture."""
    from pathlib import Path
    src = Path(bc.__file__).read_text(encoding="utf-8").lower()
    assert not [n for n in dir(bc) if n.endswith("_RETIRED")]
    assert "wldnk" not in src and "hand-inked" not in src and "lanky, angular" not in src
    assert bc.STYLE_SPEC == {} and bc.STYLE_SUSPENDED is True
