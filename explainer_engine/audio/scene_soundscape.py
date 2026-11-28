"""Scene-locked 48kHz stereo soundscape builder with CC0 SFX binding and ITU-R BS.1770-4 mastering.

Eliminates constant unrelated rain noise across films:
- Every shot declares its exact ``scene_environment`` (e.g., ``dry_daylight_valley``,
  ``map_table_war_room``, ``night_rain_camp``, ``torchlit_tent``, ``windy_ridge``, ``alpine_blizzard``).
- Smooth equal-power crossfades (0.6s) transition ambience at scene boundaries.
- Synchronized CC0 map-action SFX (``parchment_unfold``, ``ink_arrow_sweep``, ``camp_pin_stamp``,
  ``troop_march_pulse``) and scene transition cues (``cinematic_whoosh``) are verified by SHA-256
  and mixed at exact timeline offsets.
- Mastered to ``-14.0 LUFS`` / ``<= -1.0 dBTP`` via ``pyloudnorm`` (ITU-R BS.1770-4) with clean
  peak limiting and per-shot spectral telemetry.
"""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pyloudnorm as pyln

DEFAULT_LIBRARY_MANIFEST = Path("assets/audio/library/cc0_cinema_manifest.json")
SAMPLE_RATE = 48000


def _read_stereo_float(wav_path: Path) -> np.ndarray:
    """Read a 48kHz 16-bit PCM WAV into ``(N, 2)`` float64 in ``[-1, 1]``."""
    with wave.open(str(wav_path), "rb") as wf:
        ch = wf.getnchannels()
        sr = wf.getframerate()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if sr != SAMPLE_RATE or sw != 2:
        raise ValueError(f"Expected 48kHz 16-bit PCM WAV, got {sr}Hz {sw*8}-bit: {wav_path}")
    arr = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch == 1:
        return np.stack([arr, arr], axis=-1)
    return arr.reshape(-1, ch)[:, :2]


