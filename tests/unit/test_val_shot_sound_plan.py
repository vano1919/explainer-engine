import copy
import pytest
from explainer_engine.audio import val_shot_sound_plan as m

def S(i="s1", kind="photo", bed="room_tone_hall", silent=False, reason="empty hall, echo carries the dread", cues=()):
    return {"shot_id": i, "kind": kind, "bed": bed, "silent_by_design": silent, "reason": reason, "cues": list(cues)}
def r(shots): return [x["rule"] for x in m.check(shots) if x["where"] != "film"]

def test_clean(): assert r([S()]) == []
def test_s2(): assert r([S("s2", "map", None, False, "the map pans over the front line")]) == ["SP-01", "SP-04"]
def test_both(): assert r([S(silent=True)]) == ["SP-02"]
def test_silent_photo(): assert r([S(bed=None, silent=True)]) == []
def test_silent_map(): assert r([S(kind="map", bed=None, silent=True)]) == []
@pytest.mark.parametrize("reason", ["todo", "TBD", "short", "   "])
def test_reason(reason): assert r([S(reason=reason)]) == ["SP-03"]
def test_reason_12(): assert r([S(reason="abcdefghijkl")]) == []
def test_cues():
    assert r([S(cues=[{}] * 7)]) == ["SP-05"] and r([S(cues=[{}] * 6)]) == []
def test_share():
    sh = [S(f"s{i}", bed=None, silent=i < 3) for i in range(4)]
    for s in sh: s["bed"] = None
    f = m.check([S(f"s{i}", bed=None, silent=True) for i in range(3)] + [S("s3")])
    assert [x for x in f if x["rule"] == "SP-06"][0]["where"] == "film" and sum(x["rule"] == "SP-06" for x in f) == 1
    f2 = m.check([S(f"s{i}", bed=None, silent=True) for i in range(2)] + [S("s2"), S("s3")])
    assert not any(x["rule"] == "SP-06" for x in f2)
def test_bad():
    with pytest.raises(ValueError): m.check([S("a"), S("a")])
    with pytest.raises(ValueError): m.check([S(bed=5)])
    d = S(); del d["kind"]
    with pytest.raises(ValueError): m.check([d])
def test_empty(): assert m.check([]) == []
