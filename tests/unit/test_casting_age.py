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


# VC-10 (2026-11-06): the library has no child label and "young" holds adults; a boy scout was cast with an adult voice
SCOUT = {"names": ["scout"], "card": "a boy scout of about twelve", "voice": {"style": "quiet, nervous", "traits": {"gender": "male"}}}


def test_a_child_is_a_band_of_its_own():
    # Merge of 2026-11-12 (v4.3 P0.3): two VC-10 versions met; the kept one (PR #156, test_casting_kids.py) splits the kid
    # ages into child (4-11) and teen (12-17, and a bare "boy"), so this scout of about twelve is a teen; a kid band either way,
    # never the library's adult "young".
    assert casting.age_of(SCOUT) == "teen" and casting.age_of(SCOUT) in casting.KID_AGES
    assert casting.age_of({"voice": {"traits": {"age": "child"}}}) == "child"
    assert casting.age_of({"card": "the drummer boy", "voice": {}}) in casting.KID_AGES
    q = casting.query(SCOUT)
    assert q["search"] == "teen boy" and "age" not in q
    assert "teenage" in casting.design_description(SCOUT) and "boy" in casting.design_description(SCOUT)


def test_a_young_adult_voice_is_never_a_child():
    voices = [{"voice_id": "cam", "name": "Cam", "description": "young American male", "labels": {"gender": "male", "age": "young"}},
              {"voice_id": "bf", "name": "Brad", "description": "your favorite boyfriend voice", "labels": {"gender": "male"}},
              {"voice_id": "jb", "name": "Hosie - Professional Jersey Boy", "labels": {"gender": "male"}},
              {"voice_id": "ab", "name": "Austin Boy", "description": "A timid orphan boy", "labels": {}},
              {"voice_id": "tt", "name": "Teddy Twinkle - Cute Cartoon Boy",
               "description": "A sweet, playful little cartoon boy", "labels": {"gender": "male", "age": "young"}},
              {"voice_id": "old", "name": "Old boy", "description": "an old boy scout leader", "labels": {"age": "old"}}]
    assert [r["voice_id"] for r in casting.rank(voices, SCOUT, top=5)] == ["tt", "ab"] or \
        {r["voice_id"] for r in casting.rank(voices, SCOUT, top=5)} == {"tt", "ab"}
    assert casting.eligible(voices[0], SCOUT) and "VC-10" in casting.eligible(voices[0], SCOUT)[0]
