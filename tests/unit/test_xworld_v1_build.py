"""xworld_v1 training set (D-80, LT-69, LT-76): style + pairs with the trigger in the file, no held-out picture, 6 samples."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from explainer_engine.training.pods import xworld_v1_build as b

POD = Path(b.__file__).parent


def _man():
    chain = [f"frames/{i:04d}.png" for i in range(50, 57)]
    chain2 = [f"frames/{i:04d}.png" for i in range(60, 66)]
    return {"train": {"single": [{"img": "frames/0001.png"}, {"img": "frames/0002.png"}],
                      "scene_pairs": [{"a": "frames/0001.png", "b": "frames/0002.png"}],
                      "inshot_pairs": [{"a": "inshot/0005_a.png", "b": "inshot/0005_b.png"}]},
            "hold_out": {"chains": [chain, chain2], "guard_shots": [48, 49, 57, 58]}}


def _caps(m):
    c = {}
    for x in m["train"]["single"]:
        c[f"d:{x['img']}"] = "a kitchen at night."
    for p in m["train"]["scene_pairs"] + m["train"]["inshot_pairs"]:
        c[f"d:{p['b']}"] = "a man in a lab coat."
        c[f"c:{p['a']}>{p['b']}"] = "Change from the previous shot: he turns left."
    for ch in m["hold_out"]["chains"]:
        for a, bb in zip(ch, ch[1:]):
            c[f"d:{a}"] = c[f"d:{bb}"] = "a garage with a car."
            c[f"c:{a}>{bb}"] = "Change from the previous shot: the camera moves closer."
    return c


def test_trigger_in_every_caption_and_pairs_carry_the_change_line():
    m = _man()
    items = b.plan(m, _caps(m))
    assert {i[0] for i in items} == {"style", "pair"} and len(items) == 4
    assert all(i[4].startswith("xworld style, ") for i in items)
    assert all("Change from the previous shot:" in i[4] and i[3] for i in items if i[0] == "pair")


def test_held_out_or_guard_picture_in_training_is_refused():
    m = _man()
    m["train"]["single"].append({"img": "frames/0057.png"})   # a guard shot next to a held-out scene
    c = _caps(m)
    c["d:frames/0057.png"] = "x"
    with pytest.raises(ValueError, match="LT-76"):
        b.plan(m, c)


def test_six_samples_with_held_out_one_without_trigger_and_one_edit(tmp_path):
    m = _man()
    s = b.samples(m, _caps(m), tmp_path)
    assert len(s) == 6 and sum("ctrl_img" in x for x in s) == 1
    assert sum(not x["prompt"].startswith(b.TRIGGER) for x in s) == 1


def test_config_is_the_agreed_one():
    cfg = yaml.safe_load((POD / "xworld_v1.yaml").read_text(encoding="utf-8"))
    p = cfg["config"]["process"][0]
    assert p["model"]["name_or_path"] == "Qwen/Qwen-Image-2.1" and p["model"]["arch"] == "qwen_image_2"
    assert p["network"]["linear"] == 16 and float(p["train"]["lr"]) == 1e-4 and p["train"]["steps"] == 2500
    assert p["save"]["save_every"] == 250 and p["sample"]["sample_every"] == 250
    assert p["datasets"][1]["control_path"] == ["/workspace/ds/pairs/control"]
    sh = (POD / "xworld_v1.sh").read_text(encoding="utf-8")
    assert "captions_reviewed.jsonl" in sh and "BAD_HOST" in sh and "qwen_image_2" in sh


def test_prompt_type_test_jobs_keep_d_and_t_first_and_chain_refs():
    from explainer_engine.training.pods import xworld_v1_test as t
    m = _man()
    j = t.jobs(m, _caps(m))
    assert len(j) == 2 * 5 * (2 * len(t.LORA_VARIANTS) + len(t.BASE_VARIANTS))   # 2 chains of 6+ frames here
    assert [x["variant"] for x in j[:10]] == ["D"] * 10 and j[10]["variant"] == "T"
    t_jobs = [x for x in j if x["variant"] == "T" and x["lora"] == "A" and x["chain"] == 0]
    assert t_jobs[0]["refs"][0].startswith("real:") and t_jobs[1]["refs"] == [f"drawn:{t_jobs[0]['name']}"]
    assert all(x["truth"] not in [r[5:] for r in x["refs"]] for x in j)   # the frame to draw is never given
    assert "Change from the previous shot" not in t.prompt("V4", "a garage.", "Change from the previous shot: x.")
