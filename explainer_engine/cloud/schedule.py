"""RP-11: the run plan of a paid pod is computed before the pod, every combination of its stages tried, the cheapest one taken.

The creator, 2026-11-06 14:48 UTC (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPW7UwcxZB5ntM5UAFKMtVJnA), after the step-3 pod's H100 sat idle
behind a CPU Blender frame: "add a new layer to the pod plan: compute every combination of the run before the run and always take
the cheapest, so that it does not get in the way of the existing work". The one home of the rule text is ``docs/CLOUD_RUNBOOK.md``
(RP-11); this module is what ``runpod create --schedule`` asks.

A schedule file (``pod_schedule/1``) states the pod's stage graph, never the order:

    {"schema": "pod_schedule/1", "setup_min": 10, "end_reserve_min": 10,
     "lanes": {"gpu": 1, "cpu": 1},
     "stages": [{"id": "A.frame0", "needs": [], "on": {"cpu": {"expected_min": 4, "max_min": 30},
                                                        "gpu": {"expected_min": 0.5, "max_min": 5}},
                 "measured": false, "note": "battle line pass, memory-killed on the container"},
                {"id": "C", "needs": [], "on": {"gpu": {"expected_min": 6, "max_min": 12}}, "measured": true}, ...],
     "cards": [{"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0}, ...],
     "limits": {"max_usd": 8, "max_hours": 3.5, "max_idle_gpu_share": 0.15}}

A combination is one card x one lane for every stage that may run on more than one lane x one priority order of the GPU lane.
Each is simulated twice (expected and worst minutes) by list scheduling: a free slot takes the first stage of its lane's order
whose inputs are done, so a lane waits only when nothing of its own is ready. Minutes on the GPU lane are for a card of
``gpu_speed`` 1.0 and divide by the card's speed. Nothing is ever dropped or reordered against its inputs: every combination
runs every stage the plan states (the "does not get in the way of the existing work" part). The pod bills from create to stop,
so the cost of a combination is (setup + makespan + reserve) x the card's price.

The pick: among the combinations whose WORST case fits ``max_usd`` and ``max_hours``, the lowest expected cost (ties: lower worst
cost, then less idle GPU). ``check`` refuses when nothing fits, when the pick's worst-case idle GPU share is over
``max_idle_gpu_share`` (the card waiting on something), or when the pod's own committed order costs over ``ORDER_SLACK`` more than
the pick. stdlib only.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path

SCHEMA = "pod_schedule/1"
ORDER_SLACK = 0.05          # a committed order may cost at most 5 % more (expected) than the cheapest combination
DEFAULT_IDLE_SHARE = 0.15   # worst-case idle GPU minutes / pod minutes after setup, when the plan states no limit
FULL_ENUM_MAX = 20000       # up to this many combinations every one is tried; above it a fixed-seed sample + the heuristics
SAMPLE = 4000
LANES = ("gpu", "cpu", "net")


class ScheduleError(ValueError):
    pass


def load(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = validate(spec)
    if problems:
        raise ScheduleError("; ".join(problems))
    return spec


def validate(spec: dict) -> list[str]:
    out = []
    if spec.get("schema") != SCHEMA:
        out.append(f"schema must be {SCHEMA}")
    stages = spec.get("stages") or []
    ids = [s.get("id") for s in stages]
    if not stages:
        out.append("no stages")
    if len(set(ids)) != len(ids):
        out.append("duplicate stage ids")
    lanes = spec.get("lanes") or {}
    for s in stages:
        on = s.get("on") or {}
        if not on:
            out.append(f"{s.get('id')}: 'on' names no lane")
        for lane, t in on.items():
            if lane not in LANES or lane not in lanes:
                out.append(f"{s.get('id')}: lane {lane!r} is not one of the pod's lanes {sorted(lanes)}")
            if not isinstance(t, dict) or t.get("expected_min") is None or t.get("max_min") is None:
                out.append(f"{s.get('id')}.{lane}: expected_min and max_min are both required (a max is the stage's timeout)")
            elif t["max_min"] < t["expected_min"]:
                out.append(f"{s.get('id')}.{lane}: max_min under expected_min")
        for n in s.get("needs") or []:
            if n not in ids:
                out.append(f"{s.get('id')}: needs unknown stage {n!r}")
    if not spec.get("cards"):
        out.append("no cards: name every card the create may land on, with its price")
    for c in spec.get("cards") or []:
        if c.get("price_h") is None:
            out.append(f"card {c.get('name')}: price_h missing")
    if _cycle(stages):
        out.append("the needs form a cycle")
    for k in ("setup_min", "end_reserve_min"):
        if spec.get(k) is None:
            out.append(f"{k} missing")
    return out


def _cycle(stages) -> bool:
    need = {s["id"]: set(s.get("needs") or []) for s in stages if s.get("id")}
    seen, stack = set(), set()

    def visit(n):
        if n in stack:
            return True
        if n in seen:
            return False
        seen.add(n)
        stack.add(n)
        bad = any(visit(m) for m in need.get(n, ()) if m in need)
        stack.discard(n)
        return bad
    return any(visit(n) for n in need)


def simulate(spec: dict, card: dict, lane_of: dict, order: list[str], case: str = "expected") -> dict:
    """List scheduling of one combination. ``order`` = the GPU lane's priority; other lanes keep the plan's stage order."""
    stages = {s["id"]: s for s in spec["stages"]}
    key = "expected_min" if case == "expected" else "max_min"
    speed = float(card.get("gpu_speed") or 1.0)

    def dur(sid):
        lane = lane_of[sid]
        m = float(stages[sid]["on"][lane][key])
        return m / speed if lane == "gpu" else m

    prio = {}
    for lane in spec["lanes"]:
        ids = [sid for sid in (order if lane == "gpu" else [s["id"] for s in spec["stages"]]) if lane_of.get(sid) == lane]
        prio[lane] = ids
    slots = {lane: [0.0] * int(n) for lane, n in spec["lanes"].items()}
    done, start = {}, {}
    pending = {lane: list(ids) for lane, ids in prio.items()}
    t, gpu_busy = 0.0, 0.0
    while any(pending.values()):
        progressed = False
        for lane, queue in pending.items():
            for i, free in enumerate(slots[lane]):
                if free > t + 1e-9 or not queue:
                    continue
                pick = next((sid for sid in queue if all(n in done and done[n] <= t + 1e-9 for n in stages[sid].get("needs") or [])), None)
                if pick is None:
                    continue
                queue.remove(pick)
                d = dur(pick)
                start[pick], done[pick] = t, t + d
                slots[lane][i] = t + d
                if lane == "gpu":
                    gpu_busy += d
                progressed = True
        if progressed:
            continue
        nxt = [x for lane in slots for x in slots[lane] if x > t + 1e-9] + [x for x in done.values() if x > t + 1e-9]
        if not nxt:
            raise ScheduleError(f"no stage can start at {t:.1f} min: {pending}")
        t = min(nxt)
    span = max(done.values()) if done else 0.0
    gpu_slots = int(spec["lanes"].get("gpu", 0))
    idle = max(gpu_slots * span - gpu_busy, 0.0)
    pod_min = float(spec["setup_min"]) + span + float(spec["end_reserve_min"])
    return {"span_min": round(span, 2), "pod_min": round(pod_min, 2), "usd": round(pod_min / 60 * float(card["price_h"]), 3),
            "gpu_busy_min": round(gpu_busy, 2), "gpu_idle_min": round(idle, 2),
            "idle_share": round(idle / (gpu_slots * span), 3) if gpu_slots and span else 0.0,
            "start": {k: round(v, 2) for k, v in start.items()}}


def _topo_orders(ids: list[str], needs: dict, limit: int):
    """Every order of ``ids`` that keeps each stage after the ids it needs (needs outside ``ids`` are ignored), up to ``limit``."""
    out = []

    def rec(prefix, left):
        if len(out) >= limit:
            return
        if not left:
            out.append(list(prefix))
            return
        for sid in list(left):
            if all(n not in left for n in needs.get(sid, ())):
                left.remove(sid)
                prefix.append(sid)
                rec(prefix, left)
                prefix.pop()
                left.add(sid)
                if len(out) >= limit:
                    return
    rec([], set(ids))
    return out


def combinations(spec: dict):
    """Yield (card, lane_of, gpu_order) for every combination, or a fixed-seed sample plus the heuristic orders when too many."""
    stages = spec["stages"]
    needs = {s["id"]: set(s.get("needs") or []) for s in stages}
    flex = [s["id"] for s in stages if len(s["on"]) > 1]
    fixed = {s["id"]: next(iter(s["on"])) for s in stages if len(s["on"]) == 1}
    choices = [sorted(next(s for s in stages if s["id"] == f)["on"]) for f in flex]
    assigns = []
    for pick in itertools.product(*choices) if flex else [()]:
        lane_of = dict(fixed)
        lane_of.update(dict(zip(flex, pick)))
        assigns.append(lane_of)
    plan_order = [s["id"] for s in stages]
    total, per = 0, []
    for lane_of in assigns:
        g = [sid for sid in plan_order if lane_of[sid] == "gpu"]
        orders = _topo_orders(g, needs, FULL_ENUM_MAX + 1)
        per.append((lane_of, g, orders))
        total += len(orders) * len(spec["cards"])
    exhaustive = total <= FULL_ENUM_MAX
    rng = random.Random(11)
    for lane_of, g, orders in per:
        if not exhaustive:
            heur = [g, sorted(g, key=lambda s: -_crit(spec, s, lane_of)), sorted(g, key=lambda s: _mins(spec, s, lane_of)),
                    sorted(g, key=lambda s: -_mins(spec, s, lane_of))]
            heur = [o for o in heur if _respects(o, needs)]
            k = max(1, SAMPLE // max(len(per), 1))
            orders = heur + rng.sample(orders, min(k, len(orders)))
        for card in spec["cards"]:
            for o in orders:
                yield card, lane_of, o
    combinations.last = {"total": total, "exhaustive": exhaustive}


def _mins(spec, sid, lane_of):
    s = next(x for x in spec["stages"] if x["id"] == sid)
    return float(s["on"][lane_of[sid]]["expected_min"])


def _crit(spec, sid, lane_of):
    """Expected minutes of the longest chain that starts at ``sid`` (critical path first)."""
    kids = [s["id"] for s in spec["stages"] if sid in (s.get("needs") or [])]
    return _mins(spec, sid, lane_of) + max((_crit(spec, k, lane_of) for k in kids), default=0.0)


def _respects(order, needs):
    pos = {s: i for i, s in enumerate(order)}
    return all(pos[n] < pos[s] for s in order for n in needs.get(s, ()) if n in pos)


def plan(spec: dict) -> dict:
    lim = spec.get("limits") or {}
    max_usd, max_h = lim.get("max_usd"), lim.get("max_hours")
    rows = []
    for card, lane_of, order in combinations(spec):
        exp, worst = simulate(spec, card, lane_of, order, "expected"), simulate(spec, card, lane_of, order, "worst")
        fits = (max_usd is None or worst["usd"] <= max_usd + 1e-9) and (max_h is None or worst["pod_min"] <= max_h * 60 + 1e-9)
        rows.append({"card": card["name"], "lanes": {k: v for k, v in lane_of.items()}, "gpu_order": order,
                     "expected": exp, "worst": worst, "fits": fits})
    info = dict(getattr(combinations, "last", {}))
    ok = [r for r in rows if r["fits"]]
    pool = ok or rows
    pool.sort(key=lambda r: (r["expected"]["usd"], r["worst"]["usd"], r["worst"]["gpu_idle_min"]))
    best = pool[0] if pool else None
    seen, ups = set(), []
    for r in pool[1:]:
        k = (r["card"], r["expected"]["usd"], r["worst"]["usd"], r["worst"]["gpu_idle_min"])
        if k not in seen and k != (best["card"], best["expected"]["usd"], best["worst"]["usd"], best["worst"]["gpu_idle_min"]):
            seen.add(k)
            ups.append(r)
        if len(ups) == 3:
            break
    return {"schema": "pod_schedule_plan/1", "combinations": len(rows), "of_total": info.get("total", len(rows)),
            "exhaustive": info.get("exhaustive", True), "fitting": len(ok), "best": best,
            "runners_up": ups}


def committed(spec: dict, card: str, gpu_order: list[str], lanes: dict | None = None) -> dict:
    """The cost of the pod's own committed order (what its script will do), for the slack check."""
    c = next((x for x in spec["cards"] if x["name"] == card), None)
    if c is None:
        raise ScheduleError(f"card {card!r} is not in the schedule's cards")
    lane_of = {s["id"]: next(iter(s["on"])) for s in spec["stages"]}
    lane_of.update(lanes or {})
    g = [sid for sid in gpu_order if lane_of.get(sid) == "gpu"] + [s["id"] for s in spec["stages"]
                                                                    if lane_of[s["id"]] == "gpu" and s["id"] not in gpu_order]
    return {"expected": simulate(spec, c, lane_of, g, "expected"), "worst": simulate(spec, c, lane_of, g, "worst")}


