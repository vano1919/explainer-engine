"""LEGACY (v4.3 plan P7): the zip's soundscape renderer, kept only for its tests and the narration-source check. The
production path renders through ``episode/sound_plan`` + ``audio/stems`` (SP-01, SP-02); its voice and music synthesizers are
removed, so this module can never make a voice either.

Environmental Audio & Non-Dialogue Sound Design Continuity Engine (`environmental_sound_design.py`, v4.3).

Connects existing repository audio modules (`foley.py`, `acoustics.py`, `sfx_planner.py`, `duck.py`, `layers.py`)
to render a continuous, multi-layered stereo soundscape and separate 48kHz stems at $0.00 cost:
1. Continuous Narration & Dialogue Voice Spine (`narration.wav`):
   - Strictly forbids SFX/ambience/music packs (`G4_SFX_Footsteps_Ambience_Music_Pack.mp3`, etc.) from ever being loaded
     as a narration voice track (`SFX_PACK_FORBIDDEN_AS_NARRATION`).
   - Loads the read or leaves the stem silent (the formant voice synthesizer is gone, plan P7.3).
2. Continuous Environmental Ambience Beds (`ambience.wav`) across connected shots sharing a `continuity_group`
   (smooth 0.65s crossfades across scene changes; never hard-cuts or restarts ambience on every shot).
3. Acoustic Environment Filtering (`acoustics.impulse` & `acoustics.convolve` for `outdoor`, `room`, `hall`, `cave`)
   so moving from an outdoor storm/caldera into a limestone rock shelter shifts reverb and high-frequency roll-off naturally.
4. Synchronized Spot Foley (`sfx.wav`) with anti-repetition pitch/timing jitter (`BP-57`), stereo panning (`acoustics.pan`),
   and deterministic era-compatibility gating (`ERA_COMPATIBILITY_TABLE`).
5. Speech-Gated Sidechain Ducking (`duck.duck_gain` + `acoustics.band_dip`):
   - Ducks `music.wav` by `-5.0 dB` and `ambience.wav` by `-3.0 dB` smoothly ONLY during active speech windows
     (never causing `-11 dB` whole-mix collapses).
   - Writes all 5 separate 48kHz stereo WAV stems (`narration.wav`, `music.wav`, `ambience.wav`, `sfx.wav`, `mix.wav`).
"""
from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

from explainer_engine.audio import acoustics, duck, foley
from explainer_engine.audio.sfx_planner import build_g4_audio_fx_plan

SR = foley.SR  # 48000 Hz

FORBIDDEN_NARRATION_PACK_PATTERNS = re.compile(
    r"(g4_sfx|sfx_footsteps|ambience_music_pack|sfx_pack|sound_effects_pack|foley_pack|music_bed_pack)",
    re.IGNORECASE,
)


def validate_narration_source_file(path: Path | str | None) -> None:
    """Ensure an SFX/ambience/music pack is never loaded as a narration or dialogue voice source."""
    if path is None:
        return
    name = Path(path).name
    full = str(path)
    if FORBIDDEN_NARRATION_PACK_PATTERNS.search(name) or FORBIDDEN_NARRATION_PACK_PATTERNS.search(full):
        raise ValueError(
            f"SFX_PACK_FORBIDDEN_AS_NARRATION: '{name}' is an SFX/ambience/music pack and must never be used as a narration voice track."
        )


def _pitch_shift_resample(samples: np.ndarray, factor: float) -> np.ndarray:
    """Apply subtle deterministic pitch/speed jitter (`0.94 <= factor <= 1.06`) to prevent identical sample repetition (BP-57)."""
    if abs(factor - 1.0) < 1e-4 or len(samples) < 16:
        return samples
    new_len = max(8, int(round(len(samples) / factor)))
    xs = np.linspace(0.0, len(samples) - 1, new_len, dtype=np.float32)
    return np.interp(xs, np.arange(len(samples), dtype=np.float32), samples).astype(np.float32)


