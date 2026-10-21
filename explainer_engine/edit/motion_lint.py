"""Motion and visual-change rules MO-01..MO-07 (docs/STORY_ENGINE.md, D-48) on a timed production script.

Episode 1 (measured 2026-10-19 on its production script): 217 shots, a picture change every 5.0 s on average, but every
change the same kind (161 pushes, 54 pans, zoom at most 1.08), 89 of the changes a reframe of the same picture, no
transition but the cut, 8 bubbles and 11 data visuals in 18 minutes. The rate was fine; the sameness read as a
slideshow. These rules measure *events* (anything new the eye gets: a new picture, a reframe, an accent, a bubble, a
data visual, a card, a visual beat) and their *variety*, not only the cut rate. The MO findings are REVIEW: the creator judges
the cut. MO-01's still limits are BP-40's, section by section (the hook window, then the body's REVIEW line; the board's RHYTHM-3
gates the same events); MO-02..MO-07 read BP-83 (a hypothesis) and MO-05's word cap BP-38.
``check_sourced`` adds the sourced motion, text and face rules (BP-20..BP-33, docs/SOURCED_RULES.md): their thresholds come
from the registry and their severity is the registry's (a hypothesis or house rule never FAILs).

    findings = check(timed)      # list of {rule, severity, where, detail}; includes check_sourced(timed)
    report = measure(timed)      # numbers for the review bundle
"""

from __future__ import annotations

import re
from collections import Counter

from explainer_engine.production import accents as ACC
from explainer_engine.standards import sourced_rules as SR

HOOK_WINDOW = float(SR.T("BP-40", "hook_window_s"))  # MO-01 = BP-40: inside the hook window ...
HOOK_MAX_GAP = float(SR.T("BP-40", "hook_max_still_s"))  # ... seconds without any new visual event
MAX_GAP = float(SR.T("BP-40", "body_review_still_s"))  # ... and in the body (its REVIEW line)
WINDOW, MIN_KINDS = float(SR.T("BP-83", "window_s")), int(SR.T("BP-83", "kinds_min"))  # MO-02: kinds of event a minute
MAX_PLAIN_RUN = int(SR.T("BP-83", "plain_run_max"))  # MO-03: consecutive shots that are only a camera move
ENTRY_MIN_GAP = SR.T("BP-25", "entry_min_gap_s")  # MO-04 / BP-25: seconds between two whips or flashes
TEXT_MIN_GAP = float(SR.T("BP-83", "text_min_gap_s"))  # MO-05: seconds between two pop/slam words
MAX_WORDS = int(SR.T("BP-38", "max_words"))  # MO-05: words in one pop/slam (the beats' VB-04 cap)
HOLD_SIMILAR = float(SR.T("BP-83", "hold_similar"))  # MO-07: consecutive holds this close read as a metronome ...
MAX_SIMILAR_RUN = int(SR.T("BP-83", "similar_run_max"))  # ... when more than this many in a row
HOLD_CV = float(SR.T("BP-83", "hold_cv_min"))  # MO-07: a segment of CV_FROM+ shots whose holds vary less is a slideshow
CV_FROM = int(SR.T("BP-83", "cv_from_shots"))
ENTRY = {"whip_in", "flash_in"}
TEXT = {"pop_text", "slam_text"}


def events(timed: dict) -> list[tuple[float, str]]:
    """(time, kind) of every visual event, sorted."""
    ev: list[tuple[float, str]] = []
    prev = None
    for s in timed["shots"]:
        ev.append((s["start"], "reframe" if s["picture"] == prev else "picture"))
        prev = s["picture"]
        for a in s.get("accents", []):
            if a["kind"] != "wobble" and a.get("anchored", True):  # BP-93: an accent an untied beat made is no change
                ev.append((a["start"], a["kind"]))
        for b in s.get("bubbles", []):
            ev.append((b["start"], "bubble"))
    for g in timed.get("visuals", []):
        ev.append((g["start"], "visual"))
    for c in timed.get("cards", []):
        ev.append((c["start"], "card"))
    for b in timed.get("visual_beats", []):  # VB rules: the lines' visual beats (an accent beat is already a shot accent)
        if b["kind"] != "accent" and b.get("anchored", True):  # BP-93: only a beat tied to a narration word is new
            ev.append((b["start"], "beat_" + b["kind"]))
    return sorted(ev)


