from explainer_engine.training.cast import sheet
from explainer_engine.training.pods import xworld_v1_story as st


def test_hundred_people_one_style_block_and_lt79_faces():
    people = sheet.cast()
    assert len(people) == 100 and sheet.problems(people) == []
    assert all(sheet.prompt(c).startswith(sheet.STYLE) for c in people)
    assert sheet.cast() == people  # deterministic


def test_style_block_carries_the_creators_reference_palette_and_plain_background():
    for w in ("navy blue", "crimson red", "golden yellow", "plain warm off-white", "full body", "black ink outlines"):
        assert w in sheet.STYLE


def test_problems_catch_a_show_face_and_a_thin_face():
    c = dict(sheet.cast()[0])
    c["face"] = c["desc"] = "He has a round head and big round eyes."
    pr = sheet.problems([c])
    assert any("trait" in p for p in pr) and any("face names" in p for p in pr)


def test_show_traits_match_whole_words_only():
    assert st.show_traits("An Elizabethan actor near a brick wall") == []
    assert st.show_traits("Morty with a unibrow") == ["unibrow", "morty"]


def test_draw_is_refused_without_yes(capsys):
    assert sheet.main(["draw", "x", "--ids", "0"]) == 0
    assert "add --yes" in capsys.readouterr().out


def test_world_redraws_a_fail_with_the_next_seed_and_stops_at_the_budget(tmp_path):
    seeds, verdicts = [], iter(["FAIL", "PASS", "PASS"])

    def gen(name, it, seed):
        seeds.append((name, seed)); return 0.009

    def judge(rows):
        return [{**r, "verdict": next(verdicts), "why": []} for r in rows]

    rows = sheet.world(tmp_path, ["p001", "o002"], budget_usd=1.0, workers=1, generate=gen, judge=judge)
    assert seeds == [("p001", 1001), ("p001_t1", 101001), ("o002", 1002)]
    assert [r["verdict"] for r in rows] == ["FAIL", "PASS", "PASS"]
    assert (tmp_path / "report.jsonl").read_text().count("\n") == 3
    seeds.clear()
    sheet.world(tmp_path, ["p003", "p004"], budget_usd=0.01, workers=1, generate=gen,
                judge=lambda rs: [{**r, "verdict": "PASS", "why": []} for r in rs])
    assert len(seeds) == 1


def test_items_cover_people_places_and_objects():
    it = sheet.items()
    kinds = [v["kind"] for v in it.values()]
    assert kinds.count("person") == 100 and kinds.count("place") == len(sheet.PLACES) and kinds.count("object") == len(sheet.OBJECTS)
