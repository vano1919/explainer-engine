"""The measured length of the lines an LTX clip speaks itself (Q4, the creator 2026-11-13, answer a; D-138).

Before any paid LTX scene every video shot is sized from a real read, not from the seconds written in the script: a narrated
or silent shot from the narration's read (G6, ``audio/timing.json``), a clip-spoken shot from a read of its own line, a TTS
take or a recording of the line. This module measures those line files and keeps the result in ``audio/line_reads.json``
(``line_reads/1``): for every line its speech seconds (first to last speech span, ``qa/sound_realism.speech_spans``), the
source (``tts`` or ``recording``), the file and its sha256. ``videolane/scene.build`` sizes the clip from it (basis
``measured_line``); with switch Q4 = forced a video shot without a measured basis refuses the scene, and
``scene.storyboard_problems`` refuses it again at the paid launch (``scene_run.job_spec``).

Free: it only reads files that exist. Making a TTS take is a paid step of its own and is not done here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

SCHEMA = "line_reads/1"
REL = "audio/line_reads.json"
SOURCES = ("tts", "recording")


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def speech_seconds(path: Path) -> dict:
    """The speech of one line file: ``{"seconds", "start_s", "end_s", "spans"}``; a file with no speech refuses."""
    from explainer_engine.qa import sound_realism as SRL
    x = SRL.read_audio(Path(path))
    spans = SRL.speech_spans(x, SRL.SR)
    if not spans:
        raise ContractError(f"{path}: no speech found in the line read")
    a, b = spans[0][0], spans[-1][1]
    return {"seconds": round(b - a, 3), "start_s": a, "end_s": b, "spans": [list(s) for s in spans]}


def measure(root: Path, script: dict, files: dict, source: str) -> dict:
    """Measure ``files`` (``{line_id: path}``) and merge them into ``audio/line_reads.json``. Every id must be a character
    line of the script; ``source`` is ``tts`` or ``recording``."""
    if source not in SOURCES:
        raise ContractError(f"line read source {source!r} is not one of {SOURCES}")
    lines = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}
    root = Path(root)
    doc = load(root) or {"schema": SCHEMA, "lines": {}}
    for lid, path in files.items():
        ln = lines.get(lid)
        if not ln or ln.get("speaker_type") != "character":
            raise ContractError(f"{lid}: not a character line of the script")
        m = speech_seconds(Path(path))
        doc["lines"][lid] = dict(m, source=source, file=str(path), sha256=_sha(Path(path)),
                                 speaker=ln.get("speaker_id"), text=ln.get("text"))
    write_json_atomic(root / REL, doc)
    return doc


def load(root: Path) -> dict | None:
    import json
    p = Path(root) / REL
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def seconds_by_line(root: Path) -> dict:
    """``{line_id: seconds}`` of the lines whose file is still the one measured (a changed file no longer counts)."""
    doc = load(root) or {}
    out = {}
    for lid, r in (doc.get("lines") or {}).items():
        f = Path(r.get("file") or "")
        if f.is_file() and _sha(f) == r.get("sha256"):
            out[lid] = float(r["seconds"])
    return out
