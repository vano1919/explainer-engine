"""Picture routing (D-52): every picture is painted by Gemini on the batch tier, on one of three tiers. stdlib only.

Scope (N-06, 2026-10-30): the D-43 still-picture route. An animated episode's keyframes (D-77, D-80) are made on a pod with
Qwen-Image-2.1 and the xworld_v2 LoRA and are not routed here; its route is docs/SHOT_CONTINUITY.md and docs/SHOT_PROMPTS.md.

The tier is chosen by what the picture has to do, never by habit (docs/VISUAL_WORLD_ARCHITECTURE.md section 6):

* ``draft``    - Nano Banana 2.1 at 1K: composition and story tests, replaceable pictures. Same model as the final, so a
                 draft predicts the final (Flash-Lite at the same price ignored the world's palette and came back 1376x768,
                 Episode 1 test, 2026-10-17).
* ``standard`` - Nano Banana 2.1 at 2K: every scene picture. Episode 1's 74 pictures were made with it and accepted.
* ``premium``  - Gemini 3 Pro Image at 2K: only where the picture is reused across videos (cast references, thumbnail
                 elements) or a reveal shot that must hold several references at once; each one carries a reason, and at
                 most a tenth of an episode's pictures may be premium (PV-40).

4K is not routed: the video is 1080p/1440p and pictures are graded to 1.2 x the frame, which 2K covers.
Batch prices (USD per picture, ai.google.dev/gemini-api/docs/pricing, checked 2026-10-17) live in ``gemini.BATCH_PRICES``.
"""

from __future__ import annotations

from explainer_engine.imagegen.gemini import BATCH_PRICES, REFERENCE_USD

TIERS = {
    "draft": ("gemini-nano-banana-2.1", "1K"),
    "standard": ("gemini-nano-banana-2.1", "2K"),
    "premium": ("gemini-3-pro-image", "2K"),
}
DEFAULT_TIER = "standard"
PREMIUM_SHARE_MAX = 0.10


def tier_of(pic: dict) -> str:
    return pic.get("tier") or DEFAULT_TIER


def route(tier: str) -> tuple[str, str]:
    """(model, size) of a tier; an unknown tier is an error, never a silent default."""
    if tier not in TIERS:
        raise ValueError(f"unknown picture tier {tier!r}; one of {sorted(TIERS)}")
    return TIERS[tier]


def batch_cost(tier: str, references: int = 0) -> float:
    model, size = route(tier)
    return round(BATCH_PRICES[model][size] + references * REFERENCE_USD, 4)
