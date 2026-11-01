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
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise ConfigError(f"narrator polish failed: {done.stderr.strip()[:300]}")
    return Path(dst)
