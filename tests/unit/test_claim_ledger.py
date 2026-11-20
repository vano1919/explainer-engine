"""Tests for VAL-CLAIM-LEDGER from TASK_VAL_CLAIM_LEDGER.md section 7. """
import json
import re
from datetime import date
from pathlib import Path

import pytest

from explainer_engine.scripting import claim_ledger as M, claims

TODAY = date(2026, 11, 20)
LEGACY = """| ID | Sentence | Label | Source |
|---|---|---|---|
| C-01 | fire by lens | E | Hecht: https://example.org/optics |
| C-02 | glasses existed by 1300 | E | a book, no link |
| C-03 | the premise | I | our invention |
"""
FULL_HEAD = "| ID | Sentence | Label | Source | Type | Opened | Verdict | Confidence | Checked | Counter_source |\n|---|---|---|---|---|---|---|---|---|---|\n"


def row(cid, sentence, label="E", source="x https://e.org/a", typ="factual", opened="yes", verdict="supported",
        conf="high", checked="2026-11-01", counter=""):
    return f"| {cid} | {sentence} | {label} | {source} | {typ} | {opened} | {verdict} | {conf} | {checked} | {counter} |\n"


def mk(*rows):
    return M.parse_ledger(FULL_HEAD + "".join(rows))


def script(*lines, share=None):
    seg = {"id": "S01", "lines": list(lines)}
    if share:
        seg["drama"] = {"claim_share": share}
    return {"segments": [seg]}


def ln(text, *cids):
    d = {"text": text}
    if cids:
        d["claims"] = list(cids)
    return d


def rules(f, r):
    return [x for x in f if x["rule"] == r]


def chk(doc, cmap, **kw):
    kw.setdefault("today", TODAY)
    return M.ledger_check(doc, cmap, **kw)


def test_legacy_four_column_map_still_parses_and_pv37_findings_are_returned_unchanged():
    cmap = M.parse_ledger(LEGACY)
    assert set(cmap) == {"C-01", "C-02", "C-03"} and cmap["C-01"]["type"] is None and cmap["C-01"]["opened"] is None
    doc = script(ln("Fire by lens burns", "C-01"), ln("A number 100 with no id"))
    base = claims.check(doc, claims.parse_map(LEGACY))
    assert base and chk(doc, cmap)[:len(base)] == base


def test_new_columns_parse():
    c = mk(row("C-01", "fire by lens", counter="https://c.org/x", verdict="contradicted", conf="medium"))["C-01"]
    assert (c["type"], c["opened"], c["verdict"], c["confidence"], c["checked"]) == ("factual", True, "contradicted", "medium", "2026-11-01")
    assert c["counter_source"] == "https://c.org/x"


def test_bad_type_fails_cl02():
    f = rules(chk(script(ln("x", "C-01")), mk(row("C-01", "fire", typ="rumour"))), "CL-02")
    assert f and f[0]["severity"] == "FAIL"


def test_statistical_claim_without_a_number_fails_cl02():
    f = rules(chk(script(ln("x", "C-01")), mk(row("C-01", "many died", typ="statistical"))), "CL-02")
    assert f and f[0]["severity"] == "FAIL"
    assert not rules(chk(script(ln("x", "C-01")), mk(row("C-01", "40 died", typ="statistical"))), "CL-02")


def test_missing_type_is_review_then_fail_under_strict():
    c = mk(row("C-01", "fire", typ=""))
    assert [x["severity"] for x in rules(chk(script(ln("x", "C-01")), c), "CL-02")] == ["REVIEW"]
    assert [x["severity"] for x in rules(chk(script(ln("x", "C-01")), c, strict=True), "CL-02")] == ["FAIL"]


@pytest.mark.parametrize("word", ["never", "always", "nobody", "undefeated", "largest"])
def test_absolute_and_unverified_fails_cl03(word):
    c = mk(row("C-14", f"He was {word} beaten", opened="no", source="a book"))
    f = rules(chk(script(ln("x", "C-14")), c), "CL-03")
    assert f and f[0]["severity"] == "FAIL" and word in f[0]["detail"] and "C-14" in f[0]["detail"]


def test_absolute_but_opened_and_linked_passes():
    assert not rules(chk(script(ln("x", "C-14")), mk(row("C-14", "He was never beaten"))), "CL-03")


def test_ordinary_unverified_claim_is_reported_not_failed():
    c = mk(row("C-05", "The fort stood by the river", opened="no", source="a book", verdict="unverified"))
    f = chk(script(ln("The fort stood by the river", "C-05")), c)
    assert not [x for x in f if x["severity"] == "FAIL"]
    assert "C-05" in M.ledger_report(c)["not_opened"]


def test_absolute_with_no_opened_column_is_not_failed_unless_strict_when_linked():
    c = M.parse_ledger(LEGACY.replace("fire by lens", "fire never fails"))
    assert not rules(chk(script(ln("x", "C-01")), c), "CL-03")
    assert rules(chk(script(ln("x", "C-01")), c, strict=True), "CL-03")


def test_contradicted_without_counter_source_fails_cl05():
    f = rules(chk(script(ln("x")), mk(row("C-01", "fire", verdict="contradicted"))), "CL-05")
    assert f and f[0]["severity"] == "FAIL"


