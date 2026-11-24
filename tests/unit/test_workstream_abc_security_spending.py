"""Regression tests for Workstreams A (Security & Workflows), B (Approvals & Transactional Ledger), and C (Modal Runner Safety)."""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from explainer_engine.cloud import night_budget as NB
from explainer_engine.core import approvals as AP
from explainer_engine.core import spend_caps as SC
from explainer_engine.core import spend_ledger as SL

REPO_ROOT = Path(__file__).resolve().parents[2]


def _all_run_scripts(wf_data: dict) -> list[str]:
    scripts: list[str] = []
    for job in (wf_data.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                scripts.append(step["run"])
    return scripts


def test_drive_bridge_workflow_hardened_no_cron_no_external_fetch_no_injection():
    raw = (REPO_ROOT / ".github" / "workflows" / "orchestrator-drive-bridge.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(raw)
    triggers = wf.get("on") if "on" in wf else wf.get(True)
    assert isinstance(triggers, dict)
    assert "schedule" not in triggers
    assert "workflow_dispatch" in triggers
    assert wf.get("permissions", {}).get("contents") == "read"
    assert "contents: write" not in raw
    assert "curl " not in raw and "wget " not in raw and "drive.google.com" not in raw
    for script in _all_run_scripts(wf):
        assert "${{ github.event.inputs" not in script
        assert "${{ inputs." not in script


def test_modal_smoke_workflow_hardened_protected_env_and_safe_defaults():
    raw = (REPO_ROOT / ".github" / "workflows" / "modal-ltx-smoke-qa.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(raw)
    triggers = wf.get("on") if "on" in wf else wf.get(True)
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["check_only"]["default"] is True
    assert "approval_id" in inputs
    job = next(iter(wf["jobs"].values()))
    assert job.get("environment") == "modal-paid-approval"
    assert "EE_DURABLE_LEDGER_PATH" in raw
    assert "modal secret create" not in raw
    for script in _all_run_scripts(wf):
        assert "${{ github.event.inputs" not in script
        assert "${{ inputs." not in script
        assert "--force" not in script


def test_owner_approvals_file_starts_empty_no_invented_approvals():
    cfg = json.loads((REPO_ROOT / "config" / "owner_approvals.json").read_text(encoding="utf-8"))
    assert cfg.get("schema_version") == "owner_approvals/1"
    assert cfg.get("approvals") == {}


def test_approvals_verify_enforces_manifest_sha256_provider_budget_expiry_and_evidence(tmp_path: Path):
    manifest = {"plan": "battle", "gpu": "H100", "seconds": 2.0}
    digest = AP.canonical_manifest_sha256(manifest)
    assert len(digest) == 64

    approvals_file = tmp_path / "owner_approvals.json"
    approvals_file.write_text(
        json.dumps(
            {
                "schema_version": "owner_approvals/1",
                "approvals": {
                    "cmsg_valid_0001": {
                        "provider": "modal",
                        "operation_mode": "ltx_smoke",
                        "manifest_sha256": digest,
                        "max_usd": 1.5,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "owner_evidence": "Owner explicitly approved in session log 2026-11-24",
                    },
                    "cmsg_expired_01": {
                        "provider": "modal",
                        "operation_mode": "ltx_smoke",
                        "manifest_sha256": digest,
                        "max_usd": 1.5,
                        "expires_at": "2020-01-01T00:00:00Z",
                        "owner_evidence": "old",
                    },
                    "cmsg_noevid_001": {
                        "provider": "modal",
                        "operation_mode": "ltx_smoke",
                        "manifest_sha256": digest,
                        "max_usd": 1.5,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "owner_evidence": "",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    rec = AP.verify_approval(
        "cmsg_valid_0001",
        provider="modal",
        operation_mode="ltx_smoke",
        manifest_sha256=digest,
        requested_usd=1.0,
        registry_path=approvals_file,
    )
    assert rec["approval_id"] == "cmsg_valid_0001"
    assert rec["manifest_sha256"] == digest

    # Mismatched manifest fails
    with pytest.raises(AP.ApprovalError):
        AP.verify_approval(
            "cmsg_valid_0001",
            provider="modal",
            operation_mode="ltx_smoke",
            manifest_sha256=AP.canonical_manifest_sha256({"plan": "tampered"}),
            requested_usd=1.0,
            registry_path=approvals_file,
        )

    # Over budget fails
    with pytest.raises(AP.ApprovalError):
        AP.verify_approval(
            "cmsg_valid_0001",
            provider="modal",
            operation_mode="ltx_smoke",
            manifest_sha256=digest,
            requested_usd=1.6,
            registry_path=approvals_file,
        )

    # Expired fails
    with pytest.raises(AP.ApprovalError):
        AP.verify_approval(
            "cmsg_expired_01",
            provider="modal",
            operation_mode="ltx_smoke",
            manifest_sha256=digest,
            requested_usd=0.5,
            registry_path=approvals_file,
        )

    # Missing evidence fails
    with pytest.raises(AP.ApprovalError):
        AP.verify_approval(
            "cmsg_noevid_001",
            provider="modal",
            operation_mode="ltx_smoke",
            manifest_sha256=digest,
            requested_usd=0.5,
            registry_path=approvals_file,
        )


def test_spend_ledger_80pct_stop_duplicate_refusal_overrun_block_and_concurrency(tmp_path: Path):
    db = tmp_path / "ledger.sqlite3"

    # 80% stop rule on $1.50 cap -> stop ceiling is $1.20
    SL.reserve("modal", "item_1", 0.60, cap_usd=1.50, why="first", ledger_path=db)
    with pytest.raises(SL.DuplicateReservationError):
        SL.reserve("modal", "item_1", 0.10, cap_usd=1.50, why="dup", ledger_path=db)

    # Concurrent reservations racing for remaining $0.60 under 80% stop ($1.20)
    def _try_reserve(idx: int) -> bool:
        try:
            SL.reserve("modal", f"race_{idx}", 0.50, cap_usd=1.50, why="race", ledger_path=db)
            return True
        except SC.OverCeiling:
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_try_reserve, range(6)))
    assert results.count(True) == 1  # Exactly one 0.50 reservation fits (0.60 + 0.50 = 1.10 <= 1.20)

    # Settlement overrun past full cap triggers persistent OVERRUN block
    settled = SL.settle("modal", "item_1", actual_usd=1.80, ledger_path=db)
    assert settled["state"] == "OVERRUN"

    st = SL.service_status("modal", ledger_path=db)
    assert st["blocked"] is True

    # Subsequent reservation is refused because service is blocked
    with pytest.raises(SL.ServiceOverrunBlockedError):
        SL.reserve("modal", "item_after_overrun", 0.01, cap_usd=10.0, why="after", ledger_path=db)


def test_spend_ledger_ci_requires_durable_path(monkeypatch):
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("EE_DURABLE_LEDGER_PATH", raising=False)
    with pytest.raises(SL.LedgerPersistenceError):
        SL.default_ledger_path()


def test_spend_caps_strictest_modal_cap_and_unverified_envelopes():
    cfg = SC.load()
    assert cfg["orchestration_envelopes"]["enabled"] is False
    assert cfg["orchestration_envelopes"]["verified_owner_evidence"] is False
    assert SC.envelope_enabled(cfg) is False
    assert SC.strictest_modal_cap_usd(cfg) == 1.5


def test_modal_runner_no_default_card_ref_no_cli_secret_no_k_exclusions():
    script = (REPO_ROOT / "scripts" / "run_modal_ltx_smoke_and_qa.py").read_text(encoding="utf-8")
    assert "cmsg_owner_approved" not in script
    assert "modal secret create" not in script
    assert "HF_TOKEN=" not in script
    assert "not test_the_hand_over" not in script
    assert "not test_the_best_tail_search" not in script

    # --check-only succeeds with zero credentials and zero approvals
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_modal_ltx_smoke_and_qa.py"), "--check-only"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"


def test_modal_jobs_no_hardcoded_mnt_project_files_night_ledger():
    for rel in (
        "explainer_engine/training/pods/ltx/modal_ltx_jobs.py",
        "explainer_engine/training/pods/ltx/modal_layout_jobs.py",
    ):
        txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "/mnt/project-files/explainer-engine/final_plan_2026-11-19/modal_stage/NIGHT_LEDGER" not in txt


def test_night_budget_uses_transactional_ledger_and_enforces_cap(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    lp = tmp_path / "night.sqlite3"
    NB.reserve(lp, "smoke_1", 0.50, "unit test")
    NB.settle(lp, "smoke_1", 0.40)
    with pytest.raises(NB.NightCapExceeded):
        NB.reserve(lp, "smoke_huge", 5.00, "too big")


def test_blockers_ac_modal_workers_refuse_unregistered_go_cards():
    from explainer_engine.training.pods.ltx import modal_layout_jobs as MLAY
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ

    plan_sha = "a" * 64
    forged_env = {
        "EE_MODAL_GO": f"cmsg_forged_1234:{plan_sha[:12]}",
        "EE_MODAL_APPROVAL_MANIFEST_SHA256": "b" * 64,
    }
    with pytest.raises(SystemExit, match="owner approval verification failed"):
        MLJ.verify_worker_approval(forged_env, plan_sha=plan_sha, operation_mode="modal-ltx-smoke", requested_usd=0.5)
    with pytest.raises(SystemExit, match="owner approval verification failed"):
        MLAY.verify_worker_approval(forged_env, plan_sha=plan_sha, operation_mode="modal-layout-weights", requested_usd=0.32)


def test_blocker_b_workflow_check_only_step_has_zero_secrets():
    raw = (REPO_ROOT / ".github" / "workflows" / "modal-ltx-smoke-qa.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(raw)
    steps = next(iter(wf["jobs"].values()))["steps"]
    check_step = next(s for s in steps if "check-only" in s.get("name", "").lower())
    step_env = check_step.get("env") or {}
    for k, v in step_env.items():
        assert "secrets." not in str(v), f"Secret leaked to check_only step: {k}={v}"


def test_blocker_d_stage_cost_accounted_for():
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ

    assert MLJ.stage_hard_bill_usd() == 0.32
    script = (REPO_ROOT / "scripts" / "run_modal_ltx_smoke_and_qa.py").read_text(encoding="utf-8")
    assert "MLJ.stage_hard_bill_usd()" in script


def test_blocker_e_night_budget_ci_fail_closed_and_durable_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("EE_DURABLE_LEDGER_PATH", raising=False)
    with pytest.raises(SL.LedgerPersistenceError):
        NB.default_night_ledger_path()

    durable = tmp_path / "durable.sqlite3"
    monkeypatch.setenv("EE_DURABLE_LEDGER_PATH", str(durable))
    assert NB.default_night_ledger_path() == durable


def test_blocker_h_approvals_and_ledger_reject_nan_and_inf(tmp_path: Path):
    digest = "a" * 64
    for bad_val in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(AP.ApprovalError):
            AP.verify_approval(
                "cmsg_valid_0001",
                provider="modal_modal1",
                operation_mode="modal-ltx-smoke",
                manifest_sha256=digest,
                requested_usd=bad_val,
            )
        with pytest.raises(SC.OverCeiling):
            SL.reserve("modal", "nan_item", bad_val, cap_usd=1.5, ledger_path=tmp_path / "l.sqlite3")


def test_blocker_i_worker_night_settle_propagates_errors(tmp_path: Path, monkeypatch):
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ

    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(SystemExit, match="NIGHT LEDGER SETTLE FAILED"):
        MLJ.night_settle("nonexistent_item_xyz", 0.5, path=tmp_path / "empty.sqlite3")


def test_remote_worker_boundary_refuses_missing_or_expired_approval_proof():
    from explainer_engine.training.pods.ltx import modal_layout_jobs as MLAY
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ

    # Missing proof refused at remote boundary
    with pytest.raises(RuntimeError, match="missing owner approval_proof"):
        MLJ.verify_remote_approval_payload(None, operation_mode="modal-ltx-smoke")
    with pytest.raises(RuntimeError, match="missing owner approval_proof"):
        MLAY.verify_remote_approval_payload(None, operation_mode="modal-layout-weights")

    # Expired proof refused at remote boundary
    expired = {
        "approval_id": "cmsg_expired_0001",
        "provider": "modal_modal1",
        "operation_mode": "modal-ltx-smoke",
        "manifest_sha256": "a" * 64,
        "max_usd": 1.5,
        "owner_evidence": "old",
        "expires_at": "2020-01-01T00:00:00Z",
    }
    with pytest.raises(RuntimeError, match="expired"):
        MLJ.verify_remote_approval_payload(expired, operation_mode="modal-ltx-smoke")

    # Confirm both remote worker files invoke verify_remote_approval_payload inside remote functions
    for rel in ("explainer_engine/training/pods/ltx/modal_ltx_jobs.py", "explainer_engine/training/pods/ltx/modal_layout_jobs.py"):
        src = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert src.count("verify_remote_approval_payload(") >= 3, f"Remote boundary check missing in {rel}"


def test_spend_ledger_rejects_non_numeric_string_with_over_ceiling(tmp_path: Path):
    with pytest.raises(SC.OverCeiling):
        SL.reserve("modal", "bad_str", "1.0", cap_usd=1.5, ledger_path=tmp_path / "l.sqlite3")  # type: ignore[arg-type]
