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
from explainer_engine.audio import acoustics, seams, sound_director as SD
from explainer_engine.audio import cues as CUES, duck
from explainer_engine.audio import spine as SPINE
from explainer_engine.core import contracts, delivery
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import replace_file, write_json_atomic
from explainer_engine.production import accents as ACC
from explainer_engine.production import beats as BEATS
from explainer_engine.production import faces as FACES
from explainer_engine.production import continuity
from explainer_engine.production import parallax as PAR
from explainer_engine.production import graphics as GFX
from explainer_engine.finish import bubbles as BUB
from explainer_engine.finish import grade as grade_mod
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

    def __init__(self, dirs: list[Path], library: Path | None = None):
        lib = Path(library) if library is not None else LIB  # a job's manifest names the library it was planned against
        self.dirs = [Path(d) for d in dirs]
        man = lib / "manifest.json"
        items = json.loads(man.read_text())["items"] if man.exists() else []
        self.lib = {x["id"]: lib / x["file"] for x in items}
        self.meta = {x["id"]: x for x in items}
        music = lib / "music"
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


# --- the stereo mix (P4: BP-116..123, docs/AUDIO_SYSTEM.md SD-01..SD-15) -------------------------------------------------------
# Used only when the job holds a fresh ``audio/sound_mix_manifest.json`` (``v2_manifest``); without one ``build_audio`` above
# runs unchanged. Every stem is float32; the centred ones (narration, cues) stay mono until they are written.

def v2_manifest(job: Path | None) -> dict | None:
    """The job's sound mix manifest when it exists and is valid and fresh; ``None`` when there is none (the old mono path). A
    manifest that is not a ``sound_mix_manifest/2``, fails its schema or its CN-16 rules, or is stale against its inputs (CN-02)
    stops the render: SD-15, invariant 7 (a forged or out-of-date plan never selects the stereo path)."""
    if job is None:
        return None
    path = Path(job) / "audio" / "sound_mix_manifest.json"
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"refused: SD-15 the sound mix manifest is not JSON ({e})") from None
    if not isinstance(manifest, dict) or manifest.get("schema") != "sound_mix_manifest/2":
        raise SystemExit("refused: SD-15 the sound mix manifest names no sound_mix_manifest/2 (the stereo mix reads only /2); run "
                         f"python -m explainer_engine.audio.sound_director plan {job}")
    found = [f for f in contracts.errors(manifest, Path(job)) if f["severity"] == "FAIL"]
    if found:
        stale = [f for f in found if f["rule"] == "CN-02"]
        what = "stale" if stale else "invalid"
        f = (stale or found)[0]
        raise SystemExit(f"refused: SD-15 the sound mix manifest is {what} ({f['rule']} {f['where']}: {f['detail']}); run "
                         f"python -m explainer_engine.audio.sound_director plan {job} and render again")
    return manifest


def v2_library(manifest: dict, job: Path) -> Path:
    """The sound library the manifest was planned against (its ``derived_from.library`` file's folder)."""
    return (Path(job) / manifest["derived_from"]["library"]["path"]).resolve().parent


def perspective(name: str) -> dict:
    """BP-122 as render numbers: the wet share of the scene's impulse response, the far high shelf and the near proximity boost.
    ``mid`` is the midpoint of the registry's two ends (BP-122 names only the far and the close one)."""
    wide, close = float(RULES.T("BP-122", "wide_wet")), 1.0 - float(RULES.T("BP-122", "close_dry"))
    k = {"far": 1.0, "mid": 0.5, "near": 0.0}[name]
    return {"wet": close + (wide - close) * k, "shelf_db": float(RULES.T("BP-122", "wide_shelf_db")) * k,
            "prox_db": float(RULES.T("BP-122", "proximity_db")) * (1.0 - k)}


def _wet(x: np.ndarray, ir: np.ndarray | None, wet: float, tail: bool = False) -> np.ndarray:
    """``x`` with the scene's impulse response mixed in at the ``wet`` share; ``tail`` keeps the room's decay after the sound ends."""
    if ir is None or len(ir) <= 1:
        return x
    dry = np.pad(x, (0, len(ir) - 1)) if tail else x
    return ((1.0 - wet) * dry + wet * acoustics.convolve(x, ir, tail=tail)).astype(np.float32)


def _stereo_add(dst: np.ndarray, a: int, src: np.ndarray) -> None:
    z = min(len(dst), a + len(src))
    if z > a:
        dst[a:z] += src[: z - a]


def _normalised(x: np.ndarray, gain_db: float) -> np.ndarray:
    return (x / (np.abs(x).max() + 1e-9) * db(gain_db)).astype(np.float32)


def write_wav(path: Path, x: np.ndarray, rate: int = SR) -> None:
    """16-bit PCM, written in blocks (a 15-minute stereo float array is never copied whole). ``x`` is (n,) or (n, ch)."""
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch), w.setsampwidth(2), w.setframerate(rate)
        for i in range(0, len(x), 1 << 20):
            w.writeframes((np.clip(x[i:i + (1 << 20)], -1, 1) * 32767).astype("<i2").tobytes())


def write_stems(stems: dict, directory: Path) -> list[Path]:
    """``<job>/audio/stems/<name>.wav``: one file per stem, the mixer's own sum before loudnorm."""
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for name, x in stems.items():
        p = directory / f"{name}.wav"
        write_wav(p, x)
        out.append(p)
    return out


def _vacuum(stem: np.ndarray, vacuums: list[dict], fps: int, target_db: float) -> list[dict]:
    """Pull ``stem`` (n, 2, in place) to ``target_db`` RMS (mid channel) inside every vacuum: a fall over VACUUM_RAMP_MS (never
    steeper than BP-53's step limit), the level held to the reveal, BP-53's release after it. Returns the measured pulls."""
    t = lambda f: int(round(f / fps * SR))  # noqa: E731
    ramp, rel = int(SD.VACUUM_RAMP_MS / 1000 * SR), int(duck.RELEASE_MS / 1000 * SR)
    done = []
    for v in vacuums:
        a, z = t(v["start_frame"]), min(len(stem), t(v["end_frame"]))
        r = min(ramp, max(0, z - a))
        if z - a <= r or z - a < SR // 20:
            continue
        level = rms_db(stem[a + r:z].mean(axis=1))
        pull = target_db - level
        if pull >= 0:  # already under the vacuum level
            done.append({"start_frame": v["start_frame"], "pull_db": 0.0, "level_dbfs": round(level, 2)})
            continue
        fall = 10 ** (np.linspace(0.0, pull, r) / 20.0) if r else np.zeros(0)
        back = 10 ** (np.linspace(pull, 0.0, min(rel, len(stem) - z)) / 20.0)
        stem[a:a + r] *= fall[:, None].astype(np.float32)
        stem[a + r:z] *= np.float32(10 ** (pull / 20.0))
        stem[z:z + len(back)] *= back[:, None].astype(np.float32)
        done.append({"start_frame": v["start_frame"], "pull_db": round(pull, 2), "level_dbfs": round(level, 2)})
    return done


