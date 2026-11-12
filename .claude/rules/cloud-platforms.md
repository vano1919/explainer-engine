# Cloud platform execution rules — Ink Chronicle

> Route-scoped since D-116 (2026-11-06): the route lines below describe the D-116 Qwen/LTX/Blender route; the v4.3 rebuild (2026-11-12) replaces the route, and the money and lifecycle rules stay in force.

**Canonical operating policy for every Claude Code agent using paid cloud infrastructure.**
Applies to the current Ink Chronicle route D-116 and its future provider adapters. Read this file before any cloud, GPU, model-hosting, token API, storage, or agent-MCP action.

## 1. Current architecture and what is actually integrated

The active production route is D-116, not the legacy still-picture route:

- Qwen-Image-2.1 + `xworld_v2` draws the visual identity, scene assets and first frames.
- Blender builds space and time: camera, 360-degree environments, 2.5D cards, crowds, rigs, clay/depth/line layouts and J5 renders.
- LTX-2.5 / LTX-2.3 generates motion only for the J2/J4 route types.
- Python and FFmpeg handle helper graphics, cut-outs, QA and final assembly.
- The route for every archetype is authoritative in `explainer_engine/visual/archetypes_ic.json`; the explanatory matrix is `docs/architecture/ROUTE_PLAN_2026-11-06.md`.

**Current provider status:** the repository currently has a RunPod-specific manager in `explainer_engine/cloud/runpod.py`. `cloud/jobs.py` has provider-neutral job-state concepts, but `cloud/watchdog.py`, the pod wrapper, billing guard and provider lifecycle remain RunPod-specific. Hyperstack and Modal are researched candidates, not implemented adapters. Do not claim that a Hyperstack or Modal resource can be launched safely through the current project manager.

Do not replace the active visual route or move any production job to a new provider just because its hourly list price is lower.

## 2. Source-of-truth order

Use this order when resolving conflicts:

1. Creator's latest explicit decision and approval.
2. Current branch's `CLAUDE.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/ORCHESTRATION.md`, `docs/CONTRACTS.md`, `docs/COST_AND_TIME_MODEL.md`, and current D-116 route documents.
3. This file for cloud-provider policy.
4. Current provider's official docs, OpenAPI, account Pricebook, live stock and billing data.
5. Third-party comparisons only as secondary evidence.

Never copy an old RunPod rule to Hyperstack or Modal without checking the destination provider's lifecycle and billing semantics. Mark every price with a check date and whether it is official list price, account price, measured cost, or estimate.

## 3. Decision gates before any paid action

Every paid action, including a VM, serverless function, dedicated endpoint, AI Studio API request, image generation, fine-tuning, volume, object storage, public IP, snapshot, or egress charge, must pass all applicable gates:

- **OR-22:** do not guess model, revision, LoRA, dataset, settings, resource class, region, cost or stop behavior. List unresolved items.
- **OR-23:** before a VM/pod/endpoint or material batch, show the exact plan: job purpose, question answered, route/archetype, stage graph, exact model + revision + LoRA + SHA256, input files + hashes, every generation/render setting, GPU/VRAM/RAM/CPU/disk/region, expected startup/download/work/upload time, cost by component, hard time and USD caps, output paths, progress/heartbeat locations, stop/recovery behavior, and what the creator will review.
- **OR-24 / OR-26:** important architecture and paid-run plans go to the higher-model planning thread before execution. The confirmation is not a substitute for the creator's word where the creator must decide spend, a strategy change or destructive action.
- **OR-34:** the full-repository Fable audit must PASS before any paid test. It must verify that the run uses the active Ink Chronicle route and does not accidentally invoke legacy code.
- **OR-33:** every paid output is uploaded as it arrives and SHA256-verified in the canonical vault before the compute resource is released.
- **OR-36:** start the read-only Haiku watchdog beside every paid run. It reports ALIVE/PROBLEM; it does not create, stop, delete, restart or edit resources.
- The creator's explicit approval is required for every paid run under the current process. A successful plan or a working CLI login does not authorize spending.

No approval means no API request, no VM create, no endpoint deploy, no image/video generation, no training and no paid retry.

## 4. Budget, ledger and stopping rules

