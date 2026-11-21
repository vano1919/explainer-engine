"""The creator's seven answers of 2026-11-13 to the Fable audit's questions (D-138), as gates: Q3 the hero face binds and the
costume warns (with the eye check the palette needs), Q4 a measured read before every paid LTX scene, Q5 one fixed voice
text per character in every prompt. Q1, Q2, Q6 and Q7 are in test_creator_open_questions / test_clip_audio_layer."""
from __future__ import annotations

import json
import math
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.core import open_questions as OQ
from explainer_engine.core.errors import ContractError
from explainer_engine.qa import gates as G
from explainer_engine.videolane import identity as ID
from explainer_engine.videolane import line_reads as LR
from explainer_engine.videolane import plan as P
from explainer_engine.videolane import scene as SC
from explainer_engine.videolane import storyboard as SB
from tests.unit import test_videolane as TV

ROOT = Path(__file__).resolve().parents[2]
BATTLE = Path("/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12/ltx_battle_test/battle_scene_joined_2k.mp4")


def _board(tmp_path, reads=True):
    doc = TV._scene()
    root, pics = TV._board_episode(tmp_path, doc)
    if reads:
        TV._reads(root, doc)
    SB.build(root, doc, [s["shot_id"] for s in doc["shots"]], "s1", pictures=pics)
    return doc, root


# ---- Q4: the read first, a hard gate --------------------------------------------------------------------------------------

def test_q4_a_scene_without_a_measured_read_is_refused(tmp_path):
    doc, root = _board(tmp_path, reads=False)
    assert OQ.value("Q4") == "forced"
    with pytest.raises(ContractError, match=r"Q4 = forced: 4 video shot\(s\) have no measured time"):
        SC.build(root, doc, "s1", tmp_path / "scene.json")


def test_q4_the_paid_launch_refuses_a_scene_sized_from_the_script(tmp_path):
    doc, root = _board(tmp_path)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json", budget={"usd": 1}, ledger={"path": "x"})
    assert {r["seconds_basis"] for r in scene["shots"]} <= set(P.MEASURED_BASES)
    scene["shots"][0]["seconds_basis"] = "planned_length"          # a hand-edited file
    assert any("Q4 = forced" in w for w in SC.storyboard_problems(scene))


