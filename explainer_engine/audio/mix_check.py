"""The final mix check (SP-07, docs/EPISODE_FIRST.md): the five stems of ``audio/stems`` measured as a listener would get them.

* Delivered loudness and true peak: the mix is normalised the way assembly does it (``qa/targets.normalise_file``, BP-50) and
  measured with ffmpeg's ebur128 (ITU-R BS.1770): the numbers the long-form or Shorts profile judges (``profile``, so the spec
  is configurable and lives in the registry, never here).
* Clipping in the rendered mix (samples at full scale) and digital silence (BP-161's -70 dBFS over 10 ms windows) outside the
  stretches the cue sheet declares silent.
* Narration protection: while the narrator speaks, the voice stem against the music and the background (ambience + effects)
  in LU on the same gating (BP-52), and per shot the background's RMS under the voice (a shot where an effect covers a word).

Every row says what it measured; nothing here listens for taste (that is the creator's ear).
"""
from __future__ import annotations

import tempfile
import wave
from pathlib import Path

import numpy as np

from explainer_engine.audio import duck
from explainer_engine.qa import gates as G
from explainer_engine.qa import targets as T
from explainer_engine.standards import sourced_rules as SR_RULES

SR = 48000
CLIP_LEVEL = 0.999
SILENCE_DBFS = float(SR_RULES.T("BP-161", "digital_silence_dbfs"))
SILENCE_WINDOW_MS = float(SR_RULES.T("BP-161", "window_ms"))
COMBINED_UNDER_LU = float(SR_RULES.T("BP-52", "combined_under_lu"))
SPEECH_THRESHOLD = 0.02


def read(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        ch, raw = w.getnchannels(), w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch) if ch > 1 else x[:, None]


def _write(path: Path, x: np.ndarray) -> None:
    x = x if x.ndim == 2 else x[:, None]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def _db(x: np.ndarray) -> float:
    return float(20 * np.log10(max(1e-9, float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))))) if len(x) else -120.0


def speech_mask(voice_mono: np.ndarray) -> np.ndarray:
    lvl = duck.control_level(voice_mono, SR)
    m = np.repeat(lvl > SPEECH_THRESHOLD, int(SR / duck.CTRL_HZ))
    return np.pad(m, (0, max(0, len(voice_mono) - len(m))))[: len(voice_mono)]


def _lufs(x: np.ndarray, d: Path, name: str) -> float | None:
    if len(x) < SR // 2:
        return None
    p = d / f"{name}.wav"
    _write(p, x)
    try:
        v = T.measure_file(p)["lufs"]
    except RuntimeError:
        return None
    return None if v == float("-inf") or v < -69.0 else v


