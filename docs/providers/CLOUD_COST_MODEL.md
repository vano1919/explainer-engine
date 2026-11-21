# Comparable Multi-Provider Cloud Cost Model (`CLOUD_COST_MODEL.md`)

**Date Accessed & Verified:** 2026-11-06 / 2026-11-07
**Scope:** Transparent, apples-to-apples total-cost comparison across **RunPod**, **Hyperstack**, **Modal**, **Lambda Cloud**, **Vast.ai**, **Nebius**, and **AWS EC2** on the exact four required workloads (`Workload A`, `Workload B`, `Workload C`, `Workload D`), plus full 12-minute episode projections.

## 1. Common Workload Assumptions & Formulas (`[ASSUMPTION]` / `[OBSERVED RESULT]`)

To avoid misleading headline `$/hr` comparisons, every provider is evaluated using the exact total-cost formula:

$$\text{TotalCostUSD} = \underbrace{(T_{\text{boot}} + T_{\text{download}} + T_{\text{load}} + T_{\text{work}} + T_{\text{upload}} + T_{\text{scaledown}})}_{\text{Billable Wall Time (hours)}} \times (R_{\text{GPU}} + R_{\text{CPU+RAM}} + R_{\text{ActiveDisk}} + R_{\text{IP}}) + C_{\text{IdleStorage}} + C_{\text{Egress}} + C_{\text{RetryOverhead}}$$

### Hardware & Timing Inputs (`[OBSERVED RESULT]` from `LTX_HELPERS.md`, `p12b.json`, `B_COST_MODEL.md`)
1. **Reference Speeds (Measured on RunPod H100 NVL & A100 80GB):**
   - `Qwen-Image-2.1` (`bf16`, 30 steps, 1280x720): Load = `61.0 s` (H100) / `103.7 s` (A100 `1.7x`); Inference = `36.0 s/pic` (H100) / `61.2 s/pic` (A100) / `40.0 s/pic` (L40S/L40 estimate `0.9x` H100).
   - `LTX-2.5` 22B (`fp8-cast`, 2-stage `1920x1088`, 24 fps): Load = `90.0 s` (`[ESTIMATE]`); `121 frames (5.04 s)` = `227.6 s` (H100) / `386.9 s` (A100 `1.7x`); `73 frames (3.04 s, Argon's proposed LTX ceiling (not yet in the BP registry) cap)` = `137.3 s` (H100) / `233.4 s` (A100); `185 frames (7.71 s)` = `348.0 s` (`5.8 min` measured on H100, `LTX_HELPERS.md`).
2. **Weight Download & Container Boot Overhead:**
   - **Cold VM/Pod (RunPod, Hyperstack, Lambda, Vast, Nebius, AWS):** Pulling container + weights when not cached takes `~15.0 min` (`900 s`) for Qwen-only (`~42 GB` @ `~50 MB/s`) or `~45.0 min` (`2,700 s`) for combined Qwen + LTX (`160 GB`, matching `p12b.json` `fixed_setup_minutes = 45`).
   - **Warm Volume / Hibernated Root Disk / Modal Volume:** When weights are pre-populated on a free Modal Volume (`1 TiB` free) or cached local/persistent disk, container/VM boot + mount takes `~2.0 min` (`120 s`) on VMs or `~15.0 s` startup + `10.0 s` scaledown (`25.0 s`) on Modal (`configured scaledown_window = 10 s`).
