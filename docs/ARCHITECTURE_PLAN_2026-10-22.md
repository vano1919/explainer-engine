# Architecture plan (the 2026-10-22 master brief, stages A-H)

The creator's master brief of 2026-10-22 asks for a production system that keeps one visual world across episodes, uses the
best current models through replaceable adapters, never loses a result or leaves a pod billing, and shows the creator from a
phone what happened since the last look. This plan is stage A's output: it is built on what the code really does today
([research/REPO_AUDIT_2026-10-22](research/REPO_AUDIT_2026-10-22.md)) and on the dated tooling research
([TOOLING_RESEARCH](TOOLING_RESEARCH.md)). Status of the whole plan: decision [D-70](DECISIONS_AND_OPEN_QUESTIONS.md), an
approval gate. Nothing paid runs before the creator's word; stage B needs no paid call at all.

## 1. Where the code stands (stage A audit, the facts that shape the plan)

| Responsibility in the brief | Today | Gap |
|---|---|---|
| Cloud Job Manager | `cloud/runpod.py`: create/guard/stop/sweep/cost/check/logs, verified stop and delete, no blind re-POST, ledger reservation, 36 fake-API tests; **ported to REST v2 on 2026-10-22** (v1 is retired 2026-11-15) | one provider; no job state history |
| Infrastructure Watchdog independent of pod and session | the guard is a detached process on the Claude sandbox; it dies with the container and `check()` then reports a live pod as fine | nothing watches a pod when the session is gone; no heartbeat, no incident log, no inbound events |
| Durable storage of results | none in this repo; TMR `cloud/store.py` pushes to the HF dataset from inside the pod | a sole copy on the pod disk is the documented cause of two lost picture runs |
| Incident history | prose in TMR `docs/INCIDENTS_RUNPOD.md`, `docs/PROGRESS.md`, [RISK_REGISTER](RISK_REGISTER.md) R-29 | no fingerprints, no machine-readable record, three unreconciled balance drops |
| Provider-agnostic image layer | `imagegen/plan.py` lists gemini/pod/local but only Gemini executes; `production/paint.py` constructs `GeminiClient` directly | no interface; cache key differs between sync and batch; no seed or model-version field |
| World Bible / Asset Library | `world/resolver.py` + `eras.json` + `look_v2.json` resolve a look on the fly; references live per script (`look.style_refs`, `cast.<id>.reference`, face sheets) | [ASSET_SYSTEM](ASSET_SYSTEM.md)'s asset record, licence register and tag search exist only on paper; no persisted, versioned world file |
| Scene Package | `production_script/3` segments with `scene`, lines, shots, pictures; approvals bound to hashes (paint plans, scenario, references, editorial review) | fits the brief's Scene Package already; staging/continuity of PR #17 is not merged yet |
| Motion | `production/assemble.py` Ken Burns + chunked ffmpeg, resumable | no parallax, no generated motion (none wanted by default) |
| QA | deterministic validators (PV, SC, N, MO, ENG, PC) + `editorial_gate` + in-session `sheet_review` | no automatic repaint loop; visual review is one pass |
| Status for the creator | per-module CLIs; `run.json` ledger; `production_gate` | no `status`/`doctor`/`incidents` view across jobs; no record of the watchdog's own actions |

Dead or document-only pieces the plan retires or revives: `core/store.JobStore` and `core/jobs` (tested, unused by the
pipeline: revived as the job-state home), `pod_text` engine (no producer), Remotion renderer, `qa/style_distance.py`,
`schemas/world.schema.json`, `assets/LICENSES.json` (named in documents, absent in code: either built in stage C or
struck from the documents).

## 2. Target shape (responsibilities, not services)

```
creator's phone ── ntfy alerts + "STOP ALL" button ── GitHub Mobile "kill-all" workflow (second path)
        ▲                                                       │
Cloudflare Worker cron */5 (free) ── RunPod REST v2 / Modal ── stop, terminate, alert; reads heartbeat + state from R2
GitHub Actions cron */30 (backup) ── python -m explainer_engine.cloud.runpod check  (exists)
        ▲
Claude session (when open): plan → approve → launch → assemble (ffmpeg/PIL, RULE-R1) → QA → unlisted upload
   ├─ cloud/jobs.py   job record + state history + heartbeat (revives core/store.JobStore; state.json + events.jsonl)
   ├─ cloud/providers/  adapter interface: runpod (pods, serverless), modal, fal, replicate; one error vocabulary
   ├─ cloud/store.py   durable copy of every stage output + sha256 sidecars (R2; HF for finished deliverables)
   ├─ cloud/incidents.py  fingerprint → cause → action → outcome, appended, searched before any diagnosis
   ├─ imagegen/providers  ImageProvider interface (generate, edit, estimate, refs, seed); gemini, bfl, fal, pod
   ├─ world/bible.json (versioned, approval status) + assets/library.json (ids, provenance, licence, hash, parent)
   └─ qa: deterministic gates unchanged; Gemini Flash whole-video semantics; Claude in-session frames
```

