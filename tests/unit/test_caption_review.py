"""LT-74 automatic caption review: cut endings trimmed, names become roles, style words go, broken rows dropped not lost."""
from __future__ import annotations

import json

from explainer_engine.training.pods import caption_review as cr

LONG = ("Inside a lab, an old man with spiky blue hair in a white coat points at a glowing machine while a boy in a yellow "
        "shirt watches. Shelves of jars line the back wall and green light spills across the floor. The camera holds a "
        "medium shot from eye level, the machine on the left and both of them on the right, with the")


def test_cut_description_is_trimmed_to_its_last_sentence():
    r = cr.clean({"id": "d:a", "kind": "describe", "text": LONG})
    assert r["text"].endswith("both of them on the right.") is False and r["text"].endswith("floor.")
    assert r["raw"] == LONG and not r["drop"]


def test_names_become_roles_and_style_words_go():
    r = cr.clean({"id": "d:a", "kind": "describe", "text": "Rick " + LONG.replace("Inside a lab", "inside a cartoon lab")})
    assert "Rick" not in r["text"] and r["text"].startswith("The old scientist") and "cartoon" not in r["text"]


def test_change_prefix_restored_and_broken_rows_dropped(tmp_path):
    ok = cr.clean({"id": "c:a>b", "kind": "change", "text": "Change: the camera moves closer to the boy, who now frowns."})
    assert ok["text"].startswith(cr.PREFIX) and not ok["drop"]
    bad = cr.clean({"id": "c:b>c", "kind": "change", "text": "Nothing."})
    assert bad["drop"] and "no change line" in bad["review"]
    short = cr.clean({"id": "d:c", "kind": "describe", "text": "A room."})
    assert short["drop"]
    src = tmp_path / "c.jsonl"
    src.write_text("\n".join(json.dumps(x) for x in ({"id": "d:a", "kind": "describe", "text": "x."},
                                                     {"id": "d:a", "kind": "describe", "text": LONG})), encoding="utf-8")
    rep = cr.review(src, tmp_path / "r.jsonl", tmp_path / "rep.json")
    assert rep["rows"] == 1 and rep["dropped"] == 0   # the resumed duplicate: the last row wins