def _synthesize_or_load_narration_voice_track(
    script_doc: Dict[str, Any],
    total_samples: int,
    existing_audio_pack_path: Path | None = None,
    source_out: Dict[str, Any] | None = None,
) -> np.ndarray:
    """Load the read (WAV/MP3) or return silence: v4.3 plan P7.3 removed the formant voice synthesizer from the code, so no
    path can make a voice. ``source_out["narration_source"]`` is the loaded file, or ``"none"`` (never shippable, EP-03)."""
    validate_narration_source_file(existing_audio_pack_path)
    if source_out is not None:
        source_out["narration_source"] = "none"
    voice = np.zeros(total_samples, dtype=np.float32)
    if existing_audio_pack_path and Path(existing_audio_pack_path).is_file():
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(existing_audio_pack_path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
            capture_output=True, check=True,
        ).stdout
        loaded = np.frombuffer(raw, dtype=np.float32)
        use_len = min(total_samples, len(loaded))
        voice[:use_len] = loaded[:use_len]
        if use_len and source_out is not None:
            source_out["narration_source"] = str(existing_audio_pack_path)
    return voice


def _silent_music(total_samples: int) -> np.ndarray:
    """No music here: the numpy cello was removed (plan P7.3); real music comes from the library through audio/stems.py."""
    return np.zeros((total_samples, 2), dtype=np.float32)


