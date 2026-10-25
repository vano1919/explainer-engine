"""Film shot cards (film_shots/1, KP-15..KP-30 in docs/SHOT_PROMPTS.md): the composed prompts and the card rules."""

import copy
import json
from pathlib import Path

from explainer_engine.qa import style_prompt
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


def test_keyframe_tells_the_moment_at_its_peak_with_a_reaction_and_no_layout():
    p = prompts(doc())["S01-02.first"]
    assert p["kind"] == "keyframe" and p["prompt"].startswith("wldnk style, a snowy plain")  # LT-65: trigger, place
    assert "the old man, thin-limbed and bulging-eyed, throws both hands up" in p["prompt"]  # body words, the peak
    assert "the nurse turns her head toward him" in p["prompt"]  # someone's reaction
    assert "cold blue morning light" in p["prompt"]
    assert not style_prompt.check(p["prompt"])  # no tail, no camera/size/position, at most 40 words
    assert "full-body" not in p["prompt"] and "on the left" not in p["prompt"]  # the layout is the gate card's
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


def test_composition_goes_to_the_gate_card_and_the_cut_prompt_not_the_keyframe_words():
    # LT-65: a keyframe is the trigger, a short scene and the style tail; supports, heights, relations and free space are
    # the gate card's layout (for boxes or a blockout); a cut (Edit, scene LoRA) still writes them
    d = doc()
    ps = prompts(d)
    k = ps["S01-02.first"]["prompt"]
    assert "frame height" not in k and "Empty space" not in k
    card = {c["id"]: c for c in F.gate_cards(d)}["S01-02.first"]
    assert any(p["on"] == "sitting on the bottom step of the bus door" and p["height"] == "third" for p in card["people"])
    assert "the yellow city bus stands behind the four of them" in card["relations"] and card["lead_room"]["side"] == "above"
    assert "filling most of the frame height" in ps["S01-04.first"]["prompt"]  # S01-04 is a cut
    assert "frame height" not in ps["S01-02.last"]["prompt"]  # a next pose never re-frames (KP-07)
    b = shot(d, "S01-04")["blocking"][0]
    b.pop("height")
    b["height_pct"] = 55
    k = prompts(d)["S01-04.first"]["prompt"]
    assert "filling about half of the frame height" in k and "%" not in k and "55" not in k  # numbers get drawn (KP-32)


def test_keyframes_and_sheets_keep_the_moment_shape_and_name_each_figure_once():
    d = json.loads((ROOT / "examples" / "napoleon_vs_genghis" / "film_shots.json").read_text(encoding="utf-8"))
    style = [p for p in F.compose(d) + F.sheet_prompts(d) if p.get("lora") == "style"]
    assert style and not [f for p in style for f in style_prompt.check(p["prompt"])]  # LT-65
    for p in style:  # LY-09: a repeated tag drew a twin
        assert all(p["prompt"].count(c["tag"]) <= 1 for c in d["cast"].values())
    s = next(s for s in d["shots"] if s["source"] == "keyframe" and len(s.get("blocking", [])) >= 4)
    card = {c["id"]: c for c in F.gate_cards(d)}[f"{s['id']}.first"]
    assert len(card["people"]) == len(s["blocking"])  # everyone is placed and counted by the card, not the words
    d["style"]["body"] = "a camera close-up"
    assert "LT-65" in {f["rule"] for f in F.style_check(d)}  # a layout word in the moment is caught


def test_each_prompt_names_its_lora_and_the_gate_gets_a_card():
    ps = prompts(doc())
    assert ps["S01-02.first"]["lora"] == "style"
    assert {ps[i]["lora"] for i in ("S01-02.last", "S01-03.first", "S01-06.first")} == {"scene"}  # never style in Edit
    cards = {c["id"]: c for c in F.gate_cards(doc())}
    assert cards["S01-06.first"]["kind"] == "nextpose" and cards["S01-06.first"]["master"] == "S01-02"  # KG-13 vs it
    c = cards["S01-02.first"]
    assert [p["actor"] for p in c["people"]] == [True, False, False, False]
    assert c["people"][2] == {"tag": "the pink-haired girl in the yellow hoodie", "where": "center_back",
                              "height": "third", "on": "sitting on the bottom step of the bus door", "actor": False}
    assert c["lead_room"]["side"] == "above" and c["relations"]


