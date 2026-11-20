import copy
import pytest
from explainer_engine.audio import val_clip_fit as m

def L(id, s, a, b): return {"id": id, "shot_id": s, "start": a, "end": b}
CLIP = [{"shot_id": "s1", "start": 10.0, "end": 14.0}]
def r(lines, clips=CLIP): return [x["rule"] for x in m.check(lines, clips)]

def test_example(): assert r([L("L1", "s1", 10.2, 13.5)]) == []
def test_tail(): assert r([L("L1", "s1", 10.2, 13.9)]) == ["CLIP-01"]
def test_tail_boundary(): assert r([L("L1", "s1", 10.2, 13.75)]) == []
def test_lead(): assert r([L("L1", "s1", 9.9, 13.5)]) == ["CLIP-02"]
def test_lead_ok(): assert r([L("L1", "s1", 9.96, 13.5)]) == []
def test_slack():
    assert r([L("L1", "s1", 10.2, 13.5)], [{"shot_id": "s1", "start": 10.0, "end": 20.0}]) == ["CLIP-03"]
def test_no_clip(): assert r([L("L1", "zz", 10.2, 13.5)]) == ["CLIP-04"]
def test_shared_shot():
    ls = [L("a", "s1", 10.2, 11.0), L("b", "s1", 12.0, 13.5)]
    assert r(ls) == []
    f = m.check(ls, [{"shot_id": "s1", "start": 10.0, "end": 13.6}])
    assert [x["rule"] for x in f] == ["CLIP-01"] and f[0]["where"] == "s1"
def test_bad():
    with pytest.raises(ValueError): m.check([L("a", "s1", 5, 4)], CLIP)
    with pytest.raises(ValueError): m.check([L("a", "s1", 10.2, 13)], [{"shot_id": "s1", "start": 5, "end": 5}])
def test_sorted_immutable():
    ls = [L("b", "s1", 12.0, 13.5), L("a", "zz", 1.0, 2.0)]
    c = copy.deepcopy(ls); f = m.check(ls, CLIP)
    assert ls == c and [x["where"] for x in f] == ["a", "b"]
