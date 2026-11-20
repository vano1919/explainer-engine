"""Validate voice cast consistency across characters and video prompts.

Requirement IDs:
  - OR-A13: Every speaking character has an own voice, by personality.
  - OR-A20: One four-facet voice description per character, copied unchanged into every video prompt.
  - OR-A11 + OR-A21: A real person gets a type-matched voice, never a clone, a soundalike, their accent or cadence; no paid samples.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any

FACETS = ("age", "gender", "accent", "temperament")
_ALLOWED_VOICE_SOURCES = frozenset({"library", "designed", "clone", "soundalike"})

@dataclass(frozen=True)
class Limits:
    """Threshold and policy configuration for voice cast validation."""

    shared_ok: frozenset[str] = frozenset({"narrator"})
    banned_sources: frozenset[str] = frozenset({"clone", "soundalike"})
    severity: str = "REVIEW"

def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces and strip leading/trailing whitespace."""
    return " ".join(text.split())

def _validate_limits(limits: Limits) -> None:
    """Ensure Limits has valid field types."""
    if not isinstance(limits, Limits):
        raise ValueError("limits must be a Limits instance.")
    if not isinstance(limits.shared_ok, (frozenset, set, tuple, list)):
        raise ValueError("limits.shared_ok must be a collection of strings.")
    if any(not isinstance(item, str) for item in limits.shared_ok):
        raise ValueError("limits.shared_ok entries must be strings.")
    if not isinstance(limits.banned_sources, (frozenset, set, tuple, list)):
        raise ValueError("limits.banned_sources must be a collection of strings.")
    if any(not isinstance(item, str) for item in limits.banned_sources):
        raise ValueError("limits.banned_sources entries must be strings.")
    if not isinstance(limits.severity, str) or not limits.severity.strip():
        raise ValueError("limits.severity must be a non-empty string.")

def _validate_cast_entry(character_id: Any, entry: Any) -> dict[str, Any]:
    """Validate structure and field types of a single character entry in cast."""
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("cast keys must be non-empty strings.")
    if not isinstance(entry, dict):
        raise ValueError(f"cast['{character_id}'] must be a dict.")

    required_keys = ("speaking", "voice_id", "voice_text", "facets", "real_person", "voice_source")
    for key in required_keys:
        if key not in entry:
            raise ValueError(f"cast['{character_id}'] is missing required key '{key}'.")

    speaking = entry["speaking"]
    if not isinstance(speaking, bool):
        raise ValueError(f"cast['{character_id}']['speaking'] must be a bool.")

    voice_id = entry["voice_id"]
    if voice_id is not None and not isinstance(voice_id, str):
        raise ValueError(f"cast['{character_id}']['voice_id'] must be a str or None.")

    voice_text = entry["voice_text"]
    if not isinstance(voice_text, str):
        raise ValueError(f"cast['{character_id}']['voice_text'] must be a str.")

    facets = entry["facets"]
    if not isinstance(facets, dict):
        raise ValueError(f"cast['{character_id}']['facets'] must be a dict.")
    for k, v in facets.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError(f"cast['{character_id}']['facets'] keys and values must be strings.")

    real_person = entry["real_person"]
    if not isinstance(real_person, bool):
        raise ValueError(f"cast['{character_id}']['real_person'] must be a bool.")

    voice_source = entry["voice_source"]
    if not isinstance(voice_source, str) or voice_source not in _ALLOWED_VOICE_SOURCES:
        raise ValueError(
            f"cast['{character_id}']['voice_source'] must be one of {sorted(_ALLOWED_VOICE_SOURCES)}."
        )

    return {
        "speaking": speaking,
        "voice_id": voice_id,
        "voice_text": voice_text,
        "facets": dict(facets),
        "real_person": real_person,
        "voice_source": voice_source,
    }

def _validate_prompt_entry(index: int, prompt: Any) -> dict[str, str]:
    """Validate structure and field types of a single video prompt entry."""
    if not isinstance(prompt, dict):
        raise ValueError(f"prompts[{index}] must be a dict.")

    for key in ("shot_id", "character", "voice_text"):
        if key not in prompt:
            raise ValueError(f"prompts[{index}] is missing required key '{key}'.")
        if not isinstance(prompt[key], str):
            raise ValueError(f"prompts[{index}]['{key}'] must be a str.")
        if key in ("shot_id", "character") and not prompt[key].strip():
            raise ValueError(f"prompts[{index}]['{key}'] must be a non-empty string.")

    return {
        "shot_id": prompt["shot_id"],
        "character": prompt["character"],
        "voice_text": prompt["voice_text"],
    }

