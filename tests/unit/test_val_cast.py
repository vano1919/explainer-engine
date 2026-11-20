import copy
import pytest
from explainer_engine.audio import val_cast as m

def person(vid, text, facets=None, **kw):
    d = {"speaking": True, "voice_id": vid, "voice_text": text,
         "facets": facets or {"age": "young", "gender": "woman", "accent": "Scottish", "temperament": "calm"},
         "real_person": False, "voice_source": "designed"}
    d.update(kw); return d
T1 = "young woman, warm Scottish accent, calm"
T2 = "old man, gravelly Irish accent, gruff"
F2 = {"age": "old", "gender": "man", "accent": "Irish", "temperament": "gruff"}
def cast(): return {"anna": person("v1", T1), "bob": person("v2", T2, F2)}
def P(sid, ch, t): return {"shot_id": sid, "character": ch, "voice_text": t}
def r(c, p=()): return [x["rule"] for x in m.check(c, list(p))]

def test_clean(): assert r(cast(), [P("s1", "anna", T1), P("s1", "bob", T2)]) == []
def test_dup():
    c = cast(); c["bob"]["voice_id"] = "v1"
    f = m.check(c, []); assert [x["rule"] for x in f] == ["CAST-01"] and f[0]["where"] == "anna|bob"
def test_narrator_shared():
    c = cast(); c["narrator"] = person("v1", T1); assert r(c) == []
def test_nonspeaking():
    c = cast(); c["x"] = person(None, "", {}, speaking=False); assert r(c) == []
@pytest.mark.parametrize("v", [None, ""])
def test_no_voice(v):
    c = cast(); c["anna"]["voice_id"] = v; assert r(c) == ["CAST-02"]
def test_ws(): assert r(cast(), [P("s1", "anna", "young  woman,  warm Scottish accent, calm ")]) == []
def test_word(): assert r(cast(), [P("s1", "anna", "young woman, warm Scots accent, calm")]) == ["CAST-03"]
def test_case(): assert r(cast(), [P("s1", "anna", T1.upper())]) == ["CAST-03"]
@pytest.mark.parametrize("s,e", [("clone", ["CAST-04"]), ("soundalike", ["CAST-04"]), ("library", []), ("designed", [])])
def test_real(s, e):
    c = cast(); c["anna"]["real_person"] = True; c["anna"]["voice_source"] = s; assert r(c) == e
def test_facet_missing():
    c = cast(); del c["anna"]["facets"]["accent"]; assert r(c) == ["CAST-05"]
def test_facet_mismatch():
    c = cast(); c["anna"]["voice_text"] = "young woman, warm Irish accent, calm"; assert r(c) == ["CAST-05"]
def test_unknown_char(): assert r(cast(), [P("s1", "zed", "x")]) == ["CAST-06"]
def test_bad_shape():
    c = cast(); c["anna"] = "oops"
    with pytest.raises(ValueError): m.check(c, [])
    with pytest.raises(ValueError): m.check(cast(), [{"shot_id": "s", "character": "anna"}])
def test_immutable():
    c = cast(); p = [P("s1", "anna", "x")]; c0, p0 = copy.deepcopy(c), copy.deepcopy(p); m.check(c, p)
    assert c == c0 and p == p0
