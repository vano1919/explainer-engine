"""Fable audit 2026-11-13 FA-09: the bed belongs to the place, the era to the manifest, the mood to the segment. Words of the
prose stay candidates (the same rule D-135 set for effects), and a sound no script event asked for (the designed riser) is
named in the event report as a derived event with its reason."""
from __future__ import annotations

from explainer_engine.audio.sfx_planner import build_shot_sound_design_metadata
from explainer_engine.episode import av_report as AVR
from explainer_engine.episode import sound_plan as SP

# the audit's three measured sentences: the planner's substring match reads rain, ash and an ash room from them
MEASURED = ("The supply line strains as the column marches",
            "A flash of bronze as the brain of the army, the general, trains his men",
            "They wash the grain in the shallow river")


def _script(sentences, bed=None, era=None):
    loc = {"location_id": "loc_field", "name": "the open field"}
    if bed:
        loc["ambience_bed"] = bed
    doc = {"episode_id": "ep_x", "segments": [{"segment_id": "S01"}],
           "world_bible": {"locations": [loc]},
           "shots": [{"shot_id": f"A{k}", "segment_id": "S01", "target_duration_seconds": 3.0, "location_id": "loc_field",
                      "audio_line_ids": [], "action_start_state": s, "route": "still_25d"} for k, s in enumerate(sentences)],
           "audio_lines": []}
    if era:
        doc["historical_period"] = era
    return doc


def test_the_measured_sentences_fool_the_word_planner():
    """The fault is real: the planner's weather from words is not the place (kept as the candidate's reason)."""
    weathers = [build_shot_sound_design_metadata({"action_start_state": s}, historical_period="bronze_age")["weather"]
                for s in MEASURED]
    assert any("rain" in w for w in weathers) and any("ash" in w for w in weathers)


def test_the_authored_place_bed_wins_over_the_words():
    bed = {"classes": ["wind", "birds"], "room": "outdoor", "why": "an open field: wind and birds"}
    plan = SP.build(_script(MEASURED, bed), era="bronze_age")
    assert [b["classes"] for b in plan["beds"]] == [["wind", "birds"]]
    assert plan["beds"][0]["basis"] == "authored" and {s["room"] for s in plan["shots"]} == {"outdoor"}


def test_without_an_authored_bed_the_word_bed_is_only_a_candidate():
    plan = SP.build(_script(MEASURED), era="bronze_age")
    assert all(b["basis"].startswith("candidate:") for b in plan["beds"])


def test_the_era_comes_from_the_manifest_and_a_guess_is_marked():
    assert SP.build(_script(MEASURED), era="bronze_age")["era_basis"] == "manifest"
    assert SP.build(_script(MEASURED, era="bronze_age"))["era_basis"] == "script"
    troy = _script(["Achilles drags the body around the walls"])
    troy["episode_id"] = "ep_troy"
    plan = SP.build(troy)
    assert plan["era"] == "napoleonic_1815" and plan["era_basis"] == "default"   # the old fallback, now refused at G4
    assert plan["era_basis"] not in SP.ERA_BASES


def test_the_authored_mood_wins_and_the_word_mood_is_a_candidate():
    doc = _script(["a storm of war, the attack begins"])
    word = SP.build(doc, era="bronze_age")["segment_moods"]["S01"]
    assert word["basis"].startswith("word:") or word["basis"] == "default"
    doc["segments"][0]["mood"] = "peaceful"
    assert SP.build(doc, era="bronze_age")["segment_moods"]["S01"] == {**SP.build(doc, era="bronze_age")["segment_moods"]["S01"],
                                                                     "mood": "peaceful", "basis": "authored"}


def test_the_riser_is_a_derived_event_with_its_reason():
    sheet = {"rows": [{"cue_id": "TR_S01_S02", "event_id": None, "layer": "transition", "class": "riser", "shot_id": "B1",
                       "start_s": 3.5, "end_s": 6.0, "asset_id": "riser__v1",
                       "selection_reason": "designed: peaceful -> tense at the cut (derived from the segment moods, mood basis authored)"}]}
    rep = AVR.event_report({"shots": {}, "fps": 24}, {"shots": []}, sheet, None)
    (ev,) = rep["events"]
    assert ev["source"] == "derived" and ev["op"] == "derived:riser" and "derived from the segment moods" in ev["why"]


def _toba_episode(tmp_path, era_id):
    import json
    import shutil
    from pathlib import Path
    toba = Path(__file__).resolve().parents[2] / "episodes" / "ep_toba"
    root = tmp_path / "ep_toba"
    (root / "story").mkdir(parents=True)
    man = json.loads((toba / "episode.json").read_text(encoding="utf-8"))
    if era_id is None:
        man["historical_period"].pop("era_id")
    (root / "episode.json").write_text(json.dumps(man), encoding="utf-8")
    shutil.copy(toba / "story" / "production_script.json", root / "story" / "production_script.json")
    return root


def test_g4_takes_the_era_from_the_manifest_and_fails_without_it(tmp_path):
    from explainer_engine.episode import run as RUN
    ep = RUN.Episode(_toba_episode(tmp_path, "keep"))
    rows, _ = RUN.stage_sound_plan(ep, True)
    era = next(r for r in rows if r["gate"] == "era_from_the_manifest")
    beds = next(r for r in rows if r["gate"] == "beds_authored_per_place")
    assert era["status"] == "PASS" and "prehistoric_pleistocene" in era["detail"] and "(manifest)" in era["detail"]
    assert beds["status"] == "PASS"                        # the four Toba places carry their authored beds (P3)
    ep2 = RUN.Episode(_toba_episode(tmp_path / "b", None))
    rows2, _ = RUN.stage_sound_plan(ep2, True)
    era2 = next(r for r in rows2 if r["gate"] == "era_from_the_manifest")
    assert era2["status"] == "FAIL"


def test_two_builds_in_one_process_share_no_state():
    """FA-18: the per-shot decisions, candidates and heard-not-seen classes live in the build, not in module globals."""
    a = _script(["the hearth fire crackles"])
    b = _script(["a quiet empty field"])
    b["shots"][0]["shot_id"] = "A0"
    pa = SP.build(a, era="bronze_age")
    pb = SP.build(b, era="bronze_age")
    assert pa["shots"][0]["candidates"] != pb["shots"][0]["candidates"] or not pa["shots"][0]["candidates"]
    assert SP.build(a, era="bronze_age")["shots"][0] == pa["shots"][0]       # same input, same row, whatever ran between
    assert not any(n.startswith("_") and n.isupper() for n in ("_HEARD", "_DECISIONS", "_CANDIDATES") if hasattr(SP, n))
