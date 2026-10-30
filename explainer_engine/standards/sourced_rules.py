"""The sourced production rules (BP-xx, docs/SOURCED_RULES.md; the creator's order of 2026-10-19).

No production rule is law by itself: every number a validator enforces comes from this registry (``sourced_rules.json``),
and every entry names its sources. A rule is ``binding`` only when at least two of the three source types back it
(``A`` an article, official page or study; ``B`` a book; ``C`` a YouTube video or vlog). A rule with one source type is a
``hypothesis``: it may be checked, but only as REVIEW, never as FAIL, and its number is the one the project already used.
A ``house`` rule is the creator's own call (dated), kept here so the validators and the documents agree on it.

    python -m explainer_engine.standards.sourced_rules check    # registry integrity (the unit test runs the same)
    python -m explainer_engine.standards.sourced_rules render   # the table for docs/SOURCED_RULES.md
    python -m explainer_engine.standards.sourced_rules write    # rewrite the generated block of docs/SOURCED_RULES.md

Code reads a threshold with ``T("BP-01", "wpm_target")``; the test ``tests/unit/test_sourced_rules.py`` fails when a
document and the registry disagree, when a rule lacks its sources, or when ``enforced_by`` names code that does not exist.
stdlib only.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).with_name("sourced_rules.json")
DOC = ROOT / "docs" / "SOURCED_RULES.md"
BEGIN, END = "<!-- sourced-rules:begin -->", "<!-- sourced-rules:end -->"
TYPES = {"A": "article", "B": "book", "C": "video"}
STATUSES = {"binding", "hypothesis", "house"}
ID = re.compile(r"^BP-\d{2,3}$")  # BP-100 onwards since 2026-10-24


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def rules() -> list[dict]:
    return load()["rules"]


def rule(rule_id: str) -> dict:
    for r in rules():
        if r["id"] == rule_id:
            return r
    raise KeyError(rule_id)


def T(rule_id: str, key: str):
    """One threshold of one rule, as the validators read it (never copy the number into code)."""
    return rule(rule_id)["thresholds"][key]


def severity(rule_id: str) -> str:
    """The severity the registry gives a rule's check (REVIEW when the rule names none)."""
    return rule(rule_id).get("severity", "REVIEW")


def level(rule_id: str, wanted: str = "FAIL") -> str:
    """The severity a check may emit for this rule (D-59): a hypothesis never FAILs, binding and house rules may."""
    return "REVIEW" if wanted == "FAIL" and rule(rule_id)["status"] == "hypothesis" else wanted


