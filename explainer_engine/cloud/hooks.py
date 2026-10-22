"""Claude Code session hooks for money (D-56): the rules are checked by code at every turn, not remembered.

    session-start  prints what bills on the RunPod account (stray pods, stopped disks, 24 h billing, balance)
    stop           refuses to end a turn while something bills that nobody approved or guards (exit 2 tells Claude why)
    pre-bash       refuses pod starts that bypass the guarded manager (TMR's rp.py create/start, raw POST /pods on REST v1 or
                   v2, a v2 ``action`` start/restart, the GraphQL deploy mutations, the Python SDK's create_pod/resume_pod)
No key or no network: the hooks say so and never block (a broken check must not lock the session).
"""
from __future__ import annotations

import json
import re
import sys

from explainer_engine.cloud import runpod as R

BYPASS = [re.compile(p) for p in (r"rp\.py\s+(create|start|adopt)\b", r"/v[12]/pods/?['\"]?\s*(-X\s*POST|--request\s+POST)",
                                   r"-X\s*POST[^|;&]*(rest|api)\.runpod\.io/v[12]/pods/?(['\"\s]|$)",
                                   r"rest\.runpod\.io/v1/pods/\w+/start",
                                   r"(?s)(?=.*/v2/pods/\w+/action)(?=.*['\"]action['\"]\s*:\s*['\"](start|restart)['\"])",
                                   r"podFindAndDeployOnDemand|podRentInterruptible|podResume", r"runpod\.(create_pod|resume_pod)\(")]


def _stdin():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def _check():
    try:
        R.api_key()
    except SystemExit:
        return None
    try:
        return R.check(R.Api(retries=1, timeout=20))
    except (R.RunPodError, OSError) as e:
        return {"problems": [], "info": [f"RunPod not reachable: {str(e)[:80]}"]}


def session_start() -> int:
    res = _check()
    if res is None:
        return 0
    lines = [f"RunPod check (D-56): {len(res['problems'])} problem(s)"] + ["PROBLEM " + p for p in res["problems"]] + res["info"]
    if res["problems"]:
        lines.append("Fix these before other work (stop/delete per the rules) and tell the creator what they cost.")
    print("\n".join(lines))
    return 0


def stop(event: dict) -> int:
    if event.get("stop_hook_active"):
        return 0
    res = _check()
    if not res or not res["problems"]:
        return 0
    print("Something on RunPod is billing without approval or guard (D-56):\n  " + "\n  ".join(res["problems"])
          + "\nStop it (`python -m explainer_engine.cloud.runpod sweep`), or ask the creator to delete or keep the disk,"
            " and report the cost.", file=sys.stderr)
    return 2


def pre_bash(event: dict) -> int:
    cmd = (event.get("tool_input") or {}).get("command", "")
    if any(p.search(cmd) for p in BYPASS):
        print("refused (D-56): pods start only through `python -m explainer_engine.cloud.runpod create|start`, which checks "
              "config/spend_caps.json, the ledger and the account and starts the guard.", file=sys.stderr)
        return 2
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    what = argv[0] if argv else ""
    if what == "session-start":
        return session_start()
    if what == "stop":
        return stop(_stdin())
    if what == "pre-bash":
        return pre_bash(_stdin())
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
