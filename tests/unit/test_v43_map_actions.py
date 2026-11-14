"""v4.3 plan P4 (Q6): real relief (no invented terrain), map type that is not a comic face, and an action layer that lands on
its word, anchored in lon/lat. Each action kind has its own check (nothing before its word, something after, the same pixels
on a second render); the plate is a small fixture raster, so no download is needed."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.maps import actions as MA
from explainer_engine.maps import camera as CAM
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, plate, relief

REPO = Path(__file__).resolve().parents[2]
PLACES = {"toba": {"lon": 98.88, "lat": 2.68, "name": "Toba"}, "shinfa": {"lon": 36.0, "lat": 12.8, "name": "Shinfa-Metema"},
          "india": {"lon": 78.1, "lat": 15.3, "name": "Jwalapuram"}}
W, H, FPS = 320, 180, 24


@pytest.fixture()
def raster(tmp_path, monkeypatch):
    """A 1-degree world raster with a smooth, known pattern, georeferenced like SR_HR (pixel centres)."""
    rows, cols = np.mgrid[0:180, 0:360]
    arr = (128 + 100 * np.sin(cols / 9.0) * np.cos(rows / 7.0)).astype(np.uint8)
    Image.fromarray(arr, "L").save(tmp_path / relief.RASTER_NAME)
    (tmp_path / "SR_HR.tfw").write_text("1.0\n0.0\n0.0\n-1.0\n-179.5\n89.5\n")
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path))
    relief._load.cache_clear()
    yield arr
    relief._load.cache_clear()


def _script(text="The killer lay four thousand miles away in the ash.", dur=4.0, actions=None, view=None):
    shot = {"shot_id": "M1", "route": "map_action", "target_duration_seconds": dur, "audio_line_ids": ["L1"],
            "actions": actions or []}
    if view:
        shot["map_view"] = view
    return shot, {"audio_lines": [{"line_id": "L1", "text": text}], "shots": [shot]}


def _render(shot, script, f, places=PLACES):
    p = MA.plan(shot, script, places, FPS)
    base = MA.card_base(W, H) if p["card"] else MA.Plate(p, W, H)
    return p, np.asarray(MA.render_frame(p, f, base, W, H), dtype=np.int16)


def test_relief_samples_the_raster_where_the_view_is(raster):
    v = geo.View(0.0, 0.0, 2000, 40, 22)
    got = relief.sample(v)
    lon, lat = v.to_lonlat(20.5, 11.5)
    want = raster[int(round(89.5 - float(lat))), int(round(float(lon) + 179.5))] / 255.0
    assert got.shape == (22, 40) and abs(float(got[11, 20]) - want) < 0.03


def test_relief_without_the_raster_refuses_and_never_invents_terrain(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path / "none"))
    relief._load.cache_clear()
    with pytest.raises(ConfigError, match="never invents"):
        plate.render_plate(geo.View(98.88, 2.68, 1200, W, H), shaded_relief=True)
    src = (REPO / "explainer_engine" / "maps" / "plate.py").read_text(encoding="utf-8")
    assert not hasattr(plate, "generate_regional_dem_grid") and "dist_toba" not in src and "barisan" not in src.lower()   # F6


def test_the_map_look_recolours_the_plate(raster):
    v = geo.View(98.88, 2.68, 1200, W, H)
    a = np.asarray(plate.render_plate(v, shaded_relief=True, ss=1))
    b = np.asarray(plate.render_plate(v, shaded_relief=True, ss=1, look={"sea": "night", "land": "kit_card"}))
    assert (a != b).any()
    assert plate.spec_hash(v, shaded_relief=True) != plate.spec_hash(v, shaded_relief=True, look={"sea": "night"})


def test_map_lettering_uses_the_map_face_not_the_comic_face():
    f = D.font(40, "map")
    assert "Inter" in " ".join(str(x) for x in f.getname())
    assert "Comic" in " ".join(str(x) for x in D.font(40).getname())


def test_tilt_leaves_no_empty_corner():
    im = Image.fromarray(np.random.default_rng(0).integers(0, 255, (H, W, 3)).astype("uint8"))
    out = np.asarray(CAM.tilt_fill(im, 40).convert("RGBA"))
    assert out.shape[:2] == (H, W) and out[..., 3].min() > 200


def test_an_action_must_land_on_a_spoken_word_and_a_known_place():
    shot, script = _script(actions=[{"kind": "pulse", "at_word": "volcano", "from": "toba"}])
    with pytest.raises(ContractError, match="spoken word"):
        MA.plan(shot, script, PLACES, FPS)
    shot, script = _script(actions=[{"kind": "pulse", "at_word": "killer", "from": "krakatoa"}])
    with pytest.raises(ContractError, match="krakatoa"):
        MA.plan(shot, script, PLACES, FPS)
    shot, script = _script(actions=[{"kind": "route_arrow", "at_word": "killer", "from": "toba"}])
    with pytest.raises(ContractError, match="'to'"):
        MA.plan(shot, script, PLACES, FPS)


def test_words_are_in_order_estimated_without_a_spine_and_measured_with_one():
    acts = [{"kind": "pulse", "at_word": "killer", "from": "toba"}, {"kind": "label", "at_word": "away", "from": "shinfa"}]
    shot, script = _script(actions=acts)
    p = MA.plan(shot, script, PLACES, FPS)
    assert p["basis"] == "estimated" and p["actions"][0]["start"] < p["actions"][1]["start"]
    words = MA.shot_words(shot, script)
    spine = [{"word": w, "start_frame": 2 * i} for i, w in enumerate(words)]
    m = MA.plan(shot, script, PLACES, FPS, spine)
    assert m["basis"] == "measured" and m["actions"][1]["start"] == 2 * words.index("away")
    with pytest.raises(ContractError):
        MA.plan(shot, script, PLACES, FPS, spine[:-1])


@pytest.mark.parametrize("act", [
    {"kind": "route_arrow", "at_word": "four thousand", "from": "toba", "to": "shinfa"},
    {"kind": "front_line", "at_word": "four thousand", "from": "toba", "to": "india"},
    {"kind": "spread", "at_word": "four thousand", "from": "toba", "value": 900},
    {"kind": "plume", "at_word": "four thousand", "from": "toba", "to": "india", "value": 700},
    {"kind": "pulse", "at_word": "four thousand", "from": "toba"},
    {"kind": "highlight", "at_word": "four thousand", "from": "toba", "value": 400},
    {"kind": "label", "at_word": "four thousand", "from": "shinfa"},
    {"kind": "counter", "at_word": "four thousand", "value": 4000, "unit": "miles"},
    {"kind": "split_compare", "at_word": "four thousand", "label": "summer | winter"},
], ids=lambda a: a["kind"])
def test_each_action_appears_on_its_word_and_renders_the_same_twice(raster, act):
    anchor = [{"kind": "label", "at_word": "killer", "from": "toba"}] if act["kind"] in ("counter", "split_compare") else []
    shot, script = _script(actions=anchor + [act], view={"lon": 67.0, "lat": 9.0, "span_km": 9500})
    p = MA.plan(shot, script, PLACES, FPS)
    p["drift"] = 0.0   # W3's restrained camera drift moves the whole frame; the locality check compares one view
    a = p["actions"][-1]
    base = MA.Plate(p, W, H)
    before = np.asarray(MA.render_frame(p, a["start"] - 1, base, W, H), dtype=np.int16)
    after = np.asarray(MA.render_frame(p, a["end"], base, W, H), dtype=np.int16)
    again = np.asarray(MA.render_frame(p, a["end"], base, W, H), dtype=np.int16)
    changed = np.abs(after - before).max(axis=2) > 12
    assert changed.mean() > 0.001, "the action draws nothing on its word"
    assert (after == again).all(), "a frame must be a pure function of its number (CMP-09)"
    if act["kind"] in ("pulse", "highlight", "label"):   # anchored: the change sits round the place
        x, y = geo.View(67.0, 9.0, 9500, W, H).to_px(PLACES[act["from"]]["lon"], PLACES[act["from"]]["lat"])
        ys, xs = np.nonzero(changed)
        assert np.hypot(xs.mean() - float(x), ys.mean() - float(y)) < W * 0.25


def test_a_front_line_with_cues_none_stands_whole_on_its_word(raster):
    """map_action/2.2: a line the viewer already knows (``cues: none``, silent by design) is not drawn stroke by stroke: it
    stands whole on its word."""
    view = {"lon": 67.0, "lat": 9.0, "span_km": 9500}
    line = {"kind": "front_line", "at_word": "four thousand", "from": "toba", "to": "india"}
    grown, landed = {}, {}
    for name, act in (("drawn", line), ("stands", dict(line, cues="none"))):
        shot, script = _script(actions=[act], view=view)
        p = MA.plan(shot, script, PLACES, FPS)
        p["drift"] = 0.0
        base = MA.Plate(p, W, H)
        a = p["actions"][0]
        fr = lambda f: np.asarray(MA.render_frame(p, f, base, W, H), dtype=np.int16)
        before, first, last = fr(a["start"] - 1), fr(a["start"]), fr(a["end"])
        landed[name] = (np.abs(first - before).max(axis=2) > 12).sum()
        grown[name] = (np.abs(last - first).max(axis=2) > 12).sum()
    assert landed["stands"] > 5 * max(1, landed["drawn"]), f"the line must be whole on its word: {landed}"
    assert grown["stands"] < 0.2 * grown["drawn"], f"a cues-none line does not grow after its word: {grown}"
    assert MA.RENDERER_VERSION == "map_action/2.2"


def test_zoom_moves_the_camera_to_its_place():
    shot, script = _script(actions=[{"kind": "zoom", "at_word": "killer", "to": "toba", "value": 1200}],
                           view={"lon": 67.0, "lat": 9.0, "span_km": 9500})
    p = MA.plan(shot, script, PLACES, FPS)
    assert MA.camera(p, 0) == p["view0"]
    end = MA.camera(p, p["frames"] - 1)
    assert abs(end["lon"] - 98.88) < 0.01 and abs(end["span_km"] - 1200) < 1


def test_a_shot_without_places_is_a_card_with_its_counter():
    shot, script = _script(actions=[{"kind": "counter", "at_word": "four thousand", "value": 4000, "unit": "miles"}])
    p, end = _render(shot, script, 95)
    assert p["card"] and p["view0"] is None
    _, start = _render(shot, script, 0)
    assert (np.abs(end - start).max(axis=2) > 12).mean() > 0.002


def test_the_action_clip_has_exactly_its_frames(raster, tmp_path):
    from explainer_engine.production.map_clip import render_action_map_clip
    shot, script = _script(dur=1.0, actions=[{"kind": "pulse", "at_word": "killer", "from": "toba"}])
    r = render_action_map_clip(shot, script, {"places": PLACES}, tmp_path / "m.mp4", width=W, height=H, fps=FPS)
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(tmp_path / "m.mp4")], capture_output=True, text=True).stdout
    assert int(n.strip()) == r["total_frames"] == 24 and r["word_basis"] == "estimated" and r["relief_upsample_max"] is not None
    gates = {g["gate"]: g for g in r["gates"]["gates"]}   # final audit B1: a map clip is measured, never a literal PASS
    assert gates["map_has_actions"]["status"] == "PASS" and isinstance(gates["map_not_standing_still"]["measured"], int)


def test_the_toba_proposal_resolves_against_the_script():
    root = REPO / "episodes" / "ep_toba"
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    prop = json.loads((root / "planning" / "map_actions_proposal_p4.json").read_text(encoding="utf-8"))
    shots = {s["shot_id"]: s for s in script["shots"]}
    for sid, extra in prop["shots"].items():
        assert shots[sid]["route"] == "map_action"
        p = MA.plan(dict(shots[sid], **extra), script, prop["places"], FPS)
        assert [a["kind"] for a in p["actions"]] == [a["kind"] for a in extra["actions"]]