- All approved spending ceilings remain in `config/spend_caps.json`. Do not add, raise, reuse or reinterpret the existing `runpod` caps for Hyperstack or Modal.
- New provider-specific budgets must be approved and added to the single budget source before paid use. Until that happens, Hyperstack and Modal have a **zero approved project budget**.
- Estimate before submitting. For every provider, include compute, CPU, RAM, boot, model download, warm-up, retries, storage, public IP, egress, token charges, image patches and idle/scale-down time as applicable.
- At 80% of any approved run, provider, daily or episode cap: report PROBLEM and stop initiating new work; follow the creator's approved stop policy. Never increase a cap to finish a run.
- A run is not successful because the provider says RUNNING or a request returned HTTP 200. Require stage progress, expected outputs and hash-verified storage.
- Do not blindly retry any request whose submission result is uncertain. First reconcile provider state, job id, request id, billing ledger and output store. A duplicate create can double-bill.
- Stop compute on successful completion. Do not leave a GPU, warm worker, minimum replica, endpoint or VM running "for convenience."
- Deletion is destructive. Never delete user data, volumes, snapshots, endpoints, buckets or VMs without the creator's explicit instruction. When a workload is done, use the non-destructive stop/hibernate path approved for that provider; do not assume it stops billing.

## 5. Provider selection policy

### Existing RunPod adapter

- RunPod remains the only provider wired to the current `cloud/runpod.py` manager.
- All existing RunPod pods must continue through the manager, ledger, guard, unique lifetime name, heartbeat, upload wrapper and verified stop path. Never use raw `POST /pods`, `runpodctl create`, or the RunPod MCP to bypass the manager.
- Current code already uses REST v2; do not reintroduce REST v1.
- The RunPod official plugin is useful documentation/skills for its own service, but its MCP tools can directly create/manage/delete live resources. It must not bypass project approvals or the repository manager.

### Hyperstack: three different products, never conflate them

1. **GPU VM:** ordinary virtual machine for custom Python/CUDA/Docker workloads. This is the relevant Hyperstack option for the current Qwen/LTX pipeline. It is billed by the GPU flavor while ACTIVE **and SHUTOFF**. SHUTOFF is not a cost-saving state. HIBERNATE releases GPU/CPU/RAM, while persistent storage and any retained public IP continue billing. DELETE ends resource billing but destroys the VM's local state. Re-check stock immediately before deployment; inventory changes by region and flavor.
2. **AI Studio Partner API:** text/VLM is token-priced; image generation/editing is priced per 16x16 output patch. These models are exposed through third-party provider integrations. Do not assume that a model is running on our own Hyperstack GPU, that its provider is Hyperstack, that our prompts remain in Hyperstack, or that custom LoRAs are supported. Check data processing, commercial terms, exact model id, rate, output format, rate limits and account availability before using it.
3. **Dedicated Inference:** one open-weight LLM served by vLLM on GPU(s) reserved for the organization, priced per GPU-hour even when no tokens are being generated. It is not the token-priced Partner API, not a general container VM, and not a custom Diffusion/LTX runtime. Do not use it as a Qwen-image or video endpoint unless Hyperstack officially adds and documents that exact model/runtime.

Hyperstack VM state:
- ACTIVE = compute billed.
- SHUTOFF = GPU/CPU/RAM remain reserved and billed at the running rate.
- HIBERNATED = GPU/CPU/RAM released; saved root data/storage and retained public IP can still bill. Restore may require the same flavor to be in stock; do not assume immediate capacity.
- DELETE = irreversible for local instance data; only on explicit creator instruction.
- SSVs and snapshots bill independently, including unattached/reserved states. List them during every cost audit.
- Hyperstack Object Storage is currently Canada-only and has no multi-region replication. It is not the canonical vault.

Hyperstack APIs and credentials are distinct:
- Core API base: `https://infrahub-api.nexgencloud.com/v1`; API key in `api_key: <key>` header.
- GPU stock: `GET /core/stocks`; refreshes frequently and is regional/flavor-specific.
- Account Pricebook: `GET /pricebook`; use the returned account `value`, not just public list rates.
- AI Studio API base: `https://console.hyperstack.cloud/ai/api/v1`; API key in `api_key: <key>` header, no Bearer prefix. Use OpenAI-compatible requests only after checking the selected model's current schema and price.
- Dedicated Inference endpoint uses its own endpoint key as `Authorization: Bearer <endpoint-key>`. This is not the AI Studio API key.
- Do not log credentials, print them in prompts, commit them, or place them in HF/git artifacts.

Hyperstack MCP:
- `https://docs.hyperstack.cloud/mcp` is read-only documentation search. It is safe for research.
- `https://console.hyperstack.cloud/ai/mcp` is an account control-plane MCP that can create, modify and delete live VMs, storage, clusters and other resources. Treat it as a privileged operator, not a read-only documentation tool. Default use is read-only inventory, price, stock and billing inspection. No create/update/hibernate/delete action without all gates and creator approval.
- A configured OAuth session does not confer project authorization.

