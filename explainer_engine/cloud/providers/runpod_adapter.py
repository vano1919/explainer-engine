"""Thin read-only adapter wrapping ``explainer_engine.cloud.runpod`` for unified comparison.

Does NOT modify ``explainer_engine/cloud/runpod.py`` or ``config/spend_caps.json``.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from explainer_engine.cloud import runpod as R
from explainer_engine.cloud.providers.base import (
    CostBreakdown,
    GpuCapacityOffer,
    InsufficientVramError,
    JobStatusView,
    PriceLookupError,
    ProviderError,
    StaleStockError,
    UnsupportedGpuError,
    WorkloadSpec,
)

RUNPOD_STATE_MAP: dict[str, str] = {
    "PROVISIONING": "PROVISIONING",
    "STARTING": "STARTING",
    "RUNNING": "RUNNING",
    "EXITED": "COMPLETED",
    "TERMINATED": "CANCELLED",
    "ERROR": "FAILED",
}


class RunPodProviderAdapter:
    """Adapter around ``explainer_engine.cloud.runpod.Api`` for cross-provider ranking."""

    provider_name = "runpod"

    def __init__(
        self,
        api: R.Api | None = None,
        *,
        clock: Callable[[], float] = time.time,
        max_stock_age_s: float = 120.0,
    ) -> None:
        self.api = api
        self.clock = clock
        self.max_stock_age_s = max_stock_age_s

    def list_gpu_capacity(
        self,
        *,
        clouds: tuple[str, ...] = ("COMMUNITY", "SECURE"),
        fetched_at: float | None = None,
    ) -> list[GpuCapacityOffer]:
        ts = self.clock() if fetched_at is None else fetched_at
        if self.api is None:
            return []
        offers: list[GpuCapacityOffer] = []
        for cloud in clouds:
            for g in self.api.catalog(cloud):
                gid = str(g.get("id") or "")
                if not gid or "MIG" in gid:
                    continue
                price = float(((g.get("price") or {}).get(cloud.lower())) or 0.0)
                avail = str(g.get("availability") or "NONE").upper()
                offers.append(
                    GpuCapacityOffer(
                        provider="runpod",
                        gpu_type=gid,
                        flavor_name=f"runpod-{cloud.lower()}-{gid}",
                        region=cloud,
                        vram_gb=int(g.get("memory") or 0),
                        cpu_cores=16,
                        ram_gb=64,
                        root_disk_gb=R.CONTAINER_GB,
                        ephemeral_disk_gb=R.VOLUME_GB,
                        gpu_count=1,
                        available=avail in R.AVAIL_RANK,
                        availability_tier=avail if avail in R.AVAIL_RANK else "NONE",
                        fetched_at=ts,
                        price_per_hour_usd=price if price > 0 else None,
                        supports_hibernation=True,
                        reliability_score=0.99 if cloud == "SECURE" else 0.96,
                    )
                )
        return offers

    def can_run(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        now: float | None = None,
    ) -> tuple[bool, str]:
        if offer.is_stale(now=now, max_age_s=self.max_stock_age_s):
            raise StaleStockError(f"RunPod stock data for {offer.gpu_type} is stale")
        sp = R.speeds()
        if offer.gpu_type not in sp and offer.vram_gb <= 0:
            raise UnsupportedGpuError(f"Unsupported RunPod GPU: {offer.gpu_type}")
        if offer.vram_gb < workload.min_vram_gb:
            raise InsufficientVramError(
                f"RunPod {offer.gpu_type} ({offer.vram_gb} GB) < required {workload.min_vram_gb} GB"
            )
        if offer.price_per_hour_usd is None or offer.price_per_hour_usd <= 0:
            raise PriceLookupError(f"Missing RunPod price for {offer.gpu_type}")
        if not offer.available:
            return False, f"RunPod {offer.gpu_type} ({offer.region}) has availability={offer.availability_tier}"
        return True, "compatible"

    def estimate_cost(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        warm_weights: bool = False,
        now: float | None = None,
    ) -> CostBreakdown:
        ok, reason = self.can_run(workload, offer, now=now)
        if not ok and "availability=" not in reason:
            raise ProviderError(reason)
        assert offer.price_per_hour_usd is not None
        sp = R.speeds()
        speed = sp.get(offer.gpu_type, min(sp.values()) / 2.0)
        work_min = workload.ref_a100_work_minutes / speed
        setup_min = workload.setup_minutes_warm if warm_weights else workload.setup_minutes_cold
        total_hours = (work_min + setup_min) / 60.0
        disk_hr = (offer.root_disk_gb + offer.ephemeral_disk_gb) * R.GB_MONTH_RUNNING / R.HOURS_PER_MONTH
        compute_usd = round(total_hours * (offer.price_per_hour_usd + disk_hr), 4)
        stopped_day_usd = round(offer.ephemeral_disk_gb * R.GB_MONTH_STOPPED / R.HOURS_PER_MONTH * 24.0, 4)
        setup_share = round(setup_min / max(1e-6, work_min + setup_min), 4)
        return CostBreakdown(
            provider="runpod",
            gpu_type=offer.gpu_type,
            flavor_name=offer.flavor_name,
            region=offer.region,
            work_minutes=round(work_min, 2),
            setup_minutes=round(setup_min, 2),
            scaledown_minutes=0.0,
            total_billable_hours=round(total_hours, 4),
            gpu_Hourly_usd=offer.price_per_hour_usd,
            cpu_ram_hourly_usd=0.0,
            active_disk_ip_hourly_usd=round(disk_hr, 4),
            compute_usd=compute_usd,
            egress_usd=0.0,
            idle_storage_per_day_usd=stopped_day_usd,
            expected_total_usd=compute_usd,
            conservative_retry_total_usd=round(compute_usd * 1.25, 4),
            net_after_credits_usd=compute_usd,
            setup_share=setup_share,
            assumptions=(
                f"Active disk ({offer.root_disk_gb + offer.ephemeral_disk_gb} GB) "
                f"billed at ${R.GB_MONTH_RUNNING}/GB/mo",
                f"Stopped pod volume ({offer.ephemeral_disk_gb} GB) bills ${stopped_day_usd:.2f}/day until deleted",
            ),
        )

    def normalize_status(self, pod_payload: dict[str, Any]) -> JobStatusView:
        flat = R.norm(pod_payload) or {}
        st = str(flat.get("status") or "UNKNOWN").upper()
        norm = RUNPOD_STATE_MAP.get(st, "UNKNOWN")
        billing = st in ("PROVISIONING", "STARTING", "RUNNING")
        idle_day = round(R.disk_per_hour(flat, running=False) * 24.0, 4) if st in ("EXITED", "ERROR") else 0.0
        return JobStatusView(
            provider="runpod",
            resource_id=str(flat.get("id", "")),
            name=str(flat.get("name", "")),
            provider_state=st,
            normalized_state=norm,
            billing_active=billing,
            hourly_rate_usd=float(flat.get("costPerHr") or 0.0) if billing else 0.0,
            idle_disk_per_day_usd=idle_day,
        )
