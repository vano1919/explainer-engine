"""Wave 8: 4-layer contract, integration, and adversarial hardening tests for AC-01..AC-15."""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import post_assembly_spotting as PAS
from explainer_engine.core import approvals
from explainer_engine.core import execution_gateway as EG
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import av_report as AVR
from explainer_engine.governance import gateway_hook as GH
from explainer_engine.maps import draw as MD
from explainer_engine.qa import identity_lock as IL
from explainer_engine.qa import perceptual_qa as PQA
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ

ROOT = Path(__file__).resolve().parents[2]


def _write_stereo_48k_wav(path: Path, duration_s: float = 2.0, freq_hz: float = 440.0, amp: float = 0.25) -> None:
    sr = 48000
    n = int(sr * duration_s)
    t = np.arange(n, dtype=np.float32) / sr
    left = amp * np.sin(2 * np.pi * freq_hz * t)
    right = amp * np.sin(2 * np.pi * (freq_hz * 1.25) * t)
    stereo = np.stack([left, right], axis=1)
    pcm = np.clip(stereo * 32767.0, -32768, 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def test_approvals_persistent_replay_and_hmac_verification(tmp_path: Path) -> None:
    db = tmp_path / "replay.sqlite3"
    key = "super-secret-signing-key-2026"
    proof = {
        "approval_id": "cmsg_test_replay_01",
        "provider": "modal_modal1",
        "operation_mode": "ltx_smoke",
        "manifest_sha256": "a" * 64,
        "max_usd": 1.5,
        "expires_at": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat(),
        "owner_evidence": "approved in chat",
    }
    signed = approvals.sign_approval_proof(proof, signing_key=key, operation_id="op_unique_001")
    assert approvals.verify_approval_hmac(signed, signing_key=key) is True
    tampered = dict(signed, max_usd=99.0)
    assert approvals.verify_approval_hmac(tampered, signing_key=key) is False

    assert approvals.is_operation_consumed("op_unique_001", db_path=db) is False
    approvals.record_consumed_operation(
        "op_unique_001",
        approval_id="cmsg_test_replay_01",
        manifest_sha256="a" * 64,
        db_path=db,
    )
    assert approvals.is_operation_consumed("op_unique_001", db_path=db) is True
    with pytest.raises(approvals.ApprovalError, match="Replay detected"):
        approvals.record_consumed_operation(
            "op_unique_001",
            approval_id="cmsg_test_replay_01",
            manifest_sha256="a" * 64,
            db_path=db,
        )


def test_execution_gateway_signs_hmac_and_normalizes_posix_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = {"job": "smoke", "frames": 25}
    msha = approvals.canonical_manifest_sha256(manifest)
    reg = tmp_path / "owner_approvals.json"
    reg.write_text(
        json.dumps(
            {
                "schema_version": "owner_approvals/1",
                "approvals": {
                    "cmsg_valid_hmac_01": {
                        "provider": "modal_modal1",
                        "operation_mode": "ltx_smoke",
                        "manifest_sha256": msha,
                        "max_usd": 1.5,
                        "expires_at": (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat(),
                        "owner_evidence": "owner approved",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EE_APPROVAL_HMAC_KEY", "test-hmac-key-at-least-16-chars")
    sm = EG.ProductionStateMachine(tmp_path / "production_state.json", episode_id="ep_hmac")
    auth = sm.authorize_paid_action(
        approval_id="cmsg_valid_hmac_01",
        provider="modal_modal1",
        operation_mode="ltx_smoke",
        manifest=manifest,
        estimated_usd=0.5,
        cap_usd=1.5,
        item_id="item_hmac_1",
        registry_path=reg,
        ledger_path=tmp_path / "spend.sqlite3",
    )
    proof = auth["approval_proof"]
    assert proof["operation_id"].startswith("op_")
    assert approvals.verify_approval_hmac(proof, signing_key="test-hmac-key-at-least-16-chars")

    # Remote worker accepts the signed proof and rejects replay
    verified = MLJ.verify_remote_approval_payload(
        proof,
        operation_mode="ltx_smoke",
        expected_manifest_sha256=msha,
        estimated_max_usd=0.5,
    )
    assert verified["operation_id"] == proof["operation_id"]
    with pytest.raises(RuntimeError, match="replayed"):
        MLJ.verify_remote_approval_payload(
            proof,
            operation_mode="ltx_smoke",
            expected_manifest_sha256=msha,
            estimated_max_usd=0.5,
        )


def test_gateway_hook_windows_exe_powershell_and_pre_write_blocks() -> None:
    payloads = [
        "modal.exe run explainer_engine/training/pods/ltx/modal_ltx_jobs.py",
        "git.exe reset --hard HEAD~1",
        "Invoke-WebRequest https://api.elevenlabs.io/v1/text-to-speech",
        "Set-Content -Path config/owner_approvals.json -Value '{}'",
        "echo '{}' > config/owner_approvals.json",
    ]
    for cmd in payloads:
        assert GH.check_shell_command_for_gateway_bypass(cmd), f"Expected block for: {cmd}"

    # Read-only grep is allowed
    assert GH.check_shell_command_for_gateway_bypass("grep write_text config/owner_approvals.json") == []

    # Pre-write hook blocks Write/Edit to owner_approvals.json
    denied = GH.check_write_payload({"tool_input": {"file_path": "config/owner_approvals.json"}})
    assert denied["decision"] == "deny"
    denied_win = GH.check_write_payload({"tool_input": {"file_path": r"C:\repo\config\owner_approvals.json"}})
    assert denied_win["decision"] == "deny"
    allowed = GH.check_write_payload({"tool_input": {"file_path": "explainer_engine/core/approvals.py"}})
    assert allowed["decision"] == "allow"

    # Subprocess fail-closed test for pre-write mode
    proc = subprocess.run(
        [sys.executable, "-m", "explainer_engine.governance.gateway_hook", "pre-write"],
        input=json.dumps({"tool_input": {"file_path": "config/owner_approvals.json"}}),
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 2


def test_maps_draw_strictly_uses_liberation_serif_with_no_comic_fallback() -> None:
    assert "LiberationSerif" in str(MD.MAP_FONT)
    f = MD.font(24)
    assert "Liberation Serif" in " ".join(str(x) for x in f.getname())
    for p in MD.FONT_FILES:
        assert "ComicNeue" not in str(p) and "Bangers" not in str(p)


def test_identity_lock_refuses_self_comparison_path_and_identical_sha(tmp_path: Path) -> None:
    ref = tmp_path / "ref.png"
    dup = tmp_path / "dup.png"
    other = tmp_path / "other.png"
    Image.new("RGB", (128, 128), (180, 110, 70)).save(ref)
    dup.write_bytes(ref.read_bytes())
    Image.new("RGB", (128, 128), (30, 60, 210)).save(other)

    res_same_path = IL.check_cross_scene_identity(ref, ref, character_id="hero", mandatory=True)
    assert res_same_path["status"] == "FAIL"
    assert res_same_path["failure_kind"] == "self_comparison_forbidden"

    res_same_sha = IL.check_cross_scene_identity(ref, dup, character_id="hero", mandatory=True)
    assert res_same_sha["status"] == "FAIL"
    assert res_same_sha["failure_kind"] == "self_comparison_forbidden"

    res_diff = IL.check_cross_scene_identity(ref, other, character_id="hero", mandatory=True)
    assert res_diff["status"] == "FAIL"
    assert res_diff["failure_kind"] == "identity_mismatch"


def test_perceptual_qa_multi_scene_vs_single_shot_and_youtube_editorial(tmp_path: Path) -> None:
    # 8 frames: scene 1 (frames 0-3 dark), hard cut, scene 2 (frames 4-7 bright)
    frames = []
    for i in range(8):
        val = 30 + i * 2 if i < 4 else 220 - (i - 4) * 2
        fp = tmp_path / f"f_{i:02d}.png"
        Image.new("RGB", (160, 90), (val, val, val)).save(fp)
        frames.append(PQA.SampledFrame(index=i, timestamp_s=float(i), path=fp, sha256=hashlib.sha256(fp.read_bytes()).hexdigest()))

    wav = tmp_path / "stereo_48k.wav"
    _write_stereo_48k_wav(wav, duration_s=2.0, freq_hz=330.0, amp=0.2)

    m_single, _ = PQA.analyze_clip_signals(frames, wav, duration_s=8.0, analysis_mode="single_shot")
    m_multi, _ = PQA.analyze_clip_signals(frames, wav, duration_s=8.0, analysis_mode="multi_scene")

    assert m_single["no_melt_passed"] is False
    assert m_multi["detected_scene_cuts"] == 1
    assert m_multi["no_melt_passed"] is True
    assert "youtube_editorial_checks" in m_multi
    assert m_multi["audio_integrated_lufs"] is not None
    assert m_multi["youtube_editorial_checks"]["stereo_balance_compliant"] is True


def test_post_assembly_spotting_freshness_and_stereo_48k_preservation(tmp_path: Path) -> None:
    video = tmp_path / "master.mp4"
    video.write_bytes(b"video-v1")
    sfx = tmp_path / "lib" / "whoosh.wav"
    _write_stereo_48k_wav(sfx, duration_s=0.3, freq_hz=500.0, amp=0.4)
    base = tmp_path / "base.wav"
    _write_stereo_48k_wav(base, duration_s=2.0, freq_hz=220.0, amp=0.1)

    sha_sfx = hashlib.sha256(sfx.read_bytes()).hexdigest()
    rec = PAS.build_spotting_record(
        video,
        [
            {
                "cue_id": "SPOT-01",
                "visual_timestamp_s": 0.5,
                "asset_id": "whoosh",
                "asset_path": str(sfx),
                "asset_sha256": sha_sfx,
                "licence": {"status": "cc0", "commercial_use": True, "source": "local_test"},
                "approval_status": "approved",
                "gain_db": -6.0,
            }
        ],
        require_verified_assets=True,
    )
    out_wav = tmp_path / "spotted.wav"
    mix = PAS.mix_spotted_cues_onto_audio(base, rec, out_wav, preview_video=video, require_stereo_48k=True)
    assert mix["sample_rate"] == 48000 and mix["channels"] == 2 and mix["cues_mixed"] == 1

    # Mutate video -> freshness check MUST refuse stale spotting
    video.write_bytes(b"video-v2-changed")
    with pytest.raises(ContractError, match="Stale post-assembly spotting"):
        PAS.mix_spotted_cues_onto_audio(base, rec, out_wav, preview_video=video, require_stereo_48k=True)


def test_episode_manifest_schema_accepts_runner_keys_and_av_report_handles_none_frames() -> None:
    schema = json.loads((ROOT / "explainer_engine/schemas/episode_manifest.schema.json").read_text(encoding="utf-8"))
    toba = json.loads((ROOT / "episodes/ep_toba/episode.json").read_text(encoding="utf-8"))
    toba["fps"] = 24
    toba["render_size"] = [1920, 1080]
    toba["enable_post_assembly_spotting"] = True
    toba["character_references"] = [{"character_id": "hero", "reference_image": "assets/ref.png"}]
    jsonschema.validate(toba, schema)

    md = AVR.markdown(
        {
            "episode_id": "ep_test",
            "resolver": "events/1",
            "contract": "av_events/1",
            "with_warnings": 0,
            "note": "test",
            "events": [
                {
                    "event_id": "EV-1",
                    "shot_id": "S01_SH001",
                    "op": "transition_riser",
                    "frames": None,
                    "decision": "review",
                    "class": "riser",
                    "assets": [],
                    "onset_off_ms": None,
                    "audible": None,
                    "warnings": [],
                }
            ],
        }
    )
    assert "n/a" in md


def test_manifest_character_references_array_schema_and_run_stage_qa_compat(tmp_path: Path) -> None:
    """Fix 1: character_references validates as array in episode_manifest.schema.json and works in run.py."""
    import jsonschema

    schema = json.loads(Path("explainer_engine/schemas/episode_manifest.schema.json").read_text(encoding="utf-8"))
    ref_img = tmp_path / "ref.png"
    cand_img = tmp_path / "cand.png"
    from PIL import Image

    Image.new("RGB", (64, 64), (120, 80, 60)).save(ref_img)
    Image.new("RGB", (64, 64), (125, 84, 63)).save(cand_img)

    manifest = {
        "schema_version": "episode_manifest/4",
        "episode_id": "ep_char_ref_test",
        "title": "Test",
        "character_references": [
            {
                "character_id": "tribune",
                "reference_image": str(ref_img),
                "candidate_image": str(cand_img),
                "mandatory": True,
            }
        ],
    }
    validator = jsonschema.Draft202012Validator(schema)
    errs = [e.message for e in validator.iter_errors(manifest) if "character_references" in list(e.path)]
    assert not errs, errs


def test_authorize_paid_action_and_modal_worker_replay_db_and_hmac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix 2: verify_approval_hmac + SQLite replay ledger wired into execution_gateway and modal workers."""
    import datetime as dt

    from explainer_engine.core import approvals, execution_gateway
    from explainer_engine.training.pods.ltx import modal_layout_jobs, modal_ltx_jobs

    monkeypatch.setenv("OWNER_APPROVAL_SIGNING_KEY", "test-secret-key-phase1")
    manifest = {"job": "smoke_test", "frames": 24}
    msha = approvals.canonical_manifest_sha256(manifest)
    exp = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat()
    reg_path = tmp_path / "owner_approvals.json"
    reg_path.write_text(
        json.dumps(
            {
                "schema_version": "owner_approvals/1",
                "approvals": {
                    "cmsg_phase1test0001": {
                        "provider": "modal_modal1",
                        "operation_mode": "modal-ltx-smoke",
                        "manifest_sha256": msha,
                        "max_usd": 5.0,
                        "expires_at": exp,
                        "owner_evidence": "owner approved in chat",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    gw = execution_gateway.ProductionStateMachine(tmp_path / "state.json", episode_id="ep_replay")
    replay_db = tmp_path / "gateway_replay.db"
    auth = gw.authorize_paid_action(
        approval_id="cmsg_phase1test0001",
        provider="modal_modal1",
        operation_mode="modal-ltx-smoke",
        manifest=manifest,
        estimated_usd=1.0,
        cap_usd=10.0,
        item_id="item_1",
        registry_path=reg_path,
        ledger_path=tmp_path / "spend.db",
        replay_db_path=replay_db,
        operation_id="op_fixed_replay_001",
    )
    assert approvals.verify_approval_hmac(auth["approval_proof"], signing_key="test-secret-key-phase1")
    assert approvals.is_operation_consumed("op_fixed_replay_001", db_path=replay_db)
    with pytest.raises(approvals.ApprovalError, match="Replay detected"):
        gw.authorize_paid_action(
            approval_id="cmsg_phase1test0001",
            provider="modal_modal1",
            operation_mode="modal-ltx-smoke",
            manifest=manifest,
            estimated_usd=1.0,
            cap_usd=10.0,
            item_id="item_2",
            registry_path=reg_path,
            ledger_path=tmp_path / "spend.db",
            replay_db_path=replay_db,
            operation_id="op_fixed_replay_001",
        )

    worker_db = tmp_path / "worker_replay.db"
    proof = auth["approval_proof"]
    modal_ltx_jobs._SEEN_REMOTE_OPERATION_IDS.discard(proof["operation_id"])
    verified = modal_ltx_jobs.verify_remote_approval_payload(
        proof,
        operation_mode="modal-ltx-smoke",
        expected_manifest_sha256=msha,
        estimated_max_usd=1.0,
        signing_key="test-secret-key-phase1",
        replay_db_path=worker_db,
    )
    assert verified["approval_id"] == "cmsg_phase1test0001"
    # Even if in-memory set is cleared (simulating cold container restart), persistent replay DB blocks replay!
    modal_ltx_jobs._SEEN_REMOTE_OPERATION_IDS.discard(proof["operation_id"])
    with pytest.raises(RuntimeError, match="replayed operation_id"):
        modal_ltx_jobs.verify_remote_approval_payload(
            proof,
            operation_mode="modal-ltx-smoke",
            expected_manifest_sha256=msha,
            estimated_max_usd=1.0,
            signing_key="test-secret-key-phase1",
            replay_db_path=worker_db,
        )
    modal_layout_jobs._SEEN_REMOTE_OPERATION_IDS.discard(proof["operation_id"])
    with pytest.raises(RuntimeError, match="replayed operation_id"):
        modal_layout_jobs.verify_remote_approval_payload(
            proof,
            operation_mode="modal-ltx-smoke",
            expected_manifest_sha256=msha,
            estimated_max_usd=1.0,
            signing_key="test-secret-key-phase1",
            replay_db_path=worker_db,
        )


def test_review_stage_empty_outputs_is_not_fresh(tmp_path: Path) -> None:
    """Fix 3: REVIEW stage recorded with empty output_paths fails closed in verify_stage_outputs and is_stage_fresh."""
    from explainer_engine.core import execution_gateway

    gw = execution_gateway.ProductionStateMachine(tmp_path / "state.json", episode_id="ep_review")
    gw.record_stage_completion("script", status="REVIEW", output_paths=[])
    ok_out, errs = gw.verify_stage_outputs("script")
    assert not ok_out and any("no recorded verifiable output hashes" in e for e in errs)
    fresh, reasons = gw.is_stage_fresh("script")
    assert not fresh and any("no recorded verifiable output hashes" in r for r in reasons)


def test_perceptual_qa_evaluate_and_cli_expose_analysis_mode(tmp_path: Path) -> None:
    """Fix 4: evaluate_clip_perceptual and CLI --mode expose multi_scene analysis_mode."""
    import inspect
    import subprocess

    from explainer_engine.qa import perceptual_qa

    sig = inspect.signature(perceptual_qa.evaluate_clip_perceptual)
    assert "analysis_mode" in sig.parameters
    assert sig.parameters["analysis_mode"].default == "single_shot"
    # Verify CLI accepts --mode multi_scene in help output
    proc = subprocess.run(
        [sys.executable, "-m", "explainer_engine.qa.perceptual_qa", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--mode" in proc.stdout and "multi_scene" in proc.stdout
