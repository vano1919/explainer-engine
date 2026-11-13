"""FA-05 (Fable audit 2026-11-13): the sound guides and the production script schema agree. A script written exactly by
guide v2 (a shot's intentional_silence, a sound event's class and at_word, a segment's mood and music) validates, and the
sound plan reaches INTENTIONAL_SILENCE and the authored mood from it."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from explainer_engine.episode import sound_plan as SP

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
TOBA = ROOT / "episodes" / "ep_toba" / "story" / "production_script.json"


def _guide_script() -> tuple[dict, str, str]:
    doc = json.loads(TOBA.read_text(encoding="utf-8"))
    talk = [s for s in doc["shots"] if s["route"] == "still_25d" and s.get("audio_line_ids")]
    quiet, loud = talk[0], talk[1]
    quiet["intentional_silence"] = "the moment after the blast: only room tone"
    lid = loud["audio_line_ids"][0]
    loud["sound_events"] = [
        {"kind": "spot", "what": "eruption_boom", "class": "eruption_boom",
         "at_word": {"line_id": lid, "word": 0, "offset_s": 0.1}, "distance": "distant", "purpose": "sync"},
        {"kind": "ambience", "what": "wind", "class": "wind", "at_s": 0.0}]
    doc["segments"][0].update(mood="tense", music=True)
    doc["segments"][1].update(mood="peaceful", music=False)
    return doc, quiet["shot_id"], loud["shot_id"]


def test_a_script_written_by_guide_v2_validates():
    doc, _, _ = _guide_script()
    errs = list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(doc))
    assert errs == [], [e.message[:120] for e in errs[:5]]


def test_the_guide_fields_reach_the_sound_plan():
    doc, quiet, loud = _guide_script()
    plan = SP.build(doc)
    by = {s["shot_id"]: s for s in plan["shots"]}
    assert by[quiet]["design"]["state"] == "INTENTIONAL_SILENCE"
    assert any(e["class"] == "eruption_boom" for e in by[loud]["events"])
    assert plan["segment_moods"]["S01"] == {"mood": "tense", "basis": "authored", "music": True,
                                           "music_reason": "authored music=True"}
    assert plan["segment_moods"]["S02"]["music"] is False


def test_silence_true_and_an_unknown_mood_are_refused():
    seg = SCHEMA["$defs"]["ProductionScriptV4"]["properties"]["segments"]["items"]["properties"]
    assert set(seg["mood"]["enum"]) == set(SP.MOOD_NAMES)
    shot = SCHEMA["$defs"]["ShotSpec"]["properties"]
    v = jsonschema.Draft202012Validator(shot["intentional_silence"])
    assert list(v.iter_errors(True)) and not list(v.iter_errors("the room after the fall"))
    assert list(jsonschema.Draft202012Validator(seg["mood"]).iter_errors("happy"))


def test_the_guides_name_only_schema_fields():
    """Both guide copies in the repo (docs/SOUND_GUIDE_*.md) carry the corrected section: class is a schema key, at_word exists."""
    for name in ("SOUND_INTEGRATION_GUIDE_v1.md", "SOUND_INTEGRATION_GUIDE_v2.md"):
        text = (ROOT / "docs" / "sound_guides" / name).read_text(encoding="utf-8")
        assert "There is no `class` key in the schema" not in text
        assert "at_word" in text and "intentional_silence" in text and '"mood"' in text
