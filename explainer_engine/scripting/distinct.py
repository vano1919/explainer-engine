"""Episode distinctness (PV-38; audit 2026-10-19 Q4). stdlib only.

YouTube's inauthentic-content policy (Help 1311392, opened 2026-10-19) names "videos where characters are put in the same
situation over and over again with the same outcome". A recurring format is allowed; a repeated premise with the same
outcome is not. Each production script states ``episode.distinct`` (premise, question, outcome, mechanism: what is new), and
this check compares it with every approved episode in ``docs/episodes.json``. It only REVIEWs: the creator decides what is
new enough.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "docs" / "episodes.json"
FIELDS = ("premise", "question", "outcome", "mechanism")
SIMILAR = 0.6  # word-sequence similarity of premise + outcome above which two episodes read as the same situation


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def similarity(a: dict, b: dict) -> float:
    def key(e):
        return _words(e.get("premise", "") + " " + e.get("outcome", ""))
    return difflib.SequenceMatcher(a=key(a), b=key(b), autojunk=False).ratio()


def check(doc: dict, registry: Path = REGISTRY) -> list[dict]:
    out = []
    ep = doc["episode"]
    mine = ep.get("distinct")
    if not mine:
        return [{"rule": "PV-38", "severity": "REVIEW", "where": "episode.distinct",
                 "detail": "say the premise, question, outcome and what is new (mechanism), so the series cannot repeat itself"}]
    missing = [f for f in FIELDS if not str(mine.get(f, "")).strip()]
    if missing:
        out.append({"rule": "PV-38", "severity": "REVIEW", "where": "episode.distinct", "detail": f"empty: {missing}"})
    others = json.loads(registry.read_text(encoding="utf-8"))["episodes"] if registry.exists() else []
    for other in others:
        if other["id"] == ep["id"]:
            continue
        r = similarity(mine, other)
        if r >= SIMILAR:
            out.append({"rule": "PV-38", "severity": "REVIEW", "where": other["id"],
                        "detail": f"premise and outcome {r:.0%} like {other['id']}: the same situation with the same outcome "
                                  "is inauthentic content (Help 1311392); change the situation, the outcome or both"})
        elif _words(mine.get("mechanism", "")) and _words(mine.get("mechanism", "")) == _words(other.get("mechanism", "")):
            out.append({"rule": "PV-38", "severity": "REVIEW", "where": other["id"], "detail": "the same mechanism as " + other["id"]})
    return out
