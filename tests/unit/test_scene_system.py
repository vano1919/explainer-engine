"""The 2026-10-19 scene rewrite (D-58): scenes and dialogue (SC rules, PV-48), story cadence (ST-00/ST-12/ST-13), the
inverted cue logic on a production_script/3 (VB-08 / VB-10 / VB-11), hold variance (MO-07), and the audio bugs fixed for
every schema: cue pitch variants, loop/one-shot manifest guards, beat de-stacking, AL-02 counting cues."""
import copy

import numpy as np

from explainer_engine.audio import cues as CUES
from explainer_engine.audio import layers as L
from explainer_engine.edit import motion_lint
from explainer_engine.production import assemble as ASM
from explainer_engine.production import beats as BEATS
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import validate as V
from explainer_engine.scripting import scene_lint as SC
from explainer_engine.scripting import speech as SP
from explainer_engine.scripting import story_lint as ST
from explainer_engine.standards import sourced_rules as SR


def HOUSE(bp: str) -> str:  # noqa: N802  the severity the registry holds for a registered number (a JSON switch)
    return SR.rule(bp)["severity"]


from test_production_script import mini


def scene_doc() -> dict:
    """A /3 segment written the way the dialogue-scenes skill asks: a scene header, addressed lines, a turn."""
    return {
        "schema": "production_script/3",
        "cast": {"capone": {}, "enzo": {}},
        "segments": [{
            "id": "S03",
            "lines": [
                {"text": "The club went quiet when the ledger came out."},
                {"text": "You counted it twice?", "speaker": "capone", "to": "enzo", "intent": "press"},
                {"text": "Three times. It's short.", "speaker": "enzo", "to": "capone", "intent": "reveal"},
                {"text": "Short.", "speaker": "capone", "to": "room", "intent": "banter"},
                {"text": "Someone's skimming the north side.", "speaker": "enzo", "to": "capone", "intent": "reveal",
                 "visual_beats": [{"at": "skimming", "kind": "expression", "why": "the word lands on Capone",
                                   "expression": "angry", "who": "capone"}]},
            ],
            "scene": {"place": "the back room of the club, night", "present": ["capone", "enzo"], "pov": "capone",
                      "want": "find who is skimming before the bosses hear",
                      "obstacle_want": "admit nothing until Capone names a number", "value": "trust",
                      "open_charge": "+", "close_charge": "-",
                      "turn": "the ledger comes up short and the room changes sides", "exit": "interrupted",
                      "surface_topic": "the ledger", "real_subject": "who Capone can still trust"},
        }],
    }


def sc_rules(doc, sev=None):
    return {f["rule"] for f in SC.lint(doc) if sev is None or f["severity"] == sev}


def test_a_well_built_scene_passes_and_earlier_schemas_get_no_sc_findings():
    d = scene_doc()
    assert SC.lint(d) == [], SC.lint(d)
    d2 = copy.deepcopy(d)
    d2["schema"] = "production_script/2"
    assert SC.lint(d2) == []  # /1 and /2 keep their contract: SC binds only /3


def test_scene_header_addressing_and_turn_are_required():
    d = scene_doc()
    del d["segments"][0]["scene"]
    assert "SC-01" in sc_rules(d, "FAIL")  # dialogue with no scene
    d = scene_doc()
    d["segments"][0]["scene"]["close_charge"] = "+"
    assert "SC-02" in sc_rules(d, "FAIL")  # the charge never turns: a nonevent
    d = scene_doc()
    d["segments"][0]["scene"]["obstacle_want"] = d["segments"][0]["scene"]["want"]
    assert "SC-03" in sc_rules(d, "FAIL")  # no collision, no scene
    d = scene_doc()
    del d["segments"][0]["lines"][1]["to"]
    assert "SC-04" in sc_rules(d, "FAIL")  # a line said to nobody (the narrator is never an addressee)
    d = scene_doc()
    d["segments"][0]["lines"][1]["to"] = "narrator"
    assert "SC-04" in sc_rules(d, "FAIL")


def test_a_scene_needs_a_real_exchange():
    d = scene_doc()
    d["segments"][0]["lines"].insert(3, {"text": "Outside, the snow kept falling."})  # narrator breaks the run
    assert "SC-05" in sc_rules(d, "FAIL")


