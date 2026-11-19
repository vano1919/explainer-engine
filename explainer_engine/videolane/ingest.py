"""LTX clips into the episode (VL-07, VL-11, docs/VIDEO_LANE.md): every generated clip is kept whole (``production/video/raw``,
sha256 pinned, never overwritten), cut to its edit by its MEASURED speech, normalised to the episode's rate, and recorded in
``production/video/<shot>.json``: the record the runner's clips stage (G7) reads for a ``video`` shot (``run._wan_clip``).

Before this module no code wrote that record for an LTX clip, so the runner could not take an LTX clip at all (the
2026-11-12 battle and love scenes were joined by hand, outside the runner).

The edit of one clip:

* spoken clip: in = the first word minus a head lead (BP-190; never past the first word, the first word is never cut), widened
  to the shot's ``head_handle_s`` when the clip has it; out = the last word plus the tail (BP-190's band, at least the shot's
  ``tail_handle_s``). LTX starts a line about 0.75 s in, so this is where the dead head goes.
* silent clip: in = its head handle (LTX's first settling frames), out = in + its planned length (the tail handle stays in
  the raw clip for the editor).
* continuation hand-over (VL-05): when the next clip was generated from frame k of this one, this clip ends ON frame k and
  the next clip drops its frame 0 (the same picture), so the action runs on across the cut without a repeated frame.
* the clip's frame rate is normalised to the episode's (a 30 fps clip on a 24 fps episode is resampled by ffmpeg ``fps``,
  the sound is cut by the same seconds so nothing drifts).

The trimmed clip's speech spans (trimmed seconds) are the clip-timed clock's input (``episode/timing.retime_with_clips``).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

SCHEMA = "video_clip_record/1"
BP201_HEAD_LEAD_S = float(SR.T("BP-201", "head_lead_s"))
BP201_TAIL_MIN_S = float(SR.T("BP-201", "reaction_tail_min_s"))
BP201_TAIL_TARGET_S = float(SR.T("BP-201", "reaction_tail_target_s"))
HEAD_LEAD = [float(SR.T("BP-190", "head_lead_s")[0]), BP201_HEAD_LEAD_S]
CUT_TAIL = [BP201_TAIL_MIN_S, BP201_TAIL_TARGET_S]
SPEECH_TAIL_S = float(SR.T("BP-187", "speech_tail_s"))   # a spoken line ends inside its clip with this much after it


def resolve_reaction_tail_s(edit_plan: dict | None = None, reaction_tail_s: float | None = None) -> float:
    """Single BP-201 reaction-tail rule shared by ingest.edit_points and ingest.whisper_edit_points."""
    ep = edit_plan or {}
    raw_target = (
        float(reaction_tail_s)
        if reaction_tail_s is not None
        else float(ep.get("tail_handle_s", BP201_TAIL_TARGET_S))
    )
    return max(float(CUT_TAIL[0]), min(float(CUT_TAIL[1]), raw_target))


def build_trim_contract(rec_or_pts: dict, shot_id: str = "") -> dict:
    in_s = float(rec_or_pts.get("in_s", rec_or_pts.get("in", 0.0)))
    out_s = float(rec_or_pts.get("out_s", rec_or_pts.get("out", 0.0)))
    frames = int(rec_or_pts.get("frames", 0))
    sid = shot_id or str(rec_or_pts.get("shot_id") or "")
    return {
        "shot_id": sid,
        "in_s": round(in_s, 4),
        "out_s": round(out_s, 4),
        "trim_duration_s": round(max(0.0, out_s - in_s), 4),
        "frames": frames,
        "clip_path": str(rec_or_pts.get("clip_path") or (f"production/video/cut/{sid}.mp4" if sid else "")),
        "clip_sha256": str(rec_or_pts.get("clip_sha256") or ""),
        "head_lead_min_s": BP201_HEAD_LEAD_S,
        "reaction_tail_min_s": BP201_TAIL_MIN_S,
        "reaction_tail_target_s": BP201_TAIL_TARGET_S,
        "single_trimmed_source": True,
    }


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,avg_frame_rate,nb_frames,duration",
                          "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True,
                         check=True).stdout
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise ContractError(f"{Path(path).name}: no video stream")
    fps = Fraction(v.get("avg_frame_rate") or "0/1")
    dur = float(v.get("duration") or d.get("format", {}).get("duration") or 0)
    return {"fps": float(fps) if fps else 0.0, "duration": dur, "has_audio": a is not None,
            "audio_duration": float(a.get("duration") or 0) if a else 0.0}


def speech(path: Path) -> list[tuple[float, float]]:
    """Where the clip's own sound speaks (``qa/sound_realism.speech_spans``, the gate's own detector, so the trim and the
    final-file gate agree)."""
    from explainer_engine.qa import sound_realism as R
    x = R.read_audio(path)
    return [(float(a), float(b)) for a, b in R.speech_spans(x)] if len(x) else []


# TD-323 (audit, 2026-11-13): the speech detector can close a span early (a sung or held last word); when the sound after the
# planned out point is still this close to the last span's own level, the cut goes on until it has fallen this far below it
# (or the raw clip ends). Both numbers are engineering defaults.
LATE_SOUND_WITHIN_DB = 6.0
LATE_SOUND_FALL_DB = 12.0
LATE_SOUND_STEP_S = 0.04


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def matched_word_spans(words: list[dict], line_text: str, gap_s: float = 0.35) -> list[tuple[float, float]]:
    """TD-327 (audit, 2026-11-13): the time spans of the heard words (the local Whisper's, ``{text, start, end}``) that match
    the shot's own script line, in order (``difflib`` over the lower-cased word tokens), joined where less than ``gap_s``
    apart. A word the line does not hold (a misheard "You", an extra word) is never in them. ``gap_s`` is an engineering default."""
    heard = [(_tokens(w.get("text"))[:1] or [""])[0] for w in words]
    want = _tokens(line_text)
    blocks = difflib.SequenceMatcher(None, want, heard, autojunk=False).get_matching_blocks()
    spans: list[tuple[float, float]] = []
    for _a, b, size in blocks:
        for k in range(b, b + size):
            if heard[k]:
                spans.append((float(words[k]["start"]), float(words[k]["end"])))
    spans.sort()
    out: list[tuple[float, float]] = []
    for a, b in spans:
        if out and a - out[-1][1] < gap_s:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _local_words(path: Path) -> list[dict] | None:
    """The local Whisper's words of a clip, or None when faster-whisper is not installed (it is optional: the detector's spans
    alone are then used, and the record says so)."""
    try:
        from explainer_engine.audio import local_words as LW
    except ImportError:
        return None
    try:
        return LW.transcribe(path)["words"]
    except ImportError:
        return None


TRIM_WINDOW_S = 0.02
TRIM_BELOW_DB = 20.0       # engineering default: a word's span keeps the windows within this of its own loudest window


def _trim_to_sound(span: tuple, audio, rate: int) -> tuple | None:
    """The local Whisper times a word from the end of the one before it, so a first word can start seconds before any sound
    (S05_SH019: 0.0 s for a word at 2.4 s). The span is cut back to the 20 ms windows within ``TRIM_BELOW_DB`` of its own
    loudest window; None when it holds no sound at all."""
    a, b = int(span[0] * rate), int(min(span[1] * rate, len(audio)))
    win = int(TRIM_WINDOW_S * rate)
    if b - a < win:
        return None
    lv = [_rms_db(audio[i:i + win]) for i in range(a, b - win + 1, win)]
    top = max(lv)
    if top <= -70.0:
        return None
    keep = [i for i, v in enumerate(lv) if v >= top - TRIM_BELOW_DB]
    return (round(span[0] + keep[0] * TRIM_WINDOW_S, 3), round(span[0] + (keep[-1] + 1) * TRIM_WINDOW_S, 3))


# --- Step 1.2 (V4.1, D-139, MA-06): one trim rule from the clip's own sound -------------------------------------------------
# `qa/sound_realism.speech_spans` is band energy against percentiles, not a voice detector, so it cannot tell a gunshot or loud
# steady ambience from speech. A word counts only where a VOICING classifier hears a voice: Silero VAD through faster-whisper when
# it is installed, else a harmonicity check (normalised autocorrelation peak in the pitch range). The record says which ran.
# All numbers are engineering defaults (D-59), chosen on synthetic voices, gunshots and ambience in tests/unit/test_trim_rule.py.
VOICE_FRAME_S = 0.03
VOICE_HOP_S = 0.01
VOICE_F0_HZ = (70.0, 400.0)
VOICE_MIN_PERIODICITY = 0.5   # normalised autocorrelation peak of a voiced frame
VOICE_GAP_S = 0.25            # voiced runs closer than this are one span (consonants, breaths)
VOICE_MIN_RUN_S = 0.09
VOICE_MIN_HIGH_SHARE = 0.015  # share of a frame's power above 1 kHz: a voice has formants there, a low boom or low wind has none
VOICE_PURE_PERIODICITY = 0.78  # ...unless the frame is as periodic as a held note (a sung or held word has few upper partials)
VOICE_FLOOR_DBFS = -62.0      # nothing quieter is a voice
VOICE_BELOW_PEAK_DB = 45.0    # nor anything this far under the clip's loudest frames
WORD_MIN_VOICED_S = 0.08      # a word needs this much voiced time inside its own span (or half its length when shorter)
MUTE_TAIL_AFTER_S = 0.25
# Silero options, recorded so the numbers can be reproduced: faster-whisper's default speech_pad_ms=400 widens every span by 0.4 s
# of silence on each side (S06_SH008 spans ran 0.00-1.10 over a line heard at 0.19-0.63), and padding is not voiced, so it is 0.
SILERO_VAD_OPTIONS = {"threshold": 0.5, "min_silence_duration_ms": int(VOICE_GAP_S * 1000), "speech_pad_ms": 0}
HALLUCINATED_TAIL_TOKENS = {"you", "you.", "thank", "thanks", "bye"}


def harmonic_voiced_spans(audio, rate: int) -> list[tuple[float, float]]:
    """Voiced spans (seconds) by periodicity: frames whose normalised autocorrelation peaks at a pitch lag (70-400 Hz) above
    ``VOICE_MIN_PERIODICITY`` and are loud enough, joined across ``VOICE_GAP_S``, runs under ``VOICE_MIN_RUN_S`` dropped."""
    x = np.asarray(audio, np.float64)
    n, hop = int(VOICE_FRAME_S * rate), int(VOICE_HOP_S * rate)
    if len(x) < n or n < 8:
        return []
    starts = np.arange(0, len(x) - n + 1, hop)
    frames = np.stack([x[i:i + n] for i in starts]) * np.hanning(n)
    db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9)
    gate = max(VOICE_FLOOR_DBFS, float(np.percentile(db, 95)) - VOICE_BELOW_PEAK_DB)
    spec = np.fft.rfft(frames, 2 * n, axis=1)
    ac = np.fft.irfft(spec * np.conj(spec), axis=1)[:, :n]
    lo, hi = int(rate / VOICE_F0_HZ[1]), min(int(rate / VOICE_F0_HZ[0]), n - 1)
    r = ac[:, lo:hi + 1].max(axis=1) / (ac[:, 0] + 1e-12)
    power = np.abs(spec) ** 2
    high = power[:, np.fft.rfftfreq(2 * n, 1.0 / rate) >= 1000.0].sum(axis=1) / (power.sum(axis=1) + 1e-12)
    voiced = (r >= VOICE_MIN_PERIODICITY) & (db >= gate) & ((high >= VOICE_MIN_HIGH_SHARE) | (r >= VOICE_PURE_PERIODICITY))
    runs: list[list[float]] = []
    for i in np.flatnonzero(voiced):
        a, b = (starts[i] + (n - hop) / 2) / rate, (starts[i] + (n + hop) / 2) / rate   # the frame's centre hop: no smear of 30 ms
        if runs and a - runs[-1][1] <= VOICE_GAP_S:
            runs[-1][1] = b
        else:
            runs.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in runs if b - a >= VOICE_MIN_RUN_S]


def _silero_voiced_spans(audio, rate: int) -> list[tuple[float, float]] | None:
    """Silero VAD through faster-whisper (an optional dependency, like ``audio/local_words``); None when it is not there."""
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except Exception:
        return None
    x = np.asarray(audio, np.float32)
    if rate != 16000 and len(x):
        x = np.interp(np.arange(0, len(x) * 16000 / rate), np.arange(len(x)) * 16000 / rate, x).astype(np.float32)
    try:
        ts = get_speech_timestamps(x, VadOptions(**SILERO_VAD_OPTIONS), sampling_rate=16000)
    except Exception:
        return None
    return [(round(t["start"] / 16000, 3), round(t["end"] / 16000, 3)) for t in ts]


def voiced_spans(audio, rate: int) -> tuple[list[tuple[float, float]], str]:
    """``(spans, detector)``: Silero VAD when installed, else the harmonicity check; ``detector`` names the one that ran."""
    sil = _silero_voiced_spans(audio, rate)
    if sil is not None:
        return sil, "silero_vad"
    return harmonic_voiced_spans(audio, rate), "harmonicity"


def _wtext(w: dict) -> str:
    return str(w.get("text", w.get("word", "")))


def drop_word_artifacts(words: list[dict], audio=None, rate: int = 16000, notes: list | None = None) -> tuple[list[dict], float | None]:
    """The two word-only filters, in one place for the ingest cut and ``whisper_edit_points``: a duplicate opening word more than
    0.8 s before its repeat, and a trailing hallucinated token after a 0.45 s gap ("You"). Returns the words and the
    ``mute_tail_from_s`` of a dropped tail token (else None). The duplicate is dropped ONLY when no voice is heard under it:
    S06_SH008's two "Maybe." are two soldiers, both voiced (G1 + the creator's listen), and the first is a real line. Without
    audio the duplicate cannot be judged and is kept (never dropped on the words alone); ``notes`` receives the REVIEW item."""
    ws = list(words)
    mute_at = None
    if len(ws) >= 2:
        w0, w1 = (re.sub(r"\W+", "", _wtext(w).lower()) for w in ws[:2])
        if w0 and w0 == w1 and float(ws[1].get("start", 0.0)) - float(ws[0].get("end", 0.0)) > 0.8:
            a, b = float(ws[0].get("start", 0.0)), float(ws[0].get("end", 0.0))
            if audio is not None and len(audio):
                voiced, _ = voiced_spans(audio, rate)
                have = sum(min(b, vb) - max(a, va) for va, vb in voiced if min(b, vb) > max(a, va))
            else:
                have = None
            if have is not None and have + 1e-9 < min(WORD_MIN_VOICED_S, 0.5 * max(b - a, 0.0)):
                ws = ws[1:]                         # unvoiced: a transcript artifact
            elif notes is not None:
                notes.append({"kind": "duplicate_opening_word_kept", "text": _wtext(ws[0]), "start": a, "end": b,
                              "why": "a voice is heard under it" if have is not None else "no audio to check it against",
                              "review": "the clip has one more spoken line than the script's text; the creator decides"})
    if len(ws) >= 2:
        last = re.sub(r"\W+", "", _wtext(ws[-1]).lower())
        if last in HALLUCINATED_TAIL_TOKENS and float(ws[-1].get("start", 0.0)) - float(ws[-2].get("end", 0.0)) >= 0.45:
            mute_at = round(float(ws[-2].get("end", 0.0)) + MUTE_TAIL_AFTER_S, 3)
            ws = ws[:-1]
    return ws, mute_at


def accept_voiced_words(words: list[dict], audio, rate: int) -> dict:
    """Words kept only where a voice is heard, their times clamped to the voiced span they overlap (Whisper's raw start is never
    kept: S03_SH007 "Oh, my God" dated 0.00 s over a floor whose only event is at 2.4 s). A word with less voiced time than
    ``WORD_MIN_VOICED_S`` (or half its length) is rejected with its reason. ``{detector, voiced, kept, rejected}``."""
    voiced, detector = voiced_spans(audio, rate) if audio is not None and len(audio) else ([], "none")
    kept, rejected = [], []
    for w in words:
        a, b = float(w.get("start", 0.0)), float(w.get("end", 0.0))
        hits = [(max(a, va), min(b, vb)) for va, vb in voiced if min(b, vb) > max(a, va)]
        have = sum(y - x for x, y in hits)
        if detector == "none" or have + 1e-9 < min(WORD_MIN_VOICED_S, 0.5 * max(b - a, 0.0)) or not hits:
            rejected.append({"text": _wtext(w), "start": a, "end": b, "why": "no voice heard under the word" if detector != "none"
                             else "no audio to check the word against"})
            continue
        kept.append(dict(w, start=round(hits[0][0], 3), end=round(hits[-1][1], 3), raw_start=a, raw_end=b))
    return {"detector": detector, "voiced": voiced, "kept": kept, "rejected": rejected}


def trim_decision(spans: list, words: list[dict] | None, line_text: str | None, *, spoken: bool, dur: float,
                  audio=None, rate: int = 16000) -> dict:
    """The one trim rule (Step 1.2): ``{spans, mute_tail_from_s, detector, rejected}``. The detector's spans plus the matched
    words that a voice supports (clamped to the voiced span); the word-only artifact filters run first. Without audio the words
    cannot be checked: ``detector`` is "none" and no word is added (it is never guessed from words alone)."""
    base = [tuple(sp) for sp in spans]
    if not spoken or not words or not line_text:
        return {"spans": base, "mute_tail_from_s": None, "detector": "n/a", "rejected": [], "notes": []}
    notes: list = []
    clean, mute_at = drop_word_artifacts(words, audio, rate, notes)
    acc = accept_voiced_words(clean, audio, rate)
    if acc["detector"] == "none":
        return {"spans": base, "mute_tail_from_s": mute_at, "detector": "none", "rejected": acc["rejected"], "notes": notes}
    extra = [(a, min(dur, b)) for a, b in matched_word_spans(acc["kept"], line_text)]
    extra = [t for t in (_trim_to_sound(e, audio, rate) for e in extra) if t]
    out: list[tuple[float, float]] = []
    for a, b in sorted(base + extra):
        if out and a <= out[-1][1] + 1e-9:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    if mute_at is None and acc["kept"] and any(r["start"] >= float(acc["kept"][-1]["end"]) for r in acc["rejected"]):
        mute_at = round(float(acc["kept"][-1]["end"]) + MUTE_TAIL_AFTER_S, 3)   # a word heard after the last voiced one is not speech
    return {"spans": out, "mute_tail_from_s": mute_at, "detector": acc["detector"], "rejected": acc["rejected"], "notes": notes}


def speech_with_words(spans: list, words: list[dict] | None, line_text: str | None, *, spoken: bool, dur: float,
                      audio=None, rate: int = 16000) -> list:
    """TD-327: the detector's spans plus the matched word spans that a voice supports (``trim_decision``), for a clip-spoken
    shot only (a silent clip is cut exactly as before), merged where they touch, never past the clip's own length. Without
    ``audio`` the words are used as the local Whisper dated them (the old behaviour; callers with a file always pass audio)."""
    if audio is None and spoken and words and line_text:
        extra = [(a, min(dur, b)) for a, b in matched_word_spans(words, line_text)]
        both = sorted([tuple(sp) for sp in spans] + extra)
        out: list[tuple[float, float]] = []
        for a, b in both:
            if out and a <= out[-1][1] + 1e-9:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
        return out
    return trim_decision(spans, words, line_text, spoken=spoken, dur=dur, audio=audio, rate=rate)["spans"]


def _rms_db(x) -> float:
    return float(20 * np.log10(float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) + 1e-9)) if len(x) else -120.0


def late_sound_out(t_out: float, dur: float, last_span: tuple, audio, rate: int) -> float:
    """TD-323: the out point (seconds) moved on past ``t_out`` when the loudest 100 ms of the half second after it is within
    ``LATE_SOUND_WITHIN_DB`` of the last span's own level, to the end of the first 40 ms window that is ``LATE_SOUND_FALL_DB``
    under that level, else to the clip's end. Unchanged for a quiet tail."""
    a, b = int(last_span[0] * rate), int(last_span[1] * rate)
    ref = _rms_db(audio[a:b])
    if ref <= -80.0 or t_out >= dur:
        return t_out
    step, t = int(LATE_SOUND_STEP_S * rate), t_out
    # the loudest 100 ms window of the half second after the planned out point (a mean over the half second would let the
    # decay at its far end hide a held note: S03_SH003 measured 8.4 dB under the span on the mean, 5.6 dB on the window)
    after = audio[int(t_out * rate):int(min(dur, t_out + 0.5) * rate)]
    win = int(0.1 * rate)
    loud = max((_rms_db(after[i:i + win]) for i in range(0, max(1, len(after) - win + 1), step)), default=-120.0)
    if loud < ref - LATE_SOUND_WITHIN_DB:
        return t_out
    while t < dur:
        w = audio[int(t * rate):int(t * rate) + step]
        if len(w) and _rms_db(w) < ref - LATE_SOUND_FALL_DB:
            return round(min(dur, t + LATE_SOUND_STEP_S), 4)
        t += LATE_SOUND_STEP_S
    return dur


