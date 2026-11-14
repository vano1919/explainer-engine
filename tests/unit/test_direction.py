"""P1 (roadmap 2026-11-14 B.1): the Scene Director's draft file: a change without a reason FAILs, targets must be things the
director saw, still_by_design does not move the camera, words resolve to the shot's own clock, variants replace the tracks."""
from __future__ import annotations

import copy

import pytest

from explainer_engine.production import direction as D

def LP(area_pct, text, focus, quality, cost):
    return {"area_pct": area_pct, "text": text, "focus": focus, "quality": quality, "cost": cost}


SPINE = [{"word": "no", "frame": 149}, {"word": "nobody", "frame": 211}, {"word": "asked", "frame": 217}]
BASE = {
    "schema": D.SCHEMA, "shot_id": "S02_SH008", "picture_sha256": "abc", "intent": "intended",
    "seen": {"what": "two men by a brazier", "objects": [{"id": "thomas", "points": [[0.3, 0.5]], "names": ["nobody"]}],
             "lights": [{"id": "flame", "point": [0.5, 0.7], "radius": 0.03}],
             "living": [{"id": "brazier", "kind": "fire", "where": [0.5, 0.7], "decision": "animate", "effects": ["fx_fire"],
                         **LP(2, 1, 2, 2, 2)},
                        {"id": "brazier_smoke", "kind": "smoke", "where": [0.5, 0.6], "decision": "animate",
                         "effects": ["fx_smoke"], **LP(3, 0, 1, 2, 2)},
                        {"id": "trench_mist", "kind": "mist", "where": [0.5, 0.8], "decision": "animate",
                         "effects": ["fx_mist"], **LP(30, 0, 1, 2, 2)},
                        {"id": "dusk_sky", "kind": "sky", "where": [0.5, 0.1], "decision": "animate",
                         "effects": ["fx_sky"], **LP(10, 0, 0, 2, 2)}]},
    "tracks": [
        {"track": "camera", "op": "hold", "renderer": "directed25d", "timing": {"end": {"word": "nobody"}}, "validate": {}},
        {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 1.0},
         "target": {"mask": "thomas", "point": [0.355, 0.33]},
         "timing": {"start": {"word": "nobody"}, "end": {"frac": 1.0}}, "validate": {"measure": "scale"}},
        {"track": "lighting", "op": "fire", "renderer": "directed25d", "target": {"lights": ["flame"]}, "params": {},
         "id": "fx_fire"},
        {"track": "atmosphere", "op": "smoke", "renderer": "directed25d", "target": {"point": [0.5, 0.6]}, "params": {},
         "id": "fx_smoke"},
        {"track": "atmosphere", "op": "mist", "renderer": "directed25d", "params": {}, "id": "fx_mist"},
        {"track": "atmosphere", "op": "cloud_drift", "renderer": "directed25d", "params": {}, "id": "fx_sky"},
        {"track": "camera", "op": "handheld", "renderer": "directed25d", "params": {"strength": 0.3}, "validate": {}},
        {"track": "audio", "decision": "ambience_only", "why": "brazier"}],
    "overrides": [{"field": "camera.push.target", "from": "centre", "to": "Thomas", "why": "the line is about him"}],
}


def test_a_good_file_passes_and_resolves_words_to_frames():
    assert D.check(BASE, "abc") == []
    assert D.check(BASE, "abc", SPINE, frames=263) == []
    plan = D.resolve(BASE, 263, SPINE)
    assert plan["cameras"] == [{"op": "push", "strength": 1.0, "direction": None, "from": 211, "to": 263,
                                "easing": "ease_in_out", "target": {"mask": "thomas", "point": [0.355, 0.33]}}]
    assert plan["effects"][0]["op"] == "fire" and plan["effects"][0]["lights"] == ["flame"]


def test_change_without_reason_fails():
    d = copy.deepcopy(BASE)
    d["overrides"][0]["why"] = " "
    assert any("without a reason" in p["what"] for p in D.check(d))


def test_targets_must_be_seen_and_pictures_must_match():
    d = copy.deepcopy(BASE)
    d["tracks"][1]["target"]["mask"] = "chaplain"
    d["tracks"][2]["target"]["lights"] = ["lantern"]
    whats = " ".join(p["what"] for p in D.check(d, "other"))
    assert "chaplain" in whats and "lantern" in whats and "another picture" in whats


def test_still_by_design_does_not_move_and_minimal_is_capped():
    d = copy.deepcopy(BASE)
    d["intent"] = "still_by_design"
    assert any("camera moves" in p["what"] for p in D.check(d))
    still = copy.deepcopy(d)
    still["tracks"] = [t for t in d["tracks"] if t["track"] != "camera" or t["op"] == "hold"]
    assert not [p for p in D.check(still) if p["level"] == "FAIL"]
    d["intent"] = "minimal"
    probs = D.check(d)
    assert any(p["level"] == "REVIEW" and "minimal" in p["what"] for p in probs)


