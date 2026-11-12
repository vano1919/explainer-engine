"""The one sound renderer (v4.3 plan P7, SP-02 in docs/EPISODE_FIRST.md): it plays an episode's ``sound_plan.json``
(``episode/sound_plan``) into five 48 kHz stereo stems (narration, music, ambience, sfx, mix), whatever the picture route of a
shot, so a Wan shot, a 2.5D shot and a map sound alike (R-D).

- Narration is the episode's real read (one WAV on the spine's clock); nothing here can make a voice. Without it a shippable
  render stops; a preview renders without a voice and says so.
- Sounds come from the library (``audio/sfx_library``). A placeholder (a procedural numpy sound from ``audio/foley``) plays
  only in a preview (``shippable=False``) and the report says ``shippable: false``; a shippable render with one stops.
- Levels: every event of a kind is set to the same RMS (``LEVELS``, engineering defaults kept under BP-65's caps), music and
  ambience duck under the voice (BP-53's house depth for music, its floor for the bed), each place gets its room tone and its
  room (a cave's impulse response), and a place change carries the plan's J/L bridge.
- ``level_report`` measures, per shot, the background (ambience + sfx) under speech and in the gaps, groups the shots by route
  and compares the groups' medians (BP-186, the creator's "the same level everywhere").
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from explainer_engine.audio import acoustics, duck, foley, sfx_library
from explainer_engine.audio.environmental_sound_design import validate_narration_source_file
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import sound_plan as SP
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR_RULES

SR = 48000
# RMS of one event in dBFS before ducking (engineering defaults; BP-65 caps the peaks: effect -8 dB, bed -15 dB)
LEVELS = {"spot": -26.0, "foley": -30.0, "ambience": -36.0, "music": -32.0, "clip_audio": -36.0}
ROOM_TONE_DB = -54.0         # the place's floor (BP-60/BP-161: never digital silence)
BED_DUCK_DB = float(SR_RULES.T("BP-53", "depth_db")[0])
MUSIC_DUCK_DB = duck.DEPTH_DB
SPREAD_MAX_DB = float(SR_RULES.T("BP-186", "route_spread_db_max"))
SPEECH_THRESHOLD = 0.02      # the voice's control level where a window counts as speech (duck.duck_gain's default)
# placeholder sounds: class -> foley generator (procedural, preview only)
PLACEHOLDER = {"footsteps_dirt": "footstep_dirt", "footsteps_stone": "footstep_stone", "footsteps_grass": "footstep_grass",
               "footsteps_ash": "footstep_dirt", "running": "footstep_dirt", "eruption_boom": "volcanic_explosion_debris",
               "eruption_rumble": "thunder_rumble", "ash_fall": "wind_howl", "thunder": "thunder_rumble",
               "fire": "fire_crackle_bed", "water_waves": "rain_downpour", "river": "rain_downpour", "rain": "rain_downpour",
               "wind": "wind_howl", "crowd": "crowd_battle_murmur", "stone_tools": "footstep_stone", "bow": "swish",
               "impact": "hit_body", "horse_hooves": "horse_hooves_gallop", "metal_clash": "sword_metal_clash"}


def _resample(x: np.ndarray, rate: int) -> np.ndarray:
    if rate == SR or len(x) < 2:
        return x.astype(np.float32)
    n = int(round(len(x) * SR / rate))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _rms_db(x: np.ndarray) -> float:
    return float(20 * np.log10(max(1e-9, float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))))))


def _at_level(x: np.ndarray, db: float) -> np.ndarray:
    return (x * np.float32(10 ** ((db - _rms_db(x)) / 20))).astype(np.float32) if len(x) else x


def _loop(x: np.ndarray, n: int, fade: int) -> np.ndarray:
    """``x`` repeated to ``n`` samples with an equal-power crossfade at every seam."""
    if len(x) >= n:
        return x[:n].copy()
    fade = max(1, min(fade, len(x) // 4))
    out = np.zeros(n, np.float32)
    w = np.sin(np.linspace(0, np.pi / 2, fade, dtype=np.float32))
    pos = 0
    while pos < n:
        seg = x.copy()
        if pos > 0:
            seg[:fade] *= w
            out[pos:pos + fade] *= w[::-1][: min(fade, n - pos)]
        end = min(n, pos + len(seg))
        out[pos:end] += seg[: end - pos]
        pos += len(x) - fade
    return out


def _fades(x: np.ndarray, a: int, b: int) -> np.ndarray:
    if a > 0:
        x[:a] *= np.linspace(0, 1, a, dtype=np.float32)
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b, dtype=np.float32)
    return x


class Sounds:
    """Sound per class: a real library take, or (preview only) a placeholder; every use is logged."""

    def __init__(self, sources: dict, library_root: Path, allow_placeholder: bool):
        self.sources, self.root, self.allow = sources, Path(library_root), allow_placeholder
        self.items = {i["id"]: i for i in sfx_library.load_manifest(self.root)["items"]} if (self.root / "manifest.json").is_file() \
            else {}
        self.used: list[dict] = []

    def get(self, cls: str, k: int) -> np.ndarray:
        src = self.sources.get(cls) or {"status": "missing"}
        if src["status"] == "library":
            iid = src["ids"][k % len(src["ids"])]
            path = self.root / self.items[iid]["file"]
            if path.is_file():
                x, rate = sfx_library.read_wav(path)
                self.used.append({"class": cls, "id": iid, "status": "library"})
                return _resample(x, rate)
            if not self.allow:
                raise ContractError(f"{cls}: library sound {iid} is listed but its file {path} is not here (fetch it from the vault)")
            src = {"status": "file not here"}
        if not self.allow:
            raise ContractError(f"{cls}: no real library sound ({src['status']}); a shippable mix never plays a placeholder")
        self.used.append({"class": cls, "id": PLACEHOLDER.get(cls), "status": "placeholder", "why": src["status"]})
        gen = PLACEHOLDER.get(cls)
        if gen is None:
            return np.zeros(SR // 10, np.float32)
        return foley.BUILD[gen][1](k + 1).astype(np.float32)


def _write(path: Path, stereo: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part.wav")
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(stereo, -1, 1) * 32767).astype("<i2").tobytes())
    tmp.replace(path)


def _narration(path: Path | None, n: int, shippable: bool) -> tuple[np.ndarray, str]:
    if path is None:
        if shippable:
            raise ContractError("no narration: a shippable mix needs the episode's real read (ElevenLabs), never a made voice")
        return np.zeros(n, np.float32), "none (preview)"
    validate_narration_source_file(path)
    with wave.open(str(path)) as w:
        ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ContractError(f"{path.name}: narration must be 16-bit PCM WAV")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    x = x.reshape(-1, ch).mean(axis=1) if ch > 1 else x
    x = _resample(x, rate)
    out = np.zeros(n, np.float32)
    out[: min(n, len(x))] = x[:n]
    return out, f"file:{path.name}"


def render(plan: dict, sources: dict, out_dir: Path, *, library_root: Path, narration: Path | None = None,
           shippable: bool = True) -> dict:
    """Render the plan into the five stems in ``out_dir``. ``shippable=False`` is a preview: placeholders allowed, no voice
    needed, and the report says it cannot ship."""
    ok, why = SP.shippable(sources, plan)
    if shippable and not ok:
        raise ContractError("not shippable: " + "; ".join(why))
    n = int(round(plan["duration_s"] * SR))
    snd = Sounds(sources, library_root, allow_placeholder=not shippable)
    voice, voice_src = _narration(Path(narration) if narration else None, n, shippable)
    amb = np.zeros((n, 2), np.float32)
    sfx = np.zeros((n, 2), np.float32)
    mus = np.zeros((n, 2), np.float32)
    fade = int(SP.BED_FADE_S * SR)
    for bi, bed in enumerate(plan["beds"]):
        a = max(0.0, bed["start_s"] - bed.get("lead_s", 0.0))
        b = min(plan["duration_s"], bed["end_s"] + bed.get("tail_s", 0.0))
        i0, i1 = int(round(a * SR)), min(n, int(round(b * SR)))
        m = i1 - i0
        if m <= 0:
            continue
        layer = np.zeros(m, np.float32)
        for k, cls in enumerate(bed["classes"]):
            layer += _at_level(_loop(snd.get(cls, bi + k), m, SR // 4), LEVELS["ambience"] - 3.0 * k)
        tone = _at_level(acoustics.room_tone(bed["room"] if bed["room"] in acoustics.KINDS else "outdoor",
                                             acoustics.seed_of(bed["bed_id"]), m / SR + 0.01, SR)[:m], ROOM_TONE_DB)
        layer += tone
        if bed["room"] == "cave":
            layer = acoustics.convolve(layer, acoustics.impulse("cave", acoustics.seed_of(bed["bed_id"]), SR))[:m]
        layer = _fades(layer, fade if bi > 0 else 0, fade if bi + 1 < len(plan["beds"]) else 0)
        amb[i0:i1] += acoustics.widen(layer, seed=acoustics.seed_of(bed["bed_id"]))[:m]
    placed = []
    for si, shot in enumerate(plan["shots"]):
        s0, dur = shot["start_s"], shot["dur_s"]
        for ei, ev in enumerate(shot["events"]):
            at = int(round((s0 + ev["at_s"]) * SR))
            if at >= n:
                continue
            if ev.get("source") == "clip_audio":
                continue   # the clip's own track joins at assembly as an extra layer, levelled like the rest (LEVELS)
            if ev["kind"] == "ambience":   # a place sound named in this shot: a shot-long layer over the bed
                m = min(n, int(round((s0 + dur) * SR))) - at
                if m <= 0:
                    continue
                x = _fades(_at_level(_loop(snd.get(ev["class"], si + ei), m, SR // 4), LEVELS["ambience"]), SR // 5, SR // 5)
                amb[at:at + m] += acoustics.widen(x, seed=acoustics.seed_of(shot["shot_id"] + ev["class"]))[:m]
            else:
                x = _at_level(snd.get(ev["class"], si + ei), LEVELS[ev["kind"]])
                if shot["room"] == "cave":
                    x = acoustics.convolve(x, acoustics.impulse("cave", acoustics.seed_of(shot["shot_id"]), SR))
                m = min(len(x), n - at)
                pan = float(np.clip(((ei % 5) - 2) * 0.15, -0.3, 0.3))
                sfx[at:at + m] += acoustics.pan(x[:m], pan)
            placed.append({"shot_id": shot["shot_id"], "class": ev["class"], "at_s": round(s0 + ev["at_s"], 3)})
    for mi, cue in enumerate(plan["music"]):
        i0, i1 = int(round(cue["start_s"] * SR)), min(n, int(round(cue["end_s"] * SR)))
        if i1 - i0 <= 0:
            continue
        x = _fades(_at_level(_loop(snd.get("music_bed", mi), i1 - i0, SR // 2), LEVELS["music"]), SR, 2 * SR)
        mus[i0:i1] += acoustics.pan(x, 0.0) * acoustics.CENTRE_GAIN
    g_mus = duck.duck_gain(voice, SR, n, depth_db=MUSIC_DUCK_DB, threshold=SPEECH_THRESHOLD).astype(np.float32)
    g_bed = duck.duck_gain(voice, SR, n, depth_db=BED_DUCK_DB, threshold=SPEECH_THRESHOLD).astype(np.float32)
    mus *= g_mus[:, None]
    amb *= g_bed[:, None]
    nar = (acoustics.pan(voice, 0.0) * acoustics.CENTRE_GAIN).astype(np.float32)
    mix = nar + amb + sfx + mus
    peak = float(np.abs(mix).max()) if n else 0.0
    if peak > 0.89:
        k = 0.89 / peak
        nar, amb, sfx, mus, mix = (s * k for s in (nar, amb, sfx, mus, mix))
    out_dir = Path(out_dir)
    stems = {"narration": nar, "music": mus, "ambience": amb, "sfx": sfx, "mix": mix}
    for name, s in stems.items():
        _write(out_dir / f"{name}.wav", s)
    levels = level_report(plan, voice, amb.mean(axis=1) + sfx.mean(axis=1))
    placeholders = sorted({u["class"] for u in snd.used if u["status"] == "placeholder"})
    return {"schema": "stems_report/1", "shippable": ok and not placeholders and voice_src.startswith("file:"),
            "narration_source": str(narration) if narration else "none",
            "blocked_era_events": plan.get("blocked_era_events", []), "music_duck_depth_db": MUSIC_DUCK_DB,
            "ambience_duck_depth_db": BED_DUCK_DB,
            "not_shippable_because": why + ([] if voice_src.startswith("file:") else ["no narration"]),
            "placeholders": placeholders, "narration": voice_src, "duration_s": plan["duration_s"], "sample_rate_hz": SR,
            "stems": {k: str(out_dir / f"{k}.wav") for k in stems}, "events_placed": placed,
            "bridges": plan["bridges"], "levels": levels, "gates": G.verdict(levels["rows"]),
            "sounds_used": snd.used}


def level_report(plan: dict, voice: np.ndarray, background: np.ndarray) -> dict:
    """Per shot: background RMS under speech and in the gaps; per route group: the medians; rows on the spread (BP-186)."""
    lvl = duck.control_level(voice, SR)
    speech = np.repeat(lvl > SPEECH_THRESHOLD, int(SR / duck.CTRL_HZ))
    speech = np.pad(speech, (0, max(0, len(voice) - len(speech))))[: len(voice)]
    per_shot = []
    for s in plan["shots"]:
        i0, i1 = int(round(s["start_s"] * SR)), min(len(voice), int(round((s["start_s"] + s["dur_s"]) * SR)))
        bg, sp = background[i0:i1], speech[i0:i1]
        rec = {"shot_id": s["shot_id"], "route": s.get("route") or "unrouted",
               "under_speech_db": round(_rms_db(bg[sp]), 2) if sp.sum() > SR // 10 else None,
               "in_gaps_db": round(_rms_db(bg[~sp]), 2) if (~sp).sum() > SR // 10 else None}
        per_shot.append(rec)
    groups: dict[str, dict] = {}
    for key in ("under_speech_db", "in_gaps_db"):
        by = {}
        for r in per_shot:
            if r[key] is not None:
                by.setdefault(r["route"], []).append(r[key])
        groups[key] = {g: round(float(np.median(v)), 2) for g, v in sorted(by.items())}
    rows = []
    for key, label in (("under_speech_db", "equal_level_under_speech"), ("in_gaps_db", "equal_level_in_gaps")):
        med = groups[key]
        if len(med) < 2:
            rows.append(G.row(label, None, f"fewer than two route groups measured ({sorted(med)}): nothing to compare",
                              med))
            continue
        spread = max(med.values()) - min(med.values())
        rows.append(G.row(label, spread <= SPREAD_MAX_DB, f"background {key[:-3].replace('_', ' ')}: route medians "
                          f"{med} dB, spread {spread:.2f} dB (BP-186: {SPREAD_MAX_DB})", round(spread, 2),
                          level=SR_RULES.level("BP-186")))
    return {"per_shot": per_shot, "groups": groups, "rows": rows}
