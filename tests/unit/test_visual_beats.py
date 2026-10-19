"""Visual beats (VB-00..VB-08, PV-44; the creator 2026-10-19): something new on screen about every 1.5 s, tied to the
words said at that instant; in dialogue the face changes about once a second; every beat names its short cue sound."""
import copy
import json
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import cues as CUES
from explainer_engine.edit import motion_lint
from explainer_engine.production import beats as BEATS
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V
from explainer_engine.scripting import stage_guard as G

from test_production_script import ROOT, mini, words_for

EP1 = ROOT / "examples" / "stone_age" / "ep1_v1" / "production_script.json"


def _b(at, kind, why, cue="tick", **kw):
    return dict(at=at, kind=kind, why=why, cue={"sound": cue, **({"why": "an effect sounds here"} if cue == "none" else {})}, **kw)


def beats_doc() -> dict:
    """mini() as a production_script/2 with its beats written the way the beat-writer is asked to."""
    d = mini()
    d["schema"] = "production_script/2"
    d["cast"]["einstein"]["voice"] = {"voice_id": "e1", "name": "E", "style": "bright, quick, amused tenor"}
    s1, s2 = d["segments"][0]["lines"], d["segments"][1]["lines"]
    s1[0]["visual_beats"] = [_b("survive", "symbol", "asks if they survive", "blip", symbol="question"),
                             _b("night", "text", "the night is the threat", text="THE NIGHT")]
    s1[1]["visual_beats"] = [_b("not even", "accent", "not even the bravest: a jolt", "thud", effect="punch"),
                             _b("bravest", "highlight", "rings the bravest of them", "pluck", pos=[0.4, 0.45]),
                             _b("cold wind", "label", "names the cold wind", "tap", text="COLD WIND", pos=[0.3, 0.4]),
                             _b("rising", "symbol", "the wind is rising", "rise", symbol="arrow_up")]
    s2[0]["visual_beats"] = [_b("takes off", "prop", "the glasses Einstein takes off", "pop", thing="glasses"),
                             _b("glasses", "highlight", "rings his glasses", "pluck", pos=[0.7, 0.32])]
    s2[1]["speaker"] = "einstein"  # "Oh. A lens."
    s2[1]["visual_beats"] = [_b("Oh.", "expression", "oh: he sees it", "chime", expression="surprised"),
                             _b("lens", "expression", "a lens: he works it out", "none", expression="curious")]
    s2[1]["visual_beats"][1]["cue"] = {"sound": "none", "why": "a quiet face change: the voice carries it"}
    s2[2]["visual_beats"] = [_b("One careful", "symbol", "a careful breath, hold it", "none", symbol="clock"),
                             _b("small flame", "text", "a small flame", text="SMALL FLAME"),
                             _b("hundred", "label", "a hundred tired faces", "tap", text="TIRED FACES", pos=[0.5, 0.6]),
                             _b("turn toward", "symbol", "faces turn toward the fire", "whiff", symbol="arrow_down")]
    return d


def _vb(found, rule=None, sev=None):
    return [f for f in found if f["rule"].startswith("PV-44") and (rule is None or f["rule"].endswith(rule))
            and (sev is None or f["severity"] == sev)]


def _check(doc):
    return V.check_script(C.compile_doc(doc))


def _timed(doc, gap=0.12):
    return T.time_script(doc, words_for(doc, gap))


# --- schema and the static lint ------------------------------------------------------------------------------------------

def test_beats_doc_is_valid_and_has_no_vb_fail():
    d = beats_doc()
    assert not S.schema_errors(d)
    found = _check(d)
    assert not _vb(found, sev="FAIL"), _vb(found, sev="FAIL")
    assert not [f for f in found if f["severity"] == "FAIL"], [f for f in found if f["severity"] == "FAIL"]


def test_legacy_script_gets_one_review_and_v2_without_beats_fails():
    legacy = _vb(V.check_script(C.compile_doc(mini())))
    assert [f["rule"] for f in legacy] == ["PV-44 VB-00"] and legacy[0]["severity"] == "REVIEW"
    d = mini()
    d["schema"] = "production_script/2"
    assert _vb(_check(d), "VB-01", "FAIL")