def _episode(d, n=12, seconds=4.0):
    """The example's cards stretched to a minute of narrated holds and full scenes, under the script engine v1."""
    base = copy.deepcopy(d["shots"])
    d["engine"] = F.ENGINE
    d["claims"] = {"C1": {"text": "The army crossed the Neman on 24 June 1812.", "source": "https://en.wikipedia.org/wiki/French_invasion_of_Russia"}}
    d["channel"] = {"worlds_on": ["the Stone Age"], "worlds_coming": ["the Ice Age"]}
    shots = []
    for i in range(n):
        s = copy.deepcopy(base[i % len(base)])
        s["id"] = f"X{i:02d}"
        s["seconds"] = seconds
        s["tier"] = "full"
        s["frame"]["camera"] = "push_in" if i == 0 else "static"
        s["frame"].pop("camera_end", None)
        if s.get("narration"):
            s["claims"] = ["C1"]
        if s["source"] != "keyframe":
            s["master"] = f"X{(i // len(base)) * len(base):02d}"
        shots.append(s)
    d["shots"] = shots
    return d


def test_episode_rules_apply_only_under_the_engine():
    d = doc()
    d["shots"][0].pop("tier", None)
    assert not rules(d) & {"ZI-02", "ZI-03", "KP-35", "KP-37"}
    d = _episode(doc())
    assert not rules(d) & {"KP-35", "KP-36", "KP-37", "KP-38", "KP-40", "ZI-02", "ZI-03"}
    d["shots"][0].pop("tier")
    assert "ZI-03" in rules(d, "FAIL")


def test_a_number_needs_a_claim_and_the_claim_must_exist():
    d = _episode(doc())
    narrated = next(s for s in d["shots"] if s.get("narration"))
    narrated["narration"] = "In 1812, half a million men marched east."
    narrated.pop("claims")
    assert "ZI-02" in rules(d, "FAIL")
    narrated["claims"] = ["C1"]
    assert "ZI-02" not in rules(d, "FAIL")
    narrated["claims"] = ["C9"]
    assert "ZI-02" in rules(d, "FAIL")


def test_long_clips_holds_and_lines_on_holds():
    d = _episode(doc())
    talk = next(s for s in d["shots"] if s.get("dialogue"))
    talk["tier"] = "light"
    assert "KP-37" in rules(d, "FAIL")
    talk["tier"] = "full"
    talk["seconds"] = F.CLIP_MAX_S + 2
    assert "KP-36" in rules(d, "REVIEW")
    d = _episode(doc())
    for s in d["shots"][:4]:
        if not s.get("dialogue"):
            s["tier"] = "hold"
    assert "KP-37" in rules(d, "REVIEW")


def test_rhythm_and_camera_moves():
    d = _episode(doc(), n=6, seconds=12.0)  # 6 shots in 72 s = 5 a minute, median 12 s
    msgs = [f["detail"] for f in F.check(d) if f["rule"] == "KP-35"]
    assert len(msgs) == 2
    d = _episode(doc())
    for s in d["shots"]:
        s["frame"]["camera"] = "push_in"
    assert "KP-38" in rules(d, "REVIEW")


def test_outro_points_to_the_channel_worlds():
    d = _episode(doc())
    last = d["shots"][-1]
    last.pop("dialogue", None)
    last["mode"] = "narrated"
    last["tier"] = "light"
    last["narration"] = "Subscribe so you never miss a world."
    assert "KP-40" in rules(d, "FAIL")
    last["narration"] = ("On the channel: the Stone Age is waiting. Next comes the Ice Age. Subscribe if you don't want "
                         "to miss it.")
    assert "KP-40" not in rules(d, "FAIL")
    last["narration"] = "Thanks for watching."
    assert "KP-40" in rules(d, "FAIL")


def test_compose_carries_tier_model_and_ltx_frames():
    assert F.frames(4.0) == 97 and F.frames(10.0) == 241 and F.frames(3.0) == 73
    d = _episode(doc())
    d["shots"][0]["tier"] = "hold"
    video = [p for p in F.compose(d) if p["kind"] == "video"]
    assert video[0]["model"] == "camera" and video[1]["model"] == F.MODEL["full"]
    assert all((p["frames"] - 1) % 8 == 0 for p in video)


def test_script_export_has_the_clock_lines_and_claims():
    d = _episode(doc())
    text = F.script(d)
    assert text.startswith("# ") and "`0:00.0`" in text and "## Claims" in text and "C1" in text


def test_a_cut_draws_its_last_frame_from_its_own_first_frame():
    d = doc()
    cut = next(s for s in d["shots"] if s["source"] == "cut")
    cut["last_frame"] = True
    last = prompts(d)[f"{cut['id']}.last"]
    assert last["master"] == cut["id"]


def test_sheet_prompts_for_named_heroes_only():
    d = doc()
    d["cast"]["crowd"] = {"tag": "the crowd of commuters in grey coats on the platform"}
    sheets = F.sheet_prompts(d)
    assert {s["id"] for s in sheets} == {f"sheet.{c}" for c, v in d["cast"].items() if v.get("name")}
    assert all(s["prompt"].startswith(d["style"]["trigger"]) and s["lora"] == "style" for s in sheets)
    assert not [f for f in F.lint.check(sheets, names=[c["name"] for c in d["cast"].values() if c.get("name")])
                if f["severity"] == "FAIL"]