def build_audio_v2(manifest: dict, spine: dict, narration: np.ndarray, sounds: "Sounds", stats: dict) -> tuple[np.ndarray, dict]:
    """The stereo mix of ``sound_mix_manifest/2`` (docs/AUDIO_SYSTEM.md): ``(mix (n, 2) float32, stems {name: (n, 2)})``.

    Narration: leveled as today, high-passed (BP-118), cut into pieces around the spine's dialogue windows (D-88) with the seam
    fade at each edge. Beds and room tone: looped or played once, faded, a scene impulse response at the mid wet share, widened.
    Music: as today (BP-62 fades) plus widen, the presence-band dip keyed by the voice (BP-118) and BP-53's duck. Spots:
    perspective (BP-122), the pan of the manifest (BP-121), hits as three summed layers. Vacuums (BP-120) pull every stem but
    narration, room tone, cues and hits. Cues are centred. The sum gets the same 0.5 s / FADE_OUT ramps and the 0.89 peak as the
    old path, applied to the stems too so they still add up to the mix."""
    fps, n = int(manifest["fps"]), int(round(manifest["total_frames"] / manifest["fps"] * SR))
    t = lambda f: int(round(f / fps * SR))  # noqa: E731
    can_loop = getattr(sounds, "loopable", lambda name: True)
    stats["engine"] = "v2"
    cache: dict = {}

    def load(ref: str) -> np.ndarray:
        if ref not in cache:
            cache[ref] = np.asarray(sounds.load(ref), dtype=np.float32)
        return cache[ref]

    # narration and dialogue
    voice = level_voice(np.asarray(narration, dtype=np.float64), SR)
    voice = acoustics.highpass(voice, SR, float(RULES.T("BP-118", "narration_hpf_hz")[0]))
    voice = (voice / (np.abs(voice).max() + 1e-9) * 0.9 * db(-3)).astype(np.float32)
    nar = np.zeros(n, np.float32)
    wins = sorted(spine["post_hoc_shots"], key=lambda h: h["start_frame"])
    cuts = [0] + [f for h in wins for f in (h["start_frame"], h["end_frame"])] + [int(manifest["total_frames"])]
    edge = int(seams.EDGE_FADE * SR)
    for fa, fz in zip(cuts[0::2], cuts[1::2]):
        a, z = t(fa), min(n, t(fz))
        r0 = int(round(SPINE.read_time(spine, fa) * SR))
        piece = voice[r0:r0 + (z - a)].copy()
        if wins:
            fade(piece, edge if fa > 0 else 0, edge if fz < manifest["total_frames"] else 0)
        nar[a:a + len(piece)] = piece
    del voice
    speech, pause = SD.speech_masks(spine, n, SR)
    dlg = np.zeros(n, np.float32)
    present = [d for d in manifest["dialogue"] if d["ref"]]
    if present:
        target = rms_db(nar[speech])
        for d in present:
            clip = load(d["ref"])
            a = t(d["start_frame"])
            clip = clip[: t(d["end_frame"]) - a].copy()
            clip *= np.float32(10 ** ((target - rms_db(clip)) / 20.0)) if len(clip) else 1.0
            fade(clip, edge, edge)
            dlg[a:a + len(clip)] += clip[: max(0, n - a)]
    side = nar + dlg
    vduck = duck.duck_gain(side, SR, n).astype(np.float32)  # BP-53: music and beds dip under every voice
    stats["voice_duck_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(vduck, SR), 3)
    del side

    # scenes: the impulse response and widen seed of each, found by frame
    scenes = {s["scene"]: s for s in manifest["scenes"]}
    irs: dict = {}

    def room_of(sid: str):
        s = scenes[sid]
        if sid not in irs:
            irs[sid] = acoustics.impulse(s["acoustic"], s["ir_seed"], SR)
        return irs[sid], s["ir_seed"]

    mid = perspective("mid")

    def scene_at(frame: int) -> str:
        return next((s["scene"] for s in manifest["scenes"] if s["start_frame"] <= frame < s["end_frame"]), manifest["scenes"][-1]["scene"])

    # beds, room tone, native clip audio
    room, amb = np.zeros((n, 2), np.float32), np.zeros((n, 2), np.float32)
    for b in manifest["beds"]:
        a, z = max(0, t(b["start_frame"])), min(n, t(b["end_frame"]))
        if z <= a:
            continue
        src = load(b["ref"])
        meta = getattr(sounds, "meta", {}).get(b["ref"], {})
        if b["kind"] == "room_tone" and meta.get("source", {}).get("kind") == "procedural":
            seg = np.resize(src, z - a)  # a procedural tone is circular: tiled, it has no seam
        else:
            seg = loop_to(src, z - a) if can_loop(b["ref"]) and b["kind"] != "native" else play_once(src, z - a)
        seg = _normalised(seg, b["gain_db"])
        fade(seg, t(b["fade_in_frames"]), t(b["fade_out_frames"]))
        ir, seed = room_of(b["scene"])
        seg = _wet(seg, ir, mid["wet"])
        _stereo_add(room if b["kind"] == "room_tone" else amb, a, acoustics.widen(seg, seed))

    # music
    mus = np.zeros(n, np.float32)
    for m in manifest["music"]:
        a, z = t(m["start_frame"]), min(n, t(m["end_frame"]))
        if z <= a:
            continue
        src = load(m["ref"])
        seg = loop_to(src, z - a) if can_loop(m["ref"]) else play_once(src, z - a)
        seg = _normalised(seg, m["gain_db"])
        fade(seg, t(m["fade_in_frames"]), t(m["fade_out_frames"]))
        mus[a:z] += seg
    music = acoustics.widen(mus, acoustics.seed_of("music"))
    del mus

    # spots: perspective, room, pan; hits are summed layers and kept apart (a vacuum does not pull them)
    sfx = np.zeros((n, 2), np.float32)
    hit_parts: list[tuple[int, np.ndarray]] = []
    shares: dict = {}
    bands = {"sub": (0.0, float(RULES.T("BP-119", "sub_hz"))), "body": tuple(map(float, RULES.T("BP-119", "body_hz"))),
             "air": tuple(map(float, RULES.T("BP-119", "air_hz")))}
    stats["sfx"] = []
    for s in manifest["spots"]:
        f = s["frame"] if s["frame"] is not None else spine["words"][s["word_index"]]["start_frame"]
        a = t(f)
        if a >= n:
            continue
        w = _normalised(load(s["ref"]), s["gain_db"])
        if s["group"]:
            shares[s["id"]] = acoustics.band_share(np.pad(w, (0, max(0, 32768 - len(w)))), SR, *bands[s["layer"]])
        w[: min(240, len(w))] *= np.linspace(0, 1, min(240, len(w)))  # 5 ms in, 10 ms out: no click
        w[-min(480, len(w)):] *= np.linspace(1, 0, min(480, len(w)))
        p = perspective(s["perspective"])
        w = acoustics.shelf(w, SR, float(RULES.T("BP-122", "shelf_hz")), p["shelf_db"], True)
        w = acoustics.shelf(w, SR, float(RULES.T("BP-122", "proximity_hz")), p["prox_db"], False)
        ir, _seed = room_of(scene_at(f))
        w = _wet(w, ir, p["wet"], tail=True)
        st = acoustics.pan(w, s["pan"]) * np.float32(acoustics.CENTRE_GAIN)
        if s["group"]:
            hit_parts.append((a, st.astype(np.float32)))
        else:
            _stereo_add(sfx, a, st.astype(np.float32))
            stats["sfx"].append({"sound": s["ref"], "start": round(f / fps, 3), "seconds": round(len(w) / SR, 3)})
    stats["hit_band_share"] = {k: round(v, 3) for k, v in shares.items() if v is not None}

    # the sidechain of the world sounds: music and beds dip under them (BP-53)
    side = sfx.mean(axis=1)
    for a, st in hit_parts:
        z = min(n, a + len(st))
        side[a:z] += st[: z - a].mean(axis=1)
    fduck = duck.duck_gain(side, SR, n, threshold=0.01).astype(np.float32)
    bduck = duck.duck_gain(side, SR, n, depth_db=float(RULES.T("BP-53", "depth_db")[0]), threshold=0.01).astype(np.float32)
    del side
    stats["music_dip_max_step_db_per_ms"] = round(duck.max_step_db_per_ms(fduck, SR), 3)

    # the presence-band dip, keyed by the voice's own duck curve, on everything that is not the voice (BP-118)
    hz, q = float(RULES.T("BP-118", "notch_hz")), float(RULES.T("BP-118", "notch_q"))
    lo, hi = (float(x) for x in RULES.T("BP-118", "measure_band_hz"))
    gap = float(RULES.T("BP-118", "notch_depth_db")[1])
    depth = acoustics.dip_centre_for_gap(gap, hz, q, lo, hi)
    key = acoustics.key_from_gain(vduck, duck.DEPTH_DB)
    music = acoustics.band_dip(music, SR, key, hz, q, depth)
    room = acoustics.band_dip(room, SR, key, hz, q, depth)
    amb = acoustics.band_dip(amb, SR, key, hz, q, depth)
    del key
    music *= (fduck * vduck)[:, None]
    bg = bduck * vduck
    room *= bg[:, None]
    amb *= bg[:, None]
    del fduck, bduck, bg, vduck

    # vacuums, then the hits on top, the bus of cues, the sum
    target = float(RULES.T("BP-120", "vacuum_dbfs"))
    stats["vacuums"] = {"music": _vacuum(music, manifest["vacuums"], fps, target), "ambience": _vacuum(amb, manifest["vacuums"], fps, target),
                        "sfx": _vacuum(sfx, manifest["vacuums"], fps, target)}
    for a, st in hit_parts:
        _stereo_add(sfx, a, st)
    amb += room
    cues = cue_bus([{"sound": c["name"], "start": c["frame"] / fps, "gain_db": c["gain_db"], "max_ms": c.get("max_ms")}
                    for c in manifest["cues"]], n).astype(np.float32)
    stats["cues"] = len(manifest["cues"])
    centre = nar + dlg + cues
    mix = np.stack([centre, centre], axis=1)
    del centre
    for part in (amb, music, sfx):
        mix += part
    stats.update(voice_rms_db=round(rms_db(nar[speech]), 2), bed_rms_db=round(rms_db(amb[speech].mean(axis=1)), 2),
                 music_rms_db=round(rms_db(music[speech].mean(axis=1)), 2))
    ramp_in, ramp_out = int(0.5 * SR), int(FADE_OUT * SR)
    up, down = np.linspace(0, 1, ramp_in, dtype=np.float32), np.linspace(1, 0, min(ramp_out, n), dtype=np.float32)

    def ramps(x: np.ndarray) -> np.ndarray:  # the sound opens and closes with the picture
        x[:ramp_in] *= up if x.ndim == 1 else up[:, None]
        x[-len(down):] *= down if x.ndim == 1 else down[:, None]
        return x

    ramps(mix)
    peak = float(np.abs(mix).max())
    k = np.float32(0.89 / peak) if peak > 0.89 else np.float32(1.0)
    mix *= k
    for x in (nar, dlg, cues, room, amb, music, sfx):
        ramps(x)
        x *= k
    stems = {"narration": np.broadcast_to((nar)[:, None], (n, 2)), "music": music, "sfx": sfx, "ambience": amb, "room_tone": room,
             "cues": np.broadcast_to(cues[:, None], (n, 2))}
    if manifest["dialogue"]:
        stems["dialogue"] = np.broadcast_to(dlg[:, None], (n, 2))
    return mix, stems


def stem_measures(stems: dict, spine: dict, workdir: Path) -> dict:
    """BP-52 on the stems while the narrator speaks: the integrated loudness (ebur128, ffmpeg) of the narration, music and ambience
    stems cut down to the stretches of speech and joined. ``voice_lu`` / ``music_lu`` / ``bed_lu`` are the keys the scorecard reads."""
    speech, _pause = SD.speech_masks(spine, len(stems["narration"]), SR)
    out = {}
    for key, name in (("voice_lu", "narration"), ("music_lu", "music"), ("bed_lu", "ambience")):
        x = stems[name].mean(axis=1)[speech]
        if not len(x) or float(np.abs(x).max()) < 1e-6:
            continue  # nothing of this stem under the voice: no gap to judge
        wav = workdir / f"{name}.speech.wav"
        write_wav(wav, x)
        try:
            out[key] = targets.measure_file(wav)["lufs"]
        finally:
            wav.unlink(missing_ok=True)
    return out


def render_v2(timed: dict, nar: np.ndarray, out: Path, job: Path, manifest: dict, sound_dirs: list[Path], stats: dict) -> list[dict]:
    """The stereo path of ``_assemble``: mix, ``audio_raw.wav`` (stereo) -> loudnorm, the stems in ``<job>/audio/stems/``, the BP-52
    measures and the render half of the sound director's checks. Returns the SD findings (also written into the report)."""
    spine = json.loads((job / "audio" / "audio_spine.json").read_text(encoding="utf-8"))
    sounds = Sounds([Path(d) for d in sound_dirs] + [job / "audio"], library=v2_library(manifest, job))
    n = int(round(manifest["total_frames"] / manifest["fps"] * SR))
    mix, stems = build_audio_v2(manifest, spine, nar, sounds, stats)
    write_wav(out / "audio_raw.wav", mix)
    targets.normalise_file(out / "audio_raw.wav", out / "audio.wav", "long", SR, channels=2)
    write_stems(stems, job / "audio" / "stems")
    measures = stem_measures(stems, spine, out)
    stats.update(measures)
    findings = SD.check_job(job, stems=dict(stems, mix=mix), measures=dict(measures, hit_band_share=stats.get("hit_band_share", {})))
    return findings


def sd14_pointer(stats: dict) -> list[dict]:
    """SD-14: the delivered loudness and true peak are judged by ``qa/targets`` (BP-50); this only points at that verdict."""
    out = []
    for key, what in (("loudness_verdict", "integrated loudness"), ("true_peak_verdict", "true peak")):
        if stats.get(key) not in (None, "PASS"):
            out.append({"rule": "SD-14", "severity": stats[key], "where": "mix", "basis": "BP-50",
                        "detail": f"{what} {stats.get('lufs' if key == 'loudness_verdict' else 'true_peak')}: {stats[key]} (qa/targets, BP-50)"})
    return out


# --- the picture timeline (P7: BP-128..130, ED-04, CN-02, CN-09, D-85) ----------------------------------------------------------
# ``edit_and_grade_manifest/1`` + the rendered shot clips -> the assembled video at the job's fps and the delivery size, with
# handles, the whip, the per-scene colour transfer toward the key master frame and the one LOOK last; its derived manifest and an
# OTIO export (card D3: export only). One assembler: this sits beside ``build_audio_v2``, it does not replace ``_assemble``.

CLIP_SUFFIXES = (".npy", ".mp4", ".mkv", ".mov", ".webm")  # .npy = uint8 frames (N, H, W, 3), the form tests and stills-to-motion use


def _finding(rule: str, where: str, detail: str, severity: str) -> dict:
    return contracts._f(rule, where, detail, severity)


def _checked_ref(job: Path, ref: dict, name: str) -> Path:
    path = Path(job) / ref["path"]
    if not path.exists():
        raise ContractError(f"CN-02 {name}: {ref['path']} does not exist")
    if contracts.sha256_file(path) != ref["sha256"]:
        raise ContractError(f"CN-02 {name}: {ref['path']} changed: the edit manifest is stale, re-plan it (never hand-edit)")
    return path


def clip_path(shots_dir: Path, shot_id: str) -> Path:
    for suffix in CLIP_SUFFIXES:
        p = Path(shots_dir) / f"{shot_id}{suffix}"
        if p.exists():
            return p
    raise ContractError(f"shot {shot_id} has no rendered clip in {shots_dir} ({'/'.join(CLIP_SUFFIXES)})")


def clip_info(path: Path) -> tuple[int, int, int]:
    """``(frames, width, height)`` of a rendered clip (the frames are counted, never trusted from a header)."""
    if path.suffix == ".npy":
        a = np.load(path, mmap_mode="r")
        return int(a.shape[0]), int(a.shape[2]), int(a.shape[1])
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames,width,height", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]
    return int(st["nb_read_frames"]), int(st["width"]), int(st["height"])


def clip_frames(path: Path, start: int, count: int):
    """The frames ``start .. start + count`` of a clip, one (H, W, 3) uint8 array at a time."""
    if path.suffix == ".npy":
        a = np.load(path, mmap_mode="r")
        for k in range(start, start + count):
            yield np.asarray(a[k])
        return
    _n, w, h = clip_info(path)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select='between(n,{start},{start + count - 1})'",
                           "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    try:
        for _ in range(count):
            raw = ff.stdout.read(w * h * 3)
            if len(raw) < w * h * 3:
                raise ContractError(f"{path.name}: ended before frame {start + count}")
            yield np.frombuffer(raw, np.uint8).reshape(h, w, 3)
    finally:
        ff.kill()
        ff.wait()


def _fit(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if (frame.shape[1], frame.shape[0]) == tuple(size):
        return frame
    return np.asarray(Image.fromarray(frame).resize(tuple(size), Image.LANCZOS))


def whip_length() -> int:
    """BP-129 ``whip_frames``: the middle of the registry's band."""
    lo, hi = RULES.T("BP-129", "whip_frames")
    return int(round((lo + hi) / 2))


def plan_video_v2(manifest: dict, job: Path, shots_dir: Path, *, size: tuple[int, int] | None = None, blend: float | None = None,
                  onsets: dict | None = None) -> dict:
    """The picture timeline of an ``edit_and_grade_manifest/1``: every shot's place, source window, handles and cut, the audio
    entries with their J/L leads, the scene grades and the findings. Refuses (``ContractError``, invariant 7, nothing repaired) a
    stale reference, a fps that disagrees with the spine, a timeline that does not tile the read, a clip shorter than its span, a
    lead longer than the shot it leaves. REVIEW findings: handles under BP-128's band, a cut off BP-128's onset band (``onsets``
    = {to_shot: frame the action begins}), a blend over BP-130's cap (applied capped)."""
    job = Path(job)
    contracts.validate(manifest)
    spine = json.loads(_checked_ref(job, manifest["audio_spine"], "audio_spine").read_text(encoding="utf-8"))
    film = json.loads(_checked_ref(job, manifest["film_shots"], "film_shots").read_text(encoding="utf-8"))
    fps, total = int(spine["fps"]), int(spine["total_frames"])
    if film.get("fps") not in (None, fps):
        raise ContractError(f"CN-09 film_shots.fps {film['fps']} differs from the spine's {fps} (D-85)")
    size = tuple(size or delivery.size())
    timeline = SD.shot_timeline(spine, {}, film, manifest)
    findings: list[dict] = []
    if not timeline or timeline[0]["start_frame"] != 0 or timeline[-1]["end_frame"] != total or any(
            a["end_frame"] != b["start_frame"] for a, b in zip(timeline, timeline[1:])):
        raise ContractError(f"the shots do not tile the {total} frames of the read (first start, gaps or overlaps, last end): "
                            "the compiler cuts what the manifest says and repairs nothing")
    cuts = {c["to_shot"]: c for sc in manifest["scenes"] for c in sc["cuts"]}
    by_id = {s["id"]: s for s in timeline}
    h_lo, _h_hi = RULES.T("BP-128", "handle_frames")
    o_lo, o_hi = RULES.T("BP-128", "cut_after_onset_frames")
    whip = whip_length()
    shots, audio = [], []
    for s in timeline:
        sid, span = s["id"], s["frames"]
        path = clip_path(shots_dir, sid)
        n, _w, _h = clip_info(path)
        if n < span:
            raise ContractError(f"shot {sid}: the clip has {n} frames, the cut span {span} (frames {s['start_frame']}..{s['end_frame']}); "
                                "render the shot again, a short clip is never stretched or repeated")
        head = (n - span) // 2
        if head < h_lo:
            findings.append(_finding("BP-128", sid, f"handles of {head} and {n - span - head} frames, under the band's {h_lo} (hypothesis rule)", "REVIEW"))
        cut = cuts.get(sid)
        entry = {"shot_id": sid, "scene": s["scene"], "start_frame": s["start_frame"], "end_frame": s["end_frame"], "frames": span,
                 "clip": path.name, "clip_frames": n, "source_in": head, "cut": None}
        lead = 0
        if cut is not None:
            if cut["at_frame"] != s["start_frame"] or cut["from_shot"] not in by_id:
                raise ContractError(f"cut {cut['from_shot']} -> {sid} at {cut['at_frame']}: the shot starts at {s['start_frame']} "
                                    "(a post-hoc window or an unknown shot)")
            lead = cut["audio_lead_frames"]
            if lead > by_id[cut["from_shot"]]["frames"]:
                raise ContractError(f"cut into {sid}: the audio lead of {lead} frames is longer than the shot it leaves "
                                    f"({by_id[cut['from_shot']]['frames']} frames)")
            entry["cut"] = dict(cut, whip_frames=whip if cut["cut_type"] == "WHIP_PAN" else 0)
            if cut["cut_type"] in ("DEPTH_MATCH_CUT", "OCCLUSION_WIPE"):
                findings.append(_finding("P7", sid, f"{cut['cut_type']} is rendered as a straight cut (no compositor in the picture path)", "REVIEW"))
            if onsets and sid in onsets:
                d = cut["at_frame"] - onsets[sid]
                if not o_lo <= d <= o_hi:
                    findings.append(_finding("BP-128", sid, f"the cut lands {d} frames after the action begins, the band is {o_lo}..{o_hi} (hypothesis rule)", "REVIEW"))
        shots.append(entry)
        audio.append({"shot_id": sid, "start_frame": s["start_frame"] - lead, "end_frame": s["end_frame"], "lead_frames": lead})
    top = float(RULES.T("BP-130", "blend_max"))
    applied, capped = grade_mod.blend_cap(top if blend is None else blend)
    if capped:
        findings.append(_finding("BP-130", "scenes", f"blend {blend} is over blend_max {top}: applied {applied}", "REVIEW"))
    codex = resolver.load_codex()["grades"]
    scenes = {}
    for sc in manifest["scenes"]:
        if sc["grade"] is not None and sc["grade"]["lut"] not in codex:
            raise ContractError(f"scene {sc['scene_id']}: grade {sc['grade']['lut']} is not in world/eras.json grades")
        key = None
        if sc["key_master_frame"] is not None:
            key = job / sc["key_master_frame"]
            if not key.exists():
                raise ContractError(f"scene {sc['scene_id']}: key master frame {sc['key_master_frame']} does not exist")
        scenes[sc["scene_id"]] = {"key_master_frame": sc["key_master_frame"], "grade": sc["grade"], "blend": applied if key else 0.0}
    return {"fps": fps, "total_frames": total, "size": list(size), "shots": shots, "audio": audio, "scenes": scenes, "findings": findings}


def iter_video_frames(plan: dict, job: Path, shots_dir: Path):
    """The assembled frames in order, ``(frame_index, uint8 (H, W, 3))``: source window, colour transfer toward the scene's key from
    the shot's two boundary frames (one correction per shot, so nothing flickers), the whip over a WHIP_PAN, and last the LOOK
    (era grade + grain, ED-04) of the scene."""
    size, codex = tuple(plan["size"]), resolver.load_codex()["grades"]
    whip_at = {s["start_frame"]: s["cut"]["whip_frames"] for s in plan["shots"] if s["cut"] and s["cut"]["whip_frames"]}
    keys: dict = {}
    for s in plan["shots"]:
        sc = plan["scenes"][s["scene"]]
        look = codex[sc["grade"]["lut"]] if sc["grade"] else None
        key = None
        if sc["key_master_frame"] is not None:
            if s["scene"] not in keys:
                keys[s["scene"]] = np.asarray(_fit(np.asarray(Image.open(Path(job) / sc["key_master_frame"]).convert("RGB")), size)) / 255.0
            key = keys[s["scene"]]
        frames = [_fit(f, size) for f in clip_frames(clip_path(shots_dir, s["shot_id"]), s["source_in"], s["frames"])]
        params = None
        if key is not None:
            a, b = frames[0] / 255.0, frames[-1] / 255.0
            params = grade_mod.transfer_params(np.concatenate([a.reshape(-1, 1, 3), b.reshape(-1, 1, 3)]), key)
        for k, im in enumerate(frames):
            f = s["start_frame"] + k
            x = im / 255.0
            if params is not None:
                x = grade_mod.apply_transfer(x, params, sc["blend"])
            for start, w in whip_at.items():  # the whip is centred on the cut; BP-129 ``whip_frames`` long
                i = f - (start - w // 2)
                if 0 <= i < w:
                    x = _whip_blur(x, 1.0 - abs(2.0 * (i + 0.5) / w - 1.0))
            if look is not None:
                x = grade_mod.grade(x, look, seed=f)
            yield f, np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)


def _whip_blur(x: np.ndarray, strength: float) -> np.ndarray:
    """A horizontal smear of up to 6 % of the width at the whip's middle (a camera whip; the 2D plane stays flat, BP-128)."""
    reach = strength * x.shape[1] * 0.06
    if reach < 1.0:
        return x
    taps = 7
    return sum(np.roll(x, int(round((j / (taps - 1) - 0.5) * reach)), axis=1) for j in range(taps)) / taps


def export_otio(derived: dict, path: Path) -> Path:
    """The derived manifest as OpenTimelineIO JSON (``Timeline.1``, stdlib ``json``, no dependency: card D3, export only). One video
    track and two audio tracks (picture and sound overlap at a J/L cut, so alternate shots alternate tracks)."""
    fps = derived["fps"]
    rt = lambda v: {"OTIO_SCHEMA": "RationalTime.1", "rate": float(fps), "value": float(v)}  # noqa: E731
    rng = lambda a, n: {"OTIO_SCHEMA": "TimeRange.1", "start_time": rt(a), "duration": rt(n)}  # noqa: E731

    def clip(name, src_in, n, url, meta):
        return {"OTIO_SCHEMA": "Clip.2", "name": name, "source_range": rng(src_in, n), "metadata": {"explainer_engine": meta},
                "media_reference": {"OTIO_SCHEMA": "ExternalReference.1", "target_url": url, "available_range": None, "metadata": {}},
                "effects": [], "markers": [], "enabled": True}

    video, a_tracks = [], [[], []]
    ends = [0, 0]
    for k, s in enumerate(derived["shots"]):
        video.append(clip(s["shot_id"], s["source_in"], s["frames"], s["clip"],
                          {"at_frame": s["start_frame"], "scene": s["scene"], "cut": s["cut"]}))
        a = derived["audio"][k]
        lane = k % 2
        if a["start_frame"] > ends[lane]:
            a_tracks[lane].append({"OTIO_SCHEMA": "Gap.1", "name": "", "source_range": rng(0, a["start_frame"] - ends[lane]),
                                   "metadata": {}, "effects": [], "markers": [], "enabled": True})
        n = a["end_frame"] - a["start_frame"]
        a_tracks[lane].append(clip(s["shot_id"] + "_audio", 0, n, "audio/mix.wav",
                                   {"at_frame": a["start_frame"], "lead_frames": a["lead_frames"], "picture_at_frame": s["start_frame"]}))
        ends[lane] = a["end_frame"]
    track = lambda name, kind, items: {"OTIO_SCHEMA": "Track.1", "name": name, "kind": kind, "children": items,  # noqa: E731
                                       "source_range": None, "metadata": {}, "effects": [], "markers": [], "enabled": True}
    doc = {"OTIO_SCHEMA": "Timeline.1", "name": derived.get("name", "episode"), "global_start_time": rt(0),
           "metadata": {"explainer_engine": {"schema": derived["schema"], "total_frames": derived["total_frames"], "fps": fps}},
           "tracks": {"OTIO_SCHEMA": "Stack.1", "name": "tracks", "source_range": None, "metadata": {}, "effects": [], "markers": [],
                      "enabled": True,
                      "children": [track("V1", "Video", video)] + [track(f"A{i + 1}", "Audio", t) for i, t in enumerate(a_tracks)]}}
    return write_json_atomic(Path(path), doc)


def build_video_v2(manifest: dict | Path, shots_dir: Path, out: Path, job: Path | None = None, *, size: tuple[int, int] | None = None,
                   blend: float | None = None, onsets: dict | None = None, crf: int = 18, name: str = "episode") -> dict:
    """Compile and encode the picture: ``out`` (an .mp4, no sound: ``build_audio_v2`` mixes that), beside it ``<out>.assemble.json``
    (the derived manifest, CN-02 ``derived_from``) and ``<out>.otio``. ``manifest`` is the ``edit_and_grade_manifest/1`` document or
    its path; ``job`` is the folder its file references are relative to (default: the parent of ``shots_dir``)."""
    shots_dir, out = Path(shots_dir), Path(out)
    job = Path(job) if job is not None else shots_dir.parent
    manifest_path = None
    if not isinstance(manifest, dict):
        manifest_path, manifest = Path(manifest), json.loads(Path(manifest).read_text(encoding="utf-8"))
    plan = plan_video_v2(manifest, job, shots_dir, size=size, blend=blend, onsets=onsets)
    w, h = plan["size"]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(plan["fps"]),
                           "-i", "-", "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an",
                           "-frames:v", str(plan["total_frames"]), str(tmp)], stdin=subprocess.PIPE)
    written = 0
    try:
        for f, frame in iter_video_frames(plan, job, shots_dir):
            ff.stdin.write(frame.tobytes())
            written += 1
        ff.stdin.close()
    except BaseException:
        ff.kill()
        raise
    finally:
        ff.wait()
    if ff.returncode != 0 or written != plan["total_frames"]:
        tmp.unlink(missing_ok=True)
        raise ContractError(f"ffmpeg failed or the frame count differs ({written} of {plan['total_frames']})")
    replace_file(tmp, out)
    derived_from = {k: dict(manifest[k]) for k in ("film_shots", "audio_spine")}
    if manifest_path is not None:
        try:
            derived_from["edit_and_grade_manifest"] = {"path": str(manifest_path.relative_to(job)), "sha256": contracts.sha256_file(manifest_path)}
        except ValueError:
            pass
    derived = dict(plan, schema="assemble_manifest/1", name=name, derived_from=derived_from, video=out.name,
                   handles={"handle_frames": RULES.T("BP-128", "handle_frames"), "cut_after_onset_frames": RULES.T("BP-128", "cut_after_onset_frames")})
    derived_path = write_json_atomic(out.with_name(out.stem + ".assemble.json"), derived)
    otio_path = export_otio(derived, out.with_suffix(".otio"))
    return {"video": out, "manifest": derived_path, "otio": otio_path, "frames": written, "findings": plan["findings"]}


