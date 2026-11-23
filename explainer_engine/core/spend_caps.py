
"""The creator's money ceilings from ``config/spend_caps.json`` (D-56): one file, read by the run ledger and the pod manager.
A run ledger may hold lower caps than the file, never higher; ``$EXPLAINER_SPEND_CAPS`` points at another file (tests)."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]

PATH = Path(__file__).resolve().parents[2] / "config" / "spend_caps.json"


class OverCeiling(ValueError):
    """A cap or a pod asks for more than the creator's ceiling."""


def load() -> dict:
    p = Path(os.environ.get("EXPLAINER_SPEND_CAPS") or PATH)
    return json.loads(p.read_text(encoding="utf-8"))


def episode_ceiling(service: str) -> float | None:
    return load().get("per_episode", {}).get(service)


def allowance(name: str) -> dict:
    """A tool's own spending allowance (``allowances.<name>``: service, per_run): a ceiling inside the run's cap of that
    service, spent without asking first (the QA loop's re-reads, the creator 2026-10-20). Missing = no allowance."""
    a = load().get("allowances", {}).get(name)
    if not isinstance(a, dict) or "service" not in a or "per_run" not in a:
        raise OverCeiling(f"no allowance {name!r} in config/spend_caps.json: spending needs the creator's yes")
    return a


def paid_test(name: str) -> dict[str, float]:
    """One paid test's caps (``paid_tests.<name>``, the ``*_usd`` lines: service -> ceiling). Refuses a test that is not in the
    file and a section whose tests together pass ``total_usd``."""
    tests = load().get("paid_tests", {})
    t = tests.get(name) if not name.startswith("_") else None
    if not isinstance(t, dict):
        raise OverCeiling(f"no paid test {name!r} in config/spend_caps.json: a paid test needs the creator's yes and its line")
    total = sum(float(v) for row in tests.values() if isinstance(row, dict) for k, v in row.items() if k.endswith("_usd"))
    if total > float(tests.get("total_usd", 0)) + 1e-9:
        raise OverCeiling(f"paid tests add up to {total:g} USD, above their total_usd {tests.get('total_usd')} (config/spend_caps.json)")
    return {k: float(v) for k, v in t.items() if k.endswith("_usd")}


def casting_credits_max() -> float:
    """The ElevenLabs credits one casting session may spend (``casting.casting_credits_max``, the creator 2026-10-30)."""
    v = load().get("casting", {}).get("casting_credits_max")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no casting_credits_max in config/spend_caps.json: casting spends nothing without the creator's number")
    return float(v)


def gemini_api() -> dict:
    """The Gemini API line (``gemini_api``: max_usd per calendar month). Missing or not a positive number = refused."""
    g = load().get("gemini_api")
    v = g.get("max_usd") if isinstance(g, dict) else None
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no gemini_api max_usd in config/spend_caps.json: the Gemini API spends nothing without the creator's line")
    return g


def overnight(name: str) -> dict:
    """One night's ceiling (``overnight.<name>``: max_usd and its lines). A night whose lines together pass its max_usd, or
    a night not in the file, is refused: the lines of every paid service of the night add up to one number (the creator
    2026-11-22: $20 in total)."""
    nights = load().get("overnight", {})
    n = nights.get(name) if not name.startswith("_") else None
    if not isinstance(n, dict) or not isinstance(n.get("max_usd"), (int, float)) or isinstance(n.get("max_usd"), bool):
        raise OverCeiling(f"no overnight {name!r} with a max_usd in config/spend_caps.json: a night spends nothing without its line")
    total = 0.0
    for row in (n.get("lines") or {}).values():
        if isinstance(row, dict):
            total += sum(float(v) for k, v in row.items() if k.endswith("_usd"))
    if total > float(n["max_usd"]) + 1e-9:
        raise OverCeiling(f"overnight {name!r} lines add up to {total:g} USD, above its max_usd {n['max_usd']} (config/spend_caps.json)")
    return n


OVERNIGHT = "overnight_2026_11_23"   # the night the paid runners are counted against (config/spend_caps.json overnight)


def _overnight_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_OVERNIGHT_DIR") or Path(__file__).resolve().parents[2] / "jobs" / "overnight")


