
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


def modal_bakeoff() -> dict:
    """The creator's line for the v4.3 video bake-off only (``modal_bakeoff``: ``per_run_usd``, ``tests_total_usd``; the creator
    2026-11-12 17:50 UTC). It is not the Wan route's ``modal`` line: that one stays unset (a zero budget) until rung L3."""
    m = load().get("modal_bakeoff")
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0  # noqa: E731
    if not (isinstance(m, dict) and num(m.get("per_run_usd")) and num(m.get("tests_total_usd"))):
        raise OverCeiling("no modal_bakeoff line in config/spend_caps.json: the bake-off spends nothing until the creator sets it")
    return m


def modal_cheap_video() -> dict:
    """The creator's line for the cheaper-video-generator test on Modal (``modal_cheap_video``: ``per_run_usd``,
    ``tests_total_usd``; the creator 2026-11-12 22:21 UTC, "$3 on Modal"). Its own key, like ``modal_bakeoff``."""
    m = load().get("modal_cheap_video")
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0  # noqa: E731
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
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0  # noqa: E731
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
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0  # noqa: E731
    if not (isinstance(m, dict) and num(m.get("per_run_usd"))):
        raise OverCeiling("no modal_ltx per_run_usd in config/spend_caps.json: the LTX video route spends nothing until the "
                          "creator sets the line (zero approved budget)")
    if episode and not num(m.get("per_episode_usd")):
        raise OverCeiling("no modal_ltx per_episode_usd in config/spend_caps.json: an episode's LTX runs wait for the creator's "
                          "episode line, set after rung L3 (zero approved episode budget)")
    return m
