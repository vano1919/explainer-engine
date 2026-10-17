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

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "rights_manifest.schema.json"
MAX_QUOTES = 6               # P-122
MAX_QUOTE_WORDS = 40
MAX_QUOTE_SENTENCES = 2
RECAP_REVIEW = 0.20          # P-120
RECAP_FAIL = 0.35
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
                "fan_theories", "thumbnail", "description_has_unofficial_note", "uses_leaks")
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
        add("quote_count", "RR-04", "FAIL", f"{len(quotes)} quotes > {MAX_QUOTES}")
    for q in quotes:
        words = len(q["text"].split())
        if words > MAX_QUOTE_WORDS or _sentences(q["text"]) > MAX_QUOTE_SENTENCES:
            add("quote_length", "RR-04", "FAIL", f"quote from {q['source']} has {words} words / "
                f"{_sentences(q['text'])} sentences (max {MAX_QUOTE_WORDS} / {MAX_QUOTE_SENTENCES})")
        if not q["analyzed"]:
            add("quote_not_analyzed", "RR-04", "FAIL", f"quote from {q['source']} is not analysed")

    total, recap = manifest["narration_words"], manifest["recap_words"]
    if total <= 0:
        add("narration_words", "RR-05", "FAIL", "narration word count missing")
    else:
        share = recap / total
        if share > RECAP_FAIL:
            add("recap_share", "RR-05", "FAIL", f"recap is {share:.0%} of the narration (> {RECAP_FAIL:.0%})")
        elif share > RECAP_REVIEW:
            add("recap_share", "RR-05", "REVIEW", f"recap is {share:.0%} of the narration (> {RECAP_REVIEW:.0%})")

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
    return findings


def blocking(findings: list[dict]) -> bool:
    return any(f["verdict"] == "FAIL" for f in findings)


if __name__ == "__main__":
    result = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for f in result:
        print(f["verdict"], f["rule"], f["check"], "-", f["detail"])
    print(f"{len(result)} finding(s)")
    raise SystemExit(1 if blocking(result) else 0)
