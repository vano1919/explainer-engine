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
SEARCH = 0.25  # seconds around the measured gap searched for the really quiet spot (word times are off by 0.1-0.2 s;
# Syndicate Wars "three. Our": the quiet began 0.10 s after the recogniser's boundary, so 0.10 found no pause)
QUIET_DB = -46.0  # the insertion point must be at least this quiet (10 ms rms), below the dropout scan's -42 dB (ED-12) with margin;
# louder means inside a word or its breath: skip it (Syndicate Wars: inserts at -40..-42 dB were reported as cuts)
FADE_MS = 10  # the silence is entered and left with a 10 ms fade, so it never clicks


def quiet_point(audio: np.ndarray, sr: int, lo: float, hi: float, prefer: float | None = None) -> tuple[float, float]:
    """(time, level dB) of the quietest 10 ms between lo and hi seconds: where a pause may be inserted without cutting a word."""
    a, b = max(0, int(lo * sr)), min(len(audio), int(hi * sr))
    h = max(1, int(0.01 * sr))
    if b - a < h:
        return (lo + hi) / 2, 0.0
    seg = audio[a:b].astype(np.float64)
    n = (len(seg) // h) * h
    rms = np.sqrt(np.mean(seg[:n].reshape(-1, h) ** 2, axis=1))
    # prefer the middle of a quiet stretch: smooth over 3 blocks so a single zero-crossing does not win
    sm = np.convolve(rms, np.ones(3) / 3, mode="same")
    near = np.flatnonzero(sm <= sm.min() * 1.41 + 1e-9)  # within 3 dB of the quietest: take the one nearest the measured gap
    centre = ((lo + hi) / 2 if prefer is None else prefer)
    k = int(near[np.argmin(np.abs((a + near * h + h / 2) / sr - centre))])
    return (a + k * h + h / 2) / sr, float(20 * np.log10(sm[k] + 1e-9))


def pad_pauses(words: list[dict], audio: np.ndarray, sr: int, min_gap: float = MIN_GAP,
               targets: dict[int, float] | None = None) -> tuple[np.ndarray, list[dict], dict]:
    """(padded audio, words on the padded clock, report). ``words`` are ordered, times in seconds of ``audio``.
    ``targets`` (word index -> seconds, D-43): a scripted pause after that word (a line's ``pause_after``) is at least
    that long, whatever the voice did."""
    targets = targets or {}
    inserts: list[tuple[float, float]] = []  # (position in the old clock, seconds of silence)
    skipped = 0
    for k, (a, b) in enumerate(zip(words, words[1:])):
        mark = a["w"].rstrip("\"'”’)")[-1:]
        gap = b["s"] - a["e"]
        want = max(min_gap if mark and mark in CUT_MARKS else 0.0, targets.get(k, 0.0))
        if gap < want:
            # Word times from the recogniser are off by 0.1-0.2 s: the middle of the measured gap can be inside a word
            # (Episode 1, 2:58 "Franklin keeps the tinder dry,": 67 of 131 insertions cut into sound). Find the quietest spot.
            lo, hi = max(a["s"] + 0.05, a["e"] - SEARCH), min(b["e"] - 0.05, b["s"] + SEARCH)
            pos, level = quiet_point(audio, sr, lo, hi, (a["e"] + b["s"]) / 2) if hi > lo else ((a["e"] + b["s"]) / 2, 0.0)
            if level > QUIET_DB:
                skipped += 1
                continue
            inserts.append((pos, want - gap))
    inserts.sort()
    src = audio.copy()
    f = max(1, int(FADE_MS / 1000 * sr))
    for pos, _ in inserts:  # the silence is entered and left on a 10 ms fade (no click, no clipped consonant)
        i = int(round(pos * sr))
        n0 = min(f, i)
        if n0:
            src[i - n0:i] *= np.linspace(1, 0, n0)
        n1 = min(f, len(src) - i)
        if n1:
            src[i:i + n1] *= np.linspace(0, 1, n1)
    pieces, last = [], 0
    for pos, add in inserts:
        i = int(round(pos * sr))
        pieces.append(src[last:i])
        pieces.append(np.zeros(int(round(add * sr)), audio.dtype))
        last = i
    pieces.append(src[last:])
    out = np.concatenate(pieces) if pieces else audio
    shifted = []
    for w in words:
        s0, e0, before = w["s"], w["e"], 0.0
        for pos, add in inserts:
            if pos <= s0:
                before += add
            elif pos < e0:
                if pos - s0 <= e0 - pos:  # the quiet spot is at the word's start: the recogniser began it early
                    s0, before = pos, before + add
                else:  # at its end: the recogniser ended it late; the word ends where the quiet begins
                    e0 = pos
        shifted.append(dict(w, s=round(s0 + before, 3), e=round(e0 + before, 3)))
    report = {"min_gap": min_gap, "inserted": len(inserts), "added_seconds": round(sum(a for _, a in inserts), 3),
              "skipped_not_quiet": skipped, "words": len(words)}
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
