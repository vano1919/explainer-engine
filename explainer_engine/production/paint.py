"""Paint an episode's pictures, one approved batch at a time (OR-01..OR-04, PP-01..PP-07; audit 2026-10-19).

    python -m explainer_engine.production.paint plan    <script.json> --out <pictures dir> --id B1 --provider gemini
                                                        [--model M --size S --batch] [--only id,id] [--first] [--limit N]
                                                        [--purpose "..."] [--reusable]                            # free
    python -m explainer_engine.production.paint approve <plan.json> --run jobs/<run>/run.json --by <name> --ref <message>
    python -m explainer_engine.production.paint run     <plan.json> <script.json> --run jobs/<run>/run.json --out <dir>
                                                        [--refs DIR] [--workers 4] [--wait 1500]
    python -m explainer_engine.production.paint collect <batch name> <plan.json> --run ... --out ...

``plan`` is free: it takes the compiled prompts and references of the pictures still to paint, prices the batch at every known
provider (the table the creator chooses from) and writes ``<out>/plans/<id>.json`` with a hash. The provider has no default:
Claude asks the creator which one to use and never paints without the answer. ``approve`` records the creator's yes (who,
and which message) against that hash in the run ledger. ``run`` refuses unless: the script validates with 0 FAIL (PV-11 lints
every painted prompt), the plan has no PP FAIL, and the ledger holds an approval for exactly this hash. Then every picture is
reserved in the ledger before its call and recorded with its prompt hash as soon as it arrives, so a stop, a cap or a crash
loses nothing; a re-run skips what was painted from the same prompt, repaints a picture whose prompt changed (in a new plan),
never re-sends an item of an open batch, and stops an item after three failures.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.core.store import write_json_atomic
from explainer_engine.imagegen import plan as P
from explainer_engine.imagegen.gemini import ChargeUncertain, GeminiClient, GeminiError, open_batches
from explainer_engine.production import compile as C
from explainer_engine.production import script as S

MAX_FAILURES = 3


def ref_bytes(dirs: list[Path], doc: dict, ref: str) -> bytes:
    from PIL import Image
    name = (doc.get("library", {}).get(ref) or {}).get("file") or f"{ref}.png"
    for d in dirs:
        p = d / name
        if p.exists():
            im = Image.open(p).convert("RGB")
            im.thumbnail((1280, 720))
            b = io.BytesIO()
            im.save(b, "PNG")
            return b.getvalue()
    raise FileNotFoundError(f"reference {ref!r} ({name}) not found in {[str(d) for d in dirs]}")


def as_jpeg(png: bytes, quality: int = 90) -> bytes:
    """A smaller reference for the batch tier (inline requests stay under 20 MB)."""
    from PIL import Image
    b = io.BytesIO()
    Image.open(io.BytesIO(png)).convert("RGB").save(b, "JPEG", quality=quality)
    return b.getvalue()


def to_paint(doc: dict) -> list[dict]:
    """Every used picture without a file that an engine paints: gemini (prompt + style refs) and pod_ref (edit + hero refs)."""
    gem, pod = C.jobs(doc)
    return ([{"id": j["id"], "prompt": j["prompt"], "refs": [f"{r}.png" for r in j["refs"]], "first_use": j["first_use"]}
             for j in gem] +
            [{"id": j["id"], "prompt": j["prompt"] + C.POD_SUFFIX, "refs": j["refs"], "first_use": j["first_use"]}
             for j in pod["pictures"]])


def pending(items: list[dict], out: Path, run: Run | None) -> list[dict]:
    """Items not yet painted from their current prompt (a PNG painted from another prompt is stale and painted again)."""
    done = (run.data["items"].get("pictures", {}) if run else {})
    todo = []
    for it in items:
        rec = done.get(it["id"])
        if (out / f"{it['id']}.png").exists() and (rec is None or rec.get("hash") in (None, P.item_hash(it))):
            continue  # painted (by an older run without a hash, or from this prompt)
        todo.append(it)
    return todo


def preflight(plan: dict, doc: dict, dirs: list[Path], run: Run, script_path: Path | None = None) -> list[str]:
    """Every reason not to spend (empty = go)."""
    from explainer_engine.production import validate as V
    why = []
    from explainer_engine.scripting import claims
    cmap = claims.load_map(script_path) if script_path else None
    fails = [f for f in V.check_script(doc, picture_dirs=dirs, claim_map=cmap) if f["severity"] == "FAIL"]
    why += [f"{f['rule']} {f['where']}: {f['detail']}" for f in fails]
    why += [f"{f['rule']} {f['where']}: {f['detail']}" for f in P.check(plan, doc) if f["severity"] == "FAIL"]
    if not run.approved(plan["id"], plan["hash"]):
        why.append(f"PP-02 plan {plan['id']} ({plan['hash']}) has no approval in {run.path}: ask the creator, then `paint approve`")
    return why


def cmd_plan(a) -> int:
    path = Path(a.script)
    doc = S.load(path)
    out = Path(a.out)
    run = Run.open(a.run) if a.run else None
    items = pending(to_paint(doc), out, run)
    if a.only:
        want = set(a.only.split(","))
        items = [i for i in items if i["id"] in want]
    if a.first:
        items = items[:1]
    if a.limit:
        items = items[:a.limit]
    plan = P.make(a.id, doc["episode"]["id"], items, provider=a.provider, model=a.model, size=a.size, batch=a.batch,
                  purpose=a.purpose or "", reusable=a.reusable)
    dest = write_json_atomic(out / "plans" / f"{a.id}.json", plan)
    print(f"plan {a.id}: {len(items)} pictures, {plan['provider']} {plan['model'] or ''} {plan['size'] or ''}"
          f"{' batch' if a.batch else ''}, estimate ${plan['estimate_usd']:.3f}, hash {plan['hash']} -> {dest}")
    print(P.table(P.options(items), chosen=plan))
    for f in P.check(plan, doc):
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    print("nothing is painted until the creator chooses a provider and `paint approve` records the yes")
    return 0


def cmd_approve(a) -> int:
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    if P.plan_hash(plan) != plan["hash"]:
        print("PP-02: the plan was edited after it was made; make it again")
        return 1
    run = Run.open(a.run)
    run.approve(plan["id"], plan["hash"], by=a.by, ref=a.ref, provider=plan["provider"], usd=plan["estimate_usd"])
    print(f"approved {plan['id']} ({plan['hash']}): {len(plan['items'])} pictures, {plan['provider']}, ${plan['estimate_usd']:.3f}")
    return 0


def _load(a):
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    path = Path(a.script)
    doc = S.load(path)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dirs = [Path(x) for x in a.refs] + [path.parent / d for d in doc.get("picture_dirs", [])] + [out]
    return plan, doc, out, dirs


def cmd_run(a) -> int:
    plan, doc, out, dirs = _load(a)
    run = Run.open(a.run)
    why = preflight(plan, doc, dirs, run, Path(a.script))
    if why:
        print("refused, nothing was sent:")
        for w in why:
            print("  " + w)
        return 2
    if not P.PROVIDERS[plan["provider"]]["paints_here"]:
        print(f"plan {plan['id']} is approved for {plan['provider']}: {P.PROVIDERS[plan['provider']]['note']}. "
              f"Run it there with {a.plan}; record each picture with its hash in {run.path}.")
        return 0
    client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
    open_items = open_batches(out / "_gemini")
    todo = []
    for it in pending(plan["items"], out, run):
        if it["id"] in open_items:
            print(f"skip {it['id']}: in open batch {open_items[it['id']]} (collect it; it is never sent twice)")
        elif len(run.data["failures"].get(it["id"], [])) >= MAX_FAILURES:
            print(f"skip {it['id']}: stopped after {MAX_FAILURES} failures (OR-04)")
        else:
            todo.append(it)
    print(f"{len(todo)} pictures to paint; spent so far ${run.spent('gemini_usd'):.3f} of cap "
          f"{run.data['caps'].get('gemini_usd')} (stop at 80 %)")
    if plan.get("batch"):
        return _run_batch(a, todo, doc, dirs, out, run, client, plan)
    stats = {"painted": 0, "failed": 0, "stop": None}

    def one(it: dict) -> None:
        key = it["id"]
        if stats["stop"]:
            return
        try:
            refs = [ref_bytes(dirs, doc, r.removesuffix(".png")) for r in it["refs"]]
            p = client.generate(key, it["prompt"], model=plan["model"], size=plan["size"], refs=refs)
            (out / f"{key}.png").write_bytes(Path(p).read_bytes())
            run.done("pictures", key, file=f"{key}.png", plan=plan["id"], hash=P.item_hash(it),
                     usd=P.price("gemini", plan["model"], plan["size"], len(refs)))
            stats["painted"] += 1
            print("painted", key, f"${run.spent('gemini_usd'):.3f}", flush=True)
        except CapReached as exc:
            stats["stop"] = str(exc)
            print("STOP:", exc, flush=True)
        except ChargeUncertain as exc:  # never retried: it may have been billed
            stats["failed"] += 1
            run.fail(key, f"charge uncertain: {exc}")
            print("uncertain", key, str(exc)[:120], flush=True)
        except (GeminiError, FileNotFoundError) as exc:
            stats["failed"] += 1
            more = run.fail(key, str(exc))
            print("failed", key, "(may be tried again)" if more else f"(stopped after {MAX_FAILURES})", str(exc)[:120], flush=True)

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        list(pool.map(one, todo))
    if stats["stop"]:
        run.phase("5_pictures", "STOPPED", stats["stop"])
        return 3
    print(f"painted {stats['painted']}, failed {stats['failed']}")
    return 0 if not stats["failed"] else 1


def _record(res: dict, plan: dict, out: Path, run: Run, batch: str) -> int:
    by_id = {i["id"]: i for i in plan["items"]}
    failed = 0
    for item, val in res["items"].items():
        if isinstance(val, Path):
            (out / f"{item}.png").write_bytes(val.read_bytes())
            run.done("pictures", item, file=f"{item}.png", batch=batch, plan=plan["id"],
                     hash=P.item_hash(by_id[item]) if item in by_id else None)
            print("painted", item, flush=True)
        else:
            failed += 1
            run.fail(item, str(val))
            print("failed", item, str(val)[:100], flush=True)
    return failed


def _run_batch(a, todo, doc, dirs, out, run, client, plan) -> int:
    """Half-price tier: submit in groups under the inline size limit, then wait for the answers and record every picture."""
    groups, group, size_now = [], [], 0
    for it in todo:
        try:
            refs = [as_jpeg(ref_bytes(dirs, doc, r.removesuffix(".png"))) for r in it["refs"]]
        except FileNotFoundError as exc:
            print("skip", it["id"], exc)
            continue
        item = {"name": it["id"], "prompt": it["prompt"], "refs": refs}
        w = sum(len(r) for r in refs) * 4 // 3
        if group and size_now + w > 14_000_000:
            groups.append(group)
            group, size_now = [], 0
        group.append(item)
        size_now += w
    if group:
        groups.append(group)
    names = []
    for g in groups:
        try:
            names.append(client.submit_batch(g, model=plan["model"], size=plan["size"]))
            print(f"submitted {names[-1]} with {len(g)} pictures", flush=True)
        except (CapReached, GeminiError) as exc:
            print("STOP:", exc, flush=True)
            run.phase("5_pictures", "STOPPED", str(exc))
            return 3
    failed = 0
    for n in names:
        res = client.collect_batch(n, wait_s=a.wait, poll_s=30)
        failed += _record(res, plan, out, run, n)
        if not res["done"]:
            print(f"{n} not finished ({res['state']}); collect later with `paint collect {n}`; its items are never re-sent",
                  flush=True)
            failed += 1
    return 0 if not failed else 1


def cmd_collect(a) -> int:
    plan, doc, out, dirs = _load(a)
    run = Run.open(a.run)
    client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
    res = client.collect_batch(a.batch_name, wait_s=a.wait)
    failed = _record(res, plan, out, run, a.batch_name)
    print(res["state"], len(res["items"]), "pictures")
    return 0 if res["done"] and not failed else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.paint", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("plan")
    q.add_argument("script")
    q.add_argument("--out", required=True)
    q.add_argument("--id", required=True)
    q.add_argument("--provider", required=True, choices=sorted(P.PROVIDERS), help="no default: the creator chooses")
    q.add_argument("--model")
    q.add_argument("--size")
    q.add_argument("--batch", action="store_true", help="Gemini half-price batch tier (answers in minutes to hours)")
    q.add_argument("--run", help="the run ledger, to skip pictures already painted from the same prompt")
    q.add_argument("--only")
    q.add_argument("--first", action="store_true", help="one picture only (OR-01: the test before the batch)")
    q.add_argument("--limit", type=int)
    q.add_argument("--purpose")
    q.add_argument("--reusable", action="store_true", help="channel assets reused across episodes (Gemini allowed)")
    q = sub.add_parser("approve")
    q.add_argument("plan")
    q.add_argument("--run", required=True)
    q.add_argument("--by", required=True)
    q.add_argument("--ref", required=True, help="the creator's message that says yes (thread message id, or date and words)")
    for name in ("run", "collect"):
        q = sub.add_parser(name)
        if name == "collect":
            q.add_argument("batch_name")
        q.add_argument("plan")
        q.add_argument("script")
        q.add_argument("--run", required=True)
        q.add_argument("--out", required=True)
        q.add_argument("--refs", action="append", default=[])
        q.add_argument("--workers", type=int, default=4, help="pictures painted at the same time (Gemini takes 1-2 min each)")
        q.add_argument("--wait", type=float, default=1500.0, help="seconds to wait for a batch before leaving it for collect")
    a = ap.parse_args(argv)
    if a.cmd == "plan" and a.provider == "gemini" and not (a.model and a.size):
        ap.error("--provider gemini needs --model and --size (prices: imagegen/gemini.py)")
    return {"plan": cmd_plan, "approve": cmd_approve, "run": cmd_run, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
