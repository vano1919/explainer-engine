"""One production script, one command line (D-43).

    python -m explainer_engine.production validate <script.json> [--pics DIR ...] [--snd DIR ...]
    python -m explainer_engine.production compile  <script.json> --out DIR          # prompts into the script + derived files
    python -m explainer_engine.production words    <script.json> <read.mp3|wav> --out DIR [--transcript scribe.json]
    python -m explainer_engine.production time     <script.json> <words.json> --out timed.json
    python -m explainer_engine.production assemble <script.json> <timed.json> <narration.wav> --out DIR --pics DIR ... --snd DIR ...
                                                   [--final] [--size 1920x1080] [--audio-only]
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


def cmd_words(doc: dict, audio: Path, out: Path, transcript: Path | None) -> dict:
    from explainer_engine.audio import local_words, pause_pad, scribe_words, voice_layer
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "read.wav"
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-ac", "1", "-ar", "48000", str(wav)], check=True)
    if transcript:
        heard = scribe_words.transcript_words(json.loads(transcript.read_text(encoding="utf-8")))
        source = f"transcript {transcript.name}"
    else:
        res = local_words.transcribe(wav)
        (out / "heard.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
        heard, source = res["words"], res["source"]
    pcm, sr = voice_layer.read_wav(wav)
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
    doc_w = {"source": f"{source}; aligned by scribe_words (coverage {aligned['coverage']}, {aligned['status']}); "
                       f"pause_pad +{rep['added_seconds']} s", "duration": round(len(padded) / sr, 3),
             "coverage": aligned["coverage"], "unmatched": aligned["unmatched"], "words": words}
    (out / "words.json").write_text(json.dumps(doc_w, indent=0), encoding="utf-8")
    return doc_w


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.production", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "compile", "words", "time", "assemble", "run"):
        q = sub.add_parser(name)
        q.add_argument("script")
        if name == "words":
            q.add_argument("audio")
            q.add_argument("--transcript")
        if name == "time":
            q.add_argument("words")
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
    if a.cmd == "words":
        w = cmd_words(doc, Path(a.audio), Path(a.out), Path(a.transcript) if a.transcript else None)
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
                         grade_key=doc["episode"].get("grade") or C.world_of(doc)["grade"], audio_only=a.audio_only)
        print(json.dumps({k: res[k] for k in ("video", "audio")}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