def edit_points(dur: float, spans: list, edit_plan: dict | None, planned_s: float, fps: int, *, spoken: bool,
                handover_s: float | None = None, drop_first: bool = False, shot_id: str = "?", audio=None, rate: int = 16000) -> dict:
    """The in and out points (clip seconds, on whole frames) of one clip; see the module text.

    A hand-over frame (VL-05) before the last speech end + BP-187's tail would cut the line: a ContractError (repair class C,
    regenerate the clip or move the hand-over), never a silent cut (Fable audit FA-07)."""
    ep = edit_plan or {}
    fr = 1.0 / fps
    if handover_s is not None and spans:
        s_end = float(spans[-1][1])
        if handover_s + 1e-9 < s_end + SPEECH_TAIL_S:
            raise ContractError(f"{shot_id}: the hand-over frame at {handover_s:.3f} s lies before the speech end {s_end:.3f} s "
                                f"+ BP-187's {SPEECH_TAIL_S:g} s tail: the cut would clip the line (class C: regenerate the "
                                "clip or pick a later hand-over frame, FA-07)")
    if spoken:
        if not spans:
            raise ContractError("a spoken clip with no speech in its own sound (LTX dropped the line?): regenerate or "
                                "re-plan; nothing is trimmed blind")
        s0, s1 = spans[0][0], spans[-1][1]
        lead = max(HEAD_LEAD[1], float(ep.get("head_handle_s", 0.0)))
        t_in = max(0.0, s0 - lead)
        reaction_tail = resolve_reaction_tail_s(ep)
        t_out = min(dur, s1 + reaction_tail)
        if audio is not None and handover_s is None:
            t_out = late_sound_out(t_out, dur, spans[-1], audio, rate)   # TD-323: a last word the detector closed early
    else:
        t_in = min(float(ep.get("head_handle_s", 0.0)), max(0.0, dur - planned_s))
        t_out = min(dur, t_in + planned_s) if planned_s > 0 else dur
    if drop_first:
        t_in = max(t_in, fr)
    if handover_s is not None:
        t_out = min(dur, handover_s + fr)            # end ON the hand-over frame (VL-05)
    f_in, f_out = int(t_in * fps + 1e-6), int(round(t_out * fps))
    if spoken and f_in / fps > spans[0][0] - HEAD_LEAD[0] + 1e-6 and spans[0][0] >= HEAD_LEAD[0]:
        f_in = max(0, int((spans[0][0] - HEAD_LEAD[0]) * fps))   # the first word is never cut
    if f_out - f_in < 1:
        raise ContractError(f"the edit leaves {f_out - f_in} frame(s) of a {dur:.2f} s clip")
    return {"in_s": round(f_in / fps, 4), "out_s": round(f_out / fps, 4), "frames": f_out - f_in}