Every box maps to an existing module where one exists; new modules are listed with the stage that builds them. The
spend ceilings stay only in `config/spend_caps.json` (invariant 1); the ledger (`core/ledger.py`) stays the one money record.

## 3. Stages

### Stage B: Infrastructure Guardian (no paid call; the first thing to build)

1. **REST v2 port** of `cloud/runpod.py` (`status`, `cost`, `runtime.gpus[].util`, `/v2/billing/pods`, SSE logs) behind the
   existing `Api` transport so the 27 fake-API tests keep running against a v2 fixture. Deadline: before 2026-11-15.
2. **Job record with history**: `jobs/<slug>/job-NNN/state.json` (revive `core/store.JobStore`) + `events.jsonl`
   (every transition with time, reason, log pointer) + `heartbeat.json` (60 s, written by the running stage). States
   QUEUED → PROVISIONING → STARTING → MODEL_LOADING → READY → RUNNING → CHECKPOINTING → UPLOADING → SUCCEEDED, with
   FAILED, RETRYING, STALLED, STOPPING, STOPPED, RECOVERY_REQUIRED; mapped from RunPod's PROVISIONING/STARTING/RUNNING/
   EXITED/ERROR/TERMINATED plus the conductor's status line. The guard and `check()` read this record, not only the
   per-pod session file, so a live pod after a sandbox restart is a *problem*, not an info line.
3. **Durable copy**: `cloud/store.py` (ported from TMR with provenance) uploads stage outputs with sha256 sidecars to the
   configured store (R2 when the creator opens the account; the HF dataset until then) and verifies before any local delete.
   The in-pod stage order becomes "push before any fatal stop" (the lost 35-picture run).
4. **Stall detection** by stage: expected duration per stage (`job_speeds.json`, ported), heartbeat age, GPU utilisation
   from v2 `runtime`, log growth; STALLED → alert; stop only when the record shows the outputs are already stored.
5. **Incident log** `cloud/incidents.py`: fingerprint (provider, resource type, stage, error class), cause, action, outcome,
   repeat count; `doctor` searches it first. Seeded with the 20 incidents already recorded in prose.
6. **External watchdog**: `cloud/watchdog.py` holds the rules as pure functions (tested); two runners call them: a
   GitHub Actions workflow (cron */30 and `workflow_dispatch` kill-all; needs `RUNPOD_API_KEY` as a repository secret) and
   a small Cloudflare Worker (cron */5, free plan) once the creator opens the account. Alerts via ntfy with an `http`
   action "STOP ALL".
7. **Status for a phone**: `python -m explainer_engine.cloud status|logs|doctor|budget|incidents|stop-all`, each printing
   "what changed since the last look" from `events.jsonl`; no invented percentages (stage + last confirmed activity).
8. **Recovery tests** (mocked, 15 scenarios of the brief: create fails, stuck STARTING, model load fails, no progress, pod
   dies, API timeout/429, store unreachable, upload fails after generation, watchdog dies, user stop, budget reached, repeated
   error, resume from checkpoint, finished job not re-run, nothing left running). Fix the latent `end_pod` NameError.

Acceptance: all existing tests pass; the 15 scenarios pass; `check` after a simulated sandbox restart flags the live pod;
a dry run of the GitHub workflow stops a fake pod; nothing paid.

### Stage C: World Bible and Asset Library

- `world/bible.json` versioned (version, date, reason, approved_by): style, palette words, light, camera language,
  architecture, materials, vegetation, graphics style, era-change rules, banned drift, approved reference ids. Resolver
  reads it; prompts cite its version. Schema `schemas/world_bible.schema.json`.
- `assets/library.json` + `explainer_engine/assets/library.py`: id `<kind>.<name>[.<variant>]`, file, category, description,
  bible version, model + version, prompt + parameters, seed, references, LoRA, licence/provenance, sha256, approval status,
  parent/derived; search by tags and by SigLIP-2/DINOv2 embedding (self-hosted, Apache); duplicate warning, never a veto.
  Three levels: bible → library → episode pack (`picture_dirs` today). Paint plans record the asset ids they produce.
- Documents reconciled: [ASSET_SYSTEM](ASSET_SYSTEM.md), [VISUAL_WORLD_ARCHITECTURE](VISUAL_WORLD_ARCHITECTURE.md),
  [CREATIVE_STYLE_BIBLE](CREATIVE_STYLE_BIBLE.md) point at the code or lose the invented module names.

