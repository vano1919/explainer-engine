"""The sound director (P4, explainer_engine/audio/sound_director.py): plan and plan-time checks on the shipped Titans episode and on
small synthetic jobs. Free: committed files and numpy only, libraries live in tmp dirs (never the real assets/audio/library)."""

from __future__ import annotations

import copy
import json
import shutil
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio import acoustics as A
from explainer_engine.audio import sfx_library
from explainer_engine.audio import sound_director as D
from explainer_engine.audio import spine as SP
from explainer_engine.core import contracts as C
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
FPS = 50  # 60 ms is exactly three frames


def put(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def ids(findings, sd=None):
    return [f["rule"] for f in findings if sd is None or f["rule"] == sd]


def film_shot(sid, scene, lane, size, place, frames, focal=0.5, sound=None, extra=None):
    d = {"id": sid, "scene": scene, "mode": "scene", "beat": "b", "seconds": frames / FPS, "frame": {"size": size, "place": place},
         "source": "keyframe", "lane": lane, "archetype": "a", "duration_frames": frames, "width": 1920, "height": 1088, "lens_tier": "normal",
         "focal_xy": [focal, 0.5], "continuity_ref": None, "blocking_ref": None}
    if sound:
        d["sound"] = sound
    d.update(extra or {})
    return d


def make_job(tmp_path, *, plan_of=None, nseg=3, seg_s=10.0, speech=(1.0, 6.0), places=None, audio=None, shots=None, native=None,
             timed_shots=None, edit=None, film=True):
    """A job folder: words.json, timed.json, an optional film_shots.json and the compiled audio spine. ``plan_of`` maps a scene id to
    a list of ``(id, lane, size, place, kwargs)`` whose frames split the scene evenly; ``shots`` is a ready list instead."""
    job = tmp_path / "job"
    words, lines, segs = [], [], []
    for k in range(nseg):
        t0 = k * seg_s
        ws = [round(t0 + speech[0] + 0.5 * i, 3) for i in range(int((speech[1] - speech[0]) / 0.5))]
        words += [{"w": "w", "s": w, "e": round(w + 0.4, 3), "para": k} for w in ws]
        lines.append({"segment": f"S{k + 1:02d}", "line": 1, "text": "x", "start": ws[0], "end": round(ws[-1] + 0.4, 3)})
        segs.append({"id": f"S{k + 1:02d}", "start": ws[0], "end": round(ws[-1] + 0.4, 3)})
    dur = nseg * seg_s
    put(job / "words.json", {"words": words, "duration": dur})
    timed = {"schema": "production_timed/1", "fps": FPS, "duration": dur, "frames": int(dur * FPS), "lines": lines, "segments": segs,
             "shots": timed_shots or [], "audio": audio or {"beds": [], "sfx": [], "music": [], "cues": []}}
    put(job / "timed.json", timed)
    refs = {"words": SP._ref(job, job / "words.json"), "timed": SP._ref(job, job / "timed.json")}
    film_doc = None
    if film and (plan_of or shots):
        starts = [0] + [round((k * seg_s + speech[0]) * FPS) for k in range(1, nseg)]
        ends = starts[1:] + [int(dur * FPS)]
        bounds = {f"S{k + 1:02d}": (a, b) for k, (a, b) in enumerate(zip(starts, ends))}
        built = list(shots or [])
        for scene, spec in (plan_of or {}).items():
            a, b = bounds[scene]
            n = len(spec)
            for i, (sid, lane, size, place, kw) in enumerate(spec):
                frames = (b - a) // n + ((b - a) - (b - a) // n * n if i == n - 1 else 0)
                built.append(film_shot(sid, scene, lane, size, place, frames, **kw))
        film_doc = {"schema": "film_shots/2", "episode": "t", "fps": FPS, "style": {"trigger": "x", "video_sentence": "x"},
                    "cast": {"a": {"tag": "t"}}, "places": places or {}, "shots": built}
        put(job / "film_shots.json", film_doc)
        refs["film_shots"] = SP._ref(job, job / "film_shots.json")
    if edit:
        put(job / "audio" / "edit_and_grade_manifest.json", edit)
    spine = SP.compile_spine({"words": words, "duration": dur}, timed, film_shots=film_doc, refs=refs, native=native)
    put(job / "audio" / "audio_spine.json", spine)
    return job, spine


def lib_with(tmp_path, *names):
    """A tmp library holding short real WAVs: name -> tags."""
    root = tmp_path / "lib"
    for name, tags in names:
        sfx_library.add(root, name=name, take=1, category="foley", tags=tags, rate=48000,
                        samples=(np.random.default_rng(1).standard_normal(4800) * 0.2).astype(np.float32),
                        source={"kind": "procedural", "seed": 1}, licence={"status": "own_procedural", "note": "test"})
    return root


def planned(job, root):
    m, rep = D.plan_with_report(job, library=root)
    return m, rep


# --- plan on the shipped episode ------------------------------------------------------------------------------------------

def test_plan_on_titans_is_deterministic_valid_fresh_and_goes_stale_with_one_byte(tmp_path):
    job = tmp_path / "titans"
    job.mkdir()
    for name in ("timed.json", "words.json"):
        shutil.copy(ROOT / "examples" / "titans_from_zero" / name, job / name)
    assert SP.main([str(job)]) == 0
    lib = tmp_path / "lib"
    first = D.plan(job, library=lib)
    bytes1 = (job / "audio" / "sound_mix_manifest.json").read_bytes()
    D.plan(job, library=lib)
    assert (job / "audio" / "sound_mix_manifest.json").read_bytes() == bytes1  # deterministic: the same inputs, the same bytes
    assert first["schema"] == "sound_mix_manifest/2" and C.errors(first, job) == []  # valid /2, CN-02 fresh
    assert len(first["scenes"]) == 16 and {b["kind"] for b in first["beds"]} == {"room_tone", "ambience"}
    assert (job / "audio" / "sound_director_report.json").exists()
    assert not (ROOT / "assets/audio/library/roomtone_hall__v1.wav").exists()  # nothing was written into the real library
    spine = json.loads((job / "audio" / "audio_spine.json").read_text())
    timeline = D.shot_timeline(spine, json.loads((job / "timed.json").read_text()), None)
    assert D.check(first, spine=spine, timeline=timeline, job=job) == [] or "SD-15" not in ids(D.check(first, spine=spine, timeline=timeline, job=job))
    (job / "timed.json").write_bytes((job / "timed.json").read_bytes() + b" ")
    stale = [f for f in D.check(first, spine=spine, timeline=timeline, job=job) if f["rule"] == "SD-15"]
    assert stale and all(f["severity"] == "FAIL" for f in stale)  # CN-02: SD-15, invariant 7


def test_the_matrix_table_in_the_doc_is_the_code():
    text = (ROOT / "docs" / "AUDIO_SYSTEM.md").read_text(encoding="utf-8")
    body = text.split(D.MATRIX_MARKERS[0], 1)[1].split(D.MATRIX_MARKERS[1], 1)[0]
    assert body.strip() == D.render_matrix().strip()
    assert set(D.MATRIX) == {"KEYFRAME_LTX", "DIALOGUE_CU", "HOST_COMMENTARY", "DRAMA_BLOCKED_3D", "ATMOS_BROLL", "MAP", "COMPENSATOR",
                             "STILL_HOLD", None}


# --- rooms, scenes, J and L -----------------------------------------------------------------------------------------------

def test_every_scene_gets_a_procedural_room_tone_inside_bp116_and_a_hole_is_sd01(tmp_path):
    job, spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "hall", {})], "S02": [("b", "KEYFRAME_LTX", "MS", "hall", {})],
                                             "S03": [("c", "KEYFRAME_LTX", "CU", "hall", {})]}, places={"hall": "a great hall"})
    root = tmp_path / "lib"
    m, rep = planned(job, root)
    lib = {i["id"]: i for i in sfx_library.load_manifest(root)["items"]}
    assert all(i["source"]["kind"] == "procedural" and "room_tone" in i["tags"] for i in lib.values() if i["id"].startswith("roomtone"))
    lo, hi = SR.T("BP-116", "room_tone_dbfs")
    tones = [b for b in m["beds"] if b["kind"] == "room_tone"]
    assert {b["scene"] for b in tones} == {"S01", "S02", "S03"}
    for b in tones:
        crest = lib[b["ref"]]["peak_dbfs"] - lib[b["ref"]]["rms_dbfs"]
        assert lo <= b["gain_db"] - crest <= hi  # the placed RMS, in the band
    assert "SD-01" not in ids(rep["findings"])
    spine2 = json.loads((job / "audio" / "audio_spine.json").read_text())
    tl = D.shot_timeline(spine2, {"shots": [], "audio": {}}, json.loads((job / "film_shots.json").read_text()))
    holed = copy.deepcopy(m)
    holed["beds"][1]["end_frame"] -= 25  # a 0.5 s hole before the next scene
    holed["beds"][1]["fade_out_frames"] = 0
    f = D.check(holed, spine=spine2, timeline=tl, library=list(lib.values()))
    assert any(x["rule"] == "SD-01" and x["severity"] == "REVIEW" and x["where"] == "S02" for x in f)


