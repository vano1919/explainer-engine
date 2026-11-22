"""Owner rule (2026-11-22): Gemini Neon never makes pictures - it is expensive. The provider factory refuses it."""
import pytest

from explainer_engine.imagegen import providers


@pytest.mark.parametrize("name", ["neon", "gemini_neon", "gemini-neon"])
def test_neon_is_refused_as_an_image_provider(name):
    with pytest.raises(ValueError, match="Gemini Neon does not generate pictures"):
        providers.cls(name)
    with pytest.raises(ValueError, match="Gemini Neon does not generate pictures"):
        providers.get(name, root=None)


def test_the_known_image_providers_still_resolve():
    for name in ("bfl", "fal", "gemini"):
        assert providers.cls(name).__name__


def test_an_unknown_name_is_still_an_unknown_name_not_a_neon_refusal():
    with pytest.raises(ValueError, match="unknown image provider"):
        providers.cls("nonexistent")
