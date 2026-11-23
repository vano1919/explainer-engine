"""Regression tests for P0/P1 audit findings: QA-001, RUNNER-001, ORCH-002/003/005, COST-001/002, SEC-006."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import pytest

from explainer_engine.core import spend_caps
from explainer_engine.episode import run as ep_run
from explainer_engine.llm import claude_api, deepseek_api
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator
from explainer_engine.qa.perceptual_qa import evaluate_clip_perceptual


def _make_broadband_mp4(path: Path, seconds: float = 1.5) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=duration={seconds}:size=320x180:rate=24",
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.15:duration={seconds}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, check=True)
    return path


def test_qa001_signal_only_never_returns_pass(tmp_path: Path):
    """QA-001: Passing technical signal checks without multimodal review must return NEEDS_REVIEW, never PASS."""
    vid = _make_broadband_mp4(tmp_path / "broadband.mp4")
    rep = evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa", use_gemini=False)
    assert rep["technical_status"] == "PASS"
    assert rep["perceptual_status"] == "NEEDS_REVIEW"
    assert rep["verdict"] == "NEEDS_REVIEW"


def test_orch002_003_005_no_fake_pass_and_hash_bound_checkpoint(tmp_path: Path):
    """ORCH-002/003/005: Checkpoint invalidates on payload change, REVIEW/NEEDS_REVIEW never collapses to PASS, empty outputs stay empty."""
    orch = SkillOrchestrator()
    calls: list[str] = []

    def ok_handler(sid: str):
        def _run(payload: dict) -> dict:
            calls.append(f"{sid}:{payload.get('rev', 1)}")
            return {"status": "PASS", "outputs": []}
        return _run

    def review_handler(payload: dict) -> dict:
        calls.append("S10:review")
        return {"status": "NEEDS_REVIEW", "outputs": []}

    for sid in ("S1_research", "S2_story_and_script", "S3_film_direction", "S5_gemini_images"):
        orch.register_executor(sid, ok_handler(sid))

    plan = orch.select_plan(
        requested_stages=["S5_gemini_images"],
        context={"needs_gemini_images": True},
        available_artifacts={"topic_brief", "episode_film_preset"},
        allow_gaps=True,
    )
    cp = tmp_path / "cp.json"
    ledger = tmp_path / "ledger.json"

    r1 = orch.run_plan(plan, {"S1_research": {"rev": 1}}, ledger_path=ledger, checkpoint_path=cp, allow_gaps=True)
    assert r1["status"] == "PASS"
    # ORCH-005: ledger must not fabricate expected_outputs when executor returned []
    entries = json.loads(ledger.read_text(encoding="utf-8"))["executions"]
    assert all(e["outputs"] == [] and e.get("run_id") for e in entries)

    # ORCH-003: changing payload must invalidate checkpoint and re-run
    r2 = orch.run_plan(plan, {"S1_research": {"rev": 2}}, ledger_path=ledger, checkpoint_path=cp, allow_gaps=True)
    assert r2["status"] == "PASS"
    assert "S1_research:2" in calls

    # ORCH-003: NEEDS_REVIEW must not collapse to PASS
    orch.register_executor("S5_gemini_images", review_handler)
    r3 = orch.run_plan(plan, {"S1_research": {"rev": 3}}, ledger_path=ledger, checkpoint_path=cp, allow_gaps=True)
    assert r3["status"] == "NEEDS_REVIEW"
    assert "S5_gemini_images" not in r3["completed_stages"]


def test_runner001_clips_fingerprint_tracks_video_records_and_pictures(tmp_path: Path):
    """RUNNER-001: Updating a non-clip-spoken video record or pictures.json must change the clips stage fingerprint."""
    ep_dir = tmp_path / "ep_test"
    (ep_dir / "story").mkdir(parents=True)
    (ep_dir / "production" / "video").mkdir(parents=True)
    (ep_dir / "episode.json").write_text(json.dumps({"episode_id": "ep_test", "size": [1280, 720], "fps": 24}), encoding="utf-8")
    script = {
        "episode_id": "ep_test",
        "shots": [{"shot_id": "s01", "route": "video", "target_duration_seconds": 3.0}],
    }
    (ep_dir / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
    (ep_dir / "production" / "pictures.json").write_text(json.dumps({"pictures": {"s01_start": "a.png"}}), encoding="utf-8")
    (ep_dir / "production" / "video" / "s01.json").write_text(json.dumps({"schema": "video_clip_record/1", "sha": "v1"}), encoding="utf-8")

    ep = ep_run.Episode(ep_dir)
    fp1 = ep_run.fingerprint(ep, "clips")

    # Mutate video record out of band
    (ep_dir / "production" / "video" / "s01.json").write_text(json.dumps({"schema": "video_clip_record/1", "sha": "v2"}), encoding="utf-8")
    fp2 = ep_run.fingerprint(ep, "clips")
    assert fp2 != fp1

    # Mutate pictures.json out of band
    (ep_dir / "production" / "pictures.json").write_text(json.dumps({"pictures": {"s01_start": "b.png"}}), encoding="utf-8")
    fp3 = ep_run.fingerprint(ep, "clips")
    assert fp3 != fp2


def test_cost001_002_overnight_enforces_independent_envelope(tmp_path: Path, monkeypatch, real_overnight):
    """COST-001/002: overnight_reserve/settle enforces independent orchestration envelopes with file locking."""
    caps_file = tmp_path / "spend_caps.json"
    caps_file.write_text(json.dumps({
        "overnight": {"overnight_2026_11_23": {"max_usd": 20.0, "lines": {}}},
        "orchestration_envelopes": {
            "combined_max_usd": 74.5,
            "services": {
                "modal_modal1": {"max_usd": 20.0},
                "deepseek": {"max_usd": 4.5},
                "claude_api": {"max_usd": 50.0},
            },
        },
    }), encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(caps_file))
    monkeypatch.setenv("EXPLAINER_OVERNIGHT_DIR", str(tmp_path / "overnight"))
    monkeypatch.setenv("EXPLAINER_ENVELOPE_LEDGER", str(tmp_path / "envelope_ledger.json"))

    spend_caps.overnight_reserve("deepseek", "t1", 3.0)
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.overnight_reserve("deepseek", "t2", 2.0)  # exceeds $4.50 independent envelope even though overnight is $20
    spend_caps.overnight_settle("deepseek", "t1", 1.25, 3.0)
    st = spend_caps.envelope_status()["deepseek"]
    assert st["spent_usd"] == pytest.approx(1.25)
    assert st["reserved_usd"] == pytest.approx(0.0)


def test_sec006_pack_and_secret_path_reject_absolute_and_escape(tmp_path: Path):
    """SEC-006: check_secret_path and deepseek_api.pack reject absolute paths and symlink escapes."""
    with pytest.raises(claude_api.SecretInPrompt):
        claude_api.check_secret_path("/etc/hosts")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    link = repo / "escape.txt"
    link.symlink_to(outside)
    with pytest.raises(claude_api.SecretInPrompt):
        deepseek_api.pack(["escape.txt"], repo, {})
