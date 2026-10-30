"""RETIRED by D-39 (2026-10-16, ElevenLabs is the narrator): Kokoro code kept for provenance (docs/PROVENANCE.md) and for audio/timings consumers; never a production read.

Narration from a voice spec: Kokoro timed render of the blended voice -> words.json -> alteration -> checked WAV.

    python -m explainer_engine.audio.narrate --spec assets/audio/voices/<id>.json --text narration.txt --out <dir>

Writes ``base.wav`` (the blended voice, the reference for the timings), ``narration.wav`` (the altered voice, what the
mix uses), ``words.json`` (measured on the base render) and ``voice_report.json``. WAVs are not committed.
Needs ``kokoro-onnx`` and the timed model in ``tools/kokoro`` (or ``$EXPLAINER_KOKORO_DIR``):
``kokoro-v1.0-timed.onnx`` (kokoro-onnx release model-files-v1.1, ``kokoro-v1.0.onnx``) and ``voices-v1.0.bin``.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise SystemExit("RETIRED by D-39: no Kokoro reads; narration is ElevenLabs (docs/AUDIO_SYSTEM.md)")

import argparse
import json
import os
from pathlib import Path

import numpy as np

from . import timings, voice_layer

SR = 24000
LEAD = 0.15  # silence before the first word
GAP = 0.55  # between paragraphs
TAIL = 0.6
SENTENCE_PAUSE = 0.28
CLAUSE_PAUSE = 0.14


def kokoro_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_KOKORO_DIR", Path(__file__).resolve().parents[2] / "tools" / "kokoro"))


def load_kokoro(directory: Path | None = None):
    from kokoro_onnx import Kokoro

    d = directory or kokoro_dir()
    return Kokoro(str(d / "kokoro-v1.0-timed.onnx"), str(d / "voices-v1.0.bin"))


def render_base(kokoro, spec: dict, paragraphs: list[str]) -> tuple[np.ndarray, list[dict]]:
    """The blended voice speaking ``paragraphs``; the words with times on the programme clock."""
    style = voice_layer.narrator_style(kokoro.get_voice_style, spec)
    out = [np.zeros(int(LEAD * SR), np.float32)]
    t, words = LEAD, []
    for i, p in enumerate(paragraphs):
        audio, sr, spoken = kokoro.create_timed(p, voice=style, speed=spec["speed"], lang="en-us",
                                                sentence_pause=SENTENCE_PAUSE, clause_pause=CLAUSE_PAUSE)
        if sr != SR:
            raise RuntimeError(f"Kokoro returned {sr} Hz, expected {SR}")
        phonemes = [[x.phoneme, float(x.start), float(x.end)] for x in spoken]
        for w in timings.align(p, phonemes):
            words.append({"w": w["w"], "s": round(t + w["s"], 3), "e": round(t + w["e"], 3), "para": i})
        out.append(np.asarray(audio, np.float32))
        t += len(audio) / SR
        if i < len(paragraphs) - 1:
            out.append(np.zeros(int(GAP * SR), np.float32))
            t += GAP
    out.append(np.zeros(int(TAIL * SR), np.float32))
    return np.concatenate(out), words


def run(spec_path: Path, text_path: Path, out_dir: Path, kokoro=None) -> dict:
    spec = voice_layer.load_voice_spec(spec_path)
    if spec["rvc"] is not None:
        raise NotImplementedError("RVC is specified but not implemented: it waits for a licensed model (D-38)")
    paragraphs = [p.strip() for p in Path(text_path).read_text(encoding="utf-8").splitlines() if p.strip()]
    kokoro = kokoro or load_kokoro()
    base, words = render_base(kokoro, spec, paragraphs)
    final, report = voice_layer.alter(base, SR, spec)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_layer.write_wav(out_dir / "base.wav", base, SR)
    voice_layer.write_wav(out_dir / "narration.wav", final, SR)
    duration = len(base) / SR
    (out_dir / "words.json").write_text(json.dumps({
        "source": f"Kokoro-82M kokoro-v1.0-timed.onnx (model-files-v1.1), voice {spec['id']} (base {spec['base']}, blend "
                  f"{[(b['voice'], b['weight']) for b in spec['blend']]}), speed {spec['speed']}, sentence_pause "
                  f"{SENTENCE_PAUSE}, clause_pause {CLAUSE_PAUSE}, paragraph gap {GAP} s, lead {LEAD} s; measured on the "
                  "base render (before the alteration layer); words aligned with explainer_engine.audio.timings.align",
        "voice": spec["id"], "duration": round(duration, 3), "words": words}, indent=0), encoding="utf-8")
    report.update(base=voice_layer.measure(base, SR, len(words)), final=voice_layer.measure(final, SR, len(words)),
                  words=len(words), duration=round(duration, 2))
    (out_dir / "voice_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--spec", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    report = run(Path(a.spec), Path(a.text), Path(a.out))
    print(json.dumps(report, indent=1))
    return 0 if report["timing"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
