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


def test_the_creators_word_band_40_to_150_and_the_crowd_review_above_90():
    """The creator, 2026-11-06 12:27 UTC (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWQ83nahs7XqJbJiNjko9vuk): 40 to 150 words, as the scene
    needs. Over 150 FAILs; a crowd or mass scene (V1, S3) over 90 words is a REVIEW (clone soldiers, asset pod 2026-11-06)."""
    import json
    from pathlib import Path
    SP = sp
    reg = json.loads((Path(SP.__file__).resolve().parents[1] / "visual" / "archetypes_ic.json").read_text(encoding="utf-8"))
    assert set(SP.CROWD_SUB_CATEGORIES) <= {s["id"] for s in reg["sub_categories"]}
    assert (SP.MAX_WORDS, SP.CROWD_REVIEW_WORDS, SP.MOMENT_WORDS) == (150, 90, 40)

    def prompt(n):
        return f"{SP.TRIGGER}, " + " ".join(["soldier"] * (n - len(SP.TRIGGER.split())))
    assert not SP.check(prompt(120))
    assert not SP.check(prompt(120), sub_category="V2")
    crowd = SP.check(prompt(120), sub_category="V1")
    assert [f["severity"] for f in crowd] == ["REVIEW"] and "clone" in crowd[0]["detail"]
    assert not SP.check(prompt(90), sub_category="S3")
    assert [f["severity"] for f in SP.check(prompt(151))] == ["FAIL"]
    assert "150 words" in dict(SP.ABSOLUTES)["A4"]


def test_style_clash_rejects_oil_painting_and_other_media():
    """Regression test (D-130 Item 7): ensure STYLE_CLASH in style_prompt.py catches 'oil painting' on Ink Chronicle prompts."""
    assert "oil painting" in sp.STYLE_CLASH.pattern
    res = sp.check(f"{T}, an oil painting of a soldier standing by a tent")
    assert any(f["rule"] == "LT-66" and f["severity"] == "FAIL" and "oil painting" in f["detail"].lower() for f in res)
