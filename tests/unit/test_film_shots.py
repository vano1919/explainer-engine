"""Film shot cards (film_shots/1, KP-15..KP-30 in docs/SHOT_PROMPTS.md): the composed prompts and the card rules."""

import copy
import json
from pathlib import Path

from explainer_engine.scripting import film_shots as F
from explainer_engine.scripting.shot_prompt_lint import check_shot

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "film_shots" / "bus_in_the_ice_age.json"
STYLE = "Hand-drawn 2D cartoon animation with bold black ink outlines and bright colours. "


def doc():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def shot(d, sid):
    return next(s for s in d["shots"] if s["id"] == sid)


def found(d, severity=None):
    return {(f["rule"], f["where"]) for f in F.check(d) if severity is None or f["severity"] == severity}


def rules(d, severity=None):
    return {r for r, _ in found(d, severity)}


def prompts(d):
    return {p["id"]: p for p in F.compose(d)}


def test_the_worked_example_is_clean_and_valid():
    d = doc()
    assert F.schema_errors(d) == []
    assert F.check(d) == []


def test_keyframe_starts_with_the_trigger_and_shows_the_start_not_the_peak():
    p = prompts(doc())["S01-02.first"]
    assert p["kind"] == "keyframe" and p["prompt"].startswith("wldnk style, full-body shot at eye level")
    assert "squints at the empty white horizon" in p["prompt"]
    assert "throws both hands up" not in p["prompt"]  # the peak is the video's job
    assert "on the left, facing right" in p["prompt"] and "Only these 4 people" in p["prompt"]
    assert "cartoon" not in p["neg"].lower()  # KP-09


def test_next_pose_uses_the_training_prefix_and_the_last_frame_is_the_settle():
    ps = prompts(doc())
    last = ps["S01-02.last"]
    assert last["kind"] == "nextpose" and last["source"] == "master"
    assert last["prompt"].startswith(F.NEXTPOSE)
    assert "holds both hands high" in last["prompt"]
    assert not check_shot(last)  # KP-07: no framing word
    first = ps["S01-06.first"]
    assert first["master"] == "S01-02" and "stares over the roof of the bus" in first["prompt"]


def test_video_prompt_is_one_paragraph_with_quoted_line_one_camera_and_no_names():
    v = prompts(doc())["S01-04.video"]["prompt"]
    assert "\n" not in v and v.startswith("Hand-drawn 2D cartoon animation")
    assert '"Walter. Buses don\'t drive through glaciers."' in v  # a name said aloud is fine
    assert v.count("The camera pushes in slowly") == 1 and "Static camera" not in v
    assert "Everyone stays in frame." in v and "We hear wind" in v
    narrated = prompts(doc())["S01-01.video"]["prompt"]
    assert "Nobody speaks." in narrated and '"' not in narrated


def test_bare_or_twin_tags_fail():
    d = doc()
    d["cast"]["dee"]["tag"] = "the woman"
    assert ("KP-15", "dee") in found(d, "FAIL")
    d = doc()
    d["cast"]["kim"]["tag"] = "the nurse in the purple puffer jacket"
    assert ("KP-15", "kim") in found(d, "FAIL")


def test_a_story_name_in_an_action_fails():
    d = doc()
    shot(d, "S01-02")["reactions"][0]["does"] = "turns toward Walter"
    assert ("KP-22", "S01-02.video") in found(d, "FAIL")


def test_the_actor_must_stand_in_the_frame():
    d = doc()
    shot(d, "S01-06")["action"]["who"] = "ghost"
    assert "KP-16" in rules(d, "FAIL") and "KP-15" in rules(d, "FAIL")


def test_dialogue_rules():
    d = doc()
    s = shot(d, "S01-03")
    s["dialogue"]["text"] = " ".join(["word"] * 20)  # 5 s holds about 10 words
    assert ("KP-18", "S01-03") in found(d, "REVIEW")
    d = doc()
    shot(d, "S01-03")["dialogue"]["to"] = "bo"  # Bo is not in this shot
    assert ("KP-18", "S01-03") in found(d, "FAIL")
    d = doc()
    shot(d, "S01-01")["dialogue"] = {"who": "walter", "to": "room", "text": "Hello?"}
    assert ("KP-20", "S01-01") in found(d, "FAIL")


def test_narration_that_describes_the_picture_is_flagged():
    d = doc()
    s = shot(d, "S01-02")
    s["narration"] = "Walter squints at the empty white horizon and throws his hands up."
    assert ("KP-20", "S01-02") in found(d, "REVIEW")


def test_faces_and_wides():
    d = doc()
    shot(d, "S01-02")["frame"]["size"] = "MS"  # four people at waist height
    assert ("KP-19", "S01-02") in found(d, "REVIEW")
    d = doc()
    shot(d, "S01-06")["frame"]["size"] = "WS"
    assert ("KP-19", "S01-06") in found(d, "REVIEW")


def test_emotion_named_without_a_face():
    d = doc()
    shot(d, "S01-04")["action"]["face"] = "she is angry"
    assert ("KP-17", "S01-04") in found(d, "REVIEW")


def test_scene_grammar_establish_size_run_and_screen_sides():
    d = doc()
    shot(d, "S01-03")["blocking"][0]["where"] = "right"
    shot(d, "S01-03")["blocking"][1]["where"] = "left"
    assert ("KP-26", "S01-03") in found(d, "REVIEW")
    shot(d, "S01-03")["frame"]["crosses_line"] = True
    assert ("KP-26", "S01-03") not in found(d)
    d = doc()
    d["shots"] = [s for s in d["shots"] if s["id"] not in ("S01-01", "S01-02")]
    for s in d["shots"]:
        s["source"] = "keyframe"
        s.pop("master", None)
    assert ("KP-26", "S01") in found(d, "REVIEW")  # the scene opens close with 2+ people
    d = doc()
    base = shot(d, "S01-03")
    for i in range(4):
        extra = copy.deepcopy(base)
        extra["id"] = f"S01-03{i}"
        d["shots"].append(extra)
    assert any(r == "KP-26" and w.startswith("S01-03") for r, w in found(d, "REVIEW"))


