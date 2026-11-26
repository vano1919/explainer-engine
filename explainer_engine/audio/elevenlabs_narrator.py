"""Governed ElevenLabs Odom Documentary Narrator + Word-Level Timestamps + Polish Chain.

Uses the creator's locked channel narrator ``Odom - Deep, Resonant, Dramatic``
(``CcSJ2r3qw0XU9gJpEPyk``) via ElevenLabs ``/with-timestamps`` (preferring ``eleven_v4``,
auto-falling back to ``eleven_v3`` / ``eleven_multilingual_v2`` if unavailable on the account),
applies ``explainer_engine/audio/narrator_polish.py`` to every take without moving timestamps,
inserts intentional dramatic breathing pauses (0.8-1.8s) on peak LTX scenes, and runs
``faster-whisper`` ASR verification for proper-noun accuracy.

Kokoro is strictly banned from this module and from final YouTube masters.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from explainer_engine.audio.narrator_polish import polish_in_place
from explainer_engine.core.env_loader import LOCKED_NARRATOR_VOICE_ID, load_project_env
from explainer_engine.qa.cinema_gates import check_tts_pronunciation_asr

PREFERRED_MODELS: tuple[str, ...] = ("eleven_v4", "eleven_v3", "eleven_multilingual_v2")
PREFERRED_FORMATS: tuple[str, ...] = ("mp3_44100_128", "mp3_44100_192")


def _api_key() -> str:
    load_project_env()
    key = (os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_API") or "").strip()
    if not key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY; refusing silent fallback to Kokoro.")
    return key


def check_elevenlabs_subscription() -> dict[str, Any]:
    """Verify ElevenLabs API key, active status, remaining characters, and available TTS models."""
    key = _api_key()
    req_sub = urllib.request.Request(
        "https://api.elevenlabs.io/v1/user/subscription",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req_sub, timeout=20) as resp:
        sub = json.loads(resp.read().decode("utf-8"))

    req_mod = urllib.request.Request(
        "https://api.elevenlabs.io/v1/models",
        headers={"xi-api-key": key},
    )
    with urllib.request.urlopen(req_mod, timeout=20) as resp:
        models = json.loads(resp.read().decode("utf-8"))

    tts_models = [m.get("model_id") for m in models if isinstance(m, dict) and m.get("can_do_text_to_speech")]
    chosen_model = next((m for m in PREFERRED_MODELS if m in tts_models), tts_models[0] if tts_models else "eleven_multilingual_v2")
    used = int(sub.get("character_count") or 0)
    limit = int(sub.get("character_limit") or 0)
    return {
        "tier": sub.get("tier"),
        "status": sub.get("status"),
        "character_count": used,
        "character_limit": limit,
        "remaining_characters": max(0, limit - used),
        "chosen_model": chosen_model,
        "available_tts_models": tts_models,
    }


def _chars_to_words(alignment: dict[str, Any], offset_s: float, fps: int) -> list[dict[str, Any]]:
    """Convert ElevenLabs character-level alignment into exact word-level timestamps."""
    chars = list(alignment.get("characters") or [])
    starts = list(alignment.get("character_start_times_seconds") or [])
    ends = list(alignment.get("character_end_times_seconds") or [])
    n = min(len(chars), len(starts), len(ends))
    words: list[dict[str, Any]] = []
    cur_chars: list[str] = []
    w_start: float | None = None
    w_end: float | None = None

    def flush() -> None:
        nonlocal cur_chars, w_start, w_end
        raw = "".join(cur_chars).strip()
        clean = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", raw)
        if clean and w_start is not None and w_end is not None:
            st = round(offset_s + float(w_start), 3)
            en = round(offset_s + float(w_end), 3)
            words.append(
                {
                    "word": clean,
                    "start_s": st,
                    "end_s": max(st + 0.04, en),
                    "start_frame": int(round(st * fps)),
                }
            )
        cur_chars = []
        w_start = None
        w_end = None

    for i in range(n):
        ch = str(chars[i])
        if ch.isspace():
            flush()
            continue
        if w_start is None:
            w_start = float(starts[i])
        w_end = float(ends[i])
        cur_chars.append(ch)
    flush()
    return words


def _decode_mp3_to_48k_mono_wav(mp3_path: Path, wav_path: Path, target_sr: int = 48000) -> float:
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(mp3_path),
        "-ac",
        "1",
        "-ar",
        str(target_sr),
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True)
    info = sf.info(str(wav_path))
    return float(info.frames) / float(info.samplerate)


def _call_elevenlabs_tts_with_timestamps(
    text: str,
    *,
    voice_id: str,
    model_id: str,
    output_format: str,
    voice_settings: dict[str, Any],
    previous_text: str | None = None,
    next_text: str | None = None,
) -> dict[str, Any]:
    key = _api_key()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format={output_format}"
    body: dict[str, Any] = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }
    if previous_text and model_id != "eleven_v3":
        body["previous_text"] = previous_text[-300:]
    if next_text and model_id != "eleven_v3":
        body["next_text"] = next_text[:300]

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_srt_timestamp(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000.0)))
    hh = ms_total // 3_600_000
    rem = ms_total % 3_600_000
    mm = rem // 60_000
    rem %= 60_000
    ss = rem // 1_000
    ms = rem % 1_000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def write_subtitles_srt(word_timestamps: list[dict[str, Any]], out_srt: Path, *, max_words_per_cue: int = 8) -> Path:
    """Build clean, frame-accurate YouTube English subtitles (.srt) from ElevenLabs word timestamps."""
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    cues: list[str] = []
    idx = 1
    i = 0
    while i < len(word_timestamps):
        chunk = word_timestamps[i : i + max_words_per_cue]
        # Prefer natural break if a gap > 0.45s occurs inside the chunk
        for k in range(1, len(chunk)):
            if float(chunk[k]["start_s"]) - float(chunk[k - 1]["end_s"]) > 0.45:
                chunk = chunk[:k]
                break
        st = float(chunk[0]["start_s"])
        en = max(st + 0.35, float(chunk[-1]["end_s"]))
        text = " ".join(str(w["word"]) for w in chunk)
        cues.append(f"{idx}\n{format_srt_timestamp(st)} --> {format_srt_timestamp(en)}\n{text}\n")
        idx += 1
        i += len(chunk)
    out_srt.write_text("\n".join(cues), encoding="utf-8")
    return out_srt


def synthesize_elevenlabs_odom_narration(
    lines: list[dict[str, Any]],
    out_dir: Path,
    *,
    voice_id: str = LOCKED_NARRATOR_VOICE_ID,
    model_id: str | None = None,
    output_format: str = "mp3_44100_128",
    target_sr: int = 48000,
    fps: int = 24,
    verify_asr: bool = True,
    required_proper_nouns: list[str] | None = None,
    reuse_cached_takes: bool = True,
) -> dict[str, Any]:
    """Synthesize documentary narration with ElevenLabs Odom, apply narrator_polish.py, and build word timestamps."""
    if voice_id != LOCKED_NARRATOR_VOICE_ID:
        raise ValueError(f"Narrator voice is locked to Odom ({LOCKED_NARRATOR_VOICE_ID}), got {voice_id!r}")

    sub_before = check_elevenlabs_subscription()
    chosen_model = model_id or str(sub_before["chosen_model"])
    total_chars_needed = sum(len(str(line.get("text", "")).strip()) for line in lines)
    out_dir.mkdir(parents=True, exist_ok=True)

    utterances: list[dict[str, Any]] = []
    word_timestamps: list[dict[str, Any]] = []
    line_wavs: list[tuple[float, np.ndarray]] = []
    full_script_parts: list[str] = []
    chars_spent_live = 0

    cursor_s = 0.0
    valid_lines = [ln for ln in lines if str(ln.get("text", "")).strip()]

    for idx, line in enumerate(valid_lines):
        lid = str(line.get("id") or f"line_{idx + 1:02d}")
        text = str(line.get("text", "")).strip()
        prev_txt = str(valid_lines[idx - 1]["text"]).strip() if idx > 0 else None
        next_txt = str(valid_lines[idx + 1]["text"]).strip() if idx + 1 < len(valid_lines) else None

        voice_settings = {
            "stability": float(line.get("stability", 0.42)),
            "similarity_boost": float(line.get("similarity_boost", 0.82)),
            "style": float(line.get("style", 0.35)),
            "use_speaker_boost": True,
        }

        mp3_path = out_dir / f"{lid}.mp3"
        wav_path = out_dir / f"{lid}.wav"
        align_path = out_dir / f"{lid}.alignment.json"
        meta_path = out_dir / f"{lid}.meta.json"

        # Cache hit avoids wasting ElevenLabs characters on identical lines across QA iterations!
        cached_ok = False
        if reuse_cached_takes and wav_path.is_file() and align_path.is_file() and meta_path.is_file():
            try:
                old_meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if old_meta.get("text") == text and old_meta.get("voice_id") == voice_id:
                    cached_ok = True
                    alignment = json.loads(align_path.read_text(encoding="utf-8"))
                    polish_info = old_meta.get("polish", {})
            except (OSError, ValueError):
                cached_ok = False

        if not cached_ok:
            resp_data = _call_elevenlabs_tts_with_timestamps(
                text,
                voice_id=voice_id,
                model_id=chosen_model,
                output_format=output_format,
                voice_settings=voice_settings,
                previous_text=prev_txt,
                next_text=next_txt,
            )
            audio_bytes = base64.b64decode(resp_data["audio_base64"])
            mp3_path.write_bytes(audio_bytes)
            alignment = resp_data.get("alignment") or resp_data.get("normalized_alignment") or {}
            align_path.write_text(json.dumps(alignment, indent=2), encoding="utf-8")
            _decode_mp3_to_48k_mono_wav(mp3_path, wav_path, target_sr=target_sr)
            # Mandatory creator polish chain (+12 dB @ 150 Hz, -2 dB @ 300 Hz, 60 Hz HPF, light afftdn, limiter)
            polish_info = polish_in_place(wav_path)
            chars_spent_live += len(text)
            meta_path.write_text(
                json.dumps(
                    {
                        "id": lid,
                        "text": text,
                        "voice_id": voice_id,
                        "model_id": chosen_model,
                        "output_format": output_format,
                        "chars": len(text),
                        "polish": polish_info,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        samples, sr_in = sf.read(str(wav_path), dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        if sr_in != target_sr:
            samples = resample_poly(samples, target_sr, sr_in).astype(np.float32)

        # Gentle 12ms anti-click edge fade
        fade_n = min(int(target_sr * 0.012), len(samples) // 4)
        if fade_n > 2:
            ramp = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
            samples[:fade_n] *= ramp
            samples[-fade_n:] *= ramp[::-1]

        dur_s = len(samples) / float(target_sr)
        req_start = line.get("start_s")
        if req_start is not None:
            start_s = max(cursor_s + 0.10, float(req_start))
        else:
            prev_breather = float(valid_lines[idx - 1].get("breather_after_s", 0.0)) if idx > 0 else 0.0
            default_gap = 0.28 if idx > 0 else 0.35
            gap_before = float(line.get("pause_before_s", max(default_gap, prev_breather)))
            start_s = cursor_s + gap_before
        end_s = start_s + dur_s
        cursor_s = end_s

        line_words = _chars_to_words(alignment, offset_s=start_s, fps=fps)
        word_timestamps.extend(line_words)
        line_wavs.append((start_s, samples))
        full_script_parts.append(text)
        utterances.append(
            {
                "id": lid,
                "text": text,
                "voice_id": voice_id,
                "model_id": chosen_model,
                "start_s": round(start_s, 3),
                "end_s": round(end_s, 3),
                "duration_s": round(dur_s, 3),
                "wav_path": str(wav_path),
                "chars": len(text),
                "dramatic_breather_after": bool(line.get("dramatic_breather_after", False)),
                "breather_after_s": float(line.get("breather_after_s", 0.0)),
                "polish": polish_info,
            }
        )

    tail_pad = float(lines[-1].get("tail_pad_s", 1.5)) if lines else 1.0
    total_dur_s = max((u["end_s"] for u in utterances), default=1.0) + tail_pad
    total_samples = int(round(total_dur_s * target_sr))
    timeline = np.zeros(total_samples, dtype=np.float32)
    for st_s, wav in line_wavs:
        s_idx = int(round(st_s * target_sr))
        e_idx = min(total_samples, s_idx + len(wav))
        if e_idx > s_idx:
            timeline[s_idx:e_idx] += wav[: e_idx - s_idx]

    master_voice_wav = out_dir / "narration_odom_48k.wav"
    sf.write(str(master_voice_wav), np.clip(timeline, -0.98, 0.98), target_sr, subtype="PCM_16")

    # Optional faster-whisper ASR cross-check for proper nouns
    asr_report: dict[str, Any] = {"status": "SKIPPED"}
    expected_script = " ".join(full_script_parts)
    if verify_asr and utterances:
        from faster_whisper import WhisperModel

        wm = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        audio_16k = resample_poly(np.clip(timeline, -0.98, 0.98), 16000, target_sr).astype(np.float32)
        segments, _ = wm.transcribe(audio_16k, language="en", word_timestamps=False, beam_size=1)
        observed = " ".join(seg.text.strip() for seg in segments).strip()
        asr_report = check_tts_pronunciation_asr(
            expected_script,
            observed_transcript=observed,
            required_proper_nouns=required_proper_nouns,
        )

    word_ts_path = out_dir / "word_timestamps.json"
    word_ts_path.write_text(json.dumps(word_timestamps, indent=2), encoding="utf-8")
    srt_path = write_subtitles_srt(word_timestamps, out_dir / "subtitles_en.srt")

    sub_after = check_elevenlabs_subscription()
    manifest = {
        "schema": "elevenlabs_odom_narration/1",
        "engine": "elevenlabs",
        "voice_id": voice_id,
        "voice_name": "Odom - Deep, Resonant, Dramatic",
        "model_id": chosen_model,
        "output_format": output_format,
        "sample_rate": target_sr,
        "total_duration_s": round(total_dur_s, 3),
        "total_script_chars": total_chars_needed,
        "live_chars_spent_this_run": chars_spent_live,
        "remaining_characters_after": sub_after["remaining_characters"],
        "master_voice_wav": str(master_voice_wav),
        "word_timestamps_path": str(word_ts_path),
        "subtitles_srt_path": str(srt_path),
        "word_count": len(word_timestamps),
        "utterances": utterances,
        "asr_verification": asr_report,
    }
    (out_dir / "narration_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
