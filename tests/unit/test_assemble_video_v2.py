"""The picture timeline (P7, production/assemble.py ``build_video_v2``, finish/grade.py ``transfer_to_key``): synthetic numpy
clips through an ``edit_and_grade_manifest/1`` fixture job. The frame logic runs without ffmpeg; only the encode test needs it.
(The sound director's stereo mix is tested in test_assemble_v2.py; this file is the picture half of the same P7 compiler.)"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.finish import grade as G
from explainer_engine.production import assemble as ASM
from explainer_engine.standards import sourced_rules as SR

FPS, SIZE = 24, (32, 18)
HANDLE = SR.T("BP-128", "handle_frames")[0]  # a clip rendered with the band's lower handle at both ends
COLOURS = {"A": (40, 60, 110), "B": (220, 150, 60), "C": (60, 160, 70)}
SPANS = {"A": 24, "B": 24, "C": 48}


def _clip(colour, n, seed):
    rng = np.random.default_rng(seed)
    return np.clip(np.array(colour) + rng.normal(0, 18, (n, SIZE[1], SIZE[0], 3)), 0, 255).astype(np.uint8)


JOB: list[Path] = [Path(".")]


def _write(path: Path, doc) -> dict:
    """Write a fixture file and return its file reference (path relative to the job, sha256)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return {"path": str(path.relative_to(JOB[0])), "sha256": contracts.sha256_file(path)}


def make_job(tmp_path, *, extra=0, lead=6, key=False, grade=None, handle=HANDLE, clip_n=None):
    job = tmp_path / "job"
    JOB[0] = job
    shots_dir = job / "shots"
    shots_dir.mkdir(parents=True)
    for i, (sid, span) in enumerate(SPANS.items()):
        n = (clip_n or {}).get(sid, span + 2 * handle + extra)
        np.save(shots_dir / f"{sid}.npy", _clip(COLOURS[sid], n, i))
    spine = {"schema": "audio_spine/2", "fps": FPS, "total_frames": 96, "words": [], "post_hoc_shots": [],
             "segments": [{"id": "s1", "start_frame": 0}, {"id": "s2", "start_frame": 48}]}
    film = {"schema": "film_shots/2", "episode": "napoleon", "fps": FPS, "style": {"trigger": "xworld", "video_sentence": "Hand-drawn cartoon."},
            "cast": {"nap": {"tag": "a short man in a green coat with a bicorne hat"}}, "places": {"p": "a canvas command tent"}, "shots": [
        {"id": sid, "scene": sc, "mode": "narrated", "beat": "A beat.", "seconds": SPANS[sid] / FPS, "frame": {"size": "WS", "place": "p"},
         "source": "keyframe", "tier": "hold", "lane": "KEYFRAME_LTX", "archetype": "scene_wide", "duration_frames": SPANS[sid],
         "width": 1920, "height": 1088, "lens_tier": "normal", "focal_xy": [0.5, 0.5], "continuity_ref": None, "blocking_ref": None}
        for sid, sc in (("A", "s1"), ("B", "s1"), ("C", "s2"))]}
    spine_ref, film_ref = _write(job / "audio_spine.json", spine), _write(job / "film_shots.json", film)
    key_ref = None
    if key:
        Image.fromarray(np.full((SIZE[1], SIZE[0], 3), COLOURS["A"], np.uint8)).save(job / "key_s1.png")
        key_ref = "key_s1.png"
    manifest = {"schema": "edit_and_grade_manifest/1", "film_shots": film_ref, "audio_spine": spine_ref, "scenes": [
        {"scene_id": "s1", "key_master_frame": key_ref, "grade": {"lut": grade} if grade else None,
         "cuts": [{"from_shot": "A", "to_shot": "B", "cut_type": "KULESHOV_L_CUT", "at_frame": 24, "audio_lead_frames": lead}]},
        {"scene_id": "s2", "key_master_frame": None, "grade": None,
         "cuts": [{"from_shot": "B", "to_shot": "C", "cut_type": "WHIP_PAN", "at_frame": 48, "audio_lead_frames": 0}]}]}
    return job, shots_dir, manifest


def frames_of(plan, job, shots_dir):
    return dict(ASM.iter_video_frames(plan, job, shots_dir))


def test_the_plan_tiles_the_read_and_the_incoming_audio_of_a_j_cut_starts_its_lead_early(tmp_path):
    job, shots, manifest = make_job(tmp_path)
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    assert (plan["fps"], plan["total_frames"]) == (FPS, 96)
    assert [(s["shot_id"], s["start_frame"], s["end_frame"]) for s in plan["shots"]] == [("A", 0, 24), ("B", 24, 48), ("C", 48, 96)]
    assert {a["shot_id"]: a["start_frame"] for a in plan["audio"]} == {"A": 0, "B": 24 - 6, "C": 48}
    assert all(s["source_in"] == HANDLE for s in plan["shots"])
    assert plan["findings"] == []


