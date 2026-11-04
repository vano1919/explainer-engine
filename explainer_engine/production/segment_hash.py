# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/segment_hash.py`
# Target Module : explainer_engine/production/segment_hash.py
# Target Classes/Symbols : def _h(), def _pictures(), def hashes(), def stale(), def check(), def main()
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

"""Per-segment hashes (D-70 stage F): when a script changes, only what depends on the changed segments is made again.

A segment's voice depends on its spoken text (lines: text, tags, emphasis, pause_after, speaker); its pictures on their
prompts and references; its timing and edit on both plus the shots. ``stale(old, new)`` names, per changed segment, which
artifacts are out of date, so a fix to one line never re-voices or re-paints the rest. stdlib only.
"""

from __future__ import annotations

import hashlib
import json

VOICE_KEYS = ("text", "tags", "emphasis", "pause_after", "speaker")


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _pictures(seg: dict) -> dict:
    out = {}
    for s in seg.get("shots", []):
        p = s["picture"]
        if isinstance(p, dict):
            out[p["id"]] = _h({k: v for k, v in p.items() if k != "id"})
        else:
            out[p] = _h(p)
    return out


def hashes(doc: dict) -> dict:
    """{segment id: {voice, pictures: {picture id: hash}, edit}}."""
    out = {}
    for seg in doc["segments"]:
        voice = _h([{k: ln.get(k) for k in VOICE_KEYS} for ln in seg["lines"]])
        pics = _pictures(seg)
        edit = _h([voice, sorted(pics.items()), seg.get("shots"), [ln.get("visual_beats") for ln in seg["lines"]],
                   seg.get("audio"), seg.get("scene")])
        out[seg["id"]] = {"voice": voice, "pictures": pics, "edit": edit}
    return out


def stale(old: dict, new: dict) -> dict:
    """What to make again: {segment id: {"voice": bool, "pictures": [ids], "edit": bool, "removed"?: True}}.
    A segment with nothing out of date is left out. ``old`` and ``new`` are scripts or the output of ``hashes``."""
    a = old if all(isinstance(v, dict) and "voice" in v for v in old.values()) and "segments" not in old else hashes(old)
    b = new if all(isinstance(v, dict) and "voice" in v for v in new.values()) and "segments" not in new else hashes(new)
    out = {}
    for sid, h in b.items():
        was = a.get(sid)
        if was is None:
            out[sid] = {"voice": True, "pictures": sorted(h["pictures"]), "edit": True}
            continue
        pics = sorted(p for p, ph in h["pictures"].items() if was["pictures"].get(p) != ph)
        row = {"voice": was["voice"] != h["voice"], "pictures": pics, "edit": was["edit"] != h["edit"]}
        if row["voice"] or pics or row["edit"]:
            out[sid] = row
    for sid in a:
        if sid not in b:
            out[sid] = {"voice": False, "pictures": [], "edit": True, "removed": True}
    return out


def check(doc: dict, library: dict | None = None) -> list[dict]:
    """PV-59: a segment's ``asset_ids`` are records of the asset library and the script's ``bible`` version exists.
    PV-60: an approved segment review was given on the segment as it is now (its ``review.hash`` is the current edit hash)."""
    out = []
    used = [(seg["id"], a) for seg in doc["segments"] for a in seg.get("asset_ids", [])]
    if used:
        if library is None:
            from explainer_engine.assets import library as L
            library = L.load() if L.PATH.exists() else {"items": []}
        known = {r["id"] for r in library.get("items", [])}
        for sid, a in used:
            if a not in known:
                out.append({"rule": "PV-59", "severity": "FAIL", "where": sid, "detail": f"asset {a} is not in the asset library"})
    if doc.get("bible"):
        from explainer_engine.world import bible as B
        if doc["bible"]["version"] not in B.versions():
            out.append({"rule": "PV-59", "severity": "FAIL", "where": "bible",
                        "detail": f"world bible version {doc['bible']['version']} never existed (known: {B.versions()})"})
    now = hashes(doc)
    for seg in doc["segments"]:
        r = seg.get("review")
        if r and r["status"] == "approved":
            if not r.get("by"):
                out.append({"rule": "PV-60", "severity": "FAIL", "where": seg["id"], "detail": "an approved review needs a name (by)"})
            if r.get("hash") != now[seg["id"]]["edit"]:
                out.append({"rule": "PV-60", "severity": "REVIEW", "where": seg["id"],
                            "detail": "the segment changed after its review: show it again (python -m explainer_engine.production"
                                      ".segment_hash <script> prints the current hashes)"})
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.segment_hash",
                                 description="per-segment hashes of a production script, or what a new version makes stale")
    ap.add_argument("script")
    ap.add_argument("--against", help="an older version of the script: print what to make again")
    a = ap.parse_args(argv)
    new = json.loads(Path(a.script).read_text(encoding="utf-8"))
    if a.against:
        print(json.dumps(stale(json.loads(Path(a.against).read_text(encoding="utf-8")), new), indent=2))
    else:
        print(json.dumps(hashes(new), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