# --- picture helpers -------------------------------------------------------------------------------------------------

FADE_IN, FADE_OUT = 1.0, 1.5  # ED-04: the episode opens from black and closes to black
LOOK = "vignette=PI/5,noise=alls=2:allf=t"  # ED-04: one constant film look over the whole episode (free, made by ffmpeg)


def look_filter(duration: float) -> str:
    return chunk_look(True, True, duration)


def overlays(frame: Image.Image, f: int, fps: int, timed: dict) -> Image.Image:
    """ED-09 period cards, ED-15 the time counter and ED-10 data visuals on one finished frame."""
    carded = False
    for c in timed.get("cards", []):
        t = (f - c["start_frame"]) / fps
        if 0 <= t <= GFX.card_length():
            frame = GFX.card(frame, c, t, c["of"], c["index"])
            carded = True
    for c in timed.get("counters", []):
        if c["start_frame"] <= f < c["end_frame"] and not carded:  # a card names the period itself
            frame = GFX.counter(frame, c["label"], (f - c["start_frame"]) / fps, c.get("prev"))
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


def close_beats(sb: list[dict] | None, s: dict) -> list[dict]:
    """The shot's expression beats that the render turns into a close-up (VB-09: a painted sheet face)."""
    return [b for b in sb or [] if b.get("kind") == "expression" and b.get("close_up") and b.get("shot") == s["id"]]


