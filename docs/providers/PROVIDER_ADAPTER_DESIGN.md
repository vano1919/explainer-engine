# Provider-Neutral Cloud Adapter Design (`PROVIDER_ADAPTER_DESIGN.md`)

**Date:** 2026-11-07
**Target Package:** `explainer_engine/cloud/providers/`
**Design Principle:** Reuse `explainer_engine/cloud/jobs.py` (`Job`, `STATES`, `TRANSITIONS`), `explainer_engine/cloud/speeds.py`, `explainer_engine/cloud/batching.py` (`RP-01..10`), `explainer_engine/cloud/store.py`, and `explainer_engine/core/spend_caps.py` without duplicating job state machines or weakening any RunPod safety gate (`OR-21..36`, `CR-01..18`).

## 1. How Existing `explainer_engine/cloud/jobs.py` Is Reused

`explainer_engine/cloud/jobs.py` was already designed with a `provider` field (`Job.create(root, slug, kind=..., provider=..., inputs=..., caps=..., ledger=...)`) and a `resource` ID!
Rather than inventing a parallel job record, `explainer_engine/cloud/providers/` plugs directly into `jobs.Job`:
- Every adapter maps its provider-specific status payload into the **normalized 9-state lifecycle** (`NormalizedState`: `PENDING`, `PROVISIONING`, `STARTING`, `RUNNING`, `STOPPING`, `COMPLETED`, `FAILED`, `CANCELLED`, `UNKNOWN`) AND provides `to_guardian_state()` to map directly onto `jobs.STATES` (`QUEUED`, `PROVISIONING`, `STARTING`, `MODEL_LOADING`, `READY`, `RUNNING`, `CHECKPOINTING`, `UPLOADING`, `SUCCEEDED`, `FAILED`, `RETRYING`, `STALLED`, `STOPPING`, `STOPPED`, `RECOVERY_REQUIRED`).

## 2. State Mapping Table Across Providers (`[VERIFIED FACT]`)

| Normalized Adapter State (`NormalizedState`) | `explainer_engine/cloud/jobs.py` (`STATES`) | **RunPod** (`GET /v2/pods/{id}`) | **Hyperstack** (`GET /v1/core/virtual-machines/{id}`) | **Modal** (`FunctionCall` / Sandbox state) | Billing Implication & Watchdog Action |
|---|---|---|---|---|---|
| **`PENDING`** | `QUEUED` | Local pre-POST state | `CREATING` | `PENDING` / queued in Function input queue | Not billing GPU yet |
| **`PROVISIONING`** | `PROVISIONING` | `PROVISIONING` | `BUILD` | Container image pull / cold-start allocation | Allocating hardware (`$0` on Hyperstack/Modal until active/load) |
| **`STARTING`** | `STARTING` / `MODEL_LOADING` | `STARTING` (or `RUNNING` before port/conductor ready) | `STARTING` / `RESTORING` (or `ACTIVE` before SSH/beat ready) | Container init / `@modal.enter()` weight loading | Billing active on RunPod & Modal; transitional `$0` on Hyperstack until `ACTIVE` |
| **`RUNNING`** | `READY` / `RUNNING` / `CHECKPOINTING` / `UPLOADING` | `RUNNING` (with conductor `STATUS RUNNING`) | `ACTIVE` (with active heartbeat) | `RUNNING` (executing function body) | **Full GPU billing active**; guarded by `OR-36` watchdog & `OR-33` incremental store |
| **`STOPPING`** | `STOPPING` | Stopping in progress | `STOPPING` / `HIBERNATING` / `DELETING` | Container draining / scaledown window | Transitioning to non-GPU-billing state |
| **`COMPLETED`** | `SUCCEEDED` -> `STOPPED` | `EXITED` with beat `DONE rc=0` & `store.verify` OK | `HIBERNATED` or `DELETED` with beat `DONE rc=0` & `store.verify` OK | `SUCCESS` (exit 0) with verified HF outputs | RunPod `EXITED` still bills `$0.20/GB/mo` disk; Hyperstack `HIBERNATED` bills `$0.07/GB/mo` root disk; Hyperstack `DELETED` & Modal scale-to-zero bill **$0.00** |
| **`FAILED`** | `FAILED` / `RECOVERY_REQUIRED` | `ERROR` or `EXITED` with `rc != 0` | `ERROR` (or `SHUTOFF` — **CRITICAL ALERT: `SHUTOFF` still bills 100% GPU!**) | `FAILURE` / `TIMEOUT` / `PREEMPTED` | If `job.unstored_outputs()` is non-empty, moves to `RECOVERY_REQUIRED` (`jobs.py:249`) |
| **`CANCELLED`** | `STOPPED` | `TERMINATED` / `EXITED` on user/cap stop | `DELETED` / `HIBERNATED` on user/cap stop | `CANCELLED` (`FunctionCall.cancel()`) | Verified stopped |
| **`UNKNOWN`** | `STALLED` / `RECOVERY_REQUIRED` | Unrecognized status or HTTP 5xx/timeout | Unrecognized status or `SHUTOFF` billing anomaly | Unrecognized state | Never assume stopped; trigger watchdog alert |

## 3. Safety & Idempotency Contracts (`explainer_engine/cloud/providers/base.py`)

1. **Default-Deny Live Provisioning (`allow_live_provisioning = False`):**
   - Non-RunPod providers (`hyperstack`, `modal`) have **zero approved budget** in `config/spend_caps.json`.
   - `config/spend_caps.json` is **never modified** by this prototype. Instead, `PROPOSED_PROVIDER_CAPS` lives in `explainer_engine/cloud/providers/base.py` with `enabled: False` and `approved_by: None`. Any call to `submit_job(..., dry_run=False)` raises `ApprovalRequiredError` unless an explicit approval record (`OR-23` + `OR-24` + creator `OR-22` word) is passed and verified.
2. **Idempotency & Zero Blind POST Retries (`CR-12`, `T22/T24`):**
   - Before any `create` POST, the adapter writes a pending intent record (`idempotency_key`, `job_id`, `vm_name` with `-until-<epoch>`).
   - If a `POST` times out or returns HTTP `5xx` / `Unclear`, the adapter **never** re-sends `POST`. It queries `list_resources(name=vm_name)` to adopt any created instance or marks the job `RECOVERY_REQUIRED`.
3. **Hyperstack `SHUTOFF` Guard:**
   - If `HyperstackAdapter.normalize_status()` ever observes `status == "SHUTOFF"`, it flags `billing_active = True` and `billing_trap_warning = "SHUTOFF state on Hyperstack continues billing 100% of GPU rate; must HIBERNATE or DELETE"`, ensuring the watchdog immediately alerts and hibernates/deletes rather than treating `SHUTOFF` like RunPod `EXITED`.