def _alive(s: dict) -> bool:
    return bool(s.get("accents") or s.get("bubbles") or s.get("speaker") or s.get("visual_beats"))


def measure(timed: dict) -> dict:
    ev = events(timed)
    times = [t for t, _ in ev] + [timed["duration"]]
    gaps = [b - a for a, b in zip(times, times[1:])]
    shots = timed["shots"]
    return {"events": len(ev), "per_minute": round(len(ev) / max(timed["duration"], 1e-6) * 60, 1),
            "mean_gap": round(sum(gaps) / max(1, len(gaps)), 2), "max_gap": round(max(gaps, default=0.0), 2),
            "kinds": dict(Counter(k for _, k in ev)),
            "alive_share": round(sum(_alive(s) for s in shots) / max(1, len(shots)), 2),
            "transitions": dict(Counter(s.get("transition", "cut") for s in shots))}


FLASHES = {"flash_in"}  # BP-26: the accents that step the whole frame to white (a whip slides, a slam only jolts)
_WORD = re.compile(r"[a-z']+")


def _sev(rule_id: str) -> str:
    """The registry's severity for a rule's hard case (a hypothesis or house rule is never more than REVIEW)."""
    return SR.rule(rule_id).get("severity", "REVIEW")


def _move(s: dict) -> tuple[float, float, float, float, str, dict]:
    """(z0, z1, x0, x1, kind, the move dict) of what the assembler draws: ``render_motion`` (production/continuity.py)
    when the shot is chained, else the script's ``motion`` (``dx`` = a pan from -dx/2 to +dx/2 of the width)."""
    m = s.get("render_motion") or s.get("motion") or {}
    z0 = float(m.get("z0", 1.0))
    z1 = float(m.get("z1", z0))
    if "x0" in m:
        x0, x1 = float(m["x0"]), float(m.get("x1", m["x0"]))
    else:
        dx = float(m.get("dx", 0.0))
        x0, x1 = -dx / 2, dx / 2
    return z0, z1, x0, x1, str(m.get("kind", "hold")), m


