import copy
import pytest
from explainer_engine.audio import val_word_cuts as m

W = [{"word": "hello", "start": 0.0, "end": 0.4}, {"word": "world", "start": 0.6, "end": 1.0}]
def r(t, f=40.0, w=W): return [x["rule"] for x in m.check(w, [{"t": t, "fade_ms": f}])]

def test_clean(): assert r(0.5) == []
def test_inside(): assert r(0.2) == ["CUT-01"]
def test_at_end(): assert r(0.4) == ["CUT-02"]
def test_pad_boundary(): assert r(0.43) == []
def test_close(): assert r(0.41) == ["CUT-02"]
def test_fade(): assert r(0.5, None) == ["CUT-03"] and r(0.5, 10) == ["CUT-03"]
def test_inside_and_fade(): assert r(0.2, 10) == ["CUT-01", "CUT-03"]
def test_before_first(): assert r(0.0) == ["CUT-02"] and r(-1.0) == []
def test_after_last(): assert r(2.0) == []
def test_bad():
    with pytest.raises(ValueError): m.check([{"word": "a", "start": 0, "end": 1}, {"word": "b", "start": 0.5, "end": 2}], [])
    with pytest.raises(ValueError): m.check(W, [{"t": "x", "fade_ms": 40}])
    with pytest.raises(ValueError): m.check([], [{"t": 1.0, "fade_ms": 40}])
def test_empty(): assert m.check(W, []) == []
def test_immutable():
    c = [{"t": 0.2, "fade_ms": 10}]; w0, c0 = copy.deepcopy(W), copy.deepcopy(c); m.check(W, c); assert W == w0 and c == c0
