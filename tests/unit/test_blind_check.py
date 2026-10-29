"""KG-23..KG-27: the blind description is compared with the scene contract by code (ვანო 2026-10-25 16:27 Tbilisi)."""

from explainer_engine.qa import blind_check as bc

CARD = {"id": "S01-01.first", "kind": "keyframe",
        "people": [{"tag": "a lanky bald old man", "where": "left"}, {"tag": "a wiry tired nurse", "where": "right"}],
        "things": [{"name": "yellow bus", "plural": "yellow buses", "count": 1}],
        "absent": ["city", "a paved road"], "relations": ["the bus is stuck nose-down in a snowdrift"]}
STYLE_OK = {k: "yes" for k in bc.STYLE_SPEC}


def desc(**kw):
    d = {"people": [{"look": "bald old man, round glasses", "where": "left"}, {"look": "nurse, white cap", "where": "right"}],
         "animals": [], "things": [{"name": "yellow bus", "count": 1, "where": "center_back"}],
         "text": False, "overlays": False, "floating": [], "anatomy": [], "style": dict(STYLE_OK), "uncertain": []}
    d.update(kw)
    return d


def test_a_matching_description_passes():
    assert bc.compare(CARD, desc())["status"] == "PASS"


def test_a_second_small_bus_far_away_fails_the_count():
    # the 2.1 style LoRA sample of 2026-10-25: one bus asked, a second small one in the background
    r = bc.compare(CARD, desc(things=[{"name": "yellow bus", "count": 1, "where": "left"},
                                      {"name": "small school bus", "count": 1, "where": "right_back"}]))
    assert r["status"] == "FAIL" and r["fails"][0]["got"] == 2


def test_an_absent_city_named_by_a_synonym_fails():
    r = bc.compare(CARD, desc(things=[{"name": "yellow bus", "count": 1, "where": "left"},
                                      {"name": "city skyline", "count": 1, "where": "back"}]))
    assert any(f["what"] == "absent city" for f in r["fails"])


def test_a_question_mark_is_a_review_with_a_second_look_not_a_pass():
    r = bc.compare(CARD, desc(things=[{"name": "yellow bus", "count": "?", "where": "left"}],
                              uncertain=["a shape behind the hill may be a second bus"]))
    assert r["status"] == "REVIEW" and len(r["reviews"]) == 2
    assert "far background" in bc.second_look(r["reviews"][0])


def test_style_no_fails_and_style_question_reviews():
    assert bc.compare(CARD, desc(style={**STYLE_OK, "line": "no"}))["status"] == "FAIL"
    assert bc.compare(CARD, desc(style={**STYLE_OK, "texture": "?"}))["status"] == "REVIEW"


def test_style_verdict_needs_the_score_and_the_eye():
    assert bc.style_verdict(0.68, STYLE_OK) == "PASS"
    assert bc.style_verdict(0.68, {**STYLE_OK, "texture": "no"}) == "FAIL"    # flat vector frames scored 0.56-0.69
    assert bc.style_verdict(0.44, STYLE_OK) == "FAIL"                          # step 750 of the 2.1 LoRA
    assert bc.style_verdict(0.60, {**STYLE_OK, "light": "?"}) == "REVIEW"


def test_wrong_number_of_people_floating_and_anatomy_fail():
    assert bc.compare(CARD, desc(people=[{"look": "old man", "where": "left"}]))["status"] == "FAIL"
    assert bc.compare(CARD, desc(floating=["a bird in mid-air with no wings spread"]))["status"] == "FAIL"
    assert bc.compare(CARD, desc(anatomy=["six fingers on the nurse's hand"]))["status"] == "FAIL"


def test_the_rules_hide_the_prompt_and_list_every_style_item():
    rules = bc.DESCRIBE_RULES
    assert "NOT told what the picture was meant to show" in rules
    for k in bc.STYLE_SPEC:
        assert f'"{k}"' in rules


def test_a_floating_thing_named_in_the_scene_text_is_meant_to_float_and_a_zero_count_is_a_review():
    sc = "an astronaut falls past a rocket, sparks and steam from the engine"
    r = bc.compare(CARD, desc(floating=["steam from the engine", "a floating lamp"]), scene=sc)
    assert [f["what"] for f in r["fails"]] == ["floating: a floating lamp"]
    r = bc.compare(CARD, desc(things=[]), scene=sc)
    assert r["status"] == "REVIEW" and r["reviews"][0]["got"] == 0


def test_the_cast_counts_foreground_people_and_animal_characters_not_far_scenery():
    two = {"people": [{}, {}]}
    monkey = desc(people=[{"look": "explorer", "where": "left"}], animals=[{"name": "monkey", "count": 1, "where": "right"}])
    assert bc.compare(two, monkey)["status"] == "PASS"
    far = desc(people=[{"look": "vendor", "where": "left"}, {"look": "child", "where": "right"},
                       {"look": "shopper", "where": "right_back"}])
    assert bc.compare(two, far)["status"] == "PASS"
    assert bc.compare(two, desc(people=[{"where": "left"}, {"where": "center"}, {"where": "right"}]))["status"] == "FAIL"
