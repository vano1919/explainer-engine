"""The professional sound library and the layered sound design (2026-11-13, docs/SOUND_LIBRARY.md LIB-01..LIB-08, docs/EPISODE_FIRST.md SP-03..SP-07):
licence scope, QC, the catalog and its search, the scene-aware design per shot (visibility, map shots, distance, mood and music,
coverage states), the cue sheet and its validation, the bus limiter and the final mix check."""
from __future__ import annotations

import json
import wave

import numpy as np
import pytest

from explainer_engine.audio import asset_qc as Q
from explainer_engine.audio import catalog as C
from explainer_engine.audio import free_import as FI
from explainer_engine.audio import mix_check as M
from explainer_engine.audio import sfx_library as L
from explainer_engine.audio import sources as S
from explainer_engine.audio import stems as ST
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import cue_sheet as CS
from explainer_engine.episode import sound_plan as SP

SR = 48000
FPS = 24


# --- licences: the creator's scope (2026-11-13) ------------------------------------------------------------------------
def test_licence_matters_for_music_only_and_bbc_is_the_recorded_sfx_exception():
    assert S.verdict("bbc_remarc", use="sfx") == "verified"
    assert S.verdict("bbc_remarc", use="music") == "rejected"           # never a BBC take as background music
    assert S.verdict("bbc_remarc") == "rejected"                        # the default is the strict reading
    assert S.verdict("cc_by_sa", use="music") == "rejected" and S.verdict("cc_by_4", use="music") == "verified"
    rec = S.licence_record("bbc_remarc", creator="BBC", source_url="u", read_on="2026-11-13",
                           attribution_text=S.BBC_CREDIT, use="sfx")
    assert rec["production"] == "verified" and "07:49" in rec["exception"] and rec["attribution_required"]


def test_a_bbc_pick_fetches_only_the_head_a_loop_needs(monkeypatch):
    meta = {"id": "07019150", "seconds": 404.0, "sample_rate": 44100, "channels": 2, "bits": 16, "wav_bytes": 71_000_000}
    monkeypatch.setattr(S, "read_bbc", lambda item: {"licence": "bbc_remarc", "creator": "BBC", "title": "Battle Crowd",
                                                     "page": "p", "attribution_text": S.BBC_CREDIT, "meta": meta,
                                                     "files": [{"name": f"{item}.wav", "url": "u"}]})
    a = FI._resolve({"name": "x", "source": "bbc", "item": "07019150", "kind": "loop", "seconds": 60, "start_s": 30}, {})
    assert a["max_bytes"] == int(4096 + 93.0 * 44100 * 2 * 2) and a["full_seconds"] == 404.0
    short = FI._resolve({"name": "y", "source": "bbc", "item": "07019150", "kind": "one_shot"}, {})
    assert short["max_bytes"] is None                                     # a one-shot takes the whole recording


def test_a_quarantined_take_is_hidden_from_production_search(tmp_path):
    x = (np.random.default_rng(1).standard_normal(SR) * 0.1).astype(np.float32)
    for name, prod in (("ok", "verified"), ("q", "quarantine")):
        L.add(tmp_path, name=name, take=1, category="foley", tags=["wind"], samples=x, rate=SR, source={"kind": "third_party"},
              licence={"status": "licensed", "production": prod})
    assert [i["id"] for i in L.find(tmp_path, tags=["wind"])] == ["ok__v1"]
    assert {i["id"] for i in L.find(tmp_path, tags=["wind"], usable=False)} == {"ok__v1", "q__v1"}


# --- QC --------------------------------------------------------------------------------------------------------------
def test_qc_finds_clipping_plateaus_silence_and_near_duplicates():
    rng = np.random.default_rng(2)
    x = (rng.standard_normal(SR) * 0.2).astype(np.float32)
    clipped = x.copy()
    clipped[1000:1010] = 1.0
    assert Q.measure(clipped, SR)["clipped_samples"] == 10 and Q.measure(x, SR)["clipped_samples"] == 0
    silent = np.zeros(SR, np.float32)
    silent[:2000] = x[:2000]
    rep = Q.check({"ok": True, "codec": "pcm_s16le"}, Q.measure(silent, SR), kind="one_shot")
    assert rep["status"] == "FAIL" and "digital silence" in rep["findings"][0]["detail"]
    long = (rng.standard_normal(SR * 6) * 0.2).astype(np.float32)
    a, b = Q.fingerprint(long, SR), Q.fingerprint(long[SR:SR * 4] * 0.5, SR)
    assert Q.similarity(a, b) > Q.NEAR_DUP_CORR
    brown = np.cumsum(rng.standard_normal(SR * 3)).astype(np.float32)          # a different recording: another spectrum
    other = Q.fingerprint(brown / np.abs(brown).max() * 0.5, SR)
    assert Q.similarity(a, other) < Q.NEAR_DUP_CORR


