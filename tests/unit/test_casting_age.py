"""Ages matter most (creator 2026-10-19): the casting filters by age and never offers a voice of the wrong age."""

from explainer_engine.audio import casting

OLD = {"names": ["vito"], "card": "an older patriarch", "voice": {"style": "a soft, low, slightly husky elderly voice",
                                                          "traits": {"gender": "male"}}}
MID = {"names": ["mizuno"], "voice": {"style": "calm", "traits": {"gender": "male", "age": "middle_aged"}}}


def test_the_age_comes_from_the_traits_or_from_the_style_and_card():
    assert casting.age_of(MID) == "middle_aged"
    assert casting.age_of(OLD) == "old"
    assert casting.query(OLD)["age"] == "old"
    assert casting.age_of({"voice": {"style": "a calm voice"}}) is None
    assert "elderly" in casting.design_description(OLD)


def test_a_voice_of_the_wrong_age_is_never_ranked():
    voices = [{"voice_id": "a", "labels": {"gender": "male", "age": "young"}},
              {"voice_id": "b", "labels": {"gender": "male", "age": "middle_aged"}},
              {"voice_id": "c", "labels": {"gender": "male", "age": "old"}}]
    assert [r["voice_id"] for r in casting.rank(voices, OLD)] == ["c", "b"]
    assert [r["voice_id"] for r in casting.rank(voices, MID)][0] == "b"
    assert "a" not in [r["voice_id"] for r in casting.rank(voices, MID)]
