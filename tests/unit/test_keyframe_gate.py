"""KG-01..KG-17 (docs/KEYFRAME_GATE.md) on the real cases of 2026-10-24: the ambiguous mammoth, glasses in an eye, the style
LoRA loaded into the edit model."""

import pytest

from explainer_engine.qa import keyframe_gate as kg

ICE = {"id": "ice_01", "kind": "keyframe", "lead_room": {"side": "right", "for": "he lunges at the lynx"},
       "people": [{"tag": "the cave man with a torch", "where": "left", "height": "third", "on": "the snow", "actor": True},
                  {"tag": "the cave woman in green fur", "where": "center", "on": "a log"}],
       "relations": ["a living woolly mammoth stands behind the boulder"]}


def answers(qs, override=None):
    """The answers a correct picture gets, with some changed."""
    out = [str(q["expect"]) for q in qs]
    for code, value in (override or {}).items():
        out = [value if q["code"] == code else a for q, a in zip(qs, out)]
    return out


def test_questions_come_from_the_card():
    qs = kg.questions(ICE)
    codes = [q["code"] for q in qs]
    assert qs[0] == {"code": "KG-01", "q": "How many people and animals are in the picture? Answer with a number.", "expect": 2,
                     "hard": True}
    assert codes.count("KG-02") == 2 and codes.count("KG-05") == 2
    assert any("living woolly mammoth stands behind the boulder" in q["q"] for q in qs)
    assert {"KG-07", "KG-08", "KG-09", "KG-11", "KG-12"} <= set(codes)
    assert "at least a third of" in next(q["q"] for q in qs if q["code"] == "KG-04")
    assert "empty space on the right of the cave man" in next(q["q"] for q in qs if q["code"] == "KG-11")
    assert "KG-13" not in codes     # a master has no first image to compare with
    assert next(q["q"] for q in qs if q["code"] == "KG-03") == "Is the cave man with a torch on the left side of the picture?"
    assert "KG-13" in {q["code"] for q in kg.questions(dict(ICE, kind="nextpose"))}
    with pytest.raises(ValueError):
        kg.questions(dict(ICE, kind="video"))


def test_the_ambiguous_mammoth_and_glasses_in_the_eye_fail():
    qs = kg.questions(ICE)
    assert kg.verdict(qs, answers(qs))["status"] == "PASS"
    mammoth = kg.verdict(qs, answers(qs, {"KG-06": "no", "KG-09": "yes"}))
    assert mammoth["status"] == "FAIL" and {f["code"] for f in mammoth["fails"]} == {"KG-06", "KG-09"}
    assert kg.verdict(qs, answers(qs, {"KG-08": "yes"}))["status"] == "FAIL"
    assert kg.verdict(qs, answers(qs, {"KG-01": "3"}))["status"] == "FAIL"
    # soft checks (size, text) and unreadable answers ask for a look, never fail alone
    assert kg.verdict(qs, answers(qs, {"KG-04": "no"}))["status"] == "REVIEW"
    assert kg.verdict(qs, answers(qs, {"KG-10": "yes"}))["status"] == "REVIEW"
    assert kg.verdict(qs, [None] + answers(qs)[1:])["status"] == "REVIEW"


def test_the_vision_model_round_trip():
    qs = kg.questions(ICE)
    prompt = kg.vlm_prompt(qs)
    assert prompt.count("\n") == len(qs) and "1. How many people and animals" in prompt
    reply = "1. 2\n2. Yes, on the left.\n3) yes\n4: No\n" + "\n".join(f"{i}. maybe" for i in range(5, len(qs) + 1))
    got = kg.parse_answers(reply, len(qs))
    assert got[:4] == ["2", "yes", "yes", "no"] and got[4] is None


def test_redraw_at_most_three_times_then_fix_the_prompt():
    assert kg.next_step([]) == "redraw"
    assert kg.next_step([{"status": "FAIL"}]) == "redraw"
    assert kg.next_step([{"status": "FAIL"}, {"status": "PASS"}]) == "use"
    assert kg.next_step([{"status": "FAIL"}] * kg.MAX_TRIES) == "fix_prompt"


def test_blame_looks_at_the_base_model_before_the_lora():
    assert kg.blame("KG-09", with_lora=True, without_lora=True, other_seed=True) == "prompt"
    assert kg.blame("KG-09", with_lora=True, without_lora=False, other_seed=True) == "lora"
    assert kg.blame("KG-09", with_lora=True, without_lora=False, other_seed=False) == "chance"
    assert kg.blame("KG-09", with_lora=False, without_lora=True, other_seed=True) == "none"