### Modal

- Use Modal for containerized Python jobs that should scale to zero and avoid idle-GPU charges. It is a better conceptual fit for bursty jobs and reusable functions than for an always-on GPU VM.
- Modal Functions/Sandboxes charge CPU, memory and GPU by active time; image build, initialization, model download, application startup and the default scaledown waiting window are billable. Scale-to-zero removes ongoing compute charges, but Shared Endpoints billed per token are a separate product and are not included in Starter credits.
- Starter currently has $30/month of compute credits, 10 GPU concurrency and 1 TiB/month included egress. CPU/RAM/GPU compute uses these credits; Shared Endpoint token charges do not.
- Keep `min_containers=0`, `buffer_containers=0` and no warm containers for this project unless a measured latency requirement and separate approval justify them. Configure a short, valid `scaledown_window`; do not leave replicas warm.
- Use named Modal Volumes only as a cache/state layer. Explicitly `commit()` writes and `reload()` before reading cross-container changes. Concurrent writers to the same file are unsafe (last write wins). Keep one writer per job/prefix.
- Use Modal Secrets for HF and provider credentials; never hardcode them in the image, source code, CLI output or job manifest.
- Keep completed outputs in the canonical HF vault with hashes. Modal Volumes are not the only copy.
- Modal CLI and Modal skills can deploy actual billable apps and functions. `modal run`, `modal serve`, `modal deploy`, `modal endpoint`, `modal volume`, `modal secret` and resource deletion are not harmless documentation commands. Require the same gates.

## 6. Model and hardware fit for this repository

The active p14 stack contains Qwen-Image-2.1, BiRefNet and large LTX-2.5/2.3 assets. The pinned LTX-2.5 base is a 22B transformer with additional text encoder and VAEs; LTX-2.3 is also a 22B-class video base. Do not choose the GPU from hourly price alone.

- A 48 GB A6000/L40 is a low-cost **candidate for isolated tests**, not a proven fit for the full p14 combined workload.
- Start the full LTX/Qwen integration test at 80 GB-class A100/H100 only after checking current VRAM, quantization/offload assumptions and the schedule. An H100 is not automatically cheaper per job than A100; measure throughput and total job cost.
- Hyperstack AI Studio currently lists Qwen text/VLM models and several image models, including Qwen-Image/Qwen-Image-2512 and Z-Image-Turbo, but not the exact repository model/adapter combination `Qwen-Image-2.1 + xworld_v2`. Its public model catalogue does not list a video-generation modality or LTX-2.5. Never silently replace these.
- No candidate's model list proves a custom adapter, LoRA, ControlNet, mask, seed or generation parameter is supported. Verify the exact request and output in a tiny approved pilot.
- The p14 LTX speed record for this exact D-116 route is not yet a production benchmark. Do not use older 200-second LTX clip assumptions as if they measure the current LTX-2.5/2.3 pipeline.

## 7. Mandatory provider adapter contract before migration

Do not update production routing to Hyperstack or Modal until the following exists and tests pass:

1. A provider interface used by `cloud/jobs.py` state transitions, not provider-specific logic scattered through production.
2. Lifecycle mapping for create, provisioning, running, failure, stop, hibernate/scale-to-zero, deletion and billing states.
3. Idempotent create/reconciliation: a lost response must not submit a second paid job.
4. Per-job ledger reservation, provider-native cost reconciliation and daily/episode limits.
5. Heartbeat/progress and external watchdog that survives the Claude session.
6. Output streaming/checkpoint upload to HF with SHA256 verification before stop/release.
7. Recovery tests for provisioning timeout, no GPU stock, auth failure, CUDA failure, model download hang, job timeout, rate limit, provider outage, lost submission response, partial output upload, duplicate worker, hard cap and kill request.
8. Live no-cost/read-only smoke test, then a creator-approved paid pilot with expected/worst-case cost and acceptance metrics.
9. Full-repository OR-34 audit and a verified rollback path to the current RunPod adapter.

A README or successful MCP connection is not a provider adapter.

## 8. Required report after every run

Report:
- provider + resource/endpoint id + region + GPU/VRAM;
- source commit and hashes of pod/function code, model revisions and LoRAs;
- start/end timestamps, wall clock, GPU-active seconds and idle/boot/download/upload seconds;
- estimated, reserved and provider-billed cost separately;
- tokens or image patches if an API was used;
- each stage result and failure/retry;
- output HF paths and SHA256 verification;
- final provider state and proof that no compute resource remains billable;
- next decision, unresolved issue and whether any approval is needed.

Never say “done” or “saved” unless the output exists in the vault and its hash matches.
