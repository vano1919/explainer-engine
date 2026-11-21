"""Provider-neutral GPU capacity selector (RP-01, RP-09, OR-22).

Ranks compatible GPU offers across RunPod, Hyperstack, and Modal by estimated total job cost,
stock confidence, and provider reliability, or returns ``status="no_safe_option"`` with explicit
rejection reasons when no offer satisfies all safety constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from explainer_engine.cloud.providers.base import (
    CostBreakdown,
    GpuCapacityOffer,
    ProviderError,
    WorkloadSpec,
)

TIER_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 9}


@dataclass(frozen=True)
class RankedCandidate:
    """A compatible, ranked GPU candidate with its cost breakdown and selection rationale."""

    rank: int
    offer: GpuCapacityOffer
    cost: CostBreakdown
    reason: str


class ProviderSelector:
    """Evaluate and rank GPU offers across providers without provisioning resources."""

    def __init__(self, adapters: dict[str, Any], *, setup_share_max: float = 0.40) -> None:
        self.adapters = adapters
        self.setup_share_max = setup_share_max

    def select(
        self,
        workload: WorkloadSpec,
        offers: list[GpuCapacityOffer],
        *,
        warm_by_provider: dict[str, bool] | None = None,
        use_net_credits: bool = False,
        now: float | None = None,
    ) -> dict[str, Any]:
        """Filter and rank ``offers`` for ``workload``. Never provisions anything."""
        cur = time.time() if now is None else now
        warm_map = warm_by_provider or {}
        accepted: list[tuple[GpuCapacityOffer, CostBreakdown]] = []
        rejected: list[dict[str, str]] = []

        for offer in offers:
            adapter = self.adapters.get(offer.provider)
            if adapter is None:
                rejected.append({
                    "provider": offer.provider,
                    "gpu": offer.gpu_type,
                    "region": offer.region,
                    "reason": f"unknown provider {offer.provider}",
                })
                continue
            try:
                ok, msg = adapter.can_run(workload, offer, now=cur)
                if not ok:
                    rejected.append({
                        "provider": offer.provider,
                        "gpu": offer.gpu_type,
                        "region": offer.region,
                        "reason": msg,
                    })
                    continue
                warm = bool(warm_map.get(offer.provider, offer.provider == "modal"))
                cost = adapter.estimate_cost(workload, offer, warm_weights=warm, now=cur)
                if not workload.measure_only and cost.setup_share > self.setup_share_max + 1e-9:
                    rejected.append({
                        "provider": offer.provider,
                        "gpu": offer.gpu_type,
                        "region": offer.region,
                        "reason": f"RP-09: setup_share {cost.setup_share:.0%} > {self.setup_share_max:.0%}",
                    })
                    continue
                accepted.append((offer, cost))
            except ProviderError as exc:
                rejected.append({
                    "provider": offer.provider,
                    "gpu": offer.gpu_type,
                    "region": offer.region,
                    "reason": str(exc),
                })

        if not accepted:
            return {
                "status": "no_safe_option",
                "workload_id": workload.workload_id,
                "candidates": [],
                "rejected": rejected,
            }

        def _sort_key(item: tuple[GpuCapacityOffer, CostBreakdown]) -> tuple[float, int, float, float]:
            off, cst = item
            primary_usd = cst.net_after_credits_usd if use_net_credits else cst.expected_total_usd
            return (
                round(primary_usd, 3),
                TIER_RANK.get(off.availability_tier, 9),
                -round(off.reliability_score, 3),
                round(cst.expected_total_usd, 3),
            )

        accepted.sort(key=_sort_key)
        ranked: list[RankedCandidate] = []
        for idx, (off, cst) in enumerate(accepted, 1):
            ranked.append(
                RankedCandidate(
                    rank=idx,
                    offer=off,
                    cost=cst,
                    reason=(
                        f"{off.provider} {off.gpu_type} ({off.region}): expected ${cst.expected_total_usd:.2f} "
                        f"(net ${cst.net_after_credits_usd:.2f}), "
                        f"work={cst.work_minutes}m + setup={cst.setup_minutes}m, "
                        f"stock={off.availability_tier}, reliability={off.reliability_score:.3f}"
                    ),
                )
            )
        return {
            "status": "ok",
            "workload_id": workload.workload_id,
            "candidates": ranked,
            "rejected": rejected,
        }
