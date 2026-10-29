"""The craft checklists (P3b, docs/CRAFT_CURRICULUM.md): one JSON per department, rendered into its skill page.

Each ``craft_checklists/<dept>.json`` has the shape of ``training/video_criteria.json`` (``about``, ``criteria[]`` with
``id``, ``group``, ``name``, ``check``, ``rules``) plus ``artefact`` (the field the check reads), ``source`` and
``enforced_by``. The JSON is the one home of a CRAFT- id; the CHECKLIST table in the department's SKILL.md and the index in
docs/CRAFT_CURRICULUM.md are rendered copies. This module checks and renders; it judges no video (the validators are
P4-P9, named in ``enforced_by`` with their phase in ``planned``).

    python -m explainer_engine.standards.craft check    # integrity (the unit test runs the same)
    python -m explainer_engine.standards.craft write    # rewrite the rendered tables in the skills and the curriculum

stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
DIR = Path(__file__).with_name("craft_checklists")
CURRICULUM = ROOT / "docs" / "CRAFT_CURRICULUM.md"
CHECKS = {"code", "critic", "eye", "manual"}
FIELDS = ("id", "group", "name", "check", "rules", "artefact", "source", "enforced_by")
PREFIX = {"screenwriting": "SCR", "sound": "SND", "cartography": "CART", "cinematography": "CIN",
          "editing_colour": "EDC", "animation": "ANI", "voice": "VOX", "packaging": "PKG", "motion_graphics": "MOG"}
SOURCE = re.compile(r"^(CRAFT_SOURCES_2026-10 §\d{1,2} \((SUPPORTED|PARTIAL)\): .+"
                    r"|Blueprint 2026-10 \(unverified\): .+|repo: .+)$")
PLANNED = re.compile(r"^P\d{1,2}[a-z]?$")
INDEX = ("<!-- craft-index:begin -->", "<!-- craft-index:end -->")


def markers(dept: str) -> tuple[str, str]:
    return f"<!-- craft-checklist:{dept}:begin -->", f"<!-- craft-checklist:{dept}:end -->"


def load(dept: str) -> dict:
    return json.loads((DIR / f"{dept}.json").read_text(encoding="utf-8"))


def departments() -> list[str]:
    return sorted(p.stem for p in DIR.glob("*.json"))


def _cell(text: str) -> str:
    return str(text).replace("|", "/")


def render(dept: str) -> str:
    """The CHECKLIST table of one department, as its SKILL.md carries it."""
    out = ["| ID | check | rule | artefact field | sourced rules | enforced by |", "|---|---|---|---|---|---|"]
    for c in load(dept)["criteria"]:
        enf = "manual" if c["enforced_by"] == "manual" else f"`{c['enforced_by']}`"
        if c.get("planned"):
            enf += f" (planned, {c['planned']})"
        rules = ", ".join(c["rules"]) or "-"
        out.append(f"| {c['id']} | {c['check']} | {_cell(c['name'])} | {_cell(c['artefact'])} | {rules} | {enf} |")
    return "\n".join(out) + "\n"


def render_index() -> str:
    """The department index of docs/CRAFT_CURRICULUM.md (rows start with the department, never with an id: D-23)."""
    out = ["| department | skill | checklist | ids | code / critic / eye / manual | sourced rules |", "|---|---|---|---|---|---|"]
    for dept in departments():
        data = load(dept)
        crit = data["criteria"]
        kinds = " / ".join(str(sum(c["check"] == k for c in crit)) for k in ("code", "critic", "eye", "manual"))
        bps = sorted({r for c in crit for r in c["rules"] if r.startswith("BP-")}, key=lambda r: int(r[3:]))
        ids = f"{crit[0]['id']}..{crit[-1]['id'].rsplit('-', 1)[1]} ({len(crit)})"
        skill = data["skill"].split("/")[2]
        out.append(f"| {dept} | `{skill}` | `standards/craft_checklists/{dept}.json` | {ids} | {kinds} | "
                   f"{', '.join(bps) or '-'} |")
    return "\n".join(out) + "\n"


def block(text: str, begin: str, end: str) -> str | None:
    if begin not in text or end not in text:
        return None
    return text.split(begin, 1)[1].split(end, 1)[0].strip("\n")


def _replace(text: str, begin: str, end: str, body: str) -> str:
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n{body}{end}{tail}"


def _defined_ids() -> dict:
    from explainer_engine import docs_lint
    return docs_lint.definitions()


def check() -> list[dict]:
    found: list[dict] = []

    def add(where: str, detail: str) -> None:
        found.append({"where": where, "detail": detail})

    bp_ids = {r["id"] for r in SR.rules()}
    defs = _defined_ids()
    from explainer_engine import docs_lint
    seen: set[str] = set()
    if set(departments()) != set(PREFIX):
        add("craft_checklists", f"departments {departments()} differ from {sorted(PREFIX)}")
    for dept in departments():
        data = load(dept)
        for key in ("about", "department", "skill", "criteria"):
            if key not in data:
                add(dept, f"missing {key}")
        if data.get("department") != dept:
            add(dept, "department field differs from the file name")
        skill = ROOT / data.get("skill", "")
        if not skill.is_file():
            add(dept, f"skill page {data.get('skill')} does not exist")
        else:
            begin, end = markers(dept)
            got = block(skill.read_text(encoding="utf-8"), begin, end)
            if got is None:
                add(dept, f"{data['skill']} lacks the rendered CHECKLIST markers")
            elif got.strip() != render(dept).strip():
                add(dept, f"{data['skill']} CHECKLIST differs from the JSON: python -m explainer_engine.standards.craft write")
        for c in data.get("criteria", []):
            cid = c.get("id", "?")
            if not re.fullmatch(rf"CRAFT-{PREFIX.get(dept, '?')}-\d{{2}}", cid):
                add(cid, f"id is not CRAFT-{PREFIX.get(dept)}-NN")
            if cid in seen:
                add(cid, "duplicate id")
            seen.add(cid)
            for key in FIELDS:
                if key not in c or (key != "rules" and not c[key]):
                    add(cid, f"missing {key}")
            if c.get("check") not in CHECKS:
                add(cid, f"check {c.get('check')!r} is not one of {sorted(CHECKS)}")
            if not SOURCE.match(str(c.get("source", ""))):
                add(cid, "source is not 'CRAFT_SOURCES_2026-10 §N (SUPPORTED|PARTIAL): ...', 'Blueprint 2026-10 (unverified): ...' "
                         "or 'repo: ...'")
            for r in c.get("rules", []):
                if r.startswith("BP-"):
                    if r not in bp_ids:
                        add(cid, f"{r} is not in sourced_rules.json")
                elif docs_lint.ID.fullmatch(r) and r not in defs:
                    add(cid, f"{r} is defined in no document")
            enf = c.get("enforced_by", "")
            planned = c.get("planned")
            if enf == "manual":
                if c.get("check") == "code":
                    add(cid, "a code check cannot be enforced manually")
            elif not (ROOT / enf.split(":")[0]).exists():
                if not planned:
                    add(cid, f"enforced_by {enf!r} does not exist and names no planned phase")
            if planned and not PLANNED.match(planned):
                add(cid, f"planned {planned!r} is not a plan phase (P4, P4b, ...)")
    text = CURRICULUM.read_text(encoding="utf-8") if CURRICULUM.exists() else ""
    got = block(text, *INDEX)
    if got is None:
        add("CRAFT_CURRICULUM.md", "lacks the craft-index markers")
    elif got.strip() != render_index().strip():
        add("CRAFT_CURRICULUM.md", "the index differs from the checklists: python -m explainer_engine.standards.craft write")
    return found


def write() -> None:
    for dept in departments():
        path = ROOT / load(dept)["skill"]
        path.write_text(_replace(path.read_text(encoding="utf-8"), *markers(dept), render(dept)), encoding="utf-8")
    CURRICULUM.write_text(_replace(CURRICULUM.read_text(encoding="utf-8"), *INDEX, render_index()), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    cmd = (argv or sys.argv[1:] or ["check"])[0]
    if cmd == "write":
        write()
        print("wrote the CHECKLIST tables and the curriculum index")
        return 0
    found = check()
    for f in found:
        print(f"{f['where']}: {f['detail']}")
    print(f"{len(departments())} checklists, {sum(len(load(d)['criteria']) for d in departments())} criteria, "
          f"{len(found)} findings")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