def test_the_acoustic_is_inferred_from_the_place_text_and_recorded(tmp_path):
    assert [D.infer_acoustic(t) for t in ("a deep cave", "the great hall", "a church", "a palace", "a canvas command tent", "an office", "a snowy field")] == \
        ["cave", "hall", "hall", "hall", "room", "room", "outdoor"]
    assert D.acoustic_of({"acoustic": "cave", "text": "x"}) == ("cave", "declared") and D.acoustic_of("a hall") == ("hall", "inferred")
    job, _ = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "tent", {})], "S02": [("b", "MAP", "WS", "tent", {})],
                                         "S03": [("c", "KEYFRAME_LTX", "WS", "field", {})]}, places={"tent": "a tent", "field": "open field"})
    m, rep = planned(job, tmp_path / "lib")
    got = {s["scene"]: (s["acoustic"], s["acoustic_source"]) for s in m["scenes"]}
    assert got == {"S01": ("room", "inferred"), "S02": ("neutral", "inferred"), "S03": ("outdoor", "inferred")}
    assert {r["scene"] for r in rep["inferred"] if r["what"] == "acoustic"} == {"S01", "S02", "S03"}  # the critic sees every guess


def test_a_place_change_leads_with_a_j_cut_and_a_kuleshov_cut_trails_with_an_l_cut(tmp_path):
    spec = {"S01": [("a", "KEYFRAME_LTX", "WS", "hall", {})], "S02": [("b", "KEYFRAME_LTX", "WS", "field", {})],
            "S03": [("c", "KEYFRAME_LTX", "WS", "field", {})]}
    places = {"hall": "a hall", "field": "a field"}
    job, spine = make_job(tmp_path, plan_of=spec, places=places)
    m, _ = planned(job, tmp_path / "lib")
    j = round(abs((SR.T("BP-117", "j_cut_s")[0] + SR.T("BP-117", "j_cut_s")[1]) / 2) * FPS)
    s2, s3 = m["scenes"][1], m["scenes"][2]
    assert (s2["entry"], s2["lead_frames"]) == ("J", j) and s3["entry"] == "butt"
    rt = {b["scene"]: b for b in m["beds"] if b["kind"] == "room_tone"}
    assert rt["S02"]["start_frame"] == s2["start_frame"] - j and rt["S01"]["end_frame"] == s2["start_frame"]  # the incoming bed leads
    edit = {"schema": "edit_and_grade_manifest/1", "scenes": [{"scene_id": "S03", "key_master_frame": None, "grade": None, "cuts": [
        {"from_shot": "b", "to_shot": "c", "cut_type": "KULESHOV_L_CUT", "at_frame": s3["start_frame"], "audio_lead_frames": 0}]}]}
    job2, _ = make_job(tmp_path / "two", plan_of=spec, places=places, edit=edit)
    m2, _ = planned(job2, tmp_path / "two" / "lib")
    l = round((SR.T("BP-117", "l_cut_s")[0] + SR.T("BP-117", "l_cut_s")[1]) / 2 * FPS)
    s3b = m2["scenes"][2]
    assert (s3b["entry"], s3b["lead_frames"]) == ("L", l)
    rt2 = {b["scene"]: b for b in m2["beds"] if b["kind"] == "room_tone"}
    assert rt2["S02"]["end_frame"] == s3b["start_frame"] + l and rt2["S03"]["start_frame"] == s3b["start_frame"]  # the outgoing bed trails
    assert C.errors(m2, job2) == []


