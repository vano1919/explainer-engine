"""D-48 story engine: the story layer (ST, scripting/story_lint.py), motion accents (production/accents.py) and the
motion rules (MO, edit/motion_lint.py), voice casting from traits (VC, audio/casting.py) and Shorts styles (SS, PV-34)."""
import copy
import json

import numpy as np
from PIL import Image

from explainer_engine.audio import casting
from explainer_engine.edit import motion_lint as M
from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import accents as ACC
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V
from explainer_engine.scripting import story_lint as SL

from test_production_script import ROOT, mini, words_for

EP1 = ROOT / "examples" / "stone_age" / "ep1_v1" / "production_script.json"


def storied() -> dict:
    d = mini()
    d["drama"] = {"premise": "Two geniuses wake up in a cold valley twelve thousand years ago.",
                  "question": "Could they survive the first night?", "promise": "how the first fire was really made",
                  "needs": ["curiosity", "stakes", "humour"],
                  "arcs": {"einstein": {"want": "to be warm", "flaw": "thinks in theories, not hands"}},
                  "loops": [{"id": "L01", "question": "will they survive the night?"}],
                  "setups": [{"id": "P01", "what": "the reading glasses", "plant": "S01", "payoff": "S02"}],
                  "ending": {"kind": "callback"}}
    d["segments"][0]["drama"] = {"function": "hook", "turn": "start", "shift": "calm -> cold", "need": "curiosity",
                                 "opens": ["L01"], "claim_share": "reasoned"}
    d["segments"][1]["drama"] = {"function": "resolution", "turn": "but", "stakes": "freezing", "shift": "cold -> warm",
                                 "need": "stakes", "closes": ["L01"], "claim_share": "reasoned"}
    d["segments"][1]["lines"][0]["text"] = "Then Einstein takes off his glasses."
    d["segments"][1]["drama"]["need"] = "humour"
    d["segments"][0]["drama"]["need"] = "stakes"
    d["segments"][1]["lines"][1]["claims"] = []
    return d


def _st(doc, rule=None, sev=None):
    return [f for f in SL.lint(doc) if (rule is None or f["rule"] == rule) and (sev is None or f["severity"] == sev)]


# --- schema ------------------------------------------------------------------------------------------------------------

def test_schema_takes_the_new_optional_layers_and_old_scripts_stay_valid():
    d = storied()
    d["segments"][0]["shots"][0]["accents"] = [{"kind": "punch", "at": "night?"}, {"kind": "pop_text", "text": "NIGHT"}]
    d["cast"]["einstein"]["voice"] = {"style": "bright, quick, amused tenor",
                                      "traits": {"gender": "male", "age": "middle_aged", "temperament": ["playful"]}}
    assert not S.schema_errors(d)
    assert not S.schema_errors(S.load(EP1))
    bad = copy.deepcopy(d)
    bad["segments"][0]["shots"][0]["accents"] = [{"kind": "spin"}]
    assert S.schema_errors(bad)


# --- story layer (ST) --------------------------------------------------------------------------------------------------

def test_story_lint_passes_a_complete_story_and_asks_for_one_when_missing():
    assert not _st(storied(), sev="FAIL"), _st(storied())
    assert _st(mini(), "ST-00")
    assert [f for f in V.check_script(mini()) if f["rule"] == "PV-33 ST-00" and f["severity"] == "REVIEW"]


def test_story_lint_structure_failures():
    d = storied()
    d["segments"][0]["drama"]["closes"] = ["L01"]
    d["segments"][0]["drama"]["opens"] = []
    assert _st(d, "ST-05", "FAIL")  # closed before it was opened
    d = storied()
    d["drama"]["setups"][0].update(plant="S02", payoff="S01")
    assert _st(d, "ST-06", "FAIL")  # paid off before it is planted
    d = storied()
    d["segments"][1]["drama"]["claim_share"] = "fact"
    assert _st(d, "ST-09", "FAIL")  # a fact segment without a claim id