def shot_views(s: dict, sb: list[dict] | None, fps: int) -> list[dict]:
    """What each frame of shot ``s`` shows (faces.views): the timed file's ``views`` when timing wrote them, else the plan
    made here from the painted close-ups and the shot's bubbles (older timed files)."""
    if s.get("views"):
        return s["views"]
    return FACES.views(close_beats(sb, s), s["start_frame"], s["end_frame"], fps, bubbles=s.get("bubbles") or [])


def shot_bubbles(s: dict, pic: dict, size: tuple[int, int], out: tuple[int, int], sb: list[dict] | None = None,
                 fps: int = 30, order: list[str] | None = None) -> list:
    """The bubbles of one shot, each laid out once on the view it is shown on (faces.views: a bubble never crosses a change
    of the face frame, the creator 2026-10-20, CC-01): on the scene above the speaker's mouth point, clear of every hero's
    face, with the faces taken at the bubble's start AND end so a camera drift under a still bubble never slides a face
    beneath it; on the speaker's own close-up at the close-up's mouth, clear of its head. A bubble of an older timed file
    that still crosses a view change ends with its view (never on a frame it was not laid out for); on another hero's
    close-up its tail points off screen to the speaker's side."""
    W, H = size
    OW, OH = out
    f0, f1 = s["start_frame"], s["end_frame"]
    speakers = pic.get("speakers", {})
    close = close_beats(sb, s)
    vs = shot_views(s, sb, fps) if close or s.get("views") else [{"start_frame": f0, "end_frame": f1, "who": None}]
    bubbles = []
    for b in s["bubbles"]:
        bf0 = b["start_frame"]
        v = FACES.view_at(vs, min(max(bf0, f0), f1 - 1)) or {"start_frame": f0, "end_frame": f1, "who": None}
        bf1 = min(b["end_frame"], v["end_frame"], f1)
        end = b["end"] if bf1 == b["end_frame"] else bf1 / fps
        beat = FACES.face_in_view(close, v, bf0) if v["who"] is not None else None
        if beat is not None:
            mouth, head = FACES.mouth_and_head(beat, order or sorted({x.get("who") for x in close}), (OW, OH))
            if v["who"] == b["who"]:
                sp = mouth
            else:  # another hero's close-up (only an older timed file): the speaker is off screen on his side
                sx = speakers.get(b["who"], [0.5, 0.4])[0]
                sp = (0.0 if sx < 0.5 else float(OW), OH * 0.42)
            faces = [head]
        else:
            faces = []
            for fr in (bf0, max(bf0, bf1 - 1)):
                u = (fr - f0) / max(1, f1 - f0 - 1)
                box = motion_box(s.get("render_motion", s["motion"]), W, H, min(max(u, 0.0), 1.0))
                faces += [BUB.head_box(to_frame(pt, box, W, H, OW, OH), (OW, OH)) for who, pt in speakers.items()]
            u = (bf0 - f0) / max(1, f1 - f0 - 1)
            box = motion_box(s.get("render_motion", s["motion"]), W, H, min(max(u, 0.0), 1.0))
            sp = to_frame(speakers.get(b["who"], [0.5, 0.4]), box, W, H, OW, OH)
        bubbles.append(BUB.Bubble(b["text"], sp, b["start"], end, (OW, OH), kind=b.get("kind", "speech"),
                                  avoid=[x.box for x in bubbles if x.end > b["start"]], faces=faces))
    return bubbles