3. **All-In Hourly Rate Breakdown (`R_all_in = R_GPU + R_CPU_RAM + R_ActiveDisk + R_IP`):**
   - **RunPod (`A100 80GB Comm`):** `$1.390/hr` GPU + `$0.00` CPU/RAM + `$0.0315/hr` disk (`230 GB * $0.10 / 730h`) = **`$1.4215 / hr`** (`H100 NVL Comm`: `$2.590 + $0.0315` = **`$2.6215 / hr`**).
   - **Hyperstack (`n3-A100x1 80GB PCIe`):** `$1.350/hr` GPU + `$0.00` CPU/RAM/850GB local NVMe + `$0.00672/hr` Public IP = **`$1.3567 / hr`** (`n3-H100x1 80GB PCIe`: `$2.500 + $0.00672` = **`$2.5067 / hr`**; `n3-L40x1 48GB`: `$1.000 + $0.00672` = **`$1.0067 / hr`**).
   - **Modal (Functions with 8 Physical Cores [16 vCPU] + 64 GiB RAM):**
     - `L40S 48GB`: `$1.950` GPU + `$0.377` CPU + `$0.511` RAM = **`$2.838 / hr`** (or with 4 cores + 32 GiB RAM: `$1.950 + $0.189 + $0.256` = **`$2.395 / hr`**).
     - `A100 80GB`: `$2.500` GPU + `$0.377` CPU + `$0.511` RAM = **`$3.388 / hr`**.
     - `H100 SXM 80GB (auto-H200)`: `$3.950` GPU + `$0.377` CPU + `$0.511` RAM = **`$4.838 / hr`**.
   - **Lambda Cloud (`1x A100 80GB`):** **`$1.790 / hr`** (`1x H100 PCIe`: **`$2.490 / hr`**; `1x GH200 96GB`: **`$1.490 / hr`**).
   - **Vast.ai (`1x A100 80GB` verified host median):** `$1.150/hr` GPU + `$0.035/hr` disk = **`$1.185 / hr`** (`1x H100`: **`$1.890 / hr`**; high variance / `1.25x` retry factor for host instability).
   - **Nebius (`1x L40S` / `1x RTX PRO 6000 96GB` / `1x H100 SXM`):** `L40S`: **`$1.550 / hr`**; `RTX PRO 6000 96GB`: **`$1.800 / hr`**; `H100 SXM`: **`$4.500 / hr`** (`+$0.015/GiB` egress).
   - **AWS EC2 (`p5.4xlarge` 1x H100):** **`$6.880 / hr`** on-demand (`$5.190/hr` Capacity Block) + `$0.09/GB` egress.

## 2. Workload Cost Comparison Table (`Workloads A, B, C, D`)

### Workload Definitions
- **Workload A (Isolated Image Generation Batch):** `16 Qwen-Image-2.1` pictures (`xworld_v2` LoRA, 30 steps) for one episode's new assets (`6 shots + 10 scene cards` per `OR23_ROUTE_TEST_APPROVAL_PAGE.md`). Pure GPU compute = `61s load + 16 * 36s = 637s` (`10.6 min` on H100; `18.0 min` on A100; `11.8 min` on L40/L40S). Cold setup = `15.0 min` (`900 s`); Warm setup (Modal Volume / cached VM) = `25 s` (Modal) / `120 s` (VM).
- **Workload B (Isolated Video Generation Batch):** `6 LTX-2.5` clips totaling `30.0 s` (`822 frames` per `OR23_ROUTE_TEST_APPROVAL_PAGE.md`: two 290f + two 121f, or ten `73f` [3.04s] impact clips). Pure GPU compute = `90s load + 1,546s render = 1,636s` (`27.3 min` on H100; `46.4 min` on A100). Cold setup = `30.0 min` (`1,800 s`); Warm Volume setup = `35 s` (Modal).
- **Workload C (Combined `p12b` / `p14` Multi-Stage Pod):** Full combined pod (`45.0 min` setup + `176.0 min` planned work = `221.0 min` [`3.683 hr`] on A100-class reference, or `45.0 min` setup + `103.5 min` work = `148.5 min` [`2.475 hr`] on H100-class, `p12b.json` `plan`).
- **Workload D (Serverless Short Job — `p15_mini_cal` / Single Retry):** `2 Qwen restyles + 1 LTX 73-frame (3.04 s) impact clip` (`~4.5 min` pure GPU work on H100 / `7.6 min` on A100). On a cold VM this violates **RP-01** (`work < 3 * setup`) because `15–25 min` setup dwarfs `4.5 min` work; on Modal with a warm Volume (`25 s` cold-start + scaledown), setup is only `9%` of wall time!