def test_story_lint_craft_reviews():
    d = storied()
    d["segments"][1]["lines"][0]["text"] = "And then Einstein takes off his glasses."
    assert _st(d, "ST-02", "REVIEW")
    d = storied()
    d["segments"][1]["drama"]["turn"] = "start"
    assert _st(d, "ST-02")
    d = storied()
    d["drama"]["needs"] = ["curiosity"]
    assert _st(d, "ST-08")
    d = storied()
    d["drama"]["loops"].append({"id": "L02", "question": "who keeps the fire?"})
    d["segments"][0]["drama"]["opens"].append("L02")
    assert any("never paid off" in f["detail"] for f in _st(d, "ST-05"))


# --- motion accents ------------------------------------------------------------------------------------------------------

def test_accents_resolve_on_their_words_and_entries_start_the_shot():
    starts = {"night?": 1.4}
    acc = ACC.resolve([{"kind": "punch", "at": "night?"}, {"kind": "whip_in", "at": "night?"}, {"kind": "shake", "at": "nope"}],
                      1.0, 4.0, starts.get, 30)
    assert [a["start"] for a in acc] == [1.4, 1.0, 1.0]
    assert acc[0]["start_frame"] == 42


def test_camera_punch_holds_shake_decays_wobble_breathes():
    punch = ACC.resolve([{"kind": "punch", "strength": 1.0}], 0, 3, lambda p: None, 30)
    z = [ACC.camera(punch, f, 30, 0)[0] for f in (0, 2, 4, 30, 80)]
    assert z[0] == 1.0 and z[1] < z[2] <= z[3] == z[4] and abs(z[4] - 1.18) < 1e-6
    shake = ACC.resolve([{"kind": "shake"}], 0, 3, lambda p: None, 30)
    assert any(abs(ACC.camera(shake, f, 30, 0)[1]) > 0.002 for f in range(1, 6))
    assert ACC.camera(shake, 20, 30, 0) == (1.0, 0.0, 0.0)  # over after 0.45 s
    wob = ACC.resolve([{"kind": "wobble"}], 0, 5, lambda p: None, 30)
    assert ACC.camera(wob, 0, 30, 0)[0] == 1.0 < ACC.camera(wob, 36, 30, 0)[0]
    box = ACC.apply_camera((0, 0, 100, 50), 100, 50, 1.2, 0.5, 0.5)
    assert box[0] >= 0 and box[1] >= 0 and box[2] <= 100 and box[3] <= 50  # never leaves the picture


def test_drawn_accents_change_the_frame_and_render_the_same_twice():
    frame = Image.new("RGB", (320, 180), (40, 60, 80))
    prev = Image.new("RGB", (320, 180), (200, 30, 30))
    acc = ACC.resolve([{"kind": "flash_in"}, {"kind": "pop_text", "text": "TWELVE"}], 0, 2, lambda p: None, 30)
    f0 = ACC.draw(frame.copy(), acc, 0, 30, 0, 60, prev, BUB.FONT)
    assert np.asarray(f0).mean() > np.asarray(frame).mean() + 40  # the flash
    f8 = ACC.draw(frame.copy(), acc, 8, 30, 0, 60, prev, BUB.FONT)
    assert np.abs(np.asarray(f8, dtype=int) - np.asarray(frame, dtype=int)).sum() > 0  # the words are drawn
    assert np.array_equal(np.asarray(f8), np.asarray(ACC.draw(frame.copy(), acc, 8, 30, 0, 60, prev, BUB.FONT)))
    whip = ACC.resolve([{"kind": "whip_in"}], 0, 2, lambda p: None, 30)
    f2 = np.asarray(ACC.draw(frame.copy(), whip, 2, 30, 0, 60, prev, BUB.FONT))
    assert f2[:, :40, 0].mean() > 120  # the previous shot is still leaving on the left
    assert np.array_equal(np.asarray(ACC.draw(frame.copy(), whip, 20, 30, 0, 60, prev, BUB.FONT)), np.asarray(frame))


