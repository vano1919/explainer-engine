"""PC-01..PC-08: the publish checklist before approval #2 (audit 2026-10-19 M6). Free and deterministic."""
import copy

from explainer_engine.qa import publish_check as PC

GOOD = {
    "schema": "publish/1", "title": "What Happens When 100 Geniuses Are Trapped in the Stone Age?",
    "description": "Sources: https://example.org/claims", "duration_s": 1100,
    "chapters": [{"t": "0:00", "title": "Day 1"}, {"t": "4:13", "title": "Week 1"}, {"t": "8:18", "title": "Month 1"}],
    "audience": "not_made_for_kids",
    "disclosure": {"decision": "disclose", "reason": "invented scenes with real people", "photoreal_pictures": False,
                   "real_person_realistic": False, "real_event_altered": False, "ai_music_main": False},
    "mid_roll": "off", "self_certification_answered": True,
    "shorts": [{"id": "SH01", "seconds": 45, "audio": ["own_voice", "library"]}],
    "approval": {"by": "creator", "ref": "cmsg_x"},
}


def rules(pub, sev="FAIL"):
    return {f["rule"] for f in PC.check(pub) if f["severity"] == sev}


def test_a_complete_package_passes():
    assert PC.check(GOOD) == []


def test_chapters_follow_youtube_rules():
    p = copy.deepcopy(GOOD)
    p["chapters"] = [{"t": "0:05", "title": "a"}, {"t": "0:09", "title": "b"}]
    assert "PC-01" in rules(p)


def test_kids_audience_and_missing_disclosure_fail():
    p = copy.deepcopy(GOOD)
    p["audience"] = "made_for_kids"
    p["disclosure"].update(decision="not_needed", photoreal_pictures=True)
    assert {"PC-02", "PC-03"} <= rules(p)


def test_a_long_short_with_claimable_audio_fails():
    p = copy.deepcopy(GOOD)
    p["shorts"] = [{"id": "SH02", "seconds": 75, "audio": ["own_voice", "third_party"]},
                   {"id": "SH03", "seconds": 200, "audio": ["library"]}]
    assert {"PC-04", "PC-05"} <= rules(p)


def test_unrecorded_decisions_are_reviews_not_silence():
    p = copy.deepcopy(GOOD)
    p.pop("approval")
    p["mid_roll"] = "undecided"
    p["description"] = "no links"
    assert "PC-07" in rules(p, "REVIEW") and "PC-08" in rules(p, "FAIL")  # invariant 4: no approval is a FAIL, not a note


def test_a_bad_shape_is_a_schema_fail():
    p = copy.deepcopy(GOOD)
    p["chapters"][0]["t"] = "zero"
    assert rules(p) == {"PC-01"}
