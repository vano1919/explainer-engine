"""Draft style preset from reference frames: draft flag, empty font, loader refusal, determinism, roles, compare."""
import json

import numpy as np
import pytest
from PIL import Image

from explainer_engine.maps.maplibre_lane import preset_from_frames as pf
from explainer_engine.maps.maplibre_lane import render


def _frame(paper, ink, accent, size=(160, 120)):
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    arr[:] = paper
    arr[: size[1] // 3, : size[0] // 3] = ink
    arr[-size[1] // 4:, -size[0] // 3:] = accent
    return Image.fromarray(arr)


def _frames(n=4):
    return [_frame((226, 214, 180), (30, 26, 22), (170, 40, 30)) for _ in range(n)]


def test_frame_count_must_be_3_to_6():
    with pytest.raises(ValueError):
        pf.build_draft("x", _frames(2))
    with pytest.raises(ValueError):
        pf.build_draft("x", _frames(7))
    assert pf.build_draft("x", _frames(3))["draft"] is True
    assert pf.build_draft("x", _frames(6))["draft"] is True


def test_draft_flag_and_empty_font():
    d = pf.build_draft("x", _frames())
    assert d["draft"] is True and d["font"] == ""
    for key in ("map", "line", "hud", "finish", "palette_check", "proposal_notes"):
        assert key in d


def test_deterministic():
    assert pf.build_draft("x", _frames()) == pf.build_draft("x", _frames())


def test_roles_from_synthetic_colours():
    d = pf.build_draft("x", _frames())
    bg = pf._hex_lab(d["map"]["background"])
    ink = pf._hex_lab(d["hud"]["chip_bg"])
    assert bg[0] > 75 and ink[0] < 30                       # paper light, ink dark
    stroke = pf._hex_lab(d["line"]["stroke"])
    assert stroke[1] > 3                                    # warm accent found in the frames
    assert pf.delta_e(stroke, pf._hex_lab("#aa281e")) < 25
    assert pf._palette_problems(d) == []                    # palette_check passes


def test_cold_frames_fall_back_to_vermillion():
    frames = [_frame((220, 224, 228), (20, 24, 30), (70, 110, 150)) for _ in range(3)]
    d = pf.build_draft("x", frames)
    assert "vermillion" in d["proposal_notes"]["line_stroke_source"]
    assert pf._palette_problems(d) == []


def test_grid_from_file(tmp_path):
    path = tmp_path / "sheet.png"
    Image.new("RGB", (400, 300), (200, 200, 200)).save(path)
    assert len(pf.load_frames([path], (3, 2))) == 6
    with pytest.raises(ValueError):
        pf.load_frames([path, path], (3, 2))


def test_compare_identical_is_zero():
    d = pf.build_draft("x", _frames())
    rows = pf.compare_presets(d, d)
    assert rows and all(r.get("delta_e", 0) == 0 and r.get("difference", 0) == 0 for r in rows)


def test_compare_with_1917_film_lists_every_shared_colour():
    ref = json.loads((render.STYLES_DIR / "1917_film.json").read_text(encoding="utf-8"))
    rows = pf.compare_presets(pf.build_draft("x", _frames()), ref)
    fields = {r["field"] for r in rows}
    assert {"map.background", "line.stroke", "hud.counter_value", "finish.vignette"} <= fields


def test_loader_refuses_draft_and_empty_font(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "STYLES_DIR", tmp_path)
    d = pf.build_draft("tmp_draft", _frames())
    (tmp_path / "tmp_draft.json").write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="DRAFT"):
        render.load_style_preset("tmp_draft")
    d.pop("draft")
    (tmp_path / "tmp_draft.json").write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="empty font"):
        render.load_style_preset("tmp_draft")
    d["font"] = "'Liberation Serif', serif"
    (tmp_path / "tmp_draft.json").write_text(json.dumps(d), encoding="utf-8")
    assert render.load_style_preset("tmp_draft")["font"].startswith("'Liberation")


def test_existing_presets_still_load():
    assert render.load_style_preset("1917_film")["font"]
