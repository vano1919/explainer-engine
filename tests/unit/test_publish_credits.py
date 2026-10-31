"""F5 (D-83: licences never block, they only add text): the description of the long video carries the CC BY credits of the library
items that ``sound_mix_manifest/2`` references, and nothing for CC0 or our own sounds. Free: a tmp library and a tmp episode."""
from __future__ import annotations

import json

import numpy as np
from test_youtube_publish import PUB, episode

from explainer_engine.audio import sfx_library
from explainer_engine.publish import plan as P
from explainer_engine.qa import publish_check as PC

TONE = (np.random.default_rng(1).standard_normal(4800) * 0.2).astype(np.float32)


def library(tmp_path):
    root = tmp_path / "lib"
    for name, lic in (("wind", {"status": "cc0", "note": "CC0 from a free library"}),
                      ("rain", {"status": "licensed", "note": "CC BY 4.0, Jane Doe", "attribution": "Rain loop by Jane Doe (CC BY 4.0), freesound.example/123"}),
                      ("creak", {"status": "licensed", "note": "CC-BY 3.0 by Rob Roe, freesound.example/9"}),
                      ("paid", {"status": "licensed", "note": "bought from a stock site; no credit asked"}),
                      ("tick", {"status": "own_procedural", "note": "ours"})):
        sfx_library.add(root, name=name, take=1, category="foley", tags=[name], rate=48000, samples=TONE,
                        source={"kind": "recorded" if name != "tick" else "procedural"}, licence=lic)
    return root


def with_sound(ep, refs):
    items = [{"id": f"b{k}", "ref": r} for k, r in enumerate(refs)]
    (ep / "audio").mkdir(exist_ok=True)
    (ep / "audio" / "sound_mix_manifest.json").write_text(json.dumps(
        {"schema": "sound_mix_manifest/2", "beds": items, "music": [], "spots": [], "cues": []}), encoding="utf-8")


def test_a_cc_by_item_is_credited_in_the_long_description_and_cc0_and_own_sounds_add_nothing(tmp_path):
    root, ep = library(tmp_path), episode(tmp_path)
    with_sound(ep, ["rain__v1", "creak__v1", "wind__v1", "paid__v1", "tick__v1", "not_in_library"])
    long = P.build(ep, library=root)["items"][0]["body"]["snippet"]["description"]
    assert "Sound credits" in long
    assert "Rain loop by Jane Doe (CC BY 4.0), freesound.example/123" in long          # the licence's own attribution line
    assert "creak__v1: CC-BY 3.0 by Rob Roe, freesound.example/9" in long               # no attribution field: the note names CC BY
    assert "wind" not in long and "tick" not in long and "bought from" not in long      # CC0, procedural, a licence that asks nothing
    assert long.startswith(PUB["description"])                                          # the creator's text first, credits appended


def test_a_cc0_only_job_has_no_credit_block_and_no_manifest_means_none(tmp_path):
    root, ep = library(tmp_path), episode(tmp_path)
    assert "Sound credits" not in P.build(ep, library=root)["items"][0]["body"]["snippet"]["description"]    # no sound manifest at all
    with_sound(ep, ["wind__v1", "tick__v1"])
    plan = P.build(ep, library=root)
    assert "Sound credits" not in plan["items"][0]["body"]["snippet"]["description"]
    assert P.credits_block(ep, {}, root) == ""
    assert all("Sound credits" not in i["body"]["snippet"]["description"] for i in plan["items"][1:])


def test_the_plan_with_credits_still_validates_and_a_licence_never_blocks(tmp_path):
    root, ep = library(tmp_path), episode(tmp_path)
    with_sound(ep, ["rain__v1"])
    plan = P.build(ep, library=root)
    long = plan["items"][0]["body"]["snippet"]["description"]
    assert not [f for f in plan["findings"] if f["severity"] == "FAIL"]                 # field limits hold (<, >, bytes)
    assert not [f for f in PC.check({**PUB, "description": long}, None, ep) if f["severity"] == "FAIL"]
    assert sfx_library.credit_line({"id": "x", "licence": {"status": "cc0", "note": "n"}}) is None
    assert sfx_library.credit_line({"id": "x", "licence": {"status": "licensed", "note": "Attribution required: A <b>"}}).startswith("x: ")
    assert "<" not in P.credits_block(ep, {}, _angle_library(tmp_path)) and ">" not in P.credits_block(ep, {}, _angle_library(tmp_path))


def _angle_library(tmp_path):
    root = tmp_path / "lib2"
    sfx_library.add(root, name="ang", take=1, category="foley", tags=["ang"], rate=48000, samples=TONE, source={"kind": "recorded"},
                    licence={"status": "licensed", "note": "x", "attribution": "Door by <Ann> (CC BY)"})
    ep = tmp_path / "ep"
    (ep / "audio").mkdir(parents=True, exist_ok=True)
    (ep / "audio" / "sound_mix_manifest.json").write_text(json.dumps({"beds": [{"ref": "ang__v1"}], "cues": []}), encoding="utf-8")
    return root
