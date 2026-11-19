"""Anchors that follow the read (Fable audit 2026-11-13, FA-06 / P1) and picture sound events through the one resolver
(FA-10): word and fraction anchors, the G6 list of broken anchors right after the retime, the G1 REVIEW of absolute anchors
in a locked script."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import events as E
from explainer_engine.episode import sound_plan as SP
from explainer_engine.production import layers25d as L25
from explainer_engine.qa import gates as G

ROOT = Path(__file__).resolve().parents[2]
FPS = 24


def _pilot(tmp_path) -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    import av_pilot
    root = av_pilot.build(tmp_path, "new")
    return json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))


def _scaled(doc: dict, k: float) -> dict:
    s = copy.deepcopy(doc)
    for sh in s["shots"]:
        sh["target_duration_seconds"] = round(float(sh["target_duration_seconds"]) * k, 3)
    return s


def _rows(doc):
    return {r["gate"]: r for r in E.anchor_rows(doc, None, FPS)}


def test_the_pilot_retimed_gives_the_g6_list_instead_of_an_exception_later(tmp_path):
    """FA-06: at 0.6 the cut camera segments are a REVIEW (never silent); at 0.5 and 0.33 every broken anchor is one FAIL list."""
    doc = _pilot(tmp_path)
    assert all(r["status"] == G.PASS for r in _rows(doc).values())
    r6 = _rows(_scaled(doc, 0.6))
    assert r6["av_anchors_truncated"]["status"] == G.REVIEW and len(r6["av_anchors_truncated"]["measured"]) == 2
    r5 = _rows(_scaled(doc, 0.5))
    assert r5["av_anchors_inside_retimed_shots"]["status"] == G.FAIL
    assert any("S01_SH007" in m for m in r5["av_anchors_inside_retimed_shots"]["measured"])
    r3 = _rows(_scaled(doc, 0.33))["av_anchors_inside_retimed_shots"]
    assert r3["status"] == G.FAIL and len(r3["measured"]) == 3 and any("eruption_boom" in m for m in r3["measured"])


def _shot(**kw) -> tuple[dict, dict]:
    lines = [{"line_id": "L1", "speaker_type": "narrator", "speaker_id": "narrator_main",
              "text": "The mountain wakes and the sky turns black over the valley."}]
    sh = dict({"shot_id": "X1", "route": "still_25d", "target_duration_seconds": 4.0, "audio_line_ids": ["L1"]}, **kw)
    return sh, {"shots": [sh], "audio_lines": lines}


def _spine(words: int, frames: int, k: float) -> list[dict]:
    names = "the mountain wakes and the sky turns black over the valley".split()
    return [{"word": names[i], "start_frame": int(round((4 + 8 * i) * k))} for i in range(words)]


@pytest.mark.parametrize("k", [1.0, 0.75, 0.5])
def test_a_word_anchored_sound_event_lands_on_its_word_at_every_speed(k):
    """FA-06: ``at_word`` (a phrase, or {line_id, word, offset_s}) resolves on the measured spine of the read."""
    sh, doc = _shot(sound_events=[{"kind": "spot", "what": "eruption_boom", "class": "eruption_boom", "at_word": "wakes"},
                                  {"kind": "spot", "what": "thunder", "at_word": {"line_id": "L1", "word": 6, "offset_s": 0}}])
    sh["target_duration_seconds"] = round(4.0 * k, 3)
    spine = _spine(11, int(4.0 * k * FPS), k)
    f_wakes, how = E.sound_event_frame(sh, doc, sh["sound_events"][0], spine, FPS)
    assert how == "measured:word" and f_wakes == spine[2]["start_frame"]
    f_turns, _ = E.sound_event_frame(sh, doc, sh["sound_events"][1], spine, FPS)
    assert f_turns == spine[6]["start_frame"]
    evs, _ = SP.shot_events(sh, doc, FPS, "late_pleistocene", spine)
    boom = next(e for e in evs if e["class"] == "eruption_boom")
    assert boom["at_frame"] == f_wakes


def test_both_at_s_and_at_word_is_refused_and_the_schema_says_so():
    sh, doc = _shot(sound_events=[{"kind": "spot", "what": "thunder", "at_s": 1.0, "at_word": "wakes"}])
    with pytest.raises(ContractError, match="exactly one"):
        E.sound_event_frame(sh, doc, sh["sound_events"][0], None, FPS)
    import jsonschema
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text())
    item = dict(schema["$defs"]["ShotSpec"]["properties"]["sound_events"]["items"], **{"$defs": schema["$defs"]})
    v = jsonschema.Draft202012Validator(item)
    assert not list(v.iter_errors({"kind": "spot", "what": "thunder", "at_word": {"line_id": "L1", "word": 2}}))
    assert list(v.iter_errors({"kind": "spot", "what": "thunder", "at_s": 1.0, "at_word": "wakes"}))


@pytest.mark.parametrize("dur", [4.0, 2.0, 1.4])
def test_a_fraction_anchored_camera_segment_keeps_its_share(dur):
    """FA-06: from_frac / to_frac are shares of the (retimed) shot: the second segment keeps its place at every length."""
    mi = [{"effect": "push", "from_frac": 0.0, "to_frac": 0.5, "event_id": "X1.c1"},
          {"effect": "orbit_small", "from_frac": 0.6, "to_frac": 1.0, "event_id": "X1.c2"},
          {"effect": "embers", "region": [0.1, 0.6, 0.5, 1.0]}, {"effect": "fire_flicker", "region": [0.1, 0.5, 0.6, 1.0]}]
    sh, doc = _shot(motion_imitation=mi, target_duration_seconds=dur)
    frames = int(round(dur * FPS))
    p = L25.plan(sh, FPS, script=doc)
    a, b = p["cameras"]
    assert (a["from"], a["to"]) == (0, int(round(0.5 * frames))) and (b["from"], b["to"]) == (int(round(0.6 * frames)), frames)
    assert all(r["status"] == G.PASS for r in E.anchor_rows(doc, None, FPS))


def test_a_picture_sound_event_goes_through_the_resolver_and_is_placed_once():
    """FA-10: the eruption that shakes the 2.5D picture is a resolved event (source sound_events) in the event report and the
    renderer's impacts; the sound plan places its sound once."""
    sh, doc = _shot(sound_events=[{"kind": "spot", "what": "eruption_boom", "at_word": "wakes", "picture_event": "eruption",
                                   "event_id": "X1.boom"}],
                    motion_imitation=[{"effect": "push"}, {"effect": "smoke_drift", "region": [0, 0, 1, 0.5]},
                                      {"effect": "ash_fall"}])
    evs = E.visual_events(sh, doc, None, FPS)
    pic = [e for e in evs if e["source"] == "sound_events"]
    assert len(pic) == 1 and pic[0]["event_id"] == "X1.boom" and pic[0]["picture_event"] == "eruption"
    p = L25.plan(sh, FPS, script=doc)
    assert any(i["kind"] == "eruption" and i["frame"] == pic[0]["start_frame"] for i in p["impacts"])
    placed, _ = SP.shot_events(sh, doc, FPS, "late_pleistocene")
    assert sum(1 for e in placed if e["class"] == "eruption_boom") == 1
    rep = E.events_report(doc, None, FPS)
    assert "X1.boom" in [e["event_id"] for e in rep["shots"]["X1"]["events"]]
    import inspect
    assert "at_s" not in inspect.getsource(L25.plan).split("if events is None")[1].split("for ev in events")[0]


def test_g1_lists_absolute_anchors_of_a_locked_script_as_review():
    """FA-06 at G1: with av_contract an at_s / at_frame / from_frame / to_frame under a read line is REVIEW; an older script
    is not checked."""
    sh, doc = _shot(sound_events=[{"kind": "spot", "what": "thunder", "at_s": 1.0}],
                    motion_imitation=[{"effect": "push", "from_frame": 0, "to_frame": 40}])
    assert E.absolute_anchor_rows(doc) == []
    doc["av_contract"] = E.CONTRACT
    row = E.absolute_anchor_rows(doc)[0]
    assert row["status"] == G.REVIEW and row["measured"] == ["X1.sound_events[0].at_s", "X1.motion_imitation[0].from_frame",
                                                             "X1.motion_imitation[0].to_frame"]
    import inspect
    from explainer_engine.episode import run as RUN
    assert "absolute_anchor_rows" in inspect.getsource(RUN.stage_script)
    assert "_anchor_rows(ep, timing)" in inspect.getsource(RUN.stage_voice)
    assert "_anchor_rows(ep, timing)" in inspect.getsource(RUN._voice_with_clips)
