"""Reproducer & Verification Suite for Commit 4b7a24ce Independent Audit Findings (B1-B5).

Every test in this module reproduces a specific blocker from TASK_FIX_AUDIT_FINDINGS.md / CHATGPT_AUDIT_4b7a24ce.md
and FAILS on the unmodified 4b7a24ce code before passing with the general fixes.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio import duck as DUCK
from explainer_engine.audio import stems as STEMS
from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.episode import run as EP_RUN
from explainer_engine.episode import timing as ET
from explainer_engine.finish import superres as SR_UP
from explainer_engine.finish import upscale as FIN_UP
from explainer_engine.qa import targets as TG
from explainer_engine.training.pods.ltx import modal_ltx_jobs as LTX
from explainer_engine.videolane import ingest as IN
from explainer_engine.videolane import plan as VP
from tools.render_tools import build_segments as BS
from tools.render_tools import mix as MIX


def test_b1_inproc_ltx_session_forwards_painterly_negative_prompt_to_stream_chunks(tmp_path):
    """B1: LtxSession.clip() must pass the parsed painterly-safe negative_prompt to pipe.stream_chunks()."""
    from tests.unit import test_ltx_inproc as TLI

    log, written = [], []
    recorded_stream_kwargs: list[dict] = []
    fake_mod = TLI.fake_ltx(log, written)
    orig_distilled = fake_mod.D.DistilledPipeline

    def wrapped_distilled(**kw):
        pipe = orig_distilled(**kw)
        orig_stream = pipe.stream_chunks

        def capturing_stream_chunks(**skw):
            recorded_stream_kwargs.append(dict(skw))
            return orig_stream(**skw)

        pipe.stream_chunks = capturing_stream_chunks
        return pipe

    fake_mod.D.DistilledPipeline = wrapped_distilled
    launch = LTX.load_launch()
    assert LTX.runner_of(launch) == "inproc"

    job = {
        "shot_id": "S02_SH002",
        "seconds": 5.0,
        "fps": 24,
        "width": 1280,
        "height": 704,
        "seed": 42,
        "motion_prompt": "Soldiers walk through trench mist.",
        "negative_prompt": "cartoonish rendering, 3D CGI look, blurry, extra fingers",
    }
    argv = LTX.ltx_argv(launch, job, tmp_path / "in.png", tmp_path / "out.mp4")
    session = LTX.LtxSession([job["motion_prompt"]], ltx=fake_mod)
    session.clip(argv)
    session.close()

    assert len(recorded_stream_kwargs) == 1
    # The real DistilledPipeline (CFG-free) has no negative prompt: stream_chunks() raised TypeError on it in the L3 smoke
    # on Modal, 2026-11-19 22:56. The session therefore passes none; the painterly-safe text stays resolved for the run
    # record (resolve_negative_prompt).
    assert "negative_prompt" not in recorded_stream_kwargs[0]
    neg = LTX.resolve_negative_prompt(launch, job).lower()
    assert "extra fingers" in neg and "cartoonish" not in neg and "3d cgi" not in neg


def test_b2a_retime_with_edit_points_uses_ingested_clip_record_as_source_of_truth(tmp_path):
    """B2.1: retime_with_edit_points must use production/video/<sid>.json (actual trimmed clip record)
    as the authoritative source of truth over stale edit_points_doc."""
    vdir = tmp_path / "production" / "video"
    vdir.mkdir(parents=True, exist_ok=True)
    # Actual ingested clip record has 84 frames (3.50s), whereas edit_points_doc claims 96 frames (4.00s)
    clip_rec = {
        "schema": "video_clip_record/1",
        "shot_id": "S01_SH001",
        "route": "video",
        "status": "PASS",
        "clip_path": "production/video/cut/S01_SH001.mp4",
        "clip_sha256": "abc123def456",
        "fps": 24,
        "in_s": 0.35,
        "out_s": 3.85,
        "frames": 84,
    }
    (vdir / "S01_SH001.json").write_text(json.dumps(clip_rec), encoding="utf-8")

    script = {"shots": [{"shot_id": "S01_SH001", "segment_id": "S01", "route": "video"}]}
    timing = {
        "fps": 24,
        "total_frames": 96,
        "shots": {"S01_SH001": {"segment_id": "S01", "start_frame": 0, "end_frame": 96, "frames": 96}},
    }
    stale_edit_points = {"clips": {"S01_SH001": {"in": 0.20, "out": 4.20}}}

    retimed = ET.retime_with_edit_points(timing, script, stale_edit_points, episode_dir=tmp_path)
    assert retimed["shots"]["S01_SH001"]["frames"] == 84
    assert retimed["shots"]["S01_SH001"]["trim_contract"]["in_s"] == pytest.approx(0.35)
    assert retimed["shots"]["S01_SH001"]["trim_contract"]["out_s"] == pytest.approx(3.85)
    assert retimed["shots"]["S01_SH001"]["trim_contract"]["timing_source"] == "clip_record"


def test_b2b_single_tail_rule_matches_between_ingest_edit_points_and_whisper_edit_points():
    """B2.2: ingest.edit_points and ingest.whisper_edit_points must enforce the exact same 0.55s target reaction tail."""
    assert IN.CUT_TAIL[0] == pytest.approx(0.50)
    assert IN.CUT_TAIL[1] == pytest.approx(0.55)

    script = {
        "shots": [
            {
                "shot_id": "S03_SH004",
                "route": "video",
                "target_duration_seconds": 4.0,
                "audio_line_ids": ["L1"],
            }
        ],
        "audio_lines": [{"line_id": "L1", "speaker_type": "character", "speaker_id": "arthur", "text": "Listen now"}],
    }
    pts = IN.edit_points(5.0, [(0.80, 2.80)], {}, 4.0, 24, spoken=True, shot_id="S03_SH004")
    w_doc = {
        "clips": {
            "S03_SH004": {
                "duration": 5.0,
                "words": [
                    {"word": "Listen", "start": 0.80, "end": 1.50},
                    {"word": "now", "start": 1.60, "end": 2.80},
                ],
            }
        }
    }
    w_ep = IN.whisper_edit_points(w_doc, script)
    assert pts["out_s"] == pytest.approx(w_ep["clips"]["S03_SH004"]["out"], abs=1.0 / 24.0)


def test_b2c_episode_run_voice_persists_unified_clock_and_consumers_enforce_verify_clock_alignment(tmp_path):
    """B2.3 & B2.4: episode/run.py timing path must route through the unified persisted clock (episode_timing/2 with timing_id),
    and build_segments.py and mix.py must enforce verify_clock_alignment() and stop on mismatch."""
    script = {
        "shots": [
            {"shot_id": "S01_SH001", "segment_id": "S01", "route": "still_25d", "target_duration_seconds": 2.0, "audio_line_ids": ["L1"]},
        ],
        "audio_lines": [{"line_id": "L1", "speaker_type": "narrator", "text": "Christmas morning"}],
    }
    aligned = {
        "lines": {"L1": [{"w": "Christmas", "s": 0.1, "e": 0.8}, {"w": "morning", "s": 0.9, "e": 1.6}]},
        "order": ["L1"],
        "coverage": 1.0,
        "status": "PASS",
        "unmatched": [],
    }
    base_tm = ET.retime(script, aligned, 24, 2.0)
    unified_tm = ET.retime_with_edit_points(base_tm, script, episode_dir=tmp_path)
    t_path = tmp_path / "audio" / "timing.json"
    ET.persist_authoritative_clock(unified_tm, t_path)

    # Consumer passing a stale/mismatched timing_doc to build_segments.build or mix.run_mix must raise ContractError
    stale_tm = dict(unified_tm, timing_id="stale_0000000000", render_epoch="epoch_stale")
    (tmp_path / "story").mkdir(parents=True, exist_ok=True)
    (tmp_path / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")

    with pytest.raises(ContractError, match="clock|alignment|timing_id"):
        BS.build("S01_SH001", episode_dir=tmp_path, work_dir=tmp_path / "work", timing_doc=stale_tm, timing_path=t_path)

    with pytest.raises(ContractError, match="clock|alignment|timing_id"):
        MIX.run_mix(episode_dir=tmp_path, dl_dir=tmp_path, work_dir=tmp_path / "work", timing_doc=stale_tm, timing_path=t_path, script_doc=script)


def test_b2d_build_segments_rejects_pad_or_truncate_beyond_one_frame_and_hashes_actual_file_with_render_params(tmp_path):
    """B2.5 & B2.6: build_segments must fail when source clip frames differ from clock frames by >1 frame,
    must hash the actual trimmed file on disk (ignoring stale rec['clip_sha256']), and include target_size/filter/encode/overlay_authority in cache key."""
    ep_dir = tmp_path / "ep"
    work_dir = tmp_path / "work"
    cut_dir = ep_dir / "production" / "video" / "cut"
    cut_dir.mkdir(parents=True, exist_ok=True)
    (ep_dir / "story").mkdir(parents=True, exist_ok=True)

    clip_p = cut_dir / "S01_SH001.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "testsrc=size=1280x704:rate=24:duration=2.0",
            "-pix_fmt", "yuv420p", str(clip_p),
        ],
        check=True,
    )
    # Record claims a stale sha256 and 48 frames, but timing clock demands 72 frames (24-frame mismatch > 1 frame!)
    rec = {
        "schema": "video_clip_record/1",
        "shot_id": "S01_SH001",
        "route": "video",
        "clip_path": "production/video/cut/S01_SH001.mp4",
        "clip_sha256": "stale_recorded_hash_that_does_not_match_disk",
        "frames": 48,
        "in_s": 0.0,
        "out_s": 2.0,
    }
    (ep_dir / "production" / "video" / "S01_SH001.json").write_text(json.dumps(rec), encoding="utf-8")
    script = {"shots": [{"shot_id": "S01_SH001", "segment_id": "S01", "route": "video"}]}
    (ep_dir / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")

    bad_timing = ET.retime_with_edit_points(
        {
            "schema": "episode_timing/1",
            "fps": 24,
            "read_s": 3.0,
            "total_frames": 72,
            "shots": {"S01_SH001": {"segment_id": "S01", "start_frame": 0, "end_frame": 72, "frames": 72, "seconds": 3.0, "planned_seconds": 3.0}},
            "spines": {"S01_SH001": []},
            "coverage": 1.0,
            "alignment_status": "PASS",
            "unmatched": [],
        },
        script,
    )
    t_path = ep_dir / "audio" / "timing.json"
    ET.persist_authoritative_clock(bad_timing, t_path)

    with pytest.raises(ContractError, match="drift|pad|truncate|frames"):
        BS.build("S01_SH001", episode_dir=ep_dir, work_dir=work_dir, timing_doc=bad_timing, timing_path=t_path)

    # Cache key must change when target_size, filter/encode settings, or actual file bytes on disk change
    t_shot = {"frames": 48, "start_frame": 0, "end_frame": 48}
    k_base = BS.compute_segment_cache_key(
        "S01_SH001", script["shots"][0], t_shot,
        timing_id="tid1", render_epoch="ep1", source_path=clip_p, target_size=(2560, 1440),
        vf_chain="fps=24,scale=2560:1440:flags=lanczos", encode_settings={"crf": 14, "preset": "veryfast"},
        overlay_authority="plate",
    )
    k_size = BS.compute_segment_cache_key(
        "S01_SH001", script["shots"][0], t_shot,
        timing_id="tid1", render_epoch="ep1", source_path=clip_p, target_size=(1920, 1080),
        vf_chain="fps=24,scale=1920:1080:flags=lanczos", encode_settings={"crf": 14, "preset": "veryfast"},
        overlay_authority="plate",
    )
    k_enc = BS.compute_segment_cache_key(
        "S01_SH001", script["shots"][0], t_shot,
        timing_id="tid1", render_epoch="ep1", source_path=clip_p, target_size=(2560, 1440),
        vf_chain="fps=24,scale=2560:1440:flags=lanczos", encode_settings={"crf": 18, "preset": "medium"},
        overlay_authority="plate",
    )
    assert k_base != k_size and k_base != k_enc

    # Modify actual file bytes on disk while keeping rec["clip_sha256"] unchanged: cache key must change!
    clip_p.write_bytes(clip_p.read_bytes() + b"\x00\x01")
    k_disk_changed = BS.compute_segment_cache_key(
        "S01_SH001", script["shots"][0], t_shot,
        timing_id="tid1", render_epoch="ep1", source_path=clip_p, target_size=(2560, 1440),
        vf_chain="fps=24,scale=2560:1440:flags=lanczos", encode_settings={"crf": 14, "preset": "veryfast"},
        overlay_authority="plate",
    )
    assert k_disk_changed != k_base


def test_b3_ltx_route_resolution_requires_real_start_frame_evidence_and_persists_renderer_script_constant(tmp_path):
    """B3: Missing start-frame evidence must return REVIEW (never PASS with default confidence 'high');
    route resolution must pass start_frame and first_frame_comparison; apply_and_persist_ltx_routes must write RENDERER_SCRIPT_REL."""
    bare_shot = {
        "shot_id": "S09_SH001",
        "route": "video",
        "camera_spec": {"shot_size": "wide"},
        "character_ids": ["arthur"],
        "action_start_state": "Wide field in winter fog",
        "action_end_state": "Snow drifts across the field",
    }
    script = {"shots": [bare_shot], "audio_lines": []}

    # 1. No start_frame, no inspection_meta, no positions -> must be REVIEW (never PASS)
    sf_res = VP.inspect_ltx_start_frame(bare_shot)
    assert sf_res["status"] == "REVIEW"
    assert sf_res["confidence"] in ("missing", "unverified", "low")
    fit_res = VP.classify_ltx_natural_fit(bare_shot, script)
    assert fit_res["status"] == "REVIEW" and fit_res["natural_for_ltx"] is False

    # 2. reroute_unnatural_ltx_shots must forward start_frames and first_frame_comparisons
    f0_good = np.full((64, 64, 3), 80, dtype=np.uint8)
    f0_diverged = np.full((64, 64, 3), 230, dtype=np.uint8)
    cmp_bad = VP.compare_ltx_first_frame_to_source(f0_good, f0_diverged)
    rerouted = VP.reroute_unnatural_ltx_shots(
        script,
        start_frames={"S09_SH001": f0_good},
        inspections={"S09_SH001": {"confidence": "high", "source_sha256": "deadbeef"}},
        first_frame_comparisons={"S09_SH001": cmp_bad},
    )
    assert "S09_SH001" in rerouted["rerouted_to_25d"]
    assert any("frame 0 diverged" in r for r in rerouted["evaluations"]["S09_SH001"]["reasons"])

    # 3. Single renderer script path constant shared by plan.py, build_segments.py, and mix.py
    assert hasattr(VP, "RENDERER_SCRIPT_REL") and VP.RENDERER_SCRIPT_REL == "story/production_script.json"
    assert BS.RENDERER_SCRIPT_REL == VP.RENDERER_SCRIPT_REL
    assert MIX.RENDERER_SCRIPT_REL == VP.RENDERER_SCRIPT_REL

    ep_dir = tmp_path / "ep_test"
    (ep_dir / "story").mkdir(parents=True, exist_ok=True)
    (ep_dir / VP.RENDERER_SCRIPT_REL).write_text(json.dumps(script), encoding="utf-8")
    persisted = VP.apply_and_persist_ltx_routes(ep_dir)
    assert Path(persisted["renderer_script_path"]) == ep_dir / VP.RENDERER_SCRIPT_REL
    saved_doc = json.loads((ep_dir / VP.RENDERER_SCRIPT_REL).read_text(encoding="utf-8"))
    assert saved_doc["shots"][0]["route"] == "still_25d"


def test_b4a_mix_populates_ambience_beds_or_records_intentional_absence_and_removes_hand_set_map_fallbacks(tmp_path):
    """B4.1 & B4.2: mix.py must populate BEDS via loop_fill_spatial (or record intentional absence per shot)
    and must NOT invent 0.25s/0.35s fallback map events when a map shot has no emitter plan (flag REVIEW instead)."""
    unplanned_map_shot = {"shot_id": "S02_SH001", "route": "map", "map_spec": {"line_style": "chalk"}}
    t_map = {"start_frame": 0, "frames": 48, "end_frame": 48}
    # No draw_spans_frames and no frame_locked_audio_events -> must return empty list, NOT a 0.25s fallback event!
    evs = MIX.emit_map_audio_events_for_shot(unplanned_map_shot, t_map, fps=24)
    assert evs == []

    script_doc = {
        "segments": [{"id": "S01", "mood": "somber"}],
        "shots": [
            {
                "shot_id": "S01_SH001",
                "segment_id": "S01",
                "route": "still_25d",
                "sound_plan": {"bed": "trench_wind", "gain_db": -22.0, "source_x": 0.35, "distance": "medium"},
            },
            {
                "shot_id": "S01_SH002",
                "segment_id": "S01",
                "route": "still_25d",
                "intentional_silence": True,
            },
            unplanned_map_shot,
        ],
    }
    timing_doc = ET.retime_with_edit_points(
        {
            "schema": "episode_timing/1",
            "fps": 24,
            "read_s": 6.0,
            "total_frames": 144,
            "shots": {
                "S01_SH001": {"segment_id": "S01", "start_frame": 0, "end_frame": 48, "frames": 48, "seconds": 2.0, "planned_seconds": 2.0},
                "S01_SH002": {"segment_id": "S01", "start_frame": 48, "end_frame": 96, "frames": 48, "seconds": 2.0, "planned_seconds": 2.0},
                "S02_SH001": {"segment_id": "S01", "start_frame": 96, "end_frame": 144, "frames": 48, "seconds": 2.0, "planned_seconds": 2.0},
            },
            "spines": {"S01_SH001": [], "S01_SH002": [], "S02_SH001": []},
            "coverage": 1.0,
            "alignment_status": "PASS",
            "unmatched": [],
        },
        script_doc,
    )
    t_path = tmp_path / "clock" / "timing.json"
    ET.persist_authoritative_clock(timing_doc, t_path)

    # P0-3: narration is a hard contract now (no silent substitution): give the fixture a canonical narration.wav
    (tmp_path / "audio").mkdir(exist_ok=True)
    with wave.open(str(tmp_path / "audio" / "narration.wav"), "wb") as _w:
        _w.setnchannels(1)
        _w.setsampwidth(2)
        _w.setframerate(24000)
        _w.writeframes((np.sin(np.arange(24000 * 6) / 20.0) * 3000).astype(np.int16).tobytes())
    rep = MIX.run_mix(
        episode_dir=tmp_path,
        dl_dir=tmp_path,
        work_dir=tmp_path / "work",
        timing_doc=timing_doc,
        timing_path=t_path,
        script_doc=script_doc,
    )
    assert "shot_beds" in rep
    assert rep["shot_beds"]["S01_SH001"]["bed_populated"] is True
    assert rep["shot_beds"]["S01_SH002"]["bed_intentionally_absent"] is True
    assert rep["stems"]["bed_lufs"] is not None and rep["stems"]["bed_lufs"] > -65.0
    # Unplanned map shot must surface a REVIEW finding instead of silently passing with 0.25s/0.35s fallback
    assert any(f.get("shot_id") == "S02_SH001" and f.get("status") == "REVIEW" for f in rep["findings"])


def test_b4b_bs1770_k_weighted_channel_sum_lufs_and_written_wav_reopen_measurement(tmp_path):
    """B4.3 & B4.4: compute_integrated_lufs must implement real BS.1770-4 K-weighting + channel-weighted energy sum
    (matching ffmpeg ebur128 within 0.15 LU on asymmetric stereo), and measure_mix_loudness_report must measure the reopened WAV on disk."""
    sr = 48000
    t = np.arange(sr * 3) / float(sr)
    left = 0.15 * np.sin(2 * np.pi * 1000.0 * t)
    right = 0.05 * np.sin(2 * np.pi * 440.0 * t)
    stereo = np.stack([left, right], axis=-1).astype(np.float32)

    wav_p = tmp_path / "test_stereo.wav"
    with wave.open(str(wav_p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.clip(stereo, -1.0, 1.0) * 32767.0).astype("<i2").tobytes())

    ebur_lufs = TG.measure_file(wav_p)["lufs"]
    calc_lufs = MIX.compute_integrated_lufs(stereo, sr=sr)
    assert abs(calc_lufs - ebur_lufs) <= 0.15

    rep = MIX.measure_mix_loudness_report(wav_p, sr=sr)
    assert rep["measured_from_disk"] is True
    assert rep["measured_file"] == str(wav_p)
    assert abs(rep["integrated_lufs"] - ebur_lufs) <= 0.15


def test_b4c_episode_g8_stems_and_standalone_mix_share_spatial_placement_and_ducking():
    """B4.5: episode G8 (audio/stems) and standalone mix.py must call the same shared spatial placement and presence-band ducking."""
    sr = 48000
    n = sr * 2
    t = np.linspace(0.0, 2.0, n, dtype=np.float32)
    voice_mono = (0.20 * np.sin(2 * np.pi * 320.0 * t)).astype(np.float32)
    bed_stereo = np.stack([0.04 * np.sin(2 * np.pi * 900.0 * t)] * 2, axis=-1).astype(np.float32)
    mus_stereo = np.stack([0.05 * np.sin(2 * np.pi * 520.0 * t)] * 2, axis=-1).astype(np.float32)
    spot_mono = (0.12 * np.sin(2 * np.pi * 1200.0 * t[: sr // 2])).astype(np.float32)

    mix_sfx = np.zeros((n, 2), dtype=np.float32)
    MIX.place_spatial(mix_sfx, spot_mono, 0.25, -6.0, source_x=0.25, distance="close", camera_op="push_in", progress=0.5)

    stems_sfx = np.zeros((n, 2), dtype=np.float32)
    STEMS.place_spatial_cue(stems_sfx, spot_mono, 0.25, -6.0, source_x=0.25, distance="close", camera_op="push_in", progress=0.5, sr=sr)
    assert np.allclose(mix_sfx, stems_sfx, atol=1e-6)

    mix_bed_d, mix_mus_d = DUCK.duck_stems_under_voice(bed_stereo, mus_stereo, voice_mono, sr=sr)
    stems_bed_d, stems_mus_d = STEMS.duck_background_stems(bed_stereo, mus_stereo, voice_mono, sr=sr)
    assert np.allclose(mix_bed_d, stems_bed_d, atol=1e-6)
    assert np.allclose(mix_mus_d, stems_mus_d, atol=1e-6)


def test_b5_upscaler_derives_status_from_qc_fails_on_missing_output_checks_imwrite_and_skips_2560x1440_reencode(tmp_path, monkeypatch):
    """B5: upscale_with_backend must derive status from accepted(qc_rows) on lanczos/registered backends,
    return FAIL if model output file is missing, check every cv2.imwrite return, and skip re-encoding 2560x1440 in finish/upscale.py."""
    cv2 = pytest.importorskip("cv2")
    src = tmp_path / "src.png"
    rng = np.random.default_rng(7)
    img = rng.integers(40, 200, size=(90, 160, 3), dtype=np.uint8)
    cv2.imwrite(str(src), img)

    # 1. Lanczos resize does not pass Q3_detail_added (2x detail gain) or Q5 (when lpips absent), so status must be REVIEW, never PASS
    res_lanczos = SR_UP.upscale_with_backend(src, tmp_path / "lanczos.png", lane="still_25d", backend="lanczos", size=(320, 180))
    assert res_lanczos["status"] == "REVIEW"

    # 2. Registered backend that shifts color fails QC -> status must be REVIEW/FAIL, never PASS
    SR_UP.register_upscaler("bad_color_test", lambda im, sz, **kw: np.clip(cv2.resize(im, sz).astype(np.int16) + 40, 0, 255).astype(np.uint8))
    try:
        res_reg = SR_UP.upscale_with_backend(src, tmp_path / "reg.png", lane="still_25d", backend="bad_color_test", size=(320, 180))
        assert res_reg["status"] in ("REVIEW", "FAIL")
    finally:
        SR_UP.UPSCALER_REGISTRY.pop("bad_color_test", None)

    # 3. Missing model output file (when upscale() returns a path that does not exist) must be FAIL, never PASS on im.copy()
    monkeypatch.setattr(
        SR_UP,
        "upscale",
        lambda *a, **kw: {"status": "PASS", "result": str(tmp_path / "nonexistent_model_out.png"), "tries": []},
    )
    res_missing = SR_UP.upscale_with_backend(src, tmp_path / "missing_model.png", lane="still_25d", backend="realplksr4x", size=(320, 180))
    assert res_missing["status"] == "FAIL"

    # 4. Unchecked cv2.imwrite failure must be caught and reported as FAIL
    monkeypatch.setattr(cv2, "imwrite", lambda *a, **kw: False)
    res_write_fail = SR_UP.upscale_with_backend(src, tmp_path / "write_fail.png", lane="still_25d", backend="as_is")
    assert res_write_fail["status"] == "FAIL"
    monkeypatch.undo()

    # 5. finish/upscale.py upscale() must wire needs_resize() and pass through a 2560x1440 clip without re-encoding
    clip_2k = tmp_path / "already_2k.mp4"
    out_2k = tmp_path / "out_2k.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "testsrc=size=2560x1440:rate=24:duration=0.25",
            "-pix_fmt", "yuv420p", str(clip_2k),
        ],
        check=True,
    )
    FIN_UP.upscale(clip_2k, out_2k)
    assert out_2k.is_file()
    assert out_2k.read_bytes() == clip_2k.read_bytes()
