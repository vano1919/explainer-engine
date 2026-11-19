"""Lanes test 2026-11-19 (a real map_action clip of the Flanders sector, a real still_25d clip): the gaps it found, each with a
focused test. Regional relief (the global raster drew a 46 km frame 40x enlarged), a side on a front line (both lines were the
same coral), a date chip (the map had no date element), the map laws on a v4.3 map_action plan, a resolution gate and a
restrained flow on a finished front line."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.maps import actions as MA
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, laws, plate, relief
from explainer_engine.production import relief_regional as RR

REPO = Path(__file__).resolve().parents[2]
PLACES = {"ypres": {"lon": 2.885, "lat": 50.85, "name": "Ypres"}, "mid": {"lon": 2.89, "lat": 50.77, "name": "Mid"},
          "south": {"lon": 2.88, "lat": 50.69, "name": "South"}, "hol": {"lon": 2.945, "lat": 50.81, "name": "Hol"},
          "fre": {"lon": 2.933, "lat": 50.70, "name": "Fre"}}
W, H, FPS = 320, 180, 24
VIEW = {"lon": 2.9, "lat": 50.77, "span_km": 46}
LINE = "Two armies dug in along the line and on Christmas Eve the guns went quiet."


def _script(actions, dur=4.0):
    shot = {"shot_id": "M1", "route": "map_action", "target_duration_seconds": dur, "audio_line_ids": ["L1"], "actions": actions,
            "map_view": VIEW}
    return shot, {"audio_lines": [{"line_id": "L1", "text": LINE}], "shots": [shot]}


def _fixture_relief(tmp_path, monkeypatch, regional=True):
    """A 1-degree global raster (as the other map tests) and, optionally, a fine regional hillshade over lon 2-4, lat 50-51."""
    rows, cols = np.mgrid[0:180, 0:360]
    Image.fromarray((128 + 100 * np.sin(cols / 9.0) * np.cos(rows / 7.0)).astype(np.uint8), "L").save(tmp_path / relief.RASTER_NAME)
    (tmp_path / "SR_HR.tfw").write_text("1.0\n0.0\n0.0\n-1.0\n-179.5\n89.5\n")
    if regional:
        reg = tmp_path / "regional"
        reg.mkdir()
        h, w = 400, 800    # 0.0025 degrees a pixel
        yy, xx = np.mgrid[0:h, 0:w]
        Image.fromarray((200 + 40 * np.sin(xx / 17.0) * np.cos(yy / 13.0)).astype(np.uint8), "L").save(reg / "t.tif")
        RR.write_world_file(reg / "t.tfw", 0.0025, -0.0025, 2.00125, 50.99875)
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path))
    relief._load.cache_clear()


# --- regional relief --------------------------------------------------------------------------------------------------------

def test_hillshade_is_flat_ground_grey_and_lit_from_the_north_west():
    flat = RR.hillshade(np.zeros((20, 20), np.float32), 30.0, 30.0, 3.0)
    assert np.allclose(flat, RR.FLAT, atol=1e-5)
    x = np.arange(60, dtype=np.float32)
    nw_facing = np.tile(-x * 5.0, (60, 1))     # the ground falls towards the east: its slope faces the sun's side... lit
    se_facing = np.tile(x * 5.0, (60, 1))
    a, b = RR.hillshade(nw_facing, 30.0, 30.0, 3.0)[30, 30], RR.hillshade(se_facing, 30.0, 30.0, 3.0)[30, 30]
    assert a != b and (a < RR.FLAT) != (b < RR.FLAT)    # one side brighter than flat ground, the other darker


def test_a_view_inside_the_regional_hillshade_uses_it_and_others_fall_back(tmp_path, monkeypatch):
    _fixture_relief(tmp_path, monkeypatch)
    inside = geo.View(2.9, 50.77, 46, 64, 36)
    outside = geo.View(40.0, 10.0, 46, 64, 36)
    straddling = geo.View(3.9, 50.77, 46, 64, 36)    # reaches past lon 4: not inside, so no half-fine plate
    assert relief.regional_for(inside) == tmp_path / "regional" / "t.tif"
    assert relief.regional_for(outside) is None and relief.regional_for(straddling) is None
    assert relief.km_per_px(inside) < 0.35 and abs(relief.km_per_px(outside) - 111.32 / 60.0) < 1e-9
    assert relief.source_id(inside) != relief.source_id(outside) and relief.source_id(inside).endswith("+t")
    got = relief.sample(inside)
    assert got.shape == (36, 64) and float(got.mean()) > 0.6          # the fine raster's grey (about 0.78), not the global one
    # the cache key follows the data the plate is drawn from
    twin = geo.View(2.9, 50.77, 46, 64, 36)
    assert plate.spec_hash(inside, shaded_relief=True) == plate.spec_hash(twin, shaded_relief=True)
    with_regional = plate.spec_hash(inside, shaded_relief=True)
    (tmp_path / "regional" / "t.tfw").rename(tmp_path / "t.hidden")
    assert plate.spec_hash(inside, shaded_relief=True) != with_regional


def test_without_a_regional_raster_the_global_one_is_used(tmp_path, monkeypatch):
    _fixture_relief(tmp_path, monkeypatch, regional=False)
    v = geo.View(2.9, 50.77, 46, 64, 36)
    assert relief.regional_for(v) is None and relief.source_id(v) == relief.SOURCE_ZIP_SHA256


def test_the_region_registry_names_whole_tiles_of_one_row():
    assert RR.REGIONS["flanders"]["tiles"] and all(len(t) == 2 for t in RR.REGIONS["flanders"]["tiles"])
    src = (REPO / "explainer_engine" / "maps" / "relief.py").read_text(encoding="utf-8")
    assert "urllib" not in src and "requests" not in src       # CMP-14: the download lives in production/, not in maps/


# --- a side on a front line, the date chip ------------------------------------------------------------------------------------

def _frames(actions, f_before, f_after):
    shot, script = _script(actions)
    p = MA.plan(shot, script, PLACES, FPS)
    p["drift"] = 0.0
    base = MA.Plate(p, W, H)
    return p, [np.asarray(MA.render_frame(p, f, base, W, H), dtype=np.int16) for f in (f_before, f_after)]


def test_a_front_line_takes_the_colour_and_mark_of_its_side(tmp_path, monkeypatch):
    _fixture_relief(tmp_path, monkeypatch)
    a = {"kind": "front_line", "at_word": "armies", "from": "ypres", "to": "south", "side": "a", "label": "British"}
    b = {"kind": "front_line", "at_word": "armies", "from": "hol", "to": "fre", "side": "b", "label": "German"}
    p, (_, end) = _frames([a, b], 0, 95)
    fa, fb = np.array(D.faction("a")), np.array(D.faction("b"))
    near = lambda c: (np.abs(end - c).sum(axis=2) < 24).sum()    # noqa: E731
    assert near(fa) > 40 and near(fb) > 40, "each side's line is drawn in its own faction token"
    assert [x["side"] for x in p["actions"]] == ["a", "b"]


def test_a_side_is_a_or_b_and_two_opposing_lines_need_two_sides():
    shot, script = _script([{"kind": "front_line", "at_word": "armies", "from": "ypres", "to": "south", "side": "c"}])
    with pytest.raises(ContractError, match="side"):
        MA.plan(shot, script, PLACES, FPS)
    two = [{"kind": "front_line", "at_word": "armies", "from": "ypres", "to": "south"},
           {"kind": "front_line", "at_word": "dug", "from": "hol", "to": "fre"}]
    shot, script = _script(two)
    found = laws.check_actions(MA.plan(shot, script, PLACES, FPS))
    assert any(f["rule"] == "CMP-06" for f in found)
    two[0]["side"], two[1]["side"] = "a", "b"
    shot, script = _script(two)
    assert not any(f["rule"] == "CMP-06" for f in laws.check_actions(MA.plan(shot, script, PLACES, FPS)))


def test_the_date_chip_comes_on_its_word_and_needs_its_text(tmp_path, monkeypatch):
    _fixture_relief(tmp_path, monkeypatch)
    shot, script = _script([{"kind": "date", "at_word": "Christmas", "label": "24-25 December 1914"},
                            {"kind": "pulse", "at_word": "guns", "from": "mid"}])
    p = MA.plan(shot, script, PLACES, FPS)
    d = next(a for a in p["actions"] if a["kind"] == "date")
    base = MA.Plate(p, W, H)
    before = np.asarray(MA.render_frame(p, d["start"] - 1, base, W, H), dtype=np.int16)
    after = np.asarray(MA.render_frame(p, d["end"], base, W, H), dtype=np.int16)
    changed = np.abs(after - before).max(axis=2) > 12
    ys, xs = np.nonzero(changed[: H // 4, : W // 2])
    assert len(xs) > 200 and not p["card"], "the chip sits top left on the map"
    shot, script = _script([{"kind": "date", "at_word": "Christmas"}, {"kind": "pulse", "at_word": "guns", "from": "mid"}])
    with pytest.raises(ContractError, match="date"):
        MA.plan(shot, script, PLACES, FPS)


def test_the_schema_knows_side_and_date():
    sch = json.loads((REPO / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    item = sch["$defs"]["ShotSpec"]["properties"]["actions"]["items"]["properties"]
    assert item["side"]["enum"] == ["a", "b"] and "date" in item["kind"]["enum"]


# --- the map laws on a map_action plan ---------------------------------------------------------------------------------------

def test_the_laws_run_on_a_map_action_plan():
    labels = [{"kind": "label", "at_word": w, "from": p} for w, p in
              (("Two", "ypres"), ("armies", "mid"), ("dug", "south"), ("in", "hol"))]
    shot, script = _script(labels)
    found = laws.check_actions(MA.plan(shot, script, PLACES, FPS))
    assert any(f["rule"] == "CMP-03" and "4 labels" in f["detail"] for f in found)
    assert any(f["rule"] == "CMP-04" for f in found)     # no read spine: the landing frames are estimated
    shot, script = _script(labels[:3])
    spine = [{"word": w, "start_frame": 3 * i} for i, w in enumerate(MA.shot_words(shot, script))]
    ok = laws.check_actions(MA.plan(shot, script, PLACES, FPS, spine))
    assert ok == []
    shot, script = _script([{"kind": "label", "at_word": "Christmas", "from": "mid", "label": "24 December 1914"}])
    assert any(f["rule"] == "CMP-13" for f in laws.check_actions(MA.plan(shot, script, PLACES, FPS)))


# --- the clip: a resolution gate and a living front line ------------------------------------------------------------------------

def test_the_clip_reports_a_soft_relief_and_a_sharp_one(tmp_path, monkeypatch):
    from explainer_engine.production.map_clip import render_action_map_clip
    acts = [{"kind": "pulse", "at_word": "Two", "from": "mid"}]
    shot, script = _script(acts, dur=1.0)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _fixture_relief(tmp_path / "a", monkeypatch, regional=False)
    soft = render_action_map_clip(shot, script, {"places": PLACES}, tmp_path / "soft.mp4", width=W, height=H, fps=FPS)
    g = {x["gate"]: x for x in soft["gates"]["gates"]}["map_relief_sharp"]
    assert g["status"] == "REVIEW" and g["measured"] > 3.0
    _fixture_relief(tmp_path / "b", monkeypatch)
    sharp = render_action_map_clip(shot, script, {"places": PLACES}, tmp_path / "sharp.mp4", width=W, height=H, fps=FPS)
    g = {x["gate"]: x for x in sharp["gates"]["gates"]}["map_relief_sharp"]
    assert g["status"] == "PASS" and g["measured"] <= 3.0 and sharp["relief_upsample_max"] < soft["relief_upsample_max"]


def test_a_finished_front_line_keeps_a_slow_flow(tmp_path, monkeypatch):
    _fixture_relief(tmp_path, monkeypatch)
    shot, script = _script([{"kind": "front_line", "at_word": "Two", "from": "ypres", "to": "south", "side": "a"}], dur=6.0)
    p = MA.plan(shot, script, PLACES, FPS)
    p["drift"] = 0.0
    base = MA.Plate(p, W, H)
    a = p["actions"][0]
    f0 = np.asarray(MA.render_frame(p, a["end"] + 4, base, W, H), dtype=np.int16)
    f1 = np.asarray(MA.render_frame(p, a["end"] + 16, base, W, H), dtype=np.int16)
    assert (np.abs(f1 - f0).max(axis=2) > 12).any(), "the dots on a finished line travel (restrained life)"
