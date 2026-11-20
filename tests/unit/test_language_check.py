"""Georgian script check of the viewer's text (OR-S09)."""

from __future__ import annotations

import json
import unicodedata

from explainer_engine.qa import language_check as lc

GEO = "ა"            # U+10D0
GEO_EXT = "Ა"        # U+1C90
GEO_SUP = "ⴀ"        # U+2D00


def test_ranges_hold_only_georgian_characters_and_their_neighbours_are_not():
    for lo, hi, _ in lc.GEORGIAN_BLOCKS:
        names = [unicodedata.name(chr(c), "") for c in range(lo, hi + 1)]
        assert any(names) and all("GEORGIAN" in n for n in names if n)
    for outside in (0x109F, 0x1100, 0x1C8F, 0x1CC0, 0x2CFF, 0x2D30):
        assert not lc.is_georgian(chr(outside))


def test_each_block_is_caught():
    for ch in (GEO, GEO_EXT, GEO_SUP):
        assert lc.is_georgian(ch)


def test_english_text_passes(tmp_path):
    f = tmp_path / "narration.txt"
    f.write_text("The bridge shakes.\nAnna runs. Café, naïve, 1453, — and Cyrillic: Привет.\n", encoding="utf-8")
    res = lc.check_files([f])
    assert res == {"status": "PASS", "value": 0, "detail": res["detail"]}


def test_hit_has_where_and_count_and_first_three(tmp_path):
    f = tmp_path / "titles.txt"
    f.write_text(f"ok\nab{GEO}c{GEO_EXT}\n{GEO_SUP}{GEO}\n", encoding="utf-8")
    res = lc.check_files([f])
    assert res["status"] == "FAIL" and res["value"] == 4
    assert f"{f}:2:3 U+10D0" in res["detail"] and "+1 more" in res["detail"]
    assert res["detail"].count("U+") == 3          # only the first three are shown


def test_json_is_read_as_json_and_escapes_count(tmp_path):
    f = tmp_path / "meta.json"
    f.write_text(json.dumps({"title": "A title", "desc": ["fine", GEO]}, ensure_ascii=True), encoding="utf-8")
    assert "\\u10d0" in f.read_text(encoding="utf-8")
    res = lc.check_files([f])
    assert res["status"] == "FAIL" and res["value"] == 1 and ".desc[1]" in res["detail"]


def test_broken_json_falls_back_to_raw_text(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{" + GEO, encoding="utf-8")
    assert lc.check_files([f])["status"] == "FAIL"


def test_unreadable_file_is_not_run_and_a_hit_beats_it(tmp_path):
    missing = tmp_path / "nope.txt"
    res = lc.check_files([missing])
    assert res["status"] == "NOT_RUN" and res["value"] is None
    bad = tmp_path / "bin.txt"
    bad.write_bytes(b"\xff\xfe\x00bad")
    assert lc.check_files([bad])["status"] == "NOT_RUN"
    hit = tmp_path / "hit.txt"
    hit.write_text(GEO, encoding="utf-8")
    assert lc.check_files([missing, hit])["status"] == "FAIL"


def test_no_files_is_not_run():
    assert lc.check_files([])["status"] == "NOT_RUN"


def test_cli_exit_codes(tmp_path, capsys):
    ok = tmp_path / "a.txt"
    ok.write_text("fine", encoding="utf-8")
    bad = tmp_path / "b.txt"
    bad.write_text(GEO, encoding="utf-8")
    assert lc.main([str(ok)]) == 0 and lc.main([str(bad)]) == 1 and lc.main([str(tmp_path / "x")]) == 2
