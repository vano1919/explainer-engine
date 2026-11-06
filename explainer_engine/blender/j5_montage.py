"""Montage lint for a J5 minute of several scenes (the creator, 2026-11-06 20:17 UTC: non-dialogue editing, transitions between photos, the 30 % photo-collage
lane that keeps the animated style). Rules BP-179 (transitions), BP-180 (order and rhythm), BP-181 (the still lane); durations by BP-108 and BP-109; the cuts
inside a scene go through ``j5_cuts.lint``. Every rule is a hypothesis (REVIEW) until a second source type backs it; ``lint_montage`` returns text lines,
each starting with its severity, and the plan may go to generation when no line starts with FAIL.

A shot is a dict: name, scene, lane (VIDEO_3D | STILL_3D | HELPER), seconds, subject, view, size, and optionally cut (cut | dissolve | fade_black | match | axial | punch_in),
transition_s, motivation, dialogue (bool), establishing (bool), motion {kind, scale, layers}, reuse_of, match_tag, direction, luma.
"""
from __future__ import annotations

from explainer_engine.blender import j5_cuts
from explainer_engine.standards import sourced_rules as SR

LANES = ("VIDEO_3D", "STILL_3D", "HELPER")
DISSOLVE = (float(SR.T("BP-179", "dissolve_min_s")), float(SR.T("BP-179", "dissolve_max_s")))
FADE_GAP = float(SR.T("BP-179", "fade_gap_min_s"))
TRANSITIONS = tuple(SR.T("BP-179", "transitions")) + ("axial", "punch_in")
TOL_S = float(SR.T("BP-180", "runtime_tolerance_s"))
MOVE = (float(SR.T("BP-181", "still_move_min")), float(SR.T("BP-181", "still_move_max")))
LAYERS_MIN = int(SR.T("BP-181", "parallax_layers_min"))
LUMA_MAX = float(SR.T("BP-181", "luma_ratio_max"))
SHARE, SHARE_TOL = SR.T("BP-109", "lane_share"), float(SR.T("BP-109", "lane_tolerance"))
STILL_MAX = float(SR.T("BP-109", "still_shot_max_s"))
DIALOGUE_MAX, VIDEO_MAX = float(SR.T("BP-108", "dialogue_shot_max_s")), float(SR.T("BP-108", "non_dialogue_video_max_s"))


def runtime(plan: list[dict]) -> float:
    """Clips minus the dissolve overlaps (a dissolve plays over the end of one clip and the start of the next)."""
    return sum(s["seconds"] for s in plan) - sum(s.get("transition_s", 0.0) for s in plan if s.get("cut") == "dissolve")


def lane_shares(plan: list[dict]) -> dict[str, float]:
    total = sum(s["seconds"] for s in plan)
    return {k: sum(s["seconds"] for s in plan if s["lane"] == k) / total for k in LANES}


