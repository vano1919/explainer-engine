"""film_shots/1 and /2 -> film_shots/3 (ICW-02, roadmap 10.3): the migration keeps the BP-109 shares, maps every legacy lane
onto VIDEO_3D / STILL_3D / HELPER (D-97), refuses the lanes the decisions refused (D-89, D-106), writes nothing on a dry run,
and the checked-in dry-run report and the Napoleon example are what the script makes today."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from _napoleon import NAPOLEON, ROOT, _builder, cards_v3, legacy_cards, migration
from explainer_engine.core import contracts as C
from explainer_engine.scripting import film_shots as F
from explainer_engine.standards import sourced_rules as SR

ALL_LANES = ROOT / "tests" / "fixtures" / "migrate_film_shots" / "film_shots_2_all_lanes.json"
FS2 = ROOT / "tests" / "fixtures" / "contracts" / "film_shots_2"
DRY_RUN = ROOT / "docs" / "architecture" / "ICW-02_MIGRATION_DRY_RUN_2026-11-05.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def by_id(doc: dict) -> dict:
    return {s["id"]: s for s in doc["shots"]}


def test_every_legacy_lane_lands_on_one_of_the_three():
    new, report = migration().migrate(load(ALL_LANES), bible_version="1.5")
    C.validate(new)
    assert new["schema"] == "film_shots/3" and new["fps"] == SR.T("BP-167", "fps")
    assert new["style"] == {"house_look": "ink_chronicle", "bible_version": "1.5"}
    s = by_id(new)
    assert {k: v["lane"] for k, v in s.items()} == {
        "s1": "VIDEO_3D", "s2": "VIDEO_3D", "s3": "VIDEO_3D",  # moving keyframe, spoken close-up, atmosphere
        "s4": "STILL_3D", "s5": "STILL_3D",  # a /2 keyframe at tier hold counted as a still under BP-109; the hold lane
        "s6": "HELPER", "s7": "STILL_3D", "s8": "HELPER"}  # the 2.5D tableau is a still (D-97); maps and HUDs are helpers
    assert s["s2"]["lipsync"] is True and s["s2"]["dialogue_cover"] == "on_screen"
    assert s["s1"]["lipsync"] is False and "dialogue_cover" not in s["s1"]
    assert s["s3"]["render_profile"] == "eevee_fast" and s["s1"]["render_profile"] == "eevee_full"  # tier light -> fast
    assert s["s7"]["still_mode"] == "parallax_25d" and s["s4"]["still_mode"] == "hold"
    assert s["s6"]["helper_archetype"] == "LOGISTICS_TETHER_AND_ATTRITION" and "render_profile" not in s["s6"]
    for shot in new["shots"]:
        assert shot["archetype"] is None  # the shot designer assigns 1-20 (ICW-03); nothing is guessed here
        assert (shot["width"], shot["height"]) == (SR.T("BP-167", "width"), SR.T("BP-167", "height"))
        assert shot["duration_frames"] == round(shot["seconds"] * SR.T("BP-167", "fps"))
    assert report["shares_unchanged"] and report["shares_before"] == F.lane_shares(new["shots"], "film_shots/3")


def test_the_style_keeps_no_prompt_field():
    new, report = migration().migrate(load(ALL_LANES), bible_version="1.5")
    assert not set(migration().LEGACY_STYLE) & set(new["style"])
    assert report["style_dropped"] == ["trigger", "video_sentence"]


@pytest.mark.parametrize("fixture,cite", [("invalid__host_lane.json", "D-89"), ("invalid__3d_lane.json", "D-106")])
def test_a_refused_lane_is_refused_with_its_decision(fixture, cite):
    with pytest.raises(migration().MigrationRefused, match=cite):
        migration().migrate(load(FS2 / fixture))


def test_an_invalid_input_or_another_contract_is_refused():
    doc = load(ALL_LANES)
    doc["shots"][0]["seconds"] = -1
    with pytest.raises(migration().MigrationRefused, match="does not validate"):
        migration().migrate(doc)
    with pytest.raises(migration().MigrationRefused, match="only film_shots/1 and film_shots/2"):
        migration().migrate({"schema": "shot_spec/1"})


def test_a_1_card_gets_counted_defaults():
    new, report = migration().migrate(legacy_cards(), bible_version="1.5")
    assert report["source_schema"] == "film_shots/1"
    assert report["defaults"]["lens_tier, focal_xy, refs (/1 card)"] == len(new["shots"])
    assert all(s["focal_xy"] == [0.5, 0.5] and s["continuity_ref"] is None for s in new["shots"])


def test_the_napoleon_example_is_the_migration_of_its_legacy_cards():
    """ICW-02 owns the example: the committed cards are film_shots/3 and equal what build_cards.py makes today."""
    committed = load(NAPOLEON / "film_shots.json")
    assert committed == cards_v3()
    C.validate(committed)
    assert committed["style"]["house_look"] == "ink_chronicle" and "trigger" not in committed["style"]
    _, report = migration().migrate(legacy_cards())
    assert report["shares_unchanged"]
    assert (NAPOLEON / "migration_report.md").read_text(encoding="utf-8") == _builder().migration_report(report)
    assert (NAPOLEON / "shotlist.md").read_text(encoding="utf-8") == F.shotlist(committed)


def test_the_checked_in_dry_run_is_what_the_script_says_today(tmp_path, capsys, monkeypatch):
    head = DRY_RUN.read_text(encoding="utf-8")
    command = next(line for line in head.splitlines() if "migrate_film_shots_2_to_3.py" in line)
    paths = command.split("migrate_film_shots_2_to_3.py ", 1)[1].split(" --report")[0].split()
    out = tmp_path / "report.md"
    monkeypatch.chdir(ROOT)  # the report names the inputs by their repo paths
    before = {p: (ROOT / p).read_bytes() for p in paths}
    assert migration().main([*paths, "--report", str(out)]) == 1  # the two refused fixtures
    assert {p: (ROOT / p).read_bytes() for p in paths} == before  # a dry run writes no card
    capsys.readouterr()
    assert out.read_text(encoding="utf-8") == head


def test_write_replaces_the_card_with_its_film_shots_3(tmp_path, capsys):
    card = tmp_path / "film_shots.json"
    card.write_text(ALL_LANES.read_text(encoding="utf-8"), encoding="utf-8")
    assert migration().main([str(card), "--write"]) == 0
    capsys.readouterr()
    new = load(card)
    assert new["schema"] == "film_shots/3"
    C.validate(new)


def test_a_film_shots_3_card_is_not_migrated_again():
    new, _ = migration().migrate(load(ALL_LANES))
    with pytest.raises(migration().MigrationRefused, match="only film_shots/1 and film_shots/2"):
        migration().migrate(copy.deepcopy(new))
