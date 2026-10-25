from PIL import Image

from explainer_engine.production import graphics as G, validate


def frame():
    return Image.new("RGB", (640, 360), (120, 130, 110))


def test_card_dims_and_draws_then_leaves():
    spec = {"title": "WEEK 1", "line": "Can knowledge replace calluses?"}
    mid = G.card(frame(), spec, 1.5, 7, 1)
    assert mid.getpixel((5, 5)) != frame().getpixel((5, 5))  # the picture is dimmed
    assert G.card(frame(), spec, G.card_length() + 0.1, 7, 1).tobytes() == frame().tobytes()  # gone after its length


def test_each_visual_kind_draws():
    base = frame()
    kinds = [{"kind": "calc", "lines": ["a", "b", "c"]}, {"kind": "bars", "bars": [{"label": "x", "value": 1, "text": "1"}, {"label": "y", "value": 2, "text": "2"}]},
             {"kind": "timeline", "span": "6,700 years", "marks": [{"at": 0.0, "label": "a"}, {"at": 1.0, "label": "b"}]}]
    for g in kinds:
        out = G.visual(base, dict(g, title="T"), 2.0, 5.0)
        assert out.tobytes() != base.tobytes()
        assert G.visual(base, dict(g, title="T"), 6.0, 5.0).tobytes() == base.tobytes()  # leaves before the hold ends


def test_visual_checks():
    good = {"id": "g", "kind": "calc", "lines": ["a", "b"], "claim": "C-08", "hold": 4}
    assert G.check_visual(good) == []
    assert G.check_visual(dict(good, claim=""))  # no claim
    assert G.check_visual(dict(good, hold=9))  # too long
    assert G.check_visual({"kind": "bars", "bars": [{"label": "a", "value": 0, "text": "0"}] * 2, "claim": "C", "hold": 4})


def test_validate_flags_a_period_without_a_visual():
    import json
    from pathlib import Path
    doc = json.loads((Path(__file__).parents[2] / "examples/stone_age/ep1_v1/production_script.json").read_text(encoding="utf-8"))
    assert not [f for f in validate.check_script(doc) if f["rule"] in ("PV-30", "PV-31")]
    doc["graphics"] = [g for g in doc["graphics"] if g["id"] not in ("G10", "G11")]
    assert any(f["rule"] == "PV-31" and f["where"] == "compare" for f in validate.check_script(doc))


def test_counter_chip_draws_in_the_corner_and_flips():
    base = frame()
    out = G.counter(base, "YEAR 2", 2.0, "YEAR 1")
    diff = [(x, y) for x in range(0, 640, 8) for y in range(0, 360, 8) if out.getpixel((x, y)) != base.getpixel((x, y))]
    assert diff and max(x for x, _ in diff) < 640 * 0.4 and max(y for _, y in diff) < 360 * 0.2  # a small top-left chip
    assert G.counter(base, "YEAR 2", 0.1, "YEAR 1").tobytes() != out.tobytes()  # mid-flip differs from the settled chip


def test_counter_checks():
    segs = ["S01", "S02", "S03"]
    assert G.check_counter([{"segment": "S01", "label": "DAY 1"}, {"segment": "S03", "label": "WEEK 1"}], segs) == []
    assert G.check_counter([{"segment": "S09", "label": "DAY 1"}], segs)  # unknown segment
    assert G.check_counter([{"segment": "S03", "label": "A"}, {"segment": "S01", "label": "B"}], segs)  # out of order
    assert G.check_counter([{"segment": "S01", "label": "DAY 1"}, {"segment": "S02", "label": "DAY 1"}], segs)  # no change
    assert G.check_counter([{"segment": "S01", "label": "THE FIFTEENTH YEAR"}], segs)  # too long


def test_counter_spans_from_segment_to_next_label():
    from explainer_engine.production import assemble
    timed = {"cards": [], "visuals": [], "counters": [
        {"label": "DAY 1", "start_frame": 0, "end_frame": 50, "prev": None},
        {"label": "WEEK 1", "start_frame": 50, "end_frame": 100, "prev": "DAY 1"}]}
    a = assemble.overlays(frame(), 10, 25, timed)
    b = assemble.overlays(frame(), 90, 25, timed)
    assert a.tobytes() != frame().tobytes() and a.tobytes() != b.tobytes()
    assert assemble.overlays(frame(), 120, 25, timed).tobytes() == frame().tobytes()