def test_ep1_legacy_validates_with_only_the_vb00_notice():
    found = V.check_script(json.loads(EP1.read_text(encoding="utf-8")))
    assert [f["rule"] for f in _vb(found)] == ["PV-44 VB-00"]


def test_schema_refuses_unknown_kind_and_missing_reason():
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][0]["kind"] = "explosion"
    assert S.schema_errors(d)
    d = beats_doc()
    del d["segments"][0]["lines"][0]["visual_beats"][0]["why"]
    assert S.schema_errors(d)
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["cue"] = {"sound": "airhorn"}
    assert S.schema_errors(d)


def test_vb03_reason_and_phrase_of_its_own_line():
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["why"] = "night threat!"
    assert _vb(BEATS.lint(d), "VB-03", "FAIL")
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["at"] = "bravest"  # said in the next line, not this one
    assert _vb(BEATS.lint(d), "VB-03", "FAIL")


def test_vb03_off_topic_payload_is_a_review():
    d = beats_doc()
    b = d["segments"][0]["lines"][0]["visual_beats"][1]
    b["text"], b["why"] = "STOCK PRICES", "a random chart"
    found = _vb(BEATS.lint(d), "VB-03")
    assert found and all(f["severity"] == "REVIEW" for f in found)


def test_vb04_words_and_numbers_need_a_claim():
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["text"] = "THE LONG COLD DARK NIGHT"
    assert _vb(BEATS.lint(d), "VB-04", "FAIL")
    d = beats_doc()
    d["segments"][1]["lines"][2]["visual_beats"][2] = _b("hundred", "chart", "a hundred tired faces", "blip", chart="counter",
                                                        values=[0, 100], labels=["faces"], claim="C-01")
    assert not _vb(BEATS.lint(d), "VB-04")
    del d["segments"][1]["lines"][2]["visual_beats"][2]["claim"]
    assert S.schema_errors(d)  # a chart always names its claim
    d["segments"][1]["lines"][2]["visual_beats"][2] = _b("hundred", "text", "a hundred faces", text="100 FACES")
    assert _vb(BEATS.lint(d), "VB-04", "FAIL")


# --- timing ----------------------------------------------------------------------------------------------------------------

def test_timing_places_beats_on_their_words_with_offsets_and_shots():
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["offset"] = 0.4
    w = words_for(d)
    timed = T.time_script(d, w)
    toks = S.tokens(d)
    vb = timed["visual_beats"]
    night = next(i for i, t in enumerate(toks) if t["w"].startswith("night"))
    assert vb[1]["start"] == pytest.approx(w["words"][night]["s"] + 0.4, abs=1e-3)
    assert vb[1]["shot"] == "SH001" and vb[1]["end"] > vb[1]["start"]
    punch = [a for s in timed["shots"] for a in s["accents"] if a.get("beat")]
    assert [a["kind"] for a in punch] == ["punch"]  # the accent beat is drawn by accents.py
    ex = [b for b in vb if b["kind"] == "expression"]
    assert ex[0]["who"] == "einstein" and ex[0]["end"] == ex[1]["start"]  # an expression holds until the face changes
    kinds = {k for _, k in motion_lint.events(timed)}
    assert {"beat_symbol", "beat_text", "beat_expression"} <= kinds


def test_vb01_gap_while_the_narrator_speaks():
    d = beats_doc()
    d["segments"][0]["lines"][1]["visual_beats"] = d["segments"][0]["lines"][1]["visual_beats"][:1]  # only "not even"
    found = BEATS.check_timed(_timed(d), d)
    assert _vb(found, "VB-01", "FAIL")
    assert not _vb(BEATS.check_timed(_timed(beats_doc()), beats_doc()), "VB-01", "FAIL")


def _long_dialogue(changes):
    d = beats_doc()
    line = d["segments"][1]["lines"][1]
    line["text"] = "Oh. A lens. If I hold it just so, the sun gathers into one bright point on the grass."
    line["visual_beats"] = changes
    d["segments"][1]["shots"][0]["bubbles"] = []
    return d


