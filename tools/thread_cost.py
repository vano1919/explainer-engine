"""CLI of the context-cost rule CC-1 (``explainer_engine/governance/thread_cost.py``, docs/ORCHESTRATION.md OR-38): how expensive is this thread?

usage: python tools/thread_cost.py [TRANSCRIPT.jsonl | --session ID]   (default: the newest transcript under ~/.claude/projects)

Prints context tokens, model steps since the last compaction, the limits of ``config/thread_cost.json`` and which of them are exceeded.
Exit 0 = under the limits, 1 = over (the thread must post its one-line request and write its handover file). Read-only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from explainer_engine.governance import thread_cost  # noqa: E402


def find_transcript(session: str | None = None, base: Path | None = None) -> Path | None:
    base = base or Path.home() / ".claude" / "projects"
    files = [p for p in base.glob("*/*.jsonl") if not session or p.stem == session]
    return max(files, key=lambda p: p.stat().st_mtime, default=None)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    session = argv[argv.index("--session") + 1] if "--session" in argv else None
    pos = [a for a in argv if not a.startswith("--") and a != session]
    path = Path(pos[0]) if pos else find_transcript(session)
    if not path or not path.is_file():
        print("no transcript found", file=sys.stderr)
        return 2
    rep = thread_cost.report(path, ROOT)
    print(json.dumps(rep, indent=1))
    return 1 if rep["over"] else 0


if __name__ == "__main__":
    sys.exit(main())