def check_sourced(timed: dict) -> list[dict]:
    """The sourced rules on a timed script (docs/SOURCED_RULES.md). What the data carries and what it does not:

    * BP-20/21/22 read the shot's move (``render_motion`` or ``motion``: z0, z1, x0/x1 or dx) and its duration; the
      default-push cap reads the planner's ``motion`` (a chained continuation may run on to scale_max); a ``punch``
      accent is exempt (it stacks on the move, BP-20 names the stack cap separately).
    * BP-23: the schema has no easing field, so a declared ``easing: "linear"`` is honoured if a move ever carries one;
      otherwise the check reads continuity's ``ein``/``eout`` flags (a chained move runs linear through a cut inside one
      picture) and asks a brisk move (over BP-21's rate_max) for an eased end on both sides and room for the end holds.
    * BP-24: a ``shake`` accent needs one of the registry's impact words in its shot's narration (``shots[].text``); its
      amplitude is accents.SHAKE_AMP x strength and its decay accents.SHAKE_S (an accent may carry ``decay_s``).
    * BP-26 counts ``flash_in`` starts in any 1 s window (whip_in has no white frame, slam_text only jolts).
    * BP-27 measures a popped word's hold as the render does (accents.text_hold, cut by the shot's end) and a text/label
      beat's end - start; BP-28 reads the accent's or beat's ``pos`` (shares of the frame).
    * BP-31: a dissolve must open a scene: ``time_jump`` / ``place_change`` on the shot (timing sets ``place_change`` where
      the segment's scene place or time changes), a card starting with it, or a ``period`` field that changes; it lasts
      dissolve_s to dissolve_max_s (the creator, 2026-10-20 21:14, RX-08).
    * BP-32/33 read the expression beats (``visual_beats`` kind expression): the word is start - offset, the close-up is
      drawn accents.EXPR_LEAD_FRAMES early (production/faces.composite), the hold is end - start. Mouth shapes are not in
      the data (no lip sync in this pipeline), so BP-33's mouth floor is not checked.
    """
    out: list[dict] = []

    def add(rule, sev, where, detail):
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    fps = int(timed.get("fps", 30))
    shots = timed["shots"]
    z_min, z_max, push_max = SR.T("BP-20", "scale_min"), SR.T("BP-20", "scale_max"), SR.T("BP-20", "push_default_max")
    r_min, r_max, rushed = SR.T("BP-21", "rate_min_per_s"), SR.T("BP-21", "rate_max_per_s"), SR.T("BP-21", "rushed_per_s")
    pan_max = SR.T("BP-22", "pan_max_width_per_s")
    end_hold = SR.T("BP-23", "end_hold_min_s")
    impact = set(SR.T("BP-24", "impact_words"))
    amp_max, decay_max = SR.T("BP-24", "amplitude_max_h"), SR.T("BP-24", "decay_max_s")
    hold_min, s_per_word, hold_max = SR.T("BP-27", "hold_min_s"), SR.T("BP-27", "s_per_word"), SR.T("BP-27", "hold_max_s")
    safe_x, safe_y = SR.T("BP-28", "safe_x"), SR.T("BP-28", "safe_y")
    dissolve_s, dissolve_max = SR.T("BP-31", "dissolve_s"), SR.T("BP-31", "dissolve_max_s")
    period_starts = {round(float(c["start"]), 3) for c in timed.get("cards", [])}
    flashes: list[float] = []
    prev = None
    for s in shots:
        sid = s["id"]
        dur = max(0.0, float(s["end"]) - float(s["start"]))
        z0, z1, x0, x1, kind, m = _move(s)
        lo, hi = min(z0, z1), max(z0, z1)
        if hi > z_max + 1e-9 or lo < z_min - 1e-9:
            add("BP-20", _sev("BP-20"), sid, f"scale {z0:.3f}->{z1:.3f} outside {z_min:.2f}-{z_max:.2f}")
        else:  # the default push cap is judged on the move the planner wrote; a chained continuation may run on to scale_max
            planned = s.get("motion") or m
            if planned.get("kind") == "push" and float(planned.get("z1", 1.0)) > push_max + 1e-9:
                add("BP-20", "REVIEW", sid, f"push to {float(planned['z1']):.3f}: the default push stops at {push_max:.2f}")
        dz = abs(z1 - z0)
        if dz > 1e-9 and dur > 1e-6:
            rate = dz / dur
            if rate > rushed + 1e-9:
                add("BP-21", "REVIEW", sid, f"scale changes {rate:.1%} a second ({z0:.2f}->{z1:.2f} in {dur:.1f} s): rushed; "
                    f"over {rushed:.0%}/s only a punch accent moves that fast")
            elif rate > r_max + 1e-9:
                add("BP-21", "REVIEW", sid, f"scale changes {rate:.1%} a second (at most {r_max:.1%}/s for a push or pull)")
            elif rate < r_min - 1e-9:
                add("BP-21", "REVIEW", sid, f"scale changes {rate:.2%} a second: under {r_min:.1%}/s the move is not seen")
            if rate > r_max + 1e-9:
                if not (m.get("ein", True) and m.get("eout", True)):
                    add("BP-23", "REVIEW", sid, "a brisk move runs linear through a cut inside the picture: ease both ends")
                if dur < 2 * end_hold - 1e-9:
                    add("BP-23", "REVIEW", sid, f"a brisk move in {dur:.2f} s leaves no {end_hold:.2f} s hold at its ends")
        if str(m.get("easing", "")).lower() == "linear":
            add("BP-23", "REVIEW", sid, "a linear camera move: every move is eased in and out")
        pan = abs(x1 - x0)
        if pan > 1e-9 and dur > 1e-6 and pan / dur > pan_max + 1e-9:
            add("BP-22", _sev("BP-22"), sid, f"pan of {pan:.1%} of the width in {dur:.1f} s ({pan / dur:.1%}/s; at most "
                f"{pan_max:.1%}/s, the judder rule)")
        if s.get("transition") == "dissolve" and prev is not None:
            opens = bool(s.get("time_jump") or s.get("place_change")) or round(float(s["start"]), 3) in period_starts \
                or ("period" in s and s.get("period") != prev.get("period"))
            if not opens:
                add("BP-31", _sev("BP-31"), sid, "dissolve inside a scene: a dissolve marks a change of time or place; "
                    "inside a scene every transition is a hard cut")
            ts = float(s.get("transition_seconds", dissolve_s))
            if not dissolve_s - 1e-6 <= ts <= dissolve_max + 1e-6:
                add("BP-31", "REVIEW", sid, f"dissolve of {ts:.2f} s (a dissolve lasts {dissolve_s:g}-{dissolve_max:g} s)")
        words = set(_WORD.findall(str(s.get("text", "")).lower()))
        for a in s.get("accents", []):
            k = a["kind"]
            if k == "shake":
                if not words & impact:
                    add("BP-24", "REVIEW", sid, "shake on a shot whose narration names no impact (hit, crash, fall, blast...): a "
                        "shake is an accent on an impact beat, never a move and never on a dialogue-only shot")
                amp = ACC.SHAKE_AMP * float(a.get("strength", 0.6))
                if amp > amp_max + 1e-9:
                    add("BP-24", _sev("BP-24"), sid, f"shake amplitude {amp:.1%} of the frame (at most {amp_max:.0%})")
                if float(a.get("decay_s", ACC.SHAKE_S)) > decay_max + 1e-9:
                    add("BP-24", _sev("BP-24"), sid, f"shake decays over {float(a.get('decay_s', ACC.SHAKE_S)):.2f} s (at most "
                        f"{decay_max:.1f} s)")
            if k in FLASHES:
                flashes.append(float(a["start"]))
            if k in TEXT and a.get("text"):
                n = len(str(a["text"]).split())
                hold = min(ACC.text_hold(a["text"], k), float(s["end"]) - float(a["start"]))
                floor = max(hold_min, s_per_word * n)
                if hold > hold_max + 1e-6:
                    add("BP-27", "REVIEW", sid, f"{a['text']!r} stays {hold:.1f} s (at most {hold_max:.0f} s)")
                elif hold < floor - 1e-6:
                    add("BP-27", "REVIEW", sid, f"{a['text']!r} is readable for {hold:.2f} s only (the shot ends); {n} word(s) "
                        f"need {floor:.2f} s")
                _safe(add, sid, a.get("pos"), safe_x, safe_y, a["text"])
        prev = s
    _flash_windows(add, flashes)
    for b in timed.get("visual_beats", []):
        if b.get("kind") in ("text", "label") and b.get("text"):
            n = len(str(b["text"]).split())
            hold = float(b.get("end", b["start"])) - float(b["start"])
            floor = max(hold_min, s_per_word * n)
            where = f"{b.get('segment', '?')} line {b.get('line', '?')}"
            if hold > hold_max + 1e-6:
                add("BP-27", "REVIEW", where, f"{b['text']!r} stays {hold:.1f} s (at most {hold_max:.0f} s)")
            elif hold < floor - 1e-6:
                add("BP-27", "REVIEW", where, f"{b['text']!r} is readable for {hold:.2f} s only; {n} word(s) need {floor:.2f} s")
            _safe(add, where, b.get("pos"), safe_x, safe_y, b["text"])
    _expressions(add, timed, fps)
    return out