def test_vb02_face_changes_about_once_a_second_in_dialogue():
    one = [_b("Oh.", "expression", "oh: he sees it", "chime", expression="surprised")]
    d = _long_dialogue(one)
    assert _vb(BEATS.check_timed(_timed(d), d), "VB-02", "FAIL")
    q = {"sound": "none", "why": "a quiet face change"}
    many = [dict(_b(at, "expression", f"{at} {why}", expression=e), cue=q) for at, e, why in [
        ("lens", "curious", "he looks at it"), ("hold", "determined", "he tries it"), ("just so", "doubtful", "careful angle"),
        ("sun", "amused", "it works"), ("one bright", "joyful", "the point appears"), ("point", "smug", "told you"),
        ("grass", "deadpan", "the grass smokes")]]
    many[0]["cue"] = {"sound": "chime"}
    d = _long_dialogue([one[0]] + many)
    d["segments"][1]["lines"][1]["visual_beats"][0]["cue"] = q
    found = BEATS.check_timed(_timed(d), d)
    assert not _vb(found, "VB-02", "FAIL"), _vb(found, "VB-02")
    same = copy.deepcopy(d)
    same["segments"][1]["lines"][1]["visual_beats"][2]["expression"] = "curious"  # curious twice in a row is not a change
    assert any("stays curious" in f["detail"] for f in _vb(BEATS.check_timed(_timed(same), same), "VB-02"))


def test_vb06_expression_needs_a_face_to_change():
    d = beats_doc()
    d["segments"][1]["lines"][1]["visual_beats"][0]["who"] = "franklin"  # in the duo picture, but no speakers point
    assert _vb(BEATS.check_timed(_timed(d), d), "VB-06", "FAIL")
    d["cast"]["franklin"]["expressions"] = {"surprised": "assets/characters/crossworld_cast_v0/analyst/a_startled.png"}
    assert not S.schema_errors(d)
    assert not _vb(BEATS.check_timed(_timed(d), d), "VB-06", "FAIL")
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][0] = _b("survive", "expression", "who survives", "none", expression="worried")
    assert _vb(BEATS.lint(d), "VB-06", "FAIL")  # a narrator line names no face


# --- cues (VB-08) ----------------------------------------------------------------------------------------------------------

def test_every_cue_is_short_and_named():
    for name in CUES.BUILD:
        x = CUES.render(name)
        assert CUES.MIN_MS <= CUES.length_ms(name) <= CUES.MAX_MS and abs(x).max() <= 1.0 + 1e-6
        assert abs(x[0]) < 0.05 and abs(x[-1]) < 0.05  # faded: no click
    assert np.array_equal(CUES.render("pop"), CUES.render("pop"))


def test_vb08_every_beat_has_a_cue_and_none_needs_a_reason():
    d = beats_doc()
    del d["segments"][0]["lines"][0]["visual_beats"][1]["cue"]
    assert _vb(BEATS.lint(d), "VB-08", "FAIL")
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["cue"] = {"sound": "none"}
    assert _vb(BEATS.lint(d), "VB-08", "FAIL")
    d = beats_doc()
    d["segments"][0]["lines"][0]["visual_beats"][1]["cue"] = {"sound": "none", "why": "no reason really"}
    assert any("makes no sound" in f["detail"] for f in _vb(BEATS.check_timed(_timed(d), d), "VB-08", "FAIL"))


def test_vb08_cue_never_doubles_an_effect_and_cues_never_stack():
    d = beats_doc()
    d["segments"][1]["audio"]["sfx"].append({"at": "takes off", "sound": "pop", "gain_db": -20, "max_s": 0.4})
    found = _vb(BEATS.check_timed(_timed(d), d), "VB-08", "FAIL")
    assert any("doubles a sound effect" in f["detail"] for f in found)
    d["segments"][1]["lines"][0]["visual_beats"][0]["cue"] = {"sound": "none", "why": "the pop effect sounds here"}
    assert not any("doubles" in f["detail"] for f in _vb(BEATS.check_timed(_timed(d), d), "VB-08"))
    d = beats_doc()
    d["segments"][0]["lines"][1]["visual_beats"][2]["at"] = "bravest"  # two cues on one word
    assert any("stack" in f["detail"] for f in _vb(BEATS.check_timed(_timed(d), d), "VB-08", "FAIL"))