def bubble_findings(timed: dict, size: tuple[int, int] = (1920, 1080), picture_dirs: list[Path] | None = None) -> list[dict]:
    """BUBBLE-4 before any render: every bubble laid out as the render will lay it out, none over a face (FAIL). With
    ``picture_dirs`` the painted close-ups are known, so a bubble on a close-up view is laid out on the close-up."""
    out = []
    pics = timed.get("pictures", {})
    hero_faces = hero_faces_of(timed)
    beats = timed.get("visual_beats", [])
    for s in timed["shots"]:
        if not s.get("bubbles"):
            continue
        p = pics.get(s["picture"], {})
        aspect = p.get("aspect") or 16 / 9
        W = 2048
        sb = beats_for_shot(beats, s, pics, hero_faces, picture_dirs) if picture_dirs and beats else []
        for b in shot_bubbles(s, p, (W, round(W / aspect)), size, sb, timed.get("fps", 30), sorted(hero_faces)):
            if b.covers_face:
                out.append({"rule": "BUBBLE-4", "severity": "FAIL", "where": s["id"],
                            "detail": f"bubble {b.text[:36]!r} would cover a face: re-frame the shot or move the speaker"})
    return out


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
    # the face point of each expression in its picture; keyed by (frame, hero), since BEATS.faces returns copies (keyed by
    # id() of the copy it never matched, so the face focus and the close-up's side never saw a face, QA 2026-10-20)
    face = {(b["start_frame"], b.get("who")): b["face"] for b in BEATS.faces(on, pics)}
    on = [dict(b, face=face[(b["start_frame"], b.get("who"))]) if b["kind"] == "expression"
          and (b["start_frame"], b.get("who")) in face else b for b in on]
    keyed = {(b["start_frame"], b["who"]): b["close_up"] for b in FACES.sheet_beats(on, hero_faces, picture_dirs)}
    return [dict(b, close_up=keyed[(b["start_frame"], b["who"])]) if b["kind"] == "expression"
            and (b["start_frame"], b.get("who")) in keyed else b for b in on]


