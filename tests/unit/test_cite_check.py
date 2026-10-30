"""J3/J6 citation check: only URLs returned by the same response's web search may be cited (invariant 5)."""

from explainer_engine.llm import cite_check as cc

SRC = ["https://a.example/x", "https://b.example/y/"]


def test_a_url_from_memory_is_unlisted_and_trailing_marks_do_not_matter():
    cited, bad = cc.check("- rule one (https://a.example/x).\n- rule two https://b.example/y\n- rule three https://c.example/z", SRC)
    assert bad == ["https://c.example/z"] and len(cited) == 3


def test_strip_drops_the_line_not_the_url():
    text, n = cc.strip("- ok https://a.example/x\n- bad https://c.example/z\nplain line\n", SRC)
    assert n == 1 and "c.example" not in text and "plain line" in text


def test_a_url_cut_at_its_own_parenthesis_is_still_listed():
    cited, bad = cc.check("see https://en.wikipedia.org/wiki/Labeling_(map_design) and **https://a.example/x**", SRC + ["https://en.wikipedia.org/wiki/Labeling_(map_design)"])
    assert bad == []
