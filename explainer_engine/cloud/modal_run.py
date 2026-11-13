"""Modal launcher helpers (OR-37, plan MODAL_RUN_PLAN_OPUS.md): the ladder order, the app id of a detached run and the stop command.
Pure functions; the commands themselves are run by the session that has a valid token (``pip install 'modal[api-proxy-support]'``)."""
from __future__ import annotations

import json
import re

LADDER = ("L0", "L1", "L2", "L3", "L4")   # L0 local tests, L1 CPU imports/shas/--list/token, L2 CPU model+LoRA keys, L3 GPU tiny, L4 full
APP_ID = re.compile(r"\bap-[A-Za-z0-9]{10,}\b")


def next_rung(done: list[str], red: str | None = None) -> str | None:
    """The next ladder rung to run, or None when a rung is red (stop) or all are done; a rung is never skipped."""
    if red:
        return None
    for r in LADDER:
        if r not in done:
            return r
    return None


def parse_app_id(text: str) -> str | None:
    """The first Modal app id (ap-...) in the output of `modal run --detach`."""
    m = APP_ID.search(text or "")
    return m.group(0) if m else None


def stop_target(app_list_json: str, name: str) -> list[str]:
    """App ids to stop for ``name`` from `modal app list --json`: ephemeral apps stop only by id, never by name."""
    rows = json.loads(app_list_json)
    out = []
    for r in rows:
        rn = r.get("Description") or r.get("name") or ""
        state = (r.get("State") or r.get("state") or "").lower()
        if rn == name and state not in ("stopped", "stopping"):
            out.append(r.get("App ID") or r.get("app_id") or r.get("id"))
    return [i for i in out if i]


def live_apps(app_list_json: str) -> list[dict]:
    """Every app of `modal app list --json` that is not stopped (the session hooks list them at start and stop, A7)."""
    out = []
    for r in json.loads(app_list_json or "[]"):
        state = (r.get("State") or r.get("state") or "").lower()
        if state not in ("stopped", "stopping"):
            out.append({"id": r.get("App ID") or r.get("app_id") or r.get("id"), "name": r.get("Description") or r.get("name"),
                        "state": state or "?"})
    return out


def load_ladder(path) -> dict:
    """A run's ladder record (``{"done": [...], "red": rung|None, "measured": {...}, "rungs": {rung: {...}}}``); none yet = empty."""
    from pathlib import Path
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"done": [], "red": None, "measured": {}, "rungs": {}}


PROOF = ("launch_sha", "worker_sha")   # what a Modal rung proves (final audit A5): this launch file, run by this worker


def stale(ladder: dict, proof: dict | None, upto: str = "L4") -> list[str]:
    """The green rungs L1.. below ``upto`` that were NOT proved on ``proof`` (another launch file or worker, or none recorded):
    they must be run again before any rung above them (final audit A5)."""
    if not proof:
        return []
    rungs = ladder.get("rungs") or {}
    return [r for r in LADDER[1:LADDER.index(upto)] if r in (ladder.get("done") or [])
            and any((rungs.get(r) or {}).get(k) != proof.get(k) for k in PROOF)]


def gate(ladder: dict, rung: str, proof: dict | None = None) -> None:
    """Refuse a rung that is not the next one (OR-37: L0..L4 in order, none skipped, none after a red one). A green rung may be
    run again; it never opens the rungs above it twice. With ``proof`` (the launch file's and the worker's sha256), a rung
    below that was proved on another launch file or worker counts as not green (final audit A5)."""
    if rung not in LADDER:
        raise ValueError(f"unknown rung {rung!r}; the ladder is {LADDER}")
    if ladder.get("red"):
        raise SystemExit(f"rung {ladder['red']} is red: fix it and record it green before {rung} (OR-37); nothing was started")
    done = list(ladder.get("done") or [])
    missing = [r for r in LADDER[:LADDER.index(rung)] if r not in done]
    if missing:
        raise SystemExit(f"rung {rung} needs {missing} green first (OR-37); nothing was started")
    old = stale(ladder, proof, rung)
    if old:
        raise SystemExit(f"rung(s) {old} were proved on another launch file or worker: run them again before {rung} (OR-37, "
                         "final audit A5); nothing was started")


