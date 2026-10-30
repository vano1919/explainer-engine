"""Voice consistency check (creator 2026-10-16: "from 3:17 almost to the end another voice comes in").

One ElevenLabs v4 generation of the whole Day 1 read (2,917 characters, 223 s) drifted: from about 190 s of the read the
timbre went darker and duller (spectral tilt -25 dB against a median of -21.3 dB, centroid 1,080 Hz against ~1,250 Hz),
which a listener hears as a different actor. Long single generations drift; the fix is chunked reads
(``script.tts_chunks``), and this check finds drift in any read before it is used: windows whose timbre is far from the
read's own median are REVIEW (listen there). numpy only.

P4b adds the channel registry (``config/channel_voices.json``, ``channel_voices/1``) and EL-13: ``check_against`` compares a new
take's timbre windows with the baseline of the voice the registry names, so a take that does not sound like the channel's
voice is found before it is used. The channel narrator is the creator's call (veto line V1): ``register`` replaces it only
with his recorded word.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..core import contracts
from ..core.errors import ContractError

TILT_DB = 3.5      # spectral tilt (2-5 kHz vs < 500 Hz) further than this from the read's median
CENTROID_REL = 0.22  # or a spectral centroid more than 22 % off


def _timbre(seg: np.ndarray, sr: int) -> tuple[float, float] | None:
    """(median spectral centroid, median tilt in dB) of the voiced 40 ms frames; None under 20 voiced frames."""
    n = int(0.04 * sr)
    cents, tilts = [], []
    for i in range(0, len(seg) - n, n):
        fr = seg[i:i + n] * np.hanning(n)
        if np.sqrt((fr ** 2).mean()) < 0.01:
            continue
        sp = np.abs(np.fft.rfft(fr))
        fq = np.fft.rfftfreq(n, 1 / sr)
        cents.append(float((sp * fq).sum() / (sp.sum() + 1e-12)))
        lo, hi = sp[fq < 500].sum(), sp[(fq > 2000) & (fq < 5000)].sum()
        tilts.append(float(20 * np.log10(hi / (lo + 1e-12) + 1e-12)))
    if len(cents) < 20:
        return None
    return float(np.median(cents)), float(np.median(tilts))


def window_features(x: np.ndarray, sr: int, win_s: float = 15.0) -> list[dict]:
    out = []
    for a in range(0, max(1, int(len(x) / sr - win_s / 3)), int(win_s)):
        f = _timbre(x[int(a * sr):int((a + win_s) * sr)], sr)
        if f:
            out.append({"start": float(a), "end": float(min(a + win_s, len(x) / sr)), "centroid": f[0], "tilt_db": f[1]})
    return out


def _outliers(w: list[dict], label: str) -> list[dict]:
    if len(w) < 3:
        return []
    mt = float(np.median([r["tilt_db"] for r in w]))
    mc = float(np.median([r["centroid"] for r in w]))
    found = []
    for r in w:
        dt, dc = r["tilt_db"] - mt, r["centroid"] / mc - 1
        if abs(dt) > TILT_DB or abs(dc) > CENTROID_REL:
            found.append({"rule": "VOICE-1", "severity": "REVIEW", "where": f"{r['start']:.0f}-{r['end']:.0f} s",
                          "detail": f"timbre off {label} median (tilt {dt:+.1f} dB, centroid {dc:+.0%}): listen; "
                                    "a different-sounding voice means re-read this chunk"})
    return found


def check(x: np.ndarray, sr: int, win_s: float = 15.0) -> tuple[list[dict], list[dict]]:
    """(windows, findings). A finding is REVIEW: emotion moves timbre too, so a person listens before a re-read."""
    w = window_features(x, sr, win_s)
    return w, _outliers(w, "the read's")


def check_speakers(x: np.ndarray, sr: int, turns: list[tuple[str, float, float]]) -> tuple[list[dict], list[dict]]:
    """Voiced dialogue (D-45): several voices in one read are not drift. Each speaker's turns ``(speaker, start, end)``
    are compared with that speaker's own median, so a hero whose turn sounds unlike their other turns is found and the
    other voice is not."""
    windows, found = [], []
    for who in dict.fromkeys(t[0] for t in turns):
        w = []
        for _, a, b in (t for t in turns if t[0] == who):
            f = _timbre(x[int(a * sr):int(b * sr)], sr)
            if f:
                w.append({"speaker": who, "start": float(a), "end": float(b), "centroid": f[0], "tilt_db": f[1]})
        windows += w
        found += [dict(r, detail=f"{who}: " + r["detail"]) for r in _outliers(w, f"{who}'s")]
    return windows, found


# -- the channel registry and EL-13 (P4b) -----------------------------------------------------------------------------

REGISTRY = Path(__file__).resolve().parents[2] / "config" / "channel_voices.json"


def registry_errors(doc: dict) -> list[dict]:
    """The registry's findings: the schema (CN-01), then one entry per voice id and at most one channel narrator."""
    found = contracts.errors(doc)
    if found:
        return found
    ids = [v["voice_id"] for v in doc["voices"]]
    found += [{"rule": "CN-01", "severity": "FAIL", "where": f"voices.{i}", "detail": "voice id listed twice"}
              for i in sorted(set(ids)) if ids.count(i) > 1]
    channel = [v["voice_id"] for v in doc["voices"] if v["role"] == "narrator" and v["status"] == "channel"]
    if len(channel) > 1:
        found.append({"rule": "VC-08", "severity": "FAIL", "where": "voices", "detail": f"two channel narrators: {channel}"})
    return found


