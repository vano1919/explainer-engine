"""Render one Short of the production script's ``shorts`` block (docs/ORCHESTRATION.md SH-01..SH-04): 1080x1920, the video's own
pictures cropped around the hero (``crop_x``, ``zoom``) with a slow push, the same narrator, word-timed captions, a low music bed,
and the same visual-beat layer as the long video (SS-09): the Short is timed by ``timing.time_script`` on ``beats.short_doc`` and
every frame is finished by ``assemble.finish_frame`` (face focus, accents, close-ups, beats); the beats' cues are mixed with
``assemble.cue_bus``.

    python -m explainer_engine.production.shorts <script.json> --id SH01 --audio <read.mp3> --out <dir> [--pics DIR ...] [--tempo 1.05]

Free (local Whisper + ffmpeg). ``--tempo`` speeds the read with ffmpeg's pitch-preserving atempo; the creator allowed at most
about 8 %, and the timbre check (``audio/voice_check``) runs on the result: on any drift the original pace is used.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.audio import local_words, scribe_words, voice_check, voice_layer
from explainer_engine.production import assemble as ASM
from explainer_engine.production import beats as BEATS
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.qa import short_format as SF, targets

W, H = 1080, 1920  # the frame rate is the episode's (timing.time_script)
MAX_TEMPO = 1.08
SCREEN = "sc_"  # production/select_screen.py's stat cards: text across the whole 16:9 width, never cropped to 9:16
SCREEN_MARGIN = 0.03  # share of the Short's width left on each side of a fitted card


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


def time_short(doc: dict, short: dict, words: list[dict], duration: float) -> dict:
    """The Short timed like the video (SS-09): its shots, visual beats (accent beats join their shot's accents) and cues on
    the read's words. Shot k of the result is ``short["shots"][k]``."""
    timed = T.time_script(BEATS.short_doc(doc, short), {"words": words, "duration": duration})
    if timed["problems"]:
        raise ValueError(f"{short['id']}: {timed['problems'][0]['detail']}")
    for row, sh in zip(timed["shots"], short["shots"]):
        row.update(crop_x=float(sh["crop_x"]), zoom=float(sh.get("zoom", 1.0)))
    return timed


def crop_box(row: dict, iw: int, ih: int, u: float) -> tuple[float, float, float, float]:
    """The 9:16 crop of a shot in picture pixels: ``zoom`` and ``crop_x`` set it, a push of ``beats.SHORT_PUSH`` runs over
    the shot (``u`` 0..1) about its centre."""
    z = float(row.get("zoom", 1.0))
    ch = ih / z
    cw = min(iw, ch * W / H)
    cx = min(max(float(row["crop_x"]) * iw, cw / 2), iw - cw / 2)
    k = 1 + (BEATS.SHORT_PUSH - 1) * min(max(u, 0.0), 1.0)
    return (cx - cw / 2 / k, ih / 2 - ch / 2 / k, cx + cw / 2 / k, ih / 2 + ch / 2 / k)


def fit_spots(beats: list[dict], row: dict, iw: int, ih: int, margin: float = 0.08) -> int:
    """A label or ring points at a spot of the picture; written for the 16:9 frame, the spot may fall outside the Short's
    9:16 crop. Such a spot is moved to the nearest place inside the crop (the leader then points toward the thing).
    Returns how many were moved (the report lists it)."""
    x0, y0, x1, y1 = crop_box(row, iw, ih, 0.0)
    mx, my = (x1 - x0) * margin, (y1 - y0) * margin
    moved = 0
    for b in beats:
        if b["kind"] in ("label", "highlight") and b.get("pos") and b["shot"] == row["id"]:
            px, py = b["pos"][0] * iw, b["pos"][1] * ih
            nx, ny = min(max(px, x0 + mx), x1 - mx), min(max(py, y0 + my), y1 - my)
            if (nx, ny) != (px, py):
                b["pos"] = [nx / iw, ny / ih]
                moved += 1
    return moved


def short_frame(im: Image.Image, row: dict, f: int, fps: int, sb: list[dict], hero_faces: dict, dirs: list[Path],
                before: Image.Image | None = None) -> Image.Image:
    """Frame ``f`` of shot ``row``: its crop and push, then everything ``assemble.finish_frame`` draws on the video."""
    u = (f - row["start_frame"]) / max(1, row["end_frame"] - row["start_frame"])
    box = crop_box(row, *im.size, u)
    return ASM.finish_frame(im, box, row, f, fps, (W, H), sb, hero_faces, sorted(hero_faces), dirs, None, before)


def fit_screen(im: Image.Image, beats: list[dict], row: dict) -> Image.Image:
    """A stat card in the Short (QA 2026-10-19: the 9:16 crop cut its title and stars): the whole card fitted to the width,
    over a blurred, dimmed fill of itself; the shot's spots move with the card. The row's crop then shows the whole frame."""
    iw, ih = im.size
    cw = round(W * (1 - 2 * SCREEN_MARGIN))
    chh = round(ih * cw / iw)
    x0, y0 = (W - cw) // 2, (H - chh) // 2
    k = max(W / iw, H / ih)
    fill = im.resize((round(iw * k), round(ih * k)), Image.BICUBIC)
    fill = fill.crop(((fill.width - W) // 2, (fill.height - H) // 2, (fill.width - W) // 2 + W, (fill.height - H) // 2 + H))
    fill = Image.eval(fill.filter(ImageFilter.GaussianBlur(H * 0.02)), lambda v: int(v * 0.45))
    fill.paste(im.resize((cw, chh), Image.LANCZOS), (x0, y0))
    for b in beats:
        if b.get("pos") and b.get("shot") == row["id"]:
            b["pos"] = [(x0 + b["pos"][0] * cw) / W, (y0 + b["pos"][1] * chh) / H]
    row.update(crop_x=0.5, zoom=1.0)
    return fill


def render_video(timed: dict, pics: dict, pic_dirs: list[Path], out: Path, short_id: str) -> int:
    """The silent 1080x1920 video, frame by frame; returns how many beat spots were moved into the crop."""
    fps, rows = timed["fps"], timed["shots"]
    hero_faces = ASM.hero_faces_of(timed)
    beats = [dict(b) for b in timed.get("visual_beats", [])]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-frames:v", str(timed["frames"]), str(out)], stdin=subprocess.PIPE)
    moved, last = 0, None
    for row in rows:
        name = (pics.get(row["picture"]) or {}).get("file") or f"{row['picture']}.png"
        pic = next((d / name for d in pic_dirs if (d / name).exists()), None)
        if pic is None:
            ff.kill()
            raise FileNotFoundError(f"{short_id}: picture {name} not found")
        im = Image.open(pic).convert("RGB")
        if row["picture"].startswith(SCREEN):
            im = fit_screen(im, beats, row)
        moved += fit_spots(beats, row, *im.size)
        sb = ASM.beats_for_shot(beats, row, timed["pictures"], hero_faces, pic_dirs) if beats else []
        before = last
        for f in range(row["start_frame"], row["end_frame"]):
            last = short_frame(im, row, f, fps, sb, hero_faces, pic_dirs, before)
            ff.stdin.write(last.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit(f"{short_id}: ffmpeg failed")
    return moved


def with_cues(wav: Path, cues: list[dict], out: Path) -> Path:
    """VB-08: the read with the beats' cues on it (``assemble.cue_bus``; the read is 48 kHz mono, as the long mix)."""
    pcm, sr = voice_layer.read_wav(wav)
    assert sr == ASM.SR, f"the Short's read is {sr} Hz, the cues are made at {ASM.SR}"
    mix = np.clip(np.asarray(pcm, dtype=np.float64) + ASM.cue_bus(cues, len(pcm)), -1, 1)
    path = out / "voice_cues.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    return path


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


def render(doc: dict, short_id: str, audio: Path, out: Path, pic_dirs: list[Path], music: Path | None, tempo: float) -> Path:
    short = next(s for s in doc["shorts"] if s["id"] == short_id)
    out.mkdir(parents=True, exist_ok=True)
    wav, drift = prepare_audio(audio, out, tempo)
    aligned = short_words(short, wav, out)
    pcm, sr = voice_layer.read_wav(wav)
    duration = len(pcm) / sr + 0.5
    timed = time_short(doc, short, aligned["words"], duration)
    pics, _ = S.pictures(doc)
    silent = out / "silent.mp4"
    moved = render_video(timed, pics, pic_dirs, silent, short_id)
    voice = with_cues(wav, timed["audio"]["cues"], out)
    ass_captions(aligned["words"], out / "cap.ass")
    final = out / f"{short_id}.mp4"
    inputs = ["-i", str(silent), "-i", str(voice)]
    fc = "[2:a]volume=0.10,afade=t=out:st=%.2f:d=1.2[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]" % max(0.0, duration - 1.2)
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    else:
        fc = "[1:a]anull[a]"
    _run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{fc};[0:v]subtitles={out / 'cap.ass'}[v]", "-map", "[v]", "-map", "[a]",
          "-t", f"{duration:.2f}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(final)])
    rows = [{k: r[k] for k in ("id", "picture", "at", "crop_x", "zoom", "start", "end")} for r in timed["shots"]]
    report = {"duration": round(duration, 2), "timbre_review": drift, "shots": rows, "beats": BEATS.measure(timed),
              "cues": len(timed["audio"]["cues"]), "beat_spots_moved_into_crop": moved,
              "short_format": SF.check(SF.probe(final))}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if report["short_format"]:  # a file YouTube would not make a Short is never handed on (qa/short_format.py)
        raise SystemExit(f"{short_id}: not a Short: {report['short_format'][0]['detail']}")
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
