"""The generic Qwen jobs runner and its Modal launcher (the stone-age run sa_v3, creator 2026-11-07 14:42-15:08 UTC)."""
import sys
from pathlib import Path

import pytest

from explainer_engine.blender import stoneage_qwen_jobs as J
from explainer_engine.blender import stoneage_test_layouts as S

P15 = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p15"
sys.path.insert(0, str(P15))
import modal_qwen_jobs as MJ  # noqa: E402
import qwen_jobs as QJ  # noqa: E402

INPUTS = {f"sa_{s}_flat3{x}.png": "x" for s in S.SCENES for x in ("", "_side", "_low", "_codes", "_magenta")}


def test_the_run_has_every_test_and_refs_resolve_in_order():
    doc = J.jobs(INPUTS)
    assert QJ.check_jobs(doc) == []
    w07, w10 = ({j["name"] for j in g["jobs"]} for g in doc["groups"])
    assert [g["lora_weight"] for g in doc["groups"]] == [0.7, 1.0]
    assert {f"{s}_wide_w07" for s in S.SCENES} <= w07 and {f"{s}_wide_w10" for s in S.SCENES} <= w10
    assert {f"{s}_codes_w10" for s in S.SCENES} <= w10          # 15:08 UTC: the code test at LoRA 1.0
    assert {f"{s}_{a}_w07" for s in S.SCENES for a in S.ANGLES[s]} <= w07
    b = J.asset_jobs()                                            # 15:12 UTC: the Qwen-first assets run on their own, first
    assert QJ.check_jobs(b) == [] and b["out"].endswith("out_v3b") and b["inputs"] == {}
    names = {j["name"] for j in b["groups"][0]["jobs"]}
    assert {f"env_{s}_{v}" for s in S.SCENES for v in ("front", "left", "right", "back")} | {f"char_{w}" for w in J.PEOPLE} == names
    assert not any("block" in r for g in doc["groups"] for j in g["jobs"] for r in j["refs"])   # 15:05 UTC: only flat3


def test_angles_put_the_new_still_first_and_the_master_second():
    doc = J.jobs(INPUTS)
    j = next(j for j in doc["groups"][0]["jobs"] if j["name"] == "cave_side_w07")
    assert j["refs"] == ["in:sa_cave_flat3_side.png", "out:cave_wide_w07"]
    assert "Image 2 is the master scene" in j["prompt"]


def test_check_refuses_a_ref_made_later_or_an_unpinned_input_or_a_dict_prompt():
    doc = {"inputs": {}, "groups": [{"lora_weight": 0.7, "jobs": [
        {"name": "a", "prompt": "p", "refs": ["out:b"], "size": [1280, 720]},
        {"name": "b", "prompt": {"qwen": "p"}, "refs": ["in:x.png"], "size": [1280, 721]}]}]}
    bad = " ".join(QJ.check_jobs(doc))
    assert "out:b is not made before it" in bad and "not pinned" in bad and "non-empty str" in bad and "divisible" in bad


def test_code_prompt_names_codes_not_sides_and_asks_for_no_letters():
    p = J.code_prompt("ice")
    assert "B1 is the big woolly mammoth" in p and "paint no codes or letters" in p and "on the left" not in p


def test_launcher_timeout_from_cap_and_expected_outputs():
    assert MJ.TIMEOUT_S == MJ.cost_timeout(MJ.CAP_USD) and MJ.TIMEOUT_S * MJ.USD_PER_H / 3600 < MJ.CAP_USD
    doc = J.jobs(INPUTS)
    exp = MJ.expected_outputs(doc)
    assert len(exp) == sum(len(g["jobs"]) for g in doc["groups"]) and MJ.expected_outputs(doc, smoke=True) == ["qwen/smoke.json"]
    with pytest.raises(ValueError):
        MJ.check_timeout(MJ.TIMEOUT_S + 600, MJ.CAP_USD)


def test_magenta_variant_forbids_only_the_magenta_codes():
    """15:10 UTC: codes in one unique font and colour; the negative drops the general text ban and forbids only those."""
    doc = J.jobs(INPUTS)
    j = next(j for j in doc["groups"][1]["jobs"] if j["name"] == "cave_magenta_w10")
    assert "magenta" in j["negative"] and "text" not in j["negative"] and "lettering" not in j["negative"]
    assert "remove every magenta code" in j["prompt"]
