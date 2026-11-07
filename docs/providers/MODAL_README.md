# Modal Serverless GPU Deep-Dive & Integration Specification (`MODAL_README.md`)

**Date Accessed & Verified:** 2026-11-06 / 2026-11-07
**Official Documentation:** [Modal Pricing](https://modal.com/pricing), [Modal GPU Acceleration Guide](https://modal.com/docs/guide/gpu), [ComputePrices Modal](https://computeprices.com/providers/modal), [Modal Status](https://status.modal.com/).

## 1. Architecture & Billing Model (`[VERIFIED FACT]`)

Modal is a **serverless Python container platform**, not a persistent Linux VM provider. Instead of renting a box by the hour over SSH, you decorate Python functions (`@app.function(gpu=..., image=..., volumes=..., timeout=...)`) and Modal spins up containers in `1–2 seconds` (before Python imports and model weight loading), bills **per second** for actual GPU, CPU, and RAM usage, and scales to **zero (`$0.00/hr`)** after a configurable `scaledown_window` (default `60 seconds`) ([Modal Pricing](https://modal.com/pricing)).

### Verified Per-Second & Per-Hour Compute Rates ([Modal Pricing](https://modal.com/pricing), Accessed 2026-11-06)

| Resource / GPU SKU (`gpu=...`) | VRAM | Per-Second Rate | Equivalent Per-Hour Rate | Automatic Upgrade Behavior & Notes |
|---|---:|---:|---:|---|
| **`B300`** | 288 GB | `$0.001972 / s` | **`$7.10 / hr`** | Requires CUDA `13.1+` |
| **`B200` / `B200+`** | 180 GB | `$0.001736 / s` | **`$6.25 / hr`** | `B200+` can auto-upgrade to `B300` at `B200` price |
| **`H200`** (SXM) | 141 GB | `$0.001261 / s` | **`$4.54 / hr`** | 141 GB HBM3e (`4.8 TB/s`) |
| **`H100` / `H100!`** (SXM5) | 80 GB | `$0.001097 / s` | **`$3.95 / hr`** | `gpu="H100"` **may automatically upgrade to an H200 (141 GB) at no extra cost** (`$3.95/hr`); use `H100!` to pin H100 ([Modal GPU Docs](https://modal.com/docs/guide/gpu)) |
| **`RTX-PRO-6000`** | 96 GB | `$0.000842 / s` | **`$3.03 / hr`** | Blackwell Server Edition |
| **`A100-80GB`** | 80 GB | `$0.000694 / s` | **`$2.50 / hr`** | Ampere 80 GB |
| **`A100` / `A100-40GB`** | 40 GB | `$0.000583 / s` | **`$2.10 / hr`** | `gpu="A100"` may auto-upgrade to 80 GB at no extra cost |
| **`L40S`** | 48 GB | `$0.000542 / s` | **`$1.95 / hr`** | Recommended by Modal for 48 GB inference (`Qwen-Image-2.1`) |
| **`A10`** | 24 GB | `$0.000306 / s` | **`$1.10 / hr`** | Suitable for `BiRefNet` / `Depth-Anything` |
| **`L4`** | 24 GB | `$0.000222 / s` | **`$0.80 / hr`** | Suitable for lightweight cutouts/depth |
| **`T4`** | 16 GB | `$0.000164 / s` | **`$0.59 / hr`** | Entry-level 16 GB |
| **CPU (Physical Core = 2 vCPU)** | — | `$0.0000131 / core / s` | **`$0.04716 / core / hr`** | Min `0.125` cores; billed on `max(requested, actual_used)` (`3x` on Sandboxes / non-preemptible) |
| **Memory (GiB)** | — | `$0.00000222 / GiB / s` | **`$0.007992 / GiB / hr`** | Min `128 MiB`; billed on `max(requested, actual_used)` (`3x` on Sandboxes / non-preemptible) |
| **Modal Volumes** | — | — | **`$0.09 / GiB / mo`** | **Includes `1 TiB / month` FREE** (`160 GB` of Qwen + LTX weights costs **$0.00/mo** on Starter!) |
| **Network Egress** | — | — | **`$0.04 / GiB`** | **Includes `1 TiB / month` FREE** on Starter (`10 TiB` on Team) |

**Realistic All-In Hourly Rate on Modal (GPU + 8 Physical Cores [16 vCPU] + 64 GiB RAM):**
- CPU (`8 cores * $0.04716/hr = $0.377/hr`) + RAM (`64 GiB * $0.007992/hr = $0.511/hr`) adds **`+$0.89 / hr`** to the headline GPU rate!
- Thus, an **A100-80GB** container with 8 cores and 64 GiB RAM actually bills **`$2.50 + $0.89 = $3.39 / hr`**, and an **H100 SXM** container with 8 cores and 64 GiB RAM actually bills **`$3.95 + $0.89 = $4.84 / hr`** (`[VERIFIED FACT]` from [Modal Pricing](https://modal.com/pricing) & [Thunder Compute Sandbox Analysis](https://www.thundercompute.com/blog/gpu-sandbox-pricing)).

## 2. Starter Plan & $30/Month Free Credits Verification (`[VERIFIED FACT]`)

Per [Modal Pricing](https://modal.com/pricing) (FAQ *"What does my included usage cover?"* and *"I'm on the Starter plan. Why am I being charged?"*):
- **Monthly Fee:** `$0 / month` (requires a valid payment card on file to unlock GPUs).
- **Included Compute Credits:** **`$30.00 / month` free compute credits** covering **Functions and Sandboxes** (GPU, CPU, and Memory per-second charges), plus **`1 TiB` free Volume storage** and **`1 TiB` free network egress**.
- **What Credits Do NOT Cover:** As of September 1, 2026, Starter credits do **not** cover token-priced **Shared Endpoints** (which are billed from the first token). Since Explainer Engine runs custom containers (`Functions`), **100% of our Qwen-Image and LTX Function compute is covered by the `$30/month` free credit allowance!**
- **Starter Plan Quotas:** Up to `3 seats`, `100 concurrent containers`, **`10 concurrent GPUs`**, `5 cron jobs`, **`1-day log retention`**, and no built-in environment-level hard budget cap in the UI (workspace spend limits exist, but our local `core/ledger.py` + `OR-33`/`OR-36` guard remains mandatory).

## 3. Operational Mechanics: Volumes, Preemption, Timeouts, and Multi-GPU Fallback (`[VERIFIED FACT]`)

1. **Modal Volumes (`modal.Volume`):**
   - Storing our `160 GB` (`Qwen-Image-2.1` + `xworld_v2` + `LTX-2.5` 22B) weights in a Modal Volume costs **`$0.00/month`** (under the `1 TiB` free tier) and eliminates repeated Hugging Face downloads across runs!
   - **Caveats ([Vercel Drives / Modal Volumes Analysis](https://ustechautomations.com/resources/blog/vercel-drives-explained-what-it-changes)):** Changes written by a container are only visible to other containers after an explicit `volume.commit()`, and running containers must call `volume.reload()` (which fails if files are open). v1 Volumes have a hard limit of `500,000 inodes` (recommended `< 50,000` files).
2. **Preemption vs Non-Preemptible (`3x` Multiplier):**
   - By default, Modal GPU Functions are **preemptible** ([Modal Pricing](https://modal.com/pricing): *"Modal Functions are subject to preemption by default; while interruptions are rare, they can happen"*). Opting out of preemption (or using Sandboxes/region pinning) multiplies prices by **`3x`** (for non-preemptible) or **`1.15x–1.75x`** (for region selection).
   - Therefore, any Modal Function running `Qwen` or `LTX` **must** persist every generated PNG/MP4 immediately to `vano1919/tmr-artifacts` (or commit to the Volume after every single picture/clip, `OR-33`) so a rare preemption loses at most the single in-flight clip (`~36 s` Qwen or `~3.5 min` LTX).
3. **Ordered Multi-GPU Fallback (`gpu=[...]`):**
   - Modal allows passing a ranked list: `@app.function(gpu=["A100-80GB", "H100", "RTX-PRO-6000"])`. Modal automatically allocates the first available GPU in the list without failing the job ([Modal GPU Docs](https://modal.com/docs/guide/gpu)).

## 4. Suitability Verdict for Explainer Engine (`[RECOMMENDATION]`)

- **Where Modal Excels (Best Serverless Option):**
  - **Isolated Qwen-Image-2.1 Restyle Batches (`Workload A`) & Short LTX Impact Clips (`Workload B` / `Workload D`):** When weights are cached once in a free `1 TiB` Modal Volume, spinning up a single `L40S` (`$1.95/hr` GPU + `$0.45/hr` CPU/RAM = `$2.40/hr` = `$0.000667/s`) for `2 Qwen restyles` (`~135 s` total incl. load + `10 s` scaledown) costs **`$0.097`**, and the **`$30/month` free Starter credit covers ~300 such mini-batches or ~6–8 full J5-minimised episodes per month for $0 out-of-pocket!**
- **Where Modal Is Worse Than a Persistent GPU VM (RunPod / Hyperstack):**
  - **Long Multi-Stage Monolithic Bash Scripts (`p12b.sh` / `p14.sh` > 2–3 hours) Without Credit:** Once the `$30/mo` Starter credit is exhausted, Modal's all-in hourly rate (`$3.39/hr` for A100-80GB incl. CPU/RAM, `$4.84/hr` for H100 incl. CPU/RAM) is **2.5x higher** than Hyperstack (`$1.35/hr` A100-80GB, `$2.50/hr` H100 PCIe) and RunPod (`$1.39/hr` A100-80GB, `$2.59/hr` H100 NVL), and requires wrapping `p12b.py` / `p12c_ltx.py` in `@app.function` rather than running `pod_wrapper.sh` over raw SSH/Docker.
