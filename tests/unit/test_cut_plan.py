"""D-121 (the creator, 2026-11-07 22:23 UTC): every rule of the cut is checked by code before anything is drawn. A good plan passes;
each owned rule has a bad plan that trips exactly that rule; the assembly keeps the LTX sound, mixes an ambience bed per place,
crops instead of squeezing and writes subtitles without names."""
import copy

import pytest

from explainer_engine.production import cut_plan as C

MOUTH = {k: f"ura_{k}.png" for k in C.MOUTH_STATES}


def good():
    return {
        "fps": 24, "size": [1280, 704], "total": 17.5,
        "cast": {"M": "marcus", "U": "ura"},
        "ambience": {"street": "amb_street.wav", "tundra": "amb_tundra.wav", "cave": "amb_cave.wav"},
        "lines": [
            {"who": "N", "text": "A street in New York.", "file": "l0.wav", "at": 0.15, "seconds": 2.0, "scene": "street"},
            {"who": "N", "text": "Spears. Right at his throat.", "file": "l1.wav", "at": 3.15, "seconds": 2.0, "scene": "tundra",
             "must_show": ["spears"], "action": True},
            {"who": "M", "text": "Guys, come on.", "file": "l2.wav", "at": 6.15, "seconds": 1.5, "scene": "cave"},
            {"who": "U", "text": "Hold your tongue.", "file": "l3.wav", "at": 10.15, "seconds": 1.5, "scene": "cave"},
        ],
        "shots": [
            {"id": 0, "type": "C", "start": 0, "dur": 3, "lines": [0], "place": "street", "drawing": "p1", "shows": ["street"]},
            {"id": 1, "type": "V", "start": 3, "dur": 3, "lines": [1], "place": "tundra", "drawing": "p4", "clip": "c1.mp4",
             "shows": ["spears", "hunters", "marcus"]},
            {"id": 2, "type": "V", "start": 6, "dur": 4, "lines": [2], "place": "cave", "drawing": "p6", "clip": "c2.mp4",
             "two_shot": True, "shows": ["marcus", "ura"]},
            {"id": 3, "type": "D", "start": 10, "dur": 2.5, "lines": [3], "place": "cave", "who": "ura", "cut": "ura_rest.png",
             "bg": "blur_cave.png", "framing": "MCU", "h": 1.45, "drop": 0.38, "facing": "left", "mouth": dict(MOUTH),
             "mouth_cues": "l3.mouth.json", "edge_trim_px": 2},
            {"id": 4, "type": "D", "start": 12.5, "dur": 2.5, "lines": [], "place": "cave", "who": "marcus", "cut": "m.png",
             "bg": "blur_cave.png", "framing": "MCU", "h": 1.45, "drop": 0.38, "facing": "right", "edge_trim_px": 2},
            {"id": 5, "type": "H", "start": 15, "dur": 2.5, "lines": [], "img": "h_phone.png",
             "card": {"kind": "phone", "battery": 14, "status": "No service"}},
        ],
    }


def sh(p, i):
    return p["shots"][i]


def _more_lines(p):
    for k in range(4):
        p["lines"].append({"who": "U", "text": f"Line {k}.", "file": "x.wav", "at": 10.2, "seconds": 0.1, "scene": "cave"})
    sh(p, 3)["lines"] = [3, 4, 5, 6, 7]


def _lv08(p):
    p["shots"].insert(2, {"id": 9, "type": "C", "start": 6, "dur": 0.1, "lines": [], "place": "street", "drawing": "p1b",
                          "shows": ["street"]})


MUTATIONS = {
    "LV-01": lambda p: sh(p, 1).update(place="street", drawing="p1b"),
    "LV-02": lambda p: sh(p, 1).update(place="street", drawing="p1b"),
    "LV-06": lambda p: sh(p, 1).update(place="street", drawing="p1b"),
    "LV-07": lambda p: sh(p, 0).pop("place"),
    "LV-08": _lv08,
    "LV-04": lambda p: sh(p, 5).update(kind="sharp", place="street"),
    "DL-01": lambda p: sh(p, 3).update(h=0.95),
    "DL-02": lambda p: sh(p, 3).update(bg="cave.png"),
    "DL-03": lambda p: sh(p, 3).update(edge_trim_px=0),
    "DL-04": lambda p: sh(p, 3)["mouth"].pop("round"),
    "DL-05": lambda p: sh(p, 3).update(breathing=False),
    "DL-06": lambda p: sh(p, 4).update(facing="left"),
    "DL-07": _more_lines,
    "DL-08": lambda p: sh(p, 4).update(two_shot=True),
    "DL-09": lambda p: sh(p, 3).update(overlap_at=9.0),
    "ED-04": lambda p: sh(p, 1).update(transition="wipe"),
    "ED-14": lambda p: sh(p, 2).update(two_shot=False),
    "AS-01": lambda p: sh(p, 1).update(type="C"),
    "AS-02": lambda p: sh(p, 5).update(lines=[3]),
    "AS-03": lambda p: sh(p, 2).update(dur=9),
    "AS-04": lambda p: sh(p, 0).update(lines=[0, 2]),
    "AS-05": lambda p: p["ambience"].pop("cave"),
    "AS-06": lambda p: sh(p, 2).update(shows=["ura"]),
    "AS-07": lambda p: sh(p, 3).update(start=10.5),
    "AS-08": lambda p: sh(p, 1).update(shows=["hunters"]),
    "AS-09": lambda p: p["lines"][0].update(text="MARCUS: a street."),
    "AS-10": lambda p: sh(p, 1).update(keep_audio=False),
    "AS-11": lambda p: sh(p, 1).update(fit="stretch"),
    "AS-12": lambda p: sh(p, 5).pop("card"),
    "AS-13": lambda p: (sh(p, 2).update(state={"fire": "burning"}), sh(p, 3).update(state={"fire": "embers"})),
}


