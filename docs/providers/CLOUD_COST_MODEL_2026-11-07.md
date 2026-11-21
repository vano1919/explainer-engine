# Cloud cost model — Hyperstack, Modal and RunPod baseline

**Snapshot date:** 2026-11-07  
**Working branch:** `icw/21-mouth-job`  
**Currency:** USD  
**Purpose:** compare infrastructure costs for the active D-116 Ink Chronicle route. This is a pricing model, not a production forecast.

## 1. Current project constraints

The active route is:
- Qwen-Image-2.1 + `xworld_v2` for scene assets and first frames.
- Blender for world/camera/2.5D/crowds/layout passes and J5.
- LTX-2.5 / LTX-2.3 for J2/J4 motion.
- BiRefNet for cut-outs; Python/FFmpeg for helper/assembly/QA.

The repository's target of $10–15 per 12–15-minute episode is not yet proven on the new D-116 route. The route still needs benchmarked GPU seconds, peak VRAM, model cold-start and failure/retry rates.

This file does not change `config/spend_caps.json`. There are no approved Hyperstack or Modal spend caps yet. The existing `runpod` budget may not be reused for either service.

## 2. Public GPU price comparison (2026-11-07)

| Provider | GPU | VRAM | $/GPU-hour | 1h | 3h | 5h |
|---|---|---:|---:|---:|---:|---:|
| Hyperstack | A6000 | 48 GB | $0.50 | $0.50 | $1.50 | $2.50 |
| Hyperstack | L40 | 48 GB | $1.00 | $1.00 | $3.00 | $5.00 |
| Hyperstack | A100 | 80 GB | $1.35 | $1.35 | $4.05 | $6.75 |
| Hyperstack | A100 NVLink | 80 GB | $1.40 | $1.40 | $4.20 | $7.00 |
| Hyperstack | RTX Pro 6000 SE | 96 GB | $1.85 | $1.85 | $5.55 | $9.25 |
| Hyperstack | H100 | 80 GB | $2.50 | $2.50 | $7.50 | $12.50 |
| Hyperstack | H100 NVLink | 80 GB | $2.60 | $2.60 | $7.80 | $13.00 |
| Hyperstack | H100 SXM | 80 GB | $3.20 | $3.20 | $9.60 | $16.00 |
| Modal | L40S | 48 GB | $1.9512 | $1.95 | $5.85 | $9.76 |
| Modal | A100 40 GB | 40 GB | $2.0988 | $2.10 | $6.30 | $10.49 |
| Modal | A100 80 GB | 80 GB | $2.4984 | $2.50 | $7.50 | $12.49 |
| Modal | H100 SXM5 | 80 GB | $3.9492 | $3.95 | $11.85 | $19.75 |

Hyperstack public GPU prices are billed per minute, although displayed as hourly rates. GPU flavor CPU/RAM/root+ephemeral local disk are included; attached IP and storage volumes are separate. Modal is metered per second for GPU, CPU and RAM, and uses a default 60-second scale-down window after the last input.

Prices are public list prices, not guarantees of account-specific discounts, stock or deployable flavor. Re-check live account Pricebook and stock before any spend.

## 3. Hyperstack additional resource costs

| Resource | Public price | Approximate monthly arithmetic |
|---|---:|---:|
| Public IP | $0.00672043/hour | $4.91 per 730 hours |
| SSV | $0.000096774 per GB-hour | $0.0706 per GB-month; 100 GB ≈ $7.06/month |
| Object Storage | $0.000019397 per GB-hour | about $14.29/TB-month |
| Egress / ingress | Public pricing page lists free | Recheck account terms |

A Hyperstack VM in SHUTOFF remains fully billed. Hibernate releases GPU/CPU/RAM but storage and any retained IP continue billing. SSVs can bill while unattached/reserved. Hyperstack Object Storage is currently Canada-only and has no cross-region replication; the HF D-73 vault remains canonical.

## 4. Modal credits and costs

Starter:
- $0 monthly base price + compute.
- $30/month compute credit.
- 10 GPU concurrency, 100 containers, 3 seats.
- 1 TiB/month included egress.
- Credits cover Functions/Sandboxes CPU+RAM+GPU compute, not Shared Endpoint token billing.

Rate table:
- L40S: $0.000542 per GPU-second.
- A100 80 GB: $0.000694 per GPU-second.
- H100 SXM5: $0.001097 per GPU-second.
- CPU: $0.0000131 per physical-core-second.
- RAM: $0.00000222 per GiB-second.
- Volume: $0.09/GiB-month, with 1 TiB/month included on Starter.
- Egress beyond included allowance: $0.04/GiB.

Example only, 5 hours on A100 80 GB:
- GPU = 5 × 3600 × $0.000694 = $12.49.
- If the container allocates 16 physical cores for all 5 hours, CPU = $3.77.
- If it allocates 64 GiB RAM for all 5 hours, memory = $2.56.
- Illustrative total = $18.82, within the $30 credit if no other monthly compute consumes it.

This example is not a resource recommendation. CPU/RAM charges depend on actual requested/used resources and runtime.

## 5. Hyperstack AI Studio token and image costs

Public token examples checked 2026-11-07, per 1M tokens:

