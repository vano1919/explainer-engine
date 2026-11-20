"""Edit-plan validators (final plan S14, W2): where a cut lands, handles, camera accents, graphic motion and the editing critic rows.

Code rules (BP-128, BP-129, BP-134, BP-54) return PASS or REVIEW; the critic rows (Rule of Six, reasons for cuts, signaling, chapter
cards ...) check only that the fields a critic needs exist and are always REVIEW. Frame numbers are integers at the episode's fps.
"""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-CIN-09", "CRAFT-EDC-01", "CRAFT-EDC-02", "CRAFT-EDC-03", "CRAFT-EDC-04", "CRAFT-EDC-06", "CRAFT-EDC-08",
            "CRAFT-MOG-01", "CRAFT-MOG-02", "CRAFT-MOG-03", "CRAFT-MOG-05", "CRAFT-MOG-06", "CRAFT-MOG-07", "CRAFT-MOG-10",
            "CRAFT-MOG-11", "CRAFT-MOG-15")


def cut_after_onset(cuts: list[dict]) -> list[dict]:
    """CRAFT-EDC-03 (BP-128): a cut inside an action lands cut_after_onset_frames after the motion begins. A cut with no
    ``motion_onset_frame`` is not inside an action and is skipped."""
    band = C.T("BP-128", "cut_after_onset_frames")
    if band is None:
        return [C.missing_threshold("CRAFT-EDC-03", "BP-128", "cut_after_onset_frames")]
    rows = []
    for c in cuts:
        if c.get("motion_onset_frame") is None:
            continue
        d = int(c["cut_frame"]) - int(c["motion_onset_frame"])
        rows.append(C.check(f"CRAFT-EDC-03:{c.get('cut_id', '?')}", band[0] <= d <= band[1], "BP-128",
                            f"cut {d} frames after the motion begins; allowed {band[0]}-{band[1]}", d))
    return rows or [G.row("CRAFT-EDC-03", None, "NOT_RUN: no cut inside an action was listed")]


def handles(clips: list[dict]) -> list[dict]:
    """CRAFT-EDC-04 (BP-128): every rendered shot keeps at least the lower bound of handle_frames at both ends
    (``handle_in_frames``, ``handle_out_frames`` = rendered frames beyond the cut at each end)."""
    band = C.T("BP-128", "handle_frames")
    if band is None:
        return [C.missing_threshold("CRAFT-EDC-04", "BP-128", "handle_frames")]
    rows = []
    for c in clips:
        gate = f"CRAFT-EDC-04:{c.get('shot_id', '?')}"
        if c.get("handle_in_frames") is None or c.get("handle_out_frames") is None:
            rows.append(G.row(gate, None, "NOT_RUN: the clip record gives no handle lengths"))
            continue
        lo = min(int(c["handle_in_frames"]), int(c["handle_out_frames"]))
        rows.append(C.check(gate, lo >= band[0], "BP-128", f"shortest handle {lo} frames; at least {band[0]}", lo))
    return rows or [G.row("CRAFT-EDC-04", None, "NOT_RUN: no clip listed")]


def occlusion_wipes(transitions: list[dict]) -> dict:
    """CRAFT-EDC-06 (eye): an ``occlusion_wipe`` is used only as an invisible cut: it says ``invisible`` and
    ``silhouette_crosses_lens``. Whether it is really unseen is looked at."""
    wipes = [t for t in transitions if t.get("type") == "occlusion_wipe"]
    miss = [f"invisible/silhouette_crosses_lens on {t.get('shot_id', '?')}" for t in wipes
            if t.get("invisible") is not True or t.get("silhouette_crosses_lens") is not True]
    return C.critic("CRAFT-EDC-06", "ED-04", miss[:10], f"{len(wipes)} occlusion wipe(s): used only as an invisible cut", len(wipes))


