# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/stage_guard.py`
# Target Module : explainer_engine/scripting/stage_guard.py
# Target Classes/Symbols : def _interjection_only(), def violations(), def _no_short_beats(), def _unplaced(), def words_frozen(), def _sha(), def _log(), def start(), def fresh(), def main()
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

"""Stage guard (D-48, docs/STORY_ENGINE.md "The writers' room"): each agent stage may change only its own fields of the
one production script, so a later pass (voice tags, shots, sounds) can never quietly rewrite the story an earlier pass
settled. This is how a mid-size model (Claude Sonnet) keeps the whole text while it adds technical detail: the words are
frozen after the scene pass, and the guard proves it.

    python -m explainer_engine.scripting.stage_guard <stage> before.json after.json   # exit 1 on a violation

The re-read rule (OR-32, D-79): a stage starts by Reading its page and the files the page says to read first, and records it;
a stage output without that record is reported, so a stage is never written from a compacted memory of its rules.

    python -m explainer_engine.scripting.stage_guard start <stage> --job <job folder> --page <stage page> [--input FILE]...
    python -m explainer_engine.scripting.stage_guard fresh <stage> --job <job folder> <stage output.json> [--strict]

``start`` appends ``{stage, at, page{path, sha256}, inputs[]}`` to ``<job>/story/stage_log.jsonl``; ``fresh`` lists what is wrong
with the output (REVIEW until the creator's A5 card is final; ``--strict`` exits 1).

Stages and what they own:

* ``architect``  the story layer: ``drama``, ``cast``, ``periods``, segment ids, ``beat``, ``purpose``, ``period``, ``light_beat``, segment ``drama`` and the dialogue segment's ``scene`` header (SC-01)
* ``writer``     the words: segment ``lines`` (text, speaker, claims); one segment at a time
* ``beats``      the visual beats (VB rules): line ``visual_beats`` only, written segment by segment right after the writer, on
  the same frozen words (stage 2b, agent ``beat-writer``); the Shorts' lines too (``shorts[].lines[].visual_beats``, SS-09)
* ``performer``  the delivery: line ``tags``, ``emphasis``, ``tone``, ``emotion``, ``pause_after``; the text may only gain
  an interjection at its start (``INTERJECTIONS``)
* ``editor``     the picture and sound: ``shots``, segment ``audio`` and ``staging`` (D-69), ``music``, ``graphics``, ``library``, ``story``,
  ``look``, ``picture_dirs``, ``sound_dirs``; of the beats only their ``pos`` (where on the frame), never what they show
* ``caster``     the voices: ``voice`` and ``cast.<id>.voice`` (the architect owns the rest of ``cast``)
* ``shorts``     the ``shorts`` block
* ``sound``      owns NO script field (P4, step 4b of ``edit-planner``): the sound pass runs the audio spine and the sound director
  and writes only under ``audio/`` (``sound_mix_manifest.json``, never by hand, CN-02); any change to the script it made is a violation
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

INTERJECTIONS = ("oh", "hmm", "well", "right", "ah", "uh-oh", "wait", "okay", "huh", "so", "look", "yeah", "nope")
SEG_STORY = ("id", "beat", "purpose", "period", "light_beat", "drama", "scene", "rhythm_zone")
LINE_WORDS = ("text", "speaker", "claims", "voiced")
LINE_DELIVERY = ("tags", "emphasis", "tone", "emotion", "pause_after")
STAGES = {
    "architect": {"top": {"drama", "episode", "periods", "cast"}, "seg": set(SEG_STORY), "line": set()},
    "writer": {"top": set(), "seg": {"lines"}, "line": set(LINE_WORDS)},
    "beats": {"top": set(), "seg": set(), "line": {"visual_beats"}},
    "performer": {"top": set(), "seg": set(), "line": set(LINE_DELIVERY) | {"text"}},
    "editor": {"top": {"music", "graphics", "counter", "library", "story", "look", "picture_dirs", "sound_dirs", "world"},
               "seg": {"shots", "audio", "staging"}, "line": set()},
    "caster": {"top": {"voice"}, "seg": set(), "line": set(), "cast_voice": True},
    "shorts": {"top": {"shorts"}, "seg": set(), "line": set()},
    "sound": {"top": set(), "seg": set(), "line": set()},  # owns nothing: the guard proves the pass left the script as it was
}


def _interjection_only(old: str, new: str) -> bool:
    if old == new:
        return True
    if not new.endswith(old) and not new.endswith(old[:1].lower() + old[1:]):
        return False
    head = new[: len(new) - len(old)].strip().rstrip(",.!?—-").strip().lower()
    return head in INTERJECTIONS


def violations(stage: str, before: dict, after: dict) -> list[str]:
    own = STAGES[stage]
    out: list[str] = []
    for k in sorted(set(before) | set(after)):
        if k == "segments" or k in own["top"]:
            continue
        if k == "cast" and own.get("cast_voice"):  # the caster changes only each hero's voice
            bc, ac = before.get("cast", {}), after.get("cast", {})
            for h in sorted(set(bc) | set(ac)):
                if {x: y for x, y in (bc.get(h) or {}).items() if x != "voice"} != {x: y for x, y in (ac.get(h) or {}).items() if x != "voice"}:
                    out.append(f"cast.{h} changed beyond its voice")
            continue
        if k == "shorts" and stage == "beats" and _no_short_beats(before.get(k)) == _no_short_beats(after.get(k)):
            continue  # SS-09: the beat-writer writes the Shorts' beats too, nothing else of a Short
        if before.get(k) != after.get(k):
            out.append(f"{k} changed: not the {stage}'s field")
    bs, as_ = before.get("segments", []), after.get("segments", [])
    if stage != "architect" and [s.get("id") for s in bs] != [s.get("id") for s in as_]:
        out.append("segments added, removed or reordered: only the architect does that")
        return out
    for sb, sa in zip(bs, as_):
        sid = sa.get("id")
        for k in sorted(set(sb) | set(sa)):
            if k in own["seg"] or k == "lines":
                continue
            if sb.get(k) != sa.get(k):
                out.append(f"{sid}.{k} changed: not the {stage}'s field")
        lb, la = sb.get("lines", []), sa.get("lines", [])
        if "lines" in own["seg"]:
            continue  # the writer owns whole lines of the segments it touches
        if len(lb) != len(la):
            out.append(f"{sid}: lines added or removed (the words are frozen after the writer)")
            continue
        for i, (a, b) in enumerate(zip(lb, la), 1):
            for k in sorted(set(a) | set(b)):
                if a.get(k) == b.get(k):
                    continue
                if k == "text" and "text" in own["line"] and _interjection_only(a["text"], b["text"]):
                    continue
                if k == "visual_beats" and stage == "editor" and _unplaced(a.get(k)) == _unplaced(b.get(k)):
                    continue  # the editor may move a beat on the frame (pos) to fit the picture it chose
                if k not in own["line"] or k == "text":
                    out.append(f"{sid} line {i}: {k} changed ({str(a.get(k))[:30]!r} -> {str(b.get(k))[:30]!r})")
    return out


def _no_short_beats(shorts) -> list | None:
    if shorts is None:
        return None
    return [dict(sh, lines=[{k: v for k, v in ln.items() if k != "visual_beats"} for ln in sh.get("lines", [])]) for sh in shorts]


def _unplaced(beats) -> list | None:
    return None if beats is None else [{k: v for k, v in b.items() if k != "pos"} for b in beats]


def words_frozen(before: dict, after: dict) -> bool:
    """True when every spoken word is unchanged except allowed interjections (the performer's promise)."""
    return not [v for v in violations("performer", before, after) if "text" in v]


ORDER = ("architect", "writer", "beats", "performer", "editor", "caster", "shorts")  # the stages in the order they run
LOG = Path("story") / "stage_log.jsonl"


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _log(job: Path) -> list[dict]:
    p = Path(job) / LOG
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def start(stage: str, job: Path | str, *, page: Path | str, inputs=()) -> dict:
    """Record that ``stage`` began with its page and inputs read (OR-32): their sha256 now, so a change during the stage shows."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}: {sorted(STAGES)}")
    page = Path(page)
    if not page.is_file():
        raise FileNotFoundError(f"the stage page {page} does not exist: read it before the stage starts")
    rec = {"stage": stage, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "page": {"path": str(page), "sha256": _sha(page)},
           "inputs": [{"path": str(Path(i)), "sha256": _sha(Path(i))} for i in inputs]}
    log = Path(job) / LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def fresh(stage: str, job: Path | str, out: Path | str) -> list[str]:
    """What is wrong with a stage output (OR-32): no start record, a start recorded before the previous stage's, a stage page or an
    input that changed since the start, or no output. Empty when the stage began with a fresh read."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}: {sorted(STAGES)}")
    found: list[str] = []
    rows = _log(job)
    mine = [r for r in rows if r["stage"] == stage]
    if not Path(out).is_file():
        found.append(f"{out}: the stage output does not exist")
    if not mine:
        return found + [f"no `stage_guard start {stage}` record in {Path(job) / LOG}: read the stage page and its inputs, then record it"]
    last = mine[-1]
    earlier = [r for r in rows if r["stage"] in ORDER[:ORDER.index(stage)]] if stage in ORDER else []
    if earlier and max(r["at"] for r in earlier) > last["at"]:
        found.append(f"the {stage} start ({last['at']}) is older than the {earlier[-1]['stage']} stage's: start it again after the previous stage")
    for what in [last["page"]] + last["inputs"]:
        if _sha(Path(what["path"])) != what["sha256"]:
            found.append(f"{what['path']} changed since the {stage} stage started: read it again and start the stage again")
    return found


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] in ("start", "fresh"):
        import argparse
        ap = argparse.ArgumentParser(prog=f"stage_guard {argv[0]}")
        ap.add_argument("cmd")
        ap.add_argument("stage")
        ap.add_argument("--job", required=True)
        if argv[0] == "start":
            ap.add_argument("--page", required=True)
            ap.add_argument("--input", action="append", default=[])
        else:
            ap.add_argument("out")
            ap.add_argument("--strict", action="store_true")
        a = ap.parse_args(argv)
        if a.cmd == "start":
            print(json.dumps(start(a.stage, a.job, page=a.page, inputs=a.input), ensure_ascii=False))
            return 0
        found = fresh(a.stage, a.job, a.out)
        for v in found:
            print("REVIEW", v)
        print(f"{len(found)} finding(s) for stage {a.stage} (REVIEW until the creator's A5 card is final)")
        return 1 if found and a.strict else 0
    stage, a, b = argv[0], Path(argv[1]), Path(argv[2])
    found = violations(stage, json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8")))
    for v in found:
        print("FAIL", v)
    print(f"{len(found)} violation(s) for stage {stage}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