def check(cast: dict[str, dict], prompts: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Validate cast entries and prompt voice descriptions against casting rules.

    Rules checked:
    - CAST-01: two speaking characters (neither in shared_ok) share a non-empty voice_id
    - CAST-02: a speaking character has no voice_id (None or empty/blank)
    - CAST-03: a prompt's voice_text differs from its character's cast voice_text after whitespace normalization
    - CAST-04: real_person is True and voice_source is in banned_sources
    - CAST-05: a speaking character's facets lack any FACETS key/value or a facet value is missing from voice_text
    - CAST-06: a prompt names a character not present in cast
    """
    _validate_limits(limits)

    if not isinstance(cast, dict):
        raise ValueError("cast must be a dict mapping character_id to cast metadata.")
    if not isinstance(prompts, list):
        raise ValueError("prompts must be a list of dicts.")

    parsed_cast: dict[str, dict[str, Any]] = {}
    for char_id, entry in cast.items():
        parsed_cast[char_id] = _validate_cast_entry(char_id, entry)

    parsed_prompts = [_validate_prompt_entry(idx, prompt) for idx, prompt in enumerate(prompts)]

    if not parsed_cast and not parsed_prompts:
        return []

    shared_ok = frozenset(limits.shared_ok)
    banned_sources = frozenset(limits.banned_sources)

    sortable_findings: list[tuple[str, str, dict[str, str]]] = []
    voice_id_to_chars: dict[str, list[str]] = defaultdict(list)

    for char_id in sorted(parsed_cast):
        entry = parsed_cast[char_id]
        speaking = entry["speaking"]
        voice_id = entry["voice_id"]
        voice_text = entry["voice_text"]
        facets = entry["facets"]
        real_person = entry["real_person"]
        voice_source = entry["voice_source"]

        clean_voice_id = voice_id.strip() if isinstance(voice_id, str) else ""

        if speaking:
            # CAST-02: speaking character has no voice_id (None or empty)
            if not clean_voice_id:
                sortable_findings.append(
                    (
                        char_id,
                        "CAST-02",
                        {
                            "rule": "CAST-02",
                            "severity": limits.severity,
                            "where": char_id,
                            "detail": f"Speaking character '{char_id}' has no assigned voice_id.",
                        },
                    )
                )
            elif char_id not in shared_ok:
                voice_id_to_chars[clean_voice_id].append(char_id)

            # CAST-05: speaking character's facets must include all FACETS and appear in voice_text
            voice_text_lower = voice_text.lower()
            missing_facets: list[str] = []
            unmatched_facets: list[str] = []

            for facet in FACETS:
                raw_val = facets.get(facet)
                if raw_val is None or not raw_val.strip():
                    missing_facets.append(facet)
                elif raw_val.strip().lower() not in voice_text_lower:
                    unmatched_facets.append(f"{facet}='{raw_val.strip()}'")

            if missing_facets or unmatched_facets:
                parts: list[str] = []
                if missing_facets:
                    parts.append(f"missing or blank facets ({', '.join(missing_facets)})")
                if unmatched_facets:
                    parts.append(f"facets absent from voice_text ({', '.join(unmatched_facets)})")
                sortable_findings.append(
                    (
                        char_id,
                        "CAST-05",
                        {
                            "rule": "CAST-05",
                            "severity": limits.severity,
                            "where": char_id,
                            "detail": f"Speaking character '{char_id}' has {'; '.join(parts)}.",
                        },
                    )
                )

        # CAST-04: real_person is True and voice_source is in banned_sources
        if real_person and voice_source in banned_sources:
            sortable_findings.append(
                (
                    char_id,
                    "CAST-04",
                    {
                        "rule": "CAST-04",
                        "severity": limits.severity,
                        "where": char_id,
                        "detail": f"Real-person character '{char_id}' uses banned voice_source '{voice_source}'.",
                    },
                )
            )

    # CAST-01: two speaking characters (neither in shared_ok) share a non-empty voice_id
    for shared_voice_id, char_ids in sorted(voice_id_to_chars.items()):
        if len(char_ids) > 1:
            for char_a, char_b in combinations(sorted(char_ids), 2):
                pair_where = f"{char_a}|{char_b}"
                sortable_findings.append(
                    (
                        pair_where,
                        "CAST-01",
                        {
                            "rule": "CAST-01",
                            "severity": limits.severity,
                            "where": pair_where,
                            "detail": (
                                f"Speaking characters '{char_a}' and '{char_b}' share voice_id '{shared_voice_id}'."
                            ),
                        },
                    )
                )

    # Prompt checks: CAST-06 and CAST-03
    for prompt in parsed_prompts:
        shot_id = prompt["shot_id"]
        char_id = prompt["character"]
        where_label = f"{shot_id}/{char_id}"

        if char_id not in parsed_cast:
            sortable_findings.append(
                (
                    where_label,
                    "CAST-06",
                    {
                        "rule": "CAST-06",
                        "severity": limits.severity,
                        "where": where_label,
                        "detail": f"Prompt in shot '{shot_id}' references unknown character '{char_id}'.",
                    },
                )
            )
            continue

        expected_text = _normalize_whitespace(parsed_cast[char_id]["voice_text"])
        actual_text = _normalize_whitespace(prompt["voice_text"])

        if actual_text != expected_text:
            sortable_findings.append(
                (
                    where_label,
                    "CAST-03",
                    {
                        "rule": "CAST-03",
                        "severity": limits.severity,
                        "where": where_label,
                        "detail": (
                            f"Prompt voice_text for '{char_id}' in shot '{shot_id}' differs from cast voice_text."
                        ),
                    },
                )
            )

    sortable_findings.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in sortable_findings]
