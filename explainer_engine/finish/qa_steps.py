"""``check.py`` and ``look.py`` of the vendored ffmpeg-skill as QA steps of the render path (final plan S14/S16, W7).

``check_rows`` runs the skill's platform check with its content pass (black, frozen, silent, dropouts, flashes) and returns one gate
row (VAL-QA-07) whose measured value lists every check with its status; ``look_row`` makes the timecoded contact sheet (VAL-QA-08)
for the observer or the creator. Neither can PASS a picture's content: a miss and a made sheet are REVIEW, a missing tool is NOT_RUN.
"""
from __future__ import annotations

from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.finish import ffwrap
from explainer_engine.qa import gates as G

_MAP = {"PASS": True, "WARN": False, "FAIL": False}


def check_row(video, platform: str = "youtube", gate: str = "VAL-QA-07") -> dict:
    """The skill's ``check`` of ``video``: PASS only when every row the skill returned is PASS (UNKNOWN rows are listed and make the
    row REVIEW, they are not passes); a WARN or FAIL is REVIEW (no registry number owns these rows)."""
    if not Path(video).is_file():
        return G.row(gate, None, f"NOT_RUN: {video} does not exist")
    if not ffwrap.available():
        return G.row(gate, None, "NOT_RUN: ffmpeg, ffprobe or the vendored ffmpeg-skill is missing")
    try:
        doc = ffwrap.check(Path(video), platform=platform, content=True)
    except (ContractError, OSError, ValueError) as exc:
        return G.row(gate, None, f"NOT_RUN: {exc}")
    rows = [{"check": c.get("check"), "status": c.get("status"), "value": c.get("value")} for c in doc.get("checks", [])]
    if not rows:
        return G.row(gate, None, "NOT_RUN: the skill returned no check rows")
    bad = [r for r in rows if r["status"] != "PASS"]
    return G.row(gate, not bad, f"{len(rows) - len(bad)} of {len(rows)} {platform} checks pass" +
                 (f"; not passing: {[(r['check'], r['status']) for r in bad]}" if bad else ""), rows, level=G.REVIEW)


def look_row(video, out_png, tiles: str = "4x3", gate: str = "VAL-QA-08") -> dict:
    """A contact sheet of ``video`` at ``out_png``. The row is REVIEW when the sheet exists (someone must look at it: the observation
    record is W4's), NOT_RUN when it could not be made. It is never PASS."""
    if not Path(video).is_file():
        return G.row(gate, None, f"NOT_RUN: {video} does not exist")
    if not ffwrap.available():
        return G.row(gate, None, "NOT_RUN: ffmpeg, ffprobe or the vendored ffmpeg-skill is missing")
    try:
        ffwrap.look(Path(video), Path(out_png), tiles=tiles)
    except (ContractError, OSError, ValueError) as exc:
        return G.row(gate, None, f"NOT_RUN: {exc}")
    made = Path(out_png).is_file() and Path(out_png).stat().st_size > 0
    return G.row(gate, False if made else None, f"contact sheet {out_png} made ({tiles}); looking at it is an observation, not this row"
                 if made else "NOT_RUN: the skill reported success but no sheet is on disk", {"sheet": str(out_png)}, level=G.REVIEW)