def overnight_spent(name: str = OVERNIGHT) -> float:
    """Everything the night has booked so far, in every service: reservations plus their corrections (each row adds a USD
    amount; a reservation with no correction stays booked, the safe side)."""
    f = _overnight_dir() / f"{name}.jsonl"
    if not f.exists():
        return 0.0
    return round(sum(float(json.loads(x)["usd"]) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()), 6)


def _overnight_append(name: str, row: dict) -> None:
    d = _overnight_dir()
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{name}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


_ENVELOPE_SERVICE_MAP = {
    "deepseek": "deepseek",
    "deepseek_api": "deepseek",
    "claude_api": "claude_api",
    "anthropic": "claude_api",
    "modal": "modal_modal1",
    "modal_ltx": "modal_modal1",
    "modal1": "modal_modal1",
    "modal_modal1": "modal_modal1",
}


def envelope_enabled(cfg: dict | None = None) -> bool:
    """Return False when orchestration_envelopes is explicitly disabled or marked unverified."""
    data = cfg if cfg is not None else load()
    env = data.get("orchestration_envelopes") or {}
    if not env:
        return False
    return not (env.get("enabled") is False or env.get("verified_owner_evidence") is False)


def strictest_modal_cap_usd(cfg: dict | None = None) -> float:
    """Return the strictest positive Modal USD cap across all configured spend_caps.json sections."""
    data = cfg if cfg is not None else load()
    candidates: list[float] = []
    for section, key in (
        ("modal_ltx", "per_run_usd"),
        ("modal_render", "per_episode_usd"),
        ("modal", "night_total_usd"),
        ("modal", "per_run_usd"),
    ):
        val = (data.get(section) or {}).get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0:
            candidates.append(float(val))
    overnight_cfg = data.get("overnight") or {}
    for k, night in overnight_cfg.items():
        if k.startswith("_") or not isinstance(night, dict):
            continue
        for line in (night.get("lines") or {}).values():
            if isinstance(line, dict):
                v = line.get("modal_usd")
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                    candidates.append(float(v))
    if envelope_enabled(data):
        v = ((data.get("orchestration_envelopes") or {}).get("services") or {}).get("modal_modal1", {}).get("max_usd")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            candidates.append(float(v))
    if not candidates:
        raise OverCeiling("no positive Modal cap configured in config/spend_caps.json")
    return min(candidates)


def _envelope_service_for(service: str) -> str | None:
    mapped = _ENVELOPE_SERVICE_MAP.get(service)
    if not mapped:
        return None
    cfg = load()
    if not envelope_enabled(cfg):
        return None
    env_services = (cfg.get("orchestration_envelopes") or {}).get("services") or {}
    return mapped if mapped in env_services else None


def overnight_reserve(service: str, uid: str, estimate: float, name: str = OVERNIGHT) -> None:
    """Refuse a paid call unless the night's booked spend plus this call's estimate stays within the night's max_usd
    and (when configured) the service's independent orchestration envelope. On success both are booked under uid."""
    n = overnight(name)
    spent = overnight_spent(name)
    if spent + estimate > float(n["max_usd"]) + 1e-9:
        raise OverCeiling(f"{service}: the night has ${spent:.4f} booked and this call estimates ${estimate:.4f}, which would pass "
                          f"its ${float(n['max_usd']):g} ceiling (config/spend_caps.json overnight); stop and ask the creator")
    env_svc = _envelope_service_for(service)
    if env_svc is not None:
        envelope_reserve(env_svc, uid, estimate)
    _overnight_append(name, {"service": service, "uid": uid, "usd": round(estimate, 6), "kind": "reserve"})


def overnight_settle(service: str, uid: str, actual: float, reserved: float, name: str = OVERNIGHT) -> None:
    """Replace uid's reservation by the actual USD in both overnight and orchestration envelope ledgers.

    Settlement errors are never silently swallowed: an envelope mismatch or cap overrun is recorded
    and raised loudly so runaway spend cannot be hidden.
    """
    _overnight_append(name, {"service": service, "uid": uid, "usd": round(actual - reserved, 6), "kind": "settle"})
    env_svc = _envelope_service_for(service)
    if env_svc is not None and envelope_enabled():
        envelope_settle(env_svc, uid, actual)


def runpod() -> dict:
    return load()["runpod"]