def test_the_output_is_the_spine_length_and_every_cut_lands_on_its_at_frame(tmp_path):
    job, shots, manifest = make_job(tmp_path, lead=0)
    manifest["scenes"][1]["cuts"][0]["cut_type"] = "STRAIGHT_CUT"
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    out = frames_of(plan, job, shots)
    assert sorted(out) == list(range(96))
    clips = {sid: np.load(shots / f"{sid}.npy") for sid in SPANS}
    for cut_frame, before, after in ((24, "A", "B"), (48, "B", "C")):
        assert np.array_equal(out[cut_frame - 1], clips[before][HANDLE + SPANS[before] - 1])
        assert np.array_equal(out[cut_frame], clips[after][HANDLE])


def test_a_clip_shorter_than_its_cut_span_is_refused_not_repaired(tmp_path):
    job, shots, manifest = make_job(tmp_path, clip_n={"B": 20})
    with pytest.raises(ContractError, match="B: the clip has 20 frames"):
        ASM.plan_video_v2(manifest, job, shots, size=SIZE)


def test_an_audio_lead_longer_than_the_shot_it_leaves_is_refused(tmp_path):
    job, shots, manifest = make_job(tmp_path, lead=30)
    with pytest.raises(ContractError, match="audio lead"):
        ASM.plan_video_v2(manifest, job, shots, size=SIZE)


def test_a_changed_input_makes_the_manifest_stale(tmp_path):
    job, shots, manifest = make_job(tmp_path)
    (job / "film_shots.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="CN-02"):
        ASM.plan_video_v2(manifest, job, shots, size=SIZE)


def test_handles_under_bp128_s_band_are_a_review_finding_not_a_stop(tmp_path):
    job, shots, manifest = make_job(tmp_path, handle=2)
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    assert {f["rule"] for f in plan["findings"]} == {"BP-128"} and {f["severity"] for f in plan["findings"]} == {"REVIEW"}


def test_a_cut_off_the_onset_band_is_review(tmp_path):
    job, shots, manifest = make_job(tmp_path)
    lo, hi = SR.T("BP-128", "cut_after_onset_frames")
    ok = ASM.plan_video_v2(manifest, job, shots, size=SIZE, onsets={"B": 24 - lo})
    late = ASM.plan_video_v2(manifest, job, shots, size=SIZE, onsets={"B": 24 - hi - 5})
    assert ok["findings"] == [] and [f["rule"] for f in late["findings"]] == ["BP-128"]


def test_transfer_to_key_moves_the_frame_toward_the_key_and_never_past_blend_max():
    rng = np.random.default_rng(5)
    frame = np.clip(0.25 + rng.normal(0, 0.05, (24, 24, 3)), 0, 1)
    key = np.clip(0.65 + rng.normal(0, 0.12, (24, 24, 3)), 0, 1)
    top = SR.T("BP-130", "blend_max")
    before = G.lab_distance(frame, key)
    half = G.lab_distance(G.transfer_to_key(frame, key, top / 2), key)
    full = G.lab_distance(G.transfer_to_key(frame, key, top), key)
    assert full < half < before
    assert np.array_equal(G.transfer_to_key(frame, key, 5.0), G.transfer_to_key(frame, key, top))  # capped, same picture
    assert G.blend_cap(5.0) == (top, True) and G.blend_cap(top) == (top, False)
    assert np.allclose(G.transfer_to_key(frame, key, 0.0), frame)


def test_the_cut_adjacent_frame_of_a_shot_is_closer_to_the_scene_key_after_the_compile(tmp_path):
    job, shots, manifest = make_job(tmp_path, key=True)
    plain = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    manifest_off = json.loads(json.dumps(manifest))
    manifest_off["scenes"][0]["key_master_frame"] = None
    off = ASM.plan_video_v2(manifest_off, job, shots, size=SIZE)
    key = np.asarray(Image.open(job / "key_s1.png").convert("RGB")) / 255.0
    after, before = frames_of(plain, job, shots)[24] / 255.0, frames_of(off, job, shots)[24] / 255.0
    assert G.lab_distance(after, key) < G.lab_distance(before, key)
    assert plain["scenes"]["s1"]["blend"] <= SR.T("BP-130", "blend_max")


def test_a_blend_over_the_cap_is_applied_capped_and_reported(tmp_path):
    job, shots, manifest = make_job(tmp_path, key=True)
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE, blend=0.99)
    assert plan["scenes"]["s1"]["blend"] == SR.T("BP-130", "blend_max")
    assert [f["rule"] for f in plan["findings"]] == ["BP-130"]


def test_the_look_is_applied_last_and_a_whip_smears_the_cut(tmp_path):
    job, shots, manifest = make_job(tmp_path, grade="warm_gold")
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    out = frames_of(plan, job, shots)
    raw = np.load(shots / "C.npy")[HANDLE].astype(float)
    whipped_mid = out[48]  # the middle of the whip window centred on the cut
    assert whipped_mid.astype(float).std() < raw.std()
    # scene s1 carries the era LOOK: its frames differ from the raw clip by the grade, scene s2 (no grade) after the whip only
    a_raw = np.load(shots / "A.npy")[HANDLE].astype(float)
    assert not np.allclose(out[0], a_raw)