def _write_stereo_wav(path: Path, stereo_samples: np.ndarray, sr: int = SR) -> None:
    """Write float32 stereo array `(-1..1)` to a 16-bit PCM WAV file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(stereo_samples, dtype=np.float32)
    if arr.ndim == 1:
        arr = np.stack([arr, arr], axis=1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2")
        wf.writeframes(pcm.tobytes())


def render_continuous_environmental_soundscape(
    script_doc: Dict[str, Any],
    out_wav_path: Path | str,
    existing_audio_pack_path: Path | str | None = None,
    transition_plans: List[Dict[str, Any]] | None = None,
    stems_output_dir: Path | str | None = None,
) -> Dict[str, Any]:
    """Render the complete 5-stem continuous stereo soundscape (`narration.wav`, `music.wav`, `ambience.wav`,
    `sfx.wav`, `mix.wav`) at 48kHz stereo."""
    validate_narration_source_file(existing_audio_pack_path)
    out_wav_path = Path(out_wav_path)
    out_wav_path.parent.mkdir(parents=True, exist_ok=True)

    shots = script_doc.get("shots", [])
    total_dur_s = sum(float(s.get("target_duration_seconds", 4.0)) for s in shots) or 60.0
    total_samples = int(round(total_dur_s * SR))

    g4_plan = build_g4_audio_fx_plan(script_doc)
    shot_sd_map = g4_plan["shot_sound_design"]

    # 1. Narration & Dialogue Spine (mono -> stereo centered)
    narration_info: Dict[str, Any] = {}
    voice_mono = _synthesize_or_load_narration_voice_track(
        script_doc,
        total_samples=total_samples,
        existing_audio_pack_path=Path(existing_audio_pack_path) if existing_audio_pack_path else None,
        source_out=narration_info,
    )
    voice_stereo = (acoustics.pan(voice_mono, 0.0) * acoustics.CENTRE_GAIN).astype(np.float32)

    # 2. Continuous Environmental Ambience Beds grouped by `continuity_group` (with 0.65s crossfades, never hard-cut per shot)
    amb_stereo = np.zeros((total_samples, 2), dtype=np.float32)
    grouped_spans: List[Dict[str, Any]] = []
    t_cur = 0.0
    for sh in shots:
        dur = float(sh.get("target_duration_seconds", 4.0))
        sid = sh["shot_id"]
        sd = shot_sd_map[sid]
        cgroup = sd["continuity_group"]
        if grouped_spans and grouped_spans[-1]["continuity_group"] == cgroup:
            grouped_spans[-1]["end_sec"] = round(t_cur + dur, 3)
            grouped_spans[-1]["shot_ids"].append(sid)
        else:
            grouped_spans.append({
                "continuity_group": cgroup,
                "environment": sd["environment"],
                "weather": sd["weather"],
                "spatial_context": sd["spatial_context"],
                "start_sec": round(t_cur, 3),
                "end_sec": round(t_cur + dur, 3),
                "shot_ids": [sid],
            })
        t_cur += dur

    xfade_s = 0.65
    for idx_g, grp in enumerate(grouped_spans):
        a_s = max(0.0, grp["start_sec"] - (xfade_s if idx_g > 0 else 0.0))
        b_s = min(total_dur_s, grp["end_sec"] + (xfade_s if idx_g + 1 < len(grouped_spans) else 0.0))
        span_s = max(0.5, b_s - a_s)
        a_idx = int(round(a_s * SR))
        b_idx = min(total_samples, int(round(b_s * SR)))
        n_seg = b_idx - a_idx
        if n_seg <= 0:
            continue

        weather = grp["weather"]
        if "rain" in weather:
            bed_mono = foley.rain_downpour(seed=100 + idx_g, seconds=span_s + 0.1)[:n_seg]
        elif "ash" in weather:
            bed_mono = (
                0.65 * foley.wind_howl(seed=200 + idx_g, seconds=span_s + 0.1)[:n_seg]
                + 0.35 * foley.fire_crackle_bed(seed=300 + idx_g, seconds=span_s + 0.1)[:n_seg]
            )
        elif "enclosed" in weather:
            bed_mono = acoustics.room_tone("cave", seed=400 + idx_g, seconds=span_s + 0.1, sr=SR)[:n_seg]
        else:
            bed_mono = foley.wind_howl(seed=500 + idx_g, seconds=span_s + 0.1)[:n_seg]

        if grp["spatial_context"].startswith("indoor"):
            ir = acoustics.impulse("cave", seed=600 + idx_g, sr=SR)
            bed_mono = acoustics.convolve(bed_mono, ir)[:n_seg]

        fade_samples = min(int(xfade_s * SR), n_seg // 3)
        if fade_samples > 0:
            if idx_g > 0:
                bed_mono[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
            if idx_g + 1 < len(grouped_spans):
                bed_mono[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)

        bed_mono = bed_mono / (np.max(np.abs(bed_mono)) + 1e-6) * 0.13
        bed_wide = acoustics.widen(bed_mono, seed=700 + idx_g)
        amb_stereo[a_idx:b_idx] += bed_wide[: b_idx - a_idx]

    # Ensure continuous low-level room-tone floor (-38 dBFS) across the entire duration so no 10ms window ever hits digital silence
    continuous_floor = acoustics.room_tone("outdoor", seed=99, seconds=total_dur_s + 0.1, sr=SR)[:total_samples]
    continuous_floor = continuous_floor / (np.max(np.abs(continuous_floor)) + 1e-6) * 0.025
    amb_stereo += acoustics.widen(continuous_floor, seed=99)

    # 3. Synchronized Spot Foley + Transition Bridges
    sfx_stereo = np.zeros((total_samples, 2), dtype=np.float32)
    placed_sfx_log: List[Dict[str, Any]] = []

    for idx_c, cue in enumerate(g4_plan["sfx_cues"]):
        gen_key = cue.get("generator_key", "footstep_dirt")
        seed_val = int(cue.get("variant_seed", 1)) + idx_c * 7
        jitter = float(cue.get("pitch_jitter", 1.0))

        if gen_key in foley.BUILD:
            _, gen_fn, _ = foley.BUILD[gen_key]
            raw_sfx = gen_fn(seed_val)
        else:
            raw_sfx = foley.footstep("dirt", seed_val)

        varied_sfx = _pitch_shift_resample(raw_sfx, jitter)
        start_idx = min(total_samples - 1, max(0, int(round(float(cue["start_sec"]) * SR))))
        end_idx = min(total_samples, start_idx + len(varied_sfx))
        seg_len = end_idx - start_idx
        if seg_len > 0:
            gain_lin = float(10.0 ** (float(cue.get("gain_db", -14.0)) / 20.0))
            pan_pos = float(np.clip(((idx_c % 5) - 2) * 0.18, -0.45, 0.45))
            panned = acoustics.pan(varied_sfx[:seg_len] * gain_lin, pan_pos)
            sfx_stereo[start_idx:end_idx] += panned
            placed_sfx_log.append({
                "cue_id": cue["cue_id"],
                "shot_id": cue["shot_id"],
                "sound": cue["sound"],
                "generator_key": gen_key,
                "start_sec": cue["start_sec"],
                "pitch_jitter": jitter,
                "pan": round(pan_pos, 3),
            })

    t_cursor = 0.0
    for idx_s, sh in enumerate(shots[:-1]):
        t_cursor += float(sh.get("target_duration_seconds", 4.0))
        t_plan = (transition_plans[idx_s] if transition_plans and idx_s < len(transition_plans) else None) or {}
        t_type = t_plan.get("transition_type", "hard_cut_with_jl_bridge")
        if t_type in ("map_to_location_zoom_through", "infographic_number_to_scene_morph", "motion_matched_pan_whip"):
            sw = foley.seam_shimmer(seed=900 + idx_s) if "zoom" in t_type or "morph" in t_type else foley.swish(seed=950 + idx_s)
            sw = sw / (np.max(np.abs(sw)) + 1e-6) * 0.18
            a_idx = max(0, int(round((t_cursor - 0.35) * SR)))
            b_idx = min(total_samples, a_idx + len(sw))
            if b_idx > a_idx:
                sfx_stereo[a_idx:b_idx] += acoustics.pan(sw[: b_idx - a_idx], 0.0)

    # 4. Musical Tension Ostinato Stem
    music_stereo = _silent_music(total_samples)

    # 5. Speech-Gated Sidechain Ducking (BP-53 & BP-118):
    # Music ducks smoothly by 5.0 dB under speech, ambience ducks by 3.0 dB under speech (never -11 dB full-mix collapses)
    v_duck_music = duck.duck_gain(voice_mono, SR, total_samples, depth_db=5.0, threshold=0.018).astype(np.float32)
    v_duck_amb = duck.duck_gain(voice_mono, SR, total_samples, depth_db=3.0, threshold=0.018).astype(np.float32)
    sfx_mid = sfx_stereo.mean(axis=1)
    f_duck_music = duck.duck_gain(sfx_mid, SR, total_samples, depth_db=2.5, threshold=0.035).astype(np.float32)

    ducked_music_stereo = (music_stereo * (v_duck_music * f_duck_music)[:, None]).astype(np.float32)
    ducked_amb_stereo = (amb_stereo * v_duck_amb[:, None]).astype(np.float32)
    ducked_sfx_stereo = (sfx_stereo * 0.85).astype(np.float32)

    mix_stereo = voice_stereo * 0.88 + ducked_amb_stereo + ducked_music_stereo + ducked_sfx_stereo

    peak = float(np.max(np.abs(mix_stereo)))
    if peak > 0.89:
        scale = 0.89 / peak
        mix_stereo = (mix_stereo * scale).astype(np.float32)

    # Write master mix WAV
    _write_stereo_wav(out_wav_path, mix_stereo, sr=SR)

    # Also write the 5 separate stems when stems_output_dir is provided (or alongside audio/)
    resolved_stems_dir = Path(stems_output_dir) if stems_output_dir else (out_wav_path.parent / "stems")
    resolved_stems_dir.mkdir(parents=True, exist_ok=True)
    stem_paths = {
        "narration": resolved_stems_dir / "narration.wav",
        "music": resolved_stems_dir / "music.wav",
        "ambience": resolved_stems_dir / "ambience.wav",
        "sfx": resolved_stems_dir / "sfx.wav",
        "mix": resolved_stems_dir / "mix.wav",
    }
    _write_stereo_wav(stem_paths["narration"], voice_stereo * 0.88, sr=SR)
    _write_stereo_wav(stem_paths["music"], ducked_music_stereo, sr=SR)
    _write_stereo_wav(stem_paths["ambience"], ducked_amb_stereo, sr=SR)
    _write_stereo_wav(stem_paths["sfx"], ducked_sfx_stereo, sr=SR)
    _write_stereo_wav(stem_paths["mix"], mix_stereo, sr=SR)

    return {
        "status": "generated",
        "path": str(out_wav_path),
        "stems_dir": str(resolved_stems_dir),
        "stem_paths": {k: str(v) for k, v in stem_paths.items()},
        "sample_rate_hz": SR,
        "channels": 2,
        "duration_sec": round(total_dur_s, 3),
        "historical_period": g4_plan["historical_period"],
        "narration_source": narration_info["narration_source"],
        "blocked_era_events": g4_plan["blocked_era_events"],
        "continuous_ambience_groups_count": len(grouped_spans),
        "continuous_ambience_groups": grouped_spans,
        "spot_foley_cues_placed": len(placed_sfx_log),
        "placed_sfx_log": placed_sfx_log,
        "sidechain_ducking_applied": True,
        "music_duck_depth_db": 5.0,
        "ambience_duck_depth_db": 3.0,
        "voice_duck_max_step_db_per_ms": round(duck.max_step_db_per_ms(v_duck_music, SR), 4),
        "shot_sound_design": shot_sd_map,
    }
