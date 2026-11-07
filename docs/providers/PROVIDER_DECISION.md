# Final Provider Decision & Executive Report (`PROVIDER_DECISION.md`)

**Date:** 2026-11-07
**Branch:** `argon/ltx-minimisation` (HEAD `e4b713d`)
**Status:** Research & Safe Dry-Run Prototype Complete (`$0.00` spent, `main` untouched, `config/spend_caps.json` untouched).

## 1. Executive Summary

We audited the Explainer Engine repository (`explainer_engine/cloud/*`, `config/spend_caps.json`, `explainer_engine/training/pods/p12/*`, `docs/handoff/argon_2026-11-06/argon/*`, and `explainer_engine/blender/j5_*.py`), mapped the exact hardware and storage requirements of the **Ink Chronicle** pipeline, and evaluated **18 GPU providers** (RunPod baseline + 17 alternatives) with deep technical investigations of **Hyperstack** and **Modal**.

### Key Conclusions
1. **Keep Local/CI for All Non-Diffusion Work (`$0.00` Cloud Cost):** Blender 5.2.3 2.5D card staging (`J5_DIALOGUE_CARD`), multi-plane billboard crowds (`J5_BILLBOARD_CROWD`), hinged action rigs (`J5_HINGED_RIG`), 3D layout/depth/line passes, `BiRefNet` cutouts, `Depth-Anything-V2-Small` depth maps, `Rhubarb` lip-sync, and `FFmpeg` (`lanczos+cas=0.4`, `-14 LUFS`) run locally on CPU or the creator's `RX 5700 8GB` PC at `$0.00` cloud cost (Argon's proposed J5 limits, not yet in the BP registry).
2. **Best Persistent GPU VM Alternative to RunPod — Hyperstack (`n3-A100x1` @ `$1.35/hr`, `n3-H100x1` @ `$2.50/hr`):**
   - Hyperstack's **GPU VMs** (`CANADA-1`, `NORWAY-1`, `US-1`) provide clean REST APIs for real-time stock (`GET /v1/core/stocks`, `GET /v1/core/flavors`) and account-specific pricing (`GET /v1/pricebook`), per-minute billing, **$0 data egress**, and **`750 GB` of free local NVMe ephemeral disk** on `n3-A100x1` (`$1.35/hr`) and `n3-H100x1` (`$2.50/hr`)—eliminating RunPod's `$0.10–$0.20/GB/mo` disk charges while holding all `160 GB` of Qwen + LTX-2.5 weights.
   - **Critical Caveat:** Hyperstack's `AI Studio` and `Dedicated Inference` **cannot** run our custom pipeline, and Hyperstack's VM `SHUTOFF` state **continues billing 100% of the GPU rate** ([VM States and Billing](https://docs.hyperstack.cloud/docs/billing/states-and-billing/)). Our `HyperstackAdapter` enforces `HIBERNATE` or `DELETE` instead of `STOP`.
3. **Best Serverless & Short-Job / Backup Platform — Modal (`$30/month` Free Starter Credits + `1 TiB` Free Volume):**
   - While Modal's raw hourly rates (`$3.39/hr` all-in for A100-80GB, `$4.84/hr` all-in for H100 SXM) are higher than VM providers once credits are exhausted, its **Starter plan includes `$30/month` of free Function compute credits** and **`1 TiB` of free Volume storage** ([Modal Pricing](https://modal.com/pricing)).
   - Because our J5 v3 architecture (Argon's proposed J5 limits, not yet in the BP registry) cut LTX usage to `3.04 s` (`73 frames`) on the 1-minute film and `90 s` on a 12-minute episode, caching our `160 GB` weights on a free Modal Volume lets us run **short calibration jobs (`p15_mini_cal`), single-clip retries, and up to ~5–6 J5-minimised episodes per month for `$0.00` out-of-pocket**, with built-in multi-GPU fallback (`gpu=["A100-80GB", "H100", "RTX-PRO-6000"]`) and zero `RP-01` 45-minute setup penalty!

## 2. Ten-Criterion Provider Scorecard (Top 8 Viable Providers Ranked)

Scored `1–10` (`10` = best) based on verified evidence in `PROVIDER_COMPARISON.md` and `GPU_AVAILABILITY_RESEARCH.md`:

| Provider | 1. Workload Compat. | 2. GPU Stock Visibility | 3. Reliability & SLA | 4. Total Job Cost | 5. API & Idempotency | 6. Operational Control | 7. Automation & Claude Fit | 8. Georgia Eligibility | 9. Low Lock-In | 10. Security & Audit | **Weighted Total (/100)** | Category Winner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **1. RunPod (Current Baseline)** | 10 | 8 | 8 | 9 | 9 | 9 | 10 | 10 | 9 | 9 | **91 / 100** | **Current Production Baseline** |
| **2. Hyperstack (GPU VMs)** | 10 | **9** | **9** | **9** | **9** | 9 | 9 | 8 | 9 | 9 | **90 / 100** | **Best Persistent GPU VM Alternative** |
| **3. Modal (Serverless GPU)** | 9 | 8 | **9** | **10** *(w/ $30 credit)* / 6 *(after)* | 9 | 8 | **10** | 8 | 7 | 9 | **87 / 100** | **Best Serverless & Short-Job / Retry Option** |
| **4. Lambda Cloud** | 10 | 8 | 9 | 8 | 8 | 9 | 8 | 6 | 9 | 9 | **84 / 100** | **Best Simple Data-Center VM Backup** |
| **5. Nebius AI Cloud** | 9 *(No A100)* | 8 | **9** | 7 | 8 | 9 | 8 | 8 | 8 | 9 | **83 / 100** | **Best High-Availability H100/RTX PRO 6000 Cloud** |
| **6. Vast.ai** | 9 | **9** | 6 | **9** | 8 | 8 | 8 | 9 | 9 | 6 | **81 / 100** | **Cheapest Spot/Marketplace Backup** |
| **7. Genesis Cloud / CUDO** | 9 | 7 | 8 | 8 | 7 | 8 | 7 | 8 | 9 | 8 | **79 / 100** | **Secondary EU GPU VM Backup** |
| **8. Vultr GPU** | 8 | 8 | 8 | 6 | 8 | 8 | 8 | 9 | 9 | 8 | **80 / 100** | **Global VPS Backup (L40S)** |

## 3. Direct Answers to the 10 Decision Framework Questions

1. **Which provider is the best primary VM alternative to RunPod for this exact workload?**
   - **Hyperstack GPU VMs (`n3-A100x1` 80GB @ `$1.35/hr` and `n3-H100x1` 80GB @ `$2.50/hr` in `CANADA-1`).** It runs our exact Docker/bash stack, includes `750 GB` of local NVMe storage for free, charges `$0` egress, and exposes clean read-only Stock (`/v1/core/stocks`, `/v1/core/flavors`) and Pricebook (`/v1/pricebook`) APIs.
2. **Which provider is the best backup when GPU stock is unavailable?**
   - **For short jobs / bursts (`<= 30 min`):** **Modal** (using `gpu=["A100-80GB", "H100", "RTX-PRO-6000"]` automatic multi-pool fallback and `$30/mo` free credit).
   - **For full VM pods:** **Hyperstack** (if RunPod is out of stock) or **Lambda Cloud / Vast.ai** (filtered to `verified=True, reliability > 0.99, inet_down > 500`).
3. **Which provider is genuinely cheapest after all overhead?**
   - **Up to `$30/month` of compute:** **Modal Starter Plan (`$0.00/month` net out-of-pocket)** with weights cached in the free `1 TiB` Modal Volume.
   - **Beyond `$30/month` (paid out-of-pocket):** **Hyperstack `n3-A100x1` (`$1.357/hr` all-in including IP, `$0` disk/egress)** and **RunPod `A100 80GB Community` (`$1.422/hr` all-in)** for 80GB workloads, and **Hyperstack `n3-L40x1` (`$1.007/hr`)** for isolated 48GB Qwen-Image workloads.
4. **Which provider has the best stock visibility and capacity API?**
   - **Vast.ai** (`POST /api/v0/bundles` returns exact per-machine offer IDs, upload/download speeds, and reliability scores) and **Hyperstack** (`GET /v1/core/stocks` + `GET /v1/core/flavors` returns real-time and upcoming stock per region and GPU count), followed closely by **RunPod** (`GET /v2/catalog/gpus?include=AVAILABILITY`).
5. **Is Modal a practical replacement for the whole pipeline, or only selected short-lived jobs?**
   - Modal is **best used for short-lived, decoupled jobs (`Workload A` Qwen batches, `Workload B/D` short LTX impact clips, and `p15_mini_cal`)** where scale-to-zero, Volume weight caching, and the `$30/month` free credit shine. Using Modal for multi-hour monolithic jobs after exhausting the `$30` credit costs `~2.5x` more per hour than Hyperstack/RunPod due to higher GPU base rates plus separate CPU/RAM billing (`+$0.89/hr`).
6. **Is Hyperstack a practical replacement for the whole pipeline, or only persistent GPU VM workloads?**
   - Hyperstack **GPU VMs** can run the entire cloud GPU pipeline (`p12b`/`p14` combined Qwen + LTX pods), provided the adapter **always `DELETE`s (or `HIBERNATE`s) the VM immediately upon completion** and never leaves a VM in `SHUTOFF`. Hyperstack's `AI Studio` and `Dedicated Inference` cannot run our pipeline.
7. **Should the system use one provider or a multi-provider strategy?**
   - **A 2-tier multi-provider strategy (`RunPod` + `Hyperstack` for batch VMs, `Modal` for serverless short bursts/retries)** behind the unified `explainer_engine/cloud/providers/` selector. This eliminates single-provider stock stalls while harvesting Modal's `$30/mo` free compute credit for calibration tests and retries.
8. **Which stages should remain local/CI?**
   - **100% of non-diffusion stages:** `visual_script/1`, `still_needs`, `reuse_plan` (`R0–R5`), Blender 5.2.3 2.5D card staging (`J5`), multi-plane billboard crowds, hinged cutout rigs, 3D layout/depth/line passes, `BiRefNet` cutouts, `Depth-Anything-V2-Small`, `Rhubarb` lip-sync, and `FFmpeg` post-processing (`lanczos+cas=0.4`, `-14 LUFS`).
9. **What are the biggest technical risks?**
   - **(R1) Hyperstack `SHUTOFF` Billing Trap:** Calling `stop` or `shutdown -h now` on Hyperstack bills 100% of the GPU rate (`$1.35–$3.20/hr`). Mitigation: `HyperstackAdapter` blocks `stop` by default and uses `DELETE` or `HIBERNATE`, and alerts if `SHUTOFF` is ever seen.
   - **(R2) Modal Function Preemption & Volume Commit Discipline:** Default Modal Functions are preemptible; outputs must be pushed to `vano1919/tmr-artifacts` or `volume.commit()`ed after every single unit (`OR-33`).
   - **(R3) Blackwell (`RTX PRO 6000` / `B200`) PyTorch & `ltx_pipelines` Compatibility:** Unverified until a cheap smoke test confirms CUDA 12.8+ kernel compatibility.
10. **What must be benchmarked before a production decision?**
    - **Benchmark 1 (`$0.00` Read-Only):** Verify Hyperstack account registration with Georgian billing card and run `python -m explainer_engine.cloud.providers check --provider hyperstack` (read-only `GET /v1/core/stocks`, `/v1/core/flavors`, `/v1/pricebook`).
    - **Benchmark 2 (`$0.00` Out-of-Pocket on Modal Starter Credit):** After creator `OR-23` + Opus `OR-24` + Fable `OR-34` approval, run `p15_mini_cal` (`2 Qwen restyles + 1 LTX 73f clip`) on Modal using the free `$30/mo` Starter credit (`~$0.39–$0.45` credit used, `$0.00` billed to card).

## 4. Category Rankings Summary

| Category | #1 Winner | #2 Runner-Up | Unsuitable / Disqualified |
|---|---|---|---|
| **Best Overall (For Explainer Engine)** | **RunPod + Modal (Hybrid)** | **Hyperstack GPU VMs** | CoreWeave (8-GPU min), Fluidstack (contract-only), SaladCloud (no 80GB VRAM) |
| **Best Reliability & Availability** | **Modal** (multi-GPU fallback queue) & **Nebius** (99% H100) | **Hyperstack** (`CANADA-1` / `US-1`) | Vast.ai / SaladCloud (host preemption & variable bandwidth) |
| **Lowest Verified Total Cost** | **Modal** *(up to $30/mo free credit = $0)* / **Hyperstack `n3-A100x1`** *($1.357/hr paid)* | **RunPod `A100 80GB Comm`** *($1.422/hr)* & **Vast.ai** | AWS EC2 (`$6.88/hr`), GCP (`$9.80/hr`), Azure (`$11.06/hr`) |
| **Best Serverless Option** | **Modal** | RunPod Serverless | Hyperstack AI Studio (cannot run custom LoRA/LTX) |
| **Best Persistent GPU VM** | **Hyperstack GPU VMs** (`n3-A100x1` / `n3-H100x1`) | **RunPod Pods** & **Lambda Cloud** | Vultr / Hyperstack if left in `SHUTOFF` |
| **Best Backup When Stock Is Tight** | **Hyperstack** (for VM pods) / **Modal** (for short bursts) | **Lambda Cloud** & **Vast.ai** (`verified=True`) | Fluidstack, CoreWeave |

## 5. Explicit Actions Requiring Creator Approval (`OR-22`, `OR-23`, `OR-24`, `OR-34`)

No paid action or production change has been made. The following require explicit creator approval before execution:
1. **Approval Gate 1 (Account & Read-Only Key Setup — `$0.00`):** Approve adding read-only `HYPERSTACK_API_KEY` or `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` to local environment (never committed to git) to test live read-only stock polling.
2. **Approval Gate 2 (Proposed Provider Spend Caps in `config/spend_caps.json`):** Approve adding separate, explicit budget lines for `hyperstack` (proposed: `per_vm_usd: 3.00`, `per_24h_usd: 10.00`, `max_hours_per_vm: 2.5`) and `modal` (proposed: `per_run_credit_usd: 1.50`, `require_free_credit_remaining: true`, `max_card_charge_usd: 0.00`).
3. **Approval Gate 3 (`OR-34` Fable Audit + `OR-24` Opus Verdict + `OR-23` Plan):** Required before running `p15_mini_cal` on any provider.
