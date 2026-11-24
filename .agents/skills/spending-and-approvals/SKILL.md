---
name: spending-and-approvals
description: Enforce zero-unapproved-spend rules, 64-character SHA-256 owner approvals, and transactional SQLite spend ledgers across paid providers.
---
# Spending and Approvals

## Non-Negotiable Rules
1. Never raise any cap in `config/spend_caps.json` without explicit owner instruction.
2. Never invent, default, or commit placeholder approvals in `config/owner_approvals.json`.
3. Every paid provider run must validate an approval via `explainer_engine.core.approvals.verify_approval` bound to a full 64-character SHA-256 operation manifest.
4. Reserve before launch and settle after launch via `explainer_engine.core.spend_ledger` (SQLite `BEGIN IMMEDIATE` + WAL, 80% stop rule, duplicate refusal, persistent `OVERRUN` service block).
5. In CI (`CI=true`), fail closed unless `EE_DURABLE_LEDGER_PATH` is explicitly configured.
