"""stage_guard on the v4.3 episode script (Fable audit 2026-11-13, P2, FA-03): every new field has one owning stage, and a
later stage that rewrites another stage's field is named (docs/STORY_ENGINE.md, "The v4.3 episode script: who owns the new
fields")."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from explainer_engine.scripting import stage_guard as SG

ROOT = Path(__file__).resolve().parents[2]
TOBA = ROOT / "episodes" / "ep_toba" / "story" / "production_script.json"


def _doc() -> dict:
    return json.loads(TOBA.read_text(encoding="utf-8"))


def test_the_toba_script_is_read_as_v4() -> None:
    assert SG.is_v4(_doc())
    assert not SG.is_v4({"segments": [], "voice": {}})


def test_each_new_field_has_its_owner() -> None:
    want = {
        "shots[s01].sound_events": "beats", "shots[s01].intentional_silence": "beats",
        "shots[s01].sound_design": "beats", "shots[s01].audio_line_ids": "writer",
        "shots[s01].edit_plan": "editor", "shots[s01].actions": "editor", "segments[g1].mood": "editor",
        "segments[g1].music": "editor", "segments[g1].purpose": "architect", "audio_lines[l1].text": "writer",
        "audio_lines[l1].delivery_direction": "performer",
        "world_bible.characters[kael].voice_description": "caster",
        "world_bible.locations[cave].ambience_bed": "architect", "av_contract": "editor",
        "visual_mix_target": "editor", "shorts": "shorts", "title": "architect",
    }
    for path, stage in want.items():
        assert SG.owner_v4(path) == stage, path


def test_brackets_are_literal_not_a_character_class() -> None:
    assert SG._match("shots[s01].sound_events", "shots[*].sound_events")
    assert not SG._match("shotsX.sound_events", "shots[*].sound_events")


def test_the_beat_writer_may_write_sound_events_but_not_the_edit_plan() -> None:
    before = _doc()
    after = copy.deepcopy(before)
    shot = after["shots"][0]
    shot["sound_events"] = [{"what": "a stick snaps", "class": "wood_snap", "at_word": "stick"}]
    assert SG.violations("beats", before, after) == []
    shot["edit_plan"] = {"continuity_mode": "insert"}
    found = SG.violations("beats", before, after)
    assert len(found) == 1 and "edit_plan" in found[0] and "editor" in found[0]


def test_the_editor_may_not_change_frozen_words_or_add_a_line() -> None:
    before = _doc()
    after = copy.deepcopy(before)
    after["audio_lines"][0]["text"] = "Something else entirely."
    after["audio_lines"].append({"line_id": "zz_new", "text": "New.", "speaker_type": "narrator"})
    found = SG.violations("editor", before, after)
    assert any("text" in f and "writer" in f for f in found)
    assert any("[+zz_new]" in f for f in found)


def test_the_caster_owns_only_the_voice_of_a_character() -> None:
    before = _doc()
    after = copy.deepcopy(before)
    ch = after["world_bible"]["characters"][0]
    ch["voice_description"] = "a low, slow male voice, mid-thirties, a little hoarse"
    assert SG.violations("caster", before, after) == []
    ch["name"] = ch.get("name", "") + "x"
    assert any(".name" in f and "architect" in f for f in SG.violations("caster", before, after))


def test_reordering_shots_is_the_editors() -> None:
    before = _doc()
    after = copy.deepcopy(before)
    after["shots"][0], after["shots"][1] = after["shots"][1], after["shots"][0]
    assert SG.violations("editor", before, after) == []
    assert any("shots[order]" in f for f in SG.violations("writer", before, after))