def test_the_log_says_what_to_fix(tmp_path):
    log = tmp_path / "qa_log.jsonl"
    qs = kg.questions(ICE)
    bad = kg.verdict(qs, answers(qs, {"KG-09": "yes"}))
    for i in range(kg.RETRAIN_AT):
        kg.append_log(log, kg.record(ICE, model="Qwen/Qwen-Image-2.1", loras={"xworld_v1": 1.0}, seed=i,
                                     prompt="p", result=bad, image=f"{i}.png", cause={"KG-09": "lora"}))
    kg.append_log(log, kg.record(ICE, model="Qwen/Qwen-Image-2.1", loras={"xworld_v1": 1.0}, seed=99, prompt="p",
                                 result=kg.verdict(qs, answers(qs, {"KG-06": "no"})), image="x.png",
                                 cause={"KG-06": "prompt"}))
    kg.append_log(log, kg.record(ICE, model="Qwen/Qwen-Image-2.1", loras={}, seed=7, prompt="p",
                                 result=kg.verdict(qs, answers(qs)), image="ok.png"))
    s = kg.summary(kg.read_log(log))
    assert s["pictures"] == kg.RETRAIN_AT + 2 and s["passed"] == 1
    todo = {a["code"]: a["do"] for a in s["actions"]}
    assert todo["KG-06"].startswith("prompt rule")
    assert "retraining candidate for xworld_v1" in todo["KG-09"]
    few = kg.summary(kg.read_log(log)[:3])
    assert {a["code"]: a["do"] for a in few["actions"]}["KG-09"].startswith("collect: 3/")


def test_only_the_2_1_stack():
    """D-80: Qwen-Image-2.1 draws and edits; 2512 and Edit-2511 are retired; a LoRA loads only into its own base."""
    kg.check_stack("Qwen/Qwen-Image-2.1", {"xworld_v1_000000500": 1.0})
    kg.check_stack("Qwen/Qwen-Image-2.1", {})
    for old in ("Qwen/Qwen-Image-2512", "Qwen/Qwen-Image-Edit-2511"):
        with pytest.raises(ValueError, match="retired"):
            kg.check_stack(old, {})
    with pytest.raises(ValueError, match="trained on Qwen/Qwen-Image-2.1"):
        kg.check_stack("black-forest-labs/FLUX.2", {"xworld_v1": 1.0})
    with pytest.raises(ValueError, match="unknown LoRA"):
        kg.check_stack("Qwen/Qwen-Image-2.1", {"someone_else": 1.0})


def test_old_loras_are_banned():
    """D-80 (ვანო 2026-10-26 01:15): every LoRA trained before 2026-10-26 is banned everywhere."""
    for name in ("wldnk_style_v1.0", "wldnk_scene_v1_000000750", "wldnk_qi21_v1_000000500", "wldnk_wan22_v1"):
        with pytest.raises(ValueError, match="banned"):
            kg.check_stack("Qwen/Qwen-Image-2.1", {name: 1.0})


def test_film_test_v2_cases():
    """The 1-minute film test (2026-10-24): one figure drawn twice that the total count missed, rulers drawn from numeric prompts, and a
    close-up failed for cut-off arms."""
    qs = kg.questions(ICE)
    twice = [q for q in qs if q["code"] == "KG-01" and "How many times does the cave woman in green fur" in q["q"]]
    assert len(twice) == 1 and twice[0]["expect"] == 1
    got = answers(qs)
    got[qs.index(twice[0])] = "2"
    assert kg.verdict(qs, got)["status"] == "FAIL"       # the total was right (the VLM said 5 of 6), the per-figure count is not
    assert kg.verdict(qs, answers(qs, {"KG-17": "yes"}))["status"] == "FAIL"
    close = dict(ICE, size="CU")
    assert "KG-12" not in {q["code"] for q in kg.questions(close)}
    assert "KG-12" in {q["code"] for q in kg.questions(dict(ICE, size="WS"))}


def test_twins_marks_things_and_the_world_are_asked_one_by_one():
    """KG-18..KG-22 (2026-10-24): the pink-haired girl drawn twice, the old man without his glasses, three buses, a road in
    the ice age; every question goes to the 72B on its own, and Claude fills the same rows before the creator sees it."""
    card = dict(ICE, people=[dict(ICE["people"][0], marks=["round glasses"]), ICE["people"][1]],
                things=[{"plural": "buses", "count": 1}], absent=["a road, a car or a building"])
    qs = kg.questions(card)
    by = {q["code"]: q for q in qs}
    assert by["KG-18"]["expect"] == "no" and "look-alikes" in by["KG-18"]["q"]
    assert by["KG-19"]["q"] == "Does the cave man with a torch have round glasses?"
    assert any(q["q"] == "How many buses are in the picture? Answer with a number." and q["expect"] == 1 for q in qs)
    assert by["KG-21"]["q"] == "Is there a road, a car or a building anywhere in the picture?"
    assert kg.verdict(qs, answers(qs, {"KG-18": "yes"}))["status"] == "FAIL"
    assert kg.verdict(qs, answers(qs, {"KG-21": "yes"}))["status"] == "FAIL"
    assert kg.single_prompt(by["KG-18"]).endswith("Answer with yes or no only.")
    assert "Answer with a number only." in kg.single_prompt(qs[0])
    assert "72B" in kg.VLM_MODEL
    assert "KG-18" not in {q["code"] for q in kg.questions(dict(ICE, people=ICE["people"][:1]))}   # one figure, no twin
    table = kg.review_table(card, "master_S01.jpg")
    assert table.count("\n| KG-") == len(qs) + 1 and "eras sheet" in table