def test_a_butt_cut_between_a_map_and_a_drama_shot_is_sd03(tmp_path):
    spec = {"S01": [("a", "MAP", "WS", "m", {})], "S02": [("b", "KEYFRAME_LTX", "WS", "m", {})], "S03": [("c", "KEYFRAME_LTX", "WS", "m", {})]}
    job0, _ = make_job(tmp_path / "zero", plan_of=spec, places={"m": "a map"})
    first = json.loads((job0 / "audio" / "audio_spine.json").read_text())
    start2 = D.scene_bounds(first)["S02"][0]
    edit = {"schema": "edit_and_grade_manifest/1", "scenes": [{"scene_id": "S02", "key_master_frame": None, "grade": None, "cuts": [
        {"from_shot": "a", "to_shot": "b", "cut_type": "STRAIGHT_CUT", "at_frame": start2, "audio_lead_frames": 0}]}]}
    job, spine = make_job(tmp_path, plan_of=spec, places={"m": "a map"}, edit=edit)
    m, rep = planned(job, tmp_path / "lib")
    assert m["scenes"][1]["entry"] == "butt"
    f = [x for x in rep["findings"] if x["rule"] == "SD-03"]
    assert f and f[0]["severity"] == "REVIEW"


# --- the matrix -----------------------------------------------------------------------------------------------------------

