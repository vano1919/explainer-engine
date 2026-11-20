---
name: hyperstack-operations
description: Read Hyperstack safely for this channel - stock, account pricebook and cost estimates only, through the dry-run adapter - and know its billing states (SHUTOFF still bills the GPU, hibernate keeps disk and IP billing, delete is irreversible) so no legacy or proposed Hyperstack resource costs money unseen. Hyperstack is not used for the v4.3 route. Use when the owner asks about Hyperstack, when an audit finds a Hyperstack resource, or when comparing providers on paper.
---

# Hyperstack operations, read-only (layer L31)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Status: a researched candidate,
never wired into production; the v4.3 route runs its paid GPU work on Modal (D-131, D-132) and the project has a zero
Hyperstack budget (no line in `config/spend_caps.json`). Provider notes:
[HYPERSTACK_README](../../../docs/providers/HYPERSTACK_README.md); policy: `.claude/rules/cloud-platforms.md` section 5.

## What you may do

- Read stock (`GET /core/stocks`) and the account pricebook (`GET /pricebook`, the account `value`, not the public list)
  through `explainer_engine/cloud/providers/hyperstack.py` in dry-run, or the read-only documentation MCP.
- Estimate a job on paper: `python -m explainer_engine.cloud.providers --workload <preset>` (presets in
  `explainer_engine/cloud/providers/base.py`).
- List every existing VM, volume, snapshot and public IP during a cost audit, and report what bills.

## What you may not do without every gate and the owner's word

Create, start, hibernate, restore or delete anything; call the account control-plane MCP for anything but reading; use AI
Studio or Dedicated Inference for our work. A configured login is not permission.

## The billing states (why this page exists)

| State | Compute | Disk, IP | Note |
|---|---|---|---|
| ACTIVE | billed | billed | |
| SHUTOFF | **still billed at the full GPU rate** | billed | stopping from inside the VM (`shutdown`) lands here; it saves nothing |
| HIBERNATED | released | root data and a kept public IP still bill | restore can wait for the same card to be in stock |
| DELETED | none | none | local data gone; only on the owner's explicit word |

Volumes and snapshots bill on their own, attached or not. Object storage there is single-region and is never our vault: the
vault is HF `vano1919/tmr-artifacts` with hashes.

## Three products, never one

1. **GPU VM**: an ordinary machine for our own containers; the only Hyperstack product that could run our pipeline.
2. **AI Studio partner API**: token or image-patch priced, served by third parties; no custom adapters assumed, no data
   residency assumed.
3. **Dedicated inference**: one open LLM on vLLM, billed per GPU-hour while idle; not a video or image runtime.

Two different credentials: the core and AI Studio APIs take `api_key: <key>`; a dedicated endpoint takes its own bearer key.
Never log, print or commit either.

## If a create ever times out

Never create again. Reconcile first: list VMs by the unique name (`HyperstackAdapter.reconcile_existing`) and adopt a match;
a duplicate create double-bills.

## Before Hyperstack could carry real work

The full adapter contract of cloud-platforms section 7 (provider interface, lifecycle mapping, idempotent create, ledger
and reconciliation, an outside watchdog, verified upload, recovery tests, a live read-only smoke, a priced pilot), the OR-34
audit, a budget line by the owner, and a measured advantage over Modal for a named job. None exists today.

Companions: skill `cloud-cost-audit`, skill `cloud-provider-selection`.
