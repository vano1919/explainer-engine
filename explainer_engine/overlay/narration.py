"""Free scratch narration for the overlay demo: Kokoro (Apache-2.0, local) reads each line, faster-whisper (tiny.en, local) finds the word
times in that audio, the script's words are matched to them. The result is a MEASURED spine of the scratch read (not a Scribe read of a
real narration; there is none yet) in the same ``[{word, start_frame}]`` shape ``maps/actions.plan`` takes. Demo only.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import numpy as np

WORD = re.compile(r"[A-Za-z0-9']+")
SR = 24000
VOICE = "bm_george"
KOKORO_DIR = Path("/tmp/claude-0/kokoro")          # kokoro-v1.0.int8.onnx + voices-v1.0.bin (kokoro-onnx release model-files-v1.0)
WHISPER_DIR = "/tmp/claude-0/whisper-tiny.en"


def words_of(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text)]


def trim(a: np.ndarray, floor: float = 0.01) -> tuple[np.ndarray, float]:
    """The audio without its leading and trailing silence, and the seconds cut at the front."""
    idx = np.where(np.abs(a) > floor)[0]
    if not len(idx):
        return a, 0.0
    lo, hi = max(0, idx[0] - int(0.03 * SR)), min(len(a), idx[-1] + int(0.08 * SR))
    return a[lo:hi], lo / SR


def synth(lines: list[str], speeds: list[float]) -> list[np.ndarray]:
    from kokoro_onnx import Kokoro
    k = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.int8.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    out = []
    for text, sp in zip(lines, speeds):
        a, sr = k.create(text, voice=VOICE, speed=sp, lang="en-us")
        assert sr == SR
        out.append(trim(np.asarray(a, np.float32))[0])
    return out


def word_times(audio: np.ndarray, text: str) -> list[dict]:
    """[{word, start_s, end_s}] for the script's words, from a whisper pass over the audio (prompted with the script's own spelling),
    matched by difflib; words whisper missed are spread between their neighbours."""
    from faster_whisper import WhisperModel
    m = WhisperModel(WHISPER_DIR, device="cpu", compute_type="int8")
    from scipy.signal import resample_poly
    wav16 = resample_poly(audio.astype(np.float32), 2, 3).astype(np.float32)        # whisper reads 16 kHz; 24 kHz input stretches every time by 1.5
    segs, _ = m.transcribe(wav16, word_timestamps=True, language="en", initial_prompt=text, beam_size=5, vad_filter=False)
    heard: list[tuple[str, float, float]] = []
    for s in segs:
        for w in s.words:
            parts = words_of(w.word) or [""]
            for i, p in enumerate(parts):
                a = w.start + (w.end - w.start) * i / len(parts)
                b = w.start + (w.end - w.start) * (i + 1) / len(parts)
                heard.append((p, a, b))
    want = words_of(text)
    sm = difflib.SequenceMatcher(a=want, b=[h[0] for h in heard], autojunk=False)
    start = [None] * len(want)
    end = [None] * len(want)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                start[i1 + k], end[i1 + k] = heard[j1 + k][1], heard[j1 + k][2]
    dur = len(audio) / SR
    known = [i for i, v in enumerate(start) if v is not None]
    for i in range(len(want)):
        if start[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            a0 = end[lo] if lo is not None else 0.0
            b0 = start[hi] if hi is not None else dur
            gap = [k for k in range(len(want)) if start[k] is None and (lo is None or k > lo) and (hi is None or k < hi)]
            n = len(gap)
            j = gap.index(i)
            start[i], end[i] = a0 + (b0 - a0) * j / n, a0 + (b0 - a0) * (j + 1) / n
    return [{"word": w, "start_s": round(float(s), 3), "end_s": round(float(e), 3), "heard": i in known} for i, (w, s, e) in enumerate(zip(want, start, end))]


def build(lines: list[str], windows: list[float], out_dir: Path, lead_s: float = 0.6, tail_s: float = 0.9) -> list[dict]:
    """Read every line (speed raised until it fits its window minus the lead-in and tail), save the wavs and word times."""
    import soundfile as sf
    out_dir.mkdir(parents=True, exist_ok=True)
    speeds = [0.95] * len(lines)
    audio = synth(lines, speeds)
    for i, (a, w) in enumerate(zip(audio, windows)):
        if len(a) / SR > w - lead_s - tail_s:
            speeds[i] = round(min(1.25, 0.95 * (len(a) / SR) / (w - lead_s - tail_s) + 0.01), 3)
    redo = [i for i in range(len(lines)) if speeds[i] != 0.95]
    if redo:
        for i, a in zip(redo, synth([lines[i] for i in redo], [speeds[i] for i in redo])):
            audio[i] = a
    res = []
    for i, (text, a) in enumerate(zip(lines, audio)):
        p = out_dir / f"line_{i + 1:02d}.wav"
        sf.write(p, a, SR)
        res.append({"no": i + 1, "text": text, "wav": str(p), "seconds": round(len(a) / SR, 3), "speed": speeds[i], "words": word_times(a, text)})
    (out_dir / "narration.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res
