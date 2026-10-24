"""LT-65: the style LoRA's prompts keep the trained caption shape (the approved eras prompt passes, the film's bus prompt
of 2026-10-24 fails)."""

from explainer_engine.qa import style_prompt as sp

ERAS = ("wldnk style, An ice age tribe camp: thin cavemen arguing around a fire, a woman painting mammoths on a rock, "
        "children sliding on a frozen lake, a sabre-tooth cat watching.")
BUS = ("wldnk style, full-body shot at eye level, a snowy plain with no road, a yellow city bus stuck to its wheels in the "
       "snow, pine trees far behind, flat grey daylight. " + "The old man with round glasses and a red scarf stands. " * 40)


def test_the_tail_is_the_training_captions_tail():
    assert sp.STYLE_TAIL.startswith("lanky angular cartoon characters") and sp.STYLE_TAIL.endswith("vivid glowing accents")
    p = sp.with_tail(ERAS)
    assert p.count(sp.STYLE_TAIL) == 1 and sp.with_tail(p) == p and p.startswith("wldnk style, An ice age")
    assert sp.check(p) == []
    assert sp.with_tail("a goat in a market").startswith("wldnk style, a goat")


def test_the_bus_prompt_fails():
    found = sp.check(BUS)
    details = " ".join(f["detail"] for f in found)
    assert "style tail is missing" in details and "words" in details and "flat grey daylight" in details
    assert [f["severity"] for f in sp.check(ERAS)] == ["FAIL"]          # the eras prompt lacks only the tail