def test_unknown_word_and_variants():
    with pytest.raises(ValueError):
        D.word_frame(SPINE, "pope")
    assert D.word_frame([{"word": "German", "frame": 125}, {"word": "german", "frame": 179}], "german", 2) == 179
    d = copy.deepcopy(BASE)
    d["variants"] = {"C1": {"tracks": [{"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 0.5},
                                        "validate": {}}]}}
    plan = D.resolve(d, 263, SPINE, "C1")
    assert plan["cameras"][0]["strength"] == 0.5 and plan["cameras"][0]["target"] is None and not plan["effects"]


def test_seen_what_is_required():
    d = copy.deepcopy(BASE)
    d["seen"]["what"] = ""
    assert any("seen.what" in p["what"] for p in D.check(d))


# --- the owner's rules of 2026-11-14 (BP-185, BP-195, BP-196, BP-197) -------------------------------------------------------

def _whats(probs, level=None):
    return " | ".join(p["what"] for p in probs if level is None or p["level"] == level)


def test_the_living_inventory_is_required_and_must_cover_what_the_director_wrote():
    d = copy.deepcopy(BASE)
    del d["seen"]["living"]
    assert "seen.living is missing" in _whats(D.check(d), "FAIL")
    # the S01 case: the director wrote "sunrise" and "trees" but gave the sun and the trees nothing
    d = copy.deepcopy(BASE)
    d["seen"]["what"] = "sunrise over no man's land, frosted trees, barbed wire"
    f = _whats(D.check(d), "FAIL")
    assert "names sun" in f and "names plants" in f and "names wire" in f and "names ice" in f


def test_scene_weather_and_the_words_decide_the_surroundings():
    d = copy.deepcopy(BASE)
    d["scene"] = {"weather": ["snow", "wind"], "surroundings": "dawn"}
    f = _whats(D.check(d), "FAIL")
    assert "scene.weather names snow" in f and "scene.weather names wind" in f and "scene.surroundings names sun" in f
    spine = SPINE + [{"word": "snowing", "frame": 240}]
    assert "the shot's words name snow" in _whats(D.check(BASE, spine=spine, frames=263), "FAIL")
    # added snow (not in the picture, but the scene says so) with a snow track satisfies it
    d = copy.deepcopy(BASE)
    d["scene"] = {"weather": ["snow"]}
    d["seen"]["living"].append({"id": "snowfall", "kind": "snow", "decision": "add", "effects": ["fx_snow"]})
    d["tracks"].append({"track": "atmosphere", "op": "snow", "renderer": "directed25d", "params": {}, "id": "fx_snow"})
    f = _whats(D.check(d), "FAIL")
    assert "names snow" not in f
    assert "cannot draw 'snow' yet" in f            # until the renderer has the op, the gap is a FAIL, not a frozen sky


def test_a_skipped_element_needs_a_reason_and_is_shown_to_the_reviewer():
    d = copy.deepcopy(BASE)
    d["seen"]["living"].append({"id": "sky", "kind": "sky", "decision": "skip"})
    assert "without a reason" in _whats(D.check(d), "FAIL")
    d["seen"]["living"][-1]["why"] = "a sliver of sky behind the sandbags, under 1 % of the frame"
    probs = D.check(d)
    assert not _whats(probs, "FAIL") and "left frozen" in _whats(probs, "REVIEW")


def test_an_effect_must_suit_its_element():
    d = copy.deepcopy(BASE)
    d["seen"]["living"][1]["effects"] = ["fx_fire"]
    assert "does not move a smoke" in _whats(D.check(d), "FAIL")
    d["seen"]["living"][1]["effects"] = ["fx_none"]
    assert "does not exist" in _whats(D.check(d), "FAIL")


def test_bp185_two_families_whatever_the_intent():
    d = copy.deepcopy(BASE)
    d["intent"] = "still_by_design"
    d["tracks"] = [t for t in d["tracks"] if t.get("op") not in ("push", "smoke", "mist", "cloud_drift")]
    d["seen"]["living"] = d["seen"]["living"][:1]
    f = _whats(D.check(d), "FAIL")
    assert "BP-185 needs" in f and "whatever the intent" in f
    d["tracks"].append({"track": "lighting", "op": "candle", "renderer": "directed25d", "params": {}, "id": "c"})
    d["tracks"].append({"track": "lighting", "op": "sun_shaft", "renderer": "directed25d", "params": {}, "id": "s"})
    assert "BP-185" in _whats(D.check(d), "FAIL")       # three light effects are still one family


