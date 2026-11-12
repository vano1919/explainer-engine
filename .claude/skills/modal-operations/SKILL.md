---
name: modal-operations
description: Read-only capacity, per-second GPU/CPU/Memory cost estimation, Starter $30/month credit accounting, and Volume persistence rules for Modal serverless GPU containers via explainer_engine/cloud/providers/modal_provider.py.
---

> **Route-scoped since D-116 (2026-11-06):** LTX and Qwen are named here only as GPU workloads of the J2/J4 routes and of the Qwen assets of J5 (D-116); provider runs stay dry-run until the creator approves caps in `config/spend_caps.json` (D-56).

# Modal Serverless GPU Operations (`explainer_engine/cloud/providers/modal_provider.py`)

Use this skill when evaluating or preparing short calibration jobs (`workload_d_short_calibration`), single-clip LTX-2.5
retries, or burst serverless runs on Modal (`docs/providers/MODAL_README.md`).

## 1. Non-negotiable billing & architecture rules (OR-22..36)

1. **Separate CPU and Memory billing**: Modal bills GPU per second (`A100-80GB`: `$0.000694/s` = `$2.50/hr`; `H100`:
   `$0.001097/s` = `$3.95/hr` with automatic free upgrade to `H200` 141 GB when available; `L40S`: `$0.000542/s` = `$1.95/hr`)
   **plus** physical CPU cores (`$0.0000131/core/s` = `$0.04716/core/hr`) and Memory (`$0.00000222/GiB/s` = `$0.007992/GiB/hr`).
   Always include CPU + RAM (`+$0.89/hr` for 8 physical cores + 64 GiB RAM) in gross cost estimates via
   `ModalAdapter.estimate_cost` in `explainer_engine/cloud/providers/modal_provider.py`.
2. **Starter $30/month free credit & 1 TiB free Volume**: Modal's Starter plan (`$0/mo` base fee) includes `$30/month` in free
   Function compute credits and `1 TiB` of free `modal.Volume` storage. Always report **both** gross cost (against run caps)
   and net out-of-pocket cost after free credit.
3. **Bake weights or mount `modal.Volume` (`v2`)**: never download 44 GB of `Lightricks/LTX-2.5` or `Qwen/Qwen-Image-2.1` weights
   inside a GPU-billed cold start. Populate a persistent `modal.Volume` once and call `vol.commit()` after each plate/clip
   followed by `verify_and_mark_stored` in `explainer_engine/cloud/providers/base.py`.
4. **Ordered multi-GPU fallback**: configure `gpu=["H100", "A100-80GB", "RTX-PRO-6000"]` and `max_inputs=1` with `retries=0` on
   long video generation functions so preemptions never re-bill a 45-minute batch from scratch.

## 2. Read-only CLI & adapter inspection

- Dry-run short calibration comparison:
  `python -m explainer_engine.cloud.providers --workload workload_d_short_calibration`
- Key implementation modules:
  - `explainer_engine/cloud/providers/modal_provider.py`
  - `explainer_engine/cloud/providers/base.py`
  - `explainer_engine/cloud/jobs.py`
  - `explainer_engine/cloud/store.py`
- Companion skills: skill `cloud-provider-selection` and skill `cloud-cost-audit`.
