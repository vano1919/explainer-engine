"""The v4.3 shot router (plan P1.4, the creator's answers Q4 and Q7 of 2026-11-12): every shot of an episode-first script
gets one ``route`` with a written ``route_reason``, and the mix is reported by DURATION, never by counts (R-C).

Routes:
- ``map_action``: geography, numbers, spread and comparison shots, drawn by Python over a letter-free plate (P4).
- ``still_25d``: a picture moved through space by the layered 2.5D renderer with motion imitation (P5): camera moves, weather,
  fire, water, crowds at a distance, establishing shots, objects at rest, tableaux.
- ``video``: only where a body really performs an action a still cannot fake (running, fighting, throwing, handling an object,
  a fall), and the speaker's performance shot of a played scene (Q7: a performance clip, no lip-sync, no talking still). Since
  D-132 (the creator, 2026-11-12 19:10 UTC, after the bake-off) the clip is made by LTX-2.5 distilled on Modal
  (the video lane ``videolane/scene`` + ``training/pods/ltx/scene_run`` and the worker
  ``training/pods/ltx/modal_ltx_jobs.py``, D-137); the route was called ``wan`` under D-131 and a script that still says ``wan`` is
  read as ``video`` (``LEGACY_ROUTES``).

The router is deterministic: the same shot always gets the same route. A shot may pin its route by hand
(``route_locked: true`` with its own ``route_reason``); the router then keeps it and only checks it.
"""
from __future__ import annotations

import re
from collections import defaultdict

from explainer_engine.standards import sourced_rules as SR

ROUTES = ("map_action", "still_25d", "video")
LEGACY_ROUTES = {"wan": "video"}   # D-131's name of the video route (D-132)
DIALOGUE_SHOT_MAX_S = float(SR.T("BP-108", "dialogue_shot_max_s"))
_LANE_SHARE = SR.T("BP-109", "lane_share")
MIX_TARGETS = {
    "video": float(_LANE_SHARE["video"]),
    "still_25d": float(_LANE_SHARE["still"]),
    "map_action": float(_LANE_SHARE["helper"]),
}
ILLUSTRATED_HISTORY_TARGETS = {"still_25d": 0.60, "video": 0.30, "map_action": 0.10}


def lane_mix_targets(profile_name: str | None = None) -> dict[str, float]:
    """Return lane share targets (still 60 / video 30 / helper 10 for illustrated_history)."""
    if profile_name in ("illustrated_history", "solemn_historical_docudrama"):
        return dict(ILLUSTRATED_HISTORY_TARGETS)
    return dict(MIX_TARGETS)
MIX_TOL = float(SR.T("BP-109", "lane_tolerance"))

# a body doing something a still cannot fake: whole-body motion, contact with a thing, a strike, a fall (Q4)
BODY_ACTION = re.compile(
    r"\b(sprint\w*|run(s|ning)?|ran|flee\w*|chas\w+|charg\w+|leap\w*|jump\w*|climb\w*|crawl\w*|stumbl\w*|"
    r"fell (to|onto|into)|collaps\w+|throw(s|ing)?(?! spear)|threw|hurl\w*|thrust\w*|stab\w*|strik\w+|struck|swing\w*|"
    r"swung|punch\w*|wrestl\w+|grab\w*|seiz\w+|drag\w*|lift\w*|carr(y|ies|ying)|knap\w*|flak\w+ (a|the|off)|chip\w*|"
    r"hammer\w* (a|the|at)|carv\w+ (a|the)|scrap\w+|detach\w*|draws? (the|his|her|a|two|an) \w+|releas\w+ the|nock\w*|"
    r"shoots? (an|the|a) arrow|dig\w*|wad\w+|swim\w*|paddl\w+|wrap\w*|tighten\w*|tie\w*|tying|pour\w*|feed\w*|"
    r"kneel\w*|stride\w*|strode|march\w*|trek\w*|walk\w*|crest\w*|step(s|ping)? (out|forward|into|onto|across|to|toward)|"
    r"turns? (to|toward|away)|tilt\w* (his|her) (head|face)|lower\w* (his|her) (spear|bow)|"
    r"rais\w+ (his|her) (spear|bow|arm|hand)|(press|position)\w* [\w ,'-]{3,60}?\b(into|against|onto)|bur(y|ies|ying)|"
    r"extend\w* (two|an?|the|his|her)|hold\w* (his|her|an?|the) \w+ (out|into|up))\b",
    re.I)
