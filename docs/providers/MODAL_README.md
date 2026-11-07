# Modal for Ink Chronicle — platform and migration reference

**Research snapshot:** 2026-11-07  
**Repository branch:** `icw/21-mouth-job`  
**Current route:** D-116 / Qwen-Image-2.1 → Blender → LTX-2.5/2.3 → FFmpeg  
**Status:** research/documentation only. No Modal app, function, endpoint, volume or paid job was deployed.

## Executive decision

Modal is the strongest candidate of the two for **bursty custom Python GPU work with automatic scale-to-zero**. It is not the cheapest raw GPU-hour: Hyperstack A100 80 GB costs $1.35/h while Modal A100 80 GB costs about $2.4984/h. Modal's differentiator is metered execution and the $30/month Starter compute credit, not the lowest listed GPU price.

- Use Modal Functions / jobs for Qwen and LTX work only after a provider adapter exists.
- Use a Modal Volume as a cache, not the canonical output vault.
- Keep `min_containers=0`, `buffer_containers=0` and a short `scaledown_window` for this intermittent project.
- The $30 Starter credit covers GPU + CPU + RAM compute, but not Shared Endpoint token charges.
- Keep Blender J5 and helper work on the creator's PC or existing free CI where possible. Modal should not be used to pay for work already available free.