def test_matrix_a_map_shot_has_no_spot_a_dialogue_window_has_no_narration_and_native_audio_sits_under_the_bed(tmp_path):
    snd = {"foley": ["boots on stone"], "loudest": "a door slams"}
    spec = {"S01": [("a", "MAP", "WS", "m", {"sound": snd})],
            "S02": [("b", "KEYFRAME_LTX", "MS", "r", {"sound": snd}), ("c", "DIALOGUE_CU", "CU", "r", {})],
            "S03": [("d", "KEYFRAME_LTX", "MS", "r", {})]}
    job0, spine0 = make_job(tmp_path / "z", plan_of=spec, places={"m": "map", "r": "a room"})
    # a native line: the window opens after the last word of scene 1, the narrator waits (D-88)
    native = [{"shot_id": "c", "line": 1, "frames": 100}]
    job, spine = make_job(tmp_path, plan_of=spec, places={"m": "map", "r": "a room"}, native=native)
    (job / "audio" / "native").mkdir(parents=True)
    for sid in ("b", "d"):
        (job / "audio" / "native" / f"{sid}.wav").write_bytes(b"RIFF")
    root = lib_with(tmp_path, ("boots_stone", ["footstep", "stone", "boots"]), ("door_slam", ["door", "slam", "impact"]))
    m, rep = planned(job, root)
    on_map = [s for s in m["spots"] if s["shot_id"] == "a"]
    assert on_map == []  # a MAP shot gets no spot (cues only), so no pan to give
    assert [s["origin"] for s in m["spots"] if s["shot_id"] == "b"] == ["foley", "loudest"]
    assert m["dialogue"] and m["dialogue"][0]["shot_id"] == "c" and m["dialogue"][0]["ref"] is None
    win = spine["post_hoc_shots"][0]
    assert not [w for w in spine["words"] if w["start_frame"] < win["end_frame"] and w["end_frame"] > win["start_frame"]]  # no narration in it
    assert any(f["rule"] == "SD-12" and "dialogue window" in f["detail"] for f in rep["findings"])  # the clip is missing: room tone plays
    nat = {b["scene"]: b for b in m["beds"] if b["kind"] == "native"}
    amb = [b for b in m["beds"] if b["kind"] == "room_tone" and b["scene"] == "S02"][0]
    assert nat["S02"]["gain_db"] == round(amb["gain_db"] - SR.T("BP-160", "native_under_bed_db"), 2)
    assert C.errors(m, job) == []
    # a spot in a MAP shot, written by hand, is a finding
    bad = copy.deepcopy(m)
    bad["spots"].append(dict(bad["spots"][0], id="spx", shot_id="a"))
    tl = D.shot_timeline(spine, json.loads((job / "timed.json").read_text()), json.loads((job / "film_shots.json").read_text()))
    assert any(f["rule"] == "SD-12" and "MAP" in f["detail"] for f in D.check(bad, spine=spine, timeline=tl))


def test_narration_inside_a_dialogue_window_is_sd08(tmp_path):
    job, spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})], "S02": [("b", "DIALOGUE_CU", "CU", "r", {})],
                                             "S03": [("c", "KEYFRAME_LTX", "WS", "r", {})]}, places={"r": "a room"})
    m, _ = planned(job, tmp_path / "lib")
    bad = copy.deepcopy(m)
    w = spine["words"][3]
    bad["dialogue"] = [{"shot_id": "b", "ref": None, "start_frame": w["start_frame"] - 1, "end_frame": w["end_frame"] + 1}]
    tl = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    assert "SD-08" in ids(D.check(bad, spine=spine, timeline=tl))


def test_a_shot_timeline_that_does_not_add_up_is_estimated_and_never_stretched(tmp_path):
    shots = [film_shot("a", "S01", "KEYFRAME_LTX", "WS", "r", 100), film_shot("b", "S02", "KEYFRAME_LTX", "WS", "r", 500),
             film_shot("c", "S03", "KEYFRAME_LTX", "WS", "r", 450)]
    job, spine = make_job(tmp_path, shots=shots, places={"r": "a room"})
    tl = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    assert [s["estimated"] for s in tl] == [True, False, False] and tl[0]["frames"] == 100  # laid as written
    m, rep = planned(job, tmp_path / "lib")
    assert [f["where"] for f in rep["findings"] if f["rule"] == "SD-12"] == ["S01"]


# --- hits, vacuums --------------------------------------------------------------------------------------------------------

