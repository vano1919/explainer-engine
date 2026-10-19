"""The publish checklist (PC-01..PC-08, docs/QA_SPECIFICATION.md; audit 2026-10-19 M6): what the creator types into Studio,
checked for free before approval #2. Nothing here uploads (invariant 4). stdlib + jsonschema.

    python -m explainer_engine.qa.publish_check <publish.json> [--script production_script.json]   # exit 1 on a FAIL

Sources (opened 2026-10-19): chapters Help 9884579; GenAI disclosure Help 14328491; made for kids Help 9528076; Shorts over one
minute with a claim are blocked, Help 15424877; misleading metadata Help 2801973. The decisions stay the creator's: this only
says what is missing or contradicts a rule.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "publish.schema.json"
TITLE_MAX, DESCRIPTION_MAX = 100, 5000  # Studio's field limits (characters)
MIN_CHAPTER_S, MIN_CHAPTERS = 10, 3
SHORT_MAX_S, SHORT_CLAIM_RISK_S = 180, 60
SAFE_AUDIO = {"own_voice", "library", "procedural"}
TRIGGERS = ("photoreal_pictures", "real_person_realistic", "real_event_altered", "ai_music_main")


def seconds(t: str) -> int:
    parts = [int(x) for x in t.split(":")]
    return sum(v * 60 ** k for k, v in enumerate(reversed(parts)))


def check(pub: dict, doc: dict | None = None) -> list[dict]:
    out = []

    def add(rule, where, detail, sev="FAIL"):
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    try:
        jsonschema.validate(pub, json.loads(SCHEMA.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        add("PC-01", "schema", exc.message)
        return out
    # PC-01 chapters (Help 9884579): first at 00:00, at least three, ascending, each at least 10 s
    ch = [seconds(c["t"]) for c in pub["chapters"]]
    if ch:
        if ch[0] != 0:
            add("PC-01", "chapters", "the first chapter must start at 0:00")
        if len(ch) < MIN_CHAPTERS:
            add("PC-01", "chapters", f"{len(ch)} chapters; YouTube needs at least {MIN_CHAPTERS}")
        ends = ch[1:] + ([pub["duration_s"]] if pub.get("duration_s") else [])
        for c, a, b in zip(pub["chapters"], ch, ends):
            if b - a < MIN_CHAPTER_S:
                add("PC-01", c["t"], f"chapter {c['title']!r} lasts {b - a:.0f} s (minimum {MIN_CHAPTER_S}) or is out of order")
    else:
        add("PC-01", "chapters", "no chapters (REVIEW: a long-form video should have them)", "REVIEW")
    # PC-02 audience (D-17)
    if pub["audience"] != "not_made_for_kids":
        add("PC-02", "audience", "the channel is set 'not made for kids' (D-17); a kids setting contradicts it")
    # PC-03 GenAI disclosure (Help 14328491)
    d = pub["disclosure"]
    hits = [t for t in TRIGGERS if d.get(t)]
    if hits and d["decision"] != "disclose":
        add("PC-03", "disclosure", f"{hits} need the GenAI disclosure (Help 14328491)")
    unanswered = [t for t in TRIGGERS if t not in d]
    if unanswered:
        add("PC-03", "disclosure", f"answer {unanswered} (true/false) so the decision is traceable", "REVIEW")
    if doc is not None:
        speakers = {ln.get("speaker") for seg in doc["segments"] for ln in seg["lines"] if ln.get("speaker")}
        real = sorted(s for s in speakers if ((doc.get("cast", {}).get(s, {}).get("voice") or {}).get("traits") or {})
                      .get("real_person"))
        if real and "real_person_realistic" not in d:
            add("PC-03", "disclosure", f"real people speak invented lines ({real}): say whether the result is realistic", "REVIEW")
    # PC-04 / PC-05 Shorts (Help 15424877)
    for s in pub.get("shorts", []):
        if s["seconds"] > SHORT_MAX_S:
            add("PC-05", s["id"], f"{s['seconds']:.0f} s: a Short is at most {SHORT_MAX_S} s")
        risky = [a for a in s["audio"] if a not in SAFE_AUDIO]
        if s["seconds"] > SHORT_CLAIM_RISK_S and risky:
            add("PC-04", s["id"], f"over {SHORT_CLAIM_RISK_S} s with {risky} audio: any claim blocks a Short this long")
    # PC-06 field limits and honest packaging
    if len(pub["title"]) > TITLE_MAX:
        add("PC-06", "title", f"{len(pub['title'])} characters; Studio takes {TITLE_MAX}")
    if len(pub["description"]) > DESCRIPTION_MAX:
        add("PC-06", "description", f"{len(pub['description'])} characters; Studio takes {DESCRIPTION_MAX}")
    # PC-07 sources and the decisions the creator records
    if not re.search(r"https?://", pub["description"]):
        add("PC-07", "description", "no source link in the description (PUBLISHING_AND_ANALYTICS checklist)", "REVIEW")
    if pub.get("mid_roll", "undecided") == "undecided":
        add("PC-07", "mid_roll", "the mid-roll decision is not recorded", "REVIEW")
    if not pub.get("self_certification_answered"):
        add("PC-07", "self_certification", "answer the advertiser self-certification honestly in Studio", "REVIEW")
    # PC-08 approval #2 (invariant 4)
    if not pub.get("approval"):
        add("PC-08", "approval", "no recorded creator approval: nothing may be uploaded", "REVIEW")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("publish")
    ap.add_argument("--script")
    a = ap.parse_args(argv)
    pub = json.loads(Path(a.publish).read_text(encoding="utf-8"))
    doc = json.loads(Path(a.script).read_text(encoding="utf-8")) if a.script else None
    found = check(pub, doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    print(f"{sum(f['severity'] == 'FAIL' for f in found)} FAIL, {sum(f['severity'] == 'REVIEW' for f in found)} REVIEW")
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
