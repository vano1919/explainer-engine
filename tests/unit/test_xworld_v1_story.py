import json
from pathlib import Path

import pytest

from explainer_engine.training.pods import xworld_v1_story as st

STORY = Path(st.__file__).parent / "stories" / "napoleon_tent.json"


def _story():
    return json.loads(STORY.read_text(encoding="utf-8"))


def test_frame_zero_is_text_only_and_the_rest_use_the_winning_d_form():
    j = {x["name"]: x for x in st.jobs(_story())}
    assert j["lora_A0"]["ref"] is None and j["lora_A0"]["prompt"].startswith("xworld style, Inside")
    assert j["lora_A2"]["ref"] == "lora_A0"
    assert "Keep everything else the same." in j["lora_A2"]["prompt"]
    assert "Change from the previous shot:" in j["lora_A2"]["prompt"]


def test_text_master_branch_redraws_the_master_from_text_and_its_shots_follow_it():
    j = {x["name"]: x for x in st.jobs(_story())}
    assert j["lora_B1"]["ref"] == "lora_B0" and j["lora_B0"]["ref"] == "lora_A0"
    assert j["lora_t_B0"]["ref"] is None
    assert [n for n in j if n.startswith("lora_t_")] == ["lora_t_B0", "lora_t_B1", "lora_t_B2", "lora_t_B3"]
    assert j["lora_t_B2"]["ref"] == "lora_t_B0"


def test_masters_come_before_their_shots_and_base_runs_without_lora():
    todo = st.jobs(_story())
    seen = set()
    for x in todo:
        assert x["ref"] is None or x["ref"] in seen
        seen.add(x["name"])
    base = [x for x in todo if x["run"] == "base"]
    assert [x["shot"] for x in base] == ["A0", "A1", "B0", "B2"] and all(x["lora"] is None for x in base)
    assert len(todo) == 17


def test_a_run_without_its_masters_is_refused():
    s = _story()
    s["runs"] = [{"name": "x", "lora": "A", "shots": ["A1"]}]
    with pytest.raises(ValueError):
        st.jobs(s)


def test_story_prompts_keep_the_caption_shape():
    for s in _story()["shots"]:
        assert 50 <= len(s["desc"].split()) <= 90, s["id"]
        assert "Napoleon" not in s["desc"] and "Mongol" not in s["desc"]
        if s["master"]:
            assert s["change"].startswith("Change from the previous shot:")


def test_faces_story_runs_each_shot_at_three_lora_weights_from_text():
    s = json.loads((STORY.parent / "napoleon_faces.json").read_text(encoding="utf-8"))
    todo = st.jobs(s)
    assert len(todo) == 12 and all(x["ref"] is None for x in todo)
    assert sorted({x["weight"] for x in todo}) == [0.5, 0.7, 1.0]
    for sh in s["shots"]:
        assert 50 <= len(sh["desc"].split()) <= 90, sh["id"]


def test_runs_default_to_the_lt79_weight_and_old_stories_keep_theirs():
    assert st.WEIGHT == 0.7
    assert {x["weight"] for x in st.jobs(_story()) if x["lora"]} == {1.0}
    s = _story()
    del s["runs"][0]["weight"]
    assert {x["weight"] for x in st.jobs(s) if x["lora"]} == {0.7}


GENERAL = "His face is fleshy and square, with small hooded eyes, heavy dark eyebrows and a long hooked nose."


def _new_story(face=GENERAL, desc=None, faces=("general",)):
    d = desc if desc is not None else ("Inside a lantern-lit army tent at night, a short stocky general in a black bicorne "
                                       f"hat stares ahead. {GENERAL} Close-up.")
    return {"story": "t", "cast": {"general": {"face": face}},
            "shots": [{"id": "A0", "master": None, "faces": list(faces), "desc": d}],
            "runs": [{"name": "lora", "lora": "A", "shots": "all"}]}


def test_lt79_a_story_with_written_faces_passes():
    assert st.face_problems(_new_story()) == []
    assert st.jobs(_new_story())[0]["weight"] == 0.7


def test_lt79_refuses_missing_cast_thin_face_and_a_shot_without_the_face_text():
    s = _new_story(); del s["cast"]
    assert any("no cast" in p for p in st.face_problems(s))
    with pytest.raises(ValueError):
        st.jobs(s)
    assert any("needs 4" in p for p in st.face_problems(_new_story(face="He has small eyes.")))
    assert any("lacks general" in p for p in st.face_problems(_new_story(desc="A general in a tent. Close-up.")))
    assert any("not in the cast" in p for p in st.face_problems(_new_story(faces=("officer",))))


def test_face_parts_reads_the_parts():
    assert st.face_parts(GENERAL) == ["brows", "eyes", "nose", "shape"]


def test_lt79_a_face_like_the_training_shows_people_is_refused():
    like = "His face is round, with big round eyes with tiny pupils, a unibrow, a small nose and a wobbly mouth."
    assert any("too close" in p for p in st.face_problems(_new_story(face=like, desc=f"A general. {like} Close-up.")))
    s = _new_story(); s["cast"]["general"]["look"] = "a white lab coat and spiky hair"
    assert any("too close" in p for p in st.face_problems(s))
