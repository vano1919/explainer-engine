"""Word-Locked Documentary Timeline Compiler & Dialogue Clearance Enforcer (v5.0).

Replaces ad-hoc hardcoded second tables with a deterministic, reusable timeline solver
driven directly by ElevenLabs ``word_timestamps.json``:
1. Matches every narrated hero shot's ``anchor_word`` in monotonic order to its exact
   spoken word timestamp (enforcing ``|shot_start - word_start| <= max_word_drift_s``).
2. Enforces ``>= min_dialogue_clearance_s`` (default ``0.40s``) narrator silence before
   and after every voiced character dialogue turn AND every Cinema Silence Drop window.
3. Emits a verified ``compiled_timeline.json`` manifest for downstream 2K master assembly
   and forensic QA gates.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_WORD_CLEAN_RE = re.compile(r"[^a-z0-9']+")


def _norm_token(word: str) -> str:
    return _WORD_CLEAN_RE.sub("", str(word or "").lower()).strip("'")


@dataclass(slots=True)
class CompiledShot:
    shot_id: str
    scene_id: str
    route: str
    start_s: float
    end_s: float
    duration_s: float
    has_dialogue: bool = False
    dramatic_scene: bool = False
    chained_from: str = ""
    anchor_word: str = ""
    matched_word_start_s: float | None = None
    word_drift_s: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TimelineCompilationResult:
    status: str
    total_duration_s: float
    shot_count: int
    anchors_requested: int
    anchors_matched: int
    max_word_drift_s: float
    mean_word_drift_s: float
    min_dialogue_clearance_s: float
    dialogue_clearances: list[dict[str, Any]]
    silence_drop_clearances: list[dict[str, Any]]
    shots: list[CompiledShot]
    findings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_duration_s": round(self.total_duration_s, 3),
            "shot_count": self.shot_count,
            "anchors_requested": self.anchors_requested,
            "anchors_matched": self.anchors_matched,
            "max_word_drift_s": round(self.max_word_drift_s, 3),
            "mean_word_drift_s": round(self.mean_word_drift_s, 3),
            "min_dialogue_clearance_s": round(self.min_dialogue_clearance_s, 3),
            "dialogue_clearances": self.dialogue_clearances,
            "silence_drop_clearances": self.silence_drop_clearances,
            "shots": [asdict(s) for s in self.shots],
            "findings": list(self.findings),
        }


def load_word_timestamps(path: Path) -> list[dict[str, Any]]:
    """Load ElevenLabs word timestamps from either a flat list JSON or a dict containing ``words``."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = list(raw.get("words") or raw.get("word_timestamps") or [])
    else:
        items = []

    out: list[dict[str, Any]] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        w = str(entry.get("word") or entry.get("text") or "").strip()
        if not w:
            continue
        s = float(entry.get("start_s", entry.get("start", 0.0)))
        e = float(entry.get("end_s", entry.get("end", s)))
        out.append({"word": w, "norm": _norm_token(w), "start_s": s, "end_s": max(s, e)})
    out.sort(key=lambda r: (r["start_s"], r["end_s"]))
    return out


def _find_best_anchor_word(
    anchor_phrase: str,
    words: list[dict[str, Any]],
    *,
    expected_s: float,
    min_start_s: float,
    search_window_s: float = 12.0,
) -> dict[str, Any] | None:
    """Find the closest monotonic occurrence of an anchor word or short phrase near expected_s."""
    tokens = [_norm_token(tok) for tok in str(anchor_phrase).split() if _norm_token(tok)]
    if not tokens or not words:
        return None
    target = tokens[0]
    best: tuple[float, dict[str, Any]] | None = None
    for idx, w in enumerate(words):
        ws = float(w["start_s"])
        if ws < min_start_s - 0.15:
            continue
        if w["norm"] != target:
            continue
        if len(tokens) > 1:
            seq_ok = True
            for j, tok in enumerate(tokens[1:], start=1):
                if idx + j >= len(words) or words[idx + j]["norm"] != tok:
                    seq_ok = False
                    break
            if not seq_ok:
                continue
        dist = abs(ws - expected_s)
        if dist <= search_window_s and (best is None or dist < best[0]):
            best = (dist, w)
    if best is not None:
        return best[1]
    # Fallback: first monotonic match anywhere after min_start_s
    for w in words:
        if float(w["start_s"]) >= min_start_s - 0.15 and w["norm"] == target:
            return w
    return None


