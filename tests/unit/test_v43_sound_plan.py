"""v4.3 plan P7: one sound plan per episode and one renderer for every route. Events land on their words or on the visible
action, an era refuses what it never heard, place changes carry J/L bridges, a placeholder or a missing voice never ships,
and the background is measured per route so a Wan shot, a 2.5D shot and a map sound alike (BP-186)."""
from __future__ import annotations

import json
import wave

import numpy as np
import pytest

from explainer_engine.audio import sfx_library, stems
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import sound_plan as SP

FPS = 24
SR = 48000


def _script(shots=None, lines=None, era="prehistoric_pleistocene"):
    shots = shots or [
        {"shot_id": "A1", "segment_id": "S01", "target_duration_seconds": 3.0, "location_id": "loc_caldera",
         "audio_line_ids": ["L1"], "action_start_state": "smoke over the ridge", "route": "still_25d"},
        {"shot_id": "A2", "segment_id": "S01", "target_duration_seconds": 3.0, "location_id": "loc_caldera",
         "audio_line_ids": ["L2"], "action_start_state": "the band walks down the slope", "route": "map_action"},
        {"shot_id": "B1", "segment_id": "S02", "target_duration_seconds": 3.0, "location_id": "loc_cave",
         "audio_line_ids": ["L3"], "action_start_state": "inside the cave shelter by the hearth", "route": "video"},
        {"shot_id": "B2", "segment_id": "S02", "target_duration_seconds": 3.0, "location_id": "loc_cave",
         "audio_line_ids": [], "action_start_state": "inside the cave shelter, quiet", "route": "video",
         "sound_events": [{"kind": "spot", "what": "a distant eruption boom", "at_s": 1.5, "picture_event": "eruption"}]},
    ]
    lines = lines or [{"line_id": "L1", "text": "Then the mountain erupts."}, {"line_id": "L2", "text": "They keep moving."},
                      {"line_id": "L3", "text": "Here the fire is safe."}]
    return {"episode_id": "ep_t", "historical_period": era, "segments": [{"segment_id": "S01"}, {"segment_id": "S02"}],
            "shots": shots, "audio_lines": lines}


def _library(root, classes, origin="elevenlabs", seconds=1.0):
    """A library with one sound per class (16-bit mono WAV), each of the given origin."""
    rng = np.random.default_rng(5)
    items = []
    (root / "foley").mkdir(parents=True, exist_ok=True)
    for cls in classes:
        x = (rng.standard_normal(int(SR * seconds)) * 0.1).astype(np.float32)
        f = f"foley/{cls}.wav"
        (root / f).write_bytes(sfx_library.wav_bytes(x, SR))
        items.append({"id": f"{cls}__v1", "file": f, "category": "foley", "tags": SP.EVENT_CLASSES[cls]["tags"],
                      "source": {"kind": origin}, "review": {"human": "pending"}})
    (root / "manifest.json").write_text(json.dumps({"version": 1, "items": items}))
    return root


def _narration(path, seconds, speech):
    """A test read: noise bursts where ``speech`` says someone talks (a stand-in file, never a made voice in production)."""
    x = np.zeros(int(SR * seconds), np.float32)
    rng = np.random.default_rng(9)
    for a, b in speech:
        x[int(a * SR):int(b * SR)] = rng.standard_normal(int(b * SR) - int(a * SR)) * 0.2
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def test_events_land_on_their_word_the_action_or_the_authored_time():
    plan = SP.build(_script(), fps=FPS)
    a1, a2, b1, b2 = plan["shots"]
    boom = next(e for e in a1["events"] if e["class"] == "eruption_boom")
    assert boom["basis"].startswith("word:erupts") and boom["picture_event"] == "eruption"
    assert boom["at_frame"] == int(round(boom["at_s"] * FPS)) and 0 < boom["at_s"] < 3.0
    walk = next(e for e in a2["events"] if e["class"] == "footsteps_dirt")
    assert walk["basis"] == "action" and walk["at_s"] == pytest.approx(SP.ACTION_AT * 3.0)
    assert any(e["class"] == "fire" and e["basis"].startswith("word:fire") for e in b1["events"])
    authored = next(e for e in b2["events"] if e["basis"] == "authored")
    assert authored["class"] == "eruption_boom" and authored["at_s"] == 1.5 and authored["at_frame"] == 36


def test_a_measured_spine_moves_the_word_event():
    spine = {"A1": [{"word": w, "start_frame": f} for w, f in zip(["then", "the", "mountain", "erupts"], [0, 10, 20, 60])]}
    boom = next(e for e in SP.build(_script(), fps=FPS, spines=spine)["shots"][0]["events"] if e["class"] == "eruption_boom")
    assert boom["at_frame"] == 60 and boom["basis"] == "word:erupts:measured"


