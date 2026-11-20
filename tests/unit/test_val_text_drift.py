import copy
import pytest
from explainer_engine.audio import val_text_drift as m

F = "He stopped. The door was open."
def r(p, f=F, **kw): return [x["rule"] for x in m.check(f, p, **kw)]

def test_same(): assert r("[whispers] He stopped... the DOOR was open!") == []
def test_added():
    f = m.check(F, "He stopped. The door was wide open."); assert [x["rule"] for x in f] == ["DRIFT-02"] and "wide" in f[0]["detail"] and f[0]["where"] == "word 5"
def test_removed(): assert r("He stopped. The door was open.", "He stopped. The very door was open.") == ["DRIFT-01"]
def test_replaced(): assert r("He stopped. The door was closed.") == ["DRIFT-03"]
def test_um():
    assert r("Um he stopped. The door was open.") == ["DRIFT-02"]
    assert r("Um he stopped. The door was open.", limits=m.Limits(allowed_interjections=frozenset({"um"}))) == []
def test_runs():
    L = m.Limits(allowed_interjections=frozenset({"wide"}))
    assert r("He stopped. The door was wide, wide open.", limits=L) == []
    assert r("Um oh he stopped. The door was open.", limits=m.Limits(allowed_interjections=frozenset({"um"}))) == ["DRIFT-02"]
def test_words_of():
    assert m.words_of("[laughs] It's 1914!") == ["it's", "1914"]
    assert m.words_of("a [b [c] d") == ["a", "d"]
def test_empty(): assert m.check("", "") == []
def test_two():
    f = m.check("a b c d e f g", "a X c d e f"); assert len(f) == 2 and [x["where"] for x in f] == ["word 1", "word 6"]
def test_bad():
    with pytest.raises(ValueError): m.check(1, "x")
