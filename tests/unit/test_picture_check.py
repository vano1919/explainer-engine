"""V4.1 Step 1.1 (MA-05, D-139): the picture check before the LTX job is fail-closed and records the checked bytes."""
import json
from pathlib import Path

import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.videolane import scene as SC
from explainer_engine.videolane import storyboard as SB
from tests.unit import test_videolane as TV


def _board(tmp_path):
    doc = TV._scene()
    root, pics = TV._board_episode(tmp_path, doc)
    TV._reads(root, doc)
    SB.build(root, doc, [s["shot_id"] for s in doc["shots"]], "s1", pictures=pics)
    return doc, root


def test_a_clean_shot_passes_and_records_its_picture_sha_and_continuations_name_their_source(tmp_path):
    doc, root = _board(tmp_path)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json")
    by = {s["shot_id"]: s for s in scene["shots"]}
    chk = by["C"]["picture_check"]
    pic = json.loads(Path(scene["pictures"]["manifest"]).read_text())["shots"]["C_start"]
    assert chk["state"] != "NO_PERCEPTION_INPUT" and not chk["regeneration_required"] and chk["picture_sha256"] == pic["sha256"]
    assert by["B"]["picture_check"] == {"state": "CONTINUATION", "regeneration_required": False, "picture_sha256": None,
                                        "continues": "A"}
    assert not [w for w in SC.storyboard_problems(scene) if "picture" in w]


def test_a_story_breaking_conflict_refuses_the_scene(tmp_path, monkeypatch):
    doc, root = _board(tmp_path)
    real = SC._reconcile_start_state_with_perception

    def conflict(script, shot, **kw):
        out = real(script, shot, **kw)
        return dict(out, regeneration_required=True, reconciliation_state="STORY_BREAKING_CONFLICT")
    monkeypatch.setattr(SC, "_reconcile_start_state_with_perception", conflict)
    with pytest.raises(ContractError, match="must be regenerated"):
        SC.build(root, doc, "s1", tmp_path / "scene.json")


def test_no_perception_input_is_a_refusal_not_a_pass(tmp_path):
    doc, root = _board(tmp_path)
    bad = root / "assets" / "unreadable.png"
    bad.write_bytes(b"not a picture")
    shot = next(s for s in doc["shots"] if s["shot_id"] == "C")
    chk = SC.picture_check(root, doc, shot, bad)
    assert chk["state"] == "NO_PERCEPTION_INPUT" and SC.picture_check_refusal(chk)


def test_a_scene_file_without_picture_check_or_with_a_refused_shot_is_refused(tmp_path):
    doc, root = _board(tmp_path)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json")
    clean = json.loads(json.dumps(scene))
    assert not [w for w in SC.storyboard_problems(clean) if "picture" in w]
    del clean["shots"][0]["picture_check"]
    assert any("no picture_check" in w for w in SC.storyboard_problems(clean))
    refused = json.loads(json.dumps(scene))
    refused["shots"][1]["picture_check"] = {"state": "STORY_BREAKING_CONFLICT", "regeneration_required": True,
                                            "picture_sha256": "x"}
    assert any("must be regenerated" in w for w in SC.storyboard_problems(refused))


def test_job_spec_refuses_a_picture_that_changed_after_its_check(tmp_path, monkeypatch):
    from explainer_engine.videolane import identity as ID
    monkeypatch.setattr(ID, "face_not_measured", lambda rec: False)   # the Q3 face gate is not what this test is about
    from explainer_engine.training.pods.ltx import scene_run as SRN
    doc, root = _board(tmp_path)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json", budget={"total_usd": 1000.0, "pictures_usd": 0.0, "cpu_checks_usd": 0.0},
                    ledger={"path": "x"})
    sp = tmp_path / "scene.json"
    for row in scene["shots"]:
        if row.get("picture_check", {}).get("picture_sha256"):
            row["picture_check"]["picture_sha256"] = "0" * 64   # the check was made on other bytes
            break
    sp.write_text(json.dumps(scene))
    with pytest.raises(SystemExit, match="changed after its picture check"):
        SRN.job_spec(sp)


def test_job_spec_refuses_a_picture_changed_on_disk_after_build(tmp_path, monkeypatch):
    from explainer_engine.training.pods.ltx import scene_run as SRN
    from explainer_engine.videolane import identity as ID
    monkeypatch.setattr(ID, "face_not_measured", lambda rec: False)
    doc, root = _board(tmp_path)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json", budget={"total_usd": 1000.0, "pictures_usd": 0.0, "cpu_checks_usd": 0.0},
                     ledger={"path": "x"})
    pins = json.loads(Path(scene["pictures"]["manifest"]).read_text())["shots"]
    Path(next(iter(pins.values()))["path"]).write_bytes(b"changed after build")
    with pytest.raises(SystemExit, match="not the one the scene pins"):
        SRN.job_spec(tmp_path / "scene.json")
