import copy
import pytest
from explainer_engine.audio import val_sound_licences as m

def I(id="i", cls="sfx", source="s", licence="personal use", checked=False): return {"id": id, "class": cls, "source": source, "licence": licence, "licence_checked": checked}
def r(items, mon=False, **kw): return [x["rule"] for x in m.check(items, mon, **kw)]

def test_m1(): assert r([I("m1", "music", "free library", "CC0", True)]) == []
def test_music():
    assert r([I(cls="music", licence="CC0", checked=False)]) == ["LIC-01"]
    assert r([I(cls="music", licence="  ", checked=True)]) == ["LIC-01"]
def test_sfx_recorded(): assert r([I()]) == []
def test_sfx_missing(): assert r([I(licence="")]) == ["LIC-02"] and r([I(cls="ambience", licence="")]) == ["LIC-02"]
def test_banned():
    x1 = I("x1", "sfx", "BBC RemArc 07021", "RemArc", False)
    assert r([x1], True) == ["LIC-03"] and r([x1], False) == []
def test_case(): assert r([I(source="bbc REMARC")], True) == ["LIC-03"]
def test_ids(): assert r([I("a1")], True, limits=m.Limits(banned_ids=frozenset({"a1"}))) == ["LIC-03"]
def test_music_both(): assert r([I("b", "music", "BBC RemArc", "x", False)], True) == ["LIC-01", "LIC-03"]
def test_bad():
    with pytest.raises(ValueError): m.check([I(cls="voice")], False)
    d = I(); del d["source"]
    with pytest.raises(ValueError): m.check([d], False)
def test_empty(): assert m.check([], True) == []
