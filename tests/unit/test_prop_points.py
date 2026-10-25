"""Prop points (qa/prop_points.py; the creator's CC-03, 2026-10-20: "props appear only because a rule demands them"): a ring
or label naming no hero is checked against what an open-vocabulary detector finds in its picture: moved onto the thing,
kept when it is already on it, dropped when the thing is nowhere (a ring on nothing is worse than no ring, RX-12, BP-93).
The detector is a fake here: no model download."""
import json

from PIL import Image, ImageDraw

from explainer_engine.qa import loop as L
from explainer_engine.qa import prop_points as PB


class FakeDetector:
    """Answers per text from a table: {text: [{box, score}]}; records what it was asked."""
    name = "fake"

    def __init__(self, table):
        self.table, self.asked = table, []

    def __call__(self, image, texts):
        self.asked.append(list(texts))
        return [list(self.table.get(t, [])) for t in texts]


def _picture(tmp_path):
    im = Image.new("RGB", (160, 90), (200, 200, 200))
    d = ImageDraw.Draw(im)
    d.rectangle([16, 60, 64, 80], fill=(120, 70, 30))  # a bench, bottom left
    d.ellipse([110, 20, 130, 40], fill=(210, 150, 110))  # a hero's face
    im.save(tmp_path / "hall.png")
    return tmp_path


def _doc():
    beats = [
        {"at": "wooden bench", "kind": "highlight", "pos": [0.5, 0.72]},  # guessed: empty floor
        {"at": "price tags", "kind": "highlight", "pos": [0.55, 0.55]},  # nothing of the kind is painted
        {"at": "this bench", "kind": "highlight", "pos": [0.25, 0.77]},  # already on the bench
        {"at": "courthouse hallway", "kind": "label", "text": "COURTHOUSE", "pos": [0.5, 0.2]},  # the place itself
        {"at": "Elon Musk", "kind": "highlight", "pos": [0.1, 0.1]},  # a hero: snaps to his face point, not measured here
        {"at": "the deal", "kind": "label", "text": "MUSK", "pos": [0.1, 0.1]},  # a hero named in the tag only
        {"at": "the whole room", "kind": "highlight", "pos": [0.5, 0.5]},  # a ring whose only find is the whole picture
    ]
    return {"cast": {"musk": {}}, "library": {"hall": {"speakers": {"musk": [0.75, 0.33]}}},
            "segments": [{"id": "S01", "light_beat": "x", "shots": [{"picture": "hall"}],
                          "lines": [{"text": "...", "visual_beats": beats}]}]}


def _timed(doc):
    return {"visual_beats": [dict(b, segment="S01", line=1, shot="SH001", picture="hall", start=float(i))
                             for i, b in enumerate(doc["segments"][0]["lines"][0]["visual_beats"])]}


TABLE = {"wooden bench": [{"box": [0.1, 0.66, 0.4, 0.9], "score": 0.64}],
         "bench": [{"box": [0.1, 0.66, 0.4, 0.9], "score": 0.42}],
         "price tags": [{"box": [0.5, 0.5, 0.6, 0.6], "score": 0.06}],
         "courthouse hallway": [{"box": [0.0, 0.0, 1.0, 1.0], "score": 0.33}],
         "whole room": [{"box": [0.0, 0.0, 0.95, 1.0], "score": 0.4}]}


def test_queries_drop_small_words_and_try_the_thing_of_a_verb_phrase_first():
    assert PB.query("inside their heads") == "heads" and PB.query("this bench") == "bench"
    assert PB.queries("reads the screen") == ["screen", "reads the screen"]
    assert PB.queries("a man in a grey suit") == ["grey suit", "man in a grey suit"]
    assert PB.queries("stack of white envelopes") == ["stack of white envelopes"]


def test_found_props_move_or_stay_missing_ones_drop_and_heroes_are_not_measured(tmp_path):
    doc = _doc()
    det = FakeDetector(TABLE)
    m = PB.measure(doc, _timed(doc), [_picture(tmp_path)], detect=det)
    by = {r["at"]: r for r in m["beats"]}
    assert set(by) == {"wooden bench", "price tags", "this bench", "courthouse hallway", "the whole room"}
    assert m["hero_beats"] == 2 and len(det.asked) == 1  # one detector pass per picture
    assert by["wooden bench"]["decision"] == "move" and by["wooden bench"]["new_pos"] == [0.25, 0.78]
    assert by["price tags"]["decision"] == "drop"  # best score under SCORE_MIN
    assert by["this bench"]["decision"] == "keep"  # its pos already lies in the found box
    assert by["courthouse hallway"]["decision"] == "keep" and by["courthouse hallway"].get("scene")  # a place label
    assert by["the whole room"]["decision"] == "drop" and by["the whole room"].get("scene")  # a ring cannot circle a picture
    rules = sorted((f["rule"], f["where"].split("'")[1]) for f in PB.check(m))
    assert rules == [("PB-NONE", "price tags"), ("PB-NONE", "the whole room"), ("PB-OFF", "wooden bench")]
    assert all(f["severity"] == "REVIEW" and f["shot"] == "SH001" for f in PB.check(m))


def test_apply_moves_and_removes_and_writes_two_space_json(tmp_path):
    doc = _doc()
    m = PB.measure(doc, _timed(doc), [_picture(tmp_path)], detect=FakeDetector(TABLE))
    done = PB.apply(doc, m)
    assert len(done["moved"]) == 1 and len(done["dropped"]) == 2
    beats = doc["segments"][0]["lines"][0]["visual_beats"]
    assert [b["at"] for b in beats] == ["wooden bench", "this bench", "courthouse hallway", "Elon Musk", "the deal"]
    assert beats[0]["pos"] == [0.25, 0.78] and beats[1]["pos"] == [0.25, 0.77] and beats[3]["pos"] == [0.1, 0.1]
    out = tmp_path / "script.json"
    PB.save(doc, out)
    text = out.read_text(encoding="utf-8")
    assert text == json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def test_a_beat_the_timing_dropped_is_listed_not_measured(tmp_path):
    doc = _doc()
    timed = _timed(doc)
    timed["visual_beats"] = [b for b in timed["visual_beats"] if b["at"] != "price tags"]
    m = PB.measure(doc, timed, [_picture(tmp_path)], detect=FakeDetector(TABLE))
    assert [r["at"] for r in m["not_timed"]] == ["price tags"] and "price tags" not in {r["at"] for r in m["beats"]}


def test_without_the_detector_nothing_is_measured_and_it_says_so(monkeypatch):
    monkeypatch.setattr(PB, "detector", lambda: None)
    doc = _doc()
    m = PB.measure(doc, _timed(doc), [])
    assert m["skipped"] and m["beats"] == [] and PB.check(m) == []


def test_the_loop_classes_prop_findings_as_the_scripts():
    rows = L.classify([{"rule": "PB-OFF", "severity": "REVIEW", "where": f"S01 line 1 {s} highlight 'bench'", "shot": s,
                        "source": "prop_points", "detail": ""} for s in ("SH001", "SH002")])
    assert all(r["class"] == "script" and "--apply" in r["owner"] for r in rows)


def test_sheets_draw_one_tile_per_beat(tmp_path):
    doc = _doc()
    m = PB.measure(doc, _timed(doc), [_picture(tmp_path)], detect=FakeDetector(TABLE))
    names = PB.sheets(m, tmp_path / "sheets", cols=2, width=160)
    assert len(names) == 1 and Image.open(names[0]).size == (2 * 164, 3 * (90 + 4))