def threshold_reads(source: str):
    """(rule id, key, line) of every ``T("BP-xx", "key")`` / ``SR.T(...)`` / ``sourced_rules.T(...)`` with literal arguments in
    Python source: what the sync and severity tests (CN-11, CN-12) walk."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and len(node.args) >= 2:
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            a, b = node.args[0], node.args[1]
            if name == "T" and isinstance(a, ast.Constant) and isinstance(b, ast.Constant) and str(a.value).startswith("BP-"):
                yield a.value, b.value, node.lineno


def source_types(r: dict) -> set[str]:
    """Source types that count toward D-59: an entry marked ``verified: false`` only records an origin."""
    return {s["type"] for s in r.get("sources", []) if s.get("verified", True)}


def _symbol_exists(ref: str) -> bool:
    """``path/to/file.py`` or ``path/to/file.py:name``: the file exists and, if named, the symbol appears in it."""
    path, _, symbol = ref.partition(":")
    file = ROOT / path
    if not file.exists():
        return False
    return not symbol or re.search(rf"\b{re.escape(symbol)}\b", file.read_text(encoding="utf-8")) is not None


def check() -> list[dict]:
    """Registry integrity: ids, statuses, the two-of-three source bar, resolvable enforcement, unique thresholds."""
    found: list[dict] = []

    def add(where: str, detail: str) -> None:
        found.append({"where": where, "detail": detail})

    seen: set[str] = set()
    for r in rules():
        rid = r.get("id", "?")
        if not ID.match(rid):
            add(rid, "id is not BP-NN")
        if rid in seen:
            add(rid, "duplicate id")
        seen.add(rid)
        for key in ("area", "statement", "status", "thresholds", "sources", "enforced_by", "supersedes"):
            if key not in r:
                add(rid, f"missing field {key}")
        if r.get("status") not in STATUSES:
            add(rid, f"status {r.get('status')!r} is not one of {sorted(STATUSES)}")
        for s in r.get("sources", []):
            for key in ("type", "title", "url"):
                if not s.get(key):
                    add(rid, f"a source lacks {key}")
            if s.get("type") not in TYPES:
                add(rid, f"source type {s.get('type')!r} is not A, B or C")
            if not str(s.get("url", "")).startswith("http"):
                add(rid, f"source url {s.get('url')!r} is not a link")
        types = source_types(r)
        if r.get("status") == "binding" and len(types) < 2:
            add(rid, f"binding with {len(types)} source type(s): a binding rule needs two of A, B, C")
        if r.get("status") == "hypothesis" and len(types) >= 2 and r.get("severity") == "FAIL":
            add(rid, "two source types back it: make it binding or keep severity REVIEW")
        if r.get("status") == "house" and not r.get("decided"):
            add(rid, "a house rule names the creator's dated decision in `decided`")
        if r.get("severity", "REVIEW") not in {"FAIL", "REVIEW", "INFO"}:
            add(rid, f"severity {r.get('severity')!r}")
        if r.get("status") == "hypothesis" and r.get("severity") == "FAIL":
            add(rid, "a hypothesis never FAILs")
        for ref in r.get("enforced_by", []):
            if not _symbol_exists(ref):
                add(rid, f"enforced_by {ref!r} does not exist")
        if r.get("status") == "binding" and not r.get("enforced_by"):
            add(rid, "binding but enforced nowhere")
        for key, val in r.get("thresholds", {}).items():
            if not isinstance(val, (int, float, str, list, bool, dict)):
                add(rid, f"threshold {key} has an unsupported value")
    return found


def _fmt(val) -> str:
    if isinstance(val, dict):
        return "{" + ", ".join(f"{k}: {_fmt(v)}" for k, v in val.items()) + "}"
    if isinstance(val, list):
        return "[" + ", ".join(_fmt(v) for v in val) + "]"
    if isinstance(val, float):
        return f"{val:g}"
    return str(val)


def render() -> str:
    """The generated block of docs/SOURCED_RULES.md: one row per rule, thresholds and sources spelled out."""
    out = ["| ID | area | status | rule | thresholds | sources (type) | enforced by | supersedes |", "|---|---|---|---|---|---|---|---|"]
    for r in rules():
        th = "; ".join(f"{k} = {_fmt(v)}" for k, v in r["thresholds"].items()) or "-"
        src = "<br>".join(f"{s['type']}{'' if s.get('verified', True) else ' (not counted)'}: [{s['title']}]({s['url']})"
                          + (f" ({s['note']})" if s.get("note") else "")
                          for s in r["sources"]) or "-"
        enf = "<br>".join(f"`{e}`" for e in r["enforced_by"]) or "-"
        sup = "; ".join(r["supersedes"]) or "-"
        status = r["status"] + (f" ({r['decided']})" if r.get("decided") else "") + (f", {r['severity']}" if r.get("severity") else "")
        out.append(f"| {r['id']} | {r['area']} | {status} | {r['statement']} | {th} | {src} | {enf} | {sup} |")
    return "\n".join(out) + "\n"


def doc_block(text: str) -> str | None:
    if BEGIN not in text or END not in text:
        return None
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def write_doc() -> None:
    text = DOC.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    DOC.write_text(f"{head}{BEGIN}\n{render()}{END}{tail}", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    cmd = (argv or sys.argv[1:] or ["check"])[0]
    if cmd == "render":
        print(render(), end="")
        return 0
    if cmd == "write":
        write_doc()
        print(f"wrote {DOC}")
        return 0
    found = check()
    for f in found:
        print(f"{f['where']}: {f['detail']}")
    print(f"{len(rules())} rules, {len(found)} findings")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
