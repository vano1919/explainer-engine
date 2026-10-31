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


def frame_ms(frame_rate: float | None = None) -> float:
    """One frame in ms at the job's fps (BP-54 ``frames`` x 1000 / fps); no fps given = the delivery default (BP-167)."""
    rate = fps() if frame_rate is None else frame_rate
    if rate <= 0:
        raise ValueError(f"fps must be positive, got {rate}")
    return SR.T("BP-54", "frames") * 1000.0 / rate


def shorts_frame() -> tuple[int, int]:
    """A Short's (width, height): the master frame rotated 90 degrees (BP-167), 1440 x 2560."""
    w, h = size()
    return h, w


def defaults() -> dict:
    w, h = size()
    return {"long_minutes": long_minutes(), "width": w, "height": h, "fps": fps(), "shorts": shorts()}
