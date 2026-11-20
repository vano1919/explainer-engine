"""Georgian script never reaches the viewer (creator 2026-10-17: Georgian is only for talking to him; everything the viewer
sees or hears is English).

Flags any character of the three Georgian blocks in the viewer-facing text files of an episode (narration, on-screen text,
picture prompts, titles, metadata, Shorts text). Zero is zero: there is no threshold. The block ranges were checked against
Python's ``unicodedata`` (Unicode 15.1: every assigned character in them is a GEORGIAN one, the characters just outside are
not; ``tests/unit/test_language_check.py`` repeats that check). A ``.json`` file is read as JSON, so an escaped ``\\u10d0`` counts
as the letter it is; if it does not parse, the raw text is scanned.

    python -m explainer_engine.qa.language_check <file> [...]      # exit 1 on a FAIL, 2 on NOT_RUN
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# (first, last, name): Georgian, Georgian Extended (Mtavruli), Georgian Supplement
GEORGIAN_BLOCKS = ((0x10A0, 0x10FF, "Georgian"), (0x1C90, 0x1CBF, "Georgian Extended"), (0x2D00, 0x2D2F, "Georgian Supplement"))
SHOW = 3


def is_georgian(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi, _ in GEORGIAN_BLOCKS)


def _hits_in_text(text: str, where: str) -> list[str]:
    out = []
    for lineno, line in enumerate(text.splitlines() or [text], 1):
        for col, ch in enumerate(line, 1):
            if is_georgian(ch):
                out.append(f"{where}:{lineno}:{col} U+{ord(ch):04X}")
    return out


def _walk(node, path: str, out: list[str]) -> None:
    if isinstance(node, str):
        out.extend(f"{path} U+{ord(ch):04X}" for ch in node if is_georgian(ch))
    elif isinstance(node, dict):
        for key, value in node.items():
            _walk(key, f"{path}.<key>", out)
            _walk(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk(value, f"{path}[{i}]", out)


def scan_file(path: str | Path) -> tuple[list[str], str | None]:
    """(hits, error): hits as 'where U+XXXX' strings; error is the reason the file could not be read, else None."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], f"{p}: {exc.__class__.__name__}: {exc}"
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except ValueError:
            return _hits_in_text(text, str(p)), None
        out: list[str] = []
        _walk(data, str(p), out)
        return out, None
    return _hits_in_text(text, str(p)), None


def check_files(paths: list[str | Path]) -> dict:
    """{status, value, detail}: FAIL with the count when any Georgian character is found (a hit beats an unreadable file),
    NOT_RUN when a file cannot be read or no file was given and nothing was found, else PASS (value 0)."""
    if not paths:
        return {"status": "NOT_RUN", "value": None, "detail": "no files given: nothing was checked"}
    hits: list[str] = []
    errors: list[str] = []
    for path in paths:
        h, err = scan_file(path)
        hits += h
        if err:
            errors.append(err)
    if hits:
        more = f" (+{len(hits) - SHOW} more)" if len(hits) > SHOW else ""
        return {"status": "FAIL", "value": len(hits), "detail": "Georgian script in viewer text: " + "; ".join(hits[:SHOW]) + more}
    if errors:
        return {"status": "NOT_RUN", "value": None, "detail": "not run, unreadable: " + "; ".join(errors[:SHOW])}
    return {"status": "PASS", "value": 0, "detail": f"no Georgian script in {len(paths)} file(s)"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    res = check_files(argv)
    print(f"{res['status']}: {res['detail']}")
    return {"PASS": 0, "FAIL": 1}.get(res["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
