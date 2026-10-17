"""Episode rulebook command line (docs/EPISODE_STANDARDS.md).

    python -m explainer_engine.standards check  <episode_rules.json> [--at CHECKPOINT]
    python -m explainer_engine.standards gate   <episode_rules.json> --at CHECKPOINT [--script production_script.json]
    python -m explainer_engine.standards stamp  <episode_rules.json> --at CHECKPOINT --by NAME --scope "what was re-checked"
                                                [--script production_script.json]
    python -m explainer_engine.standards brief  <episode_rules.json> --role image
    python -m explainer_engine.standards render <episode_rules.json> [--out episode_rules.md]
    python -m explainer_engine.standards baseline

CHECKPOINT is provisional, final, script_lock, paid_assets or final_qa. ``--script`` defaults to the production_script.json next
to the rulebook. Exit code 1 on any FAIL. Free: it reads files only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from explainer_engine.standards import rulebook as R

ROOT = Path(__file__).resolve().parents[2]


def _print(found: list[dict]) -> int:
    for f in found:
        print(f"{f['severity']:6} {f['rule']:6} {f['check']:24} {str(f['where'])[:24]:24} {f['detail']}")
    print(R.summary(found), file=sys.stderr)
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.standards", description=__doc__.split("\n")[0])
    p.add_argument("cmd", choices=("check", "gate", "stamp", "brief", "render", "baseline"))
    p.add_argument("rules", nargs="?")
    p.add_argument("--at", default="provisional", choices=R.CHECKPOINTS)
    p.add_argument("--script")
    p.add_argument("--role", choices=R.ROLES)
    p.add_argument("--by", default="episode-standards-director")
    p.add_argument("--scope")
    p.add_argument("--out")
    a = p.parse_args(argv)
    if a.cmd == "baseline":
        for b in R.baseline()["sources"]:
            print(f"{b['id']} {b['kind']:16} {b['checked']} {b['verified_in']:5} {b['url']}")
        return 0
    if not a.rules:
        p.error("the rulebook path is required")
    path = Path(a.rules)
    script = Path(a.script) if a.script else path.with_name("production_script.json")
    prev = R.previous_rulebooks(ROOT, exclude=path)
    if a.cmd == "check":
        return _print(R.check(R.load(path), a.at, previous=prev))
    if a.cmd == "gate":
        return _print(R.gate(path, a.at, script, previous=prev))
    if a.cmd == "stamp":
        if not a.scope:
            p.error("--scope says which rules were re-checked and why")
        print(json.dumps(R.stamp(path, a.at, by=a.by, scope=a.scope, script=script, previous=prev), indent=1))
        return 0
    if a.cmd == "brief":
        if not a.role:
            p.error("--role is required")
        sys.stdout.write(R.brief(R.load(path), a.role))
        return 0
    text = R.render(R.load(path))
    if a.out:
        from explainer_engine.core.store import write_text_atomic
        write_text_atomic(Path(a.out), text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
