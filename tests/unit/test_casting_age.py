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


JP = {"names": ["mizuno"], "voice": {"style": "calm, with a light Japanese accent",
                                     "traits": {"gender": "male", "age": "middle_aged", "origin": "a businessman speaking English",
                                                "ethnicity": "Japanese"}}}
BHAM = {"names": ["x"], "voice": {"style": "dry, Birmingham (West Midlands) accent",
                                  "traits": {"gender": "male", "age": "middle_aged", "origin": "1930s Birmingham, England"}}}


def test_ethnicity_sets_the_accent_when_the_origin_names_none():
    assert casting.accent_of(JP["voice"]["traits"]) == "japanese"
    assert casting.query(JP)["accent"] == "japanese"
    assert "japanese accent" in casting.design_description(JP)
    american = {"voice": {"traits": {"origin": "New York", "ethnicity": "Japanese"}}}
    assert casting.accent_of(american["voice"]["traits"]) == "american"  # the stated place wins over the background


def test_a_named_region_goes_into_the_search_and_into_the_ranking():
    assert casting.region_of(BHAM) == "midlands"
    assert casting.query(BHAM)["search"].startswith("midlands")
    voices = [{"voice_id": "a", "name": "Plain British", "labels": {"gender": "male", "age": "middle_aged", "accent": "british"}},
              {"voice_id": "b", "name": "Robert", "description": "middle aged British man with a midlands accent",
               "labels": {"gender": "male", "age": "middle_aged", "accent": "british"}}]
    assert [r["voice_id"] for r in casting.rank(voices, BHAM)] == ["b", "a"]
    japanese = [{"voice_id": "j", "labels": {"gender": "male", "age": "middle_aged", "accent": "japanese"}},
                {"voice_id": "u", "labels": {"gender": "male", "age": "middle_aged", "accent": "american"}}]
    assert [r["voice_id"] for r in casting.rank(japanese, JP)][0] == "j"
