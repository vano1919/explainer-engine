# Tool strategy (D-28)

Which tool makes which part of a video, what it costs, and what was measured versus assumed. Evidence comes from the
TMR repository (read-only, `vano1919/tmr-video-script-engine@d88ba8f`): `render/imagegen.py`, `render/owl_pair.py`,
`render/owl_camp.py`, `render/localimages.py`, `cloud/rp.py`, `cloud/models.json`, `docs/INCIDENTS_RUNPOD.md`.

## Who makes what

**Current routing (D-52, 2026-10-17):** every picture is painted by Gemini on the batch tier (`production/paint.py`, tiers in
`imagegen/routing.py`); narration, music and sound effects come from ElevenLabs only. The pod and Z-Image rows below are kept as
history of D-19/D-36; they are no longer used.

| Part of the video | Tool | Why | Cost | Evidence |
|---|---|---|---|---|
| Mascot pose and expression kit (made once, kept in the library) | Gemini image (`gemini-3.1-flash-image`), on a flat green background, keyed to RGBA | identity asset (D-19); the creator's references were made with Gemini; Gemini can keep one character from a reference picture | list price $0.067 (1K) / $0.101 (2K) per picture, checked 2026-10-08 in TMR, re-check before the first call | TMR keyed Gemini owls from flat green (`owl_pair.key_green`: corner-measured green, despill, 0.8 px edge blur) |
| Mouth and eye states | Gemini edits of the base pose, but only the changed region is kept | Gemini repaints the whole picture on every edit (about 5 % of pixels differ everywhere); blending whole pictures makes the character shimmer on every word | inside the kit budget | measured in TMR (`owl_pair.patch_pose` docstring) |
| World backgrounds (one per world, reused) | Z-Image-Turbo on a RunPod GPU, painted against one Gemini style reference; Gemini only for a world that the library will reuse and Z-Image cannot match | cheap, offline-licence model; no per-topic Gemini pictures (D-19) | RTX A5000 about $0.27/h; one 1536x864 picture about 14 s, so roughly $0.001 per picture plus 10-20 min of pod start-up | measured in TMR (INCIDENTS_RUNPOD 2026-10-10, 2026-10-13); licence Apache-2.0 (official model page, checked 2026-10-16) |
| Topic props and scene pictures | Z-Image-Turbo (RunPod), or the RX 5700 at home (SDXL, about 6-7 min each, free but slow) | per-topic pictures may not use Gemini | as above | TMR `localimages.py`; 13 of 23 SDXL pictures were defective in TMR run-024, so `picture_check` gates every one |
| Motion | code (Remotion): layered parallax, camera, pose tweens, bobbing, squash, glow, particles, mouth swaps on phoneme timings | image models make stills; motion in code is free, deterministic and re-renderable | $0 | D-10, D-27 |
| Explaining parts (arrows, labels, notebook doodles) | code-drawn SVG on top of the painted layers | text must be exact and editable | $0 | D-27 |
| Research and scripts | Claude Code sessions (D-13); the 7B/27B on RunPod is not used for scripts | quality of facts and imagination matters most | $0 per token | D-13; TMR's 7B needed many repairs (INCIDENTS_RUNPOD) |
| Narration | ElevenLabs (D-39, D-52; Kokoro of D-12 retired) | — | credits per read, estimated first (skill `elevenlabs-voice`) | D-39 |
| Optional signature motion (e.g. a walk loop) | Veo, only after the kit test, only for reusable loops | expensive | about $0.96 per 8 s loop in TMR, re-check | TMR `videogen.py` |

## Rules
- Image models make **poses**, not movements. "Every possible movement" means a pose library (stand, walk contact and
  passing, point, shrug, think, surprise, run, sit, hold-prop, look-back, wave, jump) plus mouth and eye states; code
  moves between them.
- The character never contains the key green; glows (the compass, the watch) are added in code, because soft glow keys
  badly on green.