def lint_montage(plan: list[dict], target_s: float | None = None) -> list[str]:
    out: list[str] = []
    add = lambda sev, name, msg: out.append(f"{SR.level('BP-180', sev) if sev == 'FAIL' else sev}: {name}: {msg}")
    names = {s["name"]: i for i, s in enumerate(plan)}
    last_fade = None
    t = 0.0
    for i, s in enumerate(plan):
        n, prev = s["name"], plan[i - 1] if i else None
        if s["lane"] not in LANES:
            add("FAIL", n, f"lane {s['lane']!r} is not one of {LANES}")
        if s.get("cut", "cut") not in TRANSITIONS:
            add("REVIEW", n, f"transition {s.get('cut')!r} is not in {TRANSITIONS} (BP-179)")
        # durations: BP-108 / BP-109
        if s.get("dialogue") and s["seconds"] > DIALOGUE_MAX:
            add("REVIEW", n, f"a dialogue shot of {s['seconds']:g} s is over {DIALOGUE_MAX:g} s (BP-108)")
        if s["lane"] == "STILL_3D" and s["seconds"] > STILL_MAX:
            add("REVIEW", n, f"a still held {s['seconds']:g} s is over {STILL_MAX:g} s (BP-109)")
        if s["lane"] == "VIDEO_3D" and not s.get("dialogue") and s["seconds"] > VIDEO_MAX:
            add("REVIEW", n, f"a video shot of {s['seconds']:g} s is over {VIDEO_MAX:g} s (BP-108)")
        # transitions: BP-179
        kind, same_scene = s.get("cut", "cut"), prev is not None and prev["scene"] == s["scene"]
        if kind == "dissolve":
            d = s.get("transition_s", 0.0)
            if same_scene:
                add("REVIEW", n, "a dissolve inside one scene: use a straight cut (a dissolve means another place or time, BP-179)")
            if not DISSOLVE[0] <= d <= DISSOLVE[1]:
                add("REVIEW", n, f"dissolve of {d:g} s is outside {DISSOLVE[0]:g}-{DISSOLVE[1]:g} s (BP-179)")
        if kind == "fade_black":
            if same_scene:
                add("REVIEW", n, "a fade to black between shots of one scene (BP-179)")
            if last_fade is not None and t - last_fade < FADE_GAP:
                add("REVIEW", n, f"fades to black closer than {FADE_GAP:g} s (BP-179)")
            last_fade = t
        if kind == "match" and (prev is None or not s.get("match_tag") or s.get("match_tag") != prev.get("match_tag")):
            add("REVIEW", n, "a match cut needs the same match_tag on both shots (shape, motion or gaze that carries over, BP-179)")
        # order: BP-180
        if (prev is None or not same_scene) and s["lane"] != "HELPER" and s["size"] != "wide" and not s.get("establishing"):
            add("REVIEW", n, "a new scene opens on an establishing wide shot (or a declared establishing shot, BP-180)")
        if same_scene and prev["lane"] != "HELPER" and s["lane"] != "HELPER" and prev.get("direction") and s.get("direction") and prev["direction"] != s["direction"] and not s.get("motivation"):
            add("REVIEW", n, f"screen direction flips ({prev['direction']} -> {s['direction']}) without a reason (180-degree rule, BP-180)")
        src = s.get("reuse_of")
        if src and (src not in names or names[src] >= i):
            add("FAIL", n, f"reuse_of {src} must name an earlier shot")
        # the still lane: BP-181
        if s["lane"] == "STILL_3D":
            m = s.get("motion") or {}
            if not m:
                add("REVIEW", n, "a still shot with no motion (Ken Burns push, pull, pan or parallax, BP-181)")
            elif m.get("kind") == "parallax":
                if m.get("layers", 0) < LAYERS_MIN:
                    add("REVIEW", n, f"parallax needs at least {LAYERS_MIN} depth layers (BP-181)")
            elif not MOVE[0] <= m.get("scale", 1.0) <= MOVE[1]:
                add("REVIEW", n, f"the move of scale {m.get('scale', 1.0):g} is outside {MOVE[0]:g}-{MOVE[1]:g} (BP-181)")
        if same_scene and s.get("luma") and prev.get("luma"):
            r = max(s["luma"], prev["luma"]) / min(s["luma"], prev["luma"])
            if r > LUMA_MAX:
                add("REVIEW", n, f"plate brightness jumps by x{r:.2f} inside a scene (limit x{LUMA_MAX:g}, BP-181)")
        t += s["seconds"] - (s.get("transition_s", 0.0) if kind == "dissolve" else 0.0)
    # the cuts inside a scene: BP-176 / BP-178 through j5_cuts
    scenes: dict[str, list[dict]] = {}
    for s in plan:
        if s["lane"] != "HELPER":
            scenes.setdefault(s["scene"], []).append(s)
    for sc in scenes.values():
        for p in j5_cuts.lint(sc):
            add("REVIEW", sc[0]["scene"], p)
    if target_s is not None and abs(runtime(plan) - target_s) > TOL_S:
        add("REVIEW", "runtime", f"{runtime(plan):g} s against the {target_s:g} s target (BP-180)")
    for k, share in lane_shares(plan).items():
        if abs(share - SHARE[{"VIDEO_3D": "video", "STILL_3D": "still", "HELPER": "helper"}[k]]) > SHARE_TOL:
            add("REVIEW", "lanes", f"{k} is {share:.0%} of the runtime against {SHARE[{'VIDEO_3D': 'video', 'STILL_3D': 'still', 'HELPER': 'helper'}[k]]:.0%} +-{SHARE_TOL:.0%} (BP-109)")
    return out
