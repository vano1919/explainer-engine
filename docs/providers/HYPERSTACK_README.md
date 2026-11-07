# Hyperstack Deep-Dive & Integration Specification (`HYPERSTACK_README.md`)

**Date Accessed & Verified:** 2026-11-06 / 2026-11-07
**Official Documentation:** [Hyperstack API Reference](https://docs.hyperstack.cloud/docs/api-reference/introduction/), [Resource Pricing & Pricebook API](https://docs.hyperstack.cloud/docs/billing/pricebook/), [VM States and Billing](https://docs.hyperstack.cloud/docs/billing/states-and-billing/), [Flavors Catalog](https://docs.hyperstack.cloud/docs/hardware/flavors/), [GPU Stock Information](https://docs.hyperstack.cloud/docs/hardware/gpu-stock-information/), [Python SDK (Alpha)](https://docs.hyperstack.cloud/docs/libraries/python/), [Hyperstack Service Status](https://status.hyperstack.cloud/).

## 1. Product Separation: Which Hyperstack Product Can Run Explainer Engine? (`[VERIFIED FACT]`)

Hyperstack offers three distinct products that **must not be conflated**:

| Hyperstack Product | What It Is | Billing Model | Can It Run Custom `Qwen-Image-2.1` (`xworld_v2` LoRA) + `LTX-2.5` (`ltx_pipelines`)? | Evidence & Source |
|---|---|---|---|---|
| **1. GPU Virtual Machines (`Core` API)** | Full root-access KVM Linux VMs (`Ubuntu 22.04 / 24.04 LTS with Docker & CUDA`) on dedicated NVIDIA GPUs in `CANADA-1`, `NORWAY-1`, `US-1` | Per-GPU hourly rate, **billed per minute**; CPU, RAM, root disk (`100 GB`), and local NVMe ephemeral disk (`750–3,300 GB`) are **included at $0** on GPU flavors (`+$0.00672/hr` public IP) | **YES — 100% COMPATIBLE (`[VERIFIED FACT]`)** | Full SSH + Docker support; `750 GB` free local ephemeral NVMe on `n3-A100x1` / `n3-H100x1` easily holds our `200 GB` Qwen + LTX-2.5 weights without paying for a network volume ([Flavors Docs](https://docs.hyperstack.cloud/docs/hardware/flavors/), [Resource Pricing](https://docs.hyperstack.cloud/docs/billing/pricebook/)). |
| **2. AI Studio (Serverless Partner API)** | Managed OpenAI-compatible inference & playground over a fixed catalog of third-party text and vision models | **Token-based** (per 1M input/output tokens) for text; **Per 16×16 pixel patch** (`256 px/patch`) for catalog image generation | **NO — INCOMPATIBLE (`[VERIFIED FACT]`)** | Served via external third-party integrations; does not accept arbitrary `VideoX-Fun` Python pipelines, custom `xworld_v2` + `mva` dual-LoRA merging, or `Lightricks/LTX-2.5` 22B video generation ([AI Studio Billing](https://docs.hyperstack.cloud/docs/ai-studio/billing/), [AI Studio Models](https://docs.hyperstack.cloud/docs/ai-studio/models/models-overview/)). |
| **3. Dedicated Inference** | Managed wizard that provisions a VM and starts **vLLM** behind a private OpenAI-compatible endpoint for open-weight LLMs | Hourly GPU flavor rate | **NO — INCOMPATIBLE (`[VERIFIED FACT]`)** | Built specifically for vLLM text/vision-language token serving, not multi-stage Bash/Python diffusion/video rendering (`p12b.sh` / `p14.sh`) ([Running Multi-GPU vLLM](https://docs.hyperstack.cloud/docs/tutorials/vllm-multi-gpu/)). |

## 2. Verified GPU Catalog, Flavors, Regions, and Pricing (`[VERIFIED FACT]`)

From [Flavors Docs (Synced Oct 5, 2026)](https://docs.hyperstack.cloud/docs/hardware/flavors/) and [ComputePrices Hyperstack (Oct 28, 2026)](https://computeprices.com/providers/hyperstack):

| Flavor API Name (`flavor_name`) | GPU Model & Count | VRAM | vCPUs | RAM | Root Disk (Persistent) | Ephemeral NVMe (Free, Wiped on Hibernate/Delete) | Regions | On-Demand Price ($/hr) | Supports Hibernation? | Fit for Explainer Engine |
|---|---|---:|---:|---:|---:|---:|---|---:|---|---|
| **`n3-A100x1`** | `1× A100-80G-PCIe` | **80 GB** | 28 | 120 GB | 100 GB | **750 GB** | `CANADA-1` | **`$1.35 / hr`** | **Yes** | **Best Value Primary VM** for combined `p12b`/`p14` Qwen + LTX-2.5 (`750 GB` free NVMe holds all `160 GB` weights!) |
| **`n3-A100-SXM4x1`** *(or SXM tier)* | `1× A100-80G-SXM` | **80 GB** | 24–28 | 120 GB | 100 GB | **750+ GB** | `US-1` / `CANADA-1` | **`$1.60 / hr`** | **Yes** | Fast 80GB fallback when PCIe is out of stock |
| **`n3-RTX-PRO6000-SEx1`** | `1× RTX-PRO6000-SE` (Blackwell) | **96 GB** | 28 | 225 GB | 100 GB | **3,300 GB** | `CANADA-1` | **`$1.85 / hr`** | **Yes** | 96 GB VRAM + 3.3 TB NVMe; requires CUDA 12.8+ / Blackwell kernel check (`[UNKNOWN / LIVE TEST REQUIRED]`) |
| **`n3-H100x1`** | `1× H100-80G-PCIe` | **80 GB** | 28 | 180 GB | 100 GB | **750 GB** | `CANADA-1` | **`$2.50 / hr`** | **Yes** | High-speed Hopper VM (`$0.09/hr` cheaper than RunPod H100 NVL `$2.59/hr`, with 750 GB free local NVMe) |
| **`H100 NVL 1×`** | `1× H100 NVL` | **94 GB** | 28 | 180 GB | 100 GB | **750 GB** | `CANADA-1` | **`$2.60 / hr`** | **Yes** | Matches RunPod H100 NVL (`94 GB` VRAM) |
| **`H100 SXM 1×`** | `1× H100-80G-SXM5` | **80 GB** | 24 | 225 GB | 100 GB | **750+ GB** | `CANADA-1`, `US-1` | **`$3.20 / hr`** | **Yes** | Maximum Hopper SXM bandwidth |
| **`n3-L40x1`** | `1× L40` (Ada) | **48 GB** | 28 | 58 GB | 100 GB | **725 GB** | `CANADA-1` | **`$1.00 / hr`** | **Yes** | Suitable for **isolated Qwen-Image-2.1** jobs (`Workload A`); **NOT sufficient for LTX-2.5 22B** |
| **`n3-RTX-A6000x1`** | `1× RTX-A6000` | **48 GB** | 28 | 58 GB | 100 GB | `0 GB` (100 GB root only on 1×) | `CANADA-1` | **`$0.50 / hr`** | **Yes** | Very cheap 48GB card for isolated Qwen/LoRA work, but 100 GB root disk is too small for LTX-2.5 (`119 GB`) without Large Root Disk flavor or SSV |
| **`n3-RTX-A4000x1`** | `1× RTX-A4000` | **16 GB** | 4 | 21 GB | 100 GB | `0 GB` | `NORWAY-1` | **`$0.15 / hr`** | **Yes** | Suitable only for lightweight `BiRefNet` / `Depth-Anything` / smoke tests; cannot run Qwen-Image-2.1 or LTX-2.5 |

### Additional Hyperstack Resource Charges ([Resource Pricing](https://docs.hyperstack.cloud/docs/billing/pricebook/) & [VM States and Billing](https://docs.hyperstack.cloud/docs/billing/states-and-billing/))
- **Public IP (`assign_floating_ip: true`):** **`$0.00672 / hr`** (`~$0.16 / day` or `~$5.00 / month`).
- **Shared Storage Volume (`Cloud-SSD`) & Hibernated Root Disk:** **`$0.000096774 / GB / hr`** (`~$0.07 / GB / month` = `$0.23 / day` for a `100 GB` hibernated root disk).
- **Ingress / Egress Bandwidth:** **`$0.00`** (free ingress and egress).

## 3. CRITICAL OPERATIONAL TRAP: `ACTIVE` vs `SHUTOFF` vs `HIBERNATED` (`[VERIFIED FACT]`)

Unlike RunPod (where `POST /pods/{id}/action {"action": "stop"}` transitions a pod to `EXITED` and stops GPU billing, charging only `$0.20/GB/month` for disk), **Hyperstack's `STOP` (`SHUTOFF`) state DOES NOT STOP GPU BILLING**:
- Per [VM States and Billing](https://docs.hyperstack.cloud/docs/billing/states-and-billing/) and [Hyperstack FAQ](https://docs.hyperstack.cloud/docs/faq/):
  - **`ACTIVE`**: Billed at 100% of GPU flavor + Public IP rate.
  - **`SHUTOFF` (via `GET /core/virtual-machines/{id}/stop` OR running `shutdown -h now` inside SSH!)**: **Billed at 100% of the full GPU flavor rate!** Hardware remains exclusively reserved.
  - **`HIBERNATED` (via `GET /core/virtual-machines/{id}/hibernate`)**: Deallocates GPU, CPU, RAM, and wipes the ephemeral disk; saves the `100 GB` root disk to persistent storage (`$0.000096774/GB/hr` = `$0.00968/hr` for 100 GB) and releases the Public IP by default (unless `retain_ip=true`).
  - **`DELETED` (via `DELETE /core/virtual-machines/{id}`)**: Permanently removes the VM and stops **all** billing (`$0.00/hr`).
  - **Transitional & Error States (`CREATING`, `BUILD`, `STARTING`, `STOPPING`, `HIBERNATING`, `RESTORING`, `DELETING`, `ERROR`)**: **Not Billed (`$0.00/hr`)**.

**Mandatory Adapter Safety Rule for Hyperstack (`explainer_engine/cloud/providers/hyperstack.py`):**
1. Our `stop_job()` / `self_stop()` equivalent on Hyperstack **MUST NEVER call `/stop` (`SHUTOFF`)** as a terminal cost-saving action!
2. Instead, `stop_job(mode="hibernate")` calls `GET /core/virtual-machines/{vm_id}/hibernate` (when root disk state is needed) or `DELETE /core/virtual-machines/{vm_id}` (after `cloud/store.py verify` confirms all outputs are in `vano1919/tmr-artifacts`), and **never runs `shutdown -h now` from inside the guest OS**.
3. All model weights (`160 GB`) on `n3-A100x1` / `n3-H100x1` should be stored on the **free `750 GB` ephemeral NVMe disk** during the run, while `$EE_OUT` is uploaded incrementally every 5 minutes to Hugging Face (`vano1919/tmr-artifacts`, `OR-33`), and the VM is **deleted (`DELETED`)** upon verified completion so zero `$0.23/day` root-disk charges linger.

## 4. Hyperstack REST API Specification (`infrahub-api.nexgencloud.com/v1`) (`[VERIFIED FACT]`)

- **Base URL:** `https://infrahub-api.nexgencloud.com/v1`
- **Authentication Header:** `api_key: <YOUR_HYPERSTACK_API_KEY>` (Note: header name is `api_key`, NOT `Authorization: Bearer`) ([Authentication Docs](https://docs.hyperstack.cloud/docs/api-reference/authentication/)).
- **Read-Only Inventory & Pricing Endpoints (Safe for Unattended Polling):**
  1. `GET /core/stocks` — Returns real-time and upcoming GPU stock by region and model ([Retrieve GPU Stocks](https://docs.hyperstack.cloud/docs/api-reference/get-gpu-stock/)).
  2. `GET /core/flavors?region={NORWAY-1|CANADA-1|US-1}` — Returns `{status: true, data: [{gpu, region_name, flavors: [{id, name, cpu, ram, disk, ephemeral, gpu, gpu_count, stock_available, features}]}]}` ([List Flavors](https://docs.hyperstack.cloud/docs/api-reference/list-flavors/)).
  3. `GET /pricebook` — Returns bare JSON array `[{id, name, value, original_value, discount_applied, start_time, end_time}]` ([Pricebook API](https://docs.hyperstack.cloud/docs/billing/pricebook/)).
  4. `GET /core/virtual-machines` — Lists existing VMs and their `status` (`CREATING`, `BUILD`, `ACTIVE`, `SHUTOFF`, `HIBERNATING`, `HIBERNATED`, `RESTORING`, `ERROR`, `DELETING`).
- **Lifecycle Mutation Endpoints (Disabled by Default Behind Approval Gates):**
  - `POST /core/virtual-machines` — Creates VM (`{name, environment_name, flavor_name, image_name, key_name, count: 1, assign_floating_ip: true, user_data: "<base64 cloud-init>"}`) ([Create VMs](https://docs.hyperstack.cloud/docs/api-reference/create-vms/)). Note: `user_data` max size is `65,535 bytes` base64-encoded (`pod_wrapper.sh` is `11,669 bytes`, which fits comfortably!).
  - `GET /core/virtual-machines/{vm_id}` — Retrieve VM details.
  - `GET /core/virtual-machines/{vm_id}/hibernate` — Hibernate VM (stops GPU billing).
  - `GET /core/virtual-machines/{vm_id}/restore` — Restore hibernated VM.
  - `DELETE /core/virtual-machines/{vm_id}` — Delete VM (stops all billing).
- **SDK, Terraform & MCP Maturity:**
  - Official Python SDK (`pip install hyperstack`, `NexGenCloud/hyperstack-sdk-python` `v1.56.0-alpha`, OpenAPI-generated) and Terraform Provider (`NexGenCloud/terraform-provider-hyperstack`) are both explicitly marked **Alpha** ([Python SDK Docs](https://docs.hyperstack.cloud/docs/libraries/python/), [Terraform Docs](https://docs.hyperstack.cloud/docs/libraries/terraform/)). Therefore, just like `explainer_engine/cloud/runpod.py`, our adapter uses **zero-dependency Python `urllib.request` stdlib** against the documented REST v1 endpoints!
  - Hyperstack documentation also exposes a remote read-only **MCP server** at `docs.hyperstack.cloud` (`Connect via MCP` button on docs pages) for querying documentation ([APIs.io NexGen Cloud](https://apis.io/providers/nexgen-cloud/)).
