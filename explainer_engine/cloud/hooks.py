"""Claude Code session hooks for money (D-56): the rules are checked by code at every turn, not remembered.

    session-start  prints what bills on the RunPod account (stray pods, stopped disks, 24 h billing, balance)
    stop           refuses to end a turn while something bills that nobody approved or guards (exit 2 tells Claude why)
    pre-bash       refuses pod starts that bypass the guarded manager (TMR's rp.py create/start, raw POST /pods on REST v1 or
                   v2, a v2 ``action`` start/restart, the GraphQL deploy mutations, the Python SDK's create_pod/resume_pod)
A broken check (no key, no network, an API error) never blocks a turn by itself; it blocks only while this machine knows of a
live pod it cannot then look at (CR-13): an unguarded pod is the one thing worth stopping a turn for.
"""
from __future__ import annotations

import json
import re
import sys
import time

from explainer_engine.cloud import runpod as R

BYPASS = [re.compile(p) for p in (r"/v[12]/pods/?['\"]?\s*(-X\s*POST|--request\s+POST)",
                                   r"-X\s*POST[^|;&]*(rest|api)\.runpod\.io/v[12]/pods/?(['\"\s]|$)",
                                   r"rest\.runpod\.io/v1/pods/\w+/start",
                                   r"(?s)(?=.*/v2/pods/\w+/action)(?=.*['\"]action['\"]\s*:\s*['\"](start|restart)['\"])",
                                   r"podFindAndDeployOnDemand|podRentInterruptible|podResume", r"runpod\.(create_pod|resume_pod)\(",
                                   r"runpodctl\s+(create|start)\b", r"(-X\s*PATCH|--request\s+PATCH)[^|;&]*/v2/pods/",
                                   r"/v2/pods/\w+['\"]?\s*(-X\s*PATCH|--request\s+PATCH)")]  # PATCH resets the pod: data outside /workspace is lost


RP_SAFE = ("sweep", "status", "list", "check", "logs", "cost", "stop")  # TMR's rp.py: read-only and stopping commands only (CR-13)
# rp.py is a RUN unless the command segment starts with a program that only reads or edits files: any launcher (timeout, nice, env,
# FOO=1, watch, stdbuf, uv run, bash -c ...) is covered without being listed. Only a token that ends at a space or the end of the
# segment counts as the program (``open('cloud/rp.py')`` does not).
RP_READERS = ("cat", "grep", "egrep", "fgrep", "rg", "sed", "awk", "less", "more", "head", "tail", "git", "diff", "wc", "cp", "mv", "ls",
              "stat", "file", "nl", "bat", "vim", "vi", "nano", "emacs", "code", "echo", "printf", "tee", "find", "ruff", "black")
RP_TOKEN = re.compile(r"(?<![\w])rp\.py(?=\s|$)(?:\s+['\"]?(?P<sub>[\w-]+))?")
RP_SEGMENT = re.compile(r"&&|\|\||[;&|\n(`]")  # backticks open a nested command: echo `./rp.py create`
RP_EXEC = re.compile(r"\s-(?:exec|execdir|ok|okdir)\b")  # find ... -exec ./rp.py create {} ; : a reader that launches another program
RP_MODULE = re.compile(r"\bpython[\d.]*(?:\.exe)?\s+(?:-\S+\s+)*-m\s+(?:\w+\.)*rp\b(?:\s+(?P<sub>[\w-]+))?")
RP_IMPORT = re.compile(r"\b(?:import\s+(?:cloud\.)?rp\b|from\s+(?:cloud\.rp|cloud\s+import\s+rp)\b|runpy\S*\s*.*\brp\b)")


def _tmr_rp(cmd):
    """True when the command runs TMR's rp.py with anything but a read-only or stopping sub-command, or imports it."""
    for seg in RP_SEGMENT.split(cmd):
        words = re.sub(r"^\s*(?:\w+=\S*\s+)*", "", seg).split()
        if words and words[0].rsplit("/", 1)[-1] in RP_READERS and not RP_EXEC.search(seg):
            continue
        for m in RP_TOKEN.finditer(seg):
            if (m.group("sub") or "") not in RP_SAFE:
                return True
    for m in RP_MODULE.finditer(cmd):
        if (m.group("sub") or "") not in RP_SAFE:
            return True
    return "python" in cmd and bool(RP_IMPORT.search(cmd))


def _stdin():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def known_live(now=None):
    """The pods this machine started and has not seen closed, whose approved lifetime is not over: (pod id, name) pairs."""
    now = time.time() if now is None else now
    out = []
    d = R.RP / "sessions"
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            s = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not s.get("closed") and (s.get("until") or 0) > now and s.get("pod"):
            out.append((s["pod"], s.get("name", "")))
    return out


def _check():
    """The account check, or None when it cannot run (no key); an unreachable API comes back as a result with ``unreadable``."""
    try:
        R.api_key()
    except SystemExit:
        return None
    try:
        return R.check(R.Api(retries=1, timeout=20))
    except (R.RunPodError, OSError) as e:
        return {"problems": [], "info": [f"RunPod not reachable: {str(e)[:80]}"], "unreadable": True}


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
    if not res or res.get("unreadable"):
        live = known_live()
        if live:  # CR-13: fail closed with a pod we know bills
            print("Cannot look at RunPod now (" + ("no key" if res is None else res["info"][0]) + f") and {len(live)} pod(s) started "
                  "from this machine may still be live: " + ", ".join(f"{p} {n}" for p, n in live)
                  + ". Stop them (`python -m explainer_engine.cloud.runpod stop <pod>`) or restore the key/network before ending the turn.",
                  file=sys.stderr)
            return 2
        return 0
    if not res["problems"]:
        return 0
    print("Something on RunPod is billing without approval or guard (D-56):\n  " + "\n  ".join(res["problems"])
          + "\nStop it (`python -m explainer_engine.cloud.runpod sweep`), or ask the creator to delete or keep the disk,"
            " and report the cost.", file=sys.stderr)
    return 2


def pre_bash(event: dict) -> int:
    cmd = (event.get("tool_input") or {}).get("command", "")
    if any(p.search(cmd) for p in BYPASS) or _tmr_rp(cmd):
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
