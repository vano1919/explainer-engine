"""PV-37: the script's claim ids resolve in claim_map.md, E/M claims carry a link (invariant 5, audit 2026-10-19 M1)."""
from test_production_script import mini

from explainer_engine.production import validate as V
from explainer_engine.scripting import claims

MAP = """| ID | Sentence | Label | Source |
|---|---|---|---|
| C-01 | fire by lens | E | Hecht, Optics: https://example.org/optics |
| C-02 | glasses existed by 1300 | E | a book, no link |
| C-03 | the premise | I | our invention |
"""


def found(doc, cmap):
    return {(f["severity"], f["where"]) for f in claims.check(doc, cmap)}


def test_the_map_is_read_from_its_table():
    m = claims.parse_map(MAP)
    assert set(m) == {"C-01", "C-02", "C-03"} and m["C-02"]["label"] == "E"


def test_an_unknown_claim_id_fails_and_blocks_validate():
    doc = mini()
    doc["segments"][1]["lines"][0]["claims"] = ["C-09"]
    assert ("FAIL", "S02#1") in found(doc, claims.parse_map(MAP))
    assert "PV-37" in {f["rule"] for f in V.check_script(doc, claim_map=claims.parse_map(MAP)) if f["severity"] == "FAIL"}


def test_cited_ids_without_any_map_fail():
    doc = mini()
    doc["segments"][1]["lines"][0]["claims"] = ["C-01"]
    assert ("FAIL", "claims") in found(doc, None)


def test_established_claims_need_a_link_and_numbers_need_a_claim():
    doc = mini()
    doc["segments"][1]["lines"][0]["claims"] = ["C-01"]
    doc["segments"][0]["lines"][1]["text"] = "Nobody knows, and 100 of them are cold."
    f = found(doc, claims.parse_map(MAP))
    assert ("REVIEW", "C-02") in f and ("REVIEW", "C-01") not in f and ("REVIEW", "C-03") not in f
    assert ("REVIEW", "S01#2") in f
