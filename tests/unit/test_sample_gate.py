"""The two-part sample gate (OR-19, D-64; creator 2026-10-21): after the script approval, paid voice and pictures run for
the first two segments only; the creator watches the stitched sample and his recorded word opens the rest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_production_script import mini

from explainer_engine.production import compile as C
from explainer_engine.production import sample as SMP
from explainer_engine.production import script as S
from explainer_engine.standards import hook


def three_parts() -> dict:
    """mini() plus a third segment with its own picture and one shared picture (valley is also in S01)."""
    doc = mini()
    doc["segments"].append({
        "id": "S03", "beat": "dawn", "light_beat": 5,
        "lines": [{"text": "By morning the fire is ash, and the valley is quiet again."}],
        "shots": [{"at": "By morning", "type": "A", "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0},
                   "picture": {"id": "ash_pit", "subject": "a cold ash pit at dawn in the quiet valley"}},
                  {"at": "the valley", "type": "A", "picture": "valley", "reuse": "reframe",
                   "motion": {"kind": "push", "z0": 1.0, "z1": 1.04}}]})
    return C.compile_doc(doc)


def episode(tmp_path: Path) -> tuple[Path, dict]:
    doc = three_parts()
    S.save(doc, tmp_path / "production_script.json")
    return tmp_path, doc


def test_scope_is_the_first_two_segments_and_the_file_can_widen_it(tmp_path):
    ep, doc = episode(tmp_path)
    assert SMP.scope_segments(doc, ep) == ["S01", "S02"]
    (ep / SMP.FILE).write_text(json.dumps({"scope_segments": ["S01", "S02", "S03"]}), encoding="utf-8")
    assert SMP.scope_segments(doc, ep) == ["S01", "S02", "S03"]


def test_scope_pictures_keep_shared_pictures_and_drop_the_rest(tmp_path):
    ep, doc = episode(tmp_path)
    pics = SMP.scope_pictures(doc, folder=ep)
    assert {"valley", "cold_hands", "duo", "camp"} <= pics  # valley is shared with S03 and the sample still needs it
    assert "ash_pit" not in pics


def test_a_sample_read_is_in_scope_and_the_rest_of_the_video_is_not(tmp_path):
    ep, doc = episode(tmp_path)
    for chunk in S.tts_chunks(doc, max_chars=1):  # the real reads, with tags, capitals and pause tags
        assert SMP.speech_in_scope(chunk["text"], doc, ep) == (set(chunk["segments"]) <= {"S01", "S02"})
    whole = S.tts_chunks(doc)[0]  # a chunk that runs past the sample is refused with the rest
    assert "S03" in whole["segments"] and not SMP.speech_in_scope(whole["text"], doc, ep)
    assert not SMP.speech_in_scope("", doc, ep)
    assert not SMP.speech_in_scope("A completely different script.", doc, ep)


def test_check_plan_fails_pictures_outside_the_sample_until_the_creators_word(tmp_path):
    ep, doc = episode(tmp_path)
    script = ep / "production_script.json"
    plan = {"id": "B9", "items": [{"id": "ash_pit"}, {"id": "camp"}]}
    found = SMP.check_plan(plan, doc, script)
    assert [f["rule"] for f in found] == ["PP-09"] and "ash_pit" in found[0]["detail"] and "camp" not in found[0]["detail"]
    assert SMP.check_plan({"id": "B1", "items": [{"id": "camp"}, {"id": "duo"}]}, doc, script) == []
    assert SMP.check_plan(dict(plan, reusable=True), doc, script) == []  # channel assets stay allowed
    assert SMP.check_plan(dict(plan, faces_saving={"close_ups": 10}), doc, script) == []  # face sheets too
    SMP.approve(ep, by="creator", ref="cmsg_yes", video="sample.mp4")
    assert SMP.check_plan(plan, doc, script) == []


def test_the_approval_is_bound_to_the_script_hash(tmp_path):
    ep, doc = episode(tmp_path)
    rec = SMP.approve(ep, by="creator", ref="cmsg_yes")
    assert rec["scope_segments"] == ["S01", "S02"]
    assert SMP.approved(ep)[0]
    doc["segments"][0]["lines"][0]["text"] = "Could they survive the storm?"
    S.save(doc, ep / "production_script.json")
    ok, why = SMP.approved(ep)
    assert not ok and "changed after the sample approval" in why
    status, detail, _ = SMP.gate_row(ep)
    assert status == "WAIT" and "changed after" in detail


def test_the_hook_refuses_a_paid_read_outside_the_sample(tmp_path):
    ep, doc = episode(tmp_path)
    chunks = S.tts_chunks(doc, max_chars=1)  # one chunk per segment: a real sample read chunks the scope alone
    inside = next(c for c in chunks if set(c["segments"]) <= {"S01", "S02"})
    outside = next(c for c in chunks if "S03" in c["segments"])
    assert SMP.hook_speech("creative_generate_speech", {"text": inside["text"]}, ep) is None
    deny = SMP.hook_speech("creative_generate_speech", {"text": outside["text"]}, ep)
    assert deny and "OR-19" in deny and "S01, S02" in deny
    assert SMP.hook_speech("creative_generate_in_flow", {"text": outside["text"]}, ep) is None  # speech only
    SMP.approve(ep, by="creator", ref="cmsg_yes")
    assert SMP.hook_speech("creative_generate_speech", {"text": outside["text"]}, ep) is None
    assert SMP.hook_speech("creative_generate_speech", {"text": "anything"}, tmp_path / "no_script") is None


def test_the_hook_wiring_reaches_the_sample_gate(tmp_path, monkeypatch):
    """hook.decide ends on the sample check once the rulebook and editorial gates pass (fakes keep the test focused)."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/active_episode.json").write_text(json.dumps({"episode": "ep"}), encoding="utf-8")
    ep = tmp_path / "ep"
    ep.mkdir()
    (ep / "episode_rules.json").write_text("{}", encoding="utf-8")
    episode(ep)
    from explainer_engine.production import editorial_gate as EG
    from explainer_engine.standards import rulebook as R
    monkeypatch.setattr(R, "gate", lambda *a, **k: [])
    monkeypatch.setattr(EG, "check", lambda *a, **k: [])
    doc = S.load(ep / "production_script.json")
    outside = next(c for c in S.tts_chunks(doc) if "S03" in c["segments"])
    deny = hook.decide("mcp__ElevenLabs__creative_generate_speech", {"generations_count": 1, "text": outside["text"]}, tmp_path)
    assert deny and "OR-19" in deny
    SMP.approve(ep, by="creator", ref="cmsg_yes")
    assert hook.decide("mcp__ElevenLabs__creative_generate_speech",
                       {"generations_count": 1, "text": outside["text"]}, tmp_path) is None