def test_unverified_is_not_contradicted():
    assert not rules(chk(script(ln("x")), mk(row("C-01", "fire", verdict="unverified"), row("C-02", "water", verdict="mixed"))), "CL-05")


def test_invalid_verdict_fails():
    assert rules(chk(script(ln("x")), mk(row("C-01", "fire", verdict="false"))), "CL-05")


def test_line_citing_a_contradicted_claim_fails():
    c = mk(row("C-01", "fire burns", verdict="contradicted", counter="https://c.org/x"))
    f = rules(chk(script(ln("Fire burns", "C-01")), c), "CL-05")
    assert [x for x in f if x["where"] == "S01#1" and x["severity"] == "FAIL"]


def test_missing_opened_is_review_then_fail_under_strict_cl04():
    c = mk(row("C-01", "fire", opened=""))
    assert [x["severity"] for x in rules(chk(script(ln("x", "C-01")), c), "CL-04")] == ["REVIEW"]
    assert [x["severity"] for x in rules(chk(script(ln("x", "C-01")), c, strict=True), "CL-04")] == ["FAIL"]


def test_date_missing_review_future_date_fails_cl06():
    assert [x["severity"] for x in rules(chk(script(ln("x")), mk(row("C-01", "fire", checked=""))), "CL-06")] == ["REVIEW"]
    f = rules(chk(script(ln("x")), mk(row("C-01", "fire", checked="2026-12-31"))), "CL-06")
    assert f and f[0]["severity"] == "FAIL"
    assert not rules(chk(script(ln("x")), mk(row("C-01", "fire", checked="2026-12-31")), today=date(2027, 1, 1)), "CL-06")


def test_number_in_line_not_in_cited_claim_fails_cl07a():
    c = mk(row("C-07", "The army had 1,020 men"))
    f = rules(chk(script(ln("The army had 1,200 men", "C-07")), c), "CL-07a")
    assert f and f[0]["severity"] == "FAIL" and f[0]["where"] == "S01#1"


def test_number_formats_are_normalised():
    c = mk(row("C-07", "The army had 1,200 men"))
    assert not rules(chk(script(ln("The army had 1200 men", "C-07")), c), "CL-07a")
    assert not rules(chk(script(ln("The army had 1200.0 men", "C-07")), c), "CL-07a")
    assert rules(chk(script(ln("The army had 1.2k men", "C-07")), c), "CL-07a")


def test_low_overlap_is_review_cl07b():
    c = mk(row("C-07", "The army crossed the frozen river at night"))
    f = rules(chk(script(ln("Bakers sold warm bread downtown", "C-07")), c), "CL-07b")
    assert f and f[0]["severity"] == "REVIEW"
    assert not rules(chk(script(ln("The army crossed the frozen river", "C-07")), c), "CL-07b")


def test_guess_cited_in_a_fact_segment_is_review_cl08():
    c = mk(row("C-09", "He probably wept", label="G"))
    f = rules(chk(script(ln("He probably wept", "C-09"), share="fact"), c), "CL-08")
    assert f and f[0]["severity"] == "REVIEW"
    assert not rules(chk(script(ln("He probably wept", "C-09"), share="invented"), c), "CL-08")


def test_cl01_never_duplicates_pv37_and_is_redundant_by_design():
    """PV-37 already flags every uncited line with a digit (claims.NUMBER), a superset of year/percent/currency, so CL-01
    is skipped on exactly those lines. Documented in the report as a brief observation."""
    doc = script(ln("It fell in the year of 1453 sadly"))
    f = chk(doc, mk(row("C-01", "x")))
    assert [x for x in f if x["rule"] == "PV-37" and x["where"] == "S01#1"] and not rules(f, "CL-01")


def test_report_lists_every_not_opened_claim_and_every_uncited_claim():
    c = mk(row("C-01", "fire"), row("C-02", "water", opened="no"), row("C-03", "air", opened=""))
    r = M.ledger_report(c, script(ln("fire", "C-01")))
    assert r["not_opened"] == ["C-02", "C-03"] and r["uncited"] == ["C-02", "C-03"]
    assert r["labels"] == {"E": 3}


def test_main_exit_codes_and_report_printed(tmp_path, capsys):
    d = tmp_path / "a"; d.mkdir()
    (d / "claim_map.md").write_text(FULL_HEAD + row("C-01", "fire burns"))
    (d / "s.json").write_text(json.dumps(script(ln("Fire burns", "C-01"))))
    assert M.main([str(d / "s.json"), "--today", "2026-11-20"]) == 0 and "Summary" in capsys.readouterr().out
    (d / "bad.json").write_text(json.dumps(script(ln("Fire burns", "C-99"))))
    assert M.main([str(d / "bad.json"), "--today", "2026-11-20"]) == 1
    assert M.main([str(tmp_path / "none.json")]) == 2


def test_findings_use_the_repo_shape():
    f = chk(script(ln("It fell in 1453")), mk(row("C-01", "x", typ="")))
    assert f and all(set(x) == {"rule", "severity", "where", "detail"} for x in f)


def test_no_network_and_no_llm_call():
    src = (Path(M.__file__)).read_text()
    assert not re.search(r"^\s*(import|from)\s+(requests|urllib|http|socket|anthropic|openai|httpx)", src, re.M)
