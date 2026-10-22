"""Assemble a video from a timed production script (D-43): nothing is decided here, everything comes from the timed
file (``production/timing.py``): which picture, from which frame to which frame, its camera move, its bubbles; which
ambience, sound and music, from when to when, how loud.

Audio: the narration (peak-normalised), ambience beds crossfaded at their times, sounds on their times, music with
BP-62's fades; the beds and music duck under the voice and dip under every sound with millisecond ramps (``audio/duck.py``,
one set of numbers for every duck, BP-53); loudness normalised to the house target (qa/targets.py, BP-50). Picture: each shot's frames from its picture, graded once (``finish/grade``),
cropped with sub-pixel boxes for the move, bubbles composited (``finish/bubbles``). A picture that is not painted yet:
``final`` stops; a draft shows its stand-in, else a placeholder card with the picture id and its subject.
CPU only (numpy, PIL, ffmpeg). Helpers come from ``examples/stone_age/day1_v5/assemble.py`` (same author, moved here).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from explainer_engine.audio.level import level_voice
from explainer_engine.audio import cues as CUES, duck
from explainer_engine.production import accents as ACC
from explainer_engine.production import beats as BEATS
from explainer_engine.production import faces as FACES
from explainer_engine.production import continuity
from explainer_engine.production import parallax as PAR
from explainer_engine.production import graphics as GFX
from explainer_engine.finish import bubbles as BUB
from explainer_engine.finish.grade import grade
from explainer_engine.world import resolver
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as RULES  # SR is the sample rate here

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


def fade(seg: np.ndarray, n: int, n_out: int | None = None) -> np.ndarray:
    """Linear fade in over ``n`` samples and out over ``n_out`` (default ``n``), each at most half the segment."""
    n_in, n_out = min(n, len(seg) // 2), min(n if n_out is None else n_out, len(seg) // 2)
    if n_in > 0:
        seg[:n_in] *= np.linspace(0, 1, n_in)
    if n_out > 0:
        seg[-n_out:] *= np.linspace(1, 0, n_out)
    return seg


def music_fades(m: dict) -> tuple[float, float]:
    """(fade in s, fade out s) of a timed music entry: its own, an older timed file's one ``fade_s``, else BP-62's."""
    one = m.get("fade_s")
    return (float(m.get("fade_in_s", one if one is not None else RULES.T("BP-62", "fade_in_s"))),
            float(m.get("fade_out_s", one if one is not None else RULES.T("BP-62", "fade_out_s"))))


class Sounds:
    """Resolves a sound name: ``<dir>/<name>.mp3|.wav`` in the sound dirs, else the library manifest id."""

    def __init__(self, dirs: list[Path]):
        self.dirs = [Path(d) for d in dirs]
        man = LIB / "manifest.json"
        items = json.loads(man.read_text())["items"] if man.exists() else []
        self.lib = {x["id"]: LIB / x["file"] for x in items}
        self.meta = {x["id"]: x for x in items}
        music = LIB / "music"
        if music.exists():
            for f in music.glob("*.wav"):
                self.lib.setdefault(f.stem, f)

    def path(self, name: str) -> Path | None:
        for d in self.dirs:
            for ext in (".mp3", ".wav"):
                if (d / f"{name}{ext}").exists():
                    return d / f"{name}{ext}"
        p = self.lib.get(name)
        # the library WAVs are not in git (media rule): a manifest entry without its file is missing, so PV-05 says so
        # before the render instead of ffmpeg failing inside it (audit 2026-10-19 M4)
        return p if p is not None and p.is_file() else None

    def exists(self, name: str) -> bool:
        return self.path(name) is not None

    def load(self, name: str) -> np.ndarray:
        p = self.path(name)
        if p is None:
            raise FileNotFoundError(name)
        return load_audio(p)

    def loopable(self, name: str) -> bool:
        """The manifest's ``loop`` field: only a sound made to loop may be tiled over a bed or music slot; a one-shot
        plays once. A sound without the field (older manifests, files in the sound dirs) keeps looping as before."""
        return bool(self.meta.get(name, {}).get("loop", True))


def play_once(a: np.ndarray, n: int) -> np.ndarray:
    """A one-shot on a bed or music slot (manifest ``loop: false``): played once, faded, padded with silence — never
    tiled by ``loop_to``, which turned a single hit into "one press plays many times" (the creator, 2026-10-19)."""
    out = np.zeros(n)
    seg = a[:n].copy()
    out[: len(seg)] = fade(seg, min(2400, len(seg) // 2))
    return out


def cue_bus(cues: list[dict], n: int) -> np.ndarray:
    """VB-08: the timed beat cues (BP-64's length and level) on one track of ``n`` samples at SR (the Shorts use it too).
    Each repeat of a sound rotates to the next pitch variant (BP-57, VB-10), so a reused cue never plays the identical waveform."""
    t = lambda s: int(round(s * SR))  # noqa: E731
    bus = np.zeros(n)
    seen: dict = {}
    for c in cues:
        a = t(c["start"])
        v = seen.get(c["sound"], 0)
        seen[c["sound"]] = v + 1
        w = CUES.render(c["sound"], v)[: t((c.get("max_ms") or 1e9) / 1000) or None] * db(c.get("gain_db", CUES.DEFAULT_GAIN_DB))
        w = w[: max(0, n - a)].copy()
        bus[a:a + len(w)] += w
    return bus


def build_audio(timed: dict, narration: np.ndarray, sounds: Sounds, stats: dict) -> np.ndarray:
    n = len(narration)
    t = lambda s: int(round(s * SR))  # noqa: E731
    narration = level_voice(narration, SR)  # D-43: even out the read's loudness swings (audio/level.py)
    voice = narration / (np.abs(narration).max() + 1e-9) * 0.9
    env = envelope(voice)
    vduck = duck.duck_gain(voice, SR, n)  # BP-53: music and bed dip under the voice with the registry's depth and times
    au = timed["audio"]
    bed = np.zeros(n)
    can_loop = getattr(sounds, "loopable", lambda name: True)  # tests stub Sounds; an unknown sound keeps looping
    for b in au["beds"]:
        a, z = t(b["start"]), min(n, t(b["end"]))
        if z <= a:
            continue
        src = sounds.load(b["sound"])
        seg = loop_to(src, z - a) if can_loop(b["sound"]) else play_once(src, z - a)
        seg = seg / (np.abs(seg).max() + 1e-9) * db(b.get("gain_db", -13))
        bed[a:z] += fade(seg, t(b.get("fade_s", 1.5)))
    music = np.zeros(n)
    for m in au["music"]:
        a, z = t(m["start"]), min(n, t(m["end"]))
        if z <= a:
            continue
        src = sounds.load(m["track"])
        seg = loop_to(src, z - a) if can_loop(m["track"]) else play_once(src, z - a)
        seg = seg / (np.abs(seg).max() + 1e-9) * db(m.get("gain_db", -18))
        f_in, f_out = music_fades(m)  # BP-62: 1 s in, 2 s out
        music[a:z] += fade(seg, t(f_in), t(f_out))
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
    bus = cue_bus(au.get("cues", []), n)  # VB-08: beat cues ride over everything without ducking it
    stats["cues"] = len(au.get("cues", []))
    # BP-53 for every duck: the registry's house depth and times (duck.py defaults); the bed under a world sound dips by the
    # range's floor (it already sits BP-65 under the voice and carries the place)
    fduck = duck.duck_gain(fx, SR, n, threshold=0.01)
    bduck = duck.duck_gain(fx, SR, n, depth_db=float(RULES.T("BP-53", "depth_db")[0]), threshold=0.01)
    stats["music_dip_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(fduck, SR), 3)
    stats["voice_duck_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(vduck, SR), 3)
    mix = voice * db(-3) + (bed * bduck + music * fduck) * vduck + fx + bus
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
LOOK = "vignette=PI/5,noise=alls=2:allf=t"  # ED-04: one constant film look over the whole episode (free, made by ffmpeg)


def look_filter(duration: float) -> str:
    return chunk_look(True, True, duration)


def overlays(frame: Image.Image, f: int, fps: int, timed: dict) -> Image.Image:
    """ED-09 period cards and ED-10 data visuals on one finished frame."""
    for c in timed.get("cards", []):
        t = (f - c["start_frame"]) / fps
        if 0 <= t <= GFX.card_length():
            frame = GFX.card(frame, c, t, c["of"], c["index"])
    for g in timed.get("visuals", []):
        if g["start_frame"] <= f < g["end_frame"]:
            frame = GFX.visual(frame, g, (f - g["start_frame"]) / fps, g["hold"])
    return frame


def motion_box(m: dict, W: int, H: int, u: float) -> tuple[float, float, float, float]:
    if "ein" in m:  # ED-08: rest at a cut to another picture
        u = continuity.warp(u, m["ein"], m["eout"])
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


def find_picture(pid: str, pics: dict, dirs: list[Path]) -> Path | None:
    p = pics.get(pid, {})
    for cand in [p.get("file"), f"{pid}.png", f"{pid}_v1.png"]:
        if not cand:
            continue
        for d in dirs:
            if (Path(d) / cand).exists():
                return Path(d) / cand
    return None


def picture_image(pid: str, pics: dict, dirs: list[Path], final: bool, report: list) -> Image.Image | None:
    p = pics.get(pid, {})
    found = find_picture(pid, pics, dirs)
    if found:
        return Image.open(found).convert("RGB")
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


def hero_faces_of(timed: dict) -> dict:
    """The cast's expression cut-outs and face sheets as the beat and face renderers take them."""
    hero_faces = {who: {"expressions": e} for who, e in timed.get("expressions", {}).items()}
    for who, sheet in timed.get("face_sheets", {}).items():
        hero_faces.setdefault(who, {})["face_sheet"] = sheet
    return hero_faces


def beats_for_shot(all_beats: list[dict], s: dict, pics: dict, hero_faces: dict, picture_dirs: list[Path]) -> list[dict]:
    """VB rules: the beats on screen during shot ``s`` (a picture-bound one only in its own shot); expressions get the
    face point of the shot's picture and, when the hero's sheet is painted, the close-up (VB-09)."""
    on = [b for b in all_beats if b["start_frame"] < s["end_frame"] and max(b["end_frame"], b["start_frame"] + 1) > s["start_frame"]
          and (b["kind"] not in BEATS.PICTURE_BOUND or b["shot"] == s["id"])]
    face = {id(b): b for b in BEATS.faces(on, pics)}
    on = [dict(b, face=face[id(b)]["face"]) if id(b) in face else b for b in on]
    keyed = {(b["start_frame"], b["who"]): b["close_up"] for b in FACES.sheet_beats(on, hero_faces, picture_dirs)}
    return [dict(b, close_up=keyed[(b["start_frame"], b["who"])]) if b["kind"] == "expression"
            and (b["start_frame"], b.get("who")) in keyed else b for b in on]


def finish_frame(im: Image.Image, box, s: dict, f: int, fps: int, size: tuple[int, int], sb: list[dict], hero_faces: dict,
                 face_order: list[str], picture_dirs: list[Path], bubbles: list | None = None,
                 before: Image.Image | None = None, depth=None) -> Image.Image:
    """One frame of shot ``s`` from its picture and the crop ``box`` of the shot's own move: the 2.5D parallax (stage F,
    ``motion.parallax`` + a depth map), the face focus (VB-02), the accents (MO), the close-ups (VB-09), the bubbles and the
    visual beats. The long video and the Shorts both draw here."""
    f0, f1 = s["start_frame"], s["end_frame"]
    W, H = im.size
    if sb:  # VB-02: the speaking face is the focus; each expression change pops toward it
        box = BEATS.face_camera(box, W, H, [b for b in sb if b.get("face") is not None and b["shot"] == s["id"]], f, fps)
    acc = s.get("accents", [])
    if acc:  # MO rules (D-48): punch, shake, wobble move the crop; whips, flashes and words are drawn
        box = ACC.apply_camera(box, W, H, *ACC.camera(acc, f, fps, f0))
    frame = im.resize(size, Image.BICUBIC, box=box)
    if depth is not None and PAR.amount(s["motion"]) > 0:
        u = (f - f0) / max(1, f1 - f0 - 1)
        frame = PAR.shift(frame, depth, box, (W, H), u, PAR.amount(s["motion"]), PAR.direction(s["motion"]))
    if acc:
        frame = ACC.draw(frame, acc, f, fps, f0, f1, before, BUB.FONT)
    if sb:  # VB-09: in dialogue the speaking hero's keyed close-up over the scene, zoomed and blurred
        frame = FACES.composite(frame, [b for b in sb if b.get("close_up") and b["shot"] == s["id"]], f, fps, face_order)
    if bubbles:
        frame = BUB.composite(frame, bubbles, f / fps)
    if sb:
        frame = BEATS.draw(frame, sb, f, fps, box, (W, H), hero_faces, picture_dirs)
    return frame


CHUNK_SECONDS = 60.0  # a render is written in chunks that survive a restart of the machine; a restart costs at most one chunk


def clean_cut(shots: list, k: int, fps: int) -> bool:
    """A chunk may start at shot k only when the frame before it is a plain frame of shot k-1: not inside that shot's own dissolve
    (a dissolve blends the frame before with the new one, so frames inside it depend on frames that came earlier)."""
    prev = shots[k - 1]
    if prev.get("transition") != "dissolve" or k - 1 == 0:
        return True
    return prev["end_frame"] - prev["start_frame"] > round(float(prev.get("transition_seconds", 1.0)) * fps)


def chunk_bounds(shots: list, fps: int, total: int, seconds: float = CHUNK_SECONDS) -> list[list[int]]:
    """[[first shot, end shot)] per chunk. Edges are shot starts (a cut is a clean place to join), chunks are at least ``seconds``
    long, and the last one keeps room for the closing fade."""
    want = max(1, round(seconds * fps)) if seconds > 0 else total
    min_tail = round((FADE_OUT + 1.5) * fps)
    starts = [0]
    for k in range(1, len(shots)):
        edge = shots[k]["start_frame"]
        if edge - shots[starts[-1]]["start_frame"] < want:
            continue
        if total - edge < min_tail:
            break
        if clean_cut(shots, k, fps):
            starts.append(k)
    return [[a, b] for a, b in zip(starts, starts[1:] + [len(shots)])]


def chunk_look(first: bool, last: bool, seconds: float) -> str:
    """The film look, plus the fade in on the first chunk and the fade out on the last (ED-04)."""
    f = LOOK
    if first:
        f += f",fade=t=in:st=0:d={FADE_IN}"
    if last:
        f += f",fade=t=out:st={max(0.0, seconds - FADE_OUT):.3f}:d={FADE_OUT}"
    return f


def plan_stamp(timed: dict, size: tuple[int, int], crf: int, grade_key: str | None, bounds: list, pics: dict, dirs: list[Path]) -> str:
    """What the chunks on disk were made from: the timing, the size, the picture files. A change anywhere starts the chunks over."""
    files = []
    for pid in sorted({s["picture"] for s in timed["shots"]}):
        p = find_picture(pid, pics, dirs)
        if p:
            st = p.stat()
            files.append([pid, p.name, st.st_size, st.st_mtime_ns])
            dm = p.with_name(p.stem + ".depth.png")  # a depth map made later changes the parallax shots
            if dm.exists():
                files.append([pid, dm.name, dm.stat().st_size, dm.stat().st_mtime_ns])
    body = {"timed": {k: v for k, v in timed.items() if k != "findings"}, "size": list(size), "crf": crf, "grade": grade_key,
            "bounds": bounds, "pictures": files, "look": LOOK, "version": 1}
    return hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def progress(out: Path, done: int, total: int, reused: int) -> None:
    (out / "render_progress.json").write_text(json.dumps({"chunks_done": done, "chunks_total": total, "reused": reused}))
    print(f"chunk {done}/{total} done ({reused} reused)", flush=True)


def mux(out: Path, bounds: list) -> None:
    """The finished chunks joined without re-encoding, with the audio; the chunk files go only after video.mp4 is whole."""
    chunks = out / "chunks"
    names = [f"c_{i:04d}.mp4" for i in range(len(bounds))]
    (chunks / "list.txt").write_text("".join(f"file '{n}'\n" for n in names))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(chunks / "list.txt"), "-i", str(out / "audio.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", *AUDIO_CODEC, str(out / "video.part.mp4")], check=True)
    os.replace(out / "video.part.mp4", out / "video.mp4")  # a video.mp4 on disk is always a finished one
    for f in chunks.iterdir():
        f.unlink()
    chunks.rmdir()


