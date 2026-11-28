
"""The narrator's standard polish (creator, 2026-11-01): every take of the channel narrator (Odom, config/channel_voices.json)
goes through one fixed ffmpeg chain, chosen by his ear on the same 41 s eleven_v4 take: rumble cut under 60 Hz, light noise
reduction, +12 dB low shelf at 150 Hz, a small -2 dB dip at 300 Hz so the bass does not make the voice muddy, a -0.6 dB trim
that keeps the loudness of the raw take (-24.4 LUFS on the test take), and a limiter at 0.95 (the test take peaked at -2.8 dBFS).
Free: no credits, no regeneration. Timing is untouched (filters only, no tempo or pitch step), so word timings stay valid."""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..core.errors import ConfigError
from ..standards import sourced_rules

BASS_DB, BASS_HZ = 12, 150
CHAIN = ("volume=-0.6dB,highpass=f=60,afftdn=nr=8:nf=-50,"
         f"bass=g={BASS_DB}:f={BASS_HZ}:w=0.7,equalizer=f=300:t=q:w=1:g=-2,alimiter=limit=0.95")


def polish(src: Path | str, dst: Path | str) -> Path:
    """``src`` through ``CHAIN`` into ``dst`` (format by its extension). Raises ConfigError when ffmpeg fails."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", CHAIN, str(dst)]
    done = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if done.returncode != 0:
        raise ConfigError(f"narrator polish failed: {done.stderr.strip()[:300]}")
    return Path(dst)


def polish_in_place(wav: Path | str) -> dict:
    """Polish ``wav`` where it lies (temp file + rename) and say what was done, for words.json. The length is checked: a
    filter chain must not move a word (the timings were measured before it)."""
    wav = Path(wav)
    tmp = wav.with_name(wav.stem + ".polish.wav")
    before = _seconds(wav)
    polish(wav, tmp)
    after = _seconds(tmp)
    if abs(after - before) > 1 / 30:
        tmp.unlink(missing_ok=True)
        raise ConfigError(f"narrator polish moved the length by {after - before:+.3f} s: the word timings would be wrong")
    import os
    os.replace(tmp, wav)
    return {"chain": CHAIN, "seconds_before": round(before, 3), "seconds_after": round(after, 3)}


def _seconds(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


DIALOGUE_RNNOISE_MIX = float(sourced_rules.T("BP-216", "rnnoise_mix"))
DIALOGUE_HIGHPASS_HZ = int(sourced_rules.T("BP-216", "highpass_hz"))
DIALOGUE_MAX_PAUSE_REDUCTION_DB = float(sourced_rules.T("BP-216", "max_pause_reduction_db"))
DIALOGUE_TARGET_LUFS = float(sourced_rules.T("BP-216", "target_lufs"))
DIALOGUE_TOLERANCE_LU = float(sourced_rules.T("BP-216", "tolerance_lu"))

_DIALOGUE_VOCAL_EQ = (
    "equalizer=f=240:t=q:w=1.1:g=-2.4,"
    "equalizer=f=2700:t=q:w=1.3:g=1.8"
)

# Used only when the RNNoise model file is missing: a light spectral denoise, same high-pass and vocal EQ.
LTX_DIALOGUE_DENOISE_CHAIN = f"highpass=f={DIALOGUE_HIGHPASS_HZ},afftdn=nr=8:nf=-40,{_DIALOGUE_VOCAL_EQ}"

_RNNOISE_MODEL = Path(__file__).resolve().parents[2] / "assets" / "audio" / "rnnoise_bd.rnnn"
_SOFT_CEILING_DBFS = -2.5
_MAX_LEVEL_GAIN_DB = 30.0


def _integrated_lufs(x: Any, sr: int, name: str) -> float:
    import numpy as np
    import pyloudnorm as pyln

    if len(x) < int(0.4 * sr) + 1:
        raise ConfigError(f"{name}: shorter than one 0.4 s loudness block, cannot be levelled")
    value = float(pyln.Meter(sr).integrated_loudness(x))
    if not np.isfinite(value):
        raise ConfigError(f"{name}: silent audio, integrated loudness cannot be measured")
    return value


def _apply_gain(x: Any, gain_db: float) -> Any:
    """Gain followed by a soft ceiling, so a levelled plosive bends instead of clipping."""
    import numpy as np

    y = x * float(10.0 ** (gain_db / 20.0))
    ceil = float(10.0 ** (_SOFT_CEILING_DBFS / 20.0))
    y = np.where(np.abs(y) > ceil, np.sign(y) * (ceil + (np.abs(y) - ceil) * 0.2), y)
    return np.clip(y, -0.96, 0.96).astype(np.float32)


def _gain_to_loudness(parts: Sequence[Any], sr: int, target_lufs: float, name: str) -> tuple[float, float]:
    """The one gain that brings ``parts`` (measured as one programme) to ``target_lufs``; returns (gain, loudness)."""
    import numpy as np

    gain_db = target_lufs - _integrated_lufs(np.concatenate(parts), sr, name)
    reached = target_lufs
    for _ in range(5):
        if abs(gain_db) > _MAX_LEVEL_GAIN_DB:
            raise ConfigError(f"{name}: needs {gain_db:+.1f} dB, too far from {target_lufs} LUFS to be real speech")
        reached = _integrated_lufs(np.concatenate([_apply_gain(p, gain_db) for p in parts]), sr, name)
        if abs(reached - target_lufs) <= 0.05:
            break
        gain_db += target_lufs - reached
    return gain_db, reached


def clean_ltx_dialogue_stem(
    src_wav: Path | str,
    dst_wav: Path | str,
    *,
    target_lufs: float = DIALOGUE_TARGET_LUFS,
    pause_atten_db: float = -DIALOGUE_MAX_PAUSE_REDUCTION_DB,
    sr: int = 48000,
    target_rms_db: float | None = None,
) -> dict[str, float]:
    """Gently remove generated wind and static from a character's line and level it (BP-216).

    One RNNoise pass (``arnndn``) at a partial mix after a ``95 Hz`` high-pass, a mild vocal EQ and a faint shared
    early reflection so both sides of a conversation sit in one space. Pauses are lowered by at most
    ``14 dB`` (a deeper ``pause_atten_db`` is limited to that), so the room tone never drops to digital silence.
    The stem is levelled to ``target_lufs`` integrated and fails when it ends outside the tolerance.

    ``target_rms_db`` is accepted from older callers and ignored: levelling is by integrated loudness.
    """
    import numpy as np
    import soundfile as sf

    src_p = Path(src_wav).resolve()
    dst_p = Path(dst_wav).resolve()
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    tmp_p = dst_p.with_name(dst_p.stem + ".denoise.wav")
    pause_atten_db = float(min(0.0, max(float(pause_atten_db), -DIALOGUE_MAX_PAUSE_REDUCTION_DB)))

    has_model = _RNNOISE_MODEL.is_file()
    if has_model:
        # The model is named relative to the working directory: a Windows drive colon cannot be escaped reliably
        # inside an ffmpeg filter string.
        filter_chain = (
            f"highpass=f={DIALOGUE_HIGHPASS_HZ},aresample=48000,"
            f"arnndn=m={_RNNOISE_MODEL.name}:mix={DIALOGUE_RNNOISE_MIX},"
            f"{_DIALOGUE_VOCAL_EQ},"
            "aecho=0.90:0.88:22|38:0.09|0.05"
        )
    else:
        filter_chain = LTX_DIALOGUE_DENOISE_CHAIN

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src_p),
        "-af", filter_chain,
        "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s24le", str(tmp_p),
    ]
    done = subprocess.run(cmd, check=False, capture_output=True, text=True,
                          cwd=_RNNOISE_MODEL.parent if has_model else None)
    if done.returncode != 0:
        raise ConfigError(f"LTX dialogue denoise failed: {done.stderr.strip()[:300]}")

    x, file_sr = sf.read(str(tmp_p), dtype="float32")
    tmp_p.unlink(missing_ok=True)
    if x.ndim > 1:
        x = x.mean(axis=1)

    # Smooth 15ms RMS activity detector to keep pauses clean without clipping plosives
    hop = max(1, int(file_sr * 0.015))
    n_blk = int(np.ceil(len(x) / hop))
    pad = n_blk * hop - len(x)
    padded = np.pad(x, (0, pad)) if pad > 0 else x
    blk_rms = np.sqrt(np.mean(padded.reshape(n_blk, hop) ** 2, axis=1) + 1e-12)
    blk_db = 20.0 * np.log10(blk_rms)
    peak_db = float(np.percentile(blk_db, 95)) if len(blk_db) else -30.0
    thresh_db = float(np.clip(peak_db - 14.5, -38.0, -22.0))
    speech_prob = np.clip((blk_db - (thresh_db - 4.0)) / 8.0, 0.0, 1.0).astype(np.float32)

    # 45ms lookahead dilation so initial plosives ('C', 'P', 'T', 'D') and trailing 's'/'t' never clip
    dilated = speech_prob.copy()
    for k in range(1, 4):
        dilated[:-k] = np.maximum(dilated[:-k], speech_prob[k:])
        dilated[k:] = np.maximum(dilated[k:], speech_prob[:-k])

    a_att = float(np.exp(-15.0 / 16.0))
    a_rel = float(np.exp(-15.0 / 120.0))
    env = np.zeros(n_blk, dtype=np.float32)
    cur = 0.0
    for i in range(n_blk):
        tgt = float(dilated[i])
        coeff = a_att if tgt > cur else a_rel
        cur = coeff * cur + (1.0 - coeff) * tgt
        env[i] = cur

    floor_lin = float(10.0 ** (pause_atten_db / 20.0))
    gain_blk = floor_lin + (1.0 - floor_lin) * env
    xp = np.arange(n_blk, dtype=np.float32) * hop
    gain = np.interp(np.arange(len(x), dtype=np.float32), xp, gain_blk).astype(np.float32)
    y = x * gain

    # Short anti-click fades only: a line may start on its first sample
    fn = min(int(file_sr * 0.008), len(y) // 4)
    if fn > 4:
        t = np.linspace(0.0, np.pi * 0.5, fn, dtype=np.float32)
        y[:fn] *= np.sin(t)
        y[-fn:] *= np.cos(t)

    gain_db, _ = _gain_to_loudness([y], file_sr, target_lufs, src_p.name)
    sf.write(str(dst_p), _apply_gain(y, gain_db), file_sr, subtype="PCM_24")
    written, _ = sf.read(str(dst_p), dtype="float32")
    lufs = _integrated_lufs(written, file_sr, dst_p.name)
    if abs(lufs - target_lufs) > DIALOGUE_TOLERANCE_LU:
        raise ConfigError(
            f"{dst_p.name}: {lufs:.2f} LUFS is outside {target_lufs} +/- {DIALOGUE_TOLERANCE_LU} LU after levelling"
        )

    active_mask = gain > 0.65
    active_s = written[active_mask] if int(np.sum(active_mask)) > 1600 else written
    rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(active_s ** 2) + 1e-12))))
    return {
        "used_rnnoise": 1.0 if has_model else 0.0,
        "rnnoise_mix": DIALOGUE_RNNOISE_MIX if has_model else 0.0,
        "pause_atten_db": round(pause_atten_db, 2),
        "integrated_lufs": round(lufs, 2),
        "speech_rms_db": round(rms_db, 2),
        "applied_gain_db": round(gain_db, 2),
        "gate_threshold_db": round(thresh_db, 2),
        "active_speech_ratio": round(float(np.mean(active_mask)), 3),
    }


def match_scene_speaker_loudness(
    stems: Sequence[Mapping[str, Any]],
    *,
    target_lufs: float = DIALOGUE_TARGET_LUFS,
    tolerance_lu: float = DIALOGUE_TOLERANCE_LU,
) -> dict[str, Any]:
    """Level every speaker of one scene to ``target_lufs`` with one gain per speaker (BP-216).

    ``stems`` are ``{"speaker", "wav_path", "out_path"?}``; without ``out_path`` the file is replaced. All lines of a
    speaker are measured as one programme, so a quiet line stays quieter than the same speaker's loud one. Nothing
    is written unless every speaker lands within ``tolerance_lu`` of the target.
    """
    import numpy as np
    import soundfile as sf

    if not stems:
        raise ConfigError("no dialogue stems to level")
    by_speaker: dict[str, list[tuple[Path, Any, int]]] = {}
    rates: set[int] = set()
    for stem in stems:
        speaker = str(stem.get("speaker") or "").strip().lower()
        if not speaker:
            raise ConfigError(f"dialogue stem without a speaker: {stem.get('wav_path')}")
        src = Path(stem["wav_path"])
        x, file_sr = sf.read(str(src), dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        rates.add(file_sr)
        by_speaker.setdefault(speaker, []).append((Path(stem.get("out_path") or src), x, file_sr))
    if len(rates) != 1:
        raise ConfigError(f"dialogue stems of one scene differ in sample rate: {sorted(rates)}")
    file_sr = rates.pop()

    speakers: dict[str, dict[str, float]] = {}
    outputs: list[tuple[Path, Any]] = []
    for speaker, rows in by_speaker.items():
        parts = [x for _, x, _ in rows]
        before = _integrated_lufs(np.concatenate(parts), file_sr, speaker)
        gain_db, after = _gain_to_loudness(parts, file_sr, target_lufs, speaker)
        if abs(after - target_lufs) > tolerance_lu:
            raise ConfigError(f"speaker {speaker!r}: {after:.2f} LUFS is outside {target_lufs} +/- {tolerance_lu} LU")
        speakers[speaker] = {
            "lufs_before": round(before, 2),
            "lufs_after": round(after, 2),
            "gain_db": round(gain_db, 2),
        }
        outputs.extend((dst, _apply_gain(x, gain_db)) for dst, x, _ in rows)

    for dst, y in outputs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.stem + ".level.wav")
        sf.write(str(tmp), y, file_sr, subtype="PCM_24")
        os.replace(tmp, dst)

    levels = [s["lufs_after"] for s in speakers.values()]
    return {
        "target_lufs": target_lufs,
        "tolerance_lu": tolerance_lu,
        "speaker_spread_lu": round(max(levels) - min(levels), 2),
        "speakers": speakers,
    }
