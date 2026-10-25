# GPU infrastructure for a solo creator's cloud video pipeline — research notes

Date of research: 2026-10-22. Research only; nothing was created or spent.
Scope: RunPod today vs alternatives; serverless vs pod cost model; durable storage; watchdogs that survive without the
Claude session; phone kill-switch; observability. Every number is marked **[V]** (verified on an official page, date given in the
source list), **[3P]** (third-party report, not confirmed on an official page), or **[INF]** (my inference/arithmetic from
verified numbers). Where I could not find a number: **not verified**.

How this relates to the repo's invariants: CLAUDE.md invariant 1 (cloud-first, pods only via `explainer_engine/cloud/runpod.py`,
caps only in `config/spend_caps.json`) and invariant 9 (no architecture change without evidence and a minimal-change proposal).
This document is the evidence; section 8 is the minimal-change proposal. Nothing here is a decision.

---

## 0. Fifteen-line summary

1. RunPod pods bill per second; stopped pods still bill volume disk at **$0.20/GB/mo** (double the running rate) and may come back with **zero GPUs** [V]. Terminate, never park.
2. RunPod has **no idle/auto-stop for pods** in the docs; the only documented pattern is `sleep 2h; runpodctl pod stop $RUNPOD_POD_ID &` inside the pod [V]. The account-level spend limit is **$80/hour** by default and is not per job [V].
3. RunPod REST **v1 retires 2026-11-15**; v2 (beta) exposes `status`, `cost` (USD/h), `runtime.gpus[].util/memoryUtil`, SSE logs, and `GET /v2/billing/pods` with hourly buckets [V]. Check which API `cloud/runpod.py` uses.
4. RunPod serverless: per-second, idle timeout default 5 s, `executionTimeout` default 600 s, webhooks (2 retries), `s3Config` for outputs; network volumes mount at `/runpod-volume` but pin one datacenter and shrink GPU availability [V]. L40S serverless $1.75/h vs pod $1.09/h [V] → serverless is cheaper below ~62 % utilisation [INF].
5. RunPod status page (uptime.runpod.io) lists ~29 regional network/storage incidents from Aug 6 to Oct 21, 2026 [V]; the "never-starting pod" is a real, recurring failure mode.
6. Modal: per-second GPU (L4 $0.80/h, L40S $1.95/h, A100-80 $2.50/h, H100 $3.95/h), Volumes free to 1 TiB, cron schedules run server-side, web endpoints, **workspace budget + spend limit that stops workloads**, $30/month free credits on Starter [V]. Best fit for custom ComfyUI/LoRA code that must scale to zero.
7. Hosted model APIs beat self-hosting for this volume: 40 FLUX.1-dev images ≈ **$1.05** on fal ($0.025/MP) or **$1.00** on Replicate ($0.025/image); a 5 s Wan 2.2 720p clip ≈ **$0.40** on fal; FLUX LoRA training **$2/run** on fal or ≈ **$1.46** on Replicate (8×H100, ~2 min) [V].
8. Self-hosting the same on RunPod costs similar money only if the pod lives < 20–30 min total; a forgotten L40S pod costs **$26/day** [INF].
9. Durable results store: **Cloudflare R2** ($0.015/GB-mo, zero egress, 10 GB free, event notifications, user checksums; object versioning not verified) or **Backblaze B2** ($6.95/TB-mo, versions kept by default, egress free to 3× storage) [V]. HF Hub git repos are wrong for mutable video assets; the new **HF Storage Buckets** (S3-compatible, mutable, webhooks + SSE change stream) are a credible alternative but pricing was not verified.
10. RunPod network volumes ($0.07/GB-mo) are a model cache, not an archive: no versioning, no pre-signed URLs, S3 API only in 15 DCs, deleted if balance stays at $0 [V].
11. Watchdog that survives without the Claude session: **Cloudflare Worker cron** (free: 5 crons, 100k req/day, 10 ms CPU — enough for one RunPod REST call + one ntfy POST) as primary; **GitHub Actions cron** (min 5 min, free 2,000 min/mo private, but routinely 10–30 min late and sometimes dropped) as backup [V/3P].
12. Phone kill-switch: GitHub Mobile can run a `workflow_dispatch` workflow (official changelog 2024-07-30) that stops/terminates every pod; and an **ntfy `http` action button** can POST to a secret Worker URL in one tap [V]. Pushover emergency priority repeats until acknowledged (retry ≥ 30 s, expire ≤ 3 h) [V].
13. Observability: write `state.json` + a 60 s `heartbeat.json` to R2 from inside the job; the watchdog reads R2 and RunPod `runtime.gpus[].util`, never the pod itself; alarm on stale heartbeat, low GPU util while RUNNING, uptime > plan, or billing > cap [INF, built on V facts].
14. Biggest uncertainties: RunPod v2 API is beta; prices move monthly (Hyperbolic went $1.50 → $3.19/h in three months [3P]); hosted-API model availability; R2 versioning; HF bucket pricing.
15. Recommended split: hosted APIs (fal, Replicate fallback) for standard FLUX/Wan/LTX/LoRA; Modal (or RunPod serverless + worker-comfyui) for custom code; RunPod pods only for time-boxed interactive debugging with a self-stop timer and the external watchdog; R2 for everything that must survive.

---

## 1. RunPod today (official docs, pricing page "Updated October 8, 2026")

### 1.1 Pods

| Item | Fact | Tag |
|---|---|---|
| Billing | "All compute and storage charges are billed per second"; network volumes billed hourly; charges deducted every 5 minutes | V |
| Pod prices (secure / community, $/h) | A5000 24 GB 0.27 / 0.16 · A40 48 GB 0.59 / 0.35 · L4 0.59 / 0.44 · RTX 4090 0.89 / 0.34 · L40S 1.09 / 0.79 · RTX 5090 1.19 / 0.69 · A100 80 GB 1.79 / 1.19 · RTX PRO 6000 2.49 / 1.69 · H100 PCIe 2.89 / 1.99 · H100 SXM 3.99 / 2.69 | V |
| Container disk | $0.10/GB/mo | V |
| Volume disk | $0.10/GB/mo running, **$0.20/GB/mo while stopped** | V |
| Network volume | $0.07/GB/mo (< 1 TB), $0.05 (> 1 TB); high-performance tier $0.14/GB/mo; Secure Cloud only for pods | V |
| Spend limit | "default spend limit of $80 per hour across all resources"; raised by support or automatically with account history. Not per pod, not per job | V |
| Balance at $0 | all pods stopped; pods **without** a network volume are terminated and data is unrecoverable; a network volume may "eventually be terminated" if the balance stays at $0 | V |
| Low-balance alert / auto-pay | email at a threshold you set; auto-pay at most once per hour | V |
| New pod | balance must cover ≥ 1 hour of the configuration | V |
| Stop vs terminate | stop releases the GPU, keeps `/workspace`, clears container disk, keeps billing volume disk; terminate deletes everything not on a network volume | V |
| Zero-GPU pods | "You may be allocated zero GPUs if capacity has changed" — a stopped pod's GPU can be rented by someone else; zero-GPU start is "primarily a data recovery feature"; FAQ: network volumes are "the most effective way to avoid this issue"; a beta "pod migration" copies data to a machine with GPUs (new pod id/IP) | V |
| Stuck initializing | troubleshooting table: check logs for command errors; keep an idle process (`sleep infinity`) if using SSH; "OCI runtime create failed" → filter by CUDA version | V |
| Auto-stop | **none documented**. The only pattern: `sleep 2h; runpodctl pod stop $RUNPOD_POD_ID &`. `runpodctl pod start/stop/delete` take only a pod id (a search snippet claimed duration flags; the official reference page lists none → treat as not available) | V |
| Editing a running pod | "resets it completely, erasing all data not stored in /workspace or a network volume" | V |
| Docker Compose | not supported | V |
| Pod webhooks | none found for pod lifecycle events (serverless jobs have webhooks) | V (absence) |

