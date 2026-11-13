"""The sound-realism gate (W1 of the realism plan, 2026-11-12; BP-189..BP-193): measured on the DELIVERED file, never on a plan
or an intermediate stem (the creator's "the silence during dialogue is the most artificial thing" and "a senseless hiss, no sound
on the map's actions", 2026-11-12 21:44 UTC).

    python -m explainer_engine.qa.sound_realism <video.mp4> [--timeline <scene_timeline.json>] [--out report.json]

What it measures (all on the file's own audio, mono, ``SR`` Hz):

1. ``no_dropout`` (BP-189): the quietest ``window_ms`` window between the first and the last second; a window under
   ``floor_dbfs`` is a dropout (the battle scene of 2026-11-12: -62 dBFS before "Attack!").
2. ``dialogue_never_dead`` (BP-189): the share of ``window_ms`` windows under ``dead_dbfs`` inside the dialogue part, intended
   pauses excluded (battle scene: 45 %).
3. ``pause_line_to_line`` (BP-190): every pause from the end of one line's speech to the start of the next line's speech, found
   by the voice-activity detector on the final file (``speech_spans``); the timeline only says which span belongs to which line.
4. ``bed_across_cuts`` (BP-191): at every picture cut, the background level (speech frames left out) half a second either side;
   a jump over ``cut_jump_db_max`` is a seam the ear hears.
5. ``action_sounds_heard`` (BP-192): every planned action sound (the timeline's ``events``): its loudest 100 ms against what
   plays around it in the same state (the bed, or the narrator), broadband or in the one band where it rises most (a tick
   over the narrator is heard in the highs); under ``heard_min_db`` it is not heard (the overlay demo: 12 LU under its bed), outside ``target_above_bed_db``
   it is REVIEW.
6. ``not_one_noise_everywhere`` (BP-193): the bed-only frames of each place (no speech, no planned event, the quieter half);
   when ``min_places`` different places share one band spectrum, one noise plays everywhere (the overlay demo's numpy "wind"
   under a cave, a river, maps and charts alike).

The timeline (``scene_timeline/1``, written by the scene join ``production/scene_join.py`` or by hand for an old file):
``{"cuts": [s], "dialogue": [[a, b]], "lines": [{"id", "start_s", "end_s"}], "intended_pauses": [[a, b]],
"events": [{"at_s", "dur_s", "class"}], "places": [{"start_s", "end_s", "place"}]}``. Without one, the whole file is the
dialogue part, every speech span is its own line, and rows that need cuts or events say NOT_RUN.

Levels are RMS dBFS of the mono mix (no K-weighting; BP-186 measures the same way). The reference numbers of the realism audit
print beside ours (``REFERENCE``, PR-03).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR_RULES

SCHEMA = "sound_realism_report/1"
SR = 16000
FRAME_S = 0.02            # the detector's frame
SPEECH_BAND_HZ = (250.0, 3800.0)
# what the audit measured (REALISM_AUDIT_2026-11-12_ka.md, sections 1-2): printed beside every row, never a threshold
REFERENCE = {
    "no_dropout": {"film_dialogue_scene": "room tone or bed always under dialogue (BP-116)", "battle_2026_11_12": -62.0},
    "dialogue_never_dead": {"target_share": 0.0, "battle_2026_11_12": 0.45, "love_2026_11_12": 0.52},
    "pause_line_to_line": {"conversation_gap_s": "about 0.2 (Stivers et al. 2009)", "battle_2026_11_12_cut1": 1.15},
    "action_sounds_heard": {"overlay_demo_2026_11_12_db_vs_bed": -12.0},
    "not_one_noise_everywhere": {"overlay_demo_2026_11_12_band_deviation": "0.03-0.05 across 12 shots"},
}


def read_audio(path: Path) -> np.ndarray:
    """The file's audio as mono float32 at ``SR`` (ffmpeg); an mp4, a wav or anything ffmpeg reads."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def db(x: float) -> float:
    return float(20 * np.log10(max(1e-9, x)))


