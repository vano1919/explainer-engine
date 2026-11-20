import copy
import numpy as np, pytest
from explainer_engine.audio import val_voice_similarity as m

def C(i, ch, e): return {"id": i, "character": ch, "embedding": e}
ANNA = [C("a1", "anna", [1, 0, 0]), C("a2", "anna", [0.99, 0.1, 0]), C("a3", "anna", [0, 1, 0])]
BOB = [C("b1", "bob", [0, 0, 1]), C("b2", "bob", [0, 0, 1])]

def test_cosine():
    assert m.cosine(np.array([1., 0]), np.array([1., 0])) == pytest.approx(1.0, abs=1e-9)
    assert m.cosine(np.array([1., 0]), np.array([0., 1])) == pytest.approx(0.0, abs=1e-9)
    assert m.cosine(np.array([1., 0]), np.array([-1., 0])) == pytest.approx(-1.0, abs=1e-9)
def test_cosine_bad():
    with pytest.raises(ValueError): m.cosine(np.zeros(2), np.array([1., 0]))
    with pytest.raises(ValueError): m.cosine(np.array([1., 0]), np.array([1., 0, 0]))
def test_centroid(): assert np.allclose(m.centroid([[2, 0], [0, 5]]), [0.5, 0.5])
def test_example():
    f = m.check(ANNA + BOB)
    assert [(x["rule"], x["where"]) for x in f] == [("VOICE-01", "a3")]
def test_cross():
    cl = [C("a1", "anna", [1, 0]), C("a2", "anna", [1, 0]), C("b1", "bob", [1, 0]), C("b2", "bob", [1, 0])]
    f = m.check(cl); assert [(x["rule"], x["where"]) for x in f] == [("VOICE-02", "anna|bob")]
def test_few_clips():
    f = m.check([C("a1", "anna", [1, 0])]); assert [(x["rule"], x["where"]) for x in f] == [("VOICE-03", "anna")]
def test_ten_same(): assert m.check([C(f"a{i}", "anna", [1, 2, 3]) for i in range(10)]) == []
def test_len_mismatch():
    with pytest.raises(ValueError): m.check([C("a", "x", [1, 0]), C("b", "x", [1, 0, 0])])
def test_scale():
    cl = copy.deepcopy(ANNA + BOB); cl[2]["embedding"] = [0, 5, 0]
    assert m.check(cl) == m.check(ANNA + BOB)
def test_immutable_sorted():
    cl = copy.deepcopy(ANNA + BOB); c0 = copy.deepcopy(cl); f = m.check(cl)
    assert cl == c0 and [x["where"] for x in f] == sorted(x["where"] for x in f)
    for x in f: assert set(x) == {"rule", "severity", "where", "detail"}
