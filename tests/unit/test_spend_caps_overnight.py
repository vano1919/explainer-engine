"""The overnight ceiling (the creator 2026-11-22: $20 in total for the night, every paid service): its lines may not pass
its max_usd, and the file's own night holds the Test Film v4 Modal line."""
import json

import pytest

from explainer_engine.core import spend_caps


def _file(tmp_path, monkeypatch, nights):
    p = tmp_path / "spend_caps.json"
    p.write_text(json.dumps({"overnight": nights}), encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(p))


def test_the_real_night_holds_its_modal_line_within_twenty_dollars():
    n = spend_caps.overnight("overnight_2026_11_23")
    assert n["max_usd"] == 20.0
    assert n["lines"]["test_film_v4_modal"]["modal_usd"] == 2.0


def test_lines_that_pass_the_night_ceiling_are_refused(tmp_path, monkeypatch):
    _file(tmp_path, monkeypatch, {"n": {"max_usd": 5.0, "lines": {"a": {"x_usd": 3.0}, "b": {"y_usd": 3.0}}}})
    with pytest.raises(spend_caps.OverCeiling, match="add up to 6"):
        spend_caps.overnight("n")


def test_lines_inside_the_ceiling_pass(tmp_path, monkeypatch):
    _file(tmp_path, monkeypatch, {"n": {"max_usd": 5.0, "lines": {"a": {"x_usd": 2.0}, "b": {"y_usd": 2.5}}}})
    assert spend_caps.overnight("n")["max_usd"] == 5.0


def test_a_night_not_in_the_file_is_refused(tmp_path, monkeypatch):
    _file(tmp_path, monkeypatch, {})
    with pytest.raises(spend_caps.OverCeiling, match="no overnight"):
        spend_caps.overnight("tomorrow")