ACCENT_REST_S = 0.3  # engineering: a camera accent eases to rest over this before (and after) a cut inside one picture


def rest_weight(s: dict, f: int, fps: int) -> float:
    """1 inside a shot; easing to 0 at an edge where the same picture continues (ED-02: the next shot starts from this
    shot's plain move, so a held punch, a wobble or the face lean must be back at rest there, never snap; CC-06)."""
    rm = s.get("render_motion") or {}
    n = max(1, round(ACCENT_REST_S * fps))
    k = 1.0
    if rm.get("eout") is False:
        k = min(k, BEATS._ease((s["end_frame"] - 1 - f) / n))
    if rm.get("ein") is False:
        k = min(k, BEATS._ease((f - s["start_frame"]) / n))
    return k


def finish_frame(im: Image.Image, box, s: dict, f: int, fps: int, size: tuple[int, int], sb: list[dict], hero_faces: dict,
                 face_order: list[str], picture_dirs: list[Path], bubbles: list | None = None,
                 before: Image.Image | None = None, depth=None) -> Image.Image:
    """One frame of shot ``s`` from its picture and the crop ``box`` of the shot's own move: the 2.5D parallax (stage F,
    ``motion.parallax`` + a depth map), the face focus (VB-02), the accents (MO), the close-ups (VB-09) as the shot's view
    plan says (faces.views), the bubbles and the visual beats. The long video and the Shorts both draw here. Camera
    additions (face lean, accents) rest at a cut inside one picture."""
    f0, f1 = s["start_frame"], s["end_frame"]
    W, H = im.size
    k = rest_weight(s, f, fps)
    close = close_beats(sb, s)
    vs = shot_views(s, sb, fps) if close else None
    v = FACES.view_at(vs, f) if vs else None
    on_close = v is not None and v["who"] is not None
    if sb and not on_close:  # VB-02: the speaking face is the focus; each expression change pops toward it
        lean = BEATS.face_camera(box, W, H, [b for b in sb if b.get("face") is not None and b["shot"] == s["id"]], f, fps)
        box = tuple(a + (b - a) * k for a, b in zip(box, lean))
    acc = s.get("accents", [])
    if acc:  # MO rules (D-48): punch, shake, wobble move the crop; whips, flashes and words are drawn
        z, dx, dy = ACC.camera(acc, f, fps, f0)
        box = ACC.apply_camera(box, W, H, 1 + (z - 1) * k, dx * k, dy * k)
    frame = im.resize(size, Image.BICUBIC, box=box)
    if depth is not None and PAR.amount(s["motion"]) > 0:
        u = (f - f0) / max(1, f1 - f0 - 1)
        frame = PAR.shift(frame, depth, box, (W, H), u, PAR.amount(s["motion"]), PAR.direction(s["motion"]))
    if acc:
        frame = ACC.draw(frame, acc, f, fps, f0, f1, before, BUB.FONT)
    if close:  # VB-09: the view's keyed close-up over the scene, zoomed and blurred; it cuts in and out with its view
        frame = FACES.composite(frame, close, f, fps, face_order, vs)
    if bubbles:
        frame = BUB.composite(frame, bubbles, f / fps)
    if sb:  # a mark that points into the picture (ring, label, face mark) is not drawn while a close-up fills the frame
        frame = BEATS.draw(frame, [b for b in sb if not (on_close and b["kind"] in BEATS.PICTURE_BOUND)], f, fps, box, (W, H),
                           hero_faces, picture_dirs)
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


