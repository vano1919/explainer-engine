"""Modal variant of the RP-11 run plan: every GPU/CPU choice and container split of a job's steps, the cheapest passing one taken.

The creator, 2026-11-07 (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWXL7x95HTyHNFSpCHonHTCr, relayed): the cheapest-combination rule that RunPod
has (``cloud/schedule.py``, RP-11) is wanted for Modal. Modal differs from a pod: there is nothing to leave running, every
function is a container billed per second while it runs, so the unit of choice is (hardware, split into N containers) per STEP,
and steps with different best hardware are separate functions (a GPU step and a CPU step never share a container).

Model (all numbers of a spec are labelled ``measured`` / ``estimate``; nothing here is measured on Modal yet):
  * price table = modal.com/pricing (GPU per second per card; CPU per PHYSICAL core = 2 vCPU; memory per GiB; a GPU container also
    bills its own cores and memory). VRAM and architecture are NVIDIA's, the pricing page does not list them.
  * a step has ``work`` (GPU: seconds on a speed-1.0 card, the H100 reference of RP-11; CPU: physical-core seconds), a per-container
    ``overhead_s`` (container start + weights read from the Volume at ``volume_gb_s``), ``max_split`` (independent units),
    ``min_vram_gb`` (GPU steps) and ``mem_gib``.
  * choice (card or cores, n containers): wall = overhead + work/(speed*n); cost = n*overhead*rate + work/speed*rate.
  * worst case = work x ``slack`` plus ``retries``-1 wasted attempts of one failed unit (``unit_work``: a picture, a frame, the whole
    clip) with a fresh container start (``overhead_s``).
  * steps run as a graph: wall = critical path (steps without a dependency between them run concurrently), cost = the sum.
  * the $30 monthly Starter credit is applied: real charge = max(0, cost - credit_left).
  * the pick: among combinations whose WORST case fits ``max_usd`` and ``max_hours`` (and the account's 10 GPU containers at once),
    the lowest expected cost (ties: lower wall); every step's options are first reduced to the Pareto set (cost, worst, wall).
ASSUMPTIONS to check: CPU steps scale linearly with cores inside one container (frames are independent, so splitting into
containers is the safer lever); a GPU card's speed is its H100-relative estimate; Volume read 1.5 GB/s.
stdlib only; offline (the price table is data, tests use a fake one).
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys

SCHEMA = "modal_schedule/1"
PRICES_DATE = "2026-11-07"
PRICES_URL = "https://modal.com/pricing"

# per second (modal.com/pricing, fetched 2026-11-07); vram/arch = NVIDIA specs (not on the Modal page);
# speed = relative to H100 = 1.0: A100 0.6 is the project's estimate (RP-11), the rest are ESTIMATES (no LTX speed measured anywhere).
GPUS = {
    "T4":            {"usd_s": 0.000164, "vram_gb": 16,  "arch": "Turing",    "speed": 0.08},
    "L4":            {"usd_s": 0.000222, "vram_gb": 24,  "arch": "Ada",       "speed": 0.18},
    "A10":           {"usd_s": 0.000306, "vram_gb": 24,  "arch": "Ampere",    "speed": 0.25},
    "L40S":          {"usd_s": 0.000542, "vram_gb": 48,  "arch": "Ada",       "speed": 0.50},
    "A100-40GB":     {"usd_s": 0.000583, "vram_gb": 40,  "arch": "Ampere",    "speed": 0.60},
    "A100-80GB":     {"usd_s": 0.000694, "vram_gb": 80,  "arch": "Ampere",    "speed": 0.60},
    "RTX-PRO-6000":  {"usd_s": 0.000842, "vram_gb": 96,  "arch": "Blackwell", "speed": 0.85},
    "H100":          {"usd_s": 0.001097, "vram_gb": 80,  "arch": "Hopper",    "speed": 1.00},
    "H200":          {"usd_s": 0.001261, "vram_gb": 141, "arch": "Hopper",    "speed": 1.15},
    "B200":          {"usd_s": 0.001736, "vram_gb": 192, "arch": "Blackwell", "speed": 1.50},
    "B300":          {"usd_s": 0.001972, "vram_gb": 288, "arch": "Blackwell", "speed": 1.60},
}
CPU_CORE_S = 0.0000131       # per physical core (2 vCPU) per second
MEM_GIB_S = 0.00000222       # per GiB per second
GPU_CONCURRENCY = 10         # Starter account limit; containers 100
CONTAINERS = 100
CORE_CHOICES = (1, 2, 4, 8)
SPLITS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 100)


class ModalScheduleError(ValueError):
    pass


def validate(spec: dict) -> list[str]:
    errs = []
    if spec.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    ids = [s.get("id") for s in spec.get("steps", [])]
    if not ids or len(set(ids)) != len(ids):
        errs.append("steps need unique ids")
    for s in spec.get("steps", []):
        if s.get("kind") not in ("gpu", "cpu"):
            errs.append(f"{s.get('id')}: kind must be gpu or cpu")
        if not isinstance(s.get("work"), (int, float)) or s["work"] <= 0:
            errs.append(f"{s.get('id')}: work must be > 0")
        for n in s.get("needs", []):
            if n not in ids:
                errs.append(f"{s['id']}: needs unknown step {n}")
        if s.get("measured") not in (True, False):
            errs.append(f"{s.get('id')}: state measured true/false (nothing is measured on Modal yet)")
    return errs


def _rate_gpu(card: dict, step: dict) -> float:
    return card["usd_s"] + step.get("cores", 2) * CPU_CORE_S + step.get("mem_gib", 32) * MEM_GIB_S


def _rate_cpu(cores: int, step: dict) -> float:
    return cores * CPU_CORE_S + step.get("mem_gib", 8) * MEM_GIB_S


def _opt(step, hw, n, rate, speed, slack, retries):
    oh = step.get("overhead_s", 20.0)
    work = step["work"] / speed
    wall = oh + work / n
    cost = n * oh * rate + work * rate
    wwall = oh + work * slack / n
    unit = min(step.get("unit_work", step["work"] / n * speed) / speed, work / n)  # the retried unit (a picture, a frame), seconds on this hardware
    wcost = n * oh * rate + work * slack * rate + (retries - 1) * (oh + unit * slack) * rate
    return {"step": step["id"], "hw": hw, "n": n, "wall_s": wall, "cost": cost, "worst_wall_s": wwall,
            "worst_cost": wcost, "rate_s": rate}


def step_options(step: dict, gpus: dict, slack: float, retries: int) -> list[dict]:
    """every (hardware, split) of one step, reduced to the Pareto set of (cost, worst cost, wall)."""
    out = []
    ms = min(int(step.get("max_split", 1)), CONTAINERS)
    if step["kind"] == "gpu":
        for name, c in gpus.items():
            if c["vram_gb"] < step.get("min_vram_gb", 0):
                continue
            for n in SPLITS:
                if n <= min(ms, GPU_CONCURRENCY):
                    out.append(_opt(step, name, n, _rate_gpu(c, step), c["speed"], slack, retries))
    else:
        for cores in CORE_CHOICES:
            for n in SPLITS:
                if n <= ms:
                    o = _opt(step, f"cpu{cores}", n, _rate_cpu(cores, step), float(cores), slack, retries)
                    out.append(o)
    out.sort(key=lambda o: (o["cost"], o["worst_cost"], o["wall_s"]))
    keep, best_w, best_ww = [], float("inf"), float("inf")
    for o in out:  # increasing cost: keep an option only if it is faster (expected or worst) than every cheaper one
        if o["wall_s"] < best_w - 1e-9 or o["worst_wall_s"] < best_ww - 1e-9:
            keep.append(o)
            best_w, best_ww = min(best_w, o["wall_s"]), min(best_ww, o["worst_wall_s"])
    return keep


def _finish(spec, choice, key):
    done = {}
    for s in spec["steps"]:  # steps are listed in dependency order (checked by _order)
        start = max([done[n] for n in s.get("needs", [])], default=0.0)
        done[s["id"]] = start + choice[s["id"]][key]
    return max(done.values())


def _order(spec):
    seen, out = set(), []
    steps = {s["id"]: s for s in spec["steps"]}

    def visit(i, stack=()):
        if i in stack:
            raise ModalScheduleError(f"cycle at {i}")
        if i in seen:
            return
        for n in steps[i].get("needs", []):
            visit(n, stack + (i,))
        seen.add(i)
        out.append(steps[i])
    for i in steps:
        visit(i)
    return {**spec, "steps": out}


def _gpu_peak(spec, choice) -> int:
    """most GPU containers that can run at once: the widest set of mutually independent GPU steps (conservative sum)."""
    steps = {s["id"]: s for s in spec["steps"]}
    gp = [s["id"] for s in spec["steps"] if s["kind"] == "gpu"]

    def anc(i, acc=None):
        acc = set() if acc is None else acc
        for n in steps[i].get("needs", []):
            if n not in acc:
                acc.add(n)
                anc(n, acc)
        return acc
    a = {i: anc(i) for i in steps}
    best = 0
    for r in range(1, len(gp) + 1):
        for grp in itertools.combinations(gp, r):
            if all(x not in a[y] and y not in a[x] for x, y in itertools.combinations(grp, 2)):
                best = max(best, sum(choice[g]["n"] for g in grp))
    return best


def plan(spec: dict, gpus: dict | None = None, top: int = 5) -> dict:
    errs = validate(spec)
    if errs:
        raise ModalScheduleError("; ".join(errs))
    spec = _order(spec)
    gpus = gpus or GPUS
    lim = spec.get("limits", {})
    slack, retries = float(spec.get("slack", 1.5)), int(spec.get("retries", 3))
    credit = float(spec.get("credit_usd", 30.0))
    opts = [step_options(s, gpus, slack, retries) for s in spec["steps"]]
    for s, o in zip(spec["steps"], opts):
        if not o:
            raise ModalScheduleError(f"{s['id']}: no hardware fits (min_vram_gb {s.get('min_vram_gb')})")
    rows = []
    for combo in itertools.product(*opts):
        ch = {o["step"]: o for o in combo}
        if _gpu_peak(spec, ch) > GPU_CONCURRENCY:
            continue
        cost = sum(o["cost"] for o in combo)
        wcost = sum(o["worst_cost"] for o in combo)
        wall, wwall = _finish(spec, ch, "wall_s"), _finish(spec, ch, "worst_wall_s")
        rows.append({"choice": {k: (v["hw"], v["n"]) for k, v in ch.items()}, "cost": cost, "worst_cost": wcost,
                     "wall_s": wall, "worst_wall_s": wwall, "charge": max(0.0, cost - credit),
                     "worst_charge": max(0.0, wcost - credit), "parts": {k: round(v["cost"], 4) for k, v in ch.items()}})
    fit = [r for r in rows
           if r["worst_cost"] <= lim.get("max_usd", float("inf")) and r["worst_wall_s"] <= lim.get("max_hours", float("inf")) * 3600]
    fit.sort(key=lambda r: (r["cost"], r["wall_s"]))
    fastest = min(fit, key=lambda r: (r["wall_s"], r["cost"])) if fit else None
    seen, runners = set(), []
    for r in fit:
        k = tuple(sorted(r["choice"].items()))
        if k not in seen:
            seen.add(k)
            runners.append(r)
        if len(runners) >= top:
            break
    over = None
    if not fit and rows:  # nothing fits the caps: show the lowest-worst-case combination and by how much it overshoots
        over = min(rows, key=lambda r: (r["worst_cost"], r["cost"]))
        over = {**over, "over_usd": round(over["worst_cost"] - lim.get("max_usd", 0.0), 2)}
    return {"job": spec.get("job"), "combos": len(rows), "passing": len(fit), "pick": fit[0] if fit else None,
            "over_cap_best": over,
            "runners_up": runners[1:], "fastest": fastest, "limits": lim, "credit_usd": credit}


def report(res: dict) -> str:
    def line(tag, r):
        ch = ", ".join(f"{k}={hw}x{n}" for k, (hw, n) in r["choice"].items())
        return (f"{tag:<9} exp ${r['cost']:.2f} (worst ${r['worst_cost']:.2f})  wall {r['wall_s']/60:.1f} min "
                f"(worst {r['worst_wall_s']/60:.1f})  real charge after credit ${r['charge']:.2f}\n          {ch}")
    out = [f"job {res['job']}: {res['combos']} combinations, {res['passing']} pass {res['limits']} (credit ${res['credit_usd']:.0f}); all speeds ESTIMATES"]
    if not res["pick"]:
        o = res.get("over_cap_best")
        extra = [line("least-bad", o), f"worst case is ${o['over_usd']:.2f} over the cap (3 attempts, x{1.5} slack); expected cost is fine"] if o else []
        return "\n".join(out + ["NOTHING PASSES the caps"] + extra)
    out.append(line("PICK", res["pick"]))
    for i, r in enumerate(res["runners_up"], 1):
        out.append(line(f"runner {i}", r))
    out.append(line("fastest", res["fastest"]))
    return "\n".join(out)


def job_spec(job: str) -> dict:
    """p15d pilot (24 stills + 2 mouth sheets + one 121-f LTX clip) or a film: J5 frames = total frames - 121 LTX frames.
    work/overhead are estimates from the RP-11 numbers (Qwen 26 pictures = 16.6 min on the H100 reference; LTX 121 f = 3.8 min;
    J5 background 1.3 s/frame and assemble_25d 8 s/frame on 4 vCPU = 2 physical cores, given by the J5 thread, not re-measured)."""
    vol = 1.5  # GB/s, Volume read, ESTIMATE
    qwen_total = 996.0
    steps = [
        {"id": "qwen_stills", "kind": "gpu", "work": qwen_total * 24 / 26, "min_vram_gb": 40, "max_split": 4,
         "overhead_s": 25 + 33.2 / vol + 60, "mem_gib": 48, "unit_work": qwen_total / 26, "measured": False},
        {"id": "mouth_sheets", "kind": "gpu", "work": qwen_total * 2 / 26, "min_vram_gb": 40, "max_split": 2,
         "overhead_s": 25 + 33.2 / vol + 60, "mem_gib": 48, "unit_work": qwen_total / 26, "needs": ["qwen_stills"], "measured": False},
        {"id": "ltx_clip", "kind": "gpu", "work": 228.0, "min_vram_gb": 80, "max_split": 1,
         "overhead_s": 25 + 71.1 / vol + 90, "mem_gib": 64, "needs": ["qwen_stills"], "measured": False},
    ]
    if job == "p15d":
        return {"schema": SCHEMA, "job": "p15d", "steps": steps, "limits": {"max_usd": 3.7, "max_hours": 2.7}}
    frames = {"film24": 576 - 121, "film21": 517 - 121}[job]
    steps += [
        {"id": "j5_background", "kind": "cpu", "work": 2.6 * frames, "max_split": 48, "overhead_s": 30, "mem_gib": 8, "unit_work": 2.6,
         "needs": ["qwen_stills"], "measured": False},
        {"id": "assemble_25d", "kind": "cpu", "work": 16.0 * frames, "max_split": 100, "overhead_s": 30, "mem_gib": 8, "unit_work": 16.0,
         "needs": ["j5_background", "mouth_sheets"], "measured": False},
        {"id": "ffmpeg_join", "kind": "cpu", "work": 60.0, "max_split": 1, "overhead_s": 20, "mem_gib": 4,
         "needs": ["assemble_25d", "ltx_clip"], "measured": False},
    ]
    return {"schema": SCHEMA, "job": job, "steps": steps, "limits": {"max_usd": 4.0, "max_hours": 2.7}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("job", nargs="?", default="p15d", choices=["p15d", "film21", "film24"])
    ap.add_argument("--spec", help="a modal_schedule/1 JSON file instead of a built-in job")
    ap.add_argument("--max-usd", type=float)
    ap.add_argument("--max-hours", type=float)
    ap.add_argument("--cards", help="comma list of GPU names to allow (e.g. A100-80GB,H100: the two with a project speed basis)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    spec = json.load(open(a.spec)) if a.spec else job_spec(a.job)
    if a.max_usd is not None or a.max_hours is not None:
        spec["limits"] = {**spec.get("limits", {}), **({"max_usd": a.max_usd} if a.max_usd is not None else {}),
                          **({"max_hours": a.max_hours} if a.max_hours is not None else {})}
    gp = {k: v for k, v in GPUS.items() if k in a.cards.split(',')} if a.cards else None
    res = plan(spec, gpus=gp)
    print(json.dumps(res, indent=1) if a.json else report(res))
    return 0 if res["pick"] else 1


if __name__ == "__main__":
    sys.exit(main())