def test_good_plan_passes_every_check():
    assert C.gate(good()) == []


@pytest.mark.parametrize("rule", sorted(MUTATIONS))
def test_each_rule_trips_on_its_bad_plan(rule):
    p = copy.deepcopy(good())
    MUTATIONS[rule](p)
    assert rule in {f["rule"] for f in C.gate(p)}


def test_every_rule_owned_by_the_gate_has_a_bad_plan():
    owned = {r for r, where in C.CHECKS.items() if where.startswith("cut_plan.")}
    assert owned == set(MUTATIONS)


def test_spoken_line_without_mouth_is_never_rendered():
    """The creator 22:18: dialogue generated without a mouth is clearly a mistake (DL-04 FAIL, AS-02 FAIL)."""
    p = good()
    sh(p, 3).pop("mouth")
    f = [x for x in C.gate(p) if x["severity"] == "FAIL"]
    assert any(x["rule"] == "DL-04" for x in f)


def test_mouth_track_rests_outside_the_line():
    cues = [{"start": 0.0, "end": 0.1, "value": "A"}, {"start": 0.1, "end": 0.3, "value": "D"}, {"start": 0.3, "end": 0.5, "value": "E"}]
    track = C.mouth_track(cues, line_at=1.0, start=0.9, n=12, fps=20)   # frames at 0.9 .. 1.45
    assert track[:2] == ["rest", "rest"] and "wide" in track and "round" in track
    assert set(C.CUE_TO_STATE.values()) == set(C.MOUTH_STATES)


def test_fit_crops_and_never_squeezes():
    f = C.fit_filter(1280, 704, 24)
    assert "force_original_aspect_ratio=increase" in f and "crop=1280:704" in f


def test_assembly_keeps_clip_sound_and_mixes_ambience_per_place(tmp_path):
    cmds = C.assemble_commands(good(), tmp_path)
    sound = next(c for c in cmds if any(str(x).endswith("sound.m4a") for x in c))
    graph = sound[sound.index("-filter_complex") + 1]
    assert sound.count("c1.mp4") == 1 and sound.count("c2.mp4") == 1                   # AS-10: both clips' own sound
    assert sound.count("amb_cave.wav") == 3 and sound.count("amb_street.wav") == 1      # AS-05: a bed under every shot of a place
    assert "-stream_loop" in sound and f"volume={C.AMBIENCE_GAIN}" in graph
    assert f"amix=inputs={4 + 2 + 5}" in graph
    p = good()
    sh(p, 1).update(keep_audio=False, mute_reason="test")
    sound = next(c for c in C.assemble_commands(p, tmp_path) if any(str(x).endswith("sound.m4a") for x in c))
    assert "c1.mp4" not in sound


def test_subtitles_carry_no_names():
    srt = C.srt_text(good())
    assert "MARCUS" not in srt and "URA:" not in srt and "Hold your tongue." in srt
    assert C.check_subtitles(good(), [(0, 1, "URA: hold")])[0]["rule"] == "AS-09"


def test_cli_refuses_a_failing_plan(tmp_path, capsys):
    import json
    p = good()
    sh(p, 3).pop("mouth")
    (tmp_path / "plan.json").write_text(json.dumps(p))
    assert C.main(["assemble", str(tmp_path)]) == 1
    assert not (tmp_path / "seg").exists()


def test_blender_renderer_gates_first_and_clips_texture_edges():
    """blender/bpy/cut_render.py runs inside Blender (not here): its source must gate the plan before any render, clip texture edges
    (DL-03), mirror on flip_x (DL-06) and drive the mouth from cut_plan.mouth_track (DL-04)."""
    import ast
    from pathlib import Path
    src = (Path(C.__file__).parents[1] / "blender" / "bpy" / "cut_render.py").read_text(encoding="utf-8")
    ast.parse(src)
    assert src.index("cut_plan.gate(plan)") < src.index("bpy.ops.render.render")
    assert 'tex.extension = "CLIP"' in src and 'flip_x' in src and "cut_plan.mouth_track(" in src
    assert 'hide_render' in src and 's.get("h", 1.45)' in src
