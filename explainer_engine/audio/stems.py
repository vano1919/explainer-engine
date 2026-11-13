"""The one sound renderer (v4.3 plan P7, SP-02 in docs/EPISODE_FIRST.md): it plays an episode's ``sound_plan.json``
(``episode/sound_plan``) into five 48 kHz stereo stems (narration, music, ambience, sfx, mix), whatever the picture route of a
shot, so a Wan shot, a 2.5D shot and a map sound alike (R-D).

- Narration is the episode's real read (one WAV on the spine's clock); nothing here can make a voice. Without it a shippable
  render stops; a preview renders without a voice and says so.
- Sounds come from the library (``audio/sfx_library``). A class without a real take is never filled with a made-up sound, in a
  preview either (D-136, OV-56 as changed: "procedural numpy sound never plays, in the demo either"): a preview
  (``shippable=False``) leaves that row silent, lists the class under ``placeholders`` (and the row under ``silent_rows``) and
  says ``shippable: false``; a shippable render with one stops. ``PLACEHOLDER`` only names the generator an older preview used.
- Every sound plays from a row of the episode's cue sheet (``episode/cue_sheet``, SP-06): asset, time, gain, pan, fades, pitch,
  low-pass and reverb come from the row; the renderer decides nothing on its own.
- Levels: every event of a kind is set to the same RMS (``LEVELS``, engineering defaults kept under BP-65's caps), music and
  ambience duck under the voice (BP-53's house depth for music, its floor for the bed), each place gets its room tone and its
  room (a cave's impulse response), and a place change carries the plan's J/L bridge.
- AV contract (D-135): every placed row keeps its ``event_id`` into ``events_placed``, and the onset of every effect row is
  measured on the signal the SFX stem receives (``onset_of``), so BP-54's rows of the cue sheet judge the rendered sound.
- ``level_report`` measures, per shot, the background (ambience + sfx) under speech and in the gaps, groups the shots by route
  and compares the groups' medians (BP-186, the creator's "the same level everywhere").
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy import signal

from explainer_engine.audio import acoustics, duck, sfx_library
from explainer_engine.audio.environmental_sound_design import validate_narration_source_file
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import cue_sheet as CS
from explainer_engine.episode import sound_plan as SP
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR_RULES

SR = 48000
# RMS of one event in dBFS before ducking (engineering defaults; BP-65 caps the peaks: effect -8 dB, bed -15 dB)
LEVELS = CS.LEVELS           # one home: episode/cue_sheet.LEVELS
ROOM_TONE_DB = CS.ROOM_TONE_DB
REVERB_WET = {"air": 0.18, "air_far": 0.35}     # an outdoor reflection share for a medium / distant source (engineering)
BED_DUCK_DB = float(SR_RULES.T("BP-53", "depth_db")[0])
MUSIC_DUCK_DB = duck.DEPTH_DB
SPREAD_MAX_DB = float(SR_RULES.T("BP-186", "route_spread_db_max"))
SPEECH_THRESHOLD = 0.02      # the voice's control level where a window counts as speech (duck.duck_gain's default)
# the generator an older preview played per class (audio/foley); since D-136 nothing plays it, a missing take stays silent
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
    a, b = min(a, len(x)), min(b, len(x))          # a row shorter than its fades fades over its whole length
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

    def take(self, row: dict, k: int) -> np.ndarray:
        """The take a cue row names: a library file, or (preview only) the placeholder of its class."""
        aid, cls = str(row["asset_id"]), row.get("class") or "?"
        if aid.startswith("placeholder:"):
            if not self.allow:
                raise ContractError(f"{cls}: a shippable mix never plays a placeholder")
            self.used.append({"class": aid.split(":", 1)[1], "id": None, "status": "placeholder", "why": "placeholder",
                              "played": "silence", "cue_id": row["cue_id"]})
            return np.zeros(SR // 10, np.float32)       # D-136 / OV-56: no procedural sound, a preview stays silent here
        item = self.items.get(aid)
        path = self.root / item["file"] if item else None
        if path is not None and path.is_file():
            x, rate = sfx_library.read_wav(path)
            self.used.append({"class": cls, "id": aid, "status": "library", "cue_id": row["cue_id"]})
            return _resample(x, rate)
        if not self.allow:
            raise ContractError(f"{cls}: library sound {aid} is listed but its file is not here (fetch it from the vault)")
        self.used.append({"class": cls, "id": None, "status": "placeholder", "why": "file not here", "played": "silence",
                          "cue_id": row["cue_id"]})
        return np.zeros(SR // 10, np.float32)

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
        self.used.append({"class": cls, "id": None, "status": "placeholder", "why": src["status"], "played": "silence"})
        return np.zeros(SR // 10, np.float32)


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


PEAK_CEILING = 0.89          # sample peak of a mix before the assembly's own true-peak limiter (about -1 dBFS)
LIMIT_ATTACK_S, LIMIT_RELEASE_S = 0.005, 0.12


def bus_limit(fixed: np.ndarray, bus: np.ndarray, ceiling: float = PEAK_CEILING) -> np.ndarray:
    """A gain envelope (per sample) for ``bus`` so that ``fixed + bus * env`` stays under ``ceiling``: the voice is never
    touched, only the background bus dips where a war cry or a horn would push the sum over (fast attack, slow release),
    instead of scaling the whole mix down for one peak."""
    f = np.abs(fixed).max(axis=1) if fixed.ndim == 2 else np.abs(fixed)
    b = np.abs(bus).max(axis=1) if bus.ndim == 2 else np.abs(bus)
    need = np.ones(len(b), np.float32)
    hot = (f + b) > ceiling
    if not hot.any():
        return need
    need[hot] = np.clip((ceiling - np.minimum(f[hot], ceiling)) / np.maximum(b[hot], 1e-9), 0.0, 1.0)
    # minimum over a short look-ahead window, then a release ramp back to 1 (both vectorised with a block minimum)
    h = max(1, int(LIMIT_ATTACK_S * SR))
    k = len(need) // h + 1
    blk = np.pad(need, (0, k * h - len(need)), constant_values=1.0).reshape(k, h).min(axis=1)
    blk = np.minimum(blk, np.concatenate([blk[1:], [1.0]]))                   # look ahead one block
    rel = np.exp(-h / (LIMIT_RELEASE_S * SR))
    env = np.empty_like(blk)
    cur = 1.0
    for i, v in enumerate(blk):                                                  # one step per 5 ms block: cheap
        cur = v if v < cur else v + (cur - v) * rel
        env[i] = cur
    return np.repeat(env, h)[: len(need)].astype(np.float32)


def _ratio(x: np.ndarray, pitch: float) -> np.ndarray:
    """Play ``x`` at ``pitch`` times its speed (a varispeed: pitch and length change together, BP-57's jitter)."""
    if abs(pitch - 1.0) < 1e-4 or len(x) < 2:
        return x
    n = max(2, int(round(len(x) / pitch)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _lowpass(x: np.ndarray, hz: float | None) -> np.ndarray:
    if not hz or len(x) < 16:
        return x
    sos = signal.butter(2, float(hz), btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def _reverb(x: np.ndarray, kind: str, seed: str) -> np.ndarray:
    if kind == "dry" or not len(x):
        return x
    if kind == "cave":
        return acoustics.convolve(x, acoustics.impulse("cave", acoustics.seed_of(seed), SR))[: len(x)]
    wet = REVERB_WET.get(kind, 0.0)
    if wet <= 0:
        return x
    y = acoustics.convolve(x, acoustics.impulse("outdoor", acoustics.seed_of(seed), SR))[: len(x)]
    return ((1 - wet) * x + wet * y * (_rms(x) / max(1e-9, _rms(y)))).astype(np.float32)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) if len(x) else 0.0


def play_row(row: dict, snd: "Sounds", k: int) -> np.ndarray:
    """One cue row as a stereo signal of exactly its duration: the take, its offset, pitch, loop or trim, level, low-pass,
    reverb, fades and pan (ambience is widened, music sits in the centre)."""
    m = int(round(row["duration_s"] * SR))
    if m <= 0:
        return np.zeros((0, 2), np.float32)
    aid = str(row["asset_id"])
    if aid.startswith("room_tone:"):
        room = aid.split(":", 1)[1]
        x = acoustics.room_tone(room if room in acoustics.KINDS else "outdoor", acoustics.seed_of(row["cue_id"]),
                                m / SR + 0.01, SR)[:m]
    else:
        x = snd.take(row, k)
    x = x[int(round(row.get("asset_offset_s", 0.0) * SR)):]
    x = _ratio(x, float(row.get("pitch", 1.0)))
    if row.get("loop"):
        x = _at_level(_loop(x, m, SR // 4 if row["layer"] != "music" else SR // 2), row["gain_db"])
    else:
        x = _at_level(x, row["gain_db"])[:m]
    x = _lowpass(x, (row.get("eq") or {}).get("lowpass_hz"))
    x = _reverb(x, row.get("reverb", "dry"), row["cue_id"])
    x = _fades(x.copy(), int(row["fade_in_s"] * SR), int(row["fade_out_s"] * SR))
    if row["layer"] == "ambience":
        st = acoustics.widen(x, seed=acoustics.seed_of(row["cue_id"]))[: len(x)]
    elif row["layer"] == "music":
        st = acoustics.pan(x, 0.0) * acoustics.CENTRE_GAIN
    else:
        st = acoustics.pan(x, float(row.get("pan", 0.0)))
    out = np.zeros((m, 2), np.float32)
    out[: min(m, len(st))] = st[:m]
    return out


ONSET_DB = -20.0     # an onset: the first 5 ms window within this of the row's loudest window (the cue sheet's take onset too)


def onset_of(x: np.ndarray, hop_s: float = 0.005) -> float | None:
    """Seconds from a rendered row's start to its onset (stereo or mono), None for silence."""
    m = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    h = max(1, int(hop_s * SR))
    k = len(m) // h
    if k == 0:
        return None
    env = 20 * np.log10(np.sqrt(np.mean(m[: k * h].astype(np.float64).reshape(k, h) ** 2, axis=1)) + 1e-12)
    if env.max() < -80:
        return None
    return float(np.flatnonzero(env >= env.max() + ONSET_DB)[0] * h / SR)


def render(plan: dict, sources: dict, out_dir: Path, *, library_root: Path, narration: Path | None = None,
           shippable: bool = True, sheet: dict | None = None) -> dict:
    """Render the plan into the five stems in ``out_dir`` by playing its cue sheet (``episode/cue_sheet``; built here when
    none is given, validated, written next to the stems). ``shippable=False`` is a preview: a class without a real take stays
    silent (never a procedural sound, D-136), no voice needed, and the report says it cannot ship."""
    ok, why = SP.shippable(sources, plan)
    if shippable and not ok:
        raise ContractError("not shippable: " + "; ".join(why))
    out_dir = Path(out_dir)
    sheet = sheet or CS.build(plan, sources, library_root, allow_placeholder=not shippable)
    gate = CS.write(sheet, plan, out_dir, library_root)
    if shippable:
        CS.require(gate)
    n = int(round(plan["duration_s"] * SR))
    snd = Sounds(sources, library_root, allow_placeholder=not shippable)
    voice, voice_src = _narration(Path(narration) if narration else None, n, shippable)
    stem_of = {"ambience": np.zeros((n, 2), np.float32), "sfx": np.zeros((n, 2), np.float32),
               "music": np.zeros((n, 2), np.float32)}
    layer_stem = {"ambience": "ambience", "foley": "sfx", "spot": "sfx", "transition": "sfx", "music": "music"}
    placed, onsets = [], {}
    for k, row in enumerate(sheet["rows"]):
        if row["layer"] == "narration":
            continue
        i0 = int(round(row["start_s"] * SR))
        if i0 >= n:
            continue
        x = play_row(row, snd, k)
        m = min(len(x), n - i0)
        stem_of[layer_stem[row["layer"]]][i0:i0 + m] += x[:m]
        if row["layer"] in ("foley", "spot", "transition") or (row["layer"] == "ambience" and row["cue_id"].startswith("EV_")):
            on = onset_of(x[:m]) if row["layer"] != "ambience" else None
            if on is not None and row.get("event_id"):
                onsets[row["cue_id"]] = round(row["start_s"] + on, 4)
            placed.append({"shot_id": row["shot_id"], "class": row["class"], "at_s": row["start_s"], "cue_id": row["cue_id"],
                           "event_id": row.get("event_id"), "decision": row.get("decision"), "asset_id": row["asset_id"],
                           "layer": row["layer"], "end_s": row["end_s"],
                           "onset_s": onsets.get(row["cue_id"])})
    amb, sfx, mus = stem_of["ambience"], stem_of["sfx"], stem_of["music"]
    g_mus = duck.duck_gain(voice, SR, n, depth_db=MUSIC_DUCK_DB, threshold=SPEECH_THRESHOLD).astype(np.float32)
    g_bed = duck.duck_gain(voice, SR, n, depth_db=BED_DUCK_DB, threshold=SPEECH_THRESHOLD).astype(np.float32)
    mus *= g_mus[:, None]
    amb *= g_bed[:, None]
    nar = (acoustics.pan(voice, 0.0) * acoustics.CENTRE_GAIN).astype(np.float32)
    env = bus_limit(nar, amb + sfx + mus)[:, None]
    amb, sfx, mus = amb * env, sfx * env, mus * env
    mix = nar + amb + sfx + mus
    peak = float(np.abs(mix).max()) if n else 0.0
    if peak > PEAK_CEILING:                      # only the voice itself can still be over: scale everything once
        k = PEAK_CEILING / peak
        nar, amb, sfx, mus, mix = (s * k for s in (nar, amb, sfx, mus, mix))
    stems = {"narration": nar, "music": mus, "ambience": amb, "sfx": sfx, "mix": mix}
    for name, s in stems.items():
        _write(out_dir / f"{name}.wav", s)
    gate = CS.write(sheet, plan, out_dir, library_root, onsets)   # BP-54 again, now on the rendered onsets
    levels = level_report(plan, voice, amb.mean(axis=1) + sfx.mean(axis=1))
    placeholders = sorted({u["class"] for u in snd.used if u["status"] == "placeholder"})
    return {"schema": "stems_report/1", "shippable": ok and not placeholders and voice_src.startswith("file:")
            and gate["verdict"]["status"] != G.FAIL,
            "narration_source": str(narration) if narration else "none",
            "blocked_era_events": plan.get("blocked_era_events", []), "music_duck_depth_db": MUSIC_DUCK_DB,
            "ambience_duck_depth_db": BED_DUCK_DB,
            "not_shippable_because": why + ([] if voice_src.startswith("file:") else ["no narration"])
            + ([f"cue sheet: {gate['verdict']['failed']}"] if gate["verdict"]["status"] == G.FAIL else []),
            "placeholders": placeholders, "silent_rows": [u["cue_id"] for u in snd.used if u.get("played") == "silence" and u.get("cue_id")],
            "narration": voice_src, "duration_s": plan["duration_s"], "sample_rate_hz": SR,
            "stems": {k: str(out_dir / f"{k}.wav") for k in stems}, "events_placed": placed,
            "bridges": plan["bridges"], "levels": levels, "gates": G.verdict(levels["rows"]),
            "cue_sheet": str(out_dir / "cue_sheet.json"), "cue_gate": {r["gate"]: r["status"] for r in gate["rows"]},
            "coverage": plan.get("coverage", {}), "credits": sheet.get("credits", []), "sounds_used": snd.used,
            "onsets_measured": len(onsets), "cue_rows": gate["rows"], "missing": sheet.get("missing", []),
            "av": plan.get("av")}


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
