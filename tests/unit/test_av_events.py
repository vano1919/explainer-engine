"""The unified audiovisual event contract (D-135, AV-01..AV-08 in docs/EPISODE_FIRST.md): one resolver for maps, 2.5D, the
sound plan and QA; words are candidates only; every visible event carries one audio decision and its id into the cue sheet and
the stems; BP-54/55/56/81 measured on the active path; the clip cache keys on everything a clip is made from; W3 map motion and
W2 2.5D camera segments. Layers A-F of the brief: A resolver, B sound plan, C cue sheet and stems, D cache, E maps, F 2.5D."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import sfx_library, stems
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import av_report as AVR
from explainer_engine.episode import cue_sheet as CS
from explainer_engine.episode import events as E
from explainer_engine.episode import sound_plan as SP
from explainer_engine.maps import actions as MA
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.production import layers25d as L
from explainer_engine.qa import gates as G

FPS = 24
SR = 48000
PLACES = {"toba": {"lon": 98.88, "lat": 2.68, "name": "Toba"}, "shinfa": {"lon": 36.0, "lat": 12.8, "name": "Shinfa-Metema"},
          "india": {"lon": 78.1, "lat": 15.3, "name": "Jwalapuram"}, "aden": {"lon": 45.0, "lat": 12.8, "name": "Aden"}}


def _map(text="The band walks from the lake to the river and on to the coast.", dur=5.0, actions=None, **kw):
    shot = dict({"shot_id": "M1", "segment_id": "S01", "route": "map_action", "target_duration_seconds": dur,
                 "audio_line_ids": ["L1"], "location_id": "loc_map", "actions": actions or []}, **kw)
    return shot, {"episode_id": "ep_t", "historical_period": "prehistoric_pleistocene", "segments": [{"segment_id": "S01"}],
                  "audio_lines": [{"line_id": "L1", "text": text}], "shots": [shot]}


# --- A: the resolver ---------------------------------------------------------------------------------------------------

def test_events_are_half_open_integer_spans_on_the_word_clock():
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "until_word": "river", "from": "toba",
                                  "to": "shinfa"},
                                 {"kind": "pulse", "at_word": "coast", "from": "shinfa"}])
    words = MA.shot_words(shot, script)
    spine = [{"word": w, "start_frame": 6 * i} for i, w in enumerate(words)]
    evs = {e["event_id"]: e for e in E.visual_events(shot, script, spine, FPS)}
    a, b = evs["M1.A1"], evs["M1.A2"]
    derived = [e for e in evs.values() if e["source"] == "derived"]
    assert all(isinstance(e["start_frame"], int) and isinstance(e["end_frame"], int) for e in (a, b))
    assert a["start_frame"] == 6 * words.index("walks")
    assert a["end_frame"] == 6 * (words.index("river") + 1)     # the start of the word after the phrase: [start, end)
    assert a["timing"] == {"start": "measured:word", "end": "measured:until_word"}
    assert b["start_frame"] == 6 * words.index("coast") and b["end_frame"] == b["start_frame"] + E.ANIM_FRAMES
    assert a["event_id"] == "M1.A1" and a["id_basis"] == "derived" and a["audio_basis"] == "default"
    assert a["audio"] == {"decision": "sfx", "class": "map_route_draw", "sync": "span", "purpose": "clarify"}
    assert {d["event_id"] for d in derived} == {"M1.A1.arrive"}     # no start cue: the draw sound starts the line (BP-81)


def test_a_continuous_action_lasts_until_the_next_one_and_an_instant_one_a_beat():
    shot, script = _map(actions=[{"kind": "counter", "at_word": "band", "value": 2000, "unit": "people", "claim": "C-01"},
                                 {"kind": "label", "at_word": "coast", "from": "shinfa"}])
    evs = {e["event_id"]: e for e in E.visual_events(shot, script, None, FPS)}
    c, lab = evs["M1.A1"], evs["M1.A2"]
    assert c["end_frame"] == lab["start_frame"] and c["timing"]["end"] == "next_action"
    assert "M1.A1.done" not in evs           # a counted number with its riser takes no second confirmation (BP-81)
    assert lab["audio"]["decision"] == "silent_by_design" and lab["audio"]["why"]
    shot["actions"][0]["audio"] = {"decision": "ui_cue", "class": "data_tick", "sync": "onset", "purpose": "clarify"}
    done = {e["event_id"]: e for e in E.visual_events(shot, script, None, FPS)}["M1.A1.done"]
    assert done["audio"]["class"] == "data_confirm" and done["start_frame"] == c["end_frame"] - 1


def test_actions_keep_the_cursor_and_motion_items_search_from_the_first_word():
    shot, script = _map(text="the lake and the lake again", actions=[{"kind": "pulse", "at_word": "lake", "from": "toba"},
                                                                    {"kind": "pulse", "at_word": "lake", "from": "toba"}])
    a, b = [e for e in E.visual_events(shot, script, None, FPS) if e["source"] == "actions"]
    assert a["start_frame"] == b["start_frame"]                # the cursor stays on the hit, as maps/actions always did
    shot2 = {"shot_id": "P1", "target_duration_seconds": 3.0, "audio_line_ids": ["L1"],
             "motion_imitation": [{"effect": "push"}, {"effect": "shake", "at_word": "again"}]}
    script2 = {"audio_lines": [{"line_id": "L1", "text": "the lake and the lake again"}], "shots": [shot2]}
    push, shake = E.visual_events(shot2, script2, None, FPS)
    assert push["start_frame"] == 0 and push["end_frame"] == 72 and push["audio"]["decision"] == "silent_by_design"
    assert shake["audio"]["class"] == "impact" and shake["start_frame"] > 0


def test_a_locked_script_needs_ids_and_audio_and_an_old_one_is_reported():
    shot, script = _map(actions=[{"kind": "pulse", "at_word": "lake", "from": "toba"}])
    rows = {r["gate"]: r for r in E.contract_rows(script, set(SP.EVENT_CLASSES))}
    assert rows["av_contract_complete"]["status"] == G.REVIEW
    script["av_contract"] = E.CONTRACT
    assert {r["gate"]: r for r in E.contract_rows(script)}["av_contract_complete"]["status"] == G.FAIL
    shot["actions"][0].update(event_id="EV1", audio={"decision": "ui_cue", "class": "map_pin_set", "sync": "onset",
                                                      "purpose": "clarify"})
    rows = {r["gate"]: r for r in E.contract_rows(script, set(SP.EVENT_CLASSES))}
    assert rows["av_contract_complete"]["status"] == G.PASS and rows["av_audio_decisions"]["status"] == G.PASS


@pytest.mark.parametrize("audio, gate", [
    ({"decision": "sfx", "sync": "onset"}, "av_audio_decisions"),                       # sfx without a class
    ({"decision": "silent_by_design", "sync": "onset"}, "av_audio_decisions"),          # silence without a reason
    ({"decision": "loud", "sync": "onset"}, "av_audio_decisions"),
    ({"decision": "sfx", "class": "map_route_draw", "sync": "onset"}, "av_audio_decisions"),   # continuous needs a span
    ({"decision": "review_required", "why": "no snap take yet", "sync": "onset"}, "av_audio_review"),
])
def test_bad_decisions_are_rows_not_silence(audio, gate):
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "from": "toba", "to": "shinfa", "event_id": "R",
                                  "audio": audio}])
    rows = {r["gate"]: r for r in E.contract_rows(script, set(SP.EVENT_CLASSES))}
    assert rows[gate]["status"] in (G.FAIL, G.REVIEW) and rows[gate]["status"] != G.PASS


def test_a_marker_riding_its_route_shares_the_route_sound():
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "from": "toba", "to": "shinfa", "event_id": "R1"},
                                 {"kind": "marker_travel", "at_word": "walks", "route": "R1"}])
    evs = {e["event_id"]: e for e in E.visual_events(shot, script, None, FPS)}
    m = evs["M1.A2"]
    assert m["audio"]["decision"] == "silent_by_design" and "R1" in m["audio"]["why"]
    assert "M1.A2.arrive" not in evs and "R1.arrive" in evs


def test_the_report_hashes_the_spine_and_the_events():
    shot, script = _map(actions=[{"kind": "pulse", "at_word": "lake", "from": "toba"}])
    words = MA.shot_words(shot, script)
    sp1 = {"M1": [{"word": w, "start_frame": 5 * i} for i, w in enumerate(words)]}
    sp2 = {"M1": [{"word": w, "start_frame": 6 * i} for i, w in enumerate(words)]}
    r1, r2 = E.events_report(script, sp1, FPS), E.events_report(script, sp2, FPS)
    assert r1["shots"]["M1"]["spine_sha"] != r2["shots"]["M1"]["spine_sha"]
    assert r1["shots"]["M1"]["events_sha"] != r2["shots"]["M1"]["events_sha"]
    assert r1["shots"]["M1"]["spine_basis"] == "measured" and r1["decisions"] == {"ui_cue": 1}


# --- B: the sound plan -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["The empire falls.", "In March.", "People moved into the region.", "The army was fired up.",
                                  "The commander was in charge."])
def test_words_never_make_a_sound_or_move_the_picture(text):
    # the picture shows everything the words could ask for: still nothing is placed
    shot = {"shot_id": "W1", "segment_id": "S01", "route": "still_25d", "target_duration_seconds": 3.0,
            "location_id": "loc_plain", "audio_line_ids": ["L1"],
            "action_start_state": "the army of soldiers and people charge, a fire burns, the wall falls, troops march",
            "motion_imitation": [{"effect": "push"}, {"effect": "dust"}, {"effect": "smoke_drift"}]}
    script = {"episode_id": "ep_t", "historical_period": "napoleonic_1815", "segments": [{"segment_id": "S01"}],
              "audio_lines": [{"line_id": "L1", "text": text}], "shots": [shot]}
    plan = SP.build(script, fps=FPS)
    s = plan["shots"][0]
    point = [e for e in s["events"] if e["kind"] != "ambience"]
    assert not point, point
    assert not any(e.get("picture_event") for e in s["events"])
    assert {e["basis"] for e in s["events"]} <= {"picture:dust", "picture:smoke_drift"}   # the picture's bed, not the words
    lp = L.plan(shot, FPS, None, script)
    assert not lp["impacts"]                                     # nothing shakes, nothing flashes
    from explainer_engine.episode.run import _events_for_picture
    assert _events_for_picture(s) == []


def test_a_map_route_has_its_draw_and_arrival_sounds_on_their_frames():
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "until_word": "coast", "from": "toba",
                                  "to": "shinfa"}])
    plan = SP.build(script, fps=FPS)
    evs = {e["event_id"]: e for e in plan["shots"][0]["events"]}
    draw, arrive = evs["M1.A1"], evs["M1.A1.arrive"]
    assert draw["class"] == "map_route_draw" and draw["sync"] == "span" and draw["dur_s"] > 1.0
    assert "M1.A1.start" not in evs and arrive["decision"] == "ui_cue"
    assert arrive["at_frame"] == draw["span_frames"][1] - 1
    assert plan["av"]["decisions"]["sfx"] == 1 and plan["av"]["candidates"] == 0     # a map takes no word candidates


def _lib(root, classes, secs=0.6, lead=0.0):
    rng = np.random.default_rng(3)
    items = []
    (root / "foley").mkdir(parents=True, exist_ok=True)
    for cls in classes:
        for k in range(3):
            iid = f"{cls}_{k}__v1"
            x = (rng.standard_normal(int(SR * secs)) * 0.2).astype(np.float32)
            x[: int(SR * lead)] = 0.0
            (root / f"foley/{iid}.wav").write_bytes(sfx_library.wav_bytes(x, SR))
            items.append({"id": iid, "file": f"foley/{iid}.wav", "category": "foley", "tags": SP.EVENT_CLASSES[cls]["tags"],
                          "kind": "loop" if SP.EVENT_CLASSES[cls]["kind"] == "ambience" or cls == "music_bed" else "one_shot",
                          "source": {"kind": "third_party"}, "review": {"human": "not_listened"},
                          "licence": {"status": "licensed", "production": "verified"}})
    (root / "manifest.json").write_text(json.dumps({"version": 1, "items": items}))
    return root


def test_the_event_id_reaches_the_cue_sheet_the_stems_and_the_report(tmp_path):
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "until_word": "coast", "from": "toba",
                                  "to": "shinfa"}])
    plan = SP.build(script, fps=FPS)
    lib = _lib(tmp_path / "lib", plan["classes"], lead=0.12)
    src = SP.resolve(plan, lib)
    assert src["map_route_draw"]["match"] == "legacy_tags" and src["map_route_draw"]["human"] == {"not_listened": 3}
    rep = stems.render(plan, src, tmp_path / "stems", library_root=lib, shippable=False)
    sheet = json.loads((tmp_path / "stems" / "cue_sheet.json").read_text())
    rows = {r["event_id"]: r for r in sheet["rows"] if r.get("event_id")}
    assert {"M1.A1", "M1.A1.arrive"} <= set(rows)
    for eid in ("M1.A1", "M1.A1.arrive"):    # the take's lead-in is skipped, for a one-shot and for a take a span repeats
        assert rows[eid]["asset_offset_s"] == pytest.approx(0.12, abs=0.006)
    assert rows["M1.A1"]["loop"] is True and rows["M1.A1"]["fade_in_s"] <= 0.011   # the draw lasts its span, from its frame
    placed = {p["event_id"]: p for p in rep["events_placed"] if p.get("event_id")}
    for eid in ("M1.A1", "M1.A1.arrive"):
        assert placed[eid]["onset_s"] == pytest.approx(rows[eid]["start_s"], abs=0.011)
    gates = {r["gate"]: r["status"] for r in rep["cue_rows"]}
    assert gates["events_on_sync"] == G.PASS and gates["events_on_the_frame"] == G.PASS
    doc = E.events_report(script, None, FPS)
    av = AVR.event_report(doc, plan, sheet, rep)
    byid = {e["event_id"]: e for e in av["events"]}
    assert byid["M1.A1"]["onset_off_ms"] is not None and abs(byid["M1.A1"]["onset_off_ms"]) <= 1000 / FPS
    assert all(e["human"] == "not_listened" for e in av["events"])
    tl = AVR.timeline(plan, [{"duration_sec": 5.0}], rep)
    assert tl["events"] and all(e["event_id"] for e in tl["events"])


def test_a_missing_class_is_review_required_never_a_substitute(tmp_path):
    shot, script = _map(actions=[{"kind": "supply_line", "at_word": "walks", "from": "toba", "to": "shinfa", "event_id": "SL",
                                  "cues": "none"},
                                 {"kind": "snap", "at_word": "coast", "route": "SL"}])
    plan = SP.build(script, fps=FPS)
    lib = _lib(tmp_path / "lib", [c for c in plan["classes"] if c != "map_line_snap"])
    src = SP.resolve(plan, lib)
    assert src["map_line_snap"]["status"] == "missing"
    sheet = CS.build(plan, src, lib, allow_placeholder=False)
    assert not any(r.get("class") == "map_line_snap" for r in sheet["rows"])
    miss = [m for m in sheet["missing"] if m.get("event_id") == "M1.A2"]
    assert miss and miss[0]["status"] == "review_required"
    gate = {r["gate"]: r for r in CS.validate(sheet, plan, lib)["rows"]}
    assert gate["review_required_events"]["status"] == G.REVIEW and "M1.A2" in gate["review_required_events"]["measured"]


# --- C: the cue sheet rules ------------------------------------------------------------------------------------------

def _sheet_with(rows, dur=60.0, shots=None):
    return {"rows": rows, "duration_s": dur, "missing": [], "shots": shots or []}


def _fx(cue, start, end, cls="map_pin_set", eid=None, decision="ui_cue", layer="foley", shot="S"):
    return {"cue_id": cue, "event_id": eid, "decision": decision, "purpose": "clarify", "class": cls, "layer": layer,
            "start_s": start, "end_s": end, "shot_id": shot, "asset_id": "x"}


@pytest.mark.parametrize("off_ms, status", [(0, G.PASS), (30, G.PASS), (80, G.REVIEW), (-30, G.PASS), (-60, G.FAIL),
                                            (150, G.FAIL)])
def test_bp54_has_three_bands_on_the_measured_onset(off_ms, status):
    plan = {"fps": 24, "shots": [{"shot_id": "S", "start_s": 0.0, "dur_s": 4.0,
                                  "events": [{"event_id": "E1", "at_frame": 24, "class": "map_pin_set"}]}]}
    rows = [_fx("C1", 1.0, 1.2, eid="E1")]
    out = {r["gate"]: r["status"] for r in CS.sync_rows(rows, plan, {"C1": 1.0 + off_ms / 1000.0})}
    fail_status = out["events_on_sync"]
    review_status = out["events_on_the_frame"]
    got = G.FAIL if fail_status == G.FAIL else (G.REVIEW if review_status == G.REVIEW else G.PASS)
    assert got == status


def test_bp56_counts_from_intervals_with_the_voice_music_and_bed_once():
    rows = [_fx(f"C{i}", 1.0 + 0.1 * i, 3.0, cls="data_tick") for i in range(3)]
    assert {r["gate"]: r for r in CS.overlap_rows(rows)}["overlap"]["status"] != G.PASS    # three of one class at once
    rows = [_fx("A", 1.0, 2.0, cls="a"), _fx("B", 1.5, 2.5, cls="b")]
    rows += [{"cue_id": "N", "layer": "narration", "start_s": 0, "end_s": 5, "asset_id": "narration:L1", "class": None},
             {"cue_id": "M", "layer": "music", "start_s": 0, "end_s": 5, "asset_id": "m", "class": "music_bed"},
             {"cue_id": "B1", "layer": "ambience", "start_s": 0, "end_s": 5, "asset_id": "w", "class": "wind"},
             {"cue_id": "B2", "layer": "ambience", "start_s": 0, "end_s": 5, "asset_id": "f", "class": "fire"},
             {"cue_id": "T", "layer": "ambience", "start_s": 0, "end_s": 5, "asset_id": "room_tone:outdoor", "class": "room_tone"}]
    assert CS.overlap_rows(rows)[0]["status"] == G.PASS                                  # 2 fx + voice + music + bed = 5
    rows.append(_fx("C", 1.6, 1.9, cls="c"))
    assert CS.overlap_rows(rows)[0]["status"] != G.PASS                                  # six layers


def test_bp55_share_and_bp81_bursts():
    plan = {"fps": 24, "shots": [{"shot_id": "S", "start_s": 0.0, "dur_s": 60.0, "audio_line_ids": ["L1"],
                                  "visual_events": [{"event_id": f"E{i}", "op": "pulse", "decision": "sfx"} for i in range(3)]
                                  + [{"event_id": "E9", "op": "label", "decision": "silent_by_design"}]}]}
    cues = [_fx(f"Q{i}", 10.0 + i, 10.2 + i, cls="data_tick", eid=f"Q{i}") for i in range(4)]
    out = {r["gate"]: r for r in CS.av_rows(cues, plan, _sheet_with(cues))}
    assert out["purpose_and_share"]["status"] == G.REVIEW and out["purpose_and_share"]["measured"] == 0.75
    assert out["cue_rate_review"]["status"] == G.REVIEW and out["cue_rate_review"]["measured"]["burst"] == 4
    assert out["cue_density"]["status"] == G.PASS


# --- D: the clip cache ------------------------------------------------------------------------------------------------

def test_the_clip_key_changes_with_every_input(tmp_path):
    from explainer_engine.episode import run as RUN
    (tmp_path / "story").mkdir()
    shot, script = _map(actions=[{"kind": "pulse", "at_word": "lake", "from": "toba"}])
    (tmp_path / "episode.json").write_text(json.dumps({"episode_id": "ep_t"}))
    (tmp_path / RUN.SCRIPT_REL).write_text(json.dumps(script))
    ep = RUN.Episode(tmp_path)
    evs = E.visual_events(shot, script, None, FPS)
    pic = {"file": "a.jpg", "sha256": "1" * 64}
    base = RUN._clip_key(shot, [pic, None], ep, None, evs, MA.RENDERER_VERSION)
    assert base == RUN._clip_key(shot, [pic, None], ep, None, evs, MA.RENDERER_VERSION)
    spine = [{"word": w, "start_frame": i} for i, w in enumerate(MA.shot_words(shot, script))]
    changed = [RUN._clip_key(shot, [dict(pic, sha256="2" * 64), None], ep, None, evs, MA.RENDERER_VERSION),
               RUN._clip_key(shot, [pic, None], ep, spine, evs, MA.RENDERER_VERSION),
               RUN._clip_key(shot, [pic, None], ep, None, evs[:0], MA.RENDERER_VERSION),
               RUN._clip_key(shot, [pic, None], ep, None, evs, "map_action/1"),
               RUN._clip_key(dict(shot, motion_profile="document"), [pic, None], ep, None, evs, MA.RENDERER_VERSION)]
    assert len({base, *changed}) == 6


# --- E: maps (W3) -----------------------------------------------------------------------------------------------------

def test_a_via_route_is_a_spline_through_its_waypoints_and_the_marker_shares_its_progress():
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "from": "toba", "via": ["india"], "to": "shinfa",
                                  "event_id": "R1", "domain": "maritime"},
                                 {"kind": "marker_travel", "at_word": "river", "route": "R1"}])
    p = MA.plan(shot, script, PLACES, FPS)
    r, m = p["actions"]
    assert r["path"][0] == (98.88, 2.68) and r["path"][-1] == (36.0, 12.8)
    assert min(abs(x - 78.1) + abs(y - 15.3) for x, y in r["path"]) < 1e-6        # passes through the waypoint
    assert m["path"] is r["path"]
    for f in range(m["start"], m["end"]):
        assert MA._head(p, r, f) >= MA._progress(m, f) - 1e-9                     # the line is never behind its marker


def test_a_supply_line_strains_and_breaks_on_its_events(tmp_path):
    shot, script = _map(actions=[{"kind": "supply_line", "at_word": "band", "from": "toba", "to": "shinfa", "event_id": "SL"},
                                 {"kind": "supply_state", "at_word": "river", "route": "SL", "state": "strained"},
                                 {"kind": "snap", "at_word": "coast", "route": "SL"}],
                        map_view={"lon": 67.0, "lat": 9.0, "span_km": 9500}, dur=6.0)
    p = MA.plan(shot, script, PLACES, FPS)
    sl, st, sn = p["actions"]
    assert MA.supply_state(p, sl, st["start"] - 1)[0] == "active"
    assert MA.supply_state(p, sl, st["start"] + 1)[0] == "strained"
    assert MA.supply_state(p, sl, sn["end"])[0] == "cut"
    view = geo.View(67.0, 9.0, 9500, 320, 180)
    px = [tuple(float(v) for v in view.to_px(*q)) for q in sl["path"]]

    def alpha_near_the_break(f):
        c = D.Canvas(320, 180, None, 1)
        MA._draw_one(c, sl, p, f, view, MA.colours(), (0, 0, 0, 255), (255, 0, 0, 255),
                     lambda ll: tuple(float(v) for v in view.to_px(*ll)), 180)
        al = np.asarray(c.im)[..., 3]
        out = []
        for t in (0.46, 0.54):          # inside the 7 % gap, clear of the X drawn on the break itself
            x, y = (int(round(v)) for v in D.polyline_point(px, t))
            out.append(int(al[y - 1:y + 2, x - 1:x + 2].max()))
        return out
    assert min(alpha_near_the_break(sn["start"] - 1)) > 0        # the line is there before the snap
    assert max(alpha_near_the_break(sn["end"])) == 0              # and the gap is open after it


@pytest.mark.parametrize("act, match", [
    ({"kind": "counter", "at_word": "band"}, "never invented"),
    ({"kind": "bar_grow", "at_word": "band", "values": [1, "x"]}, "never invented"),
    ({"kind": "progress_bar", "at_word": "band", "value": 4}, "max"),
    ({"kind": "snap", "at_word": "band"}, "supply line"),
    ({"kind": "marker_travel", "at_word": "band"}, "from and to"),
    ({"kind": "pulse", "at_word": "band", "from": "toba", "camera": "spin"}, "camera"),
])
def test_map_numbers_and_rides_need_their_data(act, match):
    shot, script = _map(actions=[act])
    with pytest.raises(ContractError, match=match):
        MA.plan(shot, script, PLACES, FPS)


def test_the_camera_drifts_answers_a_push_and_a_dense_map_holds():
    shot, script = _map(actions=[{"kind": "pulse", "at_word": "lake", "from": "toba", "camera": "push"}],
                        map_view={"lon": 67.0, "lat": 9.0, "span_km": 9000})
    p = MA.plan(shot, script, PLACES, FPS)
    a = p["actions"][0]
    v0, v1 = MA.camera(p, 0), MA.camera(p, p["frames"] - 1)
    assert v0 == p["view0"] and v1["span_km"] < 9000 * MA.CAM_PUSH * 1.0001
    p["dense"] = True
    assert MA.camera(p, p["frames"] - 1)["span_km"] == pytest.approx(9000 * (1 - MA.DRIFT))
    assert a["camera"] == "push"


def test_bars_progress_and_milestones_draw_on_their_frames_and_repeat():
    shot, script = _map(actions=[{"kind": "bar_grow", "at_word": "band", "values": [70, 2], "labels": ["before", "after"],
                                  "claim": "C-01"},
                                 {"kind": "progress_bar", "at_word": "river", "value": 60, "max": 100, "claim": "C-02"},
                                 {"kind": "milestone", "at_word": "coast", "value": 30, "label": "half", "claim": "C-02"}])
    p = MA.plan(shot, script, PLACES, FPS)
    assert p["card"]
    base = MA.card_base(320, 180)
    for a in p["actions"]:
        before = np.asarray(MA.render_frame(p, a["start"] - 1, base, 320, 180, ss=1), np.int16)
        after = np.asarray(MA.render_frame(p, a["end"], base, 320, 180, ss=1), np.int16)
        assert (np.abs(after - before).max(axis=2) > 12).mean() > 0.001, a["kind"]
        assert (after == np.asarray(MA.render_frame(p, a["end"], base, 320, 180, ss=1), np.int16)).all()


# --- F: 2.5D (W2) -----------------------------------------------------------------------------------------------------

@pytest.fixture()
def pic(tmp_path):
    h, w = 270, 480
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(7)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = [90, 120, 170]
    img[yy >= 150] = [120, 95, 60]
    img = np.clip(img + rng.integers(0, 40, (h, w, 1)), 0, 255).astype(np.uint8)
    depth = np.where(yy >= 150, 0.3 + 0.6 * (yy - 150) / 120, 0.05).astype(np.float32)
    path = tmp_path / "pic.png"
    Image.fromarray(img).save(path)
    return path, depth


def test_two_camera_segments_add_up_without_a_jump():
    shot = {"shot_id": "C2", "target_duration_seconds": 3.0, "motion_imitation": [
        {"effect": "push", "from_frame": 0, "to_frame": 30, "easing": "ease_out", "hold_frames": 6},
        {"effect": "truck", "from_frame": 36, "to_frame": 72, "direction": "left"}]}
    p = L.plan(shot, FPS)
    assert [c["move"] for c in p["cameras"]] == ["push", "truck"] and p["camera"]["move"] == "push"
    views = [L.plane_view(p, f, 1.0, 0.5) for f in range(p["frames"])]
    for a, b in zip(views, views[1:]):
        assert abs(a["scale"] - b["scale"]) < 0.01 and abs(a["cx"] - b["cx"]) < 0.005
    assert views[33] == views[35]                                   # the hold rests
    assert views[-1]["cx"] < 0 and views[-1]["scale"] > 1.05


@pytest.mark.parametrize("mi, profile, match", [
    ([{"effect": "push", "from_frame": 0, "to_frame": 40}, {"effect": "truck", "from_frame": 30, "to_frame": 60}], None,
     "before"),
    ([{"effect": "push"}, {"effect": "truck"}], None, "need their frames"),
    ([{"effect": "push", "from_frame": 0, "to_frame": 10}, {"effect": "pull", "from_frame": 10, "to_frame": 20},
      {"effect": "truck", "from_frame": 20, "to_frame": 30}], None, "at most 2"),
    ([{"effect": "orbit_small"}], "document", "does not move by"),
    ([{"effect": "cloth_flap"}], None, "needs a region"),
    ([{"effect": "cloud_drift"}], None, "needs a region"),
])
def test_segments_and_profiles_refuse_what_does_not_fit(mi, profile, match):
    shot = {"shot_id": "X", "target_duration_seconds": 3.0, "motion_imitation": mi}
    if profile:
        shot["motion_profile"] = profile
    with pytest.raises(ContractError, match=match):
        L.plan(shot, FPS)


def test_a_profile_caps_strength_and_sets_the_far_share():
    p = L.plan({"shot_id": "D", "target_duration_seconds": 2.0, "motion_profile": "document",
                "motion_imitation": [{"effect": "truck", "strength": 1.4}, {"effect": "handheld", "strength": 1.0}]}, FPS)
    assert p["cameras"][0]["strength"] == 1.0 and p["capped"] and p["far_share"] == 0.85 and p["handheld"] == 0.2


@pytest.mark.parametrize("effect, region", [("cloth_flap", [0.55, 0.05, 0.95, 0.45]), ("cloud_drift", [0.0, 0.0, 1.0, 0.4])])
def test_cloth_and_clouds_move_inside_their_region(pic, effect, region):
    path, depth = pic
    p = L.plan({"shot_id": "F", "target_duration_seconds": 2.0, "motion_imitation": [{"effect": effect, "region": region}]},
               FPS)
    sc = L.Scene(Image.open(path), p, (320, 180), depth, "given", [], "given")
    # frames 0 and 10: the flag's waves repeat every 0.625 s, so a frame 1.25 s later would look like frame 0 again
    a, b = L.render_frame(sc, 0).astype(np.int16), L.render_frame(sc, 10).astype(np.int16)
    moved = np.abs(a - b).max(axis=2).astype(np.float32)
    x0, y0, x1, y1 = region
    inside = moved[int(y0 * 180):int(y1 * 180), int(x0 * 320):int(x1 * 320)].mean()
    outside = moved[int(0.75 * 180):, :].mean()
    assert inside > 0.5 and inside > 4 * outside, (inside, outside)
    assert effect in [e["effect"] for e in p["effects"]] and p["families"]
    assert (L.render_frame(sc, 10) == L.render_frame(L.Scene(Image.open(path), p, (320, 180), depth, "given", [], "given"),
                                                     10)).all()


def test_a_shot_under_a_second_keeps_its_own_frames():
    """The pilot's regression: a Wan fallback of 20 frames (0.83 s) got event frames of a one-second map shot ([0, 24))."""
    shot = {"shot_id": "W", "target_duration_seconds": 20 / FPS, "motion_imitation": [{"effect": "push"}]}
    p = L.plan(shot, FPS)
    assert p["frames"] == 20 and (p["cameras"][0]["from"], p["cameras"][0]["to"]) == (0, 20)
    m, s = _map(dur=20 / FPS, actions=[{"kind": "pulse", "at_word": "lake", "from": "toba"}])
    assert MA.plan(m, s, PLACES, FPS)["frames"] == FPS          # a map keeps its one-second floor


