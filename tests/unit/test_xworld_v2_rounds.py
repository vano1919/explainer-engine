from pathlib import Path

from explainer_engine.training.pods import xworld_v2_build as b, xworld_v2_judge as j, xworld_v2_scenes as s

SCENES = Path("explainer_engine/training/pods/stories/v2")


def test_three_worlds_five_shots_and_faces():
    scenes = s.load(SCENES)
    assert sorted(x["world"] for x in scenes) == ["exterior", "interior", "urban"]
    assert all(len(x["shots"]) == 5 and x["era"] for x in scenes)
    todo = s.jobs(scenes)  # raises on an LT-79 face problem
    assert len(todo) == 3 * 2 * (1 + 4 * 4)


def test_forms():
    shot = {"desc": "D.", "layout": "L.", "change": "C."}
    assert "L." not in s.prompt("P1", shot) and "C." in s.prompt("P1", shot)
    assert "L." in s.prompt("P2", shot) and "Keep everything" in s.prompt("P2", shot)
    assert s.prompt("P3", shot) == "xworld style, D. L."
    todo = s.jobs(s.load(SCENES))
    assert all(t["ref"] is None for t in todo if t["form"] in ("P3", "all"))
    p1 = [t for t in todo if t["form"] == "P1" and t["scene"] == "tent" and t["seed"] == 23]
    assert p1[0]["ref"] == "tent_23_s0" and p1[1]["ref"] == p1[0]["name"]
    assert all(t["ref"] == f"{t['scene']}_{t['seed']}_s0" for t in todo if t["form"] == "P2F")
    assert "L." not in s.prompt("P2F", shot) and s.prompt("P2F", shot).startswith("xworld style, " + s.MASTER)
    assert s.prompt("P2R", shot).startswith("rm style, " + s.MASTER)


def test_round_tests_are_reduced_and_share_shot_zero():
    todo = s.jobs(s.load(SCENES), tests=s.ROUND_TESTS)
    forms = {(t["scene"], t["seed"], t["form"]) for t in todo if t["form"] != "all"}
    assert ("tent", 11, "P2R") in forms and not any(f[2] == "P2R" and f[0] != "tent" for f in forms)
    assert {f[1] for f in forms if f[2] == "P2F"} == {11, 23} and {f[1] for f in forms if f[2] == "P3"} == {11}
    assert len(todo) == 3 * ((1 + 4 + 4) + (1 + 4)) + 4  # per scene: seed 11 shot 0 + P3 + P2F, seed 23 shot 0 + P2F; tent + P2R


def test_judge_questions_and_scoring(tmp_path):
    qs = j.questions(s.load(SCENES), tmp_path)
    assert {q["key"] for q in qs} >= {"check0", "same_place", "size", "era"}
    era = next(q for q in qs if q["key"] == "era" and q["scene"] == "rome")
    assert j.ok(era, "Ancient Roman Empire") and not j.ok(era, "Medieval Europe")
    size = next(q for q in qs if q["key"] == "size")
    assert j.ok(size, size["want"].capitalize() + ".")
    rows = [{"form": "P1", "scene": "tent", "key": "check0", "ok": True}, {"form": "P1", "scene": "tent", "key": "era", "ok": False}]
    assert j.summary(rows)["P1"] == 0.5


def test_build_writes_cut_pairs_and_drops_inshot_pairs():
    v1m = {"train": {"single": [{"img": "frames/0001.png"}], "scene_pairs": [{"a": "frames/0001.png", "b": "frames/0002.png"}],
                     "inshot_pairs": [{"a": "frames/0002.png", "b": "frames/0003.png"}]},
           "hold_out": {"chains": [], "guard_shots": []}}
    caps = {"d:frames/0001.png": "a", "d:frames/0002.png": "A room.", "d:frames/0003.png": "A room again.",
            "c:frames/0001.png>frames/0002.png": "Change from the previous shot: the camera zooms in.",
            "c:frames/0002.png>frames/0003.png": "Change from the previous shot: a hand moves."}
    pr = b.pairs(v1m, caps)
    assert len(pr) == 1 and pr[0][0] == "p0000"  # the in-shot pair is left out
    assert pr[0][3] == f"rm style, {b.MASTER} A room. {b.CUT} the camera zooms in. {b.KEEP}"
    held = {i: f"xworld style, held {i}" for i in b.SAMPLE_HELD}
    smp = b.samples({"hold_out": held}, s.load(SCENES)[0] if s.load(SCENES)[0]["name"] == "tent" else s.load(SCENES)[1])
    assert smp[-1]["prompt"].startswith("rm style, held c007") and smp[-2]["prompt"] == "held c007"


def test_new_place_pairs_are_dropped():
    cap = lambda c: b.cut_caption(f"xworld style, A room. Change from the previous shot: {c}")
    assert b.new_place(cap("The scene shifts to a doorway where two new figures appear."))
    assert not b.new_place(cap("The camera zooms in to a close-up and the other figure is no longer visible."))
