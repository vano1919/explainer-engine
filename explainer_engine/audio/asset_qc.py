"""Technical quality control of a sound before it enters the library (LIB-07, docs/SOUND_LIBRARY.md): what the file is, whether it
decodes, and what it measures. Free and deterministic (ffprobe/ffmpeg + numpy, no model, no network): nothing here judges taste,
so a PASS means "technically usable", never "sounds good" (that is ``review.human``).

``probe(path)``: container facts from ffprobe (format, codec, sample rate, channels, bit depth when the codec has one, duration).
``measure(x, rate)``: peak, clipped samples, RMS, noise floor (10th percentile of 50 ms windows), the dynamic span over it,
DC offset, digital silence share. ``check(...)`` turns them into findings with a status each:

* FAIL: the file does not decode, is empty, or is mostly digital silence;
* REVIEW: clipping (runs of samples at full scale), a high noise floor for a one-shot, a DC offset, a loop whose seam steps
  (BP-58, the registry's own check), a lossy original (MP3/OGG: fine for a bed, noted for a hero sound).

``fingerprint(x, rate)``: a coarse spectral fingerprint (band energies of 0.5 s frames, log, quantised) that two copies of one
recording share even after a resample or a different encoding; ``near_duplicates`` compares fingerprints by correlation over
the best offset. Exact copies are caught earlier by the sha256 of the decoded working copy.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from explainer_engine.audio import sfx_library as L

CLIP_LEVEL = 0.999          # a sample this close to full scale counts as clipped
CLIP_RUN = 3                # ... when at least this many follow each other (a single touch is a peak, not clipping)
SILENCE_DB = -80.0          # a 50 ms window under this is digital silence
DC_MAX = 0.01               # mean sample value over the file above this is a DC offset
NOISE_FLOOR_ONE_SHOT_DB = -45.0   # a one-shot whose quietest windows sit above this carries a noise bed (REVIEW)
LOSSY = {"mp3", "vorbis", "aac", "opus"}
NEAR_DUP_CORR = 0.97        # fingerprints this correlated (over the best offset) are one recording twice


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()[:300]}
    d = json.loads(r.stdout or "{}")
    st = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if st is None:
        return {"ok": False, "error": "no audio stream"}
    bits = st.get("bits_per_raw_sample") or st.get("bits_per_sample") or 0
    return {"ok": True, "format": (d.get("format") or {}).get("format_name"), "codec": st.get("codec_name"),
            "sample_rate": int(st.get("sample_rate") or 0), "channels": int(st.get("channels") or 0),
            "bit_depth": int(bits) or None, "duration_s": round(float((d.get("format") or {}).get("duration") or 0), 3),
            "bytes": int((d.get("format") or {}).get("size") or 0)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _windows_db(x: np.ndarray, rate: int, ms: float = 50.0) -> np.ndarray:
    h = max(1, int(rate * ms / 1000))
    n = (len(x) // h) * h
    if n == 0:
        return np.array([-120.0])
    rms = np.sqrt(np.mean(x[:n].astype(np.float64).reshape(-1, h) ** 2, axis=1))
    return 20 * np.log10(rms + 1e-12)


def _clipped(x: np.ndarray) -> int:
    """Samples inside flat-topped runs at the file's own ceiling: at least ``CLIP_RUN`` samples in a row within 0.1 % of the
    peak, near full scale, that barely change (a decoded MP3 overshooting 1.0 between samples is not clipping; a plateau is)."""
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak < CLIP_LEVEL * 0.98:
        return 0
    still = np.abs(np.diff(x)) < 1e-4
    flat = np.concatenate([[False], still]) | np.concatenate([still, [False]])     # a sample whose neighbour equals it
    hot = (np.abs(x) >= peak * 0.999) & flat
    if not hot.any():
        return 0
    # count samples inside runs of at least CLIP_RUN
    d = np.diff(np.concatenate([[0], hot.astype(np.int8), [0]]))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    lens = ends - starts
    return int(lens[lens >= CLIP_RUN].sum())


def measure(x: np.ndarray, rate: int) -> dict:
    w = _windows_db(x, rate)
    floor = float(np.percentile(w, 10))
    loud = float(np.percentile(w, 95))
    return {"seconds": round(len(x) / rate, 3), "peak_dbfs": round(L.db(float(np.max(np.abs(x))) if len(x) else 0.0), 2),
            "rms_dbfs": round(L.db(float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))) if len(x) else -120.0, 2),
            "noise_floor_db": round(floor, 2), "dynamic_span_db": round(loud - floor, 2),
            "clipped_samples": _clipped(x), "dc_offset": round(float(np.mean(x)) if len(x) else 0.0, 5),
            "silence_share": round(float(np.mean(w < SILENCE_DB)), 3)}


def check(original: dict, raw_measure: dict, *, kind: str, stored: np.ndarray | None = None, rate: int = 48000,
          item_id: str = "?") -> dict:
    """Findings and the overall status (FAIL > REVIEW > PASS) for one sound: ``original`` from ``probe``, ``raw_measure``
    from ``measure`` on the decoded original, ``stored`` the working copy (BP-58 seam check for a loop)."""
    findings = []

    def add(status, what):
        findings.append({"status": status, "detail": what})

    if not original.get("ok"):
        add("FAIL", f"does not decode: {original.get('error')}")
    else:
        if raw_measure["seconds"] <= 0.05:
            add("FAIL", "empty or shorter than 50 ms")
        if raw_measure["silence_share"] > 0.8:
            add("FAIL", f"{raw_measure['silence_share']:.0%} of the file is digital silence")
        if raw_measure["clipped_samples"]:
            add("REVIEW", f"{raw_measure['clipped_samples']} clipped samples (runs of {CLIP_RUN}+ at full scale)")
        if abs(raw_measure["dc_offset"]) > DC_MAX:
            add("REVIEW", f"DC offset {raw_measure['dc_offset']:+.4f}")
        if kind == "one_shot" and raw_measure["noise_floor_db"] > NOISE_FLOOR_ONE_SHOT_DB:
            add("REVIEW", f"noise floor {raw_measure['noise_floor_db']:.1f} dBFS under a one-shot (a bed is heard with it)")
        if original.get("codec") in LOSSY:
            add("INFO", f"lossy original ({original['codec']}): fine under a bed, noted for a hero sound")
    if stored is not None and kind == "loop":
        for f in L.check_seams({"id": item_id, "kind": "loop"}, stored, rate):
            add("REVIEW", f["detail"])
    order = {"FAIL": 3, "REVIEW": 2, "INFO": 1}
    status = max((f["status"] for f in findings), key=lambda s: order[s], default="PASS")
    return {"status": "PASS" if status == "INFO" else status, "findings": findings}


def fingerprint(x: np.ndarray, rate: int, frame_s: float = 0.5, bands: int = 12) -> np.ndarray:
    """Log band energies per 0.5 s frame (bands spaced logarithmically 80 Hz-8 kHz), each frame mean-removed."""
    h = int(frame_s * rate)
    n = len(x) // h
    if n == 0:
        return np.zeros((1, bands), np.float32)
    frames = x[: n * h].reshape(n, h) * np.hanning(h)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    freqs = np.fft.rfftfreq(h, 1 / rate)
    edges = np.geomspace(80, min(8000, rate / 2 - 1), bands + 1)
    e = np.stack([spec[:, (freqs >= a) & (freqs < b)].sum(axis=1) for a, b in zip(edges, edges[1:])], axis=1)
    f = np.log10(e + 1e-12)
    return (f - f.mean(axis=1, keepdims=True)).astype(np.float32)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Best correlation of two fingerprints over every offset of the shorter inside the longer (one recording cut twice)."""
    if len(a) > len(b):
        a, b = b, a
    if len(a) < 2:
        return 0.0
    va = a.ravel() - a.mean()
    best = -1.0
    for off in range(0, len(b) - len(a) + 1):
        vb = b[off:off + len(a)].ravel()
        vb = vb - vb.mean()
        d = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if d > 0:
            best = max(best, float(va @ vb) / d)
    return best


def near_duplicates(prints: dict[str, np.ndarray], threshold: float = NEAR_DUP_CORR) -> list[dict]:
    ids = sorted(prints)
    out = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            s = similarity(prints[a], prints[b])
            if s >= threshold:
                out.append({"a": a, "b": b, "similarity": round(s, 3)})
    return out