- No franchise names, actors or key art in any prompt (RR-03); this holds for Gemini and Z-Image alike.
- Every generated picture is recorded with prompt, model, seed or reference, cost and date (ASSET_SYSTEM).
- Style match between Gemini identity assets and Z-Image backgrounds is a hypothesis: the kit test includes 3 Z-Image
  backgrounds next to the Gemini mascot. If they clash, the fallback is fewer, reused Gemini world backgrounds.

## Money control for RunPod (D-56: enforced in code, not by memory)
Every pod goes through `python -m explainer_engine.cloud.runpod` (`check`, `create`, `wait-ready`, `guard`, `stop`, `sweep`,
`cost`, `delete --yes`); TMR's `rp.py create/start` and raw `POST /pods` are refused by the Bash hook. Ceilings live in ONE file,
`config/spend_caps.json` (per pod, per 24 h of RunPod billing, per episode, hours, $/h, balance left, kept stopped disks); the run
ledger refuses caps above it. `create` refuses past any ceiling, without `--ledger`, or while the account has a stray pod or an
unkept stopped disk; it reserves `--max-usd` in the episode ledger and starts the guard as its own process. The guard stops the
pod at the money cap, the time cap, the end of the lifetime in its name (`-until-<epoch>`), the boot deadline or after the
conductor ended. A pod's end is STOP; deletion only on the creator's word (`--on-cap delete`, `delete --yes`, `sweep --delete
--yes`). `cost` settles the ledger with RunPod's billed amount. Session hooks (`.claude/settings.json`, `cloud/hooks.py`) run
`check` at session start and refuse to end a turn while something bills that nobody approved or guards.

RunPod facts behind it (docs.runpod.io API reference v2 and pricing, read 2026-10-19 and 2026-10-22):
- The manager speaks **REST v2** (`api.runpod.io/v2`) since 2026-10-22: REST v1 (`rest.runpod.io/v1`) is deprecated and
  retired on 2026-11-15. The balance still comes from GraphQL `myself`; GraphQL `podStop`/`podTerminate` are the fallbacks.
- Billing is per second for compute and disks. A stopped pod still bills its volume at $0.20/GB/month (running: $0.10 for
  container and volume): the stopped 60 GB preflight pod cost $0.40/day for three days (billing API, 2026-10-17..19).
- At a $0 balance RunPod stops pods; pods without a network volume are terminated and their data is lost. Deploying needs at
  least one hour of credits.
- `POST /pods` has no idempotency key and no TTL: a retried create can rent a second pod, so the manager never re-POSTs after
  an unclear answer (only after a 429) and finds the pod by its unique name instead. v2 takes ONE `gpu.id` per request (no
  list of types), so the manager tries the pool's cards one by one and moves on only after a clear refusal; a pod is born
  `PROVISIONING` with `cost` 0, so the money clock runs on the card ceiling until the real price shows.
- `GET /pods/{id}`: `status` PROVISIONING/STARTING/RUNNING/EXITED/ERROR/TERMINATED, `cost` $/h, `runtime` (uptime, GPU
  utilisation, mapped `ports`) only while RUNNING, `disk` and `mounts.persistent.size` for the disks, 404 when gone. `GET /pods`
  is paginated (`pagination.nextCursor`) with no name filter. `POST /pods/{id}/action` `{"action": "stop"|"start"|
  "terminate"}`; `DELETE /pods/{id}` answers 204. `GET /billing/pods?bucketSize=hour` gives `records[].totalAmount` per hour
  (no billed seconds), disks of stopped pods included. `GET /pods/{id}/logs` streams server-sent events (`runpod logs <pod>`).
- Rate limits arrive as `RateLimit` headers and 429 with `Retry-After` (v2 quotas are per minute/hour/day window, no published
  numbers); the manager waits `Retry-After` when given, else backs off. Stop on an already stopped pod is not documented, so
  stop and delete check the state first and count only what GET shows afterwards. A pod in `ERROR` is stopped by the guard
  and listed by `check`; its disk is the creator's decision like any stopped one.
