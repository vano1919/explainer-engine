"""Caption validators (final plan S18, W2): at most chars_per_line_max characters per line and at most cps_max characters per second
per cue (BP-210). Input: cues ``{start, end, text}`` (seconds; ``text`` may hold line breaks) or an SRT string."""
from __future__ import annotations

import re

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("VAL-SUB-01", "VAL-SUB-02")
_TIME = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{3})")


def parse_srt(srt: str) -> list[dict]:
    cues = []
    for block in re.split(r"\n\s*\n", srt.strip().replace("\r\n", "\n")):
        lines = block.split("\n")
        for i, ln in enumerate(lines):
            m = _TIME.search(ln)
            if m:
                g = [int(x) for x in m.groups()]
                cues.append({"start": g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, "end": g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                             "text": "\n".join(lines[i + 1:])})
                break
    return cues


def chars_per_line(cues: list[dict]) -> dict:
    """VAL-SUB-01: no caption line longer than chars_per_line_max characters."""
    mx = C.T("BP-210", "chars_per_line_max")
    if mx is None:
        return C.missing_threshold("VAL-SUB-01", "BP-210", "chars_per_line_max")
    if not cues:
        return G.row("VAL-SUB-01", None, "NOT_RUN: no cues")
    over = [(i, len(l)) for i, c in enumerate(cues) for l in c["text"].split("\n") if len(l) > mx]
    return C.check("VAL-SUB-01", not over, "BP-210", f"{len(over)} line(s) over {mx} characters: {over[:8]}" if over else
                   f"every line is at most {mx} characters", over[:20])


def reading_speed(cues: list[dict]) -> dict:
    """VAL-SUB-02: no cue read faster than cps_max characters per second (line breaks do not count)."""
    mx = C.T("BP-210", "cps_max")
    if mx is None:
        return C.missing_threshold("VAL-SUB-02", "BP-210", "cps_max")
    if not cues:
        return G.row("VAL-SUB-02", None, "NOT_RUN: no cues")
    fast = []
    for i, c in enumerate(cues):
        dur = float(c["end"]) - float(c["start"])
        cps = len(c["text"].replace("\n", "")) / dur if dur > 0 else float("inf")
        if cps > mx:
            fast.append((i, round(cps, 1)))
    return C.check("VAL-SUB-02", not fast, "BP-210", f"{len(fast)} cue(s) over {mx} CPS: {fast[:8]}" if fast else f"every cue is at most {mx} CPS",
                   fast[:20])


def validate(cues_or_srt) -> list[dict]:
    cues = parse_srt(cues_or_srt) if isinstance(cues_or_srt, str) else cues_or_srt
    return [chars_per_line(cues), reading_speed(cues)]
