"""D-120 code checks: place register (LV-01), references (RF-01/RF-04), prompt shape (HI-04/HI-01), the free jobs check."""
import json
from pathlib import Path

from explainer_engine.production import scene_reuse as S
from explainer_engine.training.pods.p15 import qwen_jobs as QJ

REG = {"marcus": "Marcus: man 1.75 m.", "ura": "Ura: sorcerer 1.80 m."}


def doc(jobs, inputs=None):
    return {"registry": REG, "inputs": inputs or {}, "groups": [{"lora_weight": 0.7, "jobs": jobs}]}


def job(name, prompt, refs=(), in_shot=("marcus", "ura"), **kw):
    return {"name": name, "prompt": prompt, "refs": list(refs), "size": [1280, 704], "in_shot": list(in_shot), **kw}


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
    assert S.check_refs(doc([job("a", "x", ["out:p"], variant_of="p")])) == []
    assert S.check_refs(doc([job("a", "x", ["out:p"])]))[0][0] == "RF-05"     # D-121: a generated picture only for its own variant


def test_prompt_shape():
    ok = f"xworld style, flat. Scene: two people. {REG['marcus']} {REG['ura']}"
    assert S.check_prompts(doc([job("a", ok)])) == []
    assert S.check_prompts(doc([job("a", "Scene: x", in_shot=())]))[0][0] == "HI-04"
    assert S.check_prompts(doc([job("a", f"xworld style. {REG['ura']} Scene: x", in_shot=["ura"])]))[0][0] == "HI-04"
    styled = f"Style: an exciting adventure style; this scene: violet dusk. xworld style, flat. Scene: two people. {REG['marcus']} {REG['ura']}"
    assert not [f for f in S.check_prompts(doc([job("s", styled)])) if f[1] == "FAIL"]
    assert S.check_prompts(doc([job("a", ok + " w" * 300)]))[-1][:2] == ("HI-08", "FAIL")   # D-121: FAIL above 280 words


def test_unknown_ref_type_is_refused_by_the_free_check():
    bad = QJ.check_jobs(doc([job("a", "x", ["job:b"])]))
    assert any("unknown" in b for b in bad)


def test_first_ten_jobs_file_passes_every_check():
    p = Path("/mnt/project-files/explainer-engine/stoneage_pilot_2026-11-07/one_place_2026-11-07/sa_v11_jobs.json")
    if not p.exists():
        return
    d = json.loads(p.read_text())
    assert QJ.check_jobs(d) == []
    # D-121 made HI-01 need each job's in_shot list and RF-05 need variant_of: this pre-D-121 file passes everything else and
    # must be migrated (by its builder) before it runs again; paid_preflight refuses it until then
    fails = [r for r in S.check_all(d) if r[1] == "FAIL"]
    assert {r[0] for r in fails} <= {"HI-01", "RF-05"}
    assert all("no in_shot list" in r[2] for r in fails if r[0] == "HI-01")


def test_in_shot_blocks_are_verbatim_and_nobody_else_is_described():
    ok = f"xworld style, flat. Scene: Marcus alone. {REG['marcus']}"
    assert S.check_prompts(doc([job("a", ok, in_shot=["marcus"])])) == []
    assert S.check_prompts(doc([job("a", ok, in_shot=["marcus", "ura"])]))[0][0] == "HI-01"
    assert S.check_prompts(doc([job("a", ok.replace("1.75", "1.8"), in_shot=["marcus"])]))[0][0] == "HI-01"
    assert S.check_prompts(doc([job("a", ok, in_shot=["ghost"])]))[0][0] == "HI-01"
    both = f"xworld style, flat. Scene: x. {REG['marcus']} {REG['ura']}"
    assert any(r[0] == "HI-04" for r in S.check_prompts(doc([job("a", both, in_shot=["marcus"])])))
    nolist = {"name": "a", "prompt": ok, "refs": [], "size": [1280, 704]}
    assert S.check_prompts(doc([nolist]))[0][0] == "HI-01"


def test_registry_heights_faces_and_one_lora_weight():
    d = {"registry": {"marcus": "Marcus: man 1.75 m, oval face, straight nose.", "ura": "Ura: tall sorcerer.",
                      "mammoth": "Mammoth: 3.5 m, brown fur."}, "registry_kinds": {"mammoth": "thing"}, "inputs": {},
         "groups": [{"lora_weight": 1.0, "jobs": []}, {"lora_weight": 0.7, "jobs": []}]}
    rules = {(r[0], r[2].split(":")[0]) for r in S.check_registry(d)}
    assert rules == {("HI-02", "ura"), ("HI-05", "ura")}
    assert S.check_lora_weight(d)[0][0] == "HI-07"