def test_next_pose_and_cut_need_a_keyframe_master_of_the_same_scene():
    d = doc()
    shot(d, "S01-06")["master"] = "S01-03"  # a cut, not a keyframe
    assert ("KP-27", "S01-06") in found(d, "FAIL")


def test_schema_refuses_unknown_fields():
    d = doc()
    shot(d, "S01-02")["style"] = "make it pretty"
    assert F.check(d)[0]["rule"] == "KP-00"


def test_prompt_lint_new_checks_on_hand_written_prompts():
    base = {"id": "v", "kind": "video", "seconds": 6}
    music = dict(base, prompt=STYLE + "The farmer in the straw hat stamps his boot and stays in frame. Static camera. "
                                       "We hear rain and an epic orchestral music.")
    assert any(f["rule"] == "KP-21" for f in check_shot(music))
    assert not any(f["rule"] == "KP-21" for f in check_shot(dict(music, diegetic_music=True)))
    buzz = dict(base, kind="keyframe", prompt="wldnk style, masterpiece, 8k, a sign that says OPEN above the door")
    assert {"KP-23"} <= {f["rule"] for f in check_shot(buzz)}
    smooth = dict(base, prompt="2D cartoon animation, smooth natural character motion. The girl in the yellow hoodie "
                               "jumps and stays in frame. Static camera.")
    assert "KP-24" in {f["rule"] for f in check_shot(smooth)}
    mute = dict(base, prompt=STYLE + "The old man in the red scarf shouts at the bus and stays in frame. Static camera.")
    assert "KP-18" in {f["rule"] for f in check_shot(mute)}
    long = dict(base, prompt=STYLE + " ".join(["The girl in the yellow hoodie jumps and stays in frame."] * 15) +
                " Static camera.")
    assert "KP-25" in {f["rule"] for f in check_shot(long)}
    sad = dict(base, prompt=STYLE + "The girl in the yellow hoodie is sad and stays in frame. Static camera.")
    assert "KP-17" in {f["rule"] for f in check_shot(sad)}
    names = check_shot(dict(base, prompt=STYLE + "Walter jumps and stays in frame. Static camera."), names=["Walter"])
    assert any(f["rule"] == "KP-22" and f["severity"] == "FAIL" for f in names)


def test_numbers_come_from_the_sourced_rules():
    from explainer_engine.standards import sourced_rules

    assert F.SPEECH_WPS == sourced_rules.T("BP-100", "words_per_second")
    assert F.CLOSE_FACES_MAX == sourced_rules.T("BP-101", "close_faces_max")
    assert F.SAME_SIZE_RUN_MAX == sourced_rules.T("BP-103", "same_size_run_max")


def test_composition_fields_are_required_on_drawn_first_frames():
    d = doc()
    s = shot(d, "S01-02")
    del s["blocking"][1]["on"]
    del s["blocking"][0]["height"]
    del s["frame"]["lead_room"]
    got = found(d, "FAIL")
    assert {("KP-31", "S01-02"), ("KP-32", "S01-02"), ("KP-34", "S01-02")} <= got
    d = doc()
    shot(d, "S01-02")["blocking"][1]["on"] = "the snow"  # names no surface relation
    assert ("KP-31", "S01-02") in found(d, "FAIL")
    d = doc()  # a next pose keeps the master's layout: its cards carry no on / height / lead_room
    assert not any(r.startswith("KP-3") and w == "S01-06" for r, w in found(d))


def test_vague_relations_fail():
    d = doc()
    shot(d, "S01-02")["frame"]["relations"] = ["a woolly mammoth by the boulder"]
    assert ("KP-33", "S01-02") in found(d, "FAIL")
    shot(d, "S01-02")["frame"]["relations"] = ["a living woolly mammoth stands behind the boulder"]
    assert ("KP-33", "S01-02") not in found(d)


def test_composition_is_written_into_keyframe_and_cut_prompts_only():
    ps = prompts(doc())
    k = ps["S01-02.first"]["prompt"]
    assert "sitting on the bottom step of the bus door, filling about a third of the frame height" in k
    assert "The yellow city bus stands behind the four of them." in k
    assert "Empty space at the top of the frame, where his hands will go." in k
    assert "filling most of the frame height" in ps["S01-04.first"]["prompt"]
    assert "frame height" not in ps["S01-02.last"]["prompt"]  # a next pose never re-frames (KP-07)
    d = doc()
    shot(d, "S01-02")["blocking"][0]["height_pct"] = 55
    assert "filling about 55 % of the frame height" in prompts(d)["S01-02.first"]["prompt"]


def test_each_prompt_names_its_lora_and_the_gate_gets_a_card():
    ps = prompts(doc())
    assert ps["S01-02.first"]["lora"] == "style"
    assert {ps[i]["lora"] for i in ("S01-02.last", "S01-03.first", "S01-06.first")} == {"scene"}  # never style in Edit
    cards = {c["id"]: c for c in F.gate_cards(doc())}
    assert "S01-06.first" not in cards  # a next pose is checked against its master
    c = cards["S01-02.first"]
    assert [p["actor"] for p in c["people"]] == [True, False, False, False]
    assert c["people"][2] == {"tag": "the pink-haired girl in the yellow hoodie", "where": "center_back",
                              "height": "third", "on": "sitting on the bottom step of the bus door", "actor": False}
    assert c["lead_room"]["side"] == "above" and c["relations"]