def hit_job(tmp_path, reveal_frames, speech=(1.0, 6.0), lane="KEYFRAME_LTX"):
    shots = [{"id": f"T{k}", "segment": "S02", "start_frame": f, "end_frame": f + 10, "reveal": f"reveal {k}", "accents": []}
             for k, f in enumerate(reveal_frames)]
    return make_job(tmp_path, plan_of={"S01": [("a", lane, "WS", "r", {})], "S02": [("b", lane, "MS", "r", {})], "S03": [("c", lane, "CU", "r", {})]},
                    places={"r": "a room"}, timed_shots=shots, speech=speech)


def test_a_reveal_gets_one_three_layer_hit_on_its_frame_and_its_onset_is_judged_by_bp54(tmp_path):
    job, spine = hit_job(tmp_path, [845])  # scene 2 runs 550..1050; its last word ends at 15.9 s, so frame 845 (16.9 s) follows a 1.0 s pause
    m, rep = planned(job, tmp_path / "lib")
    hit = [s for s in m["spots"] if s["group"]]
    assert sorted(s["layer"] for s in hit) == ["air", "body", "sub"] and len({s["group"] for s in hit}) == 1
    assert {s["frame"] for s in hit} == {845} and all(s["origin"] == "hit" for s in hit)
    tl = D.shot_timeline(spine, json.loads((job / "timed.json").read_text()), json.loads((job / "film_shots.json").read_text()))
    assert "SD-05" not in ids(D.check(m, spine=spine, timeline=tl))
    early = copy.deepcopy(m)
    for s in early["spots"]:
        if s["group"]:
            s["frame"] -= 3  # 60 ms early
    f = [x for x in D.check(early, spine=spine, timeline=tl) if x["rule"] == "SD-05"]
    assert f and f[0]["severity"] == "FAIL" and f[0]["basis"] == "BP-54"  # early is worse than late: binding
    late = copy.deepcopy(m)
    for s in late["spots"]:
        if s["group"]:
            s["frame"] += 3  # 60 ms late is inside the window
    assert "SD-05" not in ids(D.check(late, spine=spine, timeline=tl))
    spread = copy.deepcopy(m)
    next(s for s in spread["spots"] if s["layer"] == "air")["frame"] += 4  # 80 ms between layers
    f = [x for x in D.check(spread, spine=spine, timeline=tl) if x["rule"] == "SD-05"]
    assert f and f[0]["severity"] == "REVIEW" and f[0]["basis"] == "BP-119"
    gone = copy.deepcopy(m)
    gone["spots"] = [s for s in gone["spots"] if not s["group"]]
    assert any(x["rule"] == "SD-05" and "no three-layer hit" in x["detail"] for x in D.check(gone, spine=spine, timeline=tl))


def test_a_vacuum_ends_on_its_reveal_and_speech_up_to_it_or_a_fourth_reveal_changes_nothing_more(tmp_path):
    job, spine = hit_job(tmp_path, [845])
    m, rep = planned(job, tmp_path / "lib")
    lo, hi = SR.T("BP-120", "vacuum_s")
    assert len(m["vacuums"]) == 1 and m["vacuums"][0]["end_frame"] == m["vacuums"][0]["reveal_frame"] == 845
    assert lo * FPS <= 845 - m["vacuums"][0]["start_frame"] <= hi * FPS and "SD-06" not in ids(rep["findings"])
    # speech up to the reveal: scene 2's words run 11..16 s -> frame 700 (14 s) is inside speech
    job2, spine2 = hit_job(tmp_path / "b", [700])
    m2, rep2 = planned(job2, tmp_path / "b" / "lib")
    assert m2["vacuums"] == [] and any(f["rule"] == "SD-06" and f["severity"] == "REVIEW" for f in rep2["findings"])
    assert rep2["dropped_vacuums"][0]["frame"] == 700
    # a reveal after a pause that is shorter than the band's floor shrinks and is dropped: 0.5 s after the last word (16.4 s)
    job3, _ = hit_job(tmp_path / "c", [round(16.4 * FPS)])  # 820 -> a pause of only 0.5 s
    m3, _ = planned(job3, tmp_path / "c" / "lib")
    assert m3["vacuums"] == []
    # four reveals in pauses -> three vacuums; the top three by rank: later position wins a tie
    job4, spine4 = make_job(tmp_path / "d", plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})], "S02": [("b", "KEYFRAME_LTX", "WS", "r", {})],
                                                     "S03": [("c", "KEYFRAME_LTX", "WS", "r", {})]}, places={"r": "a room"}, seg_s=20.0,
                            speech=(1.0, 3.0), timed_shots=[{"id": f"T{k}", "segment": "S01", "start_frame": f, "end_frame": f + 5, "reveal": "r",
                                                             "accents": []} for k, f in enumerate((300, 500, 700, 900))])
    m4, rep4 = planned(job4, tmp_path / "d" / "lib")
    assert len(m4["vacuums"]) == 3 and [v["reveal_frame"] for v in m4["vacuums"]] == [500, 700, 900]
    tl4 = D.shot_timeline(spine4, json.loads((job4 / "timed.json").read_text()), json.loads((job4 / "film_shots.json").read_text()))
    over = copy.deepcopy(m4)
    over["vacuums"].append({"start_frame": 100, "end_frame": 150, "reason": "x", "reveal_frame": 150})
    assert any(f["rule"] == "SD-06" and "4 vacuums" in f["detail"] for f in D.check(over, spine=spine4, timeline=tl4))


