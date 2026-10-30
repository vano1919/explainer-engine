"""The data contracts (docs/CONTRACTS.md): every schema validates its valid fixture and refuses its invalid ones; derived files go
stale; one frame rate across a job; the lifecycle enum has one source."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from explainer_engine.core import contracts as C
from explainer_engine.core import store
from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "contracts"
NEW = ["job_manifest", "script_variants", "screenplay_spine", "voice_casting", "audio_spine", "sound_mix_manifest",
       "visual_comp_manifest", "comp_spec", "scene_set", "shot_spec", "pod_heartbeat", "edit_and_grade_manifest", "qa_report",
       "editorial_review", "distribution_package"]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fixtures(prefix: str) -> list:
    return [pytest.param(p, id=f"{p.parent.name}/{p.stem}") for p in sorted(FIX.glob(f"*/{prefix}*.json"))]


def test_every_new_contract_has_a_schema_and_fixtures():
    for name in NEW:
        assert (ROOT / "explainer_engine" / "schemas" / f"{name}.schema.json").exists(), name
        assert (FIX / name / "valid.json").exists(), name
        assert len(list((FIX / name).glob("invalid__*.json"))) >= 2, name
    assert (FIX / "film_shots_2" / "valid.json").exists()


def test_the_contracts_table_names_every_schema():
    text = (ROOT / "docs" / "CONTRACTS.md").read_text(encoding="utf-8")
    named = set(re.findall(r"^\| `([a-z_]+)/\d` \|", text, flags=re.M))
    assert named >= set(NEW) | {"film_shots"}, sorted(set(NEW) - named)


@pytest.mark.parametrize("path", fixtures("valid"))
def test_valid_fixture_passes(path):
    assert not [f for f in C.errors(load(path)) if f["severity"] == "FAIL"]
    C.validate(load(path))


@pytest.mark.parametrize("path", fixtures("invalid__"))
def test_invalid_fixture_is_refused(path):
    with pytest.raises(ContractError):
        C.validate(load(path))


@pytest.mark.parametrize("path", fixtures("review__"))
def test_geometry_breach_is_a_review_finding_at_the_registry_level(path):
    found = C.validate(load(path))  # no exception: BP-139 is a hypothesis (D-59, CN-11)
    assert found and {f["severity"] for f in found} == {SR.level("BP-139")} == {"REVIEW"}


def test_a_document_must_name_its_contract():
    with pytest.raises(ContractError):
        C.validate({"state": "CREATED"})
    with pytest.raises(ContractError):
        C.validate({"schema": "nonesuch/1"})


def test_film_shots_1_still_validates_unchanged():
    doc = load(FIX / "film_shots_2" / "valid.json")
    doc["schema"] = "film_shots/1"
    for s in doc["shots"]:
        for k in ("lane", "archetype", "duration_frames", "width", "height", "lens_tier", "focal_xy", "continuity_ref", "blocking_ref"):
            del s[k]
    del doc["fps"]
    assert C.errors(doc) == []


def test_film_shots_2_fps_is_the_native_rate():
    doc = load(FIX / "film_shots_2" / "valid.json")
    doc["fps"] = 30
    found = {f["rule"]: f["severity"] for f in C.errors(doc)}
    assert found["CN-09"] == SR.level("BP-139") == "REVIEW"  # a hypothesis: never a FAIL (D-59)


def test_the_lifecycle_enum_has_one_source():
    enum = load(ROOT / "explainer_engine" / "schemas" / "job_manifest.schema.json")["properties"]["state"]["enum"]
    assert tuple(enum) == store.LIFECYCLE + store.TERMINAL


def test_a_derived_file_goes_stale_when_an_input_changes(tmp_path):
    (tmp_path / "x").mkdir()
    src = tmp_path / "x" / "file.bin"
    src.write_bytes(b"one")
    doc = load(FIX / "audio_spine" / "valid.json")
    for ref in doc["derived_from"].values():
        ref["sha256"] = C.sha256_file(src)
    assert C.errors(doc, tmp_path) == []
    src.write_bytes(b"two")
    found = C.errors(doc, tmp_path)
    assert {f["rule"] for f in found} == {"CN-02"} and "stale" in found[0]["detail"]


def test_word_indexes_must_exist_in_the_spine(tmp_path):
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "audio_spine.json").write_text(json.dumps(load(FIX / "audio_spine" / "valid.json")), encoding="utf-8")
    doc = load(FIX / "sound_mix_manifest" / "valid.json")
    assert C.errors(doc, tmp_path) == []
    doc["spots"][0]["word_index"] = 99
    assert [f["rule"] for f in C.errors(doc, tmp_path)] == ["CN-01"]


def test_a_distribution_package_lists_only_real_unchanged_files(tmp_path):
    doc = load(FIX / "distribution_package" / "valid.json")
    assert {f["rule"] for f in C.errors(doc, tmp_path)} == {"CN-14"}
    (tmp_path / "packages").mkdir()
    for ref in doc["files"].values():
        if ref:
            (tmp_path / ref["path"]).write_bytes(b"x")
            ref["sha256"] = C.sha256_file(tmp_path / ref["path"])
    assert C.errors(doc, tmp_path) == []


def test_one_frame_rate_across_the_job():
    m = load(FIX / "job_manifest" / "valid.json")
    fs = load(FIX / "film_shots_2" / "valid.json")
    spec = load(FIX / "shot_spec" / "valid.json")
    assert C.cross_fps(m, fs, [spec]) == []
    spec["fps"] = 30
    assert [f["rule"] for f in C.cross_fps(m, fs, [spec])] == ["CN-09"]
    fs["fps"] = 25
    assert len(C.cross_fps(m, fs, [spec])) == 2


def test_the_cli_reports_fail_with_exit_code_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(load(FIX / "scene_set" / "invalid__feet.json")), encoding="utf-8")
    assert C.main(["check", str(bad)]) == 1
    assert "CN-01" in capsys.readouterr().out
    good = tmp_path / "good.json"
    good.write_text(json.dumps(load(FIX / "scene_set" / "valid.json")), encoding="utf-8")
    assert C.main(["check", str(good)]) == 0


def test_film_shots_1_does_not_accept_the_fields_of_2():
    doc = load(FIX / "film_shots_2" / "valid.json")
    doc["schema"] = "film_shots/1"
    with pytest.raises(ContractError):
        C.validate(doc)  # fps, scene_sets and the lane fields belong to /2


def test_a_package_must_be_cut_from_the_jobs_assembled_video(tmp_path):
    doc = load(FIX / "distribution_package" / "valid.json")
    (tmp_path / "packages").mkdir()
    for ref in doc["files"].values():
        if ref:
            (tmp_path / ref["path"]).write_bytes(b"x")
            ref["sha256"] = C.sha256_file(tmp_path / ref["path"])
    manifest = load(FIX / "job_manifest" / "valid.json")
    (tmp_path / "job_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    found = C.errors(doc, tmp_path)
    assert [f["rule"] for f in found] == ["CN-14"] and "assembled" in found[0]["detail"]  # no assembled_video recorded
    manifest["artifacts"]["assembled_video"] = {"path": "final.mp4", "sha256": "e" * 64, "schema": None, "dossier_sha256": None}
    (tmp_path / "job_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    found = C.errors(doc, tmp_path)
    assert [f["rule"] for f in found] == ["CN-14"] and "another render" in found[0]["detail"]
    manifest["artifacts"]["assembled_video"]["sha256"] = doc["source_episode_sha256"]
    (tmp_path / "job_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert C.errors(doc, tmp_path) == []
