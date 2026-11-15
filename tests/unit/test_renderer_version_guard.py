"""Audit #29 guard: the 2.5D renderer's VERSION (part of every clip cache key) changes whenever its code changes."""
from __future__ import annotations

import importlib

from explainer_engine.production import directed25d as D25


def test_version_carries_a_code_hash():
    assert D25.VERSION.startswith("directed25d/") and len(D25.VERSION.split("-")[-1]) == 12
    assert D25.VERSION != "directed25d/0.1-p1"


def test_version_changes_when_the_code_changes(monkeypatch, tmp_path):
    src = (tmp_path / "directed25d.py")
    src.write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "living_fx.py").write_text("y = 1\n", encoding="utf-8")
    monkeypatch.setattr(D25, "__file__", str(src))
    a = D25._code_digest()
    src.write_text("x = 2\n", encoding="utf-8")
    assert D25._code_digest() != a
