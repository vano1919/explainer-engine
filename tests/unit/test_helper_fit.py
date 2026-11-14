"""MA-09 (the creator, 2026-11-14): a helper shot's form fits what its words say; variety is never a quota."""
import json
from pathlib import Path

from explainer_engine.episode import helper_fit as HF

PLACES = {"ypres": {"lon": 2.885, "lat": 50.851, "name": "Ypres"}, "flanders": {"lon": 2.9, "lat": 50.8, "name": "Flanders"},
          "aachen": {"lon": 6.08, "lat": 50.78, "name": "Aachen"}, "marne": {"lon": 3.5, "lat": 48.9, "name": "Marne"}}


def _script(*shots):
    lines, out = [], []
    for i, (text, actions, extra) in enumerate(shots):
        lid = f"L{i}"
        lines.append({"line_id": lid, "text": text})
        out.append({"shot_id": f"S01_SH{i:03d}", "route": "map_action", "audio_line_ids": [lid], "actions": actions, **extra})
    return {"audio_lines": lines, "shots": out}


MAP = [{"kind": "front_line", "from": "ypres", "to": "flanders", "at_word": "x"}]
COUNTER = [{"kind": "counter", "value": 100000, "unit": "men", "claim": "C-01", "at_word": "x"}]
WHY = {"helper_reason": "the words are about where the line ran"}


def test_cues_read_the_words():
    c = HF.cues("Here, in Flanders, the two sides sat close enough to hear each other cough.", PLACES)
    assert "place" in c and "number" not in c
    c = HF.cues("The usual estimate is that about a hundred thousand men took part.", PLACES)
    assert "number" in c and "place" not in c
    c = HF.cues("The war had begun in August. Everyone said it would be over by Christmas.", PLACES)
    assert set(c) == {"time"}
    c = HF.cues("They were outnumbered: forty thousand against twelve thousand.", PLACES)
    assert {"number", "comparison"} <= set(c)


def test_a_year_is_time_not_a_quantity():
    c = HF.cues("By 1914 the guns were ready.", PLACES)
    assert "number" not in c and "time" in c


def test_shown_forms_come_from_the_actions():
    assert HF.shown({"actions": MAP}) == {"map"}
    assert HF.shown({"actions": COUNTER}) == {"counter"}
    assert HF.shown({"actions": [{"kind": "bar_grow", "values": [1, 2]}]}) == {"comparison"}
    assert HF.shown({"actions": [{"kind": "progress_bar", "value": 3, "max": 10}]}) == {"progress"}
    assert HF.shown({"actions": [{"kind": "label", "label": "December 1914"}]}) == {"date"}


def test_director_picks_from_the_words_with_a_reason():
    s = _script(("About a hundred thousand men took part.", MAP, {}),
                ("Here, in Flanders, the lines nearly touched.", MAP, {}),
                ("Everyone said it would be over by Christmas.", MAP, {}),
                ("Forty thousand men against twelve thousand.", MAP, {}))
    picks = [HF.choose(sh, s, PLACES) for sh in s["shots"]]
    assert [p["form"] for p in picks] == ["counter", "map", "progress", "comparison"]
    assert all(len(p["reason"]) > 20 for p in picks)
    assert "hundred" in picks[0]["reason"]


def test_maps_repeat_freely_when_the_words_are_about_places():
    """The creator: no new things for the sake of variety. Five maps under five place lines is right: no finding at all."""
    lines = ["Here, in Flanders, the lines nearly touched.", "The front ran from Ypres to the sea.",
             "Along the British line, it spread from trench to trench.", "The Germans marched west through Aachen.",
             "They stopped at the Marne, on the river."]
    s = _script(*[(t, MAP, WHY) for t in lines])
    assert HF.findings(s, PLACES) == []
    rows = HF.check_rows(s, PLACES)
    assert [r["status"] for r in rows] == ["PASS", "PASS"]
    assert rows[1]["measured"] == {"map": 5}


def test_a_number_the_words_name_must_be_shown():
    s = _script(("About a hundred thousand men took part.", MAP, WHY))
    f = HF.findings(s, PLACES)
    assert [x["check"] for x in f] == ["number_not_shown", "map_without_place"]
    assert all(x["level"] == "REVIEW" and x["suggest"] == "counter" for x in f)
    ok = _script(("About a hundred thousand men took part.", MAP + COUNTER, WHY))
    assert HF.findings(ok, PLACES) == []


def test_a_map_under_time_words_is_flagged_and_a_progress_bar_suggested():
    s = _script(("Everyone said it would be over by Christmas.", MAP, WHY))
    f = HF.findings(s, PLACES)
    assert [x["check"] for x in f] == ["map_without_place"] and f[0]["suggest"] == "progress"


def test_a_card_under_place_only_words_is_flagged():
    s = _script(("Here, in Flanders, the lines nearly touched.", [{"kind": "progress_bar", "value": 1, "max": 2}], WHY))
    assert [x["check"] for x in HF.findings(s, PLACES)] == ["card_under_place_words"]


def test_the_director_writes_a_reason():
    s = _script(("Here, in Flanders, the lines nearly touched.", MAP, {}))
    f = HF.findings(s, PLACES)
    assert [x["check"] for x in f] == ["reason_missing"]
    assert HF.check_rows(s, PLACES)[0]["status"] == "REVIEW"


def test_no_row_counts_forms_against_a_minimum():
    """No quota: one form for the whole lane never makes a row fail or review by itself."""
    s = _script(*[("About a hundred thousand men took part.", COUNTER, WHY)] * 4)
    rows = HF.check_rows(s, PLACES)
    assert all(r["status"] == "PASS" for r in rows)


def test_truce_demo_flags_only_the_time_line_under_a_map():
    root = Path(__file__).resolve().parents[2] / "episodes" / "ep_truce_1914"
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    places = json.loads((root / "episode.json").read_text(encoding="utf-8"))["places"]
    f = [x for x in HF.findings(script, places) if x["check"] != "reason_missing"]
    assert [(x["shot_id"], x["check"], x["suggest"]) for x in f] == [("S02_SH001", "map_without_place", "progress")]


def test_schema_accepts_the_director_fields():
    import jsonschema
    schema = json.loads((Path(HF.__file__).resolve().parents[1] / "schemas" / "production_script.schema.json").read_text())
    shot = schema["$defs"]["ShotSpec"]["properties"]
    assert shot["helper_form"]["enum"] == list(HF.FORMS)
    jsonschema.validate("the words are about where the line ran", shot["helper_reason"])
