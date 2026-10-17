"""Anti-boredom gate (docs/EPISODE_STANDARDS.md section 7, Q-E16): run before script approval and again before the final render.

    python -m explainer_engine.qa.engagement <production_script.json> [--rules episode_rules.json]

The code finds the beats that are measurably weak (no hook question, a flat run of the same beat job, a number with nothing
to see, repeated wording, an ending that never returns to the question, a long beat without a turn) and names them by segment.
Whether a beat is actually engaging is a person's call: the report ends with the gate's questions, to be answered beat by beat.
Every finding is REVIEW (a person decides); the fix is a better beat, never more cuts, sound effects or colour.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FLAT_RUN = 3            # the same beat job this many times in a row is a flat stretch
LONG_BEAT_WORDS = 260   # about 100 s at 155 wpm without a change of job
NGRAM = 5               # a 5-word phrase said in two different beats is repeated wording
QUESTIONS = (
    "Does the opening establish a compelling, accurate question or promise?",
    "Does each section change the viewer's knowledge, expectations, stakes or feeling?",
    "Is there evidence or a visual demonstration wherever a claim would benefit from being seen?",
    "Are the important reveals carried by the edit and the sound, not by random effects?",
    "Are there stretches of repetitive narration, needless explanation, generic visuals or purposeless music?",
    "Are the most memorable moments specific to this topic?",
    "Does the ending deliver a satisfying answer, consequence, comparison or insight?",
)
STOP = set("a an the and or but so of to in on at for with by from is are was were be it this that they he she we you "
           "i his her their its what how why when who which would could will did do does not no".split())


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", re.sub(r"\[[^\]]*\]", " ", text.lower()))


def _text(seg: dict) -> str:
    return " ".join(line["text"] for line in seg["lines"])


def check(doc: dict, rules: dict | None = None) -> list[dict]:
    out: list[dict] = []

    def add(rule: str, where: str, detail: str) -> None:
        out.append({"rule": rule, "severity": "REVIEW", "where": where, "detail": detail})

    segs = doc["segments"]
    first = segs[0]["lines"][0]["text"]
    if "?" not in " ".join(line["text"] for line in segs[0]["lines"][:2]):
        add("ENG-1", segs[0]["id"], f"no question in the opening two lines: {first[:60]!r}")
    jobs = [s.get("job") for s in segs]
    run = 1
    for k in range(1, len(segs)):
        run = run + 1 if jobs[k] and jobs[k] == jobs[k - 1] else 1
        if run == FLAT_RUN:
            add("ENG-2", segs[k]["id"], f"{FLAT_RUN} '{jobs[k]}' beats in a row: nothing turns here")
    for job in ("reveal", "payoff"):
        if any(jobs) and job not in jobs:
            add("ENG-2", "segments", f"no '{job}' beat in the whole script")
    with_visual = {g.get("segment") for g in doc.get("graphics", [])}
    for seg in segs:
        nums = [line["text"] for line in seg["lines"] if re.search(r"\d", line["text"])]
        if nums and seg["id"] not in with_visual:
            add("ENG-3", seg["id"], f"a number is said and nothing shows it: {nums[0][:60]!r} (ED-10)")
        n = len(_words(_text(seg)))
        if n > LONG_BEAT_WORDS:
            add("ENG-6", seg["id"], f"{n} words without a change of beat (> {LONG_BEAT_WORDS}): split it or turn it")
    seen: dict[tuple, str] = {}
    told: set[tuple[str, str]] = set()  # one finding per pair of beats
    for seg in segs:
        w = _words(_text(seg))
        for i in range(len(w) - NGRAM + 1):
            gram = tuple(w[i:i + NGRAM])
            if sum(x in STOP for x in gram) > 2:
                continue
            src = seen.setdefault(gram, seg["id"])
            if src != seg["id"] and (src, seg["id"]) not in told:
                told.add((src, seg["id"]))
                add("ENG-4", seg["id"], f"repeats {' '.join(gram)!r} from {src}")
    if rules:
        q = {x for x in _words(rules["identity"]["central_question"]) if x not in STOP and len(x) > 3}
        if q and not q & set(_words(_text(segs[-1]))):
            add("ENG-5", segs[-1]["id"], "the ending never comes back to the central question's words: "
                f"{rules['identity']['central_question']!r}")
    return out


def report(doc: dict, rules: dict | None = None) -> str:
    found = check(doc, rules)
    lines = [f"# Engagement gate: {doc['episode']['id']}", "", f"{len(found)} weak beat(s) found by the code:", ""]
    lines += [f"- {f['rule']} {f['where']}: {f['detail']}" for f in found] or ["- none"]
    lines += ["", "Answer for every beat that fails one (cite the segment and the revision):", ""]
    lines += [f"{k}. {q}" for k, q in enumerate(QUESTIONS, 1)]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("script")
    p.add_argument("--rules")
    a = p.parse_args(argv)
    doc = json.loads(Path(a.script).read_text(encoding="utf-8"))
    rules_path = Path(a.rules) if a.rules else Path(a.script).with_name("episode_rules.json")
    rules = json.loads(rules_path.read_text(encoding="utf-8")) if rules_path.exists() else None
    sys.stdout.write(report(doc, rules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