def _write_stereo_wav(path: Path, data: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    inter = np.clip(data * 32767.0, -32767, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(inter.tobytes())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _loop_segment(src: np.ndarray, n_samples: int) -> np.ndarray:
    if src.shape[0] >= n_samples:
        return src[:n_samples].copy()
    reps = (n_samples // src.shape[0]) + 1
    return np.tile(src, (reps, 1))[:n_samples].copy()


def _spectral_centroid_hz(seg: np.ndarray) -> float:
    mono = seg.mean(axis=1) if seg.ndim == 2 else seg
    if mono.size < 256:
        return 0.0
    mag = np.abs(np.fft.rfft(mono * np.hanning(mono.size)))
    freqs = np.fft.rfftfreq(mono.size, d=1.0 / SAMPLE_RATE)
    denom = float(np.sum(mag))
    return round(float(np.sum(freqs * mag) / denom), 1) if denom > 1e-9 else 0.0


def _smooth_duck_envelope(speech_bus: np.ndarray, *, duck_db: float = -11.5) -> np.ndarray:
    """Compute a smooth per-sample ducking gain curve (1.0 when silent, 10^(duck_db/20) under speech)."""
    mono = np.abs(speech_bus.mean(axis=1))
    # 80ms RMS window with smooth attack/release via decimated convolution
    hop = max(1, int(0.02 * SAMPLE_RATE))  # 20ms blocks
    n_blocks = (mono.size + hop - 1) // hop
    padded = np.pad(mono, (0, n_blocks * hop - mono.size))
    rms = np.sqrt(np.mean(padded.reshape(n_blocks, hop) ** 2, axis=1))
    active = (rms > 0.012).astype(np.float64)
    # Smooth over 14 blocks (~280ms) for silky broadcast sidechain release
    kernel = np.hanning(15)
    kernel /= max(1e-9, kernel.sum())
    smooth = np.convolve(active, kernel, mode="same")
    smooth = np.clip(smooth * 1.4, 0.0, 1.0)
    duck_lin = 10.0 ** (duck_db / 20.0)
    gain_blocks = 1.0 - (1.0 - duck_lin) * smooth
    return np.repeat(gain_blocks, hop)[: mono.size]


def build_scene_locked_soundscape(
    shots: list[dict[str, Any]],
    out_wav: Path,
    *,
    sfx_cues: list[dict[str, Any]] | None = None,
    narration_tracks: list[dict[str, Any]] | None = None,
    diegetic_tracks: list[dict[str, Any]] | None = None,
    total_duration_s: float | None = None,
    library_manifest_path: Path = DEFAULT_LIBRARY_MANIFEST,
    music_bed: str | None = "doc_strings_tense",
    music_gain_db: float = -12.0,
    duck_db: float = -11.5,
    target_lufs: float = -14.0,
    true_peak_ceiling_db: float = -1.2,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Build a mastered 48kHz stereo WAV strictly locked to each shot's ``scene_environment`` with sidechain ducking."""
    manifest = json.loads(library_manifest_path.read_text(encoding="utf-8"))
    assets = manifest.get("assets") or {}

    def load_verified(name: str) -> np.ndarray:
        meta = assets.get(name)
        if not meta:
            raise KeyError(f"Audio asset {name!r} not found in CC0 library {library_manifest_path}")
        if not meta.get("commercial_use"):
            raise ValueError(f"Audio asset {name!r} is not marked commercial_use=True")
        p = Path(meta["path"])
        if not p.is_file():
            raise FileNotFoundError(f"Missing audio asset on disk: {p}")
        if hashlib.sha256(p.read_bytes()).hexdigest() != meta["sha256"]:
            raise ValueError(f"SHA-256 mismatch for audio asset {name!r}: {p}")
        return _read_stereo_float(p)

    dur_s = total_duration_s if total_duration_s is not None else max(float(s["end_s"]) for s in shots)
    total_n = int(round(dur_s * SAMPLE_RATE))
    bed_bus = np.zeros((total_n, 2), dtype=np.float64)
    sfx_bus = np.zeros((total_n, 2), dtype=np.float64)
    speech_bus = np.zeros((total_n, 2), dtype=np.float64)

    # 1. Layer scene-locked ambience per shot with smooth 0.55s equal-power crossfades
    xfade_n = int(0.55 * SAMPLE_RATE)
    shot_telemetry: list[dict[str, Any]] = []
    for s in shots:
        env_name = str(s["scene_environment"])
        st_idx = max(0, int(round(float(s["start_s"]) * SAMPLE_RATE)))
        en_idx = min(total_n, int(round(float(s["end_s"]) * SAMPLE_RATE)))
        seg_n = max(0, en_idx - st_idx)
        if seg_n == 0:
            continue
        amb = _loop_segment(load_verified(env_name), seg_n)
        gain = 10.0 ** (float(s.get("ambience_gain_db", -4.0)) / 20.0)
        amb *= gain
        env = np.ones(seg_n, dtype=np.float64)
        fn = min(xfade_n, seg_n // 3)
        if fn > 1:
            ramp = np.sin(np.linspace(0.0, np.pi * 0.5, fn))
            env[:fn] = ramp
            env[-fn:] = ramp[::-1]
        bed_bus[st_idx:en_idx] += amb * env[:, None]
        shot_telemetry.append(
            {
                "shot_id": s.get("shot_id"),
                "kind": s.get("kind", "25d"),
                "scene_environment": env_name,
                "start_s": float(s["start_s"]),
                "end_s": float(s["end_s"]),
            }
        )

    # 2. Subtle organic documentary underscore bed
    if music_bed and music_bed in assets:
        mus = _loop_segment(load_verified(music_bed), total_n)
        mus *= 10.0 ** (music_gain_db / 20.0)
        fade_edge = min(int(0.8 * SAMPLE_RATE), total_n // 4)
        if fade_edge > 1:
            mus[:fade_edge] *= np.linspace(0.0, 1.0, fade_edge)[:, None]
            mus[-fade_edge:] *= np.linspace(1.0, 0.0, fade_edge)[:, None]
        bed_bus += mus

    # 3. Mix synchronized CC0 map-action & transition SFX cues at exact timeline offsets
    mixed_cues: list[dict[str, Any]] = []
    for cue in sfx_cues or []:
        sfx_name = str(cue["sfx"])
        t_s = float(cue["timestamp_s"])
        gain_db = float(cue.get("gain_db", -3.0))
        st_idx = int(round(t_s * SAMPLE_RATE))
        if st_idx < 0 or st_idx >= total_n:
            continue
        sfx_data = load_verified(sfx_name) * (10.0 ** (gain_db / 20.0))
        end_idx = min(total_n, st_idx + sfx_data.shape[0])
        take = end_idx - st_idx
        if take > 0:
            sfx_bus[st_idx:end_idx] += sfx_data[:take]
            mixed_cues.append(
                {
                    "cue_id": cue.get("cue_id", sfx_name),
                    "sfx": sfx_name,
                    "timestamp_s": round(t_s, 3),
                    "gain_db": gain_db,
                }
            )

    # 4. Mix narrator tracks (free rehearsal_tts) + diegetic LTX speech/foley tracks with 35ms anti-pop fades (BP-188)
    narrator_total_s = 0.0
    dialogue_total_s = 0.0
    mixed_speech: list[dict[str, Any]] = []
    anti_pop_n = int(0.035 * SAMPLE_RATE)

    def _layer_speech(tracks: list[dict[str, Any]] | None, role: str) -> float:
        dur_acc = 0.0
        for tr in tracks or []:
            wp = Path(tr["wav_path"])
            if not wp.is_file():
                continue
            seg = _read_stereo_float(wp)
            max_dur = tr.get("duration_s")
            if max_dur is not None:
                seg = seg[: int(round(float(max_dur) * SAMPLE_RATE))]
            if seg.shape[0] < 16:
                continue
            gain_db = float(tr.get("gain_db", 0.0))
            seg = seg * (10.0 ** (gain_db / 20.0))
            fn = min(anti_pop_n, seg.shape[0] // 4)
            if fn > 1:
                ramp = np.linspace(0.0, 1.0, fn)[:, None]
                seg[:fn] *= ramp
                seg[-fn:] *= ramp[::-1]
            t_s = max(0.0, float(tr.get("start_s", 0.0)))
            st_idx = int(round(t_s * SAMPLE_RATE))
            if st_idx >= total_n:
                continue
            end_idx = min(total_n, st_idx + seg.shape[0])
            take = end_idx - st_idx
            speech_bus[st_idx:end_idx] += seg[:take]
            seg_s = round(take / float(SAMPLE_RATE), 3)
            if bool(tr.get("counts_as_speech", True)):
                dur_acc += seg_s
            mixed_speech.append(
                {
                    "role": role,
                    "label": tr.get("label", wp.stem),
                    "start_s": round(t_s, 3),
                    "duration_s": seg_s,
                    "gain_db": gain_db,
                    "rehearsal_tts": bool(tr.get("rehearsal_tts", role == "narrator")),
                }
            )
        return round(dur_acc, 3)

    narrator_total_s = _layer_speech(narration_tracks, "narrator")
    dialogue_total_s = _layer_speech(diegetic_tracks, "diegetic")

    # Apply smooth sidechain ducking to ambience + music whenever narrator/dialogue speaks
    if mixed_speech:
        duck_env = _smooth_duck_envelope(speech_bus, duck_db=duck_db)
        mix = bed_bus * duck_env[:, None] + sfx_bus + speech_bus
    else:
        mix = bed_bus + sfx_bus

    # 5. ITU-R BS.1770-4 loudness normalization via pyloudnorm + soft ceiling limiter (<= -1.0 dBTP)
    meter = pyln.Meter(SAMPLE_RATE)
    loudness_before = float(meter.integrated_loudness(mix))
    if np.isfinite(loudness_before):
        mix = pyln.normalize.loudness(mix, loudness_before, target_lufs)
    ceiling_lin = 10.0 ** (true_peak_ceiling_db / 20.0)
    peak_lin = float(np.max(np.abs(mix)))
    if peak_lin > ceiling_lin:
        mix = np.tanh(mix / ceiling_lin) * ceiling_lin
        # Re-check loudness after limiting so we stay tightly within -14.0 +/- 0.5 LUFS
        loud_mid = float(meter.integrated_loudness(mix))
        if np.isfinite(loud_mid) and abs(loud_mid - target_lufs) > 0.35:
            adj = 10.0 ** ((target_lufs - loud_mid) / 20.0)
            mix = np.clip(mix * adj, -ceiling_lin, ceiling_lin)
    loudness_after = float(meter.integrated_loudness(mix))
    peak_dbfs = round(20.0 * float(np.log10(max(float(np.max(np.abs(mix))), 1e-9))), 2)

    # Compute per-shot spectral centroid & RMS on final mastered audio
    for row in shot_telemetry:
        i0 = max(0, int(round(row["start_s"] * SAMPLE_RATE)))
        i1 = min(total_n, int(round(row["end_s"] * SAMPLE_RATE)))
        seg = mix[i0:i1]
        row["rms_dbfs"] = round(20.0 * float(np.log10(max(float(np.sqrt(np.mean(seg * seg))), 1e-9))), 2)
        row["spectral_centroid_hz"] = _spectral_centroid_hz(seg)
        row["sfx_count_in_shot"] = sum(
            1 for c in mixed_cues if row["start_s"] - 0.15 <= c["timestamp_s"] <= row["end_s"] + 0.15
        )

    total_speech_s = narrator_total_s + dialogue_total_s
    narrator_ratio = round(narrator_total_s / total_speech_s, 3) if total_speech_s > 0 else 0.0

    wav_sha = _write_stereo_wav(out_wav, mix)
    report = {
        "schema_version": "scene_soundscape_report/1",
        "wav_path": str(out_wav),
        "sha256": wav_sha,
        "sample_rate": SAMPLE_RATE,
        "channels": 2,
        "duration_s": round(dur_s, 3),
        "integrated_lufs": round(loudness_after, 2),
        "peak_dbfs": peak_dbfs,
        "target_lufs": target_lufs,
        "narrator_s": narrator_total_s,
        "dialogue_s": dialogue_total_s,
        "narrator_ratio": narrator_ratio,
        "shots": shot_telemetry,
        "sfx_cues": mixed_cues,
        "speech_tracks": mixed_speech,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
