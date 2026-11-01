"""The variant planner, stage 1b (Blueprint P3, docs/SCRIPT_ENGINE.md VP-01..VP-18, OR-31): two or three priced variants of
different structure profiles before the scenario, each scored by code, so the creator picks on one card.

    python -m explainer_engine.scripting.variant_plan brief <dossier folder> [--traits traits.json]
    python -m explainer_engine.scripting.variant_plan score <script_variants.json> [--write]
    python -m explainer_engine.scripting.variant_plan check <script_variants.json>
    python -m explainer_engine.scripting.variant_plan napoleon [--write]     # the worked example, rebuilt from its committed files

``dynamics`` is the ONE function that counts lane shares, runs, rotation and turn coverage: the plan, the script (ST-24) and,
later, P6's shot router call it. A segment is ``{id, window_s?, function?, blocks[]}`` and a block ``{category|lane, archetype?,
seconds, who?, tier?, words?, shots?}``; a block that names no category is placed by its lane (``category``). Every threshold
is read through ``sourced_rules.T`` and every severity through ``level``: a hypothesis is REVIEW, only BP-142 (the creator's
"every turn is a played scene"), invariant 7 (the arithmetic of a plan) and invariant 2 (the creator's money) may FAIL.
Costs come only from ``config/job_speeds.json`` and the API price tables; a row with no measurement is ``unknown``, never a guess.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.core import contracts, ledger, spend_caps
from explainer_engine.scripting import film_shots, syllables
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
JOB_SPEEDS = ROOT / "config" / "job_speeds.json"
NAPOLEON = ROOT / "examples" / "napoleon_vs_genghis"
CATEGORIES = ("scene", "map_pure", "compensator", "host", "hold")
PLAYED = "scene"
FAMILIES = {1: "map", 2: "map", 3: "map", 4: "map", 5: "hud", 7: "hud", 11: "hud", 6: "cut", 9: "cut", 10: "graph", 12: "graph",
            8: "tableau"}  # archetype -> family (the P5 catalogue); the rotation rule counts blocks of one family (VP-07)
CENTRAL_FUNCS = ("climax", "crisis")
EPS = 0.01

# What exists in code today (a fact about the code, not a threshold). The phase that lands a lane flips its entry in the same
# commit and its own test proves the lane; tests/unit/test_variant_plan.py keeps each entry honest.
LANES: dict[str, dict] = {
    "KEYFRAME_LTX:light": {"available": False, "phase": "P6", "note": "no LTX-2.5 / Wan 2.2 clip pod script under explainer_engine/training/pods/ "
                           "passes runpod dryrun (OR-21); committed in P6, priced in P12b"},
    "KEYFRAME_LTX:full": {"available": False, "phase": "P6", "price": "unknown until P12b", "note": "no LTX-2.5 / Wan 2.2 clip pod script "
                          "under explainer_engine/training/pods/ passes runpod dryrun (OR-21); committed in P6, priced in P12b"},
    "STILL_HOLD": {"available": True, "evidence": "explainer_engine/production/assemble.py"},
    "PARALLAX_25D_TABLEAU": {"available": True, "evidence": "explainer_engine/production/parallax.py", "archetypes": [8]},
    "GRAPHICS": {"available": True, "evidence": "explainer_engine/production/graphics.py"},
    "MAP": {"available": True, "evidence": "explainer_engine/maps/render.py", "archetypes": [1, 2, 3, 4]},
    "COMPENSATOR": {"available": True, "evidence": "explainer_engine/edit/visual_compensator.py", "archetypes": [5, 6, 7, 9, 10, 11, 12]},
    "HOST_COMMENTARY": {"available": False, "phase": "P5b"},
    "DIALOGUE_CU": {"available": False, "phase": "P6"},
    "DRAMA_BLOCKED_3D": {"available": False, "phase": "P6"},
    "ATMOS_BROLL": {"available": False, "phase": "P6", "note": "UNVERIFIED which phase owns it; P6 is 'shot router, lanes'"},
}
_ARCHETYPE_KEY = {a: k for k, v in LANES.items() for a in v.get("archetypes", [])}


def sev(rule_id: str, wanted: str = "REVIEW") -> str:
    return SR.level(rule_id, wanted)


def _f(out: list, rule: str, where: str, detail: str, severity: str = "REVIEW") -> None:
    out.append({"rule": rule, "severity": severity, "where": where, "detail": detail})


# --- profiles, categories and the segments of a plan, a script and a set of shot cards --------------------------------------
def profile(pid: str) -> dict:
    return SR.T("BP-141", "episode_structure_profiles")[pid]


def category(block: dict, cast=None) -> str:
    """The category of a block: its own ``category``; else its lane (``who`` a cast member plays the scene); else the film_shots/1
    inference from tier and mode (tier hold first; scene or insert is played; narrated is played only for a cast member)."""
    if block.get("category") in CATEGORIES:
        return block["category"]
    lane, who = block.get("lane"), block.get("who")
    cast_ok = bool(who) if cast is None else who in cast
    if block.get("tier") == "hold" or lane == "STILL_HOLD":
        return "hold"
    if lane == "MAP":
        return "map_pure"
    if lane == "HOST_COMMENTARY":
        return "host"
    if lane in ("COMPENSATOR", "ATMOS_BROLL"):
        return "compensator"
    if lane in ("DIALOGUE_CU", "DRAMA_BLOCKED_3D"):
        return "scene"
    if lane == "KEYFRAME_LTX":
        return "scene" if cast_ok else "compensator"
    mode = block.get("mode")
    if mode in ("scene", "insert"):
        return "scene"
    if mode == "narrated":
        return "scene" if cast_ok else "compensator"
    return "compensator"


def segments_from_film_shots(doc: dict) -> list[dict]:
    """The shot cards grouped by scene: one block per shot, its category by ``category`` (film_shots/1 has no lanes)."""
    cast = set(doc.get("cast", {}))
    order: list[str] = []
    segs: dict[str, dict] = {}
    for s in doc["shots"]:
        seg = segs.setdefault(s["scene"], {"id": s["scene"], "blocks": []})
        if s["scene"] not in order:
            order.append(s["scene"])
        who = (s.get("action") or {}).get("who")
        block = {"id": s["id"], "seconds": float(s["seconds"]), "tier": s.get("tier"), "mode": s.get("mode"), "who": who,
                 "lane": s.get("lane"), "shots": 1}
        if s.get("archetype") is not None:
            block["archetype"] = s["archetype"]
        block["category"] = category(block, cast)
        narr = len((s.get("narration") or "").split())
        spoken = s.get("dialogue")
        spoken = [spoken] if isinstance(spoken, dict) else (spoken or [])
        block["words"] = {"narrator": narr, "character": sum(len(d.get("text", "").split()) for d in spoken)}
        seg["blocks"].append({k: v for k, v in block.items() if v is not None})
    for seg in segs.values():
        seg["window_s"] = sum(b["seconds"] for b in seg["blocks"])
    return [segs[i] for i in order]


def segments_from_script(doc: dict) -> list[dict]:
    """A production script's segments: a hero line is a played block of that hero, a narrator line a narrated one; the seconds
    are ``syllables.seconds`` (BP-01's pace) since no voice exists yet."""
    out = []
    for seg in doc.get("segments", []):
        blocks = []
        for ln in seg.get("lines", []):
            secs = syllables.seconds(ln["text"], pause_after=float(ln.get("pause_after", 0) or 0))
            words = len(ln["text"].split())
            if ln.get("speaker"):
                blocks.append({"category": "scene", "who": ln["speaker"], "seconds": secs, "words": {"character": words}})
            else:
                blocks.append({"category": "compensator", "seconds": secs, "words": {"narrator": words}})
        out.append({"id": seg["id"], "function": (seg.get("drama") or {}).get("function"), "blocks": blocks,
                    "window_s": sum(b["seconds"] for b in blocks)})
    return out


def segments_from_variant(variant: dict) -> list[dict]:
    return variant["segments"]


# --- dynamics: the one function --------------------------------------------------------------------------------------------
def _blocks(segments: list[dict]) -> list[tuple[dict, dict, float]]:
    """(segment, block, start second) in order."""
    t, out = 0.0, []
    for seg in segments:
        for b in seg["blocks"]:
            out.append((seg, b, t))
            t += b["seconds"]
    return out


def _run_max(seq: list[tuple[str, float]], test) -> float:
    best = cur = 0.0
    for cat, secs in seq:
        cur = cur + secs if test(cat) else 0.0
        best = max(best, cur)
    return best


def turn_ids(segments: list[dict], template: str = "D") -> list[str]:
    """The segments that are turns: template D's rows (BP-142 ``turn_slots_D``) and any segment whose function is a turn."""
    slots = {f"S{n:02d}" for n in SR.T("BP-142", "turn_slots_D")} if template == "D" else set()
    funcs = set(SR.T("BP-142", "turn_functions"))
    return [s["id"] for s in segments if s["id"] in slots or s.get("function") in funcs]


def dynamics(segments: list[dict], prof: dict, *, template: str = "D") -> dict:
    """Shares, runs, rotation, turn coverage and the narrator share of a plan: pure, no I/O."""
    flat = _blocks(segments)
    total = sum(b["seconds"] for _, b, _ in flat)
    secs = {c: 0.0 for c in CATEGORIES}
    for _, b, _ in flat:
        secs[category(b)] += b["seconds"]
    share = {c: (secs[c] / total if total else 0.0) for c in CATEGORIES}
    seq = [(category(b), b["seconds"]) for _, b, _ in flat]
    # rotation: the same archetype twice with no played block between, and a family over its share of one window
    adjacent = []
    for (sa, a, _), (sb, b, _) in zip(flat, flat[1:]):
        if category(a) != PLAYED and category(b) != PLAYED and a.get("archetype") is not None and a.get("archetype") == b.get("archetype"):
            adjacent.append(f"{sa['id']}..{sb['id']}")
    window = SR.T("BP-141", "rotation_window_s")
    over_family = []
    starts = [(t, FAMILIES.get(int(b["archetype"])), seg["id"]) for seg, b, t in flat if b.get("archetype") is not None
              and int(b["archetype"]) in FAMILIES]
    for t0, fam, sid in starts:
        n = sum(1 for t, f, _ in starts if f == fam and t0 <= t < t0 + window)
        if n > SR.T("BP-141", "rotation_family_max") and (fam, sid) not in over_family:
            over_family.append((fam, sid))
    # turns
    turns = turn_ids(segments, template)
    by_id = {s["id"]: s for s in segments}
    turn_played, turn_has_who = {}, {}
    for tid in turns:
        blocks = by_id[tid]["blocks"]
        w = sum(b["seconds"] for b in blocks)
        turn_played[tid] = sum(b["seconds"] for b in blocks if category(b) == PLAYED) / w if w else 0.0
        turn_has_who[tid] = any(category(b) == PLAYED and b.get("who") for b in blocks)
    played_s = {tid: sum(b["seconds"] for b in by_id[tid]["blocks"] if category(b) == PLAYED) for tid in turns}
    central = [t for t in turns if by_id[t].get("function") in CENTRAL_FUNCS]
    if not central and template == "D" and len(turns) >= 4:
        central = [turns[3]]  # template D row 10 is the central scene (docs/STORY_ENGINE.md)
    # narrator share: spoken words when the blocks carry them, else the seconds that are not played
    nw = sum((b.get("words") or {}).get("narrator", 0) for _, b, _ in flat)
    cw = sum((b.get("words") or {}).get("character", 0) for _, b, _ in flat)
    narrator, basis = ((nw / (nw + cw), "words") if nw + cw else (1.0 - share[PLAYED] if total else 0.0, "seconds"))
    shots_band = SR.T("BP-107", "shots_per_min")
    default_rate = sum(shots_band) / 2
    planned = sum(b.get("shots") or max(1, round(b["seconds"] * default_rate / 60)) for _, b, _ in flat)
    kuleshov = []
    for seg, b, _ in flat:
        if category(b) == "compensator":
            n = b.get("shots") or max(1, round(b["seconds"] * default_rate / 60))
            if b["seconds"] / n > SR.T("BP-141", "kuleshov_max_s"):
                kuleshov.append(f"{seg['id']} ({b['seconds'] / n:.0f} s)")
    return {"total_s": total, "seconds": secs, "share": share, "non_character": 1.0 - share[PLAYED] if total else 0.0,
            "map_run_max_s": _run_max(seq, lambda c: c == "map_pure"), "non_scene_run_max_s": _run_max(seq, lambda c: c != PLAYED),
            "adjacent_repeats": adjacent, "family_overruns": over_family, "turns": turns, "turn_played_share": turn_played,
            "turn_has_played": turn_has_who, "turn_played_s": played_s, "central": central, "narrator_share": narrator,
            "narrator_basis": basis, "planned_shots": planned, "shots_per_min": planned / (total / 60) if total else 0.0,
            "kuleshov_over": kuleshov, "lane_share": film_shots.lane_shares([b for _, b, _ in flat])}


# --- the checks ------------------------------------------------------------------------------------------------------------
def turn_findings(dyn: dict, prof: dict) -> list[dict]:
    """VP-08 (BP-142, house: every turn is a played scene) and VP-09 (the profile's minimum played share)."""
    out: list[dict] = []
    for tid in dyn["turns"]:
        if not dyn["turn_has_played"][tid]:
            _f(out, "VP-08", tid, "this turn has no played block with a cast member: a turn told over a map, a card or the narrator "
               "alone is not a scene (BP-142)", sev("BP-142", "FAIL"))
        elif dyn["turn_played_share"][tid] + EPS < prof["turn_scene_share_min"]:
            _f(out, "VP-09", tid, f"{dyn['turn_played_share'][tid]:.0%} of this turn is played; the profile asks for "
               f"{prof['turn_scene_share_min']:.0%} (BP-141)", sev("BP-141"))
    return out


def checks(dyn: dict, prof: dict) -> list[dict]:
    """VP-02..VP-11 (no lane table here: ``lane_findings``), VP-16..VP-18 of a plan's dynamics."""
    out: list[dict] = []
    map_max = film_shots.LANE_SHARE["helper"] + film_shots.LANE_TOLERANCE
    if dyn["share"]["map_pure"] > map_max + 1e-9:
        _f(out, "VP-02", "map_pure", f"pure map is {dyn['share']['map_pure']:.0%} of the episode (a helper visual: at most "
           f"{map_max:.0%}, BP-109)", sev("BP-109"))
    if dyn["non_character"] > prof["non_character_max"] + 1e-9:
        _f(out, "VP-03", "non_character", f"{dyn['non_character']:.0%} of the episode has no played block (this profile: at most "
           f"{prof['non_character_max']:.0%}, BP-141)", sev("BP-141"))
    if dyn["map_run_max_s"] > SR.T("BP-141", "map_run_max_s"):
        _f(out, "VP-04", "map_pure", f"{dyn['map_run_max_s']:.0f} s of pure map in a row (BP-141)", sev("BP-141"))
    if dyn["non_scene_run_max_s"] > SR.T("BP-127", "non_character_run_max_s"):
        _f(out, "VP-05", "blocks", f"{dyn['non_scene_run_max_s']:.0f} s without a played block (at most "
           f"{SR.T('BP-127', 'non_character_run_max_s'):g} s, BP-127)", sev("BP-127"))
    if SR.T("BP-141", "rotation_adjacent"):
        for where in dyn["adjacent_repeats"]:
            _f(out, "VP-06", where, "the same archetype twice in a row with no played block between (BP-141)", sev("BP-141"))
    for fam, sid in dyn["family_overruns"]:
        _f(out, "VP-07", sid, f"more than {SR.T('BP-141', 'rotation_family_max')} '{fam}' blocks inside "
           f"{SR.T('BP-141', 'rotation_window_s'):g} s (BP-141)", sev("BP-141"))
    out += turn_findings(dyn, prof)
    for where in dyn["kuleshov_over"]:
        _f(out, "VP-10", where, f"one compensator picture held longer than {SR.T('BP-141', 'kuleshov_max_s'):g} s (BP-141)",
           sev("BP-141"))
    lo, hi = SR.T("BP-105", "narrator_share")
    if not lo <= dyn["narrator_share"] <= hi:
        _f(out, "VP-16", "narrator", f"the narrator has about {dyn['narrator_share']:.0%} ({dyn['narrator_basis']}); aim {lo:.0%}-{hi:.0%} "
           "(BP-105, a template D band: a tactical profile narrates more by design)", sev("BP-105"))
    if dyn["central"] and dyn["turn_played_s"]:
        top = max(dyn["turn_played_s"], key=dyn["turn_played_s"].get)
        c = dyn["central"][0]
        if dyn["turn_played_s"][c] + EPS < dyn["turn_played_s"][top]:
            _f(out, "VP-17", c, f"the central scene has {dyn['turn_played_s'][c]:.0f} played s, less than {top}'s "
               f"{dyn['turn_played_s'][top]:.0f} s (ST-18)")
    lo, hi = SR.T("BP-107", "shots_per_min")
    if not lo <= dyn["shots_per_min"] <= hi:
        _f(out, "VP-18", "shots", f"{dyn['shots_per_min']:.1f} planned shots a minute (band {lo}-{hi}, BP-107)", sev("BP-107"))
    for lane, detail in film_shots.lane_share_findings(dyn["lane_share"]):
        _f(out, "VP-18", lane, detail, sev("BP-109"))
    return out


def lane_keys(block: dict) -> list[str]:
    """The ``LANES`` keys one block needs: its lane (a keyframe by tier), and the lane its archetype belongs to."""
    keys = []
    cat, lane = category(block), block.get("lane")
    arch = block.get("archetype")
    if arch is not None and int(arch) in _ARCHETYPE_KEY:
        keys.append(_ARCHETYPE_KEY[int(arch)])
    elif lane in LANES:
        keys.append(lane)
    elif cat == "map_pure":
        keys.append("MAP")
    elif cat == "host":
        keys.append("HOST_COMMENTARY")
    elif cat == "hold":
        keys.append("STILL_HOLD")
    else:
        keys.append("KEYFRAME_LTX:light" if block.get("tier") == "light" else "KEYFRAME_LTX:full")
    return keys


def lane_findings(segments: list[dict], lanes: dict | None = None) -> list[dict]:
    """VP-11: a scheduled lane or archetype that does not exist in code yet; one finding per lane, naming its phase."""
    table = LANES if lanes is None else lanes
    missing: dict[str, set] = {}
    for _, b, _ in _blocks(segments):
        for key in lane_keys(b):
            if not table.get(key, {}).get("available", False):
                missing.setdefault(key, set())
                if b.get("archetype") is not None:
                    missing[key].add(int(b["archetype"]))
    out: list[dict] = []
    for key, arch in missing.items():
        info = table.get(key, {})
        _f(out, "VP-11", key, f"lane {key}" + (f" (archetypes {sorted(arch)})" if arch else "") +
           f" does not exist in code yet: it lands in {info.get('phase', 'an unnamed phase')}, and the plan waits for it")
    return out


# --- cost ------------------------------------------------------------------------------------------------------------------
def load_speeds(path: Path | str | None = None) -> dict | None:
    p = Path(path) if path else JOB_SPEEDS
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _row_usd(row: dict, speeds: dict | None) -> tuple[float | None, str]:
    """(USD of one row, how its number is known); None when no measurement stands behind it."""
    kind = row["kind"]
    if kind == "cpu":
        return 0.0, "estimate (by construction)"
    if kind == "api":
        from explainer_engine.imagegen import plan as imgplan
        try:
            per = imgplan.price(row["provider"], row.get("model"), row.get("size"), int(row.get("refs", 0)), bool(row.get("batch")))
        except (ValueError, KeyError):
            return None, "unknown"
        return per * row["units"], "estimate"
    if kind == "pod":
        from explainer_engine.cloud import speeds as speed_table
        hit = speed_table.lookup(speeds or {}, row["job"], row.get("card") or row.get("gpu"))
        if hit is not None:                                  # the schema `runpod cost --record-speed` writes: jobs/<job>/rows/<card>
            return (row["units"] * hit["usd_per_unit"], "measured") if hit.get("usd_per_unit") else (None, "unknown")
        spec = (speeds or {}).get(row["job"])                # the flat form older plans carried; nothing writes it any more
        if not isinstance(spec, dict) or "seconds_per_unit" not in spec or not spec.get("gpu"):
            return None, "unknown"
        from explainer_engine.cloud import runpod
        speed = runpod.SPEED.get(spec["gpu"])
        if not speed:
            return None, "unknown"
        hours = row["units"] * spec["seconds_per_unit"] * float(spec.get("margin", 1.0)) / speed / 3600.0
        return hours * runpod.MAX_PRICE["default"], "measured" if spec.get("measured") else "estimate"
    if kind == "voice":
        rate = (speeds or {}).get("elevenlabs_usd_per_credit")
        return (row["units"] * rate, "estimate") if rate else (None, "unknown")
    return None, "unknown"


def _unpriced_why(row: dict, speeds: dict | None) -> str:
    """Why a pod row has no price: the job was never measured, or several cards were and the row names none."""
    rows = (((speeds or {}).get("jobs") or {}).get(row["job"]) or {}).get("rows") or {}
    card = row.get("card") or row.get("gpu")
    if not rows:
        return f"no measured row for job {row['job']}"
    if not card and len(rows) > 1:
        return f"{len(rows)} cards measured for {row['job']}; the row must name one (card)"
    return f"no priced row for job {row['job']} on {card or 'the measured card'}"


def cost(variant: dict, *, speeds: dict | None = None, caps: dict | None = None) -> dict:
    """Priced rows of a variant (``cost_rows``): planned = base x 1.5, worst = base x 3 on every paid row. Any unknown row makes
    the totals the string ``"unknown"``; the known part is still shown and still checked against 80 % of every cap (VP-13)."""
    caps = spend_caps.load() if caps is None else caps
    rows, unknown, why = [], [], {}
    known_p = known_w = 0.0
    by_service: dict[str, float] = {}
    by_pod: dict[str, float] = {}
    for r in variant.get("cost_rows", []):
        base, basis = _row_usd(r, speeds)
        paid = r["kind"] != "cpu"
        planned = None if base is None else base * (1.5 if paid else 1.0)
        worst = None if base is None else base * (3.0 if paid else 1.0)
        rows.append({"label": r["label"], "kind": r["kind"], "service": r.get("service"), "units": r["units"],
                     "usd_planned": planned, "usd_worst": worst, "basis": basis})
        if base is None:
            unknown.append(r["label"])
            if r["kind"] == "pod":
                why[r["label"]] = _unpriced_why(r, speeds)
            continue
        known_p += planned
        known_w += worst
        if r.get("service"):
            by_service[r["service"]] = by_service.get(r["service"], 0.0) + worst
        if r.get("pod"):
            by_pod[r["pod"]] = by_pod.get(r["pod"], 0.0) + worst
    lines = []
    fraction = ledger.STOP_FRACTION
    for service, used in sorted(by_service.items()):
        cap = caps.get("per_episode", {}).get(service)
        if cap is not None:
            lines.append({"what": f"per_episode.{service}", "known_worst": used, "limit": cap * fraction, "over": used > cap * fraction + 1e-9})
    per_pod = caps.get("runpod", {}).get("per_pod_usd")
    for pod, used in sorted(by_pod.items()):
        if per_pod is not None:
            lines.append({"what": f"runpod.per_pod_usd ({pod})", "known_worst": used, "limit": per_pod * fraction,
                          "over": used > per_pod * fraction + 1e-9})
    return {"usd_planned": "unknown" if unknown else known_p, "usd_worst": "unknown" if unknown else known_w,
            "known_usd_planned": known_p, "known_usd_worst": known_w, "unknown_rows": unknown, "unknown_why": why, "rows": rows,
            "cap_check": {"stop_fraction": fraction, "lines": lines}}


def cost_checks(c: dict) -> list[dict]:
    out: list[dict] = []
    for line in c["cap_check"]["lines"]:
        if line["over"]:
            _f(out, "VP-13", line["what"], f"the known worst case ${line['known_worst']:.2f} is above 80 % of the cap "
               f"(${line['limit']:.2f}): split the work or cut it; at 80 % of a cap the work stops and asks", "FAIL")
    if c["unknown_rows"]:
        why = "".join(f"; {label}: {reason}" for label, reason in c.get("unknown_why", {}).items())
        _f(out, "VP-12", "cost", f"cost UNKNOWN: no measurement for {', '.join(c['unknown_rows'])} "
           "(config/job_speeds.json, measured by P12b); the known part is " f"${c['known_usd_worst']:.2f} worst case, and it cannot be certified until then{why}")
    return out


# --- score, drift, findings of a variant and of a file ---------------------------------------------------------------------
def score(found: list[dict]) -> int:
    """100 - 10 per REVIEW - 25 per FAIL, floor 0; INFO does not count. Shown next to the critic's score, never summed with it."""
    return max(0, 100 - 10 * sum(f["severity"] == "REVIEW" for f in found) - 25 * sum(f["severity"] == "FAIL" for f in found))


def drift(chosen: dict, now: dict) -> list[dict]:
    """VP-15: the scenario or script against the choice. ``chosen`` is the picked variant (its segments, its cost), ``now`` the
    plan as it stands now (``segments``, ``usd``). Seconds and cost drift are REVIEW (BP-146); a cost above the ``usd_worst`` the
    creator approved is FAIL (invariant 2)."""
    out: list[dict] = []
    want = {s["id"]: s.get("window_s") or sum(b["seconds"] for b in s["blocks"]) for s in chosen["segments"]}
    for s in now["segments"]:
        w = s.get("window_s") or sum(b["seconds"] for b in s["blocks"])
        if s["id"] in want and want[s["id"]] and abs(w - want[s["id"]]) / want[s["id"]] > SR.T("BP-146", "seconds_drift"):
            _f(out, "VP-15", s["id"], f"{w:.0f} s now against {want[s['id']]:.0f} s chosen (more than "
               f"{SR.T('BP-146', 'seconds_drift'):.0%}, BP-146)", sev("BP-146"))
    for sid in sorted(set(want) ^ {s["id"] for s in now["segments"]}):
        _f(out, "VP-15", sid, "a segment was added or dropped after the choice", sev("BP-146"))
    planned, approved, usd = chosen["cost"]["usd_planned"], chosen["cost"]["usd_worst"], now.get("usd")
    if isinstance(usd, (int, float)):
        if isinstance(approved, (int, float)) and usd > approved + 1e-9:
            _f(out, "VP-15", "cost", f"${usd:.2f} is above the ${approved:.2f} worst case the creator approved: ask again", "FAIL")
        elif isinstance(planned, (int, float)) and usd > planned * (1 + SR.T("BP-146", "usd_drift")) + 1e-9:
            _f(out, "VP-15", "cost", f"${usd:.2f} is more than {SR.T('BP-146', 'usd_drift'):.0%} above the planned ${planned:.2f} (BP-146)",
               sev("BP-146"))
    return out


def variant_findings(variant: dict, *, speeds: dict | None = None, caps: dict | None = None) -> list[dict]:
    """Everything the code says about one variant: the arithmetic (VP-01), the dynamics, the lanes, the cost."""
    out = contracts.variant_sums(variant)
    if out:
        return out
    prof = profile(variant["profile_id"])
    out += checks(dynamics(segments_from_variant(variant), prof), prof)
    out += lane_findings(segments_from_variant(variant))
    out += cost_checks(cost(variant, speeds=speeds, caps=caps))
    return out


def summarize(found: list[dict], dyn: dict) -> dict:
    """The derived numbers a /2 document stores per variant (``check_file`` recomputes them)."""
    return {"dynamics": {**{f"share_{k}": round(v, 3) for k, v in dyn["share"].items()},
                         "non_character": round(dyn["non_character"], 3), "narrator_share": round(dyn["narrator_share"], 3),
                         "map_run_max_s": round(dyn["map_run_max_s"], 1), "non_scene_run_max_s": round(dyn["non_scene_run_max_s"], 1),
                         "shots_per_min": round(dyn["shots_per_min"], 1)},
            "scores_code": score(found), "eligible": not any(f["severity"] == "FAIL" for f in found),
            "findings": [f"{f['severity']} {f['rule']} {f['where']}" for f in found]}


def derive(variant: dict, *, speeds: dict | None = None, caps: dict | None = None, critic=None) -> dict:
    """The numbers code owns in a /2 variant: dynamics, cost, risks and ``scores.code`` (the critic's score is kept, never computed)."""
    found = variant_findings({**variant, "dynamics": {}}, speeds=speeds, caps=caps)  # the stored shares are what is being replaced
    dyn = dynamics(segments_from_variant(variant), profile(variant["profile_id"]))
    c = cost(variant, speeds=speeds, caps=caps)
    s = summarize(found, dyn)
    return {"dynamics": s["dynamics"], "cost": {k: c[k] for k in ("usd_planned", "usd_worst", "known_usd_planned", "known_usd_worst",
                                                                  "unknown_rows", "rows")},
            "risks": s["findings"], "scores": {"code": s["scores_code"], "critic": critic}}


def rescore(doc: dict, *, speeds: dict | None = None, caps: dict | None = None) -> dict:
    """The document with every derived number recomputed (the creator's choice and the critic's scores stay)."""
    out = json.loads(json.dumps(doc))
    for v in out["variants"]:
        v.update(derive(v, speeds=speeds, caps=caps, critic=(v.get("scores") or {}).get("critic")))
    if out.get("chosen"):
        out["chosen"]["variants_sha256"] = contracts.variants_sha256(out)
    return out


def check_file(path: Path | str, *, speeds: dict | None = None, caps: dict | None = None) -> list[dict]:
    """The contract's own findings, then (script_variants/2) each variant's code findings, VP-14, the stored scores against a
    fresh computation (CN-02), and the choice against ``variants_sha256`` (CN-04)."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = contracts.errors(doc, path.parent)
    if any(f["severity"] == "FAIL" for f in out) or doc.get("schema") != "script_variants/2":
        return out
    speeds = load_speeds() if speeds is None else speeds
    seen: dict[str, str] = {}
    for v in doc["variants"]:
        found = variant_findings(v, speeds=speeds, caps=caps)
        for f in found:
            out.append(dict(f, where=f"{v['id']} {f['where']}"))
        if score(found) != v["scores"]["code"]:
            _f(out, "CN-02", f"{v['id']}.scores.code", f"stored {v['scores']['code']} but the code now says {score(found)}: re-run "
               "`variant_plan score --write` (never hand-edit a derived number)", "FAIL")
        if v["profile_id"] in seen:
            _f(out, "VP-14", f"{seen[v['profile_id']]}/{v['id']}", f"two variants of profile {v['profile_id']}: near copies, make them "
               "really different", sev("BP-141"))
        seen.setdefault(v["profile_id"], v["id"])
    ch = doc.get("chosen")
    if ch:
        picked = next((v for v in doc["variants"] if v["id"] == ch["variant_id"]), None)
        if picked is None:
            _f(out, "CN-04", "chosen.variant_id", f"{ch['variant_id']!r} is not one of the variants: the pick names nothing", "FAIL")
        elif any(f["severity"] == "FAIL" for f in variant_findings(picked, speeds=speeds, caps=caps)):
            _f(out, "CN-04", "chosen.variant_id", f"{ch['variant_id']} has a FAIL and cannot be picked (OR-31)", "FAIL")
    if ch and ch["variants_sha256"] != contracts.variants_sha256(doc):
        _f(out, "CN-04", "chosen.variants_sha256", "the variants changed after the creator's pick: ask again", "FAIL")
    return out


# --- the brief for the Opus thread (facts only, OR-24) and the worked example -------------------------------------------------
def brief(dossier_dir: Path | str, *, traits: dict | None = None) -> dict:
    """Facts the planning thread needs and nothing else: what the dossier holds (sha256), the profiles, the turn slots, the lanes
    that exist, the caps and whether job speeds are measured. No reasoning and no recommendation (OR-24)."""
    d = Path(dossier_dir)
    files = [{"path": p.relative_to(d).as_posix(), "bytes": p.stat().st_size, "sha256": contracts.sha256_file(p)}
             for p in sorted(d.rglob("*")) if p.is_file()][:200]
    caps = spend_caps.load()
    return {"dossier": {"folder": str(d), "files": files}, "traits": traits or {},
            "profiles": SR.T("BP-141", "episode_structure_profiles"), "turn_slots_D": SR.T("BP-142", "turn_slots_D"),
            "lanes": {k: {"available": v["available"], **({"phase": v["phase"]} if "phase" in v else {})} for k, v in LANES.items()},
            "caps": {"per_episode": caps.get("per_episode"), "per_pod_usd": caps.get("runpod", {}).get("per_pod_usd"),
                     "stop_fraction": ledger.STOP_FRACTION},
            "job_speeds_measured": JOB_SPEEDS.exists(), "template_d_target_s": 900}


def napoleon_variants(*, speeds: dict | None = None, caps: dict | None = None) -> dict:
    """V1 (drama-led, profile D) rebuilt from the committed shot cards and V2 (tactical, profile B) from its committed plan, both
    scored: the worked example of docs/SCRIPT_ENGINE.md. 0 FAIL for both."""
    fs = json.loads((NAPOLEON / "film_shots.json").read_text(encoding="utf-8"))
    plan = json.loads((NAPOLEON / "variant_v2.json").read_text(encoding="utf-8"))
    v1 = {"id": "v1", "title": "Two commanders, played", "profile_id": "D", "logline": plan["v1_logline"], "outline": plan["v1_outline"],
          "segments": segments_from_film_shots(fs), "cost_rows": plan["v1_cost_rows"]}
    v2 = {"id": "v2", "title": plan["title"], "profile_id": "B", "logline": plan["logline"], "outline": plan["outline"],
          "segments": plan["segments"], "cost_rows": plan["cost_rows"]}
    variants = [{k: v[k] for k in ('id', 'title', 'profile_id', 'logline', 'outline', 'segments', 'cost_rows')} |
                derive(v, speeds=speeds, caps=caps) for v in (v1, v2)]
    return {"schema": "script_variants/2", "episode_slug": "napoleon_vs_genghis",
            "dossier_sha256": contracts.sha256_file(NAPOLEON / "film_shots.json"), "variants": variants,
            "recommended": "v1", "why": plan["why"], "chosen": None}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else ""
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    if cmd == "brief" and argv:
        traits = None
        if "--traits" in argv:
            i = argv.index("--traits")
            traits = json.loads(Path(argv[i + 1]).read_text(encoding="utf-8"))
        print(json.dumps(brief(argv[0], traits=traits), indent=1, ensure_ascii=False))
        return 0
    if cmd == "napoleon":
        doc = napoleon_variants()
        text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        if write:
            (NAPOLEON / "script_variants.json").write_text(text, encoding="utf-8")
        for v in doc["variants"]:
            print(f"{v['id']} ({v['profile_id']}): score {v['scores']['code']}  {'; '.join(v['risks'])}")
        return 0
    if cmd == "score" and argv:
        path = Path(argv[0])
        doc = rescore(json.loads(path.read_text(encoding="utf-8")), speeds=load_speeds())
        for v in doc["variants"]:
            print(f"{v['id']} ({v['profile_id']}): score {v['scores']['code']}  {'; '.join(v['risks'])}")
        if write:
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return 0
    if cmd == "check" and argv:
        found = check_file(argv[0])
        for f in found:
            print(f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}")
        return 1 if any(f["severity"] == "FAIL" for f in found) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
