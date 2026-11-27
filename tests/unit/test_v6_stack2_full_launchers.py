"""Comprehensive unit + real CLI launcher integration tests for Stack-2 full stack."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from explainer_engine.cli.stack2_runner import run_stack2_pipeline
from explainer_engine.cloud.hybrid_api_clients import (
    run_elevenlabs_v4_tts,
    run_seedance25_video_escalation,
    run_sync3_lipsync_escalation,
)
from explainer_engine.cloud.modal_cinema_studio import EpisodeBudgetGuard
from explainer_engine.cloud.modal_comfy_deploy import (
    APP_NAME,
    DEFAULT_WEIGHT_MANIFEST,
)
from explainer_engine.studio.contact_sheet_slicer import (
    CANONICAL_3X3_ROLES,
    slice_contact_sheet_3x3,
)


def test_sqlite_wal_budget_guard_persists_across_restarts(tmp_path: Path) -> None:
    db = tmp_path / "spend.sqlite3"
    g1 = EpisodeBudgetGuard(episode_id="ep_wal", cap_usd=10.00, db_path=db)
    g1.reserve(job_id="j1", category="modal_gpu", provider="L40S", estimated_usd=4.50)
    g1.settle("j1", actual_usd=4.20)
    g1.reserve(job_id="j2", category="api_lipsync", provider="sync_3", estimated_usd=4.00)

    # Simulate fresh process restart reading the exact same SQLite WAL database
    g2 = EpisodeBudgetGuard(episode_id="ep_wal", cap_usd=10.00, db_path=db)
    assert g2.committed_usd == 8.20
    assert g2.remaining_usd == 1.80
    assert g2.summary()["checkpoint_reached"] is True

    with pytest.raises(RuntimeError, match="hard budget cap exceeded"):
        g2.reserve(job_id="j3", category="api_video", provider="seedance", estimated_usd=2.50)


def test_contact_sheet_3x3_slicer_outputs_nine_16bit_pngs(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    img = np.full((1080, 1920, 3), 120, dtype=np.uint8)
    # Add thin black grid dividers
    img[:, 638:642] = 0
    img[:, 1278:1282] = 0
    img[358:362, :] = 0
    img[718:722, :] = 0
    cv2.imwrite(str(sheet), img)

    man = slice_contact_sheet_3x3(sheet, tmp_path / "panels", prefix="ep1", save_16bit_png=True)
    assert man["panel_count"] == 9
    assert [p["role"] for p in man["panels"]] == list(CANONICAL_3X3_ROLES)
    first_p = Path(man["panels"][0]["path"])
    assert first_p.is_file()
    raw16 = cv2.imread(str(first_p), cv2.IMREAD_UNCHANGED)
    assert raw16 is not None and raw16.dtype == np.uint16
    assert raw16.shape[:2] == (720, 1280)

    # Low-res sheet MUST fail closed
    tiny = tmp_path / "tiny.png"
    cv2.imwrite(str(tiny), np.zeros((300, 600, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="cell width"):
        slice_contact_sheet_3x3(tiny, tmp_path / "bad_panels")


def test_hybrid_api_clients_dry_run_and_modal_deploy_manifest(tmp_path: Path) -> None:
    guard = EpisodeBudgetGuard(episode_id="api_test", cap_usd=10.00, db_path=tmp_path / "api.sqlite3")
    r_sync = run_sync3_lipsync_escalation(
        job_id="s1",
        video_url="https://example.invalid/v.mp4",
        audio_url="https://example.invalid/a.wav",
        duration_s=5.0,
        budget_guard=guard,
        dry_run=True,
    )
    assert r_sync["status"] == "DRY_RUN_OK"
    r_seed = run_seedance25_video_escalation(
        job_id="s2",
        prompt="Two survivors arguing on a stormy island",
        reference_urls=["https://example.invalid/r1.png"],
        duration_s=5.0,
        budget_guard=guard,
        dry_run=True,
    )
    assert r_seed["status"] == "DRY_RUN_OK"
    r_tts = run_elevenlabs_v4_tts(
        job_id="s3",
        text="We hold the ridge until dawn.",
        voice_id="voice_01",
        out_wav=tmp_path / "v.wav",
        budget_guard=guard,
        dry_run=True,
    )
    assert r_tts["status"] == "DRY_RUN_OK"
    assert guard.committed_usd == 0.0
    assert APP_NAME == "explainer-cinema-studio-v2"
    assert len(DEFAULT_WEIGHT_MANIFEST) >= 5


def test_stack2_cli_launcher_end_to_end_real_subprocess(tmp_path: Path) -> None:
    out_dir = tmp_path / "mvp_run"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "explainer_engine.cli.stack2_runner",
            "--episode-id",
            "island_cli_e2e",
            "--out-dir",
            str(out_dir),
            "--cap-usd",
            "10.0",
            "--dry-run",
            "--run-qa-smoke",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"CLI launcher failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
    summary = json.loads(proc.stdout)
    assert summary["status"] == "OK"
    assert summary["qa_smoke"] == "PASS"

    report = json.loads(Path(summary["report_path"]).read_text(encoding="utf-8"))
    assert report["contact_sheet_panels"] == 9
    assert report["comfy_graphs_generated"] >= 4
    assert Path(report["ledger_db"]).is_file()
    assert Path(report["otio_master_16x9"]).is_file()
    assert Path(report["otio_teaser_9x16"]).is_file()
    assert report["qa_smoke"]["padded_wav_duration_s"] >= 1.55

    # Also verify direct Python entrypoint
    direct = run_stack2_pipeline(episode_id="direct_e2e", out_dir=tmp_path / "direct", dry_run=True, run_qa_smoke=False)
    assert direct["contact_sheet_panels"] == 9