def test_the_camera_follows_the_words():
    d = copy.deepcopy(BASE)
    d["tracks"][1]["target"] = {"point": [0.5, 0.5]}       # the push no longer aims at Thomas
    assert "no camera track aims at it" in _whats(D.check(d, spine=SPINE, frames=263), "FAIL")
    d = copy.deepcopy(BASE)
    d["tracks"][1]["timing"]["start"] = {"frame": 100}     # aimed, but 4.6 s before the word
    assert "BP-195" in _whats(D.check(d, spine=SPINE, frames=263), "REVIEW")
    d = copy.deepcopy(BASE)
    d["tracks"][1]["target"] = {"point": [0.5, 0.5]}
    d["text_targets_skip"] = [{"word": "nobody", "why": "Thomas already fills the frame"}]
    assert not _whats(D.check(d, spine=SPINE, frames=263), "FAIL")


def test_a_long_hold_before_the_first_move_is_review_unless_the_camera_drifts():
    d = copy.deepcopy(BASE)                                  # push on 'nobody' at frame 211: 8.8 s of standing
    d["tracks"] = [t for t in d["tracks"] if t.get("op") != "handheld"]
    r = _whats(D.check(d, spine=SPINE, frames=263), "REVIEW")
    assert "stands for 8.8 s" in r
    d["tracks"].append({"track": "camera", "op": "handheld", "renderer": "directed25d", "params": {"strength": 0.4},
                        "validate": {}})
    assert "stands for" not in _whats(D.check(d, spine=SPINE, frames=263))


def test_kinds_named_reads_words_and_lists():
    assert D.kinds_named("Snow falls on the frozen willows at dawn.") == {"snow", "ice", "plants", "sun"}
    assert D.kinds_named(["The", "brazier", "smoke"]) == {"fire", "smoke"}


# --- BP-200: Fable's living-photo balance (LP-01..LP-12) ----------------------------------------------------------------------

def test_the_balance_needs_scores_and_a_floor_of_moving_air():
    d = copy.deepcopy(BASE)
    for e in d["seen"]["living"]:
        for k in ("area_pct", "text", "focus", "quality", "cost"):
            e.pop(k)
    assert "no LP scores" in _whats(D.check(d, frames=263), "REVIEW")
    d = copy.deepcopy(BASE)                                  # without the mist and the sky only smoke moves beyond the flame
    d["seen"]["living"] = d["seen"]["living"][:2]
    d["tracks"] = [t for t in d["tracks"] if t.get("id") not in ("fx_mist", "fx_sky")]
    f = _whats(D.check(d, frames=263), "FAIL")
    assert "only 1 living effects" in f and "no full-frame layer of moving air" in f


def test_lp_tiers_routes_and_weather():
    from explainer_engine.production import living as L
    assert L.tier({"effect": "sun_shaft", "area_pct": 20, "text": 2, "focus": 2, "quality": 2, "cost": 2}) == "P1"
    assert L.tier({"effect": "foliage_sway", "area_pct": 0.1, "text": 0, "focus": 2, "quality": 2, "cost": 2}) == "SKIP_DOT"
    assert L.tier({"effect": "glow", "area_pct": 0.1, "text": 0, "focus": 1, "quality": 2, "cost": 2}) == "P3"   # a group
    assert L.tier({"effect": "wire_sway", "area_pct": 6, "text": 0, "focus": 1, "quality": 0, "cost": 0}) == "SKIP_QUALITY"
    assert L.tier({"effect": "fire", "area_pct": 1, "text": 2, "body_motion": True}) == "LTX"
    assert (L.cap(3.0), L.cap(7.8), L.cap(11.0)) == (4, 5, 6)
    d = copy.deepcopy(BASE)
    d["scene"] = {"weather": ["snow"]}                       # LP-09 (the owner: snow only in S08): the scene adds its snow
    p = L.plan(d, 263 / 24)
    assert any(c["effect"] == "snow" for c in p["chosen"]) and p["always_on"][0]["id"] == "brazier"
    d["people_mid_or_close"] = True
    d["seen"]["living"].append({"id": "lips", "kind": "body", "decision": "animate", "effect": "subject_sway",
                                "body_motion": True, **LP(0.3, 2, 2, 2, 0)})
    notes = " | ".join(L.plan(d, 263 / 24)["notes"])
    assert "ROUTE LP-02" in notes and "ROUTE LP-10" in notes


def test_an_animated_element_the_balance_did_not_choose_is_shown():
    d = copy.deepcopy(BASE)
    d["seen"]["living"].append({"id": "far_pine", "kind": "plants", "decision": "animate", "effects": ["fx_pine"],
                                **LP(0.1, 0, 0, 1, 1)})
    d["tracks"].append({"track": "atmosphere", "op": "foliage_sway", "renderer": "directed25d", "params": {}, "id": "fx_pine"})
    assert "far_pine is animated but LP-04..07 did not choose it (SKIP_DOT" in _whats(D.check(d, frames=263), "REVIEW")
