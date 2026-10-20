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
import sys
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_text_atomic

FADE_MS = 10


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
            t = out / f"take_{k:03d}{takes[k].suffix}"
            shutil.copyfile(takes[k], t)
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