def cut(raw: Path, out: Path, in_s: float, frames: int, fps: int, gain_db: float = 0.0) -> Path:
    """The trimmed clip: picture resampled to ``fps`` and cut to ``frames``, the sound cut by the same seconds. ``gain_db``
    (HF-4, a level trim, never a boost) is a ``volume`` filter in front of the pad and the trim; the raw file is not touched."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    dur = frames / fps
    # read two frames more than the edit: the fps filter's rounding can otherwise drop the last frame (seen on CI's
    # ffmpeg with a 30 fps clip on a 24 fps episode); -frames:v caps the picture, atrim the sound
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{in_s:.4f}", "-i", str(raw), "-t", f"{dur + 2.0 / fps:.4f}",
           "-vf", f"fps={fps}", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", (f"volume={gain_db:.3f}dB," if gain_db else "") + f"apad,atrim=0:{dur:.4f}", str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True)
    got = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(tmp)], capture_output=True, text=True,
                         check=True).stdout.strip()
    if int(got or 0) != frames:   # the record must say what the file holds (the assembler refuses a short clip)
        tmp.unlink(missing_ok=True)
        raise ContractError(f"{Path(raw).name}: the cut has {got} frames, the edit {frames} (from {in_s:.3f} s)")
    tmp.replace(out)
    return out


def _level_trim(metrics: dict, finds: list[dict]) -> tuple[float, float | None]:
    """HF-4: ``(trim in dB, true peak before)`` for a cut that has a CLIP-06 finding that is not PASS: 2 dB, or the excess over
    BP-50's ceiling plus 1 dB when that is more; ``(0.0, None)`` for a cut that is under the ceiling."""
    from explainer_engine.qa import targets
    if not any(f.get("rule") == "CLIP-06" and (f.get("status") or f.get("severity")) != "PASS" for f in finds):
        return 0.0, None
    peak = (metrics.get("audio") or {}).get("true_peak")
    if peak is None:
        return 0.0, None
    return -max(2.0, float(peak) - float(targets.PROFILES["long"]["true_peak_max"]) + 1.0), float(peak)


