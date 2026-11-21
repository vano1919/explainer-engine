"""Modal serverless GPU capacity, cost estimator, and dry-run adapter.

Implements verified Modal per-second GPU/CPU/Memory pricing (2026-11-06), Starter plan
$30/month free compute credit accounting, 1 TiB free Volume storage, preemption rules,
and ordered multi-GPU fallback (`gpu=["A100-80GB", "H100", "RTX-PRO-6000"]`).
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from explainer_engine.cloud.providers.base import (
    ApprovalGate,
    ApprovalRequiredError,
    AuthenticationError,
    BudgetExceededError,
    CostBreakdown,
    DuplicateRequestError,
    GpuCapacityOffer,
    InsufficientVramError,
    JobStatusView,
    PROPOSED_PROVIDER_CAPS,
    PriceLookupError,
    ProviderError,
    RegionMismatchError,
    StaleStockError,
    UnsupportedGpuError,
    WorkloadSpec,
)

# Verified per-second rates from https://modal.com/pricing (accessed 2026-11-06)
CPU_CORE_PER_SEC_USD = 0.0000131      # $0.04716 / physical core / hr
MEMORY_GIB_PER_SEC_USD = 0.00000222   # $0.007992 / GiB / hr
VOLUME_GIB_MONTH_USD = 0.09           # First 1 TiB / mo is free on Starter
EGRESS_GIB_USD = 0.04                 # First 1 TiB / mo is free on Starter
STARTER_FREE_CREDIT_USD = 30.00

MODAL_GPU_CATALOG: dict[str, dict[str, float]] = {
    "B300": {"vram_gb": 288, "per_sec_usd": 0.001972, "speed": 3.10},
    "B200": {"vram_gb": 180, "per_sec_usd": 0.001736, "speed": 2.80},
    "H200": {"vram_gb": 141, "per_sec_usd": 0.001261, "speed": 2.15},
    "H100": {"vram_gb": 80, "per_sec_usd": 0.001097, "speed": 2.00},
    "RTX-PRO-6000": {"vram_gb": 96, "per_sec_usd": 0.000842, "speed": 1.35},
    "A100-80GB": {"vram_gb": 80, "per_sec_usd": 0.000694, "speed": 1.05},
    "A100-40GB": {"vram_gb": 40, "per_sec_usd": 0.000583, "speed": 0.90},
    "L40S": {"vram_gb": 48, "per_sec_usd": 0.000542, "speed": 0.90},
    "A10": {"vram_gb": 24, "per_sec_usd": 0.000306, "speed": 0.45},
    "L4": {"vram_gb": 24, "per_sec_usd": 0.000222, "speed": 0.35},
    "T4": {"vram_gb": 16, "per_sec_usd": 0.000164, "speed": 0.20},
}

MODAL_STATE_MAP: dict[str, str] = {
    "PENDING": "PENDING",
    "QUEUED": "PENDING",
    "INITIALIZING": "PROVISIONING",
    "IMAGE_BUILDING": "PROVISIONING",
    "LOADING": "STARTING",
    "RUNNING": "RUNNING",
    "DRAINING": "STOPPING",
    "SUCCESS": "COMPLETED",
    "COMPLETED": "COMPLETED",
    "FAILURE": "FAILED",
    "TIMEOUT": "FAILED",
    "PREEMPTED": "FAILED",
    "CANCELLED": "CANCELLED",
}


class ModalAdapter:
    """Serverless GPU capacity, cost model, and dry-run adapter for Modal."""

    provider_name = "modal"

    def __init__(
        self,
        token_id: str | None = None,
        token_secret: str | None = None,
        *,
        clock: Callable[[], float] = time.time,
        remaining_free_credit_usd: float = STARTER_FREE_CREDIT_USD,
        max_stock_age_s: float = 120.0,
    ) -> None:
        self._token_id = token_id if token_id is not None else os.environ.get("MODAL_TOKEN_ID", "")
        self._token_secret = token_secret if token_secret is not None else os.environ.get("MODAL_TOKEN_SECRET", "")
        self.clock = clock
        self.remaining_free_credit_usd = remaining_free_credit_usd
        self.max_stock_age_s = max_stock_age_s
        self._submitted_keys: dict[str, str] = {}

    def verify_credentials(self) -> None:
        if not self._token_id or not self._token_secret:
            raise AuthenticationError(
                "Modal credentials missing (set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET)",
                secrets=(self._token_id, self._token_secret),
            )

    def list_gpu_capacity(
        self,
        *,
        regions: tuple[str, ...] | None = None,
        gpu_types: tuple[str, ...] | None = None,
        fetched_at: float | None = None,
        cpu_cores: int = 8,
        ram_gb: int = 64,
    ) -> list[GpuCapacityOffer]:
        """Return Modal's serverless GPU catalog offers with per-second rates converted to hourly."""
        ts = self.clock() if fetched_at is None else fetched_at
        if gpu_types:
            unknown = [g for g in gpu_types if g not in MODAL_GPU_CATALOG]
            if unknown:
                raise UnsupportedGpuError(f"Unsupported Modal GPU type(s): {unknown}")
        target_regions = regions or ("any",)
        offers: list[GpuCapacityOffer] = []
        for gpu, spec in MODAL_GPU_CATALOG.items():
            if gpu_types and gpu not in gpu_types:
                continue
            gpu_hr = round(spec["per_sec_usd"] * 3600.0, 4)
            for reg in target_regions:
                offers.append(
                    GpuCapacityOffer(
                        provider="modal",
                        gpu_type=gpu,
                        flavor_name=f"modal-{gpu.lower()}-{cpu_cores}c-{ram_gb}g",
                        region=reg,
                        vram_gb=int(spec["vram_gb"]),
                        cpu_cores=cpu_cores,
                        ram_gb=ram_gb,
                        root_disk_gb=512,
                        ephemeral_disk_gb=512,  # 1 TiB free Volume
                        gpu_count=1,
                        available=True,
                        availability_tier="HIGH",
                        fetched_at=ts,
                        price_per_hour_usd=gpu_hr,
                        supports_hibernation=True,
                        reliability_score=0.995,
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
            raise StaleStockError(f"Modal catalog snapshot for {offer.gpu_type} is stale")
        if offer.gpu_type not in MODAL_GPU_CATALOG:
            raise UnsupportedGpuError(f"Unsupported Modal GPU type: {offer.gpu_type}")
        if offer.vram_gb < workload.min_vram_gb:
            raise InsufficientVramError(
                f"Modal {offer.gpu_type} ({offer.vram_gb} GB) < required {workload.min_vram_gb} GB"
            )
        allowed_reg = workload.allowed_regions or PROPOSED_PROVIDER_CAPS["modal"]["allowed_regions"]
        if allowed_reg and offer.region not in allowed_reg:
            raise RegionMismatchError(f"Region {offer.region} not in allowed Modal regions {allowed_reg}")
        if offer.price_per_hour_usd is None or offer.price_per_hour_usd <= 0:
            raise PriceLookupError(f"Missing price for Modal {offer.gpu_type}")
        if not offer.available:
            return False, f"Modal {offer.gpu_type} unavailable"
        return True, "compatible"

    def estimate_cost(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        warm_weights: bool = True,
        non_preemptible: bool = False,
        region_multiplier: float = 1.0,
        scaledown_window_s: float = 10.0,
        now: float | None = None,
    ) -> CostBreakdown:
        """Compute total Modal Function/Sandbox cost including separate CPU and Memory charges."""
        ok, reason = self.can_run(workload, offer, now=now)
        if not ok:
            raise ProviderError(f"Incompatible Modal offer: {reason}")
        spec = MODAL_GPU_CATALOG[offer.gpu_type]
        speed = spec["speed"]
        work_min = workload.ref_a100_work_minutes / speed
        setup_min = workload.setup_minutes_warm if warm_weights else workload.setup_minutes_cold
        scaledown_min = scaledown_window_s / 60.0
        total_hours = (work_min + setup_min + scaledown_min) / 60.0

        mult = (3.0 if non_preemptible else 1.0) * float(region_multiplier)
        gpu_hr = round(spec["per_sec_usd"] * 3600.0 * mult, 4)
        cpu_ram_hr = round(
            (offer.cpu_cores * CPU_CORE_PER_SEC_USD + offer.ram_gb * MEMORY_GIB_PER_SEC_USD) * 3600.0 * mult,
            4,
        )
        compute_usd = round(total_hours * (gpu_hr + cpu_ram_hr), 4)
        conservative_usd = round(compute_usd * 1.15, 4)
        net_usd = round(max(0.0, compute_usd - self.remaining_free_credit_usd), 4)
        setup_share = round(setup_min / max(1e-6, work_min + setup_min), 4)

        cap_usd = workload.max_budget_usd or float(PROPOSED_PROVIDER_CAPS["modal"]["per_run_usd"])
        if compute_usd > cap_usd:
            raise BudgetExceededError(
                f"Estimated Modal gross cost ${compute_usd:.2f} exceeds proposed run cap ${cap_usd:.2f}"
            )

        return CostBreakdown(
            provider="modal",
            gpu_type=offer.gpu_type,
            flavor_name=offer.flavor_name,
            region=offer.region,
            work_minutes=round(work_min, 2),
            setup_minutes=round(setup_min, 2),
            scaledown_minutes=round(scaledown_min, 2),
            total_billable_hours=round(total_hours, 4),
            gpu_Hourly_usd=gpu_hr,
            cpu_ram_hourly_usd=cpu_ram_hr,
            active_disk_ip_hourly_usd=0.0,
            compute_usd=compute_usd,
            egress_usd=0.0,
            idle_storage_per_day_usd=0.0,  # 1 TiB Volume free on Starter
            expected_total_usd=compute_usd,
            conservative_retry_total_usd=conservative_usd,
            net_after_credits_usd=net_usd,
            setup_share=setup_share,
            assumptions=(
                f"CPU ({offer.cpu_cores} physical cores) + Memory ({offer.ram_gb} GiB) "
                f"billed separately (+${cpu_ram_hr:.2f}/hr)",
                f"Scaledown window set to {scaledown_window_s:.0f}s (scales to $0 afterwards)",
                "Weights stored in Modal Volume (first 1 TiB/month free on Starter)",
            ),
        )

    def normalize_status(self, call_payload: dict[str, Any]) -> JobStatusView:
        raw = str(call_payload.get("status") or "UNKNOWN").upper()
        norm = MODAL_STATE_MAP.get(raw, "UNKNOWN")
        gpu = str(call_payload.get("gpu") or "A100-80GB")
        spec = MODAL_GPU_CATALOG.get(gpu, MODAL_GPU_CATALOG["A100-80GB"])
        billing = norm in ("STARTING", "RUNNING", "STOPPING")
        rate = round(spec["per_sec_usd"] * 3600.0, 4) if billing else 0.0
        return JobStatusView(
            provider="modal",
            resource_id=str(call_payload.get("call_id", "")),
            name=str(call_payload.get("function_name", "")),
            provider_state=raw,
            normalized_state=norm,
            billing_active=billing,
            hourly_rate_usd=rate,
            idle_disk_per_day_usd=0.0,
            metadata={"gpu_fallbacks": call_payload.get("gpu_fallbacks", [gpu, "H100", "RTX-PRO-6000"])},
        )

    def submit_job(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        function_name: str,
        idempotency_key: str,
        dry_run: bool = True,
        approval: ApprovalGate | None = None,
    ) -> dict[str, Any]:
        """Prepare or dry-run a Modal Function invocation with multi-GPU fallback list."""
        cost = self.estimate_cost(workload, offer, now=self.clock())
        if idempotency_key in self._submitted_keys:
            raise DuplicateRequestError(f"Duplicate Modal submission for idempotency_key {idempotency_key!r}")
        fallbacks = [offer.gpu_type] + [g for g in ("A100-80GB", "H100", "RTX-PRO-6000") if g != offer.gpu_type]
        if dry_run:
            return {
                "mode": "dry_run",
                "provider": "modal",
                "function_name": function_name,
                "gpu_fallbacks": fallbacks,
                "estimated_gross_usd": cost.expected_total_usd,
                "estimated_net_usd": cost.net_after_credits_usd,
                "idempotency_key": idempotency_key,
            }
        if approval is None:
            raise ApprovalRequiredError("Live Modal execution requires an explicit ApprovalGate")
        approval.validate("modal")
        self.verify_credentials()
        call_id = f"fc-{idempotency_key[:12]}"
        self._submitted_keys[idempotency_key] = call_id
        return {
            "mode": "created",
            "provider": "modal",
            "resource_id": call_id,
            "function_name": function_name,
            "gpu_fallbacks": fallbacks,
        }

    def cancel_job(self, call_id: str) -> JobStatusView:
        return self.normalize_status({"call_id": call_id, "status": "CANCELLED"})
