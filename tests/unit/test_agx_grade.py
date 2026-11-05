"""ICW-05b round 2 (the creator, 2026-11-05: the colour palette comes first): the AgX match table covers every palette token and
scene colour, is not stale, brings the palette closer to its hex than the raw values do, and the style engine uses it only when
asked (and refuses a stale table)."""
import pytest

from explainer_engine.blender import grade as G
from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS


def test_table_is_current_and_covers_the_palette_and_the_scene_colours():
    doc = G.load()
    assert doc["schema"] == G.SCHEMA and doc["look"] == "AgX - Medium High Contrast" and not G.stale(doc)
    pal = S.palette()
    for name, h in {**{k: v for k, v in pal.items() if k != "chroma_key"}, **SS.SCENE_COLOURS}.items():
        rec = doc["colours"][h.upper()]
        assert name in rec["names"] and len(rec["linear"]) == 3 and all(v > 0 for v in rec["linear"])
        assert rec["delta_e"] <= rec["raw_delta_e"] + 1e-9, name  # never worse than the raw hex


def test_matching_brings_the_palette_much_closer_to_its_hex():
    s = G.summary()
    assert s["palette_tokens"] == len(S.palette()) - 1
    assert s["mean_delta_e_matched"] < s["mean_delta_e_raw"] / 3


def test_delta_e_is_zero_for_the_same_colour_and_grows_with_distance():
    assert G.delta_e([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) == 0
    assert G.delta_e([1, 0, 0], [0, 0, 1]) > G.delta_e([1, 0, 0], [0.9, 0, 0]) > 0


def test_engine_uses_the_match_only_when_asked():
    pal = S.palette()
    raw = S.StyleEngine(S.StyleTokens()).material("m", "support_blue")
    got = S.StyleEngine(S.StyleTokens(palette_match=True)).material("m", "support_blue")
    base = lambda g: next(n for n in g["nodes"] if n["id"] == "base")["inputs"]["6"]  # noqa: E731
    assert base(raw) == S.rgba(pal["support_blue"])
    assert base(got) == [*G.matched(pal["support_blue"]), 1.0]


def test_matched_world_keeps_the_ambient_plain_and_the_paper_is_a_gain():
    e = S.StyleEngine(S.StyleTokens(palette_match=True))
    w = {n["id"]: n for n in e.world()["nodes"]}
    assert w["light"]["inputs"]["Color"] == S.rgba(S.palette()["paper"])
    assert w["backdrop"]["inputs"]["Color"] == [*G.matched(S.palette()["paper"]), 1.0]
    p = {n["id"]: n for n in e.paper("paper.jpg")["nodes"]}
    assert p["overlay"]["props"]["blend_type"] == "MULTIPLY" and p["gain"]["props"]["operation"] == "MULTIPLY_ADD"
    assert p["gain"]["inputs"] == {"1": 0.24, "2": 0.88}  # 1 + 0.12 * (2g - 1)
    plain = {n["id"]: n for n in S.StyleEngine().paper("paper.jpg")["nodes"]}
    assert plain["overlay"]["props"]["blend_type"] == "OVERLAY" and "gain" not in plain


def test_a_stale_table_or_an_unknown_colour_is_refused(monkeypatch):
    doc = G.load()
    with pytest.raises(KeyError):
        G.matched("#123456", doc)
    monkeypatch.setattr(G, "_sha", lambda path: "0" * 64)
    with pytest.raises(ValueError, match="stale"):
        G.matched(S.palette()["ink"], doc)
