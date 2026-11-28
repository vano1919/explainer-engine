"""Local Neural Documentary Narrator (Kokoro-ONNX + faster-whisper ASR Pronunciation & Word-Sync).

Provides ``$0.00`` studio-grade neural British documentary narration (``bm_george`` / ``bm_daniel``),
automatically verifies pronunciation accuracy & proper nouns via ``faster-whisper`` CPU ASR,
and extracts frame-accurate word timestamps (``word_timestamps.json``) for editorial cut sync,
motion bridges, and map-action triggers.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from explainer_engine.qa.cinema_gates import check_tts_pronunciation_asr

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KOKORO_MODEL = ROOT / "assets" / "models" / "kokoro" / "kokoro-v1.0.onnx"
DEFAULT_KOKORO_VOICES = ROOT / "assets" / "models" / "kokoro" / "voices-v1.0.bin"


def _apply_broadcast_voice_polish(samples: np.ndarray, sr: int) -> np.ndarray:
    """Gentle broadcast documentary voice chain: 75Hz HPF, warm presence, peak normalization."""
    from scipy.signal import butter, sosfiltfilt

    x = samples.astype(np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    # Remove sub-rumble below 75Hz
    sos_hp = butter(2, 75.0 / (0.5 * sr), btype="highpass", output="sos")
    x = sosfiltfilt(sos_hp, x).astype(np.float32)
    # Gentle soft-knee limiting & headroom normalization (-1.5 dBFS peak)
    peak = float(np.max(np.abs(x))) if x.size else 1.0
    if peak > 1e-6:
        x = x * (0.84 / peak)
    # Subtle 12ms fade-in/out to prevent clicks at utterance edges
    fade_n = min(int(sr * 0.012), x.size // 4)
    if fade_n > 2:
        ramp = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        x[:fade_n] *= ramp
        x[-fade_n:] *= ramp[::-1]
    return x


def synthesize_kokoro_narration(
    lines: list[dict[str, Any]],
    out_dir: Path,
    *,
    voice: str = "bm_george",
    speed: float = 0.94,
    lang: str = "en-gb",
    target_sr: int = 48000,
    fps: int = 24,
    verify_asr: bool = True,
    required_proper_nouns: list[str] | None = None,
    model_path: Path = DEFAULT_KOKORO_MODEL,
    voices_path: Path = DEFAULT_KOKORO_VOICES,
) -> dict[str, Any]:
    """Synthesize documentary lines with Kokoro-ONNX, assemble timeline WAV, and run faster-whisper ASR."""
    if not model_path.is_file() or not voices_path.is_file():
        raise FileNotFoundError(
            f"Kokoro-ONNX model files missing: {model_path} / {voices_path}"
        )
    from kokoro_onnx import Kokoro

    out_dir.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(model_path), str(voices_path))

    utterances: list[dict[str, Any]] = []
    line_wavs: list[tuple[float, np.ndarray]] = []
    full_script_parts: list[str] = []

    cursor_s = 0.0
    for idx, line in enumerate(lines):
        lid = str(line.get("id") or f"line_{idx + 1:02d}")
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        v_id = str(line.get("voice") or voice)
        spd = float(line.get("speed") or speed)
        l_code = str(line.get("lang") or lang)

        # Pronunciation hints dictionary for historical/paleo proper nouns if needed
        spoken_text = str(line.get("phonetic_override") or text)
        samples, sr_in = kokoro.create(spoken_text, voice=v_id, speed=spd, lang=l_code)
        # Resample 24kHz -> 48kHz cleanly
        if sr_in != target_sr:
            samples = resample_poly(samples, target_sr, sr_in).astype(np.float32)
        polished = _apply_broadcast_voice_polish(samples, target_sr)
        dur_s = len(polished) / float(target_sr)

        # Honor explicit start_s if provided and not overlapping previous line
        req_start = line.get("start_s")
        if req_start is not None:
            start_s = max(cursor_s + 0.12, float(req_start))
        else:
            gap_before = float(line.get("pause_before_s", 0.35 if idx > 0 else 0.45))
            start_s = cursor_s + gap_before
        end_s = start_s + dur_s
        cursor_s = end_s

        line_wav_path = out_dir / f"{lid}.wav"
        sf.write(str(line_wav_path), polished, target_sr, subtype="PCM_16")
        line_wavs.append((start_s, polished))
        full_script_parts.append(text)
        utterances.append(
            {
                "id": lid,
                "text": text,
                "voice": v_id,
                "start_s": round(start_s, 3),
                "end_s": round(end_s, 3),
                "duration_s": round(dur_s, 3),
                "wav_path": str(line_wav_path),
                "dramatic_breather_after": bool(line.get("dramatic_breather_after", False)),
            }
        )

    total_dur_s = max((u["end_s"] for u in utterances), default=1.0) + 0.8
    total_samples = int(round(total_dur_s * target_sr))
    timeline = np.zeros(total_samples, dtype=np.float32)
    for st_s, wav in line_wavs:
        s_idx = int(round(st_s * target_sr))
        e_idx = min(total_samples, s_idx + len(wav))
        timeline[s_idx:e_idx] += wav[: e_idx - s_idx]

    master_voice_wav = out_dir / "narration_kokoro_48k.wav"
    sf.write(str(master_voice_wav), np.clip(timeline, -0.98, 0.98), target_sr, subtype="PCM_16")

    # Word-level timestamps + ASR verification via faster-whisper
    word_timestamps: list[dict[str, Any]] = []
    asr_report: dict[str, Any] = {"status": "SKIPPED"}
    expected_script = " ".join(full_script_parts)

    if verify_asr and utterances:
        from faster_whisper import WhisperModel

        wm = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        audio_16k = resample_poly(np.clip(timeline, -0.98, 0.98), 16000, target_sr).astype(np.float32)
        segments, _ = wm.transcribe(audio_16k, language="en", word_timestamps=True, beam_size=1)
        transcript_chunks: list[str] = []
        for seg in segments:
            transcript_chunks.append(seg.text.strip())
            for w in getattr(seg, "words", None) or []:
                clean_w = re.sub(r"[^A-Za-z0-9'\-]", "", str(w.word)).strip()
                if not clean_w:
                    continue
                word_timestamps.append(
                    {
                        "word": clean_w,
                        "start_s": round(float(w.start), 3),
                        "end_s": round(float(w.end), 3),
                        "start_frame": int(round(float(w.start) * fps)),
                    }
                )
        observed_transcript = " ".join(transcript_chunks).strip()
        asr_report = check_tts_pronunciation_asr(
            expected_script,
            observed_transcript=observed_transcript,
            required_proper_nouns=required_proper_nouns,
        )

    word_ts_path = out_dir / "word_timestamps.json"
    word_ts_path.write_text(json.dumps(word_timestamps, indent=2), encoding="utf-8")

    manifest = {
        "schema": "neural_narration/1",
        "engine": "kokoro-onnx",
        "voice": voice,
        "sample_rate": target_sr,
        "total_duration_s": round(total_dur_s, 3),
        "master_voice_wav": str(master_voice_wav),
        "word_timestamps_path": str(word_ts_path),
        "word_count": len(word_timestamps),
        "utterances": utterances,
        "asr_verification": asr_report,
    }
    (out_dir / "narration_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_dynamic_energy_curve(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign dynamic Docudrama x MrBeast vocal delivery curves (stability/tags) across narration lines."""
    from explainer_engine.audio.elevenlabs_narrator import EXPRESSIVE_DELIVERY_PRESETS

    cycle = ("hook_punch", "witty_twist", "rising_stakes", "intimate_whisper", "urgent_ticking", "reflective_finale")
    enriched: list[dict[str, Any]] = []
    for idx, raw in enumerate(lines):
        row = dict(raw)
        mode = str(row.get("delivery_mode") or "").strip().lower()
        if not mode:
            mode = "hook_punch" if idx == 0 else ("reflective_finale" if idx == len(lines) - 1 else cycle[idx % len(cycle)])
            row["delivery_mode"] = mode
        preset = EXPRESSIVE_DELIVERY_PRESETS.get(mode, EXPRESSIVE_DELIVERY_PRESETS["rising_stakes"])
        row.setdefault("stability", preset["stability"])
        row.setdefault("similarity_boost", preset["similarity_boost"])
        row.setdefault("audio_tag", preset["tag"])
        enriched.append(row)
    return enriched


def synthesize_expressive_odom_narration(
    lines: list[dict[str, Any]],
    out_dir: Path,
    *,
    model_id: str | None = None,
    verify_asr: bool = True,
    required_proper_nouns: list[str] | None = None,
    reuse_cached_takes: bool = True,
) -> dict[str, Any]:
    """Synthesize charismatic Docudrama x MrBeast narration via locked ElevenLabs Odom (never Kokoro)."""
    from explainer_engine.audio.elevenlabs_narrator import synthesize_elevenlabs_odom_narration

    directed = build_dynamic_energy_curve(lines)
    return synthesize_elevenlabs_odom_narration(
        directed,
        out_dir,
        model_id=model_id,
        verify_asr=verify_asr,
        required_proper_nouns=required_proper_nouns,
        reuse_cached_takes=reuse_cached_takes,
    )

