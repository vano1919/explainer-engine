"""D-120 code checks: place register (LV-01), references (RF-01/RF-04), prompt shape (HI-04/HI-01), the free jobs check."""
import json
from pathlib import Path

from explainer_engine.production import scene_reuse as S
from explainer_engine.training.pods.p15 import qwen_jobs as QJ

REG = {"marcus": "Marcus: man 1.75 m.", "ura": "Ura: sorcerer 1.80 m."}


def doc(jobs, inputs=None):
    return {"registry": REG, "inputs": inputs or {}, "groups": [{"lora_weight": 0.7, "jobs": jobs}]}


def job(name, prompt, refs=()):
    return {"name": name, "prompt": prompt, "refs": list(refs), "size": [1280, 704]}


def test_two_drawings_in_a_row_fail_and_a_separator_passes():
    A = lambda i, d, k="sharp", p="cave": {"id": i, "place": p, "drawing": d, "kind": k}
    assert S.check_place_register([A("s1", "c1"), A("s2", "c1")]) == []
    assert S.check_place_register([A("s1", "c1"), A("s2", "c2")])[0][0] == "LV-01"
    assert S.check_place_register([A("s1", "c1"), A("s2", "x", p="ice"), A("s3", "c2")]) == []
    assert S.check_place_register([A("s1", "c1"), A("s2", "c1", "blurred"), A("s3", "c2")]) == []


def test_rendered_reference_and_too_many_refs_fail():
    d = doc([job("a", "x", ["in:cave_blender.png"])], {"cave_blender.png": "sha"})
    assert S.check_refs(d)[0][0] == "RF-01"
    d = doc([job("a", "x", ["out:1", "out:2", "out:3", "out:4"])])
    assert S.check_refs(d)[0][0] == "RF-04"
    assert S.check_refs(doc([job("a", "x", ["out:p"])])) == []


def test_prompt_shape():
    ok = f"xworld style, flat. Scene: two people. {REG['marcus']} {REG['ura']}"
    assert S.check_prompts(doc([job("a", ok)])) == []
    assert S.check_prompts(doc([job("a", "Scene: x")]))[0][0] == "HI-04"
    assert S.check_prompts(doc([job("a", f"xworld style. {REG['ura']} Scene: x")]))[0][0] == "HI-04"
    assert S.check_prompts(doc([job("a", ok + " w" * 300)]))[-1][0] == "HI-08"


def test_unknown_ref_type_is_refused_by_the_free_check():
    bad = QJ.check_jobs(doc([job("a", "x", ["job:b"])]))
    assert any("unknown" in b for b in bad)


def test_first_ten_jobs_file_passes_every_check():
    p = Path("/mnt/project-files/explainer-engine/stoneage_pilot_2026-11-07/one_place_2026-11-07/sa_v11_jobs.json")
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert QJ.check_jobs(d) == [] and S.check_refs(d) == []
    assert [r for r in S.check_prompts(d) if r[1] == "FAIL"] == []