def test_a_vacuum_over_speech_or_the_wrong_length_is_sd06(tmp_path):
    job, spine = hit_job(tmp_path, [845])
    m, _ = planned(job, tmp_path / "lib")
    tl = D.shot_timeline(spine, json.loads((job / "timed.json").read_text()), json.loads((job / "film_shots.json").read_text()))
    over_speech = copy.deepcopy(m)
    over_speech["vacuums"][0]["start_frame"] = 640
    d = " ".join(f["detail"] for f in D.check(over_speech, spine=spine, timeline=tl) if f["rule"] == "SD-06")
    assert "over speech" in d and "long" in d


def test_the_lead_of_a_j_cut_never_crosses_a_vacuum(tmp_path):
    # the reveal sits on the first frame of scene 2, so the vacuum ends there and the J lead has nothing before it
    job, spine = hit_job(tmp_path, [550])
    m, _ = planned(job, tmp_path / "lib")
    s2 = m["scenes"][1]
    assert not m["vacuums"] or s2["entry"] == "butt" or s2["start_frame"] - s2["lead_frames"] >= max(v["end_frame"] for v in m["vacuums"] if v["end_frame"] <= s2["start_frame"])


# --- stereo, perspective --------------------------------------------------------------------------------------------------

def test_pan_follows_the_focal_point_inside_the_range_and_off_screen_sounds_go_to_the_far_side(tmp_path):
    snd = {"foley": ["boots on stone", "a distant bell"]}
    spec = {"S01": [("r", "KEYFRAME_LTX", "MS", "r", {"focal": 0.9, "sound": snd})], "S02": [("l", "KEYFRAME_LTX", "MS", "r", {"focal": 0.1, "sound": snd})],
            "S03": [("c", "KEYFRAME_LTX", "MS", "r", {"focal": 0.5, "sound": {"foley": ["boots on stone"]}})]}
    job, spine = make_job(tmp_path, plan_of=spec, places={"r": "a room"})
    root = lib_with(tmp_path, ("boots_stone", ["footstep", "stone", "boots"]), ("bell_far", ["bell", "distant", "ring"]))
    m, rep = planned(job, root)
    mx = SR.T("BP-121", "sfx_pan_max")
    by = {(s["shot_id"], s["ref"]): s for s in m["spots"]}
    right, left = by[("r", "boots_stone__v1")], by[("l", "boots_stone__v1")]
    assert 0 < right["pan"] <= mx and -mx <= left["pan"] < 0 and by[("c", "boots_stone__v1")]["pan"] == 0
    assert right["pan"] == pytest.approx(2 * 0.4 * mx)
    bell = by[("r", "bell_far__v1")]  # off-screen: the far side, far, 6 dB down
    assert bell["pan"] == -mx and bell["perspective"] == "far" and bell["gain_db"] == right["gain_db"] - 6.0
    tl = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    assert "SD-07" not in ids(D.check(m, spine=spine, timeline=tl))
    wrong = copy.deepcopy(m)
    next(s for s in wrong["spots"] if s["id"] == right["id"])["pan"] = -0.2
    outside = copy.deepcopy(m)
    next(s for s in outside["spots"] if s["id"] == left["id"])["pan"] = -0.8
    assert "SD-07" in ids(D.check(wrong, spine=spine, timeline=tl)) and "SD-07" in ids(D.check(outside, spine=spine, timeline=tl))


