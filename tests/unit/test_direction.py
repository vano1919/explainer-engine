"""P1 (roadmap 2026-11-14 B.1): the Scene Director's draft file: a change without a reason FAILs, targets must be things the
director saw, still_by_design does not move the camera, words resolve to the shot's own clock, variants replace the tracks."""
from __future__ import annotations

import copy

import pytest

from explainer_engine.production import direction as D

SPINE = [{"word": "no", "frame": 149}, {"word": "nobody", "frame": 211}, {"word": "asked", "frame": 217}]
BASE = {
    "schema": D.SCHEMA, "shot_id": "S02_SH008", "picture_sha256": "abc", "intent": "intended",
    "seen": {"what": "two men by a brazier", "objects": [{"id": "thomas", "points": [[0.3, 0.5]]}],
             "lights": [{"id": "flame", "point": [0.5, 0.7], "radius": 0.03}]},
    "tracks": [
        {"track": "camera", "op": "hold", "renderer": "directed25d", "timing": {"end": {"word": "nobody"}}, "validate": {}},
        {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 1.0},
         "target": {"mask": "thomas", "point": [0.355, 0.33]},
         "timing": {"start": {"word": "nobody"}, "end": {"frac": 1.0}}, "validate": {"measure": "scale"}},
        {"track": "lighting", "op": "fire", "renderer": "directed25d", "target": {"lights": ["flame"]}, "params": {}},
        {"track": "audio", "decision": "ambience_only", "why": "brazier"}],
    "overrides": [{"field": "camera.push.target", "from": "centre", "to": "Thomas", "why": "the line is about him"}],
}


def test_a_good_file_passes_and_resolves_words_to_frames():
    assert D.check(BASE, "abc") == []
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