def test_vb08_quiet_faces_and_one_take_a_line():
    d = beats_doc()
    d["segments"][1]["lines"][1]["visual_beats"][1]["cue"] = {"sound": "chime"}  # curious is a quiet change
    found = _vb(BEATS.lint(d), "VB-08")
    assert found and found[0]["severity"] == "REVIEW"
    d["segments"][1]["lines"][1]["visual_beats"][1]["expression"] = "joyful"
    d["segments"][1]["lines"][1]["visual_beats"][1]["at"] = "lens"
    assert any("expression cues on one" in f["detail"] for f in _vb(BEATS.check_timed(_timed(d, 0.5), d), "VB-08", "FAIL"))


def test_cues_are_in_the_timed_audio_and_the_mix():
    from explainer_engine.production import assemble as A
    d = beats_doc()
    timed = _timed(d)
    cues = timed["audio"]["cues"]
    assert len(cues) == sum(1 for b in timed["visual_beats"] if b["cue"]["sound"] != "none")
    assert all(-36 <= c["gain_db"] <= -20 for c in cues)

    class Quiet:
        def load(self, name):
            return np.zeros(4800)

    n = int(timed["duration"] * A.SR)
    stats: dict = {}
    mix = A.build_audio(timed, np.zeros(n), Quiet(), stats)
    a = int(cues[0]["start"] * A.SR)
    assert stats["cues"] == len(cues) and np.abs(mix[a:a + 1200]).max() > 0.01


# --- stage guard ------------------------------------------------------------------------------------------------------------

def test_stage_guard_beats_own_their_field_and_the_editor_only_moves_them():
    before, after = mini(), beats_doc()
    after["schema"], after["cast"] = before["schema"], before["cast"]
    after["segments"][1]["lines"][1].pop("speaker")
    assert not G.violations("beats", before, after)
    assert G.violations("performer", before, after)
    moved = copy.deepcopy(after)
    moved["segments"][0]["lines"][1]["visual_beats"][1]["pos"] = [0.6, 0.5]
    assert not G.violations("editor", after, moved)
    moved["segments"][0]["lines"][1]["visual_beats"][1]["kind"] = "symbol"
    assert G.violations("editor", after, moved)
    worded = copy.deepcopy(after)
    worded["segments"][0]["lines"][0]["text"] = "Could they last the night?"
    assert G.violations("beats", after, worded)  # the beat-writer never changes a word


# --- render -------------------------------------------------------------------------------------------------------------

def test_every_beat_kind_draws_something_and_renders_the_same_twice():
    frame = Image.new("RGB", (320, 180), (60, 50, 40))
    box, size = (0, 0, 320, 180), (320, 180)
    kinds = [dict(_b("x", "text", "a b c", text="HELLO")), dict(_b("x", "label", "a b c", text="FIRE", pos=[0.4, 0.5])),
             dict(_b("x", "prop", "a b c", thing="glasses")), dict(_b("x", "highlight", "a b c", pos=[0.5, 0.5])),
             dict(_b("x", "symbol", "a b c", symbol="cross")),
             dict(_b("x", "chart", "a b c", chart="bars", values=[3, 7], labels=["a", "b"], claim="C-1")),
             dict(_b("x", "chart", "a b c", chart="counter", values=[0, 100], unit="kg", claim="C-1"))]
    kinds += [dict(_b("x", "expression", "a b c", expression=e), who="einstein", face=[0.5, 0.5]) for e in BEATS.EXPRESSIONS
              if e != "neutral"]
    for b in kinds:
        b.update(start=0.0, end=1.0, start_frame=0, end_frame=30, shot="SH001")
        one = BEATS.draw(frame, [b], 12, 30, box, size, {}, [])
        two = BEATS.draw(frame, [b], 12, 30, box, size, {}, [])
        assert np.asarray(one).astype(int).__sub__(np.asarray(frame)).__abs__().sum() > 0, b["kind"] + b.get("expression", "")
        assert np.array_equal(np.asarray(one), np.asarray(two))


def test_face_camera_leans_in_on_the_face_and_rests_outside_the_dialogue():
    b = {"start_frame": 30, "end_frame": 90, "face": [0.7, 0.3], "shot": "SH001"}
    box = (0.0, 0.0, 320.0, 180.0)
    assert BEATS.face_camera(box, 320, 180, [b], 0, 30) == box
    z = BEATS.face_camera(box, 320, 180, [b], 60, 30)
    assert z[2] - z[0] < 320 and z[0] > 0  # zoomed in, towards the face on the right
    x0, y0, x1, y1 = z
    assert x0 <= 0.7 * 320 <= x1 and y0 <= 0.3 * 180 <= y1


