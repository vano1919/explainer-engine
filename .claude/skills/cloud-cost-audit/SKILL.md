---
name: cloud-cost-audit
description: Audit the money of a paid cloud run for this channel before it is offered and after it ends - the estimate against today's prices and the caps in config/spend_caps.json, the free credit first, hidden idle charges (warm containers, stopped disks, Volumes), the ledger against the provider's bill, every output hashed in the HF vault before anything is released, and the night or episode total across runs. Use before proposing any paid run, right after a run ends or aborts, and when a bill does not match the ledger.
---

# Cloud cost audit (layer L31, stages G7 and post-run)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Policy home:
`.claude/rules/cloud-platforms.md` sections 3, 4 and 8; rule homes: CH-01..CH-07 and CR rules in
[CLOUD_RUNBOOK](../../../docs/CLOUD_RUNBOOK.md); cost model in [CLOUD_COST_MODEL](../../../docs/providers/CLOUD_COST_MODEL.md).
For the v4.3 route the only paid GPU work is Modal (D-131, D-132); RunPod and Hyperstack are audited only if a legacy
resource still exists.

## Why this audit exists

A cheap hourly price says nothing about a job's cost: model loads per clip, a warm scaledown, a stopped disk, a duplicate
launch after a lost answer and an output that was never stored are where our money went before. The audit turns each of
those into a yes/no check with a number from code, not from memory.

## Before: the pre-offer audit (free)

1. **The cap.** Read the provider's line in `config/spend_caps.json`; no line means a zero budget. Never add, raise or reuse
   another provider's line; a change there is the owner's word only (hooks refuse the edit otherwise). A night or episode
   total the owner set (a message, saved in project memory) is a ceiling across all runs together.
2. **The free credit.** The month's remaining Modal credit (billing summary, or the ledgers' month when the API is out of
   reach) is counted first; the offer shows the free and the paid share (CH-07).
3. **The estimate by component**: GPU, CPU cores and memory per second, build, start and model load, the clips' seconds,
   scaledown, retries at worst case, storage and egress. Basis: `explainer_engine/cloud/cheapest.json` for measured seconds;
   an unmeasured number is labelled estimate.
4. **Combinations.** At least two, priced from today's page with the check time; the cheapest fitting one chosen
   (`python -m explainer_engine.cloud.paid_offer price <offer>` then `check`).
5. **Idle traps closed**: scaledown at most 5 s, no minimum or buffer containers (CH-04); Volumes used as cache only;
   nothing left running "for convenience".
6. **The 80 % line.** The ledger (`explainer_engine/core/ledger.py`) reserves before launch and refuses past 80 % of a cap;
   the audit states where the run's worst case lands against it.

## After: the post-run audit

1. **Outputs first.** Every output recorded on the job (`explainer_engine/cloud/jobs.py`, `Job.record_output`) passes size
   and SHA-256 through `verify_and_mark_stored` (`explainer_engine/cloud/providers/base.py`, `explainer_engine/cloud/store.py`)
   and exists at its HF path in `vano1919/tmr-artifacts`. A failed or cancelled job with unstored outputs moves to
   `RECOVERY_REQUIRED`: nothing is stopped, emptied or deleted before they are salvaged.
2. **Nothing billable remains**: no running container or app for Modal (the stop command from
   `explainer_engine/cloud/modal_run.py`); for any legacy pod, `python -m explainer_engine.cloud.runpod check` shows none.
3. **Ledger against bill.** Estimated, reserved and billed (or settled from measured seconds) side by side; a gap over a few
   cents gets a cause line. The incident log (`explainer_engine/cloud/incidents.py`) gets a fingerprint when a failure cost
   money, so the fix is found the next time.
4. **Totals.** The run's cost added to the night's and episode's totals; at 80 % of either, stop starting new work and tell
   the owner.
5. **The report** (cloud-platforms section 8): ids, GPU, hashes of the worker and the model revisions, seconds by phase, the
   three costs apart, each output's HF path and hash, the final provider state.

## Red flags that stop an offer

- a cost from an hourly price with no seconds behind it;
- a cap read from anywhere but `config/spend_caps.json`;
- an output path on a Volume or a container disk only;
- a retry planned before the first call's state is known;
- a provider "RUNNING" or HTTP 200 taken as success without stage progress and stored outputs.

## Legacy providers (only when a resource still exists)

Hyperstack: SHUTOFF keeps billing the GPU; only hibernate or delete stops it, and delete is the owner's word (skill
`hyperstack-operations`). RunPod: a stopped pod's disk and a network volume bill; delete only on the owner's word.

## Code and dry runs

`python -m explainer_engine.cloud.providers --workload workload_d_short_calibration` prints each adapter's `CostBreakdown`
(compute, CPU and RAM, disk and IP, egress, idle storage, retry worst case, setup share) without creating anything.
`PROPOSED_PROVIDER_CAPS` in `explainer_engine/cloud/providers/base.py` is a proposal, never a budget. Companions: skill
`modal-operations`, skill `cloud-provider-selection`.
