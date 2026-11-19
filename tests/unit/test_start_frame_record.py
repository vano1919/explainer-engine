"""Step 1.3 (D-139): the start-frame record, the route proposals and the unresolved-review count. Free and deterministic."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from explainer_engine.videolane import ingest as I  # noqa: E402


def _picture(path: Path, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = (rng.random((72, 128, 3)) * 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (9, 9), 3)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)
    return img


def _clip(path: Path, first: np.ndarray, frames: int = 6) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (first.shape[1], first.shape[0]))
    for _ in range(frames):
        w.write(first)
    w.release()


SHOT = {"shot_id": "S01_SH001", "route": "video", "camera_spec": {"shot_size": "wide"}}


def test_matching_frame0_and_picture_with_evidence_is_pass(tmp_path):
    img = _picture(tmp_path / "pics" / "a.png")
    _clip(tmp_path / "raw.mp4", img)
    pics = {"S01_SH001_start": {"file": "pics/a.png"}}
    r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", pics)
    assert r["status"] == "PASS" and r["frame0_vs_source"]["status"] == "PASS" and r["inspection"]["status"] == "PASS"


def test_a_missing_picture_is_needs_evidence_never_pass(tmp_path):
    _clip(tmp_path / "raw.mp4", _picture(tmp_path / "pics" / "a.png"))
    for pics in (None, {}, {"S01_SH001_start": {"file": "pics/gone.png"}}):
        r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", pics)
        assert r["status"] == "NEEDS_EVIDENCE" and r["frame0_vs_source"] is None and r["reasons"]


def test_a_continuation_has_no_picture_to_compare(tmp_path):
    img = _picture(tmp_path / "pics" / "a.png")
    _clip(tmp_path / "raw.mp4", img)
    r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", {"S01_SH001_start": {"file": "pics/a.png"}},
                            is_continuation=True)
    assert r["status"] == "NEEDS_EVIDENCE"


def test_a_diverged_frame0_is_review(tmp_path):
    _picture(tmp_path / "pics" / "a.png", seed=1)
    other = _picture(tmp_path / "other.png", seed=7)
    _clip(tmp_path / "raw.mp4", other)
    r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", {"S01_SH001_start": {"file": "pics/a.png"}})
    assert r["status"] == "REVIEW" and r["frame0_vs_source"]["status"] == "FAIL"


def test_an_undecodable_clip_is_needs_evidence(tmp_path):
    _picture(tmp_path / "pics" / "a.png")
    (tmp_path / "raw.mp4").write_bytes(b"not a video")
    r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", {"S01_SH001_start": {"file": "pics/a.png"}})
    assert r["status"] == "NEEDS_EVIDENCE"


def test_missing_inspection_data_is_review(tmp_path, monkeypatch):
    from explainer_engine.videolane import plan as P
    img = _picture(tmp_path / "pics" / "a.png")
    _clip(tmp_path / "raw.mp4", img)
    monkeypatch.setattr(P, "inspect_ltx_start_frame", lambda shot, start_frame=None: {
        "status": "REVIEW", "confidence": "missing", "has_evidence": False, "issues": ["no evidence"]})
    r = I.start_frame_check(tmp_path, SHOT, tmp_path / "raw.mp4", {"S01_SH001_start": {"file": "pics/a.png"}})
    assert r["status"] == "REVIEW" and any("no evidence" in x for x in r["reasons"])


def test_route_proposals_are_written_and_the_script_is_not_changed(tmp_path):
    script = {"shots": [{"shot_id": "S01_SH001", "route": "video", "camera_spec": {"shot_size": "close_up"},
                         "character_ids": ["a"], "audio_line_ids": ["L1"]}],
              "audio_lines": [{"line_id": "L1", "speaker_type": "character", "text": "Hello there."}]}
    before = json.dumps(script, sort_keys=True)
    props = I.route_proposals(tmp_path, script)
    assert json.dumps(script, sort_keys=True) == before and script["shots"][0]["route"] == "video"
    assert props and props[0]["from_route"] == "video" and props[0]["to_route"] != "video"
    on_disk = json.loads((tmp_path / "production" / "route_proposals.json").read_text(encoding="utf-8"))
    assert on_disk["proposals"] == props


def test_unresolved_reviews_counts_each_clip_once_with_both_reasons(tmp_path):
    v = tmp_path / "production" / "video"
    v.mkdir(parents=True)
    (v / "S01_SH001.json").write_text(json.dumps({"shot_id": "S01_SH001", "status": "REVIEW",
                                                  "start_frame_check": {"status": "REVIEW"}}), encoding="utf-8")
    (v / "S01_SH002.json").write_text(json.dumps({"shot_id": "S01_SH002", "status": "PASS",
                                                  "start_frame_check": {"status": "PASS"}}), encoding="utf-8")
    (v / "S01_SH003.json").write_text(json.dumps({"shot_id": "S01_SH003", "status": "PASS",
                                                  "start_frame_check": {"status": "NEEDS_EVIDENCE"}}), encoding="utf-8")
    r = I.unresolved_reviews(tmp_path)
    assert r["count"] == 2
    assert "start_frame_check REVIEW + clip findings REVIEW" in r["items"][0]


def test_a_padded_clip_counts_in_unresolved_reviews(tmp_path):
    v = tmp_path / "production" / "video"
    v.mkdir(parents=True)
    (v / "S01_SH009.json").write_text(json.dumps({"shot_id": "S01_SH009", "status": "REVIEW", "frame_pad": 1,
                                                  "start_frame_check": {"status": "PASS"}}), encoding="utf-8")
    r = I.unresolved_reviews(tmp_path)
    assert r["count"] == 1 and "frame_pad" in r["items"][0]
