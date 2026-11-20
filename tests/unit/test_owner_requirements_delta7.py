"""Delta 7 (episode film style, OR-F01..OR-F04) in the live registry. $0, stdlib only.

His typed words (FS-1..FS-3) are verbatim with a real cmsg id; FS-4 rests on a card press, so it is a new row that says so and
OR-V40 only carries a proposed amendment (applied false) until his typed word."""
from __future__ import annotations

import json

from _gov import ROOT
from explainer_engine.governance import owner_requirements as OR

REG = ROOT / "explainer_engine" / "governance" / "owner_requirements.json"
DELTA7 = ["OR-F01", "OR-F02", "OR-F03", "OR-F04"]


def _by():
    data = json.loads(REG.read_text(encoding="utf-8"))
    return {e["id"]: e for e in data["requirements"] + data["process_requirements"]}


def test_the_four_rows_are_loaded_once_with_real_ids():
    by = _by()
    assert all(i in by for i in DELTA7)
    assert not [i for i in by if i.startswith("PROPOSED")]
    assert OR.check_registry(OR.load(ROOT)[0], ROOT) == []


def test_fs_1_to_3_are_his_verbatim_typed_words_with_their_message_ids():
    by = _by()
    expect = {"OR-F01": ("cmsg_01Hnu5zB86sjUj5GtTgaUkPWN7eWpqaAGf9qwRANxGYZti", ["L15"]),
              "OR-F02": ("cmsg_01Hnu5zB86sjUj5GtTgaUkPW3RwHwWq7RAijoycD1PZe1u", ["L9", "L10", "L14", "L15", "L22", "L25"]),
              "OR-F03": ("cmsg_01Hnu5zB86sjUj5GtTgaUkPWCLK3soNHhgBwuWVm9Wqsws", ["L2", "L3", "L4", "L7"])}
    for rid, (ref, layers) in expect.items():
        e = by[rid]
        assert e["words_verbatim"] is True and e["source"] == {"kind": "chat", "ref": ref}, rid
        assert e["layers"] == layers and e["check"] == {"kind": "unmapped"} and e["status"] == "active", rid
        assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPWWbmkN4F56PpukNEm9N1set" in e["note"], rid  # the load word


def test_fs_2_note_says_the_film_is_chosen_per_video_and_has_no_fixed_list():
    n = _by()["OR-F02"]["note"]
    assert "No fixed list of films" in n and "episode_film.json" in n
    assert "ფილმის სტილი ყველგან" in _by()["OR-F02"]["words"]  # the words themselves are untouched


def test_fs_4_is_a_new_row_resting_on_a_card_press_not_typed_words():
    f4 = _by()["OR-F04"]
    assert f4["words_verbatim"] is False and "NOT typed words" in f4["words_origin"]
    assert f4["source"]["kind"] == "doc" and f4["layers"] == ["L15", "L25"] and f4["check"] == {"kind": "unmapped"}


def test_or_v40_is_unchanged_except_for_an_unapplied_proposed_amendment():
    v40 = _by()["OR-V40"]
    assert v40["words"] == "Maps are Python over a letter-free relief plate with our own type (D-130, L15)."
    assert v40["status"] == "active" and "superseded_by" not in v40
    pa = v40["proposed_amendment"]
    assert pa["applied"] is False and pa["change"]["amended_by"] == "OR-F04" and "waits for his word" in pa["why_not_applied"]


def test_delta_7_is_unsigned_and_delta_8_and_p03_are_not_loaded():
    data = json.loads(REG.read_text(encoding="utf-8"))
    assert not any(k in data for k in ("signed", "signature", "signed_by", "owner_signature"))
    by = _by()
    assert "OR-P03-EXC" not in by and not any(i.startswith(("OR-D8", "PROPOSED")) for i in by)
