"""Assemble Day 1 v6 (D-42): the storyboard timed on the read (edit/board.py), speech bubbles on held pictures, ambience
beds that change with the story state (the fire's crackle starts on "and fire", not with a beat), world sounds on their
words, and the music dipped under every world sound with millisecond ramps (audio/duck.py) as well as under the voice.

    python assemble_v6.py <words.json> <narration.wav> <out dir> --pics <dir> [--pics <dir> ...] --snd <dir> [--audio-only]

Pictures are looked up by id in the --pics folders in order (v6_* first, then the v5 Gemini set); a v6 picture that does not
exist yet uses its board ``stand_in`` and the report says so. CPU only (PIL, numpy, ffmpeg).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.audio import duck  # noqa: E402
from explainer_engine.edit import board as BOARD  # noqa: E402
from explainer_engine.finish import bubbles as BUB  # noqa: E402
from explainer_engine.finish.grade import grade  # noqa: E402
from explainer_engine.world import resolver  # noqa: E402

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("v5asm", HERE.parent / "day1_v5" / "assemble.py")
V5 = importlib.util.module_from_spec(spec)
sys.argv, _argv = sys.argv[:1], sys.argv  # the v5 module reads its words at import; keep our argv
spec.loader.exec_module(V5)
sys.argv = _argv
FPS, OW, OH, SR = 30, 1920, 1080, 48000
LIB = ROOT / "assets" / "audio" / "library"
CODEX = resolver.load_codex()
WORLD = resolver.resolve(json.loads((HERE / "world_spec.json").read_text()))
GRADE = CODEX["grades"][WORLD["grade"]]
BEDS = [("Could", "wind_storm"), ("Right.", "wind_day"), ("Uh-oh.", "wind_storm"), ("and fire", "fire")]
SFX = [  # (phrase the sound sits on, library id or scratch file, gain dB, max seconds)
    ("Right.", "landing_thud__v1", -16, 0.6),
    ("For a whole hour", "tick_loop_4s__v1", -22, 2.4),
    ("Somebody write that", "pencil_scribble__v2", -20, 1.0),
    ("Latrines go", "footstep_dirt__v2", -20, 0.5),
    ("So they build", "cloth_rustle__v2", -17, 1.2),
    ("Why grass?", "cloth_rustle__v3", -18, 1.0),
    ("Now. Fire.", "cloth_rustle__v1", -18, 0.8),
    ("Then Einstein takes", "cloth_rustle__v2", -20, 0.7),
    ("One careful breath", "gasp_inhale__v1", -24, 0.9),
    ("and fire", "whoosh", -15, 0.9),
]
BUBBLE_POP = ("pop_in__v1", -26)


def lib_audio(name: str, snd: Path) -> np.ndarray:
    if (snd / f"{name}.mp3").exists():
        return V5.load_audio(snd / f"{name}.mp3")
    item = next(x for x in json.load(open(LIB / "manifest.json"))["items"] if x["id"] == name)
    a, sr = V5.read_wav(LIB / item["file"])
    if sr != SR:
        a = np.interp(np.arange(int(len(a) * SR / sr)) * sr / SR, np.arange(len(a)), a)
    return a


def fade(seg: np.ndarray, n: int) -> np.ndarray:
    n = min(n, len(seg) // 2)
    if n > 0:
        seg[:n] *= np.linspace(0, 1, n)
        seg[-n:] *= np.linspace(1, 0, n)
    return seg


def build_audio(timed: dict, words: list[dict], narration: np.ndarray, snd: Path, stats: dict) -> np.ndarray:
    n = len(narration)
    t = lambda s: int(s * SR)  # noqa: E731
    voice = narration / (np.abs(narration).max() + 1e-9) * 0.9
    env = V5.envelope(voice)
    vduck = 1.0 - 0.55 * np.convolve(env, np.ones(t(0.25)) / t(0.25), mode="same")
    # beds: crossfade 1.5 s at each change, the change sits on its phrase
    marks = [(0.0 if k == 0 else max(0.0, words[BOARD.find_phrase(words, p)]["s"] - 0.4), name)
             for k, (p, name) in enumerate(BEDS)]
    beds = {k: V5.load_audio(snd / f"{k}.mp3") for k in {b for _, b in BEDS}}
    bed = np.zeros(n)
    for k, (a, name) in enumerate(marks):
        b = marks[k + 1][0] + 1.5 if k + 1 < len(marks) else n / SR
        seg = V5.loop_to(beds[name], n)[t(a):min(n, t(b))].copy()
        bed[t(a):t(a) + len(seg)] += fade(seg, t(1.5))
    bed = bed / (np.abs(bed).max() + 1e-9) * V5.db(-13)
    music = np.zeros(n)
    for name, a, b in [("clockwork_loop__v1", 0.0, 100.0), ("sneaky_pizzicato__v1", 39.0, 120.0), ("clockwork_loop__v1", 120.0, 400.0)]:
        m, _ = V5.read_wav(LIB / "music" / f"{name}.wav")
        b = min(b, n / SR)
        if b <= a:
            continue
        seg = fade(V5.loop_to(m, t(b - a)), t(2.0))
        music[t(a):t(a) + len(seg)] += seg[: n - t(a)]
    music = music / (np.abs(music).max() + 1e-9) * V5.db(-18)
    fx = np.zeros(n)
    stats["events"] = []
    starts = [w["s"] for w in words]

    def place(sound: np.ndarray, at: float, gain_db: float, max_s: float, label: str, stop_before_word: bool = True):
        w = sound[: t(max_s)].copy()
        w = w / (np.abs(w).max() + 1e-9) * V5.db(gain_db)
        a = max(0, t(at))
        if stop_before_word:  # a world sound under a word keeps to a hush: it ends before the next word (UR-15)
            nxt = next((x for x in starts if x > at + 0.25), None)
            if nxt is not None:
                w = w[: max(t(nxt - at - 0.03), t(0.12))]
        if len(w) > 480:
            w[-480:] *= np.linspace(1, 0, 480)
        w[: min(240, len(w))] *= np.linspace(0, 1, min(240, len(w)))
        fx[a:a + len(w)] += w[: n - a]
        stats["events"].append({"id": label, "at": round(at, 3), "dur": round(len(w) / SR, 3)})

    for phrase, name, g, mx in SFX:
        at = words[BOARD.find_phrase(words, phrase)]["s"] - 0.05
        place(lib_audio(name, snd), at, g, mx, name, stop_before_word=False)  # foley runs its length under the voice, quiet
    pop = lib_audio(BUBBLE_POP[0], snd)
    for s in timed["shots"]:
        for b in s["bubbles"]:
            place(pop, b["start"], BUBBLE_POP[1], 0.25, "bubble_pop", stop_before_word=False)
    fduck = duck.duck_gain(fx, SR, n, depth_db=9.0, threshold=0.01, attack_ms=20, release_ms=280, hold_ms=80)
    bduck = duck.duck_gain(fx, SR, n, depth_db=4.0, threshold=0.01, attack_ms=25, release_ms=350, hold_ms=80)
    stats["music_dip_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(fduck, SR), 3)
    stats["music_dip_depth_db"] = round(float(20 * np.log10(fduck.min())), 2)
    mix = voice * V5.db(-3) + (bed * bduck + music * fduck) * vduck + fx
    speaking = env > 0.15
    stats.update(voice_rms_db=V5.rms_db((voice * V5.db(-3))[speaking]), bed_rms_db=V5.rms_db((bed * vduck)[speaking]),
                 music_rms_db=V5.rms_db((music * vduck)[speaking]))
    peak = np.abs(mix).max()
    return mix / peak * 0.89 if peak > 0.89 else mix


def find_picture(pid: str, dirs: list[Path], pics: dict, report: list) -> Path:
    for d in dirs:
        for cand in (d / f"{pid}.png", d / f"{pid}_v1.png"):
            if cand.exists():
                return cand
    stand = pics[pid].get("stand_in")
    if stand:
        report.append(f"{pid}: not painted yet, stand-in {stand}")
        return find_picture(stand, dirs, pics, report)
    raise SystemExit(f"picture {pid} missing and has no stand-in")


def to_frame(pt, box, W, H):
    x0, y0, x1, y1 = box
    return ((pt[0] * W - x0) / (x1 - x0) * OW, (pt[1] * H - y0) / (y1 - y0) * OH)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("words")
    p.add_argument("narration")
    p.add_argument("out")
    p.add_argument("--pics", action="append", required=True)
    p.add_argument("--snd", required=True)
    p.add_argument("--audio-only", action="store_true")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    board = json.loads((HERE / "board.json").read_text())
    words_doc = json.loads(Path(a.words).read_text())
    timed, findings = BOARD.build(board, words_doc)
    words = words_doc["words"]
    (out / "timed.json").write_text(json.dumps(timed, indent=1))
    report = [f"{f['severity']} {f['rule']} {f['shot']} {f['detail']}" for f in findings]
    nar, _ = V5.read_wav(Path(a.narration))
    stats: dict = {}
    audio = build_audio(timed, words, nar, Path(a.snd), stats)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    raw = out / "audio_raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(SR),
                    "-ac", "1", str(out / "audio.wav")], check=True)
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out / "audio.wav"), "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    stats["lufs"] = float(meas.split("I:")[-1].split("LUFS")[0])
    dirs = [Path(d) for d in a.pics]
    if a.audio_only:
        (out / "report.json").write_text(json.dumps({"findings": report, "audio": stats}, indent=1))
        return 0
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                           "-i", "-", "-i", str(out / "audio.wav"), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / "video.mp4")],
                          stdin=subprocess.PIPE)
    shots, total = timed["shots"], int(round(timed["duration"] * FPS))
    for k, s in enumerate(shots):
        f0 = int(round(s["start"] * FPS))
        f1 = total if k == len(shots) - 1 else int(round(shots[k + 1]["start"] * FPS))
        path = find_picture(s["picture"], dirs, board["pictures"], report)
        im = Image.open(path).convert("RGB")
        arr = grade(np.asarray(im, dtype=np.float64) / 255.0, GRADE, seed=k)
        im = Image.fromarray((arr * 255).astype(np.uint8))
        W, H = im.size
        speakers = board["pictures"][s["picture"]].get("speakers", {})
        bubbles, boxes = [], []
        for b in s["bubbles"]:
            u = (b["start"] * FPS - f0) / max(1, f1 - f0 - 1)
            box = V5.motion_box(s["motion"], W, H, min(max(u, 0.0), 1.0))
            sp = to_frame(speakers[b["who"]], box, W, H)
            bub = BUB.Bubble(b["text"], sp, b["start"], b["end"], (OW, OH), kind=b.get("kind", "speech"),
                             avoid=[x.box for x in bubbles if x.end > b["start"]])
            bubbles.append(bub)
        for f in range(f0, f1):
            u = (f - f0) / max(1, f1 - f0 - 1)
            frame = im.resize((OW, OH), Image.BICUBIC, box=V5.motion_box(s["motion"], W, H, u))
            if bubbles:
                frame = BUB.composite(frame, bubbles, f / FPS)
            ff.stdin.write(frame.tobytes())
        print(s["id"], s["picture"], f1 - f0, flush=True)
    ff.stdin.close()
    ff.wait()
    (out / "report.json").write_text(json.dumps({"findings": report, "audio": stats}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
