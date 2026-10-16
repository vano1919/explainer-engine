"""Cast sprite prompts carry the universe thread (UR-22): the generator refuses a prompt without it."""

from __future__ import annotations

import pytest

from explainer_engine.edit import universe

LOOK = {"universe_thread": ", one single drawn universe: exaggerated shapes everywhere, thick ink outline"}


def test_sprite_prompt_has_the_thread_and_the_key_background():
    text = universe.sprite_prompt("Isaac Newton", "long curly wig, blue coat", "panic, clutching a prism", LOOK)
    assert "one single drawn universe" in text and "#00FF00" in text and "CARICATURE" in text


def test_a_prompt_without_the_thread_is_refused():
    with pytest.raises(ValueError):
        universe.assert_thread("a realistic man", LOOK)
    with pytest.raises(ValueError):
        universe.sprite_prompt("X", "y", "z", {})