def render_code() -> str:
    """The hash of the code that draws a frame: a fix in the renderer must redraw the chunks, not reuse the old ones (the QA
    loop of 2026-10-20 re-reviewed chunks drawn before the face-lean fix and found the same jump again)."""
    mods = (__file__, ACC.__file__, BEATS.__file__, BEATS.ICONS.__file__, FACES.__file__, continuity.__file__, GFX.__file__, BUB.__file__,
            grade.__module__ and __import__(grade.__module__, fromlist=["_"]).__file__, RULES.__file__,
            str(Path(RULES.__file__).with_name("sourced_rules.json")))
    h = hashlib.sha1()
    for m in mods:
        h.update(Path(m).read_bytes())
    return h.hexdigest()


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
            "bounds": bounds, "pictures": files, "look": LOOK, "version": 1, "code": render_code()}
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
             only: tuple[int, int] | None = None, job: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    fails = [x for x in timed.get("findings", []) if x.get("severity") == "FAIL"]
    if fails:  # 2026-10-16: a shell chain started a render on a timing with 3 FAIL
        raise SystemExit(f"refused: the timing has {len(fails)} FAIL ({fails[0]['rule']}: {fails[0]['detail']}); fix and re-time")
    mix_manifest = v2_manifest(job)  # None: the old mono path; a stale manifest stops here (SD-15)
    lock = out / ".assemble.lock"
    if lock.exists() and lock_alive(lock):
        raise SystemExit(f"refused: another assemble (pid {lock.read_text()}) writes {out}")  # else a stale lock from a run that died
    lock.write_text(str(os.getpid()))
    try:
        return _assemble(timed, narration_wav, out, picture_dirs, sound_dirs, size=size, final=final, grade_key=grade_key,
                         audio_only=audio_only, crf=crf, chunk_seconds=chunk_seconds, only=only, job=job, mix_manifest=mix_manifest)
    finally:
        lock.unlink(missing_ok=True)


