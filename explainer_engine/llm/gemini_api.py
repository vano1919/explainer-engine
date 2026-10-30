"""The Gemini API (the Argon reviewer): its monthly ceiling and nothing else yet.

The creator's line is ``gemini_api`` in ``config/spend_caps.json`` (max_usd per calendar month, 2026-10-30). No client exists, so
``complete`` always refuses; ``reserve`` is the check the client will call before a paid request (the 80 % stop of the ledger,
invariant 2). The picture calls of ``imagegen/gemini.py`` keep their own per-episode line and are not touched.
"""

from __future__ import annotations

from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import STOP_FRACTION


class GeminiRefused(RuntimeError):
    """A Gemini API call was asked for that this repository does not allow yet."""


def monthly_ceiling() -> float:
    return float(spend_caps.gemini_api()["max_usd"])


def reserve(estimate_usd: float, spent_month_usd: float) -> float:
    """The month's spend after this request, or GeminiRefused when it would pass 80 % of the ceiling (stop and ask)."""
    if estimate_usd < 0 or spent_month_usd < 0:
        raise GeminiRefused("a Gemini request cannot cost or have cost less than nothing")
    after = spent_month_usd + estimate_usd
    limit = monthly_ceiling() * STOP_FRACTION
    if after > limit + 1e-9:
        raise GeminiRefused(f"Gemini API: ${after:.2f} this month would pass {STOP_FRACTION:.0%} of the ${monthly_ceiling():g} ceiling "
                            "(config/spend_caps.json gemini_api); stop and ask the creator")
    return after


def complete(*_args, **_kwargs):
    raise GeminiRefused("the Gemini API client is not built yet: nothing may call it (docs/PROGRESS.md, D9 2026-10-30)")
