"""Paint an episode's pictures with Gemini on the batch tier (D-46: every picture, half price), safely.

    python -m explainer_engine.production.paint <script.json> --run jobs/<run>/run.json --out <pictures dir> [--only id,id] [--estimate]
                                                [--limit N] [--first] [--tier draft|standard|premium] [--collect NAME]

Each picture's tier (``draft``, ``standard``, ``premium``; ``imagegen/routing.py``) picks the model and size; ``--tier`` paints
the selection on one tier (a draft pass). The standard tier (synchronous calls) is never used (D-46).

Every picture is one reference-edit request: the compiled ``pod_job`` prompt plus its reference pictures (the library's files).
The price is reserved in the run ledger before the call (refused past 80 % of the cap), the PNG is written as soon as it
arrives and recorded as an item, so a stop, a cap or a crash loses nothing and a re-run skips what exists (OR-02, OR-03). A
failed picture counts a failure; the third failure stops that picture, never the whole batch. ``--first`` paints one picture
only (the phase-3 test). Before any paid call the episode rulebook's ``paid_assets`` checkpoint must pass (OR-11, D-45);
``--legacy-no-rulebook`` exists only for episodes made before it.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.imagegen import routing
from explainer_engine.imagegen.gemini import GeminiClient, GeminiError
from explainer_engine.production import compile as C
from explainer_engine.production import script as S



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


def run_batch(a, todo, doc, dirs, out, run, model, size) -> int:
    """Half-price tier: submit in groups under the inline size limit, then wait for the answers and record every picture."""
    client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
    names, group, size_now = [], [], 0
    groups = []
    for j in todo:
        try:
            refs = [as_jpeg(ref_bytes(dirs, doc, r.removesuffix(".png"))) for r in j["refs"]]
        except FileNotFoundError as exc:
            print("skip", j["id"], exc)
            continue
        item = {"name": j["id"], "prompt": j["prompt"] + C.POD_SUFFIX, "refs": refs}
        w = sum(len(r) for r in refs) * 4 // 3
        if group and size_now + w > 14_000_000:
            groups.append(group)
            group, size_now = [], 0
        group.append(item)
        size_now += w
    if group:
        groups.append(group)
    for g in groups:
        try:
            names.append(client.submit_batch(g, model=model, size=size))
            print(f"submitted {names[-1]} with {len(g)} pictures", flush=True)
        except (CapReached, GeminiError) as exc:
            print("STOP:", exc, flush=True)
            run.phase("5_pictures", "STOPPED", str(exc))
            return 3
    failed = 0
    for n in names:
        res = client.collect_batch(n, wait_s=a.wait, poll_s=30)
        for item, val in res["items"].items():
            if isinstance(val, Path):
                (out / f"{item}.png").write_bytes(val.read_bytes())
                run.done("pictures", item, file=f"{item}.png", batch=n)
                print("painted", item, flush=True)
            else:
                failed += 1
                run.fail(item, str(val))
                print("failed", item, str(val)[:100], flush=True)
        if not res["done"]:
            print(f"{n} not finished ({res['state']}); collect later with --collect {n}", flush=True)
            failed += 1
    return 0 if not failed else 1


def jobs_of(doc: dict) -> list[dict]:
    """Every picture still to paint: reference edits (``pod_ref``, painted by Gemini since D-44) and text pictures (``gemini``)."""
    gemini, pod = C.jobs(doc)
    return pod["pictures"] + [{**g, "refs": [f"{r}.png" for r in g["refs"]]} for g in gemini]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--refs", action="append", default=[])
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--tier", choices=sorted(routing.TIERS), help="paint the selection on this tier (default: each picture's own)")
    ap.add_argument("--batch", action="store_true", help="kept for old command lines: the batch tier is always used (D-46)")
    ap.add_argument("--wait", type=float, default=1500.0, help="seconds to wait for a batch before leaving it for --collect")
    ap.add_argument("--collect", help="collect an earlier batch by name instead of submitting")
    ap.add_argument("--legacy-no-rulebook", action="store_true", help="episodes made before D-45 (Episode 1) only")
    a = ap.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dirs = [Path(x) for x in a.refs] + [path.parent / d for d in doc.get("picture_dirs", [])] + [out]
    run = Run.open(a.run)
    todo = [j for j in jobs_of(doc) if not (out / f"{j['id']}.png").exists()]
    if a.only:
        want = set(a.only.split(","))
        todo = [j for j in todo if j["id"] in want]
    if a.first:
        todo = todo[:1]
    if a.limit:
        todo = todo[:a.limit]
    for j in todo:
        j["tier"] = a.tier or routing.tier_of(j)
    cost = sum(routing.batch_cost(j["tier"], len(j["refs"])) for j in todo)
    print(f"{len(todo)} pictures to paint on the batch tier, estimate ${cost:.3f}; spent so far "
          f"${run.spent('gemini_usd'):.3f} of cap {run.data['caps'].get('gemini_usd')} (stop at 80 %)")
    pending = C.canva_pending(doc)
    if pending:
        print(f"{len(pending)} filler pictures are made by hand in Canva, not painted here (PV-36): {', '.join(pending)}")
    if a.estimate:
        return 0
    if a.collect:
        client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
        res = client.collect_batch(a.collect, wait_s=a.wait)
        for item, val in res["items"].items():
            if isinstance(val, Path):
                (out / f"{item}.png").write_bytes(val.read_bytes())
                run.done("pictures", item, file=f"{item}.png", batch=a.collect)
        print(res["state"], len(res["items"]), "pictures")
        return 0 if res["done"] else 1
    if not a.legacy_no_rulebook:  # OR-11: no paid picture before the rulebook's paid_assets checkpoint passes
        from explainer_engine.standards import rulebook as R
        rules_path = path.with_name("episode_rules.json")
        if not rules_path.exists():
            print(f"STOP: no {rules_path.name} next to the script (OR-10); --legacy-no-rulebook only for episodes made "
                  "before D-45")
            return 4
        fails = [f for f in R.gate(rules_path, "paid_assets", path) if f["severity"] == "FAIL"]
        if fails:
            for f in fails:
                print("FAIL", f["rule"], f["where"], f["detail"])
            print("STOP: the rulebook's paid_assets checkpoint does not pass (OR-11)")
            return 4
    code = 0
    for tier in routing.TIERS:  # one batch run per tier: a batch has one model and size
        group = [j for j in todo if j["tier"] == tier]
        if group:
            model, size = routing.route(tier)
            code = max(code, run_batch(a, group, doc, dirs, out, run, model, size))
            if code == 3:
                break
    return code

if __name__ == "__main__":
    sys.exit(main())
