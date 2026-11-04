# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/script_approval.py`
# Target Module : explainer_engine/scripting/script_approval.py
# Target Classes/Symbols : def words_sha256(), def promises_sha256(), def check(), def approve(), def main()
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

"""The creator approves the finished script before anything is paid for (approval #1, OR-17, PV-53; creator 2026-10-20).

The order is: a short scenario the creator approves (OR-15, PV-45), then the full production script written to every
rule, then the creator reads that script and approves it, and only then does any paid step run (a read, a picture, music).
``episode.script_approval`` records the second approval: who, when, and the sha256 of every word the viewer will hear
(the segments' and the Shorts' lines with their speakers) and, when the script carries them, of the three packaging promises. A line changed after the approval is caught and the script goes
back to the creator. Delivery tags, pictures, files and voice ids may change after the approval; the words may not.

Binding on ``production_script/3`` (every new episode); earlier schemas get no finding (Syndicate Wars stays as it is).
Enforced before paid pictures (``production/paint.py``), before paid ElevenLabs audio (``standards/hook.py``) and shown as
gate 0.9 of ``production_gate``. stdlib only.

    python -m explainer_engine.scripting.script_approval check production_script.json
    python -m explainer_engine.scripting.script_approval approve production_script.json --by <creator> [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

BINDING = "production_script/3"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def words_sha256(doc: dict) -> str:
    """The hash of what is said: every segment's and every Short's lines (speaker, text, and whether it is a bubble), in order."""
    def one(ln):  # a silent line (D-62, shown as bubbles) is part of what was approved; voiced lines hash as before
        row = [ln.get("speaker") or "narrator", ln["text"].strip()]
        return row + ["bubble"] if ln.get("voiced", True) is False else row
    said = [[seg["id"], [one(ln) for ln in seg["lines"]]] for seg in doc.get("segments", [])]
    said += [[f"short:{sh.get('id', i)}", [one(ln) for ln in sh.get("lines", [])]]
             for i, sh in enumerate(doc.get("shorts", []))]
    return hashlib.sha256(json.dumps(said, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def promises_sha256(doc: dict) -> str | None:
    """The hash of the three packaging promises (``drama.packaging_promises``, BP-135), or None when the script has none."""
    promises = (doc.get("drama") or {}).get("packaging_promises")
    if not promises:
        return None
    return hashlib.sha256(json.dumps(promises, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def check(doc: dict) -> list[dict]:
    if doc.get("schema") != BINDING:
        return []
    rec = doc.get("episode", {}).get("script_approval")
    if not rec:
        return [{"rule": "PV-53", "severity": "FAIL", "where": "episode.script_approval",
                 "detail": "the creator has not approved this finished script (approval #1, OR-17): send it, then record "
                           "the approval (script_approval approve --by <creator>) before any paid step"}]
    out = []
    missing = [k for k in ("approved_by", "approved_at", "sha256") if not str(rec.get(k, "")).strip()]
    if missing:
        out.append({"rule": "PV-53", "severity": "FAIL", "where": "episode.script_approval", "detail": f"empty: {missing}"})
    if rec.get("approved_at") and not DATE.match(rec["approved_at"]):
        out.append({"rule": "PV-53", "severity": "FAIL", "where": "episode.script_approval", "detail": "approved_at is YYYY-MM-DD"})
    if rec.get("sha256") and rec["sha256"] != words_sha256(doc):
        out.append({"rule": "PV-53", "severity": "FAIL", "where": "episode.script_approval",
                    "detail": "the lines changed after the creator approved the script: send the changed script again"})
    if rec.get("promises_sha256") and rec["promises_sha256"] != promises_sha256(doc):
        out.append({"rule": "PV-53", "severity": "FAIL", "where": "drama.packaging_promises",
                    "detail": "the packaging promises changed after the creator approved the script: the title and thumbnail "
                              "promise what he agreed to (send them again)"})
    return out


def approve(path: Path, by: str, date: str | None = None) -> dict:
    """Record the creator's approval of the script as it stands now (run only after the creator said yes)."""
    from explainer_engine.core.store import write_json_atomic
    if not by.strip():
        raise ValueError("--by names the creator who approved the script")
    doc = json.loads(path.read_text(encoding="utf-8"))
    rec = {"approved_by": by.strip(), "approved_at": date or time.strftime("%Y-%m-%d"), "sha256": words_sha256(doc)}
    if promises_sha256(doc):  # the three promises are approved with the words (ZI-10): a changed one is a PV-53 FAIL
        rec["promises_sha256"] = promises_sha256(doc)
    doc["episode"]["script_approval"] = rec
    write_json_atomic(path, doc)
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["check", "approve"])
    ap.add_argument("script", type=Path)
    ap.add_argument("--by", default="")
    ap.add_argument("--date")
    a = ap.parse_args(argv)
    if a.cmd == "approve":
        print(json.dumps(approve(a.script, a.by, a.date), ensure_ascii=False))
        return 0
    found = check(json.loads(a.script.read_text(encoding="utf-8")))
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    print("approved" if not found else f"{len(found)} FAIL")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
