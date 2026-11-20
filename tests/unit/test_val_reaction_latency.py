import copy
import pytest
from explainer_engine.audio import val_reaction_latency as m

def R(kind, t, et=5.0): return [{"id": "r", "kind": kind, "t": t, "event_t": et}]
def r(x, **kw): return [f["rule"] for f in m.check(x, **kw)]

def test_ok(): assert r(R("gasp", 5.25)) == []
def test_laugh(): assert r(R("laugh", 5.0)) == ["LAT-02"]
def test_before(): assert r(R("gasp", 4.9)) == ["LAT-01"]
def test_edge(): assert r(R("gasp", 5.35)) == []
def test_over(): assert r(R("gasp", 5.36)) == ["LAT-02"]
def test_unknown(): assert r(R("boo", 5.3)) == ["LAT-03"]
def test_custom(): assert r(R("boo", 5.3), limits=m.Limits(latency_s={"boo": 0.3})) == []
def test_severity():
    assert m.check(R("laugh", 5.0))[0]["severity"] == "REVIEW"
    assert m.check(R("laugh", 5.0), m.Limits(severity="FAIL"))[0]["severity"] == "FAIL"
def test_bad():
    with pytest.raises(ValueError): m.check([{"id": "r", "kind": "gasp", "t": 1.0}])
    with pytest.raises(ValueError): m.check(R("gasp", "x"))
def test_empty(): assert m.check([]) == []
