"""KP-01..KP-14 (docs/SHOT_PROMPTS.md) on the real prompts of 2026-10-23..24 and their rewrites."""

from explainer_engine.scripting.shot_prompt_lint import check, check_shot

STYLE = "Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. "
LTX_STOCK_NEG = ("blurry, motion blur, distorted proportions, cartoonish rendering, 3D CGI look, exaggerated expressions, "
                 "stylized filters, flat lighting")


def rules(shot, severity=None):
    return {f["rule"] for f in check_shot(shot) if severity is None or f["severity"] == severity}


def test_bare_role_words_fail_and_visible_traits_pass():
    # scene LoRA v1 sample 2: "the woman" painted a stranger at four of five steps
    bad = {"id": "s2", "kind": "nextpose", "prompt": "nextpose, the woman points ahead, the pink-haired girl steps back"}
    assert "KP-01" in rules(bad, "FAIL")
    assert "KP-01" in rules({"id": "s3", "kind": "nextpose", "prompt": "nextpose, one man shouts angrily"}, "FAIL")
    good = {"id": "s2b", "kind": "nextpose",
            "prompt": "nextpose: the nurse in the purple jacket points ahead; the pink-haired girl in the yellow hoodie "
                      "steps back. Same characters, same camera."}
    assert "KP-01" not in rules(good)
    assert "KP-01" not in rules({"id": "d", "kind": "video", "prompt": STYLE + "A man with a huge afro slips. Static camera."})


def test_the_farm_prompt_that_emptied_the_frame_fails():
    farm = {"id": "farm_storm", "kind": "video", "seconds": 10,
            "prompt": STYLE + "A violent storm: lightning cracks across the sky, rain pours, the farmer clutches his hat and "
                              "runs after galloping cows heading into the barn, the windmill spins fast, branches whip in "
                              "the wind. Sounds: thunder cracks, heavy rain, cows mooing, howling wind, the farmer yelling."}
    got = rules(farm)
    assert {"KP-03", "KP-04"} <= rules(farm, "FAIL")
    assert {"KP-05", "KP-11"} <= got
    fixed = {"id": "farm_val", "kind": "video", "seconds": 10,
             "prompt": STYLE + "A farmer holds his hat on his head against the wind and leans forward; the cow in front "
                               "bucks and stamps in place, the second cow in the barn door shakes its head; both cows and "
                               "the farmer stay in frame. The windmill spins and rain slants down. Static camera."}
    assert not rules(fixed, "FAIL")
    wanted_exit = {"id": "x", "kind": "video", "exit": True,
                   "prompt": STYLE + "The farmer in the straw hat runs off, waving. Static camera."}
    assert "KP-03" not in rules(wanted_exit, "FAIL")


def test_camera_length_and_moving_vehicle():
    no_cam = {"id": "ice", "kind": "video", "prompt": STYLE + "The cave people jerk back and stay in frame."}
    assert "KP-04" in rules(no_cam, "FAIL")
    two = {"id": "t", "kind": "video", "prompt": STYLE + "The girl ducks and stays in frame. The camera pans left, then a push-in."}
    assert "KP-04" in rules(two, "REVIEW")
    assert "KP-06" in rules({"id": "l", "kind": "video", "seconds": 15, "prompt": STYLE + "x jumps. Static camera."}, "FAIL")
    assert "KP-06" in rules({"id": "l", "kind": "video", "seconds": 9, "prompt": STYLE + "x jumps. Static camera."}, "REVIEW")
    train = {"id": "ww", "kind": "video",
             "prompt": STYLE + "Two outlaws on the roof of the moving train wave and stay in frame. Static camera."}
    assert "KP-05" in rules(train, "REVIEW")
    follows = dict(train, prompt=train["prompt"].replace("Static camera.", "The camera follows the train."))
    assert "KP-05" not in rules(follows)


def test_next_pose_never_reframes_and_comes_from_the_master():
    assert "KP-07" in rules({"id": "c", "kind": "nextpose", "prompt": "nextpose, close-up of the old man in the red scarf"},
                            "FAIL")
    assert "KP-07" not in rules({"id": "c", "kind": "nextpose",
                                 "prompt": "nextpose, same camera: the old man in the red scarf raises both hands"})
    assert "KP-08" in rules({"id": "c", "kind": "nextpose", "source": "previous",
                             "prompt": "nextpose: the old man in the red scarf sits down"}, "FAIL")


def test_the_ltx_stock_negative_fights_our_style():
    shot = {"id": "n", "kind": "video", "neg": LTX_STOCK_NEG, "prompt": STYLE + "The girl ducks, stays in frame. Static camera."}
    found = [f for f in check_shot(shot) if f["rule"] == "KP-09"]
    assert len(found) >= 5 and all(f["severity"] == "FAIL" for f in found)
    ours = dict(shot, neg="text, watermark, extra people, duplicated character, deformed face, extra fingers")
    assert "KP-09" not in rules(ours)


def test_small_verbs_and_one_style_sentence():
    still = {"id": "s", "kind": "video", "prompt": STYLE + "The tribe huddles by the fire and stays in frame. Static camera."}
    assert "KP-12" in rules(still, "REVIEW")
    other = {"id": "o", "kind": "video", "prompt": "Painted anime style. The girl ducks and stays in frame. Static camera."}
    assert any(f["rule"] == "KP-10" for f in check([still, other]))
    assert not any(f["rule"] == "KP-10" for f in check([still, still]))


def test_the_video_lora_validation_prompts_pass():
    disco = {"id": "disco", "kind": "video", "seconds": 10,
             "prompt": STYLE + "A man with a huge afro on roller skates loses his balance, flails both arms and tips "
                               "backward, then catches himself with one hand on the floor; the three girls on skates gasp "
                               "and cover their mouths and stay in frame. Static camera. Sounds: funky disco music, a loud "
                               "thud, gasps."}
    assert not rules(disco, "FAIL")
    assert rules({"id": "k", "kind": "pose", "prompt": "x"}) == {"KP-00"}