Startup-time facts: the docs name the cold path as image pull → container start → init scripts → weights into VRAM and say end-to-end
cold starts "typically run 30 seconds to two minutes plus depending on image size and model" [V, RunPod guide]. A third-party
write-up measured a large model's cold start dropping from ~248 s to ~42 s after moving weights to a network volume [3P].
Mitigations in the docs: custom image with baked models, network volume cache, FlashBoot (serverless only), smaller base image [V].

### 1.2 Serverless

| Item | Fact | Tag |
|---|---|---|
| Prices ($/h, flex, from pricing page) | A4000/A4500/RTX 4000 0.58 · L4/A5000/3090 0.69 · 4090 1.10 · 5090 1.58 · A6000/A40 1.22 · L40/L40S/6000 Ada 1.75 · A100 80 GB 2.72 · RTX 6000 Pro 3.49 · H100 4.79 · H200 5.93 · B200 8.64 | V |
| Granularity | "billed from when a worker starts until it fully stops, rounded up to the nearest second"; cold start + execution + idle wait are billed; a scaled-down worker is not | V |
| Idle timeout | default 5 s (endpoint setting) | V |
| Execution timeout | default 600 s; 5 s … 7 days; per-request override via `policy.executionTimeout` | V |
| Job TTL | default 24 h, hard limit (job removed, 404) | V |
| Results retention | `/run` 30 min; `/runsync` 1 min | V |
| Webhook | top-level `"webhook"` in the request; must return 200; "retries up to 2 more times with a 10-second delay" | V |
| S3 output | `s3Config{accessId, accessSecret, bucketName, endpointUrl}` — worker code must use it; any S3-compatible provider | V |
| Workers | max workers default 3; active workers default 0 (billed continuously, discount via sales); up to 3 GPU types in priority order; FlashBoot on by default | V |
| Scaling | queue delay (default 4 s) or request count | V |
| Network volume | attachable, mounts at `/runpod-volume`; "restricting the endpoint to the volume's data center"; concurrent writes from several workers to one volume may corrupt data | V |
| Container disk (serverless) | ~$0.10/GB/mo in 5-minute intervals | V |
| FlashBoot | marketing: "Sub-200ms"; the 2023 measurement was 563 ms best, 95 % < 2.3 s on a Whisper endpoint; one independent 2026 matrix measured RunPod A100 median cold start 4.2 s (Modal 1.8 s, Replicate 6.5 s) — single author, 500 runs, not independent confirmation | V / 3P |
| ComfyUI worker | `runpod/worker-comfyui` (AGPL-3.0) tags `base`, `flux1-schnell`, `flux1-dev`, `sdxl`, `sd3`; S3 upload of outputs via env vars; webhook; models via network volume or Docker build | V |
| "Flash" SDK | `@Endpoint` Python decorator, same serverless pricing; standalone package being folded into the RunPod SDK | V |

### 1.3 API for status, logs, metrics, spend

| Item | Fact | Tag |
|---|---|---|
| REST v1 | **deprecated, retired 2026-11-15**; OpenAPI at `rest.runpod.io/v1/openapi.json` | V |
| REST v2 | "currently in beta. Endpoints and behavior may change" | V |
| `GET /v2/pods/{id}` | `status` ∈ PROVISIONING, STARTING, RUNNING, EXITED, ERROR, TERMINATED; `actions` (valid transitions); `cost` (USD/h); `startedAt`; `mounts.network.volumeId`; `runtime` (null unless RUNNING) with `uptime`, `gpus[].util`, `gpus[].memoryUtil`, `cpu.util`, `memory.util`, `ports[]` | V |
| Logs | `GET /v2/pods/{id}/logs` as Server-Sent Events, resumable with `Last-Event-ID` | V |
| Billing | `GET https://api.runpod.io/v2/billing/pods?bucketSize=hour|day|…&lastN=N|startTime/endTime&podId=` → per-pod `totalAmount/gpuAmount/cpuAmount/diskAmount` + totals; "listBilling" for aggregate across resource families | V |
| Balance / spend rate | `runpodctl user` prints `clientBalance`, `currentSpendPerHr`, `spendLimit` (GraphQL `myself`) | V |
| API status | uptime page shows "GraphQL / REST v2 APIs: elevated errors" on Sep 17 (1 h) and Oct 21 (21 min) 2026 | V |

### 1.4 Reliability record (uptime.runpod.io, read 2026-10-22 08:15 UTC)

