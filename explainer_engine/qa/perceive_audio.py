"""Layered audio perception and stem/mix verification (Task 2 R2 Step 6, Decision 5 & P4).

Implements the three-layer audio verification stack required by the R2 plan:
1. Layer 1 (Mandatory DSP): waveform RMS, LUFS approximation, true-peak clipping check, silence/dropout share, spectral
   band balance (low wind/rumble ``80-500 Hz``, vocal presence ``1000-4000 Hz``, fire crackle/air ``2500-8000 Hz``), and
   J-cut bridge verification (e.g. ``YF-Q2`` faint cough in freezing trench wind over the last ~1.5 s of ``S02_SH003``).
2. Layer 2 (Coarse Event Classification): ``YAMNet`` (521 AudioSet classes on 0.975 s windows) and ``AST``
   (``MIT/ast-finetuned-audioset-10-10-0.4593``), with deterministic spectral signature fallback when running offline.
3. Layer 3 (Optional Semantic Similarity): ``LAION-AI/CLAP`` (``laion/clap-htsat-unfused``) advisory score.
Human (Claude) listening remains the final acceptance authority.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "audio_perception_result/1.0"


def read_wav_mono(path: Path | str) -> tuple[np.ndarray, int]:
    """Read a WAV file and return ``(mono_float32_minus1_to_1, sample_rate)``."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(n)
    if sw == 2:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        arr = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    if ch > 1:
        arr = arr.reshape(-1, ch).mean(axis=1)
    return arr, int(sr)


def _dbfs(val: float) -> float:
    return round(20.0 * math.log10(max(1e-7, float(val))), 2)


