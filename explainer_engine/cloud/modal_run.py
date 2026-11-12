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


def load_ladder(path) -> dict:
    """A run's ladder record (``{"done": [...], "red": rung|None, "measured": {...}, "rungs": {rung: {...}}}``); none yet = empty."""
    from pathlib import Path
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"done": [], "red": None, "measured": {}, "rungs": {}}


def gate(ladder: dict, rung: str) -> None:
    """Refuse a rung that is not the next one (OR-37: L0..L4 in order, none skipped, none after a red one). A green rung may be
    run again; it never opens the rungs above it twice."""
    if rung not in LADDER:
        raise ValueError(f"unknown rung {rung!r}; the ladder is {LADDER}")
    if ladder.get("red"):
        raise SystemExit(f"rung {ladder['red']} is red: fix it and record it green before {rung} (OR-37); nothing was started")
    done = list(ladder.get("done") or [])
    missing = [r for r in LADDER[:LADDER.index(rung)] if r not in done]
    if missing:
        raise SystemExit(f"rung {rung} needs {missing} green first (OR-37); nothing was started")


def record_rung(path, rung: str, ok: bool, **info) -> dict:
    """Write one rung's result to the ladder file (atomically): green adds it to ``done``, red sets ``red``; L3's
    ``measured`` (gpu, s_per_clip_s, setup_s) becomes the ladder's ``measured``, the price base of L4."""
    import time
    from explainer_engine.core.store import write_json_atomic
    lad = load_ladder(path)
    gate(dict(lad, red=None if lad.get("red") == rung else lad.get("red")), rung)
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


def main(argv=None) -> int:
    """``python -m explainer_engine.cloud.modal_run record <ladder.json> <rung> ok|red [--measured '{json}'] [--note text]``
    and ``... show <ladder.json>``: the ladder file the Wan worker's entrypoints and the adapter read."""
    import argparse
    ap = argparse.ArgumentParser(prog="modal_run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("ladder")
    r.add_argument("rung", choices=LADDER)
    r.add_argument("result", choices=("ok", "red"))
    r.add_argument("--measured", default=None)
    r.add_argument("--note", default="")
    sh = sub.add_parser("show")
    sh.add_argument("ladder")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        lad = load_ladder(a.ladder)
        print(json.dumps(dict(lad, next=next_rung(lad.get("done") or [], lad.get("red"))), indent=1))
        return 0
    info = {"note": a.note}
    if a.measured:
        info["measured"] = json.loads(a.measured)
    lad = record_rung(a.ladder, a.rung, a.result == "ok", **info)
    print(json.dumps({"done": lad["done"], "red": lad["red"], "next": next_rung(lad["done"], lad["red"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
