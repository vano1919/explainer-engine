from explainer_engine.training.pods import xworld_v2_data as d


def test_caption_says_what_is_drawn():
    desc = "A young Greek hoplite, a woman, wearing a cloak. She has a long face and her braids."
    assert ", a man," in d.caption("c006", "person", desc) and "He has" in d.caption("c006", "person", desc)
    assert ", a person," in d.caption("c029", "person", desc) and "She" not in d.caption("c029", "person", desc)
    assert ", a woman," in d.caption("c001", "person", desc)
    assert d.caption("p010", "place", "A river.").startswith("xworld style, an empty place")


def test_hold_out_and_fix_lists_are_separate():
    assert not set(d.HOLD_OUT) & set(d.FIXED_MALE + d.FIXED_PERSON)
    assert d.TRIGGER != d.RM_TRIGGER
