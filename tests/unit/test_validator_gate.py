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
       "language", "master_size", "attempt_ranking", "first_shot"]
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
    assert status == "WAIT" and f"0 of {len(IDS)} ran" in detail
    assert VG.main([str(tmp_path)]) == 2


def test_each_validator_is_called_from_the_gate(tmp_path, monkeypatch):
    """Every registered runner is invoked by run_all, with the episode folder."""
    seen = []
    fake = [(rid, (lambda d, rid=rid: seen.append((rid, d)) or VG._row(rid, rid, "PASS", "ok"))) for rid in IDS]
    monkeypatch.setattr(VG, "REGISTRY", fake)
    rows = VG.run_all(tmp_path)
    assert [s[0] for s in seen] == IDS and all(s[1] == tmp_path for s in seen) and len(rows) == len(IDS)


def test_gate_row_folds_statuses(tmp_path, monkeypatch):
    def reg(*statuses):
        return [(rid, (lambda d, rid=rid, st=st: VG._row(rid, rid, st, "x"))) for rid, st in zip(IDS, statuses)]
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * len(IDS)))
    assert VG.gate_row(tmp_path)[0] == "PASS"
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * (len(IDS) - 1), "REVIEW"))
    assert VG.gate_row(tmp_path)[0] == "PASS"
    monkeypatch.setattr(VG, "REGISTRY", reg(*["PASS"] * (len(IDS) - 1), "NOT_RUN"))
    status, detail, _ = VG.gate_row(tmp_path)
    assert status == "WAIT" and IDS[-1] in detail
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


def test_camera_cards_read_the_scripts_shots_and_say_when_none_declares_a_move(tmp_path):
    write(tmp_path, "production_script.json", {"shots": [{"id": "S01_SH001"}]})
    r = by_id(VG.run_all(tmp_path))["camera_cards"]
    assert r["status"] == "NOT_RUN" and "camera_move" in r["detail"]
    write(tmp_path, "story/production_script.json", {"shots": [{"id": "S01_SH001", "camera_move": "orbit"}]})
    (tmp_path / "production_script.json").unlink()
    r = by_id(VG.run_all(tmp_path))["camera_cards"]
    assert r["status"] == "FAIL" and "CM-02" in r["detail"]


def test_shots_inside_segments_count_too_and_creator_records_are_not_viewer_text(tmp_path):
    write(tmp_path, "production_script.json", {"segments": [{"id": "S01", "lines": [{"text": "Hi."}], "shots": [{"id": "S01_SH001", "camera_move": "orbit"}]}]})
    assert by_id(VG.run_all(tmp_path))["camera_cards"]["status"] == "FAIL"
    write(tmp_path, "publish/youtube_state.json", {"confirmed_by": "creator " + GEO})      # the creator's own record: not scanned
    write(tmp_path, "narration.txt", "English only.")
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "PASS"


def test_language_reads_the_scripts_spoken_text_not_its_approval_records(tmp_path):
    doc = json.loads((EXAMPLES / "titans_from_zero" / "production_script.json").read_text(encoding="utf-8"))
    assert GEO in json.dumps(doc, ensure_ascii=False)          # the creator's name is in the file, in an approval record
    write(tmp_path, "production_script.json", doc)
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "PASS"       # the creator's name sits in approved_by only
    doc["segments"][0]["lines"][0]["text"] = "Spoken " + GEO
    write(tmp_path, "production_script.json", doc)
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "FAIL"


def test_language_reads_the_viewer_fields_of_publish_json_not_the_approval(tmp_path):
    pub = {"schema": "publish/1", "title": "A title", "description": "d", "chapters": [{"t": "0:00", "title": "One"}],
           "approval": {"by": "vano1919 (" + GEO + ")"}}
    write(tmp_path, "publish.json", pub)
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "PASS"
    pub["chapters"][0]["title"] = "Chapter " + GEO
    write(tmp_path, "publish.json", pub)
    r = by_id(VG.run_all(tmp_path))["language"]
    assert r["status"] == "FAIL" and "publish.json" in r["detail"]


def test_camera_clips_take_the_move_from_the_script_or_a_sidecar(tmp_path, monkeypatch):
    from explainer_engine.qa import camera_move
    clip = tmp_path / "ltx" / "S06_SH009_seed7100.mp4"
    clip.parent.mkdir()
    clip.write_bytes(b"x")
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "NOT_RUN"             # no declared move anywhere
    calls = []
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, m=None, **k: calls.append((p.name, m)) or {"status": "FAIL", "detail": "static"})
    write(tmp_path, "production_script.json", {"shots": [{"id": "S06_SH009", "camera_move": "zoom_in"}]})
    r = by_id(VG.run_all(tmp_path))["camera_clips"]
    assert r["status"] == "FAIL" and "S06_SH009_seed7100.mp4" in r["detail"] and calls == [("S06_SH009_seed7100.mp4", "zoom_in")]
    (tmp_path / "production_script.json").unlink()
    write(tmp_path, "ltx/S06_SH009_seed7100.mp4.camera.json", {"camera_move": "zoom_in"})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "FAIL"                # the sidecar declares it
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, m=None, **k: {"status": "PASS", "detail": ""})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "PASS"
    monkeypatch.setattr(camera_move, "camera_move_clip", lambda p, m=None, **k: {"status": "NOT_RUN", "detail": "floor OPEN"})
    assert by_id(VG.run_all(tmp_path))["camera_clips"]["status"] == "NOT_RUN"