| Provider & GPU Configuration | **Workload A:** 16 Qwen Pics (Cold VM vs Warm Volume) | **Workload B:** 30s LTX-2.5 (822f) (Cold VM vs Warm Volume) | **Workload C:** Combined `p12b`/`p14` Full Run (`3.68h` A100 / `2.48h` H100) | **Workload D:** Short Retry / `p15_mini_cal` (`2 Qwen + 1 LTX 73f`) | Retry-Buffered Conservative Case (`+25%` VM / `+35%` Marketplace) |
|---|---|---|---|---|---|
| **RunPod — `A100 80GB Comm` (`$1.422/hr` all-in)** | `$0.78` (cold 33m) / `$0.47` (warm) | `$1.81` (cold 76m) / `$1.15` (warm) | **`$5.24`** (`221 min` all-in) | `$0.54` (cold 23m) / `$0.23` (warm) | `$6.55` (Workload C) |
| **RunPod — `H100 NVL Comm` (`$2.622/hr` all-in)** | `$1.12` (cold 25.6m) / `$0.55` (warm) | `$2.50` (cold 57.3m) / `$1.28` (warm) | **`$6.49`** (`148.5 min` all-in) | `$0.85` (cold 19.5m) / `$0.28` (warm) | `$8.11` (Workload C) |
| **Hyperstack — `n3-A100x1 80GB` (`$1.357/hr` all-in)** | `$0.75` (cold 33m) / **`$0.45`** (warm) | **`$1.73`** (cold 76m) / **`$1.09`** (warm) | **`$5.00`** (`221 min`, 0 disk fee!) | `$0.51` (cold 23m) / `$0.22` (warm) | **`$6.25`** (Workload C — **Lowest Reliable VM**) |
| **Hyperstack — `n3-H100x1 80GB` (`$2.507/hr` all-in)** | `$1.07` (cold 25.6m) / `$0.53` (warm) | `$2.39` (cold 57.3m) / `$1.22` (warm) | **`$6.20`** (`148.5 min`, 0 disk fee!) | `$0.81` (cold 19.5m) / `$0.27` (warm) | `$7.75` (Workload C) |
| **Hyperstack — `n3-L40x1 48GB` (`$1.007/hr` all-in)** | **`$0.45`** (cold 26.8m) / **`$0.23`** (warm) | *N/A (48GB VRAM insufficient for LTX 22B)* | *N/A (requires 80GB for Stage L)* | *Qwen-only:* `$0.26` (cold) / `$0.06` (warm) | `$0.56` (Workload A) |
| **Modal — `L40S 48GB` (`$2.395/hr` all-in w/ 4c/32G)** | **`$0.49` gross** (**`$0.00` net** w/ `$30` Starter credit; warm Volume) | *N/A (use A100-80GB or H100 for LTX 22B)* | *N/A (use A100-80GB / H100)* | *Qwen-only (2 pics):* **`$0.066` gross** (**`$0.00` net**) | `$0.61` gross (`$0.00` w/ credit) |
| **Modal — `A100 80GB` (`$3.388/hr` all-in w/ 8c/64G)** | `$1.04` gross (**`$0.00` net** w/ credit; warm Volume) | `$2.65` gross (**`$0.00` net** w/ credit; warm Volume) | `$10.35` gross (`183m` warm Volume; **`$0.00` net** for first 2.8 runs/mo) | **`$0.45` gross** (**`$0.00` net** w/ credit; `8.0 min` total!) | `$12.94` gross (`$0.00` within `$30` credit) |
| **Modal — `H100 SXM` (`$4.838/hr` all-in, auto-H200)** | `$0.89` gross (**`$0.00` net** w/ credit; `11.0m` warm Volume) | `$2.24` gross (**`$0.00` net** w/ credit; `27.8m` warm Volume) | `$8.91` gross (`110.5m` warm Volume; **`$0.00` net** for first 3.3 runs/mo) | **`$0.39` gross** (**`$0.00` net** w/ credit; `4.9 min` total!) | `$11.14` gross (`$0.00` within `$30` credit) |
| **Lambda Cloud — `1x GH200 96GB` (`$1.490/hr`)** | `$0.64` (cold) / `$0.31` (warm) | `$1.42` (cold) / `$0.73` (warm) | **`$3.69`** (if `aarch64` wheels pass; `[UNKNOWN]`) | `$0.48` (cold) | `$4.61` (`aarch64` unverified) |
| **Lambda Cloud — `1x A100 80GB` (`$1.790/hr`)** | `$0.98` (cold) / `$0.60` (warm) | `$2.28` (cold) / `$1.44` (warm) | `$6.59` (`221 min`) | `$0.68` (cold) | `$8.24` (Workload C) |
| **Vast.ai — `1x A100 80GB` (`$1.185/hr` median)** | `$0.65` (cold) / `$0.39` (warm) | `$1.51` (cold) / `$0.95` (warm) | `$4.36` (best-case) | `$0.45` (cold) | `$5.89` (`+35%` host/download retry overhead) |
| **Nebius — `1x RTX PRO 6000 96GB` (`$1.800/hr`)** | `$0.79` (cold) / `$0.40` (warm) | `$1.75` (cold) / `$0.92` (warm) | `$4.65` (`+egress $0.08`) | `$0.59` (cold) | `$5.81` (Blackwell CUDA 12.8+ required) |
| **Nebius — `1x H100 SXM` (`$4.500/hr` + egress)** | `$1.92` (cold) / `$0.95` (warm) | `$4.30` (cold) / `$2.20` (warm) | `$11.22` (`148.5 min` + egress) | `$1.46` (cold) | `$14.03` (Workload C) |
| **AWS EC2 — `p5.4xlarge` 1x H100 (`$6.880/hr` + egress)** | `$2.98` (cold) / `$1.49` (warm) | `$6.68` (cold) / `$3.46` (warm) | `$17.48` (`148.5 min` + EBS + `$0.45` egress) | `$2.28` (cold) | `$21.85` (Workload C) |

