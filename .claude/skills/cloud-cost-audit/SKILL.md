---
name: cloud-cost-audit
description: Pre-launch and post-run cloud spend auditing across Hyperstack, Modal, and RunPod using explainer_engine/cloud/providers/base.py, explainer_engine/cloud/jobs.py, and explainer_engine/cloud/store.py. Verifies billing-trap compliance, setup-share ceilings, and SHA-256 output storage before teardown.
---

> **Route-scoped since D-116 (2026-11-06):** LTX and Qwen are named here only as GPU workloads of the J2/J4 routes and of the Qwen assets of J5 (D-116); provider runs stay dry-run until the creator approves caps in `config/spend_caps.json` (D-56).

# Cloud Cost Audit (`docs/providers/CLOUD_COST_MODEL.md`)

Use this skill before proposing any paid cloud run and immediately after any cloud job finishes or aborts.

## 1. Pre-launch cost audit checklist (OR-22, OR-23, OR-24, OR-34)

1. **Compare all three active adapters in dry-run mode**:
   run `python -m explainer_engine.cloud.providers --workload workload_c_j5_minimised_p12_p14` (or the target workload preset in
   `explainer_engine/cloud/providers/base.py`) and inspect `CostBreakdown` (`compute_usd`, `cpu_ram_hourly_usd`,
   `active_disk_ip_hourly_usd`, `egress_usd`, `idle_storage_per_day_usd`, `conservative_retry_total_usd`, `setup_share`).
2. **Verify zero hidden idle charges**:
   - On **Hyperstack** (`explainer_engine/cloud/providers/hyperstack.py`): confirm teardown uses `DELETE` (`$0.00/hr`) or
     `HIBERNATE` (`~$0.24/day` for 100 GB root disk + public IP), **never** `SHUTOFF` (`$32.40–$60.00/day` full GPU rate!).
   - On **Modal** (`explainer_engine/cloud/providers/modal_provider.py`): confirm `scaledown_window <= 60s` and persistent weights
     fit inside the `1 TiB` free `modal.Volume` tier (`$0.00/day`).
   - On **RunPod** (`explainer_engine/cloud/runpod.py` and `explainer_engine/cloud/providers/runpod_adapter.py`): account for
     stopped pod disk (`$0.20/GB/month` = `$0.67/day` per 100 GB) and network volume (`$0.07/GB/month`).
3. **Confirm `config/spend_caps.json` is untouched**: new provider caps stay in `PROPOSED_PROVIDER_CAPS` inside
   `explainer_engine/cloud/providers/base.py` with `"enabled": False` until the creator explicitly approves a paid test in their
   own words (OR-22).

## 2. Post-run output & teardown verification (OR-33, OR-36)

1. Verify every output recorded on `explainer_engine/cloud/jobs.py` (`Job.record_output`) passes SHA-256 and non-zero size checks
   via `verify_and_mark_stored` in `explainer_engine/cloud/providers/base.py` and `explainer_engine/cloud/store.py`.
2. If a job fails or cancels while `Job.unstored_outputs()` is non-empty, `sync_job_from_view` transitions the job to
   `RECOVERY_REQUIRED` so the volume/disk is never deleted before outputs are salvaged.
3. Companion skills: skill `hyperstack-operations`, skill `modal-operations`, and skill `cloud-provider-selection`.
