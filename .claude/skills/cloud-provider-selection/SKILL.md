---
name: cloud-provider-selection
description: Choose where a paid GPU job of this channel runs and on which card - by measured seconds and total job cost, not hourly price - with the dry-run selector's hard filters (VRAM, RAM, disk, stock freshness, setup share, proposed caps), the v4.3 default of Modal for LTX-2.5 distilled clips (D-132), and the evidence a provider change would need. Use when a new GPU job type appears, when a card or price changes, and before any proposal to move work to another provider.
---

# Cloud provider selection (layer L31, planning before G7)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Decision home:
[PROVIDER_DECISION](../../../docs/providers/PROVIDER_DECISION.md); adapter design:
[PROVIDER_ADAPTER_DESIGN](../../../docs/providers/PROVIDER_ADAPTER_DESIGN.md); policy: `.claude/rules/cloud-platforms.md`
sections 5-7.

## The default today

| Job | Where | Why |
|---|---|---|
| video clips, LTX-2.5 distilled (D-132) | Modal, one container per scene | scale to zero, per-second billing, the ladder and ledger exist, measured cost per generated second (`explainer_engine/cloud/cheapest.json`) |
| pictures | the Gemini chat, free (D-131) | no GPU |
| 2x upscale, still_25d, maps, assembly | local CPU, free (D-131) | no GPU needed |
| anything on RunPod or Hyperstack | not used for v4.3 (D-131) | RunPod dropped by the owner; Hyperstack has no adapter that meets section 7 |

A provider is never changed because its list price is lower. A change needs: a measured job on both (seconds and total
cost), an adapter that meets cloud-platforms section 7 (idempotent create, reconciliation, ledger, watchdog, verified
upload, recovery tests), the OR-34 audit, and the owner's word.

## How to rank a job

1. **Describe the job by its units**: clips and their seconds at the native size, model loads, containers, the VRAM need
   measured or known with its reference (never guessed; Rule one, OR-22).
2. **Run the dry-run selector** (`explainer_engine/cloud/providers/selector.py`):
   `python -m explainer_engine.cloud.providers --workload <preset>` with a preset from
   `explainer_engine/cloud/providers/base.py` (for a short Modal test, `workload_d_short_calibration`). It creates nothing.
3. **Read the five filters it applies** before any ranking:
   - offer available and its stock fresh (stale stock is rejected);
   - VRAM, system RAM and disk at or above the job's floor (a 22B video transformer does not fit a 48 GB card without an
     offload plan that was measured; D-132);
   - the region allowed;
   - the total cost, including start, load, scaledown and egress, inside the job's cap and the proposed provider cap;
   - the setup share under RP-09's ceiling unless the job is a measurement (a fast card wasted on a slow start is refused).
4. **Rank survivors by total job cost**, then by risk (stock, recovery path). Hourly price is a tiebreak at most.
5. **Write the offer** for the chosen combination and one alternative (CH-07, skill `modal-operations`).

## What the selector cannot tell you

- whether a model, adapter or setting actually runs on that card: only a tiny approved pilot proves it;
- today's price: re-check the provider's page and write the check time;
- throughput on our pipeline: older clip timings of retired routes are not evidence for LTX-2.5 distilled (D-132).

## Traps

- **Per-hour thinking**: an H100 can be cheaper per job than an A100 or dearer; measure seconds.
- **Model reloads**: a runner that reloads per clip multiplies cost whatever the card (CH-01).
- **API generators** look cheap per second until sound, licence region and quality are counted; CH-06 records the
  comparison that kept the self-hosted generator.
- **Conflating products**: a token-priced endpoint, a dedicated inference endpoint and a GPU VM are different products
  with different bills (cloud-platforms section 5).

Companions: skill `cloud-cost-audit` (before and after the money), skill `hyperstack-operations` (legacy reading only).
