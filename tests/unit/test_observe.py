"""W4 (OB-1, OB-2): observation records bound to a sha256, the stage gate, the retry router's action table. No network, no paid call."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from explainer_engine.governance import records as GR
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import shot_state as SS
from explainer_engine.qa import observe as OB
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa.observers import claude_look as CL
from explainer_engine.qa.observers import ffmpeg as OF
from explainer_engine.qa.observers import gemini as GM
from explainer_engine.qa.observers import transcript as OT

SESSION = {"by": "session", "note": "looked at the sheet and the full frame"}
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _ep(tmp_path, with_clip=True):
    r = tmp_path / "ep_t"
    (r / "assets").mkdir(parents=True)
    (r / "assets" / "p.png").write_bytes(b"picture-1")
    (r / "assets" / "c.mp4").write_bytes(b"clip-1")
    st = SS.ShotStates(r)
    st.bind("S1", "image", "assets/p.png")
    if with_clip:
        st.shot("S1")["assets"]["clip"] = {"sha256": SS.sha256_of(r / "assets/c.mp4"), "path": "assets/c.mp4"}
    st.save()
    return r


def _rec(r, kind, observer, path, defects=None, reviewed=None, verdict=None):
    return OB.write(r, OB.build(r, "S1", kind, observer, path, defects=defects, reviewed=reviewed, verdict=verdict))


def test_schema_accepts_a_record_and_refuses_an_unknown_defect_code(tmp_path):
    r = _ep(tmp_path)
    rec = OB.build(r, "S1", "image", "claude", "assets/p.png")
    assert contracts.errors(rec) == []
    bad = dict(rec, defects=[{"code": "BANANA", "where": "x", "severity": "major"}])
    assert contracts.errors(bad)


def test_a_picture_without_a_record_is_blocked_and_the_shot_is_listed(tmp_path):
    r = _ep(tmp_path)
    rows = OB.gate_rows(r, "clips")
    assert rows[0]["status"] == "FAIL" and "S1: MISSING" in rows[0]["detail"]


def test_a_clip_without_a_record_is_blocked_before_assemble(tmp_path):
    r = _ep(tmp_path)
    rows = OB.gate_rows(r, "assemble")
    assert rows[0]["status"] == "FAIL" and "S1" in rows[0]["detail"]


def test_a_passing_claude_look_opens_the_picture_gate_and_moves_the_state(tmp_path):
    r = _ep(tmp_path)
    out = _rec(r, "image", "claude", "assets/p.png", reviewed=SESSION)
    assert out["settled"]["moves"] == ["IMAGE_OBSERVED", "IMAGE_ACCEPTED"]
    assert OB.gate_rows(r, "clips")[0]["status"] == "PASS"
    assert SS.ShotStates(r).state("S1") == "IMAGE_ACCEPTED"


def test_a_changed_file_loses_its_record(tmp_path):
    r = _ep(tmp_path)
    _rec(r, "image", "claude", "assets/p.png", reviewed=SESSION)
    (r / "assets" / "p.png").write_bytes(b"picture-2")
    SS.check_all(r)   # the stage start re-hashes and resets
    row = OB.gate_rows(r, "clips")
    assert row[0]["status"] in ("FAIL", "NOT_RUN")
    sha = SS.sha256_of(r / "assets/p.png")
    assert OB.asset_status(r, "S1", "image", sha)[0] == "MISSING"


def test_a_defect_makes_the_record_retry_and_blocks_the_gate(tmp_path):
    r = _ep(tmp_path)
    out = _rec(r, "image", "claude", "assets/p.png", defects=[{"code": "F8", "where": "frame", "severity": "major"}],
               reviewed=SESSION)
    assert out["verdict"] == "RETRY" and out["action"] == "R2"
    assert OB.gate_rows(r, "clips")[0]["status"] == "FAIL"


def test_a_minor_defect_is_review_and_never_a_pass(tmp_path):
    r = _ep(tmp_path)
    _rec(r, "image", "claude", "assets/p.png", defects=[{"code": "F12", "where": "frame", "severity": "minor"}], reviewed=SESSION)
    row = OB.gate_rows(r, "clips")[0]
    assert row["status"] == "REVIEW"


def test_an_automatic_pass_needs_a_look_or_an_accepted_calibration(tmp_path, monkeypatch):
    r = _ep(tmp_path)
    _rec(r, "clip", "ffmpeg", "assets/c.mp4")
    _rec(r, "clip", "claude", "assets/c.mp4", reviewed=SESSION)
    sha = SS.sha256_of(r / "assets/c.mp4")
    assert OB.asset_status(r, "S1", "clip", sha)[0] == "UNREVIEWED"
    rid = [x for x in OB.load(r) if x["observer"] == "ffmpeg"][0]["record_id"]
    OB.review(r, rid, "session", "looked at the numbers")
    assert OB.asset_status(r, "S1", "clip", sha)[0] == "PASS"
    # calibration accepted instead of a look: only by accept(), which records his word
    r2 = _ep(tmp_path / "b")
    _rec(r2, "clip", "ffmpeg", "assets/c.mp4")
    _rec(r2, "clip", "claude", "assets/c.mp4", reviewed=SESSION)
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps({"accepted": {"ffmpeg": {"message_id": "cmsg_m1", "words": "accept", "at": "x"}}}))
    monkeypatch.setattr(OB, "CALIBRATION", cal)
    monkeypatch.setattr(OB, "GOVERNANCE_ROOT", tmp_path / "gov")
    assert OB.asset_status(r2, "S1", "clip", sha)[0] == "UNREVIEWED"   # a hand-written entry does not count
    OB.accept("ffmpeg", "cmsg_m1", "accept the ffmpeg report", cal)
    assert OB.asset_status(r2, "S1", "clip", sha)[0] == "PASS"


def test_accept_needs_a_chat_id_words_and_an_automatic_observer(tmp_path, monkeypatch):
    monkeypatch.setattr(OB, "GOVERNANCE_ROOT", tmp_path / "gov")
    cal = tmp_path / "c.json"
    for args in (("ffmpeg", "m1", "ok"), ("ffmpeg", "cmsg_1", " "), ("claude", "cmsg_1", "ok")):
        with pytest.raises(ValueError):
            OB.accept(*args, cal)
    assert not OB.calibration_accepted("ffmpeg", cal)
    OB.accept("transcript", "cmsg_77", "yes, accept it", cal)
    assert OB.calibration_accepted("transcript", cal) and not OB.calibration_accepted("ffmpeg", cal)
    # a bare true, or an entry whose record was removed, does not count
    cal.write_text(json.dumps({"accepted": {"transcript": True}}))
    assert not OB.calibration_accepted("transcript", cal)


def test_a_session_review_needs_a_note_and_an_owner_review_needs_a_recorded_id(tmp_path, monkeypatch):
    monkeypatch.setattr(OB, "GOVERNANCE_ROOT", tmp_path / "gov")
    r = _ep(tmp_path)
    with pytest.raises(ValueError, match="note"):
        _rec(r, "image", "claude", "assets/p.png", reviewed={"by": "session", "note": " "})
    with pytest.raises(ValueError, match="owner review"):
        _rec(r, "image", "claude", "assets/p.png", reviewed={"by": "owner", "message_id": "cmsg_a1"})   # not recorded
    sha = SS.sha256_of(r / "assets/p.png")
    GR.add(OB.REVIEW_ACTION, f"ep_t:S1:{sha[:12]}", "cmsg_a1", "looks right", root=tmp_path / "gov")
    out = _rec(r, "image", "claude", "assets/p.png", reviewed={"by": "owner", "message_id": "cmsg_a1"})
    assert out["verdict"] == "PASS"
    with pytest.raises(ValueError, match="owner review"):
        OB.review(r, out["record_id"], "owner", "x", "cmsg_other")
    OB.review(r, out["record_id"], "session", "re-opened the sheet and the full frame")


def test_zero_bound_assets_is_not_run_and_a_state_past_the_asset_without_one_is_blocked(tmp_path):
    r = tmp_path / "ep_e"
    r.mkdir()
    row = OB.gate_rows(r, "clips")[0]
    assert row["status"] == "NOT_RUN" and "nothing was observed" in row["detail"]
    assert OB.gate_rows(r, "assemble")[0]["status"] == "NOT_RUN"
    # a shot whose state says its picture was accepted, with no picture bound
    st = SS.ShotStates(r)
    st.shot("S1")["state"] = "IMAGE_ACCEPTED"
    st.save()
    rows = OB.gate_rows(r, "clips")
    assert rows[0]["status"] == "FAIL" and "S1: state IMAGE_ACCEPTED but no image is bound" in rows[0]["detail"]
    st.shot("S1")["state"] = "VIDEO_OBSERVED"
    st.save()
    assert OB.gate_rows(r, "assemble")[0]["status"] == "FAIL"


def test_a_not_run_record_never_passes(tmp_path):
    r = _ep(tmp_path)
    _rec(r, "image", "claude", "assets/p.png", verdict="NOT_RUN", reviewed=SESSION)
    assert OB.gate_rows(r, "clips")[0]["status"] == "FAIL"


def test_the_vault_record_gets_the_observation_id(tmp_path):
    r = _ep(tmp_path)
    sha = SS.sha256_of(r / "assets/p.png")
    row = {"schema": "asset_record/1", "asset_id": "ep_t:S1:image_start:v1", "episode_id": "ep_t", "shot_id": "S1", "type": "image_start",
           "sha256": sha, "version": 1, "parent": None, "provider": None, "model": None, "prompt_hash": None, "references": [],
           "seed": None, "parameters": {}, "cost": None, "created": "x", "observation_record_id": None, "creator_approval": None}
    (r / "assets" / "asset_records.jsonl").write_text(json.dumps(row) + "\n")
    out = _rec(r, "image", "claude", "assets/p.png", reviewed=SESSION)
    saved = json.loads((r / "assets" / "asset_records.jsonl").read_text().splitlines()[0])
    assert saved["observation_record_id"] == out["record_id"] and out["asset_id"] == row["asset_id"]


# --- OB-2 ---------------------------------------------------------------------------------------------------------------
def test_the_third_generative_retry_is_refused(tmp_path):
    r = _ep(tmp_path)
    st = SS.ShotStates(r)
    sha = SS.sha256_of(r / "assets/p.png")
    st.advance("S1", "IMAGE_OBSERVED", sha, "assets/p.png")
    for _ in range(2):
        assert RR.consume_retry(st, "S1", "image") == "IMAGE_RETRY"
        st.advance("S1", "IMAGE_GENERATED", sha, "assets/p.png")
        st.advance("S1", "IMAGE_OBSERVED", sha, "assets/p.png")
    with pytest.raises(SS.ShotStateError, match="cap"):
        RR.consume_retry(st, "S1", "image")
    assert RR.decide(st, "S1", "image", ["F8"])["action"] == "ESCALATE"
    assert RR.decide(st, "S1", "clip", ["F1"])["retries_left"] == 2
    st.shot("S1")["retries"]["video"] = 2
    assert RR.decide(st, "S1", "clip", ["F1"])["action"] == "R4"


def test_every_f_code_and_tech_code_has_an_action_and_an_unknown_one_is_refused():
    for n in range(1, 20):
        assert RR.action_for_defect(f"F{n}")["action"] in ("R1", "R2", "R3")
    assert RR.action_for_defect("TXT-DUP") == {"code": "TXT-DUP", "action": "R1", "generative": False, "why": RR.R_ACTIONS["TXT-DUP"][2]}
    with pytest.raises(ContractError):
        RR.action_for_defect("F99")


def test_a_free_fix_does_not_spend_a_retry_and_never_becomes_block():
    assert OB.verdict_of([{"code": "TXT-DUP", "where": "x", "severity": "major"}], generative_left=False) == "RETRY"
    assert OB.verdict_of([{"code": "F1", "where": "x", "severity": "major"}], generative_left=False) == "BLOCK"


# --- observers -----------------------------------------------------------------------------------------------------------
def test_transcript_finds_the_duplicated_maybe_of_s06_sh008():
    words = [(" Maybe.", 0.0, 0.6), (" Maybe.", 1.72, 1.92), (" But", 2.9, 3.1), (" not", 3.1, 3.3), (" today.", 3.3, 3.54)]
    defects, _ = OT.compare("Maybe. But not today.", words)
    assert [d["code"] for d in defects] == ["TXT-DUP"]
    assert defects[0]["where"].startswith("t=0.00-1.92")


def test_transcript_flags_words_on_a_silent_beat_like_s03_sh007():
    defects, _ = OT.compare("", [(" Oh,", 0.0, 2.74), (" my", 2.9, 4.24), (" God.", 4.24, 4.24)])
    assert [d["code"] for d in defects] == ["TXT-FALSE"]


def test_transcript_accepts_an_asr_spelling_and_reports_a_missing_word():
    ok, _ = OT.compare("Stille Nacht, heilige Nacht", [(" Stilenacht,", 0, 2), (" Heiligenacht", 3, 4)][:1] + [(" Nacht", 2, 3), (" Heilige", 3, 3.5), (" Nacht", 3.5, 4)])
    assert ok == []
    miss, _ = OT.compare("Keep your head down", [(" Keep", 0, 1), (" head", 1, 2), (" down", 2, 3)])
    assert [d["code"] for d in miss] == ["TXT-MISSING"]


def test_transcript_without_words_is_not_run(tmp_path):
    r = _ep(tmp_path)
    rec = OT.observe(r, "S1", "clip", "assets/c.mp4", "x", None)
    assert rec["verdict"] == "NOT_RUN"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_ffmpeg_observer_sees_a_black_clip_and_a_good_one(tmp_path):
    r = tmp_path / "ep_t"
    r.mkdir()
    for name, src in (("black.mp4", "color=c=black:s=64x64:d=2:r=24"), ("moving.mp4", "testsrc2=s=64x64:d=2:r=24")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-pix_fmt", "yuv420p", str(r / name)], check=True)
    bad = OF.observe(r, "S1", "clip", "black.mp4", scenes=False)
    assert "TECH-BLACK" in [d["code"] for d in bad["defects"]] and bad["verdict"] == "RETRY"
    good = OF.observe(r, "S2", "clip", "moving.mp4", scenes=False)
    assert good["verdict"] in ("PASS", "REVIEW") and "TECH-BLACK" not in [d["code"] for d in good["defects"]]


def test_ffmpeg_observer_reports_a_corrupt_file(tmp_path):
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    r = tmp_path / "ep_t"
    r.mkdir()
    (r / "bad.mp4").write_bytes(b"not a video at all")
    rec = OF.observe(r, "S1", "clip", "bad.mp4", scenes=False)
    assert rec["verdict"] in ("RETRY", "NOT_RUN")


def test_claude_look_record_refuses_an_unknown_code_and_takes_the_session_answers(tmp_path):
    r = _ep(tmp_path)
    with pytest.raises(ContractError):
        CL.record(r, "S1", "image", "assets/p.png", {"answers": {}, "defects": [{"code": "Z9", "where": "f", "severity": "major"}]})
    out = CL.record(r, "S1", "image", "assets/p.png", {"answers": {"people?": "0"}, "defects": []})
    assert out["verdict"] == "PASS" and out["reviewed"]["by"] == "session"


def test_gemini_chat_task_and_ingest(tmp_path, monkeypatch):
    monkeypatch.setattr(OB, "GOVERNANCE_ROOT", tmp_path / "gov")
    r = _ep(tmp_path)
    task = GM.chat_task(r, [{"shot": "S1", "kind": "clip", "path": "assets/c.mp4", "questions": ["Does the handshake hold?"]}], tmp_path / "t.md")
    assert "assets/c.mp4" in task.read_text() and "Does the handshake hold?" in task.read_text()
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps({"shots": {"S1": {"answers": {"q": "no"}, "defects": [
        {"code": "F5", "where": "t=2.6-4.0s", "severity": "major"}, {"code": "WAT", "where": "x", "severity": "major"}]}}}))
    out = GM.ingest_chat(r, ans, {"S1": ("clip", "assets/c.mp4")}, message_id="cmsg_m9")
    assert out[0]["verdict"] == "RETRY" and out[0]["action"] == "R3" and "unknown code" in out[0]["note"]
    assert out[0]["reviewed"] is None and "owner stamp refused" in out[0]["note"]   # his id is not recorded
    sha = SS.sha256_of(r / "assets/c.mp4")
    GR.add(OB.REVIEW_ACTION, f"ep_t:S1:{sha[:12]}", "cmsg_m9", "ran the chat", root=tmp_path / "gov")
    out = GM.ingest_chat(r, ans, {"S1": ("clip", "assets/c.mp4")}, message_id="cmsg_m9")
    assert out[0]["reviewed"]["by"] == "owner"


def test_gemini_api_without_a_client_is_not_run_and_a_mock_client_is_parsed(tmp_path):
    r = _ep(tmp_path)
    assert GM.GeminiApiObserver().observe(r, "S1", "clip", "assets/c.mp4", ["q"])["verdict"] == "NOT_RUN"

    class Mock:
        calls = []

        def generate(self, prompt, path, fps):
            self.calls.append(fps)
            return json.dumps({"shots": {"S1": {"answers": {"q": "yes"}, "defects": []}}})

    m = Mock()
    out = GM.GeminiApiObserver(m, fps=2.0, raw_dir=tmp_path / "raw").observe(r, "S1", "clip", "assets/c.mp4", ["q"])
    assert m.calls == [2.0] and out["verdict"] == "PASS" and (tmp_path / "raw" / "S1_clip_gemini_raw.json").is_file()
    assert OB.asset_status(r, "S1", "clip", SS.sha256_of(r / "assets/c.mp4"))[0] == "MISSING"   # the ffmpeg group is still missing


def test_run_stage_calls_the_gate_before_clips_and_assemble():
    src = (OB.ROOT / "explainer_engine" / "episode" / "run.py").read_text(encoding="utf-8")
    assert "OBS.gate_rows(ep.root, stage)" in src and src.index("OBS.gate_rows") < src.index("STAGE_FUNCS[stage](ep, rehearsal)")
    assert set(OB.STAGE_KIND) == {"clips", "assemble"}


def test_the_documented_action_table_equals_the_router_table():
    doc = (OB.ROOT / "docs" / "OBSERVATION.md").read_text(encoding="utf-8")
    for code, (action, gen, _why) in RR.R_ACTIONS.items():
        assert f"| `{code}` | {action} | {'yes' if gen else 'no'} |" in doc, code


def test_calibration_counts_and_expected_text():
    from explainer_engine.qa.observers import calibration as CAL
    t = CAL.tally({"a": True, "b": True, "c": False, "d": False}, {"a": True, "b": False, "c": True, "d": False})
    assert t == {"TP": ["a"], "FN": ["b"], "FP": ["c"], "TN": ["d"]}
    plan = {"shots": [{"shot": "S1", "lines": [["thomas", "Maybe. But not today."]]}, {"shot": "S2", "lines": [["none", "(they shake hands)"]]}]}
    assert CAL.expected_text(plan, "S1") == "Maybe. But not today." and CAL.expected_text(plan, "S2") == ""


def test_the_calibration_config_starts_with_no_accepted_observer():
    cfg = json.loads((OB.ROOT / "config" / "observer_calibration.json").read_text(encoding="utf-8"))
    assert cfg["accepted"] == {} and not OB.calibration_accepted("ffmpeg")


def test_run_stage_blocks_clips_on_an_unobserved_picture_and_runs_after_a_record(tmp_path, monkeypatch):
    from explainer_engine.episode import run as RUN
    from tests.unit.test_qa_status import _episode, _fake
    called = []

    def fake(stage):
        def fn(ep, rehearsal):
            called.append(stage)
            return [RUN.G.row(f"{stage}_ran", True, "ok")], {}
        return fn
    monkeypatch.setattr(RUN, "STAGE_FUNCS", {s: fake(s) for s in RUN.STAGES})
    root = _episode(tmp_path)
    (root / "assets").mkdir()
    (root / "assets" / "p.png").write_bytes(b"picture-1")
    st = SS.ShotStates(root)
    st.bind("S1", "image", "assets/p.png")
    st.save()
    ep = RUN.Episode(root)
    for stage in ("script", "sound_plan", "pictures", "voice"):
        RUN.run_stage(ep, stage)
    called.clear()
    rec = RUN.run_stage(ep, "clips")
    assert called == [] and rec["verdict"]["status"] == "FAIL" and "S1: MISSING" in rec["rows"][0]["detail"]
    OB.write(root, OB.build(root, "S1", "image", "claude", "assets/p.png", reviewed=SESSION))
    rec = RUN.run_stage(RUN.Episode(root, force=True), "clips")
    assert called == ["clips"] and rec["verdict"]["status"] == "PASS"