Official entry points:
- [Modal pricing](https://modal.com/pricing)
- [Python SDK docs](https://modal.com/docs)
- [CLI reference](https://modal.com/docs/cli/latest)
- [Volume reference](https://modal.com/docs/sdk/py/latest/Volume)
- [Function reference](https://modal.com/docs/sdk/py/latest/Function)
- [Custom container images](https://modal.com/docs/guide/custom-container)
- [Secrets](https://modal.com/docs/sdk/py/latest/Secret)
- [Modal skills CLI](https://modal.com/docs/cli/latest/skills)

## 1. Modal product model

| Modal service | Billing | What it does | Relevance |
|---|---|---|---|
| Functions | CPU + RAM + GPU time per second | Executes Python code in containers, can autoscale to zero | **Best match** for custom Qwen/LTX batch functions |
| Scheduled Functions / Web Functions | Same compute metering | Triggered jobs and HTTP entrypoints | Useful later for orchestration, not required for first adapter |
| Volumes | Storage per GiB-month, 1 TiB/month included in Starter | Persistent filesystem across containers | Model/cache and intermediate state only |
| Secrets | No compute model on their own; attached to functions/images | Environment variables injected securely | HF and API tokens |
| Shared Endpoints | Per-token model pricing | Hosted model endpoints | Separate from Starter compute credits |
| Dedicated endpoints / `modal endpoint` | Service-specific | Long-lived model serving | Only if there is measured continuous inference demand |
| Sandboxes | Non-preemptible rates | Isolated user-controlled execution environments | Not needed for standard pipeline jobs |

Modal runs containerized Python applications. It is particularly suited to ML inference, model training, data pipelines and compute-heavy job queues. It is not a general unmanaged VM where the creator SSHs into one machine and leaves it running indefinitely.

## 2. Current Starter plan and compute pricing

Starter currently costs $0/month plus compute and includes:
- $30/month compute credits.
- 3 workspace seats.
- 100 containers.
- 10 concurrent GPUs.
- Limited scheduled and web functions.
- Real-time logs and metrics.
- Region selection.
- 1 TiB/month included network egress.

The Team tier is $250/month plus compute with $100 credits and higher quotas; it is not justified for this solo project.

### GPU rates (public list, converted from per-second rates)

| GPU | List price / hour | 1h | 3h | 5h |
|---|---:|---:|---:|---:|
| T4 | $0.5904 | $0.59 | $1.77 | $2.95 |
| L4 | $0.7992 | $0.80 | $2.40 | $4.00 |
| A10 | $1.1016 | $1.10 | $3.30 | $5.51 |
| L40S | $1.9512 | $1.95 | $5.85 | $9.76 |
| A100 40 GB | $2.0988 | $2.10 | $6.30 | $10.49 |
| A100 80 GB | $2.4984 | $2.50 | $7.50 | $12.49 |
| H100 SXM5 | $3.9492 | $3.95 | $11.85 | $19.75 |
| H200 SXM | $4.5396 | $4.54 | $13.62 | $22.70 |
| B200 | $6.2496 | $6.25 | $18.75 | $31.25 |
| B300 | $7.0992 | $7.10 | $21.30 | $35.50 |

CPU: $0.0000131 per physical-core-second (one physical core = two vCPU), minimum 0.125 physical core.  
Memory: $0.00000222 per GiB-second.  
Volumes: $0.09/GiB-month, with up to 1 TiB/month included in Starter.  
Egress: $0.04/GiB beyond Starter's included 1 TiB/month.

**Important:** compute credit applies to Functions and Sandboxes' CPU, RAM and GPU time. It does not cover Shared Endpoints billed by token. Shared Endpoint tokens are billed from the first request, even while monthly compute credit remains.

### Example: 5-hour A100 80 GB job

- GPU only: 5 × $2.4984 = $12.49.
- This is within the $30 monthly compute credit, before CPU and RAM.
- CPU/RAM for installation, data handling, workers and runtime are additional compute and use the same credit.
- If total Starter compute used in the billing month exceeds $30, overage is billed.
- A Shared Endpoint token request is a separate bill and is not paid from the $30.

## 3. Why Modal can be cheaper than a GPU VM despite its higher hourly rate

Modal charges active container compute by the second and scales idle containers to zero. By default it keeps a container alive for 60 seconds after the last input, and this period is billable. Once scaled to zero, no compute charge remains.

Hyperstack GPU VM is cheaper per active GPU-hour, but:
- it bills while ACTIVE;
- a SHUTOFF VM still reserves the GPU and bills at the running rate;
- a HIBERNATED VM releases GPU but retains storage and any kept public IP.

For sporadic jobs, Modal can avoid forgotten idle GPU time. For a predictable 3–5 hour continuous run, Hyperstack A100 is cheaper in cash. Modal Starter credits can offset some or all of the compute charge if the user has not already consumed the $30 in that month.

## 4. Mapping the D-116 Ink Chronicle work

| Repo lane | Current work | Modal recommendation |
|---|---|---|
| Qwen assets / first frames | VideoX-Fun + Qwen-Image-2.1 + `xworld_v2` | One custom GPU Function or a small sequence of functions, only after peak VRAM and cold-start are measured |
| BiRefNet cut-outs | Image matte generation | GPU/CPU function according to measured profile; cache model in Volume |
| LTX J2/J4 | LTX-2.5 / LTX-2.3 + control/layout conditioning | A100 80 GB or H100 only after benchmark; long-running job must write resumable clips and sidecars as it completes |
| Blender J5 / layouts | EEVEE, projection, cards, layout passes | Prefer creator PC (RX 5700) or free CI; only send to Modal if a missing capacity/parallelism requirement is demonstrated |
| Python/FFmpeg helper | Maps, assembly, QA, packaging | PC/CI first; use Modal CPU only if the session or CI is a measured bottleneck |

The p14 job is not a simple single inference request. It installs pinned dependencies, fetches model weights, runs multiple independently recoverable stages and writes artifacts. A naïve “wrap the whole pod in one Modal function” port could create long cold starts, expensive model downloads and poor resumability.

A better design is:
1. Build one reusable image with pinned OS/Python/system packages and verified CUDA runtime.
2. Store large Hugging Face model weights in a named Volume cache, keyed by model revision and file hashes. Do not build mutable/large model weights into every deployment image without a clear reason.
3. Trigger stage functions from a provider-neutral job schedule only when their inputs exist.
4. Give each job/stage its own run id, input hash, hard timeout, progress heartbeat and output prefix.
5. Write every output to HF as it lands; verify SHA256 and mark it committed.
6. Scale to zero after each bounded stage; keep no minimum containers.
7. Reconcile Modal job/container state and actual billing before marking the project job as complete.

## 5. Functions, scaling and compute settings

The Python SDK exposes app/function decorators and autoscaler settings. For a GPU function, important settings include:
- GPU type (for example A100 / H100; exact syntax must be checked against the installed SDK version and account availability);
- CPU and memory allocations;
- container image;
- attached Secret and Volume;
- timeout / startup timeout;
- `max_containers`, `min_containers`, `buffer_containers`;
- `scaledown_window` in seconds.

For Ink Chronicle defaults:
- `min_containers = 0`.
- `buffer_containers = 0`.
- Keep `max_containers` at 1 for memory-heavy LTX jobs until concurrent memory use has been measured.
- Set a short `scaledown_window` within the SDK-supported range; do not blindly keep the 60-second default if a shorter window is safe.
- Avoid parallel LTX jobs on one model cache / GPU until memory and disk contention have been tested.
- Do not set a large retry count for paid generations. Retry only after provider state and outputs are reconciled.
- Measure the real cold start and model warmup before deciding whether a single stage, per-clip job or batched job is cheapest.

Do not run a permanently warm endpoint for a pipeline that makes only occasional episodes.

## 6. Container images and pinning

Modal supports:
- Modal-native Python images (Debian slim + apt/pip packages).
- Dockerfile-based custom images.
- External container image references.
- Build-time commands and build-time functions to fetch data.

For the project:
- Preserve the pinned package/model versions already declared in the current branch.
- Pin exact source commits, model revisions and SHA256 hashes; do not use `latest` model images or unpinned Git heads.
- Keep CUDA driver compatibility tested on the selected GPU.
- Build dependencies once into the image or a cache layer; don't reinstall the full stack on every function call.
- Model weights should be cached separately in a Modal Volume and verified by SHA256 after first download.
- Avoid one shared mutable image-build output or one cache file with several concurrent writers.

The Modal Image guide has examples for `Image.debian_slim`, apt/pip install, environment variables and Docker images. The project should use the most deterministic route that can be exercised by CI.

## 7. Modal Volumes and data durability

Volumes are writable persistent filesystems that can be mounted by more than one function. Unlike a normal shared network filesystem:
- call `volume.commit()` after writes to make them visible outside the current container;
- call `volume.reload()` to refresh a container's view before reading updates from another writer;
- reload cannot be called while files are still open;
- concurrent writes to the same path are unsafe; last write wins;
- there is no distributed file lock.

Project policy:
- Use Volume only for model weights/cache and clearly partitioned job state.
- Use one writer per prefix/file. Use atomic write/rename only where its filesystem semantics are confirmed.
- Keep completed frames, clips, manifests, sidecars, progress and logs in the canonical HF vault with SHA256.
- A Volume is not a substitute for HF and not the only copy of the result.
- Do not mount the same active output directory into two parallel functions that may overwrite the same manifest.

## 8. Secrets and authentication

Use Modal Secrets for:
- HF_TOKEN;
- any future API tokens;
- object storage credentials if a separate destination is explicitly approved.

Use `modal.Secret.from_name(...)` in functions or attach secrets via the dashboard. Do not bake tokens into Docker/Modal images, source, environment defaults, CLI args, prompt text, logs, job JSON or GitHub files.

Modal CLI setup:
```bash
python -m pip install modal
modal setup
modal profile current
modal billing
```

The exact authentication flow is user-interactive. The agent must not attempt to capture or print the token. A workspace/environment is a scope for apps, secrets and resources; use a dedicated development environment for the first adapter.

## 9. Agent support for Claude Code

Modal provides a CLI and a native Modal skills installer:

```bash
modal skills install --claude --global
modal skills show
modal skills update --yes --claude --global
```

The `--claude` flag installs to `.claude/`; `--global` places the skills in the user home scope. The installer can also download Modal documentation resources; this is a skills/doc workflow, not a cloud resource creation.

CLI entry points include:
- `modal run` — execute a function / local entrypoint;
- `modal serve` — serve a Web Function with hot reload;
- `modal deploy` — deploy an app;
- `modal shell` — shell into a container;
- `modal endpoint` — manage model endpoints;
- `modal volume` — inspect/manage volumes;
- `modal secret` — manage secrets;
- `modal billing` — inspect billing;
- `modal environment` — select environments;
- `modal skills` — manage skills.

The agent skill improves knowledge of the provider; it does not authorize any paid resource action. Do not assume that Modal exposes an official hosted MCP server for the specific workflows unless the official documentation confirms it. Prefer SDK/CLI and explicit project-owned adapters.

## 10. Cost estimation for the current project

GPU-only compute prices:

| Duration | Modal L40S | Modal A100 80 GB | Modal H100 SXM5 |
|---:|---:|---:|---:|
| 30 min | $0.98 | $1.25 | $1.97 |
| 1 hour | $1.95 | $2.50 | $3.95 |
| 2 hours | $3.90 | $5.00 | $7.90 |
| 3 hours | $5.85 | $7.50 | $11.85 |
| 5 hours | $9.76 | $12.49 | $19.75 |

These are list-price GPU costs, not whole-job prices. Add the CPU and memory seconds, image build / startup, model download or cache misses, scaledown window, retries, and any storage or endpoint costs.

### 5-hour example against Starter credits

A 5-hour A100 80 GB workload consumes $12.49 in GPU compute. With a hypothetical 16 physical CPU cores and 64 GiB RAM allocated for all five hours:
- CPU: 16 × 5 × 3600 × $0.0000131 = $3.77.
- RAM: 64 × 5 × 3600 × $0.00000222 = $2.56.
- GPU: $12.49.
- Combined illustrative compute: about $18.82, within the $30 credit if this is the only compute usage in the month.

This CPU/RAM profile is an illustration, not a recommendation for p14. Use the minimum allocations that pass the measured workload. If the containers allocate/consume more CPU or memory, cost changes.

### When Modal wins

Let:
- `T_gpu` = seconds GPU actually allocated;
- `T_cpu` = seconds × physical cores;
- `T_ram` = seconds × GiB;
- `C` = idle scale-down wait and startup/warmup time.

Then approximate compute:
`GPU_rate_per_second × T_gpu + CPU_rate_per_second × T_cpu + RAM_rate_per_second × T_ram`.

For the active p14 flow, the key is whether independent stages can scale down without re-downloading model weights on every call. If the same 22B model is loaded and used for several clips, batch/queue multiple clips into one bounded function to amortise initialization, but preserve per-clip checkpoints and retry isolation.

Do not budget an episode from the old LTX 200s-per-clip assumption. The D-116 LTX-2.5/2.3 route still needs measured speeds and failure rates before it can be priced.

## 11. Modal migration plan

No paid resource is authorised by this document. The adapter plan should be:

1. Create a provider-neutral Modal job adapter behind the same job contract as RunPod; do not refactor the production pipeline around Modal primitives.
2. Reproduce the p14 stage graph and stage-level dependency schedule from the new branch. Do not submit a long function that idles the GPU while waiting for Blender CPU outputs.
3. Create a dedicated Modal development environment and secrets; set strict workspace spend limits and concurrency caps before any paid run.
4. Build a pinned image and a separate HF-backed model-cache Volume. Prove that a new container can read the cached models and verify hashes.
5. Test a CUDA smoke, one Qwen operation, BiRefNet, one LTX clip and the upload/checkpoint protocol separately.
6. Add function timeout, startup timeout, scale-down, max/min/buffer container settings, failure states, idempotent request IDs and actual billing reconciliation.
7. Run one approved short pilot, then compare with Hyperstack A100 80 GB and the RunPod baseline on total billed cost, time-to-first-output, stage throughput, VRAM, failures and recovery.
8. Only change the default provider after Fable's OR-34 audit and creator approval.

## 12. Official source register

- [Pricing](https://modal.com/pricing)
- [CLI reference](https://modal.com/docs/cli/latest)
- [Modal skills](https://modal.com/docs/cli/latest/skills)
- [Function SDK and autoscaler settings](https://modal.com/docs/sdk/py/latest/Function)
- [App SDK](https://modal.com/docs/sdk/py/latest/App)
- [Custom container images](https://modal.com/docs/guide/custom-container)
- [Volume SDK](https://modal.com/docs/sdk/py/latest/Volume)
- [Secret SDK](https://modal.com/docs/sdk/py/latest/Secret)
- [Official Modal examples](https://modal.com/docs/examples)

