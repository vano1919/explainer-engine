"""The creator approves the finished script before anything is paid for (approval #1, OR-17, PV-53; creator 2026-10-20).

The order is: a short scenario the creator approves (OR-15, PV-45), then the full production script written to every
rule, then the creator reads that script and approves it, and only then does any paid step run (a read, a picture, music).
``episode.script_approval`` records the second approval: who, when, and the sha256 of every word the viewer will hear
(the segments' and the Shorts' lines with their speakers). A line changed after the approval is caught and the script goes
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
    return out


def approve(path: Path, by: str, date: str | None = None) -> dict:
    """Record the creator's approval of the script as it stands now (run only after the creator said yes)."""
    from explainer_engine.core.store import write_json_atomic
    if not by.strip():
        raise ValueError("--by names the creator who approved the script")
    doc = json.loads(path.read_text(encoding="utf-8"))
    rec = {"approved_by": by.strip(), "approved_at": date or time.strftime("%Y-%m-%d"), "sha256": words_sha256(doc)}
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