def _assemble(timed: dict, narration_wav: Path, out: Path, picture_dirs: list[Path], sound_dirs: list[Path], *,
              size: tuple[int, int], final: bool, grade_key: str | None, audio_only: bool, crf: int,
              chunk_seconds: float, only: tuple[int, int] | None, job: Path | None = None, mix_manifest: dict | None = None) -> dict:
    OW, OH = size
    fps = timed["fps"]
    sounds = Sounds(sound_dirs)
    nar, sr = read_wav(narration_wav)
    if sr != SR:
        nar = load_audio(narration_wav)
    stats: dict = {}
    sd_findings: list[dict] = []
    if mix_manifest is None:
        need = int(round(timed["frames"] / fps * SR))  # the audio is exactly as long as the frames (no -shortest trimming)
        nar = np.pad(nar, (0, max(0, need - len(nar))))[:need]
        audio = build_audio(timed, nar, sounds, stats)
        raw = out / "audio_raw.wav"
        with wave.open(str(raw), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        targets.normalise_file(raw, out / "audio.wav", "long", SR)
    else:  # the stereo mix of the sound director's manifest (docs/AUDIO_SYSTEM.md); the read is not stretched to the frames
        sd_findings = render_v2(timed, nar, out, Path(job), mix_manifest, sound_dirs, stats)
    # BP-50: integrated loudness and true peak are measured on the normalised mix and judged, never only stored; BP-51: the
    # narration stem's loudness against the mix (two ebur128 runs, free)
    stats.update(measure_delivery(out / "audio.wav", narration_wav, "long"))
    report: list[str] = []
    result = {"audio": stats, "pictures": report, "video": None}
    if mix_manifest is not None:
        sd_findings += sd14_pointer(stats)
        result["sound_director"] = sd_findings
    bad = targets.failures(stats) + [f"{f['rule']} {f['where']}" for f in sd_findings if f["severity"] == "FAIL" and f["rule"] != "SD-14"]
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
        bubbles = shot_bubbles(s, pics.get(pid, {}), (W, H), (OW, OH), beats_of.get(k) or [], fps, face_order)
        for b in bubbles:
            if b.covers_face:
                report.append(f"{s['id']}: bubble {b.text[:30]!r} covers a face (BUBBLE-4)")
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