# camera-only or ambient motion: these never need a video clip
AMBIENT = re.compile(r"\b(stand\w*|sit\w*|sat|rest\w*|lie\w*|lying|gaz\w+|stare\w*|look\w* (out|over|at)|wait\w*|sleep\w*|"
                     r"silhouett\w+|tableau|overlook\w*|drift\w*|fall\w* ash|ash fall\w*|smoke|mist|fog|rain|snow|blizzard|"
                     r"lightning|glow\w*|flicker\w*|burn\w*|embers?)\b", re.I)
MAP_WORDS = re.compile(r"\b(map|relief map|war table|globe|route arrows?|wind arrows?|isobar|tephra (layer|map)|population "
                       r"(curve|counter|chart)|timeline|diagram|chart|graph)\b", re.I)
# shots whose subject is too far away or too many to need body animation
DISTANT_CROWD = re.compile(r"\b(herd|herds|crowd|flock|band of|clans gather|distant figures|tiny figures|figures descending|"
                           r"aerial|tableau|silhouettes of)\b", re.I)

_TIME_PROMISE_RE = re.compile(
    r"\b(home\s+before\s+the\s+leaves\s+fall|by\s+christmas|four\s+months|five\s+months|countdown|"
    r"weeks\s+turned\s+into\s+months|days\s+until|before\s+winter)\b",
    re.I,
)
_RATIO_COMPARE_RE = re.compile(
    r"\b(against|versus|vs\.?|outnumbered|ratio|compared\s+to|\d[\d,]*\s+to\s+\d[\d,]*)\b",
    re.I,
)
_QUANT_HELPER_KINDS = ("counter", "progress_bar", "milestone", "bar_grow", "split_compare")


def _text(shot: dict) -> str:
    parts = [shot.get("narrative_purpose", ""), shot.get("action_start_state", ""), shot.get("action_end_state", "")]
    vp = shot.get("video_prompt") or {}
    parts.append(vp.get("motion_prompt") or "")
    return " ".join(p for p in parts if p)


def speaking_heroes(script: dict) -> dict[str, set[str]]:
    """Shot id -> the character ids that SPEAK a line carried by that shot (a played scene's speaker shots, Q7)."""
    lines = {l["line_id"]: l for l in script.get("audio_lines", [])}
    out: dict[str, set[str]] = {}
    for s in script.get("shots", []):
        who = {lines[i]["speaker_id"] for i in s.get("audio_line_ids", []) if i in lines
               and lines[i].get("speaker_type") == "character" and lines[i].get("speaker_id")}
        if who:
            out[s["shot_id"]] = who
    return out


def route_shot(shot: dict, speakers: set[str] | None = None) -> tuple[str, str]:
    """(route, reason) for one shot. Order: maps, a speaker on screen, a body action, else 2.5D."""
    text = _text(shot)
    if (shot.get("helper_subtype") in ("document", "letter", "newspaper", "telegram")
            or shot.get("archival_asset")
            or shot.get("visual_type") in ("archival_document", "archival_letter", "archival_newspaper", "archival_telegram")):
        sub = shot.get("helper_subtype") or (shot.get("archival_asset") or {}).get("subtype") or "document"
        return "map_action", f"archival helper ({sub}): validated historical artifact rendered in helper lane (B-P1c)"
    if shot.get("visual_type") == "map_visualization" or shot.get("generation_mode") in ("TACTILE_MAP", "MAP_25D") \
            or (not shot.get("character_ids") and MAP_WORDS.search(text)):
        return "map_action", "geography or numbers: drawn by Python over a letter-free plate, the action timed to the words (Q6)"
    heroes = set(shot.get("character_ids") or [])
    if speakers and speakers & heroes:
        who = ", ".join(sorted(speakers & heroes))
        return "video", f"a hero speaks a line in this shot ({who}): a performance clip, no lip-sync, no talking still (Q7)"
    m = BODY_ACTION.search(text)
    if m and not DISTANT_CROWD.search(text):
        return "video", f"a body performs an action a still cannot fake ({m.group(0)!r}) (Q4)"
    a = AMBIENT.search(text)
    if not heroes:
        return "still_25d", "no hero in frame: place, object or tableau, moved by the 2.5D renderer with motion imitation (Q4)"
    if a:
        return "still_25d", f"the heroes hold a pose ({a.group(0)!r}); camera, light and atmosphere carry the motion (Q4)"
    return "still_25d", "no body action named: the 2.5D renderer with motion imitation carries the shot (Q4)"


