# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/rights/ip_check.py`
# Target Module : explainer_engine/rights/ip_check.py
# Target Classes/Symbols : def _schema(), def _sentences(), def check(), def blocking()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Rights check for one episode (docs/RIGHTS_AND_FAIR_USE.md, decision D-26).

Input: a rights manifest (``schemas/rights_manifest.schema.json``). Output: findings ``{check, rule, verdict, detail}``
with verdict FAIL (blocks the package), REVIEW (a person answers it) or INFO. The checks cover what a machine can see;
they lower the legal risk and never prove a use is fair (RR intro, V-07).

Run: ``python -m explainer_engine.rights.ip_check <manifest.json>`` (exit 1 on any FAIL).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

from explainer_engine.standards import sourced_rules as SR

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "rights_manifest.schema.json"
# P-122 / P-120: the creator's limits under D-26, kept in the sourced rules registry (BP-77, docs/SOURCED_RULES.md)
MAX_QUOTES = SR.T("BP-77", "quotes_max")
MAX_QUOTE_WORDS = SR.T("BP-77", "quote_words_max")
MAX_QUOTE_SENTENCES = SR.T("BP-77", "quote_sentences_max")
RECAP_REVIEW = SR.T("BP-77", "recap_share_review")
RECAP_FAIL = SR.T("BP-77", "recap_share_fail")
LIMIT_VERDICT = SR.rule("BP-77").get("severity", "REVIEW")  # the verdict of a breached quote or recap limit
UNOFFICIAL_NOTE = "Unofficial fan analysis. Not affiliated with or endorsed by the rights holders."


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sentences(text: str) -> int:
    return max(1, len([p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]))


def check(manifest: dict) -> list[dict]:
    findings: list[dict] = []

    def add(check_id: str, rule: str, verdict: str, detail: str) -> None:
        findings.append({"check": check_id, "rule": rule, "verdict": verdict, "detail": detail})

    errors = sorted(jsonschema.Draft202012Validator(_schema()).iter_errors(manifest), key=lambda e: list(e.path))
    for err in errors:
        add("schema", "contract", "FAIL", f"{'/'.join(map(str, err.path)) or '(root)'}: {err.message}")
    if errors:
        return findings
    if not manifest["uses_third_party_fiction"]:
        return findings  # the rules apply only to episodes about someone else's fiction

    required = ("franchises", "purpose", "third_party_media", "quotes", "narration_words", "recap_words", "art",
                "fan_theories", "thumbnail", "description_has_unofficial_note", "uses_leaks",
                "commentary_target", "official_images_as_generator_input", "merch_or_product_use")
    missing = [k for k in required if k not in manifest]
    for key in missing:
        add("missing_field", "contract", "FAIL", f"franchise episode needs '{key}'")
    if missing:
        return findings

    if not manifest["franchises"]:
        add("franchises", "RR-08", "FAIL", "name the franchises discussed and their rights holders")
    for f in manifest["franchises"]:
        if not f["owner"].strip():
            add("franchise_owner", "RR-08", "REVIEW", f"rights holder of '{f['name']}' not recorded")
    if manifest["purpose"] == "none":
        add("purpose", "RR-01", "FAIL", "a franchise episode must be analysis, commentary, criticism or parody")
    for item in manifest["third_party_media"]:
        add("third_party_media", "RR-02", "FAIL", f"{item['kind']}: {item['description']}")

    quotes = manifest["quotes"]
    if len(quotes) > MAX_QUOTES:
        add("quote_count", "RR-04", LIMIT_VERDICT, f"{len(quotes)} quotes > {MAX_QUOTES} (BP-77)")
    for q in quotes:
        words = len(q["text"].split())
        if words > MAX_QUOTE_WORDS or _sentences(q["text"]) > MAX_QUOTE_SENTENCES:
            add("quote_length", "RR-04", LIMIT_VERDICT, f"quote from {q['source']} has {words} words / "
                f"{_sentences(q['text'])} sentences (max {MAX_QUOTE_WORDS} / {MAX_QUOTE_SENTENCES}, BP-77)")
        if not q["analyzed"]:
            add("quote_not_analyzed", "RR-04", "FAIL", f"quote from {q['source']} is not analysed")

    total, recap = manifest["narration_words"], manifest["recap_words"]
    if total <= 0:
        add("narration_words", "RR-05", "FAIL", "narration word count missing")
    else:
        share = recap / total
        if share > RECAP_FAIL:
            add("recap_share", "RR-05", LIMIT_VERDICT, f"recap is {share:.0%} of the narration (> {RECAP_FAIL:.0%}, BP-77)")
        elif share > RECAP_REVIEW:
            add("recap_share", "RR-05", "REVIEW", f"recap is {share:.0%} of the narration (> {RECAP_REVIEW:.0%}, BP-77)")

    art = manifest["art"]
    if not art["all_original"]:
        add("art_original", "RR-03", "FAIL", "every picture must be our own drawing")
    if art["imitates_production_design"]:
        add("art_imitation", "RR-03", "FAIL", "pictures imitate a production's designs, costumes or actors")
    if art["generator_prompts_name_franchise"]:
        add("generator_prompts", "RR-03", "FAIL", "an image-generator prompt names a franchise, character or actor")

    for t in manifest["fan_theories"]:
        if not t["credited"] or not t["author"].strip() or not t["url"].strip():
            add("theory_credit", "RR-07", "FAIL", f"theory '{t['summary'][:60]}' needs its author and link")
        if t["uses_their_text_or_art"] and not t.get("permission", False):
            add("theory_permission", "RR-07", "FAIL", f"theory '{t['summary'][:60]}' uses their words or art "
                "without written permission")

    thumb = manifest["thumbnail"]
    if not thumb["own_art_only"] or thumb["has_logo"] or thumb["has_actor_likeness"] or thumb["has_key_art"]:
        add("thumbnail", "RR-09", "FAIL", "thumbnail must be our art only: no logo, actor likeness or key art")
    if not manifest["description_has_unofficial_note"]:
        add("unofficial_note", "RR-08", "FAIL", f"description must carry: \"{UNOFFICIAL_NOTE}\"")
    if manifest["uses_leaks"]:
        add("leaks", "RR-10", "FAIL", "leaked, unaired or pirated material (not just leaked information) used as a source")
    if len(manifest["commentary_target"].split()) < 8:
        add("commentary_target", "RR-14", "FAIL", "name what the episode says ABOUT the source work (one full sentence): "
            "a story that only places its characters in a new adventure is a commercial derivative (V-38)")
    if manifest["official_images_as_generator_input"]:
        add("generator_input", "RR-15", "FAIL", "an official screenshot or key art was used as an image input to a generator")
    if manifest["merch_or_product_use"]:
        add("merch", "RR-16", "FAIL", "an invented parody brand or the franchise name is used on merchandise, an app or a product")
    return findings


def blocking(findings: list[dict]) -> bool:
    return any(f["verdict"] == "FAIL" for f in findings)


if __name__ == "__main__":
    result = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for f in result:
        print(f["verdict"], f["rule"], f["check"], "-", f["detail"])
    print(f"{len(result)} finding(s)")
    raise SystemExit(1 if blocking(result) else 0)
