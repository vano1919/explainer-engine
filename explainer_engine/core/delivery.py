"""Delivery defaults of an animated episode (BP-167, the creator's word of 2026-10-30 16:13 UTC, D-59 house).

The one reader of the registry row: the long video's target minutes, its frame size, its frame rate and the number of Shorts.
A job or script that names its own fps or size keeps it; the still-picture route (D-43) does not read this module.
"""

from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR


def long_minutes() -> int:
    return SR.T("BP-167", "long_minutes")


def size() -> tuple[int, int]:
    return SR.T("BP-167", "width"), SR.T("BP-167", "height")


def fps() -> int:
    return SR.T("BP-167", "fps")


def shorts() -> int:
    return SR.T("BP-167", "shorts")


def defaults() -> dict:
    w, h = size()
    return {"long_minutes": long_minutes(), "width": w, "height": h, "fps": fps(), "shorts": shorts()}
