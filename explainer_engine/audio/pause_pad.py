"""Pause padding for a narration read (D-39): a punctuated gap shorter than ``MIN_GAP`` gets silence inserted in its
middle, so the edit has a real pause to cut in (UR-12) while no word is touched.

    python -m explainer_engine.audio.pause_pad --audio narration.wav --words words_raw.json --out-dir out/

ElevenLabs reads a comma or a dash in 0.05-0.1 s, which is too short for a cut 0.05 s from both words. Inserting
silence is an editing step, not a voice change: every word keeps its sound and length, the words after an insertion
move later by the inserted time, and ``words.json`` is rewritten on the padded audio (the file the mix uses).
Marks padded: ``CUT_MARKS`` of ``edit.shot_rules`` (comma, full stop, colon, semicolon, question and exclamation
marks, dash, ellipsis). A lone dash joins the word before it in ``words.json``, so its gap is the gap after the dash.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import voice_layer
from ..edit.shot_rules import CUT_MARKS

MIN_GAP = 0.26  # seconds: a cut needs 2 x EDGE (0.1 s) of room plus a margin


def pad_pauses(words: list[dict], audio: np.ndarray, sr: int, min_gap: float = MIN_GAP) -> tuple[np.ndarray, list[dict], dict]:
    """(padded audio, words on the padded clock, report). ``words`` are ordered, times in seconds of ``audio``."""
    inserts: list[tuple[float, float]] = []  # (position in the old clock, seconds of silence)
    for a, b in zip(words, words[1:]):
        mark = a["w"].rstrip("\"'”’)")[-1:]
        gap = b["s"] - a["e"]
        if mark and mark in CUT_MARKS and gap < min_gap:
            inserts.append((a["e"] + gap / 2, min_gap - gap))
    pieces, last = [], 0
    for pos, add in inserts:
        i = int(round(pos * sr))
        pieces.append(audio[last:i])
        pieces.append(np.zeros(int(round(add * sr)), audio.dtype))
        last = i
    pieces.append(audio[last:])
    out = np.concatenate(pieces) if pieces else audio
    shifted, k, total = [], 0, 0.0
    for w in words:
        while k < len(inserts) and inserts[k][0] <= w["s"]:
            total += inserts[k][1]
            k += 1
        # a word that starts before an insertion ends before it, so it only moves by the insertions before it
        e_total = total
        j = k
        while j < len(inserts) and inserts[j][0] < w["e"]:
            e_total += inserts[j][1]  # an insertion inside a word never happens (gaps are between words)
            j += 1
        item = dict(w, s=round(w["s"] + total, 3), e=round(w["e"] + e_total, 3))
        shifted.append(item)
    report = {"min_gap": min_gap, "inserted": len(inserts), "added_seconds": round(sum(a for _, a in inserts), 3),
              "words": len(words)}
    return out, shifted, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--audio", required=True)
    p.add_argument("--words", required=True, help="words.json measured on --audio")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--min-gap", type=float, default=MIN_GAP)
    a = p.parse_args(argv)
    audio, sr = voice_layer.read_wav(Path(a.audio))
    doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
    out, words, report = pad_pauses(doc["words"], audio, sr, a.min_gap)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_layer.write_wav(out_dir / "narration.wav", out, sr)
    doc = dict(doc, words=words, duration=round(len(out) / sr, 3),
               source=doc.get("source", "") + f"; {report['inserted']} pauses padded to {a.min_gap} s "
                      f"(+{report['added_seconds']} s) by explainer_engine.audio.pause_pad")
    (out_dir / "words.json").write_text(json.dumps(doc, indent=0), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
