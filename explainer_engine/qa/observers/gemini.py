"""Gemini observers (OB-1): two adapters, one record format.

* ``gemini_chat``: free. ``chat_task`` writes the G1 task file the creator pastes into his own Gemini chat (files listed, the
  questions, the exact JSON to return); ``ingest_chat`` reads the returned JSON and writes the records, stamped ``reviewed: owner``.
* ``gemini_api``: the Gemini File API with an ``fps`` setting. CODE AND MOCKED TESTS ONLY in W4: ``GeminiApiObserver`` takes a client
  from the caller and has no default one, so nothing here can start a paid call; without a client it writes a NOT_RUN record. A paid
  run needs the creator's word (docs/OBSERVATION.md section 6 has the priced plan). The raw answer is saved to disk before it is
  parsed (OR-33).

The JSON answer format of both: ``{"shots": {"<shot>": {"answers": {...}, "defects": [{"code","where","severity","note"}]}}}``.
"""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.qa import observe as OB
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa import status as ST
from explainer_engine.qa.observers import claude_look as CL

ANSWER_FORMAT = {"shots": {"<shot_id>": {"answers": {"<question>": "<yes/no or short text>"},
                                         "defects": [{"code": "F1..F19", "where": "t=2.6-4.0s", "severity": "major|minor|info", "note": "..."}]}}}


def prompt(questions: list[str]) -> str:
    qs = "\n".join(f"- {q}" for q in questions)
    return ("Watch the clip (picture and sound). Answer every question below with yes/no and a short reason. List every defect with its "
            "code (F1..F19 of the failure taxonomy), the time range, and severity (major = it must be re-made or trimmed, minor = a person "
            "decides, info). Say 'none' if nothing is wrong. Do not invent defects. Return ONLY JSON in this shape:\n"
            f"{json.dumps(ANSWER_FORMAT)}\nQuestions:\n{qs}")


def chat_task(root: Path, items: list[dict], out_path: Path) -> Path:
    """``items``: [{shot, kind, path, questions}]. Writes the G1 task file for the creator's Gemini chat."""
    lines = ["# G1 task: watch these files and answer", "", "Open each file in the Gemini chat (one message per file or all together).", ""]
    for it in items:
        lines += [f"## {it['shot']} ({it['kind']})", f"File: `{it['path']}`", ""]
    qs = sorted({q for it in items for q in it["questions"]})
    lines += ["## What to answer", "", prompt(qs), "", "Send the JSON back; it is ingested with `ingest_chat`."]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _records(root: Path, doc: dict, files: dict, observer: str, reviewed, evidence) -> list[dict]:
    out = []
    for shot, ans in doc.get("shots", {}).items():
        kind, path = files[shot]
        defects = [d for d in ans.get("defects", []) if d.get("code") in RR.R_ACTIONS]
        rest = [d for d in ans.get("defects", []) if d.get("code") not in RR.R_ACTIONS]
        note = f"{len(rest)} defect(s) with an unknown code were not recorded: {[d.get('code') for d in rest]}" if rest else None
        rec = OB.build(root, shot, kind, observer, path, questions=list(ans.get("answers", {})), answers=ans.get("answers", {}),
                       defects=defects, evidence=evidence, note=note, reviewed=reviewed,
                       verdict=ST.REVIEW if rest and not defects else None)
        out.append(OB.write(root, rec))
    return out


def ingest_chat(root: Path, answers_path: Path, files: dict[str, tuple[str, str]], message_id: str | None = None) -> list[dict]:
    """``files``: {shot: (kind, path)}. The creator ran the chat, so the records carry ``reviewed: owner``."""
    doc = json.loads(Path(answers_path).read_text(encoding="utf-8"))
    return _records(Path(root), doc, files, "gemini_chat", {"by": "owner", "at": OB._now(), "note": "Gemini chat run by the creator",
                                                           "message_id": message_id}, [str(answers_path)])


class GeminiApiObserver:
    """The File-API arm. ``client.generate(prompt, path, fps) -> str`` (JSON text) is supplied by the caller; none is built in."""

    def __init__(self, client=None, fps: float = 1.0, raw_dir: Path | None = None):
        self.client, self.fps, self.raw_dir = client, fps, raw_dir

    def observe(self, root: Path, shot: str, kind: str, path: str, questions: list[str]) -> dict:
        root = Path(root)
        if self.client is None:
            return OB.write(root, OB.build(root, shot, kind, "gemini_api", path, verdict=ST.NOT_RUN,
                                           note="NOT_RUN: no client; a paid Gemini call needs the creator's word (OR-23)"))
        p = Path(path) if Path(path).is_absolute() else root / path
        raw = self.client.generate(prompt(questions), str(p), self.fps)
        ev = []
        if self.raw_dir:
            rp = Path(self.raw_dir) / f"{shot}_{kind}_gemini_raw.json"
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(raw, encoding="utf-8")   # OR-33: saved before it is parsed
            ev.append(str(rp))
        try:
            doc = json.loads(raw)
        except ValueError:
            return OB.write(root, OB.build(root, shot, kind, "gemini_api", path, verdict=ST.REVIEW, evidence=ev,
                                           note="the answer was not valid JSON: a person reads the raw file"))
        return _records(root, doc, {shot: (kind, path)}, "gemini_api", None, ev)[0]