def test_an_era_refuses_what_it_never_heard():
    shots = [{"shot_id": "X1", "segment_id": "S01", "target_duration_seconds": 2.0, "location_id": "loc_a",
              "audio_line_ids": [], "action_start_state": "riders gallop past with swords drawn"}]
    plan = SP.build(_script(shots=shots, lines=[]), fps=FPS)
    assert {b["class"] for b in plan["blocked_era_events"]} == {"horse_hooves", "metal_clash"}
    assert not {"horse_hooves", "metal_clash"} & {e["class"] for e in plan["shots"][0]["events"]}
    later = SP.build(_script(shots=shots, lines=[], era="napoleonic_1815"), fps=FPS)
    assert {"horse_hooves", "metal_clash"} <= {e["class"] for e in later["shots"][0]["events"]}


def test_an_unknown_or_late_authored_sound_is_refused():
    bad = _script()
    bad["shots"][3]["sound_events"] = [{"kind": "spot", "what": "a kazoo solo"}]
    with pytest.raises(ContractError, match="no class"):
        SP.build(bad, fps=FPS)
    late = _script()
    late["shots"][3]["sound_events"][0]["at_s"] = 9.0
    with pytest.raises(ContractError, match="after the shot's end"):
        SP.build(late, fps=FPS)


def test_one_bed_per_place_with_a_jl_bridge_at_the_change():
    plan = SP.build(_script(), fps=FPS)
    assert [b["place"] for b in plan["beds"]] == ["loc_caldera", "loc_cave"]
    assert plan["beds"][0]["shot_ids"] == ["A1", "A2"] and plan["beds"][1]["room"] == "cave"
    (br,) = plan["bridges"]
    assert br["at_s"] == 6.0 and br["j_start_s"] == 6.0 - SP.BRIDGE_S and br["l_end_s"] == 6.0 + SP.BRIDGE_S
    assert plan["beds"][0]["tail_s"] == SP.BRIDGE_S and plan["beds"][1]["lead_s"] == SP.BRIDGE_S
    assert [m["segment_id"] for m in plan["music"]] == ["S01", "S02"] and "music_bed" in plan["classes"]