# --- catalog ---------------------------------------------------------------------------------------------------------
def test_the_catalog_searches_by_every_dimension_and_keeps_quarantine_out(tmp_path):
    x = (np.random.default_rng(3).standard_normal(SR) * 0.1).astype(np.float32)
    cat = {"bst": "sound_effects", "sound_category": "weapons", "genres": ["battlefield"], "scene_types": ["battlefield"],
           "historical_era": ["bronze_age"], "environment": ["battlefield"], "materials": ["metal"], "mood": ["aggressive"],
           "distance": "close", "space": "exterior", "usage": ["foreground_action"], "action_tags": ["sword_clash"]}
    L.add(tmp_path, name="clash", take=1, category="foley", tags=["sword", "metal"], samples=x, rate=SR,
          source={"kind": "third_party"}, licence={"status": "licensed", "production": "verified"},
          extra={"kind": "one_shot", "catalog": cat})
    L.add(tmp_path, name="clash_q", take=1, category="foley", tags=["sword"], samples=x, rate=SR,
          source={"kind": "third_party"}, licence={"status": "licensed", "production": "quarantine"},
          extra={"kind": "one_shot", "catalog": dict(cat, historical_era=["modern"])})
    C.build_index(tmp_path)
    hits = C.search(tmp_path, category="weapons", era="bronze_age", material="metal", mood="aggressive")
    assert [h["asset_id"] for h in hits] == ["clash__v1"]
    assert {h["asset_id"] for h in C.search(tmp_path, category="weapons")} == {"clash__v1", "clash_q__v1"}
    assert [h["asset_id"] for h in C.search(tmp_path, playable_only=True, category="weapons")] == ["clash__v1"]


# --- the scene-aware design ------------------------------------------------------------------------------------------
def _script(shots, lines=(), segments=None, era="bronze_age"):
    return {"episode_id": "ep_d", "historical_period": era, "shots": shots, "audio_lines": list(lines),
            "segments": segments or [{"segment_id": "S01"}]}


def _shot(sid, action, lines=(), **kw):
    return dict({"shot_id": sid, "segment_id": "S01", "target_duration_seconds": 3.0, "location_id": "loc_plain",
                 "audio_line_ids": list(lines), "action_start_state": action, "route": "video"}, **kw)


def test_a_word_is_a_candidate_only_when_the_picture_shows_it_and_is_never_placed():
    # AV contract (D-135, the creator's AV brief 2026-11-13): words never place a sound; a person authors it
    lines = [{"line_id": "L1", "text": "Far away the fire spreads."}, {"line_id": "L2", "text": "Far away the fire spreads."}]
    plan = SP.build(_script([_shot("A", "a woman looks at the camera, close", ["L1"]),
                             _shot("B", "embers glow by the hearth", ["L2"])], lines), fps=FPS)
    a, b = plan["shots"]
    assert not any(e["class"] == "fire" for e in a["events"]) and "fire" in a["design"]["heard_not_seen"]
    assert not any(c["class"] == "fire" for c in a["candidates"])
    assert not any(e["class"] == "fire" for e in b["events"])
    assert any(c["class"] == "fire" and c["source"] == "word" for c in b["candidates"])


def test_a_map_shot_takes_no_word_events_only_its_action_and_authored_ones():
    lines = [{"line_id": "L1", "text": "The army marches and the drums beat."}]
    sh = _shot("M", "the arrow of the army moves east", ["L1"], route="map_action",
               sound_events=[{"class": "paper_map", "at_s": 0.5}])
    ev = SP.build(_script([sh], lines), fps=FPS)["shots"][0]["events"]
    assert {e["basis"] for e in ev} <= {"authored", "action"} and not any(e["class"] == "war_drums" for e in ev)
    assert any(e["class"] == "paper_map" for e in ev)