def rp11(path, *, max_usd=None, max_hours=None, measure=False, test=None) -> list[str]:
    """What ``runpod create`` asks: a script pod names its schedule file; the create's own caps replace the file's limits."""
    from explainer_engine.cloud.batching import EXEMPT_TESTS
    if test in EXEMPT_TESTS or measure:
        return []
    if not path:
        return ["RP-11: --schedule <pod_schedule.json> is required for a script pod: the stage graph (lanes, needs, expected and max "
                "minutes, cards), so every combination is costed before the pod (python -m explainer_engine.cloud.schedule check)"]
    try:
        spec = load(path)
    except (OSError, ValueError) as e:
        return [f"RP-11: schedule {path}: {e}"]
    spec.setdefault("limits", {})
    if max_usd is not None:
        spec["limits"]["max_usd"] = max_usd
    if max_hours is not None:
        spec["limits"]["max_hours"] = max_hours
    return check(spec)


def check(spec: dict, result: dict | None = None, own: dict | None = None) -> list[str]:
    """RP-11 refusals (empty = fine). ``own`` = ``committed()`` of the pod's own order, when the script fixes one."""
    result = result or plan(spec)
    lim = spec.get("limits") or {}
    share = float(lim.get("max_idle_gpu_share", DEFAULT_IDLE_SHARE))
    best = result["best"]
    out = []
    if best is None:
        return ["RP-11: no combination to compare"]
    if not result["fitting"]:
        out.append(f"RP-11: no combination fits the caps in its worst case (cheapest worst ${best['worst']['usd']} / "
                   f"{best['worst']['pod_min'] / 60:.2f} h vs ${lim.get('max_usd')} / {lim.get('max_hours')} h)")
    if int(spec["lanes"].get("gpu", 0)) and best["worst"]["idle_share"] > share + 1e-9:
        out.append(f"RP-11: even the cheapest combination leaves the GPU idle {best['worst']['gpu_idle_min']:.0f} min in the worst case "
                   f"({best['worst']['idle_share']:.0%} > {share:.0%}): move a stage onto the GPU, cut a wait, or split the pod")
    if own is not None:
        lim_usd = best["expected"]["usd"] * (1 + ORDER_SLACK)
        if own["expected"]["usd"] > lim_usd + 1e-9:
            out.append(f"RP-11: the pod's own order costs ${own['expected']['usd']} expected, over the cheapest ${best['expected']['usd']} "
                       f"+ {ORDER_SLACK:.0%}: use the computed order {best['gpu_order']} on {best['card']}")
        if int(spec["lanes"].get("gpu", 0)) and own["worst"]["idle_share"] > share + 1e-9:
            out.append(f"RP-11: the pod's own order leaves the GPU idle {own['worst']['gpu_idle_min']:.0f} min in the worst case "
                       f"({own['worst']['idle_share']:.0%} > {share:.0%})")
    return out


