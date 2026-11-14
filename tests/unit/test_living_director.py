"""The director's own choice of a photo shot's living effects, weather and camera (the owner, 2026-11-14 12:40 UTC: from the
words, the photo and the catalogue; 12:38 UTC: the scene's weather is a ceiling the director decides inside)."""
from __future__ import annotations

import copy

import numpy as np

from explainer_engine.production import direction as D
from explainer_engine.production import living as LV
from explainer_engine.production import living_director as LD

SPINE = [{"word": "the", "start_frame": 2}, {"word": "light", "start_frame": 10}, {"word": "was", "start_frame": 20},
         {"word": "going", "start_frame": 26}, {"word": "for", "start_frame": 40}, {"word": "thomas", "start_frame": 48}]
SEEN = {
    "schema": D.SCHEMA, "shot_id": "S06_SH001", "picture_sha256": "abc", "intent": "intended", "people_mid_or_close": True,
    "scene": {"weather": [], "surroundings": "sunset, frost", "wind": [0.02, 0.0]},
    "seen": {"what": "two soldiers at sunset on frozen ground",
             "objects": [{"id": "thomas", "points": [[0.37, 0.5], [0.38, 0.3]], "names": ["thomas"]}],
             "lights": [{"id": "sun", "kind": "sun", "point": [0.48, 0.3]},
                        {"id": "brazier_flame", "kind": "fire", "point": [0.9, 0.75], "radius": 0.03}],
             "living": [{"id": "low_sun", "kind": "sun", "where": [0.48, 0.3], "area_pct": 25},
                        {"id": "ice", "kind": "ice", "where": [0.5, 0.55], "area_pct": 6, "box": [0.25, 0.4, 0.8, 0.66]},
                        {"id": "clouds", "kind": "sky", "where": [0.5, 0.1], "area_pct": 30},
                        {"id": "brazier", "kind": "fire", "where": [0.9, 0.75], "area_pct": 2},
                        {"id": "wire", "kind": "wire", "where": [0.1, 0.4], "area_pct": 3, "thin": True},
                        {"id": "coat", "kind": "cloth", "where": [0.7, 0.7], "area_pct": 8, "on_body": True}]},
    "tracks": [{"track": "audio", "decision": "ambience_only", "why": "wind"}],
}
FACES_PX = [[360.0, 280.0, 40.0, 50.0, 0, 0, 0, 0, 0, 0, 372.0, 318.0, 388.0, 318.0, 0.93],     # live, 1000x1000 picture
            [700.0, 50.0, 200.0, 300.0, 0, 0, 0, 0, 0, 0, 760.0, 300.0, 840.0, 300.0, 0.55]]    # a false hit in the sky


def _dark(h=1000, w=1000, v=60):
    return np.full((h, w, 3), v, np.uint8)


def test_the_words_score_the_elements_and_the_fade_needs_them():
    rows = {r["id"]: r for r in LD.candidates(SEEN, SPINE, [], 3.0)}
    assert rows["low_sun_fade"]["text"] == 2 and not rows["low_sun_fade"].get("skip_why")      # "going"
    assert rows["low_sun"]["text"] == 1                                                         # "light" evokes the sun
    assert rows["wire"]["quality"] == 0 and rows["coat"]["quality"] == 0
    assert "brazier_embers" in rows and rows["brazier_embers"]["lights"] == ["brazier_flame"]
    quiet = [{"word": "two", "start_frame": 2}, {"word": "men", "start_frame": 9}]
    rows = {r["id"]: r for r in LD.candidates(SEEN, quiet, [], 3.0)}
    assert rows["low_sun_fade"]["skip_why"] == "the words do not say the light changes"


def test_faces_give_breath_in_the_cold_but_not_the_faces_of_a_picture():
    faces = LD.live_faces(FACES_PX, (1000, 1000), [])
    assert len(faces) == 1 and faces[0]["mouth"] == [0.38, 0.318]
    rows = {r["id"]: r for r in LD.candidates(SEEN, SPINE, faces, 3.0)}
    assert rows["breath_of_the_faces"]["points"] == [[0.38, 0.318]]
    assert LD.live_faces(FACES_PX, (1000, 1000), [[0.3, 0.2, 0.5, 0.4]]) == []          # inside a depicted portrait
    warm = copy.deepcopy(SEEN)
    warm["scene"]["surroundings"] = "summer noon"
    warm["seen"]["what"] = "two men at noon"
    assert "breath_of_the_faces" not in {r["id"] for r in LD.candidates(warm, SPINE, faces, 3.0)}


