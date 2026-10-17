"""Paint an episode's pictures with Gemini from reference pictures (D-44: creator's exception for Episode 1), safely.

    python -m explainer_engine.production.paint <script.json> --run jobs/<run>/run.json --out <pictures dir> [--only id,id] [--estimate]
                                                [--limit N] [--first]

Every picture is one reference-edit request: the compiled ``pod_job`` prompt plus its reference pictures (the library's files).
The price is reserved in the run ledger before the call (refused past 80 % of the cap), the PNG is written as soon as it
arrives and recorded as an item, so a stop, a cap or a crash loses nothing and a re-run skips what exists (OR-02, OR-03). A
failed picture counts a failure; the third failure stops that picture, never the whole batch. ``--first`` paints one picture
only (the phase-3 test).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.imagegen.gemini import GeminiClient, GeminiError, estimate
from explainer_engine.production import compile as C
from explainer_engine.production import script as S

MODEL, SIZE = "gemini-nano-banana-2.1", "2K"


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
    _, pod = C.jobs(doc)
    return pod["pictures"]


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
    ap.add_argument("--workers", type=int, default=4, help="pictures painted at the same time (Gemini takes 1-2 min each)")
    ap.add_argument("--batch", action="store_true", help="half-price batch tier (answers in minutes to hours)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--size", default=SIZE)
    ap.add_argument("--wait", type=float, default=1500.0, help="seconds to wait for a batch before leaving it for --collect")
    ap.add_argument("--collect", help="collect an earlier batch by name instead of submitting")
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
    model, size = a.model, a.size
    if a.batch:
        from explainer_engine.imagegen.gemini import BATCH_PRICES, REFERENCE_USD
        cost = sum(BATCH_PRICES[model][size] + len(j["refs"]) * REFERENCE_USD for j in todo)
    else:
        cost = sum(estimate(model, size, 1, len(j["refs"])) for j in todo)
    print(f"{len(todo)} pictures to paint, estimate ${cost:.3f}; spent so far ${run.spent('gemini_usd'):.3f} of cap "
          f"{run.data['caps'].get('gemini_usd')} (stop at 80 %)")
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
    from explainer_engine.production.editorial_gate import check as check_editorial
    review_path = path.with_name("editorial_review.json")
    editorial_findings = check_editorial(path, review_path)
    for item in editorial_findings:
        print(f"{item['severity']:6} {item['rule']:6} {item['where']}: {item['detail']}")
    if editorial_findings:
        print("EDITORIAL GATE BLOCKED: paid image generation requires a passing source/claim contract and a current independent review.")
        return 2
    if a.batch:
        return run_batch(a, todo, doc, dirs, out, run, model, size)
    client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
    stats = {"painted": 0, "failed": 0, "stop": None}

    def one(j: dict) -> None:
        key = j["id"]
        if stats["stop"] or len(run.data["failures"].get(key, [])) >= 3:
            return
        prompt = j["prompt"] + C.POD_SUFFIX
        try:
            refs = [ref_bytes(dirs, doc, r.removesuffix(".png")) for r in j["refs"]]
            p = client.generate(key, prompt, model=model, size=size, refs=refs)
            (out / f"{key}.png").write_bytes(Path(p).read_bytes())
            run.done("pictures", key, file=f"{key}.png", usd=estimate(model, size, 1, len(refs)))
            stats["painted"] += 1
            print("painted", key, f"${run.spent('gemini_usd'):.3f}", flush=True)
        except CapReached as exc:
            stats["stop"] = str(exc)
            print("STOP:", exc, flush=True)
        except (GeminiError, FileNotFoundError) as exc:
            stats["failed"] += 1
            more = run.fail(key, str(exc))
            print("failed", key, "(will retry)" if more else "(stopped after 3)", str(exc)[:120], flush=True)

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        list(pool.map(one, todo))
    if stats["stop"]:
        run.phase("5_pictures", "STOPPED", stats["stop"])
        return 3
    painted, failed = stats["painted"], stats["failed"]
    print(f"painted {painted}, failed {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
