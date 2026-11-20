import copy
import pytest
from explainer_engine.audio import val_cue_binding as m

E = [{"id": "e1", "t": 2.0, "type": "object_in"}]
def C(i="c1", t=2.02, s="pop_a", e="e1", **k): d = {"id": i, "t": t, "sound_id": s, "event_id": e}; d.update(k); return d
def r(ev, cu, **kw): return [x["rule"] for x in m.check(ev, cu, **kw)]

def test_clean(): assert r(E, [C()]) == []
def test_late():
    f = m.check(E, [C(t=2.2)]); assert [x["rule"] for x in f] == ["BIND-03"] and f[0]["where"] == "c1"
def test_exact_frame(): assert r(E, [C(t=2.0 + 1 / 30)]) == []
def test_orphan(): assert sorted(r(E, [C(e="zz")])) == ["BIND-01", "BIND-02"]
def test_none_event(): assert sorted(r(E, [C(e=None)])) == ["BIND-01", "BIND-02"]
def test_pan(): assert r([{"id": "e1", "t": 2.0, "type": "pan"}], []) == []
def test_repeat():
    ev = [{"id": "e1", "t": 2.0, "type": "pan"}, {"id": "e2", "t": 3.0, "type": "pan"}]
    cu = [C("c1", 2.0, "p", "e1"), C("c2", 3.0, "p", "e2")]
    f = m.check(ev, cu); assert [(x["rule"], x["where"]) for x in f] == [("BIND-04", "c1|c2")]
    assert r(ev, [C("c1", 2.0, "p", "e1", repeat_ok=True), C("c2", 3.0, "p", "e2", repeat_ok=True)]) == []
    assert r(ev, [C("c1", 2.0, "p", "e1", repeat_ok=True), C("c2", 3.0, "p", "e2")]) == ["BIND-04"]
def test_three():
    ev = [{"id": f"e{i}", "t": float(i), "type": "pan"} for i in (1, 2, 3)]
    cu = [C(f"c{i}", float(i), "p", f"e{i}") for i in (1, 2, 3)]
    assert sorted(x["where"] for x in m.check(ev, cu)) == ["c1|c2", "c2|c3"]
def test_dup(): 
    with pytest.raises(ValueError): m.check(E + E, [])
def test_fps():
    L = m.Limits(fps=24, tol_frames=2)
    assert r(E, [C(t=2.0 + 2 / 24)], limits=L) == [] and r(E, [C(t=2.0 + 2 / 24 + 0.01)], limits=L) == ["BIND-03"]