def load_registry(path: Path | str | None = None) -> dict:
    doc = json.loads(Path(path or REGISTRY).read_text(encoding="utf-8"))
    bad = [f for f in registry_errors(doc) if f["severity"] == "FAIL"]
    if bad:
        raise ContractError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
    return doc


def channel_voice(doc: dict, role: str = "narrator") -> dict | None:
    return next((v for v in doc["voices"] if v["role"] == role and v["status"] == "channel"), None)


WORD_MINUTES = 60  # how long a recorded word stays usable: the window of a protected-config edit and an effort override


def _word_given(ref: str, voice_id: str, root=None) -> bool:
    from ..governance import records
    return records.find("channel_voice", voice_id, ref, minutes=WORD_MINUTES, root=root) is not None


def register(doc: dict, entry: dict, creator_ref: str | None = None, root=None) -> dict:
    """The registry with ``entry`` added or replaced. The channel voice is the creator's call (V1, VC-08). His recorded word
    is needed to make a different voice the channel voice of a role while one stands, to retire or demote the standing one,
    and to change its ``model`` or its ``baseline`` (the model changes how it sounds; the baseline is what EL-13 measures
    drift against, so loosening it would hide drift). ``creator_ref`` is the id of his message and must name a
    ``channel_voice`` record, younger than ``WORD_MINUTES``, in ``jobs/creator_ok.jsonl`` for the voice that becomes the
    channel voice (a replacement) or the standing voice that is changed (``python -m explainer_engine.governance ok
    channel_voice <voice_id> <message id> "<his words>"``). The file is plain JSONL like the other actions' (as strong as
    they are, not tamper-evident), and ``config/channel_voices.json`` is not a protected file: a direct edit still bypasses
    this function. The name, the note and the first channel voice of a role need no
    word. Anything else raises ContractError."""
    new = json.loads(json.dumps(doc))
    ref = creator_ref.strip() if isinstance(creator_ref, str) else None
    if creator_ref is not None and not ref:
        raise ContractError("creator_ref is blank: give the creator's recorded word or none (VC-08)")
    role = entry.get("role", "narrator")
    standing = channel_voice(new, role)
    same = next((v for v in new["voices"] if v["voice_id"] == entry.get("voice_id")), None)
    replaces = entry.get("status") == "channel" and standing is not None and standing["voice_id"] != entry.get("voice_id")
    held = same if same is not None and same["status"] == "channel" else None
    changes = held is not None and any(entry.get(k) != held[k] for k in ("status", "role", "model", "baseline"))
    if replaces or changes:
        what = standing if replaces else held
        if not ref:
            raise ContractError(f"{what['name']} is the channel {what['role']}; only the creator's word changes it (VC-08)")
        vid = entry["voice_id"] if replaces else held["voice_id"]  # a replacement needs the word for the NEW voice
        if not _word_given(ref, vid, root):
            raise ContractError(f"VC-08: no recorded creator word {ref!r} for {vid} in the last {WORD_MINUTES} minutes: record it first "
                                "(`python -m explainer_engine.governance ok channel_voice <voice_id> <message id> \"<his words>\"`)")
    if replaces:
        standing["status"] = "retired"
    new["voices"] = [v for v in new["voices"] if v["voice_id"] != entry.get("voice_id")] + [entry]
    bad = [f for f in registry_errors(new) if f["severity"] == "FAIL"]
    if bad:
        raise ContractError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
    return new


def check_against(x: np.ndarray, sr: int, voice_id: str, registry: dict | None = None,
                  win_s: float = 15.0) -> tuple[list[dict], list[dict]]:
    """EL-13: ``(windows, findings)`` of a take against the registered baseline of ``voice_id``. Every finding is REVIEW
    (emotion moves timbre too): a voice that is not registered, one without a baseline, a take too short to compare, and each
    window whose timbre is further from the baseline than the read-drift limits (``TILT_DB``, ``CENTROID_REL``)."""
    reg = registry if registry is not None else load_registry()
    entry = next((v for v in reg["voices"] if v["voice_id"] == voice_id), None)

    def review(where: str, detail: str) -> dict:
        return {"rule": "EL-13", "severity": "REVIEW", "where": where, "detail": detail}

    if entry is None:
        return [], [review(voice_id, "not in config/channel_voices.json: register it before its takes are compared")]
    base = entry["baseline"]
    if base is None:
        return [], [review(entry["name"], "no baseline recorded: measure its approved first read and register it")]
    windows = window_features(x, sr, win_s)
    if not windows:
        return [], [review(entry["name"], "take too short to compare (under 20 voiced frames)")]
    found = []
    for w in windows:
        dt, dc = w["tilt_db"] - base["tilt_db"], w["centroid"] / base["centroid_hz"] - 1
        if abs(dt) > TILT_DB or abs(dc) > CENTROID_REL:
            found.append(review(f"{w['start']:.0f}-{w['end']:.0f} s",
                                f"timbre off the {entry['name']} baseline ({base['kind']}): tilt {dt:+.1f} dB, centroid {dc:+.0%}: "
                                "listen; a different-sounding voice means re-read this chunk"))
    return windows, found