def ingest_scene(root: Path, script: dict, clips: list[dict], fps: int, *, backend: str = "ltx", words_fn=None) -> list[dict]:
    """Ingest one scene's clips. ``clips``: in cut order, ``[{shot_id, path, chain_from_frame?: {frame}}]`` (the worker's rows
    with the downloaded file). Writes the raw copy, the trimmed clip and the record of each; returns the records."""
    from explainer_engine.training import video_qa as VQ
    from explainer_engine.videolane import plan as P
    root = Path(root)
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    spoken = P.clip_spoken(script)
    vdir = root / "production" / "video"
    pics_p = root / "production" / "pictures.json"
    try:
        pictures = json.loads(pics_p.read_text(encoding="utf-8")).get("pictures") if pics_p.is_file() else None
    except (OSError, ValueError):
        pictures = None
    out = []
    comparisons: dict[str, dict] = {}
    for k, c in enumerate(clips):
        sid = c["shot_id"]
        if sid not in by:
            raise ContractError(f"{sid}: a clip for a shot the script does not have")
        shot = by[sid]
        src = Path(c["path"])
        raw = vdir / "raw" / f"{sid}.mp4"
        raw.parent.mkdir(parents=True, exist_ok=True)
        if raw.exists() and _sha(raw) != _sha(src):
            raise ContractError(f"{sid}: production/video/raw/{sid}.mp4 holds another clip; the raw evidence is never "
                                "overwritten (move it aside with its record first)")
        if not raw.exists():
            shutil.copyfile(src, raw)
        pr = probe(raw)
        nxt = clips[k + 1] if k + 1 < len(clips) else None
        hand = (nxt or {}).get("chain_from_frame")
        handover_s = (int(hand["frame"]) / pr["fps"]) if hand and pr["fps"] else None
        is_cont = bool(c.get("chain_from_frame"))
        mute_tail, speech_detector = None, None
        from explainer_engine.qa import sound_realism as R
        x = R.read_audio(raw) if pr["has_audio"] else np.zeros(0, np.float32)
        spans = [(float(a), float(b)) for a, b in R.speech_spans(x)] if len(x) else []
        if sid in spoken and pr["has_audio"]:    # TD-327: the words the detector missed (the detector alone dropped a line's start)
            words_fn = words_fn or _local_words
            lines = {l["line_id"]: l for l in script.get("audio_lines") or []}
            text = " ".join(lines[i]["text"] for i in shot.get("audio_line_ids") or []
                            if lines.get(i, {}).get("speaker_type") == "character")
            heard = words_fn(raw)
            words_source = "local whisper" if heard is not None else "unavailable (detector spans only)"
            decision = trim_decision(spans, heard, text, spoken=True, dur=pr["duration"], audio=x, rate=R.SR)   # Step 1.2: one rule
            spans, mute_tail, speech_detector = decision["spans"], decision["mute_tail_from_s"], decision["detector"]
        planned = float(shot.get("target_duration_seconds") or 0.0)
        pts = edit_points(pr["duration"], spans, shot.get("edit_plan"), planned, fps, spoken=sid in spoken,
                          handover_s=handover_s, drop_first=is_cont, shot_id=sid,
                          audio=x if len(x) else None, rate=R.SR)
        trimmed = cut(raw, vdir / "cut" / f"{sid}.mp4", pts["in_s"], pts["frames"], fps)
        t_spans = [(round(max(0.0, a - pts["in_s"]), 3), round(min(pts["frames"] / fps, b - pts["in_s"]), 3))
                   for a, b in spans if b > pts["in_s"] and a < pts["out_s"]]
        metrics, finds = VQ.clip_findings(trimmed, fps=fps, expect_speech=sid in spoken)
        trim_db, peak_before = _level_trim(metrics, finds)
        if trim_db:   # HF-4 (FL-401, FL-111, TD-305): CLIP-06 is judged on the trimmed cut; the model's clip stays as it is
            trimmed = cut(raw, vdir / "cut" / f"{sid}.mp4", pts["in_s"], pts["frames"], fps, gain_db=trim_db)
            metrics, finds = VQ.clip_findings(trimmed, fps=fps, expect_speech=sid in spoken)
        bad = [f for f in finds if f.get("status") == "FAIL" or f.get("severity") == "FAIL"]
        rec = {"schema": SCHEMA, "shot_id": sid, "route": "video", "backend": backend,
               "status": G.FAIL if bad else (G.REVIEW if any((f.get("status") or f.get("severity")) == "REVIEW"
                                                                for f in finds) else G.PASS),
               "clip_path": str(trimmed.relative_to(root)), "clip_sha256": _sha(trimmed),
               "raw_path": str(raw.relative_to(root)), "raw_sha256": _sha(raw), "raw_fps": pr["fps"],
               "raw_seconds": round(pr["duration"], 4), "fps": fps, "in_s": pts["in_s"], "out_s": pts["out_s"],
               "frames": pts["frames"], "speech_raw": spans, "speech": t_spans, "clip_spoken": sid in spoken,
               "chain_from_frame": c.get("chain_from_frame"), "ends_on_handover": handover_s is not None,
               "findings": finds, "attempts": c.get("attempts") or []}
        rec["trim_contract"] = build_trim_contract(rec, sid)
        rec["start_frame_check"] = start_frame_check(root, shot, raw, pictures, is_continuation=is_cont)
        if (rec["start_frame_check"].get("frame0_vs_source") or {}).get("status") in ("PASS", "FAIL"):
            comparisons[sid] = rec["start_frame_check"]["frame0_vs_source"]
        if sid in spoken and pr["has_audio"]:
            rec["speech_words"] = words_source
            rec["speech_detector"] = speech_detector     # which voicing check decided the words (silero_vad | harmonicity | none)
            rec["trim_notes"] = decision["notes"]        # a kept duplicate opening word etc.: REVIEW items for the creator
            rec["mute_tail_from_s"] = mute_tail          # where a hallucinated tail word starts to be muted (None: no such word)
        if trim_db:
            rec.update({"level_trim_db": trim_db, "true_peak_before": peak_before})
        write_json_atomic(vdir / f"{sid}.json", rec)
        out.append(rec)
    route_proposals(root, script, comparisons)       # Step 1.3: proposals only, the script's routes stay as they are
    return out


