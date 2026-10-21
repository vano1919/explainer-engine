"""The two-part sample gate (OR-19, D-67; creator 2026-10-21): paid voice and pictures run for the SAMPLE first.

After the creator approves the script and the combined estimate (images + audio, 2026-10-20), paid generation covers only
the sample: the first two segments' voice and pictures, painted and read in parallel, rendered and stitched into one piece
the creator watches. His notes are fixed and the sample re-rendered; only his recorded word opens paid voice and pictures
for the rest of the video (and the Shorts). ``sample_approval.json`` next to the script records that word, bound to the
script's sha256, so a script edited after the approval needs a new sample and a new approval.

    python -m explainer_engine.production.sample status  <episode folder>                      # scope, counts, approval
    python -m explainer_engine.production.sample approve <episode folder> --by <name> --ref <message> [--video <file>]

Enforced in code: ``paint.preflight`` refuses a plan with pictures no sample segment uses (PP-09), the ElevenLabs hook
refuses a paid read whose text is not inside the sample segments (``standards/hook.py``), and ``production_gate`` shows
gate 6.5. Out of the gate's reach and allowed before the approval: ``estimate_only`` calls, reusable channel assets
(face sheets, references, plans marked ``reusable``) and library sounds; music and sound effects stay behind the
library-first and ``paid_assets`` gates and are kept to the sample by this rule procedurally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from explainer_engine.audio.scribe_words import norm, strip_tags
from explainer_engine.production import script as S

FILE = "sample_approval.json"
PARTS = 2  # the creator watches the first two parts before the rest is paid for


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(folder: Path) -> dict:
    p = Path(folder) / FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def scope_segments(doc: dict, folder: Path | None = None) -> list[str]:
    """The sample's segments: ``scope_segments`` of ``sample_approval.json`` when set, else the first two of the script."""
    rec = load(folder) if folder is not None else {}
    ids = [seg["id"] for seg in doc["segments"]]
    want = rec.get("scope_segments") or ids[:PARTS]
    return [i for i in ids if i in set(want)]


def scope_pictures(doc: dict, scope: list[str] | None = None, folder: Path | None = None) -> set[str]:
    """Pictures the sample needs: every picture a shot of a sample segment uses (shared pictures count)."""
    scope_set = set(scope if scope is not None else scope_segments(doc, folder))
    return {sh["picture_id"] for sh in S.shots(doc) if sh["segment"] in scope_set}


def _words(text: str) -> list[str]:
    out: list[str] = []
    for tok in strip_tags(text).split():
        out += norm(tok)
    return out


def speech_in_scope(text: str, doc: dict, folder: Path | None = None) -> bool:
    """True when the read's words sit contiguously inside the sample segments (tags, capitals and pauses ignored)."""
    want = _words(text)
    if not want:
        return False
    scope_set = set(scope_segments(doc, folder))
    have: list[str] = []
    for seg in doc["segments"]:
        if seg["id"] in scope_set:
            have += _words(" ".join(line["text"] for line in seg["lines"]))
    return any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1))


def approved(folder: Path, script_path: Path | None = None) -> tuple[bool, str]:
    """(is the sample approved for this exact script, the reason it is not)."""
    rec = load(folder)
    if not rec:
        return False, f"no {FILE}: the creator watches the stitched two-part sample first (OR-19)"
    missing = [k for k in ("approved_by", "approved_at", "ref") if not str(rec.get(k, "")).strip()]
    if missing:
        return False, f"{FILE} is missing {missing}"
    script_path = script_path or Path(folder) / "production_script.json"
    if rec.get("script_sha256") and script_path.exists() and sha256(script_path) != rec["script_sha256"]:
        return False, "the script changed after the sample approval: re-render the sample, the creator approves again"
    return True, ""


def check_plan(plan: dict, doc: dict, script_path: Path) -> list[dict]:
    """PP-09: before the sample approval a plan paints only the sample's pictures; reusable plans and face sheets pass."""
    folder = Path(script_path).parent
    ok, why = approved(folder, Path(script_path))
    if ok or plan.get("reusable") or plan.get("faces_saving"):
        return []
    pics = scope_pictures(doc, folder=folder)
    script_pics, _ = S.pictures(doc)
    outside = sorted(i["id"] for i in plan["items"] if i["id"] in script_pics and i["id"] not in pics)
    if not outside:
        return []
    return [{"rule": "PP-09", "severity": "FAIL", "where": f"plan {plan.get('id')}",
             "detail": f"{len(outside)} pictures outside the sample segments ({', '.join(scope_segments(doc, folder))}) "
                       f"before the sample approval: {', '.join(outside[:8])}"
                       + (f" (+{len(outside) - 8} more)" if len(outside) > 8 else "") + f"; {why}"}]


def hook_speech(tool: str, tool_input: dict, folder: Path) -> str | None:
    """The ElevenLabs hook's reason to deny a paid read outside the sample (None = the gate passes)."""
    if tool != "creative_generate_speech":
        return None
    script_path = Path(folder) / "production_script.json"
    if not script_path.exists():
        return None
    ok, why = approved(folder, script_path)
    if ok:
        return None
    doc = S.load(script_path)
    text = tool_input.get("text") or tool_input.get("prompt") or ""
    if speech_in_scope(text, doc, folder):
        return None
    return (f"OR-19: this read is outside the sample segments ({', '.join(scope_segments(doc, folder))}) and {why}; "
            "after the creator's word: python -m explainer_engine.production.sample approve")


def gate_row(day: Path, script_path: Path | None = None) -> tuple[str, str, str]:
    """Gate 6.5 of production_gate: PASS only on the creator's recorded sample approval for this exact script."""
    script_path = script_path or day / "production_script.json"
    ok, why = approved(day, script_path)
    if ok:
        rec = load(day)
        return "PASS", f"approved by {rec['approved_by']} ({rec['approved_at']}, {rec['ref']})", ""
    doc = S.load(script_path)
    scope = scope_segments(doc, day)
    return "WAIT", f"sample = {', '.join(scope)} ({len(scope_pictures(doc, scope))} pictures); {why}", \
        "voice + pictures for the sample only, render and stitch it, the creator watches; then production.sample approve"


def approve(folder: Path, by: str, ref: str, video: str | None = None) -> dict:
    from explainer_engine.core.store import write_json_atomic
    folder = Path(folder)
    script_path = folder / "production_script.json"
    doc = S.load(script_path)
    rec = load(folder)
    rec.update({"scope_segments": scope_segments(doc, folder), "approved_by": by, "approved_at": time.strftime("%Y-%m-%d"),
                "ref": ref, "script_sha256": sha256(script_path)})
    if video:
        rec["sample_video"] = video
    write_json_atomic(folder / FILE, rec)
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.sample", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("status")
    q.add_argument("folder")
    q = sub.add_parser("approve")
    q.add_argument("folder")
    q.add_argument("--by", required=True)
    q.add_argument("--ref", required=True, help="the creator's message that says yes (thread message id, or date and words)")
    q.add_argument("--video", help="the stitched sample the creator watched")
    a = ap.parse_args(argv)
    folder = Path(a.folder)
    if a.cmd == "approve":
        rec = approve(folder, a.by, a.ref, a.video)
        print(f"sample approved by {rec['approved_by']} ({rec['approved_at']}): segments {', '.join(rec['scope_segments'])}; "
              "paid voice and pictures for the rest may be planned now")
        return 0
    status, detail, nxt = gate_row(folder)
    print(f"{status} {detail}" + (f"  -> {nxt}" if nxt else ""))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