def accents(items: list[dict], fps: int = 24) -> list[dict]:
    """CRAFT-EDC-08 (BP-129): a whip lasts whip_frames, a speed ramp runs ramp_speeds over ramp_s, a rack focus takes rack_focus_s
    (to the frame). Items: ``{type: whip|speed_ramp|rack_focus, frames|speeds|seconds}``."""
    whip, speeds, ramp_s, rack_s = (C.T("BP-129", k) for k in ("whip_frames", "ramp_speeds", "ramp_s", "rack_focus_s"))
    if None in (whip, speeds, ramp_s, rack_s):
        return [C.missing_threshold("CRAFT-EDC-08", "BP-129", "whip_frames/ramp_speeds/ramp_s/rack_focus_s")]
    tol = 1.0 / fps
    rows = []
    for i, a in enumerate(items):
        gate = f"CRAFT-EDC-08:{a.get('id', i)}"
        t = a.get("type")
        if t == "whip":
            n = a.get("frames")
            rows.append(C.check(gate, n is not None and whip[0] <= int(n) <= whip[1], "BP-129", f"whip {n} frames; {whip[0]}-{whip[1]}", n))
        elif t == "speed_ramp":
            ok = (list(map(float, a.get("speeds") or [])) == list(map(float, speeds)) and a.get("seconds") is not None
                  and abs(float(a["seconds"]) - ramp_s) <= tol)
            rows.append(C.check(gate, ok, "BP-129", f"speed ramp {a.get('speeds')} over {a.get('seconds')} s; "
                                f"expected {speeds} over {ramp_s} s", a.get("seconds")))
        elif t == "rack_focus":
            ok = a.get("seconds") is not None and abs(float(a["seconds"]) - rack_s) <= tol
            rows.append(C.check(gate, ok, "BP-129", f"rack focus {a.get('seconds')} s; expected {rack_s} s", a.get("seconds")))
    return rows or [G.row("CRAFT-EDC-08", None, "NOT_RUN: no whip, speed ramp or rack focus listed")]


def graphic_easing(graphics: list[dict]) -> list[dict]:
    """CRAFT-MOG-01 (BP-134): a graphic enters with an ease-out inside enter_ms and leaves with an ease-in inside exit_ms."""
    enter, exit_ = C.T("BP-134", "enter_ms"), C.T("BP-134", "exit_ms")
    if enter is None or exit_ is None:
        return [C.missing_threshold("CRAFT-MOG-01", "BP-134", "enter_ms/exit_ms")]
    rows = []
    for i, g in enumerate(graphics):
        ok = (g.get("enter_ease") == "ease_out" and g.get("exit_ease") == "ease_in"
              and g.get("enter_ms") is not None and g.get("exit_ms") is not None
              and enter[0] <= g["enter_ms"] <= enter[1] and exit_[0] <= g["exit_ms"] <= exit_[1])
        rows.append(C.check(f"CRAFT-MOG-01:{g.get('id', i)}", ok, "BP-134",
                            f"enter {g.get('enter_ease')} {g.get('enter_ms')} ms (ease_out, {enter}), "
                            f"exit {g.get('exit_ease')} {g.get('exit_ms')} ms (ease_in, {exit_})"))
    return rows or [G.row("CRAFT-MOG-01", None, "NOT_RUN: no graphic listed")]


def counters(items: list[dict]) -> list[dict]:
    """CRAFT-MOG-02 (BP-134, BP-54): a counter ticks at most counter_steps_per_s_max increments a second and lands on its spoken
    number: ``lands_at_s`` minus the number word's ``word_start_s`` inside BP-54's early/late window."""
    mx, early, late = C.T("BP-134", "counter_steps_per_s_max"), C.T("BP-54", "early_max_ms"), C.T("BP-54", "late_max_ms")
    if None in (mx, early, late):
        return [C.missing_threshold("CRAFT-MOG-02", "BP-134/BP-54", "counter_steps_per_s_max, early_max_ms, late_max_ms")]
    rows = []
    for i, c in enumerate(items):
        gate = f"CRAFT-MOG-02:{c.get('id', i)}"
        if c.get("steps_per_s") is None or c.get("lands_at_s") is None or c.get("word_start_s") is None:
            rows.append(G.row(gate, None, "NOT_RUN: steps_per_s, lands_at_s or the number word's time is missing"))
            continue
        off_ms = (float(c["lands_at_s"]) - float(c["word_start_s"])) * 1000
        ok = float(c["steps_per_s"]) <= mx and -early <= off_ms <= late
        rows.append(C.check(gate, ok, "BP-134", f"{c['steps_per_s']} steps/s (at most {mx}); lands {off_ms:+.0f} ms from the spoken "
                            f"number (window -{early}..+{late})", off_ms))
    return rows or [G.row("CRAFT-MOG-02", None, "NOT_RUN: no counter listed")]


