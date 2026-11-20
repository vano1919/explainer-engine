"""Lint of a video-model (LTX) prompt, G-07: one paragraph, short, starts with the action, no forbidden camera words,
names the hero, and carries the episode's film id.

Sources (lead, 2026-11-20): the LTX-2 README ("single flowing paragraph ... start directly with the action ... literal and
precise ... keep within 200 words"; one source type, so every threshold here is a hypothesis) and the owner's camera
decision (per shot one of five moves: truck, zoom_in, zoom_out, truck_zoom_in, truck_zoom_out; orbit and static are
forbidden, the camera never stops, OR-V24). The numbers and word lists live only in ``ltx_prompt_tolerances.json``
(``ltx_prompt_tolerances/1``); this module copies none. Text-level heuristics: they read words, not meaning.

    findings = lint_ltx_prompt(prompt, hero_name="Anna", film_id="owner_film_01", pack_film_id="owner_film_01")

Findings are ``{rule, severity, where, detail}`` with severity FAIL or REVIEW; ``where`` is the character offset (int) for
LP-04 and the string ``"prompt"`` otherwise. The film id check is a plain string comparison (``check_prompt_film``); the
G-05 reader is not needed for it. Pure: reads only the tolerances JSON, never mutates its inputs, no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = "ltx_prompt_tolerances/1"
DEFAULT_TOLERANCES = Path(__file__).with_name("ltx_prompt_tolerances.json")
HYPOTHESIS_NOTE = "(hypothesis, not binding until the owner has seen it)"


def _load_tolerances(path: str | Path | None) -> dict:
    """Read and check the tolerances file; a missing key or a wrong type raises ValueError naming the key."""
    p = Path(path) if path is not None else DEFAULT_TOLERANCES
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"tolerances file {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("tolerances: the root must be an object")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"tolerances: schema must be {SCHEMA!r}")
    mw = data.get("max_words")
    if not isinstance(mw, dict) or "value" not in mw:
        raise ValueError("tolerances: max_words must be an object with a value")
    if isinstance(mw["value"], bool) or not isinstance(mw["value"], int) or mw["value"] < 1:
        raise ValueError("tolerances: max_words.value must be a positive integer")
    for key in ("non_action_openers", "forbidden_camera_phrases"):
        v = data.get(key)
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
            raise ValueError(f"tolerances: {key} must be a non-empty list of non-empty strings")
    return data


def check_prompt_film(film_id: str, pack_film_id: str | None) -> dict:
    """Equal PASS, different FAIL, no pack film id NOT_RUN (nothing measured is never approved)."""
    if not isinstance(film_id, str) or not film_id.strip():
        return {"status": "NOT_RUN", "value": None, "detail": "no film_id to compare"}
    if pack_film_id is None or (isinstance(pack_film_id, str) and not pack_film_id.strip()):
        return {"status": "NOT_RUN", "value": None, "detail": "the pack carries no film_id: nothing to compare"}
    if pack_film_id == film_id:
        return {"status": "PASS", "value": 1, "detail": f"prompt film_id {film_id!r} equals the pack's"}
    return {"status": "FAIL", "value": 0,
            "detail": f"film_id mismatch: prompt {film_id!r}, pack {pack_film_id!r}"}


def _phrase_matches(prompt: str, phrase: str) -> list[int]:
    """Character offsets of a whole-word, case-insensitive phrase ('dolly' matches, 'dollying' does not)."""
    rx = re.compile(r"(?<!\w)" + re.escape(phrase.strip()) + r"(?!\w)", re.IGNORECASE)
    return [m.start() for m in rx.finditer(prompt)]


def lint_ltx_prompt(prompt: str, *, hero_name: str, film_id: str | None, pack_film_id: str | None,
                    tolerances_path: str | None = None) -> list[dict]:
    """Findings ``[{rule, severity, where, detail}]``; ``[]`` when clean. A non-string prompt raises TypeError."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")
    if not isinstance(hero_name, str):
        raise TypeError("hero_name must be a string")
    tol = _load_tolerances(tolerances_path)
    out: list[dict] = []

    def add(rule: str, severity: str, where, detail: str) -> None:
        out.append({"rule": rule, "severity": severity, "where": where, "detail": detail})

    text = prompt.strip()
    if not text:
        return [{"rule": "LP-00", "severity": "FAIL", "where": "prompt", "detail": "the prompt is empty"}]

    if "\n" in text or "\r" in text:
        add("LP-01", "FAIL", "prompt", "the prompt has a line break or blank line: write one flowing paragraph")

    words = text.split()
    max_words = tol["max_words"]["value"]
    if len(words) > max_words:
        add("LP-02", "FAIL", "prompt", f"{len(words)} words, more than max_words {max_words} {HYPOTHESIS_NOTE}")

    first = re.sub(r"^\W+|\W+$", "", words[0]).lower()
    if first in {w.strip().lower() for w in tol["non_action_openers"]}:
        add("LP-03", "REVIEW", "prompt", f"the prompt opens with {words[0]!r}, not an action: start directly with "
                                         f"the action {HYPOTHESIS_NOTE}")

    hits: list[tuple[int, str]] = []
    for phrase in tol["forbidden_camera_phrases"]:
        hits += [(off, phrase) for off in _phrase_matches(text, phrase)]
    for off, phrase in sorted(hits):
        add("LP-04", "REVIEW", off, f"forbidden camera phrase {phrase!r} at character offset {off}: the camera moves "
                                    "by one of the five moves only, never orbits and never stops (owner's camera decision)")

    if not hero_name.strip() or hero_name.strip().lower() not in text.lower():
        add("LP-05", "REVIEW", "prompt", f"the hero {hero_name!r} is not named in the prompt")

    if film_id is not None:
        film = check_prompt_film(film_id, pack_film_id)
        if film["status"] == "FAIL":
            add("LP-06", "FAIL", "prompt", film["detail"])
    return out