### Stage D: model pilot (paid, about $3-4, ceiling $15; the creator picks providers, D-50)

`imagegen/providers/` with one `ImageProvider` interface (estimate, generate, edit, max_refs, seed, model_version) and
adapters gemini (existing client), bfl (FLUX 3 Klein), fal (Seedream 4.5, Qwen-Image-Edit-2511, LoRA training), pod
(Illustrious/Animagine via the existing pod flow). The six test shots of TOOLING_RESEARCH section 2 on every candidate, scored
by code (SigLIP-2, DINOv2) and by the creator (one collage per candidate, OR-16 style). The cache key gains model version and
seed and hashes the reference bytes once, identically for sync and batch.

### Stage E: LoRA and control, only if stage D leaves a named problem

Held-out comparison on an Apache base (Illustrious/Animagine, Qwen-Image-Edit-2511, FLUX.2 klein 4B), never on FLUX 3 Klein
Base until BFL answers the derivatives clause; ControlNet Union for pose/depth/lineart; masks and bounding boxes for edits.
Decision by the measured scores, not by assumption.

### Stage F: Scene Package pipeline

`production_script/3` already carries the Scene Package fields; add `bible_version`, `asset_ids`, `new_assets`, `motion`
(still / parallax / generated with first+last frame) and `review` per segment; merge PR #17's staging and continuity review
when the creator says so; invalidate only the downstream artifacts that depend on a changed text (hash per segment).
2.5D parallax lands in `production/assemble.py` as a new motion kind (Depth-Anything-3 BASE depth maps, numpy displacement).

### Stage G: one pilot episode end to end; Stage H: production readiness

One short episode through the whole flow with the Guardian live; measure cost per approved scene, incidents, recoveries,
QA findings; then the readiness report that separates done / documented only / needs approval.

## 4. What only the creator can decide (asked in the thread, 2026-10-22)

1. **The pilot** (stage D): run the six-shot pilot on FLUX 3 Klein (BFL), Seedream 4.5 (fal) and Qwen-Image-Edit-2511 (fal),
   plus the Illustrious/Animagine anchor on a RunPod community pod, about $3-4, ceiling $15? Include Nano Banana 2.1 as a
   Google control or not? Accounts needed: BFL API key, fal API key.
2. **Accounts for the Guardian**: a Cloudflare account (Workers cron + R2, both free at this size) gives the session-
   independent watchdog and durable storage; without it stage B ships the GitHub Actions path (cron every 30 min, slower)
   and keeps the HF dataset as the store. Also whether a Modal account is wanted for custom graphs (free $30 credit).
3. **Motion**: confirm the default stays stills + parallax, with generated video only for a few hero shots after a measured
   pilot (about $2.5-10 per episode).
4. **Characters**: the brief says permanent characters are not required; D-55's hero references then hold *within* an episode,
   and the World Bible carries the identity *between* episodes. Confirm.

## 5. Done, documented only, needs access or approval (as of 2026-10-22)

- **Done (stage A)**: repo audit; dated tooling research with sources; this plan; decision D-70 opened. The creator approved
  all stages on 2026-10-22 09:03 (pilot option: three models, ceiling $15; Cloudflare account yes; motion default; no
  permanent characters).
- **Done (stage B, 2026-10-22)**: items 1-8 in code and tests ([TOOL_STRATEGY](TOOL_STRATEGY.md) "The Guardian"): REST v2 port,
  job record with history and heartbeat, durable store with verification, stall detection, incident log (22 seeded), the
  watchdog rules + GitHub Actions cron and kill-all, the phone commands, the fifteen recovery scenarios, the `end_pod` fix.
  Not yet: the Cloudflare Worker runner (needs the account), pushing the job record from inside the pod (the TMR conductor
  side), the Modal/fal adapters (stage D).
- **Done (stage C, 2026-10-22)**: `world/bible.py` + `bible.json` v1.0 (draft; pinned parts, drift check, bump, recorded approval),
  `schemas/world_bible.schema.json`; `explainer_engine/assets/library.py` + `assets/library.json` (nine records from the existing
  generation ledgers), `schemas/asset_library.schema.json`; world.json and paint plans cite the version, plans name their library
  references, reusable plans register their pictures; rules WB-01..WB-10 in [WORLD_BIBLE](WORLD_BIBLE.md). Not built: embedding
  search (SigLIP-2 / DINOv2, with the stage D pilot); the creator's approval of a bible version (needs the pilot's anchors).
- **Documented only (until their stage runs)**: stages D-H in section 3 except what the audit lists as existing.
- **Needs the creator**: the four questions above; any paid call; a Cloudflare, BFL, fal or Modal account; raising a cap in
  `config/spend_caps.json`.
