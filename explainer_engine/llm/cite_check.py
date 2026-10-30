"""J3/J6 citation check (OR-24, invariant 5): a rule may cite only a URL that the same response's web_search_tool_result blocks returned.

    python -m explainer_engine.llm.cite_check ANSWER.md ANSWER.sources.json   # prints the unlisted URLs, exit 1 when there are any

``check`` returns (cited, unlisted); ``strip`` removes every bullet or table row that carries an unlisted URL (the rule is dropped,
never repaired from memory).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

URL = re.compile(r"https?://[^\s)\]>\"'|]+")


def _norm(u: str) -> str:
    return u.rstrip(".,;:*").rstrip("/")


def _listed(u: str, known: set[str]) -> bool:
    """Exact, or the URL was cut by the pattern at a ``)`` of its own (Wikipedia titles) or a trailing ``**``/``...``."""
    return u in known or any(k.startswith(u) and k[len(u):len(u) + 1] in ("(", ")", "%") or k.startswith(u + ")") for k in known)


def check(text: str, sources: list[str]) -> tuple[list[str], list[str]]:
    known = {_norm(s) for s in sources}
    cited = sorted({_norm(u) for u in URL.findall(text)})
    return cited, [u for u in cited if not _listed(u, known)]


def strip(text: str, sources: list[str]) -> tuple[str, int]:
    """Drop the lines that cite an unlisted URL; returns the kept text and the number of dropped lines."""
    known = {_norm(s) for s in sources}
    kept, dropped = [], 0
    for line in text.splitlines():
        if any(not _listed(_norm(u), known) for u in URL.findall(line)):
            dropped += 1
        else:
            kept.append(line)
    return "\n".join(kept) + "\n", dropped


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    text = Path(a[0]).read_text(encoding="utf-8")
    cited, bad = check(text, json.loads(Path(a[1]).read_text(encoding="utf-8")))
    print(json.dumps({"cited": len(cited), "unlisted": bad}, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
