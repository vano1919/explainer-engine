"""Captions of the finished film (final plan S18, W7): cues from the read's word timings, the SRT written by the vendored
kajisho5 subtitle-skill, the soft track put in by ffmpeg-skill ``caption --mode mux`` (CRAFT-MOG-07: never burned in on 16:9).

Splitting words into cues is our judgement (the skill takes finished cues): at most ``chars_per_line_max`` characters a line, at
most two lines, a cue breaks at a sentence end or when it is full, and its end is pushed out (into the gap before the next cue, never
over it) until it is read at no more than ``cps_max`` characters a second (BP-210). A cue that still cannot be read in time is kept
and the row VAL-SUB-02 says so: words are never dropped or shortened."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.finish import ffwrap
from explainer_engine.validators import _common as C
from explainer_engine.validators import subtitles as V

SKILL_SRC = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "v-subtitle-skill" / "src"
_END = (".", "!", "?", "…")


def _wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def build_cues(words: list[dict]) -> list[dict]:
    """``words``: ``[{word|text, start, end}]`` seconds in speaking order. Returns ``[{id, start, end, text}]`` (``text`` with a line break
    when the cue needs two lines). The widths and the reading speed are BP-210's."""
    width, cps = C.T("BP-210", "chars_per_line_max"), C.T("BP-210", "cps_max")
    if width is None or cps is None:
        raise ContractError("BP-210 chars_per_line_max / cps_max are not in standards/sourced_rules.json")
    groups, cur = [], []
    for w in words:
        token = str(w.get("word", w.get("text", ""))).strip()
        if not token:
            continue
        item = {"t": token, "s": float(w["start"]), "e": float(w["end"])}
        if cur and len(_wrap(" ".join(x["t"] for x in cur + [item]), width)) > 2:
            groups.append(cur)
            cur = []
        cur.append(item)
        if token.endswith(_END):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    cues = []
    for i, g in enumerate(groups):
        text = "\n".join(_wrap(" ".join(x["t"] for x in g), width))
        cues.append({"id": f"c{i + 1}", "start": g[0]["s"], "end": g[-1]["e"], "text": text})
    for i, c in enumerate(cues):   # read time: extend into the gap before the next cue, never over it
        need = len(c["text"].replace("\n", "")) / cps
        limit = cues[i + 1]["start"] if i + 1 < len(cues) else c["end"] + need
        c["end"] = round(min(max(c["end"], c["start"] + need), max(limit, c["end"])), 3)
    return cues


def write_srt(cues: list[dict], workspace: Path, name: str = "captions.srt", language: str = "en") -> Path:
    """The SRT through subtitle-skill ``generate`` (it validates the timeline and refuses overlaps and bad times). Returns the file."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    req = {"operation": "generate", "subtitle": {"id": Path(name).stem, "language": language, "cues": cues}, "format": "srt",
           "output_path": name, "workspace": str(workspace.resolve()),
           "constraints": {"max_chars_per_line": C.T("BP-210", "chars_per_line_max"), "reading_speed_cps": C.T("BP-210", "cps_max")}}
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "request.json"
        f.write_text(json.dumps(req), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-m", "subtitle_skill.cli", "run", str(f)], capture_output=True, text=True,
                              env={**os.environ, "PYTHONPATH": str(SKILL_SRC), "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        res = json.loads(proc.stdout)
    except ValueError:
        res = {}
    if proc.returncode != 0 or res.get("status") != "ok":
        raise ContractError(f"subtitle-skill generate failed: {(res.get('error') or {}).get('message') or proc.stderr.strip()[:300]}")
    return workspace / name


def mux_soft(video: Path, srt: Path, out: Path, language: str = "eng") -> dict:
    """The captions as a switchable track (the picture and sound streams copied untouched)."""
    return ffwrap.run("caption", [video, "--mode", "mux", "--srt", f"{srt}:{language}", "-o", out, "--overwrite"])


def rows(cues: list[dict]) -> list[dict]:
    """VAL-SUB-01 and VAL-SUB-02 on the cues."""
    return V.validate(cues)
