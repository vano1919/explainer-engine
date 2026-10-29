"""The xworld_v1 caption pod (D-80, OR-21): every image described once, every pair gets a change line, no names, no trigger."""
from __future__ import annotations

from pathlib import Path

from explainer_engine.training.pods import caption_xworld_v1 as cap

M = {"train": {"single": [{"img": "frames/0001.png"}, {"img": "frames/0002.png"}],
               "scene_pairs": [{"a": "frames/0001.png", "b": "frames/0002.png"}],
               "inshot_pairs": [{"a": "inshot/0005_a.png", "b": "inshot/0005_b.png"}]},
     "hold_out": {"chains": [["frames/0009.png", "frames/0010.png", "frames/0011.png"]]}}


def test_every_image_once_and_every_pair_a_change_line():
    j = cap.jobs(M)
    d = [x["images"][0] for x in j if x["kind"] == "describe"]
    assert len(d) == len(set(d)) == 7
    c = [tuple(x["images"]) for x in j if x["kind"] == "change"]
    assert ("frames/0001.png", "frames/0002.png") in c and ("inshot/0005_a.png", "inshot/0005_b.png") in c
    assert ("frames/0009.png", "frames/0010.png") in c and len(c) == 4
    assert len({x["id"] for x in j}) == len(j)


def test_prompts_ban_names_style_and_text():
    for p in (cap.DESCRIBE, cap.CHANGE):
        assert "no names" in p.lower() or "never use names" in p.lower()
        assert "style" in p.lower()
    assert "xworld" not in cap.DESCRIBE.lower()   # the trigger is added at training time (OR-22: still his choice)


def test_problems_flags_names_length_and_prefix():
    assert "name:morty" in cap.problems("A boy, Morty, stands in a kitchen. " + "word " * 40, "describe")
    assert any(f.startswith("length:") for f in cap.problems("too short", "describe"))
    assert cap.problems("Change from the previous shot: the camera moves closer.", "change") == []
    assert "change_prefix" in cap.problems("The camera moves closer.", "change")


def test_pod_script_resumes_and_stops_at_the_end():
    sh = (Path(cap.__file__).with_suffix(".sh")).read_text(encoding="utf-8")
    assert "captions.jsonl" in sh and "--limit 8" in sh and "Qwen/Qwen3-VL-8B-Instruct" in sh
    assert cap.MODEL == "Qwen/Qwen3-VL-8B-Instruct"
