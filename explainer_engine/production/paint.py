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
    cost = sum(estimate(MODEL, SIZE, 1, len(j["refs"])) for j in todo)
    print(f"{len(todo)} pictures to paint, estimate ${cost:.3f}; spent so far ${run.spent('gemini_usd'):.3f} of cap "
          f"{run.data['caps'].get('gemini_usd')} (stop at 80 %)")
    if a.estimate:
        return 0
    client = GeminiClient(out / "_gemini", cap_usd=1e9, run=run)
    stats = {"painted": 0, "failed": 0, "stop": None}

    def one(j: dict) -> None:
        key = j["id"]
        if stats["stop"] or len(run.data["failures"].get(key, [])) >= 3:
            return
        prompt = j["prompt"] + C.POD_SUFFIX
        try:
            refs = [ref_bytes(dirs, doc, r.removesuffix(".png")) for r in j["refs"]]
            p = client.generate(key, prompt, model=MODEL, size=SIZE, refs=refs)
            (out / f"{key}.png").write_bytes(Path(p).read_bytes())
            run.done("pictures", key, file=f"{key}.png", usd=estimate(MODEL, SIZE, 1, len(refs)))
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