def analyze_dsp_layers(samples: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute Layer 1 deterministic waveform and spectral metrics on mono float32 ``samples``."""
    if samples.size == 0:
        return {
            "duration_s": 0.0,
            "rms_dbfs": -120.0,
            "lufs_approx": -120.0,
            "peak_dbfs": -120.0,
            "clipped_share": 0.0,
            "digital_silence_share": 1.0,
            "bands_db": {"low_wind_80_500hz": -120.0, "vocal_1k_4khz": -120.0, "crackle_2k5_8khz": -120.0},
        }
    dur_s = round(float(samples.size) / max(1, sr), 3)
    rms = float(np.sqrt(np.mean(samples * samples)))
    peak = float(np.max(np.abs(samples)))
    clipped = float(np.mean(np.abs(samples) >= 0.999))

    win = max(1, int(0.05 * sr))
    n_win = max(1, samples.size // win)
    trimmed = samples[: n_win * win].reshape(n_win, win)
    win_rms = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    silence_share = round(float(np.mean(win_rms < 10 ** (-65.0 / 20.0))), 4)

    # Spectral bands via rFFT
    spec = np.abs(np.fft.rfft(samples)) / max(1, samples.size)
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / max(1, sr))

    def band_db(f_lo: float, f_hi: float) -> float:
        m = (freqs >= f_lo) & (freqs <= f_hi)
        if not m.any():
            return -120.0
        return _dbfs(float(np.sqrt(np.mean(spec[m] ** 2))))

    rms_db = _dbfs(rms)
    return {
        "duration_s": dur_s,
        "rms_dbfs": rms_db,
        "lufs_approx": round(rms_db - 0.691, 2),
        "peak_dbfs": _dbfs(peak),
        "clipped_share": round(clipped, 6),
        "digital_silence_share": silence_share,
        "bands_db": {
            "low_wind_80_500hz": band_db(80.0, 500.0),
            "vocal_1k_4khz": band_db(1000.0, 4000.0),
            "crackle_2k5_8khz": band_db(2500.0, 8000.0),
        },
    }


def run_yamnet(samples: np.ndarray, sr: int) -> list[dict]:
    """Run TensorFlow / TFLite YAMNet (521 classes, 0.975s windows) on CPU when available."""
    try:
        import tensorflow_hub as hub
        import scipy.signal

        if sr != 16000:
            samples_16k = scipy.signal.resample(samples, int(round(len(samples) * 16000 / sr))).astype(np.float32)
        else:
            samples_16k = samples.astype(np.float32)
        model = hub.load("https://tfhub.dev/google/yamnet/1")
        scores, _, _ = model(samples_16k)
        mean_scores = scores.numpy().mean(axis=0)
        top_idx = np.argsort(-mean_scores)[:5]
        return [{"class_index": int(i), "score": round(float(mean_scores[i]), 4), "model": "yamnet/1"} for i in top_idx]
    except Exception:
        return []


def run_ast(samples: np.ndarray, sr: int) -> list[dict]:
    """Run ``MIT/ast-finetuned-audioset-10-10-0.4593`` on CPU when local/HF weights are available."""
    try:
        import scipy.signal
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        model_id = "MIT/ast-finetuned-audioset-10-10-0.4593"
        fe = AutoFeatureExtractor.from_pretrained(model_id)
        model = AutoModelForAudioClassification.from_pretrained(model_id).eval()
        if sr != 16000:
            samples_16k = scipy.signal.resample(samples, int(round(len(samples) * 16000 / sr))).astype(np.float32)
        else:
            samples_16k = samples.astype(np.float32)
        inputs = fe(samples_16k, sampling_rate=16000, return_tensors="pt")
        with torch.inference_mode():
            logits = model(**inputs).logits[0]
        probs = torch.sigmoid(logits).numpy()
        top_idx = np.argsort(-probs)[:5]
        id2label = model.config.id2label
        return [{"label": str(id2label.get(int(i), i)), "score": round(float(probs[i]), 4), "model": model_id} for i in top_idx]
    except Exception:
        return []


def run_clap_similarity(samples: np.ndarray, sr: int, text_query: str) -> float | None:
    """Optional Layer 3 semantic audio-text similarity via ``laion/clap-htsat-unfused``."""
    if not text_query.strip():
        return None
    try:
        import scipy.signal
        import torch
        from transformers import ClapModel, ClapProcessor

        model_id = "laion/clap-htsat-unfused"
        proc = ClapProcessor.from_pretrained(model_id)
        model = ClapModel.from_pretrained(model_id).eval()
        if sr != 48000:
            samples_48k = scipy.signal.resample(samples, int(round(len(samples) * 48000 / sr))).astype(np.float32)
        else:
            samples_48k = samples.astype(np.float32)
        inputs = proc(text=[text_query], audios=[samples_48k], sampling_rate=48000, return_tensors="pt", padding=True)
        with torch.inference_mode():
            out = model(**inputs)
            sim = torch.cosine_similarity(out.audio_embeds, out.text_embeds)[0].item()
        return round(float(sim), 4)
    except Exception:
        return None


def _deterministic_spectral_tags(dsp: dict[str, Any], samples: np.ndarray, sr: int) -> list[dict]:
    """Deterministic acoustic event detector from spectral and envelope signatures when neural weights are offline."""
    tags: list[dict] = []
    if dsp["rms_dbfs"] <= -60.0:
        return [{"label": "Silence", "score": 0.99, "basis": "deterministic_dsp"}]
    bands = dsp["bands_db"]
    if bands["low_wind_80_500hz"] > -52.0:
        tags.append({"label": "Wind", "score": 0.84, "basis": "low_band_80_500hz"})
    if bands["vocal_1k_4khz"] > -45.0:
        tags.append({"label": "Speech", "score": 0.88, "basis": "vocal_band_1k_4khz"})
    if bands["crackle_2k5_8khz"] > -50.0:
        # High crest factor in 2.5-8 kHz indicates fire crackle, tactile map draw, or cough transient
        win = max(1, int(0.02 * sr))
        env = np.abs(samples[: (samples.size // win) * win]).reshape(-1, win).max(axis=1) if samples.size >= win else np.abs(samples)
        crest = float(env.max() / max(1e-6, env.mean())) if env.size else 1.0
        if crest >= 2.2:
            tags.append({"label": "Crackling_or_Foley_Transient", "score": 0.82, "basis": "high_band_transient_crest"})
    return tags


def verify_j_cut_bridge(samples: np.ndarray, sr: int, tail_s: float = 1.5) -> dict[str, Any]:
    """Verify that the final ``tail_s`` seconds of a shot (such as ``S02_SH003`` -> ``S02_SH004``, YF-Q2) carry an active
    acoustic bridge (wind + cough transient) rather than dead silence."""
    n_tail = max(1, int(round(tail_s * sr)))
    tail = samples[-n_tail:] if samples.size >= n_tail else samples
    dsp = analyze_dsp_layers(tail, sr)
    win = max(1, int(0.025 * sr))
    env = np.sqrt(np.mean(tail[: (tail.size // win) * win].reshape(-1, win) ** 2, axis=1)) if tail.size >= win else np.abs(tail)
    burst_ratio = float(env.max() / max(1e-6, np.median(env))) if env.size else 1.0
    has_wind = dsp["bands_db"]["low_wind_80_500hz"] > -55.0
    has_cough_burst = burst_ratio >= 1.45 and dsp["bands_db"]["vocal_1k_4khz"] > -52.0
    return {
        "tail_s": tail_s,
        "tail_rms_dbfs": dsp["rms_dbfs"],
        "has_wind_bed": bool(has_wind),
        "has_cough_or_foley_transient": bool(has_cough_burst),
        "burst_to_median_ratio": round(burst_ratio, 3),
        "passed": bool(dsp["rms_dbfs"] > -55.0 and (has_wind or has_cough_burst)),
    }


def perceive_audio(
    audio_input: Path | str | np.ndarray,
    *,
    sr: int = 48000,
    shot_id: str = "shot",
    expected_perspective: str = "",
    intentional_silence: str | None = None,
    classifier: str = "auto",
    run_clap: bool = False,
) -> dict[str, Any]:
    """Run layered audio perception on a WAV file or mono float32 array and return ``audio_perception_result/1.0``."""
    if isinstance(audio_input, (str, Path)):
        samples, sr = read_wav_mono(audio_input)
        source_path = str(audio_input)
    else:
        samples = np.asarray(audio_input, dtype=np.float32)
        source_path = None

    dsp = analyze_dsp_layers(samples, sr)
    neural_events: list[dict] = []
    model_used = "deterministic_dsp/1.0"
    if classifier in ("yamnet", "auto"):
        neural_events = run_yamnet(samples, sr)
        if neural_events:
            model_used = "yamnet/1"
    if not neural_events and classifier in ("ast", "auto"):
        neural_events = run_ast(samples, sr)
        if neural_events:
            model_used = "MIT/ast-finetuned-audioset-10-10-0.4593"
    if not neural_events:
        neural_events = _deterministic_spectral_tags(dsp, samples, sr)

    clap_score = run_clap_similarity(samples, sr, expected_perspective) if (run_clap and expected_perspective) else None

    if intentional_silence:
        tech_ok = dsp["clipped_share"] <= 0.0005
    else:
        tech_ok = dsp["rms_dbfs"] > -58.0 and dsp["clipped_share"] <= 0.0005 and dsp["digital_silence_share"] < 0.85

    return {
        "schema": SCHEMA,
        "shot_id": shot_id,
        "source_path": source_path,
        "model_used": model_used,
        "dsp": dsp,
        "detected_events": neural_events,
        "clap_advisory_similarity": clap_score,
        "intentional_silence": intentional_silence,
        "technical_pass": bool(tech_ok),
        "human_listen_required": True,
    }
