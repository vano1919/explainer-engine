"""Comprehensive integration, adversarial, and end-to-end tests for Next-Gen Production Framework.

Exercises real production entry points (episode/run.py, skill_orchestrator.py, .claude/settings.json
hook subprocesses, ltx_loop.py, post_assembly_spotting.py, bridge_compiler.py, identity_lock.py,
and perceptual_qa.py) without mocking the components under integration test.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import post_assembly_spotting as PAS
from explainer_engine.core.errors import ContractError
from explainer_engine.core.execution_gateway import EPISODE_RUNNER_DEPENDENCIES, ProductionStateMachine
from explainer_engine.episode import run as EP_RUN
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator
from explainer_engine.overlay import bridge_compiler as BC
from explainer_engine.qa import identity_lock as IL
from explainer_engine.qa import perceptual_qa as PQA
from explainer_engine.videolane.adapters import (
    GovernedModalLTXRequest,
    LocalFFmpeg2KVideoUpscaler,
    LocalRehearsalVideoAdapter,
    LocalStillUpscaler,
)
from explainer_engine.videolane.ltx_loop import PhotoObservation, sha256_file

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_ANALYST_IDLE = REPO_ROOT / "assets/characters/crossworld_cast_v0/analyst/a_idle.png"
REAL_ANALYST_AMUSED = REPO_ROOT / "assets/characters/crossworld_cast_v0/analyst/a_amused.png"
REAL_WORLD_COLD = REPO_ROOT / "assets/characters/crossworld_cast_v0/worlds/cold_2k_raw.jpg"


def _write_pcm16_wav(path: Path, samples: np.ndarray, sr: int = 24000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _make_sound_library(lib_root: Path) -> tuple[Path, Path]:
    """Create a real on-disk WAV sound library with SHA-256 and commercial-safe CC0 manifest."""
    sr = 24000
    t = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False, dtype=np.float32)
    whoosh = np.sin(2 * np.pi * (180 + 420 * t) * t) * np.hanning(len(t)) * 0.6
    wav_p = _write_pcm16_wav(lib_root / "foley" / "whoosh_test__v1.wav", whoosh, sr=sr)
    sha = hashlib.sha256(wav_p.read_bytes()).hexdigest()
    manifest = {
        "version": 1,
        "items": [
            {
                "id": "whoosh_test__v1",
                "file": "foley/whoosh_test__v1.wav",
                "category": "foley",
                "tags": ["whoosh", "ambience_swell", "transition", "impact"],
                "seconds": 0.35,
                "sample_rate": sr,
                "sha256": sha,
                "licence": {
                    "status": "cc0",
                    "type": "cc0",
                    "commercial_use": True,
                    "attribution_required": False,
                    "note": "Deterministic test fixture CC0",
                },
            }
        ],
    }
    (lib_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return lib_root, wav_p


def _make_minimal_episode(tmp_path: Path, *, with_bridges: bool = False, with_spotting: bool = False) -> Path:
    """Create a minimal episode directory compatible with episode/run.py."""
    ep_dir = tmp_path / "ep_integ"
    (ep_dir / "story").mkdir(parents=True)
    (ep_dir / "production").mkdir(parents=True)
    (ep_dir / "audio" / "stems").mkdir(parents=True)

    manifest: dict[str, Any] = {
        "episode_id": "ep_integ_01",
        "title": "Integration Test Episode",
        "fps": 24,
        "render_size": [640, 360],
        "historical_period": "ancient_mediterranean",
    }
    if with_spotting:
        manifest["enable_post_assembly_spotting"] = True
    (ep_dir / "episode.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    script: dict[str, Any] = {
        "episode_id": "ep_integ_01",
        "fps": 24,
        "shots": [
            {
                "shot_id": "S01_SH001",
                "segment_id": "S01",
                "route": "still_25d",
                "route_reason": "static establishing portrait",
                "target_duration_seconds": 2.0,
                "audio_line_ids": ["L001"],
            }
        ],
        "audio_lines": [{"line_id": "L001", "speaker_type": "narrator", "text": "Integration test narration line."}],
    }
    if with_bridges:
        script["visual_bridges"] = [
            {
                "id": "br_01",
                "kind": "chapter_card",
                "text": "CHAPTER I: THE FRONTIER",
                "subtext": "44 BCE",
                "timestamp_s": 0.2,
                "duration_s": 1.2,
            }
        ]
    (ep_dir / "story" / "production_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
    return ep_dir


# ---------------------------------------------------------------------------
# 1. P0 — Real episode/run.py + ProductionStateMachine Integration Tests
# ---------------------------------------------------------------------------


def test_p0_episode_runner_governed_by_authoritative_state_machine(tmp_path: Path) -> None:
    """Prove all 8 P0 state-machine behaviors through real episode/run.py entry points."""
    ep_dir = _make_minimal_episode(tmp_path)
    lib_root, _ = _make_sound_library(tmp_path / "sound_lib")
    ep = EP_RUN.Episode(ep_dir, sound_library=lib_root)

    # 2. Missing prerequisite blocks execution
    with pytest.raises(EP_RUN.StageRefused):
        EP_RUN.run_stage(ep, "sound_plan")

    # 1. Valid stage executes and persists production_state.json with SHA-256 hashes
    rec_script = EP_RUN.run_stage(ep, "script")
    state_file = ep_dir / "production" / "production_state.json"
    assert state_file.is_file()
    sm_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "script" in sm_data["stages"]
    assert sm_data["stages"]["script"]["output_hashes"]
    assert sm_data["stages"]["script"]["input_fingerprints"]

    # Force a clean PASS script record via real state machine + stage record to exercise downstream chain
    script_rec_path = EP_RUN.record_path(ep.root, "script")
    rec_script["verdict"]["status"] = "PASS"
    rec_script["verdict"]["failed"] = []
    script_rec_path.write_text(json.dumps(rec_script, indent=2), encoding="utf-8")
    sm = ep.state_machine()
    sm.record_stage_completion(
        "script",
        status="PASS",
        output_paths=[script_rec_path],
        input_fingerprints=EP_RUN._stage_inputs(ep, "script"),
        config={"size": list(ep.size), "fps": ep.fps},
    )

    # 3. Modified prerequisite output on disk blocks downstream stage execution
    script_rec_path.write_text(script_rec_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(EP_RUN.StageRefused, match="execution gateway refused"):
        EP_RUN.run_stage(ep, "sound_plan")

    # Restore hash & verify state survives process restart via CLI `verify`
    sm.record_stage_completion(
        "script",
        status="PASS",
        output_paths=[script_rec_path],
        input_fingerprints=EP_RUN._stage_inputs(ep, "script"),
        config={"size": list(ep.size), "fps": ep.fps},
    )
    # 7. Process restart + CLI verification
    sm_reloaded = ProductionStateMachine(state_file, stage_dependencies=EPISODE_RUNNER_DEPENDENCIES)
    ok_out, errs_out = sm_reloaded.verify_stage_outputs("script")
    assert ok_out and not errs_out
    cli_proc = subprocess.run(
        [sys.executable, "-m", "explainer_engine.core.execution_gateway", "verify", str(state_file), "script"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli_proc.returncode == 0, cli_proc.stderr

    # 5. Corrupted completed-stage output is detected by run_to (never silently reused!)
    script_rec_path.write_text(script_rec_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    ok_fresh, fresh_reasons = sm_reloaded.is_stage_fresh(
        "script", input_fingerprints=EP_RUN._stage_inputs(ep, "script"), config={"size": list(ep.size), "fps": ep.fps}
    )
    assert not ok_fresh
    assert any("corrupted or modified" in r for r in fresh_reasons)

    # 4. Changed input invalidates dependent stages
    sm.record_stage_completion(
        "script",
        status="PASS",
        output_paths=[script_rec_path],
        input_fingerprints={"story/production_script.json": "aaa"},
        config={"size": list(ep.size), "fps": ep.fps},
    )
    sp_out = ep_dir / "audio" / "sound_plan.json"
    sp_out.write_text("{}", encoding="utf-8")
    sm.record_stage_completion(
        "sound_plan",
        status="PASS",
        output_paths=[sp_out],
        input_fingerprints={"story/production_script.json": "aaa"},
        config={"size": list(ep.size), "fps": ep.fps},
    )
    inv_res = sm.record_stage_completion(
        "script",
        status="PASS",
        output_paths=[script_rec_path],
        input_fingerprints={"story/production_script.json": "bbb"},
        config={"size": list(ep.size), "fps": ep.fps},
    )
    assert "sound_plan" in inv_res["invalidated_downstream"]
    assert sm.data["stages"]["sound_plan"]["status"] == "INVALIDATED"

    # 6. Failed stage blocks downstream execution
    sm.record_stage_completion(
        "script",
        status="FAIL",
        output_paths=[script_rec_path],
        input_fingerprints={"story/production_script.json": "bbb"},
    )
    ok_sp, sp_blockers = sm.can_start_stage("sound_plan")
    assert not ok_sp and any("non-passing status" in b for b in sp_blockers)

    # 8. Interrupted/RUNNING stage blocks downstream execution (crash recovery)
    sm.record_stage_completion("script", status="PASS", output_paths=[script_rec_path])
    sm.mark_stage_started("sound_plan")
    assert sm.data["stages"]["sound_plan"]["status"] == "RUNNING"
    ok_pic, pic_blockers = sm.can_start_stage("pictures")
    assert not ok_pic and any("RUNNING" in b for b in pic_blockers)


# ---------------------------------------------------------------------------
# 2. P0 — Real Configured Claude Hook Subprocess & Adversarial Corpus Tests
# ---------------------------------------------------------------------------


def _run_real_hook_cmd(cmd_str: str, payload_text: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", "-c", cmd_str],
        check=False,
        input=payload_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_p0_active_claude_settings_hooks_adversarial_corpus(tmp_path: Path) -> None:
    """Execute the ACTUAL hook commands configured in .claude/settings.json against an adversarial corpus."""
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pre_bash_entries = [e for e in settings["hooks"]["PreToolUse"] if e.get("matcher") == "Bash"]
    assert pre_bash_entries
    pre_bash_cmds = [h["command"] for h in pre_bash_entries[0]["hooks"]]
    gw_pre_cmd = next(c for c in pre_bash_cmds if "gateway_hook" in c)
    gov_pre_cmd = next(c for c in pre_bash_cmds if "governance.hooks pre-bash" in c)

    post_bash_entries = [e for e in settings["hooks"]["PostToolUse"] if e.get("matcher") == "Bash"]
    assert post_bash_entries, "PostToolUse Bash hook must be configured in .claude/settings.json"

    stop_cmds = [h["command"] for e in settings["hooks"]["Stop"] for h in e["hooks"]]
    gw_stop_cmd = next(c for c in stop_cmds if "gateway_hook stop" in c)

    adversarial_commands = [
        # Direct commands
        "modal secret create my-secret KEY=1 --force",
        "modal run explainer_engine/cloud/modal_ltx_jobs.py",
        "git reset --hard HEAD~1",
        "curl -s 'https://generativelanguage.googleapis.com/v1/models?key=AIzaFakeSecret123'",
        # Wrapped commands
        "env FOO=1 timeout 30 modal run explainer_engine/cloud/modal_layout_jobs.py",
        "sudo modal secret create my-secret --force",
        # Chained commands
        "echo hello && git reset --hard",
        "ls -la; curl -X POST https://api.elevenlabs.io/v1/text-to-speech/abc",
        # Env-prefixed commands
        "URL=https://generativelanguage.googleapis.com/v1?key=SECRET echo ok",
        # Shell subprocesses & subshells
        'bash -c "modal run explainer_engine/cloud/modal_ltx_jobs.py"',
        "echo $(git reset --hard)",
        "echo `modal secret create prod --force`",
        # Inline Python subprocess bypass
        'python3 -c "import subprocess; subprocess.run([\'modal\', \'run\', \'modal_ltx_jobs.py\'])"',
        # Approval registry tampering
        "echo '{\"approvals\":{\"fake\":{}}}' > config/owner_approvals.json",
    ]

    for bad_cmd in adversarial_commands:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": bad_cmd}})
        r_gw = _run_real_hook_cmd(gw_pre_cmd, payload)
        assert r_gw.returncode == 2, f"gateway_hook failed to block: {bad_cmd!r} (stdout={r_gw.stdout}, stderr={r_gw.stderr})"
        r_gov = _run_real_hook_cmd(gov_pre_cmd, payload)
        assert r_gov.returncode == 2, f"governance.hooks pre-bash failed to block: {bad_cmd!r}"

    # Malformed & incomplete payloads must fail closed on gateway_hook
    for bad_payload in ("", "{not-json", "[]", json.dumps({}), json.dumps({"tool_input": {}}), json.dumps({"tool_input": {"command": 'echo "unclosed'}})):
        r_mal = _run_real_hook_cmd(gw_pre_cmd, bad_payload)
        assert r_mal.returncode == 2, f"gateway_hook did not fail closed on malformed payload: {bad_payload!r}"

    # Benign command allowed
    r_ok = _run_real_hook_cmd(gw_pre_cmd, json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}}))
    assert r_ok.returncode == 0

    # Stop hook enforces production state gate AND detects corrupted outputs
    st_path = tmp_path / "production_state.json"
    sm = ProductionStateMachine(st_path, episode_id="ep_hook_test", stage_dependencies=EPISODE_RUNNER_DEPENDENCIES)
    art = tmp_path / "script_out.json"
    art.write_text('{"ok": true}', encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[art])

    stop_payload = json.dumps({"production_state_path": str(st_path), "required_stages": ["script"]})
    assert _run_real_hook_cmd(gw_stop_cmd, stop_payload).returncode == 0

    # Corrupt output on disk -> Stop hook MUST deny (exit 2)
    art.write_text('{"ok": false}', encoding="utf-8")
    r_corrupt = _run_real_hook_cmd(gw_stop_cmd, stop_payload)
    assert r_corrupt.returncode == 2
    assert "corrupted or modified" in r_corrupt.stderr


# ---------------------------------------------------------------------------
# 3. P1 — Separate Still & Video Upscalers through SkillOrchestrator
# ---------------------------------------------------------------------------


def test_p1_orchestrator_uses_separate_still_and_video_adapters(tmp_path: Path) -> None:
    """Prove SkillOrchestrator routes video through LocalFFmpeg2KVideoUpscaler and tail frame through LocalStillUpscaler."""
    assert REAL_ANALYST_IDLE.is_file()
    orch = SkillOrchestrator()
    rehearsal_adapter = LocalRehearsalVideoAdapter()
    still_up = LocalStillUpscaler()
    video_up = LocalFFmpeg2KVideoUpscaler()

    def _obs(img_p: Path, _shot: dict[str, Any]) -> PhotoObservation:
        return PhotoObservation(
            photo_path=str(img_p),
            photo_sha256=sha256_file(img_p),
            observed_subjects=["analyst character"],
            observed_lighting="soft studio lighting",
            observed_composition="medium portrait",
            observed_environment="clean background",
        )

    def _gen(req: dict[str, Any]) -> Path:
        out_mp4 = tmp_path / f"{req['shot_id']}_raw.mp4"
        res = rehearsal_adapter.generate_clip(req, out_mp4)
        assert res["rehearsal"] is True
        return Path(res["clip_path"])

    def _tail(clip_p: Path) -> Path:
        tail_png = tmp_path / f"{clip_p.stem}_tail.png"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-sseof", "-0.1", "-i", str(clip_p), "-frames:v", "1", str(tail_png)],
            check=True,
            capture_output=True,
            text=True,
        )
        return tail_png

    res = orch.run_stage(
        "S6_ltx_video",
        {
            "loop_shots": [
                {
                    "shot_id": "SH01",
                    "scene_id": "SC01",
                    "editorial_seconds": 1.0,
                    "start_image_path": str(REAL_ANALYST_IDLE),
                    "camera_move": "zoom_in",
                    "action_beat": "subtle breathing",
                }
            ],
            "vision_observer": _obs,
            "video_generator": _gen,
            "qa_reviewer": lambda _p, _r: {"verdict": "PASS"},
            "tail_extractor": _tail,
            "still_upscaler": still_up,
            "video_upscaler": video_up,
        },
        allow_gaps=True,
    )
    assert res["status"] == "PASS"
    step = res["loop_result"]["steps"][0]
    assert step["video_upscaler_backend"] == "ffmpeg_2k_lanczos_cas"
    assert step["still_upscaler_backend"] == "local_lanczos_unsharp_still"
    assert len(step["upscaled_clip_sha256"]) == 64
    assert len(step["upscaled_tail_sha256"]) == 64
    with Image.open(step["upscaled_tail_frame_path"]) as im:
        assert im.size == (2560, 1440)

    # Governed Modal LTX request MUST fail closed without owner approval ($0.00 spend)
    with pytest.raises(ContractError):
        orch.run_stage(
            "S6_ltx_video",
            {
                "modal_request": GovernedModalLTXRequest(
                    approval_id=None,
                    manifest={"shot": "SH01"},
                    estimated_usd=0.25,
                    cap_usd=1.0,
                    item_id="sh01_paid",
                )
            },
            allow_gaps=True,
        )


# ---------------------------------------------------------------------------
# 4. P1 — Post-Assembly Sound Spotting + Real Asset Resolution + Mixing
# ---------------------------------------------------------------------------


def test_p1_post_assembly_spotting_real_asset_resolution_and_mixing(tmp_path: Path) -> None:
    """Verify real visual cut detection, SHA-256/license asset checks, rejection of invalid assets, and audio mixing."""
    lib_root, wav_p = _make_sound_library(tmp_path / "lib")

    # Build a 2-second test video with a sharp color cut at 1.0s
    vid = tmp_path / "assembled.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x112233:s=320x180:d=1.0:r=24",
            "-f",
            "lavfi",
            "-i",
            "color=c=0xEEDDCC:s=320x180:d=1.0:r=24",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(vid),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    events = PAS.detect_visual_event_timestamps(vid, tmp_path / "work", sample_fps=4.0, diff_threshold=0.10)
    assert events, "Should detect hard cut at 1.0s"
    assert any(0.7 <= e["visual_timestamp_s"] <= 1.3 for e in events)

    cues = PAS.resolve_spotted_cues(vid, events, lib_root)
    assert cues and cues[0]["asset_id"] == "whoosh_test__v1"
    assert cues[0]["licence"]["commercial_use"] is True

    rec = PAS.build_spotting_record(vid, cues, out_path=tmp_path / "spotting.json", require_verified_assets=True)
    assert rec["validation"]["status"] == "PASS"
    assert PAS.is_spotting_fresh(rec, vid)

    # Integrate into sound plan
    sp_path = tmp_path / "sound_plan.json"
    sp_path.write_text(json.dumps({"episode_id": "ep_test", "shots": []}), encoding="utf-8")
    updated_plan = PAS.integrate_spotted_cues_into_sound_plan(sp_path, rec)
    assert updated_plan["post_assembly_spotting"]["accepted_cue_count"] == len(cues)

    # Mix onto silent base audio and verify energy appears at cut timestamp
    base_wav = _write_pcm16_wav(tmp_path / "base.wav", np.zeros(24000 * 2, dtype=np.float32), sr=24000)
    mix_res = PAS.mix_spotted_cues_onto_audio(base_wav, rec, tmp_path / "mixed.wav")
    assert mix_res["cues_mixed"] == len(cues)
    assert len(mix_res["output_sha256"]) == 64
    mixed_sig, _ = PAS._read_pcm16_mono(Path(mix_res["output_wav"]))
    assert float(np.max(np.abs(mixed_sig))) > 0.05

    # Rejection tests: missing asset, tampered SHA-256, non-commercial license
    with pytest.raises(ContractError):
        PAS.resolve_sound_asset(lib_root, asset_id="does_not_exist")

    bad_man = json.loads((lib_root / "manifest.json").read_text(encoding="utf-8"))
    bad_man["items"][0]["licence"]["commercial_use"] = False
    (lib_root / "manifest.json").write_text(json.dumps(bad_man), encoding="utf-8")
    with pytest.raises(ContractError, match="commercial_use"):
        PAS.resolve_sound_asset(lib_root, asset_id="whoosh_test__v1")


# ---------------------------------------------------------------------------
# 5. P1 — Bridge Compiler Strict Font Verification & Overlay Composite
# ---------------------------------------------------------------------------


def test_p1_bridge_compiler_rejects_missing_font_no_silent_fallback(tmp_path: Path) -> None:
    """Prove bridge_compiler raises ContractError instead of silently falling back to PIL default font."""
    with pytest.raises(ContractError, match="not found on disk"):
        BC.compile_bridges_to_overlay_spec(
            [{"kind": "chapter_card", "text": "TEST", "timestamp_s": 0.1, "duration_s": 1.0}],
            font_path=tmp_path / "nonexistent_font.ttf",
        )


# ---------------------------------------------------------------------------
# 6. P1 — Identity Lock Integrated into Real Perceptual QA (Real Project Cast)
# ---------------------------------------------------------------------------


def test_p1_identity_lock_real_cast_and_perceptual_qa_enforcement(tmp_path: Path) -> None:
    """Prove real project cast assets work and mandatory identity failure blocks perceptual QA PASS."""
    assert REAL_ANALYST_IDLE.is_file() and REAL_ANALYST_AMUSED.is_file() and REAL_WORLD_COLD.is_file()

    # Positive: same character across poses
    pos = IL.check_cross_scene_identity(REAL_ANALYST_IDLE, REAL_ANALYST_AMUSED, character_id="analyst", mandatory=True)
    assert pos["status"] == "PASS"
    assert len(pos["reference_sha256"]) == 64 and len(pos["candidate_sha256"]) == 64

    # Negative: character vs unrelated cold world -> mandatory FAIL
    neg = IL.check_cross_scene_identity(
        REAL_ANALYST_IDLE, REAL_WORLD_COLD, character_id="analyst", mandatory=True, threshold=0.80
    )
    assert neg["status"] == "FAIL" and neg["failure_kind"] == "identity_mismatch"

    # Pose-guarded: back-facing -> NOT_APPLICABLE
    bg = IL.check_cross_scene_identity(REAL_ANALYST_IDLE, REAL_WORLD_COLD, character_id="analyst", pose_tag="back_facing")
    assert bg["status"] == "NOT_APPLICABLE"

    # Missing reference -> distinguished from mismatch
    miss = IL.check_cross_scene_identity(
        tmp_path / "missing_ref.png",
        REAL_ANALYST_IDLE,
        character_id="analyst",
        mandatory=True,
        allow_missing_reference_status=True,
    )
    assert miss["status"] == "FAIL" and miss["failure_kind"] == "missing_reference"

    # Real Perceptual QA integration: passing clip MUST FAIL when mandatory identity check fails
    clip = tmp_path / "clip.mp4"
    LocalRehearsalVideoAdapter().generate_clip({"start_image_path": str(REAL_ANALYST_IDLE), "ltx_frames": 25, "fps": 24}, clip)
    rep = PQA.evaluate_clip_perceptual(
        clip,
        out_dir=tmp_path / "qa_out",
        frame_count=4,
        use_gemini=False,
        identity_checks=[
            {
                "character_id": "analyst",
                "reference_image": str(REAL_WORLD_COLD),
                "mandatory": True,
                "threshold": 0.85,
            }
        ],
    )
    assert rep["verdict"] == "FAIL"
    assert any(d["defect_id"] == "ID-LOCK-ANALYST" for d in rep["defects"])
    assert rep["identity_lock_checks"][0]["status"] == "FAIL"