def moving_elements(events: list[dict]) -> dict:
    """CRAFT-MOG-03 (BP-134): at most moving_elements_max graphic element moves at one instant (events ``{start, end}`` seconds)."""
    mx = C.T("BP-134", "moving_elements_max")
    if mx is None:
        return C.missing_threshold("CRAFT-MOG-03", "BP-134", "moving_elements_max")
    if not events:
        return G.row("CRAFT-MOG-03", None, "NOT_RUN: no graphic motion listed")
    pts = sorted([(float(e["start"]), 1) for e in events] + [(float(e["end"]), -1) for e in events], key=lambda p: (p[0], p[1]))
    now = peak = 0
    for _, d in pts:
        now += d
        peak = max(peak, now)
    return C.check("CRAFT-MOG-03", peak <= mx, "BP-134", f"at most {peak} graphic element(s) move at once; limit {mx}", peak)


def _present(items: list[dict], key: str, label: str) -> list[str]:
    return [f"{key} on {label} {i}" for i, it in enumerate(items) if not it.get(key)][:10]


def critic_rows(plan: dict) -> list[dict]:
    """The critic rules: each reads one part of ``plan`` and checks only that the fields exist; always REVIEW."""
    cuts, beats = plan.get("cuts") or [], plan.get("beats") or []
    return [
        C.critic("CRAFT-EDC-01", "BP-128", _present(cuts, "rule_of_six", "cut"), "every cut decided by the Rule of Six in its order"),
        C.critic("CRAFT-EDC-02", "-", _present(cuts, "reason", "cut"), "never cut without a reason"),
        C.critic("CRAFT-CIN-09", "-", _present(plan.get("segments") or [], "intensity", "segment"),
                 "visual intensity rises toward the climax and drops at the resolution, with contrast between neighbours"),
        C.critic("CRAFT-MOG-05", "BP-93", _present(beats, "new_information", "beat"), "coherence: no decorative beat"),
        C.critic("CRAFT-MOG-06", "-", _present(plan.get("frames") or [], "focus", "frame"), "signaling: one focus, the rest dimmed"),
        C.critic("CRAFT-MOG-07", "-", [] if "captions" in plan else ["captions setting"],
                 "no burned narrator subtitles on 16:9 (captions as a soft track)", plan.get("captions")),
        C.critic("CRAFT-MOG-10", "ED-09", [] if plan.get("chapter_cards") else ["chapter_cards"],
                 "chapter cards cut the story into named parts"),
        C.critic("CRAFT-MOG-11", "-", [] if plan.get("first_30s_names_and_sides") is not None else ["first_30s_names_and_sides"],
                 "names and sides are shown before the battle"),
        C.critic("CRAFT-MOG-15", "-", _present(plan.get("host_shots") or [], "acts", "host shot"),
                 "a host appears because it acts, not to decorate"),
    ]


def validate(plan: dict, fps: int = 24) -> list[dict]:
    """``plan`` keys: cuts, clips, transitions, accents, graphics, counters, graphic_events, segments, beats, frames, captions,
    chapter_cards, first_30s_names_and_sides, host_shots (each optional; a missing code input is NOT_RUN)."""
    return [*cut_after_onset(plan.get("cuts") or []), *handles(plan.get("clips") or []),
            occlusion_wipes(plan.get("transitions") or []), *accents(plan.get("accents") or [], fps),
            *graphic_easing(plan.get("graphics") or []), *counters(plan.get("counters") or []),
            moving_elements(plan.get("graphic_events") or []), *critic_rows(plan)]
