"""Free word times from a local Whisper (faster-whisper on the CPU) instead of ElevenLabs Scribe (~1,000 credits per
3 minutes, 2026-10-16). Writes the same shape Scribe returns (``{"words": [{"text", "start", "end", "type"}]}``), so
``scribe_words.py --transcript`` aligns it to the script unchanged (missed or misheard words are interpolated there and
counted against the 97 % coverage gate).

    python -m explainer_engine.audio.local_words <audio> <out.json> [--model small.en]

faster-whisper is optional (``pip install faster-whisper``); the audio is decoded by ffmpeg (the bundled PyAV may not
open every file). Measured 2026-10-16: small.en int8 hears 25 s of ElevenLabs speech in 6-10 s on this container's CPU.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def decode(path: Path, sr: int = 16000):
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(path: Path, model: str = "small.en", prompt: str | None = None) -> dict:
    from faster_whisper import WhisperModel

    t0 = time.time()
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(decode(path), word_timestamps=True, language="en", initial_prompt=prompt)
    words = [{"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3), "type": "word"}
             for s in segs for w in s.words if w.word.strip()]
    words = [w for w in words if w["end"] - w["start"] >= 0.03]  # 20 ms "words" at the end are hallucinations
    return {"source": f"faster-whisper {model} (local, free)", "seconds": round(time.time() - t0, 1), "words": words}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("audio")
    p.add_argument("out")
    p.add_argument("--model", default="small.en")
    p.add_argument("--script", help="the script text: names in it are given to Whisper as a spelling hint")
    a = p.parse_args(argv)
    hint = Path(a.script).read_text(encoding="utf-8")[:800] if a.script else None
    res = transcribe(Path(a.audio), a.model, hint)
    Path(a.out).write_text(json.dumps(res, indent=0), encoding="utf-8")
    print(f"{len(res['words'])} words in {res['seconds']} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