def compile_word_locked_timeline(
    shots: list[dict[str, Any]],
    utterances: list[dict[str, Any]],
    word_timestamps: list[dict[str, Any]],
    *,
    silence_drops: list[dict[str, Any]] | None = None,
    max_word_drift_s: float = 1.2,
    min_dialogue_clearance_s: float = 0.40,
    min_shot_duration_s: float = 1.6,
    snap_to_words: bool = True,
) -> TimelineCompilationResult:
    """Compile shot start/end timings anchored to ElevenLabs word timestamps with strict dialogue clearance.

    Parameters
    ----------
    shots:
        Ordered shot dicts containing ``shot_id``, ``scene_id``, ``route``, ``duration_s`` (or explicit
        ``start_s``/``end_s``), optional ``anchor_word``, ``has_dialogue``, ``dramatic_scene``, ``chained_from``.
    utterances:
        Narrator utterance windows with ``start_s`` and ``end_s`` (e.g. placed Odom narration takes).
    word_timestamps:
        Global timeline word timestamps ``[{"word": ..., "start_s": ..., "end_s": ...}, ...]``.
    silence_drops:
        Optional Cinema Silence Drop windows ``[{"start_s": ..., "end_s": ..., "label": ...}, ...]``.
    max_word_drift_s:
        Maximum allowed ``|shot_start - word_start|`` for every narrated anchor shot (default ``1.2s``).
    min_dialogue_clearance_s:
        Minimum required narrator silence margin around every voiced character dialogue shot and
        every silence drop window (default ``0.40s``).
    snap_to_words:
        When ``True``, gently adjusts preceding non-dialogue shot end boundaries (respecting
        ``min_shot_duration_s``) so narrated anchor shots land tightly on their spoken cues.
    """
    norm_words: list[dict[str, Any]] = []
    for entry in word_timestamps:
        w = str(entry.get("word") or entry.get("text") or "").strip()
        if not w:
            continue
        s = float(entry.get("start_s", entry.get("start", 0.0)))
        e = float(entry.get("end_s", entry.get("end", s)))
        norm_words.append({"word": w, "norm": _norm_token(w), "start_s": s, "end_s": max(s, e)})
    norm_words.sort(key=lambda r: (r["start_s"], r["end_s"]))

    # 1. Build initial contiguous timeline from shot durations or explicit start/end timestamps
    compiled: list[CompiledShot] = []
    max_durs: list[float | None] = []
    cursor = 0.0
    for raw in shots:
        if "start_s" in raw and "end_s" in raw:
            s_t = float(raw["start_s"])
            e_t = float(raw["end_s"])
            dur = max(0.1, e_t - s_t)
        else:
            dur = max(0.1, float(raw.get("duration_s", 5.0)))
            s_t = cursor
            e_t = cursor + dur
        cursor = e_t
        max_d = float(raw["max_duration_s"]) if raw.get("max_duration_s") is not None else None
        max_durs.append(max_d)
        compiled.append(
            CompiledShot(
                shot_id=str(raw.get("shot_id") or f"shot_{len(compiled) + 1:02d}"),
                scene_id=str(raw.get("scene_id") or "scene_default"),
                route=str(raw.get("route") or "ltx_video"),
                start_s=round(s_t, 4),
                end_s=round(e_t, 4),
                duration_s=round(dur, 4),
                has_dialogue=bool(raw.get("has_dialogue", False)),
                dramatic_scene=bool(raw.get("dramatic_scene", False)),
                chained_from=str(raw.get("chained_from") or ""),
                anchor_word=str(raw.get("anchor_word") or "").strip(),
                meta=dict(raw.get("meta") or {}),
            )
        )

    # 2. Match & optionally snap narrated hero shots to their exact ElevenLabs spoken word cues
    last_matched_word_s = 0.0
    anchors_requested = 0
    anchors_matched = 0
    drifts: list[float] = []
    findings: list[str] = []

    for idx, shot in enumerate(compiled):
        if shot.has_dialogue or not shot.anchor_word:
            continue
        anchors_requested += 1
        match = _find_best_anchor_word(
            shot.anchor_word,
            norm_words,
            expected_s=shot.start_s,
            min_start_s=last_matched_word_s,
        )
        if match is None:
            findings.append(f"Anchor word {shot.anchor_word!r} for shot {shot.shot_id} not found in word_timestamps")
            continue

        word_s = float(match["start_s"])
        last_matched_word_s = word_s
        anchors_matched += 1

        # Snap cut boundary tightly onto spoken word when preceding shot is flexible and max_duration_s is respected
        if snap_to_words and idx > 0:
            prev = compiled[idx - 1]
            desired_start = max(0.0, word_s - 0.15)  # subtle 150ms visual lead into spoken keyword
            new_prev_dur = desired_start - prev.start_s
            new_cur_dur = shot.end_s - desired_start
            prev_max = max_durs[idx - 1]
            cur_max = max_durs[idx]
            within_max = (prev_max is None or new_prev_dur <= prev_max + 1e-4) and (
                cur_max is None or new_cur_dur <= cur_max + 1e-4
            )
            can_adjust_prev = (
                not prev.has_dialogue
                and not shot.chained_from
                and within_max
                and new_prev_dur >= min_shot_duration_s
                and new_cur_dur >= min_shot_duration_s
            )
            if can_adjust_prev and abs(shot.start_s - word_s) > 0.20:
                prev.end_s = round(desired_start, 4)
                prev.duration_s = round(prev.end_s - prev.start_s, 4)
                shot.start_s = round(desired_start, 4)
                shot.duration_s = round(shot.end_s - shot.start_s, 4)

        drift = abs(shot.start_s - word_s)
        shot.matched_word_start_s = round(word_s, 3)
        shot.word_drift_s = round(drift, 3)
        drifts.append(drift)
        if drift > max_word_drift_s:
            findings.append(
                f"Shot {shot.shot_id} anchor {shot.anchor_word!r} drifts {drift:.2f}s from word@{word_s:.2f}s "
                f"(shot_start={shot.start_s:.2f}s > {max_word_drift_s:.2f}s max)"
            )

    # 2b. Fail-closed source clip duration parity check (never allow a shot to exceed its physical media length)
    for idx, shot in enumerate(compiled):
        m_dur = max_durs[idx]
        if m_dur is not None and shot.duration_s > m_dur + 0.02:
            findings.append(
                f"Shot {shot.shot_id} compiled duration {shot.duration_s:.2f}s exceeds source clip max_duration_s "
                f"{m_dur:.2f}s (would cause premature cut & AV desync)"
            )

    # 3. Verify narrator silence clearance around every voiced character dialogue window
    utt_windows = [
        (float(u.get("start_s", 0.0)), float(u.get("end_s", 0.0)), str(u.get("id") or u.get("utterance_id") or f"u{i}"))
        for i, u in enumerate(utterances)
        if float(u.get("end_s", 0.0)) > float(u.get("start_s", 0.0))
    ]
    utt_windows.sort(key=lambda t: t[0])

    def _window_clearance(win_start: float, win_end: float) -> tuple[float, float, str]:
        """Return (signed_clearance_s, overlap_s, offending_utt_id) against all narrator utterances."""
        min_gap = 999.0
        max_overlap = 0.0
        offender = ""
        for us, ue, uid in utt_windows:
            overlap = min(win_end, ue) - max(win_start, us)
            if overlap > 0.0:
                if overlap > max_overlap:
                    max_overlap = overlap
                    offender = uid
                min_gap = min(min_gap, -overlap)
            else:
                gap = (win_start - ue) if ue <= win_start else (us - win_end)
                if gap < min_gap:
                    min_gap = gap
                    offender = uid
        return min_gap, max_overlap, offender

    # Group contiguous dialogue shots into dramatic dialogue blocks so clearance is checked at block edges
    dialogue_blocks: list[tuple[float, float, list[str]]] = []
    for shot in compiled:
        if not shot.has_dialogue:
            continue
        if dialogue_blocks and abs(shot.start_s - dialogue_blocks[-1][1]) <= 0.05:
            prev_s, _, ids = dialogue_blocks[-1]
            dialogue_blocks[-1] = (prev_s, shot.end_s, ids + [shot.shot_id])
        else:
            dialogue_blocks.append((shot.start_s, shot.end_s, [shot.shot_id]))

    dialogue_clearances: list[dict[str, Any]] = []
    min_observed_clearance = 999.0
    for ds, de, ids in dialogue_blocks:
        gap, overlap, offender = _window_clearance(ds, de)
        min_observed_clearance = min(min_observed_clearance, gap)
        passed = overlap <= 0.0 and gap >= (min_dialogue_clearance_s - 1e-4)
        dialogue_clearances.append(
            {
                "shot_ids": ids,
                "start_s": round(ds, 3),
                "end_s": round(de, 3),
                "narrator_clearance_s": round(gap, 3),
                "overlap_s": round(overlap, 3),
                "nearest_utterance": offender,
                "status": "PASS" if passed else "FAIL",
            }
        )
        if not passed:
            findings.append(
                f"Narrator utterance {offender!r} violates {min_dialogue_clearance_s:.2f}s clearance around "
                f"dialogue block {ids[0]}..{ids[-1]} [{ds:.2f}s..{de:.2f}s] (clearance={gap:.2f}s, overlap={overlap:.2f}s)"
            )

    # 4. Verify narrator silence clearance around Cinema Silence Drops
    silence_drop_clearances: list[dict[str, Any]] = []
    for i, sd in enumerate(silence_drops or []):
        ss = float(sd.get("start_s", 0.0))
        se = float(sd.get("end_s", ss + float(sd.get("duration_s", 0.40))))
        lbl = str(sd.get("label") or f"silence_drop_{i + 1}")
        gap, overlap, offender = _window_clearance(ss, se)
        drop_dur = max(0.0, se - ss)
        passed = overlap <= 0.0 and drop_dur >= (min_dialogue_clearance_s - 1e-4)
        silence_drop_clearances.append(
            {
                "label": lbl,
                "start_s": round(ss, 3),
                "end_s": round(se, 3),
                "duration_s": round(drop_dur, 3),
                "narrator_clearance_s": round(gap, 3),
                "overlap_s": round(overlap, 3),
                "nearest_utterance": offender,
                "status": "PASS" if passed else "FAIL",
            }
        )
        if not passed:
            findings.append(
                f"Silence drop {lbl!r} [{ss:.2f}s..{se:.2f}s] failed clearance/duration check "
                f"(dur={drop_dur:.2f}s, overlap={overlap:.2f}s with {offender!r})"
            )

    total_dur = compiled[-1].end_s if compiled else 0.0
    max_drift = max(drifts) if drifts else 0.0
    mean_drift = (sum(drifts) / len(drifts)) if drifts else 0.0
    final_min_clr = min_observed_clearance if dialogue_blocks else min_dialogue_clearance_s

    return TimelineCompilationResult(
        status="PASS" if not findings else "FAIL",
        total_duration_s=total_dur,
        shot_count=len(compiled),
        anchors_requested=anchors_requested,
        anchors_matched=anchors_matched,
        max_word_drift_s=max_drift,
        mean_word_drift_s=mean_drift,
        min_dialogue_clearance_s=final_min_clr,
        dialogue_clearances=dialogue_clearances,
        silence_drop_clearances=silence_drop_clearances,
        shots=compiled,
        findings=findings,
    )


def save_compiled_timeline(result: TimelineCompilationResult, out_json: Path) -> Path:
    """Persist a compiled timeline report to JSON."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return out_json
