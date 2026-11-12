"""Hyperstack GPU VM read-only inventory/pricebook client and safe dry-run adapter.

Implements verified Hyperstack Infrahub REST API v1 (`https://infrahub-api.nexgencloud.com/v1`)
and guards against the SHUTOFF billing trap (where `SHUTOFF` bills 100% of the GPU rate,
requiring `HIBERNATE` or `DELETE` instead).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request

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
    RateLimitError,
    RegionMismatchError,
    StaleStockError,
    UnclearProvisionError,
    UnsupportedGpuError,
    WorkloadSpec,
)

BASE_URL = "https://infrahub-api.nexgencloud.com/v1"
PUBLIC_IP_HOURLY_USD = 0.00672
HIBERNATED_DISK_GB_HOURLY_USD = 0.000096774  # ~$0.07/GB/month

# Relative speed vs A100-80GB PCIe (1.0) and VRAM table for Hyperstack GPU models
HYPERSTACK_GPU_SPECS: dict[str, dict[str, float]] = {
    "A100-80G-PCIe": {"vram_gb": 80, "speed": 1.00},
    "A100-80G-SXM4": {"vram_gb": 80, "speed": 1.08},
    "H100-80G-PCIe": {"vram_gb": 80, "speed": 1.65},
    "H100-80G-PCIe-NVLink": {"vram_gb": 94, "speed": 1.80},
    "H100-80G-SXM5": {"vram_gb": 80, "speed": 2.00},
    "H200-141G-SXM5": {"vram_gb": 141, "speed": 2.15},
    "B200-SXM": {"vram_gb": 180, "speed": 2.80},
    "B300-SXM": {"vram_gb": 288, "speed": 3.10},
    "RTX-PRO6000-SE": {"vram_gb": 96, "speed": 1.35},
    "L40": {"vram_gb": 48, "speed": 0.78},
    "RTX-A6000": {"vram_gb": 48, "speed": 0.55},
    "RTX-A4000": {"vram_gb": 16, "speed": 0.28},
}

# Verified list prices from Hyperstack / ComputePrices (2026-10-28 / 2026-11-06) used as fallback only when offline
VERIFIED_LIST_PRICES_USD: dict[str, float] = {
    "A100-80G-PCIe": 1.35,
    "A100-80G-SXM4": 1.60,
    "H100-80G-PCIe": 2.50,
    "H100-80G-PCIe-NVLink": 2.60,
    "H100-80G-SXM5": 3.20,
    "H200-141G-SXM5": 3.99,
    "B200-SXM": 6.00,
    "B300-SXM": 7.40,
    "RTX-PRO6000-SE": 1.85,
    "L40": 1.00,
    "RTX-A6000": 0.50,
    "RTX-A4000": 0.15,
}

STATE_MAP: dict[str, str] = {
    "CREATING": "PENDING",
    "BUILD": "PROVISIONING",
    "STARTING": "STARTING",
    "RESTORING": "STARTING",
    "ACTIVE": "RUNNING",
    "STOPPING": "STOPPING",
    "HIBERNATING": "STOPPING",
    "DELETING": "STOPPING",
    "HIBERNATED": "COMPLETED",
    "DELETED": "CANCELLED",
    "SHUTOFF": "FAILED",  # Trap: SHUTOFF keeps billing 100% GPU rate! Flagged as FAILED + warning
    "ERROR": "FAILED",
}


def _default_transport(
    method: str, url: str, body: bytes | None, headers: dict[str, str], timeout: int
) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers or {})


class HyperstackAdapter:
    """Read-only inventory/pricebook client and safe dry-run adapter for Hyperstack GPU VMs."""

    provider_name = "hyperstack"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        transport: Callable[..., tuple[int, str, dict[str, str]]] = _default_transport,
        clock: Callable[[], float] = time.time,
        max_stock_age_s: float = 120.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("HYPERSTACK_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.clock = clock
        self.max_stock_age_s = max_stock_age_s
        self._submitted_keys: dict[str, str] = {}
        self._known_vms: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise AuthenticationError("Hyperstack api_key is not set (set HYPERSTACK_API_KEY for read-only calls)")
        return {"Accept": "application/json", "Content-Type": "application/json", "api_key": self._api_key}

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        headers = self._headers()
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        try:
            status, text, resp_headers = self.transport(method, f"{self.base_url}{path}", data, headers, 30)
        except OSError as exc:
            raise UnclearProvisionError(
                f"Hyperstack {method} {path} network timeout/error: {exc}", secrets=(self._api_key,)
            ) from exc

        if status in (401, 403):
            raise AuthenticationError(
                f"Hyperstack authentication failed ({status}) on {path}: {text[:120]}",
                status=status,
                secrets=(self._api_key,),
            )
        if status == 429:
            retry_after = int(float((resp_headers or {}).get("Retry-After", "30")))
            raise RateLimitError(f"Hyperstack rate limit (429) on {path}", retry_after_s=retry_after)
        if status >= 500:
            raise UnclearProvisionError(
                f"Hyperstack server error ({status}) on {path}: {text[:120]}",
                status=status,
                secrets=(self._api_key,),
            )
        if status >= 400:
            raise ProviderError(
                f"Hyperstack HTTP {status} on {path}: {text[:200]}",
                status=status,
                secrets=(self._api_key,),
            )
        return json.loads(text) if text.strip() else {}

    def fetch_pricebook(self) -> dict[str, float]:
        """Call ``GET /pricebook`` (bare JSON array) and return ``{resource_name: hourly_rate_usd}``."""
        raw = self._request("GET", "/pricebook")
        if not isinstance(raw, list):
            raise PriceLookupError("Hyperstack /pricebook did not return a JSON list")
        prices: dict[str, float] = {}
        for row in raw:
            if isinstance(row, dict) and row.get("name") and row.get("value") is not None:
                prices[str(row["name"])] = float(row["value"])
        return prices

    def list_gpu_capacity(
        self,
        *,
        regions: tuple[str, ...] | None = None,
        gpu_types: tuple[str, ...] | None = None,
        pricebook: dict[str, float] | None = None,
        fetched_at: float | None = None,
    ) -> list[GpuCapacityOffer]:
        """Call ``GET /core/flavors`` and combine with ``/pricebook`` to return normalized offers."""
        ts = self.clock() if fetched_at is None else fetched_at
        prices = pricebook if pricebook is not None else self.fetch_pricebook()
        resp = self._request("GET", "/core/flavors")
        groups = resp.get("data", []) if isinstance(resp, dict) else []
        offers: list[GpuCapacityOffer] = []
        for grp in groups:
            for flv in grp.get("flavors", []):
                gpu = str(flv.get("gpu") or grp.get("gpu") or "")
                gpu_count = int(flv.get("gpu_count") or 0)
                if not gpu or gpu_count <= 0:
                    continue
                region = str(flv.get("region_name") or grp.get("region_name") or "")
                if regions and region not in regions:
                    continue
                if gpu_types and gpu not in gpu_types:
                    continue
                spec = HYPERSTACK_GPU_SPECS.get(gpu)
                vram_gb = int(spec["vram_gb"]) if spec else 0
                unit_price = prices.get(gpu)
                total_price = round(unit_price * gpu_count, 4) if unit_price is not None else None
                in_stock = bool(flv.get("stock_available", False))
                features = flv.get("features") or {}
                offers.append(
                    GpuCapacityOffer(
                        provider="hyperstack",
                        gpu_type=gpu,
                        flavor_name=str(flv.get("name", "")),
                        region=region,
                        vram_gb=vram_gb,
                        cpu_cores=int(flv.get("cpu") or 0),
                        ram_gb=int(flv.get("ram") or 0),
                        root_disk_gb=int(flv.get("disk") or 0),
                        ephemeral_disk_gb=int(flv.get("ephemeral") or 0),
                        gpu_count=gpu_count,
                        available=in_stock,
                        availability_tier="HIGH" if in_stock else "NONE",
                        fetched_at=ts,
                        price_per_hour_usd=total_price,
                        supports_hibernation=not bool(features.get("no_hibernation", False)),
                        reliability_score=0.99,
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
        """Validate whether ``offer`` can safely execute ``workload``."""
        if offer.is_stale(now=now, max_age_s=self.max_stock_age_s):
            raise StaleStockError(f"Stock data for {offer.flavor_name} is stale (> {self.max_stock_age_s}s)")
        if offer.gpu_type not in HYPERSTACK_GPU_SPECS or offer.vram_gb <= 0:
            raise UnsupportedGpuError(f"Unsupported GPU model on Hyperstack: {offer.gpu_type}")
        if offer.vram_gb < workload.min_vram_gb:
            raise InsufficientVramError(
                f"{offer.gpu_type} has {offer.vram_gb} GB VRAM, below workload minimum {workload.min_vram_gb} GB"
            )
        allowed_reg = workload.allowed_regions or PROPOSED_PROVIDER_CAPS["hyperstack"]["allowed_regions"]
        if allowed_reg and offer.region not in allowed_reg:
            raise RegionMismatchError(f"Region {offer.region} not in allowed regions {allowed_reg}")
        if offer.price_per_hour_usd is None or offer.price_per_hour_usd <= 0:
            raise PriceLookupError(f"Missing valid pricebook rate for {offer.gpu_type} ({offer.flavor_name})")
        if offer.total_disk_gb < workload.min_disk_gb:
            return False, f"total disk {offer.total_disk_gb} GB < required {workload.min_disk_gb} GB"
        if not offer.available:
            return False, f"{offer.flavor_name} in {offer.region} is currently out of stock"
        return True, "compatible"

    def estimate_cost(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        warm_weights: bool = False,
        now: float | None = None,
    ) -> CostBreakdown:
        """Compute transparent total cost for ``workload`` on ``offer``."""
        ok, reason = self.can_run(workload, offer, now=now)
        if not ok and "out of stock" not in reason:
            raise ProviderError(f"Incompatible offer {offer.flavor_name}: {reason}")
        assert offer.price_per_hour_usd is not None
        speed = HYPERSTACK_GPU_SPECS[offer.gpu_type]["speed"] * offer.gpu_count
        work_min = workload.ref_a100_work_minutes / speed
        setup_min = workload.setup_minutes_warm if warm_weights else workload.setup_minutes_cold
        scaledown_min = 0.5  # immediate DELETE or HIBERNATE via API
        total_hours = (work_min + setup_min + scaledown_min) / 60.0
        hourly_all_in = offer.price_per_hour_usd + PUBLIC_IP_HOURLY_USD
        compute_usd = round(total_hours * hourly_all_in, 4)
        conservative_usd = round(compute_usd * 1.25, 4)
        idle_day_usd = round(offer.root_disk_gb * HIBERNATED_DISK_GB_HOURLY_USD * 24.0, 4)
        setup_share = round(setup_min / max(1e-6, work_min + setup_min), 4)

        cap_usd = workload.max_budget_usd or float(PROPOSED_PROVIDER_CAPS["hyperstack"]["per_vm_usd"])
        if compute_usd > cap_usd:
            raise BudgetExceededError(
                f"Estimated Hyperstack cost ${compute_usd:.2f} exceeds proposed cap ${cap_usd:.2f}"
            )

        return CostBreakdown(
            provider="hyperstack",
            gpu_type=offer.gpu_type,
            flavor_name=offer.flavor_name,
            region=offer.region,
            work_minutes=round(work_min, 2),
            setup_minutes=round(setup_min, 2),
            scaledown_minutes=scaledown_min,
            total_billable_hours=round(total_hours, 4),
            gpu_Hourly_usd=offer.price_per_hour_usd,
            cpu_ram_hourly_usd=0.0,
            active_disk_ip_hourly_usd=PUBLIC_IP_HOURLY_USD,
            compute_usd=compute_usd,
            egress_usd=0.0,
            idle_storage_per_day_usd=idle_day_usd,
            expected_total_usd=compute_usd,
            conservative_retry_total_usd=conservative_usd,
            net_after_credits_usd=compute_usd,
            setup_share=setup_share,
            assumptions=(
                "CPU, RAM, root disk, and local NVMe ephemeral disk are $0 on GPU flavors",
                f"Public IP billed at ${PUBLIC_IP_HOURLY_USD}/hr while ACTIVE",
                "VM is DELETED (or HIBERNATED) immediately on completion; SHUTOFF is never used",
            ),
        )

    def normalize_status(self, vm_payload: dict[str, Any]) -> JobStatusView:
        """Normalize a Hyperstack VM payload into ``JobStatusView``, flagging the ``SHUTOFF`` billing trap."""
        raw_status = str(vm_payload.get("status") or "UNKNOWN").upper()
        norm = STATE_MAP.get(raw_status, "UNKNOWN")
        flv = vm_payload.get("flavor") or {}
        gpu = str(flv.get("gpu") or "")
        gpu_count = int(flv.get("gpu_count") or 1)
        root_gb = int(flv.get("disk") or 100)
        gpu_rate = VERIFIED_LIST_PRICES_USD.get(gpu, 0.0) * gpu_count

        # Critical Hyperstack rule: both ACTIVE and SHUTOFF bill the full GPU rate!
        billing_active = raw_status in ("ACTIVE", "SHUTOFF")
        warning = ""
        if raw_status == "SHUTOFF":
            warning = (
                "CRITICAL BILLING TRAP: Hyperstack VM is in SHUTOFF state, which continues billing "
                f"100% of GPU rate (${gpu_rate:.2f}/hr)! Must HIBERNATE or DELETE immediately."
            )
        idle_disk_day = round(root_gb * HIBERNATED_DISK_GB_HOURLY_USD * 24.0, 4) if raw_status == "HIBERNATED" else 0.0
        return JobStatusView(
            provider="hyperstack",
            resource_id=str(vm_payload.get("id", "")),
            name=str(vm_payload.get("name", "")),
            provider_state=raw_status,
            normalized_state=norm,
            billing_active=billing_active,
            hourly_rate_usd=round(gpu_rate + PUBLIC_IP_HOURLY_USD, 4) if billing_active else 0.0,
            idle_disk_per_day_usd=idle_disk_day,
            billing_trap_warning=warning,
            metadata={"region": (vm_payload.get("environment") or {}).get("region"), "flavor": flv.get("name")},
        )

    def reconcile_existing(self, vm_name: str) -> dict[str, Any] | None:
        """Look up an existing VM by name before retrying any failed/timed-out create request."""
        resp = self._request("GET", "/core/virtual-machines")
        instances = resp.get("instances", []) if isinstance(resp, dict) else []
        for inst in instances:
            if isinstance(inst, dict) and inst.get("name") == vm_name:
                return inst
        return None

    def submit_job(
        self,
        workload: WorkloadSpec,
        offer: GpuCapacityOffer,
        *,
        vm_name: str,
        idempotency_key: str,
        dry_run: bool = True,
        approval: ApprovalGate | None = None,
    ) -> dict[str, Any]:
        """Validate compatibility and budget; execute dry-run by default or require full OR-22..34 approval."""
        cost = self.estimate_cost(workload, offer, now=self.clock())
        if idempotency_key in self._submitted_keys:
            raise DuplicateRequestError(
                f"Duplicate idempotency_key {idempotency_key!r} "
                f"(already mapped to {self._submitted_keys[idempotency_key]})"
            )
        if dry_run:
            return {
                "mode": "dry_run",
                "provider": "hyperstack",
                "vm_name": vm_name,
                "flavor_name": offer.flavor_name,
                "region": offer.region,
                "estimated_cost_usd": cost.expected_total_usd,
                "idempotency_key": idempotency_key,
                "termination_policy": "DELETE_OR_HIBERNATE_NEVER_SHUTOFF",
            }
        if approval is None:
            raise ApprovalRequiredError("Live Hyperstack VM creation requires an explicit ApprovalGate")
        approval.validate("hyperstack")

        # Reconcile first so a previous timeout never creates a duplicate VM (CR-12)
        existing = self.reconcile_existing(vm_name)
        if existing is not None:
            rid = str(existing["id"])
            self._submitted_keys[idempotency_key] = rid
            return {"mode": "adopted", "provider": "hyperstack", "resource_id": rid, "vm_name": vm_name}

        payload = {
            "name": vm_name[:50],
            "environment_name": f"default-{offer.region}",
            "flavor_name": offer.flavor_name,
            "image_name": "Ubuntu Server 24.04 LTS R535 CUDA 12.4 with Docker",
            "key_name": "explainer-engine-key",
            "count": 1,
            "assign_floating_ip": True,
        }
        try:
            resp = self._request("POST", "/core/virtual-machines", payload)
        except UnclearProvisionError:
            # Never blindly retry POST; check if the VM appeared on the account
            adopted = self.reconcile_existing(vm_name)
            if adopted is not None:
                rid = str(adopted["id"])
                self._submitted_keys[idempotency_key] = rid
                return {
                    "mode": "adopted_after_timeout", "provider": "hyperstack",
                    "resource_id": rid, "vm_name": vm_name,
                }
            raise

        inst = (resp.get("instances") or [{}])[0]
        rid = str(inst.get("id", ""))
        self._submitted_keys[idempotency_key] = rid
        return {"mode": "created", "provider": "hyperstack", "resource_id": rid, "vm_name": vm_name}

    def cancel_job(self, vm_id: str, *, mode: str = "delete") -> JobStatusView:
        """Stop billing safely via ``DELETE`` or ``HIBERNATE`` (refuses ``stop`` / ``SHUTOFF``)."""
        if mode.lower() == "stop":
            raise ProviderError(
                "Refusing Hyperstack 'stop' (SHUTOFF continues billing 100% GPU rate); use mode='hibernate' or 'delete'"
            )
        if mode.lower() == "hibernate":
            self._request("GET", f"/core/virtual-machines/{vm_id}/hibernate")
            return self.normalize_status({"id": vm_id, "status": "HIBERNATING"})
        self._request("DELETE", f"/core/virtual-machines/{vm_id}")
        return self.normalize_status({"id": vm_id, "status": "DELETED"})
