"""Shorts cut from the finished long video (the creator, 2026-10-21): no new read of the story, only one shared outro line.

Each Short = the long video's own opening (the question card and its first lines, ``intro_end``) + one moment of the video
(``start``..``end`` on the long video's clock, cut on sentence edges) + a shared outro line that points to the full video and
ends on a phrase the opening question answers, so the Short loops without a visible start or end: the last frame is the
first frame (the question card, ``card_at``) and the outro's last words lead into the opening question.

The whole Short is sped up by ``tempo`` (the creator: about 15 % faster), laid out 1080x1920: the 16:9 frame full width in
the middle over a blurred copy of itself, a title band above, word-timed captions below and a small "full video" label.
Free: ffmpeg + PIL only; the outro line is the only paid asset and is shared by every Short.

    python -m explainer_engine.production.clip_shorts <plan.json>

plan.json: {"video", "words", "outro", "outro_words", "music", "out", "tempo": 1.15, "intro_end": 8.4, "card_at": 1.0,
            "title": "...", "label": "...", "clips": [{"id": "CS01", "start": 62.48, "end": 119.96, "title": "..."}]}
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from explainer_engine.design import palette
from explainer_engine.qa import targets

W, H = 1080, 1920
SIDE_CROP = 0.06  # share of the 16:9 width cut on each side, so the picture fills more of the phone (the card's heads stay in)
FG_H = round(W * 9 / (16 * (1 - 2 * SIDE_CROP)) / 2) * 2  # the 16:9 frame at full width after the side crop
FG_Y = (H - FG_H) // 2
FPS = 30
PAD_IN, PAD_OUT = 0.2, 0.45  # air before the clip's first word and after its last one (long-video seconds)
OUTRO_TAIL = 0.25  # the card holds this long after the outro's last word before the loop starts again
FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Bangers-Regular.ttf"
CAP_WORDS = 3


def words_in(words: list[dict], start: float, end: float) -> list[dict]:
    """The long video's words spoken inside [start, end] (word dicts {w, s, e})."""
    return [w for w in words if w["s"] >= start - 0.01 and w["e"] <= end + 0.01]


def timeline(clip: dict, intro_end: float, outro_len: float) -> list[dict]:
    """The three parts of a Short on the long video's clock, before the speed-up: intro, the moment, outro."""
    if clip["end"] <= clip["start"]:
        raise ValueError(f"{clip['id']}: end before start")
    return [{"part": "intro", "src_start": 0.0, "src_end": intro_end},
            {"part": "clip", "src_start": max(0.0, clip["start"] - PAD_IN), "src_end": clip["end"] + PAD_OUT},
            {"part": "outro", "src_start": 0.0, "src_end": outro_len + OUTRO_TAIL}]


def caption_words(parts: list[dict], long_words: list[dict], outro_words: list[dict], tempo: float) -> list[dict]:
    """Every spoken word on the Short's own clock (after the speed-up): {w, s, e}."""
    out, t0 = [], 0.0
    for p in parts:
        if p["part"] == "outro":
            src = [{"w": w["text"], "s": w["start"], "e": w["end"]} for w in outro_words]
        else:
            src = words_in(long_words, p["src_start"], p["src_end"])
        for w in src:
            out.append({"w": w["w"], "s": round((t0 + w["s"] - p["src_start"]) / tempo, 3),
                        "e": round((t0 + w["e"] - p["src_start"]) / tempo, 3)})
        t0 += p["src_end"] - p["src_start"]
    return out


def duration(parts: list[dict], tempo: float) -> float:
    return sum(p["src_end"] - p["src_start"] for p in parts) / tempo


