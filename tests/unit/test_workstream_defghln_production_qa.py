"""Regression tests for Workstreams D, E, F, G, H, L, and N (Production Correctness & Multimodal QA)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from explainer_engine.core import camera_vocab as CV
from explainer_engine.core import fingerprints as FP
from explainer_engine.core.errors import ContractError
from explainer_engine.governance import layer_gate, owner_requirements
from explainer_engine.maps import maplibre_spec as MS
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator
from explainer_engine.qa import delivery_gate as DG
from explainer_engine.qa import perceptual_qa as PQA

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_local_mp4(path: Path, *, moving: bool = True, stereo_noise: bool = True, seconds: float = 2.0) -> Path:
    """Create a real local MP4 via FFmpeg with either moving or frozen frames and stereo broadband or pure-tone audio."""
    vsrc = f"testsrc2=size=320x180:rate=24:duration={seconds}" if moving else f"color=c=0x223344:size=320x180:rate=24:duration={seconds}"
    asrc = f"anoisesrc=color=pink:amplitude=0.15:duration={seconds},pan=stereo|c0=c0|c1=0.8*c0" if stereo_noise else f"sine=frequency=440:duration={seconds}"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", vsrc,
            "-f", "lavfi", "-i", asrc,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return path


def test_perceptual_qa_uses_x_goog_api_key_header_redacts_key_and_samples_8_frames(tmp_path: Path):
    vid = _make_local_mp4(tmp_path / "moving_stereo.mp4", moving=True, stereo_noise=True)
    captured: dict[str, object] = {}

    def fake_transport(url: str, body: dict, headers: dict) -> dict:
        captured["url"] = url
        captured["headers"] = dict(headers)
        parts = body["contents"][0]["parts"]
        captured["png_count"] = sum(1 for p in parts if p.get("inline_data", {}).get("mime_type") == "image/png")
        ans = {
            "visual_assessment": {
                "composition": "balanced",
                "natural_motion": True,
                "melt_or_warp_detected": False,
                "motion_notes": "clean motion",
                "artifacts_or_distortions": "none",
            },
            "audio_assessment": {
                "natural_audio": True,
                "audio_notes": "natural broadband stereo",
                "sync_and_continuity": "aligned",
            },
            "editorial_assessment": {"cinematic_quality": "pass", "notes": "good"},
            "defects": [],
        }
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(ans)}]}}]}

    rep = PQA.evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa", use_gemini=True, transport=fake_transport)
    assert "?key=" not in str(captured["url"])
    assert "x-goog-api-key" in captured["headers"]
    assert captured["png_count"] == 8
    assert rep["technical_status"] == "PASS"
    assert rep["perceptual_status"] == "PASS"
    assert rep["editorial_status"] == "PASS"
    assert rep["creator_signoff_status"] == "PENDING"
    assert rep["technical_metrics"]["audio_channels"] == 2
    assert "temporal_coverage" in rep["technical_metrics"]
    assert PQA._redact_secret("https://x?key=SECRET123456 fail SECRET123456", "SECRET123456") == "https://x?key=[REDACTED] fail [REDACTED]"


def test_perceptual_qa_safety_block_and_malformed_json_yield_needs_review(tmp_path: Path):
    vid = _make_local_mp4(tmp_path / "moving_stereo.mp4", moving=True, stereo_noise=True)

    def safety_block(_url: str, _body: dict, _headers: dict) -> dict:
        return {"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}

    rep1 = PQA.evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa1", use_gemini=True, transport=safety_block)
    assert rep1["verdict"] == "NEEDS_REVIEW"
    assert rep1["perceptual_status"] == "NEEDS_REVIEW"

    def bad_schema(_url: str, _body: dict, _headers: dict) -> dict:
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"visual_assessment": {"natural_motion": "yes"}})}]}}]}

    rep2 = PQA.evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa2", use_gemini=True, transport=bad_schema)
    assert rep2["verdict"] == "NEEDS_REVIEW"


def test_perceptual_qa_detects_frozen_video_and_synthetic_tone_deterministically(tmp_path: Path):
    vid = _make_local_mp4(tmp_path / "frozen_tone.mp4", moving=False, stereo_noise=False)
    rep = PQA.evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa_bad", use_gemini=False)
    assert rep["verdict"] == "FAIL"
    assert rep["technical_status"] == "FAIL"
    ids = {d["defect_id"] for d in rep["defects"]}
    assert "SIG-VID-FROZEN" in ids
    assert "SIG-AUD-SYNTHETIC-TONE" in ids


def test_skill_orchestrator_strict_contracts_and_halt_on_non_pass(tmp_path: Path):
    orch = SkillOrchestrator()
    # Every stage in skill_registry.json has an explicit execution_category
    for st in orch.registry["stages"]:
        assert st.get("execution_category") in {
            "planning_only", "human_gate", "episode_stage", "route_worker", "conditional_worker", "not_implemented"
        }

    # Image provenance verifies decodable image, dimensions, and SHA-256
    img_p = tmp_path / "ref.png"
    Image.new("RGB", (64, 48), (120, 80, 40)).save(img_p)
    prov_p = tmp_path / "prov.json"
    res = orch.run_stage("S5_gemini_images", {"images": [str(img_p)], "provenance_path": str(prov_p)}, allow_gaps=True)
    assert res["status"] == "PASS"
    prov = json.loads(prov_p.read_text(encoding="utf-8"))
    assert prov["verified_assets"][0]["width"] == 64
    assert prov["verified_assets"][0]["height"] == 48
    assert len(prov["verified_assets"][0]["sha256"]) == 64

    # Corrupt image rejected
    bad_img = tmp_path / "corrupt.png"
    bad_img.write_bytes(b"not-a-png")
    with pytest.raises(ContractError):
        orch.run_stage("S5_gemini_images", {"images": [str(bad_img)], "provenance_path": str(tmp_path / "p2.json")}, allow_gaps=True)

    # LTX video_clip_record/1 requires status == PASS (NEEDS_REVIEW is NOT accepted as PASS)
    clip_p = tmp_path / "clip.mp4"
    clip_p.write_bytes(b"fake-video-bytes")
    rec_nr = tmp_path / "rec_nr.json"
    rec_nr.write_text(json.dumps({"schema": "video_clip_record/1", "status": "NEEDS_REVIEW", "clip_path": str(clip_p)}), encoding="utf-8")
    res_nr = orch.run_stage("S6_ltx_video", {"shot": {"shot_id": "s1"}, "clip_record_path": str(rec_nr)})
    assert res_nr["status"] == "PLANNED"

    rec_pass = tmp_path / "rec_pass.json"
    rec_pass.write_text(
        json.dumps({
            "schema": "video_clip_record/1",
            "status": "PASS",
            "clip_path": str(clip_p),
            "sha256": hashlib.sha256(clip_p.read_bytes()).hexdigest(),
        }),
        encoding="utf-8",
    )
    res_pass = orch.run_stage("S6_ltx_video", {"shot": {"shot_id": "s1"}, "clip_record_path": str(rec_pass)})
    assert res_pass["status"] == "PASS"

    # run_plan halts downstream when an upstream stage returns non-PASS (e.g. NEEDS_REVIEW)
    executed: list[str] = []
    orch.register_executor("S1_research", lambda _p: (executed.append("S1"), {"status": "NEEDS_REVIEW", "outputs": []})[1])
    orch.register_executor("S2_story_and_script", lambda _p: (executed.append("S2"), {"status": "PASS", "outputs": []})[1])
    plan = orch.select_plan(["S2_story_and_script"], available_artifacts=["topic_brief"], allow_gaps=True)
    out = orch.run_plan(plan, {}, allow_gaps=True)
    assert out["status"] == "NEEDS_REVIEW"
    assert out["halted_stage"] == "S1_research"
    assert executed == ["S1"]


def test_code_digest_raises_on_missing_required_file_and_layer_gate_imports():
    assert layer_gate.SCHEMA == "layer_record/1"
    assert hasattr(owner_requirements, "load")
    assert len(FP.code_digest(FP.DIRECTOR_CODE_FILES)) == 16
    with pytest.raises(FileNotFoundError):
        FP.code_digest(["explainer_engine/does_not_exist_999.py"])


def test_camera_vocab_single_source_of_truth():
    assert DG.ALLOWED_CAMERA_MOVES is CV.ALLOWED_CAMERA_MOVES
    assert MS.ALLOWED_CAMERA_MOVES is CV.ALLOWED_CAMERA_MOVES
    assert CV.normalize_camera_move("pan_crop_2d") == "truck"
    assert CV.normalize_camera_move("dolly_in") == "zoom_in"
    with pytest.raises(ContractError):
        CV.validate_camera_move("orbit")


def test_no_deprecated_vsync_zero_in_explainer_engine():
    for py in (REPO_ROOT / "explainer_engine").rglob("*.py"):
        txt = py.read_text(encoding="utf-8", errors="ignore")
        assert '"-vsync", "0"' not in txt, f"Deprecated -vsync 0 found in {py}"


def test_cast_sheet_help_renders_without_percent_formatting_error():
    proc = subprocess.run(
        [sys.executable, "-m", "explainer_engine.training.cast.sheet", "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "80 %" in proc.stdout


def test_obsolete_stubs_and_duplicate_retired_skills_removed_and_cohesive_engine_aligned():
    from explainer_engine.orchestration import cohesive_film_engine as CFE

    assert not (REPO_ROOT / "explainer_engine" / "video").exists()
    assert not (REPO_ROOT / "explainer_engine" / "orchestration" / "gemini_workflow.py").exists()
    assert not (REPO_ROOT / ".claude" / "skills" / "shot-visuals").exists()
    assert not (REPO_ROOT / ".claude" / "skills" / "animation-principles").exists()
    assert (REPO_ROOT / ".claude" / "skills" / "_archive" / "shot-visuals" / "SKILL.md").is_file()

    src = (REPO_ROOT / "explainer_engine" / "orchestration" / "cohesive_film_engine.py").read_text(encoding="utf-8")
    assert "gemini-omni-1.2-flash" not in src
    issues = CFE.check_cohesive_film_invariants_and_bounds(
        {"shots": [{"shot_id": "S1", "camera_spec": {"camera_move": "orbit"}}], "segments": [], "audio_lines": []}
    )
    assert any(i["rule"] == "KP-V4-CAMERA" and "orbit" in i["detail"] for i in issues)


def test_blocker_f_perceptual_qa_custom_transport_never_receives_real_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyREAL_SECRET_KEY_SHOULD_NEVER_LEAK")
    vid = _make_local_mp4(tmp_path / "m.mp4", moving=True, stereo_noise=True)
    seen_headers: dict[str, str] = {}

    def spy_transport(_url: str, _body: dict, headers: dict) -> dict:
        seen_headers.update(headers)
        return {"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}

    PQA.evaluate_clip_perceptual(vid, out_dir=tmp_path / "qa_spy", use_gemini=True, transport=spy_transport)
    assert seen_headers.get("x-goog-api-key") == "MOCK_TEST_KEY"
    assert "REAL_SECRET" not in seen_headers.get("x-goog-api-key", "")


def test_blocker_g_ltx_video_pass_refuses_missing_clip_path_and_missing_or_bad_sha256(tmp_path: Path):
    orch = SkillOrchestrator()
    clip_p = tmp_path / "clip.mp4"
    clip_p.write_bytes(b"real-video-bytes")

    # Missing clip_path
    rec_no_clip = tmp_path / "no_clip.json"
    rec_no_clip.write_text(json.dumps({"schema": "video_clip_record/1", "status": "PASS", "sha256": "a" * 64}), encoding="utf-8")
    with pytest.raises(ContractError, match="clip_path"):
        orch.run_stage("S6_ltx_video", {"shot": {"shot_id": "s1"}, "clip_record_path": str(rec_no_clip)})

    # Missing sha256
    rec_no_sha = tmp_path / "no_sha.json"
    rec_no_sha.write_text(json.dumps({"schema": "video_clip_record/1", "status": "PASS", "clip_path": str(clip_p)}), encoding="utf-8")
    with pytest.raises(ContractError, match="sha256"):
        orch.run_stage("S6_ltx_video", {"shot": {"shot_id": "s1"}, "clip_record_path": str(rec_no_sha)})

    # Mismatched sha256
    rec_bad_sha = tmp_path / "bad_sha.json"
    rec_bad_sha.write_text(json.dumps({"schema": "video_clip_record/1", "status": "PASS", "clip_path": str(clip_p), "sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ContractError, match="SHA-256 mismatch"):
        orch.run_stage("S6_ltx_video", {"shot": {"shot_id": "s1"}, "clip_record_path": str(rec_bad_sha)})
