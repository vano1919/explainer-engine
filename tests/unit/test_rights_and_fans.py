"""Rights check (RR rules, D-26) and fan research brief / balance (P-123..P-125).
Fixtures use placeholders (World A/B, example.org), never invented real sources."""

from __future__ import annotations

import copy

from explainer_engine.research import fan_brief
from explainer_engine.rights import ip_check


def _manifest() -> dict:
    return {
        "schema": "explainer.rights_manifest", "version": 1, "episode_id": "crossover-test",
        "uses_third_party_fiction": True,
        "franchises": [{"name": "World A", "owner": "Owner A"}, {"name": "World B", "owner": "Owner B"}],
        "purpose": "analysis", "third_party_media": [],
        "quotes": [{"text": "A short line we analyse.", "source": "World A, book 1", "analyzed": True}],
        "narration_words": 1000, "recap_words": 150,
        "art": {"all_original": True, "imitates_production_design": False, "generator_prompts_name_franchise": False},
        "fan_theories": [{"summary": "Theory about the northern wall", "author": "u/example", "url": "https://example.org/t1",
                          "credited": True, "uses_their_text_or_art": False}],
        "thumbnail": {"own_art_only": True, "has_logo": False, "has_actor_likeness": False, "has_key_art": False},
        "description_has_unofficial_note": True, "uses_leaks": False,
    }


def _verdicts(findings, rule=None):
    return {f["verdict"] for f in findings if rule is None or f.get("rule") == rule}


def test_a_clean_analysis_episode_passes():
    assert not ip_check.blocking(ip_check.check(_manifest()))


def test_an_original_episode_needs_no_franchise_fields():
    m = {"schema": "explainer.rights_manifest", "version": 1, "episode_id": "rome-pay", "uses_third_party_fiction": False}
    assert ip_check.check(m) == []


def test_each_rule_blocks():
    cases = {
        "RR-02": lambda m: m["third_party_media"].append({"kind": "still", "description": "frame from the show"}),
        "RR-01": lambda m: m.update(purpose="none"),
        "RR-03": lambda m: m["art"].update(imitates_production_design=True),
        "RR-07": lambda m: m["fan_theories"][0].update(credited=False),
        "RR-09": lambda m: m["thumbnail"].update(has_logo=True),
        "RR-08": lambda m: m.update(description_has_unofficial_note=False),
        "RR-10": lambda m: m.update(uses_leaks=True),
    }
    for rule, mutate in cases.items():
        m = _manifest()
        mutate(m)
        findings = ip_check.check(m)
        assert "FAIL" in _verdicts(findings, rule), rule
        assert ip_check.blocking(findings)


def test_quotes_are_short_few_and_analysed():
    m = _manifest()
    m["quotes"] = [{"text": "One. Two. Three sentences here.", "source": "World B", "analyzed": True}]
    assert "FAIL" in _verdicts(ip_check.check(m), "RR-04")
    m["quotes"] = [{"text": "Short.", "source": "World B", "analyzed": False}]
    assert "FAIL" in _verdicts(ip_check.check(m), "RR-04")
    m["quotes"] = [{"text": "Short.", "source": "World B", "analyzed": True}] * 7
    assert "FAIL" in _verdicts(ip_check.check(m), "RR-04")


def test_recap_share_reviews_then_fails():
    m = _manifest()
    m["recap_words"] = 250
    assert _verdicts(ip_check.check(m), "RR-05") == {"REVIEW"}
    m["recap_words"] = 400
    assert _verdicts(ip_check.check(m), "RR-05") == {"FAIL"}


def test_fan_art_needs_permission():
    m = _manifest()
    m["fan_theories"][0]["uses_their_text_or_art"] = True
    assert "FAIL" in _verdicts(ip_check.check(m), "RR-07")
    m["fan_theories"][0]["permission"] = True
    assert "FAIL" not in _verdicts(ip_check.check(m), "RR-07")


def test_unknown_fields_are_contract_errors():
    m = _manifest()
    m["looks_fine"] = True
    assert _verdicts(ip_check.check(m)) == {"FAIL"}


