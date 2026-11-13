
"""Claude Code session hooks for money (D-56): the rules are checked by code at every turn, not remembered.

    session-start  prints what bills on the RunPod account (stray pods, stopped disks, 24 h billing, balance)
    stop           refuses to end a turn while something bills that nobody approved or guards (exit 2 tells Claude why)
    pre-bash       refuses pod starts that bypass the guarded manager (TMR's rp.py create/start, raw POST /pods on REST v1 or
                   v2, a v2 ``action`` start/restart, the GraphQL deploy mutations, the Python SDK's create_pod/resume_pod,
                   the retired aivideo/pod launchers and a Python ``rp.create(``/``runpod.create(`` outside the CLI), and
                   Modal launches outside a committed worker (final audit A7, D-131): ``modal deploy`` and ``modal serve``
                   always; ``modal run`` of anything but a committed ``explainer_engine/`` worker; a paid entrypoint without
                   ``EE_MODAL_GO``; the Wan worker's paid rungs without ``EE_MODAL_GO=<card id>:<plan sha256[:12]>``
Modal (v4.3 runs Wan on Modal): session-start lists every Modal app that is not stopped, and stop refuses the first end of a
turn while one is (the turn after may end: a detached run that is being watched is allowed to go on).
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
                                   r"/v2/pods/\w+['\"]?\s*(-X\s*PATCH|--request\s+PATCH)",  # PATCH resets the pod: data outside /workspace is lost
                                   r"python[^|;&\n]*aivideo[/\\.]pod[/\\.]launch(_clips)?\b",  # the retired launchers (CP-01, D-80)
                                   r"python[^|&]*\b(rp|runpod)\.create\(",  # library create outside the CLI (N-01's 2nd net;
#                                    ``;`` and newlines allowed: ``python -c "import ...; rp.create(...)"`` and a heredoc are one program)
                                   r"python[^|&]*\brunpod\b[^|&]*\bcreate\(")]  # the same with a bare imported name or an alias
#                                    (``from ...runpod import create; create(``, ``runpod as R; R.create(``; T5's review of CP-01)


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


MODAL_CMD = re.compile(r"(?:^|[\s;&|(`'\"])(?:\S*?python[\d.]*(?:\.exe)?\s+(?:-\S+\s+)*-m\s+|[^\s;&|(`'\"]*[/\\])?"
                       r"modal(?:\.exe)?\s+(?P<sub>run|deploy|serve|shell|launch)\b"
                       r"(?P<rest>[^\n]*)")
WAN_WORKER = "explainer_engine/training/pods/wan/modal_wan_jobs.py"
LTX_WORKER = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"   # the video route since D-132 (2026-11-12 19:10 UTC)
BAKEOFF = "explainer_engine/training/pods/bakeoff/modal_bakeoff.py"   # the creator's video bake-off, 2026-11-12 15:01 UTC
BAKEOFF_ENTRIES = ("check", "stage", "run")


def bakeoff_go_sha(root=None, plan_name=None) -> str:
    """``modal_bakeoff.go_sha()`` read from the files on disk (the plan's and the worker's bytes; Fable audit A4). The plan is
    the one ``EE_BAKEOFF_PLAN`` names (its file name only, in the bake-off folder; default ``plan_v43.json``), as in
    ``modal_bakeoff.plan_path``."""
    import hashlib
    from pathlib import Path
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    w = root / BAKEOFF
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    plan = w.with_name(Path(str(plan_name or "plan_v43.json")).name)
    return hashlib.sha256((h(plan) + h(w)).encode()).hexdigest()
FREE_ENTRIES = {WAN_WORKER: ("check", "weights"), LTX_WORKER: ("check", "weights")}   # CPU rungs L1/L2: the entrypoint's own ladder gate holds them


HEREDOC = re.compile(r"(?m)^(?P<head>[^\n]*?<<-?\s*(?P<q>['\"]?)(?P<tag>\w+)(?P=q)[^\n]*)\n(?P<body>.*?)^\s*(?P=tag)\s*$", re.S)
SHELLS = ("bash", "sh", "zsh", "dash", "pwsh", "powershell")


def _without_text_heredocs(cmd: str) -> str:
    """A heredoc that only feeds a file or an interpreter's text (``cat > f <<EOF``, ``python3 - <<EOF``) is data, not a
    command; one fed to a shell (``bash <<EOF``) stays and is read like any command."""
    def drop(m):
        head = m.group("head")
        first = re.sub(r"^\s*(?:\w+=\S*\s+)*", "", RP_SEGMENT.split(head)[-1]).split()
        prog = first[0].rsplit("/", 1)[-1] if first else ""
        return m.group(0) if prog in SHELLS else head
    return HEREDOC.sub(drop, cmd)


def modal_refusal(cmd: str, env=None) -> str | None:
    """Why a Bash command that launches Modal is refused, or None (final audit A7)."""
    import os
    env = os.environ if env is None else env
    cmd = _without_text_heredocs(cmd)
    for seg in RP_SEGMENT.split(cmd):
        words = re.sub(r"^\s*(?:\w+=\S*\s+)*", "", seg).split()
        if words and words[0].rsplit("/", 1)[-1] in RP_READERS and not RP_EXEC.search(seg):
            continue
        m = MODAL_CMD.search(seg)
        if not m:
            continue
        if m.group("sub") in ("shell", "launch"):
            return (f"`modal {m.group('sub')}` starts a container outside any plan, cap or ledger: refused (Fable audit A4, "
                    "OR-23)")
        if m.group("sub") in ("deploy", "serve"):
            return (f"`modal {m.group('sub')}` leaves an app up: this project only runs committed workers with `modal run` "
                    "(.claude/rules/cloud-platforms.md section 5, D-131)")
        target = next((t for t in m.group("rest").split() if not t.startswith("-")), "")
        path, _, entry = target.partition("::")
        if not path.startswith("explainer_engine/") or not path.endswith(".py"):
            return (f"`modal run {target}`: only a committed worker under explainer_engine/ runs on Modal (OR-21, D-131)")
        from explainer_engine.episode import retired
        gone = retired.retired_worker(path)
        if gone:
            return f"`modal run {target}`: {gone} is retired everywhere (D-131, the creator 2026-11-12 14:01 UTC)"
        if entry in FREE_ENTRIES.get(path, ()):
            continue
        go = re.search(r"\bEE_MODAL_GO=['\"]?(\S+?)['\"]?(?:\s|$)", cmd)
        go = go.group(1) if go else str(env.get("EE_MODAL_GO") or "")
        if path == BAKEOFF:
            if entry not in BAKEOFF_ENTRIES:
                return (f"`modal run {target}`: the bake-off runs only through its entrypoints {BAKEOFF_ENTRIES}, which hold the "
                        "preflight, the GO and the ledger (Fable audit A4)")
            if not re.match(r"^cmsg_\w+:[0-9a-f]{12}$", go):
                return ("the bake-off bills Modal on every entrypoint (its CPU check and stage-in too): "
                        "EE_MODAL_GO=<the creator's card id>:<go sha[:12]> first (OR-23)")
            pn = re.search(r"\bEE_BAKEOFF_PLAN=['\"]?(\S+?)['\"]?(?:\s|$)", cmd)
            try:
                want = bakeoff_go_sha(plan_name=pn.group(1) if pn else env.get("EE_BAKEOFF_PLAN"))[:12]
            except OSError:
                want = None
            if go.split(":", 1)[1] != want:
                return ("EE_MODAL_GO names another plan or worker than the files on disk: the creator's GO binds the plan's and "
                        "the worker's bytes (modal_bakeoff.go_sha, Fable audit A4)")
        elif path in (WAN_WORKER, LTX_WORKER):
            if not re.match(r"^cmsg_\w+:[0-9a-f]{12}$", go):
                return (f"the {'Wan' if path == WAN_WORKER else 'LTX'} worker's paid rungs need EE_MODAL_GO=<the creator's card id>:<the plan's sha256[:12]> "
                        "(OR-23, final audit B10)")
            from explainer_engine.cloud import cheapest      # D-133: the cheapest known combination, every paid run
            why = (cheapest.generator_refusal(path, entry, cmd, env) if path == WAN_WORKER
                   else cheapest.ltx_refusal(entry, cmd, env))
            if why:
                return why
        elif not go.startswith("cmsg_"):
            return f"`modal run {target}` is paid: EE_MODAL_GO=<the creator's card id> first (OR-23)"
    return None


def _modal_live(runner=None):
    """The Modal apps that are not stopped, or None when there is no Modal CLI here (nothing to look at)."""
    import shutil
    import subprocess
    from explainer_engine.cloud import modal_run as MR
    if runner is None:
        if not shutil.which("modal"):
            return None

        def runner(argv):
            r = subprocess.run(argv, capture_output=True, text=True, timeout=25)
            return r.returncode, r.stdout
    try:
        rc, out = runner(["modal", "app", "list", "--json"])
    except Exception as e:  # noqa: BLE001 - advisory: a broken check never blocks a turn by itself
        return {"error": f"{type(e).__name__}"}
    if rc != 0:
        return {"error": f"modal app list exited {rc}"}
    try:
        return {"live": MR.live_apps(out)}
    except ValueError:
        return {"error": "modal app list gave no JSON"}


def modal_lines(res) -> list[str]:
    if res is None:
        return []
    if "error" in res:
        return [f"Modal check: cannot look ({res['error']})"]
    return [f"Modal check (D-131): {len(res['live'])} app(s) not stopped"] + \
        [f"PROBLEM Modal app {a['id']} {a['name']} is {a['state']}" for a in res["live"]]


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
        api = R.Api(retries=1, timeout=20)
        try:  # D-92: a stopped pod with 0 GB, 24 h past its until, goes before the check looks at it
            gone = R.auto_delete_stopped(api)
        except (R.RunPodError, OSError, TimeoutError) as e:
            gone = [f"auto-delete skipped: {str(e)[:80]}"]
        res = R.check(api)
        res["info"] += [f"auto-deleted (D-92): {line}" for line in gone]
    except (R.RunPodError, OSError) as e:
        return {"problems": [], "info": [f"RunPod not reachable: {str(e)[:80]}"], "unreadable": True}
    try:  # RP-07: a pod that stopped 90 min ago gets its bill into the ledger now; the PROGRESS line is for the session to copy
        res["info"] += [f"settled: {line}" for line in R.settle_due(api)]
    except Exception as e:  # noqa: BLE001 - advisory: whatever a pod's own files hold, the rest of the check must be shown
        res["info"].append(f"settle check failed ({type(e).__name__}: {str(e)[:60]}); run `runpod cost <pod>`")
    return res


def session_start(modal_runner=None) -> int:
    res = _check()
    lines = []
    if res is not None:
        lines = [f"RunPod check (D-56): {len(res['problems'])} problem(s)"] + ["PROBLEM " + p for p in res["problems"]] + res["info"]
        if res["problems"]:
            lines.append("Fix these before other work (stop/delete per the rules) and tell the creator what they cost.")
    lines += modal_lines(_modal_live(modal_runner))
    if lines:
        print("\n".join(lines))
    return 0


def stop(event: dict, modal_runner=None) -> int:
    if event.get("stop_hook_active"):
        return 0
    rc = _stop_runpod()
    if rc:
        return rc
    m = _modal_live(modal_runner)
    if m and m.get("live"):
        print("Modal apps are not stopped (D-131, cloud rules section 4: leave nothing paid running):\n  "
              + "\n  ".join(f"{a['id']} {a['name']} {a['state']}" for a in m["live"])
              + "\nStop them (`modal app stop <id>`) unless a watched, approved run is still working, and say which.",
              file=sys.stderr)
        return 2
    return 0


def _stop_runpod() -> int:
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
    why = modal_refusal(cmd)
    if why:
        print(f"refused (D-56, A7): {why}; nothing was started.", file=sys.stderr)
        return 2
    from explainer_engine.cloud import cheapest
    why = cheapest.picture_refusal(cmd)
    if why:
        print(f"refused (D-133): {why}; nothing was started.", file=sys.stderr)
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
