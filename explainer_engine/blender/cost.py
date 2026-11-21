"""The cost of a Blender render from MEASURED rows only (roadmap section 11 and 12.3; ICW-04 skeleton, ICW-09 fills the rows).

``CostModel.estimate(frames, profile, card, price_per_h)`` reads ``config/job_speeds.json`` (``blender_frame_<profile>_<tier>``,
one row per card, written by ``runpod cost`` from a pod's ``units.json``, never typed) and returns a ledger line. With no row it
raises ``CostUnknown``: every s/frame of roadmap 12.3 is HYP until ICW-09 measures it, so nothing is priced from a guess.
``CostModel.reserve(run, line)`` books the line on the run ledger, which stops at 80 % of a cap (``core.ledger.CapReached``).
"""
from __future__ import annotations

from explainer_engine.blender import profiles as P
from explainer_engine.cloud import speeds
from explainer_engine.core.errors import NeedsReview


class CostUnknown(NeedsReview):
    """No measured row for this profile, tier and card: the estimate is not made (ICW-09 measures it first)."""


class CostModel:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data if data is not None else speeds.load()

    def estimate(self, frames: int, profile: str, card: str, price_per_h: float, *, tier: str = "1440") -> dict:
        if frames <= 0:
            raise ValueError("frames must be positive")
        job = P.get(profile).job_type(tier)
        if job not in self.data["jobs"]:
            raise CostUnknown(f"no job type {job} in config/job_speeds.json (a new tier is a PR)")
        est = speeds.estimate(job, card, frames, self.data)
        if est is None:
            raise CostUnknown(f"{job} has no measured row on {card}: no estimate before ICW-09 measures it (roadmap 12.3 is HYP)")
        hours = est["work_h"] + est["setup_h"]
        return {"service": "runpod_usd", "job_type": job, "card": card, "frames": frames, "work_h": round(est["work_h"], 4),
                "setup_h": round(est["setup_h"], 4), "setup_known": est["setup_known"], "price_per_h": price_per_h,
                "usd": round(hours * price_per_h, 4), "basis": est["basis"]}

    @staticmethod
    def reserve(run, line: dict, item: str) -> None:
        """Book the estimate before the pod (OR-02): ``Run.reserve`` raises CapReached past 80 % of the cap (invariant 2)."""
        run.reserve(line["service"], line["usd"], item=item)
