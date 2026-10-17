"""Story hypotheses (docs/EPISODE_STANDARDS.md section 8): several different premises, researched fairly, before the treatment.

    python -m explainer_engine.research.hypotheses jobs/<slug>/research/story_hypotheses.json

Evidence and narrative potential are scored separately, and entertainment never compensates for missing evidence: the
selected premise needs an evidence score of at least 3 and supporting claims. Findings are FAIL (fix before the treatment)
or REVIEW (a person answers it). Exit code 1 on any FAIL.
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "story_hypotheses.schema.json"
MIN_HYPOTHESES = 3
MIN_EVIDENCE = 3
SAME_PREMISE = 0.75


def check(doc: dict) -> list[dict]:
    out: list[dict] = []

    def add(rule: str, sev: str, where: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    for err in errors:
        add("HY-0", "FAIL", "/".join(map(str, err.path)) or "(root)", err.message)
    if errors:
        return out
    hyps = {h["id"]: h for h in doc["hypotheses"]}
    if len(hyps) < MIN_HYPOTHESES:
        add("HY-1", "FAIL", "hypotheses", f"{len(hyps)} hypotheses; compare at least {MIN_HYPOTHESES} genuinely different ones")
    items = list(hyps.values())
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if difflib.SequenceMatcher(a=a["premise"].lower(), b=b["premise"].lower()).ratio() >= SAME_PREMISE:
                add("HY-1", "REVIEW", f"{a['id']}/{b['id']}", "two premises are near copies: make them really different")
    for h in items:
        if not h["evidence_for"]:
            add("HY-2", "FAIL" if h["id"] == doc["selected"]["id"] else "REVIEW", h["id"], "no supporting evidence listed")
        if not h["evidence_against"] and not h.get("counterarguments"):
            add("HY-2", "REVIEW", h["id"], "nothing against it was looked for (evidence_against or counterarguments)")
    sel = hyps.get(doc["selected"]["id"])
    if sel is None:
        add("HY-3", "FAIL", "selected", f"{doc['selected']['id']} is not one of the hypotheses")
        return out
    if sel["scores"]["evidence"] < MIN_EVIDENCE:
        add("HY-3", "FAIL", sel["id"], f"evidence score {sel['scores']['evidence']} < {MIN_EVIDENCE}: a good story does not "
            "make up for weak evidence")
    for h in items:
        if h is not sel and h["scores"]["evidence"] > sel["scores"]["evidence"] \
                and h["scores"]["narrative"] > sel["scores"]["narrative"]:
            add("HY-3", "REVIEW", sel["id"], f"{h['id']} scores higher on both evidence and narrative: say why it lost")
    jobs = [b["job"] for b in doc["selected"]["beats"]]
    if jobs[0] not in ("hook", "question"):
        add("HY-4", "REVIEW", "beats", "the beat sheet does not open on a hook or a question")
    if "payoff" not in jobs:
        add("HY-4", "FAIL", "beats", "the beat sheet has no payoff")
    for k, b in enumerate(doc["selected"]["beats"]):
        if b["job"] == "evidence" and not b.get("claims"):
            add("HY-4", "REVIEW", f"beat {k + 1}", "an evidence beat without claim ids")
    return out


if __name__ == "__main__":
    found = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for f in found:
        print(f["severity"], f["rule"], f["where"], "-", f["detail"])
    print(f"{len(found)} finding(s)")
    raise SystemExit(1 if any(f["severity"] == "FAIL" for f in found) else 0)