def test_timing_carries_accents_to_the_timed_shots():
    d = mini()
    d["segments"][1]["shots"][1]["accents"] = [{"kind": "slam_text", "at": "A small flame", "text": "FIRE"}]
    timed = T.time_script(d, words_for(d))
    shot = next(s for s in timed["shots"] if s["picture"] == "camp")
    assert shot["accents"][0]["kind"] == "slam_text"
    assert shot["start"] < shot["accents"][0]["start"] < shot["end"]
    assert all(s["accents"] == [] for s in timed["shots"] if s["picture"] != "camp")


# --- motion rules (MO) ---------------------------------------------------------------------------------------------------

def _timed(shots, duration):
    return {"duration": duration, "shots": shots, "visuals": [], "cards": []}


def _shot(i, start, end, pic, accents=()):
    return {"id": f"SH{i:03d}", "segment": "S01", "picture": pic, "start": start, "end": end,
            "start_frame": int(start * 30), "end_frame": int(end * 30), "accents": list(accents), "bubbles": []}


def test_motion_rules_flag_a_slideshow_and_clear_with_accents():
    plain = _timed([_shot(i, i * 4.0, i * 4.0 + 4.0, f"p{i}") for i in range(8)], 32.0)
    rules = {f["rule"] for f in M.check(plain)}
    assert {"MO-03", "MO-06"} <= rules
    alive = copy.deepcopy(plain)
    for s in alive["shots"]:
        s["accents"] = [{"kind": "punch", "start": s["start"] + 2.0}]
    assert not {"MO-03", "MO-06"} & {f["rule"] for f in M.check(alive)}
    gap = _timed([_shot(1, 0.0, 12.0, "p1")], 12.0)
    assert any(f["rule"] == "MO-01" for f in M.check(gap))


def test_motion_rules_keep_whips_for_story_turns():
    t = _timed([_shot(1, 0, 4, "a"), _shot(2, 4, 8, "b", [{"kind": "whip_in", "start": 4.0}])], 8.0)
    assert any(f["rule"] == "MO-04" for f in M.check(t))  # inside a segment
    t["shots"][1]["segment"] = "S02"
    assert not any(f["rule"] == "MO-04" for f in M.check(t))


def test_episode_one_measures_as_a_slideshow():
    """The creator's note (slow, not animated) in numbers: almost no shot moves besides the camera."""
    doc = S.load(EP1)
    timed = T.time_script(doc, V.estimated_words(doc))
    m = M.measure(timed)
    assert m["alive_share"] < 0.1 and m["kinds"].get("reframe", 0) > 50
    assert any(f["rule"] == "MO-06" for f in M.check(timed))


# --- voice casting (VC) -------------------------------------------------------------------------------------------------

def hero(**traits):
    t = {"gender": "male", "age": "old", "temperament": ["gruff", "witty"], "energy": "low", "origin": "Boston, USA",
         "role": "mentor"}
    t.update(traits)
    return {"names": ["franklin"], "card": "Benjamin Franklin, balding, round spectacles",
            "voice": {"style": "warm, dry, unhurried older storyteller", "traits": t}}


def test_casting_query_comes_from_traits_only():
    q = casting.query(hero())
    assert q["gender"] == "male" and q["age"] == "old" and q["accent"] == "american"
    assert q["descriptives"][:2] == ["rough", "sassy"] and "voice_category" not in q  # gruff, witty (+ warm from the style)
    assert "franklin" not in json.dumps(q).lower()
    assert all("accent" not in r for r in casting.relaxed(q))


def test_casting_refuses_imitation_and_undocumented_real_people():
    h = hero()
    h["voice"]["style"] = "sounds like Franklin in the film"
    assert casting.problems(h)
    h = hero(real_person=True)
    assert any("documented" in p for p in casting.problems(h))
    h = hero(real_person=True, documented=["C-12: raised in Boston; famed for dry wit (Isaacson 2003)"])
    assert not casting.problems(h)
    d = mini()
    d["cast"]["franklin"]["voice"] = {"style": "in the voice of a famous actor"}
    d["segments"][1]["lines"][1]["speaker"] = "franklin"
    assert [f for f in V.check_script(d) if f["rule"] == "PV-10" and f["severity"] == "FAIL"]


