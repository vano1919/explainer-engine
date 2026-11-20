"""G-06: the map lane takes its style only from the episode film (owner rule 2026-11-20: every episode has its own film)."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import pytest
from explainer_engine.maps import maplibre_spec as S
from explainer_engine.maps.maplibre_lane import render as R

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "episode_film" / "valid_film.json"
PAGE = Path(R.__file__).resolve().parent / "page.html"


def _film(tmp_path, style="1917_film", film_id="film_1917"):
    film = json.loads(FIXTURE.read_text(encoding="utf-8"))
    film["film_id"] = film_id
    film["map"]["style_preset"] = style
    film["counter"]["style_preset"] = style
    path = tmp_path / "episode_film.json"
    path.write_text(json.dumps(film), encoding="utf-8")
    return path


def _spec(**extra):
    spec = {"size": [1280, 704], "fps": 24, "seconds": 5, "center": [2.8, 50.9], "zoom": 8, "line_geojson": "l.geojson",
            "line_t": [0.5, 4.0], "counter": {"from": 0, "to": 10, "t0": 0.5, "t1": 4.0, "label": "x"}, "date_chip": [],
            "towns": [], "footnote": ""}
    spec.update(extra)
    return spec


def test_style_preset_and_film_id_come_from_the_film(tmp_path):
    f = _film(tmp_path)
    assert R.resolve_style_preset_name(_spec(film_file=str(f)), tmp_path) == ("1917_film", "film_1917")


def test_film_file_relative_to_the_spec_folder(tmp_path):
    _film(tmp_path)
    assert R.resolve_style_preset_name(_spec(film_file="episode_film.json"), tmp_path)[0] == "1917_film"


def test_missing_film_file_is_refused_and_no_browser_starts(tmp_path, monkeypatch):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_spec()), encoding="utf-8")
    monkeypatch.setattr(R, "sync_playwright", lambda: pytest.fail("the browser must not start without a film"))
    with pytest.raises(S.ShotSpecError, match="film_file is required"):
        R.render_shot(str(p), str(tmp_path / "o.mp4"), str(tmp_path), str(tmp_path / "w"))


def test_spec_preset_that_differs_from_the_film_is_refused(tmp_path):
    f = _film(tmp_path)
    with pytest.raises(S.ShotSpecError) as err:
        R.resolve_style_preset_name(_spec(film_file=str(f), style_preset="neutral"), tmp_path)
    assert "neutral" in str(err.value) and "1917_film" in str(err.value)


def test_spec_preset_equal_to_the_film_is_fine(tmp_path):
    f = _film(tmp_path)
    assert R.resolve_style_preset_name(_spec(film_file=str(f), style_preset="1917_film"), tmp_path)[0] == "1917_film"


def test_invalid_film_becomes_a_shot_spec_error_with_the_problem(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(S.ShotSpecError):
        R.resolve_style_preset_name(_spec(film_file=str(bad)), tmp_path)
    film = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del film["map"]
    bad.write_text(json.dumps(film), encoding="utf-8")
    with pytest.raises(S.ShotSpecError, match="map"):
        R.resolve_style_preset_name(_spec(film_file=str(bad)), tmp_path)


def test_no_default_preset_any_more():
    assert not hasattr(R, "DEFAULT_STYLE_PRESET")
    with pytest.raises(TypeError):
        R._validate_hud_palette(None)


def test_font_is_absent_or_preset_only(tmp_path):
    f = _film(tmp_path)
    for ok in ({}, {"font": "preset"}):
        assert R.resolve_style_preset_name(_spec(film_file=str(f), **ok), tmp_path)[0] == "1917_film"
    with pytest.raises(S.ShotSpecError, match="font comes from the film preset"):
        R.resolve_style_preset_name(_spec(film_file=str(f), font="Inter"), tmp_path)


def test_validate_shot_spec_checks_film_file_type():
    base = _spec()
    assert not [p for p in S.validate_shot_spec(base) if "film_file" in p]
    for bad in ("", 5):
        probs = S.validate_shot_spec({**copy.deepcopy(base), "film_file": bad})
        assert "film_file must be a non-empty string" in probs


def test_render_result_names_film_id_and_style(tmp_path):
    # the return dict carries film_id and style_preset (checked on the source: the render itself needs a browser)
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert '"film_id": film_id' in src and '"style_preset": preset["name"]' in src


def test_page_has_no_look_of_its_own():
    html = PAGE.read_text(encoding="utf-8")
    assert "no style preset: this page has no look of its own" in html
    assert "P ?" not in html and '"Inter"' not in html and "#f0f0eb" not in html
    assert "cfg.preset.font" in html


def test_preset_without_finish_tint_is_refused(tmp_path, monkeypatch):
    preset = json.loads((R.STYLES_DIR / "1917_film.json").read_text(encoding="utf-8"))
    for dotted in ("tint", "grain", "vignette"):
        broken = copy.deepcopy(preset)
        del broken["finish"][dotted]
        (tmp_path / "broken.json").write_text(json.dumps(broken), encoding="utf-8")
        monkeypatch.setattr(R, "STYLES_DIR", tmp_path)
        with pytest.raises(ValueError, match=f"finish.{dotted}"):
            R.load_style_preset("broken")


def test_page_has_no_finish_of_its_own():
    html = PAGE.read_text(encoding="utf-8")
    assert '{ color: "#000", opacity: 0 }' not in html and "|| 256" not in html
    assert "has no finish of its own" in html
