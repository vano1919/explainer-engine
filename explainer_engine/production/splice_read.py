# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/splice_read.py`
# Target Module : explainer_engine/production/splice_read.py
# Target Classes/Symbols : def points(), def cut(), def join(), def pieces(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Put new narrator takes where runs of bubble lines were (D-63), so the rest of the read is reused, not paid for again.

    python -m explainer_engine.production.splice_read points <old_script.json> <read_dir> --out points.json
    python -m explainer_engine.production.splice_read pieces <points.json> <read_dir> <take1.mp3> ... --out DIR

``points`` aligns the old script's voiced lines on the read the words step made (``read.wav`` + ``heard.json``) and
writes, for every run of silent lines, the second of the voiced read where its gap opened (``silent.insert_points``).
``pieces`` cuts ``read.wav`` at those seconds and writes the slices and the takes in order (piece_000.wav, take_000.*,
piece_001.wav, ...) for ``production words <new_script> <pieces...>``: take k replaces run k, in the order of the script.
Each cut sits in the quietest spot of a pause, entered and left on a short fade (ED-12).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_text_atomic

FADE_MS = 10
JOIN_GAP = 0.6  # s between two takes read at one point (a sentence pause, BP-10)


def points(old_doc: dict, read_dir: Path) -> list[dict]:
    from explainer_engine.audio import scribe_words, voice_layer
    from explainer_engine.production import script as S, silent as SIL
    heard = json.loads((read_dir / "heard.json").read_text(encoding="utf-8"))["words"]
    pcm, sr = voice_layer.read_wav(read_dir / "read.wav")
    vdoc = SIL.voiced_doc(old_doc)
    aligned = scribe_words.align(S.narration_text(vdoc), heard, len(pcm) / sr)
    runs = SIL.insert_points(old_doc, aligned["words"], pcm, sr)
    return [{"at": round(r["at"], 4), "lines": [[old_doc["segments"][a]["id"], b] for a, b in r["lines"]],
             "text": " ".join(old_doc["segments"][a]["lines"][b]["text"] for a, b in r["lines"])} for r in runs]


def cut(pcm: np.ndarray, sr: int, at: list[float]) -> list[np.ndarray]:
    """``pcm`` cut at every second in ``at`` (sorted), each edge on a FADE_MS fade so no cut clicks."""
    f = max(1, int(FADE_MS / 1000 * sr))
    edges = [0] + [int(round(t * sr)) for t in at] + [len(pcm)]
    out = []
    for a, b in zip(edges, edges[1:]):
        piece = np.asarray(pcm[a:b], dtype=np.float64).copy()
        n = min(f, len(piece) // 2)
        if n:
            if a > 0:
                piece[:n] *= np.linspace(0, 1, n)
            if b < len(pcm):
                piece[-n:] *= np.linspace(1, 0, n)
        out.append(piece)
    return out


def join(paths: list[Path], sr: int, gap: float = JOIN_GAP) -> np.ndarray:
    """Takes read one after another with a short silence between them (``a.wav+b.wav`` on the command line)."""
    out = []
    for i, p in enumerate(paths):  # any format ffmpeg reads, decoded at the read's rate (mono, float)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        out += ([np.zeros(int(gap * sr))] if i else []) + [np.frombuffer(raw, dtype="<f4").astype(np.float64)]
    return np.concatenate(out)


def pieces(pts: list[dict], read_dir: Path, takes: list[Path], out: Path) -> list[Path]:
    from explainer_engine.audio import voice_layer
    if len(takes) != len(pts):
        raise SystemExit(f"{len(takes)} takes for {len(pts)} bubble runs: one take per run, in script order")
    pcm, sr = voice_layer.read_wav(read_dir / "read.wav")
    out.mkdir(parents=True, exist_ok=True)
    slices = cut(np.asarray(pcm, dtype=np.float64), sr, sorted(p["at"] for p in pts))
    files = []
    for k, sl in enumerate(slices):
        p = out / f"piece_{k:03d}.wav"
        voice_layer.write_wav(p, sl, sr)
        files.append(p)
        if k < len(takes):
            parts = str(takes[k]).split("+")
            if len(parts) == 1:
                t = out / f"take_{k:03d}{takes[k].suffix}"
                shutil.copyfile(takes[k], t)
            else:  # "a.wav+b.wav": a new line written after a former run (no run of its own) is read right after that run's take
                t = out / f"take_{k:03d}.wav"
                voice_layer.write_wav(t, join([Path(x) for x in parts], sr), sr)
            files.append(t)
    write_text_atomic(out / "pieces.json", json.dumps([str(f) for f in files], indent=1))
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.splice_read")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("points")
    a.add_argument("script")
    a.add_argument("read_dir")
    a.add_argument("--out", required=True)
    b = sub.add_parser("pieces")
    b.add_argument("points")
    b.add_argument("read_dir")
    b.add_argument("takes", nargs="+")
    b.add_argument("--out", required=True)
    x = ap.parse_args(argv)
    if x.cmd == "points":
        from explainer_engine.production import script as S
        pts = points(S.load(Path(x.script)), Path(x.read_dir))
        write_text_atomic(Path(x.out), json.dumps(pts, indent=1, ensure_ascii=False))
        print(f"{len(pts)} bubble runs", file=sys.stderr)
        return 0
    files = pieces(json.loads(Path(x.points).read_text(encoding="utf-8")), Path(x.read_dir), [Path(t) for t in x.takes],
                   Path(x.out))
    print("\n".join(str(f) for f in files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