def check_caps(caps: dict) -> dict:
    """Fill a run's missing caps from the file and refuse any cap above it."""
    out = dict(caps)
    for service, ceiling in load().get("per_episode", {}).items():
        if service not in out:
            out[service] = ceiling
        elif out[service] > ceiling + 1e-9:
            raise OverCeiling(f"{service} cap {out[service]} is above the creator's ceiling {ceiling} (config/spend_caps.json)")
    return out


def modal_bakeoff() -> dict:
    """The creator's line for the v4.3 video bake-off only (``modal_bakeoff``: ``per_run_usd``, ``tests_total_usd``; the creator
    2026-11-12 17:50 UTC). It is not the Wan route's ``modal`` line: that one stays unset (a zero budget) until rung L3."""
    m = load().get("modal_bakeoff")
    def num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    if not (isinstance(m, dict) and num(m.get("per_run_usd")) and num(m.get("tests_total_usd"))):
        raise OverCeiling("no modal_bakeoff line in config/spend_caps.json: the bake-off spends nothing until the creator sets it")
    return m


def modal_cheap_video() -> dict:
    """The creator's line for the cheaper-video-generator test on Modal (``modal_cheap_video``: ``per_run_usd``,
    ``tests_total_usd``; the creator 2026-11-12 22:21 UTC, "$3 on Modal"). Its own key, like ``modal_bakeoff``."""
    m = load().get("modal_cheap_video")
    def num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    if not (isinstance(m, dict) and num(m.get("per_run_usd")) and num(m.get("tests_total_usd"))):
        raise OverCeiling("no modal_cheap_video line in config/spend_caps.json: the test spends nothing until the creator sets it")
    return m


def modal_test_line(name: str) -> dict:
    """One of the creator's Modal test lines by name (a bake-off plan's ``spend_line``); any other name is refused."""
    lines = {"modal_bakeoff": modal_bakeoff, "modal_cheap_video": modal_cheap_video}
    if name not in lines:
        raise OverCeiling(f"{name!r} is not one of the creator's Modal test lines {sorted(lines)}")
    return lines[name]()


def modal(episode: bool = False) -> dict:
    """The Modal line (``modal``: ``per_run_usd``, ``per_episode_usd``; v4.3 D-131: Wan runs on Modal). A missing or
    non-positive ``per_run_usd`` = refused: until the creator adds the line, Modal has a zero approved project budget
    (.claude/rules/cloud-platforms.md section 4), whatever an approval card says. ``per_episode_usd`` is asked only for an
    episode's runs (``episode=True``): the creator sets it after rung L3 has measured the real price per clip (final audit
    section 7, answer 3, 2026-11-12 14:01 UTC); until then only the ladder's test runs may spend, each under ``per_run_usd``."""
    m = load().get("modal")
    def num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    if not (isinstance(m, dict) and num(m.get("per_run_usd"))):
        raise OverCeiling("no modal per_run_usd in config/spend_caps.json: Modal spends nothing until the creator sets the "
                          "line (zero approved budget)")
    if episode and not num(m.get("per_episode_usd")):
        raise OverCeiling("no modal per_episode_usd in config/spend_caps.json: an episode's Modal runs wait for the creator's "
                          "episode line, set after rung L3 measures the price per clip (zero approved episode budget)")
    return m


def modal_ltx(episode: bool = False) -> dict:
    """The creator's Modal line for the video route's LTX clips (``modal_ltx``: ``per_run_usd``, later ``per_episode_usd``;
    D-132, 2026-11-12). Its own key, like ``modal_bakeoff``: the Wan route's ``modal`` line is not reused. Missing = refused, a
    zero approved budget, until the creator sets the numbers (cloud rules section 4); ``per_episode_usd`` comes after rung L3."""
    m = load().get("modal_ltx")
    def num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    if not (isinstance(m, dict) and num(m.get("per_run_usd"))):
        raise OverCeiling("no modal_ltx per_run_usd in config/spend_caps.json: the LTX video route spends nothing until the "
                          "creator sets the line (zero approved budget)")
    if episode and not num(m.get("per_episode_usd")):
        raise OverCeiling("no modal_ltx per_episode_usd in config/spend_caps.json: an episode's LTX runs wait for the creator's "
                          "episode line, set after rung L3 (zero approved episode budget)")
    return m