def record_rung(path, rung: str, ok: bool, **info) -> dict:
    """Write one rung's result to the ladder file (atomically): green adds it to ``done``, red sets ``red``; L3's
    ``measured`` (gpu, s_per_clip_s, setup_s) becomes the ladder's ``measured``, the price base of L4."""
    import time
    from explainer_engine.core.store import write_json_atomic
    if ok and rung == "L0" and not info.get("commit"):
        raise ValueError("a green L0 records the commit its tests ran on (final audit A5): use `modal_run l0`")
    if ok and rung != "L0" and not all(info.get(k) for k in PROOF):
        raise ValueError(f"a green {rung} records the launch file's and the worker's sha256 (final audit A5): only the worker's "
                         "own entrypoint records it")
    lad = load_ladder(path)
    pr = {k: info[k] for k in PROOF if info.get(k)} or None
    gate(dict(lad, red=None if lad.get("red") == rung else lad.get("red")), rung, proof=pr)
    lad.setdefault("rungs", {})[rung] = dict(info, ok=bool(ok), at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    if ok:
        lad["done"] = [r for r in LADDER if r in set(lad.get("done") or []) | {rung}]
        lad["red"] = None if lad.get("red") == rung else lad.get("red")
        if rung == "L3" and info.get("measured"):
            lad["measured"] = dict(info["measured"])
    else:
        lad["red"] = rung
    write_json_atomic(path, lad)
    return lad


L0_TESTS = ("tests/unit/test_v43_wan_adapter.py", "tests/unit/test_v43_wan_worker.py", "tests/unit/test_v43_retired.py",
            "tests/unit/test_cloud_hooks_modal.py")


def _sh(argv) -> tuple[int, str]:
    import subprocess
    r = subprocess.run(argv, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def l0(path, tests=L0_TESTS, runner=None) -> dict:
    """Rung L0, free and local: the Wan tests run here, and the rung records their pytest summary and the commit they ran on;
    green only when pytest exits 0 and the tree has no uncommitted change to the code (final audit A5)."""
    import sys
    runner = runner or _sh
    rc, out = runner([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests])
    summary = next((ln.strip() for ln in reversed(out.splitlines()) if ln.strip()), "")
    crc, commit = runner(["git", "rev-parse", "HEAD"])
    drc, dirty = runner(["git", "status", "--porcelain", "--", "explainer_engine", "tests", "config"])
    ok = rc == 0 and crc == 0 and drc == 0 and not dirty.strip()
    info = {"tests": list(tests), "pytest": summary[:300], "commit": commit.strip() if crc == 0 else None}
    if drc == 0 and dirty.strip():
        info["note"] = "uncommitted changes to the code: commit first, so L0 names what it tested"
    return record_rung(path, "L0", ok, **info)


def main(argv=None) -> int:
    """``python -m explainer_engine.cloud.modal_run l0 <ladder.json>`` (rung L0: the tests, recorded with their summary and
    commit), ``... red <ladder.json> <rung> [--note text]`` (mark a rung red by hand: only a rung's own run makes it green) and
    ``... show <ladder.json>``: the ladder file the Wan worker's entrypoints and the adapter read."""
    import argparse
    ap = argparse.ArgumentParser(prog="modal_run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("l0")
    z.add_argument("ladder")
    r = sub.add_parser("red")
    r.add_argument("ladder")
    r.add_argument("rung", choices=LADDER)
    r.add_argument("--note", default="")
    sh = sub.add_parser("show")
    sh.add_argument("ladder")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        lad = load_ladder(a.ladder)
        print(json.dumps(dict(lad, next=next_rung(lad.get("done") or [], lad.get("red"))), indent=1))
        return 0
    lad = l0(a.ladder) if a.cmd == "l0" else record_rung(a.ladder, a.rung, False, note=a.note)
    print(json.dumps({"done": lad["done"], "red": lad["red"], "next": next_rung(lad["done"], lad["red"])}))
    return 0 if a.cmd == "red" or "L0" in lad["done"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