def test_sources_are_library_first_placeholders_and_gaps_go_on_the_needs_list(tmp_path):
    plan = SP.build(_script(), fps=FPS)
    real = [c for c in plan["classes"] if c not in ("fire", "music_bed")]
    _library(tmp_path, real)
    items = json.loads((tmp_path / "manifest.json").read_text())["items"]
    x = np.zeros(SR // 2, np.float32)
    (tmp_path / "foley/fire_p.wav").write_bytes(sfx_library.wav_bytes(x, SR))
    items.append({"id": "fire_p__v1", "file": "foley/fire_p.wav", "category": "foley", "tags": ["fire"],
                  "source": {"kind": "procedural"}, "review": {"human": "pending"}})
    (tmp_path / "manifest.json").write_text(json.dumps({"version": 1, "items": items}))
    src = SP.resolve(plan, tmp_path)
    assert src["fire"]["status"] == "placeholder" and src["music_bed"]["status"] == "missing"
    assert all(src[c]["status"] == "library" for c in real)
    assert [(n["class"], n["status"]) for n in SP.needs(src)] == [("fire", "placeholder"), ("music_bed", "missing")]
    ok, why = SP.shippable(src, plan)
    assert not ok and len(why) == 2
    out = SP.write(plan, src, tmp_path / "ep")
    saved = json.loads(out.read_text())
    assert saved["shippable"] is False and saved["needs"][0]["class"] == "fire"


def test_a_placeholder_or_a_missing_voice_never_ships_but_a_preview_says_so(tmp_path):
    plan = SP.build(_script(), fps=FPS)
    lib = _library(tmp_path / "lib", [c for c in plan["classes"] if c != "fire"])
    src = SP.resolve(plan, lib)
    with pytest.raises(ContractError, match="not shippable"):
        stems.render(plan, src, tmp_path / "out", library_root=lib, shippable=True)
    rep = stems.render(plan, src, tmp_path / "prev", library_root=lib, shippable=False)
    assert rep["shippable"] is False and rep["placeholders"] == ["fire"] and rep["narration"].startswith("none")
    assert {p.name for p in (tmp_path / "prev").glob("*.wav")} == {f"{k}.wav" for k in
                                                                   ("narration", "music", "ambience", "sfx", "mix")}
    full = _library(tmp_path / "lib2", plan["classes"])
    with pytest.raises(ContractError, match="no narration"):
        stems.render(plan, SP.resolve(plan, full), tmp_path / "o2", library_root=full, shippable=True)
    with pytest.raises(ValueError, match="SFX_PACK_FORBIDDEN_AS_NARRATION"):
        stems.render(plan, SP.resolve(plan, full), tmp_path / "o3", library_root=full,
                     narration=_narration(tmp_path / "G4_SFX_Footsteps_Ambience_Music_Pack.wav", 12.0, []))


def _stem(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32).reshape(-1, 2) / 32768


def test_the_bed_ducks_under_the_voice_and_the_bridge_overlaps_the_cut(tmp_path):
    plan = SP.build(_script(), fps=FPS)
    lib = _library(tmp_path / "lib", plan["classes"], seconds=2.0)
    nar = _narration(tmp_path / "read.wav", 12.0, [(0.5, 2.5), (6.5, 8.5)])
    rep = stems.render(plan, SP.resolve(plan, lib), tmp_path / "out", library_root=lib, narration=nar)
    assert rep["shippable"] is True and rep["placeholders"] == [] and rep["narration"] == "file:read.wav"
    amb = _stem(tmp_path / "out/ambience.wav").mean(axis=1)

    def db(a, b):
        return stems._rms_db(amb[int(a * SR):int(b * SR)])

    assert db(3.2, 3.8) - db(1.2, 1.8) >= stems.BED_DUCK_DB - 1.5   # the bed dips under speech, comes back in the gap
    assert db(5.8, 5.95) > -70 and db(6.05, 6.2) > -70                 # J/L: no hole at the place change


def test_the_level_gate_compares_routes_and_flags_one_that_is_louder(tmp_path):
    plan = SP.build(_script(), fps=FPS)
    lib = _library(tmp_path / "lib", plan["classes"], seconds=2.0)
    nar = _narration(tmp_path / "read.wav", 12.0, [(0.3, 1.5), (3.3, 4.5), (6.3, 7.5), (9.3, 10.5)])
    rep = stems.render(plan, SP.resolve(plan, lib), tmp_path / "even", library_root=lib, narration=nar)
    rows = {r["gate"]: r for r in rep["levels"]["rows"]}
    assert set(rep["levels"]["groups"]["in_gaps_db"]) == {"map_action", "still_25d", "video"}
    voice = np.zeros(int(12 * SR), np.float32)
    bg = np.random.default_rng(1).standard_normal(int(12 * SR)).astype(np.float32) * 0.01
    bg[int(6 * SR):] *= 4.0     # the Wan shots' background 12 dB up
    loud = stems.level_report(plan, voice, bg)
    row = next(r for r in loud["rows"] if r["gate"] == "equal_level_in_gaps")
    assert row["status"] == "REVIEW" and row["measured"] > stems.SPREAD_MAX_DB     # BP-186 is a hypothesis: REVIEW
    even = stems.level_report(plan, voice, np.random.default_rng(1).standard_normal(int(12 * SR)).astype(np.float32) * 0.01)
    assert next(r for r in even["rows"] if r["gate"] == "equal_level_in_gaps")["status"] == "PASS"
    assert rows["equal_level_in_gaps"]["status"] in ("PASS", "REVIEW")


def test_one_route_is_nothing_to_compare_and_says_so():
    plan = SP.build(_script(), fps=FPS)
    for s in plan["shots"]:
        s["route"] = "video"
    rep = stems.level_report(plan, np.zeros(12 * SR, np.float32), np.ones(12 * SR, np.float32) * 0.01)
    assert all(r["status"] == "NOT_RUN" for r in rep["rows"])


def test_a_take_from_a_later_world_never_plays_in_the_era(tmp_path):
    plan = SP.build(_script(), fps=FPS)
    _library(tmp_path, ["wind"])
    items = json.loads((tmp_path / "manifest.json").read_text())["items"]
    (tmp_path / "foley/garage.wav").write_bytes(sfx_library.wav_bytes(np.zeros(SR // 2, np.float32), SR))
    items.append({"id": "amb_burnt_garage__v1", "file": "foley/garage.wav", "category": "foley",
                  "tags": ["ambience", "fire", "ruin"], "source": {"kind": "elevenlabs", "prompt": "a burnt-out garage"},
                  "review": {"human": "pending"}})   # like the real one: "garage" only in the id and the prompt
    (tmp_path / "manifest.json").write_text(json.dumps({"version": 1, "items": items}))
    assert SP.resolve(plan, tmp_path)["fire"]["status"] == "missing"
    later = SP.build(_script(era="modern_20th_century"), fps=FPS)
    assert SP.resolve(later, tmp_path)["fire"]["status"] == "library"