def report(spec: dict, result: dict) -> str:
    b = result["best"]
    head = (f"{result['combinations']} combinations tried of {result['of_total']}"
            f"{'' if result['exhaustive'] else ' (sampled: too many to try all)'}; {result['fitting']} fit the caps")
    if b is None:
        return head
    lines = [head, f"cheapest: {b['card']}  expected ${b['expected']['usd']} ({b['expected']['pod_min'] / 60:.2f} h, idle GPU "
                   f"{b['expected']['gpu_idle_min']:.0f} min)  worst ${b['worst']['usd']} ({b['worst']['pod_min'] / 60:.2f} h, idle GPU "
                   f"{b['worst']['gpu_idle_min']:.0f} min)",
             "  gpu order: " + " > ".join(b["gpu_order"]),
             "  lanes: " + ", ".join(f"{k}={v}" for k, v in sorted(b["lanes"].items()) if len(_on(spec, k)) > 1)]
    for r in result["runners_up"]:
        lines.append(f"  next: {r['card']} expected ${r['expected']['usd']} worst ${r['worst']['usd']} idle {r['worst']['gpu_idle_min']:.0f} min")
    return "\n".join(lines)


def _on(spec, sid):
    return next(s for s in spec["stages"] if s["id"] == sid)["on"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.cloud.schedule", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "check"):
        p = sub.add_parser(name)
        p.add_argument("spec")
        p.add_argument("--out", help="write the plan JSON here")
        p.add_argument("--card", help="check: the card the pod's own order is meant for")
        p.add_argument("--order", help="check: the pod's own GPU order, comma separated")
    a = ap.parse_args(argv)
    spec = load(a.spec)
    res = plan(spec)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(report(spec, res))
    if a.cmd == "check":
        own = committed(spec, a.card, a.order.split(",")) if a.card and a.order else None
        why = check(spec, res, own)
        for w in why:
            print("refused", w)
        return 1 if why else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
