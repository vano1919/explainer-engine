# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/qa/sheet_review.py`
# Target Module : explainer_engine/qa/sheet_review.py
# Target Classes/Symbols : def metas(), def request(), def apply(), def main()
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

"""Claude's free picture review (audit 2026-10-19 item 13): the visual judge's questions, answered by Claude in the session.

The paid judge (``GeminiClient.judge``) is no longer part of the default flow. Claude opens every painted picture (and the
contact sheet) itself, answers ``visual_judge.QUESTIONS`` per picture into ``visual_review.json``, and ``apply`` turns the
answers into the same PASS / FAIL / REVIEW verdicts. The creator's look at the sheet stays the last word. stdlib only.

    python -m explainer_engine.qa.sheet_review request <production_script.json> --pictures <dir>   # writes visual_review_request.md
    python -m explainer_engine.qa.sheet_review apply <production_script.json> <visual_review.json>   # exit 1 on a FAIL

Contract (``visual_review/1``): ``{"schema": "visual_review/1", "by": "claude", "pictures": {"<id>": {"adults": true, ...,
"why_<key>": "...", "note": "..."}}}``; every key of QUESTIONS answered, a ``why_`` for every true answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from explainer_engine.production import compile as C, script as S
from explainer_engine.qa import visual_judge as J
from explainer_engine.world import resolver

SCHEMA = "visual_review/1"


def metas(doc: dict) -> dict[str, dict]:
    """{picture id: the judge's meta}: stakes, the named hero, plate, what the story has not made yet."""
    world = C.world_of(doc)
    pics, _ = S.pictures(doc)
    out = {}
    for pid, pic in pics.items():
        if not pic.get("uses"):
            continue
        kind, beat = C.shot_type_of(doc, pid)
        heroes = pic.get("heroes", [])
        out[pid] = {"stakes": pic.get("stakes", ""), "hero": heroes[0] if heroes else None, "plate": bool(pic.get("plate")),
                    "not_yet": resolver.not_yet(world, beat) if beat is not None else [], "shot": kind}
    return out


def request(doc: dict, picture_dirs: list[Path]) -> str:
    world = C.world_of(doc)
    lines = [f"# Picture review: {doc['episode']['id']}", "",
             "Open every file below, answer every question with true/false and a why_ for each true, and write "
             f"`visual_review.json` ({SCHEMA}, see `explainer_engine/qa/sheet_review.py`). Nothing here is paid.", ""]
    for pid, meta in metas(doc).items():
        path = next((str(d / f"{pid}.png") for d in picture_dirs if (d / f"{pid}.png").exists()), "(not painted yet)")
        lines += [f"## {pid}", f"file: {path}", "", "```", J.build_prompt(world, meta), "```", ""]
    return "\n".join(lines)


def apply(doc: dict, review: dict) -> list[dict]:
    out = []
    if review.get("schema") != SCHEMA:
        return [{"rule": "QV", "severity": "FAIL", "where": "schema", "detail": f"expected {SCHEMA}"}]
    answers = review.get("pictures", {})
    for pid, meta in metas(doc).items():
        res = answers.get(pid)
        if res is None:
            out.append({"rule": "QV", "severity": "REVIEW", "where": pid, "detail": "not reviewed"})
            continue
        missing_why = [k for k in J.QUESTIONS if res.get(k) is True and not res.get(f"why_{k}")]
        v = J.verdict(res, meta)
        for f in v["fails"]:
            out.append({"rule": "QV", "severity": "FAIL", "where": pid, "detail": f})
        for r in v["review"] + [f"{k}: true without why_{k}" for k in missing_why]:
            out.append({"rule": "QV", "severity": "REVIEW", "where": pid, "detail": r})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rq = sub.add_parser("request")
    rq.add_argument("script")
    rq.add_argument("--pictures", action="append", default=[])
    rq.add_argument("--out")
    ap_ = sub.add_parser("apply")
    ap_.add_argument("script")
    ap_.add_argument("review")
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.script).read_text(encoding="utf-8"))
    if a.cmd == "request":
        from explainer_engine.core.store import write_text_atomic
        target = Path(a.out) if a.out else Path(a.script).parent / "visual_review_request.md"
        write_text_atomic(target, request(doc, [Path(p) for p in a.pictures]))
        print(target)
        return 0
    found = apply(doc, json.loads(Path(a.review).read_text(encoding="utf-8")))
    for f in found:
        print(f"{f['severity']:6} {f['where']}: {f['detail']}")
    print(f"{sum(f['severity'] == 'FAIL' for f in found)} FAIL, {sum(f['severity'] == 'REVIEW' for f in found)} REVIEW")
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