def _ts(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass(words: list[dict], path: Path) -> Path:
    """Captions: blocks of CAP_WORDS words under the picture, the spoken word in the accent colour."""
    tok = palette.load()["tokens"]

    def bgr(hexv: str) -> str:
        h = hexv.lstrip("#")
        return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"

    paper, ink, accent = bgr(tok["paper"]["hex"]), bgr(tok["ink"]["hex"]), bgr(tok["uncertain_amber"]["hex"])
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
            "MarginV, Encoding\n"
            f"Style: Cap,Bangers,108,{paper},{paper},{ink},&H80000000,0,0,0,0,100,100,2,0,1,6,2,8,70,70,{FG_Y + FG_H + 70},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = []
    blocks = [words[i:i + CAP_WORDS] for i in range(0, len(words), CAP_WORDS)]
    for bi, b in enumerate(blocks):
        end_block = blocks[bi + 1][0]["s"] if bi + 1 < len(blocks) else b[-1]["e"] + 0.3
        for k, w in enumerate(b):
            s = w["s"] if k else b[0]["s"]
            e = b[k + 1]["s"] if k + 1 < len(b) else end_block
            txt = " ".join((f"{{\\c{accent}}}{x['w'].upper()}{{\\c{paper}}}" if j == k else x["w"].upper())
                           for j, x in enumerate(b))
            lines.append(f"Dialogue: 0,{_ts(s)},{_ts(max(e, s + 0.05))},Cap,,0,0,0,,{txt}")
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def band(title: str, label: str, path: Path) -> Path:
    """The transparent overlay: the title above the picture and the small full-video label under the captions."""
    tok = palette.load()["tokens"]
    fill, stroke = tok["paper"]["hex"], tok["ink"]["hex"]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 104
    lines = _wrap(title.upper(), d, size, W - 120)
    font = ImageFont.truetype(str(FONT), size)
    y = FG_Y - 70 - len(lines) * int(size * 1.05)
    for ln in lines:
        d.text(((W - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=fill, stroke_width=7, stroke_fill=stroke)
        y += int(size * 1.05)
    small = ImageFont.truetype(str(FONT), 54)
    lw = d.textlength(label.upper(), font=small)
    ly = FG_Y + FG_H + 330
    d.rounded_rectangle(((W - lw) / 2 - 30, ly - 12, (W + lw) / 2 + 30, ly + 70), radius=22, fill=(0, 0, 0, 170))
    d.text(((W - lw) / 2, ly), label.upper(), font=small, fill=fill)
    im.save(path)
    return path


def _wrap(text: str, d: ImageDraw.ImageDraw, size: int, width: int) -> list[str]:
    font = ImageFont.truetype(str(FONT), size)
    out, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and d.textlength(nxt, font=font) > width:
            out.append(cur)
            cur = word
        else:
            cur = nxt
    return out + ([cur] if cur else [])


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def render(plan: dict, clip: dict, root: Path) -> dict:
    out = Path(plan["out"]) / clip["id"]
    out.mkdir(parents=True, exist_ok=True)
    video, tempo = Path(plan["video"]), float(plan.get("tempo", 1.15))
    long_words = json.loads(Path(plan["words"]).read_text(encoding="utf-8"))["words"]
    outro_words = [w for w in json.loads(Path(plan["outro_words"]).read_text(encoding="utf-8"))["words"]
                   if w.get("type", "word") == "word"]
    outro_len = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      plan["outro"]], capture_output=True, text=True, check=True).stdout)
    outro_len = min(outro_len, outro_words[-1]["end"] + 0.15)
    parts = timeline(clip, float(plan.get("intro_end", 8.4)), outro_len)
    card_at = float(plan.get("card_at", 1.0))
    card = out / "card.png"
    _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{card_at}", "-i", str(video), "-frames:v", "1", str(card)])
    intro, mid, outro = parts
    d_out = outro["src_end"]
    # the 16:9 programme at normal speed: card held over the fade-in, the opening, the moment, the card under the outro
    fc = (f"[0:v]trim={card_at}:{intro['src_end']},setpts=PTS-STARTPTS,fps={FPS}[iv];"
          f"[1:v]loop=-1:1,trim=0:{card_at},setpts=PTS-STARTPTS,fps={FPS}[ih];"
          f"[0:v]trim={mid['src_start']}:{mid['src_end']},setpts=PTS-STARTPTS,fps={FPS}[mv];"
          f"[1:v]loop=-1:1,trim=0:{d_out},setpts=PTS-STARTPTS,fps={FPS}[ov];"
          f"[0:a]atrim=0:{intro['src_end']},asetpts=PTS-STARTPTS,afade=t=out:st={intro['src_end'] - 0.12}:d=0.12[ia];"
          f"[0:a]atrim={mid['src_start']}:{mid['src_end']},asetpts=PTS-STARTPTS,afade=t=in:d=0.12,"
          f"afade=t=out:st={mid['src_end'] - mid['src_start'] - 0.3}:d=0.3[ma];"
          f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:{d_out}[ovo];"
          f"[3:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{d_out},volume=0.06,"
          f"afade=t=in:d=0.4,afade=t=out:st={d_out - 1.2}:d=1.2[om];"
          "[ovo][om]amix=inputs=2:duration=first:normalize=0[oa];"
          "[ih][iv][mv][ov]concat=n=4:v=1:a=0[v];[ia][ma][oa]concat=n=3:v=0:a=1[a]")
    prog = out / "programme.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-loop", "1", "-i", str(card), "-i", plan["outro"],
          "-i", plan["music"], "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16",
          "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(prog).replace(".mp4", ".mov")])
    prog = Path(str(prog).replace(".mp4", ".mov"))
    words = caption_words(parts, long_words, outro_words, tempo)
    cap = ass(words, out / "cap.ass")
    over = band(plan["title"], plan["label"], out / "band.png")
    final = out / f"{clip['id']}.mp4"
    fonts = FONT.parent
    vf = (f"[0:v]setpts=PTS/{tempo},fps={FPS},split[a][b];"
          f"[a]scale=-2:{H},crop={W}:{H},boxblur=28:2,eq=brightness=-0.22:saturation=0.8[bg];"
          f"[b]crop=iw*{1 - 2 * SIDE_CROP}:ih,scale={W}:{FG_H}[fg];[bg][fg]overlay=0:{FG_Y}[base];[base][1:v]overlay=0:0[o];"
          f"[o]subtitles={cap}:fontsdir={fonts}[v];"
          f"[0:a]atempo={tempo},{targets.loudnorm('short')}[au]")
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(prog), "-i", str(over), "-filter_complex", vf, "-map", "[v]",
          "-map", "[au]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(final)])
    prog.unlink(missing_ok=True)
    report = {"id": clip["id"], "duration": round(duration(parts, tempo), 2), "tempo": tempo, "parts": parts,
              "words": len(words), "first_word_s": words[0]["s"] if words else None,
              "loudness": {k: v for k, v in targets.measure_file(final).items() if k in ("lufs", "true_peak")}}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    only = set(filter(None, a.only.split(",")))
    for clip in plan["clips"]:
        if only and clip["id"] not in only:
            continue
        print(json.dumps(render(plan, clip, Path(a.plan).parent)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
