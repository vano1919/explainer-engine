"""Shorts validators (final plan S19, W2): a Short's length (BP-137, BP-12) and the packaging promise (BP-135, critic)."""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-PKG-02", "CRAFT-PKG-05")


def short_length(seconds: float | None, gate: str = "CRAFT-PKG-05") -> dict:
    """CRAFT-PKG-05 (code): a Short stays inside YouTube's length limit (BP-137 shorts_max_s); outside BP-12's length bands but inside
    the limit is a REVIEW."""
    mx, bands = C.T("BP-137", "shorts_max_s"), C.T("BP-12", "bands_s")
    if mx is None or bands is None:
        return C.missing_threshold(gate, "BP-137/BP-12", "shorts_max_s, bands_s")
    if seconds is None:
        return G.row(gate, None, "NOT_RUN: the Short's length is not known")
    s = float(seconds)
    if s > mx:
        return C.check(gate, False, "BP-137", f"{s} s is over YouTube's {mx} s limit for a Short", s)
    in_band = any(lo <= s <= hi for lo, hi in bands)
    return G.row(gate, in_band, f"{s} s: inside the limit {mx} s; " + ("inside" if in_band else "outside") + f" BP-12's bands {bands}", s,
                 level=G.REVIEW)


def promise_paid(packaging: dict) -> dict:
    """CRAFT-PKG-02 (critic): the packaging names its ``promise`` and the script gives ``first_seconds_text`` (BP-135: paid within
    promise_paid_by_s); whether the first seconds pay it is judged."""
    by = C.T("BP-135", "promise_paid_by_s")
    miss = [k for k in ("promise", "first_seconds_text") if not str(packaging.get(k) or "").strip()]
    return C.critic("CRAFT-PKG-02", "BP-135", miss, f"the script's first seconds pay the chosen promise (within {by} s)")


def validate(packaging: dict, short_seconds: list[float] | None = None) -> list[dict]:
    rows = [promise_paid(packaging)]
    rows += [short_length(s) for s in (short_seconds or [])] or [short_length(None)]
    return rows
