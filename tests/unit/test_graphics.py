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