def test_press_release_narration_is_banned_on_scene_scripts():
    d = scene_doc()
    d["segments"][0]["lines"][0]["text"] = "Rockstar's page says it comes out on November 19."
    assert "SC-07" in sc_rules(d, "FAIL")
    d["segments"][0]["lines"][0]["text"] = "The game is set to release this winter."
    assert "SC-07" in sc_rules(d, "FAIL")
    d["segments"][0]["lines"][0]["text"] = "He had until November 19, and the city knew it."  # a date as stakes is fine
    assert "SC-07" not in sc_rules(d)


def test_disclaimers_live_in_one_honesty_beat():
    d = scene_doc()
    seg = d["segments"][0]
    d["segments"] = []
    for i in range(3):
        s = copy.deepcopy(seg)
        s["id"] = f"S0{i + 3}"
        s["lines"][0]["text"] = "We invented this part of the night."
        d["segments"].append(s)
    assert "SC-08" in sc_rules(d, "FAIL")  # three segments of "invented, remember"


def test_turn_taking_lengths_and_subtext():
    d = scene_doc()
    d["segments"][0]["lines"][3]["text"] = " ".join(["word"] * 40) + "."
    assert "SC-09" in sc_rules(d, "FAIL")  # a 40-word turn
    d = scene_doc()
    d["segments"][0]["lines"][3]["text"] = "They say he counts every crate himself, twice over, before the trucks move an inch off the lot."
    assert "SC-09" in sc_rules(d, "REVIEW")  # over the 5-15 default, under the speech band
    d = scene_doc()
    d["segments"][0]["lines"][3]["text"] = "I need to know who Capone can still trust."
    d["segments"][0]["lines"][3]["speaker"] = "enzo"
    assert "SC-10" in sc_rules(d, "FAIL")  # the real subject spoken out loud


def test_scene_openers_and_closers_are_flagged():
    d = scene_doc()
    d["segments"][0]["lines"][1]["text"] = "Hello, Enzo."
    assert "SC-06" in sc_rules(d, "REVIEW")


def test_validate_wires_scene_lint_as_pv47():
    d = mini()
    d["schema"] = "production_script/3"
    d["segments"][1]["lines"][1]["speaker"] = "einstein"
    found = V.check_script(C.compile_doc(d))
    assert any(f["rule"] == "PV-48 SC-01" for f in found)  # dialogue on /3 with no scene header


# --- story cadence (ST-00 / ST-12 / ST-13) ---------------------------------------------------------------------------------

def story_doc(funcs, words=120) -> dict:
    segs = [{"id": f"S{i:02d}", "lines": [{"text": ("word " * words).strip() + "."}],
             "drama": {"function": fn, "turn": "start" if i == 0 else "therefore", "stakes": "x", "shift": "a -> b"}}
            for i, (fn) in enumerate(funcs)]
    return {"schema": "production_script/3", "cast": {},
            "drama": {"question": "Will it work?", "premise": "p", "promise": "pr", "arcs": {}, "loops": [],
                      "needs": ["curiosity", "stakes", "wonder"], "ending": "twist", "setups": []},
            "segments": segs}


def st_rules(doc):
    return {f["rule"] for f in ST.lint(doc)}


def test_missing_drama_blocks_a_scene_script():
    sev = {f["rule"]: f["severity"] for f in ST.lint({"schema": "production_script/3", "segments": []})}
    assert sev["ST-00"] == "FAIL"  # Syndicate Wars shipped without a drama block on one REVIEW
    sev = {f["rule"]: f["severity"] for f in ST.lint({"schema": "production_script/2", "segments": []})}
    assert sev["ST-00"] == "REVIEW"


def test_midpoint_placement_and_turn_cadence():
    funcs = ["cold_open", "midpoint"] + ["escalation"] * 5 + ["resolution"]
    assert "ST-12" in st_rules(story_doc(funcs))  # the pivot sits at ~19 % of the words
    funcs = ["cold_open"] + ["escalation"] * 3 + ["midpoint"] + ["escalation"] * 2 + ["resolution"]
    assert "ST-12" not in st_rules(story_doc(funcs))  # mid-story: fine
    funcs = ["cold_open"] + ["escalation"] * 4 + ["resolution"]
    assert "ST-13" in st_rules(story_doc(funcs, words=160))  # ~256 s of therefore-joins without one turn
    funcs = ["cold_open", "escalation", "reversal", "escalation", "crisis", "resolution"]
    assert "ST-13" not in st_rules(story_doc(funcs, words=160))


# --- the inverted cue logic on /3 (VB-08 / VB-10 / VB-11) ------------------------------------------------------------------

