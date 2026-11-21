"""Delivery gate fails closed: hand-made receipts only."""
from __future__ import annotations

import json

from explainer_engine.qa import delivery_gate as DG


def _write_receipt(clip_path, receipt):
    rec_path = clip_path.with_suffix(".render_log.json")
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps(receipt), encoding="utf-8")


def _make_clip(clips_dir, shot_id, receipt):
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip = clips_dir / f"{shot_id}.mp4"
    clip.write_bytes(b"x")
    _write_receipt(clip, receipt)
    return clip.name


def _write_log(log_path, shots, paid_calls=0):
    log_path.write_text(json.dumps({"paid_calls": paid_calls, "shots": shots}), encoding="utf-8")


def _photo_receipt(**overrides):
    rec = {"kind": "photo", "camera": {"move": "zoom_in"}, "film_id": "film1", "font": "TestFont",
           "depth": {"file": "d.npy", "near_m": 2.5, "far_m": 60.0},
           "plume_checks": [{"frame": 0, "status": "PASS", "person_share": 0.0}]}
    rec.update(overrides)
    return rec


def _map_receipt(**overrides):
    rec = {"kind": "map", "render": {"frames": 1}, "camera": {"move": "zoom_in"}, "film_id": "film1", "font": "TestFont"}
    rec.update(overrides)
    return rec


def test_pass(tmp_path):
    clips_dir = tmp_path / "clips"
    c1 = _make_clip(clips_dir, "S1", _photo_receipt())
    c2 = _make_clip(clips_dir, "M1", _map_receipt())
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": c1}, {"id": "M1", "clip": c2}])
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "PASS", verdict
    assert verdict["problems"] == []
    assert verdict["shots"] == {"S1": "PASS", "M1": "PASS"}


def test_missing_receipt_is_a_fail(tmp_path):
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir(parents=True)
    clip = clips_dir / "S1.mp4"
    clip.write_bytes(b"x")
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": clip.name}])
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "FAIL"
    assert verdict["shots"]["S1"] == "FAIL"
    assert any("missing receipt" in p for p in verdict["problems"])


def test_paid_calls_need_a_cost_card(tmp_path):
    clips_dir = tmp_path / "clips"
    c = _make_clip(clips_dir, "S1", _photo_receipt())
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": c}], paid_calls=1)
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "FAIL"
    assert any("paid calls" in p for p in verdict["problems"])


def test_photo_orbit_is_a_fail(tmp_path):
    clips_dir = tmp_path / "clips"
    c = _make_clip(clips_dir, "S1", _photo_receipt(camera={"move": "orbit"}))
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": c}])
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "FAIL"
    assert any("photo camera.move" in p for p in verdict["problems"])


def test_plume_status_fail_is_a_fail(tmp_path):
    clips_dir = tmp_path / "clips"
    rec = _photo_receipt(plume_checks=[{"frame": 0, "status": "FAIL", "person_share": 0.1}])
    c = _make_clip(clips_dir, "S1", rec)
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": c}])
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "FAIL"
    assert any("plume_checks[0]" in p for p in verdict["problems"])


def test_map_receipt_without_film_id_is_a_fail(tmp_path):
    clips_dir = tmp_path / "clips"
    c = _make_clip(clips_dir, "M1", _map_receipt(film_id=None))
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "M1", "clip": c}])
    verdict = DG.check(log_path, clips_dir)
    assert verdict["status"] == "FAIL"
    assert any("map receipt missing film_id" in p for p in verdict["problems"])


def test_main_exit_codes(tmp_path, capsys):
    clips_dir = tmp_path / "show_work" / "clips"
    c = _make_clip(clips_dir, "S1", _photo_receipt())
    log_path = tmp_path / "show.episode_log.json"
    _write_log(log_path, [{"id": "S1", "clip": c}])
    assert DG.main([str(log_path)]) == 0
    out = capsys.readouterr().out
    assert '"status": "PASS"' in out

    _write_log(log_path, [{"id": "S1", "clip": c}], paid_calls=1)
    assert DG.main([str(log_path)]) == 1
    out = capsys.readouterr().out
    assert "paid calls" in out
