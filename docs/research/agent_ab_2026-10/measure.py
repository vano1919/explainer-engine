"""P0c measurement: independent gate counts per stage snapshot of one arm (A/B of D-79 vs D-81, free).

    PYTHONPATH=. python3 docs/research/agent_ab_2026-10/measure.py docs/research/agent_ab_2026-10/arm_A > docs/research/agent_ab_2026-10/metrics_arm_A.json

Run from the repo root. Everything is computed by the repo's own validators, not by the arm that wrote the file.
"""
from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
from pathlib import Path

from explainer_engine.scripting import stage_guard, story_lint

STAGES = [("s01_architect", "architect"), ("s02_writer", "writer"), ("s02b_beats", "beats"), ("s03_performer", "performer"),
          ("s03r_writer", "writer_repair"), ("s04_editor", "editor"), ("s04r_architect", "architect_repair"), ("s05_caster", "caster"), ("s06_shorts", "shorts")]
CLAIM = re.compile(r"\b[CI]\d{2}\b")


def validate(path: Path) -> dict:
    p = subprocess.run([sys.executable, "-m", "explainer_engine.production", "validate", str(path)], capture_output=True, text=True)
    rules = collections.Counter()
    for ln in p.stdout.splitlines():
        m = re.match(r"(FAIL|REVIEW)\s+(PV-\d+)\s+(\S+)", ln)
        if m:
            rules[f"{m.group(1)} {m.group(2)} {m.group(3)}"] += 1
    tot = re.search(r"script: (\d+) FAIL, (\d+) REVIEW", p.stdout + p.stderr)
    return {"fail": int(tot.group(1)) if tot else None, "review": int(tot.group(2)) if tot else None, "by_rule": dict(rules)}


def shape(doc: dict) -> dict:
    segs = doc.get("segments", [])
    lines = [ln for s in segs for ln in s.get("lines", [])]
    words = sum(len(ln.get("text", "").split()) for ln in lines)
    cited = {c for ln in lines for c in (ln.get("claims") or [])}
    return {"segments": len(segs), "lines": len(lines), "words": words, "claims_cited": len(cited),
            "shots": sum(len(s.get("shots", [])) for s in segs), "shorts": len(doc.get("shorts", []))}


def main(arm: str) -> dict:
    arm_dir, out, prev = Path(arm), {}, None
    for stem, stage in STAGES:
        f = arm_dir / f"{stem}.json"
        if not f.exists():
            if stem != "s04r_architect":  # the repair round exists only when the orchestrator routed a defect back
                out[stem] = {"missing": True}
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        lint = story_lint.lint(doc)
        row = {"shape": shape(doc), "story_lint": {"fail": sum(x["severity"] == "FAIL" for x in lint),
                                                   "review": sum(x["severity"] != "FAIL" for x in lint),
                                                   "rules": dict(collections.Counter(f'{x["severity"]} {x["rule"]}' for x in lint))},
               "validate": validate(f)}
        if prev is not None and stage != "architect":
            row["stage_guard_violations_vs_previous"] = stage_guard.violations({"architect_repair": "architect", "writer_repair": "writer"}.get(stage, stage), prev, doc)
        out[stem], prev = row, doc
    final = arm_dir / "production_script.json"
    if final.exists():
        doc = json.loads(final.read_text(encoding="utf-8"))
        out["final"] = {"shape": shape(doc), "validate": validate(final),
                        "story_lint_fail": sum(x["severity"] == "FAIL" for x in story_lint.lint(doc))}
        if prev is not None:
            out["final"]["same_as_last_snapshot"] = doc == prev
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=1, ensure_ascii=False))