def test_perspective_follows_the_size_and_one_impulse_response_serves_a_scene(tmp_path):
    snd = {"foley": ["boots on stone"]}
    spec = {"S01": [("a", "KEYFRAME_LTX", "WS", "r", {"sound": snd}), ("b", "KEYFRAME_LTX", "CU", "r", {"sound": snd})],
            "S02": [("c", "KEYFRAME_LTX", "MS", "r", {"sound": snd})], "S03": [("d", "KEYFRAME_LTX", "MS", "r", {})]}
    job, spine = make_job(tmp_path, plan_of=spec, places={"r": "a room"})
    m, _ = planned(job, lib_with(tmp_path, ("boots_stone", ["footstep", "stone", "boots"])))
    persp = {s["shot_id"]: s["perspective"] for s in m["spots"]}
    assert persp == {"a": "far", "b": "near", "c": "mid"}
    tl = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    assert "SD-09" not in ids(D.check(m, spine=spine, timeline=tl))
    bad = copy.deepcopy(m)
    next(s for s in bad["spots"] if s["shot_id"] == "a")["perspective"] = "near"
    assert any(f["rule"] == "SD-09" and "follows the size" in f["detail"] for f in D.check(bad, spine=spine, timeline=tl))
    twice = copy.deepcopy(m)
    twice["scenes"].append(dict(twice["scenes"][0], ir_seed=twice["scenes"][0]["ir_seed"] + 1))
    assert any(f["rule"] == "SD-09" and "impulse responses" in f["detail"] for f in D.check(twice, spine=spine, timeline=tl))


# --- music ----------------------------------------------------------------------------------------------------------------

def test_a_cut_off_the_beat_grid_while_music_is_up_is_sd10_and_a_motif_is_one_per_owner(tmp_path):
    audio = {"beds": [], "sfx": [], "cues": [], "music": [{"track": "theme__v1", "start": 0.0, "end": 30.0, "gain_db": -26, "fade_in_s": 2.0, "fade_out_s": 2.0}]}
    shots = [{"id": "T0", "segment": "S01", "start_frame": 0, "end_frame": 500, "accents": []}]
    job, spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})], "S02": [("b", "KEYFRAME_LTX", "WS", "r", {})],
                                             "S03": [("c", "KEYFRAME_LTX", "WS", "r", {})]}, places={"r": "a room"}, audio=audio)
    root = tmp_path / "lib"
    sfx_library.add(root, name="theme", take=1, category="music", tags=["music", "theme"], rate=48000, loop=True,
                    samples=(np.random.default_rng(1).standard_normal(4800) * 0.2).astype(np.float32),
                    source={"kind": "procedural", "seed": 1}, licence={"status": "own_procedural", "note": "t"})
    man = sfx_library.load_manifest(root)
    man["items"][0]["beat_grid"] = {"bpm": 120.0, "offset_s": 0.0, "source": "declared"}
    man["items"][0]["motif_of"] = "napoleon"
    (root / "manifest.json").write_text(json.dumps(man))
    m, _ = planned(job, root)
    assert m["music"][0]["beat_grid"] == {"bpm": 120.0, "offset_s": 0.0, "source": "declared"} and m["music"][0]["motif_of"] == "napoleon"
    base = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    edit_cut = lambda frame: [dict(s, cut={"cut_type": "ACTION_PEAK_CUT", "from_shot": "x", "to_shot": s["id"], "at_frame": frame, "audio_lead_frames": 0},  # noqa: E731
                                   start_frame=frame) if s["id"] == "b" else s for s in base]
    on = [f for f in D.check(m, spine=spine, timeline=edit_cut(round(5.5 * FPS))) if f["rule"] == "SD-10"]  # 5.5 s = 11 beats at 120 BPM
    off = [f for f in D.check(m, spine=spine, timeline=edit_cut(round(5.5 * FPS) + 4)) if f["rule"] == "SD-10"]  # 80 ms off; tolerance 31 ms
    assert on == [] and len(off) == 1 and off[0]["severity"] == "REVIEW" and "31 ms" in off[0]["detail"]
    items = [{"id": "a__v1", "tags": ["music", "motif:napoleon"]}, {"id": "b__v1", "tags": ["music"], "motif_of": "napoleon"}]
    assert D.motif_of("napoleon", items[:1])["id"] == "a__v1" and D.motif_of("nobody", items) is None
    assert any(f["rule"] == "SD-11" and f["severity"] == "REVIEW" for f in D.check(m, spine=spine, timeline=base, library=items))
    assert not any(f["rule"] == "SD-11" for f in D.check(m, spine=spine, timeline=base, library=items[:1]))


