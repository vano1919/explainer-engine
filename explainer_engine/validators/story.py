"""Story validators for a v4 production script (final plan S1/S2, W2).

``scripting/story_lint`` runs only ST-02, ST-13, ST-14 and ST-21 on a ``4.0.0`` script (W8's finding: 0 findings hide four flat
shots in a row); ``scripting/scene_lint`` runs SC-07, SC-08, SC-09, SC-11 and SC-12 only on the pre-v4 segment model. This module
holds the checks that work on the v4 model (``audio_lines``, ``segments``, ``shots``) without editing either linter: SC-07 (press-release
register, via ``narration_lint.press_release``), SC-09 (turn length, BP-72/BP-73), SC-11 and SC-12 (via ``scene_lint.immersion_and_showing``
on an adapter of the v4 lines), and four new rules: VAL-STO-01 value-charge cadence, VAL-STO-02 every scene names what each side wants and
its turn, VAL-STO-03 a narrated sentence is not stronger than its claim, VAL-STO-04 a numeric claim names at least two sources.
Thresholds only from ``sourced_rules`` (BP-72, BP-73, BP-76, BP-213); a hypothesis is REVIEW.
"""
from __future__ import annotations

import re

from explainer_engine.qa import gates as G
from explainer_engine.scripting import narration_lint, scene_lint, story_lint
from explainer_engine.validators import _common as C

RULE_IDS = ("SC-07", "SC-09", "SC-11", "SC-12", "VAL-STO-01", "VAL-STO-02", "VAL-STO-03", "VAL-STO-04")
_URL = re.compile(r"https?://[^\s|)>\]]+")
_NUMBER = re.compile(r"\b\d[\d,.]*\b")


def _narrator(ln: dict) -> bool:
    return ln.get("speaker_type", "narrator") == "narrator"


def _findings_row(gate: str, found: list[dict], ok_detail: str) -> dict:
    """One row from a legacy linter's findings: PASS without findings, FAIL if any finding is FAIL, else REVIEW."""
    if not found:
        return G.row(gate, True, ok_detail)
    hard = any(f.get("severity") == "FAIL" for f in found)
    return G.row(gate, False, f"{len(found)} finding(s); first: {found[0].get('where')}: {str(found[0].get('detail'))[:140]}",
                 [f.get("where") for f in found[:20]], level=G.FAIL if hard else G.REVIEW)


def v4_as_segments(script: dict) -> dict:
    """The v4 script in the segment model ``scene_lint.immersion_and_showing`` reads: ``segments[].lines[]`` with ``speaker`` set for
    character lines, plus a ``cast`` of the world bible's names."""
    by = {}
    for ln in script.get("audio_lines") or []:
        by.setdefault(ln.get("segment_id"), []).append({"text": ln.get("text", ""), "speaker": None if _narrator(ln) else ln.get("speaker_id")})
    cast = {c.get("character_id"): {"names": [n for n in (c.get("name"), c.get("display_name")) if n]}
            for c in (script.get("world_bible") or {}).get("characters", []) if c.get("character_id")}
    return {"segments": [{"id": sid, "lines": lines, "shots": []} for sid, lines in by.items()], "cast": cast}


def immersion_and_showing(script: dict) -> list[dict]:
    """SC-11 (full immersion, BP-88) and SC-12 (show, don't tell, BP-87) on a v4 script, through the one lexicon of ``scene_lint``."""
    found = scene_lint.immersion_and_showing(v4_as_segments(script))
    return [_findings_row("SC-11", [f for f in found if f["rule"] == "SC-11"], "no line steps outside the story or hedges it"),
            _findings_row("SC-12", [f for f in found if f["rule"] == "SC-12"], "no narrator line states a trait or a rating")]


def press_release(script: dict) -> dict:
    """SC-07: no narrator line in press-release register (BP-15's lexicon, the one N-14 uses)."""
    hits = [(ln.get("line_id", "?"), narration_lint.press_release(ln.get("text", ""))) for ln in script.get("audio_lines") or [] if _narrator(ln)]
    hits = [(i, h) for i, h in hits if h]
    return _findings_row("SC-07", [{"where": i, "detail": f"press-release register: {h!r}", "severity": "REVIEW"} for i, h in hits],
                         "no press-release register in the narration")


def turn_length(script: dict) -> list[dict]:
    """SC-09: a character turn is at most BP-72's turn_words_max (BP-72's severity) and at most BP-73's turn_words_review (REVIEW)."""
    cap, review = C.T("BP-72", "turn_words_max"), C.T("BP-73", "turn_words_review")
    if cap is None or review is None:
        return [C.missing_threshold("SC-09", "BP-72/BP-73", "turn_words_max/turn_words_review")]
    rows = []
    for ln in script.get("audio_lines") or []:
        if _narrator(ln):
            continue
        n = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", ln.get("text", "")))
        gate = f"SC-09:{ln.get('line_id', '?')}"
        if n > cap:
            rows.append(G.row(gate, False, f"a {n}-word turn; cap {cap} (BP-72)", n, level=C.level("BP-72")))
        else:
            rows.append(G.row(gate, n <= review, f"{n} words in one turn (default up to {review}, BP-73)", n, level=G.REVIEW))
    return rows or [G.row("SC-09", None, "NOT_RUN: no character line")]


