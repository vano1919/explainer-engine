"""Assemble a video from a timed production script (D-43): nothing is decided here, everything comes from the timed
file (``production/timing.py``): which picture, from which frame to which frame, its camera move, its bubbles; which
ambience, sound and music, from when to when, how loud.

Audio: the narration (peak-normalised), ambience beds crossfaded at their times, sounds on their times, music; the
beds and music duck under the voice (as in v5) and dip under every sound with millisecond ramps (``audio/duck.py``,
UR-32); loudness normalised to -14 LUFS. Picture: each shot's frames from its picture, graded once (``finish/grade``),
cropped with sub-pixel boxes for the move, bubbles composited (``finish/bubbles``). A picture that is not painted yet:
``final`` stops; a draft shows its stand-in, else a placeholder card with the picture id and its subject.
CPU only (numpy, PIL, ffmpeg). Helpers come from ``examples/stone_age/day1_v5/assemble.py`` (same author, moved here).
"""

from __future__ import annotations

import json
import os
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from explainer_engine.audio.level import level_voice
from explainer_engine.audio import duck
from explainer_engine.finish import bubbles as BUB
from explainer_engine.finish.grade import grade
from explainer_engine.world import resolver

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "assets" / "audio" / "library"
SR = 48000


# --- audio helpers ---------------------------------------------------------------------------------------------------

def read_wav(p: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(p)) as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype={1: np.uint8, 2: np.int16, 4: np.int32}[sw]).astype(np.float64)
    a = a / float({1: 128.0, 2: 32768.0, 4: 2147483648.0}[sw])
    return a.reshape(-1, ch).mean(axis=1), sr


