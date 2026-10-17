"""One production script, one command line (D-43).

    python -m explainer_engine.production validate <script.json> [--pics DIR ...] [--snd DIR ...]
    python -m explainer_engine.production compile  <script.json> --out DIR          # prompts into the script + derived files
    python -m explainer_engine.production words    <script.json> <read.mp3|wav> --out DIR [--transcript scribe.json]
    python -m explainer_engine.production time     <script.json> <words.json> --out timed.json
    python -m explainer_engine.production assemble <script.json> <timed.json> <narration.wav> --out DIR --pics DIR ... --snd DIR ...
                                                   [--final] [--size 1920x1080] [--audio-only]
    python -m explainer_engine.production fill     <script.json> [<words.json>]           # re-framed shots for dead holds (RHYTHM-3)
    python -m explainer_engine.production run      <script.json> <narration.wav> <words.json> --out DIR --pics ... --snd ...

``words`` is free: a local Whisper hears the read (or a Scribe JSON is given), ``scribe_words.align`` puts the times on the
script's own tokens, ``pause_pad`` widens punctuated gaps and every line's scripted ``pause_after``. Exit code 1 on any
FAIL. Nothing here spends money; the paid reads and pictures use the files ``compile`` writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from explainer_engine.production import assemble as A
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V


def _print(found: list[dict], title: str) -> int:
    for f in found:
        print(f"{f['severity']:6} {f['rule']:16} {str(f['where'])[:18]:18} {f['detail']}")
    print(f"{title}: {V.summary(found)}", file=sys.stderr)
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


def _dirs(doc_path: Path, extra: list[str] | None, key: str) -> list[Path]:
    doc = S.load(doc_path)
    base = doc_path.parent
    return [Path(p) for p in (extra or [])] + [base / p for p in doc.get(key, [])]


def join_reads(audio: list[Path], wav: Path, gap_s: float = 0.3) -> None:
    """One read, or the chunk reads joined in order with a short silence (pause_pad widens it where the script wants)."""
    import subprocess
    if len(audio) == 1:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio[0]), "-ac", "1", "-ar", "48000", str(wav)], check=True)
        return
    from explainer_engine.audio import seams
    rep = seams.plan(audio)  # ED-01: every chunk to one loudness, edges faded inside the silence
    ins, parts = [], []
    for k, p in enumerate(audio):
        ins += ["-i", str(p)]
        parts.append(seams.chain(k, p, rep["gains_db"][k], gap_s))
    join_reads.report = rep
    graph = ";".join(parts) + ";" + "".join(f"[a{k}]" for k in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", str(wav)],
                   check=True)


def cmd_words(doc: dict, audio: list[Path], out: Path, transcript: Path | None) -> dict:
    from explainer_engine.audio import local_words, pause_pad, scribe_words, voice_check, voice_layer
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "read.wav"
    join_reads(audio, wav)
    if transcript:
        heard = scribe_words.transcript_words(json.loads(transcript.read_text(encoding="utf-8")))
        source = f"transcript {transcript.name}"
    else:
        res = local_words.transcribe(wav)
        (out / "heard.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
        heard, source = res["words"], res["source"]
    pcm, sr = voice_layer.read_wav(wav)
    _, drift = voice_check.check(np.asarray(pcm, dtype=float), sr)
    aligned = scribe_words.align(S.narration_text(doc), heard, len(pcm) / sr)
    toks = S.tokens(doc)
    targets, k = {}, -1
    for seg_i, seg in enumerate(doc["segments"]):
        for li, line in enumerate(seg["lines"]):
            k = max(i for i, t in enumerate(toks) if t["seg"] == seg_i and t["line"] == li)
            if line.get("pause_after"):
                targets[k] = float(line["pause_after"])
    padded, words, rep = pause_pad.pad_pauses(aligned["words"], pcm, sr, targets=targets)
    voice_layer.write_wav(out / "narration.wav", padded, sr)
    from explainer_engine.audio import dropouts
    cuts = dropouts.scan(np.asarray(padded, dtype=float), sr)  # ED-12: no word may be cut by a padded pause
    seam_spread = (getattr(join_reads, "report", None) or {}).get("spread_after_db", 0.0)
    doc_w = {"source": f"{source}; aligned by scribe_words (coverage {aligned['coverage']}, {aligned['status']}); "
                       f"pause_pad +{rep['added_seconds']} s", "duration": round(len(padded) / sr, 3),
             "coverage": aligned["coverage"], "unmatched": aligned["unmatched"], "voice_check": drift,
             "seams": getattr(join_reads, "report", None), "dropouts": cuts, "words": words}
    (out / "words.json").write_text(json.dumps(doc_w, indent=0), encoding="utf-8")
    n_cut = len(cuts["cut_into_sound"])
    print(f"dropout scan: {cuts['silence_runs']} silence runs, {n_cut} cut into sound; chunk loudness spread {seam_spread} dB")
    if seam_spread > 1.5:
        print(f"REVIEW ED-01 chunk loudness spread {seam_spread} dB after levelling (limit 1.5)")
    if n_cut:
        print(f"{'FAIL' if n_cut >= 3 else 'REVIEW'} ED-12 {n_cut} padded pause(s) cut into sound: {cuts['cut_into_sound'][:5]}")
        if n_cut >= 3:
            raise SystemExit("words: stopped, the read has words cut by padded pauses (ED-12); words.json is written for a look")
    return doc_w


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.production", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "compile", "words", "time", "assemble", "run", "fill"):
        q = sub.add_parser(name)
        q.add_argument("script")
        if name == "words":
            q.add_argument("audio", nargs="+", help="one read, or the chunk reads in order (tts_chunks.json)")
            q.add_argument("--transcript")
        if name in ("time",):
            q.add_argument("words")
        if name == "fill":
            q.add_argument("words", nargs="?")
        if name == "assemble":
            q.add_argument("timed")
            q.add_argument("narration")
        if name == "run":
            q.add_argument("narration")
            q.add_argument("words")
        q.add_argument("--out")
        q.add_argument("--pics", action="append")
        q.add_argument("--snd", action="append")
        q.add_argument("--final", action="store_true")
        q.add_argument("--audio-only", action="store_true")
        q.add_argument("--chunks", help="assemble: draw only chunks FIRST:END (e.g. 0:3 = chunks 0, 1, 2); the video is joined "
                       "when every chunk is on disk")
        q.add_argument("--chunk-seconds", type=float, default=A.CHUNK_SECONDS,
                       help="assemble: seconds per saved chunk (a restart of the machine loses at most one); 0 = one chunk")
        q.add_argument("--size", default="1920x1080")
        q.add_argument("--write", action="store_true", help="compile: write the prompts back into the script")
    a = p.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    pics = _dirs(path, a.pics, "picture_dirs") if a.pics or doc.get("picture_dirs") else None
    snd = _dirs(path, a.snd, "sound_dirs")
    sounds = A.Sounds(snd)
    if a.cmd == "validate":
        return _print(V.check_script(doc, pics, sounds.exists), "script")
    if a.cmd == "compile":
        new = C.compile_doc(doc)
        if a.write or not a.out:
            S.save(new, path)
        if a.out:
            for f in C.write_outputs(new, Path(a.out)):
                print("wrote", f)
        return _print(V.check_script(new, pics, sounds.exists), "script after compile")
    if a.cmd == "fill":
        from explainer_engine.production import fill_holds as F
        words_doc = json.loads(Path(a.words).read_text(encoding="utf-8")) if a.words else V.estimated_words(doc)
        doc, dropped = F.drop_short_shots(doc, words_doc)
        for row in dropped:
            print("dropped", row["segment"], repr(row["at"]), row["picture"], f"{row['duration']:.2f}s")
        new, ins, stuck = F.fill_holds(doc, words_doc)
        S.save(new, path)
        for row in ins:
            print("added", row["segment"], repr(row["at"]), row["picture"], f"{row['start']:.1f}s")
        for row in stuck:
            print("stuck", row)
        print(f"{len(ins)} re-framed shots added, {len(stuck)} gaps left", file=sys.stderr)
        return 0
    if a.cmd == "words":
        w = cmd_words(doc, [Path(x) for x in a.audio], Path(a.out), Path(a.transcript) if a.transcript else None)
        _print(w["voice_check"], "voice check")
        print(json.dumps({k: w[k] for k in ("duration", "coverage")}))
        return 0 if w["coverage"] >= 0.97 else 1
    if a.cmd in ("time", "run"):
        words_doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
        timed = T.time_script(doc, words_doc)
        timed["bubble_pop"] = {"sound": "pop_in__v1", "gain_db": -26} if sounds.exists("pop_in__v1") else None
        out = Path(a.out) if a.out else path.with_name("timed.json")
        target = out if a.cmd == "time" else out / "timed.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        found = V.check_timed(timed, doc, final=a.final, picture_dirs=pics)
        timed["findings"] = found
        target.write_text(json.dumps(timed, indent=1, ensure_ascii=False), encoding="utf-8")
        code = _print(found, "timed")
        if a.cmd == "time" or code:
            return code
        a.timed, a.cmd = str(target), "assemble"
    if a.cmd == "assemble":
        timed = json.loads(Path(a.timed).read_text(encoding="utf-8"))
        W, H = (int(x) for x in a.size.lower().split("x"))
        res = A.assemble(timed, Path(a.narration), Path(a.out), pics or [], snd, size=(W, H), final=a.final,
                         grade_key=doc["episode"].get("grade") or C.world_of(doc)["grade"], audio_only=a.audio_only,
                         chunk_seconds=a.chunk_seconds,
                         only=tuple(int(x) for x in a.chunks.split(":")) if a.chunks else None)
        print(json.dumps({k: res[k] for k in ("video", "audio")}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
