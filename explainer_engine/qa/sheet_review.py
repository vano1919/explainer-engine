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
