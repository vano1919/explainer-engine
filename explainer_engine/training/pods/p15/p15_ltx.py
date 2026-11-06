"""The pilot pod's LTX part (PILOT_1MIN_PLAN.md v3): ONE job of ``p15.json`` ``ltx_jobs`` (plain LTX-2.5 distilled image-to-video
from the Qwen first frame, no LoRA, no control video) through the step-3 pod's runner (``p14/p14_ltx.run``: pinned weights, inputs
read from the pod's own disk first, ``ltx/<job>.mp4`` + sidecar, the speeds file). One process per clip, so a hung clip is killed
at its schedule max without taking the next one.

    python3 -m explainer_engine.training.pods.p15.p15_ltx --job <id>        # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
    python3 -m explainer_engine.training.pods.p15.p15_ltx --prefetch        # the LTX-2.5 weights, checked by sha256
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from explainer_engine.training.pods.p14 import p14_ltx as X

HERE = Path(__file__).resolve().parent


def load_cfg() -> dict:
    return json.loads((HERE / "p15.json").read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pilot pod: one LTX clip")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--job")
    g.add_argument("--prefetch", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_cfg()
    ltx = cfg["ltx"]
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    log = X.Log(out)
    if a.prefetch:
        bad = X.download_base(ltx, "ltx25", log)
        log.ev("prefetch_done", bad=bad)
        return 1 if bad else 0
    jobs = [j for j in cfg["ltx_jobs"] if j["id"] == a.job]
    if len(jobs) != 1:
        raise SystemExit(f"no LTX job {a.job!r} in p15.json")
    rows = X.run(ltx, {"jobs": jobs}, out, float(os.environ["EE_DEADLINE"]), log, speeds_name=f"speeds_{a.job}.json")
    return 0 if rows and rows[-1]["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