- Independent validation (thread "RunPod validation", 2026-10-22, report in the project files) added: the account bills with
  no pod through **network volumes** (`GET /network-volumes`, $0.07/GB/month), **global volumes** (`GET /global-volumes`) and
  **serverless endpoints** with min workers > 0 (`GET /serverless`); `check`, the watchdog and the 24 h ceiling now cover them,
  and the 24 h figure comes from the aggregate `GET /billing` (every resource), not from pods alone. `POST /pods` answering
  **402** means no balance: no other card is tried. The GraphQL `myself` balance is the only balance source and **GraphQL
  retires in early 2027** with no v2 balance endpoint (openapi.json, 2026-10-22): revisit by 2026-12; fallback = the creator's
  top-ups reconciled against `billing_total` deltas. At **$0 balance RunPod terminates pods without a network volume** and
  their data is gone: the creator should set RunPod's low-balance e-mail alert (the only native alert; v2 has no webhooks).
  Inside a pod only a RESTRICTED key (`tools/runpod/pod_api_key.txt`, scope pods:write) is injected for the boot self-stop;
  without it the guard's boot deadline does the stopping. The Bash hook also refuses `runpodctl create|start` and
  `PATCH /v2/pods/{id}` (a pod edit resets the container: everything outside /workspace is lost).
- The lost-money audit (thread "RunPod-ის დაკარგული თანხა", 2026-10-22): the $8 → $0.97 drop happened 2026-10-15..19, before
  D-56 ($2.31 TMR pods on 10-15, $5.34 pods on 10-16, $1.05 the stopped 60 GB preflight disk 10-17..19); $0.00 billed since
  2026-10-19 and the account is clean. Billing rows lag up to an hour (hour buckets).

## The Guardian: job record, watchdog, phone commands (master brief 2026-10-22, stage B)