# BP-63: the delivered file carries stereo AAC-LC at the registry's bitrate and sample rate (YouTube's recommended upload
# settings); the mono mix is upmixed to two identical channels. Shared with the Shorts renderer.
_DELIVERY = RULES.rule("BP-63")["thresholds"]
AUDIO_CODEC = ["-c:a", "aac", "-b:a", f"{_DELIVERY['aac_kbps']}k", "-ar", str(_DELIVERY["sample_rate"]), "-ac", str(_DELIVERY["channels"])]


def measure_delivery(audio: Path, narration: Path | None = None, profile: str = "long") -> dict:
    """ebur128 of the normalised mix (integrated, true peak) with the verdicts next to the numbers (BP-50), and, when the
    narration stem is given, the dialogue anchor (BP-51: mix minus voice in LU) from a second measurement."""
    meas = targets.measure_file(audio)
    voice = targets.measure_file(narration)["lufs"] if narration is not None else None
    out = {k: v for k, v in meas.items() if k in ("lufs", "true_peak", "lra", "max_short_term")}
    if voice is not None:
        out["voice_lufs"] = voice
    out.update(targets.verdicts(meas, profile, voice))
    return out


def lock_alive(lock: Path) -> bool:
    """Is the process named in the lock still an assemble? After a restart of the machine the pid may belong to something else."""
    try:
        pid = int(lock.read_text())
        os.kill(pid, 0)
    except PermissionError:
        pass  # the pid exists but belongs to another user (a non-root runner): it is not ours unless its cmdline says so
    except (ProcessLookupError, ValueError, FileNotFoundError):
        return False
    cmd = Path(f"/proc/{pid}/cmdline")
    return b"explainer_engine" in cmd.read_bytes() if cmd.exists() else True