def window_db(x: np.ndarray, win_s: float, rate: int = SR) -> np.ndarray:
    """RMS dBFS of consecutive windows of ``win_s`` (the last partial window dropped)."""
    w = max(1, int(round(win_s * rate)))
    k = len(x) // w
    if k == 0:
        return np.zeros(0)
    r = np.sqrt(np.mean(np.asarray(x[: k * w], np.float64).reshape(k, w) ** 2, axis=1) + 1e-18)
    return 20 * np.log10(r)


def _band_db(x: np.ndarray, rate: int, lo: float, hi: float, frame_s: float = FRAME_S) -> np.ndarray:
    w = max(16, int(round(frame_s * rate)))
    k = len(x) // w
    if k == 0:
        return np.zeros(0)
    fr = np.asarray(x[: k * w], np.float64).reshape(k, w) * np.hanning(w)
    spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(w, 1 / rate)
    band = spec[:, (f >= lo) & (f <= hi)].sum(axis=1) / w
    return 10 * np.log10(band + 1e-18)


def speech_spans(x: np.ndarray, rate: int = SR, *, below_peak_db: float = 10.0, min_span_s: float = 0.12,
                 merge_gap_s: float = 0.2, floor_margin_db: float = 10.0, ref_spans=None) -> list[tuple[float, float]]:
    """Where someone speaks: frames whose speech-band level is within ``below_peak_db`` of the file's loud speech (its 97th
    percentile) and ``floor_margin_db`` over its floor (20th percentile); gaps under ``merge_gap_s`` merge (the pauses inside a
    sentence), spans under ``min_span_s`` drop. Shouts and war cries count as speech: the timeline says which spans are lines.
    ``ref_spans`` (the dialogue part) sets where the percentiles are taken, so a charge's roar after the last line does not
    lift the threshold over the lines themselves."""
    e = _band_db(x, rate, *SPEECH_BAND_HZ)
    if not len(e):
        return []
    ref = e
    if ref_spans:
        m = _mask(len(e), FRAME_S, ref_spans)
        ref = e[m] if m.sum() > 10 else e
    thr = max(np.percentile(ref, 97) - below_peak_db, np.percentile(ref, 20) + floor_margin_db)
    on = e > thr
    spans, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            spans.append([i * FRAME_S, j * FRAME_S])
            i = j
        else:
            i += 1
    merged: list[list[float]] = []
    for a, b in spans:
        if merged and a - merged[-1][1] < merge_gap_s:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in merged if b - a >= min_span_s]


def _inside(t: float, spans) -> bool:
    return any(a <= t < b for a, b in spans)


def _mask(n_win: int, win_s: float, spans) -> np.ndarray:
    c = (np.arange(n_win) + 0.5) * win_s
    m = np.zeros(n_win, bool)
    for a, b in spans:
        m |= (c >= a) & (c < b)
    return m


def _pad(spans, s: float, end: float):
    return [(max(0.0, a - s), min(end, b + s)) for a, b in spans]


def line_pauses(spans, lines: list[dict] | None) -> list[dict]:
    """The pause from each line's last speech to the next line's first speech. With lines from the timeline, a detected span
    belongs to the line it overlaps most; without them, each span is a line."""
    if not lines:
        return [{"from": i, "to": i + 1, "end_s": a[1], "next_start_s": b[0], "pause_s": round(b[0] - a[1], 3)}
                for i, (a, b) in enumerate(zip(spans, spans[1:]))]
    own: dict[str, list] = {}
    for a, b in spans:
        best, ov = None, 0.0
        for ln in lines:
            o = min(b, ln["end_s"]) - max(a, ln["start_s"])
            if o > ov:
                best, ov = ln["id"], o
        if best is not None:
            own.setdefault(best, []).append((a, b))
    out = []
    order = [ln for ln in sorted(lines, key=lambda L: L["start_s"]) if ln["id"] in own]
    for la, lb in zip(order, order[1:]):
        end = max(b for _, b in own[la["id"]])
        start = min(a for a, _ in own[lb["id"]])
        out.append({"from": la["id"], "to": lb["id"], "end_s": end, "next_start_s": start, "pause_s": round(start - end, 3)})
    return out