def test_distance_comes_from_the_composition_plane_then_the_shot_size():
    near = _shot("N", "the general rides past", screen_composition={"foreground": "a horse rears"},
                 camera_spec={"shot_size": "extreme_wide"}, sound_events=[{"class": "horse_neigh", "at_s": 1.0}])
    far = _shot("F", "a column on the plain", camera_spec={"shot_size": "extreme_wide"},
                sound_events=[{"class": "horse_neigh", "at_s": 1.0}])
    plan = SP.build(_script([near, far]), fps=FPS)
    assert plan["shots"][0]["events"][0]["distance"] == "close" and plan["shots"][1]["events"][0]["distance"] == "distant"


def test_music_follows_the_segment_mood():
    segs = [{"segment_id": "S01", "title": "Market day in the village", "narrative_purpose": "a peaceful morning"},
            {"segment_id": "S02", "title": "The attack on the walls"},
            {"segment_id": "S03", "title": "Quiet fields", "narrative_purpose": "calm harvest", "music": True},
            {"segment_id": "S04"}]
    shots = [_shot(f"X{i}", "two elders look out", segment_id=f"S0{i}") for i in range(1, 5)]
    plan = SP.build(_script(shots, segments=segs), fps=FPS)
    m = plan["segment_moods"]
    assert m["S01"]["mood"] == "peaceful" and m["S01"]["music"] is False
    assert m["S02"]["mood"] == "aggressive" and m["S02"]["music"] is True
    assert m["S03"]["music"] is True and m["S03"]["music_reason"].startswith("authored")
    assert m["S04"]["mood"] == "neutral" and m["S04"]["music"] is True
    assert [c["segment_id"] for c in plan["music"]] == ["S02", "S03", "S04"]
    assert plan["shots"][0]["design"]["state"] == "AMBIENCE_ONLY"


def test_every_shot_names_a_coverage_state_and_silence_needs_its_reason():
    shots = [_shot("A", "riders gallop past", segment_id="S01",
                   sound_events=[{"class": "horse_hooves", "at_s": 0.5, "what": "riders gallop past"}]),
             _shot("B", "the hall is empty", sound_design={"silence": "the moment after the news: nothing moves"})]
    plan = SP.build(_script(shots, era="napoleonic_1815"), fps=FPS)
    a, b = plan["shots"]
    assert a["design"]["state"] == "FULL_LAYERED_DESIGN" and b["design"]["state"] == "INTENTIONAL_SILENCE"
    assert set(a["design"]["answers"]) == {"visible", "environment_sounds", "audible_actions", "perspective",
                                           "ambience_layer", "music_supports", "emotion", "sync_points", "protect_voice",
                                           "silence", "visual_events", "candidates"}
    assert set(a["design"]["layers"]) == set(CS.LAYERS)
    assert SP.coverage_state([], False, True, None) == "MINIMAL_DESIGN"
    with pytest.raises(ContractError, match="needs its reason"):
        SP.build(_script([_shot("C", "x", sound_design={"silence": True})]), fps=FPS)


# --- the cue sheet ---------------------------------------------------------------------------------------------------
def _lib(root, spec):
    """spec: {class: [(kind, seconds, extra_catalog)]} -> a library with those takes."""
    rng = np.random.default_rng(7)
    items = []
    (root / "foley").mkdir(parents=True, exist_ok=True)
    for cls, takes in spec.items():
        for k, (kind, secs, cat) in enumerate(takes):
            iid = f"{cls}_{k}__v1"
            x = (rng.standard_normal(int(SR * secs)) * 0.1).astype(np.float32)
            (root / f"foley/{iid}.wav").write_bytes(L.wav_bytes(x, SR))
            tags = SP.EVENT_CLASSES[cls]["tags"]
            items.append({"id": iid, "file": f"foley/{iid}.wav", "category": "foley", "tags": tags, "seconds": secs,
                          "kind": kind, "source": {"kind": "third_party"}, "review": {"human": "pending"},
                          "licence": {"status": "licensed", "production": "verified",
                                      "attribution_required": cls == "music_bed",
                                      "attribution_text": "\"T\" K (x) CC BY 4.0" if cls == "music_bed" else None},
                          "catalog": cat or {}})
    (root / "manifest.json").write_text(json.dumps({"version": 1, "items": items}))
    return root


