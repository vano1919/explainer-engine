---
name: hyperstack-operations
description: Read-only inventory, pricebook, total-cost estimation, and safe lifecycle rules for Hyperstack GPU VMs (CANADA-1, NORWAY-1, US-1) via explainer_engine/cloud/providers/hyperstack.py. Enforces OR-22/23/24/34 approval gates and guards against the Hyperstack SHUTOFF billing trap where SHUTOFF continues billing 100% of the GPU rate.
---

> **Route-scoped since D-116 (2026-11-06):** LTX and Qwen are named here only as GPU workloads of the J2/J4 routes and of the Qwen assets of J5 (D-116); provider runs stay dry-run until the creator approves caps in `config/spend_caps.json` (D-56).

# Hyperstack GPU VM Operations (`explainer_engine/cloud/providers/hyperstack.py`)

Use this skill when inspecting Hyperstack GPU capacity (`A100-80G-PCIe`, `H100-80G-PCIe`, `H200-141G-SXM5`, `L40`),
estimating workload cost, or preparing an approved VM run (`docs/providers/HYPERSTACK_README.md`).

## 1. Non-negotiable billing & safety rules (OR-22..36)

1. **Never use `STOP` / `SHUTOFF` or `shutdown -h now` inside SSH to save money**: on Hyperstack
   (`https://infrahub-api.nexgencloud.com/v1`), a VM in `SHUTOFF` state continues billing **100% of the full GPU hourly
   rate** (`$1.35/hr` on `n3-A100x1`, `$2.50/hr` on `n3-H100x1`). Only `HIBERNATE` (`GET /core/virtual-machines/{id}/hibernate` ->
   `HIBERNATED`, root disk billed at `$0.000096774/GB/hr` + public IP `$0.00672/hr`) or `DELETE` (`DELETE /core/virtual-machines/{id}` ->
   `$0.00/hr`) stops GPU compute billing.
2. **Product surface boundary**: use **Hyperstack GPU VMs** only. Hyperstack AI Studio and Dedicated Inference (vLLM wizard)
   cannot run our custom `Qwen/Qwen-Image-2.1` + `xworld_v2` LoRA or `Lightricks/LTX-2.5` 22B pipelines.
3. **Zero live spend without OR-22/23/24/34 approval**: `HyperstackAdapter.submit_job(..., dry_run=False)` requires a valid
   `ApprovalGate` in `explainer_engine/cloud/providers/base.py` with creator confirmation (OR-22), an item-by-item plan (OR-23),
   an Opus verdict (OR-24), and a Fable readiness audit (OR-34).
4. **Timeout reconciliation (OR-25)**: if `POST /core/virtual-machines` times out or returns HTTP 5xx, never blind-retry creation.
   Call `HyperstackAdapter.reconcile_existing(vm_name)` via `GET /core/virtual-machines` first and adopt any matching VM.

## 2. Read-only CLI & adapter inspection

- Dry-run provider comparison and cost estimate:
  `python -m explainer_engine.cloud.providers --workload workload_c_j5_minimised_p12_p14`
- Key implementation modules:
  - `explainer_engine/cloud/providers/hyperstack.py`
  - `explainer_engine/cloud/providers/base.py`
  - `explainer_engine/cloud/jobs.py`
  - `explainer_engine/cloud/store.py`
- Companion skills: skill `cloud-provider-selection` and skill `cloud-cost-audit`.