def test_the_weather_is_a_ceiling_decided_by_the_five_criteria_in_order():
    d = copy.deepcopy(SEEN)
    assert LD.decide_weather(d, SPINE, _dark()) == []                       # no snow in the scene: none in the shot
    d["scene"]["weather"] = ["snow_light"]
    r = LD.decide_weather(d, SPINE, _dark())[0]
    assert r["in"] and r["decided_by"] == "scene"
    shut = copy.deepcopy(d)
    shut["seen"]["sky_open"] = False
    assert LD.decide_weather(shut, SPINE, _dark())[0]["decided_by"] == "1 open_sky"
    r = LD.decide_weather(d, SPINE, _dark(v=235))[0]
    assert not r["in"] and r["decided_by"] == "2 light"                     # flakes would not read on a white picture
    close = LD.live_faces([[300.0, 200.0, 300.0, 400.0, 0, 0, 0, 0, 0, 0, 400.0, 500.0, 500.0, 500.0, 0.95]], (1000, 1000), [])
    r = LD.decide_weather(d, SPINE, _dark(), close)[0]
    assert r["layers"] == [0] and "only the far flakes" in r["picture"]
    snowing = SPINE + [{"word": "snow", "start_frame": 60}]
    assert LD.decide_weather(d, snowing, _dark())[0]["decided_by"] == "4 words"
    prev = {"weather": [{"weather": "snow_light", "in": False}]}
    r = LD.decide_weather(d, SPINE, _dark(), None, prev)[0]
    assert not r["in"] and r["decided_by"] == "5 neighbours"


def test_the_check_fails_snow_outside_the_ceiling_and_an_unexplained_leave_out():
    d = LD.direct(SEEN, SPINE, 72, 24.0, _dark(), FACES_PX)
    assert not [p for p in D.check(d, "abc", SPINE, frames=72) if p["level"] == "FAIL"]
    bad = copy.deepcopy(d)
    bad["tracks"].append({"id": "fx_snow", "track": "atmosphere", "op": "snow", "renderer": "directed25d", "params": {}})
    assert any("falls but the scene's weather" in p["what"] for p in D.check(bad, frames=72))
    out = copy.deepcopy(d)
    out["scene"]["weather"] = ["snow"]
    out["weather"] = [{"weather": "snow", "in": False, "decided_by": "1 open_sky", "why": "inside the dugout"}]
    assert not [p for p in D.check(out, frames=72) if p["level"] == "FAIL"]       # left out with a reason: no FAIL
    out["weather"][0]["why"] = ""
    assert any("left out without a reason" in p["what"] for p in D.check(out, frames=72))
    out["weather"] = []
    assert any("scene.weather names snow" in p["what"] for p in D.check(out, frames=72))


def test_a_weather_jump_between_neighbours_needs_a_reason_of_the_place():
    a = {"shot_id": "S08_SH001", "weather": [{"weather": "snow", "in": True, "decided_by": "scene", "why": "x"}]}
    b = {"shot_id": "S08_SH002", "weather": [{"weather": "snow", "in": False, "decided_by": "scene", "why": "x"}]}
    assert LD.weather_jumps([a, b])[0]["level"] == "FAIL"
    b["weather"][0]["decided_by"] = "1 open_sky"
    assert LD.weather_jumps([a, b]) == []
    c = {"shot_id": "S09_SH001", "weather": []}
    assert LD.weather_jumps([a, c]) == []


def test_direct_chooses_a_balanced_living_frame_with_a_reason_for_everything():
    d = LD.direct(SEEN, SPINE, 72, 24.0, _dark(), FACES_PX)
    living = d["seen"]["living"]
    assert all(str(e.get("why", "")).strip() for e in living)
    chosen = [e for e in living if e["decision"] != "skip"]
    fx = {t["id"]: t for t in d["tracks"] if t["track"] not in ("camera", "audio")}
    assert all(e["effects"][0] in fx for e in chosen)
    p = LV.plan(d, 3.0)
    assert not [n for n in p["notes"] if n.startswith("FAIL")]
    assert {"wire", "coat"} <= {e["id"] for e in living if e["decision"] == "skip"}
    ops = {t["op"] for t in fx.values()}
    assert "light_fade" in ops and "fire" in ops
    cams = [t for t in d["tracks"] if t["track"] == "camera"]
    assert cams[0]["op"] == "pull"                                          # the light is going: the camera pulls back
    accent = next(t for t in cams if t.get("timing", {}).get("start") == {"word": "thomas"})
    assert accent["target"]["mask"] == "thomas" and cams[-1]["op"] == "handheld"
    assert d["choice"]["camera"] and d["tracks"][-1]["track"] == "audio"


def test_the_balance_keeps_its_floor_outside_the_light_family():
    rows = [{"id": f"l{i}", "effect": e, "area_pct": 20, "text": 2, "focus": 2, "quality": 2, "cost": 2, "decision": "animate"}
            for i, e in enumerate(("sun_glint", "sun_shaft", "light_fade", "cloud_drift"))]
    rows.append({"id": "ice", "effect": "glint", "area_pct": 6, "text": 1, "focus": 2, "quality": 2, "cost": 2,
                 "decision": "animate"})
    p = LV.plan({}, 3.0, rows=rows)
    assert "ice" in {c["id"] for c in p["chosen"]} and len(p["chosen"]) == 4
    assert not [n for n in p["notes"] if n.startswith("FAIL")]