def test_beats_lint_inverts_vb08_on_scene_schema():
    from test_visual_beats import beats_doc
    d = beats_doc()
    d["schema"] = "production_script/3"
    found = [f for f in BEATS.lint(d) if f["rule"].endswith("VB-08") and f["severity"] == "FAIL"]
    assert found  # the /2 beats carry cues with no story event: on /3 that is the FAIL
    assert all("story event" in f["detail"] for f in found)
    for seg in d["segments"]:
        for ln in seg["lines"]:
            for b in ln.get("visual_beats", []):
                if (b.get("cue") or {}).get("sound", "none") != "none":
                    b["cue"]["event"] = "impact"
    assert not [f for f in BEATS.lint(d) if f["rule"].endswith("VB-08") and f["severity"] == "FAIL"]
    d["segments"][0]["lines"][0]["visual_beats"][0].pop("cue")  # silence is the default: no cue is no finding
    assert not [f for f in BEATS.lint(d) if f["rule"].endswith("VB-08") and f["severity"] == "FAIL"]


def _cues(seq, line=1):
    return [{"sound": s, "start": t, "end": t + 0.1, "segment": "S01", "line": line, "kind": "text",
             "start_frame": int(t * 30)} for s, t in seq]


def _timed_cues(cues, duration=120.0):
    return {"duration": duration, "audio": {"cues": cues, "sfx": [], "music": [], "beds": []}}


def _cue_find(timed, schema="production_script/3"):
    out: list = []
    BEATS._cue_findings(timed, {"schema": schema}, [], out)
    return out


def test_a_repeated_cue_sound_is_a_tic():
    found = _cue_find(_timed_cues(_cues([("tick", 1.0), ("tick", 5.0)])))
    assert any(f["rule"].endswith("VB-10") and f["severity"] == "REVIEW" for f in found)
    found = _cue_find(_timed_cues(_cues([("tick", 1.0), ("tick", 10.0), ("tick", 20.0)])))
    assert any(f["rule"].endswith("VB-10") and f["severity"] == HOUSE("BP-80") for f in found)  # 3 inside 30 s
    found = _cue_find(_timed_cues(_cues([("tick", 1.0), ("blip", 5.0), ("tick", 40.0)])))
    assert not any(f["rule"].endswith("VB-10") for f in found)
    found = _cue_find(_timed_cues(_cues([("tick", 1.0), ("tick", 5.0)])), schema="production_script/2")
    assert not any(f["rule"].endswith("VB-10") for f in found)  # /2 keeps its contract


def test_cue_density_is_capped_on_scene_scripts():
    names = ["tick", "blip", "tap", "pop"]
    many = _cues([(names[i % 4], 1.0 + i * 5.5) for i in range(11)])  # 11 a minute
    found = _cue_find(_timed_cues(many, duration=60.0))
    assert any(f["rule"].endswith("VB-11") and f["severity"] == "REVIEW" and "a minute" in f["detail"] for f in found)
    many = _cues([(names[i % 4], 0.3 + i * 1.0) for i in range(15)])  # 15 a minute, and bursts
    found = _cue_find(_timed_cues(many, duration=60.0))
    assert any(f["rule"].endswith("VB-11") and f["severity"] == HOUSE("BP-81") for f in found)
    two = _cues([("thud", 1.0), ("chime", 3.0)])  # two emphasis cues on one line
    found = _cue_find(_timed_cues(two))
    assert any(f["rule"].endswith("VB-11") and "emphasis" in f["detail"] for f in found)
    quiet = _cues([("tick", 1.0), ("blip", 30.0), ("tap", 59.0)])
    assert not any(f["rule"].endswith("VB-11") for f in _cue_find(_timed_cues(quiet, duration=60.0)))


def test_beats_landing_on_one_collapsed_instant_are_destacked():
    doc = {"schema": "production_script/3", "episode": {"id": "x"},
           "segments": [{"id": "S01", "lines": [{"text": "One two three four.", "visual_beats": [
               {"at": "two", "kind": "symbol", "why": "marks two", "symbol": "question"},
               {"at": "three", "kind": "symbol", "why": "marks three", "symbol": "check"}]}], "shots": []}]}
    toks = S.tokens(doc)
    words = [{"w": t["w"], "s": 1.0 if i in (1, 2) else 0.2 + i * 0.4, "e": 1.4 if i in (1, 2) else 0.6 + i * 0.4}
             for i, t in enumerate(toks)]  # "two" and "three" collapsed onto one instant by the timing fallback
    shots = [{"id": "T1", "picture": "p", "start": 0.0, "end": 10.0, "accents": []}]
    problems: list = []
    out = BEATS.resolve(doc, toks, words, lambda i: i, shots, 30, 10.0, problems)
    assert len(out) == 1  # the first beat is kept
    assert any("same instant" in p["detail"] for p in problems)


