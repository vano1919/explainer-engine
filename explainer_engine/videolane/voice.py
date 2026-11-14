"""The voice track of an episode with clip-spoken shots (VL-13, docs/VIDEO_LANE.md): the narrator's read, split where the
clock inserted a clip-timed shot (``timing.inserts``), with each LTX clip's own speech laid on its shot's frames. This one file
is the ``narration`` the stem renderer (``audio/stems.render``) ducks the music and the bed under, so:

* the LTX dialogue is heard once (the read never speaks a clip-spoken line, ``timing.read_order``; this track carries the
  clip's line exactly where its picture is), never twice;
* the bed and the music duck under the dialogue as under the narrator (BP-52: ducking, never muting), and keep running
  across the cuts (the bed belongs to the place, ``episode/sound_plan``);
* every clip's speech is set to the read's speech level (LTX speakers differ by up to 9 dB, W1), and the clip's own track
  between its lines stays in, 15 dB down (``scene_join.BETWEEN_LINES_DB``): LTX's room and effects colour the gap, the bed
  carries it, and each clip's own track fades in and out over BP-191's ``clip_fade_s`` at its cuts.

The sound files belong to the AV thread (``scene_join``, ``stems``); this module only reads their helpers.
"""
from __future__ import annotations

import hashlib
import subprocess
import wave
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

RATE = 48000
CLIP_FADE_S = float(np.mean(SR.T("BP-191", "clip_fade_s")))
SEAM_FADE_S = float(SR.T("BP-188", "seam_fade_s"))   # FA-13: the de-click minimum at every read piece and clip edge
GAIN_MAX_DB = 12.0          # engineering default: a clip quieter than this under the read is a bad take, not a level to fix
# TD-320 (audit, 2026-11-13): one equaliser curve per man from the median long-term spectrum of his own clips, in this track only
EQ_EDGES_HZ = (100, 200, 400, 800, 1600, 3200, 6400, 8000)     # seven octave bands, 100 Hz to 8 kHz (engineering default)
EQ_MAX_DB = 4.0             # every band's correction stays inside this (the audit's bound)
EQ_MIN_CLIPS = 3            # a man with fewer clips has no median worth matching to
EQ_MIN_SPEECH_S = 1.0       # TD-321: under a second of measured speech the curve follows noise, the clip is not measured
# TD-320: a pitch shift only on a clip two estimators and the tracker's own confidence agree on, 2 to 4 semitones from the median
PITCH_MIN_CONF = 0.5
PITCH_AGREE_ST = 1.0
PITCH_SHIFT_MIN_ST = 2.0
PITCH_SHIFT_MAX_ST = 4.0


def read_mono(path: Path, rate: int = RATE) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def write_mono(path: Path, x: np.ndarray, rate: int = RATE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.rint(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())   # rounded: a read's dither survives
    return path


def dither_read(x: np.ndarray, seed: str = "read") -> np.ndarray:
    """TD-329: one 16-bit step of triangular dither (deterministic per ``seed``) on the narrator's read, added where the read is
    loaded as sound. The RC-004 chain leaves pauses under half a step (about -101 dB); the 16-bit conversion turned them into exact
    zero, which ED-12's dropout scan reads as a hole cut into the line. A real recording's room tone does the same job. Only the
    read gets it: every zero the pipeline makes itself (a gap, a missing piece, a pad) stays exact zero, so the gate still finds a
    real hole."""
    rng = np.random.default_rng(int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16))
    d = (rng.random(len(x), dtype=np.float32) - rng.random(len(x), dtype=np.float32)) / 32767
    return (x + d).astype(np.float32)


def _rms_db(x: np.ndarray) -> float:
    return 20 * np.log10(float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) + 1e-9) if len(x) else -120.0


def speech_level(x: np.ndarray, spans, rate: int = RATE) -> float:
    parts = [x[int(a * rate):int(b * rate)] for a, b in spans or []]
    parts = [p for p in parts if len(p)]
    return _rms_db(np.concatenate(parts)) if parts else _rms_db(x)


def _speech_segments(x: np.ndarray, spans, rate: int = RATE) -> np.ndarray:
    segs = [x[int(a * rate):int(b * rate)] for a, b in spans or [] if b - a > 0.15]
    segs = [g for g in segs if len(g)]
    return np.concatenate(segs) if segs else np.zeros(0, np.float32)