def test_a_measured_beat_grid_is_stored_back_on_the_library_item(tmp_path):
    sr = 48000
    x = np.zeros(sr * 12, np.float32)
    burst = (np.random.default_rng(1).standard_normal(240) * np.exp(-np.arange(240) / 60)).astype(np.float32)
    for k in range(24):
        x[int(k * 0.5 * sr):int(k * 0.5 * sr) + 240] += burst
    root = tmp_path / "lib"
    sfx_library.add(root, name="clicks", take=1, category="music", tags=["music"], rate=sr, loop=True, samples=x,
                    source={"kind": "procedural", "seed": 1}, licence={"status": "own_procedural", "note": "t"})
    audio = {"beds": [], "sfx": [], "cues": [], "music": [{"track": "clicks__v1", "start": 0.0, "end": 12.0, "gain_db": -26}]}
    job, _ = make_job(tmp_path, nseg=3, plan_of=None, audio=audio, film=False)
    m, _ = planned(job, root)
    g = m["music"][0]["beat_grid"]
    assert g["source"] == "measured" and abs(g["bpm"] - 120) <= 1
    assert sfx_library.load_manifest(root)["items"][0]["beat_grid"]["source"] == "measured"
    assert sfx_library.validate(root) == []


# --- library, rules, severities ---------------------------------------------------------------------------------------------

def test_a_free_generator_take_without_an_admission_is_sd13_and_fails(tmp_path, monkeypatch):
    job, spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})]}, places={"r": "a room"})
    m, _ = planned(job, tmp_path / "lib")
    ref = m["beds"][0]["ref"]
    base = D.shot_timeline(spine, {"shots": []}, json.loads((job / "film_shots.json").read_text()))
    lib = [{"id": ref, "tags": ["room_tone"], "source": {"kind": "open_model", "model": "x"}, "peak_dbfs": -3.0, "rms_dbfs": -15.0}]
    f = [x for x in D.check(m, spine=spine, timeline=base, library=lib) if x["rule"] == "SD-13"]
    assert f and f[0]["severity"] == "FAIL"
    lib[0]["source"]["admission"] = "ADM-does-not-exist"      # a non-empty string is not an admission (BP-162): the file must hold it
    f = [x for x in D.check(m, spine=spine, timeline=base, library=lib) if x["rule"] == "SD-13"]
    assert f and f[0]["severity"] == "FAIL" and "ADM-does-not-exist" in f[0]["detail"]
    adm = tmp_path / "generator_admission.json"
    adm.write_text(json.dumps({"admissions": [{"id": "ADM-1", "kind": "room_tone", "model": "x", "generator": "g"}]}), encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_GENERATOR_ADMISSION", str(adm))
    lib[0]["source"]["admission"] = "ADM-1"
    assert not [x for x in D.check(m, spine=spine, timeline=base, library=lib) if x["rule"] == "SD-13"]
    adm.write_text(json.dumps({"admissions": [{"id": "ADM-1", "kind": "music", "model": "x", "generator": "g"}]}), encoding="utf-8")
    assert any(x["rule"] == "SD-13" and "music" in x["detail"] for x in D.check(m, spine=spine, timeline=base, library=lib))   # wrong kind


def test_every_sd_severity_is_the_registry_level_of_its_rule():
    for sd, rule in D.RULE_OF.items():
        if rule is None:
            assert D._level(None) == "FAIL"  # SD-15: CN-02, invariant 7
        else:
            assert D._level(rule) == SR.level(rule, SR.severity(rule)), sd
    fails = {sd for sd, rule in D.RULE_OF.items() if rule and D._level(rule) == "FAIL"}
    assert fails == {"SD-13", "SD-14"}  # BP-162 (house) and BP-50 (binding, existing); SD-05 FAILs through BP-54 only for the onset
    assert D._level("BP-54") == "FAIL" and D._level("BP-119") == "REVIEW"
    new = [SR.rule(f"BP-{n}") for n in range(160, 164)]
    assert [r["severity"] for r in new] == ["REVIEW", "REVIEW", "FAIL", "REVIEW"] and new[2]["status"] == "house" and new[2]["decided"]
    assert not any(r["status"] == "binding" for r in new)


def test_the_docs_table_names_the_same_rules_and_severities_as_the_code():
    text = (ROOT / "docs" / "AUDIO_SYSTEM.md").read_text(encoding="utf-8")
    table = text.split("| ID | Check | Rule | Severity |", 1)[1].split("\n\n", 1)[0]
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        sd, rules = cells[0], cells[2]
        want = D.RULE_OF[sd]
        assert (want is None and rules == "CN-02") or (want in rules), (sd, rules)


def test_the_bp_rules_the_director_enforces_name_it():
    for rid in ("BP-116", "BP-117", "BP-118", "BP-119", "BP-120", "BP-121", "BP-122", "BP-123", "BP-160", "BP-161", "BP-162"):
        assert "explainer_engine/audio/sound_director.py" in SR.rule(rid)["enforced_by"], rid
        assert not SR.rule(rid).get("planned"), rid
