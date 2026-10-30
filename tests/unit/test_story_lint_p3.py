"""P3 story checks: ST-20 an and-then chain, ST-21 double exposition, ST-22 the ad-safety window, ST-23 the twist lands, the first
packaging promise paid (BP-135). All hypotheses, so REVIEW, never FAIL (D-59); the declared connector is a contract FAIL elsewhere."""
import copy

from explainer_engine.scripting import story_lint as SL
from explainer_engine.standards import sourced_rules as SR

from test_story_engine import storied


def found(doc, rule):
    return [f for f in SL.lint(doc) if f["rule"] == rule]


def two_segments(first, second, function="resolution"):
    d = copy.deepcopy(storied())
    d["segments"][0]["lines"] = [{"text": t} for t in first]
    d["segments"][1]["lines"] = [{"text": t} for t in second]
    d["segments"][1]["drama"]["function"] = function
    return d


def test_an_and_then_chain_in_one_segment_reviews_but_one_join_does_not():
    d = two_segments(["The khan rode out.", "And then the snow fell.", "After that the guns froze.", "Next, the horses died."], ["Done."])
    f = found(d, "ST-20")
    assert [x["severity"] for x in f] == ["REVIEW"] and f[0]["where"] == "S01"
    one = two_segments(["The khan rode out.", "And then the snow fell."], ["Done."])
    assert not found(one, "ST-20")
    assert SR.level("BP-145") == "REVIEW"


def test_two_segments_in_a_row_that_open_with_an_and_then_join_review():
    d = two_segments(["The khan rode out."], ["And then he stopped."])
    d["segments"].append(copy.deepcopy(d["segments"][1]))
    d["segments"][2]["id"] = "S03"
    d["segments"][2]["lines"] = [{"text": "After that he waited."}]
    d["segments"][2]["drama"] = dict(d["segments"][1]["drama"], function="button")
    assert any(f["where"] == "S02..S03" for f in found(d, "ST-20"))


def test_a_narrator_line_that_repeats_the_adjacent_hero_line_reviews():
    d = two_segments(["Napoleon looks at the frozen cannon.", "The frozen cannon will not fire, he says."],
                     ["Done."])
    d["segments"][0]["lines"][0] = {"speaker": "einstein", "text": "The frozen cannon will not fire today, Sire."}
    f = found(d, "ST-21")
    assert [x["where"] for x in f] == ["S01 line 2"]
    d["segments"][0]["lines"][1] = {"text": "A silence follows, and the old marshal looks at the ground."}
    assert not found(d, "ST-21")


def test_violence_inside_the_first_seven_seconds_reviews_and_later_does_not():
    assert SR.T("BP-143", "window_s") == 7
    early = two_segments(["The beheaded king lay in the snow."], ["Done."])
    assert [f["severity"] for f in found(early, "ST-22")] == ["REVIEW"]
    late = two_segments(["The march began at dawn, and the snow fell all morning long over the empty plain and the silent hills, while the "
                         "baggage wagons crawled behind the guns and nobody in the long grey column spoke a word to anyone at all.",
                         "The beheaded king lay in the snow."], ["Done."])
    assert not found(late, "ST-22")


def test_the_twist_line_over_the_estimate_reviews_and_a_short_one_does_not():
    long_line = "Nobody in the whole camp had ever imagined that the quiet old interpreter could possibly be the khan himself."
    d = two_segments(["The march began."], [long_line], function="twist")
    assert [f["severity"] for f in found(d, "ST-23")] == ["REVIEW"]
    d["segments"][1]["lines"] = [{"text": "He was the khan."}]
    assert not found(d, "ST-23")
    assert SR.T("BP-115", "twist_max_s") == 4.5


def test_the_first_packaging_promise_must_be_paid_in_the_first_seconds():
    d = two_segments(["A blizzard buries the French army outside Moscow."], ["Done."])
    d["drama"]["packaging_promises"] = ["Napoleon against a blizzard", "second", "third"]
    assert not [f for f in found(d, "ST-01") if f["where"] == "drama.packaging_promises"]
    d["drama"]["packaging_promises"] = ["Genghis rides at Waterloo", "second", "third"]
    assert [f["severity"] for f in found(d, "ST-01") if f["where"] == "drama.packaging_promises"] == ["REVIEW"]
