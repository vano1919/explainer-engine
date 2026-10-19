"""PV-47 / OR-16: one approved variant collage before a hero or the episode's world is painted."""

import copy

import pytest

from explainer_engine.production import script as S
from explainer_engine.scripting import reference_approval as RA

REC = {"collage": "review/collage.jpg", "tile": 2, "picture": "p_vito", "approved_by": "creator", "approved_at": "2026-10-19"}
BASE = {"schema": "production_script/2", "episode": {"id": "x", "title": "X episode"},
        "look": {"style_refs": [], "default_engine": "pod_ref"},
        "cast": {"vito": {"names": ["vito"], "card": "an older patriarch in a dark suit"}},
        "library": {"p_vito": {"file": "p_vito.png", "engine": "existing", "heroes": ["vito"]},
                    "v13_table": {"heroes": ["vito"]}},
        "segments": [{"id": "S01", "lines": [{"text": "Olive oil."}]}]}


def test_a_painted_hero_and_world_without_an_approved_collage_fail_on_a_new_script_and_review_on_an_old_one():
    assert sorted((f["severity"], f["where"]) for f in RA.check(BASE)) == [("FAIL", "look.environment"), ("FAIL", "vito")]
    old = dict(BASE, schema="production_script/1")
    assert {f["severity"] for f in RA.check(old)} == {"REVIEW"}


def test_the_recorded_pick_passes_and_must_name_a_library_picture_and_an_existing_collage(tmp_path):
    d = copy.deepcopy(BASE)
    d["cast"]["vito"]["reference"] = REC
    d["look"]["environment"] = dict(REC, picture="v13_table", tile=5)
    assert RA.check(d) == []
    assert "not found" in RA.check(d, tmp_path)[0]["detail"]
    (tmp_path / "review").mkdir()
    (tmp_path / "review" / "collage.jpg").write_bytes(b"x")
    assert RA.check(d, tmp_path) == []
    d["cast"]["vito"]["reference"] = dict(REC, picture="p_nobody", approved_by="")
    details = " ".join(f["detail"] for f in RA.check(d))
    assert "approved_by" in details and "p_nobody" in details
    assert not [e for e in S.schema_errors(d) if "reference" in str(e) or "environment" in str(e)]


def test_nothing_painted_needs_no_collage_and_a_face_sheet_hero_does():
    d = copy.deepcopy(BASE)
    d["library"] = {"p_vito": {"file": "p_vito.png", "engine": "existing", "heroes": ["vito"]}}
    assert RA.check(d) == []
    d["cast"]["vito"]["face_sheet"] = {"id": "vito_faces"}
    assert [f["where"] for f in RA.check(d)] == ["vito"]


def test_one_collage_prompt_holds_four_to_six_variants():
    p = RA.collage_prompt("Vice City's skyline at dusk", ["neon pink", "teal", "golden hour", "storm"])
    assert "4 equal tiles" in p and "tile 4: storm" in p
    with pytest.raises(ValueError):
        RA.collage_prompt("x", ["a", "b"])


def test_a_free_sheet_from_existing_pictures(tmp_path):
    from PIL import Image
    pics = []
    for i in range(4):
        pics.append(tmp_path / f"{i}.png")
        Image.new("RGB", (64, 36), (i * 60, 0, 0)).save(pics[-1])
    out = RA.build_sheet(pics, ["a", "b", "c", "d"], tmp_path / "sheet.jpg", tile=(64, 36), cols=2)
    assert Image.open(out).size == (128, 2 * (36 + 40))


def test_a_picture_painted_inline_on_a_shot_needs_the_world_record():
    d = copy.deepcopy(BASE)
    d["library"] = {}
    d["segments"][0]["shots"] = [{"picture": {"engine": "pod_ref", "subject": "a neon street", "refs": ["s01_skyline"]}}]
    assert [f["where"] for f in RA.check(d)] == ["look.environment"]
