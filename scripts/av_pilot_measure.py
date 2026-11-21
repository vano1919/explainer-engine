"""Measure and compare two runs of the AV pilot (scripts/av_pilot.py): motion, frozen stretches, render speed, sound timing.

    python scripts/av_pilot_measure.py <baseline ep folder> <new ep folder> --out <folder>

Writes ``<out>/compare.json`` and ``compare.md``, a contact sheet per shot (``sheet_<shot>.jpg``: baseline above, new below, five
frames each) and an SFX-stem picture with the event frames marked (``sfx_<run>.png``). Everything is measured on the files the
runner wrote: the shot clips, ``production/stages``, ``audio/stems`` and the cue sheet. Nothing here listens: a waveform and its
onsets are numbers, not a person's ear.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

FROZEN_DIFF, FROZEN_SIZE = 0.4, (160, 90)     # BP-164 as the registry reads it (frozen_diff_max, analysis_size)


def frames_of(mp4: Path, size=FROZEN_SIZE) -> np.ndarray:
    w, h = size
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(mp4), "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def motion(mp4: Path) -> dict:
    g = frames_of(mp4)
    d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)) if len(g) > 1 else np.zeros(0)
    run = longest = 0
    for v in d:
        run = run + 1 if v < FROZEN_DIFF else 0
        longest = max(longest, run + 1 if run else 0)
    # the overall travel: phase correlation of the first and last frame (pixels at 160x90, scaled to the frame width share)
    a, b = g[0] - g[0].mean(), g[-1] - g[-1].mean()
    f = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    r = np.abs(np.fft.ifft2(f / (np.abs(f) + 1e-6)))
    dy, dx = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = (dy - g.shape[1] if dy > g.shape[1] // 2 else dy), (dx - g.shape[2] if dx > g.shape[2] // 2 else dx)
    return {"frames": int(len(g)), "mean_change": round(float(d.mean()) if len(d) else 0.0, 3),
            "frames_with_change_share": round(float((d >= FROZEN_DIFF).mean()) if len(d) else 0.0, 3),
            "longest_frozen_frames": int(longest), "first_last_diff": round(float(np.abs(g[-1] - g[0]).mean()), 2),
            "global_shift_px160": [int(dx), int(dy)]}


def sheet(clips: list[tuple[str, Path]], out: Path, n: int = 5, w: int = 384) -> None:
    rows = []
    for label, mp4 in clips:
        info = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout
        total = int(info.strip() or 1)
        pics = []
        for k in range(n):
            f = int(round(k * (total - 1) / (n - 1)))
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(mp4), "-vf", f"select=eq(n\\,{f}),scale={w}:-2",
                                  "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
            ImageDraw.Draw(im).text((6, 6), f"{label} f{f}", fill=(255, 255, 0))
            pics.append(im)
        row = Image.new("RGB", (w * n, pics[0].height))
        for k, im in enumerate(pics):
            row.paste(im, (k * w, 0))
        rows.append(row)
    out_im = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        out_im.paste(r, (0, y))
        y += r.height
    out_im.save(out, quality=88)


def read_wav(p: Path) -> tuple[np.ndarray, int]:
    """Mono float samples in [-1, 1] (16- or 32-bit PCM) and the rate."""
    with wave.open(str(p)) as wf:
        sr, ch, n, sw = wf.getframerate(), wf.getnchannels(), wf.getnframes(), wf.getsampwidth()
        x = np.frombuffer(wf.readframes(n), {2: np.int16, 4: np.int32}[sw]).astype(np.float32)
    return x.reshape(-1, ch).mean(axis=1) / float(2 ** (8 * sw - 1)), sr


def sfx_picture(ep: Path, out: Path) -> dict:
    stems = ep / "audio" / "stems"
    p = next((q for q in (stems / "sfx.wav", stems / "sfx_stem.wav") if q.is_file()), None)
    if p is None:
        return {"sfx_stem": None}
    x, sr = read_wav(p)
    hop = int(sr * 0.01)
    env = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode="same"))[::hop]
    db = 20 * np.log10(np.maximum(env, 1e-5))
    W, H = 1600, 260
    im = Image.new("RGB", (W, H), (250, 250, 247))
    d = ImageDraw.Draw(im)
    secs = len(x) / sr
    pts = [(int(i * W / len(db)), int(H - 20 - (max(-60.0, v) + 60) / 60 * (H - 40))) for i, v in enumerate(db)]
    d.line(pts, fill=(40, 60, 120), width=1)
    rep = json.loads((ep / "audio" / "stems_report.json").read_text()) if (ep / "audio" / "stems_report.json").is_file() else {}
    for e in rep.get("events_placed", []):
        X = int(e["at_s"] / secs * W)
        d.line([(X, 10), (X, H - 20)], fill=(200, 60, 40), width=1)
        if e.get("onset_s") is not None:
            X2 = int(e["onset_s"] / secs * W)
            d.line([(X2, 10), (X2, 30)], fill=(20, 150, 60), width=2)
    rec = json.loads((ep / "production" / "shot_records.json").read_text())["shots"]
    for s in rec[1:]:
        X = int(s["start_sec"] / secs * W)
        d.line([(X, 0), (X, H)], fill=(120, 120, 120), width=1)
    d.text((6, H - 16), f"{p.name}: RMS dB (10 ms), red = cue start, green = measured onset, grey = cuts; {secs:.1f} s", fill=(0, 0, 0))
    im.save(out)
    return {"sfx_stem": str(p), "seconds": round(secs, 2)}


def run_summary(ep: Path) -> dict:
    st = ep / "production" / "stages"
    stages = {}
    for p in sorted(st.glob("*.json")):
        r = json.loads(p.read_text())
        stages[r["stage"]] = {"status": r["verdict"]["status"], "elapsed_s": r.get("elapsed_s"),
                              "rows": {g["gate"]: g["status"] for g in r.get("rows", [])}}
    recs = json.loads((ep / "production" / "shot_records.json").read_text())["shots"]
    shots = {}
    for s in recs:
        clip = ep / "production" / "shot_clips" / f"{s['shot_id']}.clip.json"
        rend = json.loads(clip.read_text())["renderer"] if clip.is_file() else {}
        g = rend.get("gates") or {}
        mp4 = Path(s["clip_path"]) if s.get("clip_path") else None
        shots[s["shot_id"]] = {"route": s["route"], "frames": s["total_frames"], "status": s["status"],
                               "sec_per_frame": rend.get("sec_per_frame"), "prep_s": rend.get("prep_s"),
                               "profile": rend.get("profile"), "cameras": [c.get("move") for c in rend.get("cameras") or []]
                               or ([rend["camera"]["move"]] if rend.get("camera") else []),
                               "families": rend.get("families"), "gates_failed": g.get("failed"), "gates_review": g.get("review"),
                               "gates_not_run": g.get("not_run"), "longest_still_frames_renderer": rend.get("longest_still_frames"),
                               "sha256": s.get("output_sha256"),
                               "measured": motion(mp4) if mp4 and mp4.is_file() else None}
    sheet_doc = json.loads((ep / "audio" / "stems" / "cue_sheet.json").read_text()) \
        if (ep / "audio" / "stems" / "cue_sheet.json").is_file() else {"rows": []}
    rep = json.loads((ep / "audio" / "stems_report.json").read_text()) if (ep / "audio" / "stems_report.json").is_file() else {}
    starts = {r["cue_id"]: r["start_s"] for r in sheet_doc["rows"]}
    offs = [round((e["onset_s"] - starts[e["cue_id"]]) * 1000, 1) for e in rep.get("events_placed", [])
            if e.get("onset_s") is not None and e.get("cue_id") in starts]
    by_layer: dict[str, int] = {}
    for r in sheet_doc["rows"]:
        by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
    master = ep / "production" / "master.json"
    return {"stages": stages, "shots": shots, "cue_rows_by_layer": by_layer,
            "event_rows": sum(1 for r in sheet_doc["rows"] if r.get("event_id")),
            "rows_from_words": sum(1 for r in sheet_doc["rows"] if "word" in str(r.get("reason", ""))),
            "onset_minus_cue_ms": offs, "missing": [m.get("class") for m in sheet_doc.get("missing", [])],
            "master": json.loads(master.read_text()) if master.is_file() else None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("baseline", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    doc = {"baseline": run_summary(a.baseline), "new": run_summary(a.new)}
    for name, ep in (("baseline", a.baseline), ("new", a.new)):
        doc[name]["sfx_picture"] = sfx_picture(ep, a.out / f"sfx_{name}.png")
    for sid in doc["new"]["shots"]:
        clips = []
        for name, ep in (("baseline", a.baseline), ("new", a.new)):
            s = doc[name]["shots"].get(sid)
            mp4 = ep / "production" / "shot_clips" / f"{sid}.mp4"
            if s and mp4.is_file():
                clips.append((f"{name} {sid}", mp4))
        if clips:
            sheet(clips, a.out / f"sheet_{sid}.jpg")
    (a.out / "compare.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    lines = ["| shot | route | run | status | cameras | families | mean change | share of frames changing | longest frozen | "
             "s/frame | failed gates |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for sid in doc["new"]["shots"]:
        for name in ("baseline", "new"):
            s = doc[name]["shots"].get(sid)
            if not s:
                continue
            m = s["measured"] or {}
            lines.append(f"| {sid} | {s['route']} | {name} | {s['status']} | {', '.join(s['cameras'] or [])} | "
                         f"{', '.join(s['families'] or [])} | {m.get('mean_change')} | {m.get('frames_with_change_share')} | "
                         f"{m.get('longest_frozen_frames')} | {s['sec_per_frame']} | {', '.join(s['gates_failed'] or [])} |")
    (a.out / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(a.out / "compare.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
