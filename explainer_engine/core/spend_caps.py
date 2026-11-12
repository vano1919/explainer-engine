
"""The creator's money ceilings from ``config/spend_caps.json`` (D-56): one file, read by the run ledger and the pod manager.
A run ledger may hold lower caps than the file, never higher; ``$EXPLAINER_SPEND_CAPS`` points at another file (tests)."""

from __future__ import annotations

import json
import os
from pathlib import Path

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


def modal(episode: bool = False) -> dict:
    """The Modal line (``modal``: ``per_run_usd``, ``per_episode_usd``; v4.3 D-131: Wan runs on Modal). A missing or
    non-positive ``per_run_usd`` = refused: until the creator adds the line, Modal has a zero approved project budget
    (.claude/rules/cloud-platforms.md section 4), whatever an approval card says. ``per_episode_usd`` is asked only for an
    episode's runs (``episode=True``): the creator sets it after rung L3 has measured the real price per clip (final audit
    section 7, answer 3, 2026-11-12 14:01 UTC); until then only the ladder's test runs may spend, each under ``per_run_usd``."""
    m = load().get("modal")
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0  # noqa: E731
    if not (isinstance(m, dict) and num(m.get("per_run_usd"))):
        raise OverCeiling("no modal per_run_usd in config/spend_caps.json: Modal spends nothing until the creator sets the "
                          "line (zero approved budget)")
    if episode and not num(m.get("per_episode_usd")):
        raise OverCeiling("no modal per_episode_usd in config/spend_caps.json: an episode's Modal runs wait for the creator's "
                          "episode line, set after rung L3 measures the price per clip (zero approved episode budget)")
    return m