## 3. 12-Minute Episode Cost Projection Under J5 v3 Architecture (`[ESTIMATE]`)

In Turn 3–4 (`docs/J5_LTX_MINIMISATION_REPORT.md` and `docs/handoff/argon_2026-11-06/argon/B_COST_MODEL.md`), our J5 v3 architecture (Argon's proposed J5 limits, not yet in the BP registry) + `R0–R5` reuse reduced a 12-minute (`720 s`) episode's cloud GPU needs to:
- **Qwen-Image-2.1:** `~32–40` new pictures (`~20–24 min` H100 compute or `~34–40 min` A100 compute).
- **LTX-2.5:** `90.0 s` (`12.5%` of episode runtime = ~30 short impact clips of `73 frames [3.04 s]` each).
- **Expected Episode Cloud GPU Cost by Provider:**
  1. **Modal (using `$30/mo` Starter credit, warm Volume):** **`$0.00 out-of-pocket`** for up to ~5–6 full 12-minute episodes per month (`~$4.60–$5.50` gross compute deducted from the `$30/mo` free credit)!
  2. **Hyperstack (`n3-A100x1` @ `$1.35/hr` or `n3-H100x1` @ `$2.50/hr`):** **`$3.30 – $4.25 / episode`** (single batch VM run, `$0` disk/egress fees, deleted immediately after `cloud/store.py verify`).
  3. **RunPod (`A100 80GB Comm` @ `$1.39/hr` or `H100 NVL` @ `$2.59/hr`):** **`$3.44 – $4.44 / episode`** (`Policy 3` in `B_COST_MODEL.md`).
  4. **Even under legacy Policy 1 (432s LTX, no J5 minimisation):** Hyperstack (`$10.10–$13.60`) and RunPod (`$10.35–$14.37`) sit inside the `$10–15` unverified discussion target, whereas AWS (`$31+`) and uncredited Modal (`$22+`) exceed it.
