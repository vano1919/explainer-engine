"""Unit tests for v5 Loop 3: Modern Underscore Guard, Strict Per-Scene Audio Isolation, 3-Stem QA Export & Headroom."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from explainer_engine.audio.broadcast_cinema_mix import mix_broadcast_cinema_audio
from explainer_engine.audio.cinematic_score import validate_music_stem
from explainer_engine.qa.cinema_gates import check_audio_scene_bleed, check_music_to_voice_headroom


def _write_noise_wav(path: Path, dur_s: float, *, sr: int = 48000, amp: float = 0.25, seed: int = 7) -> Path:
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, dur_s, int(dur_s * sr), endpoint=False, dtype=np.float32)
    sig = (amp * np.sin(2.0 * np.pi * 220.0 * t) + amp * 0.2 * rng.standard_normal(len(t))).astype(np.float32)
    stereo = np.stack([sig, sig], axis=1)
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


def test_validate_music_stem_rejects_classical_and_short_loops(tmp_path: Path) -> None:
    classical_p = _write_noise_wav(tmp_path / "beethoven_symphony_no5.wav", 50.0)
    with pytest.raises(ValueError, match="classical"):
        validate_music_stem(classical_p, modern_underscore_only=True)

    short_p = _write_noise_wav(tmp_path / "modern_tension_drone.wav", 12.0)
    with pytest.raises(ValueError, match="45.0s"):
        validate_music_stem(short_p)

    good_p = _write_noise_wav(tmp_path / "modern_tension_underscore.wav", 48.0)
    res = validate_music_stem(good_p, modern_underscore_only=True)
    assert res["status"] == "PASS"
    assert res["modern_underscore_verified"] is True


def test_strict_scene_isolation_clamps_sfx_and_exports_3_qa_stems(tmp_path: Path) -> None:
    sr = 48000
    # 12s voice track with speech in 0.5-4.5s and 6.5-10.5s
    t = np.linspace(0.0, 12.0, 12 * sr, endpoint=False, dtype=np.float32)
    v = np.zeros_like(t)
    v[int(0.5 * sr) : int(4.5 * sr)] = 0.25 * np.sin(2.0 * np.pi * 180.0 * t[int(0.5 * sr) : int(4.5 * sr)])
    v[int(6.5 * sr) : int(10.5 * sr)] = 0.25 * np.sin(2.0 * np.pi * 180.0 * t[int(6.5 * sr) : int(10.5 * sr)])
    voice_p = tmp_path / "voice.wav"
    sf.write(str(voice_p), np.stack([v, v], axis=1), sr, subtype="PCM_16")

    music_p = _write_noise_wav(tmp_path / "modern_dark_tension.wav", 48.0, amp=0.18, seed=11)
    amb1_p = _write_noise_wav(tmp_path / "amb_atrium.wav", 8.0, amp=0.12, seed=12)
    sfx_p = _write_noise_wav(tmp_path / "sfx_door.wav", 4.0, amp=0.20, seed=13)

    scene_windows = [
        {"scene_id": "scene_atrium", "start_s": 0.0, "end_s": 6.0},
        {"scene_id": "scene_street", "start_s": 6.0, "end_s": 12.0},
    ]
    out_wav = tmp_path / "master.wav"
    report = mix_broadcast_cinema_audio(
        total_duration_s=12.0,
        voice_wav=voice_p,
        music_acts=[{"wav_path": str(music_p), "start_s": 0.0, "end_s": 12.0, "level_dbfs": -44.0}],
        scene_ambiences=[
            {"shot_id": "a1", "wav_path": str(amb1_p), "start_s": 0.0, "end_s": 6.0, "l_cut_tail_s": 3.0, "level_dbfs": -38.0}
        ],
        sfx_events=[
            {"label": "door_thud", "wav_path": str(sfx_p), "time_s": 5.2, "max_duration_s": 4.0, "level_dbfs": -28.0}
        ],
        out_wav=out_wav,
        scene_windows=scene_windows,
        strict_scene_isolation=True,
        max_scene_bleed_s=0.25,
        export_qa_stems=True,
        min_music_raw_duration_s=45.0,
    )

    assert report["clamped_sfx_count"] == 1
    assert report["shots"][0]["effective_end_s"] <= 6.25
    assert Path(report["qa_stems"]["music_only"]).is_file()
    assert Path(report["qa_stems"]["sfx_amb_only"]).is_file()
    assert Path(report["qa_stems"]["voice_plus_bed"]).is_file()

    # Verify zero SFX/ambience energy remains inside Scene 2 after 6.30s!
    sfx_amb, _ = sf.read(report["qa_stems"]["sfx_amb_only"], dtype="float32")
    scene2_tail = sfx_amb[int(6.35 * sr) :]
    assert float(np.max(np.abs(scene2_tail))) < 1e-4

    # Verify music-to-voice headroom sits cleanly inside [22, 38] dB!
    hr = check_music_to_voice_headroom(voice_p, Path(report["qa_stems"]["music_only"]))
    assert hr["status"] == "PASS", hr


def test_check_audio_scene_bleed_catches_overflow() -> None:
    scenes = [{"scene_id": "s1", "start_s": 0.0, "end_s": 10.0}, {"scene_id": "s2", "start_s": 10.0, "end_s": 20.0}]
    bad = check_audio_scene_bleed(
        sfx_events=[{"label": "wolf_growl", "time_s": 8.0, "max_duration_s": 6.0}],
        scene_ambiences=[{"shot_id": "amb1", "start_s": 0.0, "end_s": 10.0, "l_cut_tail_s": 0.2}],
        scene_windows=scenes,
        max_bleed_s=0.35,
    )
    assert bad["status"] == "FAIL"
    assert len(bad["bleed_violations"]) == 1

    good = check_audio_scene_bleed(
        sfx_events=[{"label": "door_thud", "time_s": 8.0, "effective_end_s": 10.20}],
        scene_ambiences=[{"shot_id": "amb1", "start_s": 0.0, "end_s": 10.0, "effective_end_s": 10.25}],
        scene_windows=scenes,
        max_bleed_s=0.35,
    )
    assert good["status"] == "PASS"
