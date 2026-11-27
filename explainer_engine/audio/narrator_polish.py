
"""The narrator's standard polish (creator, 2026-11-01): every take of the channel narrator (Odom, config/channel_voices.json)
goes through one fixed ffmpeg chain, chosen by his ear on the same 41 s eleven_v4 take: rumble cut under 60 Hz, light noise
reduction, +12 dB low shelf at 150 Hz, a small -2 dB dip at 300 Hz so the bass does not make the voice muddy, a -0.6 dB trim
that keeps the loudness of the raw take (-24.4 LUFS on the test take), and a limiter at 0.95 (the test take peaked at -2.8 dBFS).
Free: no credits, no regeneration. Timing is untouched (filters only, no tempo or pitch step), so word timings stay valid."""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..core.errors import ConfigError

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


LTX_DIALOGUE_DENOISE_CHAIN = (
    "highpass=f=95,lowpass=f=7600,"
    "afftdn=nr=26:nf=-24:nt=w,"
    "anlmdn=s=0.004:p=0.002:r=0.004,"
    "equalizer=f=220:t=q:w=1.1:g=-2.5,"
    "equalizer=f=2800:t=q:w=1.2:g=1.8"
)

_RNNOISE_MODEL = Path(__file__).resolve().parents[2] / "assets" / "audio" / "rnnoise_bd.rnnn"


def clean_ltx_dialogue_stem(
    src_wav: Path | str,
    dst_wav: Path | str,
    *,
    target_rms_db: float = -16.8,
    pause_atten_db: float = -42.0,
    sr: int = 48000,
) -> dict[str, float]:
    """Strip LTX-2.5 generative broadband wind/static roar via RNNoise neural speech isolation.

    Uses FFmpeg high-pass + gentle spectral denoise + single-pass ``arnndn`` (avoiding watery
    double-RNNoise modulation), matched documentary vocal EQ, subtle shared stone-courtyard
    early reflection so shot-reverse-shot actors share one acoustic space, tight smooth VAD
    pause gating (-42 dB so baked-in LTX wind never steps across camera cuts), and uniform
    active-speech RMS leveling.
    """
    import numpy as np
    import soundfile as sf

    src_p = Path(src_wav)
    dst_p = Path(dst_wav)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    tmp_p = dst_p.with_name(dst_p.stem + ".denoise.wav")

    if _RNNOISE_MODEL.is_file():
        m_esc = str(_RNNOISE_MODEL).replace("\\", "/").replace(":", "\\:")
        filter_chain = (
            f"highpass=f=125,afftdn=nr=10:nf=-32,"
            f"arnndn=m='{m_esc}':mix=0.72,"
            "lowpass=f=7000,"
            "equalizer=f=240:t=q:w=1.1:g=-2.4,"
            "equalizer=f=2700:t=q:w=1.3:g=1.8,"
            "aecho=0.90:0.88:22|38:0.09|0.05"
        )
    else:
        filter_chain = LTX_DIALOGUE_DENOISE_CHAIN

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src_p),
        "-af", filter_chain,
        "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s24le", str(tmp_p),
    ]
    done = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if done.returncode != 0:
        raise ConfigError(f"LTX dialogue denoise failed: {done.stderr.strip()[:300]}")

    x, file_sr = sf.read(str(tmp_p), dtype="float32")
    tmp_p.unlink(missing_ok=True)
    if x.ndim > 1:
        x = x.mean(axis=1)

    # Smooth 15ms RMS activity detector to keep pauses whisper-clean without clipping plosives
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

    # Normalize active speech uniformly to target_rms_db with gentle -2.5 dBFS soft ceiling
    active_mask = gain > 0.65
    active_s = y[active_mask] if int(np.sum(active_mask)) > 1600 else y
    rms_val = float(np.sqrt(np.mean(active_s ** 2) + 1e-12))
    rms_db = float(20.0 * np.log10(rms_val + 1e-12))
    gain_db = float(np.clip(target_rms_db - rms_db, -12.0, 14.0))
    y = y * float(10.0 ** (gain_db / 20.0))
    ceil = float(10.0 ** (-2.5 / 20.0))
    y = np.where(np.abs(y) > ceil, np.sign(y) * (ceil + (np.abs(y) - ceil) * 0.2), y)
    fn = min(int(file_sr * 0.055), len(y) // 4)
    if fn > 4:
        t = np.linspace(0.0, np.pi * 0.5, fn, dtype=np.float32)
        y[:fn] *= np.sin(t)
        y[-fn:] *= np.cos(t)

    sf.write(str(dst_p), np.clip(y, -0.96, 0.96).astype(np.float32), file_sr, subtype="PCM_24")
    return {
        "used_rnnoise": 1.0 if _RNNOISE_MODEL.is_file() else 0.0,
        "speech_rms_db": round(target_rms_db, 2),
        "applied_gain_db": round(gain_db, 2),
        "gate_threshold_db": round(thresh_db, 2),
        "active_speech_ratio": round(float(np.mean(active_mask)), 3),
    }

