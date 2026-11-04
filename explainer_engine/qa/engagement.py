# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/qa/engagement.py`
# Target Module : explainer_engine/qa/engagement.py
# Target Classes/Symbols : def _words(), def _text(), def sev(), def shown(), def forward(), def check(), def report(), def main()
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

"""Anti-boredom gate (docs/EPISODE_STANDARDS.md section 7, Q-E16): run before script approval and again before the final render.

    python -m explainer_engine.qa.engagement <production_script.json> [--rules episode_rules.json]

The code finds the beats that are measurably weak (no hook question, a flat run of the same beat job, a number with nothing
to see, repeated wording, an ending that never returns to the question, a long beat without a turn, a long stretch without a
forward-pointing line, a recap or goodbye at the end) and names them by segment. Whether a beat is actually engaging is a
person's call: the report ends with the gate's questions, to be answered beat by beat. Every finding is REVIEW (a person
decides) except ENG-8's sign-off lexicon and end-screen narration, which carry BP-43's severity (binding FAIL); the fix is a
better beat, never more cuts, sound effects or colour. The numbers come from the sourced rules registry
(docs/SOURCED_RULES.md): BP-01 (pace: words become seconds at its heard pace), BP-04 (the central answer waits for the last
tenth, ENG-5), BP-08 (a number is shown: a data visual, a chart beat or a text/label beat with the digit, ENG-3), BP-42 (the
forward-pointing cadence), BP-43 (the ending).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

WPM = SR.T("BP-01", "wpm_target")  # BP-01: the heard pace every estimate uses
FLAT_RUN = 3            # the same beat job this many times in a row is a flat stretch
LONG_BEAT_WORDS = round(WPM * 100 / 60)   # about 100 s at the BP-01 pace without a change of job
NGRAM = 5               # a 5-word phrase said in two different beats is repeated wording
# BP-42 / BP-44: a line points forward when it asks ("?") or carries a promise marker
PROMISE = re.compile(r"\b(will|by the end|watch|until|but|turns out|wait)\b", re.I)
MICROHOOK_EVERY_S, REVIEW_GAP_S = SR.T("BP-42", "microhook_every_s"), SR.T("BP-42", "review_gap_s")
LAST_SHARE = SR.T("BP-43", "last_share")  # BP-43: the ending is abrupt
END_SCREEN_MIN_S = SR.T("BP-43", "end_screen_narration_min_s")  # BP-43: narration runs on under the end screen
ANSWER_AFTER_SHARE = SR.T("BP-04", "answer_after_share")  # BP-04: the central answer waits for the last tenth
END_LEXICON = [p.lower() for p in SR.T("BP-43", "lexicon")]
NEXT_POINTER = re.compile(r"\b(next|watch|episode)\b", re.I)
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


def sev(rule_id: str) -> str:
    """A registered rule's severity, as the registry holds it."""
    return SR.rule(rule_id).get("severity", "REVIEW")


def shown(line: dict) -> bool:
    """BP-08: a number said on this line is also on screen through the line's own beats: a chart beat (values) or a text /
    label beat whose text has the digit."""
    for b in line.get("visual_beats") or []:
        if b.get("kind") == "chart" and b.get("values"):
            return True
        if b.get("kind") in ("text", "label") and re.search(r"\d", b.get("text", "")):
            return True
    return False


def forward(text: str) -> bool:
    """A forward-pointing line (BP-42): an open question or a promise marker."""
    return "?" in text or bool(PROMISE.search(text))