def route_script(script: dict) -> list[dict]:
    """Route every shot in place (``route`` + ``route_reason``); a ``route_locked`` shot keeps its own. Returns the
    decisions as rows (shot id, route, reason, locked)."""
    speakers = speaking_heroes(script)
    rows = []
    for s in script.get("shots", []):
        if s.get("route") in LEGACY_ROUTES:   # D-132: a D-131 script's ``wan`` is the video route
            s["route"] = LEGACY_ROUTES[s["route"]]
        if s.get("route_locked") and s.get("route") in ROUTES and s.get("route_reason"):
            rows.append({"shot_id": s["shot_id"], "route": s["route"], "reason": s["route_reason"], "locked": True})
            continue
        route, reason = route_shot(s, speakers.get(s["shot_id"]))
        s["route"], s["route_reason"] = route, reason
        rows.append({"shot_id": s["shot_id"], "route": route, "reason": reason, "locked": False})
    return rows


def mix_report(script: dict, durations: dict[str, float] | None = None) -> dict:
    """The visual mix by DURATION (R-C). ``durations`` = measured seconds per shot from the timed spine; without it the
    script's ``target_duration_seconds`` are used and the report says ``estimated``."""
    secs: dict[str, float] = defaultdict(float)
    missing = []
    for s in script.get("shots", []):
        r = LEGACY_ROUTES.get(s.get("route"), s.get("route"))
        if r not in ROUTES:
            missing.append(s["shot_id"])
            continue
        d = (durations or {}).get(s["shot_id"], s.get("target_duration_seconds") or 0.0)
        secs[r] += float(d)
    total = sum(secs.values())
    shares = {r: round(secs[r] / total, 4) if total else 0.0 for r in ROUTES}
    return {"basis": "measured" if durations else "estimated", "total_seconds": round(total, 2),
            "seconds": {r: round(secs[r], 2) for r in ROUTES}, "shares": shares, "unrouted": missing}


_DECLARED_TARGET_KEYS = {"cinematic_video_target": "video", "composed_illustration_target": "still_25d",
                         "map_visualization_target": "map_action"}


def _declared_mix(script: dict) -> dict | None:
    """Owner-approved item 4: a docudrama that declares its OWN planning mix (``visual_mix_target`` + ``visual_mix_band`` in the
    production script, 2.5D 60 / LTX 30 / helper 10 for Truce) is judged against that declaration, as an advisory REVIEW. A script
    without the pair keeps BP-109's registry mix and its FAIL (cartoon episodes are video-heavy by design; the registry is
    not flipped for them)."""
    tgt, band = script.get("visual_mix_target"), script.get("visual_mix_band")
    if not isinstance(tgt, dict) or not isinstance(band, dict):
        return None
    targets = {r: float(tgt[k]) for k, r in _DECLARED_TARGET_KEYS.items() if k in tgt}
    aliases = {"video": ("video", "video_ltx_band"), "still_25d": ("still_25d", "still_25d_band"),
               "map_action": ("map_action", "map_helper_band")}
    bands = {}
    for r, keys in aliases.items():
        for k in keys:
            if isinstance(band.get(k), (list, tuple)) and len(band[k]) == 2:
                bands[r] = band[k]
                break
    return {"targets": targets, "bands": bands} if targets and bands else None


