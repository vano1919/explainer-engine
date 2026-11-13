"""Guide step 3 (D-116): the J2/J4 spec writer ``edit/ltx_jobs.py`` turns the route shots into ``ltx_job/1`` rows on both bases
(the creator's card 2026-11-06 11:11 UTC), with the LJ rules of docs/LTX_JOBS.md. No pod, no network."""
import copy
import json
from pathlib import Path

import pytest

from explainer_engine.cloud import pins as pins_mod
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.edit import ltx_jobs as LJ

ROOT = Path(__file__).resolve().parents[2]
RS = json.loads((ROOT / "tests" / "fixtures" / "route_test" / "route_shots.json").read_text(encoding="utf-8"))
CODE = {"url": "https://github.com/Lightricks/LTX-2", "sha": "e98f6d927d83c92ef2be6aec76c8440b19306e39"}


def test_only_the_j2_and_j4_clips_with_a_layout_get_jobs_and_the_default_matrix_is_ten_generations():
    doc = LJ.build(RS)
    assert len(doc["jobs"]) == 10 <= C.LTX_MAX_GENERATIONS
    assert {j["clip_id"] for j in doc["jobs"]} == set(LJ.LAYOUT_OF)
    assert {j["route"] for j in doc["jobs"]} == {"J2", "J4"}
    assert all(j["first_frame"]["pose"] == "start" for j in doc["jobs"])          # C1: the first frame is the start pose
    assert all(j["frames"] % 8 == 1 for j in doc["jobs"])


def test_every_lora_sits_on_its_own_base_and_the_route_takes_its_passes():
    pins = pins_mod.load()["models"]
    for j in LJ.build(RS)["jobs"]:
        assert pins[j["lora"]["key"]]["base"] == pins[C.LTX_BASES[j["base"]]]["id"]
        passes = {c["pass"] for c in j["conditioning"]}
        if j["route"] == "J2":
            assert j["base"] == "ltx25" and passes == {"clay"} and not j["stage2_ic"]
        elif j["base"] == "ltx25":
            assert passes == {"colour"} and j["stage2_ic"]
        else:
            assert passes in ({"line", "depth"}, {"canny_full", "depth"}) and j["text_encoder"]["key"] == "text_encoder_gemma3"


def test_the_derived_controls_and_the_chain():
    jobs = {j["id"]: j for j in LJ.build(RS)["jobs"]}
    line = jobs["S02-02.c1.ltx23.line_foremid.s42"]["conditioning"]
    assert line[0]["derive"] == "invert" and line[0]["path"].endswith("battle_c1_line.mp4") and "derive" not in line[1]
    canny = jobs["S02-02.c1.ltx23.canny_full.s42"]["conditioning"][0]
    assert canny["derive"] == "canny" and canny["path"].endswith("battle_c1_colour.mp4")
    c2 = jobs["S02-02.c2.ltx25.colour.s42"]
    assert c2["chain_from"] == {"job": "S02-02.c1.ltx25.colour.s42", "frames": LJ.CHAIN_FRAMES}


def test_an_unpinned_weight_leaves_its_jobs_at_review_and_the_pinned_matrix_is_clean():
    """Gemma 3 is gated: until its sha256 was read (the creator accepted the licence, 2026-11-06 12:16 UTC) the LTX-2.3 jobs were
    REVIEW; with every weight pinned the default matrix has no finding."""
    assert pins_mod.load()["models"]["text_encoder_gemma3"]["sha256"]
    assert C.errors(LJ.build(RS)) == []
    pins = pins_mod.load()
    pins["models"]["text_encoder_gemma3"] = {**pins["models"]["text_encoder_gemma3"], "sha256": None}
    found = C.errors(LJ.build(RS, pins=pins))
    review = {f["where"] for f in found if f["rule"] == "LJ-01" and f["severity"] == "REVIEW"}
    assert review == {j["id"] for j in LJ.build(RS)["jobs"] if j["base"] == "ltx23"}
    assert not [f for f in found if f["severity"] == "FAIL"]


def test_a_matrix_row_for_a_clip_without_a_layout_or_a_chain_without_an_earlier_job_is_refused():
    with pytest.raises(ContractError):
        LJ.build(RS, matrix=[{"clip": "S02-03", "base": "ltx25", "variant": "clay", "seeds": [42]}])
    with pytest.raises(ContractError):
        LJ.build(RS, matrix=[{"clip": "S02-02.c2", "base": "ltx25", "variant": "colour", "seeds": [42], "chain": "S02-02.c1"}])
    with pytest.raises(ContractError):   # LJ-02: clay on a J4 shot
        LJ.build(RS, matrix=[{"clip": "S02-02.c1", "base": "ltx25", "variant": "clay", "seeds": [42]}])


def test_a_lora_put_on_the_other_base_fails_lj01():
    doc = LJ.build(RS)
    bad = copy.deepcopy(doc)
    j25 = next(j for j in bad["jobs"] if j["base"] == "ltx25")
    j23 = next(j for j in doc["jobs"] if j["base"] == "ltx23")
    j25["lora"] = j23["lora"]
    with pytest.raises(ContractError, match="LJ-01"):
        C.validate(bad)


def test_layout_shas_come_from_the_layout_manifest(tmp_path):
    (tmp_path / "battle").mkdir()
    (tmp_path / "battle" / "layout_manifest.json").write_text(json.dumps(
        {"passes": {"colour": {"clips": {"battle_c1": {"sha256": "a" * 64}}}}}), encoding="utf-8")
    jobs = {j["id"]: j for j in LJ.build(RS, layouts=tmp_path)["jobs"]}
    assert jobs["S02-02.c1.ltx25.colour.s42"]["conditioning"][0]["sha256"] == "a" * 64
    assert jobs["S03-02.ltx25.clay.s42"]["conditioning"][0]["sha256"] is None


def test_the_committed_pod_files_are_what_the_writer_makes_now():
    """The committed pod files are the lean pod's (training/pods/p14/lean.py build: the LEAN matrix under step3/, and p14.json =
    ltx_jobs.pod_config() + the extras' file, the 2K scale filter and the lean pod's 10-minute clip cap of its RP-11 schedule)."""
    from explainer_engine.training.pods.p14 import lean
    pod = LJ.POD_DIR
    cfg = json.loads((pod / "p14.json").read_text(encoding="utf-8"))
    assert cfg == lean.pod_config()
    assert cfg["clip_timeout_s"] == 600
    base = LJ.pod_config()
    assert {k: v for k, v in cfg.items() if k != "extra_jobs_file"} | {"controls": {"canny_vf": LJ.CANNY_VF},
                                                                      "clip_timeout_s": base["clip_timeout_s"]} == base
    committed = json.loads((pod / "ltx_jobs.json").read_text(encoding="utf-8"))

    def bare(doc):   # the layout hashes come from the layout manifests (--layouts) once the renders are on the vault
        doc = copy.deepcopy(doc)
        for j in doc["jobs"]:
            for c in j["conditioning"]:
                c["sha256"] = None
        return doc
    assert bare(committed) == bare(LJ.build(RS, matrix=LJ.LEAN, out_root="step3"))
    assert len(LJ.build(RS)["jobs"]) == 10   # the full matrix stays the writer's default
