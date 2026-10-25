"""Creator 2026-10-21: the narrator tells a conversation in his own words, and each told turn keeps a bubble with its key
phrase over the speaker, or the scene is a still picture under a voice (the faces cannot change without new pictures)."""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.production import script as S

DOC = Path("examples/titans_from_zero/production_script.json")


def _doc():
    return json.loads(DOC.read_text(encoding="utf-8"))


def test_every_told_exchange_has_bubbles_on_its_speakers():
    doc = _doc()
    pics = {sh["picture"]["id"]: sh["picture"] for sg in doc["segments"] for sh in sg["shots"] if isinstance(sh["picture"], dict)}
    for seg in doc["segments"]:
        told = [ln for ln in seg["lines"] if ln.get("new_read") and any(w in ln["text"] for w in (" says", " asks", " tells"))]
        reported = [b for sh in seg["shots"] for b in sh.get("bubbles", []) if b.get("reported")]
        if told:
            assert reported, seg["id"]
        for sh in seg["shots"]:
            pic = sh["picture"] if isinstance(sh["picture"], dict) else pics[sh["picture"]]
            for b in sh.get("bubbles", []):
                assert b["who"] in (pic.get("speakers") or {}), (seg["id"], b)
                assert len(b["text"].split()) <= 4, b


def test_the_schema_takes_the_reported_flag_and_nothing_else_new():
    doc = _doc()
    sh = next(sh for sg in doc["segments"] for sh in sg["shots"] if any(b.get("reported") for b in sh.get("bubbles", [])))
    assert not [e for e in S.schema_errors(doc) if "reported" in e]
    sh["bubbles"][0]["reported"] = "yes"
    assert S.schema_errors(doc)
    sh["bubbles"][0]["reported"] = True
    sh["bubbles"][0]["mood"] = "x"
    assert S.schema_errors(doc)


def test_a_bubble_sits_nearer_its_speaker_than_the_hero_beside_him():
    """titans SH015 101 s: O'Leary's bubble landed by Belfort's face and read as Belfort's line (the frame's numbers)."""
    import math
    from explainer_engine.finish import bubbles as BUB
    FW, FH = 1920, 1080
    speaker = (1195, 323)
    faces = [(317, 160, 605, 462), (1051, 63, 1339, 366), (1497, 60, 1785, 362)]  # Musk, O'Leary himself, Belfort
    _, (w, h) = BUB.draw_bubble("Short one. In bankruptcy.", FH)
    x, y = BUB.layout(speaker, (w, h), (FW, FH), faces=faces)
    c = (x + w / 2, y + h / 2)
    mine = math.dist(c, (speaker[0], speaker[1] - 0.1 * FH))
    assert all(mine <= math.dist(c, ((f[0] + f[2]) / 2, (f[1] + f[3]) / 2)) for f in (faces[0], faces[2]))
    assert not any(BUB.overlaps((x, y, x + w, y + h), f) for f in faces)
