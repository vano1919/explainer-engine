"""The Napoleon example two ways (ICW-02): ``examples/napoleon_vs_genghis/film_shots.json`` is the film_shots/3 cards of the
Ink Chronicle path; ``legacy_cards()`` rebuilds the same shot list as film_shots/1 in memory, the worked example of the
legacy prompt composer (D-80), so the composer's tests keep their real 214-shot episode. ``migration()`` is the one
film_shots/3 migration (``scripts/migrate_film_shots_2_to_3.py``)."""

from __future__ import annotations

import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAPOLEON = ROOT / "examples" / "napoleon_vs_genghis"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=None)
def migration():
    return _load("migrate_film_shots_2_to_3", ROOT / "scripts" / "migrate_film_shots_2_to_3.py")


@lru_cache(maxsize=None)
def _builder():
    return _load("napoleon_build_cards", NAPOLEON / "build_cards.py")


@lru_cache(maxsize=None)
def _legacy() -> dict:
    return _builder().legacy_cards()


def legacy_cards() -> dict:
    """A fresh copy of the film_shots/1 cards (tests may edit it)."""
    return copy.deepcopy(_legacy())


def cards_v3() -> dict:
    """The film_shots/3 cards as build_cards.py writes them (the migration of ``legacy_cards``)."""
    return _builder().cards()[0]