def _safe(add, where, pos, safe_x, safe_y, text) -> None:
    if not pos:
        return
    x, y = float(pos[0]), float(pos[1])
    if not (safe_x[0] - 1e-9 <= x <= safe_x[1] + 1e-9 and safe_y[0] - 1e-9 <= y <= safe_y[1] + 1e-9):
        add("BP-28", "REVIEW", where, f"{text!r} at ({x:.2f}, {y:.2f}) sits outside the text safe area x {safe_x[0]:.3f}-"
            f"{safe_x[1]:.3f}, y {safe_y[0]:.2f}-{safe_y[1]:.2f}")


def _flash_windows(add, starts: list[float]) -> None:
    per_s = SR.T("BP-26", "flashes_per_s_max")
    starts = sorted(starts)
    done: set[float] = set()
    for t in starts:
        n = sum(1 for x in starts if t <= x < t + 1.0)
        if n > per_s and t not in done:
            done.add(t)
            add("BP-26", _sev("BP-26"), f"{t:.1f}s", f"{n} flashes inside one second (at most {per_s}): photosensitivity")


def _expressions(add, timed: dict, fps: int) -> None:
    lead_lo, lead_hi = SR.T("BP-32", "lead_frames")
    lag_max = SR.T("BP-32", "lag_max_frames")
    hold_min = SR.T("BP-33", "hold_min_s")
    beats = [b for b in timed.get("visual_beats", []) if b.get("kind") == "expression"]
    for k, b in enumerate(beats):
        where = f"{b.get('segment', '?')} line {b.get('line', '?')} {b.get('who', '')}".rstrip()
        word_frame = int(round((float(b["start"]) - float(b.get("offset", 0.0))) * fps))
        shown = int(b.get("start_frame", round(float(b["start"]) * fps))) - int(b.get("lead_frames", ACC.EXPR_LEAD_FRAMES))
        lead = word_frame - shown
        if lead < -lag_max:
            add("BP-32", _sev("BP-32"), where, f"{b.get('expression')} lands {-lead} frame(s) after its word {b.get('at')!r}: "
                f"an expression answers {lead_lo}-{lead_hi} frames before the word, never after it")
        elif lead < lead_lo:
            add("BP-32", "REVIEW", where, f"{b.get('expression')} lands on its word {b.get('at')!r}: lead it by "
                f"{lead_lo}-{lead_hi} frames")
        elif lead > lead_hi:
            add("BP-32", "REVIEW", where, f"{b.get('expression')} lands {lead} frames before its word {b.get('at')!r} "
                f"(at most {lead_hi}): it reads as a reaction to nothing")
        hold = float(b.get("end", b["start"])) - float(b["start"])
        nxt = next((x for x in beats[k + 1:] if x.get("who") == b.get("who")), None)
        if hold < hold_min - 1e-6:
            if nxt is not None and float(nxt["start"]) - float(b["start"]) < hold_min - 1e-6:
                add("BP-33", _sev("BP-33"), where, f"{b.get('who')} changes {b.get('expression')} -> {nxt.get('expression')} "
                    f"{float(nxt['start']) - float(b['start']):.2f} s apart (at least {hold_min:.1f} s between two changes)")
            else:
                add("BP-33", _sev("BP-33"), where, f"{b.get('expression')} holds {hold:.2f} s (at least {hold_min:.1f} s)")