def test_sprite_inset_swaps_the_heroes_own_cut_out(tmp_path):
    Image.new("RGBA", (40, 60), (200, 30, 30, 255)).save(tmp_path / "e_surprised.png")
    frame = Image.new("RGB", (320, 180), (0, 0, 0))
    b = dict(_b("x", "expression", "a b c", expression="surprised"), who="einstein", start=0.0, end=1.0, start_frame=0,
             end_frame=30, shot="SH001")
    out = BEATS.draw(frame, [b], 15, 30, (0, 0, 320, 180), (320, 180), {"einstein": {"expressions": {"surprised": "e_surprised.png"}}},
                     [tmp_path])
    px = np.asarray(out)
    assert (px[..., 0] > 150).sum() > 400  # the red cut-out is on screen


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="needs ffmpeg")
def test_end_to_end_beats_render(tmp_path):
    from test_production_script import _wav
    from explainer_engine.production import __main__ as CLI
    d = C.compile_doc(beats_doc())
    rng = np.random.default_rng(0)
    pics, snd = tmp_path / "pictures", tmp_path / "sounds"
    pics.mkdir(), snd.mkdir()
    for k, name in enumerate(["valley", "camp", "duo", "cold_hands"]):
        Image.fromarray((rng.random((180, 320, 3)) * 80 + k * 40).astype(np.uint8)).save(pics / f"{name}.png")
    sr = 48000
    for name, x in [("wind", rng.normal(0, 0.1, sr * 2)), ("crackle", rng.normal(0, 0.1, sr)),
                    ("pop", np.sin(np.arange(sr // 4) * 0.2) * 0.5), ("tone", np.sin(np.arange(sr * 2) * 0.03) * 0.3)]:
        _wav(snd / f"{name}.wav", x)
    w = words_for(d)
    _wav(tmp_path / "narration.wav", np.zeros(int(w["duration"] * sr)))
    d["picture_dirs"], d["sound_dirs"] = ["pictures"], ["sounds"]
    (tmp_path / "script.json").write_text(json.dumps(d))
    (tmp_path / "words.json").write_text(json.dumps(w))
    out = tmp_path / "out"
    assert CLI.main(["run", str(tmp_path / "script.json"), str(tmp_path / "narration.wav"), str(tmp_path / "words.json"),
                     "--out", str(out), "--size", "320x180"]) == 0
    rep = json.loads((out / "assemble_report.json").read_text())
    assert rep["audio"]["cues"] > 0 and rep["frames_written"] == json.loads((out / "timed.json").read_text())["frames"]


# --- the example episode -------------------------------------------------------------------------------------------------

def ep1_with_beats() -> dict:
    """Episode 1's first three segments as a production_script/2 with the beats of tests/fixtures/ep1_beats."""
    d = json.loads(EP1.read_text(encoding="utf-8"))
    fx = json.loads((ROOT / "tests/fixtures/ep1_beats/beats_S01-S03.json").read_text(encoding="utf-8"))
    d["schema"] = "production_script/2"
    d["segments"] = d["segments"][:3]
    for k in ("shorts", "graphics", "periods"):
        d.pop(k, None)
    for seg in d["segments"]:
        seg.pop("period", None)
        for line, beats in zip(seg["lines"], fx[seg["id"]], strict=True):
            line["visual_beats"] = beats
    return d


def test_episode1_opening_with_beats_meets_the_cadence():
    d = ep1_with_beats()
    assert not S.schema_errors(d), S.schema_errors(d)[:3]
    found = BEATS.lint(d)
    timed = T.time_script(d, V.estimated_words(d))
    found += BEATS.check_timed(timed, d)
    assert not [f for f in found if f["severity"] == "FAIL"], [f for f in found if f["severity"] == "FAIL"]
    m = BEATS.measure(timed)
    assert m["narration_gap_mean"] <= BEATS.MEAN_OK and m["beats"] == 49
