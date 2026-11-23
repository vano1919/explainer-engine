---
name: modal-operations
description: Run and price the channel's only paid GPU work - the video route's LTX-2.5 distilled clips on Modal (D-132) - safely - the free credit first, the CH-01..CH-07 cheapest-combination rules, the paid offer file, one container per scene, nothing warm, the ledger reservation and the GO bound to the scene's hash, outputs to HF with hashes, the watchdog beside it, and the report after. Use before offering, planning, launching or auditing any Modal run, and when a Modal job fails, hangs or costs more than planned.
---

# Modal operations (layers L13 and L31, stage G7 video clips)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Rule homes: the CH rules and CR
rules in [CLOUD_RUNBOOK](../../../docs/CLOUD_RUNBOOK.md), the money and lifecycle policy in
`.claude/rules/cloud-platforms.md`, the caps only in `config/spend_caps.json`. RunPod is dropped for the v4.3 route (D-131);
Modal is the one paid GPU provider in use, on the creator's second account (the HF token lives in a Modal Secret, never pasted).

## What runs on Modal and what does not

| Runs on Modal | Never on Modal |
|---|---|
| LTX-2.5 distilled clips of the `video` route (D-132), one container per scene, through `explainer_engine/training/pods/ltx/scene_run.py` and the worker `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` | pictures (the free Gemini chat tool, D-131 turn packs) |
| weight staging into the Volume (CPU only, about $0) | the 2x upscale (free, local: `explainer_engine/finish/upscale.py`) |
| a measured bake-off only with its own recorded line (`modal_bakeoff`) | still_25d and map_action clips (local Python, D-131) |
| | the Wan worker (stays as code, refused by CH-06), warm endpoints, Shared Endpoints billed per token |

## Before any paid run: the order

1. **The creator's story is approved** and the scene file under `explainer_engine/training/pods/ltx/scenes/` is committed (D-132);
   its sha256 is the plan the creator says yes to.
2. **Free first, then the offer (CH-07, D-133).** Draft a `paid_offer/1` file and run
   `python -m explainer_engine.cloud.paid_offer fetch <offer>` (the free credit and today's cards, read-only),
   `... price <offer>` (every combination priced, the free/paid split) and `... check <offer>` (exit 0 prints the card text).
   Two priced combinations at least; the cheapest fitting one is chosen or its `not_chosen_why` is written. The month's free
   credit is spent before real money.
3. **The cheapest-combination rules hold (CH-01..CH-06, `explainer_engine/cloud/cheapest.py`):** one model load per container
   (`runner: inproc`), clips only at the native size (2K comes from the free upscale), one container per scene, nothing warm
   (scaledown at most 5 s, no minimum or buffer containers), LTX-2.5 distilled as the generator (D-132).
4. **The audit gate.** OR-34 asks a full-repo audit before a paid test; the owner's 2026-11-19 rule sets its model (Opus or
   Sonnet by complexity, never Haiku; narrow to the delta when he says so).
5. **The owner's word** in a message, naming the money. A plan thread's confirmation is not his word for spend (OR-24).
   Overnight budgets he sets (for example a night total) are ceilings for everything paid that night together.
6. **Reserve, then launch once:**
   `python -m explainer_engine.training.pods.ltx.scene_run job <scene.json> <spec.json>` (free: pins, sizes, the chain; D-132),
   `python -m explainer_engine.training.pods.ltx.scene_run reserve <scene.json>` (one reservation per scene and run id; a second (D-132)
   one is refused), then the plain Bash launch the hook reads, with `EE_MODAL_GO=<message id>:<scene sha[:12]>` and
   `EE_PAID_OFFER=<offer>`. Raw `modal deploy|serve|run|shell|launch` outside these entrypoints is refused by the session hooks.
7. **The watchdog thread** starts beside the run (OR-36, stage page `paid-run-watchdog`): read-only ALIVE/PROBLEM at the
   interval named.

## During the run

- Outputs leave the container as they arrive (OR-33): each clip is written, hashed and uploaded to
  HF `vano1919/tmr-artifacts` under the run id before the next one starts; a Modal Volume is a cache, never the only copy.
- The ledger (`explainer_engine/core/ledger.py`) stops new reservations at 80 % of the run, daily or episode cap; a cap is
  never raised to finish a run.
- A lost answer is reconciled (provider state, run id, ledger, output store) before anything is resubmitted; a duplicate
  launch can bill twice.
- The worker's own `container_gate` checks CH-01, CH-02 and CH-04 before any model loads; the timeout comes from the same
  number as the reservation, so the ledger and the container agree.

## Weights and Volumes

The weights are staged once into the named Volume (`ee-weights`) on CPU, never downloaded inside a GPU-billed cold start.
One writer per prefix; `commit()` after writes, `reload()` before reading another container's writes. Concurrent writers to
one file lose data (last write wins).

## Billing facts to price with (re-check on modal.com/pricing the same day)

GPU, CPU cores and memory bill separately per second while a container runs; image build, start, model load and the
scaledown window bill too. The Starter plan's monthly credit covers compute, not Shared Endpoint tokens. Price every offer
from today's page, write the check time, and keep gross cost (against the caps) and net out-of-pocket (after free credit)
apart. Measured basis: `explainer_engine/cloud/cheapest.json` (cost per generated second, model load share).

## Failure modes

| Symptom | Likely cause | Do |
|---|---|---|
| clips cost about five times the estimate | model reloaded per clip (CLI runner) | `runner: inproc` (CH-01); the hook refuses otherwise |
| a container keeps billing after the last clip | scaledown or a warm minimum | CH-04 values; stop through the app id `explainer_engine/cloud/modal_run.py` prints |
| `modal` cannot reach the API | the proxy | `pip install "modal[api-proxy-support]"`; read `/root/.ccr/README.md` |
| the worker refuses the spec | no open reservation or a second launch | reserve once; never edit the ledger by hand |
| a clip looks wrong | prompt or frame, not money | the repair ladder R1-R4 of skill `v-director-cinematic`; at most 2 generative retries (P-5) |

## The report after every run

Provider, app and function ids, GPU and VRAM, source commit and the worker's sha, model revisions; start, end, wall clock,
GPU-active and boot/load/upload seconds; estimated, reserved and billed cost apart; each clip's HF path and sha256; proof
that no container remains; the next decision and whether the owner's word is needed. Never say "saved" before the hash in
the vault matches.

## Code

`explainer_engine/cloud/providers/modal_provider.py` (dry-run capacity and per-second estimate),
`explainer_engine/cloud/modal_schedule.py` (hardware and container split, the cheapest passing one),
`explainer_engine/cloud/modal_run.py` (ladder order, app id, stop command), `explainer_engine/cloud/paid_offer.py` (CH-07),
`explainer_engine/cloud/cheapest.py` (CH-01..CH-06), `explainer_engine/cloud/store.py` (verified storage). Dry-run
comparison: `python -m explainer_engine.cloud.providers --workload workload_d_short_calibration`. Companions: skill
`cloud-cost-audit`, skill `cloud-provider-selection`.