def measure(path: Path, timeline: dict | None = None, x: np.ndarray | None = None) -> dict:
    """The report of one delivered file (``x`` lets a test pass samples instead of a file)."""
    x = read_audio(Path(path)) if x is None else np.asarray(x, np.float32)
    tl = timeline or {}
    dur = len(x) / SR
    win_s = SR_RULES.T("BP-189", "window_ms") / 1000.0
    floor, dead = SR_RULES.T("BP-189", "floor_dbfs"), SR_RULES.T("BP-189", "dead_dbfs")
    wdb = window_db(x, win_s)
    centres = (np.arange(len(wdb)) + 0.5) * win_s
    body = (centres >= 1.0) & (centres <= dur - 1.0) if dur > 3.0 else np.ones(len(wdb), bool)
    spans = speech_spans(x, ref_spans=tl.get("dialogue"))
    rows, meas = [], {"duration_s": round(dur, 3), "speech_spans": spans}

    # 1. dropouts
    q = float(wdb[body].min()) if body.any() else None
    at = float(centres[body][int(np.argmin(wdb[body]))]) if body.any() else None
    meas["quietest_window"] = {"dbfs": None if q is None else round(q, 1), "at_s": None if at is None else round(at, 2)}
    meas["share_below_dbfs"] = {"-40": round(float(np.mean(wdb[body] < -40)), 3) if body.any() else None,
                                "-50": round(float(np.mean(wdb[body] < -50)), 3) if body.any() else None}
    rows.append(G.row("no_dropout", None if q is None else q >= floor,
                      f"quietest {win_s * 1000:.0f} ms window {q if q is None else round(q, 1)} dBFS at {at if at is None else round(at, 2)} s"
                      f" (BP-189 floor {floor} dBFS)", meas["quietest_window"], level=SR_RULES.level("BP-189")))

    # 2. dead air in the dialogue part
    dlg = tl.get("dialogue") or [[0.0, dur]]
    pauses = tl.get("intended_pauses") or []
    in_dlg = _mask(len(wdb), win_s, dlg) & ~_mask(len(wdb), win_s, pauses)
    share = float(np.mean(wdb[in_dlg] < dead)) if in_dlg.any() else None
    meas["dialogue_dead_share"] = None if share is None else round(share, 3)
    rows.append(G.row("dialogue_never_dead", None if share is None else share <= SR_RULES.T("BP-189", "dead_share_max"),
                      f"{0 if share is None else round(100 * share)} % of the dialogue part under {dead} dBFS (BP-189 max "
                      f"{SR_RULES.T('BP-189', 'dead_share_max') * 100:.0f} %; intended pauses left out: {len(pauses)})",
                      meas["dialogue_dead_share"], level=SR_RULES.level("BP-189")))

    # 3. pauses line to line
    lo, hi = SR_RULES.T("BP-190", "pause_s")
    drama = SR_RULES.T("BP-190", "dramatic_max_s")
    dspans = sorted((max(a, s0), min(b, s1)) for a, b in spans for s0, s1 in dlg if min(b, s1) - max(a, s0) > 0.05)
    ps = line_pauses(dspans, tl.get("lines"))
    for p in ps:
        intended = any(a - 0.3 <= p["end_s"] and p["next_start_s"] <= b + 0.3 for a, b in pauses)
        p["intended"] = intended
        p["ok"] = (p["pause_s"] <= drama) if intended else (lo <= p["pause_s"] <= hi)
    meas["line_pauses"] = ps
    bad = [p for p in ps if not p["ok"]]
    rows.append(G.row("pause_line_to_line", None if not ps else not bad,
                      ("no two lines in the dialogue part" if not ps else
                       f"{len(ps)} pauses {[p['pause_s'] for p in ps]} s; outside {lo}-{hi} s (intended: <= {drama} s): "
                       f"{[(p['from'], p['to'], p['pause_s']) for p in bad]} (BP-190)"),
                      [p["pause_s"] for p in ps], level=SR_RULES.level("BP-190")))

    # 4. the bed across cuts
    cuts = tl.get("cuts")
    jump_max, side = SR_RULES.T("BP-191", "cut_jump_db_max"), SR_RULES.T("BP-191", "cut_window_s")
    if cuts is None:
        rows.append(G.row("bed_across_cuts", None, "no timeline: the cuts are not known"))
    else:
        w100 = window_db(x, 0.1)
        c100 = (np.arange(len(w100)) + 0.5) * 0.1
        # speech padded by 0.15 s: a line's breath and decay are not the bed (love scene 2026-11-12: a 0.5 s pause measured as a
        # 10 dB "jump" from the breath alone); each side's level is the median of its quiet windows within the side window,
        # or, when a short pause leaves fewer than two there, of the three quiet windows of that shot nearest the cut
        quiet = ~_mask(len(w100), 0.1, _pad(spans, 0.15, dur))
        cut_rows = []
        bounds = [0.0] + sorted(cuts) + [dur]

        def side_level(c, sign):
            k = bounds.index(c)
            lo_t, hi_t = (bounds[k - 1], c) if sign < 0 else (c, bounds[k + 1])
            near = quiet & ((c100 >= c - side) & (c100 < c) if sign < 0 else (c100 >= c) & (c100 < c + side))
            if near.sum() >= 2:
                return float(np.median(w100[near]))
            idx = np.flatnonzero(quiet & (c100 >= lo_t) & (c100 < hi_t))
            if not len(idx):
                return None
            idx = idx[np.argsort(np.abs(c100[idx] - c))[:3]]
            return float(np.median(w100[idx]))

        for c in cuts:
            la, lb = side_level(c, -1), side_level(c, +1)
            near = (c100 >= c - side) & (c100 < c + side)
            low = float(w100[near].min()) if near.any() else None
            cut_rows.append({"cut_s": c, "before_db": None if la is None else round(la, 1),
                             "after_db": None if lb is None else round(lb, 1),
                             "jump_db": None if la is None or lb is None else round(abs(la - lb), 1),
                             "lowest_100ms_db": None if low is None else round(low, 1)})
        meas["cuts"] = cut_rows
        jumps = [r for r in cut_rows if r["jump_db"] is not None]
        badc = [r for r in jumps if r["jump_db"] > jump_max]
        rows.append(G.row("bed_across_cuts", None if not jumps else not badc,
                          ("no speech-free background next to any cut" if not jumps else
                           f"background jump at {len(jumps)} cuts {[r['jump_db'] for r in jumps]} dB (BP-191 max {jump_max})"),
                          [r["jump_db"] for r in jumps], level=SR_RULES.level("BP-191")))
        broken = [r for r in cut_rows if r["lowest_100ms_db"] is not None and r["lowest_100ms_db"] < floor]
        rows.append(G.row("bed_not_broken_at_cut", bool(cut_rows) and not broken if cut_rows else None,
                          f"lowest 100 ms within {side} s of each cut {[r['lowest_100ms_db'] for r in cut_rows]} dBFS "
                          f"(BP-189 floor {floor})", [r["lowest_100ms_db"] for r in cut_rows],
                          level=SR_RULES.level("BP-189")))

    # 5. action sounds heard: the event's loudest 100 ms against the windows around it in the same state (speech or not), so a
    # sound under the narrator is compared with the narrator and a sound in a gap with the bed
    evs = tl.get("events")
    heard_min = SR_RULES.T("BP-192", "heard_min_db")
    t_lo, t_hi = SR_RULES.T("BP-192", "target_above_bed_db")
    if not evs:
        why = "no timeline: no planned action sounds to look for" if evs is None else "the timeline plans no action sound"
        rows.append(G.row("action_sounds_heard", None, why))
        rows.append(G.row("action_sounds_level", None, why))
    else:
        w100 = window_db(x, 0.1)
        c100 = (np.arange(len(w100)) + 0.5) * 0.1
        bands = band_windows(x, 0.1)[:, :len(w100)]
        talk = _mask(len(w100), 0.1, spans)
        others = [(float(e["at_s"]), float(e["at_s"]) + max(0.15, float(e.get("dur_s", 0.15)))) for e in evs]
        er = []
        for (a0, a1), e in zip(others, evs):
            inside = (c100 >= a0 - 0.05) & (c100 < a1 + 0.05)
            if not inside.any():
                continue
            state = bool(np.median(talk[inside]) >= 0.5)
            around = ((c100 >= a0 - 2.0) & (c100 < a1 + 2.0)) & ~inside & (talk == state) & ~_mask(len(w100), 0.1, others)
            if not around.any():
                continue
            peak = float(w100[inside].max())
            bed = float(np.median(w100[around]))
            # heard where it is not masked: the largest rise of one band over that band around it (a tick over the narrator
            # rises in the highs, a thud in the lows), counting only bands that carry a real share of the window (BAND_SHARE_DB)
            rise, best = peak - bed, None
            k_in = np.flatnonzero(inside)
            top = bands[:, k_in].max(axis=1)
            live = top >= top.max() - BAND_SHARE_DB
            for b in np.flatnonzero(live):
                r = float(top[b] - np.median(bands[b, around]))
                if r > rise:
                    rise, best = r, b
            er.append({"class": e.get("class"), "at_s": a0, "under_speech": state, "peak_db": round(peak, 1),
                       "around_db": round(bed, 1), "broadband_rise_db": round(peak - bed, 1),
                       "band_hz": None if best is None else [round(BED_EDGES_HZ[best]), round(BED_EDGES_HZ[best + 1])],
                       "above_bed_db": round(rise, 1)})
        meas["events"] = er
        unheard = [r for r in er if r["above_bed_db"] < heard_min]
        off = [r for r in er if not t_lo <= r["above_bed_db"] <= t_hi]
        rows.append(G.row("action_sounds_heard", (not unheard) if er else None,
                          f"{len(er)} action sounds measured, {len(unheard)} under {heard_min} dB over what plays around them "
                          f"{[(r['class'], r['at_s'], r['above_bed_db']) for r in unheard][:6]} (BP-192)",
                          [r["above_bed_db"] for r in er], level=SR_RULES.level("BP-192")))
        rows.append(G.row("action_sounds_level", (not off) if er else None,
                          f"{len(off)} of {len(er)} outside {t_lo}-{t_hi} dB over what plays around them (BP-192 target, REVIEW)",
                          [r["above_bed_db"] for r in er], level=G.REVIEW))

    # 6. one generated noise everywhere: the bed-only spectrum of each place
    dev_max, min_places = SR_RULES.T("BP-193", "same_spectrum_share_max"), SR_RULES.T("BP-193", "min_places")
    pr = bed_spectra(x, spans, evs or [], tl.get("places"), SR_RULES.T("BP-193", "place_min_s"))
    meas["bed_by_place"] = pr
    measured = [p for p in pr if p["bands"] is not None]
    if len(measured) < min_places:
        rows.append(G.row("not_one_noise_everywhere", None,
                          f"{len(measured)} places with enough bed-only time; the check needs {min_places}"))
    else:
        vec = np.array([p["bands"] for p in measured])
        dev = float(np.max(np.abs(vec - vec.mean(axis=0))))
        rows.append(G.row("not_one_noise_everywhere", dev > dev_max,
                          f"{len(measured)} places, largest band-share deviation of their beds {dev:.3f} (one spectrum in "
                          f"every place under {dev_max}: one noise plays everywhere, BP-193)", round(dev, 3),
                          level=SR_RULES.level("BP-193")))
    return {"schema": SCHEMA, "file": str(path), "measured": meas, "reference": REFERENCE, "rows": rows,
            "verdict": G.verdict(rows)["status"], "gates": G.verdict(rows)}


