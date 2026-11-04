# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/standards/__main__.py`
# Target Module : explainer_engine/standards/__main__.py
# Target Classes/Symbols : def _print(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
