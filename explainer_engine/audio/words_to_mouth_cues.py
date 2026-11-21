"""Mouth cues in Rhubarb's JSON shape from a word-timed transcript (ElevenLabs Scribe), for a machine where Rhubarb Lip
Sync cannot run (2026-11-06: the 1.14.0 release is x86_64 only and the M4 Mac has no Rosetta). stdlib only.

    python -m explainer_engine.audio.words_to_mouth_cues --words scribe_words.json --wav line.wav --out line.rhubarb.json

Input ``words``: Scribe's ``{"text", "start", "end"}`` list (``words`` key of a transcript, or a bare list). Each word's
span is shared equally among its letters and every letter gets a Preston Blair shape by spelling (``LETTER_SHAPES``: m/b/p
close the lips -> A, a -> D wide open, e -> C, i/y -> B, o -> E, u/w -> F, f/v -> G, l -> H, other consonants -> B);
consecutive equal shapes merge, a cue shorter than ``MIN_CUE`` is folded into the one before it, gaps between words and
the lead-in and tail rest on X. The result is ``{"metadata": {"soundFile", "duration", "estimated": true}, "mouthCues":
[...]}``, which ``blender.rigs.LipSync`` reads like a Rhubarb file. It is a spelling approximation, not phoneme
recognition: good enough for a test clip, REVIEW for an episode (BP-xx has no rule yet; the real tool is Rhubarb).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MIN_CUE = 0.04
LETTER_SHAPES = {"m": "A", "b": "A", "p": "A", "a": "D", "e": "C", "i": "B", "y": "B", "o": "E", "u": "F", "w": "F",
                 "f": "G", "v": "G", "l": "H"}
DEFAULT_SHAPE = "B"
REST = "X"
_LETTERS = re.compile(r"[a-z]+")


def _r(t: float) -> float:
    return round(t + 1e-9, 2)


def word_cues(text: str, start: float, end: float) -> list[dict]:
    """The cues of one word: its letters' shapes spread evenly over [start, end), equal neighbours merged."""
    letters = "".join(_LETTERS.findall(text.lower()))
    if not letters or end <= start:
        return []
    step = (end - start) / len(letters)
    cues: list[dict] = []
    for i, ch in enumerate(letters):
        shape = LETTER_SHAPES.get(ch, DEFAULT_SHAPE)
        s, e = start + i * step, start + (i + 1) * step
        if cues and cues[-1]["value"] == shape:
            cues[-1]["end"] = e
        else:
            cues.append({"start": s, "end": e, "value": shape})
    return cues


def mouth_cues(words: list[dict], duration: float | None = None, min_cue: float = MIN_CUE) -> list[dict]:
    """Rhubarb-shaped ``mouthCues`` for a timed word list: rest (X) before, between and after the words."""
    words = sorted((w for w in words if w.get("type", "word") == "word"), key=lambda w: float(w["start"]))
    raw: list[dict] = []
    t = 0.0
    for w in words:
        s, e = float(w["start"]), float(w["end"])
        if s > t:
            raw.append({"start": t, "end": s, "value": REST})
        for c in word_cues(w["text"], max(s, t), e):
            raw.append(c)
        t = max(t, e)
    if duration is not None and duration > t:
        raw.append({"start": t, "end": duration, "value": REST})
    cues: list[dict] = []
    for c in raw:
        if cues and (c["end"] - c["start"] < min_cue or cues[-1]["value"] == c["value"]):
            cues[-1]["end"] = c["end"]
        else:
            cues.append(dict(c))
    for c in cues:
        c["start"], c["end"] = _r(c["start"]), _r(c["end"])
    return [c for c in cues if c["end"] > c["start"]]


def rhubarb_doc(words: list[dict], sound_file: str, duration: float) -> dict:
    return {"metadata": {"soundFile": sound_file, "duration": _r(duration), "estimated": True,
                         "source": "explainer_engine.audio.words_to_mouth_cues (spelling approximation)"},
            "mouthCues": mouth_cues(words, duration)}


def wav_duration(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--words", required=True, help="Scribe transcript JSON (a dict with 'words' or a bare list)")
    ap.add_argument("--wav", required=True, help="the line's WAV (its length is the cues' duration)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
    words = doc["words"] if isinstance(doc, dict) else doc
    out = rhubarb_doc(words, Path(a.wav).name, wav_duration(Path(a.wav)))
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{a.out}: {len(out['mouthCues'])} cues over {out['metadata']['duration']} s (estimated from spelling)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
