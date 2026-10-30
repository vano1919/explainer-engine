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