def test_the_napoleon_episode_is_clean_under_the_engine():
    ep = json.loads((ROOT / "examples" / "napoleon_vs_genghis" / "film_shots.json").read_text(encoding="utf-8"))
    assert ep["engine"] == F.ENGINE
    assert not F.check(ep)
    assert sum(s["seconds"] for s in ep["shots"]) == 900


def test_a_relation_with_a_or_an_before_a_cast_noun_fails():
    d = doc()
    s = shot(d, "S01-02")
    s["frame"]["relations"] = ["a yellow city bus stands behind the old man"]
    assert "KP-33" not in rules(d, "FAIL")  # the bus is no cast member
    d["cast"]["mammoth"] = {"tag": "the woolly mammoth with a broken left tusk"}
    s["blocking"].append({"who": "mammoth", "where": "right_back", "facing": "left", "on": "standing on the hill",
                          "height": "half"})
    s["frame"]["relations"] = ["a living woolly mammoth stands on the hill behind the yellow city bus"]
    assert ("KP-33", "S01-02") in found(d, "FAIL")
    s["frame"]["relations"] = ["the woolly mammoth stands on the hill behind the yellow city bus"]
    assert ("KP-33", "S01-02") not in found(d, "FAIL")


def test_a_partly_visible_figure_is_written_and_counted_without_support():
    d = doc()
    d["cast"]["mammoth"] = {"tag": "the woolly mammoth with a broken left tusk"}
    s = shot(d, "S01-02")
    s["blocking"].append({"who": "mammoth", "where": "right", "facing": "left", "partial": "the trunk"})
    assert "KP-31" not in rules(d, "FAIL")
    k = prompts(d)["S01-02.first"]["prompt"]
    assert "the woolly mammoth with a broken left tusk" not in k and "right" not in k  # the card carries it
    card = {c["id"]: c for c in F.gate_cards(d)}["S01-02.first"]
    assert card["people"][-1]["partial"] == "the trunk"


def test_the_cold_open_shows_pieces_of_later_shots():
    d = _episode(doc(), n=16)
    assert ("KP-41", "opening") in found(d, "REVIEW")
    d["shots"][1]["teaser_of"], d["shots"][2]["teaser_of"] = "X10", "X11"
    assert "KP-41" not in rules(d)
    p = prompts(d)
    assert p["X01.video"]["kind"] == "reuse" and p["X01.video"]["of"] == "X10.video" and "X01.first" not in p
    assert "X01.first" not in {g["id"] for g in F.gate_cards(d)}
    d["shots"][3]["teaser_of"] = "X00"  # an earlier shot is no teaser
    assert ("KP-41", "X03") in found(d, "FAIL")


def test_a_long_stay_in_one_place_needs_a_cutaway():
    d = _episode(doc(), n=24)
    for s in d["shots"]:
        s["frame"]["place"] = "road"
    assert "KP-42" in rules(d, "REVIEW")
    d["shots"][12]["frame"]["place"] = "road_close"
    assert "KP-42" not in rules(d)


def test_a_run_of_spoken_lines_is_broken_and_acting_is_checked():
    d = _episode(doc(), n=12)
    talk = next(i for i, s in enumerate(d["shots"]) if s.get("dialogue"))
    for k in range(1, F.TALK_RUN_MAX + 1):
        s = copy.deepcopy(d["shots"][talk])
        s["id"] = f"T{k}"
        d["shots"].insert(talk + k, s)
    assert "KP-43" in rules(d, "REVIEW")
    acted = [p for p in F.compose(d) if p["kind"] == "video" and p.get("qa")]
    assert acted and all(p["qa"] == ["acting"] and p["acting"]["lips"] and p["fallback"]["kind"] for p in acted)
    d["shots"][talk]["tier"] = "light"
    assert "acting" not in json.dumps(prompts(d)[f"{d['shots'][talk]['id']}.video"])


def test_the_shot_list_puts_every_prompt_under_its_shot():
    d = _episode(doc(), n=16)
    d["shots"][1]["teaser_of"] = "X10"
    text = F.shotlist(d)
    assert "Teaser: the clip of X10" in text and "First frame" in text and "Video (" in text
    assert text.count("\n### ") == len(d["shots"])
    assert "Only these 1 " not in json.dumps(F.compose(d))


