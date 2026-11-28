"""Unit tests for v5.0 Loop 2: Expressive Eleven v4 Narration, Dialogue Presence & Scene-First Routing Gates."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from explainer_engine.audio.elevenlabs_narrator import (
    _chars_to_words,
    resolve_expressive_line,
    strip_audio_tags,
)
from explainer_engine.audio.neural_narrator import build_dynamic_energy_curve
from explainer_engine.qa.cinema_gates import (
    check_dramatic_dialogue_presence,
    check_scene_first_routing,
)


def test_elevenlabs_v4_expressive_tags_and_clean_word_alignment() -> None:
    spoken, settings = resolve_expressive_line(
        {"text": "Caesar almost stayed home.", "delivery_mode": "hook_punch"},
        model_id="eleven_v4",
    )
    assert spoken.startswith("[curious, energetic, leaning in] ")
    assert strip_audio_tags(spoken) == "Caesar almost stayed home."
    assert "style" not in settings  # eleven_v4 uses stability + similarity_boost only
    assert settings["stability"] <= 0.40

    # Verify _chars_to_words skips bracketed audio tags cleanly
    sample = "[whispers] Stay home."
    chars = list(sample)
    starts = [i * 0.05 for i in range(len(chars))]
    ends = [(i + 1) * 0.05 for i in range(len(chars))]
    words = _chars_to_words(
        {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends},
        offset_s=1.0,
        fps=24,
    )
    assert [w["word"] for w in words] == ["Stay", "home"]

    curve = build_dynamic_energy_curve([{"text": "A"}, {"text": "B"}, {"text": "C"}])
    assert curve[0]["delivery_mode"] == "hook_punch"
    assert curve[-1]["delivery_mode"] == "reflective_finale"


def test_dramatic_dialogue_presence_passes_voiced_and_fails_silent_or_narrator_collision(tmp_path: Path) -> None:
    sr = 16000
    t = np.linspace(0.0, 6.0, sr * 6, endpoint=False, dtype=np.float32)
    # Voiced formant-band energy (800Hz + 1600Hz) in 0.5-2.5s and 3.5-5.5s
    sig = np.zeros_like(t)
    m1 = (t >= 0.4) & (t <= 2.6)
    m2 = (t >= 3.4) & (t <= 5.6)
    sig[m1] = 0.25 * np.sin(2 * np.pi * 800 * t[m1]) + 0.15 * np.sin(2 * np.pi * 1600 * t[m1])
    sig[m2] = 0.22 * np.sin(2 * np.pi * 900 * t[m2]) + 0.14 * np.sin(2 * np.pi * 1700 * t[m2])
    wav = tmp_path / "dialogue.wav"
    sf.write(str(wav), sig, sr)

    shots = [
        {"shot_id": "d1", "has_dialogue": True, "start_s": 0.0, "end_s": 3.0},
        {"shot_id": "d2", "has_dialogue": True, "start_s": 3.0, "end_s": 6.0},
    ]
    ok = check_dramatic_dialogue_presence(shots, wav, utterances=[])
    assert ok["status"] == "PASS", ok

    # Narrator colliding during dialogue -> FAIL
    bad_col = check_dramatic_dialogue_presence(shots, wav, utterances=[{"start_s": 1.0, "end_s": 2.0}])
    assert bad_col["status"] == "FAIL", bad_col

    # Silent staring -> FAIL
    silent_wav = tmp_path / "silent.wav"
    sf.write(str(silent_wav), np.zeros_like(t), sr)
    bad_silent = check_dramatic_dialogue_presence(shots, silent_wav, utterances=[])
    assert bad_silent["status"] == "FAIL", bad_silent


def test_scene_first_routing_rejects_one_off_ltx_slideshows() -> None:
    good = [
        {"shot_id": "s1", "route": "ltx_video", "scene_id": "atrium"},
        {"shot_id": "s2", "route": "ltx_video", "scene_id": "atrium"},
        {"shot_id": "m1", "route": "map_action", "scene_id": "rome_map"},
        {"shot_id": "e1", "route": "drawing_explainer", "scene_id": "conspiracy_chart"},
    ]
    assert check_scene_first_routing(good)["status"] == "PASS"

    bad = [
        {"shot_id": "s1", "route": "ltx_video", "scene_id": "solo_slideshow"},
        {"shot_id": "s2", "route": "ltx_video", "scene_id": "another_solo"},
    ]
    res = check_scene_first_routing(bad)
    assert res["status"] == "FAIL"
    assert len(res["findings"]) == 2
