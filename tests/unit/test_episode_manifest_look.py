"""TD-335: ``episode.json`` ``look`` is either the two sentences written in the episode (as before) or ``{"preset": name}``
(the main-style amendment of 2026-11-12); the manifest loaders resolve the preset after the schema, so an unknown preset still
stops the load."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import context as C

ROOT = Path(__file__).resolve().parents[2]
TRUCE = ROOT / "episodes" / "ep_truce_1914"
TOBA = ROOT / "episodes" / "ep_toba"
SENT = "A sentence that is long enough for a look."


def _man(look):
    m = json.loads((TRUCE / "episode.json").read_text(encoding="utf-8"))
    m = copy.deepcopy(m)
    m["look"] = look
    return m


def test_the_preset_form_passes_and_the_episode_loads():
    C.validate_manifest(_man({"preset": "crossworld_main_style_v1"}))
    assert C.load_episode_context(TRUCE).episode_id == "ep_truce_1914"


def test_the_two_sentence_form_still_passes():
    C.validate_manifest(_man({"style_sentence": SENT, "face_sentence": SENT, "approved_by_creator": "2026-11-12"}))


def test_an_unknown_preset_stops_the_load():
    with pytest.raises(ContractError):
        C.validate_manifest(_man({"preset": "no_such_style"}))


def test_a_look_with_neither_form_fails():
    for bad in ({}, {"style_sentence": SENT}, {"face_sentence": SENT}, {"approved_by_creator": "x"}):
        with pytest.raises(jsonschema.ValidationError):
            C.validate_manifest(_man(bad))


def test_an_extra_key_fails_in_both_forms():
    with pytest.raises(jsonschema.ValidationError):
        C.validate_manifest(_man({"preset": "crossworld_main_style_v1", "style_sentence": SENT}))
    with pytest.raises(jsonschema.ValidationError):
        C.validate_manifest(_man({"style_sentence": SENT, "face_sentence": SENT, "colour": "red"}))
    with pytest.raises(jsonschema.ValidationError):
        C.validate_manifest(_man({"preset": ""}))


def test_a_short_preset_sentence_stops_the_load(monkeypatch):
    from explainer_engine.imagegen import turn_pack
    monkeypatch.setattr(turn_pack, "preset", lambda pid: {"style_sentence": "short", "face_sentence": SENT})
    with pytest.raises(ContractError):
        C.validate_manifest(_man({"preset": "crossworld_main_style_v1"}))
