"""Render one Short of the production script's ``shorts`` block (docs/ORCHESTRATION.md SH-01..SH-04): 1080x1920, the video's own
pictures cropped around the hero (``crop_x``, ``zoom``) with a slow push, the same narrator, word-timed captions, a low music bed.

    python -m explainer_engine.production.shorts <script.json> --id SH01 --audio <read.mp3> --out <dir> [--pics DIR ...] [--tempo 1.05]

Free (local Whisper + ffmpeg). ``--tempo`` speeds the read with ffmpeg's pitch-preserving atempo; the creator allowed at most
about 8 %, and the timbre check (``audio/voice_check``) runs on the result: on any drift the original pace is used.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from explainer_engine.audio import local_words, scribe_words, voice_check, voice_layer
from explainer_engine.production import script as S
from explainer_engine.qa import targets

W, H, FPS = 1080, 1920, 30
MAX_TEMPO = 1.08


def narration(short: dict) -> str:
    return " ".join(line["text"].strip() for line in short["lines"]) + "\n"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def prepare_audio(src: Path, out: Path, tempo: float) -> tuple[Path, list[dict]]:
    """Levelled mono wav (tempo applied) and a timbre report; falls back to the original pace on drift."""
    assert 1.0 <= tempo <= MAX_TEMPO, f"tempo above {MAX_TEMPO} is not allowed"
    wav = out / "short.wav"
    chain = f"atempo={tempo}," if tempo != 1.0 else ""
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain + targets.loudnorm("short"), "-ac", "1", "-ar", "48000", str(wav)])
    pcm, sr = voice_layer.read_wav(wav)
    found, _ = voice_check.check(np.asarray(pcm, dtype=float), sr)
    drift = [f for f in found if f.get("severity") in ("FAIL", "REVIEW")]
    if tempo != 1.0 and drift:
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", targets.loudnorm("short"), "-ac", "1", "-ar", "48000", str(wav)])
    return wav, drift


def short_words(short: dict, wav: Path, out: Path) -> dict:
    heard = local_words.transcribe(wav)
    pcm, sr = voice_layer.read_wav(wav)
    aligned = scribe_words.align(narration(short), heard["words"], len(pcm) / sr)
    (out / "words.json").write_text(json.dumps(aligned, indent=0), encoding="utf-8")
    return aligned


def shot_times(short: dict, words: list[dict], duration: float) -> list[dict]:
    toks = scribe_words.script_tokens(narration(short))
    rows, cursor = [], 0
    for k, sh in enumerate(short["shots"]):
        i = 0 if k == 0 else S.find_phrase([{"w": t["w"]} for t in toks], sh["at"], cursor)
        if i is None:
            raise ValueError(f"{short['id']}: phrase {sh['at']!r} not found in order")
        cursor = i + 1
        start = 0.0 if k == 0 else max(0.0, words[i]["s"] - 0.12)
        rows.append(dict(sh, start=round(start, 3)))
    for k, r in enumerate(rows):
        r["end"] = rows[k + 1]["start"] if k + 1 < len(rows) else round(duration, 3)
    return rows


def ass_captions(words: list[dict], path: Path) -> None:
    def t(x: float) -> str:
        h, rem = divmod(x, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            "Style: Cap,DejaVu Sans,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,90,90,430,1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or w["w"].rstrip("\"'”’)")[-1:] in ".?!":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    rows = []
    for k, ln in enumerate(lines):
        end = lines[k + 1][0]["s"] if k + 1 < len(lines) else ln[-1]["e"] + 0.4
        rows.append(f"Dialogue: 0,{t(ln[0]['s'])},{t(max(end - 0.02, ln[0]['s'] + 0.2))},Cap,,0,0,0,,{' '.join(x['w'] for x in ln).upper()}")
    path.write_text(head + "\n".join(rows) + "\n", encoding="utf-8")


def clip(pic: Path, sh: dict, dur: float, out: Path) -> None:
    from PIL import Image
    iw, ih = Image.open(pic).size
    z = float(sh.get("zoom", 1.0))
    ch = ih / z
    cw = min(iw, ch * 9 / 16)
    cx = min(max(float(sh["crop_x"]) * iw, cw / 2), iw - cw / 2)
    x0, y0 = cx - cw / 2, (ih - ch) / 2
    n = max(1, int(round(dur * FPS)))
    vf = (f"crop={int(cw)}:{int(ch)}:{int(x0)}:{int(y0)},scale={W}:{H}:flags=lanczos,"
          f"zoompan=z='min(1+0.07*on/{n},1.07)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
    _run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(pic), "-vf", vf,
          "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", str(out)])


def render(doc: dict, short_id: str, audio: Path, out: Path, pic_dirs: list[Path], music: Path | None, tempo: float) -> Path:
    short = next(s for s in doc["shorts"] if s["id"] == short_id)
    out.mkdir(parents=True, exist_ok=True)
    wav, drift = prepare_audio(audio, out, tempo)
    aligned = short_words(short, wav, out)
    pcm, sr = voice_layer.read_wav(wav)
    duration = len(pcm) / sr + 0.5
    rows = shot_times(short, aligned["words"], duration)
    pics, _ = S.pictures(doc)
    parts = []
    for k, r in enumerate(rows):
        name = (pics.get(r["picture"]) or {}).get("file") or f"{r['picture']}.png"
        pic = next((d / name for d in pic_dirs if (d / name).exists()), None)
        if pic is None:
            raise FileNotFoundError(f"{short_id}: picture {name} not found")
        part = out / f"clip{k}.mp4"
        clip(pic, r, r["end"] - r["start"], part)
        parts.append(part)
    (out / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    silent = out / "silent.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(out / "list.txt"), "-c", "copy", str(silent)])
    ass_captions(aligned["words"], out / "cap.ass")
    final = out / f"{short_id}.mp4"
    inputs = ["-i", str(silent), "-i", str(wav)]
    fc = "[2:a]volume=0.10,afade=t=out:st=%.2f:d=1.2[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]" % max(0.0, duration - 1.2)
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    else:
        fc = "[1:a]anull[a]"
    _run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{fc};[0:v]subtitles={out / 'cap.ass'}[v]", "-map", "[v]", "-map", "[a]",
          "-t", f"{duration:.2f}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(final)])
    (out / "report.json").write_text(json.dumps({"duration": round(duration, 2), "timbre_review": drift, "shots": rows}, indent=1), encoding="utf-8")
    return final


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--id", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pics", action="append", default=[])
    ap.add_argument("--music")
    ap.add_argument("--tempo", type=float, default=1.05)
    a = ap.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    dirs = [Path(x) for x in a.pics] + [path.parent / d for d in doc.get("picture_dirs", [])]
    final = render(doc, a.id, Path(a.audio), Path(a.out), dirs, Path(a.music) if a.music else None, a.tempo)
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