# ---- Step 1.3 (D-139): the start-frame record and the route proposals (records only, nothing is re-routed here) ------------------

START_FRAME_STATES = ("PASS", "REVIEW", "NEEDS_EVIDENCE")


def frame0_of(clip: Path):
    """Frame 0 of a clip as a BGR array, or None when it cannot be decoded."""
    try:
        import cv2
        cap = cv2.VideoCapture(str(clip))
        ok, img = cap.read()
        cap.release()
        return img if ok else None
    except Exception:
        return None


def start_frame_check(root: Path, shot: dict, raw: Path, pictures: dict | None, *, is_continuation: bool = False) -> dict:
    """Raw frame 0 against the pinned start picture ``{shot_id}_start`` (production/pictures.json). Status is PASS only when
    the comparison ran AND the start-frame inspection has evidence and no issue; a missing picture, a continuation (its start
    is the previous clip, not a picture) or an undecodable frame is NEEDS_EVIDENCE; a divergence or an inspection issue is REVIEW."""
    from explainer_engine.videolane import plan as P
    sid = shot["shot_id"]
    key = f"{sid}_start"
    rec = {"picture_key": key, "frame0_vs_source": None, "inspection": None, "status": "NEEDS_EVIDENCE", "reasons": []}
    entry = (pictures or {}).get(key)
    pic = (Path(root) / entry["file"]) if entry and entry.get("file") else None
    if is_continuation:
        rec["reasons"].append("continuation: its start is the previous clip's frame, no pinned start picture to compare")
        return rec
    if pic is None or not pic.is_file():
        rec["reasons"].append(f"no pinned start picture {key} in production/pictures.json")
        return rec
    rec["picture_sha256"] = _sha(pic)
    f0 = frame0_of(raw)
    if f0 is None:
        rec["reasons"].append("frame 0 of the raw clip could not be decoded")
        return rec
    cmp_ = P.compare_ltx_first_frame_to_source(pic, f0)
    insp = P.inspect_ltx_start_frame(shot, start_frame=pic)
    rec["frame0_vs_source"] = {k: cmp_.get(k) for k in ("status", "matched", "mean_abs_diff", "luma_corr", "reason")}
    rec["inspection"] = {k: insp.get(k) for k in ("status", "confidence", "has_evidence", "issues")}
    if cmp_.get("status") not in ("PASS", "FAIL"):
        rec["reasons"].append(str(cmp_.get("reason")))
        return rec                                   # the comparison did not run: no data, no PASS
    if cmp_.get("status") == "FAIL":
        rec["reasons"].append(str(cmp_.get("reason")))
    rec["reasons"] += list(insp.get("issues") or [])
    if not insp.get("has_evidence"):
        rec["reasons"].append("start-frame inspection has no evidence")
    rec["status"] = "REVIEW" if rec["reasons"] else "PASS"
    return rec


