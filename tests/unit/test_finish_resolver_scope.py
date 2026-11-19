"""W7: UR-22..27 apply to the legacy ink route only; a v4.3 new-style prompt is checked by validators/prompts.py."""
from __future__ import annotations

import pytest

from explainer_engine.world import resolver as R

NEW_STYLE = ("A 35mm lens at f/2.8, shallow depth of field: Thomas Hale in a peaked cap stands in a flooded trench at dusk, "
             "mud on his coat, one hand raised.")


def _world():
    return R.resolve({"topic": "t", "host": {"era": next(iter(R.load_codex()["eras"])), "place": "p", "when": "w", "landscape": []}})


def test_a_new_style_prompt_fails_the_legacy_lint_by_design():
    found = R.check_text(NEW_STYLE, _world())
    assert {"UR-22", "UR-26"} <= {f["rule"] for f in found}   # no look thread, no light key: the legacy contract


def test_a_new_style_prompt_is_not_judged_by_ur_rules_on_the_v43_route():
    assert R.check_prompt(NEW_STYLE, R.NEW_STYLE_ROUTE) == []


def test_the_v43_route_still_catches_a_slop_word_through_validators_prompts():
    found = R.check_prompt("A masterpiece, 8k, ultra detailed trench at dusk with mud on the coat", R.NEW_STYLE_ROUTE)
    assert found and all(f["rule"] == "VAL-PRM-01" and not f["rule"].startswith("UR-") for f in found)


def test_the_legacy_route_goes_through_the_ur_lint_and_needs_a_world():
    world = _world()
    assert R.check_prompt(NEW_STYLE, R.LEGACY_ROUTE, world) == R.check_text(NEW_STYLE, world)
    with pytest.raises(ValueError):
        R.check_prompt(NEW_STYLE, R.LEGACY_ROUTE)


def test_an_unknown_route_is_an_error_not_a_pass():
    with pytest.raises(ValueError):
        R.check_prompt(NEW_STYLE, "mystery")


def test_ur_rule_ids_are_the_legacy_set():
    assert R.UR_RULES == tuple(f"UR-{n}" for n in range(22, 28))