BED_EDGES_HZ = tuple(float(v) for v in np.geomspace(60, 7900, 9))
BAND_SHARE_DB = 10.0      # a band counts for "heard" only within this far of the window's strongest band


def band_windows(x: np.ndarray, win_s: float, rate: int = SR) -> np.ndarray:
    """dB of each of the 8 ``BED_EDGES_HZ`` bands per window of ``win_s`` (rows: bands)."""
    w = max(1, int(round(win_s * rate)))
    k = len(x) // w
    if k == 0:
        return np.zeros((8, 0))
    fr = np.asarray(x[:k * w], np.float64).reshape(k, w) * np.hanning(w)
    p = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(w, 1 / rate)
    out = np.stack([p[:, (f >= lo) & (f < hi)].sum(axis=1) for lo, hi in zip(BED_EDGES_HZ, BED_EDGES_HZ[1:])])
    return 10 * np.log10(out + 1e-18)


def bed_spectra(x: np.ndarray, spans, events: list[dict], places: list[dict] | None, min_s: float) -> list[dict]:
    """Per place: the band shares (8 log bands, 60 Hz - 7.9 kHz) of its bed-only 50 ms frames: no speech, no planned event,
    the quieter half of the rest."""
    w = int(0.05 * SR)
    k = len(x) // w
    if k == 0:
        return []
    dur = len(x) / SR
    fr = np.asarray(x[: k * w], np.float64).reshape(k, w)
    lv = 10 * np.log10((fr ** 2).mean(axis=1) + 1e-18)
    c = (np.arange(k) + 0.5) * 0.05
    busy = _pad(spans, 0.1, dur) + [(float(e["at_s"]) - 0.1, float(e["at_s"]) + float(e.get("dur_s", 0.3)) + 0.2)
                                    for e in events]
    free = ~_mask(k, 0.05, busy) & (lv > -80)
    f = np.fft.rfftfreq(w, 1 / SR)
    win = np.hanning(w)
    out = []
    spans_of: dict[str, list] = {}
    for p in places or [{"start_s": 0.0, "end_s": dur, "place": "all"}]:
        spans_of.setdefault(p["place"], []).append((p["start_s"], p["end_s"]))
    for name, ss in spans_of.items():
        p = {"place": name}
        m = free & _mask(k, 0.05, ss)
        if m.any():
            m &= lv <= np.percentile(lv[m], 50)
        if m.sum() * 0.05 < min_s:
            out.append({"place": p["place"], "bed_s": round(m.sum() * 0.05, 2), "bands": None})
            continue
        spec = (np.abs(np.fft.rfft(fr[m] * win, axis=1)) ** 2).mean(axis=0)
        b = np.array([spec[(f >= lo) & (f < hi)].sum() for lo, hi in zip(BED_EDGES_HZ, BED_EDGES_HZ[1:])])
        out.append({"place": p["place"], "bed_s": round(m.sum() * 0.05, 2), "level_db": round(float(np.median(lv[m])), 1),
                    "bands": [round(float(v), 4) for v in b / max(b.sum(), 1e-18)]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sound_realism")
    ap.add_argument("video")
    ap.add_argument("--timeline")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    tl = json.loads(Path(a.timeline).read_text(encoding="utf-8")) if a.timeline else None
    rep = measure(Path(a.video), tl)
    if a.out:
        write_json_atomic(Path(a.out), rep)
    for r in rep["rows"]:
        print(f"{r['status']:8} {r['gate']:28} {r['detail']}")
    print("VERDICT", rep["verdict"])
    return 0 if rep["verdict"] in (G.PASS, G.REVIEW) else 1


if __name__ == "__main__":
    sys.exit(main())