# --- the audio bugs, fixed for every schema --------------------------------------------------------------------------------

def test_cue_variants_are_deterministic_pitch_shifts():
    a0, a1, a2 = CUES.render("tick", 0), CUES.render("tick", 1), CUES.render("tick", 2)
    assert len(a1) > len(a0) > len(a2)  # 0.94 stretches, 1.06 shortens
    assert np.array_equal(CUES.render("tick", 1), a1)  # deterministic
    assert np.array_equal(CUES.render("tick", 3), a0)  # wraps round
    assert np.array_equal(CUES.render("tick"), a0)  # the old call is variant 0


def test_cue_bus_rotates_variants_so_no_two_presses_are_identical():
    g = ASM.db(CUES.DEFAULT_GAIN_DB)
    w0, w1 = CUES.render("tick", 0) * g, CUES.render("tick", 1) * g
    bus = ASM.cue_bus([{"sound": "tick", "start": 0.0}, {"sound": "tick", "start": 1.0}], ASM.SR * 3)
    assert np.allclose(bus[: len(w0)], w0)
    assert np.allclose(bus[ASM.SR: ASM.SR + len(w1)], w1)
    assert not np.allclose(bus[ASM.SR: ASM.SR + len(w0)], w0)


def test_one_shot_sounds_are_never_tiled():
    snd = ASM.Sounds([])
    assert snd.loopable("clockwork_loop__v1")  # made to loop
    assert not snd.loopable("reveal_sting__v1")  # the 30.772 s sting prompted as "one ~4 s hit"
    assert snd.loopable("some_future_file")  # no manifest entry: the old behaviour stays
    one = np.ones(100)
    out = ASM.play_once(one, 500)
    assert len(out) == 500 and np.all(out[100:] == 0.0)  # played once, padded, never tiled
    assert ASM.loop_to(one, 500)[300:400].max() > 0  # what loop_to would have done


def test_sound_density_counts_cues_with_effects():
    cues = [{"sound": "tick", "start": i * 2.0, "end": i * 2.0 + 0.05} for i in range(25)]
    timed = {"duration": 60.0, "shots": [], "audio": {"sfx": [], "beds": [], "music": [], "cues": cues}}
    assert any(f["rule"] == "AL-02" and "clutter" in f["detail"] for f in L.check(timed))  # 25 events, 0 "effects"
    timed["audio"]["cues"] = cues[:10]
    assert not any(f["rule"] == "AL-02" for f in L.check(timed))


# --- MO-07 and the manner of speech ----------------------------------------------------------------------------------------

def _mshot(i, start, end, seg="S01"):
    return {"id": f"T{i}", "segment": seg, "picture": f"p{i}", "start": float(start), "end": float(end),
            "start_frame": int(start * 30), "end_frame": int(end * 30), "accents": [], "bubbles": []}


def test_hold_variance_flags_a_metronome_cut():
    shots = [_mshot(i, i * 4.0, (i + 1) * 4.0) for i in range(6)]  # six identical 4 s holds
    timed = {"duration": 24.0, "shots": shots, "visuals": [], "cards": [], "visual_beats": []}
    assert "MO-07" in {f["rule"] for f in motion_lint.check(timed)}
    spans = [(0, 3), (3, 10), (10, 12), (12, 20), (20, 23), (23, 24)]
    varied = {"duration": 24.0, "shots": [_mshot(i, a, b) for i, (a, b) in enumerate(spans)],
              "visuals": [], "cards": [], "visual_beats": []}
    assert "MO-07" not in {f["rule"] for f in motion_lint.check(varied)}


def test_a_declared_manner_must_be_heard_on_scene_scripts():
    doc = {"schema": "production_script/3",
           "cast": {"capone": {"speech": {"basis": "personality", "style": "short, hard, never raises his voice",
                                          "words": ["numbers", "quiet", "mine"]}}},
           "segments": [{"id": "S01", "lines": [{"text": "We move tonight.", "speaker": "capone"},
                                                {"text": "You heard me.", "speaker": "capone"},
                                                {"text": "Get the car.", "speaker": "capone"}]}]}
    assert any("signature" in f["detail"] for f in SP.check(doc))
    doc["segments"][0]["lines"][0]["text"] = "The numbers stay mine."
    assert not any("signature" in f["detail"] for f in SP.check(doc))