def exchange_holds(timed: dict) -> list[dict]:
    """BP-94 (a hypothesis, REVIEW): after a segment's last hero line the picture holds the hero's mood at least hold_min_s
    before the next cut, under the narrator's conclusion (RX-07)."""
    hold = float(SR.T("BP-94", "hold_min_s"))
    out = []
    last: dict = {}
    for ln in timed.get("lines", []):
        if ln.get("speaker"):
            last[ln["segment"]] = ln
    cuts = sorted(float(s["start"]) for s in timed["shots"])
    for seg, ln in last.items():
        end = float(ln["end"])
        nxt = next((c for c in cuts if c > end - 1e-6), None)
        if nxt is not None and nxt - end < hold - 1e-6:
            out.append({"rule": "BP-94", "severity": SR.rule("BP-94").get("severity", "REVIEW"), "where": f"{seg} line {ln['line']}",
                        "detail": f"a cut {nxt - end:.1f} s after the exchange's last line: hold the hero's mood at least "
                                  f"{hold:g} s under the narrator's conclusion, then move slowly to the next scene (BP-94)"})
    return out


def check(timed: dict) -> list[dict]:
    out: list[dict] = []
    mo = SR.rule("BP-83").get("severity", "REVIEW")  # MO-02..MO-07: a hypothesis, REVIEW

    def add(rule, where, detail, sev=None):
        out.append({"rule": rule, "severity": sev or mo, "where": where, "detail": detail})

    out += check_sourced(timed)  # BP-20..33 (docs/SOURCED_RULES.md); the MO rules follow
    ev = events(timed)
    dur = timed["duration"]
    times = [0.0] + [t for t, _ in ev] + [dur]
    for a, b in zip(times, times[1:]):  # MO-01 on BP-40's section limits (REVIEW; RHYTHM-3 on the board is the gate)
        hook, body = max(0.0, min(b, HOOK_WINDOW) - a), max(0.0, b - max(a, HOOK_WINDOW))
        if hook > HOOK_MAX_GAP + 1e-6 or body > MAX_GAP + 1e-6:
            limit = HOOK_MAX_GAP if hook > HOOK_MAX_GAP + 1e-6 else MAX_GAP
            add("MO-01", f"{a:.1f}s", f"{b - a:.1f} s with nothing new on screen: add an accent, a bubble, a reframe, a visual or "
                f"a beat (at most {limit:.0f} s {'in the hook' if limit == HOOK_MAX_GAP else 'in the body'}, BP-40)", "REVIEW")
    t = 0.0
    while t + WINDOW <= dur + 1e-6:
        kinds = {k for x, k in ev if t <= x < t + WINDOW}
        if len(kinds) < MIN_KINDS:
            add("MO-02", f"{t:.0f}-{t + WINDOW:.0f}s", f"only {len(kinds)} kind(s) of visual event ({', '.join(sorted(kinds)) or 'none'}); "
                f"a minute needs at least {MIN_KINDS} (pictures, reframes, accents, bubbles, visuals)")
        t += WINDOW
    run: list[str] = []
    for s in timed["shots"] + [{"id": "<end>", "accents": [{"kind": "end"}]}]:
        plain = not _alive(s) and not any(g["start_frame"] < s.get("end_frame", 0) and g["end_frame"] > s.get("start_frame", 0)
                                          for g in timed.get("visuals", []))
        if plain:
            run.append(s["id"])
            continue
        if len(run) > MAX_PLAIN_RUN:
            add("MO-03", run[0], f"{len(run)} shots in a row are only a camera move ({run[0]}..{run[-1]}): a slideshow run, "
                f"at most {MAX_PLAIN_RUN}")
        run = []
    last_entry = last_text = None
    seg_first = {}
    for s in timed["shots"]:
        seg_first.setdefault(s["segment"], s["id"])
    for s in timed["shots"]:
        for a in s.get("accents", []):
            if a["kind"] in ENTRY:
                if seg_first[s["segment"]] != s["id"]:
                    add("MO-04", s["id"], f"{a['kind']} inside a segment: a whip or flash marks a story turn, so it opens a segment")
                if last_entry is not None and a["start"] - last_entry < ENTRY_MIN_GAP:
                    add("MO-04", s["id"], f"{a['kind']} {a['start'] - last_entry:.0f} s after the last one (at least {ENTRY_MIN_GAP:.0f} s)")
                last_entry = a["start"]
            if a["kind"] in TEXT:
                if last_text is not None and a["start"] - last_text < TEXT_MIN_GAP:
                    add("MO-05", s["id"], f"words pop {a['start'] - last_text:.0f} s after the last ones (at least {TEXT_MIN_GAP:.0f} s): "
                        "on-screen words are for the one word that matters")
                if len(a.get("text", "").split()) > MAX_WORDS:
                    add("MO-05", s["id"], f"more than {MAX_WORDS} words on screen (BP-38)")
                last_text = a["start"]
    m = measure(timed)
    if timed["shots"]:  # MO-06 is reported only (BP-83: the creator, 2026-10-20 21:14; a target pushed accents onto plain shots)
        add("MO-06", "video", f"{m['alive_share']:.0%} of shots have motion besides the camera (accent, bubble or beat); "
            "reported only, no target (BP-83)", "INFO")
    out += exchange_holds(timed)
    # MO-07 rhythm follows content, not a clock: a run of near-equal holds, or a whole segment of them, is a metronome
    holds = [(s["segment"], s["id"], s["end"] - s["start"]) for s in timed["shots"] if "end" in s and "start" in s]
    same_run = 1
    for (seg_a, _, a), (seg_b, sid, b) in zip(holds, holds[1:]):
        same = seg_a == seg_b and max(a, b) > 0 and abs(b - a) / max(a, b) <= HOLD_SIMILAR
        same_run = same_run + 1 if same else 1
        if same_run == MAX_SIMILAR_RUN + 1:
            add("MO-07", sid, f"{same_run} shots in a row hold almost the same time (~{b:.1f} s, within ±{HOLD_SIMILAR:.0%}): "
                "a metronome cut; hold long on wonder, cut short on action")
    by_seg: dict = {}
    for seg, _, h in holds:
        by_seg.setdefault(seg, []).append(h)
    for seg, hs in by_seg.items():
        if len(hs) >= CV_FROM:
            mean = sum(hs) / len(hs)
            cv = (sum((h - mean) ** 2 for h in hs) / len(hs)) ** 0.5 / max(mean, 1e-6)
            if cv < HOLD_CV:
                add("MO-07", seg, f"{len(hs)} shots whose holds barely vary (spread {cv:.2f} of the mean, under {HOLD_CV}): "
                    "the cut rhythm should breathe with the content, not tick")
    return out