def test_the_otio_export_parses_and_lists_the_same_cuts_and_leads(tmp_path):
    job, shots, manifest = make_job(tmp_path)
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    derived = dict(plan, schema="assemble_manifest/1")
    path = ASM.export_otio(derived, tmp_path / "ep.otio")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["OTIO_SCHEMA"] == "Timeline.1"
    tracks = {t["name"]: t for t in doc["tracks"]["children"]}
    starts, at = {}, 0
    for c in tracks["V1"]["children"]:
        starts[c["name"]] = at
        at += c["source_range"]["duration"]["value"]
    assert starts == {"A": 0, "B": 24, "C": 48} and at == 96
    heard = {}
    for name in ("A1", "A2"):
        t = 0
        for c in tracks[name]["children"]:
            if c["OTIO_SCHEMA"].startswith("Clip"):
                heard[c["name"]] = t
            t += c["source_range"]["duration"]["value"]
    assert heard == {"A_audio": 0, "B_audio": 18, "C_audio": 48}


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")
def test_build_video_v2_encodes_the_master_frame_at_the_job_fps_and_writes_the_derived_manifest_and_otio(tmp_path):
    job, shots, manifest = make_job(tmp_path)
    r = ASM.build_video_v2(manifest, shots, tmp_path / "out" / "ep.mp4", job)
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(r["video"])],
                           capture_output=True, text=True, check=True)
    st = json.loads(probe.stdout)["streams"][0]
    assert (st["width"], st["height"], st["r_frame_rate"], int(st["nb_read_frames"])) == (2560, 1440, f"{FPS}/1", 96)
    derived = json.loads(r["manifest"].read_text(encoding="utf-8"))
    assert derived["schema"] == "assemble_manifest/1" and set(derived["derived_from"]) >= {"film_shots", "audio_spine"}
    assert contracts.derived_findings(derived, job) == []
    assert json.loads(r["otio"].read_text(encoding="utf-8"))["OTIO_SCHEMA"] == "Timeline.1"


@pytest.mark.parametrize("lane,match", [("HOST_COMMENTARY", "D-89"), ("DRAMA_BLOCKED_3D", "D-75"), ("NOT_A_LANE", "CN-01")])
def test_a_refused_or_unknown_lane_in_film_shots_does_not_compile(tmp_path, lane, match):
    job, shots, manifest = make_job(tmp_path)
    film = json.loads((job / "film_shots.json").read_text(encoding="utf-8"))
    film["shots"][0]["lane"] = lane
    manifest["film_shots"] = _write(job / "film_shots.json", film)
    with pytest.raises(ContractError, match=match):
        ASM.plan_video_v2(manifest, job, shots, size=SIZE)


def test_frames_are_streamed_not_held_per_shot(tmp_path, monkeypatch):
    """The first frame comes out after one clip frame (plus the two boundary reads of a keyed scene), not after the whole shot."""
    job, shots, manifest = make_job(tmp_path, key=True)
    plan = ASM.plan_video_v2(manifest, job, shots, size=SIZE)
    read, real = [], ASM.clip_frames

    def spy(path, start, count):
        for fr in real(path, start, count):
            read.append(count)
            yield fr
    monkeypatch.setattr(ASM, "clip_frames", spy)
    it = ASM.iter_video_frames(plan, job, shots)
    next(it)
    assert read.count(24) == 1 and read.count(1) == 2   # one frame of the 24-frame stream, the two boundary frames of the first shot


def test_whip_blur_repeats_the_edge_pixels_instead_of_wrapping_them_round_the_frame():
    x = np.zeros((4, 100, 3), dtype=np.float32)
    x[:, 0] = 1.0                                              # a bright left edge, black everywhere else
    out = ASM._whip_blur(x, 1.0)
    assert out[:, -1].max() == 0.0 and out[:, -5].max() == 0.0     # np.roll used to carry the edge to the right side
    assert out[:, 0].min() > 0.0                                   # the edge pixel still smears inward
    assert np.array_equal(ASM._whip_blur(x, 0.0), x)


def test_clip_info_probes_a_file_once(tmp_path, monkeypatch):
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"x")
    calls = []

    class R:
        stdout = json.dumps({"streams": [{"nb_read_frames": "5", "width": 8, "height": 4}]})

    monkeypatch.setattr(ASM.subprocess, "run", lambda *a, **k: calls.append(a) or R())
    ASM._CLIP_INFO.clear()
    assert [ASM.clip_info(clip) for _ in range(3)] == [(5, 8, 4)] * 3 and len(calls) == 1
    clip.write_bytes(b"xy")                                       # a re-rendered clip is probed again
    ASM.clip_info(clip)
    assert len(calls) == 2


def test_a_near_flat_boundary_frame_cannot_blow_the_transfer_scale_up_and_is_reported():
    rng = np.random.default_rng(0)
    key = rng.random((16, 16, 3))
    flat = np.full((16, 16, 3), 0.02) + rng.normal(0, 1e-4, (16, 16, 3))      # a night sky: std ~ 0
    p = G.transfer_params(flat, key)
    assert p["scale_clipped"] and p["scale"].max() <= G.SCALE_MAX and p["scale"].min() >= G.SCALE_MIN
    assert not G.transfer_params(key, key)["scale_clipped"]
