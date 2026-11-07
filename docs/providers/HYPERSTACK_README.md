# Hyperstack for Ink Chronicle — platform and migration reference

**Research snapshot:** 2026-11-07  
**Repository branch:** `icw/21-mouth-job`  
**Current route:** D-116 / Qwen-Image-2.1 → Blender → LTX-2.5/2.3 → FFmpeg  
**Status:** research/documentation only. No Hyperstack resource was created and no paid test was run.

## Executive decision

Hyperstack is a credible lower-hourly-cost alternative for custom GPU jobs. It is not a drop-in replacement for RunPod's manager.

- For custom Qwen/LTX Python/CUDA workloads, use a normal **GPU VM**. This is the only Hyperstack product in this comparison that lets the project run arbitrary pinned code, models, LoRAs and stage scripts.
- For short text generation, summaries, research support, vision review and selected image APIs, consider **AI Studio Partner API**. It is billed per token or image patch and may be convenient, but its models are served through external provider integrations.
- **Dedicated Inference** is a private vLLM LLM endpoint on reserved GPUs, billed per hour. It is not token-priced, not serverless, and does not run arbitrary Diffusion/LTX workloads.
- Do not retire RunPod until the adapter, billing, watchdog, resume, hash-storage and recovery requirements in `.claude/rules/cloud-platforms.md` are implemented and tested.

