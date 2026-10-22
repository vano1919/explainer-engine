"""Image providers behind one interface (D-70 stage D): ``get(name)`` returns an adapter with ``estimate``, ``generate``
and ``edit``; prices, reference limits and model versions are data on the adapter. New providers are added here, never by
teaching ``paint.py`` another API."""
from __future__ import annotations

from explainer_engine.imagegen.providers.base import ChargeUncertain, ImageProvider, ProviderError, Result  # noqa: F401


def cls(name: str) -> type[ImageProvider]:
    """The adapter class (prices, limits, versions as class data; no folder is made, no key is read)."""
    if name == "bfl":
        from explainer_engine.imagegen.providers.bfl import BFL
        return BFL
    if name == "fal":
        from explainer_engine.imagegen.providers.fal import Fal
        return Fal
    if name == "gemini":
        from explainer_engine.imagegen.providers.gemini_adapter import Gemini
        return Gemini
    raise ValueError(f"unknown image provider {name!r}; known: bfl, fal, gemini")


def get(name: str, **kw) -> ImageProvider:
    if name == "bfl":
        from explainer_engine.imagegen.providers.bfl import BFL
        return BFL(**kw)
    if name == "fal":
        from explainer_engine.imagegen.providers.fal import Fal
        return Fal(**kw)
    if name == "gemini":
        from explainer_engine.imagegen.providers.gemini_adapter import Gemini
        return Gemini(**kw)
    raise ValueError(f"unknown image provider {name!r}; known: bfl, fal, gemini")
