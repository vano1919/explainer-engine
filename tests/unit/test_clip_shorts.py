from explainer_engine.production import clip_shorts as C

LONG = [{"w": "What", "s": 0.0, "e": 0.3}, {"w": "if?", "s": 0.3, "e": 0.6},
        {"w": "Musk", "s": 10.0, "e": 10.4}, {"w": "signs.", "s": 10.4, "e": 11.0}, {"w": "Later.", "s": 20.0, "e": 20.5}]
OUTRO = [{"text": "One", "start": 0.0, "end": 0.4}, {"text": "question.", "start": 0.4, "end": 1.0}]


def test_a_short_is_the_opening_then_the_moment_then_the_shared_outro():
    parts = C.timeline({"id": "CS01", "start": 10.0, "end": 11.0}, 1.0, 1.0)
    assert [p["part"] for p in parts] == ["intro", "clip", "outro"]
    assert parts[1]["src_start"] == 10.0 - C.PAD_IN and parts[1]["src_end"] == 11.0 + C.PAD_OUT


def test_captions_follow_the_speed_up_and_skip_words_outside_the_moment():
    parts = C.timeline({"id": "CS01", "start": 10.0, "end": 11.0}, 1.0, 1.0)
    words = C.caption_words(parts, LONG, OUTRO, 1.15)
    assert [w["w"] for w in words] == ["What", "if?", "Musk", "signs.", "One", "question."]  # "Later." is not in the Short
    assert words[2]["s"] == round((1.0 + C.PAD_IN) / 1.15, 3)  # after the 1 s opening, the clip's lead-in, sped up
    assert words[-1]["e"] < C.duration(parts, 1.15)  # the outro ends inside the Short; the card then holds into the loop


def test_a_clip_that_ends_before_it_starts_is_refused():
    try:
        C.timeline({"id": "CS09", "start": 5.0, "end": 4.0}, 1.0, 1.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
