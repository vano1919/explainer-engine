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
