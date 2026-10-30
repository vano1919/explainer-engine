"""LT-65: style-LoRA prompts keep the approved shape (the eras prompt and the v5 sample prompt pass; the film's bus prompt of
2026-10-24 fails; the caption tail and layout words are flagged)."""

from explainer_engine.qa import style_prompt as sp
from explainer_engine.training import lora_rules

T = lora_rules.trigger()  # D-80: the one home (N-09)

ERAS = (f"{T}, An ice age tribe camp: thin cavemen arguing around a fire, a woman painting mammoths on a rock, "
        "children sliding on a frozen lake, a sabre-tooth cat watching.")
SAMPLE = (f"{T}, close-up of a bald old man with round glasses and a red scarf, terrified face, snowy background")
BUS = (f"{T}, full-body shot at eye level, a snowy plain with no road, a yellow city bus stuck to its wheels in the "
       "snow, pine trees far behind, flat grey daylight. " + "The old man with round glasses and a red scarf stands. " * 40)


def test_the_approved_prompts_pass():
    assert sp.check(ERAS) == []
    assert [f["severity"] for f in sp.check(SAMPLE)] == ["REVIEW"]          # "close-up": the size goes to the layout
    assert sp.shaped("a goat in a market").startswith(f"{T}, a goat")
    assert sp.shaped(ERAS) == ERAS.rstrip(".")


def test_the_bus_prompt_fails_and_the_tail_is_flagged():
    found = sp.check(BUS)
    details = " ".join(f["detail"] for f in found)
    assert any(f["severity"] == "FAIL" for f in found)
    assert "words" in details and "flat grey daylight" in details and "layout" in details
    tailed = ERAS.rstrip(".") + ", " + sp.STYLE_TAIL
    assert "tail" in " ".join(f["detail"] for f in sp.check(tailed))
    assert sp.with_tail(tailed) == ERAS.rstrip(".") and sp.STYLE_TAIL not in sp.with_tail(ERAS)


def test_the_cli_reads_the_composers_dict(tmp_path):
    import json
    f = tmp_path / "prompts.json"
    f.write_text(json.dumps({"sheets": [{"id": "sheet.a", "kind": "keyframe", "prompt": ERAS}],
                             "shots": [{"id": "S1.first", "kind": "keyframe", "prompt": BUS}], "gate": [{"id": "x"}]}))
    assert sp.main([str(f)]) == 1
    f.write_text(json.dumps({"sheets": [], "shots": [{"id": "S1.first", "kind": "keyframe", "prompt": ERAS}]}))
    assert sp.main([str(f)]) == 0
