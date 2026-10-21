"""Story cards (design/cards.py, the creator 2026-10-21): a dark title card with the heroes' heads, recap boards with signs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.design import cards as C

SCHEMA = json.loads((C.ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))


def _portrait(tmp_path: Path, name: str) -> Path:
    im = Image.new("RGB", (400, 300), (90, 120, 160))
    ImageDraw.Draw(im).ellipse([170, 80, 230, 160], fill=(230, 190, 160))
    p = tmp_path / f"{name}.png"
    im.save(p)
    return p


@pytest.fixture
def faces(monkeypatch):
    monkeypatch.setattr(C, "face_box", lambda picture, prefer_x=None: (0.5, 0.4, 0.15, 0.27))


def test_the_board_is_dark_but_not_black():
    a = np.asarray(C.background("night")).astype(float)
    assert 20 < a.mean() < 90  # dark, never the black screen the creator turned down


def test_a_title_card_draws_the_question_and_every_head(tmp_path, faces):
    for h in ("a", "b", "c"):
        _portrait(tmp_path, f"p_{h}")
    spec = {"kind": "title", "title": "What if they lost everything?",
            "heroes": [{"picture": f"p_{h}", "name": h} for h in ("a", "b", "c")]}
    a = np.asarray(C.title_card(spec, [tmp_path])).astype(int)
    assert a.shape[:2] == (C.SIZE[1], C.SIZE[0])
    skin = (abs(a[..., 0] - 230) < 12) & (abs(a[..., 1] - 190) < 12) & (abs(a[..., 2] - 160) < 12)
    assert skin[int(C.SIZE[1] * 0.35):].sum() > 3 * 2000  # three faces under the title


def test_recap_rows_take_a_head_or_a_sign_and_rings_land_on_them(tmp_path, faces):
    _portrait(tmp_path, "p_a")
    spec = {"kind": "recap", "title": "Year two: the score", "next": "year three",
            "rows": [{"picture": "p_a", "icon": "car", "text": "the car"}, {"icon": "battery", "text": "cells on a shelf"},
                     {"icon": "flame", "text": "the garage"}]}
    im = C.recap_card(spec, [tmp_path])
    pts = C.row_points(spec)
    assert len(pts) == 3 and all(0 < x < 1 and 0 < y < 1 for x, y in pts)
    a = np.asarray(im).astype(int)
    board = a[C.SIZE[1] // 2, C.SIZE[0] // 2 - 40].sum()
    for x, y in pts:  # each point is inside its head or sign (paper or a face), well off the dark board
        px, py = int(x * C.SIZE[0]), int(y * C.SIZE[1])
        assert a[py, px].sum() > board + 150


def test_cards_and_card_lines_are_in_the_schema():
    assert SCHEMA["properties"]["cards"]["items"]["properties"]["kind"]["enum"] == ["title", "recap"]
    line = SCHEMA["properties"]["segments"]["items"]["properties"]["lines"]["items"]["properties"]
    assert line["card"]["type"] == "boolean"


def test_the_titans_episode_opens_on_its_title_card_and_recaps_four_chapters():
    doc = json.loads((C.ROOT / "examples" / "titans_from_zero" / "production_script.json").read_text(encoding="utf-8"))
    kinds = [c["kind"] for c in doc["cards"]]
    assert kinds == ["title", "recap", "recap", "recap", "recap"]
    first = doc["segments"][0]["shots"][0]["picture"]
    assert first["id"] == "card_intro" and first["engine"] == "existing"
    assert not any(ln.get("speaker") for s in doc["segments"] for ln in s["lines"])  # one narrator reads every line