def test_an_authored_sound_event_keeps_its_id_purpose_and_class_id():
    shot = {"shot_id": "E1", "segment_id": "S01", "route": "still_25d", "target_duration_seconds": 3.0, "location_id": "x",
            "audio_line_ids": ["L1"], "motion_imitation": [{"effect": "push"}],
            "sound_events": [{"kind": "spot", "what": "eruption_boom", "at_s": 1.0, "picture_event": "eruption"},
                             {"kind": "spot", "what": "thunder", "at_s": 2.0, "event_id": "T1", "purpose": "transition"}]}
    script = {"episode_id": "ep_t", "historical_period": "prehistoric_pleistocene", "segments": [{"segment_id": "S01"}],
              "audio_lines": [{"line_id": "L1", "text": "A quiet sea."}], "shots": [shot]}
    evs = {e["event_id"]: e for e in SP.build(script, fps=FPS)["shots"][0]["events"] if e.get("event_id")}
    assert evs["E1.S1"]["class"] == "eruption_boom" and evs["E1.S1"]["purpose"] == "sync"     # a class id names its class
    assert evs["T1"]["purpose"] == "transition" and evs["T1"]["audio_basis"] == "authored"


def test_a_take_with_a_declared_onset_starts_before_its_frame_so_the_onset_meets_it(tmp_path):
    """TD-330: the library record may carry the take's measured onset (``onset_s``). A one-shot with it is placed that much earlier
    (never before 0), played once from its head, and its onset lands on the event; a take without it is placed as before (the lead
    skipped, at most LEAD_MAX_S)."""
    shot, script = _map(actions=[{"kind": "route_arrow", "at_word": "walks", "until_word": "coast", "from": "toba",
                                  "to": "shinfa"}])
    plan = SP.build(script, fps=FPS)
    lib = _lib(tmp_path / "lib", plan["classes"], secs=2.4, lead=0.8)       # a silent 0.8 s head, over LEAD_MAX_S
    src = SP.resolve(plan, lib)
    st = {}
    for name, declare in (("plain", False), ("declared", True)):
        root = tmp_path / name
        shutil.copytree(lib, root)
        if declare:
            man = json.loads((root / "manifest.json").read_text())
            for it in man["items"]:
                it["onset_s"] = CS.take_onset_s(root / it["file"])
            (root / "manifest.json").write_text(json.dumps(man))
        rep = stems.render(plan, src, tmp_path / f"stems_{name}", library_root=root, shippable=False)
        sheet = json.loads((tmp_path / f"stems_{name}" / "cue_sheet.json").read_text())
        row = next(r for r in sheet["rows"] if r.get("event_id") == "M1.A1.arrive")
        placed = next(p for p in rep["events_placed"] if p.get("event_id") == "M1.A1.arrive")
        st[name] = (row, placed)
    plain, decl = st["plain"][0], st["declared"][0]
    assert plain["asset_offset_s"] == pytest.approx(0.5, abs=0.006) and "take_onset_s" not in plain      # as before
    assert st["plain"][1]["onset_s"] - plain["start_s"] == pytest.approx(0.3, abs=0.02)                  # the rest of the head
    assert decl["take_onset_s"] == pytest.approx(0.8, abs=0.006)
    pre = decl["sync_point_s"] - decl["start_s"]
    assert pre == pytest.approx(min(0.8, decl["sync_point_s"]), abs=0.006)                                # earlier, never before 0
    assert decl["asset_offset_s"] == pytest.approx(0.8 - pre, abs=0.006)
    assert decl["loop"] is False
    assert st["declared"][1]["onset_s"] == pytest.approx(decl["sync_point_s"], abs=0.011)                 # the onset meets the event
