"""Progress fragments: one file per change in ``docs/progress.d/`` instead of a new entry at the end of ``docs/PROGRESS.md``.

Every parallel branch appended at the same spot of PROGRESS.md, so each merged PR made the next one conflict. A fragment is a file of its own
(``<YYYY-MM-DD>-<branch-slug>.md``), so two branches never touch the same file. ``docs/PROGRESS.md`` keeps its old content, frozen.

Codes (each has a test): PRG-01 file name is not ``YYYY-MM-DD-<lowercase-slug>.md`` with a real date; PRG-02 the first line is not
``## YYYY-MM-DD — <title>``; PRG-03 no body under the heading; PRG-04 a merge conflict marker; PRG-05 the heading date differs from the file name's;
PRG-06 not UTF-8. ``README.md`` and non-``.md`` files are ignored.

    python -m explainer_engine.progress_fragments check [--dir D]      # exit 1 on a finding, 2 on an error
    python -m explainer_engine.progress_fragments assemble [--dir D]   # all fragments in filename order, to stdout
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "docs" / "progress.d"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9._-]*\.md$")
HEAD = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — \S")
MARKER = re.compile(r"^(<<<<<<<|=======|>>>>>>>)( |$)", re.M)


def fragments(directory: Path = DIR) -> list[Path]:
    return sorted(p for p in Path(directory).glob("*.md") if p.name != "README.md")


def _finding(rule: str, path: Path, detail: str) -> dict:
    return {"rule": rule, "severity": "FAIL", "where": path.name, "detail": detail}


def _valid_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def check(directory: Path = DIR) -> list[dict]:
    out: list[dict] = []
    for p in fragments(directory):
        m = NAME.match(p.name)
        if not m or not _valid_date(m.group(1)):
            out.append(_finding("PRG-01", p, "name must be YYYY-MM-DD-<lowercase-slug>.md with a real date"))
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out.append(_finding("PRG-06", p, "not UTF-8"))
            continue
        lines = text.splitlines()
        h = HEAD.match(lines[0]) if lines else None
        if not h:
            out.append(_finding("PRG-02", p, "first line must be '## YYYY-MM-DD — <title>'"))
        elif m and h.group(1) != m.group(1):
            out.append(_finding("PRG-05", p, f"heading date {h.group(1)} differs from the file name's {m.group(1)}"))
        if h and not any(line.strip() for line in lines[1:]):
            out.append(_finding("PRG-03", p, "heading without a body"))
        if MARKER.search(text):
            out.append(_finding("PRG-04", p, "merge conflict marker in the fragment"))
    return out


def assemble(directory: Path = DIR) -> str:
    return "\n".join(p.read_text(encoding="utf-8").rstrip() + "\n" for p in fragments(directory))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.progress_fragments")
    ap.add_argument("action", choices=("check", "assemble"))
    ap.add_argument("--dir", default=str(DIR))
    a = ap.parse_args(argv)
    d = Path(a.dir)
    if not d.is_dir():
        print(f"{d} is not a directory", file=sys.stderr)
        return 2
    if a.action == "assemble":
        sys.stdout.write(assemble(d))
        return 0
    found = check(d)
    for f in found:
        print(f"{f['rule']} {f['where']}: {f['detail']}")
    print(f"progress fragments: {'FAIL' if found else 'ok'} ({len(fragments(d))} file(s))")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
