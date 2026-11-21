"""Read-only CLI for inspecting provider capacity, estimating workload costs, and dry-run ranking.

Usage:
    python -m explainer_engine.cloud.providers estimate [--workload workload_c_combined_p12_p14]
"""

from __future__ import annotations

import json
import sys
import time

from explainer_engine.cloud.providers.base import GpuCapacityOffer, WORKLOAD_PRESETS
from explainer_engine.cloud.providers.hyperstack import HyperstackAdapter, VERIFIED_LIST_PRICES_USD
from explainer_engine.cloud.providers.modal_provider import ModalAdapter
from explainer_engine.cloud.providers.selector import ProviderSelector


def offline_reference_offers(now: float | None = None) -> list[GpuCapacityOffer]:
    """Return offline reference offers from verified 2026-11-06 price tables for dry-run comparison."""
    ts = time.time() if now is None else now
    hs = [
        GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=ts,
            price_per_hour_usd=VERIFIED_LIST_PRICES_USD["A100-80G-PCIe"],
        ),
        GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="H100-80G-PCIe",
            flavor_name="n3-H100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=180,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=ts,
            price_per_hour_usd=VERIFIED_LIST_PRICES_USD["H100-80G-PCIe"],
        ),
        GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="L40",
            flavor_name="n3-L40x1",
            region="CANADA-1",
            vram_gb=48,
            cpu_cores=28,
            ram_gb=58,
            root_disk_gb=100,
            ephemeral_disk_gb=725,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=ts,
            price_per_hour_usd=VERIFIED_LIST_PRICES_USD["L40"],
        ),
    ]
    modal_adapter = ModalAdapter()
    md = modal_adapter.list_gpu_capacity(gpu_types=("A100-80GB", "H100", "L40S"), fetched_at=ts)
    return hs + md


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    w_key = "workload_c_combined_p12_p14"
    if "--workload" in args:
        idx = args.index("--workload")
        if idx + 1 < len(args):
            w_key = args[idx + 1]
    workload = WORKLOAD_PRESETS.get(w_key, WORKLOAD_PRESETS["workload_c_combined_p12_p14"])
    now = time.time()
    adapters = {
        "hyperstack": HyperstackAdapter(api_key="offline-dry-run"),
        "modal": ModalAdapter(token_id="offline", token_secret="offline"),
    }
    selector = ProviderSelector(adapters)
    res = selector.select(workload, offline_reference_offers(now=now), now=now)
    summary = {
        "status": res["status"],
        "workload_id": res["workload_id"],
        "candidates": [
            {
                "rank": c.rank,
                "provider": c.offer.provider,
                "gpu_type": c.offer.gpu_type,
                "flavor_name": c.offer.flavor_name,
                "region": c.offer.region,
                "expected_total_usd": c.cost.expected_total_usd,
                "net_after_credits_usd": c.cost.net_after_credits_usd,
                "reason": c.reason,
            }
            for c in res["candidates"]
        ],
        "rejected": res["rejected"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