def value_charge_cadence(segments: list[dict]) -> dict:
    """VAL-STO-01: the value charge (``charge`` or ``value_charge``: -1, 0, +1 on a segment of the script's skeleton; not on shot cards) flips at least once every
    ``story_lint.proportional_turn_gap_s`` seconds (BP-76's cadence, hypothesis: REVIEW). A segment without a charge makes the row NOT_RUN, never PASS."""
    charged = [(float(s.get("target_duration_seconds") or s.get("duration_s") or 0.0), s.get("charge", s.get("value_charge"))) for s in segments]
    if not charged or any(c is None for _, c in charged):
        return G.row("VAL-STO-01", None, "NOT_RUN: the script's segment skeleton carries no value charge (shot cards do not and should not)")
    total = sum(d for d, _ in charged)
    gap = story_lint.proportional_turn_gap_s(total)
    t, last_flip, prev, worst = 0.0, 0.0, None, 0.0
    for d, c in charged:
        if prev is not None and c != prev:
            worst, last_flip = max(worst, t - last_flip), t
        prev, t = c, t + d
    worst = max(worst, t - last_flip)
    return C.check("VAL-STO-01", worst <= gap, "BP-76", f"longest stretch without a charge flip {worst:.1f} s; at most {gap:.1f} s", worst)


def scene_headers(scenes: list[dict]) -> list[dict]:
    """VAL-STO-02: every scene header names what each side wants (``wants`` with two non-empty entries) and its ``turn``."""
    rows = []
    for s in scenes:
        wants = s.get("wants") or {}
        ok = len([v for v in wants.values() if str(v or "").strip()]) >= 2 and bool(str(s.get("turn") or "").strip())
        rows.append(C.check(f"VAL-STO-02:{s.get('scene_id', '?')}", ok, "SC-03", "both sides want something and the scene turns" if ok else
                            "the scene header lacks two opposing wants or a turn"))
    return rows or [G.row("VAL-STO-02", None, "NOT_RUN: no scene header")]


def stronger_than_claim(script: dict, claim_map: dict[str, dict]) -> list[dict]:
    """VAL-STO-03: a narrator line that uses an absolute word of BP-213 (everyone, always, never ...) while no claim it cites uses that
    word says more than its claim. Lines with no claim id are skipped (PV-37 owns those)."""
    words = C.T("BP-213", "absolute_words")
    if words is None:
        return [C.missing_threshold("VAL-STO-03", "BP-213", "absolute_words")]
    rx = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in words) + r")(?![\w-])", re.I)
    rows = []
    for ln in script.get("audio_lines") or []:
        ids = ln.get("citation_ids") or ln.get("claims") or []
        if not _narrator(ln) or not ids:
            continue
        said = {m.lower() for m in rx.findall(ln.get("text", ""))}
        backed = {m.lower() for i in ids for m in rx.findall((claim_map.get(i) or {}).get("sentence", ""))}
        over = sorted(said - backed)
        rows.append(C.check(f"VAL-STO-03:{ln.get('line_id', '?')}", not over, "BP-213",
                            f"the line says {over} but its claim(s) {ids} do not" if over else "no word stronger than its claim", over))
    return rows or [G.row("VAL-STO-03", None, "NOT_RUN: no narrator line cites a claim")]


def numeric_claim_sources(claim_map: dict[str, dict]) -> list[dict]:
    """VAL-STO-04: a claim whose sentence holds a number names at least ``numeric_claim_sources_min`` distinct source links."""
    need = C.T("BP-213", "numeric_claim_sources_min")
    if need is None:
        return [C.missing_threshold("VAL-STO-04", "BP-213", "numeric_claim_sources_min")]
    rows = []
    for cid, c in sorted(claim_map.items()):
        if not _NUMBER.search(c.get("sentence", "")):
            continue
        n = len(set(_URL.findall(c.get("source", ""))))
        rows.append(C.check(f"VAL-STO-04:{cid}", n >= need, "BP-213", f"{n} source link(s) for a numeric claim (at least {need})", n))
    return rows or [G.row("VAL-STO-04", None, "NOT_RUN: no numeric claim in the map")]


def validate(script: dict, *, claim_map: dict[str, dict] | None = None, scenes: list[dict] | None = None) -> list[dict]:
    rows = [press_release(script), *turn_length(script), *immersion_and_showing(script), value_charge_cadence(script.get("segments") or [])]
    rows += scene_headers(scenes) if scenes is not None else [G.row("VAL-STO-02", None, "NOT_RUN: no scene headers given")]
    if claim_map is None:
        rows += [G.row("VAL-STO-03", None, "NOT_RUN: no claim map"), G.row("VAL-STO-04", None, "NOT_RUN: no claim map")]
    else:
        rows += [*stronger_than_claim(script, claim_map), *numeric_claim_sources(claim_map)]
    return rows
