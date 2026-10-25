"""LT-74 caption review, the automatic half (D-80, OR-21): runs on the pod's captions.jsonl before Claude reads them.

* a description cut off by the token limit is trimmed to its last full sentence;
* a character name the VL model let through becomes a plain role ("the old scientist"), studio names go;
* style words (cartoon, animated, drawn ...) go: the trigger carries the look (LT-13);
* a change line gets its "Change from the previous shot:" prefix back when the model wrote its own label;
* what stays broken (too short or too long, no change line) is kept with ``drop: true`` and a reason, never deleted.
Every row keeps its ``raw`` text, so the eye review and the morning report can see each edit.

    python -m explainer_engine.training.pods.caption_review <captions.jsonl> <captions_reviewed.jsonl> <report.json>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PREFIX = "Change from the previous shot:"
ROLES = [(r"\b(Rick Sanchez|Rick)\b", "the old scientist"), (r"\b(Morty Smith|Morty)\b", "the boy"),
         (r"\bSummer\b", "the teenage girl"), (r"\bBeth\b", "the woman"), (r"\bJerry\b", "the man"),
         (r"\b(Mr\.? )?Meeseeks\b", "the blue creature"), (r"\b(Sanchez|Smith)\b", ""), (r"\b(Adult Swim|Cartoon Network)\b", "")]
STYLE = re.compile(r"\b(cartoon|animated|animation|anime|illustration|illustrated|hand-drawn|drawn|2D|cel[- ]shaded)\b ?",
                   re.I)
WORDS = (30, 130)  # a description outside this after trimming is dropped (the prompt asked 50-90)


def trim(text):
    """The text up to its last full sentence when the model stopped mid-sentence."""
    t = text.strip()
    if re.search(r"[.!?][\"')’]?$", t):
        return t
    cut = max(t.rfind(". "), t.rfind("! "), t.rfind("? "))
    return t[:cut + 1] if cut > 0 else t


def clean(row):
    """The reviewed row: text edited, ``raw`` kept, ``drop`` + ``review`` reasons."""
    t = row["text"]
    for pat, role in ROLES:
        t = re.sub(pat, role, t)
    t = STYLE.sub("", t)
    t = re.sub(r"\s{2,}", " ", trim(t)).strip()
    t = re.sub(r"\s+([,.])", r"\1", t)
    t = re.sub(r"(^|[.!?] )the ", lambda m: m.group(1) + "The ", t)
    why = []
    if row["kind"] == "change":
        if not t.startswith(PREFIX):
            head, _, rest = t.partition(":")
            t = f"{PREFIX} {rest.strip()}" if rest and len(head.split()) <= 6 else t
            why.append("prefix")
        if not t.startswith(PREFIX) or len(t.split()) < 7:
            why.append("no change line")
    else:
        n = len(t.split())
        if not WORDS[0] <= n <= WORDS[1]:
            why.append(f"words {n}")
    return {**row, "text": t, "raw": row["text"], "drop": any(w != "prefix" for w in why), "review": why}


def review(src, dst, report):
    rows = {}
    for line in Path(src).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r  # a resumed pod may write an id twice: the last one wins
    out = [clean(r) for r in rows.values()]
    Path(dst).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    words = [len(r["text"].split()) for r in out if r["kind"] == "describe" and not r["drop"]]
    rep = {"rows": len(out), "edited": sum(r["text"] != r["raw"] for r in out), "dropped": sum(r["drop"] for r in out),
           "kinds": dict(Counter(r["kind"] for r in out)), "reasons": dict(Counter(w for r in out for w in r["review"])),
           "describe_words": [min(words), sum(words) // len(words), max(words)] if words else None}
    Path(report).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    print(json.dumps(review(*sys.argv[1:4]), indent=1))
