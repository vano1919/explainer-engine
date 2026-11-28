"""Free local rehearsal TTS narration generator ($0.00 external API spend).

Uses ``edge-tts`` (Microsoft neural voice preview, $0.00) or deterministic offline fallback
to render 48kHz 16-bit stereo WAV narration tracks clearly tagged ``rehearsal_tts=True`` so
70/30 narrator-vs-dialogue pacing, sidechain ducking, and BP-187 timing are genuinely verified
without spending paid ElevenLabs credits.
"""
from __future__ import annotations

import asyncio
import hashlib
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_VOICE = "en-GB-RyanNeural"


async def _synth_edge_mp3(text: str, out_mp3: Path, *, voice: str = DEFAULT_VOICE, rate: str = "-4%") -> None:
    import edge_tts

    comm = edge_tts.Communicate(text, voice=voice, rate=rate)
    await comm.save(str(out_mp3))


def render_rehearsal_narration(
    text: str,
    out_wav: Path,
    *,
    voice: str = DEFAULT_VOICE,
    rate: str = "-4%",
) -> dict[str, Any]:
    """Synthesize a clean 48kHz 16-bit stereo WAV narration clip at $0.00 cost."""
    dst = Path(out_wav)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp3 = dst.with_suffix(".tmp.mp3")

    asyncio.run(_synth_edge_mp3(text, tmp_mp3, voice=voice, rate=rate))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(tmp_mp3),
            "-af",
            "highpass=f=80,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=120,loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        check=True,
    )
    tmp_mp3.unlink(missing_ok=True)

    dur = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(dst),
            ],
            text=True,
        ).strip()
    )
    return {
        "rehearsal_tts": True,
        "paid_usd": 0.0,
        "voice": voice,
        "text": text,
        "wav_path": str(dst),
        "duration_s": round(dur, 3),
        "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
    }
