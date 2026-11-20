import copy
import pytest
from explainer_engine.audio import val_pace as m

def mk(zone_specs):
    words, zones = [], []
    for name, a, b, n in zone_specs:
        step = (b - a) / n if n else 1
        for i in range(n):
            s = a + i * step
            words.append({"word": "w", "start": s, "end": s + step / 2})
        zones.append({"zone": name, "start": a, "end": b})
    return words, zones

def rules(f): return [x["rule"] for x in f]

def test_example_clean():
    w, z = mk([("hook", 0, 20, 60), ("middle", 20, 80, 150), ("finale", 80, 100, 60)])
    assert m.check(w, z) == []

def test_all_170():
    w, z = mk([("hook", 0, 20, 57), ("middle", 20, 80, 170), ("finale", 80, 100, 57)])
    assert rules(m.check(w, z)) == ["PACE-02", "PACE-03"]

def test_overall_slow():
    w, z = mk([("hook", 0, 20, 50), ("middle", 20, 80, 110), ("finale", 80, 100, 50)])
    r = rules(m.check(w, z)); assert "PACE-01" in r and "PACE-02" not in r and "PACE-03" not in r

def test_overall_fast():
    w, z = mk([("hook", 0, 20, 80), ("middle", 20, 80, 210), ("finale", 80, 100, 80)])
    assert "PACE-01" in rules(m.check(w, z))

def test_hook_few_words():
    w, z = mk([("hook", 0, 20, 3), ("middle", 20, 80, 150), ("finale", 80, 100, 60)])
    f = m.check(w, z)
    assert any(x["rule"] == "PACE-04" and x["where"] == "hook" for x in f)
    assert not any(x["rule"] == "PACE-02" for x in f)

def test_zone_wpm():
    w, _ = mk([("hook", 0, 20, 30)])
    assert m.zone_wpm(w, {"zone": "hook", "start": 0, "end": 20}) == pytest.approx(90.0)

def test_overall_one_word():
    assert m.overall_wpm([{"word": "a", "start": 0, "end": 1}]) is None

def test_bad_zone():
    w, z = mk([("hook", 0, 20, 60), ("middle", 20, 80, 150), ("finale", 80, 100, 60)])
    z2 = copy.deepcopy(z); z2[0]["end"] = z2[0]["start"]
    with pytest.raises(ValueError): m.check(w, z2)
    z3 = copy.deepcopy(z); z3[1]["zone"] = "hook"
    with pytest.raises(ValueError): m.check(w, z3)

def test_severity_and_immutable():
    w, z = mk([("hook", 0, 20, 57), ("middle", 20, 80, 170), ("finale", 80, 100, 57)])
    w0, z0 = copy.deepcopy(w), copy.deepcopy(z)
    f = m.check(w, z, m.Limits(severity="FAIL"))
    assert f and all(x["severity"] == "FAIL" for x in f)
    assert w == w0 and z == z0

def test_finding_shape():
    w, z = mk([("hook", 0, 20, 57), ("middle", 20, 80, 170), ("finale", 80, 100, 57)])
    for x in m.check(w, z): assert set(x) == {"rule", "severity", "where", "detail"}
