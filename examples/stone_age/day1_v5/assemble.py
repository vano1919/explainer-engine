"""Assemble the Day 1 v5 animatic/test video: graded pictures with the planned motion on hard cuts, narration, ambience beds,
cut sounds and a quiet music bed, ducked under the voice. CPU only (PIL, numpy, ffmpeg); frames are cropped with sub-pixel
boxes so push/pan moves are smooth. Run: python assemble.py <pictures dir> <sound dir> <narration.wav> <out dir>"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.finish.grade import grade  # noqa: E402
from explainer_engine.world import resolver  # noqa: E402

HERE = Path(__file__).parent
FPS, OW, OH, SR = 30, 1920, 1080, 48000
LIB = ROOT / "assets" / "audio" / "library"
CODEX = resolver.load_codex()
WORLD = resolver.resolve(json.loads((HERE / "world_spec.json").read_text()))
GRADE = CODEX["grades"][WORLD["grade"]]
SOFT_CUT = {"swish__v1", "swish__v2", "pop_in__v1", "seam_shimmer__v1", "jump_whoosh__v1"}  # -> the soft whoosh
FOLEY = {"footstep_grass__v1", "cloth_rustle__v1", "cloth_rustle__v2", "cloth_rustle__v3", "page_flip__v1", "page_flip__v2",
         "glow_ping__v1", "pencil_scribble__v2"}
BED = {"hook": "wind_storm", "rules": "wind_day", "meadow": "wind_day", "water": "wind_day", "dusk": "wind_storm",
       "fire": "wind_storm", "night": "fire", "end": "fire"}


def read_wav(p):
    with wave.open(str(p)) as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype={1: np.uint8, 2: np.int16, 4: np.int32}[sw]).astype(np.float64)
    a = a / float({1: 128.0, 2: 32768.0, 4: 2147483648.0}[sw])
    a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def load_audio(path: Path) -> np.ndarray:
    """Any file -> mono float at SR via ffmpeg."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def db(x):
    return 10 ** (x / 20.0)


def loop_to(a: np.ndarray, n: int, fade: int = 24000) -> np.ndarray:
    out = np.zeros(n)
    pos = 0
    while pos < n:
        seg = a.copy()
        f = min(fade, len(seg) // 2)
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        end = min(n, pos + len(seg))
        out[pos:end] += seg[: end - pos]
        pos += len(seg) - f
    return out


def envelope(voice: np.ndarray, win: float = 0.08) -> np.ndarray:
    k = int(SR * win)
    sq = np.convolve(voice ** 2, np.ones(k) / k, mode="same")
    rms = np.sqrt(sq)
    return np.clip(rms / (rms.max() * 0.25 + 1e-9), 0, 1)


def build_audio(shots, narration: np.ndarray, snd: Path) -> np.ndarray:
    n = len(narration)
    t = lambda s: int(s * SR)  # noqa: E731
    voice = narration / (np.abs(narration).max() + 1e-9) * 0.9
    duck = 1.0 - 0.55 * np.convolve(envelope(voice), np.ones(int(SR * 0.25)) / int(SR * 0.25), mode="same")
    beds = {k: load_audio(snd / f"{k}.mp3") for k in ("wind_storm", "wind_day", "fire")}
    bed = np.zeros(n)
    for s in shots:
        a, b = t(s["start"]), min(n, t(s["end"]))
        name = BED[s["beat"]]
        seg = loop_to(beds[name], n)[a:b]
        f = min(len(seg) // 3, t(1.2))
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        bed[a:b] += seg
    bed = bed / (np.abs(bed).max() + 1e-9) * db(-27)
    music = np.zeros(n)
    plan = [("clockwork_loop__v1", 0.0, 100.0), ("sneaky_pizzicato__v1", 39.0, 120.0), ("clockwork_loop__v1", 120.0, 185.0)]
    for name, a, b in plan:
        m, _ = read_wav(LIB / "music" / f"{name}.wav")
        seg = loop_to(m, t(min(b, n / SR) - a))
        f = t(2.0)
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        music[t(a):t(a) + len(seg)] += seg[: n - t(a)]
    music = music / (np.abs(music).max() + 1e-9) * db(-31)
    fx = np.zeros(n)
    whoosh = load_audio(snd / "whoosh.mp3")[: t(0.9)]
    whoosh = whoosh / (np.abs(whoosh).max() + 1e-9) * db(-20)
    for i, s in enumerate(shots):
        sid = s.get("sound")
        at = t(s["start"]) - t(0.05)
        if not sid or at < 0:
            continue
        if sid in SOFT_CUT and s["type"] in ("A", "B") and i % 2 == 0:
            w = whoosh
        elif sid in FOLEY:
            w, _ = read_wav(LIB / next(x["file"] for x in json.load(open(LIB / "manifest.json"))["items"] if x["id"] == sid))
            w = w[: t(0.8)] / (np.abs(w).max() + 1e-9) * db(-24)
        else:
            continue
        fx[at:at + len(w)] += w[: n - at]
    mix = voice * db(-3) + (bed + music) * duck + fx
    peak = np.abs(mix).max()
    return mix / peak * 0.89 if peak > 0.89 else mix


def motion_box(m, W, H, u):
    kind, z0, z1 = m["kind"], m["z0"], m["z1"]
    z = z0 + (z1 - z0) * u
    cw, ch = W / z, H / z
    dx = m.get("dx", 0.0) * W * (u - 0.5)
    cx = W / 2 + dx
    return (cx - cw / 2, H / 2 - ch / 2, cx + cw / 2, H / 2 + ch / 2)


def main(pics: Path, snd: Path, narr: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads((HERE / "shots.json").read_text())
    shots, dur = doc["shots"], doc["duration"]
    nar, _ = read_wav(narr)
    audio = build_audio(shots, nar, snd)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out / "audio.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                           "-i", "-", "-i", str(out / "audio.wav"), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / "video.mp4")],
                          stdin=subprocess.PIPE)
    total = int(round(dur * FPS))
    for k, s in enumerate(shots):
        f0 = int(round(s["start"] * FPS))
        f1 = total if k == len(shots) - 1 else int(round(shots[k + 1]["start"] * FPS))
        im = Image.open(pics / f"{s['picture']}.png").convert("RGB")
        arr = grade(np.asarray(im, dtype=np.float64) / 255.0, GRADE, seed=k)
        im = Image.fromarray((arr * 255).astype(np.uint8))
        W, H = im.size
        for f in range(f0, f1):
            u = (f - f0) / max(1, f1 - f0 - 1)
            frame = im.resize((OW, OH), Image.BICUBIC, box=motion_box(s["motion"], W, H, u))
            ff.stdin.write(frame.tobytes())
        print(s["id"], f1 - f0, flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main(*[Path(a) for a in sys.argv[1:5]])