def _battle_plan():
    segs = [{"segment_id": "S01", "title": "The column waits", "narrative_purpose": "tense watch"},
            {"segment_id": "S02", "title": "The charge", "narrative_purpose": "the attack"}]
    shots = [_shot("A", "the column waits on the plain", segment_id="S01",
                   sound_events=[{"class": "horse_neigh", "at_s": 0.5, "distance": "distant"},
                                 {"class": "horse_neigh", "at_s": 2.0, "distance": "close"}]),
             _shot("B", "the column waits on the plain", segment_id="S01"),
             _shot("C", "the army charges", segment_id="S02",
                   sound_events=[{"class": "war_horn", "at_s": 0.0, "distance": "distant"}])]
    return SP.build(_script(shots, segments=segs), fps=FPS)


def _battle_lib(tmp_path, plan):
    spec = {c: [("loop", 4.0, None)] for c in plan["classes"]}
    spec["horse_neigh"] = [("one_shot", 1.0, None), ("one_shot", 1.2, None)]
    spec["war_horn"] = [("one_shot", 2.0, None)]
    spec["riser"] = [("one_shot", 3.0, None)]
    spec["music_bed"] = [("track", 8.0, {"mood": ["tense"], "historical_era": ["bronze_age"], "intensity": 3}),
                         ("track", 8.0, {"mood": ["aggressive"], "historical_era": ["bronze_age"], "intensity": 5}),
                         ("track", 8.0, {"mood": ["peaceful"], "historical_era": ["medieval"], "intensity": 1})]
    return _lib(tmp_path, spec)


def test_the_cue_sheet_gives_every_sound_its_asset_time_gain_and_reason(tmp_path):
    plan = _battle_plan()
    plan["classes"] = sorted(set(plan["classes"]) | {"riser"})
    lib = _battle_lib(tmp_path, plan)
    sheet = CS.build(plan, SP.resolve(plan, lib), lib)
    rows = {r["cue_id"]: r for r in sheet["rows"]}
    far, near = rows["EV_A_horse_neigh_0"], rows["EV_A_horse_neigh_1"]
    assert far["asset_id"] != near["asset_id"]                                  # BP-57: the class rotates its takes
    assert far["gain_db"] < near["gain_db"] - 5 and far["eq"]["lowpass_hz"] == CS.DISTANCE_LOWPASS_HZ["distant"]
    assert near["eq"]["lowpass_hz"] is None and far["reverb"] == "air_far"
    assert 1 - CS.PITCH_JITTER <= far["pitch"] <= 1 + CS.PITCH_JITTER
    for k in ("cue_id", "scene_id", "shot_id", "asset_id", "start_s", "end_s", "duration_s", "layer", "visual_event",
              "sync_point_s", "gain_db", "pan", "fade_in_s", "fade_out_s", "pitch", "eq", "reverb", "ducking_group",
              "priority", "selection_reason", "confidence", "license_status"):
        assert k in far
    music = [r for r in sheet["rows"] if r["layer"] == "music"]
    assert [r["asset_id"] for r in music] == ["music_bed_0__v1", "music_bed_1__v1"]      # tense, then aggressive
    assert music[0]["end_s"] > music[1]["start_s"] and music[1]["fade_in_s"] == CS.MUSIC_XFADE_S   # the crossfade
    (riser,) = [r for r in sheet["rows"] if r["layer"] == "transition"]
    assert riser["end_s"] == pytest.approx(6.0) and riser["selection_reason"].startswith("designed: tense -> aggressive")
    assert sheet["credits"] == ["\"T\" K (x) CC BY 4.0"]
    gate = CS.validate(sheet, plan, lib)
    assert gate["verdict"]["status"] in ("PASS", "REVIEW"), gate["verdict"]


