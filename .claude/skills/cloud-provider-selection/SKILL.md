---
name: cloud-provider-selection
description: Deterministic, dry-run multi-provider GPU ranking across Hyperstack, Modal, and RunPod via explainer_engine/cloud/providers/selector.py. Enforces VRAM, RAM, disk, stock freshness, RP-09 setup-share, and proposed budget caps without creating live resources.
---

> **Route-scoped since D-116 (2026-11-06):** LTX and Qwen are named here only as GPU workloads of the J2/J4 routes and of the Qwen assets of J5 (D-116); provider runs stay dry-run until the creator approves caps in `config/spend_caps.json` (D-56).

# Cloud Provider Selection (`explainer_engine/cloud/providers/selector.py`)

Use this skill to rank GPU offers across Hyperstack, Modal, and RunPod for any Explainer Engine workload
(`docs/providers/PROVIDER_DECISION.md` and `docs/providers/PROVIDER_ADAPTER_DESIGN.md`).

## 1. Selection & hard-filter rules

`ProviderSelector.select` in `explainer_engine/cloud/providers/selector.py` evaluates every `GpuCapacityOffer` through five
mandatory gates before ranking:

1. **Availability & stock freshness (`<= 120s`)**: offers with `available=False` or `offer.is_stale(now, max_age_s=120.0)` are
   rejected (`StaleStockError`).
2. **VRAM, system RAM, and disk floor**: LTX-2.5 (`workload_b_ltx_30s`, `workload_c_j5_minimised_p12_p14`,
   `workload_c_combined_p12_p14`) requires `>= 80 GB` VRAM; 48 GB GPUs (`L40`, `L40S`, `RTX-A6000`) are rejected
   (`InsufficientVramError`).
3. **Allowed regions**: offers outside the workload's or provider's allowed regions are rejected (`RegionMismatchError`).
4. **Full total-cost cap (`BudgetExceededError`)**: total cost (including cold/warm setup, GPU + CPU/RAM + active disk/IP,
   scaledown, and egress) must fit inside both `workload.max_budget_usd` and `PROPOSED_PROVIDER_CAPS` in
   `explainer_engine/cloud/providers/base.py`.
5. **Setup-share ceiling (RP-09)**: unless `workload.measure_only=True`, offers where `setup_share > 0.40` (boot/setup time exceeds
   40% of total runtime) are rejected so fast, expensive GPUs are not wasted on slow cold-image pulls.

## 2. Recommended routing policy

- **Primary full-episode batch VM (`workload_c_j5_minimised_p12_p14`, `workload_c_combined_p12_p14`)**: Hyperstack `n3-A100x1`
  (`$1.35/hr`, `~$1.71` for J5-minimised episode) or `n3-H100x1` (`$1.90/hr` on-demand, `~$2.22` for J5-minimised episode) via
  skill `hyperstack-operations`.
- **Primary short calibration (`workload_d_short_calibration`) & burst single-clip retries**: Modal `H100` (`$0.36` gross,
  `$0.00` net under Starter `$30/mo` credit) or `A100-80GB` (`$0.45` gross, `$0.00` net) via skill `modal-operations`.
- **Legacy baseline & warm network volume**: RunPod via `explainer_engine/cloud/runpod.py` and
  `explainer_engine/cloud/providers/runpod_adapter.py`.

## 3. Read-only CLI

- Run dry-run ranking:
  `python -m explainer_engine.cloud.providers --workload workload_c_j5_minimised_p12_p14`
