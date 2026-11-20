"""Prompt validators (final plan S5, W2): the image and motion prompts of the production script's shots (BP-207).

``image_prompt.start_frame_prompt`` must name at least ``image_details_min`` physical details, ``video_prompt.motion_prompt`` at most
``motion_actions_max`` physical action (the declared ``primary_action_count`` when the shot has one, else the count of
``shot_prompt_lint``), and neither may contain a word of the registry's ``slop_words`` list.
"""
from __future__ import annotations

import re

from explainer_engine.qa import gates as G
from explainer_engine.scripting import shot_prompt_lint as SPL
from explainer_engine.validators import _common as C

RULE_IDS = ("VAL-PRM-01", "VAL-PRM-02", "VAL-PRM-03", "VAL-PRM-04")
_STYLE = re.compile(r"\b(cinematic|anamorphic|\d+\s?mm|lens|film grain|photograph|docudrama|realism|chiaroscuro|style|render|"
                    r"aspect ratio|frame|shot)\b", re.I)


def _slop_re():
    words = C.T("BP-207", "slop_words")
    if not words:
        return None
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![\w-])", re.I)


def slop_words(shots: list[dict]) -> dict:
    """VAL-PRM-01: no banned quality-buzz word in any image, end-frame or motion prompt."""
    rx = _slop_re()
    if rx is None:
        return C.missing_threshold("VAL-PRM-01", "BP-207", "slop_words")
    hits = []
    for s in shots:
        texts = [(s.get("image_prompt") or {}).get("start_frame_prompt"), (s.get("image_prompt") or {}).get("end_frame_prompt"),
                 (s.get("video_prompt") or {}).get("motion_prompt")]
        for t in texts:
            for m in rx.findall(t or ""):
                hits.append((s.get("shot_id", "?"), m.lower()))
    return C.check("VAL-PRM-01", not hits, "BP-207", f"{len(hits)} banned word(s): {hits[:8]}" if hits else "no banned word", hits[:20])


def physical_details(prompt: str) -> int:
    """Distinct described details of an image prompt: comma, semicolon and 'with'/'and' separated phrases of at least three
    words that are not style or camera boilerplate."""
    parts = re.split(r"[,;.]|\bwith\b|\band\b", prompt)
    seen = {p.strip().lower() for p in parts if len(p.split()) >= 3 and not _STYLE.search(p)}
    return len(seen)


def image_details(shots: list[dict]) -> list[dict]:
    """VAL-PRM-02: every image prompt names at least image_details_min physical details."""
    need = C.T("BP-207", "image_details_min")
    if need is None:
        return [C.missing_threshold("VAL-PRM-02", "BP-207", "image_details_min")]
    rows = []
    for s in shots:
        p = (s.get("image_prompt") or {}).get("start_frame_prompt")
        gate = f"VAL-PRM-02:{s.get('shot_id', '?')}"
        if not p:
            rows.append(G.row(gate, None, "NOT_RUN: the shot has no image prompt"))
            continue
        n = physical_details(p)
        rows.append(C.check(gate, n >= need, "BP-207", f"{n} physical details (at least {need})", n))
    return rows or [G.row("VAL-PRM-02", None, "NOT_RUN: no shots")]


def motion_actions(shots: list[dict]) -> list[dict]:
    """VAL-PRM-03: a motion prompt asks for at most motion_actions_max physical action."""
    most = C.T("BP-207", "motion_actions_max")
    if most is None:
        return [C.missing_threshold("VAL-PRM-03", "BP-207", "motion_actions_max")]
    rows = []
    for s in shots:
        vp = s.get("video_prompt") or {}
        gate = f"VAL-PRM-03:{s.get('shot_id', '?')}"
        if not vp.get("motion_prompt"):
            continue   # a still has no motion prompt: nothing to count
        declared = vp.get("primary_action_count")
        n = declared if isinstance(declared, int) else SPL._clauses(SPL._action(vp["motion_prompt"]))
        src = "declared" if isinstance(declared, int) else "counted by shot_prompt_lint"
        rows.append(C.check(gate, n <= most, "BP-207", f"{n} physical action(s), {src} (at most {most})", n))
    return rows or [G.row("VAL-PRM-03", None, "NOT_RUN: no shot has a motion prompt")]


_LENS = {"focal_length": re.compile(r"\b\d{2,3}\s?mm\b", re.I), "aperture": re.compile(r"\bf\s?/?\s?\d{1,2}(\.\d)?\b", re.I),
         "depth_of_field": re.compile(r"\bdepth[- ]of[- ]field\b|\bDoF\b", re.I)}


def lens_named(shots: list[dict]) -> list[dict]:
    """VAL-PRM-04: every image prompt names its lens: a focal length, an aperture and a depth of field (BP-207 lens_parts)."""
    parts = C.T("BP-207", "lens_parts")
    if parts is None:
        return [C.missing_threshold("VAL-PRM-04", "BP-207", "lens_parts")]
    rows = []
    for s in shots:
        p = (s.get("image_prompt") or {}).get("start_frame_prompt")
        gate = f"VAL-PRM-04:{s.get('shot_id', '?')}"
        if not p:
            rows.append(G.row(gate, None, "NOT_RUN: the shot has no image prompt"))
            continue
        lacking = [k for k in parts if not _LENS[k].search(p)]
        rows.append(C.check(gate, not lacking, "BP-207", f"lens missing {lacking}" if lacking else "focal length, aperture and depth of field named",
                            lacking))
    return rows or [G.row("VAL-PRM-04", None, "NOT_RUN: no shots")]


def validate(script: dict) -> list[dict]:
    shots = script.get("shots") or []
    return [slop_words(shots), *image_details(shots), *motion_actions(shots), *lens_named(shots)]
