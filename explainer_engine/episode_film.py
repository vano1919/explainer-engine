"""Single reader and validator for episode_film.json across all production layers."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "episode_film/1"
BLOCKS = ("picture", "map", "counter", "colour", "subtitles", "direction", "narration")

_TOP_LEVEL_KEYS = frozenset({"schema", "film_id", "film_name", "era", *BLOCKS})
_BLOCK_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "picture": ("era_look", "grade_words"),
    "map": ("style_preset", "font"),
    "counter": ("style_preset",),
    "colour": ("targets",),
    "subtitles": ("font", "colour", "position"),
    "direction": ("notes",),
    "narration": ("notes",),
}
_NOTE_BLOCKS = frozenset({"direction", "narration"})
_FILM_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


class EpisodeFilmError(ValueError):
    """Raised when an episode_film.json file or block lookup is invalid."""


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_leaf_strings(value: Any, prefix: str, problems: list[str]) -> None:
    if isinstance(value, str):
        if not value.strip():
            problems.append(f"{prefix}: string value must be non-empty after strip")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _check_leaf_strings(item, f"{prefix}.{key}", problems)
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _check_leaf_strings(item, f"{prefix}[{idx}]", problems)


def validate_episode_film(film: dict) -> list[str]:
    """Validate an episode_film dictionary and return a list of problems ([] when valid)."""
    if not isinstance(film, dict):
        return ["film must be a dict"]

    problems: list[str] = []

    unknown_top = sorted(k for k in film if k not in _TOP_LEVEL_KEYS)
    if unknown_top:
        problems.append(f"unknown top-level keys: {', '.join(unknown_top)}")

    schema_val = film.get("schema")
    if not isinstance(schema_val, str) or schema_val != SCHEMA:
        problems.append(f"schema must equal {SCHEMA!r}, got {schema_val!r}")

    raw_film_id = film.get("film_id")
    if not isinstance(raw_film_id, str) or not _FILM_ID_PATTERN.fullmatch(raw_film_id):
        problems.append(f"film_id must match [a-z0-9_]+, got {raw_film_id!r}")

    for field in ("film_name", "era"):
        if not _is_non_empty_str(film.get(field)):
            problems.append(f"{field} must be a non-empty string")

    valid_blocks: dict[str, dict[str, Any]] = {}
    for block_name in BLOCKS:
        if block_name not in film:
            problems.append(f"missing required block: {block_name}")
            continue
        block_val = film[block_name]
        if not isinstance(block_val, dict):
            problems.append(f"block {block_name!r} must be a dict")
            continue
        valid_blocks[block_name] = block_val

        for req_key in _BLOCK_REQUIRED_KEYS[block_name]:
            if req_key not in block_val:
                problems.append(f"{block_name}.{req_key} is required")

        if block_name in _NOTE_BLOCKS:
            if "notes" in block_val:
                notes_val = block_val["notes"]
                if (
                    not isinstance(notes_val, list)
                    or len(notes_val) == 0
                    or not all(_is_non_empty_str(item) for item in notes_val)
                ):
                    problems.append(f"{block_name}.notes must be a non-empty list of non-empty strings")
        else:
            for req_key in _BLOCK_REQUIRED_KEYS[block_name]:
                # an empty/blank string is reported once by the leaf check below; here only a wrong TYPE
                if req_key in block_val and not isinstance(block_val[req_key], str):
                    problems.append(f"{block_name}.{req_key} must be a non-empty string")

        # the notes of direction/narration have their own check above: never count their items twice
        _check_leaf_strings(
            {k: v for k, v in block_val.items() if not (block_name in _NOTE_BLOCKS and k == "notes")},
            block_name,
            problems,
        )

    map_block = valid_blocks.get("map")
    counter_block = valid_blocks.get("counter")
    if map_block is not None and counter_block is not None:
        map_preset = map_block.get("style_preset")
        counter_preset = counter_block.get("style_preset")
        if (
            _is_non_empty_str(map_preset)
            and _is_non_empty_str(counter_preset)
            and map_preset != counter_preset
        ):
            problems.append(
                f"map.style_preset ({map_preset!r}) must equal counter.style_preset ({counter_preset!r})"
            )

    return problems


def load_episode_film(path: str) -> dict:
    """Read an episode_film.json file, validate it, and return a defensive copy."""
    file_path = Path(path)
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EpisodeFilmError(f"Cannot read episode film at {path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise EpisodeFilmError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise EpisodeFilmError(f"Episode film root in {path} must be a JSON object")

    problems = validate_episode_film(data)
    if problems:
        raise EpisodeFilmError(f"Invalid episode film in {path}: {'; '.join(problems)}")

    return copy.deepcopy(data)


def block(film: dict, name: str) -> dict:
    """Return a deep copy of the requested film block, or raise EpisodeFilmError."""
    if name not in BLOCKS:
        raise EpisodeFilmError(f"Unknown block name: {name!r}")
    if not isinstance(film, dict) or name not in film:
        raise EpisodeFilmError(f"Missing block: {name!r}")
    block_val = film[name]
    if not isinstance(block_val, dict):
        raise EpisodeFilmError(f"Block {name!r} is not a dict")
    return copy.deepcopy(block_val)


def film_id(film: dict) -> str:
    """Return the validated film_id string from an episode film dict."""
    if not isinstance(film, dict):
        raise EpisodeFilmError("film must be a dict")
    raw_id = film.get("film_id")
    if not isinstance(raw_id, str) or not _FILM_ID_PATTERN.fullmatch(raw_id):
        raise EpisodeFilmError(f"Invalid or missing film_id: {raw_id!r}")
    return raw_id


def check_film_ids(film: dict, records: list[dict]) -> dict:
    """Verify that every record carries the expected film_id."""
    expected_id = film_id(film)

    if not records:
        return {
            "status": "NOT_RUN",
            "value": 0,
            "detail": "records list is empty",
        }

    mismatches: list[str] = []
    missing_or_empty: list[str] = []

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            missing_or_empty.append(f"record[{idx}] is not a dict")
            continue

        layer = rec.get("layer", "<unknown-layer>")
        where = rec.get("where", f"record[{idx}]")

        if "film_id" not in rec:
            missing_or_empty.append(f"{layer} ({where}): missing film_id")
            continue

        rec_id = rec["film_id"]
        if not isinstance(rec_id, str) or not rec_id.strip():
            missing_or_empty.append(f"{layer} ({where}): empty film_id")
            continue

        if rec_id != expected_id:
            mismatches.append(f"{layer} ({where}): {rec_id!r}")

    if mismatches:
        shown = ", ".join(mismatches[:3])
        return {
            "status": "FAIL",
            "value": len(mismatches),
            "detail": f"expected {expected_id!r}, wrong records: {shown}",
        }

    if missing_or_empty:
        return {
            "status": "NOT_RUN",
            "value": len(missing_or_empty),
            "detail": f"missing or empty film_id: {missing_or_empty[0]}",
        }

    return {
        "status": "PASS",
        "value": len(records),
        "detail": f"all {len(records)} records match film_id {expected_id!r}",
    }