All components "Operational" at read time. 90-day incident list (truncated page, so possibly incomplete): Aug 06 EUR-NO-1 network
storage down 1h51m; Aug 13–17 EUR-IS-1 network degraded (~20 h, 2h50m, 3 h); Aug 14 US-IL-1 DC unavailable 5h34m; Aug 19 EU-CZ-1,
EUR-NO-2; Aug 31 US-NC-2; Sep 06 Serverless/SSH proxy elevated errors 1h25m; Sep 09 CA-MTL-4; Sep 12 EUR-IS-1 degraded ~9h40m;
Sep 16 EU-NL-1 down 1h59m; Sep 17 APIs; Sep 22 EUR-IS-2 degraded 5h23m; Sep 24 CA-MTL-4 emergency maintenance 4 h; Oct 07/09
US-CA-2 (storage down 1h31m); Oct 09 EUR-NO-2 emergency maintenance 9h30m; Oct 10 EU-RO-1 storage degraded; Oct 19 upstream
maintenance degraded ~14 h; Oct 20 EUR-IS-1; Oct 21 REST v2 elevated errors 21 min. 30/60/90-day uptime per region 99.7–100 %.
Third-party: PulsAPI 99.80 % 30-day uptime, "degraded" on Oct 19 [3P]; a 2026 review counts "227+ outages in nine months"
(source unclear) [3P]; a GitHub issue reports provisioning failing before runner registration from 2026-09-24 (one user's CI) [3P].

Reading: incidents cluster on **regional networking and network storage**. A pipeline that pins one DC through a network
volume inherits that DC's incidents. Multi-DC volumes (no auto-sync) or stateless workers + external object storage avoid it.

---

## 2. Alternatives (prices read on official pages 2026-10-22 unless tagged; none list an effective date beyond "© 2026")

### 2.1 Price table ($/GPU-hour; per-second where the provider bills per second)

| Provider | L4 / A10(G) | L40S | A100 80 GB | H100 | Granularity | Idle cost | Storage | Spend cap / alerts | Tag |
|---|---|---|---|---|---|---|---|---|---|
| RunPod pod (secure) | L4 0.59 | 1.09 | 1.79 | 2.89 PCIe / 3.99 SXM | per second | full price while RUNNING; $0.20/GB/mo stopped volume | NV $0.07/GB/mo | $80/h account limit; low-balance email | V |
| RunPod serverless | L4 0.69 | 1.75 | 2.72 | 4.79 | per second, incl. cold start + idle (5 s default) | none when scaled to zero | NV $0.07/GB/mo | same | V |
| Modal | L4 0.80 (0.000222/s) · A10 1.10 (0.000306/s) | 1.95 (0.000542/s) | 2.50 (0.000694/s) | 3.95 (0.001097/s) | per second; CPU $0.0000131/core/s, RAM $0.00000222/GiB/s | scaledown_window default 60 s (2 s–20 min) billed | Volumes $0.09/GiB-mo, **1 TiB free**; egress $0.04/GiB | **workspace budget + spend limit** (stops workloads); $30/mo credits Starter, $100 Team ($250/mo) | V |
| fal serverless (own code) | — | — | not listed | 4.50 list / "as low as" 2.49 (0.00125 / 0.000692 /s); H200 6.00/2.99; RTX PRO 6000 4.00/1.99 | per second "while your runners are alive"; `keep_alive`, `min/max_concurrency` | keep_alive billed | not verified | not verified | V |
| fal model APIs | FLUX.1 dev $0.025/MP, +LoRA $0.035/MP, schnell $0.003/MP, FLUX 2 $0.012/MP; Wan 2.2 A14B i2v $0.04/0.06/0.08 per video-second at 480/580/720p (16 fps); LTX-Video 13B distilled i2v $0.04/s (24 fps), $0.08 with detail pass; flux-lora-fast-training $2/run (scales with steps, default 1000) | | | | per output; "pay only for successful outputs" [3P] | none | n/a | not verified | V |
| Replicate | T4 0.81 (0.000225/s) | 3.51 (0.000975/s) | 5.04 (0.0014/s) | 5.49 (0.001525/s); 8×H100 0.0122/s | per second | public models: setup/idle free; private/deployments: pay for all online time | n/a | not on billing page (not verified) | V |
| Replicate model APIs | flux-dev $0.025/image; Pruna-optimised Wan 2.2 fast i2v 480p $0.05/video, t2v 720p $0.10 (blog); FLUX LoRA training ≈ $1.46 (8×H100 ~2 min, official guide) | | | | | | | | V |
| Baseten | L4 0.85 (0.01414/min) · A10G 1.21 (0.02012/min) | — | 4.00 (0.06667/min) | 6.50 (0.10833/min); H100 MIG 40 GB 3.75 | per minute | "do not pay for idle time" (billed deploying/scaling/predicting) | not listed | credits for new accounts (amount not stated) | V |
| Together | — | — | — | dedicated H100 5.49; clusters H100 3.99 on-demand / 1.99 preemptible | per hour | n/a | n/a | not verified | V |
| Fireworks | — | — | not listed | 8.00 (also H200 8.00, B200 13.00) | per GPU second | — | — | not verified | V |
| Koyeb | RTX 4000 SFF Ada 0.50 · L4 0.70 | 1.20 (0.000333/s) | 1.60 (0.000444/s) | 2.50 | per second | scale to zero | volume price not listed | Pro $29/mo incl. $10 compute | V |
| Beam | RTX 4090 0.69 (0.000192/s) · 5090 (0.000303/s) | on-demand VM from 0.76 | VM from 1.36 | 3.50 serverless (0.000972/s) / VM from 1.83 | per millisecond (serverless) | none | 1 TB included, $0.021/GB beyond | Developer $20/mo credits | V |
| Cerebrium | L4 0.80 (0.000222/s) · A10 1.10 | 1.95 (0.000542/s) | 2.10 (0.000583/s) | 3.40 (0.000944/s) | per second | — | $0.05/GB-mo, first 100 GB free | Hobby free + compute | V |
| Google Cloud Run (GPU) | L4 $0.0001867/s ≈ 0.67/h (zonal redundancy off), $0.0002909/s ≈ 1.05/h (on) + 4 vCPU/16 GiB minimum; "L4 instances start in approximately 5 seconds"; services scale to zero, min instances billed | | | | per second | none at zero | GCS | GCP budgets | V (docs) / 3P for the price (official page 457 days old per search metadata; tracker verified 2026-09-17) |
| Lambda | A10 1.29 | — | A100 40 GB 1.99; 80 GB 2.79 (8× only) | PCIe 3.29 / SXM 4.29 (1×) | not stated on page | full price while running | not listed | not verified | V |
| Vast.ai | marketplace; 4090 floor $0.15–0.31/h, 5090 median ~$0.63/h [3P, Aug–Sep 2026] | | | | per second; interruptible "50%+ cheaper" | stopped instances still pay disk; bandwidth $/TB per host | per-host | auto-stop at $0 balance; low-balance email; no spend-limit feature documented | V (billing docs) / 3P (prices) |
| Hyperbolic | H100 SXM tracked at $1.50 (Jun) → $2.89 (Jul) → $3.19/h (Aug 2026); official page returned 404 | | | | | | | | 3P only — **not verified** |
| Novita | 4090 on-demand $0.35/h, spot $0.18/h (vendor blog, undated); pricing page lists only token APIs | | | | | | | | 3P / not verified |
| AWS EC2 spot | g6.xlarge (1×L4) on-demand ~$0.80/h, spot $0.42–0.74/h us-east-1 (Jul 2026 snapshots); g6e.xlarge (1×L40S) on-demand ~$1.86/h, spot $0.87–1.40/h | | | | per second | full price while running | EBS extra | AWS Budgets | 3P |
| Azure spot (NC A10) | not found — **not verified** | | | | | | | | — |

Observations (INF): for 24–48 GB work, the cheapest *reliable* per-second options are Cloud Run L4 ($0.67/h), Modal/Cerebrium
L4 ($0.80/h) and RunPod L4 ($0.59 pod / $0.69 serverless). For 48 GB the L40S costs $1.09 (RunPod pod) … $1.95 (Modal) … $3.51
(Replicate). Modal and RunPod serverless are within 11 % of each other on L40S/A100; the decisive differences are elsewhere
(budgets, Volumes free to 1 TiB, cron, cold-start behaviour, API maturity).

### 2.2 Qualitative notes

- **Modal**: containers "boot in about one second", warm-up "seconds to minutes" depending on model load; memory snapshots cut
  warm-up; weights baked into the Image or on a Volume. Volumes: background commit every few seconds + on shutdown; last write
  wins; v1 ≤ 5 concurrent writers, 500k inodes; v2 no file-count limit, files < 1 TiB; `modal volume get/put` from outside;
  `CloudBucketMount` for S3/R2/GCS (sequential large-file reads; no append/rename). Cron: `modal.Cron("0 6 * * *", timezone=…)`
  runs after `modal deploy` "without any further interaction"; cannot be paused (remove + redeploy). Web endpoints with
  `Modal-Key`/`Modal-Secret` proxy auth; 200 req/s per new account. Budgets: "Only Workspace Owners and Managers can set"; at the
  spend limit Modal "stops workloads that would incur additional out-of-pocket charges". Outages 2026 [3P trackers]: Apr 28 DNS
  change (~1.5 h), Jun 3 auth failure (~49 min), several short regional ones. [V except outages]
- **fal**: custom apps as `fal.App` Python classes or `ContainerImage` (Dockerfile / private registry); `fal run` for a temporary
  worker, `fal deploy` for a persistent URL; queue-based with webhooks (queue docs not read). Reliability [3P]: ~0.9 incidents/month,
  23 h total over 2 years; Jun 29 2026 DNS incident 1h14m. [V except reliability]
- **Replicate**: public models bill only active time; private models/deployments bill all online time (one L40S kept online ≈
  $2,527/mo [3P arithmetic]). Trainings bill the trainer's hardware per second. Spend caps: not on the billing page → not verified.
- **Baseten**: per-minute; "do not pay for idle time"; independent cold-start figures conflict (sub-10 s vs 16–60 s) [3P].
- **Cloud Run GPU**: instance-based billing; min instances billed at full rate; L4 only (RTX PRO 6000 not confirmed); regions
  us-central1, us-east4, europe-west1/4, asia-southeast1; new projects get quota 3 GPUs (zonal redundancy off) [V docs].
- **Vast.ai**: cheapest raw $/h but host-dependent reliability, bandwidth and disk prices; no spend-limit feature; stopped disks bill.

---

## 3. Serverless vs persistent pod: cost model with worked numbers

Speed assumptions (all [3P], wide ranges — measure before relying): FLUX.1-dev 1024² ~20–28 steps: 4090 FP8 4–12 s, L40S BF16
7–8 s, H100 FP8 1.6–2.2 s. Wan 2.2 A14B 5 s 720p: 4090 (quantised/offload) 4.3–9 min (one source 24 min), H100 ~5–17 min
(sources do not say i2v vs t2v or step counts). FLUX LoRA 1000 steps rank 16: 4090 20–40 min, A100-80 20–35 min, ai-toolkit on
A100 ~38–41 min; Replicate's 8×H100 trainer ~2 min.

Break-even (INF, from V prices): RunPod L40S serverless $1.75/h vs pod $1.09/h → serverless is cheaper when the pod would be
busy less than 1.09/1.75 = **62 %** of its wall-clock life. Modal L40S $1.95/h → break-even 56 %. Historically this creator's
pods were busy far less than that (a forgotten pod billed for hours), so per-second scale-to-zero wins unless a job is
≥ 1 hour of continuous GPU work.

### 3.1 Forty FLUX.1-dev images (1024², one LoRA, one batch)

| Route | Arithmetic | Cost | Tag |
|---|---|---|---|
| fal FLUX.1 dev API | 40 × 1.05 MP × $0.025 | **$1.05**; with LoRA $0.035/MP → **$1.47** | V prices, INF arithmetic |
| Replicate flux-dev | 40 × $0.025 | **$1.00** (LoRA model price not verified) | V |
| Together FLUX.2 [dev] | 40 × $0.0154 | $0.62 (different model) | V |
| Modal L40S own ComfyUI | 40 × 8 s = 320 s + ~60 s warm-up (weights on Volume) = 380 s × $0.000542 + CPU/RAM ≈ $0.02 | **≈ $0.23** (inside the $30/mo credit) | V prices, 3P speed |
| RunPod serverless L40S + worker-comfyui | 320 s + cold start 60–120 s + 5 s idle ≈ 440 s × $0.000486 | **≈ $0.21**; 3 parallel workers each pay their own cold start → ≈ $0.25 | V prices, 3P speed |
| RunPod pod L40S secure | 15 min total (5 min startup + 5 min gen + margin) = $0.27; left 1 h = $1.09; **forgotten 24 h = $26.16** + NV 100 GB $7/mo | $0.27 … $26 | V prices |
| RunPod pod 4090 community | 15 min at $0.34/h | $0.09 (community = less reliable, no NV) | V |

Reading: hosted APIs cost ~4–5× the raw GPU seconds but zero engineering, zero idle risk, LoRA upload included (fal). Self-hosting
only pays off with custom nodes or > ~200 images/batch — and the "forgotten pod" tail risk is 100× the batch cost.

### 3.2 One 5-second Wan 2.2 image-to-video clip (720p)

| Route | Arithmetic | Cost | Tag |
|---|---|---|---|
| fal Wan 2.2 A14B i2v | 5 s × $0.08 (720p); 480p 5 × $0.04 | **$0.40** / $0.20 | V |
| fal LTX-Video 13B distilled i2v | 5 s × $0.04 | **$0.20** ($0.40 with detail pass) | V |
| Replicate Pruna fast Wan 2.2 i2v 480p | flat | $0.05/video (blog; standard a14b price not verified) | V (blog) |
| RunPod pod H100 PCIe $2.89/h | 5–17 min gen = $0.24–0.82; first clip adds 10–20 min weights download ≈ $0.5–1.0 | **$0.75–1.8 first clip, $0.24–0.82 each after** | V prices, 3P speed |
| RunPod serverless H100 $4.79/h | 5–17 min + minutes of cold start (tens of GB of weights) | $0.5–1.6 | V prices, 3P speed |
| RunPod pod 4090 secure $0.89/h | 4.3–9 min quantised/offloaded | $0.06–0.13 marginal; quality/VRAM risk | V prices, 3P speed |

Reading: for 1–10 clips per video, hosted APIs are cheaper than self-hosting and avoid 30–80 GB model downloads. Self-host only
for Wan LoRAs the APIs do not serve.

### 3.3 Ten-minute video render (ffmpeg + PIL, CPU)

| Route | Arithmetic | Cost | Tag |
|---|---|---|---|
| Claude cloud session (today) | included | $0 marginal; but ties the render to the session (RULE-R1 chunking) | — |
| Modal CPU function | 8 cores × 1,800 s × $0.0000131 + 16 GiB × 1,800 × $0.00000222 | **≈ $0.25 for a 30-min render**; cron/webhook-triggerable; survives session loss | V |
| GitHub Actions job | 30 min of the 2,000 free min/mo (2-core runner, 6 h max job) | $0 within quota; slow | V |
| Hetzner shared VM | Regular Performance "from €6.49/mo" (specs not shown on the page I read) | ~€6.5/mo flat | V (price) |
| RunPod CPU pod | CPU pod prices **not verified** (pricing page I read lists only GPU) | — | — |

### 3.4 Thirty-minute FLUX LoRA training (24–48 GB GPU)

| Route | Arithmetic | Cost | Tag |
|---|---|---|---|
| fal flux-lora-fast-training | flat per run, 1000 steps default | **$2.00** | V |
| Replicate ostris/flux-dev-lora-trainer | 8×H100 $0.0122/s × ~120 s | **≈ $1.46** (official guide) | V |
| Modal A100-80 | 1,800 s × $0.000694 (+ one-off weights to Volume) | $1.25 | V prices, 3P time |
| Modal L40S | 1,800 s × $0.000542 | $0.98 | V prices, 3P time |
| RunPod pod L40S secure | 30 min + 10–15 min setup ≈ 45 min × $1.09 | $0.82 (+ forgotten-pod risk) | V prices, 3P time |
| RunPod pod 4090 secure | 20–40 min + setup | $0.45–0.90 | V prices, 3P time |

Reading: hosted trainers ≈ self-hosting within $1; use fal/Replicate for FLUX LoRAs, self-host only for Qwen-Image/Wan LoRAs
or custom captions/ranks.

### 3.5 Per-video budget under the "tens of dollars" ceiling (INF)

40–80 images ($1–3 hosted) + 4–8 clips ($1–3) + 0–1 LoRA ($2) + storage ($0.1–1/mo) + watchdog ($0) ≈ **$4–9 per video**
on hosted APIs; the same on self-hosted serverless ≈ $1–3 plus engineering time; a single forgotten L40S pod for a day ($26)
exceeds either.

---

## 4. Durable storage for assets and results

| Store | Price | Egress | Free tier | Durability features | Fit | Tag |
|---|---|---|---|---|---|---|
| **Cloudflare R2** (pricing page updated Oct 1, 2026) | Standard $0.015/GB-mo; IA $0.01 (30-day minimum) | **$0 egress** via S3 API / Workers / r2.dev | 10 GB-mo, 1 M Class A, 10 M Class B per month | Event notifications → Queues (GA Sep 2024, up to 5,000 msg/s); user-specified checksums SHA-1/256/384/512 on put/get/head, MD5 default for non-multipart; **object versioning: not found → not verified** | Best default results/assets store; Workers cron can read it for heartbeats | V |
| **Backblaze B2** | $6.95/TB-mo (≈ $0.007/GB) | free up to 3× average stored, then $0.01/GB | first 10 GB | file **versions kept by default** (lifecycle rules: keep all / last / N days; ≤ 100 rules/bucket), Object Lock; SHA-1 per file (B2 API; not re-verified today); event notifications not verified | Cheapest archive with versioning | V (price, versions) |
| **AWS S3 Standard** | ~$0.023/GB-mo first 50 TB [3P; official table did not render] | $0.09/GB after 100 GB/mo free [3P] | $200 credits for new accounts (Jul 2025) [V] | versioning, checksums, lifecycle (standard, not re-verified) | Most expensive egress; no reason here | 3P |
| **Wasabi** | $7.99/TB-mo, **1 TB minimum**, **90-day minimum retention** | free (fair-use ≈ ≤ storage) | none | — | 1 TB minimum makes it wrong for tens of GB | V |
| **Hugging Face Hub repos** | public "best-effort" free; private 100 GB free, PRO 1 TB then $18/TB-mo; public add-on $12/TB-mo | free (CloudFront) | — | git-backed: full history, LFS/Xet dedup; limits: < 100k files/repo, < 10k entries/folder, file < 200 GB (500 GB hard), ~50–100 files per commit; rate limits (5-min windows): free 1,000 API / 5,000 resolve, PRO 2,500 / 12,000; deleting LFS pointers does not free space; "a git repository is not meant to work as a database with a lot of writes"; datasets must be for community reuse | Wrong for mutable per-video renders; fine for publishing a finished LoRA | V |
| **HF Storage Buckets** (new repo type) | "simple per-TB pricing" at hf.co/storage — **not verified**; free allowance | — | — | mutable, **non-versioned**, S3-compatible API, `hf buckets sync/cp`, server-side copy from repos, **webhooks + SSE change stream** (`/api/buckets/.../events`, ~15 min replay), CDN pre-warming; "deletions are immediate and permanent" | Credible R2 alternative inside the HF ecosystem once price is known | V (features) |
| **RunPod network volume** | $0.07/GB-mo (< 1 TB) | none | — | S3 API in 15 DCs (`s3api-<dc>.runpod.io`), PutObject < 500 MB else multipart (part ≤ 500 MB), no versioning, no pre-signed URLs, no DeleteObjects yet, `aws s3 sync` unreliable > 10k files; data lost if balance stays at $0; pins DC; concurrent writers may corrupt | Model cache per DC only — not an archive | V |
| **Modal Volume** | $0.09/GiB-mo, 1 TiB free | $0.04/GiB egress | 1 TiB | commit/reload semantics, last-write-wins, `modal volume get` for > 16 MB | Model cache + scratch for Modal jobs; mirror results to R2 | V |

Recommendation (INF): one R2 bucket per channel (`jobs/<slug>/job-NNN/...` mirroring `jobs/` on disk), `sha256` sidecar files
written by the job (R2 stores user checksums too), lifecycle rule to IA after 30 days; B2 if versioning is required; a HF model
repo only for a finished LoRA the creator wants to keep public/private long-term.

---

## 5. Watchdog patterns that do not depend on the GPU host or on the Claude session

| Mechanism | Facts | Reliability | Cost | Tag |
|---|---|---|---|---|
| **Cloudflare Workers Cron Trigger** | UTC cron, shortest example every minute; Free plan: **5 cron triggers/account, 100,000 requests/day, 10 ms CPU per invocation, 50 subrequests**; Paid $5/mo: 10 M requests, 30 M CPU-ms, 5 min CPU; changes take up to 15 min to propagate | A 2026 benchmark found Cloudflare's scheduler far more punctual than GitHub's [3P] | $0 (free plan is enough: one RunPod GET + one ntfy POST ≈ 2 subrequests, < 10 ms CPU) | V |
| **GitHub Actions `schedule`** | min interval 5 min; "can be delayed during periods of high loads… some queued jobs may be dropped"; disabled after 60 days inactivity (public repos); default branch only; Free 2,000 min/mo private (public free), $0.006/min after | Jan 20 2026 incident: 23 % of runs delayed, avg 11 min [V status]; community reports of 17–26 min median lateness and skipped 5-min ticks [3P] | $0 within quota (a 1-min check every 15 min ≈ 2,900 min/mo → exceeds the free 2,000 on a private repo; every 30 min ≈ 1,450 min/mo fits) | V / 3P |
| **Modal `modal.Cron`** | server-side after `modal deploy`; cannot be paused; logs in dashboard | depends on Modal (several short 2026 incidents [3P]) | CPU seconds only, inside $30/mo credit | V |
| **Cheap always-on VM** | Hetzner Regular Performance from €6.49/mo [V]; Oracle Always Free ARM reportedly cut to 2 OCPU/12 GB in 2026 [3P] | you own uptime, patches, and the risk the VM itself dies silently | €4–7/mo | V / 3P |
| **Provider-side limits** | RunPod: $80/h account spend limit, low-balance email, prepaid balance (pods stop at $0); Modal: budget + spend limit stops workloads; Vast: stop at $0 balance; Replicate/fal: not verified | hard floor, but coarse (hours, not minutes) | $0 | V |
| **In-job self-timer** | `sleep 2h; runpodctl pod stop $RUNPOD_POD_ID &` in the pod start command (docs); serverless `executionTimeout` (default 600 s) and `ttl` | dies with the pod process; cannot survive a hung container — needs the external layer | $0 | V |
| **Provider webhooks** | RunPod serverless job webhook (200 required, 2 retries); Modal web endpoints; HF bucket webhooks; R2 event notifications | push, but nothing fires for a pod that never started — polling is still needed | $0 | V |

### Phone notification and kill-switch

| Channel | Facts | Tag |
|---|---|---|
| **ntfy** | free ntfy.sh (topic = password; access tokens available); up to 3 action buttons per message: `view`, `http` (default POST, custom headers/body, `clear=true` only on success), `broadcast` (Android); priorities 1–5 (5 = pop-over + long vibration); messages cached 12 h; attachments 15 MB / 100 MB per visitor; self-host defaults: 60-request burst, +1 per 5 s; Pro $5/$10/$20 per month (2,500/20,000/50,000 msgs/day, phone calls on Pro) | V |
| **Pushover** | $4.99 one-time per platform, 30-day trial; 10,000 messages/month per account free; priority 2 = emergency: repeats every `retry` ≥ 30 s until acknowledged, `expire` ≤ 10,800 s, ≤ 50 retries, acknowledgement `callback` URL; message ≤ 1,024 chars | V |
| **Telegram bot** | free; `setWebhook` or `getUpdates` (mutually exclusive); inline keyboards deliver `callback_query`; ≤ 1 msg/s per chat, ~30 msg/s bulk; send files ≤ 50 MB, download ≤ 20 MB; needs an HTTPS receiver for buttons (a Worker) | V |
| **GitHub Mobile** | can run `workflow_dispatch` workflows from Repository → Actions → Workflows (changelog 2024-07-30); needs write access, workflow on default branch; inputs ≤ 25, payload ≤ 65,535 chars | V |

Kill-switch design (INF, built from the V facts above):
1. ntfy alert carries an `http` action `STOP ALL` → `POST https://<worker>/kill?token=…` (secret token header). The Worker calls
   RunPod REST `POST /pods/{id}/stop` (or `DELETE` to terminate) for every pod, and `modal app stop` equivalents, then posts a
   confirmation to ntfy. One tap, no app install beyond ntfy.
2. GitHub Mobile `workflow_dispatch` "kill-all" workflow as the second path (independent of Cloudflare; slower, but the repo's
   secrets and `python -m explainer_engine.cloud.runpod stop` already exist).
3. Pushover emergency priority (or ntfy priority 5) for "pod RUNNING with no heartbeat" so the phone keeps ringing until acknowledged.

---

## 6. Observability basics

What RunPod exposes [V]: `GET /v2/pods/{id}` → `status`, `cost` ($/h), `startedAt`, `runtime.uptime`, `runtime.gpus[].util`,
`runtime.gpus[].memoryUtil`, `runtime.cpu.util`, `runtime.memory.util` (all null unless RUNNING); SSE logs; `/v2/billing/pods`
hourly buckets per pod; `runpodctl user` → balance, `currentSpendPerHr`, `spendLimit`. Serverless: `/status/{id}` with
COMPLETED/FAILED/CANCELLED/TIMED_OUT, 30-min result retention.
What Modal exposes [V]: dashboard logs and per-function metrics; budgets; `modal volume` CLI; web endpoints you write yourself.

Proposed job-state contract (INF; consistent with the repo's `core/store.py` atomic writes):
- `jobs/<slug>/job-NNN/state.json` (exists today) gains `provider`, `resource_id` (pod id / Modal call id / fal request id),
  `started_at`, `plan_cap_usd`, `plan_cap_minutes`, `spent_usd_estimate`.
- `heartbeat.json` written every 60 s by the running stage: `{ts, stage, step, total, resource_id, gpu_util, note}`; mirrored to
  R2 (`PutObject`, < 1 KB) so the watchdog never needs the pod.
- Watchdog rules (Cloudflare Worker cron every 5 min): (a) any pod `RUNNING` whose id is not in an active `state.json` on R2 →
  stop + alert ("orphan pod"); (b) `RUNNING` with heartbeat older than 10 min → alert, stop at 20 min; (c) `RUNNING` with
  `gpus[].util` < 5 % for 20 min → alert; (d) `uptime` > `plan_cap_minutes` → stop + alert; (e) `/v2/billing/pods lastN=1
  bucketSize=hour` sum > hourly cap, or `runpodctl user` balance < threshold → alert; (f) pod `STARTING`/`PROVISIONING` > 15 min
  → alert (the "never starts" case) and terminate; (g) every pod must carry a `-until-<epoch>` name (the tmr-engine convention)
  or be stopped.
- Every stop/terminate the watchdog performs is appended to `docs/COST_AND_TIME_MODEL.md`'s ledger by the next session (the Worker
  writes a line to R2; the session ingests it) — keeps invariant 2's "estimate and log" intact.

---

## 7. Risks and uncertainties

- RunPod REST **v2 is beta**; v1 retires **2026-11-15**. If `cloud/runpod.py` targets v1 (or GraphQL fields that move), the pod
  manager can break the week before a shoot. Action: confirm which API the module uses; add a test against the v2 schema.
- RunPod regional network/storage incidents are frequent (Aug–Oct 2026). A network volume pins the DC; "zero GPU" pods are
  documented behaviour, not a bug. Stateless workers + R2 avoid both.
- Cold starts for large video models (tens of GB) on any serverless platform are minutes, not the marketed sub-second; budget for
  them or keep clips on hosted APIs.
- Prices move monthly (Hyperbolic tripled in three months [3P]; Modal repriced Volumes in June 2026 [3P]); every number above
  needs re-reading before it enters `config/spend_caps.json` or a skill.
- Hosted APIs: model versions get replaced; per-output billing hides GPU type; provider terms for commercial use must pass the
  repo's rights check (D-50: the creator picks the provider per batch; `.claude/settings.json` hook guards paid calls).
- Not verified: R2 object versioning; HF Storage Buckets pricing; fal/Replicate spend caps; RunPod CPU pod prices; Azure spot
  prices; Hyperbolic/Novita official prices; whether Modal budgets send e-mail alerts; current ntfy.sh public-server limits.
- GitHub cron is a backup, not a primary watchdog (10–30 min lateness, dropped ticks, 60-day disable).
- Cloudflare Worker free plan: 10 ms CPU and 50 subrequests per invocation — a Worker that loops over many pods or does retries
  may need the $5 paid plan.
- A watchdog with stop/terminate rights holds a RunPod API key outside the Claude session: scope it (RunPod API keys have
  read/write scopes in the console — not re-verified today) and rotate it.

---

## 8. Recommended architecture sketch (proposal for the creator; not a decision)

```
                 phone (ntfy app / GitHub Mobile)
                    ▲ alerts            │ tap "STOP ALL" / Run workflow
                    │                   ▼
   Cloudflare Worker (free): cron */5  ─┬─► RunPod REST v2: list pods, runtime.gpus, billing; stop/terminate
   reads heartbeat.json + state.json    ├─► Modal: budget already enforced by Modal; app stop on kill
   from R2; posts ntfy                  └─► writes watchdog log line to R2
   GitHub Actions cron */30 (backup)  ──► python -m explainer_engine.cloud.runpod check/guard/stop (existing CLI)

   Claude cloud session (when open) ──► plans, approves, launches jobs, assembles video (ffmpeg/PIL) ──► R2
        │
        ├── Tier 1 (default, per-output billing): fal (FLUX dev/LoRA, Wan 2.2, LTX, flux-lora-fast-training);
        │                                          Replicate as fallback (flux-dev, Pruna Wan, FLUX LoRA trainer)
        ├── Tier 2 (custom code, scale-to-zero): Modal functions (ComfyUI workflow, Qwen-Image, Wan LoRA) with weights on a
        │       Modal Volume (1 TiB free) + CloudBucketMount(R2); budget + spend limit set in Modal; webhook endpoint returns job id
        │       — or RunPod serverless + worker-comfyui + network volume if the creator prefers to stay on RunPod
        ├── Tier 3 (exception, interactive): RunPod pod with network volume, `-until-<epoch>` name,
        │       `sleep Nh; runpodctl pod stop` in the start command, terminated (not stopped) at the end
        └── Results: every stage uploads outputs + sha256 sidecars + state.json/heartbeat.json to R2 (zero egress);
                     finished LoRAs optionally to a private HF model repo; nothing durable lives on a pod or a network volume
```

Which provider for which workload (INF from sections 2–3):
- (a) image bursts 1–50, LoRA sometimes → fal / Replicate hosted; Modal or RunPod serverless only for custom ComfyUI graphs.
- (b) 5–10 s image-to-video → fal Wan 2.2 / LTX hosted ($0.20–0.80 per clip); self-host only with a Wan LoRA.
- (c) 10-minute ffmpeg/PIL render → stays in the Claude session (chunked, RULE-R1); Modal CPU function (~$0.25) or GitHub Actions
  as the session-independent fallback.
- (d) 30-min LoRA training → fal $2 / Replicate ~$1.5 for FLUX; Modal L40S/A100 (~$1–1.3) for non-FLUX bases.

Minimal change to the repo (INF): (1) `cloud/runpod.py` → REST v2 + heartbeat/billing reads; (2) a Worker (or Modal cron) that
calls the same checks and ntfy; (3) `config/spend_caps.json` gains per-job minute caps the watchdog enforces; (4) R2 as the
`jobs/` mirror in `core/store.py`; (5) a `provider` field in paint plans so fal/Replicate/Modal are first-class choices (D-50).

---

## 9. Sources (read 2026-10-22 unless noted; page dates as shown on the page)

RunPod (official)
- https://www.runpod.io/pricing — "Updated October 8, 2026": pod, serverless, storage prices.
- https://docs.runpod.io/pricing/serverless — billing window, idle timeout, container disk, $80/h spend limit.
- https://docs.runpod.io/references/billing-information — per-second billing, stopped-pod storage, balance-at-$0 behaviour, alerts.
- https://docs.runpod.io/storage/network-volumes — price, serverless mount, DC pinning, performance, data at $0 balance.
- https://docs.runpod.io/storage/s3-api — 15 DCs, endpoint format, supported/unsupported S3 operations, limits.
- https://docs.runpod.io/pods/manage-pods — stop vs terminate, zero GPUs, `sleep 2h; runpodctl pod stop`, troubleshooting.
- https://docs.runpod.io/pods/troubleshooting/zero-gpus and /pods/troubleshooting/pod-migration — zero-GPU recovery (via search summary).
- https://docs.runpod.io/references/runpodctl/runpodctl_start_pod — pod CLI flags (no auto-stop flags).
- https://docs.runpod.io/runpodctl/reference/runpodctl-user — `clientBalance`, `currentSpendPerHr`, `spendLimit`.
- https://docs.runpod.io/api-reference/overview — REST v1 deprecated, retired 2026-11-15.
- https://docs.runpod.io/api-reference-v2/overview and /api-reference-v2/pods/get-a-pod.md — v2 beta; pod schema incl. `runtime.gpus[].util`.
- https://docs.runpod.io/api-reference-v2/pods/stream-pod-logs.md — SSE logs.
- https://docs.runpod.io/api-reference-v2/billing/get-pod-billing-history — `/v2/billing/pods` parameters and fields.
- https://docs.runpod.io/serverless/endpoints/endpoint-configurations — timeouts, workers, FlashBoot, GPU priority, network volume, scaling.
- https://docs.runpod.io/serverless/endpoints/send-requests — `/run`, `/runsync`, webhook retries, policy, `s3Config`.
- https://docs.runpod.io/flash/pricing — Flash SDK.
- https://docs.runpod.io/pods/templates/overview — templates.
- https://github.com/runpod-workers/worker-comfyui — ComfyUI serverless worker.
- https://uptime.runpod.io/ — status and incident history (read 2026-10-22 08:15 UTC).
- https://www.runpod.io/blog/introducing-flashboot-serverless-cold-start (2023 measurements) and https://runpod.io/product/serverless (marketing claim).

RunPod (independent)
- https://statusgator.com/services/runpod ; https://www.pulsapi.com/services/runpod (99.80 % 30-day, Oct 19 2026)
- https://hackceleration.com/labs/review/runpod (2026 review; outage count unsourced)
- https://github.com/tensor4all/tenferro-rs/issues/1921 (provisioning failures from 2026-09-24, one user)
- https://github.com/brendanlong/gpu-coordinator/issues/83 (network volume pins DC)
- https://markaicode.com/errors/runpod-timeout-fix/ (248 s → 42 s cold start with network volume, anecdotal)

Alternatives (official)
- https://modal.com/pricing ; https://modal.com/docs/guide/cold-start ; https://modal.com/docs/guide/cron ; https://modal.com/docs/guide/webhooks ;
  https://modal.com/docs/guide/budgets ; https://modal.com/docs/guide/volumes ; https://modal.com/docs/guide/cloud-bucket-mounts
- https://fal.ai/pricing ; https://fal.ai/models/fal-ai/flux-lora-fast-training ; https://fal.ai/models/fal-ai/wan/v2.2-a14b/image-to-video ;
  https://fal.ai/models/fal-ai/ltx-video-13b-distilled/image-to-video ; https://fal.ai/docs/private-serverless-models
- https://replicate.com/pricing ; https://replicate.com/docs/topics/billing ; https://replicate.com/docs/get-started/fine-tune-with-flux ;
  https://replicate.com/blog/wan-22 (Pruna Wan prices)
- https://www.baseten.co/pricing/ ; https://www.together.ai/pricing ; https://fireworks.ai/pricing ; https://lambda.ai/pricing ;
  https://www.koyeb.com/pricing ; https://www.beam.cloud/pricing ; https://www.cerebrium.ai/pricing ; https://vast.ai/pricing ; https://docs.vast.ai/billing
- https://docs.cloud.google.com/run/docs/configuring/services/gpu (L4 facts); https://cloud.google.com/run/pricing (did not render; L4 price via
  https://cloudgpuprices.com/vendors/google-cloud verified 2026-09-17 and https://cloudchipr.com/blog/cloud-run-pricing)

Alternatives (independent)
- https://dev.to/mrzitoun/benchmarking-serverless-gpus-modal-vs-runpod-vs-replicate-cold-starts-2026-a5c and https://github.com/mrzitoun/awesome-serverless-gpu-latency (Sep 2026)
- https://isdown.app/status/modal-labs/outage-history ; https://pingoru.io/providers/modal ; https://pingoru.io/providers/fal/outage-history
- https://www.spheron.network/blog/gpu-price-increase-2026-hyperbolic-h100/ ; https://usagepricing.com/blueprint/activity/hyperbolic-2026-08-04-price-change
- https://blogs.novita.ai/rtx-4090-from-0-18-hr-on-novita-ai-instant-gpu-access/ (undated vendor blog)
- https://calculator.holori.com/aws/ec2/g6.xlarge/us-east-1 ; https://calculator.holori.com/aws/ec2/g6e.xlarge (Jul 16 2026) ; https://compute.doit.com/spot/us-east-1/g6e.xlarge
- https://www.beam.cloud/blog/nvidia-rtx-5090-pricing ; https://computeprices.com/providers/vast/gpus/rtx4090 (Aug 2026) ; https://gpus.io/en/gpus/rtx4090

Speed benchmarks (all third-party)
- FLUX: https://github.com/comfyanonymous/ComfyUI/discussions/4571 ; https://packet.ai/blog/flux-image-generation-gpu-vram-requirements ;
  https://www.spheron.network/blog/best-gpu-ai-image-generation-2026/
- Wan 2.2: https://www.runpod.io/articles/guides/comfyui-wan-2-2 ; https://www.spheron.network/blog/deploy-wan-2-1-ai-video-generation-gpu-setup/ ;
  https://localaimaster.com/blog/wan-video-generation-guide ; https://willitrunai.com/blog/wan-2-2-vram-requirements
- LoRA: https://jarvislabs.ai/ai-faqs/best-gpu-for-flux ; https://replicate.com/lucataco/ai-toolkit

Storage (official)
- https://developers.cloudflare.com/r2/pricing/ (last updated Oct 1, 2026) ; https://developers.cloudflare.com/r2/buckets/event-notifications/ ;
  https://developers.cloudflare.com/r2/platform/changelog (checksums Aug 2024)
- https://www.backblaze.com/cloud-storage/pricing ; https://www.backblaze.com/docs/cloud-storage-lifecycle-rules
- https://wasabi.com/pricing ; https://aws.amazon.com/s3/pricing/ (tables did not render; $0.023 and $0.09 from
  https://www.cloudforecast.io/blog/amazon-s3-pricing-and-optimization-guide/ and https://upstash.com/blog/aws-s3-pricing-explained-2026, Aug 2026)
- https://huggingface.co/docs/hub/storage-limits ; https://huggingface.co/docs/hub/rate-limits (limits "in September '25") ; https://huggingface.co/docs/hub/storage-buckets

Watchdog / notifications (official)
- https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows (schedule, workflow_dispatch)
- https://docs.github.com/en/billing/concepts/product-billing/github-actions (2,000 free min, $0.006/min)
- https://github.blog/changelog/2024-07-30-run-workflows-set-as-workflow_dispatch-manually (GitHub Mobile)
- https://www.githubstatus.com/incidents/fw294tth5m8y (Jan 20 2026 scheduled-run delays) ; https://github.com/orgs/community/discussions/185355 ;
  https://josephhall.org/blog/small-bake-off/ (GitHub vs Cloudflare scheduler lateness)
- https://developers.cloudflare.com/workers/configuration/cron-triggers/ (updated Oct 17, 2026) ; https://developers.cloudflare.com/workers/platform/limits/ ;
  https://developers.cloudflare.com/workers/platform/pricing/ (updated Oct 2, 2026)
- https://docs.ntfy.sh/publish/ ; https://docs.ntfy.sh/config/ ; https://ntfy.sh/ (Pro tiers)
- https://pushover.net/pricing ; https://pushover.net/api
- https://core.telegram.org/bots/api ; https://core.telegram.org/bots/faq
- https://www.hetzner.com/cloud/ ; Oracle Always Free cut: https://korben.info/en/oracle-quietly-cuts-free-arm-offer-in-half.html (3P)