def check(stems_dir: Path, *, plan: dict | None = None, sheet: dict | None = None, profile: str = "long") -> dict:
    stems_dir = Path(stems_dir)
    mix, nar = read(stems_dir / "mix.wav"), read(stems_dir / "narration.wav")
    mus, amb, sfx = read(stems_dir / "music.wav"), read(stems_dir / "ambience.wav"), read(stems_dir / "sfx.wav")
    n = min(len(mix), len(nar), len(mus), len(amb), len(sfx))
    mix, nar, mus, bg = mix[:n], nar[:n], mus[:n], amb[:n] + sfx[:n]
    rows, numbers = [], {}
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        _write(d / "mix.wav", mix)
        meas = T.normalise_file(d / "mix.wav", d / "delivered.wav", profile=profile, channels=2)
        v = T.verdicts(meas, profile)
        numbers["delivered"] = meas
        rows.append(G.row("delivered_loudness", v["loudness_verdict"] == "PASS",
                          f"after the assembly's normalisation: {meas['lufs']} LUFS ({profile} profile, "
                          f"{T.PROFILES[profile]['rule']})", meas["lufs"],
                          level="REVIEW" if v["loudness_verdict"] == "REVIEW" else G.FAIL))
        if "true_peak" in meas:
            rows.append(G.row("delivered_true_peak", v["true_peak_verdict"] == "PASS",
                              f"true peak {meas['true_peak']} dBTP (max {T.PROFILES[profile]['true_peak_max']})",
                              meas["true_peak"], level=SR_RULES.level(T.PROFILES[profile]["rule"])))
        clipped = int(np.sum(np.abs(mix) >= CLIP_LEVEL))
        rows.append(G.row("no_clipping", clipped == 0, f"{clipped} samples at full scale in the rendered mix", clipped))
        sp = speech_mask(nar.mean(axis=1))
        numbers["speech_s"] = round(float(sp.sum()) / SR, 2)
        if sp.sum() >= SR:
            v_l = _lufs(nar[sp], d, "v")
            m_l = _lufs(mus[sp], d, "m")
            b_l = _lufs(bg[sp], d, "b")
            numbers.update(voice_lufs_in_speech=v_l, music_lufs_in_speech=m_l, background_lufs_in_speech=b_l)
            if v_l is None:
                rows.append(G.row("narration_protected", None, "the voice measured nothing under ebur128's gate"))
            else:
                g = T.gaps(v_l, m_l, b_l)
                numbers["gaps_lu"] = {k: round(x, 2) for k, x in g.items()}
                verdict = T.gap_verdict(v_l, m_l, b_l)
                rows.append(G.row("narration_protected", verdict == "PASS",
                                  f"BP-52 under the voice: {numbers['gaps_lu']} LU (music >= "
                                  f"{SR_RULES.T('BP-52', 'music_under_lu')}, bed >= {SR_RULES.T('BP-52', 'bed_under_lu')}, "
                                  f"combined >= {COMBINED_UNDER_LU})", numbers["gaps_lu"].get("combined"),
                                  level=SR_RULES.level("BP-52")))
        else:
            rows.append(G.row("narration_protected", None, "less than one second of speech: nothing to protect or measure"))
        masked = []
        for s in (plan or {}).get("shots", []):
            i0, i1 = int(s["start_s"] * SR), min(n, int((s["start_s"] + s["dur_s"]) * SR))
            m = sp[i0:i1]
            if m.sum() < SR // 4:
                continue
            gap = _db(nar[i0:i1].mean(axis=1)[m]) - _db(bg[i0:i1].mean(axis=1)[m])
            if gap < COMBINED_UNDER_LU - 4.0:      # RMS dB per shot is cruder than LU: 4 dB of slack before a REVIEW
                masked.append({"shot_id": s["shot_id"], "voice_over_background_db": round(gap, 1)})
        numbers["masked_shots"] = masked
        rows.append(G.row("no_masked_shot", not masked if plan else None,
                          f"per shot, the background's RMS under the voice: shots within {COMBINED_UNDER_LU - 4.0:g} dB of "
                          f"the voice {masked[:5]}" if plan else "no plan given: shots not measured", len(masked),
                          level="REVIEW"))
        quiet = set()
        for s in (sheet or {}).get("shots", []):
            if s.get("state") == "INTENTIONAL_SILENCE":
                quiet.add((s["start_s"], s["start_s"] + s["dur_s"]))
        h = int(SR * SILENCE_WINDOW_MS / 1000)
        mono = mix.mean(axis=1)
        k = len(mono) // h
        w = 20 * np.log10(np.sqrt(np.mean(mono[: k * h].astype(np.float64).reshape(k, h) ** 2, axis=1)) + 1e-12)
        dead = [i * h / SR for i in np.flatnonzero(w < SILENCE_DBFS)]
        dead = [t for t in dead if not any(a <= t < b for a, b in quiet)]
        rows.append(G.row("no_digital_silence", not dead, f"{len(dead)} windows of {SILENCE_WINDOW_MS:g} ms under "
                          f"{SILENCE_DBFS:g} dBFS outside a declared silence (first at {dead[:3]})", len(dead),
                          level=SR_RULES.level("BP-161")))
    return {"schema": "mix_check/1", "profile": profile, "rows": rows, "verdict": G.verdict(rows), "numbers": numbers}
