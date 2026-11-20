"""Spec section 7.2 (owner 2026-11-20 08:37 UTC: "words are not enough, Claude still skips"): the episode runner and the trial scripts call
``layer_gate.require_layers``, which raises; the only way past is the owner's recorded ``layer_waiver`` (D-84 pattern), never a flag.
These tests run the real gate (``real_layer_gate``); every other unit test gets a gate that passes. $0."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from _gov import ROOT
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN
from explainer_engine.governance import layer_gate as LG
from explainer_engine.governance import records
from test_owner_requirements import REG, entry, final, put, registry, rec_for, root  # noqa: F401 (root is a fixture)

MSG = "cmsg_01Hnu5zB86sjUj5GtTgaUkPW1oFAyBSLLgTCU7KMSLutpZ"
pytestmark = pytest.mark.usefixtures("real_layer_gate")


def write_layer(root, layer="L9", **kw):
    rec = final(rec_for("REQ-001"))
    rec.update(kw)
    (root / "docs" / "layers").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "layers" / f"{layer}.json").write_text(json.dumps(rec), encoding="utf-8")


def test_a_final_pass_record_lets_the_layer_through(root):
    put(root, registry(entry(1)))
    write_layer(root)
    assert LG.require_layers(("L9",), root=root) == []


@pytest.mark.parametrize("what", ["no record", "draft record"])
def test_a_layer_without_a_final_record_is_refused(root, what):
    put(root, registry(entry(1)))
    if what == "draft record":
        write_layer(root, state="draft")
    with pytest.raises(ContractError, match="L9"):
        LG.require_layers(("L9",), root=root)


def test_the_refusal_names_every_layer_and_the_owners_way_past(root):
    put(root, registry(entry(1)))
    with pytest.raises(ContractError) as e:
        LG.require_layers(("L9", "L10"), root=root)
    msg = str(e.value)
    assert "L9" in msg and "L10" in msg and "layer_waiver" in msg


def test_a_waiver_is_the_owners_recorded_word_for_one_layer_for_a_day(root):
    put(root, registry(entry(1)))
    records.add("layer_waiver", "L9", MSG, "go on with the pictures", root=root)
    notes = LG.require_layers(("L9",), root=root)
    assert "L9 waived by the owner" in notes[0] and MSG in notes[0]
    with pytest.raises(ContractError, match="L10"):                       # another layer is not covered by it
        LG.require_layers(("L9", "L10"), root=root)
    old = records.add("layer_waiver", "L10", MSG, "yesterday's word", root=root, now=time.time() - 25 * 3600)
    assert old["target"] == "L10"
    with pytest.raises(ContractError, match="L10"):                       # a day later he is asked again
        LG.require_layers(("L10",), root=root)


@pytest.mark.parametrize("target", ["*", "L9,L10", "9", "L"])
def test_a_waiver_cannot_be_a_wildcard(root, target):
    with pytest.raises(ValueError):
        records.add("layer_waiver", target, MSG, "all of them", root=root)


def test_a_waiver_needs_his_message_id_and_a_quote(root):
    with pytest.raises(ValueError):
        records.add("layer_waiver", "L9", "", "words", root=root)
    with pytest.raises(ValueError):
        records.add("layer_waiver", "L9", MSG, "  ", root=root)


def test_a_waiver_does_not_open_a_missing_registry(root):
    records.add("layer_waiver", "L9", MSG, "go on", root=root)
    with pytest.raises(ContractError, match="REG-MISSING"):               # deleting the registry never opens a layer
        LG.require_layers(("L9",), root=root)


def test_a_broken_registry_refuses_even_a_waived_layer(root):
    put(root, registry(entry(1, words="")))
    records.add("layer_waiver", "L9", MSG, "go on", root=root)
    with pytest.raises(ContractError, match="REG-FIELDS"):
        LG.require_layers(("L9",), root=root)


def test_every_runner_stage_has_its_layers_and_every_layer_is_known():
    assert set(LG.STAGE_LAYERS) == set(RUN.STAGES)
    for stage, layers in LG.STAGE_LAYERS.items():
        assert layers and all(layer in LG.GROUP_OF for layer in layers), stage


def test_the_runner_refuses_a_stage_whose_layers_are_not_final(monkeypatch, tmp_path):
    ep = SimpleNamespace(root=tmp_path)
    monkeypatch.setattr(LG, "root_dir", lambda r=None: tmp_path)           # a repo with no registry and no records
    with pytest.raises(RUN.StageRefused, match="layer gate"):
        RUN.run_stage(ep, "pictures")


def test_a_trial_script_refuses_before_it_reserves_or_writes(monkeypatch, tmp_path):
    from explainer_engine.training.pods.ltx import scene_run as SR
    monkeypatch.setattr(LG, "root_dir", lambda r=None: tmp_path)
    out = tmp_path / "spec.json"
    with pytest.raises(SystemExit, match="refused"):
        SR.main(["job", str(tmp_path / "scene.json"), str(out)])
    assert not out.exists()
    with pytest.raises(SystemExit, match="refused"):
        SR.main(["reserve", str(tmp_path / "scene.json")])


def test_the_committed_repo_refuses_today_because_no_layer_is_final():
    with pytest.raises(ContractError):
        LG.require_stage("pictures", root=ROOT)
