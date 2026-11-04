# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/publish/__main__.py`
# Target Module : explainer_engine/publish/__main__.py
# Target Classes/Symbols : def main()
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

"""YouTube staging (D-57): the episode goes up unlisted or private with everything filled in; going public is the creator's.

    python -m explainer_engine.publish stage <episode> [--privacy unlisted|private] [--video F] [--shorts-dir D]
                                             [--only long,SH01] [--yes --confirm '<who said OK, where>'] [--adopt SH01=<id>]
    python -m explainer_engine.publish thumbnail <episode> [--generate --approved-by '<who said OK, where>']
    python -m explainer_engine.publish auth <client_secret.json>        # once, on the creator's PC
    python -m explainer_engine.publish auth-url | auth-finish '<address>'  # the same from the cloud, consent on a phone

Without --yes ``stage`` is a dry run: it writes <episode>/publish/youtube_stage.json and prints the plan, the quota and the
review checklist, with no network call. There is no public option.
"""

from __future__ import annotations

import argparse
import sys

from explainer_engine.publish.youtube import STAGE_PRIVACY


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.publish", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage", help="upload as unlisted/private (dry run without --yes)")
    s.add_argument("episode")
    s.add_argument("--privacy", choices=STAGE_PRIVACY, default="unlisted")
    s.add_argument("--video")
    s.add_argument("--shorts-dir")
    s.add_argument("--only", help="comma-separated item ids (long, SH01, ...)")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--confirm", default="")
    s.add_argument("--adopt", action="append", default=[], help="ID=videoId: record an already uploaded video")
    t = sub.add_parser("thumbnail", help="price, then (after the creator's OK) paint the long video's thumbnail")
    t.add_argument("episode")
    t.add_argument("--generate", action="store_true")
    t.add_argument("--approved-by", default="")
    t.add_argument("--tier", choices=("draft", "standard", "premium"), default="premium",
                   help="draft = a cheap try beside the final file; premium = the final thumbnail")
    a = sub.add_parser("auth", help="one-time sign-in on the creator's PC")
    a.add_argument("client_secret")
    sub.add_parser("auth-url", help="print the consent link (sign in on a phone)")
    f = sub.add_parser("auth-finish", help="exchange the address the phone ended on for a token")
    f.add_argument("answer")
    args = ap.parse_args(argv)
    if args.cmd == "stage":
        from explainer_engine.publish import stage
        adopt = dict(x.split("=", 1) for x in args.adopt)
        only = set(args.only.split(",")) if args.only else None
        return stage.run(args.episode, privacy=args.privacy, yes=args.yes, confirm=args.confirm, video=args.video,
                         shorts_dir=args.shorts_dir, only=only, adopt=adopt)
    if args.cmd == "thumbnail":
        from explainer_engine.publish import thumbnail
        return thumbnail.run(args.episode, generate=args.generate, approved_by=args.approved_by,
                             tier=args.tier)
    from explainer_engine.publish import auth
    if args.cmd == "auth-url":
        return auth.url_step()
    if args.cmd == "auth-finish":
        return auth.finish_step(args.answer)
    return auth.main(args.client_secret)


if __name__ == "__main__":
    sys.exit(main())