def test_validation_catches_silence_a_missing_bed_an_unlicensed_score_and_a_crowd(tmp_path):
    plan = _battle_plan()
    lib = _battle_lib(tmp_path, plan)
    sheet = CS.build(plan, SP.resolve(plan, lib), lib)
    holed = dict(sheet, rows=[r for r in sheet["rows"] if r["layer"] not in ("ambience", "music")])
    st = {r["gate"]: r["status"] for r in CS.validate(holed, plan, lib)["rows"]}
    assert st["no_undeclared_silence"] == "FAIL" and st["ambience_present"] == "FAIL"
    bad = json.loads(json.dumps(sheet))
    next(r for r in bad["rows"] if r["layer"] == "music")["license_status"]["production"] = "rejected"
    for i in range(6):
        bad["rows"].append(dict(bad["rows"][-1], cue_id=f"X{i}", layer="spot", **{"class": "impact"}, start_s=7.0,
                                end_s=8.0, duration_s=1.0, shot_id="C"))
    st = {r["gate"]: r["status"] for r in CS.validate(bad, plan, lib)["rows"]}
    assert st["music_licence"] == "FAIL" and st["overlap"] == "FAIL"
    with pytest.raises(ContractError, match="cue sheet FAIL"):
        CS.require(CS.validate(holed, plan, lib))


def test_a_declared_silence_is_not_a_hole(tmp_path):
    shots = [_shot("A", "the hall", sound_design={"silence": "the verdict lands: the room holds its breath"})]
    plan = SP.build(_script(shots), fps=FPS)
    lib = _lib(tmp_path, {c: [("loop", 4.0, None)] for c in plan["classes"]})
    sheet = CS.build(plan, SP.resolve(plan, lib), lib)
    assert not [r for r in sheet["rows"] if r["layer"] == "ambience" and not r["asset_id"].startswith("room_tone")]
    st = {r["gate"]: r["status"] for r in CS.validate(sheet, plan, lib)["rows"]}
    assert st["no_undeclared_silence"] == "PASS" and st["coverage_state"] == "PASS"


# --- the mix ---------------------------------------------------------------------------------------------------------
def test_the_bus_limiter_dips_the_background_and_never_the_voice():
    n = SR
    voice = np.zeros((n, 2), np.float32)
    voice[:, :] = 0.5
    bus = np.zeros((n, 2), np.float32)
    bus[SR // 2:SR // 2 + 200] = 0.8                                         # a war cry peak on top of the voice
    env = ST.bus_limit(voice, bus)
    mix = voice + bus * env[:, None]
    assert float(np.abs(mix).max()) <= ST.PEAK_CEILING + 1e-6 and env[:SR // 4].min() == 1.0
    assert ST.bus_limit(voice * 0.1, bus * 0.1).min() == 1.0                 # nothing over: nothing touched


def _wav(path, x):
    x = x if x.ndim == 2 else np.stack([x, x], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def test_the_mix_check_measures_delivered_loudness_clipping_and_narration_protection(tmp_path):
    rng = np.random.default_rng(4)
    n = SR * 6
    voice = np.zeros(n, np.float32)
    for a in (0.5, 2.5, 4.5):
        voice[int(a * SR):int((a + 1.2) * SR)] = rng.standard_normal(int(1.2 * SR)) * 0.2
    bed = (rng.standard_normal(n) * 0.004).astype(np.float32)
    for name, x in (("narration", voice), ("music", bed * 0.5), ("ambience", bed), ("sfx", bed * 0),
                    ("mix", voice + bed * 1.5)):
        _wav(tmp_path / f"{name}.wav", x)
    rep = M.check(tmp_path, plan={"shots": [{"shot_id": "A", "start_s": 0.0, "dur_s": 6.0}]})
    st = {r["gate"]: r["status"] for r in rep["rows"]}
    assert st["delivered_loudness"] == "PASS" and st["no_clipping"] == "PASS" and st["narration_protected"] == "PASS"
    assert st["no_masked_shot"] == "PASS" and rep["numbers"]["gaps_lu"]["combined"] > 14
    loud = voice + bed * 1.5
    loud[SR:SR + 50] = 1.0
    _wav(tmp_path / "mix.wav", loud)
    _wav(tmp_path / "ambience.wav", bed * 60)                                # the bed as loud as the voice
    rep = M.check(tmp_path, plan={"shots": [{"shot_id": "A", "start_s": 0.0, "dur_s": 6.0}]})
    st = {r["gate"]: r["status"] for r in rep["rows"]}
    assert st["no_clipping"] == "FAIL" and st["narration_protected"] == "FAIL" and st["no_masked_shot"] == "REVIEW"