def test_casting_ranks_returned_voices_and_never_reuses_one():
    voices = [{"voice_id": "a", "name": "Old Boston", "labels": {"gender": "male", "age": "old", "accent": "american",
                                                                  "descriptive": "rough"}},
              {"voice_id": "b", "name": "Young Girl", "labels": {"gender": "female", "age": "young"}},
              {"voice_id": "c", "name": "Star", "labels": {"gender": "male", "age": "old", "category": "famous"}}]
    r = casting.rank(voices, hero())
    assert [x["voice_id"] for x in r] == ["a", "b"]
    assert [x["voice_id"] for x in casting.rank(voices, hero(), taken={"a"})] == ["b"]
    desc = casting.design_description(hero())
    assert "elderly male voice" in desc and "american" in desc and "Franklin" not in desc


def test_casting_flags_two_speakers_the_ear_cannot_tell_apart():
    cast = {"a": hero(), "b": hero()}
    assert casting.distinct(cast)
    cast["b"]["voice"]["traits"]["age"] = "young"
    assert not casting.distinct(cast)


# --- Shorts styles (SS, PV-34) ------------------------------------------------------------------------------------------

def test_a_set_of_shorts_needs_several_styles():
    d = mini()
    base = {"hook": "Could they survive the night?", "shots": [{"at": "Could", "picture": "valley", "crop_x": 0.5}]}
    d["shorts"] = []
    for i in range(6):
        d["shorts"].append(dict(copy.deepcopy(base), id=f"SH{i + 1:02d}", hook=f"Could they survive night {i + 1}?",
                                style="fact_bomb",
                                lines=[{"text": f"Could they survive night {i + 1}?"}, {"text": f"Line {i} of its own."},
                                       {"text": "Full story on the channel."}]))
    found = [f for f in V.check_script(d) if f["rule"] == "PV-34"]
    assert any("styles in" in f["detail"] for f in found) and any("same style" in f["detail"] for f in found)
    styles = ["fact_bomb", "pov_you", "dialogue_clash", "loop", "countdown_hud", "would_you"]
    for sh, st in zip(d["shorts"], styles):
        sh["style"] = st
    assert not [f for f in V.check_script(d) if f["rule"] == "PV-34" and "styles in" in f["detail"]]


# --- stage guard ---------------------------------------------------------------------------------------------------------

from explainer_engine.scripting import stage_guard as G  # noqa: E402


def test_stage_guard_freezes_the_words_after_the_writer():
    before = storied()
    after = copy.deepcopy(before)
    after["segments"][0]["lines"][0]["tags"] = ["curious"]
    after["segments"][1]["lines"][2]["text"] = "Oh, " + after["segments"][1]["lines"][2]["text"]
    assert G.violations("performer", before, after) == []
    after["segments"][1]["lines"][1]["text"] = "Oh. A magnifying lens."
    assert G.violations("performer", before, after) and not G.words_frozen(before, after)
    shots = copy.deepcopy(before)
    shots["segments"][0]["shots"][0]["accents"] = [{"kind": "punch"}]
    assert G.violations("editor", before, shots) == []
    assert G.violations("performer", before, shots)  # a performer may not touch the shots


def test_stage_guard_ownership_of_story_cast_and_shorts():
    before = storied()
    after = copy.deepcopy(before)
    after["drama"]["question"] = "Could they last a week?"
    assert G.violations("architect", before, after) == [] and G.violations("writer", before, after)
    v = copy.deepcopy(before)
    v["cast"]["einstein"]["voice"] = {"style": "bright, quick, amused tenor"}
    assert G.violations("caster", before, v) == []
    v["cast"]["einstein"]["card"] = "someone else"
    assert G.violations("caster", before, v)
    s = copy.deepcopy(before)
    s["segments"] = s["segments"][::-1]
    assert G.violations("writer", before, s)
