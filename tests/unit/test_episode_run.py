"""End-to-end episode runner, orchestrator state-machine, remote approval, hook, font, and stereo spotting tests."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from explainer_engine.audio import post_assembly_spotting as PAS
from explainer_engine.core import approvals
from explainer_engine.core.errors import ContractError
from explainer_engine.core.execution_gateway import EPISODE_RUNNER_DEPENDENCIES, ProductionStateMachine
from explainer_engine.episode import run as EP_RUN
from explainer_engine.maps import draw as MAP_DRAW
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator
from explainer_engine.training.pods.ltx import modal_layout_jobs as MLAY
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ
from explainer_engine.videolane.adapters import LocalRehearsalVideoAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_ANALYST_IDLE = REPO_ROOT / "assets/characters/crossworld_cast_v0/analyst/a_idle.png"
REAL_ANALYST_AMUSED = REPO_ROOT / "assets/characters/crossworld_cast_v0/analyst/a_amused.png"
REAL_WORLD_WARM = REPO_ROOT / "assets/characters/crossworld_cast_v0/worlds/warm_2k_raw.jpg"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write_wav(path: Path, arr: np.ndarray, *, sr: int = 48000, channels: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(arr.reshape(-1) * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _make_schema_valid_episode(tmp_path: Path) -> tuple[Path, Path]:
    ep_dir = tmp_path / "ep_full_01"
    for sub in ("story", "production/stages", "audio/stems", "editing", "planning", "renders/final", "qa"):
        (ep_dir / sub).mkdir(parents=True, exist_ok=True)

    man = json.loads((REPO_ROOT / "episodes/ep_toba/episode.json").read_text(encoding="utf-8"))
    man["episode_id"] = "ep_full_01"
    man["slug"] = "ep_full_01"
    man["title"] = "Episode Runner Remediation Test"
    (ep_dir / "episode.json").write_text(json.dumps(man, indent=2), encoding="utf-8")

    script = {
        "episode_id": "ep_full_01",
        "fps": 24,
        "shots": [
            {
                "shot_id": "S01_SH001",
                "segment_id": "S01",
                "route": "still_25d",
                "route_reason": "opening portrait",
                "target_duration_seconds": 2.0,
                "audio_line_ids": ["L001"],
            },
            {
                "shot_id": "S02_SH001",
                "segment_id": "S02",
                "route": "still_25d",
                "route_reason": "world establishing shot",
                "target_duration_seconds": 2.0,
                "audio_line_ids": ["L002"],
            },
        ],
        "audio_lines": [
            {"line_id": "L001", "speaker_type": "narrator", "text": "Opening line one."},
            {"line_id": "L002", "speaker_type": "narrator", "text": "Second scene line two."},
        ],
        "visual_bridges": [
            {
                "id": "br_01",
                "kind": "date_location_card",
                "text": "FRONTIER SECTOR",
                "subtext": "44 BCE",
                "timestamp_s": 0.3,
                "duration_s": 1.2,
            }
        ],
    }
    (ep_dir / "story/production_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
    (ep_dir / "audio/sound_plan.json").write_text(json.dumps({"episode_id": "ep_full_01", "shots": []}, indent=2), encoding="utf-8")

    # Real 48 kHz mono SFX library with CC0 manifest
    lib_dir = ep_dir / "sound_library"
    sr = 48000
    t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False, dtype=np.float32)
    whoosh = np.sin(2 * np.pi * (180 + 400 * t) * t) * np.hanning(len(t)) * 0.5
    sfx_p = _write_wav(lib_dir / "foley/whoosh_48k.wav", whoosh, sr=sr, channels=1)
    (lib_dir / "manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "id": "whoosh_48k",
                        "file": "foley/whoosh_48k.wav",
                        "tags": ["whoosh", "ambience_swell", "transition"],
                        "seconds": 0.25,
                        "sample_rate": sr,
                        "sha256": _sha(sfx_p),
                        "licence": {"status": "cc0", "type": "cc0", "commercial_use": True, "attribution_required": False},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return ep_dir, lib_dir


def test_episode_runner_blocks_legacy_reuse_and_enforces_state_freshness(tmp_path: Path) -> None:
    """Legacy stage record without ProductionStateMachine entry MUST NOT be considered fresh or reused."""
    ep_dir, lib_dir = _make_schema_valid_episode(tmp_path)
    ep = EP_RUN.Episode(ep_dir, size=(640, 360), fps=24, sound_library=lib_dir)

    # Create a legacy production/stages/script.json without recording it in ProductionStateMachine
    legacy_rec = {
        "schema": EP_RUN.RECORD_SCHEMA,
        "episode_id": "ep_full_01",
        "stage": "script",
        "gate": "G1-G3",
        "verdict": {"status": "PASS", "failed": [], "not_run": []},
        "rows": [],
        "outputs": {},
        "rehearsal": False,
        "fingerprint": EP_RUN.fingerprint(ep, "script"),
        "elapsed_s": 0.01,
        "at": "2026-11-24T00:00:00Z",
    }
    EP_RUN.record_path(ep.root, "script").write_text(json.dumps(legacy_rec), encoding="utf-8")

    # state() MUST report fresh=False because ProductionStateMachine has no verified SHA-256 record
    st_rows = {r["stage"]: r for r in EP_RUN.state(ep)}
    assert st_rows["script"]["fresh"] is False

    # run_to("script") MUST NOT reuse the unverified legacy record
    done = EP_RUN.run_to(ep, "script")
    assert not done[0].get("reused"), "Legacy record without ProductionStateMachine entry must never be reused"


def test_episode_assemble_stereo_48khz_bridges_spotting_and_stage_qa_identity_guards(tmp_path: Path) -> None:
    """Full stage_assemble (48kHz stereo + bridges + spotting) + stage_qa identity self-compare prevention."""
    ep_dir, lib_dir = _make_schema_valid_episode(tmp_path)

    # Render two real animated clips from project cast/world assets
    c1 = tmp_path / "c1.mp4"
    c2 = tmp_path / "c2.mp4"
    adapter = LocalRehearsalVideoAdapter()
    adapter.generate_clip({"start_image_path": str(REAL_ANALYST_IDLE), "ltx_frames": 48, "fps": 24}, c1)
    adapter.generate_clip({"start_image_path": str(REAL_WORLD_WARM), "ltx_frames": 48, "fps": 24}, c2)

    shot_records = [
        {"shot_id": "S01_SH001", "segment_id": "S01", "route": "still_25d", "start_sec": 0.0, "end_sec": 2.0, "duration_sec": 2.0, "total_frames": 48, "clip_path": str(c1), "source_start_keyframe": str(REAL_ANALYST_IDLE), "status": "PASS"},
        {"shot_id": "S02_SH001", "segment_id": "S02", "route": "still_25d", "start_sec": 2.0, "end_sec": 4.0, "duration_sec": 2.0, "total_frames": 48, "clip_path": str(c2), "source_start_keyframe": str(REAL_WORLD_WARM), "status": "PASS"},
    ]
    (ep_dir / "production/shot_records.json").write_text(json.dumps({"episode_id": "ep_full_01", "fps": 24, "size": [640, 360], "shots": shot_records}), encoding="utf-8")

    # 2-channel 48 kHz stereo base mix
    sr = 48000
    t = np.linspace(0, 4.0, sr * 4, endpoint=False, dtype=np.float32)
    bed_l = 0.04 * np.sin(2 * np.pi * 110 * t)
    bed_r = 0.035 * np.sin(2 * np.pi * 112 * t)
    _write_wav(ep_dir / "audio/stems/mix.wav", np.stack([bed_l, bed_r], axis=1), sr=sr, channels=2)
    (ep_dir / "audio/spotted_cues_config.json").write_text(json.dumps({"sample_fps": 4.0, "diff_threshold": 0.04}), encoding="utf-8")

    ep = EP_RUN.Episode(ep_dir, size=(640, 360), fps=24, sound_library=lib_dir)
    sm = ep.state_machine()
    for st in ("script", "sound_plan", "pictures", "voice", "clips", "sound"):
        rp = EP_RUN.record_path(ep.root, st)
        rp.write_text(json.dumps({"schema": EP_RUN.RECORD_SCHEMA, "episode_id": "ep_full_01", "stage": st, "gate": EP_RUN.GATES[st], "verdict": {"status": "PASS", "failed": [], "not_run": []}, "rows": [], "outputs": {}, "rehearsal": False, "fingerprint": EP_RUN.fingerprint(ep, st)}), encoding="utf-8")
        sm.record_stage_completion(st, status="PASS", output_paths=[rp], input_fingerprints=EP_RUN._stage_inputs(ep, st), config={"size": list(ep.size), "fps": ep.fps})

    asm = EP_RUN.run_stage(ep, "assemble")
    assert asm["verdict"]["status"] == "PASS"

    # Verify stereo 48 kHz preservation in spotted mix WAV
    spotted_wav = ep_dir / "audio/stems/mix_spotted.wav"
    assert spotted_wav.is_file()
    with wave.open(str(spotted_wav), "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getframerate() == 48000
        assert round(wf.getnframes() / wf.getframerate(), 2) == 4.0

    # Self-comparison identity check MUST FAIL (never PASS!)
    (ep_dir / "planning/identity_checks.json").write_text(
        json.dumps({"checks": [{"character_id": "analyst", "reference_image": str(REAL_ANALYST_IDLE), "candidate_image": str(REAL_ANALYST_IDLE), "mandatory": True}]}),
        encoding="utf-8",
    )
    qa_self = EP_RUN.run_stage(ep, "qa")
    id_row = next(r for r in qa_self["rows"] if r["gate"] == "identity_lock_analyst")
    assert id_row["status"] == "FAIL"
    assert "self-comparison" in id_row["detail"]


def test_remote_modal_approval_rejects_forged_and_replayed_proofs() -> None:
    """Forged unsigned dicts MUST be refused; valid HMAC proofs accepted once and rejected on replay."""
    forged = {
        "approval_id": "cmsg_forged_99999",
        "provider": "modal_modal1",
        "operation_mode": "modal-ltx-smoke",
        "manifest_sha256": "a" * 64,
        "max_usd": 5.0,
        "owner_evidence": "forged",
        "expires_at": "2099-01-01T00:00:00Z",
        "operation_id": "op_forged_0001",
    }
    for mod in (MLJ, MLAY):
        with pytest.raises(RuntimeError, match="unauthenticated/forged"):
            mod.verify_remote_approval_payload(forged, operation_mode="modal-ltx-smoke")

    # Valid HMAC-signed proof
    key = "super-secret-owner-signing-key-2026"
    signed = approvals.sign_approval_proof(forged, signing_key=key, operation_id="op_valid_unique_0001")
    res = MLJ.verify_remote_approval_payload(
        signed,
        operation_mode="modal-ltx-smoke",
        expected_manifest_sha256="a" * 64,
        estimated_max_usd=2.0,
        signing_key=key,
    )
    assert res["approval_id"] == "cmsg_forged_99999"

    # Replay of same operation_id MUST fail
    with pytest.raises(RuntimeError, match="replayed operation_id"):
        MLJ.verify_remote_approval_payload(signed, operation_mode="modal-ltx-smoke", signing_key=key)

    # Cost mismatch MUST fail
    signed_low = approvals.sign_approval_proof(forged, signing_key=key, operation_id="op_valid_unique_0002")
    with pytest.raises(RuntimeError, match="max_usd"):
        MLJ.verify_remote_approval_payload(signed_low, operation_mode="modal-ltx-smoke", estimated_max_usd=10.0, signing_key=key)


def test_orchestrator_mandatory_state_machine_dependencies_and_checkpoint_revalidation(tmp_path: Path) -> None:
    """SkillOrchestrator.run_plan ALWAYS uses ProductionStateMachine, reads `dependencies`, and re-runs corrupted checkpoints."""
    orch = SkillOrchestrator()
    # Confirm skill_registry.json uses `dependencies` and run_plan builds a real state machine even when state_path=None
    st0 = orch.registry["stages"][0]
    sid = st0["stage_id"]
    plan = orch.select_plan([sid], available_artifacts=list(st0.get("required_inputs") or []), allow_gaps=True)
    art = tmp_path / "stage_art.json"
    art.write_text('{"ok": true}', encoding="utf-8")
    calls = {"n": 0}

    def _exec(_payload: dict[str, Any]) -> dict[str, Any]:
        calls["n"] += 1
        return {"status": "PASS", "outputs": ["stage_out"], "output_path": str(art)}

    orch.register_executor(sid, _exec)
    cp = tmp_path / "checkpoint.json"
    res1 = orch.run_plan(plan, {sid: {}}, checkpoint_path=cp, allow_gaps=True)
    assert res1["status"] == "PASS" and calls["n"] == 1
    assert (tmp_path / "production_state.json").is_file()

    # Corrupt artifact on disk -> checkpoint MUST NOT blindly skip!
    art.write_text('{"ok": false}', encoding="utf-8")
    res2 = orch.run_plan(plan, {sid: {}}, checkpoint_path=cp, allow_gaps=True)
    assert res2["status"] == "PASS" and calls["n"] == 2


def test_spotting_path_traversal_and_strict_map_font_and_post_bash_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify sound library path containment, strict map font failure, and active PostToolUse/Stop gateway hooks."""
    # 1. Sound spotting path traversal refused
    outside = _write_wav(tmp_path / "outside.wav", np.zeros(4800, dtype=np.float32), sr=48000, channels=1)
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "manifest.json").write_text(
        json.dumps({"version": 1, "items": [{"id": "esc", "file": "../outside.wav", "sha256": _sha(outside), "licence": {"type": "cc0", "commercial_use": True}}]}),
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="escapes sound library root"):
        PAS.resolve_sound_asset(lib, asset_id="esc")

    # 2. Strict map font: missing MAP_FONT raises ContractError (no silent fallback)
    MAP_DRAW.font.cache_clear()
    monkeypatch.setattr(MAP_DRAW, "MAP_FONT", tmp_path / "missing_liberation_serif.ttf")
    with pytest.raises(ContractError, match="silent fallback"):
        MAP_DRAW.font(24, face="map")
    MAP_DRAW.font.cache_clear()

    # 3. Real .claude/settings.json PostToolUse Bash & Stop gateway_hook with project root pointer
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    post_cmds = [h["command"] for e in settings["hooks"]["PostToolUse"] if e.get("matcher") == "Bash" for h in e["hooks"]]
    gw_post = next(c for c in post_cmds if "gateway_hook post-bash" in c)
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    r_post = subprocess.run(
        ["bash", "-c", gw_post],
        input=json.dumps({"tool_input": {"command": "git status"}, "tool_response": {"exit_code": 0}}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r_post.returncode == 0

    # Stop hook via active_production_state.json pointer in temp project root
    proj = tmp_path / "proj"
    (proj / "jobs").mkdir(parents=True)
    st_p = proj / "production_state.json"
    sm = ProductionStateMachine(st_p, stage_dependencies=EPISODE_RUNNER_DEPENDENCIES)
    out_f = proj / "script.json"
    out_f.write_text('{"v": 1}', encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[out_f])
    (proj / "jobs/active_production_state.json").write_text(json.dumps({"state_path": str(st_p)}), encoding="utf-8")
    out_f.write_text('{"v": 2}', encoding="utf-8")  # corrupt on disk!

    env_stop = os.environ.copy()
    env_stop["CLAUDE_PROJECT_DIR"] = str(proj)
    env_stop["PYTHONPATH"] = str(REPO_ROOT)
    r_stop = subprocess.run(
        [os.sys.executable, "-m", "explainer_engine.governance.gateway_hook", "stop"],
        input=json.dumps({"required_stages": ["script"]}),
        capture_output=True,
        text=True,
        env=env_stop,
        check=False,
    )
    assert r_stop.returncode == 2 and "corrupted or modified" in r_stop.stderr