def test_the_gate_and_cli_report_the_sample_state(tmp_path, capsys):
    ep, doc = episode(tmp_path)
    from explainer_engine import production_gate as G
    rows = {r["gate"]: r for r in G.gates(ep)}
    assert rows[6.5]["status"] == "WAIT" and "S01, S02" in rows[6.5]["detail"]
    assert "sample approval (6.5)" in rows[7]["detail"]
    assert SMP.main(["status", str(ep)]) == 1
    assert SMP.main(["approve", str(ep), "--by", "creator", "--ref", "cmsg_yes"]) == 0
    assert SMP.main(["status", str(ep)]) == 0
    assert {r["gate"]: r for r in G.gates(ep)}[6.5]["status"] == "PASS"
    out = capsys.readouterr().out
    assert "approved by creator" in out


def test_paint_plan_sample_keeps_only_the_samples_pictures(tmp_path, capsys):
    from explainer_engine.production import paint
    ep, doc = episode(tmp_path)
    script = ep / "production_script.json"
    assert paint.main(["plan", str(script), "--out", str(ep / "pics"), "--id", "B1", "--provider", "gemini",
                       "--model", "gemini-nano-banana-2.1", "--size", "2K", "--purpose", "sample", "--sample"]) == 0
    plan = json.loads((ep / "pics" / "plans" / "B1.json").read_text(encoding="utf-8"))
    ids = {i["id"] for i in plan["items"]}
    assert "ash_pit" not in ids and "cold_hands" in ids