def _declared_mix_row(script: dict, rep: dict, declared: dict) -> dict:
    from explainer_engine.qa import gates as G
    shares = rep["shares"]
    outside = [f"{r}={shares.get(r, 0.0):.1%} (band {lo:.0%}-{hi:.0%})" for r, (lo, hi) in declared["bands"].items()
               if not float(lo) - 1e-6 <= float(shares.get(r, 0.0)) <= float(hi) + 1e-6]
    locked = [s["shot_id"] for s in script.get("shots", []) if s.get("locked_shot")]
    eligible = [s["shot_id"] for s in script.get("shots", [])
                if not s.get("locked_shot") and s.get("conversion_eligibility") == "eligible_if_asset_available"]
    summary = ", ".join(f"{r} {shares.get(r, 0.0):.1%} (target {declared['targets'].get(r, 0.0):.0%})"
                        for r in ("video", "still_25d", "map_action"))
    detail = (f"visual mix ({rep['basis']}) against the episode's own declared band: {summary}; {len(locked)} locked shot(s) "
              f"(chorus / visible singing) are never converted; {len(eligible)} unlocked shot(s) eligible for conversion"
              + (f" — outside band: {', '.join(outside)}" if outside else ""))
    return G.row("route_mix_60_30_10", not outside, detail,
                 dict(rep, locked_shots=len(locked), eligible_conversions=eligible[:40]), level=G.REVIEW)


def mix_gate_rows(script: dict, durations: dict[str, float] | None = None, tol: float = MIX_TOL,
                  scope: str = "full") -> list[dict]:
    """A2.3 (BP-109): enforce the 60/30/10 duration mix with explicit tolerance ``tol`` (default +-5 percentage points from
    ``sourced_rules.json`` BP-109). On a ``full`` episode a route outside its band is a hard ``FAIL``; on a ``sample``
    episode it is ``REVIEW``."""
    from explainer_engine.qa import gates as G
    rep = mix_report(script, durations)
    shares = rep["shares"]
    declared = _declared_mix(script)
    if declared is not None:
        return [_declared_mix_row(script, rep, declared)]
    outside: list[str] = []
    for r in ROUTES:
        target = MIX_TARGETS[r]
        got = float(shares.get(r, 0.0))
        if abs(got - target) > tol + 1e-6:
            outside.append(f"{r}={got:.1%} (target {target:.0%} +- {tol:.0%})")
    lvl = G.REVIEW if scope == "sample" else G.FAIL
    summary = ", ".join(f"{r} {shares.get(r, 0.0):.1%} (target {MIX_TARGETS[r]:.0%})" for r in ("video", "still_25d", "map_action"))
    return [G.row("route_mix_60_30_10", not outside,
                  f"visual mix ({rep['basis']}): {summary}; tolerance +-{tol:.0%} (BP-109)"
                  + (f" — outside band: {', '.join(outside)}" if outside else ""),
                  rep, level=lvl)]


def infer_helper_form(text: str, actions: list[dict] | None = None) -> str:
    """MA-09 (Audit #66): infer which 10% helper form fits a shot's spoken line and actions."""
    acts = list(actions or [])
    kinds = {str(a.get("kind") or "") for a in acts}
    if kinds & {"progress_bar", "milestone"}:
        return "timeline_progress"
    if "counter" in kinds:
        return "counter"
    if kinds & {"bar_grow", "split_compare"}:
        return "comparison_chart"
    t = str(text or "")
    if _TIME_PROMISE_RE.search(t):
        return "timeline_progress"
    if _RATIO_COMPARE_RE.search(t) and len(re.findall(r"\b\d[\d,]*\b", t)) >= 2:
        return "comparison_chart"
    if re.search(r"\b(\d[\d,]*\s+(?:men|soldiers|casualties|dead|miles|kilometers|km|patches|sectors)|hundred\s+thousand)\b", t, re.I):
        return "counter"
    return "geographic_map"


