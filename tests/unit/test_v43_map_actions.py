"""v4.3 plan P4 (Q6): real relief (no invented terrain), map type that is not a comic face, and an action layer that lands on
its word, anchored in lon/lat. Each action kind has its own check (nothing before its word, something after, the same pixels
on a second render); the plate is a small fixture raster, so no download is needed."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.edit.cinematic_transitions import select_optimal_cinematic_transition
from explainer_engine.maps import actions as MA
from explainer_engine.maps import camera as CAM
from explainer_engine.maps import data as MD
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, plate, relief
from explainer_engine.production.map_clip import render_action_map_clip

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


# --- M1..M9 focused tests + S02 visual keyframe test -----------------------------------------------------------------

def test_m1_fly_to_and_zoom_honour_value_with_log_scale_pan_coupling():
    """M1: fly_to/zoom honour a['value'] (target span km) with log-scale zoom and pan coupled to scale (lerp_view)."""
    places = {"flanders": {"lon": 2.90, "lat": 50.72, "name": "Flanders"}}
    shot, script = _script(
        text="Here in Flanders the two sides sat close enough.",
        actions=[{"kind": "zoom", "at_word": "Here", "until_word": "close", "to": "flanders", "value": 60, "camera": "fly_to"}],
        view={"lon": 4.95, "lat": 49.31, "span_km": 1000.0},
    )
    p = MA.plan(shot, script, places, FPS)
    p["drift"] = 0.0
    a = p["actions"][0]
    mid_f = (a["start"] + a["end"] - 1) / 2.0
    # At end of shot, fly_to must reach value=60 km (failed on attached code which kept ~1000 km)
    end_v = MA.camera(p, p["frames"] - 1)
    assert abs(end_v["span_km"] - 60.0) < 0.5
    assert abs(end_v["lon"] - 2.90) < 1e-3 and abs(end_v["lat"] - 50.72) < 1e-3

    # Verify log-scale span and scale-coupled pan at u=0.5 via lerp_view
    v0 = {"lon": 4.95, "lat": 49.31, "span_km": 1000.0}
    v1 = {"lon": 2.90, "lat": 50.72, "span_km": 60.0}
    mid = MA.lerp_view(v0, v1, 0.5)
    assert abs(mid["span_km"] - math.sqrt(1000.0 * 60.0)) < 1e-4
    pan_progress = (mid["lon"] - v0["lon"]) / (v1["lon"] - v0["lon"])
    assert pan_progress > 0.65, "pan must couple to log-scale zoom rather than lagging at linear 0.5"
    assert abs(MA.camera(p, int(mid_f))["span_km"] - mid["span_km"]) < 30.0


def test_m2_standing_lines_drawn_from_frame_0(raster):
    """M2: an action with cues: 'none' or stands: true is fully drawn from frame 0 (no blank frames at a cut)."""
    shot_cues, script_cues = _script(
        text="Here in Flanders the two sides sat close.",
        actions=[{"kind": "front_line", "at_word": "Flanders", "from": "toba", "to": "india", "cues": "none"}],
        view={"lon": 88.5, "lat": 9.0, "span_km": 3200.0},
    )
    p_cues = MA.plan(shot_cues, script_cues, PLACES, FPS)
    p_cues["drift"] = 0.0
    assert p_cues["actions"][0]["start"] == 0
    assert MA._progress(p_cues["actions"][0], 0) == 1.0

    base = MA.Plate(p_cues, W, H)
    clean_f0 = np.asarray(base.frame(MA.camera(p_cues, 0), 1).convert("RGB"), dtype=np.int16)
    drawn_f0 = np.asarray(MA.render_frame(p_cues, 0, base, W, H, ss=1), dtype=np.int16)
    drawn_last = np.asarray(MA.render_frame(p_cues, p_cues["frames"] - 1, base, W, H, ss=1), dtype=np.int16)
    assert (np.abs(drawn_f0 - clean_f0).max(axis=2) > 20).mean() > 0.002
    assert np.array_equal(drawn_f0, drawn_last)

    shot_stands, script_stands = _script(
        text="Here in Flanders the two sides sat close.",
        actions=[{"kind": "front_line", "at_word": "close", "from": "toba", "to": "shinfa", "stands": True}],
        view={"lon": 67.0, "lat": 9.0, "span_km": 8500.0},
    )
    p_stands = MA.plan(shot_stands, script_stands, PLACES, FPS)
    assert p_stands["actions"][0]["start"] == 0 and MA._progress(p_stands["actions"][0], 0) == 1.0


def test_m3_camera_inheritance_and_stage_clips_wiring(raster, tmp_path):
    """M3: render_action_map_clip writes <cache>/<shot_id>_end_view.json; _first_view accepts prev_end_view and moves
    to the shot's own view; episode/run.py stage_clips wires prev_end_view only for same-location consecutive maps."""
    sh1 = {
        "shot_id": "S02_SH001", "segment_id": "S02", "location_id": "loc_western_front_map",
        "route": "map_action", "visual_type": "map_visualization", "target_duration_seconds": 1.0,
        "audio_line_ids": ["L1"], "map_view": {"lon": 4.84, "lat": 49.9, "span_km": 530.0},
        "actions": [{"kind": "pulse", "at_word": "begun", "from": "toba",
                     "event_id": "S02_SH001.A1", "audio": {"decision": "ui_cue", "class": "map_pin_set", "sync": "onset", "purpose": "clarify"}}],
    }
    sh2 = {
        "shot_id": "S02_SH002", "segment_id": "S02", "location_id": "loc_western_front_map",
        "route": "map_action", "visual_type": "map_visualization", "target_duration_seconds": 1.0,
        "audio_line_ids": ["L2"], "map_view": {"lon": 4.95, "lat": 49.31, "span_km": 1000.0},
        "actions": [{"kind": "pulse", "at_word": "December", "from": "india",
                     "event_id": "S02_SH002.A1", "audio": {"decision": "ui_cue", "class": "map_pin_set", "sync": "onset", "purpose": "clarify"}}],
    }
    sh3_diff_loc = {
        "shot_id": "S02_SH003", "segment_id": "S02", "location_id": "loc_other_theater",
        "route": "map_action", "visual_type": "map_visualization", "target_duration_seconds": 1.0,
        "audio_line_ids": ["L3"], "map_view": {"lon": 36.0, "lat": 12.8, "span_km": 700.0},
        "actions": [{"kind": "pulse", "at_word": "Here", "from": "shinfa",
                     "event_id": "S02_SH003.A1", "audio": {"decision": "ui_cue", "class": "map_pin_set", "sync": "onset", "purpose": "clarify"}}],
    }
    script = {
        "episode_id": "ep_test", "fps": FPS,
        "audio_lines": [
            {"line_id": "L1", "text": "The war had begun in August."},
            {"line_id": "L2", "text": "By December it dug into trenches."},
            {"line_id": "L3", "text": "Here in another theater entirely."},
        ],
        "shots": [sh1, sh2, sh3_diff_loc],
    }
    ep_manifest = {"episode_id": "ep_test", "places": PLACES}
    cache_dir = tmp_path / "cache"
    render_action_map_clip(sh1, script, ep_manifest, cache_dir / "S02_SH001.mp4", width=W, height=H, fps=FPS)
    end_view_file = cache_dir / "S02_SH001_end_view.json"
    assert end_view_file.is_file(), "render_action_map_clip must write <cache>/<shot_id>_end_view.json"
    ev1 = json.loads(end_view_file.read_text(encoding="utf-8"))
    assert set(ev1.keys()) == {"lon", "lat", "span_km"} and abs(ev1["span_km"] - 530.0 * (1.0 - MA.DRIFT)) < 1.0

    # Direct _first_view and camera check on sh2 with prev_end_view=ev1
    p2 = MA.plan(sh2, script, PLACES, FPS, prev_end_view=ev1)
    assert MA._first_view(sh2, p2["actions"], prev_end_view=ev1) == ev1
    cam2_start = MA.camera(p2, 0)
    cam2_end = MA.camera(p2, p2["frames"] - 1)
    assert cam2_start == ev1
    assert abs(cam2_end["lon"] - 4.95) < 0.01 and abs(cam2_end["span_km"] - 1000.0 * (1.0 - MA.DRIFT)) < 2.0

    # Check stage_clips wiring on an episode folder
    from explainer_engine.episode import run as RUN
    ep_root = tmp_path / "ep"
    (ep_root / "story").mkdir(parents=True)
    (ep_root / "episode.json").write_text(json.dumps(ep_manifest), encoding="utf-8")
    (ep_root / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
    ep = RUN.Episode(ep_root, size=(W, H), fps=FPS, rehearsal=True, sound_library=tmp_path)
    RUN.stage_clips(ep, rehearsal=True)
    rep2 = json.loads((ep_root / "production" / "shot_clips" / "S02_SH002.clip.json").read_text(encoding="utf-8"))
    rep3 = json.loads((ep_root / "production" / "shot_clips" / "S02_SH003.clip.json").read_text(encoding="utf-8"))
    assert (ep_root / "production" / "shot_clips" / "S02_SH001_end_view.json").is_file()
    assert abs(rep2["renderer"]["end_view"]["lon"] - 4.95) < 0.01
    assert abs(rep3["renderer"]["end_view"]["lon"] - 36.0) < 0.01


def test_m4_word_timing_measured_spine_vs_estimated_fallback(raster, tmp_path):
    """M4: measured word spine is used when present; uniform spread stays only as fallback and marks spine_basis: estimated."""
    shot, script = _script(
        text="The war had begun in August.",
        dur=2.0,
        actions=[{"kind": "pulse", "at_word": "August", "from": "toba"}],
    )
    p_est = MA.plan(shot, script, PLACES, FPS)
    est_start = p_est["actions"][0]["start"]

    words = MA.shot_words(shot, script)
    measured_spine = [{"word": w, "start_frame": idx + 1 if w != "august" else 41} for idx, w in enumerate(words)]
    ep_dir = tmp_path / "ep_m4"
    sp_dir = ep_dir / "production" / "spines"
    sp_dir.mkdir(parents=True)
    (sp_dir / "M1.json").write_text(json.dumps({"words": measured_spine}), encoding="utf-8")
    res_meas = render_action_map_clip(shot, script, {"places": PLACES}, ep_dir / "clips" / "M1.mp4", width=W, height=H, fps=FPS)
    assert res_meas["word_basis"] == "measured" and res_meas.get("spine_basis") == "measured"
    assert res_meas["actions"][0]["start"] == 41 and res_meas["actions"][0]["start"] != est_start

    res_est = render_action_map_clip(shot, script, {"places": PLACES}, tmp_path / "est" / "M1.mp4", width=W, height=H, fps=FPS)
    assert res_est["word_basis"] == "estimated" and res_est.get("spine_basis") == "estimated"
    assert p_est.get("spine_basis") == "estimated"


def test_m5_label_8pos_collision_free_and_chip_hud_card(raster):
    """M5: 8-position greedy label placement with safe-frame clamp and collision avoidance against other labels, lines
    and HUD cards; date actions at from: 'chip_*' render as a top-left screen-space HUD card instead of a geo label."""
    places = {
        **PLACES,
        "p_same_1": {"lon": 67.0, "lat": 9.0, "name": "Alpha Sector"},
        "p_same_2": {"lon": 67.0, "lat": 9.0, "name": "Bravo Sector"},
        "p_edge": {"lon": 112.0, "lat": 25.0, "name": "Far Edge Outpost"},
        "chip_aug": {"lon": 45.0, "lat": 12.0, "name": "date chip"},
    }
    # 1. Verify chip_aug renders as screen-space top-left HUD card that does not drift when view pans
    shot_chip, script_chip = _script(
        text="The killer lay four thousand miles away in the ash.",
        actions=[{"kind": "label", "at_word": "killer", "from": "chip_aug", "label": "August 1914"}],
        view={"lon": 67.0, "lat": 9.0, "span_km": 9500.0},
    )
    p1 = MA.plan(shot_chip, script_chip, places, FPS)
    p1["drift"] = 0.0
    base = MA.Plate(p1, W, H)
    f_last = p1["frames"] - 1
    clean_a = np.asarray(base.frame(MA.camera(p1, f_last), 1).convert("RGB"), dtype=np.int16)
    drawn_a = np.asarray(MA.render_frame(p1, f_last, base, W, H, ss=1), dtype=np.int16)
    diff_a = np.abs(drawn_a - clean_a).max(axis=2) > 15

    p2 = dict(p1, view0={"lon": 75.0, "lat": 6.0, "span_km": 7500.0})
    clean_b = np.asarray(base.frame(MA.camera(p2, f_last), 1).convert("RGB"), dtype=np.int16)
    drawn_b = np.asarray(MA.render_frame(p2, f_last, base, W, H, ss=1), dtype=np.int16)
    diff_b = np.abs(drawn_b - clean_b).max(axis=2) > 15
    ys_a, xs_a = np.nonzero(diff_a)
    ys_b, xs_b = np.nonzero(diff_b)
    assert abs(float(xs_a.mean()) - float(xs_b.mean())) < 1.0 and abs(float(ys_a.mean()) - float(ys_b.mean())) < 1.0
    assert float(xs_a.min()) < W * 0.10 and float(ys_a.min()) < H * 0.10

    # 2. Verify 8-position solver avoids label collisions and clamps to safe frame
    shot, script = _script(
        text="In August the killer lay four thousand miles away in the ash.",
        actions=[
            {"kind": "label", "at_word": "August", "from": "chip_aug", "label": "August 1914"},
            {"kind": "front_line", "at_word": "killer", "from": "toba", "to": "shinfa", "cues": "none"},
            {"kind": "label", "at_word": "four", "from": "p_same_1", "label": "Alpha Sector"},
            {"kind": "label", "at_word": "thousand", "from": "p_same_2", "label": "Bravo Sector"},
            {"kind": "label", "at_word": "miles", "from": "p_edge", "label": "Far Edge Outpost"},
        ],
        view={"lon": 67.0, "lat": 9.0, "span_km": 9500.0},
    )
    p = MA.plan(shot, script, places, FPS)
    MA.render_frame(p, p["frames"] - 1, base, W, H, ss=1)
    boxes = p["_label_boxes"][p["frames"] - 1]
    geo_lbls = [b for b in boxes if b["kind"] == "geo_label"]
    xmin, ymin, xmax, ymax = MA.safe_frame_bounds(W, H)
    for lb in geo_lbls:
        x0, y0, x1, y1 = lb["box"]
        assert x0 >= xmin - 1e-3 and y0 >= ymin - 1e-3 and x1 <= xmax + 1e-3 and y1 <= ymax + 1e-3
    b1, b2 = geo_lbls[0]["box"], geo_lbls[1]["box"]
    iw = max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
    ih = max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
    assert iw * ih == 0.0, f"colocated labels collided: {b1} vs {b2}"


def test_m6_counter_locked_box_width_and_nonzero_first_frame(raster):
    """M6: counter box width is locked to the final formatted value (no jitter) and never shows 0 on its first visible frame."""
    shot, script = _script(
        text="The killer lay four thousand miles away in the ash.",
        actions=[
            {"kind": "label", "at_word": "killer", "from": "toba"},
            {"kind": "counter", "at_word": "four", "until_word": "ash", "value": 100000, "unit": "men (estimate)", "claim": "C-03"},
        ],
        view={"lon": 67.0, "lat": 9.0, "span_km": 9500.0},
    )
    p = MA.plan(shot, script, PLACES, FPS)
    p["drift"] = 0.0
    base = MA.Plate(p, W, H)
    cnt = p["actions"][1]
    before_cnt = np.asarray(MA.render_frame(p, cnt["start"] - 1, base, W, H, ss=1), dtype=np.int16)
    first_cnt = np.asarray(MA.render_frame(p, cnt["start"], base, W, H, ss=1), dtype=np.int16)
    last_cnt = np.asarray(MA.render_frame(p, p["frames"] - 1, base, W, H, ss=1), dtype=np.int16)

    # Pixel-level check: the counter box horizontal span at its first visible frame must match its final frame (no jitter)
    xs_first = np.nonzero((np.abs(first_cnt - before_cnt).max(axis=2) > 15)[int(H * 0.70):, :])[1]
    xs_last = np.nonzero((np.abs(last_cnt - before_cnt).max(axis=2) > 15)[int(H * 0.70):, :])[1]
    assert abs(int(xs_first.max() - xs_first.min()) - int(xs_last.max() - xs_last.min())) <= 2

    widths = {round(p["_counter_boxes"][f][2] - p["_counter_boxes"][f][0], 4) for f in (cnt["start"], p["frames"] - 1)}
    assert len(widths) == 1
    u0 = MA._u_counter(cnt, cnt["start"])
    assert u0 > 0.0 and MA._fmt(max(1.0, float(cnt["value"]) * u0), cnt["value"]) != "0"


def test_m7_1914_borders_layer_and_pre_1945_plate_switching():
    """M7: borders_1914.json.gz built by build_1914.py, recorded in SOURCES.json, and used by plate.py instead of
    modern borders when period < 1945 (Alsace-Lorraine inside Germany; modern Rhine border never drawn for 1914)."""
    from explainer_engine.maps.data import build_1914
    assert build_1914.OUT.is_file() and build_1914.build(check=True) == 0
    sources = json.loads(build_1914.SOURCES.read_text(encoding="utf-8"))
    assert "borders_1914" in sources
    assert sources["borders_1914"]["sha256"] == hashlib.sha256(build_1914.OUT.read_bytes()).hexdigest()
    assert "licence" in sources["borders_1914"] and "source_url" in sources["borders_1914"]

    ds1914 = geo.dataset_1914()
    required_countries = {
        "Germany", "France", "Belgium", "Netherlands", "Luxembourg",
        "Switzerland", "United Kingdom", "Austria-Hungary", "Italy", "Denmark",
    }
    assert required_countries <= set(ds1914["countries"].keys())
    # Strasbourg (7.75E, 48.58N) and Metz (6.18E, 49.12N) are inside 1914 Germany and NOT inside 1914 France
    assert geo.in_polygons(ds1914["countries"]["Germany"], 7.75, 48.58)
    assert not geo.in_polygons(ds1914["countries"]["France"], 7.75, 48.58)
    assert geo.in_polygons(ds1914["countries"]["Germany"], 6.18, 49.12)
    assert not geo.in_polygons(ds1914["countries"]["France"], 6.18, 49.12)

    # Render Alsace-Lorraine view (centred on Strasbourg / Vosges) for 1914 vs modern (post-1945)
    v_alsace = geo.View(7.0, 48.5, 320.0, 320, 180)
    im_no_borders = np.asarray(plate.render_plate(v_alsace, layers=("land",), ss=1), dtype=np.int16)
    im_1914 = np.asarray(plate.render_plate(v_alsace, layers=("land", "borders"), ss=1, period=1914), dtype=np.int16)
    im_modern = np.asarray(plate.render_plate(v_alsace, layers=("land", "borders"), ss=1, period=2020), dtype=np.int16)

    diff_1914 = np.abs(im_1914 - im_no_borders).max(axis=2) > 8
    diff_modern = np.abs(im_modern - im_no_borders).max(axis=2) > 8

    vosges_pts = [(5.92, 49.33), (6.16, 48.91), (6.68, 48.65), (7.12, 48.36), (7.02, 47.96)]
    rhine_pts = [(7.78, 48.60), (7.60, 48.25), (7.58, 47.95), (7.90, 48.75)]

    def patch_hits(mask, ll_pts):
        hits = 0
        for lon, lat in ll_pts:
            px_x, px_y = v_alsace.to_px(lon, lat)
            ix, iy = int(round(float(px_x))), int(round(float(px_y)))
            if bool(mask[max(0, iy - 4):iy + 5, max(0, ix - 4):ix + 5].any()):
                hits += 1
        return hits

    assert patch_hits(diff_1914, vosges_pts) >= 4, "1914 Vosges/Metz border must be drawn for period=1914"
    assert patch_hits(diff_1914, rhine_pts) == 0, "modern Rhine border must never be drawn for 1914"
    assert patch_hits(diff_modern, rhine_pts) >= 2, "modern plate draws the Rhine border"


def test_m8_map_to_map_transitions_same_vs_different_location():
    """M8: map->map in same location + inherited camera -> seamless cut (0 frames, 0.15 s prelap);
    different location -> cross_dissolve_8f (8 frames)."""
    map_a = {
        "shot_id": "S02_SH001", "segment_id": "S02", "location_id": "loc_western_front_map",
        "route": "map_action", "visual_type": "map_visualization", "generation_mode": "TACTILE_MAP",
    }
    map_b_same = {
        "shot_id": "S02_SH002", "segment_id": "S02", "location_id": "loc_western_front_map",
        "route": "map_action", "visual_type": "map_visualization", "generation_mode": "TACTILE_MAP",
    }
    map_b_diff = {
        "shot_id": "S02_SH002", "segment_id": "S02", "location_id": "loc_eastern_front_map",
        "route": "map_action", "visual_type": "map_visualization", "generation_mode": "TACTILE_MAP",
    }
    t_same = select_optimal_cinematic_transition(map_a, map_b_same)
    assert t_same["transition_type"] == "hard_cut_with_jl_bridge"
    assert t_same["transition_frames"] == 0
    assert t_same["audio_j_cut_prelap_sec"] == 0.15

    t_diff = select_optimal_cinematic_transition(map_a, map_b_diff)
    assert t_diff["transition_type"] == "cross_dissolve_8f"
    assert t_diff["transition_frames"] == 8


def test_m9_font_renders_liege_armentieres_with_no_notdef_glyphs(tmp_path, monkeypatch):
    """M9: renders 'Liège–Armentières' with the map font and verifies zero missing-glyph (.notdef) boxes."""
    sample = "Liège–Armentières"
    D.font.cache_clear()
    monkeypatch.setattr(D, "MAP_FONT", tmp_path / "missing_Inter.ttf")
    f = D.font(36, "map")

    def render_glyph(ch: str) -> np.ndarray:
        im = Image.new("L", (96, 96), 0)
        ImageDraw.Draw(im).text((16, 16), ch, font=f, fill=255)
        return np.asarray(im, dtype=np.uint8)

    notdef = render_glyph("\ufffe")
    for ch in sample:
        g = render_glyph(ch)
        assert g.sum() > 0 and not np.array_equal(g, notdef), f"character {ch!r} rendered as .notdef missing-glyph box"
    assert not np.array_equal(render_glyph("è"), render_glyph("–"))
    D.font.cache_clear()


# --- S9 V1..V7 focused tests + S02 & S05 visual contact-sheet test ---------------------------------------------------

def test_v1_hud_date_card_inside_safe_frame_at_least_4pct_margin(raster):
    """V1: safe_frame_bounds and HUD date card (August 1914 / December 1914) stay >= 4 % inside every frame edge."""
    for tw_px, th_px in ((W, H), (640, 360), (1920, 1080)):
        xmin, ymin, xmax, ymax = MA.safe_frame_bounds(tw_px, th_px)
        assert xmin >= tw_px * 0.04 - 1e-6 and ymin >= th_px * 0.04 - 1e-6
        assert xmax <= tw_px * 0.96 + 1e-6 and ymax <= th_px * 0.96 + 1e-6

    places = {**PLACES, "chip_aug": {"lon": 1.584, "lat": 50.892, "name": "date chip"},
              "chip_dec": {"lon": -1.119, "lat": 51.182, "name": "date chip"}}
    for chip_id, label_txt in (("chip_aug", "August 1914"), ("chip_dec", "December 1914")):
        shot, script = _script(
            text="The killer lay four thousand miles away in the ash.",
            actions=[{"kind": "label", "at_word": "killer", "from": chip_id, "label": label_txt}],
            view={"lon": 67.0, "lat": 9.0, "span_km": 9500.0},
        )
        p = MA.plan(shot, script, places, FPS)
        p["drift"] = 0.0
        base = MA.Plate(p, W, H)
        f_end = p["frames"] - 1
        clean = np.asarray(base.frame(MA.camera(p, f_end), 1).convert("RGB"), dtype=np.int16)
        drawn = np.asarray(MA.render_frame(p, f_end, base, W, H, ss=1), dtype=np.int16)
        diff = np.abs(drawn - clean).max(axis=2) > 12
        ys, xs = np.nonzero(diff)
        assert xs.min() >= W * 0.04 and ys.min() >= H * 0.04
        assert xs.max() <= W * 0.96 and ys.max() <= H * 0.96
        hud_boxes = [b["box"] for b in p["_label_boxes"][f_end] if b["kind"] == "hud_chip"]
        assert len(hud_boxes) == 1
        bx0, by0, bx1, by1 = hud_boxes[0]
        xmin, ymin, xmax, ymax = MA.safe_frame_bounds(W, H)
        assert bx0 >= xmin and by0 >= ymin and bx1 <= xmax and by1 <= ymax


def test_v2_auto_place_label_pills_and_macro_reference_cities_capped_at_6(raster):
    """V2: automatic place label pills for narration/action places + theater reference cities at macro spans, <= 6 per frame."""
    ep_dir = REPO / "episodes" / "ep_truce_1914"
    episode = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    script = json.loads((ep_dir / "story" / "production_script.json").read_text(encoding="utf-8"))
    places = episode["places"]
    shots = {s["shot_id"]: s for s in script["shots"]}

    # Macro shot S02_SH001 authors no geo labels, yet must draw >= 3 and <= 6 unique city pills
    p1 = MA.plan(shots["S02_SH001"], script, places, FPS)
    base1 = MA.Plate(p1, 640, 360, look={"period": 1914})
    for f_idx in (0, p1["frames"] - 1):
        MA.render_frame(p1, f_idx, base1, 640, 360, look={"period": 1914}, ss=1)
        geo_lbls = [b for b in p1["_label_boxes"][f_idx] if b["kind"] == "geo_label"]
        names = [b["text"] for b in geo_lbls]
        assert 3 <= len(geo_lbls) <= 6
        assert len(names) == len(set(names)), f"duplicate label pills on frame {f_idx}: {names}"
    end_names_1 = {b["text"] for b in p1["_label_boxes"][p1["frames"] - 1] if b["kind"] == "geo_label"}
    assert {"Aachen", "Brussels", "Paris"} <= end_names_1

    # Close shot S05_SH001 (90 km) must draw Flanders sector town pills (<= 6, unique)
    p5 = MA.plan(shots["S05_SH001"], script, places, FPS)
    base5 = MA.Plate(p5, 640, 360, look={"period": 1914})
    MA.render_frame(p5, p5["frames"] - 1, base5, 640, 360, look={"period": 1914}, ss=1)
    geo_lbls_5 = [b for b in p5["_label_boxes"][p5["frames"] - 1] if b["kind"] == "geo_label"]
    names_5 = [b["text"] for b in geo_lbls_5]
    assert 4 <= len(geo_lbls_5) <= 6 and len(names_5) == len(set(names_5))
    assert {"Wulverghem", "Ploegsteert", "Frelinghien", "Fleurbaix"} <= set(names_5)


def test_v3_close_span_micro_relief_detail_above_3x_upsample_without_inventing_coast_or_rivers(raster):
    """V3: when relief upsample > 3x (60-90 km), multi-octave Sobel hillshade + parchment grain sharpens land without
    inventing coastlines or rivers."""
    from scipy.ndimage import sobel
    v_close = geo.View(2.89, 50.71, 75.0, 320, 180)
    assert plate.relief_upsample(v_close) > 3.0

    im_crisp = np.asarray(plate.render_plate(v_close, layers=("land",), shaded_relief=True, ss=1, period=1914), dtype=np.float32)
    im_blur = np.asarray(
        plate.render_plate(v_close, layers=("land",), shaded_relief=True, ss=1, look={"disable_micro_relief": True}, period=1914),
        dtype=np.float32,
    )
    luma_crisp = 0.299 * im_crisp[:, :, 0] + 0.587 * im_crisp[:, :, 1] + 0.114 * im_crisp[:, :, 2]
    luma_blur = 0.299 * im_blur[:, :, 0] + 0.587 * im_blur[:, :, 1] + 0.114 * im_blur[:, :, 2]

    grad_crisp = float(np.hypot(sobel(luma_crisp, axis=1), sobel(luma_crisp, axis=0)).std())
    grad_blur = float(np.hypot(sobel(luma_blur, axis=1), sobel(luma_blur, axis=0)).std())
    assert grad_crisp > grad_blur * 1.8, f"close-span micro-relief did not sharpen terrain: {grad_crisp} vs {grad_blur}"

    # Verify sea pixels on a mixed coast view are untouched by land micro-relief
    v_coast = geo.View(2.60, 51.15, 75.0, 240, 135)
    mask_land = plate.land_mask(v_coast, ss=1)
    rgb_crisp = plate.relief_rgb(v_coast, plate.colours(), look={})
    rgb_plain = plate.relief_rgb(v_coast, plate.colours(), look={"disable_micro_relief": True})
    assert np.array_equal(rgb_crisp[~mask_land], rgb_plain[~mask_land]), "micro-relief must never alter sea or invent coasts"


def test_v4_western_front_dual_line_and_route_arrow_head_and_shadow(raster):
    """V4: front_line draws Entente blue on the west and German red on the east around a dark core with traverse ticks;
    route_arrow draws a soft drop shadow and swept chevron arrowhead."""
    places = {
        "north_pt": {"lon": 4.0, "lat": 51.0, "name": "North"},
        "south_pt": {"lon": 4.0, "lat": 48.0, "name": "South"},
        "east_pt": {"lon": 6.0, "lat": 50.0, "name": "East"},
        "west_pt": {"lon": 2.5, "lat": 50.0, "name": "West"},
    }
    shot_fl, script_fl = _script(
        text="The killer lay four thousand miles away in the ash.",
        actions=[{"kind": "front_line", "at_word": "killer", "from": "north_pt", "to": "south_pt", "cues": "none"}],
        view={"lon": 4.0, "lat": 49.5, "span_km": 420.0},
    )
    p_fl = MA.plan(shot_fl, script_fl, places, FPS)
    p_fl["auto_labels"] = []
    c_fl = D.Canvas(320, 180, (245, 238, 224), ss=2)
    c_fl.face = "map"
    view_fl = geo.View(4.0, 49.5, 420.0, 320, 180)
    MA.draw(c_fl, p_fl, 0, view_fl)
    rgb_fl = np.asarray(c_fl.image().convert("RGB"), dtype=np.int16)

    # Sample horizontal slice across the vertical front line at y=90 (centre x=160)
    row = rgb_fl[90, :, :]
    west_band = row[148:159]
    core_px = row[160]
    east_band = row[161:172]
    assert (west_band[:, 2] - west_band[:, 0]).max() > 35, "west flank of front_line must be Entente blue (B > R)"
    assert (east_band[:, 0] - east_band[:, 2]).max() > 35, "east flank of front_line must be German red (R > B)"
    assert core_px.mean() < 90, "centre of front_line must be dark ink core"

    # Route arrow shadow + arrowhead check
    shot_ar, script_ar = _script(
        text="The killer lay four thousand miles away in the ash.",
        actions=[{"kind": "route_arrow", "at_word": "killer", "from": "east_pt", "to": "west_pt", "cues": "none"}],
        view={"lon": 4.25, "lat": 50.0, "span_km": 420.0},
    )
    p_ar = MA.plan(shot_ar, script_ar, places, FPS)
    p_ar["auto_labels"] = []
    c_ar = D.Canvas(320, 180, (245, 238, 224), ss=2)
    c_ar.face = "map"
    view_ar = geo.View(4.25, 50.0, 420.0, 320, 180)
    MA.draw(c_ar, p_ar, 0, view_ar)
    rgb_ar = np.asarray(c_ar.image().convert("RGB"), dtype=np.int16)
    bg_luma = float(rgb_ar[10, 10].mean())
    tip_x, tip_y = view_ar.to_px(2.5, 50.0)
    tx, ty = int(round(float(tip_x))), int(round(float(tip_y)))
    head_patch = rgb_ar[max(0, ty - 10):ty + 11, max(0, tx - 4):tx + 16]
    assert (head_patch[:, :, 0] - head_patch[:, :, 2] > 40).sum() >= 15, "route_arrow must render a prominent arrowhead"
    # Drop shadow below the arrow shaft is darker than background but lighter than solid ink
    shaft_cols = rgb_ar[:, 160, :].mean(axis=1)
    assert ((shaft_cols < bg_luma - 8) & (shaft_cols > 80)).any(), "route_arrow must include a soft drop shadow"


def test_v5_carry_over_ghost_line_at_22pct_in_next_same_theater_shot(raster):
    """V5: an action line or arrow drawn in shot k stays visible as a 22 % ghost at frame 0 of shot k+1 in the same theater."""
    ep_dir = REPO / "episodes" / "ep_truce_1914"
    episode = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    script = json.loads((ep_dir / "story" / "production_script.json").read_text(encoding="utf-8"))
    places = episode["places"]
    shots = {s["shot_id"]: s for s in script["shots"]}

    p1 = MA.plan(shots["S02_SH001"], script, places, FPS)
    ev1 = MA.camera(p1, p1["frames"] - 1)
    p2 = MA.plan(shots["S02_SH002"], script, places, FPS, prev_end_view=ev1)
    assert len(p2["carry_over"]) == 1
    ghost = p2["carry_over"][0]
    assert ghost["kind"] == "route_arrow" and ghost["from_id"] == "aachen" and ghost["to_id"] == "marne"
    assert abs(float(ghost["alpha"]) - 0.22) < 1e-6

    # Render frame 0 of S02_SH002 (before December front_line starts) and verify ghost pixels along the August route
    p2_no_lbl = dict(p2, auto_labels=[])
    base2 = MA.Plate(p2_no_lbl, W, H, look={"period": 1914})
    clean_f0 = np.asarray(base2.frame(MA.camera(p2_no_lbl, 0), 1).convert("RGB"), dtype=np.float32)
    drawn_f0 = np.asarray(MA.render_frame(p2_no_lbl, 0, base2, W, H, look={"period": 1914}, ss=1), dtype=np.float32)
    v0 = geo.View(ev1["lon"], ev1["lat"], ev1["span_km"], W, H)
    route_hits = 0
    for lon, lat in ghost["path"][2:-2:3]:
        rx, ry = v0.to_px(lon, lat)
        ix, iy = int(round(float(rx))), int(round(float(ry)))
        if 2 <= ix < W - 2 and 2 <= iy < H - 2:
            diff_patch = np.abs(drawn_f0[iy - 2:iy + 3, ix - 2:ix + 3] - clean_f0[iy - 2:iy + 3, ix - 2:ix + 3]).max()
            if diff_patch > 8.0:
                route_hits += 1
    assert route_hits >= 10, f"expected carried-over 22% ghost route pixels at frame 0 of S02_SH002, got {route_hits} hits"


def test_v6_highlight_and_pulse_clamped_6_to_14pct_height_and_thin_1914_borders(raster):
    """V6: highlight discs and pulse rings are clamped to 6-14 % of frame height (area <= 3 % of frame);
    1914 border dashes are <= 2 px at 1080p."""
    for val_km, want_frac in ((0.2, 0.06), (500.0, 0.14)):
        shot, script = _script(
            text="The killer lay four thousand miles away in the ash.",
            actions=[
                {"kind": "highlight", "at_word": "killer", "from": "toba", "value": val_km},
                {"kind": "pulse", "at_word": "four", "from": "shinfa", "value": val_km},
            ],
            view={"lon": 67.0, "lat": 9.0, "span_km": 90.0},
        )
        p = MA.plan(shot, script, PLACES, FPS)
        p["auto_labels"] = []
        base = MA.Plate(p, W, H)
        f_end = p["frames"] - 1
        MA.render_frame(p, f_end, base, W, H, ss=1)
        hl_r = p["_highlight_radii"][f_end][0]
        pl_r = p["_pulse_radii"][f_end][0]
        assert abs((2.0 * hl_r) / H - want_frac) < 1e-4
        assert abs((2.0 * pl_r) / H - want_frac) < 1e-4
        assert (math.pi * hl_r * hl_r) / (W * H) <= 0.03

    # Verify 1914 border dashes are thin (<= 2 px at 1080p)
    v_1080 = geo.View(5.95, 49.25, 120.0, 1920, 1080)
    im_land = np.asarray(plate.render_plate(v_1080, layers=("land",), ss=1, period=1914), dtype=np.int16)
    im_b1914 = np.asarray(plate.render_plate(v_1080, layers=("land", "borders"), ss=1, period=1914), dtype=np.int16)
    b_mask = np.abs(im_b1914 - im_land).max(axis=2) > 10
    # Measure horizontal run lengths across the vertical Franco-German 1914 border segment near (5.90E, 49.25N)
    bx, by = v_1080.to_px(5.90, 49.25)
    ix, iy = int(round(float(bx))), int(round(float(by)))
    widths = []
    for r_y in range(max(0, iy - 80), min(1080, iy + 80)):
        row_runs = b_mask[r_y, max(0, ix - 30):min(1920, ix + 30)]
        if row_runs.any():
            widths.append(int(row_runs.sum()))
    assert widths and int(np.median(widths)) <= 2, f"1914 border dash width at 1080p exceeded 2 px: {widths[:10]}"


def test_v7_colocated_labels_on_front_line_zero_overlap(raster):
    """V7: multiple colocated labels sitting directly on a front_line never overlap each other."""
    places = {
        **PLACES,
        "p_same_1": {"lon": 67.0, "lat": 9.0, "name": "Alpha Sector"},
        "p_same_2": {"lon": 67.0, "lat": 9.0, "name": "Bravo Sector"},
        "p_same_3": {"lon": 67.0, "lat": 9.0, "name": "Charlie Sector"},
        "p_same_4": {"lon": 67.0, "lat": 9.0, "name": "Delta Sector"},
    }
    shot, script = _script(
        text="In August the killer lay four thousand miles away in the ash.",
        actions=[
            {"kind": "front_line", "at_word": "August", "from": "toba", "to": "shinfa", "cues": "none"},
            {"kind": "label", "at_word": "killer", "from": "p_same_1", "label": "Alpha Sector"},
            {"kind": "label", "at_word": "four", "from": "p_same_2", "label": "Bravo Sector"},
            {"kind": "label", "at_word": "thousand", "from": "p_same_3", "label": "Charlie Sector"},
            {"kind": "label", "at_word": "miles", "from": "p_same_4", "label": "Delta Sector"},
        ],
        view={"lon": 67.0, "lat": 9.0, "span_km": 9500.0},
    )
    p = MA.plan(shot, script, places, FPS)
    base = MA.Plate(p, W, H)
    MA.render_frame(p, p["frames"] - 1, base, W, H, ss=1)
    boxes = [b["box"] for b in p["_label_boxes"][p["frames"] - 1] if b["kind"] == "geo_label"]
    assert len(boxes) >= 4
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            b1, b2 = boxes[i], boxes[j]
            iw = max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            ih = max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
            assert iw * ih == 0.0, f"labels {i} and {j} overlapped: {b1} vs {b2}"


def test_visual_s02_sh001_to_003_keyframes_contact_sheet_and_safe_frame(raster, tmp_path):
    """Visual test: renders S02_SH001..003 keyframes (first/last frame of each shot) into a contact sheet PNG in tmp
    and asserts zero camera jump between consecutive shots (<= 0.5 % span) and no label outside the safe frame."""
    ep_dir = REPO / "episodes" / "ep_truce_1914"
    episode = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    script = json.loads((ep_dir / "story" / "production_script.json").read_text(encoding="utf-8"))
    places = episode["places"]
    look = {"period": episode["historical_period"]["start_year"]}
    shots_by_id = {s["shot_id"]: s for s in script["shots"]}

    kw, kh = 640, 360
    shot_ids = ("S02_SH001", "S02_SH002", "S02_SH003", "S05_SH001", "S05_SH002")
    plans: dict[str, dict] = {}
    bases: dict[str, MA.Plate] = {}
    keyframes = []
    prev_end_view = None
    prev_seg = None

    for sid in shot_ids:
        sh = dict(shots_by_id[sid])
        seg = sh.get("segment_id")
        if prev_end_view is not None and seg == prev_seg:
            sh["prev_end_view"] = prev_end_view
        p = MA.plan(sh, script, places, FPS)
        base = MA.Plate(p, kw, kh, look=look)
        im_start = MA.render_frame(p, 0, base, kw, kh, look=look, ss=1)
        im_end = MA.render_frame(p, p["frames"] - 1, base, kw, kh, look=look, ss=1)
        keyframes.append((sid, "start", im_start, MA.camera(p, 0), 0))
        keyframes.append((sid, "end", im_end, MA.camera(p, p["frames"] - 1), p["frames"] - 1))
        prev_end_view = MA.camera(p, p["frames"] - 1)
        prev_seg = seg
        plans[sid] = p
        bases[sid] = base

    # Assert zero camera jump between consecutive shots (end view of shot k == start view of shot k+1 within 0.5% span)
    for sid_a, sid_b in (("S02_SH001", "S02_SH002"), ("S02_SH002", "S02_SH003"), ("S05_SH001", "S05_SH002")):
        pa, pb = plans[sid_a], plans[sid_b]
        end_k = MA.camera(pa, pa["frames"] - 1)
        start_next = MA.camera(pb, 0)
        span_diff_pct = abs(end_k["span_km"] - start_next["span_km"]) / end_k["span_km"]
        assert span_diff_pct <= 0.005, f"shot {sid_a}->{sid_b} span jump {span_diff_pct:.4%} > 0.5%"
        assert abs(end_k["lon"] - start_next["lon"]) < 1e-4 and abs(end_k["lat"] - start_next["lat"]) < 1e-4

    # Assert S02_SH003 zoomed into Flanders (~60 km)
    end_sh003 = MA.camera(plans["S02_SH003"], plans["S02_SH003"]["frames"] - 1)
    assert end_sh003["span_km"] <= 65.0

    # Assert no label outside safe frame across all rendered keyframes
    xmin, ymin, xmax, ymax = MA.safe_frame_bounds(kw, kh)
    assert xmin >= kw * 0.04 - 1e-6 and ymin >= kh * 0.04 - 1e-6
    for sid, _which, _im, cam_v, f_idx in keyframes:
        p = plans[sid]
        lboxes = p.get("_label_boxes", {}).get(f_idx, [])
        geo_lbls = [lb for lb in lboxes if lb["kind"] == "geo_label"]
        if cam_v["span_km"] >= 300.0:
            assert len(geo_lbls) >= 3, f"{sid} f={f_idx} (macro span={cam_v['span_km']:.1f}km) has < 3 labels: {geo_lbls}"
        assert len(geo_lbls) <= 6
        all_boxes = [lb["box"] for lb in lboxes]
        if f_idx in p.get("_counter_boxes", {}):
            all_boxes.append(p["_counter_boxes"][f_idx])
        for bx0, by0, bx1, by1 in all_boxes:
            assert bx0 >= xmin - 1e-3 and by0 >= ymin - 1e-3 and bx1 <= xmax + 1e-3 and by1 <= ymax + 1e-3, (
                f"{sid} f={f_idx} box {(bx0, by0, bx1, by1)} outside safe frame {(xmin, ymin, xmax, ymax)}"
            )
        for i in range(len(all_boxes)):
            for j in range(i + 1, len(all_boxes)):
                b1, b2 = all_boxes[i], all_boxes[j]
                iw = max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
                ih = max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                assert iw * ih == 0.0, f"{sid} f={f_idx} boxes overlapped: {b1} vs {b2}"

    # 4. Assert line pixels present at frame 0 of S02_SH002 (carry-over ghost) and S02_SH003 (standing front_line)
    for sid, path_source in (
        ("S02_SH002", plans["S02_SH002"]["carry_over"][0]["path"]),
        ("S02_SH003", plans["S02_SH003"]["actions"][0]["path"]),
    ):
        p_nl = dict(plans[sid], auto_labels=[])
        b_nl = bases[sid]
        v0_dict = MA.camera(p_nl, 0)
        v0 = geo.View(v0_dict["lon"], v0_dict["lat"], v0_dict["span_km"], kw, kh)
        clean0 = np.asarray(b_nl.frame(v0_dict, 1).convert("RGB"), dtype=np.float32)
        drawn0 = np.asarray(MA.render_frame(p_nl, 0, b_nl, kw, kh, look=look, ss=1), dtype=np.float32)
        hits = 0
        for lon, lat in path_source[2:-2:4]:
            px_x, px_y = v0.to_px(lon, lat)
            ix, iy = int(round(float(px_x))), int(round(float(px_y)))
            if 2 <= ix < kw - 2 and 2 <= iy < kh - 2:
                if float(np.abs(drawn0[iy - 2:iy + 3, ix - 2:ix + 3] - clean0[iy - 2:iy + 3, ix - 2:ix + 3]).max()) > 8.0:
                    hits += 1
        assert hits >= 8, f"{sid} frame 0 missing line pixels along path ({hits} hits)"

    # 5. Assert highlight area <= 3 % of the frame on S02_SH003 and S05_SH002
    for sid in ("S02_SH003", "S05_SH002"):
        p = plans[sid]
        f_end = p["frames"] - 1
        radii = p.get("_highlight_radii", {}).get(f_end, [])
        assert radii, f"{sid} end frame must record highlight radii"
        total_area_frac = sum(math.pi * r * r for r in radii) / float(kw * kh)
        assert total_area_frac <= 0.03, f"{sid} highlight area {total_area_frac:.4%} > 3.0%"

    # Assemble 3x2 contact sheet PNG in tmp_path
    sheet = Image.new("RGB", (kw * 2, kh * 5), (22, 26, 35))
    for idx, (_sid, _which, im, _cam, _f_idx) in enumerate(keyframes):
        col_i = idx % 2
        row_i = idx // 2
        sheet.paste(im, (col_i * kw, row_i * kh))
    sheet_path = tmp_path / "s02_s05_keyframes_contact_sheet.png"
    sheet.save(sheet_path)
    assert sheet_path.is_file() and sheet_path.stat().st_size > 20000