def route_proposals(root: Path, script: dict, comparisons: dict[str, dict] | None = None) -> list[dict]:
    """Proposals only (``apply_routes=False``): ``production/route_proposals.json`` lists the video shots C2 says are not natural
    for LTX. The script is never changed here; a route change is the creator's (D-139)."""
    from explainer_engine.videolane import plan as P
    res = P.reroute_unnatural_ltx_shots(script, apply_routes=False, first_frame_comparisons=comparisons or {})
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    props = []
    for sid in res["rerouted_to_25d"]:
        ev = res["evaluations"][sid]
        props.append({"shot_id": sid, "from_route": by.get(sid, {}).get("route", "video"),
                      "to_route": ev["recommended_route"], "reason": "; ".join(ev.get("reasons") or [])[:400]})
    write_json_atomic(Path(root) / "production" / "route_proposals.json", {"schema": "route_proposals/1", "proposals": props})
    return props


def unresolved_reviews(root: Path) -> dict:
    """The open REVIEW items of the clip records: ``{count, items}`` (printed by publish_check, non-blocking until Step 5)."""
    items = []
    for p in sorted((Path(root) / "production" / "video").glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(r, dict) or "shot_id" not in r:
            continue
        why = []
        sf = (r.get("start_frame_check") or {}).get("status")
        if sf in ("REVIEW", "NEEDS_EVIDENCE"):
            why.append(f"start_frame_check {sf}")
        if r.get("status") == G.REVIEW:
            why.append("clip findings REVIEW")
        if why:                                      # one item per clip, both reasons named
            items.append(f"{r['shot_id']}: " + " + ".join(why))
    return {"count": len(items), "items": items}



def recut(root: Path, rec: dict, frames: int, fps: int) -> dict:
    """A silent or narrated video shot whose clock (the read) gives it another length than its first cut: cut it again from
    its kept raw clip at the same in point (free, class A). A raw clip too short for the shot is a ContractError: the clip
    is made again (class C), never stretched."""
    root = Path(root)
    raw = root / rec["raw_path"]
    if not raw.is_file() or _sha(raw) != rec["raw_sha256"]:
        raise ContractError(f"{rec['shot_id']}: its raw clip is missing or changed; it cannot be cut again")
    if rec.get("clip_spoken"):
        raise ContractError(f"{rec['shot_id']}: a clip-spoken shot is timed by its own cut, never re-cut to a clock")
    if rec.get("ends_on_handover") and frames != int(rec["frames"]):
        raise ContractError(f"{rec['shot_id']}: it ends on the frame its continuation starts from (VL-05); a cut at another "
                            "frame would repeat or skip the action: time the read to it, or re-plan the continuation")
    have = float(rec["raw_seconds"]) - float(rec["in_s"])
    if frames / fps > have + 0.5 / fps:
        raise ContractError(f"{rec['shot_id']}: the shot needs {frames / fps:.2f} s, the raw clip holds {have:.2f} s after "
                            "its in point: make the clip longer (VL-06), it is never stretched")
    out = root / rec["clip_path"]
    cut(raw, out, float(rec["in_s"]), frames, fps, gain_db=float(rec.get("level_trim_db") or 0.0))
    new = dict(rec, frames=frames, out_s=round(float(rec["in_s"]) + frames / fps, 4), clip_sha256=_sha(out),
               recut_from=rec.get("frames"))
    write_json_atomic(root / "production" / "video" / f"{rec['shot_id']}.json", new)
    return new


def clip_timings(root: Path, script: dict) -> dict:
    """``{shot_id: {frames, speech}}`` of every clip-timed shot whose record exists (the voice stage's input)."""
    from explainer_engine.videolane import plan as P
    out = {}
    for sid in sorted(P.clip_spoken(script)):
        p = Path(root) / "production" / "video" / f"{sid}.json"
        if p.is_file():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("status") != G.FAIL:
                out[sid] = {"frames": int(d["frames"]), "speech": d.get("speech") or []}
    return out



REACTION_TAIL_MIN_S = BP201_TAIL_MIN_S


def whisper_edit_points(
    whisper_doc: dict,
    script: dict,
    *,
    head_lead_s: float = BP201_HEAD_LEAD_S,
    reaction_tail_s: float = BP201_TAIL_TARGET_S,
    min_dur_s: float = 1.50,
    raw_durations: dict[str, float] | None = None,
    audio_by_shot: dict[str, tuple] | None = None,
) -> dict:
    """Step 1 (Trim/Clock Fix): compute frame-accurate edit_points from measured Whisper word timestamps.

    - For every clip-spoken shot, trims ``in`` to ``max(0.0, first_word_start - head_lead_s)`` and
      ``out`` to ``min(raw_dur, last_word_end + max(REACTION_TAIL_MIN_S, reaction_tail_s))`` so no spoken
      syllable is ever severed mid-word and at least 0.50 s of reaction tail is preserved when available.
    - With ``audio_by_shot`` (``{shot_id: (samples, rate)}``) a word counts only where a voice is heard (``accept_voiced_words``,
      Step 1.2) and its times are clamped to the voiced span; the entry names the ``detector`` that ran ("none" without audio).
    - For silent or narrator-voiced clips where Whisper detects hallucinated trailing speech tokens
      (e.g. ``"You"`` in the last 1.2 s), records ``mute_tail_from_s`` so the mixer fades out the tail.
    """
    from explainer_engine.videolane import plan as P

    spoken = P.clip_spoken(script)
    shots_by_id = {s["shot_id"]: s for s in script.get("shots", [])}
    raw_durations = raw_durations or {}
    clips_out: dict[str, dict] = {}
    whisper_clips = whisper_doc.get("clips") if isinstance(whisper_doc, dict) and "clips" in whisper_doc else whisper_doc
    if not isinstance(whisper_clips, dict):
        whisper_clips = {}

    for sid, wrec in sorted(whisper_clips.items()):
        shot = shots_by_id.get(sid) or {}
        words = list((wrec or {}).get("words") or [])
        raw_dur = float(
            raw_durations.get(sid)
            or (wrec or {}).get("duration")
            or (wrec or {}).get("raw_seconds")
            or max([float(w.get("end", 0.0)) for w in words] + [float(shot.get("target_duration_seconds") or 4.0)])
        )
        if sid in spoken and words:
            dup_audio = audio_by_shot.get(sid) if audio_by_shot else None
            dup_notes: list = []
            clean_words, mute_at = drop_word_artifacts(words, *(dup_audio or (None, 16000)), notes=dup_notes)   # the same filters as the runner's cut (one trim rule)
            detector = "none"
            if audio_by_shot and sid in audio_by_shot:   # a voice must be heard under a word (Step 1.2); clamps its times
                x, rate = audio_by_shot[sid]
                acc = accept_voiced_words(clean_words, x, rate)
                detector, clean_words = acc["detector"], acc["kept"]
                if not clean_words:
                    clips_out[sid] = {"in": 0.0, "out": round(raw_dur, 3), "detector": detector, "no_voice_heard": True,
                                      "rejected_words": [r["text"] for r in acc["rejected"]]}
                    continue
                if mute_at is None and acc["rejected"] and any(r["start"] >= float(clean_words[-1]["end"]) for r in acc["rejected"]):
                    mute_at = round(float(clean_words[-1]["end"]) + MUTE_TAIL_AFTER_S, 3)

            first_start = float(clean_words[0].get("start", 0.0))
            last_end = float(clean_words[-1].get("end", first_start + 1.0))
            t_in = round(max(0.0, first_start - head_lead_s), 3)
            tail_need = resolve_reaction_tail_s(shot.get("edit_plan"), reaction_tail_s)
            t_out = round(min(raw_dur, max(t_in + min_dur_s, last_end + tail_need)), 3)
            avail_tail = round(t_out - last_end, 3)
            entry: dict = {
                "in": t_in,
                "out": t_out,
                "speech_start_s": round(first_start, 3),
                "speech_end_s": round(last_end, 3),
                "reaction_tail_s": avail_tail,
                "truncated_in_raw": avail_tail < 0.20,
                "detector": detector,
            }
            if dup_notes:
                entry["trim_notes"] = dup_notes
            if mute_at is not None:
                entry["mute_tail_from_s"] = mute_at
            clips_out[sid] = entry
        elif words:
            # Silent / narrated shot: check for hallucinated trailing tokens like "You"
            tail_hallucinations = [
                w for w in words
                if re.sub(r"\W+", "", str(w.get("word", "")).lower()) in HALLUCINATED_TAIL_TOKENS
            ]
            if tail_hallucinations:
                first_hal = min(float(w.get("start", raw_dur)) for w in tail_hallucinations)
                clips_out[sid] = {
                    "in": 0.0,
                    "out": round(raw_dur, 3),
                    "mute_tail_from_s": round(max(0.0, first_hal - 0.08), 3),
                    "why": "mute LTX hallucinated speech token in tail",
                }
    return {"schema": "edit_points/2", "clips": clips_out}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="videolane.ingest", description="LTX clips into the episode: raw kept, cut by speech")
    ap.add_argument("episode")
    ap.add_argument("clips", help="JSON list [{shot_id, path, chain_from_frame?}] in cut order (the worker's rows + files)")
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args(argv)
    root = Path(a.episode)
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    recs = ingest_scene(root, script, json.loads(Path(a.clips).read_text(encoding="utf-8")), a.fps)
    print(json.dumps([{k: r[k] for k in ("shot_id", "status", "in_s", "out_s", "frames")} for r in recs], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
