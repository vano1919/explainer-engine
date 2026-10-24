"""LY-01..LY-08 (docs/KEYFRAME_GATE.md, Layout): sizes come from real heights and the camera, never from a guess."""

from PIL import Image

from explainer_engine.scripting import layout as L

OLD = "the old man with round glasses and a red scarf"
BUS = "the yellow city bus"
MAMMOTH = "the woolly mammoth with a broken left tusk"


def spec(mammoth_depth=11, elev=0, size="WS"):
    return {"id": "S02-01", "size": size, "angle": "low", "items": [
        {"tag": OLD, "kind": "old_adult", "where": "left", "lead": True},
        {"tag": "the nurse in the purple puffer jacket", "kind": "adult", "where": "right"},
        {"tag": BUS, "kind": "city_bus", "where": "center", "depth": 5},
        {"tag": MAMMOTH, "kind": "woolly_mammoth", "where": "center", "depth": mammoth_depth, "elev": elev}]}


def item(lay, tag):
    return next(i for i in lay["items"] if i["tag"] == tag)


def test_sizes_follow_real_heights_and_distance():
    lay = L.solve(spec())
    assert abs(item(lay, OLD)["height"] - L.LEAD_SHARE["WS"]) < 0.01          # the lead fills its shot size's share
    nurse = item(lay, "the nurse in the purple puffer jacket")
    assert nurse["height"] > item(lay, OLD)["height"]                          # same distance, taller person
    near = L.solve(spec(mammoth_depth=5))
    assert item(near, MAMMOTH)["height"] > item(near, BUS)["height"]           # side by side: a mammoth outgrows a bus
    assert item(lay, MAMMOTH)["height"] < item(lay, BUS)["height"]             # 6 m further back it looks smaller
    assert L.solve(spec(size="MWS"))["items"][0]["height"] > item(lay, OLD)["height"]


def test_the_check_catches_a_mammoth_hidden_behind_the_bus():
    found = L.check(L.solve(spec()))
    assert any(f["rule"] == "LY-04" and f["where"] == MAMMOTH and f["severity"] == "FAIL" for f in found)
    raised = L.solve(spec(elev=5))
    assert not [f for f in L.check(raised) if f["where"] == MAMMOTH and f["severity"] == "FAIL"]
    assert item(raised, MAMMOTH)["box"][1] < item(raised, BUS)["box"][1]       # it now rises above the bus roof


def test_overlap_outside_and_tiny_figures():
    s = spec(elev=5)
    s["items"].append({"tag": "the bearded man in the green beanie", "kind": "adult", "where": "right"})
    assert any("overlap" in f["detail"] for f in L.check(L.solve(s)))
    far = {"size": "EWS", "items": [{"tag": BUS, "kind": "city_bus", "where": "center", "lead": True},
                                    {"tag": "the lynx", "kind": "lynx", "where": "right", "depth": 40}]}
    assert any(f["rule"] == "LY-04" and "too small" in f["detail"] for f in L.check(L.solve(far)))
    off = {"size": "WS", "items": [{"tag": OLD, "kind": "old_adult", "where": "left", "lead": True},
                                   {"tag": BUS, "kind": "city_bus", "where": "center", "depth": -30}]}
    assert any(f["rule"] == "LY-03" for f in L.check(L.solve(off)))


def test_technical_relative_and_eligen_come_from_one_layout():
    lay = L.solve(spec(elev=5))
    tech = L.technical(lay)
    assert tech.startswith("The old man") and "35 % ± 5 % of the frame height" in tech and "centred 22 % from the left" in tech
    rel = L.relative(lay)
    assert f"{MAMMOTH} is about twice as tall as {OLD} and stands about 11 metres behind {OLD}, about 5 metres higher up" in rel
    assert "about one and a half times as tall as" in rel or "about twice as tall as" in rel
    boxes = L.eligen(lay)
    assert len(boxes) == 4 and all(0 <= v <= 1 for b in boxes for v in b["box"])


def test_blockout_is_nearer_lighter(tmp_path):
    lay = L.solve(spec(elev=5))
    im = Image.open(L.blockout(lay, tmp_path / "b.png")).convert("L")
    assert im.size == (1280, 720)
    def at(tag):
        x0, y0, x1, y1 = item(lay, tag)["box"]
        return im.getpixel((int((x0 + x1) / 2 * 1280), int((y0 + 0.75 * (y1 - y0)) * 720)))
    assert at(OLD) > at(BUS) > 0
    mx0, my0, mx1, my1 = item(lay, MAMMOTH)["box"]
    assert 0 < im.getpixel((int((mx0 + mx1) / 2 * 1280), int((my0 + 0.1 * (my1 - my0)) * 720))) < at(BUS)
