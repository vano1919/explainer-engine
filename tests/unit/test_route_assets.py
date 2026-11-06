"""Route-test Qwen asset pod (2026-11-06): the job list is complete and checked without a GPU, the pinned hashes match the files, the
helpers measure what the report needs. The pod itself (route_assets.main) runs only on a pod."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

D = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods"
R = D / "route"
spec = importlib.util.spec_from_file_location("route_assets", R / "route_assets.py")
RA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RA)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_the_job_list_is_the_plan():
    js = RA.jobs()
    groups = {g: [j for j in js if j["group"] == g] for g in ("A", "B", "C", "D", "D2")}
    assert [len(groups[g]) for g in "ABCD"] == [4, 12, 8, 6] and len(groups["D2"]) == 6
    assert len({j["name"] for j in js}) == len(js)
    assert [j["group"] for j in js][:12] == ["D"] * 6 + ["D2"] * 6          # the useful scenes first, then the 90-word twins (creator test)
    assert all(j["words_limit"] == 90 and j["seed"] == 11 and j["cfg"] == 4.0 and j["size"] == [1280, 720] for j in groups["D2"])
    assert [j["name"].replace("_90", "")[:2] for j in groups["D2"]] == [j["name"][:2] for j in groups["D"]]
    assert all(40 < len(j["prompt"].split()) <= 90 for j in groups["D2"])
    assert all(j["size"] == [2048, 1024] for j in groups["A"]) and all(j["size"] == [1280, 720] for j in groups["B"] + groups["C"] + groups["D"])
    assert {j["seed"] for j in groups["C"]} == {11, 23} and all(j["cfg"] == 2.5 for j in groups["C"])
    assert all(j["cfg"] == 4.0 and j["seed"] == 11 for j in groups["A"] + groups["B"] + groups["D"])
    names = [j["name"] for j in js]
    for j in groups["C"]:                                                     # every reference is drawn before it is used
        for r in j["refs"]:
            assert names.index(r.split(":")[0]) < names.index(j["name"])
    assert all(RA.CFG["flat"] in j["prompt"] for j in groups["B"])
    assert {j["lora"] for j in js} == {"style"} and RA.STYLE == ("style", 0.7)


def test_the_text_prompts_pass_the_style_check():
    assert RA.prompt_problems() == []


def test_no_banned_lora_or_base():
    text = (R / "route_assets.json").read_text() + (R / "route_assets.py").read_text()
    assert "wldnk" not in text and "2512" not in text and "2511" not in text
    assert RA.CFG["base"]["repo"] == "Qwen/Qwen-Image-2.1"


def test_the_style_lora_is_the_pinned_checkpoint():
    import json
    pins = json.loads((D.parents[2] / "config" / "cloud_pins.json").read_text())["models"]["loras"]["xworld_v2"]
    s = RA.CFG["style_lora"]
    assert (s["hf"], s["path"], s["sha256"], s["weight"]) == (pins["hf"], pins["path"], pins["sha256"], pins["weight"])


def test_the_picks_file_becomes_redraws_and_fix_edits():
    picks = {"redraw": [{"job": "D3_tent", "seeds": [12, 13, 14]}],
             "fix": [{"image": "D1_ford", "defect": "the knight has three arms"}, {"image": "B_H1_back", "defect": "a"}, {"image": "A2_courtyard", "defect": "b"},
                     {"image": "D2_duel", "defect": "too many"}]}
    js = RA.picks_jobs(picks)
    assert [j["name"] for j in js] == ["D3_tent_redraw12", "D3_tent_redraw13", "E_D1_ford", "E_B_H1_back", "E_A2_courtyard"]  # two seeds, three fixes at most
    e = js[2]
    assert e["refs"] == ["D1_ford"] and "Change nothing else; fix: the knight has three arms" in e["prompt"] and e["cfg"] == 2.5
    assert js[4]["size"] == [2048, 1024]


def test_seam_score_tells_a_joined_edge_from_a_cut_one():
    x = np.linspace(0, 2 * np.pi, 2048)
    base = np.rint(127 + 100 * np.sin(x))[None, :, None].repeat(1024, 0).repeat(3, 2)
    joined = Image.fromarray(base.round().astype("uint8"))
    cut = Image.fromarray(np.concatenate([base[:, :1024] * 0 + 20, base[:, 1024:] * 0 + 230], axis=1).astype("uint8"))
    assert RA.seam_score(joined) < 2 < RA.seam_score(cut)


def test_the_view_and_the_panorama_canvas():
    img = Image.new("RGB", (2048, 1024), (200, 10, 10))
    assert RA.view_of(img).size == (1280, 720)
    c = RA.pano_canvas(img)
    assert c.size == (2048, 1024) and c.getpixel((5, 5)) == (0, 255, 0) and c.getpixel((1024, 512)) == (200, 10, 10)
    assert [j["size"] for j in RA.pano_jobs()] == [[2048, 1024]] * 2 and len(RA.pano_jobs()) == 2


def test_the_pod_script_pins_its_job_files():
    sh = (R / "route_assets.sh").read_text()
    assert "PLACEHOLDER" not in sh
    pinned = dict(zip(("route_assets.py", "route_assets.json", "xworld_v1_test.py"),
                      re.search(r"printf '%s  %s\\n' (\w{64}) \S+ (\w{64}) \S+ (\w{64}) ", sh).groups()))
    assert pinned["route_assets.py"] == sha(R / "route_assets.py")
    assert pinned["route_assets.json"] == sha(R / "route_assets.json")
    assert pinned["xworld_v1_test.py"] == sha(D / "xworld_v1_test.py")        # the working branch's copy, the one that drew round 3b
    assert "heartbeat: datasets/vano1919/tmr-artifacts:route_test_2026-11/assets/beat.txt" in sh
    assert "XW_GPU_MODE=model_cpu_offload" in sh


def test_three_failed_jobs_in_a_row_abort_the_run(tmp_path):
    import pytest
    R = RA.Run(tmp_path)
    j = RA.jobs()[0]

    class Boom:
        def __call__(self, key):
            raise RuntimeError("cuda out of memory")
    RA.make(R, Boom(), None, j)
    RA.make(R, Boom(), None, j)
    with pytest.raises(RA.Abort):
        RA.make(R, Boom(), None, j)


def test_prompt_check_allows_ninety_words_only_in_d2():
    assert RA.prompt_problems() == []
    cfg = json.loads(json.dumps(RA.CFG))
    cfg["scenes"][0][1] = cfg["scenes_d2"][0][1]                              # 75 words in group D still fails
    assert any(n == "D1_ford" for n, _ in RA.prompt_problems(cfg))
    cfg = json.loads(json.dumps(RA.CFG))
    cfg["scenes_d2"][0][1] += " " + "more " * 30                              # more than 90 words in D2 fails too
    assert any(n == "D1_ford_90" for n, _ in RA.prompt_problems(cfg))