Official entry points:
- [Hyperstack GPU pricing](https://www.hyperstack.cloud/gpu-pricing)
- [Hyperstack docs](https://docs.hyperstack.cloud/)
- [Docs index for agents](https://docs.hyperstack.cloud/llms.txt)
- [GPU stock API guide](https://docs.hyperstack.cloud/docs/hardware/gpu-stock-information/)
- [Core API OpenAPI](https://docs.hyperstack.cloud/openapi/hyperstack.json)
- [AI Studio API OpenAPI](https://docs.hyperstack.cloud/openapi/ai-studio.json)
- [AI Studio model catalogue](https://docs.hyperstack.cloud/docs/ai-studio/models/models-overview/)
- [Agent-friendly docs](https://docs.hyperstack.cloud/docs/libraries/agent-docs/)

## 1. What Hyperstack offers

| Product | Billing unit | What runs | Fit for Ink Chronicle |
|---|---|---|---|
| GPU VM | GPU-hour, billed per minute | Arbitrary Docker/Python/CUDA code | **Primary candidate** for Qwen/LTX jobs |
| CPU VM | CPU/RAM/disk resources per hour | CPU-only services, build, utilities | Not needed for jobs that already run free on PC/CI |
| AI Studio Partner API | Per 1M input/output tokens; images per 16×16 patch | Models served through external partners | Useful for selected text/VLM/image API tasks, not custom Qwen/LTX |
| Dedicated Inference | GPU-hour | One open-weight LLM on vLLM behind private API | Only consider for an always-on private LLM; unlikely to be economical for current intermittent use |
| Kubernetes | Worker-node resources | Multi-node container orchestration | Premature for a solo creator's episodic pipeline |
| Shared Storage Volume (SSV) | GB-hour | Persistent block/file data attached to VM | Optional cache; costs while detached/reserved too |
| Object Storage | GB-hour | S3-compatible object storage | Optional cache/secondary copy, not the canonical vault |

The word “AI” in AI Studio does not imply that every model is loaded on a GPU you own. Partner API inference is routed through external provider integrations. Hyperstack's model docs explicitly warn that availability, pricing and provider data handling can change.

## 2. GPU VM pricing and selection

Official public on-demand prices checked 2026-11-07:

| GPU | VRAM | Public price / GPU-hour | 1 hour | 3 hours | 5 hours | Candidate use |
|---|---:|---:|---:|---:|---:|---|
| A4000 | 16 GB | $0.15 | $0.15 | $0.45 | $0.75 | Too small for current Qwen/LTX stack |
| A6000 | 48 GB | $0.50 | $0.50 | $1.50 | $2.50 | Isolated Qwen/asset tests only until measured |
| L40 | 48 GB | $1.00 | $1.00 | $3.00 | $5.00 | Candidate isolated tests; not assumed to fit full p14 |
| A100 80 GB | 80 GB | $1.35 | $1.35 | $4.05 | $6.75 | Best starting candidate for full pipeline pilot |
| A100 NVLink | 80 GB | $1.40 | $1.40 | $4.20 | $7.00 | Test only if multi-GPU/interconnect matters |
| A100 SXM | 80 GB | $1.60 | $1.60 | $4.80 | $8.00 | Compare on measured throughput |
| RTX Pro 6000 SE | 96 GB | $1.85 | $1.85 | $5.55 | $9.25 | Interesting VRAM headroom candidate |
| H100 PCIe | 80 GB | $2.50 | $2.50 | $7.50 | $12.50 | Benchmark against A100; may finish sooner |
| H100 NVLink | 80 GB | $2.60 | $2.60 | $7.80 | $13.00 | Multi-GPU/interconnect use only if needed |
| H100 SXM | 80 GB | $3.20 | $3.20 | $9.60 | $16.00 | Faster, but only worth it if job cost falls |
| H200 SXM | 141 GB | $3.99 | $3.99 | $11.97 | $19.95 | Likely excessive until benchmark proves need |

Rates are per GPU. A multi-GPU flavor multiplies the GPU rate by its GPU count. On GPU flavors, allocated CPU, RAM and root/ephemeral local disk are included in the GPU rate; attached public IP and SSV are separate charges. Public prices are not a guarantee of the account's final rate: retrieve the account's Pricebook and inspect the deployment price breakdown.

### Spot rates

The public page lists the following Spot rates: A6000 $0.40/h, A100 $1.08/h, H100 PCIe $2.00/h, RTX Pro 6000 SE $1.48/h and L40 $0.80/h. Spot capacity can be reclaimed. Use Spot only for checkpointed/resumable work with proven output uploads and retry behavior; don't make it the first production route.

### Reserved rates

Reservation prices can be materially lower (the public table currently lists A100 from $0.95/h and A6000 from $0.35/h), but reservation implies an availability/commitment trade-off. Do not reserve before at least several weeks of measured utilization establish a predictable base load.

### Which GPU should the project test?

The active p14 job combines large Qwen image weights, BiRefNet, and LTX-2.5/2.3 with additional text encoders and VAEs. A 48 GB card may not fit the combined working set without offload/quantization. The previous test selected an H100 NVL and the new route has not yet produced a measured current LTX clip speed. Therefore:

1. Start a paid comparison with A100 80 GB as the cost baseline.
2. Compare H100 80 GB only if the job completes materially faster or more reliably.
3. Do not select A6000 solely because it is $0.50/h; first prove the exact stage fits, with peak VRAM and no CPU offload stall.
4. For Qwen-only and BiRefNet-only tasks, create separate measured resource profiles if the stage graph allows those to run independently.

## 3. VM regions, stock and provisioning

Hyperstack publishes regions including `CANADA-1`, `NORWAY-1` and `US-1`. GPU stock is live and varies by GPU model, region and requested GPU count. The stock page refreshes at least every 30 seconds.

The project must query stock immediately before every deployment:
```bash
curl -fsS "https://infrahub-api.nexgencloud.com/v1/core/stocks" \
  -H "accept: application/json" \
  -H "api_key: $HYPERSTACK_API_KEY"
```

A flavor appearing in the Pricebook does not mean it can be deployed now. Use the live stock API or console's Deploy VM flow, check exact region/flavor/GPU count, then read the resulting deployment price breakdown.

Recommended OS image for custom workloads: Ubuntu Server 24.04 LTS with NVIDIA driver/CUDA and Docker already installed (for example an R570/CUDA 12.8 image with Docker). Confirm the host's driver/CUDA compatibility against the exact project's pinned PyTorch, Diffusers/VideoX-Fun, LTX and Blender versions; do not upgrade the entire environment to latest packages on a production job.

Hyperstack documents preinstalled Docker Engine, Docker Compose plugin and NVIDIA Container Toolkit on its Docker images. Verify `nvidia-smi`, `docker run --gpus all ... nvidia-smi`, PyTorch CUDA allocation and a real tiny kernel before any model load.

## 4. Hyperstack billing semantics — highest-risk differences from RunPod

The pricing docs say resources are charged for the time they exist, not just when code is actively using them.

| State/resource | Billing behavior | Project rule |
|---|---|---|
| VM ACTIVE | GPU flavor billed | Normal work state |
| VM SHUTOFF | GPU/CPU/RAM remain reserved and billed at running rate | **Never use Stop as an idle-cost solution** |
| VM HIBERNATED | GPU/CPU/RAM released; saved storage and retained public IP still bill | Preferred pause for a reusable VM, after durable outputs are stored |
| VM DELETE | Billing stops; local VM data is destroyed | Explicit creator approval only |
| SSV AVAILABLE / IN-USE / RESERVED | Bills by GB-hour, even unattached/reserved | Inventory and account for every volume |
| Snapshot | Bills for consumed Cloud-SSD storage | Delete only with creator's approval |
| Public IP | Additional hourly charge | Release unless approved use requires it |
| Object Storage | Bills stored GB-hour | Separate from VM compute |

Current additional public list prices:
- Public IP: $0.00672043/hour (about $4.91 per 730-hour month).
- SSV: $0.000096774 per GB-hour (about $0.0706/GB-month; 100 GB ≈ $7.06/month).
- Egress/ingress: listed as free on the public pricing page.
- Object Storage: $0.000019397 per GB-hour (about $14.29/TB-month).

**Hibernate is not free:** local root data is preserved as storage, and any retained IP/SSV is still billed. The VM's ephemeral disk is released and its data is lost. On restore, the same flavor must be available; capacity is not guaranteed. Hibernation may release the public IP unless it is explicitly retained, and a new IP may be allocated on restore. Dedicated Inference has hibernate/snapshot disabled. Delete the VM only if the run is complete, all outputs are in the vault, and the creator explicitly authorizes deletion.

At zero balance, Hyperstack may hibernate compatible VMs; the docs describe a 30-day retention window before resources can be deleted if the balance is not restored. Do not rely on this as a job stop mechanism.

## 5. AI Studio: models, APIs, price and limits

### 5.1 Token-priced Partner API

AI Studio exposes an OpenAI-compatible API:
- Base URL: `https://console.hyperstack.cloud/ai/api/v1`
- Authentication header: `api_key: $HYPERSTACK_AI_API_KEY` (no `Bearer` prefix).
- First call: `POST /chat/completions`.
- The current docs say the same key works for Core Hyperstack and AI Studio APIs. Keep it in a secret store.

Example request:
```bash
curl -fsS "https://console.hyperstack.cloud/ai/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "api_key: $HYPERSTACK_AI_API_KEY" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [{"role": "user", "content": "Summarise the scene outline in 5 bullets."}],
    "stream": true
  }'
```

The public pricing page, checked 2026-11-07, lists these example rates per 1M tokens:

| Model | Input / 1M | Output / 1M |
|---|---:|---:|
| Llama 3.1 8B | $0.20 | $0.20 |
| Mistral Small 3 | $0.40 | $0.40 |
| Llama 3.3 70B | $0.80 | $0.80 |
| OpenAI gpt-oss-120b | $0.10 | $0.40 |

Example arithmetic for a workload that uses 5M input tokens and 1M output tokens:
- Llama 3.1 8B: $1.20.
- Mistral Small 3: $2.40.
- Llama 3.3 70B: $4.80.
- gpt-oss-120b: $0.90.

Formula:
`USD = input_tokens / 1,000,000 × input_rate + output_tokens / 1,000,000 × output_rate`.

The full live model/rate list is in AI Studio → Inference → Models, and the Pricebook API also returns entries suffixed `(input)` and `(output)`. Rates in a docs list are snapshots; always query current account pricing before a paid call.

### 5.2 What models are listed

The docs' model catalogue (last updated 2026-09-24; availability is dynamic) shows:
- Text models: several Qwen 2.5/3.x/3.5 families, DeepSeek, Gemma, Llama, GLM and other open-weight models.
- Image-to-text/VLM: Gemma, Qwen-VL and several other vision-language models.
- Text-to-image: FLUX.1, Qwen-Image, Qwen-Image-2512, Z-Image-Turbo, HunyuanImage-3, CogView and SD3.5 variants.
- Image-to-image: editing models, including Qwen-Image-Edit families and other editors (check the live catalogue for current IDs).

The model catalogue does **not** list a video-generation modality. It does not prove support for our exact `Qwen-Image-2.1 + xworld_v2` model/adapter, the repository's custom BiRefNet cut-out setup, or LTX-2.5/2.3.

### 5.3 Image API billing: patches, not tokens

Image generation/editing is charged per 16×16 output patch (256 pixels per patch), with the price per patch varying by model. The per-model amount is visible in AI Studio → Inference → Vision Models. It is not a universal fixed price per image.

Approximate patch counts:
- 1024×1024: 4,096 patches.
- 1536×1024: 6,144 patches.
- 2560×1440: 14,400 patches.

Formula:
`image_cost = generated_patch_count × selected_model_price_per_patch`.

Do not quote an image-generation cost until the exact model, resolution, number of outputs and price/patch are read from the live account. Compare mode can call multiple models and multiplies cost accordingly.

### 5.4 Fine-tuning line

The public pricing page currently lists fine-tuning at $0.063/minute. It does **not** prove that the fine-tuning product trains the exact custom image LoRA `xworld_v2`, or that it supports the repository's data, model base, rank, alpha, steps or optimizer. Do not use this rate to estimate our LoRA training without confirming the exact fine-tuning workflow and supported model.

### 5.5 Privacy and provider dependency

AI Studio docs say Partner API models are delivered through external provider integrations. Requests may be processed by external providers, and model availability, reliability, pricing and data handling depend on the provider. Before sending unreleased scripts, private assets, unpublished characters or sensitive project prompts:
- identify the provider for the selected model;
- read its data retention / training / abuse-monitoring terms;
- check commercial-use permissions and output rights;
- review endpoint region and data residency;
- do not send restricted assets until approved.

## 6. Dedicated Inference

Dedicated Inference:
- Deploys one open-weight LLM onto reserved GPUs.
- Uses a Hyperstack-managed VM, vLLM runtime, generated HTTPS hostname and endpoint API key.
- Downloads model weights from Hugging Face on first boot; an HF token is needed for private/gated weights.
- Fits hardware based on model weights, KV cache (context length × concurrency) and serving overhead. The wizard uses around 90% of advertised VRAM as usable.
- Allows context lengths 4,096–32,768 tokens and concurrency 1–32 in the wizard.
- Bills hourly as long as GPU resources run; it is not a pay-per-token serverless API.
- Does not support hibernate/snapshot for the underlying endpoint VM.

Endpoint requests use:
`POST https://<endpoint-host>.ai.hyperstackcustomers.cloud/v1/chat/completions`
with `Authorization: Bearer <dedicated-endpoint-key>`.

The key is separate from the AI Studio API key. Anyone with the key can use the model, and the reserved GPU bills even when the endpoint gets no requests.

**Ink Chronicle verdict:** not a good first choice for an episodic project with intermittent LLM calls. Use AI Studio token billing for simple text work, or a short VM/Modal function when custom open weights or code are required. Do not leave a dedicated endpoint running as a convenience service without a measured utilisation and approved monthly cap.

## 7. API and agent integration

### 7.1 Public, read-only Docs MCP

The official Docs MCP is a public, read-only Streamable HTTP server:
`https://docs.hyperstack.cloud/mcp`

Claude Code:
```bash
claude mcp add --transport http hyperstack-docs https://docs.hyperstack.cloud/mcp
claude mcp list
```

It exposes documentation lookup tools (search docs, retrieve page, list sections, lookup errors, retrieve flavor info). It does not need account OAuth and cannot create a VM. Any docs page can also be fetched as Markdown by adding `.md` or `.txt` to the path. Official skill:
- Index: `https://docs.hyperstack.cloud/.well-known/agent-skills/index.json`
- Skill: `https://docs.hyperstack.cloud/.well-known/agent-skills/hyperstack/SKILL.md`

A skill can be downloaded into the relevant Claude Code skills directory after review. It is a knowledge skill, not a permission to operate the account.

### 7.2 Account-control Hyperstack MCP

The separate account MCP is:
`https://console.hyperstack.cloud/ai/mcp`

Claude Code connection:
```bash
claude mcp add --transport http hyperstack-mcp https://console.hyperstack.cloud/ai/mcp
claude mcp list
```

It authenticates through browser OAuth and can query usage/billing, list VMs/volumes and perform live changes such as VM or volume creation/deletion, clusters and environment actions. Treat it as a privileged operator:
- use only read-only inventory/stock/price/billing calls for reconnaissance;
- no resource creation, reboot, hibernate, snapshot, deletion or resize unless OR-23/OR-34 and creator approval pass;
- do not allow it to bypass the project ledger or current provider adapter;
- do not grant it secrets or upload project files through an agent prompt without approval.

### 7.3 Core API

- Base: `https://infrahub-api.nexgencloud.com/v1`.
- Authentication: header `api_key: <key>`.
- Pricebook: `GET /pricebook`.
- Stock: `GET /core/stocks`.
- Core OpenAPI: [hyperstack.json](https://docs.hyperstack.cloud/openapi/hyperstack.json).

The account Pricebook contains rates for GPU resources, SSV, PublicIP, ObjectStorage and AI Studio input/output model units. Account `value` is the charge rate; `original_value` and `discount_applied` may also appear. A pricebook GPU entry is not proof of live stock.

### 7.4 Docker and CUDA

The official Ubuntu CUDA + Docker VM image includes NVIDIA driver, CUDA toolkit, Docker and NVIDIA Container Toolkit. The project job still needs a boot-time smoke test:
```bash
nvidia-smi
docker run --rm --gpus all <approved-cuda-image> nvidia-smi
python -c "import torch; x=torch.ones(8, device='cuda'); print(torch.cuda.get_device_name(0), (x * 2).sum().item(), torch.cuda.get_device_properties(0).total_memory / 2**30)"
```

This verifies GPU exposure and an actual CUDA operation; `nvidia-smi` alone is insufficient.

## 8. Storage and the project vault

The creator's current canonical project vault is the private Hugging Face dataset `vano1919/tmr-artifacts` (D-73). Keep it as the primary copy.

Hyperstack Object Storage:
- S3-compatible endpoint: `ca1.obj.nexgencloud.io`.
- Currently only in `CANADA-1`.
- Public rate: $0.000019397/GB-hour (about $14.29/TB-month).
- No multi-region replication / regional redundancy is currently documented.
- Supports Boto3, S3cmd and MinIO with a key/secret pair. The secret is shown only once at key creation.

Use only for a disposable model cache, re-creatable batch cache or explicitly approved secondary copy. Do not relocate the only output copy or the D-73 vault to a single-region bucket. For every paid run, upload outputs as generated, hash-check them in the HF vault, and only then release the GPU.

SSV differs from object storage: it is persistent block storage, can be attached to VMs, and is billed even when unattached/reserved. A retained volume can be expensive over time and can constrain region/GPU scheduling.

## 9. Cost estimates for the current workload

GPU-only arithmetic, public list rates, before per-minute rounding and excluding startup, model download, CPU-only VM, SSV, public IP, retries and token/patch costs:

| Job duration on one GPU | Hyperstack A100 80 GB ($1.35/h) | Hyperstack H100 80 GB ($2.50/h) | Modal A100 80 GB ($2.4984/h) |
|---:|---:|---:|---:|
| 30 min | $0.68 | $1.25 | $1.25 |
| 1 hour | $1.35 | $2.50 | $2.50 |
| 2 hours | $2.70 | $5.00 | $5.00 |
| 3 hours | $4.05 | $7.50 | $7.50 |
| 5 hours | $6.75 | $12.50 | $12.49 |

Hyperstack A100 80 GB example, 5 hours:
- GPU: $6.75.
- Public IP if attached for five hours: about $0.034.
- 100 GB SSV for five hours: about $0.048, but then about $7.06/month if left allocated.
- Approximate temporary total: $6.83 before storage lifecycle, boot, and any extra retries.

Dedicated Inference A100 80 GB left running 24/7 for 730 hours would be about $985.50 GPU compute plus about $4.91/month for a retained public IP, before storage. That is why it is not the right pattern for low-volume sporadic model calls.

AI Studio example, 5M input + 1M output tokens: costs $0.90–$4.80 using the four public model rates in section 5.1. The model's actual quality and the provider terms still need an A/B test.

**Episode cost is not yet proven.** The 12–15-minute Ink Chronicle target is $10–15, but the current D-116 route still needs a measured full pipeline benchmark. Use:
`GPU_USD = GPU_rate × (Qwen_GPU_seconds + LTX_GPU_seconds + other_GPU_seconds) / 3600`
then add boot/warm-up, model download, CPU, retries, public IP/SSV, image patch/token charges and storage. Record actual per-job seconds in `config/job_speeds.json`; don't reuse the older LTX 200s/clip estimate as a measured D-116 value.

## 10. Recommended test sequence (no run authorised by this document)

1. Read the account's Pricebook and live stock for A100 80 GB and H100 80 GB in each eligible region.
2. Verify the available Ubuntu 24.04 CUDA/Docker image and exact flavor CPU/RAM/disk specs.
3. Build a provider-specific adapter proposal, lifecycle table and cost guard. Do not call VM create from the current RunPod manager.
4. Dry-run the exact p14 stage graph from the new branch. Confirm dependency scheduling prevents idle GPU waiting for CPU outputs.
5. Prepare an OR-23 plan with model revisions, SHA256 pins, settings, time/cost caps, vault output prefixes and watchdog.
6. Get the OR-34 Fable audit PASS and all required approvals.
7. Run one smallest useful paid smoke: CUDA kernel, HF download, Qwen isolated job, LTX isolated clip, then full graph only if each gate passes.
8. Measure stage seconds, peak VRAM, wall-clock, idle time, failure rate, retries, billed cost and storage. Compare to the current RunPod baseline.
9. Accept Hyperstack only if measured cost/reliability, output QA and recovery are better enough to justify maintaining a second adapter.

## 11. Official source register

- [GPU pricing and GPU VRAM](https://www.hyperstack.cloud/gpu-pricing)
- [Resource Pricebook and billing](https://docs.hyperstack.cloud/docs/billing/pricebook/)
- [VM lifecycle and billing states](https://docs.hyperstack.cloud/docs/virtual-machines/manage-vm-state/)
- [Virtual machine features](https://docs.hyperstack.cloud/docs/virtual-machines/virtual-machine-features/)
- [GPU stock and stock API](https://docs.hyperstack.cloud/docs/hardware/gpu-stock-information/)
- [Docker GPU VM guide](https://docs.hyperstack.cloud/docs/tutorials/docker-support/)
- [AI Studio billing](https://docs.hyperstack.cloud/docs/ai-studio/billing/)
- [AI Studio models](https://docs.hyperstack.cloud/docs/ai-studio/models/models-overview/)
- [AI Studio API quickstart](https://docs.hyperstack.cloud/docs/ai-studio-api-reference/quickstart/)
- [Dedicated Inference](https://docs.hyperstack.cloud/docs/ai-studio/dedicated-inference/)
- [vLLM on a GPU VM](https://docs.hyperstack.cloud/docs/tutorials/vllm/)
- [Agent-friendly docs and read-only MCP](https://docs.hyperstack.cloud/docs/libraries/agent-docs/)
- [Account-control MCP](https://docs.hyperstack.cloud/docs/libraries/mcp-server/)
- [S3 Object Storage](https://docs.hyperstack.cloud/docs/storage/object-storage/)

