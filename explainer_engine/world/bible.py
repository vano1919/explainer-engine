# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/world/bible.py`
# Target Module : explainer_engine/world/bible.py
# Target Classes/Symbols : def sha256(), def hashes(), def load(), def validate(), def cite(), def text(), def versions(), def drift(), def check(), def _next(), def bump(), def approve(), def main()
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

"""The World Bible (D-70 stage C; rules WB-01..WB-05 in docs/WORLD_BIBLE.md): ONE versioned record of the channel's
visual world. It does not restate the look, the era codex or the palette; it pins their files by hash under one version,
adds what no part holds (camera language, graphics style, era-change rules, motion default, the approved anchor
assets) and carries the creator's approval. Every picture, prompt and paint plan cites the version it was made under
(``world.resolver.resolve`` and ``imagegen.plan.make`` copy ``cite()``), so a change of look is visible in the records
and never silent: a part edited without a bump is a ``check`` finding until ``bump`` writes the new version.

    python -m explainer_engine.world.bible show
    python -m explainer_engine.world.bible check                       # exit 1 on drift or an invalid bible
    python -m explainer_engine.world.bible bump --reason "..." [--major]
    python -m explainer_engine.world.bible approve --by "ვანო" [--note "..."]   # the creator's recorded yes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import jsonschema

from explainer_engine.core.store import write_json_atomic

HERE = Path(__file__).resolve().parent
PATH = HERE / "bible.json"
SCHEMA_PATH = HERE.parent / "schemas" / "world_bible.schema.json"
PARTS = {"look": HERE / "look_v2.json", "eras": HERE / "eras.json", "palette": HERE.parent / "design" / "palette.json"}
STATUSES = ("draft", "approved", "superseded")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes(parts: dict | None = None) -> dict:
    return {name: sha256(p) for name, p in (parts or PARTS).items()}


def load(path: Path | None = None) -> dict:
    return json.loads(Path(path or PATH).read_text(encoding="utf-8"))


def validate(bible: dict) -> None:
    jsonschema.validate(bible, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def cite(bible: dict | None = None) -> dict:
    """What a world.json, prompt record or paint plan carries: the version and whether the creator approved it."""
    b = bible or load()
    return {"version": b["version"], "status": b["status"]}


def text(bible: dict | None = None) -> str:
    c = cite(bible)
    return f"world bible v{c['version']} ({c['status']})"


def versions(bible: dict | None = None) -> list[str]:
    """Every version that ever existed (the changelog), newest last; asset records may cite any of them."""
    b = bible or load()
    return [e["version"] for e in b["changelog"]]


def drift(bible: dict, parts: dict | None = None) -> list[str]:
    """Parts whose file no longer matches the hash pinned under this version (WB-02)."""
    now = hashes(parts)
    return [f"{name} ({bible['parts'][name]['file']}) changed since bible v{bible['version']}: bump the version with the reason"
            for name in bible["parts"] if name in now and now[name] != bible["parts"][name]["sha256"]]


def check(bible: dict | None = None, *, parts: dict | None = None, library: dict | None = None) -> list[str]:
    """Problems with the bible: an invalid file, a part edited without a bump, an approval without a name, an anchor
    that is not a library asset. Empty means the bible and its parts agree."""
    b = bible or load()
    try:
        validate(b)
    except jsonschema.ValidationError as exc:
        return [f"bible: {exc.message}"]
    problems = drift(b, parts)
    if b["status"] == "approved" and not (b.get("approved_by") and b.get("approved_at")):
        problems.append("status approved without approved_by and approved_at (WB-03)")
    if b["changelog"][-1]["version"] != b["version"]:
        problems.append("the changelog's last entry is not the current version")
    if b["anchors"]:
        from explainer_engine.assets import library as L
        lib = library if library is not None else L.load()
        known = {i["id"] for i in lib["items"]}
        problems += [f"anchor {a} is not in the asset library" for a in b["anchors"] if a not in known]
    return problems


def _next(version: str, major: bool) -> str:
    big, small = (int(x) for x in version.split("."))
    return f"{big + 1}.0" if major else f"{big}.{small + 1}"


def bump(reason: str, *, major: bool = False, bible: dict | None = None, parts: dict | None = None, path: Path | None = None,
         date: str | None = None) -> dict:
    """A new draft version: the parts' hashes are pinned again, the old version is written to the changelog as it was.
    ``major`` is for a change of drawing grammar (the thread itself); a minor bump covers palette, era and rule edits."""
    if not reason.strip():
        raise ValueError("a bump needs the reason (WB-02)")
    b = json.loads(json.dumps(bible or load(path)))
    files = parts or PARTS
    b["version"] = _next(b["version"], major)
    b["status"] = "draft"
    b["approved_by"] = None
    b["approved_at"] = None
    b["date"] = date or time.strftime("%Y-%m-%d")
    b["reason"] = reason
    b["parts"] = {name: {"file": b["parts"][name]["file"] if name in b["parts"] else files[name].name, "sha256": sha256(files[name])}
                  for name in files}
    b["changelog"].append({"version": b["version"], "date": b["date"], "reason": reason, "approved_by": None})
    validate(b)
    if path or bible is None:
        write_json_atomic(path or PATH, b)
    return b


def approve(by: str, *, note: str = "", bible: dict | None = None, parts: dict | None = None, path: Path | None = None,
            at: str | None = None) -> dict:
    """The creator's yes on the current version. Refused while a part has drifted (approve what is on disk, WB-03)."""
    if not by.strip():
        raise ValueError("approve needs the name of the person (WB-03)")
    b = json.loads(json.dumps(bible or load(path)))
    bad = drift(b, parts)
    if bad:
        raise ValueError("cannot approve a version whose parts changed: " + "; ".join(bad))
    b["status"] = "approved"
    b["approved_by"] = by
    b["approved_at"] = at or time.strftime("%Y-%m-%dT%H:%M:%S")
    entry = b["changelog"][-1]
    entry["approved_by"] = by
    if note:
        entry["note"] = note
    validate(b)
    if path or bible is None:
        write_json_atomic(path or PATH, b)
    return b


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--path", default=str(PATH))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("check")
    bp = sub.add_parser("bump")
    bp.add_argument("--reason", required=True)
    bp.add_argument("--major", action="store_true")
    ap = sub.add_parser("approve")
    ap.add_argument("--by", required=True)
    ap.add_argument("--note", default="")
    a = p.parse_args(argv)
    path = Path(a.path)
    if a.cmd == "show":
        b = load(path)
        print(text(b), b["date"], "-", b["reason"])
        for name, part in b["parts"].items():
            print(f"  {name:8} {part['file']:22} {part['sha256'][:12]}")
        print(f"  anchors: {', '.join(b['anchors']) or 'none yet'}; motion: {b['motion']['default']}")
        return 0
    if a.cmd == "check":
        problems = check(load(path))
        for x in problems:
            print("FAIL", x)
        print(f"{text(load(path))}: {len(problems)} finding(s)")
        return 1 if problems else 0
    if a.cmd == "bump":
        b = bump(a.reason, major=a.major, path=path)
        print(f"written {text(b)} -> {path}")
        return 0
    b = approve(a.by, note=a.note, path=path)
    print(f"{text(b)} approved by {b['approved_by']} at {b['approved_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