def _envelope_ledger_path() -> Path:
    env = os.environ.get("EXPLAINER_ENVELOPE_LEDGER")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "jobs" / "orchestrator" / "envelope_ledger.json"


def envelope_limit(service: str) -> float:
    """Return the independent aggregate USD ceiling for an orchestration envelope service."""
    env = load().get("orchestration_envelopes", {})
    services = env.get("services") or {}
    row = services.get(service)
    if not isinstance(row, dict) or not isinstance(row.get("max_usd"), (int, float)) or isinstance(row.get("max_usd"), bool):
        raise OverCeiling(f"no orchestration_envelopes.services.{service}.max_usd in config/spend_caps.json")
    combined = float(env.get("combined_max_usd", 0.0))
    total_defined = sum(float(r["max_usd"]) for r in services.values() if isinstance(r, dict) and "max_usd" in r)
    if combined > 0 and total_defined > combined + 1e-9:
        raise OverCeiling(f"orchestration envelopes sum to {total_defined:g} USD, above combined_max_usd {combined:g}")
    return float(row["max_usd"])


def envelope_status() -> dict:
    """Return actual spent, reserved, and remaining USD per independent envelope."""
    env_cfg = load().get("orchestration_envelopes", {})
    services = env_cfg.get("services") or {}
    lp = _envelope_ledger_path()
    ledger = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {"entries": []}
    out = {}
    for svc, cfg in services.items():
        spent = sum(float(e.get("actual_usd", 0.0)) for e in ledger.get("entries", []) if e.get("service") == svc and e.get("state") == "SETTLED")
        reserved = sum(float(e.get("reserved_usd", 0.0)) for e in ledger.get("entries", []) if e.get("service") == svc and e.get("state") == "RESERVED")
        lim = float(cfg["max_usd"])
        out[svc] = {
            "max_usd": lim,
            "spent_usd": round(spent, 6),
            "reserved_usd": round(reserved, 6),
            "remaining_usd": round(max(0.0, lim - spent - reserved), 6),
        }
    return out


@contextlib.contextmanager
def _envelope_lock(lp: Path):
    lp.parent.mkdir(parents=True, exist_ok=True)
    lock_path = lp.with_suffix(lp.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lf:
        if fcntl is not None:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def envelope_reserve(service: str, task_id: str, max_estimated_usd: float) -> dict:
    """Fail-closed, file-locked reservation against the service's independent aggregate envelope."""
    if max_estimated_usd < 0:
        raise OverCeiling("negative reservation is invalid")
    lim = envelope_limit(service)
    lp = _envelope_ledger_path()
    with _envelope_lock(lp):
        ledger = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {"entries": []}
        spent = sum(float(e.get("actual_usd", 0.0)) for e in ledger.get("entries", []) if e.get("service") == service and e.get("state") == "SETTLED")
        reserved = sum(float(e.get("reserved_usd", 0.0)) for e in ledger.get("entries", []) if e.get("service") == service and e.get("state") == "RESERVED")
        if spent + reserved + max_estimated_usd > lim + 1e-9:
            raise OverCeiling(
                f"{service}: spent ${spent:.4f} + reserved ${reserved:.4f} + "
                f"request ${max_estimated_usd:.4f} exceeds independent ceiling ${lim:.2f}"
            )
        entry = {"task_id": task_id, "service": service, "reserved_usd": round(float(max_estimated_usd), 6), "actual_usd": 0.0, "state": "RESERVED"}
        ledger["entries"].append(entry)
        _atomic_write_json(lp, ledger)
        return entry


def envelope_settle(service: str, task_id: str, actual_usd: float) -> dict:
    """File-locked settlement of a reserved envelope entry with provider-reported actual USD."""
    lp = _envelope_ledger_path()
    with _envelope_lock(lp):
        ledger = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {"entries": []}
        for e in reversed(ledger.get("entries", [])):
            if e.get("service") == service and e.get("task_id") == task_id and e.get("state") == "RESERVED":
                e["actual_usd"] = round(float(actual_usd), 6)
                e["state"] = "SETTLED"
                _atomic_write_json(lp, ledger)
                return e
    raise OverCeiling(f"no open RESERVED envelope entry for {service}/{task_id}")
