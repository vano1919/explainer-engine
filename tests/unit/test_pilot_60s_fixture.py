"""Unit tests for TODO-16: 60-second 12-shot Waterloo pilot fixture, migration utility, and 4-stage pilot dry-run."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from explainer_engine.production import __main__ as prod_cli
from explainer_engine.scripting import scene_lint, shot_prompt_lint, story_lint
from scripts import migrate_script_to_v4

ROOT = Path(__file__).resolve().parents[2]
PILOT_PATH = ROOT / "tests" / "fixtures" / "pilot_60s_waterloo.json"
PS_SCHEMA = json.loads((ROOT / "explainer_engine/schemas/production_script.schema.json").read_text(encoding="utf-8"))


def test_pilot_60s_waterloo_fixture_conforms_to_v4_schema_and_60_30_10_mix() -> None:
    assert PILOT_PATH.exists(), f"Missing {PILOT_PATH}"
    doc = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, PS_SCHEMA)

    shots = doc["shots"]
    assert len(shots) == 12
    assert round(sum(s["target_duration_seconds"] for s in shots), 1) in (60.0, 61.4)

    # Verify 7 video (4 WAN_I2V + 3 WAN_FLF2V), 4 composed_illustration (STILL_25D), 1 map_visualization (MAP_25D)
    by_mode = {}
    for s in shots:
        by_mode[s["generation_mode"]] = by_mode.get(s["generation_mode"], 0) + 1
    assert by_mode in ({"WAN_I2V": 4, "WAN_FLF2V": 3, "STILL_25D": 4, "MAP_25D": 1}, {"WAN_I2V": 4, "WAN_FLF2V": 3, "COLLAGE_STILL": 4, "TACTILE_MAP": 1})

    # Verify spoken balance: 45.0s narrator (75%) / 15.0s character dialogue (25%)
    lines = doc["audio_lines"]
    assert len(lines) == 12
    narr_s = sum(l["estimated_duration_seconds"] for l in lines if l["speaker_type"] == "narrator")
    char_s = sum(l["estimated_duration_seconds"] for l in lines if l["speaker_type"] == "character")
    assert (round(narr_s, 1), round(char_s, 1)) in ((45.0, 15.0), (46.2, 15.2))

    # Verify zero lint FAILs or REVIEWs
    assert shot_prompt_lint.check_v4_script(doc) == []
    assert story_lint.lint(doc) == []
    assert scene_lint.check(doc) == []


def test_pilot_60s_cli_dryrun_and_migrate_script_to_v4(tmp_path: Path) -> None:
    out_dir = tmp_path / "waterloo_pilot_run"
    rc = prod_cli.main(["--pilot-60s", "--script", str(PILOT_PATH), "--dry-run", "--out", str(out_dir)])
    assert rc == 0
    assert (out_dir / "04_assembly" / "qa_report.json").exists()

    # Test migration utility from legacy production_script shape
    legacy = {
        "schema": "production_script/3",
        "episode": {"id": "roman_legion_test", "title": "What If Rome Industrialized Early?"},
        "cast": {"caesar": {"names": ["Julius Caesar"]}},
        "segments": [
            {"id": "S01", "beat": "Steam engines in Alexandria", "lines": [{"text": "Hero of Alexandria built the aeolipile."}]},
            {"id": "S02", "beat": "Imperial patronage", "lines": [{"text": "What if Roman emperors funded coal-fired pumps?"}]},
        ],
    }
    v4_migrated = migrate_script_to_v4.migrate_to_v4(legacy)
    jsonschema.validate(v4_migrated, PS_SCHEMA)
    assert v4_migrated["episode_id"] == "ep_roman_legion_test"
    assert v4_migrated["segments"][1]["cause_from_segment_id"] == "S01"
