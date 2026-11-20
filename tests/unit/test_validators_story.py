"""W2: story validators on the v4 model (the gap W8 found: story_lint/scene_lint skip these on a 4.0.0 script)."""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.validators import prompts as P
from explainer_engine.validators import story as S


def _st(rows):
    return [r["status"] for r in (rows if isinstance(rows, list) else [rows])]


def _script(**kw):
    base = {"audio_lines": [
        {"line_id": "L1", "segment_id": "S1", "speaker_type": "narrator", "text": "Snow fell on the wire.", "citation_ids": ["C-01"]},
        {"line_id": "L2", "segment_id": "S1", "speaker_type": "character", "speaker_id": "hale", "text": "Cold, sir."}],
        "world_bible": {"characters": [{"character_id": "hale", "name": "Thomas Hale"}]}, "shots": []}
    base.update(kw)
    return base


def test_immersion_and_showing_on_v4_lines():
    ok = S.immersion_and_showing(_script())
    assert _st(ok) == [G.PASS, G.PASS]
    bad = _script(audio_lines=[{"line_id": "L1", "segment_id": "S1", "speaker_type": "narrator",
                                "text": "This is a work of fiction and none of this happened."}])
    assert S.immersion_and_showing(bad)[0]["status"] in (G.REVIEW, G.FAIL)   # severity is BP-88's own


def test_turn_length():
    assert _st(S.turn_length(_script())) == [G.PASS]
    long = _script(audio_lines=[{"line_id": "L", "speaker_type": "character", "text": " ".join(["word"] * 200)}])
    assert _st(S.turn_length(long)) in ([G.REVIEW], [G.FAIL])
    assert _st(S.turn_length({"audio_lines": []})) == [G.NOT_RUN]


def test_value_charge_cadence():
    flips = [{"target_duration_seconds": 5, "charge": c} for c in (1, -1, 1, -1)]
    flat = [{"target_duration_seconds": 30, "charge": -1} for _ in range(4)]
    assert S.value_charge_cadence(flips)["status"] == G.PASS
    assert S.value_charge_cadence(flat)["status"] == G.REVIEW
    assert S.value_charge_cadence([{"target_duration_seconds": 5}])["status"] == G.NOT_RUN


def test_scene_header_wants_and_turn():
    ok = {"scene_id": "A", "wants": {"hale": "a truce", "fritz": "his orders"}, "turn": "the carol"}
    assert _st(S.scene_headers([ok])) == [G.PASS]
    assert _st(S.scene_headers([{"scene_id": "B", "wants": {"hale": "x"}}])) == [G.REVIEW]
    assert _st(S.scene_headers([])) == [G.NOT_RUN]


def test_narrated_sentence_not_stronger_than_its_claim():
    cmap = {"C-01": {"sentence": "Snow fell on the wire.", "label": "E", "source": ""}}
    ok = S.stronger_than_claim(_script(), cmap)
    assert _st(ok) == [G.PASS]
    strong = _script(audio_lines=[{"line_id": "L1", "speaker_type": "narrator", "text": "Everyone always froze.", "citation_ids": ["C-01"]}])
    r = S.stronger_than_claim(strong, cmap)
    assert _st(r) == [G.REVIEW] and r[0]["measured"] == ["always", "everyone"]
    assert _st(S.stronger_than_claim(_script(audio_lines=[]), cmap)) == [G.NOT_RUN]


def test_numeric_claim_names_two_sources():
    two = {"C-01": {"sentence": "100,000 men fought.", "source": "https://a.example/x https://b.example/y"}}
    one = {"C-01": {"sentence": "100,000 men fought.", "source": "https://a.example/x"}}
    assert _st(S.numeric_claim_sources(two)) == [G.PASS]
    assert _st(S.numeric_claim_sources(one)) == [G.REVIEW]
    assert _st(S.numeric_claim_sources({"C-02": {"sentence": "No numbers.", "source": ""}})) == [G.NOT_RUN]


def test_validate_reports_every_rule_and_press_release():
    rows = S.validate(_script(), claim_map={"C-01": {"sentence": "Snow fell.", "source": ""}},
                      scenes=[{"scene_id": "A", "wants": {"a": "x", "b": "y"}, "turn": "t"}])
    assert {r["gate"].split(":")[0] for r in rows} == set(S.RULE_IDS)
    pr = _script(audio_lines=[{"line_id": "L", "speaker_type": "narrator", "text": "The film comes out on Friday."}])
    assert S.press_release(pr)["status"] in (G.REVIEW, G.FAIL)


def test_lens_named_in_every_image_prompt():
    good = {"shot_id": "A", "image_prompt": {"start_frame_prompt": "A soldier at dawn, 85mm lens, f/1.8, shallow depth of field"}}
    bad = {"shot_id": "B", "image_prompt": {"start_frame_prompt": "A soldier at dawn, 35mm anamorphic"}}
    r = P.lens_named([good, bad, {"shot_id": "C"}])
    assert _st(r) == [G.PASS, G.REVIEW, G.NOT_RUN] and r[1]["measured"] == ["aperture", "depth_of_field"]
