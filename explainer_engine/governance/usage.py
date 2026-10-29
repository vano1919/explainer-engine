"""Usage limits (creator 2026-10-29, project instruction 8; OR-30): at 95 % of the 5-hour or the weekly limit the unfinished
work is backed up so an endless job loses nothing.

What can be read: only the status-line JSON carries ``rate_limits.five_hour|seven_day.used_percentage`` (interactive Claude Code,
claude.ai Pro/Max). Cloud threads have ``get_session`` ``rate_limit_info.status == "allowed_warning"`` (no percentage) and the
``StopFailure`` hook (matcher ``rate_limit``) when the limit is already hit. All three end in :func:`backup`."""
from __future__ import annotations

import json
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from explainer_engine.core.store import write_json_atomic
from explainer_engine.governance import load, root_dir

DIR = Path("jobs") / "_usage"
WINDOWS = ("five_hour", "seven_day")
GIT_ID = ["-c", "user.name=vano1919", "-c", "user.email=122537395+vano1919@users.noreply.github.com"]
TRAILER = "\n\nAutomatic backup at the usage limit (OR-30); Co-Authored-By: Claude <noreply@anthropic.com>\n"
SECRET_NAMES = (".env", ".claude/settings.local.json", "api_key", "token", "secret", ".pem", "id_rsa", "id_ed25519", "credentials")
WINDOW_SECONDS = {"five_hour": 5 * 3600, "seven_day": 7 * 86400}


def record(data: dict, root=None, now: float | None = None) -> dict:
    """Keep the percentages of a status-line JSON in ``jobs/_usage/usage.json``; absent windows stay absent."""
    out = {"at": now if now is not None else time.time()}
    for w in WINDOWS:
        win = ((data or {}).get("rate_limits") or {}).get(w) or {}
        if "used_percentage" in win:
            out[w] = {"pct": float(win["used_percentage"]), "resets_at": win.get("resets_at")}
    if len(out) > 1:
        write_json_atomic(root_dir(root) / DIR / "usage.json", out)
    return out


def current(root=None, now: float | None = None) -> dict | None:
    """The last recorded usage if it is younger than ``usage.fresh_minutes``."""
    path = root_dir(root) / DIR / "usage.json"
    if not path.exists():
        return None
    cfg = load(root)["usage"]
    data = json.loads(path.read_text(encoding="utf-8"))
    if (now if now is not None else time.time()) - data["at"] > cfg["fresh_minutes"] * 60:
        return None
    return data


def over(usage: dict | None, threshold: float) -> list[tuple[str, float, object]]:
    """The windows at or above ``threshold`` as (window, percent, resets_at)."""
    return [(w, usage[w]["pct"], usage[w].get("resets_at")) for w in WINDOWS if usage and w in usage and usage[w]["pct"] >= threshold]


def _git(root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=120, check=check)


def backup(reason: str, root=None, *, window_key: str | None = None, push: bool = True, now: float | None = None) -> dict:
    """Save the unfinished work: project-files folder (diff, untracked files, state) and a WIP commit pushed to the current branch
    (never ``main``, never forced). Once per ``window_key`` (a marker file); returns what was done."""
    root = root_dir(root)
    cfg = load(root)["usage"]
    marker = None
    if window_key:
        marker = root / DIR / f"backup_{window_key}.done"
        if marker.exists():
            return {"skipped": "already backed up in this window", "window": window_key}
    stamp = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "detached"
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    base = Path(cfg["backup_dir"])
    dest = (base if base.parent.exists() else root / DIR / "backup") / branch.replace("/", "_") / stamp
    dest.mkdir(parents=True, exist_ok=True)
    result: dict = {"dest": str(dest), "branch": branch, "head": head, "reason": reason}
    (dest / "changes.diff").write_text(_git(root, "diff", "HEAD").stdout, encoding="utf-8")
    untracked = [p for p in _git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines() if p]
    cap, size, kept = cfg["untracked_cap_mb"] * 1024 * 1024, 0, []
    with tarfile.open(dest / "untracked.tar.gz", "w:gz") as tar:
        for rel in untracked:
            f = root / rel
            if f.is_file() and size + f.stat().st_size <= cap:
                size += f.stat().st_size
                tar.add(f, arcname=rel)
                kept.append(rel)
    result.update(untracked=len(untracked), untracked_saved=len(kept))
    phase = None
    active = root / "jobs" / "active_phase.json"
    if active.exists():
        phase = json.loads(active.read_text(encoding="utf-8")).get("phase")
        for f in sorted((root / "jobs" / phase).glob("*.json"))[:40] if phase and (root / "jobs" / phase).is_dir() else []:
            if f.stat().st_size < 1024 * 1024:
                (dest / f"job_{f.name}").write_bytes(f.read_bytes())
    result["phase"] = phase
    if push and branch not in ("main", "master", "detached"):
        _git(root, "add", "-A")
        staged = _git(root, "diff", "--cached", "--name-only").stdout.splitlines()
        secret = [f for f in staged if any(n in f.lower() for n in SECRET_NAMES)]
        if secret:  # never push what looks like a credential; it stays in the project-files copy only
            _git(root, "reset", "-q", "HEAD", "--", *secret)
            result["secret_like_not_committed"] = secret
        if _git(root, "status", "--porcelain").stdout.strip():
            c = _git(root, *GIT_ID, "commit", "-m", f"WIP auto-backup: {reason}{TRAILER}")
            result["commit"] = "ok" if c.returncode == 0 else c.stderr.strip()[:200]
        p = _git(root, "push", "-u", "origin", branch)
        result["push"] = "ok" if p.returncode == 0 else p.stderr.strip()[:200]
    else:
        result["push"] = "skipped (main/detached or push off)"
    write_json_atomic(dest / "state.json", result | {"usage": current(root, now=now)})
    if marker:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(stamp, encoding="utf-8")
    return result


def backup_if_over(usage: dict | None, root=None, **kw) -> dict | None:
    """Back up once per limit window when any window is at the configured percentage."""
    hit = over(usage, load(root)["usage"]["backup_at_percent"])
    if not hit:
        return None
    w, pct, resets = hit[0]
    # resets_at can be absent: fall back to a time bucket as long as the window, so the backup is once per window and not once ever
    return backup(f"usage {w} {pct:.0f}%", root, window_key=f"{w}_{resets or int(time.time() // WINDOW_SECONDS[w])}", **kw)