def test_q4_a_line_read_is_measured_and_a_changed_file_no_longer_counts(tmp_path):
    rate = 16000
    t = np.arange(int(rate * 2.0)) / rate
    x = np.zeros_like(t)
    on = (t >= 0.5) & (t < 1.7)                                     # 1.2 s of speech-band tone between silences
    x[on] = 0.4 * np.sin(2 * math.pi * 700 * t[on])
    f = tmp_path / "L1.wav"
    with wave.open(str(f), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    doc = TV._scene()
    rec = LR.measure(tmp_path, doc, {"L1": f}, "tts")
    assert rec["lines"]["L1"]["seconds"] == pytest.approx(1.2, abs=0.08) and rec["lines"]["L1"]["source"] == "tts"
    assert LR.seconds_by_line(tmp_path) == {"L1": rec["lines"]["L1"]["seconds"]}
    f.write_bytes(f.read_bytes() + b"\0\0")
    assert LR.seconds_by_line(tmp_path) == {}
    with pytest.raises(ContractError, match="not a character line"):
        LR.measure(tmp_path, doc, {"L3": f}, "tts")
    s = doc["shots"][2]
    got = P.clip_seconds(doc, s, 10.0, measured_line_s=1.2)
    assert got["basis"] == "measured_line" and got["speech_s"] == 1.2


# ---- Q5: one voice text per character ------------------------------------------------------------------------------------

def test_q5_the_voice_card_names_four_facets_found_in_the_one_text():
    doc = TV._scene()
    assert SC.voice_card_problems(doc, ["gen", "cmd"]) == []
    doc["world_bible"]["characters"][0]["voice_card"].pop("accent")
    doc["world_bible"]["characters"][1]["voice_card"]["pace"] = "slow and lazy"
    got = SC.voice_card_problems(doc, ["gen", "cmd"])
    assert "gen: the voice card has no accent" in got[1] and "cmd: the voice text does not carry its card's pace" in got[0]


def test_q5_the_same_text_in_every_prompt_and_every_scene(tmp_path):
    doc, root = _board(tmp_path)
    out = tmp_path / "scenes" / "s1.json"
    scene = SC.build(root, doc, "s1", out, budget={"usd": 1}, ledger={"path": "x"})
    text = doc["world_bible"]["characters"][0]["voice_description"]
    assert scene["voices"]["gen"]["description"] == text and scene["voice_problems"] == []
    row = next(r for r in scene["shots"] if (r.get("line") or {}).get("speaker") == "gen")
    assert f"in {text}:" in row["motion_prompt"]
    row["prompt_parts"]["speech"] = row["prompt_parts"]["speech"].replace("hoarse", "rough")   # a tampered prompt
    assert any("word for word (Q5)" in w for w in SC.storyboard_problems(scene))
    # the card changes after a first scene file: the next scene file of the episode is refused until both match
    doc["world_bible"]["characters"][0]["voice_description"] = text.replace("slow", "slow, very slow")
    s2 = SC.build(root, doc, "s1", tmp_path / "scenes" / "s2.json", budget={"usd": 1}, ledger={"path": "x"})
    assert any("differs from the one in s1.json" in w for w in s2["voice_problems"])
    assert any("voice cards (Q5)" in w for w in SC.storyboard_problems(s2))


def test_q5_toba_cards_hold():
    doc = json.loads((ROOT / "episodes/ep_toba/story/production_script.json").read_text("utf-8"))
    speakers = {ln["speaker_id"] for ln in doc["audio_lines"] if ln.get("speaker_type") == "character"}
    assert speakers and SC.voice_card_problems(doc, speakers) == []


# ---- Q3: the face binds, the costume warns ----------------------------------------------------------------------------

def _two(size_b="medium", ids=("gen",)):
    sh = lambda sid, size: {"shot_id": sid, "camera_spec": {"shot_size": size}, "character_ids": list(ids),
                            "edit_plan": {"screen_positions": {h: "left" for h in ids}}}
    return {"shots": [sh("A", "medium"), sh("B", size_b)]}


def test_q3_a_costume_change_seen_by_eye_is_a_warning_and_an_unlooked_cut_never_passes():
    doc = _two()
    same = (np.full((90, 160, 3), 120, np.uint8),) * 2
    frames = {"A": same, "B": same}
    rows = {r["gate"]: r for r in ID.rows(doc, ["A", "B"], frames, {}, {}, "storyboard")}
    assert rows["storyboard_hero_costume_holds"]["status"] == G.REVIEW and "wait for the eye check" in \
        rows["storyboard_hero_costume_holds"]["detail"]
    review = {"schema": ID.REVIEW_SCHEMA, "cuts": {"A->B": {"same_headgear": False, "same_props": True,
                                                               "same_clothes": True, "note": "a crest appears"}}}
    rows = {r["gate"]: r for r in ID.rows(doc, ["A", "B"], frames, {}, {}, "storyboard", review=review)}
    cost = rows["storyboard_hero_costume_holds"]
    assert cost["status"] == G.REVIEW and "A->B: headgear changed by eye (a crest appears)" in cost["measured"]
    review["cuts"]["A->B"]["same_headgear"] = True
    rows = {r["gate"]: r for r in ID.rows(doc, ["A", "B"], frames, {}, {}, "storyboard", review=review)}
    assert rows["storyboard_hero_costume_holds"]["status"] == G.PASS


def test_q3_wide_shots_and_heroes_facing_away_are_not_face_judged(monkeypatch, tmp_path):
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    model = tmp_path / "yunet.onnx"
    model.write_bytes(b"x")
    ref = tmp_path / "gen.jpg"
    ref.write_bytes(b"x")
    monkeypatch.setattr(PX, "YUNET", model)
    monkeypatch.setattr(FP, "recognizer", lambda: object())
    monkeypatch.setattr(FP, "detect", lambda p, m, r: [{"_emb": 1}])
    monkeypatch.setattr(FP, "identify", lambda faces, refs, rec, heroes: {})          # nobody named
    pics = {"A": tmp_path / "a.png", "B": tmp_path / "b.png"}
    assert ID.face_findings(_two(), ["A", "B"], pics, {"gen": ref}) == ["A: gen's face is not found",
                                                                          "B: gen's face is not found"]
    assert ID.face_findings(_two("wide"), ["A", "B"], pics, {"gen": ref}) == ["A: gen's face is not found"]
    assert ID.face_findings(_two(), ["A", "B"], pics, {"gen": ref}, {"B": {"gen": "away"}}) == ["A: gen's face is not found"]
    rows = {r["gate"]: r for r in ID.rows(_two(), ["A", "B"], {}, pics, {"gen": ref}, "storyboard")}
    assert rows["storyboard_hero_face_holds"]["status"] == G.FAIL                      # Q3: the face binds


def test_q3_a_paid_scene_is_refused_while_the_binding_face_is_not_measured(tmp_path):
    doc, root = _board(tmp_path)
    draft = SC.build(root, doc, "s1", tmp_path / "scene.json")
    assert not any("face" in w for w in SC.storyboard_problems(draft))                 # a draft says only it is a draft
    paid = SC.build(root, doc, "s1", tmp_path / "scene2.json", budget={"usd": 1}, ledger={"path": "x"})
    assert any("hero face binding" in w for w in SC.storyboard_problems(paid))


@pytest.mark.skipif(not BATTLE.is_file(), reason="the 11-12 battle file lives in the project files")
def test_q3_on_the_11_12_battle_the_helmet_is_a_warning(tmp_path):
    """The real battle of 2026-11-12: the palette does not see the general's helmet at cut 1 (head box under BP-166's 0.15),
    the eye check names it and the row is a warning (REVIEW), not a stop."""
    scene = {"shots": [
        {"shot_id": "c1", "camera_spec": {"shot_size": "wide"}, "character_ids": ["gen", "cmd"],
         "edit_plan": {"screen_positions": {"gen": "centre", "cmd": "centre"}}},
        {"shot_id": "c2", "camera_spec": {"shot_size": "medium"}, "character_ids": ["gen", "cmd"],
         "edit_plan": {"screen_positions": {"gen": "left", "cmd": "right"}}},
        {"shot_id": "c3", "camera_spec": {"shot_size": "medium_wide"}, "character_ids": ["gen", "cmd"],
         "edit_plan": {"screen_positions": {"gen": "left", "cmd": "right"}}, "facing": {"gen": "away", "cmd": "away"}},
        {"shot_id": "c4", "camera_spec": {"shot_size": "wide"}, "character_ids": [], "edit_plan": {}}]}
    rec = ID.check_joined(BATTLE, [160, 250, 442], scene, tmp_path)
    cost = next(r for r in rec["rows"] if r["gate"] == "clip_hero_costume_holds")
    assert cost["status"] == G.REVIEW and "wait for the eye check" in cost["detail"]  # the palette alone sees nothing
    review = {"schema": ID.REVIEW_SCHEMA, "cuts": {
        "c1->c2": {"same_headgear": False, "same_props": False, "same_clothes": True, "note": "the general's crest"},
        "c2->c3": {"same_headgear": True, "same_props": True, "same_clothes": True}}}
    rec = ID.check_joined(BATTLE, [160, 250, 442], scene, tmp_path, review=review)
    cost = next(r for r in rec["rows"] if r["gate"] == "clip_hero_costume_holds")
    assert cost["status"] == G.REVIEW and rec["verdict"]["status"] != G.FAIL
    assert Path(rec["sheet"]).is_file()