| Model | Input / 1M | Output / 1M |
|---|---:|---:|
| Llama 3.1 8B | $0.20 | $0.20 |
| Mistral Small 3 | $0.40 | $0.40 |
| Llama 3.3 70B | $0.80 | $0.80 |
| OpenAI gpt-oss-120b | $0.10 | $0.40 |

For 5M input + 1M output:
- Llama 3.1 8B ≈ $1.20.
- Mistral Small 3 ≈ $2.40.
- Llama 3.3 70B ≈ $4.80.
- gpt-oss-120b ≈ $0.90.

Text formula:
`input_tokens / 1,000,000 × input_rate + output_tokens / 1,000,000 × output_rate`.

AI Studio image generation/editing uses per-16×16 patch billing. Approximate patch counts are 4,096 for 1024², 6,144 for 1536×1024 and 14,400 for 2560×1440. The live price per patch varies by model and must be read from AI Studio → Inference → Vision Models / account Pricebook. Do not forecast image API costs without the exact model and patch rate.

AI Studio model API requests are served through external providers. Their terms/data handling and availability must be checked before sending unreleased project scripts or assets. The catalogue lists image models such as Qwen-Image, Qwen-Image-2512 and Z-Image-Turbo, but does not prove support for the exact `Qwen-Image-2.1 + xworld_v2` combination or LTX video generation.

## 6. Example run budgets

GPU-only cost by one-GPU wall-clock duration:

| Scenario | Hyperstack A100 | Hyperstack H100 | Modal A100 |
|---|---:|---:|---:|
| 30 min isolated smoke | $0.68 | $1.25 | $1.25 |
| 1h isolated stage | $1.35 | $2.50 | $2.50 |
| 3h multi-stage test | $4.05 | $7.50 | $7.50 |
| 5h long job | $6.75 | $12.50 | $12.49 |

For the Hyperstack 5h A100 example, add ≈$0.034 for a 5h public IP and ≈$0.048 for a 100GB SSV used for those same 5h. If that SSV is left allocated after the job, it continues billing ≈$7.06/month.

For Modal, a 5h A100 GPU-only run is $12.49, but CPU/RAM runtime is extra. The compute credit can reduce out-of-pocket cost if still available. Shared Endpoint tokens are charged separately and do not draw on the $30 credit.

These scenarios are price arithmetic, not end-to-end pipeline measurements. They omit startup, downloads, idle scale-down, CPU/RAM, retries, uploads and failures unless stated.

## 7. Cost model for one D-116 episode

The only defensible equation until the current route is benchmarked:

`Episode_USD = Σ(provider rate × measured active seconds / 3600) + CPU/RAM + setup/download + storage + public IP + retries + token/patch API usage`.

Collect these values separately:
- Qwen image-generation seconds and count of images.
- BiRefNet image count and seconds.
- LTX seconds per clip by model/base/route and resolution.
- Blender CPU/GPU seconds by pass; do not include creator PC/CI work as paid cloud compute.
- Weight-download and dependency-install time.
- Wait/idle time caused by dependency scheduling.
- Upload throughput, retries and the cost of recovery.
- Actual provider-billed amounts vs the project ledger.

The old cost table in `docs/COST_AND_TIME_MODEL.md` is a legacy estimate based on earlier LTX assumptions. It is not a reliable D-116 LTX-2.5/2.3 benchmark. The current branch's route plan also explicitly labels the $10–15 target as estimated/unproven.

## 8. Recommendation

**Current choice: retain RunPod as the existing integrated execution path; benchmark Hyperstack A100 80 GB first; test Modal when scale-to-zero and the $30 credits can offset sporadic workload.**

Why:
- Hyperstack A100 80GB's $1.35/h is about 46% below Modal A100 80GB's $2.4984/h before CPU/RAM and ancillary charges.
- Modal's advantage is scale-to-zero, reusable container functions, autoscaling and Starter credits. It can win where RunPod/Hyperstack idle reservations or persistent VMs would be billed.
- Hyperstack AI Studio is the most direct route for cheap token-priced LLM/VLM use, but should not replace our custom Qwen/LTX jobs without exact feature, licence, privacy and output QA proof.
- A 48GB card may be cheaper but has no verified fit for the full p14 stack.
- A new cloud adapter costs engineering effort and requires an external watchdog; do not duplicate the whole project manager for a small price difference without measured savings.

## 9. Sources

- [Hyperstack public GPU pricing](https://www.hyperstack.cloud/gpu-pricing)
- [Hyperstack resource Pricebook](https://docs.hyperstack.cloud/docs/billing/pricebook/)
- [Hyperstack VM billing states](https://docs.hyperstack.cloud/docs/virtual-machines/manage-vm-state/)
- [Hyperstack live GPU stock](https://docs.hyperstack.cloud/docs/hardware/gpu-stock-information/)
- [Hyperstack AI Studio model list](https://docs.hyperstack.cloud/docs/ai-studio/models/models-overview/)
- [Hyperstack AI Studio billing](https://docs.hyperstack.cloud/docs/ai-studio/billing/)
- [Hyperstack object storage](https://docs.hyperstack.cloud/docs/storage/object-storage/)
- [Modal pricing](https://modal.com/pricing)
- [Modal Volume reference](https://modal.com/docs/sdk/py/latest/Volume)
- [Modal Function reference](https://modal.com/docs/sdk/py/latest/Function)
- [Modal skills CLI](https://modal.com/docs/cli/latest/skills)