def _brief() -> dict:
    kinds = ["reddit", "forum", "fan_wiki", "youtube_comments", "article", "book"]
    sources = [{"id": f"S-{i:02d}", "kind": k, "url": f"https://example.org/s{i}", "title": f"Example source {i}",
                "accessed": "2026-10-16"} for i, k in enumerate(kinds, start=1)]
    return {
        "schema": "explainer.fan_brief", "version": 1, "episode_id": "crossover-test",
        "worlds": ["World A", "World B"], "sources": sources,
        "theories": [{"id": f"T-{i:02d}", "summary": f"Placeholder theory number {i}", "source_ids": [f"S-0{i}"],
                      "popularity": "medium", "canon_status": "plausible"} for i in range(1, 6)],
        "fan_demands": [{"summary": f"Fans ask for placeholder thing {i}", "source_ids": ["S-01"]} for i in range(3)],
        "existing_crossovers": [{"title": f"Existing take {i}", "url": f"https://example.org/x{i}",
                                 "angle": "army against army battle"} for i in range(3)],
        "canon_rules": [{"world": w, "rule": f"Placeholder canon rule {j} for {w}", "source_ids": ["S-03"]}
                        for w in ("World A", "World B") for j in range(2)],
        "our_angle": {"premise": "The banking system of World A tries to finance the long winter of World B",
                      "why_new": "Existing takes compare armies; ours follows the money and supply lines of both worlds.",
                      "differs_from": ["Existing take 0"]},
        "casual_onramps": ["who rules World A", "what the winter means", "what the bank is"],
        "deep_cuts": ["placeholder deep cut 1", "placeholder deep cut 2", "placeholder deep cut 3"],
    }


def test_a_deep_brief_passes():
    assert [f for f in fan_brief.check(_brief()) if f["verdict"] == "FAIL"] == []


def test_a_shallow_brief_fails():
    b = _brief()
    b["sources"] = b["sources"][:2]
    b["theories"] = b["theories"][:2]
    checks = {f["check"] for f in fan_brief.check(b) if f["verdict"] == "FAIL"}
    assert {"source_depth", "theories_depth", "dangling_source"} <= checks


def test_canon_rules_needed_for_each_world():
    b = _brief()
    b["canon_rules"] = [r for r in b["canon_rules"] if r["world"] == "World A"]
    assert any(f["check"] == "canon_rules" and "World B" in f["detail"] for f in fan_brief.check(b))


def test_a_premise_copied_from_an_existing_take_is_flagged():
    b = _brief()
    b["our_angle"]["premise"] = "army against army battle existing take"
    assert any(f["check"] == "premise_originality" for f in fan_brief.check(b))


def test_balance_needs_both_audiences():
    ok = [{"id": "B1", "audience": "casual"}, {"id": "B2", "audience": "fan"}, {"id": "B3", "audience": "both"}]
    assert fan_brief.check_balance(ok) == []
    only_fans = [{"id": f"B{i}", "audience": "fan"} for i in range(5)]
    assert {f["check"] for f in fan_brief.check_balance(only_fans)} == {"balance_casual"}
    assert fan_brief.check_balance([{"id": "B1"}])[0]["check"] == "balance_tags"


def test_template_phrases_are_flagged_not_removed():
    text = "In a world where kings fall... who would win? Let's dive in."
    assert set(fan_brief.template_flags(text)) == {"in a world where", "who would win", "let's dive in"}
    assert fan_brief.template_flags("The wall was built to keep the cold out.") == []


def test_overlap_ignores_stopwords():
    assert fan_brief.overlap("What if the bank met the winter", "the bank and the winter") == 1.0
    assert fan_brief.overlap("dragons", "") == 0.0


def test_rr10_bans_leaked_material_but_allows_labelled_leaked_information():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "docs" / "RIGHTS_AND_FAIR_USE.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| RR-10"))
    assert "material" in row and "information" in row and "reported leak" in row
