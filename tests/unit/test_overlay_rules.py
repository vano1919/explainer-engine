"""The overlay validator (overlay/rules.py): a good demo passes with no FAIL, and every OV rule has one bad input that makes it FAIL (R-B).
The demo's shots are built here from a synthetic narration (uniform word times), so the test needs no audio, no photos and no render."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.overlay import demo_script as D
from explainer_engine.overlay import rules as R
from explainer_engine.overlay import spec2

STYLE = json.loads((Path(R.__file__).parent / "demo_style.json").read_text())
FACES = {"id": "T", "faces": [], "subject": [(0.0, 0.0, 0.1, 0.1)], "size": [2752, 1548], "calm": np.zeros((54, 96), np.float32)}


WORDS = {l["no"]: l for l in json.loads((Path(R.__file__).parent / "demo_words.json").read_text())}


def narr(no: int) -> dict | None:
    return WORDS[no]


@pytest.fixture(scope="module")
def base():
    specs = {}
    for sh in D.SHOTS:
        specs[sh["no"]] = spec2.build(sh, narr(sh["no"]), STYLE, {"M1": FACES, "M3": FACES, "C1": FACES})
    return specs


def ctx(base, no, mut=None, shot_mut=None, boxes=None, meas=None, html=None):
    sp = copy.deepcopy(base[no])
    sh = copy.deepcopy(next(s for s in D.SHOTS if s["no"] == no))
    if mut:
        mut(sp)
    if shot_mut:
        shot_mut(sh)
    line = narr(no)
    return R.Ctx(sp, sh, line, boxes, meas or {}, html)


def run(rule, c):
    return R.SHOT_RULES[rule](c)


def test_good_demo_has_no_fail(base):
    for sh in D.SHOTS:
        c = ctx(base, sh["no"])
        for k, fn in R.SHOT_RULES.items():
            res = fn(c)
            assert res["status"] != R.FAIL, (sh["no"], k, res)


def item(sp, kind):
    return next(i for i in sp["items"] if i["kind"] == kind)


def panel0(sp):
    return sp["panels"][0]


def add_item(sp, **kw):
    sp["items"].append({"id": "x1", "pid": "p0", "kind": "label", "start": 20, "motion_end": 26, "end": 100, "word": None, "layer": "screen", "sound": [], **kw})


def bad_overlap_motion(sp):
    sp["items"][3]["start"] = sp["items"][2]["start"] + 2        # the highlight starts while the pulse still moves


def bad_first_bar(sp):
    next(i for i in sp["items"] if i["kind"] == "bar")["start"] += 10


def bad_sound_none(sp):
    sp["sound"] = [e for e in sp["sound"] if e["item"] != item(sp, "route_arrow")["id"]]


def bad_pencil_len(sp):
    for e in sp["sound"]:
        if e["cls"] == "pencil_scribble":
            e["dur"] = 40


def bad_three_pops(sp):
    sp["sound"] += [{"cls": "pop_in", "t": 30, "dur": 20, "gain": 1, "item": "i0"}] * 3


BAD = {
    "OV-01": (8, lambda sp: sp["items"].append({"id": "x", "kind": "label"}), None, {}),
    "OV-02": (2, lambda sp: panel0(sp).update(end=sp["frames"] - 2), None, {}),
    "OV-03": (8, lambda sp: sp.update(overlay_reason="date"), None, {}),
    "OV-04": (2, None, lambda sh: sh.update(route="still_25d"), {}),
    "OV-05": (3, lambda sp: sp.update(mode="full"), None, {}),
    "OV-06": (2, lambda sp: sp.update(route="still_25d"), None, {}),
    "OV-10": (3, lambda sp: sp["style"].update(source_picture=None), None, {}),
    "OV-11": (3, None, None, {"html": "<g fill='#123456'>"}),
    "OV-13": (3, lambda sp: sp["style"]["tokens"].update(paper="#FFFFFF"), None, {}),
    "OV-14": (3, lambda sp: item(sp, "label").update(size=30), None, {}),
    "OV-15": (3, None, None, {"meas": {"contrast": {"i0": 3.0}}}),
    "OV-16": (2, bad_overlap_motion, None, {}),
    "OV-17": (6, lambda sp: item(sp, "counter").update(unit="km"), None, {}),
    "OV-18": (6, None, None, {"boxes": "on the line"}),
    "OV-20": (3, lambda sp: sp.update(surface="solid"), None, {}),
    "OV-21": (6, lambda sp: panel0(sp).update(alpha=0.9), None, {}),
    "OV-22": (3, lambda sp: sp["style"].update(halo_px_2k=0), None, {}),
    "OV-23": (9, lambda sp: sp.update(surface="glass") or panel0(sp).update(surface="glass"), None, {}),
    "OV-24": (2, None, None, {"meas": {"bg_std": 0.0}}),
    "OV-30": (3, lambda sp: sp.update(overlay_reason="mood"), None, {}),
    "OV-32": (6, lambda sp: sp["items"][0].update(pid="p9"), None, {}),
    "OV-33": (6, lambda sp: panel0(sp).update(box=[100, 100, 1800, 1000]), None, {}),
    "OV-34": (3, lambda sp: sp.update(protected=[[0.0, 0.0, 1.0, 1.0]]), None, {}),
    "OV-35": (3, lambda sp: item(sp, "label").update(start=item(sp, "label")["start"] + 10), None, {}),
    "OV-36": (3, lambda sp: sp.update(anchor="map"), None, {}),
    "OV-37": (3, lambda sp: sp.update(camera_events=[{"kind": "shake", "start": 0, "end": 300}]), None, {}),
    "OV-38": (6, lambda sp: panel0(sp).update(box=[848, 460, 864, 486]), None, {}),
    "OV-40": (3, lambda sp: item(sp, "label").update(kind="sparkle"), None, {}),
    "OV-41": (2, lambda sp: sp.update(items=[i for i in sp["items"] if i["kind"] != "date_chip"]), None, {}),
    "OV-42": (2, lambda sp: sp.update(frames=24 * 20), None, {}),
    "OV-43": (2, None, None, {"meas": {"max_frozen_run": 60}}),
    "OV-45": (4, lambda sp: item(sp, "chart_title").update(text="one two three four five six seven eight"), None, {}),
    "OV-46": (4, lambda sp: sp.update(demo_data=False), None, {}),
    "OV-47": (4, bad_first_bar, None, {}),
    "OV-48": (4, lambda sp: item(sp, "bar").update(label=""), None, {}),
    "OV-50": (6, bad_sound_none, None, {}),
    "OV-51": (6, bad_pencil_len, None, {}),
    "OV-54": (3, bad_three_pops, None, {}),
}


@pytest.mark.parametrize("rule", sorted(BAD))
def test_each_rule_fails_on_its_bad_input(base, rule):
    no, mut, shot_mut, kw = BAD[rule]
    kw = dict(kw)
    if kw.get("boxes") == "on the line":
        sp = base[no]
        ln = item(sp, "route_arrow")
        bx, by = sp["panels"][0]["box"][:2]
        x, y = ln["path"][len(ln["path"]) // 2]
        kw["boxes"] = {item(sp, "counter")["id"]: [x + bx - 40, y + by - 20, 80, 40]}
    c = ctx(base, no, mut, shot_mut, **kw)
    res = run(rule, c)
    assert res["status"] == R.FAIL, (rule, res)


def test_rules_that_cannot_be_checked_say_so(base):
    assert run("OV-31", ctx(base, 3))["status"] == R.NOT_RUN
    assert run("OV-15", ctx(base, 3))["status"] == R.NOT_RUN          # no measurement: never PASS by default
    assert run("OV-43", ctx(base, 2))["status"] == R.NOT_RUN
    assert run("OV-49", ctx(base, 4))["status"] == R.NA
    assert run("OV-44", ctx(base, 2))["status"] == R.NOT_RUN


def test_episode_rules_fail_on_bad_input(base):
    specs = [base[s["no"]] for s in D.SHOTS]
    assert R.ep12({"order": ["grade", "composite"]})["status"] == R.FAIL
    assert R.ep12({"order": ["composite", "grade"]})["status"] == R.PASS
    assert R.ep12(None)["status"] == R.NOT_RUN
    assert R.ep53({"sfx_under_scene_lu": 3.0})["status"] == R.FAIL
    assert R.ep55({"groups": {"10 %": -34.0, "30 %": -31.0, "LTX": -34.0}, "ambience_min_100ms_dbfs": -40})["status"] == R.FAIL
    assert R.ep55({"groups": {"10 %": -34.0, "30 %": -33.5, "LTX": -34.0}, "ambience_min_100ms_dbfs": -90})["status"] == R.FAIL
    bad = copy.deepcopy(specs)
    bad[1]["sound"][0]["cls"] = "beep"
    assert R.ep52(bad)["status"] == R.FAIL
    assert R.ep52(specs)["status"] == R.PASS
    acc = [copy.deepcopy(specs[2]) for _ in range(3)]
    assert R.ep32(acc)["status"] == R.FAIL
    full = [copy.deepcopy(specs[1]) for _ in range(6)]
    for s in full:
        s["frames"] = 24 * 12
    assert R.ep42(full)["status"] == R.FAIL
    odd = copy.deepcopy(specs)
    odd[1]["style"] = copy.deepcopy(odd[1]["style"])           # the specs share one style object; give this shot its own
    odd[1]["style"]["tokens"]["ink"] = "#000001"
    assert R.ep11(odd)["status"] == R.FAIL
    assert R.ep56(False, {"pop_in"})["status"] == R.NOT_RUN