def load_audio(path: Path, sr: int = SR) -> np.ndarray:
    """Any file -> mono float at ``sr`` via ffmpeg."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def db(x: float) -> float:
    return 10 ** (x / 20.0)


def loop_to(a: np.ndarray, n: int, fade: int = 24000) -> np.ndarray:
    out = np.zeros(n)
    if len(a) == 0:
        return out
    pos = 0
    while pos < n:
        seg = a.copy()
        f = min(fade, len(seg) // 2)
        if f:
            seg[:f] *= np.linspace(0, 1, f)
            seg[-f:] *= np.linspace(1, 0, f)
        end = min(n, pos + len(seg))
        out[pos:end] += seg[: end - pos]
        pos += max(1, len(seg) - f)
    return out


def moving_mean(x: np.ndarray, k: int) -> np.ndarray:
    """Centred moving average, O(n) (np.convolve with a 12,000-tap box took minutes on a 3-minute mix)."""
    k = max(1, int(k))
    c = np.concatenate([[0.0], np.cumsum(x)])
    lo = np.clip(np.arange(len(x)) - k // 2, 0, len(x))
    hi = np.clip(lo + k, 0, len(x))
    return (c[hi] - c[lo]) / k


def envelope(voice: np.ndarray, win: float = 0.08) -> np.ndarray:
    rms = np.sqrt(np.maximum(moving_mean(voice ** 2, SR * win), 0.0))
    return np.clip(rms / (rms.max() * 0.25 + 1e-9), 0, 1)


def rms_db(a: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12)) if len(a) else -120.0


def fade(seg: np.ndarray, n: int) -> np.ndarray:
    n = min(n, len(seg) // 2)
    if n > 0:
        seg[:n] *= np.linspace(0, 1, n)
        seg[-n:] *= np.linspace(1, 0, n)
    return seg


class Sounds:
    """Resolves a sound name: ``<dir>/<name>.mp3|.wav`` in the sound dirs, else the library manifest id."""

    def __init__(self, dirs: list[Path]):
        self.dirs = [Path(d) for d in dirs]
        man = LIB / "manifest.json"
        self.lib = {x["id"]: LIB / x["file"] for x in json.loads(man.read_text())["items"]} if man.exists() else {}
        music = LIB / "music"
        if music.exists():
            for f in music.glob("*.wav"):
                self.lib.setdefault(f.stem, f)

    def path(self, name: str) -> Path | None:
        for d in self.dirs:
            for ext in (".mp3", ".wav"):
                if (d / f"{name}{ext}").exists():
                    return d / f"{name}{ext}"
        return self.lib.get(name)

    def exists(self, name: str) -> bool:
        return self.path(name) is not None

    def load(self, name: str) -> np.ndarray:
        p = self.path(name)
        if p is None:
            raise FileNotFoundError(name)
        return load_audio(p)


def build_audio(timed: dict, narration: np.ndarray, sounds: Sounds, stats: dict) -> np.ndarray:
    n = len(narration)
    t = lambda s: int(round(s * SR))  # noqa: E731
    narration = level_voice(narration, SR)  # D-43: even out the read's loudness swings (audio/level.py)
    voice = narration / (np.abs(narration).max() + 1e-9) * 0.9
    env = envelope(voice)
    vduck = 1.0 - 0.55 * moving_mean(env, t(0.25))
    au = timed["audio"]
    bed = np.zeros(n)
    for b in au["beds"]:
        a, z = t(b["start"]), min(n, t(b["end"]))
        if z <= a:
            continue
        seg = loop_to(sounds.load(b["sound"]), z - a)
        seg = seg / (np.abs(seg).max() + 1e-9) * db(b.get("gain_db", -13))
        bed[a:z] += fade(seg, t(b.get("fade_s", 1.5)))
    music = np.zeros(n)
    for m in au["music"]:
        a, z = t(m["start"]), min(n, t(m["end"]))
        if z <= a:
            continue
        seg = loop_to(sounds.load(m["track"]), z - a)
        seg = seg / (np.abs(seg).max() + 1e-9) * db(m.get("gain_db", -18))
        music[a:z] += fade(seg, t(m.get("fade_s", 2.0)))
    fx = np.zeros(n)
    stats["sfx"] = []
    for e in au["sfx"]:
        a, z = t(e["start"]), min(n, t(e["end"]))
        w = sounds.load(e["sound"])[: max(0, z - a)].copy()
        if not len(w):
            continue
        w = w / (np.abs(w).max() + 1e-9) * db(e.get("gain_db", -18))
        w[: min(240, len(w))] *= np.linspace(0, 1, min(240, len(w)))  # 5 ms in, 10 ms out: no click
        w[-min(480, len(w)):] *= np.linspace(1, 0, min(480, len(w)))
        fx[a:a + len(w)] += w
        stats["sfx"].append({"sound": e["sound"], "start": e["start"], "seconds": round(len(w) / SR, 3)})
    if timed.get("bubble_pop"):
        pop = sounds.load(timed["bubble_pop"]["sound"])[: t(0.25)]
        pop = pop / (np.abs(pop).max() + 1e-9) * db(timed["bubble_pop"].get("gain_db", -26))
        for s in timed["shots"]:
            for b in s["bubbles"]:
                a = t(b["start"])
                fx[a:a + len(pop)] += pop[: max(0, n - a)]
    fduck = duck.duck_gain(fx, SR, n, depth_db=9.0, threshold=0.01, attack_ms=20, release_ms=280, hold_ms=80)
    bduck = duck.duck_gain(fx, SR, n, depth_db=4.0, threshold=0.01, attack_ms=25, release_ms=350, hold_ms=80)
    stats["music_dip_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(fduck, SR), 3)
    mix = voice * db(-3) + (bed * bduck + music * fduck) * vduck + fx
    speaking = env > 0.15
    stats.update(voice_rms_db=round(rms_db((voice * db(-3))[speaking]), 2),
                 bed_rms_db=round(rms_db((bed * vduck)[speaking]), 2), music_rms_db=round(rms_db((music * vduck)[speaking]), 2))
    ramp_in, ramp_out = t(0.5), t(FADE_OUT)  # the sound opens and closes with the picture
    mix[:ramp_in] *= np.linspace(0, 1, ramp_in)
    mix[-ramp_out:] *= np.linspace(1, 0, min(ramp_out, len(mix)))
    peak = np.abs(mix).max()
    return mix / peak * 0.89 if peak > 0.89 else mix


# --- picture helpers -------------------------------------------------------------------------------------------------

FADE_IN, FADE_OUT = 1.0, 1.5  # ED-04: the episode opens from black and closes to black
LOOK = "vignette=PI/5,noise=alls=5:allf=t"  # ED-04: one constant film look over the whole episode (free, made by ffmpeg)


def look_filter(duration: float) -> str:
    return f"{LOOK},fade=t=in:st=0:d={FADE_IN},fade=t=out:st={max(0.0, duration - FADE_OUT):.3f}:d={FADE_OUT}"


def motion_box(m: dict, W: int, H: int, u: float) -> tuple[float, float, float, float]:
    z = m["z0"] + (m["z1"] - m["z0"]) * u
    cw, ch = W / z, H / z
    if "x0" in m:  # a chained move (production/continuity.py): the centre offset runs from x0 to x1, shares of the width
        dx = (m["x0"] + (m["x1"] - m["x0"]) * u) * W
    else:
        dx = m.get("dx", 0.0) * W * (u - 0.5)
    cx = min(max(W / 2 + dx, cw / 2), W - cw / 2)  # the crop never leaves the picture
    return (cx - cw / 2, H / 2 - ch / 2, cx + cw / 2, H / 2 + ch / 2)


def placeholder(pid: str, text: str, size: tuple[int, int]) -> Image.Image:
    W, H = size
    im = Image.new("RGB", (W, H), (38, 34, 40))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(str(BUB.FONT), max(12, H // 18))
    f2 = ImageFont.truetype(str(BUB.FONT), max(10, H // 34))
    d.rectangle([W * 0.04, H * 0.06, W * 0.96, H * 0.94], outline=(200, 190, 170), width=max(2, H // 200))
    d.text((W * 0.07, H * 0.12), f"PICTURE PENDING: {pid}", font=f1, fill=(240, 230, 210))
    y = H * 0.30
    for line in BUB.textwrap.wrap(text, 70)[:8]:
        d.text((W * 0.07, y), line, font=f2, fill=(200, 190, 170))
        y += H / 20
    return im


def picture_image(pid: str, pics: dict, dirs: list[Path], final: bool, report: list) -> Image.Image | None:
    p = pics.get(pid, {})
    for cand in [p.get("file"), f"{pid}.png", f"{pid}_v1.png"]:
        if not cand:
            continue
        for d in dirs:
            if (Path(d) / cand).exists():
                return Image.open(Path(d) / cand).convert("RGB")
    if final:
        raise SystemExit(f"final render: picture {pid} is missing (PV-25)")
    if p.get("stand_in"):
        report.append(f"{pid}: stand-in {p['stand_in']}")
        return picture_image(p["stand_in"], pics, dirs, final, report)
    report.append(f"{pid}: placeholder card")
    return None


def to_frame(pt, box, W, H, OW, OH):
    x0, y0, x1, y1 = box
    return ((pt[0] * W - x0) / (x1 - x0) * OW, (pt[1] * H - y0) / (y1 - y0) * OH)


def assemble(timed: dict, narration_wav: Path, out: Path, picture_dirs: list[Path], sound_dirs: list[Path], *,
             size: tuple[int, int] = (1920, 1080), final: bool = False, grade_key: str | None = None,
             audio_only: bool = False, crf: int = 18) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    fails = [x for x in timed.get("findings", []) if x.get("severity") == "FAIL"]
    if fails:  # 2026-10-16: a shell chain started a render on a timing with 3 FAIL
        raise SystemExit(f"refused: the timing has {len(fails)} FAIL ({fails[0]['rule']}: {fails[0]['detail']}); fix and re-time")
    lock = out / ".assemble.lock"
    if lock.exists():
        try:
            os.kill(int(lock.read_text()), 0)
            raise SystemExit(f"refused: another assemble (pid {lock.read_text()}) writes {out}")
        except (ProcessLookupError, ValueError):
            pass  # a stale lock from a run that died
    lock.write_text(str(os.getpid()))
    try:
        return _assemble(timed, narration_wav, out, picture_dirs, sound_dirs, size=size, final=final, grade_key=grade_key,
                         audio_only=audio_only, crf=crf)
    finally:
        lock.unlink(missing_ok=True)


def _assemble(timed: dict, narration_wav: Path, out: Path, picture_dirs: list[Path], sound_dirs: list[Path], *,
              size: tuple[int, int], final: bool, grade_key: str | None, audio_only: bool, crf: int) -> dict:
    OW, OH = size
    fps = timed["fps"]
    sounds = Sounds(sound_dirs)
    nar, sr = read_wav(narration_wav)
    if sr != SR:
        nar = load_audio(narration_wav)
    need = int(round(timed["frames"] / fps * SR))  # the audio is exactly as long as the frames (no -shortest trimming)
    nar = np.pad(nar, (0, max(0, need - len(nar))))[:need]
    stats: dict = {}
    audio = build_audio(timed, nar, sounds, stats)
    raw = out / "audio_raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(SR),
                    "-ac", "1", str(out / "audio.wav")], check=True)
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out / "audio.wav"), "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    stats["lufs"] = float(meas.split("I:")[-1].split("LUFS")[0])
    report: list[str] = []
    result = {"audio": stats, "pictures": report, "video": None}
    if audio_only:
        (out / "assemble_report.json").write_text(json.dumps(result, indent=1))
        return result
    codex = resolver.load_codex()
    params = codex["grades"].get(grade_key or "prehistory")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(fps),
                           "-i", "-", "-i", str(out / "audio.wav"), "-vf", look_filter(timed["duration"]), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-frames:v", str(timed["frames"]),
                           str(out / "video.part.mp4")], stdin=subprocess.PIPE)
    pics, cache = timed["pictures"], {}
    written = 0
    last = None
    for k, s in enumerate(timed["shots"]):
        f0, f1 = s["start_frame"], s["end_frame"]
        pid = s["picture"]
        if pid not in cache:
            im = picture_image(pid, pics, picture_dirs, final, report)
            if im is None:
                im = placeholder(pid, pics.get(pid, {}).get("subject") or pics.get(pid, {}).get("edit", ""), (OW, OH))
            elif params:
                im = Image.fromarray((grade(np.asarray(im, dtype=np.float64) / 255.0, params, seed=k) * 255).astype(np.uint8))
            cache = {pid: im}  # one picture in memory at a time (8 GB machines)
        im = cache[pid]
        W, H = im.size
        speakers = pics.get(pid, {}).get("speakers", {})
        bubbles = []
        for b in s["bubbles"]:
            u = (b["start_frame"] - f0) / max(1, f1 - f0 - 1)
            box = motion_box(s.get("render_motion", s["motion"]), W, H, min(max(u, 0.0), 1.0))
            sp = to_frame(speakers.get(b["who"], [0.5, 0.4]), box, W, H, OW, OH)
            bubbles.append(BUB.Bubble(b["text"], sp, b["start"], b["end"], (OW, OH), kind=b.get("kind", "speech"),
                                      avoid=[x.box for x in bubbles if x.end > b["start"]]))
        dissolve = round(float(s.get("transition_seconds", 1.0)) * fps) if s.get("transition") == "dissolve" and last is not None else 0
        for f in range(f0, f1):
            u = (f - f0) / max(1, f1 - f0 - 1)
            frame = im.resize((OW, OH), Image.BICUBIC, box=motion_box(s.get("render_motion", s["motion"]), W, H, u))
            if bubbles:
                frame = BUB.composite(frame, bubbles, f / fps)
            if f - f0 < dissolve:  # UR-14: the picture before melts into this one
                frame = Image.blend(last, frame, (f - f0 + 1) / (dissolve + 1))
            last = frame
            ff.stdin.write(frame.tobytes())
            written += 1
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed; video.part.mp4 kept for a look")
    os.replace(out / "video.part.mp4", out / "video.mp4")  # a video.mp4 on disk is always a finished one
    result["video"] = str(out / "video.mp4")
    result["frames_written"] = written
    result["frames_planned"] = timed["frames"]
    (out / "assemble_report.json").write_text(json.dumps(result, indent=1))
    return result
