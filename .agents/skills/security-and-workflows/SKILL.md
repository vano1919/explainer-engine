---
name: security-and-workflows
description: Maintain least-privilege GitHub Actions workflows, safe Modal secret handling, and zero-injection shell steps.
---
# Security and Workflows

## Workflow Hardening Checklist
1. Never schedule unguarded cron jobs or fetch external untrusted scripts in GitHub Actions.
2. Always pass `workflow_dispatch` inputs through `env:` variables rather than interpolating `${{ inputs.* }}` inside `run:` blocks.
3. Gate paid cloud workflows with a protected GitHub Environment (`environment: modal-paid-approval`), default `check_only: true`, and require explicit `approval_id` + `EE_DURABLE_LEDGER_PATH`.
4. Never pass `HF_TOKEN=...` on the CLI or overwrite Modal secrets with `modal secret create --force`; use `modal.Secret.from_name(..., required_keys=["HF_TOKEN"])`.
5. Never expose API keys in URL query parameters (`?key=`); use request headers (`x-goog-api-key`) and redact secrets from exceptions and logs.
