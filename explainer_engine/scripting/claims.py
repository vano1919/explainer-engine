"""Claims resolve to sources (invariant 5; PV-37, audit 2026-10-19 M1). stdlib only.

The episode's ``claim_map.md`` (next to the production script) is the one place a claim lives: a table row
``| C-01 | sentence | label | source |`` with the labels of the claim map (E established, M a model or one study, R our
reasoning, G a guess, I the episode's invention). The script's lines carry claim ids (``line.claims``). This check is the
deterministic half: every id resolves, every E/M claim names a link, numbers on screen or in the voice have a claim. Whether a
source really says what the sentence says is a reading job (the script critic's claim pass, docs/QA_SPECIFICATION.md).
"""

from __future__ import annotations

import re
from pathlib import Path

ROW = re.compile(r"^\|\s*(C-\d{2,3})\s*\|(.*)$")
URL = re.compile(r"https?://\S+")
NUMBER = re.compile(r"\b\d[\d,.]*\b")
SOURCED = ("E", "M")  # labels that claim the world says so: they need a link


def parse_map(text: str) -> dict[str, dict]:
    out = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).rstrip("|").split("|")]
        sentence, label, source = (cells + ["", "", ""])[:3]
        out[m.group(1)] = {"sentence": sentence, "label": label, "source": source}
    return out


def load_map(script_path: Path | str) -> dict[str, dict] | None:
    p = Path(script_path).parent / "claim_map.md"
    return parse_map(p.read_text(encoding="utf-8")) if p.exists() else None


def check(doc: dict, cmap: dict[str, dict] | None) -> list[dict]:
    """PV-37 findings: [{rule, severity, where, detail}]."""
    out = []

    def add(where, detail, sev="FAIL"):
        out.append({"rule": "PV-37", "severity": sev, "where": where, "detail": detail})

    lines = [(f"{seg['id']}#{k + 1}", ln) for seg in doc["segments"] for k, ln in enumerate(seg["lines"])]
    for sh in doc.get("shorts") or []:
        lines += [(f"{sh.get('id', 'short')}#{k + 1}", ln) for k, ln in enumerate(sh.get("lines", []))]
    used = {c for _, ln in lines for c in ln.get("claims", [])}
    if cmap is None:
        if used:
            add("claims", f"lines cite {len(used)} claim ids but there is no claim_map.md next to the script")
        else:
            add("claims", "no claim_map.md next to the script: facts are not tied to sources", "REVIEW")
        return out
    for where, ln in lines:
        for cid in ln.get("claims", []):
            if cid not in cmap:
                add(where, f"claim {cid} is not in claim_map.md")
        if not ln.get("claims") and NUMBER.search(ln["text"]):
            add(where, f"a number with no claim id: {ln['text'][:60]!r}", "REVIEW")
    for cid, row in cmap.items():
        if row["label"][:1] in SOURCED and not URL.search(row["source"]):
            add(cid, f"label {row['label']} but no link in the source column", "REVIEW")
    if cmap and not used:
        add("claims", f"claim_map.md has {len(cmap)} claims but no line cites one: put the ids on the lines", "REVIEW")
    return out