def check(doc: dict, rules: dict | None = None) -> list[dict]:
    out: list[dict] = []

    def add(rule: str, where: str, detail: str, severity: str = "REVIEW") -> None:
        out.append({"rule": rule, "severity": severity, "where": where, "detail": detail})

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
        nums = [line["text"] for line in seg["lines"] if re.search(r"\d", line["text"]) and not shown(line)]
        if nums and seg["id"] not in with_visual:  # ENG-3: every number that matters is also shown (BP-08, ED-10)
            add("ENG-3", seg["id"], f"a number is said and nothing shows it (no data visual, chart beat or text beat with "
                f"the number): {nums[0][:60]!r} (BP-08, ED-10)")
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
    # ENG-7 (BP-42): the estimated time between forward-pointing lines, at WPM, never over REVIEW_GAP_S
    since, last_id = 0, segs[0]["id"]
    for seg in segs:
        for line in seg["lines"]:
            n = len(_words(line["text"]))
            if forward(line["text"]):
                if since / WPM * 60 > REVIEW_GAP_S:
                    add("ENG-7", seg["id"], f"{since} words (~{since / WPM * 60:.0f} s at {WPM} wpm) since the last question or "
                        f"promise, from {last_id}: a forward-pointing line at least every {MICROHOOK_EVERY_S} s (BP-42)")
                since, last_id = 0, seg["id"]
            else:
                since += n
    if since / WPM * 60 > REVIEW_GAP_S:
        add("ENG-7", segs[-1]["id"], f"{since} words (~{since / WPM * 60:.0f} s at {WPM} wpm) to the end without a question or "
            f"promise, from {last_id}: a forward-pointing line at least every {MICROHOOK_EVERY_S} s (BP-42)")
    # ENG-8 (BP-43): the ending is abrupt: no recap or goodbye in the last LAST_SHARE of the words (FAIL, binding); the last
    # sentence is an open question or a pointer to the next video (REVIEW)
    lines = [(seg["id"], line["text"]) for seg in segs for line in seg["lines"]]
    total = sum(len(_words(t)) for _, t in lines)
    tail, count = [], 0
    for sid, t in reversed(lines):
        tail.append((sid, t))
        count += len(_words(t))
        if count >= total * LAST_SHARE:
            break
    tail_text = " ".join(t for _, t in tail).lower().replace("’", "'")
    for phrase in END_LEXICON:
        if phrase in tail_text:
            add("ENG-8", tail[0][0], f"{phrase!r} in the last {LAST_SHARE:.0%}: no recap, no goodbye, the ending is abrupt (BP-43)",
                sev("BP-43"))
    last_sentence = [s for s in re.split(r"(?<=[.!?])\s+", lines[-1][1].strip()) if s.strip()][-1] if lines[-1][1].strip() else ""
    if not (last_sentence.endswith("?") or NEXT_POINTER.search(last_sentence)):
        add("ENG-8", lines[-1][0], f"the last sentence is neither an open question nor a pointer to one next video: "
            f"{last_sentence[:60]!r} (BP-43)")
    # ENG-8 (BP-43): the end screen goes up with the line that points to the next video, and the narration runs on under
    # it for at least END_SCREEN_MIN_S (words at the BP-01 pace from that line to the end)
    at = next((k for k in range(len(lines) - 1, -1, -1) if NEXT_POINTER.search(lines[k][1])), None)
    if at is not None:
        under = sum(len(_words(t)) for _, t in lines[at:]) / WPM * 60
        if under < END_SCREEN_MIN_S:
            add("ENG-8", lines[at][0], f"about {under:.0f} s of narration from the pointer to the next video to the end; the "
                f"narration runs on at least {END_SCREEN_MIN_S} s under the end screen (BP-43): point earlier", sev("BP-43"))
    # ENG-5 (BP-04): the central answer is held back until the last tenth; the resolution segment starts that late
    total_words = sum(len(_words(_text(s))) for s in segs)
    before = 0
    for seg in segs:
        if (seg.get("drama") or {}).get("function") == "resolution":
            if total_words and before / total_words < ANSWER_AFTER_SHARE:
                add("ENG-5", seg["id"], f"the resolution (the central answer) starts at {before / total_words:.0%} of the words; "
                    f"hold it until the last {1 - ANSWER_AFTER_SHARE:.0%} (BP-04)", sev("BP-04"))
            break
        before += len(_words(_text(seg)))
    if rules:
        # ENG-5: the ending comes back to the central question (BP-04 holds its answer to the last tenth; BP-43 ends on it)
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
