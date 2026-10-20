"""Render one Short of the production script's ``shorts`` block (docs/ORCHESTRATION.md SH-01..SH-04): 1080x1920, the video's own
pictures cropped around the hero (``crop_x``, ``zoom``) with a slow push, the same narrator, word-timed captions, a low music bed,
and the same visual-beat layer as the long video (SS-09): the Short is timed by ``timing.time_script`` on ``beats.short_doc`` and
every frame is finished by ``assemble.finish_frame`` (face focus, accents, close-ups, beats); the beats' cues are mixed with
``assemble.cue_bus``.

    python -m explainer_engine.production.shorts <script.json> --id SH01 --audio <read.mp3> --out <dir> [--pics DIR ...] [--tempo 1.05]

Free (local Whisper + ffmpeg). ``--tempo`` speeds the read with ffmpeg's pitch-preserving atempo, at most BP-02's ceiling
(the creator's own; docs/SOURCED_RULES.md), and the timbre check (``audio/voice_check``) runs on the result: on any drift the
original pace is used. The read's leading silence is trimmed so the hook is spoken from the first second (BP-11); the report
carries the hook timing (BP-11), the caption reading speed (BP-13) and the caption safe zone (BP-29).
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
from explainer_engine.standards import sourced_rules as SR

W, H = 1080, 1920  # the frame rate is the episode's (timing.time_script)
MAX_TEMPO = SR.T("BP-02", "max_tempo")  # BP-02: the creator's ceiling on a Short's speed-up
DEFAULT_TEMPO = SR.T("BP-02", "rates")[0]  # BP-02: the first offered rate is the default --tempo
LEAD_SILENCE_KEEP_S = 0.1  # BP-11: the leading silence of the read is trimmed to about this, so the hook starts by first_word_by_s
FIRST_WORD_BY_S = SR.T("BP-11", "first_word_by_s")
HOOK_DONE_BY_S = SR.T("BP-11", "hook_done_by_s")  # BP-11: the hook's last word ends by this (the tighter bound at 170 wpm)
SCREEN = "sc_"  # production/select_screen.py's stat cards: text across the whole 16:9 width, never cropped to 9:16
SCREEN_MARGIN = 0.03  # share of the Short's width left on each side of a fitted card
CAP_FONT_PX, CAP_MARGIN_LR, CAP_MARGIN_V = 76, 90, 430  # the ASS caption style (unchanged; BP-29 only reports how it sits)
CAP_WORDS_PER_BLOCK = 3  # words per caption block (BP-13 allows up to block_words_max)


def narration(short: dict) -> str:
    return " ".join(line["text"].strip() for line in short["lines"]) + "\n"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def audio_chain(tempo: float) -> str:
    """The ffmpeg audio filter of the Short's read: leading silence trimmed to about LEAD_SILENCE_KEEP_S (BP-11: the hook is
    spoken from the first second), the tempo (BP-02), then the shared loudness target."""
    trim = f"silenceremove=start_periods=1:start_threshold=-45dB:start_silence={LEAD_SILENCE_KEEP_S},"
    return trim + (f"atempo={tempo}," if tempo != 1.0 else "") + targets.loudnorm("short")


def prepare_audio(src: Path, out: Path, tempo: float) -> tuple[Path, list[dict]]:
    """Levelled mono wav (leading silence trimmed, tempo applied) and a timbre report; falls back to the original pace on drift."""
    assert 1.0 <= tempo <= MAX_TEMPO, f"tempo above {MAX_TEMPO} is not allowed (BP-02)"
    wav = out / "short.wav"
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", audio_chain(tempo), "-ac", "1", "-ar", "48000", str(wav)])
    pcm, sr = voice_layer.read_wav(wav)
    found, _ = voice_check.check(np.asarray(pcm, dtype=float), sr)
    drift = [f for f in found if f.get("severity") in ("FAIL", "REVIEW")]
    if tempo != 1.0 and drift:
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", audio_chain(1.0), "-ac", "1", "-ar", "48000", str(wav)])
    return wav, drift


def hook_timing(words: list[dict], hook_words: int | None = None) -> dict:
    """BP-11 on the real read: the first word starts within FIRST_WORD_BY_S of frame 0 and, when ``hook_words`` (the hook
    line's token count) is given, the hook's last word ends by HOOK_DONE_BY_S. A miss carries BP-11's severity (binding
    FAIL: the render stops)."""
    start = float(words[0]["s"]) if words else None
    end = float(words[hook_words - 1]["e"]) if hook_words and 0 < hook_words <= len(words) else None
    why = []
    if start is None or start > FIRST_WORD_BY_S:
        why.append(f"the first word starts at {start} s, after {FIRST_WORD_BY_S} s: trim the read or re-cut the hook")
    if end is not None and end > HOOK_DONE_BY_S:
        why.append(f"the hook ends at {end:.2f} s, after {HOOK_DONE_BY_S} s: shorten the hook or re-read it")
    return {"first_word_s": None if start is None else round(start, 2), "limit_s": FIRST_WORD_BY_S,
            "hook_end_s": None if end is None else round(end, 2), "hook_limit_s": HOOK_DONE_BY_S,
            "severity": SR.rule("BP-11").get("severity", "REVIEW") if why else "PASS",
            "detail": ("; ".join(why) + " (BP-11)") if why else "the hook is spoken from the first second and complete by "
            f"{HOOK_DONE_BY_S:g} s (BP-11)"}


def caption_blocks(words: list[dict]) -> list[dict]:
    """The caption blocks as ``ass_captions`` burns them: CAP_WORDS_PER_BLOCK words or up to a sentence end, each shown from
    its first word until the next block starts (the last one 0.4 s past its last word, every block at least 0.2 s)."""
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= CAP_WORDS_PER_BLOCK or w["w"].rstrip("\"'”’)")[-1:] in ".?!":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    rows = []
    for k, ln in enumerate(lines):
        end = lines[k + 1][0]["s"] if k + 1 < len(lines) else ln[-1]["e"] + 0.4
        rows.append({"start": ln[0]["s"], "end": max(end - 0.02, ln[0]["s"] + 0.2), "text": " ".join(x["w"] for x in ln).upper(),
                     "words": len(ln)})
    return rows


def caption_report(words: list[dict]) -> dict:
    """BP-13 (hypothesis, REVIEW only): reading speed and block sizes of the burned captions."""
    cps_max, (block_lo, block_hi) = SR.T("BP-13", "cps_max"), SR.T("BP-13", "block_s")
    words_max, s_per_word = SR.T("BP-13", "block_words_max"), SR.T("BP-13", "s_per_word_min")
    blocks = caption_blocks(words)
    if not blocks:
        return {"blocks": 0, "severity": "REVIEW", "detail": "no caption blocks (BP-13)"}
    cps = [len(b["text"]) / max(b["end"] - b["start"], 1e-6) for b in blocks]
    outside = [b for b in blocks if not block_lo <= b["end"] - b["start"] <= block_hi]
    fast = [b for b in blocks if (b["end"] - b["start"]) / b["words"] < s_per_word]
    too_many = [b for b in blocks if b["words"] > words_max]
    why = []
    if max(cps) > cps_max:
        why.append(f"{sum(c > cps_max for c in cps)} block(s) over {cps_max} characters per second (max {max(cps):.0f})")
    if fast:
        why.append(f"{len(fast)} block(s) under {s_per_word} s per word")
    if outside:
        why.append(f"{len(outside)} block(s) shown outside {block_lo}-{block_hi} s")
    if too_many:
        why.append(f"{len(too_many)} block(s) over {words_max} words")
    return {"blocks": len(blocks), "cps_max": round(max(cps), 1), "words_per_block_max": max(b["words"] for b in blocks),
            "severity": "REVIEW" if why else "PASS",
            "detail": ("; ".join(why) + " (BP-13)") if why else "captions read at adult subtitle speed (BP-13)"}


def safe_zone_report() -> dict:
    """BP-29 (hypothesis, REVIEW only): where the burned captions and a fitted stat card sit against the 1080 x 1920 ad safe
    zone. Reports only; the rendered margins are unchanged."""
    (sx0, sx1), (sy0, sy1) = SR.T("BP-29", "safe_x_px"), SR.T("BP-29", "safe_y_px")
    cap = [CAP_MARGIN_LR, H - CAP_MARGIN_V - CAP_FONT_PX, W - CAP_MARGIN_LR, H - CAP_MARGIN_V]  # one caption line, bottom-centred
    card_w = round(W * (1 - 2 * SCREEN_MARGIN))
    card = [(W - card_w) // 2, None, (W - card_w) // 2 + card_w, None]
    why = []
    if cap[0] < sx0 or cap[2] > sx1:
        why.append(f"caption box x {cap[0]}-{cap[2]} px leaves the safe x {sx0}-{sx1}")
    if cap[1] < sy0 or cap[3] > sy1:
        why.append(f"caption box y {cap[1]}-{cap[3]} px leaves the safe y {sy0}-{sy1}")
    if card[0] < sx0 or card[2] > sx1:
        why.append(f"a fitted stat card spans x {card[0]}-{card[2]} px, past the safe x {sx0}-{sx1}")
    return {"caption_box_px": cap, "card_x_px": [card[0], card[2]], "safe_x_px": [sx0, sx1], "safe_y_px": [sy0, sy1],
            "severity": "REVIEW" if why else "PASS",
            "detail": ("; ".join(why) + " (BP-29): captions, labels and cards inside the ad safe zone") if why
            else "captions and cards inside the ad safe zone (BP-29)"}


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
            f"Style: Cap,DejaVu Sans,{CAP_FONT_PX},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,"
            f"{CAP_MARGIN_LR},{CAP_MARGIN_LR},{CAP_MARGIN_V},1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    rows = [f"Dialogue: 0,{t(b['start'])},{t(b['end'])},Cap,,0,0,0,,{b['text']}" for b in caption_blocks(words)]
    path.write_text(head + "\n".join(rows) + "\n", encoding="utf-8")


def music_filter(duration: float) -> str:
    """The Short's music under the voice (input 2 over input 1): BP-62's fades, in at the start and out at the end."""
    f_in, f_out = float(SR.T("BP-62", "fade_in_s")), float(SR.T("BP-62", "fade_out_s"))
    return (f"[2:a]volume=0.10,afade=t=in:st=0:d={f_in:.2f},afade=t=out:st={max(0.0, duration - f_out):.2f}:d={f_out:.2f}[m];"
            "[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")


def render(doc: dict, short_id: str, audio: Path, out: Path, pic_dirs: list[Path], music: Path | None, tempo: float) -> Path:
    short = next(s for s in doc["shorts"] if s["id"] == short_id)
    out.mkdir(parents=True, exist_ok=True)
    wav, drift = prepare_audio(audio, out, tempo)
    aligned = short_words(short, wav, out)
    hook = hook_timing(aligned["words"], len(scribe_words.script_tokens(short["lines"][0]["text"])))
    if hook["severity"] == "FAIL":  # BP-11: a Short whose hook is not spoken from the first second is never handed on
        (out / "report.json").write_text(json.dumps({"timbre_review": drift, "hook_timing": hook}, indent=1), encoding="utf-8")
        raise SystemExit(f"{short_id}: {hook['detail']}")
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
    fc = music_filter(duration)  # BP-62 fades
    if music:
        # only a track the library marks loopable is tiled; a one-shot plays once and the fade-out covers the rest
        loop_args = ["-stream_loop", "-1"] if ASM.Sounds([]).loopable(music.stem) else []
        inputs += [*loop_args, "-i", str(music)]
    else:
        fc = "[1:a]anull[a]"
    _run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{fc};[0:v]subtitles={out / 'cap.ass'}[v]", "-map", "[v]", "-map", "[a]",
          "-t", f"{duration:.2f}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", *ASM.AUDIO_CODEC, str(final)])  # BP-63: stereo AAC at the delivery bitrate
    rows = [{k: r[k] for k in ("id", "picture", "at", "crop_x", "zoom", "start", "end")} for r in timed["shots"]]
    report = {"duration": round(duration, 2), "timbre_review": drift, "shots": rows, "beats": BEATS.measure(timed),
              "cues": len(timed["audio"]["cues"]), "beat_spots_moved_into_crop": moved,
              "hook_timing": hook, "captions": caption_report(aligned["words"]), "safe_zone": safe_zone_report(),
              "short_format": SF.check(SF.probe(final)),
              "loudness": measure_final(final)}  # BP-61: measured on the FINAL file, after cues and music, not the voice stem
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if report["short_format"]:  # a file YouTube would not make a Short is never handed on (qa/short_format.py)
        raise SystemExit(f"{short_id}: not a Short: {report['short_format'][0]['detail']}")
    bad = targets.failures(report["loudness"])
    if bad:  # BP-61: a Short whose loudness, short-term peak or true peak fails is never handed on
        raise SystemExit(f"{short_id}: loudness fails {', '.join(bad)} (BP-61); fix the mix, then render again")
    return final


def measure_final(final: Path) -> dict:
    """ebur128 of the finished Short with the short profile's verdicts (BP-61: integrated, max short-term, true peak)."""
    meas = targets.measure_file(final)
    out = {k: v for k, v in meas.items() if k in ("lufs", "true_peak", "max_short_term", "lra")}
    out.update(targets.verdicts(meas, "short"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--id", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pics", action="append", default=[])
    ap.add_argument("--music")
    ap.add_argument("--tempo", type=float, default=DEFAULT_TEMPO)  # BP-02
    a = ap.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    dirs = [Path(x) for x in a.pics] + [path.parent / d for d in doc.get("picture_dirs", [])]
    final = render(doc, a.id, Path(a.audio), Path(a.out), dirs, Path(a.music) if a.music else None, a.tempo)
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
