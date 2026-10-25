"""Library first (OR-18, D-76): the lookup record and the ElevenLabs hook's refusal of unsearched music/SFX."""

from __future__ import annotations

import json

import numpy as np
import pytest

from explainer_engine import assets_reuse as AR
from explainer_engine.audio import sfx_library
from explainer_engine.standards import hook


def _tone(seconds=0.5, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    return (np.sin(2 * np.pi * 220 * t) * 0.5).astype(np.float32)


def test_lookup_routes_to_the_sound_library(tmp_path):
    sfx_library.add(tmp_path, name="heist_tension", take=1, category="music", tags=["tense", "heist", "music"],
                    samples=_tone(), rate=16000, source={"kind": "elevenlabs"},
                    licence={"status": "generated_terms_verified", "note": "test"}, loop=True)
    assert [m["id"] for m in AR.lookup("music", ["tense"], sound_root=tmp_path)] == ["heist_tension__v1"]
    assert AR.lookup("music", ["ocean"], sound_root=tmp_path) == []
    with pytest.raises(ValueError):
        AR.lookup("video", [])


def test_record_and_has_lookup(tmp_path):
    assert not AR.has_lookup(tmp_path, "music")
    AR.record(tmp_path, kind="music", tags=["tense"], matches=[], decision="generate_new")
    assert AR.has_lookup(tmp_path, "music")
    assert not AR.has_lookup(tmp_path, "sfx")
    doc = json.loads((tmp_path / AR.RECORD_NAME).read_text())
    assert doc["lookups"][0]["decision"] == "generate_new"


def test_generate_new_over_matches_needs_a_reason(tmp_path):
    match = [{"id": "heist_tension__v1"}]
    with pytest.raises(ValueError):
        AR.record(tmp_path, kind="music", tags=["tense"], matches=match, decision="generate_new")
    AR.record(tmp_path, kind="music", tags=["tense"], matches=match, decision="generate_new", why="too bright for the scene")
    AR.record(tmp_path, kind="music", tags=["tense"], matches=match, decision="reuse")


def _root_with_episode(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "active_episode.json").write_text(json.dumps({"episode": "ep"}), encoding="utf-8")
    (tmp_path / "ep").mkdir()
    return tmp_path


def test_hook_refuses_music_generation_without_a_recorded_search(tmp_path):
    root = _root_with_episode(tmp_path)
    call = {"node_type": "music-generation", "generations_count": 1}
    reason = hook.decide("mcp__ElevenLabs__creative_generate_in_flow", call, root)
    assert reason and "OR-18" in reason
    AR.record(root / "ep", kind="music", tags=["tense"], matches=[], decision="generate_new")
    reason = hook.decide("mcp__ElevenLabs__creative_generate_in_flow", call, root)
    assert reason and "OR-11" in reason  # past the library gate; the rulebook gate still stands


def test_hook_sound_kind_and_speech_exemption(tmp_path):
    assert hook._sound_kind("x", {"node_type": "music-generation"}) == "music"
    assert hook._sound_kind("x", {"node_type": "sound-effect-generation"}) == "sfx"
    assert hook._sound_kind("x", {"model": "eleven_music_v2_5"}) == "music"
    assert hook._sound_kind("x", {"node_type": "text-to-speech"}) is None
    root = _root_with_episode(tmp_path)
    reason = hook.decide("mcp__ElevenLabs__creative_generate_speech", {"generations_count": 1}, root)
    assert reason and "OR-11" in reason  # narration is episode-bound: no library search required
