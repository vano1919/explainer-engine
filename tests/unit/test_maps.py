"""The map engine (explainer_engine/maps, docs/COMPENSATOR.md): the data, the letterless plate, the camera, the routes and the eight
map laws, each with a clean case and a case that breaks it."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.design import palette as PAL
from explainer_engine.maps import camera as CAM
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, laws, paths, plate, render, timeline
from explainer_engine.standards import sourced_rules as SR
from tests.unit import _comp

ROOT = Path(__file__).resolve().parents[2]
SPINE = _comp.spine()
VIEW = geo.View(25.0, 52.0, 2200, 160, 90)


def item(archetype="TACTICAL_UNIT_MANEUVER", **payload):
    s = _comp.spec(archetype, "t")
    s["payload"].update(payload)
    return s


def run(s, frames=_comp.MAP_FRAMES):
    tl, clock = timeline.build(s, SPINE, 0, frames)
    return tl, clock


def rules(findings):
    return {f["rule"] for f in findings}


# --- the data and the plate ----------------------------------------------------------------------------------------------------

def test_the_extract_is_the_pinned_one():
    pins = json.loads((ROOT / "explainer_engine" / "maps" / "data" / "SOURCES.json").read_text(encoding="utf-8"))
    blob = (ROOT / "explainer_engine" / "maps" / "data" / "ne50m.json.gz").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == pins["output"]["sha256"]
    ds = geo.dataset()
    assert len(ds["land"]) > 1000 and len(ds["rivers"]) > 100 and len(ds["borders"]) > 100 and len(ds["lakes"]) > 100
    assert set(pins["files"]) == {"ne_50m_land", "ne_50m_lakes", "ne_50m_rivers_lake_centerlines", "ne_50m_admin_0_boundary_lines_land"}


def test_water_and_land():
    assert geo.is_water(19.0, 56.0)           # the Baltic
    assert not geo.is_water(23.9, 54.9)       # inland Lithuania
    assert not geo.is_water(2.35, 48.85)      # Paris


def test_the_projection_round_trips_and_is_north_up():
    v = geo.View(24.0, 54.0, 100, 1920, 1080)
    x, y = v.to_px(24.0, 54.0)
    assert (round(float(x)), round(float(y))) == (960, 540)
    lon, lat = v.to_lonlat(*v.to_px(24.3, 54.2))
    assert abs(lon - 24.3) < 1e-9 and abs(lat - 54.2) < 1e-9
    assert v.to_px(24.0, 54.5)[1] < v.to_px(24.0, 54.0)[1]    # north is up
    assert abs(geo.distance_km(24, 54, 25, 54) - 65.5) < 1.0


def test_clipping_keeps_a_far_vertex_drawable():
    poly = geo.clip_polygon([(-1e6, -1e6), (1e6, -1e6), (1e6, 1e6), (-1e6, 1e6)], 0, 0, 10, 10)
    assert sorted(set(poly)) == [(0, 0), (0, 10), (10, 0), (10, 10)]
    pieces = geo.clip_line([(-5, 5), (15, 5)], 0, 0, 10, 10)
    assert pieces == [[(0.0, 5.0), (10.0, 5.0)]]
    assert geo.clip_line([(-5, -5), (-1, -1)], 0, 0, 10, 10) == []


def test_a_plate_renders_to_the_same_bytes_twice_and_changes_with_its_spec():
    a, b = D.png_bytes(plate.render_plate(VIEW)), D.png_bytes(plate.render_plate(VIEW))
    assert a == b
    assert plate.spec_hash(VIEW) == plate.spec_hash(geo.View(25.0, 52.0, 2200, 160, 90))
    assert plate.spec_hash(VIEW) != plate.spec_hash(geo.View(25.1, 52.0, 2200, 160, 90))
    assert D.png_bytes(plate.render_plate(geo.View(25.5, 52.0, 2200, 160, 90))) != a


def test_a_plate_has_no_letters_by_construction(monkeypatch):
    def no_text(*_a, **_k):
        raise AssertionError("a plate drew text (CMP-01)")
    monkeypatch.setattr(D.Canvas, "text", no_text)
    im = plate.render_plate(VIEW)
    assert im.size == (160, 90)
    src = (ROOT / "explainer_engine" / "maps" / "plate.py").read_text(encoding="utf-8")
    assert ".text(" not in src.replace("Canvas.text", "") and "ImageFont" not in src


@pytest.mark.skipif(not shutil.which("tesseract"), reason="OCR engine not installed here; the construction test above holds the line")
def test_ocr_finds_no_letters_on_a_plate(tmp_path):
    import subprocess
    p = tmp_path / "p.png"
    p.write_bytes(D.png_bytes(plate.render_plate(geo.View(25.0, 52.0, 2200, 1280, 720))))
    out = subprocess.run(["tesseract", str(p), "-", "--psm", "11"], capture_output=True, text=True).stdout
    assert len([c for c in out if c.isalpha()]) == 0


def test_the_plate_cache_is_named_by_its_hash(tmp_path):
    first = plate.save_plate(VIEW, tmp_path)
    stamp = first.stat().st_mtime_ns
    assert plate.save_plate(VIEW, tmp_path) == first and first.stat().st_mtime_ns == stamp
    assert plate.spec_hash(VIEW)[:16] in first.name


def test_a_painted_plate_needs_its_certificate(tmp_path):
    p = tmp_path / "painted.png"
    p.write_bytes(D.png_bytes(plate.render_plate(VIEW)))
    assert plate.certificate_findings(p, None)
    cert = plate.certificate(p, 0, 0.99, "tesseract 5")
    assert plate.certificate_findings(p, cert) == []
    assert plate.certificate_findings(p, {**cert, "ocr_chars": 4})
    assert plate.certificate_findings(p, {**cert, "geometry_iou": 0.5})
    p.write_bytes(p.read_bytes() + b"x")
    assert plate.certificate_findings(p, cert)          # repainted: the old certificate is for another file


def test_the_land_mask_of_a_plate_is_its_own_land():
    mask = plate.land_mask(VIEW)
    assert 0.2 < mask.mean() < 0.95 and plate.iou(mask, mask) == 1.0
    assert plate.iou(mask, ~mask) == 0.0


# --- the camera, the routes, the easing ---------------------------------------------------------------------------------------

def test_tiers_follow_the_registry_widths():
    assert [CAM.tier_of(s) for s in (3000, 2000, 300, 50, 8, 1.5)] == ["macro", "macro", "meso", "meso", "micro", "micro"]


def test_a_move_is_eased_and_zooms_in_log_space():
    a, b = CAM.State(24, 54, 2000), CAM.State(25, 55, 50)
    m = [CAM.Move(100, 200, b)]
    assert CAM.state_at(a, m, 50) == a and CAM.state_at(a, m, 200) == b and CAM.state_at(a, m, 999) == b
    mid = CAM.state_at(a, m, 150)
    assert abs(mid.span_km - (2000 * 50) ** 0.5) < 1e-6 and abs(mid.lon - 24.5) < 1e-9
    assert CAM.state_at(a, m, 110).span_km > 1900          # a slow start


def test_the_march_starts_slow_cruises_and_halts():
    us = np.linspace(0, 1, 1001)
    p = np.array([D.march(u) for u in us])
    assert p[0] == 0 and abs(p[-1] - 1) < 1e-9 and (np.diff(p) >= -1e-12).all()
    speed = np.diff(p) * 1000
    assert speed[5] < 0.1 * speed[500] and speed[-5] < 0.1 * speed[500]      # slow start, soft halt
    assert abs(speed[400] - speed[600]) < 1e-6                              # a constant cruise


def test_zdepth_and_tilt():
    z = np.asarray(CAM.zdepth(40, 30, 45))
    assert z[0, 0] < z[-1, 0] and (np.diff(z[:, 0].astype(int)) >= 0).all()
    im = Image.new("RGB", (64, 36), (200, 200, 200))
    assert CAM.tilt(im, 0) is im and CAM.tilt(im, 45).size == (64, 36)


# --- law 1: no diffusion maps ----------------------------------------------------------------------------------------------------

def test_law1_a_map_is_never_generated(tmp_path):
    s = item()
    assert laws.no_diffusion(s, tmp_path) == []
    bad = item(model_id="x")
    assert rules(laws.no_diffusion(bad, tmp_path)) == {"CMP-01"}
    painted = item(base={"kind": "plate", "ref": "p.png", "certificate": "p.cert.json", "view": {"lon": 25, "lat": 52, "span_km": 2200}})
    assert "missing" in laws.no_diffusion(painted, tmp_path)[0]["detail"]
    (tmp_path / "p.png").write_bytes(D.png_bytes(plate.render_plate(VIEW)))
    assert "certificate" in laws.no_diffusion(painted, tmp_path)[0]["detail"]
    (tmp_path / "p.cert.json").write_text(json.dumps(plate.certificate(tmp_path / "p.png", 0, 0.99, "t")), encoding="utf-8")
    assert laws.no_diffusion(painted, tmp_path) == []
    (tmp_path / "p.cert.json").write_text(json.dumps(plate.certificate(tmp_path / "p.png", 7, 0.99, "t")), encoding="utf-8")
    assert "letters" in laws.no_diffusion(painted, tmp_path)[0]["detail"]


def test_a_certified_painted_plate_is_a_base_the_renderer_uses(tmp_path):
    view = geo.View(24.4, 54.8, 300, 640, 360)
    (tmp_path / "p.png").write_bytes(D.png_bytes(plate.render_plate(view)))
    s = {**_comp.spec("TACTICAL_UNIT_MANEUVER", "t"), "width": 160, "height": 90}
    s["payload"]["camera"] = {"start": {"lon": 24.4, "lat": 54.8, "span_km": 300}, "moves": []}
    s["payload"]["base"] = {"kind": "plate", "ref": "p.png", "view": {"lon": 24.4, "lat": 54.8, "span_km": 300}}
    s["payload"]["focus"] = None
    s["events"] = []
    tl, clock = run(s)
    painted = render.render_frame(s, tl, clock, 0, 1, tmp_path)
    s["payload"]["base"] = {"kind": "vector"}
    vector = render.render_frame(s, tl, clock, 0, 1, tmp_path)
    assert np.abs(np.asarray(painted, dtype=int) - np.asarray(vector, dtype=int)).mean() < 14


# --- law 2: terrain paths -------------------------------------------------------------------------------------------------------

def test_law2_routes_follow_the_land():
    good = {"waypoints": [[23.5, 54.9], [24.4, 54.8], [25.3, 54.7]], "ease": "march"}
    assert paths.validate(good) == []
    assert "ease" in paths.validate({**good, "ease": "linear"})[0]["detail"]
    sea = {"waypoints": [[20.0, 56.0], [10.0, 56.0]], "ease": "march"}
    assert "sea" in paths.validate(sea)[0]["detail"]
    ring = [[24.0, 54.6], [24.8, 54.6], [24.8, 55.0], [24.0, 55.0]]
    assert "no-go" in paths.validate({**good, "no_go": [ring]})[0]["detail"]
    s = item(routes=[{"id": "r1", "side": "a", "waypoints": sea["waypoints"], "ease": "linear"}])
    assert rules(laws.terrain_paths(s)) == {"CMP-02"} and len(laws.terrain_paths(s)) == 2
    assert laws.terrain_paths(item()) == []


def test_a_spline_passes_through_its_waypoints():
    wp = [[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]]
    curve = paths.spline(wp, 8)
    assert curve[0] == (0.0, 0.0) and curve[-1] == (2.0, 0.0) and (1.0, 1.0) in [(round(x, 9), round(y, 9)) for x, y in curve]


# --- law 3: signalling ------------------------------------------------------------------------------------------------------------

def test_law3_a_frame_stays_simple():
    s = item()
    tl, _ = run(s)
    assert laws.signalling(s, tl) == []
    many = item(labels=[{"id": f"l{i}", "text": "x", "lon": 24, "lat": 54.8, "class": "city"} for i in range(5)])
    many["events"] = [{"id": f"s{i}", "word_index": 2 * i, "op": "show_label", "target": f"l{i}", "frames": 6} for i in range(5)]
    tl, _ = run(many)
    found = laws.signalling(many, tl)
    assert any("5 labels" in f["detail"] for f in found) and rules(found) == {"CMP-03"}
    units = item(units=[{"id": f"u{i}", "side": "a", "route": "r1"} for i in range(5)])
    units["events"] = [{"id": f"s{i}", "word_index": 12 * i, "op": "show_unit", "target": f"u{i}", "frames": 6} for i in range(5)]
    tl, _ = run(units)
    assert any("5 unit groups" in f["detail"] for f in laws.signalling(units, tl))
    grouped = item(units=[{"id": f"u{i}", "side": "a", "group": "army", "route": "r1"} for i in range(5)])
    grouped["events"] = units["events"]
    tl, _ = run(grouped)
    assert not any("unit groups" in f["detail"] for f in laws.signalling(grouped, tl))


def test_law3_one_change_at_a_time_and_an_active_area():
    s = item()
    s["events"][2]["frames"] = 400                     # the ring grows over the route
    tl, _ = run(s)
    assert any("same time" in f["detail"] for f in laws.signalling(s, tl))
    s2 = item(focus=None)
    tl, _ = run(s2)
    assert any("not dimmed" in f["detail"] for f in laws.signalling(s2, tl))


def test_law3_the_inactive_terrain_is_dimmed_and_the_changed_thing_flagged_first():
    s = {**item(), "width": 160, "height": 90}
    s["payload"]["camera"] = {"start": {"lon": 24.4, "lat": 54.8, "span_km": 300}, "moves": []}
    s["payload"]["focus"] = {"lon": 24.4, "lat": 54.8, "radius_km": 30}
    tl, clock = run(s)
    im = np.asarray(render.render_frame(s, tl, clock, 0, 1), dtype=float)
    centre, corner = im[45, 80].mean(), im[2, 2].mean()
    s["payload"]["focus"] = {"lon": 24.4, "lat": 54.8, "radius_km": 5000}
    full = np.asarray(render.render_frame(s, tl, clock, 0, 1), dtype=float)
    assert corner < full[2, 2].mean() * (1 - 0.3)        # about the registry's 40 % of the way to the night colour
    assert abs(centre - full[45, 80].mean()) < 2
    # the pulse: a ring closes in on the label in the frames before its event
    s["payload"]["focus"] = None
    s["events"] = [{"id": "e", "word_index": 10, "op": "show_label", "target": "l1", "frames": 6}]
    before = np.asarray(render.render_frame(s, tl, clock, 114, 1))
    far = np.asarray(render.render_frame(s, tl, clock, 60, 1))
    assert (before != far).any()


# --- law 4: word lock -------------------------------------------------------------------------------------------------------------

def test_law4_every_element_appears_on_a_word():
    s = item()
    tl, _ = run(s)
    assert laws.word_lock(s, tl, _comp.MAP_FRAMES) == []
    s["events"] = [e for e in s["events"] if e["op"] != "show_route"]
    tl, _ = run(s)
    found = laws.word_lock(s, tl, _comp.MAP_FRAMES)
    assert any("frame 1, frozen" in f["detail"] for f in found) and rules(found) == {"CMP-04"}
    s = item()
    tl, _ = run(s)
    assert any("after the item" in f["detail"] for f in laws.word_lock(s, tl, 100))
    s["events"] = []
    tl, _ = run(s)
    assert any("without a timed" in f["detail"] for f in laws.word_lock(s, tl, 100))


def test_events_start_on_the_first_frame_of_their_word():
    clock = timeline.WordClock(SPINE, 10)
    assert clock.frame_of(10) == 0 and clock.frame_of(12) == 24
    with pytest.raises(ValueError, match="before the item's trigger"):
        clock.frame_of(3)
    with pytest.raises(ValueError):
        clock.frame_of(10 ** 6)
    with pytest.raises(ValueError):
        timeline.WordClock(SPINE, 10 ** 6)


# --- law 5: scale progression ------------------------------------------------------------------------------------------------------

def test_law5_macro_then_meso_then_micro():
    s = item()
    tl, clock = run(s)
    assert laws.scale_progression(s, tl, clock) == []
    up = item()
    up["payload"]["camera"]["moves"][0]["span_km"] = 3000          # the camera climbs back out
    up["payload"]["camera"]["start"]["span_km"] = 10
    tl, clock = run(up)
    assert any("climbs" in f["detail"] for f in laws.scale_progression(up, tl, clock))


def test_law5_an_altitude_change_takes_four_to_eight_seconds():
    s = item()
    s["payload"]["camera"]["moves"][0]["to_word"] = s["payload"]["camera"]["moves"][0]["from_word"] + 2     # one second
    tl, clock = run(s)
    found = laws.scale_progression(s, tl, clock)
    assert any("takes 1.0 s" in f["detail"] for f in found) and rules(found) == {"CMP-05"}


def test_law5_the_camera_does_not_hold_for_long():
    s = item()
    s["payload"]["camera"]["moves"] = s["payload"]["camera"]["moves"][:1]
    tl, clock = run(s)
    assert any("holds one view" in f["detail"] for f in laws.scale_progression(s, tl, clock))


# --- law 6: faction colours ---------------------------------------------------------------------------------------------------------

def test_law6_colours_are_sides_never_literals():
    assert laws.faction_colours(item()) == []
    s = item()
    s["payload"]["units"][0]["color"] = "red"
    s["payload"]["routes"][0]["note"] = "#D93025"
    found = laws.faction_colours(s)
    assert len(found) == 2 and rules(found) == {"CMP-06"}


def test_law6_the_palette_pair_is_colour_blind_safe_and_marked():
    assert PAL.faction_findings() == []
    pal = PAL.load()
    close = copy.deepcopy(pal)
    close["tokens"]["faction_b"]["hex"] = "#2A7AEA"
    assert {f["check"] for f in PAL.faction_findings(close)} == {"faction_cvd"}
    same_mark = copy.deepcopy(pal)
    same_mark["faction_pairs"][0]["mark_b"] = "square"
    assert PAL.faction_findings(same_mark)[0]["check"] == "faction_mark"
    for vision in PAL.CVD:
        assert PAL.delta_e("#1A73E8", "#F55A24", vision) > SR.T("BP-144", "faction_delta_e_min")


def test_law6_the_two_sides_differ_by_shape_not_only_colour():
    masks = []
    for side in ("a", "b"):
        c = D.Canvas(40, 40, None, 1)
        D.marker(c, side, 20, 20, 10)
        masks.append(np.asarray(c.image())[..., 3] > 0)
    assert (masks[0] != masks[1]).sum() > 40
    for token in ("faction_a", "faction_b"):
        assert token in PAL.load()["fill_only"]


# --- law 7: map to scene ----------------------------------------------------------------------------------------------------------

def test_law7_the_map_hands_over_at_the_same_angle(tmp_path):
    s = _comp.spec("MAP_3D_TERRAIN_FLYOVER", "t")
    Path(tmp_path / "visual").mkdir()
    CAM.zdepth(40, 30, 45).save(tmp_path / "visual" / "zdepth.png")
    scene = {"cameras": [{"shot_id": "s9", "pos": [0, 0, 0], "yaw_deg": 0, "pitch_deg": 45, "fov_deg": 40}]}
    assert laws.map_to_scene(s, 24, scene, tmp_path) == []
    assert laws.map_to_scene(item(), 24) == []                       # no transition, no finding
    s["payload"]["camera"]["moves"][-1]["pitch_deg"] = 10
    assert any("ends at pitch" in f["detail"] for f in laws.map_to_scene(s, 24))
    s = _comp.spec("MAP_3D_TERRAIN_FLYOVER", "t")
    scene["cameras"][0]["pitch_deg"] = 20
    assert any("looks down at 20" in f["detail"] for f in laws.map_to_scene(s, 24, scene))
    s["payload"]["transition"].update({"zdepth_ref": None, "prelap_frames": 2})
    details = " ".join(f["detail"] for f in laws.map_to_scene(s, 24))
    assert "depth map" in details and "early" in details
    assert rules(laws.map_to_scene(s, 24, {"cameras": []})) == {"CMP-07"}


# --- law 8: stimulus window ---------------------------------------------------------------------------------------------------------

def test_law8_nothing_is_still_for_long():
    s = item()
    tl, clock = run(s)
    assert [f for f in laws.stimulus_window(s, tl, clock) if f["severity"] != "INFO"] == []
    s["events"] = s["events"][:2]
    s["payload"]["camera"]["moves"] = []
    tl, clock = run(s)
    found = laws.stimulus_window(s, tl, clock)
    assert found[0]["rule"] == "CMP-08" and found[0]["severity"] == "REVIEW" and "nothing changes" in found[0]["detail"]


# --- the date chip, the frames -----------------------------------------------------------------------------------------------------

def test_a_date_chip_when_time_advances():
    s = item(time_advances=True)
    s["events"] = [e for e in s["events"] if e["op"] != "date"]
    tl, _ = run(s)
    assert rules(laws.date_chip(s, tl)) == {"CMP-13"}
    assert laws.date_chip(item(time_advances=True), run(item())[0]) == []


def test_a_map_frame_is_a_pure_function_of_the_spec_and_the_frame():
    s = {**item(), "width": 160, "height": 90}
    tl, clock = run(s)
    a = [D.png_bytes(render.render_frame(s, tl, clock, f, 1)) for f in (0, 300, 400)]
    b = [D.png_bytes(render.render_frame(s, tl, clock, f, 1)) for f in (400, 0, 300)]
    assert a == [b[1], b[2], b[0]]
    assert len(set(a)) == 3


def test_only_the_laws_that_the_registry_numbers_read_the_registry():
    """CN-12: every threshold the maps read exists; every rule they cite is listed as enforced by them."""
    for name in ("laws", "camera", "render", "plate"):
        src = (ROOT / "explainer_engine" / "maps" / f"{name}.py").read_text(encoding="utf-8")
        for rid, key, _line in SR.threshold_reads(src):
            assert key in SR.rule(rid)["thresholds"], (name, rid, key)
            assert any(e.startswith(f"explainer_engine/maps/{name}.py") or e.startswith("explainer_engine/standards/craft_checklists")
                       for e in SR.rule(rid)["enforced_by"]), (name, rid)
