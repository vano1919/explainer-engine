"""The P2 result table, free and offline: the owner's PASS/FAIL against each model's per-defect probabilities, and the two models against each other.

    python -m explainer_engine.training.pods.judge.compare <results.json> <labels.json> [--flag-at 0.5]

``labels.json`` = ``{"<frame id>": "PASS" | "FAIL"}`` (the owner's blind scoring). Nothing here is a threshold decision: it prints raw
counts at the stated flag line and the lowest/highest probability seen on each side, so the line can be refitted by looking."""
from __future__ import annotations

import argparse
import json
import sys


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def table(results: dict, labels: dict, flag_at: float = 0.5) -> dict:
    models = results["models"]
    frames = [f for f in (next(iter(models.values()))["frames"] if models else {}) if f in labels]
    out = {"n_frames": len(frames), "flag_at": flag_at, "owner_fail": sum(labels[f] == "FAIL" for f in frames), "models": {}, "agreement": {}}
    for k, m in models.items():
        rows = {}
        for d in results["defects"]:
            fl = {f: m["frames"][f]["defects"][d]["probability"] >= flag_at for f in frames if f in m["frames"]}
            ps = {f: m["frames"][f]["defects"][d]["probability"] for f in fl}
            on_fail = [f for f in fl if labels[f] == "FAIL"]
            on_pass = [f for f in fl if labels[f] == "PASS"]
            rows[d] = {"flagged_on_owner_FAIL": f"{sum(fl[f] for f in on_fail)}/{len(on_fail)}",
                       "flagged_on_owner_PASS": f"{sum(fl[f] for f in on_pass)}/{len(on_pass)}",
                       "p_range_on_FAIL": [min((ps[f] for f in on_fail), default=None), max((ps[f] for f in on_fail), default=None)],
                       "p_range_on_PASS": [min((ps[f] for f in on_pass), default=None), max((ps[f] for f in on_pass), default=None)]}
        verd = {f: m["frames"][f]["verdict"] for f in frames if f in m["frames"]}
        out["models"][k] = {"defects": rows,
                            "verdict_vs_owner": {"owner_FAIL": {v: sum(1 for f, x in verd.items() if x == v and labels[f] == "FAIL") for v in ("PASS", "REVIEW", "RETRY")},
                                                 "owner_PASS": {v: sum(1 for f, x in verd.items() if x == v and labels[f] == "PASS") for v in ("PASS", "REVIEW", "RETRY")}},
                            "state": m.get("state"), "vram_peak": m.get("vram_peak"), "vram_after_load": m.get("vram_after_load")}
    names = list(models)
    if len(names) == 2:
        a, b = (models[n]["frames"] for n in names)
        for d in results["defects"]:
            fa = [a[f]["defects"][d]["probability"] >= flag_at for f in frames if f in a and f in b]
            fb = [b[f]["defects"][d]["probability"] >= flag_at for f in frames if f in a and f in b]
            out["agreement"][d] = {"same_flag": f"{sum(x == y for x, y in zip(fa, fb))}/{len(fa)}", "kappa": kappa(fa, fb)}
    return out


def markdown(t: dict) -> str:
    L = [f"Frames {t['n_frames']} (owner FAIL {t['owner_fail']}); flag line p >= {t['flag_at']} (placeholder)", ""]
    for k, m in t["models"].items():
        L += [f"### {k}  (state {m['state']}, VRAM after load {m['vram_after_load']}, peak {m['vram_peak']})",
              "| defect | flagged on owner FAIL | flagged on owner PASS | p range FAIL | p range PASS |", "|---|---|---|---|---|"]
        for d, r in m["defects"].items():
            L.append(f"| {d} | {r['flagged_on_owner_FAIL']} | {r['flagged_on_owner_PASS']} | {r['p_range_on_FAIL']} | {r['p_range_on_PASS']} |")
        L += ["", f"verdict vs owner: {json.dumps(m['verdict_vs_owner'])}", ""]
    if t["agreement"]:
        L += ["### the two models against each other", "| defect | same flag | kappa |", "|---|---|---|"]
        L += [f"| {d} | {a['same_flag']} | {a['kappa']} |" for d, a in t["agreement"].items()]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("labels")
    ap.add_argument("--flag-at", type=float, default=0.5)
    a = ap.parse_args(argv)
    print(markdown(table(json.load(open(a.results, encoding="utf-8")), json.load(open(a.labels, encoding="utf-8")), a.flag_at)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