def assemble(timed: dict, narration_wav: Path, out: Path, picture_dirs: list[Path], sound_dirs: list[Path], *,
             size: tuple[int, int] = (1920, 1080), final: bool = False, grade_key: str | None = None,
             audio_only: bool = False, crf: int = 18, chunk_seconds: float = CHUNK_SECONDS,
             only: tuple[int, int] | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    fails = [x for x in timed.get("findings", []) if x.get("severity") == "FAIL"]
    if fails:  # 2026-10-16: a shell chain started a render on a timing with 3 FAIL
        raise SystemExit(f"refused: the timing has {len(fails)} FAIL ({fails[0]['rule']}: {fails[0]['detail']}); fix and re-time")
    lock = out / ".assemble.lock"
    if lock.exists() and lock_alive(lock):
        raise SystemExit(f"refused: another assemble (pid {lock.read_text()}) writes {out}")  # else a stale lock from a run that died
    lock.write_text(str(os.getpid()))
    try:
        return _assemble(timed, narration_wav, out, picture_dirs, sound_dirs, size=size, final=final, grade_key=grade_key,
                         audio_only=audio_only, crf=crf, chunk_seconds=chunk_seconds, only=only)
    finally:
        lock.unlink(missing_ok=True)


def _assemble(timed: dict, narration_wav: Path, out: Path, picture_dirs: list[Path], sound_dirs: list[Path], *,
              size: tuple[int, int], final: bool, grade_key: str | None, audio_only: bool, crf: int,
              chunk_seconds: float, only: tuple[int, int] | None) -> dict:
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
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", targets.loudnorm("long"), "-ar", str(SR),
                    "-ac", "1", str(out / "audio.wav")], check=True)
    # BP-50: integrated loudness and true peak are measured on the normalised mix and judged, never only stored; BP-51: the
    # narration stem's loudness against the mix (two ebur128 runs, free)
    stats.update(measure_delivery(out / "audio.wav", narration_wav, "long"))
    report: list[str] = []
    result = {"audio": stats, "pictures": report, "video": None}
    bad = targets.failures(stats)
    if bad and final:  # a final render never passes a FAIL silently: the report is written, then the run stops with the numbers
        (out / "assemble_report.json").write_text(json.dumps(result, indent=1))
        raise SystemExit(f"final render refused: the mix fails {', '.join(bad)} ({stats['loudness_verdict']} loudness, "
                         f"{stats.get('true_peak_verdict', 'n/a')} true peak; BP-50); fix the mix, then render again")
    if audio_only:
        (out / "assemble_report.json").write_text(json.dumps(result, indent=1))
        return result
    codex = resolver.load_codex()
    params = codex["grades"].get(grade_key or "prehistory")
    pics, shots = timed["pictures"], timed["shots"]
    bounds = chunk_bounds(shots, fps, timed["frames"], chunk_seconds)
    chunks = out / "chunks"
    chunks.mkdir(exist_ok=True)
    stamp = plan_stamp(timed, size, crf, grade_key, bounds, pics, picture_dirs)
    plan_file = chunks / "plan.json"
    if not plan_file.exists() or json.loads(plan_file.read_text()).get("stamp") != stamp:
        for old in chunks.glob("c_*.mp4"):  # a chunk of another plan is never reused
            old.unlink()
        for old in chunks.glob("c_*.part.mp4"):
            old.unlink()
        plan_file.write_text(json.dumps({"stamp": stamp, "bounds": bounds}))
    cache: dict = {}
    all_beats = timed.get("visual_beats", [])
    hero_faces = hero_faces_of(timed)
    depths: dict = {}  # the depth map of the picture in memory (stage F parallax)
    face_order = sorted(hero_faces)

    def prep(k: int):
        """The graded picture and the bubbles of shot k. A run of shots on one picture shares one grading (the seed is the
        run's first shot), so a chunk edge inside such a run draws the same grain as the unbroken render would."""
        s = shots[k]
        pid = s["picture"]
        if pid not in cache:
            seed = k
            while seed > 0 and shots[seed - 1]["picture"] == pid:
                seed -= 1
            im = picture_image(pid, pics, picture_dirs, final, report)
            if im is None:
                im = placeholder(pid, pics.get(pid, {}).get("subject") or pics.get(pid, {}).get("edit", ""), (OW, OH))
            elif params:
                im = Image.fromarray((grade(np.asarray(im, dtype=np.float64) / 255.0, params, seed=seed) * 255).astype(np.uint8))
            cache.clear()  # one picture in memory at a time (8 GB machines)
            cache[pid] = im
            depths.clear()
            if PAR.amount(s["motion"]) > 0:
                depths[pid] = PAR.load(find_picture(pid, pics, picture_dirs))
                if depths[pid] is None:
                    report.append(f"{pid}: parallax asked, no depth map (python -m explainer_engine.production.depth): flat")
        im = cache[pid]
        W, H = im.size
        f0, f1 = s["start_frame"], s["end_frame"]
        speakers = pics.get(pid, {}).get("speakers", {})
        bubbles = []
        for b in s["bubbles"]:
            u = (b["start_frame"] - f0) / max(1, f1 - f0 - 1)
            box = motion_box(s.get("render_motion", s["motion"]), W, H, min(max(u, 0.0), 1.0))
            sp = to_frame(speakers.get(b["who"], [0.5, 0.4]), box, W, H, OW, OH)
            bubbles.append(BUB.Bubble(b["text"], sp, b["start"], b["end"], (OW, OH), kind=b.get("kind", "speech"),
                                      avoid=[x.box for x in bubbles if x.end > b["start"]]))
        return im, bubbles

    def draw(k: int, im: Image.Image, bubbles: list, f: int, before: Image.Image | None = None) -> Image.Image:
        s = shots[k]
        f0, f1 = s["start_frame"], s["end_frame"]
        W, H = im.size
        u = (f - f0) / max(1, f1 - f0 - 1)
        box = motion_box(s.get("render_motion", s["motion"]), W, H, u)
        frame = finish_frame(im, box, s, f, fps, (OW, OH), beats_of.get(k) or [], hero_faces, face_order, picture_dirs,
                             bubbles, before, depths.get(s["picture"]))
        return overlays(frame, f, fps, timed)

    beats_of = {k: beats_for_shot(all_beats, s, pics, hero_faces, picture_dirs) for k, s in enumerate(shots)} if all_beats else {}

    written, reused = 0, 0
    todo = range(len(bounds)) if only is None else range(*only)  # a part-by-part run draws only its chunks (e.g. 0:3)
    for i, (k0, k1) in enumerate(bounds):
        if i not in todo:
            continue
        n_frames = sum(shots[k]["end_frame"] - shots[k]["start_frame"] for k in range(k0, k1))
        part = chunks / f"c_{i:04d}.mp4"
        if part.exists():
            written += n_frames
            reused += 1
            progress(out, i + 1, len(bounds), reused)
            continue
        tmp = chunks / f"c_{i:04d}.part.mp4"
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(fps),
                               "-i", "-", "-vf", chunk_look(i == 0, i == len(bounds) - 1, n_frames / fps), "-c:v", "libx264",
                               "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", "-frames:v", str(n_frames), "-an",
                               str(tmp)], stdin=subprocess.PIPE)
        last = None
        if k0 > 0 and shots[k0].get("transition") == "dissolve":  # the picture before melts into this one: draw its last frame
            im, bubbles = prep(k0 - 1)
            last = draw(k0 - 1, im, bubbles, shots[k0 - 1]["end_frame"] - 1)
        for k in range(k0, k1):
            s = shots[k]
            f0, f1 = s["start_frame"], s["end_frame"]
            im, bubbles = prep(k)
            dissolve = round(float(s.get("transition_seconds", 1.0)) * fps) if s.get("transition") == "dissolve" and last is not None else 0
            before = last  # the last frame of the shot before (a whip accent pulls from it)
            for f in range(f0, f1):
                frame = draw(k, im, bubbles, f, before)
                if f - f0 < dissolve:  # UR-14: the picture before melts into this one
                    frame = Image.blend(last, frame, (f - f0 + 1) / (dissolve + 1))
                last = frame
                ff.stdin.write(frame.tobytes())
                written += 1
        ff.stdin.close()
        if ff.wait() != 0:
            raise SystemExit(f"ffmpeg failed in chunk {i}; the finished chunks stay in {chunks} and the next run reuses them")
        os.replace(tmp, part)  # a c_NNNN.mp4 on disk is always a finished chunk
        progress(out, i + 1, len(bounds), reused)
    left = [i for i in range(len(bounds)) if not (chunks / f"c_{i:04d}.mp4").exists()]
    result["chunks"] = {"count": len(bounds), "reused": reused, "left": left}
    if not left:
        mux(out, bounds)
        result["video"] = str(out / "video.mp4")
    result["frames_written"] = written
    result["frames_planned"] = timed["frames"]
    (out / "assemble_report.json").write_text(json.dumps(result, indent=1))
    return result
