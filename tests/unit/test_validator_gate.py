"""The 2026-11-20 validators run from one registry and one production-gate row; NOT_RUN is never a pass."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from explainer_engine import production_gate as PG
from explainer_engine.qa import validator_gate as VG

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
IDS = ["shift_line_id", "stated_theme", "claim_ledger", "camera_cards", "camera_clips", "ltx_prompts", "continuity_cards",
       "language", "master_size", "attempt_ranking"]
GEO = "ა"


def by_id(rows):
    return {r["id"]: r for r in rows}


def write(day, name, data):
    p = Path(day) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


def film(day, film_id="owner_film_01"):
    b = {"style_preset": "p"}
    write(day, "episode_film.json", {
        "schema": "episode_film/1", "film_id": film_id, "film_name": "n", "era": "e",
        "picture": {"era_look": "a", "grade_words": "b"}, "map": {"style_preset": "p", "font": "preset"}, "counter": b,
        "colour": {"targets": "c"}, "subtitles": {"font": "f", "colour": "#fff", "position": "bottom"},
        "direction": {"notes": ["n"]}, "narration": {"notes": ["n"]}})


def test_registry_lists_every_validator_once():
    assert [rid for rid, _ in VG.REGISTRY] == IDS


def test_empty_folder_is_all_not_run_and_the_gate_waits(tmp_path):
    rows = VG.run_all(tmp_path)
    assert [r["id"] for r in rows] == IDS and {r["status"] for r in rows} == {"NOT_RUN"}
    status, detail, _ = VG.gate_row(tmp_path)
    assert status == "WAIT" and "0 of 10 ran" in detail
    assert VG.main([str(tmp_path)]) == 2


def test_each_validator_is_called_from_the_gate(tmp_path, monkeypatch):
    """Every registered runner is invoked by run_all, with the episode folder."""
    seen = []
    fake = [(rid, (lambda d, rid=rid: seen.append((rid, d)) or VG._row(rid, rid, "PASS", "ok"))) for rid in IDS]
    monkeypatch.setattr(VG, "REGISTRY", fake)
    rows = VG.run_all(tmp_path)
    assert [s[0] for s in seen] == IDS and all(s[1] == tmp_path for s in seen) and len(rows) == 10


def test_gate_row_folds_statuses(tmp_path, monkeypatch):
    def reg(*statuses):
        return [(rid, (lambda d, rid=rid, st=st: VG._row(rid, rid, st, "x"))) for rid, st in zip(IDS, statuses)]
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * 10))
    assert VG.gate_row(tmp_path)[0] == "PASS"
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * 9, "REVIEW"))
    assert VG.gate_row(tmp_path)[0] == "PASS"
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * 9, "NOT_RUN"))
    status, detail, _ = VG.gate_row(tmp_path)
    assert status == "WAIT" and "attempt_ranking" in detail
    monkeypatch.setattr(VG, "REGISTRY", reg("FAIL", *["NOT_RUN"] * 9))
    assert VG.gate_row(tmp_path)[0] == "BLOCKED" and VG.main([str(tmp_path)]) == 1


def test_a_crashing_validator_is_not_run_not_pass(tmp_path, monkeypatch):
    def boom(day):
        raise RuntimeError("bad input")
    monkeypatch.setattr(VG, "REGISTRY", [("shift_line_id", boom)])
    row = VG.run_all(tmp_path)[0]
    assert row["status"] == "NOT_RUN" and "RuntimeError" in row["detail"]


def test_script_validators_run_on_a_real_script(tmp_path):
    shutil.copy(EXAMPLES / "titans_from_zero" / "production_script.json", tmp_path / "production_script.json")
    rows = by_id(VG.run_all(tmp_path))
    assert rows["shift_line_id"]["status"] in ("FAIL", "REVIEW") and "SL" in rows["shift_line_id"]["detail"]
    assert rows["stated_theme"]["status"] in ("REVIEW", "PASS")
    assert rows["claim_ledger"]["status"] in ("PASS", "REVIEW", "FAIL", "NOT_RUN")   # ran or said why not


def test_camera_cards_fail_through_the_gate(tmp_path):
    write(tmp_path, "shot_cards.json", [{"shot_id": "S01", "camera_move": "orbit"}])
    r = by_id(VG.run_all(tmp_path))["camera_cards"]
    assert r["status"] == "FAIL" and "CM-02" in r["detail"]


def test_camera_clips_use_the_sidecar_and_never_pass_a_missing_clip(tmp_path, monkeypatch):
    write(tmp_path, "clips/a.mp4.camera.json", {"camera_move": "zoom_in"})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "NOT_RUN"      # the clip file is missing
    (tmp_path / "clips" / "a.mp4").write_bytes(b"x")
    from explainer_engine.qa import camera_move
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, **k: {"status": "FAIL", "detail": "static"})
    r = by_id(VG.run_all(tmp_path))["camera_clips"]
    assert r["status"] == "FAIL" and "a.mp4" in r["detail"]
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, **k: {"status": "PASS", "detail": ""})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "PASS"
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, **k: {"status": "NOT_RUN", "detail": "floor OPEN"})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "NOT_RUN"


def test_ltx_prompts_fail_on_film_mismatch_and_need_the_film_to_pass(tmp_path):
    prompt = "Anna runs across the bridge while the camera trucks left"
    write(tmp_path, "ltx_prompts.json", [{"shot_id": "S01", "prompt": prompt, "hero_name": "Anna", "film_id": "other_film"}])
    assert by_id(VG.run_all(tmp_path))["ltx_prompts"]["status"] == "NOT_RUN"      # clean prompt, but LP-06 could not run
    film(tmp_path)
    r = by_id(VG.run_all(tmp_path))["ltx_prompts"]
    assert r["status"] == "FAIL" and "S01" in r["detail"] and "LP-06" in r["detail"]
    write(tmp_path, "ltx_prompts.json", [{"shot_id": "S01", "prompt": prompt, "hero_name": "Anna", "film_id": "owner_film_01"}])
    assert by_id(VG.run_all(tmp_path))["ltx_prompts"]["status"] == "PASS"


def test_continuity_cards_are_checked_with_the_episode_film(tmp_path):
    card = json.loads((EXAMPLES / "continuity" / "napoleon_tent.json").read_text(encoding="utf-8"))
    write(tmp_path, "continuity_cards.json", [card])
    assert by_id(VG.run_all(tmp_path))["continuity_cards"]["status"] == "PASS"
    card["film_id"] = "wrong_film"
    for c in card["cast"].values():
        c["identity"] = {"canon_frame": "c.png", "locked": ["jaw"]}
    write(tmp_path, "continuity_cards.json", card)
    film(tmp_path)
    r = by_id(VG.run_all(tmp_path))["continuity_cards"]
    assert r["status"] == "FAIL" and "CT-17" in r["detail"]


def test_language_fails_on_georgian_in_viewer_text(tmp_path):
    write(tmp_path, "narration.txt", "A fine English line.")
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "PASS"
    write(tmp_path, "viewer_text/title.txt", "Title " + GEO)
    r = by_id(VG.run_all(tmp_path))["language"]
    assert r["status"] == "FAIL" and "title.txt" in r["detail"]


def test_master_size_through_the_gate(tmp_path, monkeypatch):
    (tmp_path / "master.mp4").write_bytes(b"x")
    from explainer_engine.qa import master_size
    monkeypatch.setattr(master_size, "check_master_size", lambda p, d=None: {"status": "FAIL", "value": "1x1", "detail": "wrong size"})
    r = by_id(VG.run_all(tmp_path))["master_size"]
    assert r["status"] == "FAIL" and r["detail"] == "wrong size"
    (tmp_path / "master.mp4").unlink()
    assert by_id(VG.run_all(tmp_path))["master_size"]["status"] == "NOT_RUN"


def test_attempt_ranking_is_review_for_the_creator_never_pass(tmp_path):
    chk = lambda cid, sev: {"check_id": cid, "rule": cid, "severity": sev, "measured": "x", "threshold": None, "passed": False}
    write(tmp_path, "qa/attempts.json", {"S01": [{"attempt": 1, "checks": [chk("A", "FAIL")]}]})
    assert by_id(VG.run_all(tmp_path))["attempt_ranking"]["status"] == "NOT_RUN"          # one attempt: nothing to rank
    write(tmp_path, "qa/attempts.json", {"S01": [{"attempt": 1, "checks": [chk("A", "FAIL")]}, {"attempt": 2, "checks": []}]})
    r = by_id(VG.run_all(tmp_path))["attempt_ranking"]
    assert r["status"] == "REVIEW" and "by eye" in r["detail"] and "attempt 2" in r["detail"]


def test_production_gate_has_the_validators_row(tmp_path):
    shutil.copy(EXAMPLES / "titans_from_zero" / "production_script.json", tmp_path / "production_script.json")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows["V"]["name"] == "validators" and rows["V"]["status"] in ("BLOCKED", "WAIT")
    assert rows["V"]["status"] != "PASS"        # nothing but the script exists, so most validators are NOT_RUN