def test_a_crowded_keyframe_stays_in_the_word_limit_and_keeps_its_light():
    d = doc()
    s = shot(d, "S01-02")
    for i, w in enumerate(["left_front", "right_front"]):
        d["cast"][f"x{i}"] = {"tag": f"the very tall stranger number {i} in a long patched green coat with a wide hat"}
        s["blocking"].append({"who": f"x{i}", "where": w, "facing": "camera", "on": "standing in the snow", "height": "half"})
    d["cast"]["mammoth"] = {"tag": "the woolly mammoth with a broken left tusk and frost on its long brown fur"}
    s["blocking"].append({"who": "mammoth", "where": "center_back", "facing": "left", "on": "standing on the hill",
                          "height": "third"})
    k = F.keyframe_prompt(d, s)
    assert len(k.split()) <= F.MOMENT_WORDS_MAX and not style_prompt.check(k)
    assert s["frame"]["light"] in k  # the light carries the look
    assert all(k.count(c["tag"]) <= 1 for c in d["cast"].values())  # LY-09


LOOK = {"phrase": "warm amber firelight with deep teal shadows", "lights": {"night": "deep indigo night with amber lamplit glow"}}


def test_every_style_prompt_ends_with_the_episode_look_and_still_fits_lt65(tmp_path):
    d = doc()
    (tmp_path / "look.json").write_text(json.dumps({"schema": "episode_look/1", **LOOK}), encoding="utf-8")
    d["style"]["look"] = "look.json"
    shot(d, "S01-02")["frame"]["look"] = "night"
    (tmp_path / "cards.json").write_text(json.dumps(d), encoding="utf-8")
    d = F.load(tmp_path / "cards.json")  # AC-16: the look file is read next to the cards
    assert not F.schema_errors(d) and not F.style_check(d)
    style = [p for p in F.compose(d) + F.sheet_prompts(d) if p.get("lora") == "style"]
    assert style and all(not style_prompt.check(p["prompt"]) for p in style)  # 40 words with the phrase (AC-17)
    assert all(p["prompt"].endswith(LOOK["phrase"]) for p in style if p["id"] != "S01-02.first")
    assert prompts(d)["S01-02.first"]["prompt"].endswith(LOOK["lights"]["night"])  # the scene's light variant
    shot(d, "S01-02")["frame"]["look"] = "dawn"
    assert "AC-17" in {f["rule"] for f in F.style_check(d)}  # a variant the look does not have
    assert "AC-17" in rules(d, "FAIL")  # and the full check reports it instead of crashing


def test_a_look_with_style_words_or_a_negative_of_its_own_fails_lt66():
    d = doc()
    d["style"]["look"] = {"phrase": "cinematic watercolour glow"}
    assert "AC-17" in {f["rule"] for f in F.style_check(d) if f["severity"] == "FAIL"}
    d = doc()
    d["style"]["neg_keyframe"] = "text, extra fingers"
    assert "LT-66" in {f["rule"] for f in F.style_check(d) if f["severity"] == "FAIL"}  # A3
    assert prompts(doc())["S01-02.first"]["neg"] == style_prompt.NEGATIVE
    shot(d := doc(), "S01-02")["action"]["peak"] = "takes a photo of the bus"
    assert "LT-66" in {f["rule"] for f in F.style_check(d)}  # A8: another medium named in the moment


def test_every_drawn_frame_gets_a_gate_card_with_exact_counts_and_absent_things():
    from explainer_engine.qa import keyframe_gate as G

    d = doc()
    d["absent"] = ["a city", "a paved road"]  # the world's (KG-21)
    s = shot(d, "S01-02")
    s["frame"]["things"] = {"yellow city bus": 1, "spear": {"count": 2, "plural": "spears"}}
    s["frame"]["absent"] = ["a building", "a city"]
    assert not F.schema_errors(d)
    cards = {c["id"]: c for c in F.gate_cards(d)}
    c = cards["S01-02.first"]
    assert c["things"][0] == {"name": "yellow city bus", "plural": "yellow city buses", "count": 1}
    assert c["absent"] == ["a city", "a paved road", "a building"]  # once each
    qs = G.questions(c)
    assert {"code": "KG-01", "q": "How many yellow city buses are in the picture? Answer with a number.", "expect": 1,
            "hard": True} in qs  # one bus is one bus (the 2.1 style LoRA drew a second one and a city)
    assert sum(q["code"] == "KG-21" for q in qs) == 3
    last = cards["S01-02.last"]  # the guided last frame is checked too, against its own first frame
    assert last["kind"] == "nextpose" and last["master"] == "S01-02" and last["things"] == c["things"]
    assert all(G.questions(x) for x in cards.values())  # every card is one the gate can ask about
    assert {k for k in cards if k.endswith(".first")} == {f"{x['id']}.first" for x in d["shots"]}
