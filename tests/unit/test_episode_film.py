from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest

from explainer_engine.episode_film import (
    BLOCKS,
    EpisodeFilmError,
    SCHEMA,
    block,
    check_film_ids,
    film_id,
    load_episode_film,
    validate_episode_film,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "episode_film"


@pytest.fixture
def valid_film() -> dict:
    with (FIXTURES_DIR / "valid_film.json").open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Acceptance Test 1: Valid film, validate_episode_film, block copy, film_id
# ---------------------------------------------------------------------------

def test_valid_film_validates_and_block_returns_copy(valid_film: dict) -> None:
    assert validate_episode_film(valid_film) == []
    assert film_id(valid_film) == "owner_film_01"

    for block_name in BLOCKS:
        original_block = valid_film[block_name]
        copied_block = block(valid_film, block_name)
        assert copied_block == original_block
        assert copied_block is not original_block

    # Verify deep-copy isolation on nested lists
    dir_copy = block(valid_film, "direction")
    dir_copy["notes"].append("mutated note")
    assert "mutated note" not in valid_film["direction"]["notes"]


def test_film_id_negative_raises_on_missing_or_empty() -> None:
    with pytest.raises((EpisodeFilmError, KeyError, ValueError)):
        film_id({})

    with pytest.raises((EpisodeFilmError, KeyError, ValueError)):
        film_id({"film_id": ""})


# ---------------------------------------------------------------------------
# Acceptance Test 2: Single-problem validation cases (each -> len == 1)
# ---------------------------------------------------------------------------

def test_missing_block_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    del film["picture"]
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "picture" in problems[0]


def test_empty_string_leaf_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["picture"]["era_look"] = ""
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "era_look" in problems[0]


def test_empty_notes_list_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["direction"]["notes"] = []
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "notes" in problems[0]


def test_unknown_top_level_key_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["unexpected_top_key"] = "some_value"
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "unexpected_top_key" in problems[0]


def test_wrong_schema_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["schema"] = "episode_film/999"
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert SCHEMA in problems[0] or "schema" in problems[0].lower()


def test_film_id_with_space_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["film_id"] = "owner film_01"
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "film_id" in problems[0]


def test_film_id_with_capital_letter_produces_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["film_id"] = "Owner_film_01"
    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "film_id" in problems[0]


# ---------------------------------------------------------------------------
# Acceptance Test 3: map.style_preset != counter.style_preset
# ---------------------------------------------------------------------------

def test_mismatched_style_presets_names_both_values(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["map"]["style_preset"] = "test_preset_alpha"
    film["counter"]["style_preset"] = "test_preset_beta"

    problems = validate_episode_film(film)
    assert len(problems) == 1
    assert "test_preset_alpha" in problems[0]
    assert "test_preset_beta" in problems[0]


# ---------------------------------------------------------------------------
# Acceptance Test 4: check_film_ids status transitions
# ---------------------------------------------------------------------------

def test_check_film_ids_all_match_returns_pass(valid_film: dict) -> None:
    records = [
        {"record_id": "rec_1", "film_id": "owner_film_01"},
        {"record_id": "rec_2", "film_id": "owner_film_01"},
        {"record_id": "rec_3", "film_id": "owner_film_01"},
    ]
    result = check_film_ids(valid_film, records)
    assert result["status"] == "PASS"
    assert result["value"] == 3
    assert isinstance(result["detail"], str)


def test_check_film_ids_one_wrong_returns_fail(valid_film: dict) -> None:
    records = [
        {"record_id": "rec_1", "film_id": "owner_film_01"},
        {"record_id": "rec_2", "film_id": "wrong_film_99"},
    ]
    result = check_film_ids(valid_film, records)
    assert result["status"] == "FAIL"
    assert "wrong_film_99" in result["detail"]


def test_check_film_ids_missing_key_returns_not_run(valid_film: dict) -> None:
    records = [
        {"record_id": "rec_1"},
    ]
    result = check_film_ids(valid_film, records)
    assert result["status"] == "NOT_RUN"
    assert isinstance(result["detail"], str)


def test_check_film_ids_one_wrong_and_one_missing_returns_fail(valid_film: dict) -> None:
    records = [
        {"record_id": "rec_1", "film_id": "wrong_film_99"},
        {"record_id": "rec_2"},
    ]
    result = check_film_ids(valid_film, records)
    assert result["status"] == "FAIL"
    assert "wrong_film_99" in result["detail"]


def test_check_film_ids_empty_records_returns_not_run(valid_film: dict) -> None:
    result = check_film_ids(valid_film, [])
    assert result["status"] == "NOT_RUN"
    assert isinstance(result["detail"], str)


# ---------------------------------------------------------------------------
# Acceptance Test 5: load_episode_film positive & negative (fixture files)
# ---------------------------------------------------------------------------

def test_load_episode_film_valid_fixture(valid_film: dict) -> None:
    loaded = load_episode_film(str(FIXTURES_DIR / "valid_film.json"))
    assert loaded == valid_film


def test_load_episode_film_multiple_problems_raises_with_all_problems() -> None:
    bad_path = FIXTURES_DIR / "multiple_problems.json"
    raw_bad_film = json.loads(bad_path.read_text(encoding="utf-8"))
    expected_problems = validate_episode_film(raw_bad_film)
    assert len(expected_problems) >= 2

    with pytest.raises(EpisodeFilmError) as exc_info:
        load_episode_film(str(bad_path))

    error_message = str(exc_info.value)
    for problem in expected_problems:
        assert problem in error_message


def test_load_episode_film_invalid_json_raises_error() -> None:
    invalid_json_path = FIXTURES_DIR / "invalid_json.json"
    with pytest.raises(EpisodeFilmError):
        load_episode_film(str(invalid_json_path))


# ---------------------------------------------------------------------------
# Acceptance Test 6: block(film, "nope") & missing block in valid dict
# ---------------------------------------------------------------------------

def test_block_unknown_name_raises_episode_film_error(valid_film: dict) -> None:
    with pytest.raises(EpisodeFilmError):
        block(valid_film, "nope")


def test_block_missing_known_block_raises_episode_film_error(valid_film: dict) -> None:
    incomplete_film = copy.deepcopy(valid_film)
    del incomplete_film["narration"]
    with pytest.raises(EpisodeFilmError):
        block(incomplete_film, "narration")


# ---- added by the reviewing thread (the original tests above are untouched) ----
def test_blank_note_item_is_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["narration"]["notes"] = ["fine", "  "]
    problems = validate_episode_film(film)
    assert len(problems) == 1 and "narration.notes" in problems[0]


def test_required_key_of_wrong_type_is_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    film["subtitles"]["font"] = 12
    problems = validate_episode_film(film)
    assert len(problems) == 1 and "subtitles.font" in problems[0]


def test_missing_required_key_in_a_block_is_one_problem(valid_film: dict) -> None:
    film = copy.deepcopy(valid_film)
    del film["subtitles"]["position"]
    problems = validate_episode_film(film)
    assert len(problems) == 1 and "subtitles.position" in problems[0]


def test_check_film_ids_names_layer_where_and_at_most_three(valid_film: dict) -> None:
    recs = [{"layer": f"L{i}", "where": f"w{i}", "film_id": f"bad_{i}"} for i in range(5)]
    result = check_film_ids(valid_film, recs)
    assert result["status"] == "FAIL" and result["value"] == 5
    assert "L0" in result["detail"] and "w0" in result["detail"] and "bad_0" in result["detail"] and "bad_3" not in result["detail"]


def test_inputs_are_not_mutated(valid_film: dict) -> None:
    before = copy.deepcopy(valid_film)
    validate_episode_film(valid_film); block(valid_film, "map"); film_id(valid_film)
    check_film_ids(valid_film, [{"film_id": "owner_film_01"}])
    assert valid_film == before
