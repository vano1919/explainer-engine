"""Character-select screens (Syndicate Wars): the creator's stats are pinned, every screen is drawn without a network."""

from __future__ import annotations

import select_screen as SS  # examples/syndicate_wars_ep1 (pytest puts this folder on sys.path)


def test_the_creators_stats_are_exact():
    got = {b: dict(v["stats"]) for b, v in SS.BOSSES.items()}
    assert got["capone"] == {"Brutality": 5, "Adaptability": 1, "Tech-Savviness": 1, "Intimidation": 4, "Chaos Management": 2}
    assert got["vito"] == {"Brutality": 2, "Adaptability": 2, "Tech-Savviness": 1, "Influence / Networking": 5, "Strategy": 4}
    assert got["mizuno"] == {"Brutality": 4, "Adaptability": 4, "Tech-Savviness": 4, "Discipline": 5, "Chaos Management": 2}
    assert got["shelby"] == {"Brutality": 3, "Adaptability": 5, "Tech-Savviness": 5, "Intelligence / Strategy": 5, "Influence": 4}
    assert all(1 <= n <= 5 for s in got.values() for n in s.values())


def test_the_after_test_changes_are_the_ones_the_script_says():
    after = {b: v["after"] for b, v in SS.BOSSES.items()}
    assert after == {"capone": {"Intimidation": 2}, "vito": {"Influence / Networking": 3},
                     "mizuno": {"Discipline": 4}, "shelby": {"Intelligence / Strategy": 4}}


def test_all_screens_are_written_even_without_portraits(tmp_path):
    paths = SS.make_all(tmp_path)
    names = sorted(p.name for p in paths)
    assert names == sorted(["thumbnail.png", "sc_all.png", "sc_final.png", "sc_capone.png", "sc_vito.png", "sc_mizuno.png", "sc_shelby.png",
                            "sc_capone_out.png", "sc_vito_out.png", "sc_mizuno_out.png"])
    assert all(p.stat().st_size > 5000 for p in paths)