def helper_fit_rows(script: dict) -> list[dict]:
    """MA-09 (Audit #66): verify that 10% helper-lane shots whose narration is a time promise / countdown or a pure numerical
    comparison include a matching quantitative/temporal helper action (``progress_bar``, ``milestone``, ``counter``,
    ``bar_grow``, ``split_compare``) instead of being drawn as a pure geographic map."""
    from explainer_engine.qa import gates as G
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", []) if ln.get("line_id")}
    mismatched: list[str] = []
    for s in script.get("shots", []):
        if s.get("route") != "map_action":
            continue
        sid = s.get("shot_id", "?")
        ltxt = " ".join(str((lines.get(lid) or {}).get("text") or "") for lid in (s.get("audio_line_ids") or [])).strip()
        text = " ".join(x for x in (ltxt, str(s.get("narration_excerpt") or ""), str(s.get("narrative_purpose") or "")) if x)
        acts = list(s.get("actions") or [])
        kinds = {str(a.get("kind") or "") for a in acts}
        has_quant = bool(kinds & set(_QUANT_HELPER_KINDS))
        if _TIME_PROMISE_RE.search(text) and not has_quant:
            mismatched.append(f"{sid}: time/countdown promise drawn as pure map without progress_bar/milestone/counter (MA-09)")
        elif _RATIO_COMPARE_RE.search(text) and len(re.findall(r"\b\d[\d,]*\b", text)) >= 2 and not has_quant:
            mismatched.append(f"{sid}: numerical ratio/comparison drawn as pure map without bar_grow/split_compare/counter (MA-09)")
    return [G.row("helper_lane_form_fit", not mismatched,
                  f"{len(mismatched)} helper shot(s) drawn as pure geographic map when narration calls for a counter, progress bar or comparison chart (MA-09)",
                  mismatched[:20], level=G.REVIEW)]


def talking_check(script: dict) -> list[dict]:
    """Q7 (plan P6.4): a hero who speaks is seen performing, never a still with a voice over a closed mouth. A shot that
    carries a character's line AND shows that character (``character_ids``) is a video shot (FAIL otherwise). A line over a
    shot that does not show its speaker (a cutaway, an insert, a listener) is the off-screen voice of Q7's "speaker plus
    listener reactions": REVIEW until the creator says yes to off-screen lines (final audit A9, 2026-11-12). A speaker shot
    stays within BP-108's dialogue length (REVIEW: a house rule whose registry severity is REVIEW)."""
    from explainer_engine.qa import gates as G
    speakers = speaking_heroes(script)
    shots = {s["shot_id"]: s for s in script.get("shots", [])}
    seen = {sid: who & set(shots[sid].get("character_ids") or []) for sid, who in speakers.items()}
    still = sorted(sid for sid in speakers if seen[sid] and shots[sid].get("route") != "video")
    off = sorted(f"{sid}: {', '.join(sorted(speakers[sid]))} off screen on {shots[sid].get('route')}"
                 for sid in speakers if not seen[sid] and shots[sid].get("route") != "video")
    long_ = sorted(sid for sid in speakers if float(shots[sid].get("target_duration_seconds") or 0) > DIALOGUE_SHOT_MAX_S)
    return [G.row("speaker_shots_are_video", not still, f"{len(still)} of {len(speakers)} shot(s) that show their speaker are "
                  "not video performance clips (Q7: no talking still)", still),
            G.row("speaker_off_screen", not off, f"{len(off)} line(s) over a shot that does not show the speaker (a cutaway "
                  "or a listener): allowed only on the creator's yes to off-screen lines (audit A9)", off, level=G.REVIEW),
            G.row("speaker_shots_short", not long_, f"{len(long_)} speaker shot(s) longer than {DIALOGUE_SHOT_MAX_S} s "
                  "(BP-108)", long_, level=SR.severity("BP-108") if SR.severity("BP-108") == "REVIEW" else SR.level("BP-108"))]