Built 2026-10-22 after the creator's balance fell from ~$8 to $0.95 with "nothing paid running" (project chat, 09:13); every
part is tested against a fake RunPod (`tests/unit/test_cloud_guardian.py`, the brief's fifteen recovery scenarios) and none
of it spends money.

- **Job record** (`explainer_engine/cloud/jobs.py`): `jobs/cloud/<slug>/job-NNN_<date>/{state.json, events.jsonl,
  heartbeat.json}`. States QUEUED → PROVISIONING → STARTING → MODEL_LOADING → READY → RUNNING → CHECKPOINTING → UPLOADING →
  SUCCEEDED, with FAILED, RETRYING, STALLED, STOPPING, STOPPED, RECOVERY_REQUIRED; only the listed transitions are legal.
  `create` makes the record and the guard writes it on every look (`jobs.observe`: the pod's status and the conductor's
  status line become job states; a heartbeat means progress - the status line changed, the stage changed or the GPU is busy -
  never just "the API answered"). `jobs.stall` says when a state is quiet past its measured limit; the guard then marks
  STALLED and pushes, and stops the pod only when every recorded output is in the store (`safe_to_release`); with unstored
  outputs it marks RECOVERY_REQUIRED and leaves the pod to a person. A finished job with the same inputs is not run again.
- **Durable store** (`cloud/store.py`, from TMR): `store_job` pushes the record and the output folders with a sha256 sidecar
  and verifies size + hash before an output counts as stored. Backends: the HF dataset `vano1919/tmr-artifacts` or a folder
  (`EXPLAINER_STORE_LOCAL`; a mounted R2 bucket later). Damaged files (torn JSON, empty PNG, cut MP4) are never pushed.
- **Incident log** (`cloud/incidents.py` + `incidents.json`, 22 known incidents from TMR's prose log with fingerprint
  provider/resource/stage/error class, cause, fix in code, cost): the guard, the watchdog and `create` append what they saw to
  `tools/runpod/incidents.jsonl`; `doctor` names the known cause and fix and how often the fingerprint was seen.
- **Watchdog outside the session** (`cloud/watchdog.py`, `.github/workflows/watchdog.yml`): pure rules over what RunPod shows,
  no session file needed: a live pod past the lifetime in its name or without one is stopped; a pod in ERROR, a stopped disk, a
  stand-alone network volume and a serverless endpoint with min workers > 0 are reported with their $/day; at the 24 h ceiling
  every live pod is stopped; a balance under the floor is reported. GitHub Actions runs it every 30 minutes and "Run workflow"
  with `kill_all` is the creator's STOP ALL from GitHub Mobile (stops, never deletes). **Setup the creator does once**: add the
  repository secret `RUNPOD_API_KEY` (and `NTFY_TOPIC` for pushes) under Settings → Secrets and variables → Actions. A
  Cloudflare Worker (cron every 5 min) is the second runner once the account exists.
- **Phone commands** (`python -m explainer_engine.cloud status | logs <job|pod> | doctor [text] | budget | incidents [grep] |
  stop-all --yes`): what bills now, what changed since the last look, the last confirmed sign of life per job, ceilings against
  the last 24 h and the balance, known causes and fixes. No invented percentages. `check` (and the session hooks) now also list
  network volumes and idle serverless workers, the two ways an account bills with no pod at all.

## Image providers behind one interface and the model pilot (master brief 2026-10-22, stage D)

`explainer_engine/imagegen/providers/`: `base.ImageProvider` (prices, reference limits and model versions as class data;
`estimate` before any call; the run ledger reserves the money, `settle` records what the provider itself bills; one cache keyed by
provider + model + prompt + size + seed + reference bytes, so a paid picture is never bought twice; a lost answer is
`ChargeUncertain`, never retried or refunded; keys only from environment variables, never printed). Adapters: `bfl.py` (FLUX 3
Image Klein, `POST /v1/flux-3-image-klein`, header `x-key`, poll only the returned `polling_url`, Ready / Error / moderation
states, the signed picture URL lives 10 minutes), `fal.py` (queue API, `Authorization: Key`, `status_url` + `response_url` from
the answer, Seedream 4.5 text-to-image and edit, Qwen-Image-Edit-2511), `gemini_adapter.py` (the existing client). `paint plan`
prices bfl and fal rows next to Gemini's; `paint run` paints through the adapter with the same ledger. Caps: `config/spend_caps.json`
`bfl_usd` 3, `fal_usd` 9 (the creator's card, 2026-10-22; ceiling $15 with RunPod's 3).

`imagegen/pilot.py`: six shots x four takes per candidate, priced before anything is sent (`estimate`: $1.92 for Klein 1k +
Seedream 4.5 2K + Qwen-Edit 1344x768), `run` refused without the creator's approval of the plan hash on the ledger
(`Run.approve("pilot", ...)`), results.json per take (cost, seconds, seed, refusal or error), a collage per candidate for the
creator (OR-16). Not computed by code: SigLIP-2 / DINOv2 similarity (model download; the creator's 1-5 decides).
Not built: a Modal/Replicate adapter, the Illustrious pod leg (RunPod balance), the batch tier outside Gemini.

## Kit test (before any full kit)
1. Gemini, 1K: base traveller from the creator's reference 02 on flat green, then 8 poses and 4 expressions
   (13 pictures + about 30 % retries, about $1.20).
2. Key, measure identity drift (outline, scarf, satchel, face proportions) and edge quality; build one 10 s parallax
   test scene in code.
3. Z-Image: 3 world backgrounds against the same style reference (one pod session, under $0.50).
4. Creator judges; only then the full kit (about 40 pictures, about $3-4 at 1K).

## Kit test result (2026-10-16, model gemini-3.1-flash-image, 1K, list price $0.067 per picture)
Spend: 15 pictures, about $1.01 (estimate at list price; no retries were needed). Files: `assets/characters/traveller/test_v0/`
(keyed pictures, two world backgrounds, contact sheet, walk-test frames, generation ledger with every prompt).
- **Identity held** across 1 base + 8 poses + 4 expressions from one reference: face, cheeks, scarf, satchel, proportions
  and line style look the same on the contact sheet. This was judged by eye only; no numeric drift measure was made.
- **Keying works**: no green pixels left on the keyed edges (measured on 3 pictures); edges look clean on dark and light.
- **Defects found**: the scarf tail and the satchel differ per picture (the frontal expressions show the scarf hanging in
  front; the delighted picture has the satchel on the other side); a faint blue rim on shaded edges; one world
  background came with a painted paper border that must be cropped; mouth states for lip-sync are NOT tested yet (only
  four whole-face expressions).
- **Animation test** (8 s, 1080p30, built in code, 84 s to render on this sandbox, not the creator's PC): two backgrounds
  blended into one panorama, camera pan, two-frame walk cycle with bob, seam glow and particles, shadow, surprise pop,
  delighted finish. It reads as a living storybook scene; the walk is a two-pose swap, not smooth limb animation.
- **Not tested**: Z-Image backgrounds (no RunPod cap yet), so the style match between Gemini mascot and Z-Image worlds
  is still a hypothesis; mouth patches; a second world pair; consistency over many more poses.

## Cast bank result (2026-10-16): the analyst and the companion
Files: `assets/characters/crossworld_cast_v0/` (12 analyst poses and expressions, 8 companion poses, two 2K worlds, a contact
sheet, test frames, the generation ledger with all prompts).
- **Identity held** across 12 analyst and 8 companion pictures generated from one reference each, judged by eye: hat, monocle,
  neckerchief, satchel, proportions and line style repeat. Small variations: which hand holds the notebook, the monocle
  hanging in the startled pose. The companion is the easier design (no face, no limbs).
- **2K needs an explicit parameter**: asking for "2K" in the prompt text returned 1376x768; `imageConfig.imageSize: "2K"` returned
  2752x1536 (list price $0.101). Two 1K worlds ($0.13) were wasted.
- **Border defect persists**: the cold world still arrives with a painted paper edge on the top and left despite the prompt;
  crop 2-3 % of each edge in the asset step (a measured crop, to be built into the picture gate).
- **Test scene** (10 s, 2560x1440, 30 fps, code only, CPU in the cloud session: 152 s): analyst walks across the seam, startled
  pop, looks to the horizon, ends with a wry smile; the companion floats beside, changes eye state and opens its wings at the end.
  The walk is still a two-pose swap. Limbs do not move between poses; this is the ceiling of the pose-bank method.

## Sound result (2026-10-16): what Gemini can and cannot make
- Gemini has **no sound-effect model** (pricing page, 2026-10-16). Gemini TTS (`gemini-3.8-flash-tts`, $9 per 1M audio tokens
  until the end of 2026, 25 tokens per second) can make vocal reactions; Lyria (`lyria-3-clip-preview`, $0.04) makes 30 s
  music clips only (the request "about 4 seconds" returned 30.8 s, MP3 data in a .wav-named field).
- **Measured**: plain instructions ("Make only a short gasp") were read aloud by the voice (8 of 11 clips contained speech of the
  instruction, per a model listener). Bracketed tags worked: 15 of 24 tried sounds matched their intent, 5 were mislabelled by
  the listener (gasp heard as snicker, chuckle as gasp, sniff as groan, gulp as sigh), 4 failed on rate limits (HTTP 429 with 4 parallel
  calls). One uncapped call ran 458 s and cost about $0.10; every later call carries `maxOutputTokens`.
- **The model listener is weak** (it disagreed with itself between runs); only the creator's ears count (`review.human`).
- Result: 63 sounds in the library: 21 foley types x 1-3 takes (45 files, procedural, free), 15 vocal reactions, 3 music clips.
  Audio spend about $0.26 (estimate).

