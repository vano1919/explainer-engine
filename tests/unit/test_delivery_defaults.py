"""BP-167 (house, the creator's word of 2026-10-30 16:13 UTC): the animated route's delivery defaults, one registry row, one reader,
a test per default. The still-picture route and the production_script schema default are not changed (TECH_QUESTIONS Q-29..Q-31)."""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.core import delivery, store
from explainer_engine.scripting import film_shots
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_the_row_is_house_and_dated_by_his_word():
    r = SR.rule("BP-167")
    assert r["status"] == "house" and "2026-10-30 16:13 UTC" in r["decided"]
    assert set(r["thresholds"]) == {"long_minutes", "width", "height", "fps", "shorts"}


def test_long_video_is_twelve_minutes_and_the_rhythm_profile_agrees():
    """The creator's 12-minute episode (2026-11-01, WP-3a): BP-167 and BP-169's zone scale are the same 720 s, and the
    variant planner's brief reads it from here instead of its old 900."""
    assert delivery.long_minutes() == 12
    assert SR.T("BP-169", "episode_s") == delivery.long_minutes() * 60
    from explainer_engine.scripting import variant_plan
    assert variant_plan.brief(Path(__file__).resolve().parents[2] / "docs")["episode_runtime_s"] == 720


def test_delivery_size_is_2560_by_1440():
    assert delivery.size() == (2560, 1440)


def test_delivery_fps_is_24_and_matches_the_video_model_and_the_shot_cards():
    assert delivery.fps() == 24 == SR.T("BP-139", "native_fps") == film_shots.FPS


def test_five_shorts():
    assert delivery.shorts() == 5


def test_a_job_without_fps_gets_the_delivery_rate_and_a_named_fps_is_kept(tmp_path):
    a = store.EpisodeJob.create(tmp_path / "a", job_id="job-a", episode_slug="x", ledger="run.json")
    b = store.EpisodeJob.create(tmp_path / "b", job_id="job-b", episode_slug="x", ledger="run.json", fps=30)
    assert a.manifest["fps"] == 24 and b.manifest["fps"] == 30


def test_the_still_route_and_the_schema_default_are_unchanged():
    schema = json.loads((ROOT / "explainer_engine/schemas/production_script.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["episode"]["properties"]["fps"]["default"] == 30
    timing = (ROOT / "explainer_engine/production/timing.py").read_text(encoding="utf-8")
    assert 'doc["episode"].get("fps", 30)' in timing