def _prompts(day, text):
    write(day, "prompts.json", {"shots": [{"id": "S01-01.first", "kind": "keyframe", "prompt": "Static camera"},
                                          {"id": "S01-01.video", "kind": "video", "prompt": text},
                                          {"id": "S01-02.video", "kind": "reuse", "of": "S01-01.video"}]})


def test_ltx_prompts_lint_only_video_prompts_and_a_clean_one_is_review_not_pass(tmp_path):
    _prompts(tmp_path, "Drumstick strikes the drum while the camera trucks left across the fog")
    r = by_id(VG.run_all(tmp_path))["ltx_prompts"]
    assert r["status"] == "REVIEW" and "LP-05" in r["detail"] and "LP-06" in r["detail"] and "1 prompts" in r["detail"]


def test_ltx_prompts_report_the_real_defects(tmp_path):
    _prompts(tmp_path, "The drumstick strikes the drum. Static camera.\nA second paragraph.")
    r = by_id(VG.run_all(tmp_path))["ltx_prompts"]
    assert r["status"] == "FAIL" and "S01-01.video" in r["detail"] and "LP-01" in r["detail"]


def test_continuity_cards_are_found_by_schema_and_checked_with_the_episode_film(tmp_path):
    card = json.loads((EXAMPLES / "continuity" / "napoleon_tent.json").read_text(encoding="utf-8"))
    write(tmp_path, "cards/s04.json", card)
    write(tmp_path, "cards/not_a_card.json", {"schema": "something/1"})
    assert by_id(VG.run_all(tmp_path))["continuity_cards"]["status"] == "PASS"
    card["film_id"] = "wrong_film"
    for c in card["cast"].values():
        c["identity"] = {"canon_frame": "c.png", "locked": ["jaw"]}
    write(tmp_path, "cards/s04.json", card)
    film(tmp_path)
    r = by_id(VG.run_all(tmp_path))["continuity_cards"]
    assert r["status"] == "FAIL" and "CT-17" in r["detail"]


def test_language_fails_on_georgian_in_viewer_text(tmp_path):
    write(tmp_path, "narration.txt", "A fine English line.")
    assert by_id(VG.run_all(tmp_path))["language"]["status"] == "PASS"
    write(tmp_path, "metadata.md", "Title " + GEO)
    r = by_id(VG.run_all(tmp_path))["language"]
    assert r["status"] == "FAIL" and "metadata.md" in r["detail"]


def test_master_size_through_the_gate(tmp_path, monkeypatch):
    (tmp_path / "render").mkdir()
    (tmp_path / "render" / "video.mp4").write_bytes(b"x")
    from explainer_engine.qa import master_size
    monkeypatch.setattr(master_size, "check_master_size", lambda p, d=None: {"status": "FAIL", "value": "1x1", "detail": "wrong size"})
    r = by_id(VG.run_all(tmp_path))["master_size"]
    assert r["status"] == "FAIL" and r["detail"] == "wrong size"
    (tmp_path / "render" / "video.mp4").unlink()
    assert by_id(VG.run_all(tmp_path))["master_size"]["status"] == "NOT_RUN"


def test_attempt_ranking_needs_checks_in_the_ledger_rows_and_is_review_never_pass(tmp_path):
    chk = lambda cid, sev: {"check_id": cid, "rule": cid, "severity": sev, "measured": "x", "threshold": None, "passed": False}
    rows = [{"n": 1, "escalated": False, "cause": "a"}, {"n": 2, "escalated": False, "cause": "b"}]
    write(tmp_path, "jobs/S01/attempts.json", rows)                    # what core/ledger.Attempts writes today: no checks
    r = by_id(VG.run_all(tmp_path))["attempt_ranking"]
    assert r["status"] == "NOT_RUN" and "cause only" in r["detail"]
    rows[0]["checks"], rows[1]["checks"] = [chk("A", "FAIL")], []
    write(tmp_path, "jobs/S01/attempts.json", rows)
    r = by_id(VG.run_all(tmp_path))["attempt_ranking"]
    assert r["status"] == "REVIEW" and "by eye" in r["detail"] and "attempt 2" in r["detail"]


def test_production_gate_has_the_validators_row(tmp_path):
    shutil.copy(EXAMPLES / "titans_from_zero" / "production_script.json", tmp_path / "production_script.json")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows["V"]["name"] == "validators" and rows["V"]["status"] in ("BLOCKED", "WAIT")
    assert rows["V"]["status"] != "PASS"        # nothing but the script exists, so most validators are NOT_RUN


def timed_doc(first_len):
    return {"duration": 60.0, "shots": [{"start": 0.0, "end": first_len}, {"start": first_len, "end": 60.0}]}


def test_first_shot_runs_on_a_timed_json(tmp_path):
    assert by_id(VG.run_all(tmp_path))["first_shot"]["status"] == "NOT_RUN"
    write(tmp_path, "timed.json", timed_doc(1.0))
    r = by_id(VG.run_all(tmp_path))["first_shot"]
    assert r["status"] == "FAIL" and "flash" in r["detail"]
    assert VG.gate_row(tmp_path)[0] == "BLOCKED"
    write(tmp_path, "timed.json", timed_doc(3.0))
    assert by_id(VG.run_all(tmp_path))["first_shot"]["status"] == "PASS"
