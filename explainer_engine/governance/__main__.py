# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M8A: Governance CLI Entrypoint (`status [--check]` Support for `BATCH-M8A` Verification)
# Target Module : explainer_engine/governance/__main__.py
# Target Classes/Symbols : def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Update `build_parser()` and `cmd_status()` in `explainer_engine/governance/__main__.py`:
#    - Add optional flag `--check` (`parser_status.add_argument("--check", action="store_true", help="Exit non-zero if any required governance artifact, hash pin, or gate invariant is invalid")`) to the `status` subcommand so that `python -m explainer_engine.governance status --check` (the exact command specified in `MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md` `BATCH-M8A`) works without raising `unrecognized arguments: --check`!
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/governance/__main__.py:72` defines `sub.add_parser("status")` with ZERO optional arguments. Running the roadmap's `BATCH-M8A` command `python -m explainer_engine.governance status --check` currently fails with `error: unrecognized arguments: --check`.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Synchronizes the actual CLI parser with the `BATCH-M8A` verification command in the integration roadmap and enables automated CI/pre-flight exit-code checking.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] RunPod Pods Pricing & Per-Second Billing
#        URL: https://docs.runpod.io/pods/pricing
#        Rationale: Details per-second GPU billing for RTX PRO 6000 Blackwell ($1.89/hr Secure Cloud) and H200 SXM ($3.59/hr), requiring hard budget caps and empirical runtime measurement.
#    [2] RunPod Account Billing & Storage Costs
#        URL: https://docs.runpod.io/accounts-billing/billing
#        Rationale: Documents that stopped pods still incur container/volume storage charges until terminated (`runpodctl remove pod`), grounding D-78 / BP-148 auto-teardown.
#    [3] PyTorch torch.compile Tutorial & Cold-Start Behavior
#        URL: https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html
#        Rationale: Explains why compilation overhead is avoided (`compile_mode: none` for <=2 segments in cloud_pins.json) and why cold-start must be amortized.
#    [4] GitHub Docs — About Protected Branches
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
#        Rationale: Specifies required status checks (`quality`), PR-only merge enforcement, and branch protection rules required by GATE-EXT-MAIN-PROTECT.
#    [5] GitHub Docs — Managing Rulesets for a Repository
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
#        Rationale: Specifies ruleset protections preventing force-pushes, accidental branch deletion, and unreviewed merges into main.
#    [6] Python 3.12 What's New — PEP 701 Syntactic Formalization of f-strings
#        URL: https://docs.python.org/3/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
#        Rationale: Explains why nested double-quotes inside an f-string expression (`blind_check.py:36`) raise SyntaxError on Python 3.11 even though Python 3.12+ permits them.
# =============================================================================

"""CLI: ok | start | attempt | status | log | check | backup | backup-if-over."""
from __future__ import annotations

import argparse
import json
import sys
import time

from explainer_engine.core.errors import NeedsReview
from explainer_engine.governance import load, records, status, usage
from explainer_engine.core.store import write_json_atomic
from explainer_engine.governance import root_dir


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.governance")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("ok", help="record the creator's own word (action: model_switch | effort_override | protected_config | channel_voice | generator_admit)")
    o.add_argument("action", choices=records.ACTIONS)
    o.add_argument("target", help="the model or the one file the word covers (* only for model_switch and effort_override)")
    o.add_argument("message_id")
    o.add_argument("quote")
    s = sub.add_parser("start", help="name the active phase (the Stop hook checks it when it is review/done)")
    s.add_argument("phase")
    a = sub.add_parser("attempt", help="count an attempt at a phase (OR-04: 2 at the assigned level, the 3rd escalated, then stop)")
    a.add_argument("phase")
    a.add_argument("--escalated", action="store_true")
    a.add_argument("--cause", default="")
    st = sub.add_parser("status", help="check or write docs/blueprint/STATUS.md")
    st.add_argument("--write", action="store_true")
    lg = sub.add_parser("log", help="append the phase's routing_log line")
    for k in ("phase", "level", "model", "effort", "result"):
        lg.add_argument(k)
    lg.add_argument("--thread", default="")
    lg.add_argument("--note", default="")
    sub.add_parser("check", help="all validators (config, phases, cards, log, STATUS)")
    b = sub.add_parser("backup")
    b.add_argument("--reason", default="manual")
    b.add_argument("--no-push", action="store_true")
    sub.add_parser("backup-if-over")
    args = p.parse_args(argv)
    root = root_dir()
    if args.cmd == "ok":
        print(json.dumps(records.add(args.action, args.target, args.message_id, args.quote), ensure_ascii=False))
    elif args.cmd == "start":
        write_json_atomic(root / "jobs" / "active_phase.json", {"phase": args.phase, "at": time.time()})
    elif args.cmd == "attempt":
        from explainer_engine.core.ledger import Attempts
        try:
            esc = load(root)["escalation"]
            att = Attempts(root / "jobs" / args.phase / "attempts.json", esc["attempts_at_level"], esc["escalated_attempts"])
            print(json.dumps(att.add(args.cause, escalated=args.escalated)))
        except NeedsReview as e:
            print(e, file=sys.stderr)
            return 2
    elif args.cmd == "status":
        if args.write:
            print(status.write_status())
        else:
            errs = status.check_all()
            print("\n".join(errs) or "ok")
            return 1 if errs else 0
    elif args.cmd == "log":
        status.append_log({"kind": "phase", "date": time.strftime("%Y-%m-%d", time.gmtime()), "phase": args.phase, "thread": args.thread,
                           "level": args.level, "model": args.model, "effort": args.effort, "result": args.result, "note": args.note})
    elif args.cmd == "check":
        load()
        errs = status.check_all()
        print("\n".join(errs) or "ok")
        return 1 if errs else 0
    elif args.cmd == "backup":
        print(json.dumps(usage.backup(args.reason, push=not args.no_push), ensure_ascii=False))
    elif args.cmd == "backup-if-over":
        print(json.dumps(usage.backup_if_over(usage.current(), push=True), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