def band_shape(x: np.ndarray, spans, rate: int = RATE) -> list[float] | None:
    """The long-term spectrum of the speech inside ``spans`` in ``EQ_EDGES_HZ``'s bands: dB of the mean power per bin, minus
    the mean over the bands (the shape only, the level is the voice track's own business). None when too little speech."""
    y = _speech_segments(x, spans, rate)
    if len(y) < EQ_MIN_SPEECH_S * rate:
        return None
    n, hop = 4096, 2048
    win = np.hanning(n).astype(np.float64)
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    frames = np.stack([y[i:i + n] * win for i in range(0, len(y) - n + 1, hop)])
    power = (np.abs(np.fft.rfft(frames, axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(n, 1 / rate)
    db = []
    for lo, hi in zip(EQ_EDGES_HZ[:-1], EQ_EDGES_HZ[1:]):
        sel = (f >= lo) & (f < hi)
        db.append(10 * np.log10(float(power[sel].mean()) + 1e-12))
    db = np.array(db)
    return [round(float(v), 2) for v in db - db.mean()]


def eq_plan(shapes: dict[str, list[float] | None], speakers: dict[str, str]) -> dict:
    """Per man the median shape of his clips, and per clip the band gains that bring it to that median, each inside
    ``EQ_MAX_DB``. ``shapes``: shot id -> ``band_shape``; ``speakers``: shot id -> the man. A man with fewer than
    ``EQ_MIN_CLIPS`` measured clips is listed as skipped, nothing is changed for him."""
    out = {"bands_hz": [list(b) for b in zip(EQ_EDGES_HZ[:-1], EQ_EDGES_HZ[1:])], "max_db": EQ_MAX_DB, "speakers": {}, "clips": {}}
    for who in sorted(set(speakers.values())):
        ids = [i for i in speakers if speakers[i] == who and shapes.get(i)]
        if len(ids) < EQ_MIN_CLIPS:
            out["speakers"][who] = {"clips": len(ids), "skipped": f"fewer than {EQ_MIN_CLIPS} measured clips"}
            continue
        med = np.median(np.array([shapes[i] for i in ids]), axis=0)
        out["speakers"][who] = {"clips": len(ids), "median_shape_db": [round(float(v), 2) for v in med]}
        for i in ids:
            g = np.clip(med - np.array(shapes[i]), -EQ_MAX_DB, EQ_MAX_DB)
            out["clips"][i] = {"speaker": who, "shape_db": shapes[i], "gain_db": [round(float(v), 2) for v in g]}
    return out


def apply_eq(x: np.ndarray, gain_db: list[float], rate: int = RATE) -> np.ndarray:
    """The band gains as one smooth zero-phase curve (linear in dB over log frequency between the band centres, held flat
    beyond the first and the last), applied in the frequency domain with room for the tail."""
    centres = np.sqrt(np.array(EQ_EDGES_HZ[:-1], float) * np.array(EQ_EDGES_HZ[1:], float))
    n = len(x)
    size = 1 << int(np.ceil(np.log2(n + 8192)))
    f = np.fft.rfftfreq(size, 1 / rate)
    curve = np.interp(np.log(np.maximum(f, 1.0)), np.log(centres), np.asarray(gain_db, float))
    y = np.fft.irfft(np.fft.rfft(x.astype(np.float64), size) * 10 ** (curve / 20), size)[:n]
    return y.astype(np.float32)


def f0_estimates(x: np.ndarray, spans, rate: int = RATE) -> dict | None:
    """Median F0 of the speech inside ``spans`` by two estimators (pyin with its voiced probability, and yin), 60-400 Hz."""
    import librosa
    y = _speech_segments(x, spans, rate)
    if len(y) < EQ_MIN_SPEECH_S * rate:
        return None
    y = librosa.resample(y.astype(np.float32), orig_sr=rate, target_sr=16000)
    f, _vf, vp = librosa.pyin(y, fmin=60, fmax=400, sr=16000, frame_length=1024)
    ok = ~np.isnan(f)
    if not ok.any():
        return None
    keep = ok & (vp >= 0.1)
    yin = librosa.yin(y, fmin=60, fmax=400, sr=16000, frame_length=1024)
    return {"pyin_hz": float(np.median(f[keep])) if keep.any() else None, "pyin_conf": float(np.median(vp[ok])),
            "yin_hz": float(np.median(yin))}


def pitch_plan(measures: dict[str, dict | None], speakers: dict[str, str]) -> dict:
    """TD-320: a clip is shifted only when pyin and yin agree within ``PITCH_AGREE_ST`` semitones, pyin's confidence is at
    least ``PITCH_MIN_CONF``, and the clip is ``PITCH_SHIFT_MIN_ST``..``PITCH_SHIFT_MAX_ST`` semitones from its man's median
    (the median of the clips that pass the first two tests); the shift is that distance, at most the maximum, towards the
    median. Every other clip is listed with the reason, for the owner's ear."""
    st = lambda a, b: 12 * np.log2(a / b)
    rows, reliable = {}, {}
    for i, m in measures.items():
        if not m or not m.get("pyin_hz"):
            rows[i] = {"speaker": speakers.get(i), "shift_st": 0.0, "why": "no F0 measured"}
        elif abs(st(m["pyin_hz"], m["yin_hz"])) > PITCH_AGREE_ST:
            rows[i] = {"speaker": speakers.get(i), "shift_st": 0.0, **m,
                       "why": f"the two estimators disagree by {abs(st(m['pyin_hz'], m['yin_hz'])):.1f} st"}
        elif m["pyin_conf"] < PITCH_MIN_CONF:
            rows[i] = {"speaker": speakers.get(i), "shift_st": 0.0, **m, "why": f"pyin confidence {m['pyin_conf']:.2f} < {PITCH_MIN_CONF}"}
        else:
            reliable.setdefault(speakers.get(i), {})[i] = m
    medians = {who: float(np.median([m["pyin_hz"] for m in ms.values()])) for who, ms in reliable.items()}
    for who, ms in reliable.items():
        for i, m in ms.items():
            d = st(m["pyin_hz"], medians[who])
            if abs(d) < PITCH_SHIFT_MIN_ST:
                rows[i] = {"speaker": who, "shift_st": 0.0, **m, "d_median_st": round(float(d), 2), "why": "inside the 2 st band, left alone"}
            elif abs(d) > PITCH_SHIFT_MAX_ST:
                rows[i] = {"speaker": who, "shift_st": 0.0, **m, "d_median_st": round(float(d), 2),
                           "why": f"{abs(d):.1f} st from the median: more than the {PITCH_SHIFT_MAX_ST:.0f} st bound, left for the owner"}
            else:
                rows[i] = {"speaker": who, "shift_st": round(float(-d), 2), **m, "d_median_st": round(float(d), 2), "why": "shifted"}
    return {"median_hz": {w: round(v, 1) for w, v in medians.items()}, "clips": rows}


def shift_pitch(x: np.ndarray, semitones: float, rate: int = RATE) -> np.ndarray:
    """ffmpeg's rubberband with the formants preserved; the length is kept (tempo 1) and checked to a frame."""
    if not semitones:
        return x
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-", "-af",
                          f"rubberband=pitch={2 ** (semitones / 12):.6f}:formant=preserved", "-f", "f32le", "-"],
                         input=x.astype("<f4").tobytes(), capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype="<f4").astype(np.float32)
    if abs(len(y) - len(x)) > rate // 30:
        raise ContractError(f"the pitch shift moved the clip's length by {len(y) - len(x)} samples")
    return np.pad(y, (0, max(0, len(x) - len(y))))[: len(x)]


def compose(timing: dict, read: Path | None, clip_audio: dict, out: Path, *, read_speech=None, eq_match: bool = True,
            pitch_shifts: dict | None = None) -> dict:
    """Write the voice track. ``clip_audio``: ``{shot_id: {"path": trimmed clip, "speech": [[s, e]], "speaker": the man}}`` for
    every inserted shot. With ``speaker`` on the entries the per-man EQ match (TD-320, ``eq_plan``) is applied to each clip
    before its level is set; ``pitch_shifts`` (shot id -> semitones, from ``pitch_plan``) shifts the listed clips. Returns what
    was laid where (the report the QA reads to prove the line is heard once), with every band gain and every shift."""
    from explainer_engine.production.scene_join import between_lines_gain
    speakers = {sid: c["speaker"] for sid, c in clip_audio.items() if c.get("speaker")}
    eq = None
    if eq_match and speakers:
        shapes = {sid: band_shape(read_mono(Path(clip_audio[sid]["path"])), clip_audio[sid].get("speech")) for sid in speakers}
        eq = eq_plan(shapes, speakers)
    from explainer_engine.production.scene_join import between_lines_gain
    fps = int(timing["fps"])
    total = int(round(timing["total_frames"] / fps * RATE))
    y = np.zeros(total, np.float32)
    x = read_mono(read) if read else np.zeros(0, np.float32)
    ref_db = speech_level(x, read_speech) if len(x) else -20.0
    x = dither_read(x)
    inserts = sorted(timing.get("inserts") or [], key=lambda i: i["at_read_frame"])
    # the read in pieces: read frame r -> episode frame r + (frames inserted before r)
    cuts = [0] + [i["at_read_frame"] for i in inserts] + [None]
    shift, laid = 0, []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        sa = int(round(a / fps * RATE))
        sb = len(x) if b is None else min(len(x), int(round(b / fps * RATE)))
        if sb > sa:
            d = int(round((a + shift) / fps * RATE))
            piece = x[sa:sb][: max(0, total - d)].copy()
            # FA-13 / BP-188: a de-click fade on each edge where the read was split for a clip (never on the read's own ends)
            f = min(len(piece) // 2, int(SEAM_FADE_S * RATE))
            if f and k > 0:
                piece[:f] *= np.linspace(0, 1, f, dtype=np.float32)
            if f and b is not None:
                piece[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
            y[d:d + len(piece)] += piece
            laid.append({"what": "read", "read_s": [round(sa / RATE, 3), round(sb / RATE, 3)],
                         "at_s": round(d / RATE, 3)})
        if k < len(inserts):
            shift += int(inserts[k]["frames"])
    for ins in inserts:
        sid = ins["shot_id"]
        c = clip_audio.get(sid)
        if c is None:
            raise ContractError(f"{sid}: a clip-timed shot without its clip sound")
        start = int(round(timing["shots"][sid]["start_frame"] / fps * RATE))
        n = int(round(int(ins["frames"]) / fps * RATE))
        a = read_mono(Path(c["path"]))[:n]
        if len(a) < n:
            a = np.pad(a, (0, n - len(a)))
        spans = c.get("speech") or []
        eq_row = (eq or {}).get("clips", {}).get(sid)
        if eq_row:
            a = apply_eq(a, eq_row["gain_db"])
        shift_st = float((pitch_shifts or {}).get(sid) or 0.0)
        if shift_st:
            a = shift_pitch(a, shift_st)
        # HF-5 (FL-408, FL-409, TD-306): the clamp holds for boosts only, a clip louder than the read is turned down by
        # whatever it needs; the last speech span runs to the clip's end (the detector can close early on a short line
        # and the end of the line was dropped 15 dB), the level itself is still taken from the spans as detected
        want_db = ref_db - speech_level(a, spans) if spans else 0.0
        gain_db = min(GAIN_MAX_DB, want_db) if spans else 0.0
        boost_clamped = bool(spans and want_db > GAIN_MAX_DB)
        held = [list(sp) for sp in spans]
        if held:
            held[-1][1] = max(held[-1][1], len(a) / RATE)
        a = a * (10 ** (gain_db / 20)) * between_lines_gain(len(a), held, RATE)
        k = min(len(a) // 2, int(max(CLIP_FADE_S, SEAM_FADE_S) * RATE))
        if k:
            r = np.linspace(0, 1, k, dtype=np.float32)
            a[:k] *= r
            a[-k:] *= r[::-1]
        y[start:start + n] += a[: max(0, total - start)]
        laid.append({"what": "clip", "shot_id": sid, "at_s": round(start / RATE, 3), "seconds": round(n / RATE, 3),
                     "gain_db": round(gain_db, 2), "boost_clamped": boost_clamped, "speech": spans,
                     "eq_gain_db": eq_row["gain_db"] if eq_row else None, "pitch_shift_st": shift_st})
    write_mono(out, y)
    peak = float(np.abs(y).max()) if len(y) else 0.0
    return {"path": str(out), "seconds": round(total / RATE, 4), "read_level_db": round(ref_db, 2), "laid": laid,
            "peak_dbfs": round(20 * float(np.log10(peak + 1e-9)), 2),
            "boost_clamped": [l["shot_id"] for l in laid if l.get("boost_clamped")], "eq_match": eq}
