import copy
import pytest
from explainer_engine.audio import val_stem_levels as m

inf = float("inf")
def S(layer, p, **k): d = {"id": "s", "layer": layer, "peak_dbfs": p}; d.update(k); return d
def r(x, **kw): return [f["rule"] for f in m.check([x], **kw)]

def test_dialogue(): assert r(S("dialogue", -5)) == [] and r(S("dialogue", -1)) == ["STEM-01"] and r(S("dialogue", -12)) == ["STEM-02"]
def test_edges(): assert r(S("dialogue", -9.0)) == [] and r(S("dialogue", -3.0)) == []
def test_dense(): assert r(S("sfx", -14, dense=True)) == [] and r(S("sfx", -14)) == ["STEM-02"]
def test_dense_high(): assert r(S("sfx", -7, dense=True)) == ["STEM-01"]
def test_dense_dialogue(): assert r(S("dialogue", -5, dense=True)) == [] and r(S("dialogue", -12, dense=True)) == ["STEM-02"]
def test_silent(): assert r(S("ambience", -inf)) == ["STEM-03"] and r(S("ambience", -130.0)) == ["STEM-03"]
def test_unknown(): assert r(S("voiceover", -5)) == ["STEM-04"]
def test_nan():
    with pytest.raises(ValueError): m.check([S("dialogue", float("nan"))])
def test_custom(): assert r(S("x", -15), limits=m.Limits(ranges={"x": (-20.0, -10.0)})) == []
def test_empty(): assert m.check([]) == []
