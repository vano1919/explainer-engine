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
