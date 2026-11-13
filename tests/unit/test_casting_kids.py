"""A child or a teen hero never gets an adult voice (VC-10; the creator 2026-11-07: "yesterday a child had a 40-year-old
man's voice"). The voices below are copied from the free ElevenLabs library listing of 2026-11-07 (name, description,
labels only), including the two the J5 scout got on 2026-11-06 (Cam, then Ben Young Man)."""

from explainer_engine.audio import casting

SCOUT = {"names": ["scout"], "card": "a freckled boy of about 13 in a green hood",
         "voice": {"style": "earnest, a little nervous, reporting to his commander",
                   "traits": {"gender": "male", "age": "teen", "temperament": ["nervous", "eager"], "role": "hero"}}}
PAGE = {"names": ["page"], "voice": {"style": "a little boy, curious", "traits": {"gender": "male", "role": "hero"}}}
COMMANDER = {"names": ["commander"], "voice": {"style": "grave, weathered", "traits": {
    "gender": "male", "age": "old", "temperament": ["stern", "gruff"], "role": "mentor"}}}

BEN = {"voice_id": "lKwD8tN2jdXnBKugh4YP", "name": "Ben Young Man", "description": "Clear, energetic, friendly voice perfect "
       "for story telling, narration and most types of content.", "labels": {"gender": "male", "age": "young",
                                                                             "accent": "american", "descriptive": "upbeat"}}
JOHNNY_KID = {"voice_id": "8JVbfL6oEdmuxKn5DK2C", "name": "Johnny Kid Serious",
              "description": "Teenager with an american accent. Serious and calm. Perfect for audiobooks.", "labels": {}}
AUSTIN_BOY = {"voice_id": "Xb3zeLrTi6F4ziIcXdwk", "name": "Austin Boy", "description": "A timid orphan boy ",
              "labels": {"English": "American"}}
VALF = {"voice_id": "loY1uopAz31XyhAEhNSa", "name": "VALF - Child, Young, Playful & Sarcastic",
        "description": "A very Young voice with an energetic, playful. Perfect for cartoons, animation, anime dubbing, video "
                       "games, children's content. Ideal for kid characters, young heroes, mischievous boys.",
        "labels": {"gender": "male", "age": "young", "accent": "en-american"}}
TEDDY = {"voice_id": "XjGYkUkzth8BPs29fmcV", "name": "Teddy Twinkle - Cute Cartoon Boy",
         "description": "A sweet, playful and adorable little cartoon boy inspired by popular kids characters.",
         "labels": {"gender": "male", "age": "young"}}
BRAYDEN = {"voice_id": "3XOBzXhnDY98yeWQ3GdM", "name": "Brayden - Conversational Older Teen",
           "description": "A deep-voiced male teenager", "labels": {"Accent": "American", "Gender": "Male", "Age": "17"}}
JOSH_TEACHER = {"voice_id": "nzFihrBIvB34imQBuxub", "name": "Josh - Teacher for Kids", "description": "Sweet energetic and "
                "encouraging. A super cool big brother to read children's books. Bedtime stories.",
                "labels": {"gender": "male", "age": "young"}}
KUYA = {"voice_id": "Z0J3eW5H8x7rllGL9dBS", "name": "Kuya Boy: The 20-Year-Old Narrator and Explainer",
        "description": "Kuya Boy's youthful yet knowledgeable voice bridges the gap between generations.", "labels": {}}
CHILL = {"voice_id": "N5m2ReaeSIcn4Ssu8rpQ", "name": "Chill - Casual and friendly", "description": "Warm, moderately deep "
         "male voice with a natural, conversational tone. Sounds like a man in his mid-30s.",
         "labels": {"gender": "male", "age": "young"}}
TUCKER = {"voice_id": "EI3BL0ECeQayX8N4doHx", "name": "Tucker Thomas", "description": "Deep, resonant, and full-bodied.",
          "labels": {"gender": "male", "age": "old", "accent": "american"}}
LIBRARY = [BEN, CHILL, KUYA, JOSH_TEACHER, BRAYDEN, TEDDY, VALF, AUSTIN_BOY, JOHNNY_KID, TUCKER]


def test_a_boy_is_never_searched_with_the_librarys_young_adult_filter():
    q = casting.query(SCOUT)
    assert "age" not in q and "descriptives" not in q
    assert q["search"] == "teen boy" and q["gender"] == "male"
    assert casting.age_of(PAGE) == "child" and casting.kid_search(PAGE)[0] == "kid boy"
    assert casting.age_of({"voice": {"style": "a young boy"}}) == "teen"  # never "young" (a young adult)


def test_yesterdays_young_man_and_every_adult_are_refused_for_the_scout():
    for v in (BEN, CHILL, KUYA, JOSH_TEACHER, TUCKER):
        assert casting.eligible(v, SCOUT), v["name"]
        assert casting.score(v, SCOUT) == 0.0
    ranked = [r["voice_id"] for r in casting.rank(LIBRARY, SCOUT, top=5)]
    assert BEN["voice_id"] not in ranked and CHILL["voice_id"] not in ranked
    assert set(ranked) <= {JOHNNY_KID["voice_id"], AUSTIN_BOY["voice_id"], BRAYDEN["voice_id"], VALF["voice_id"],
                           TEDDY["voice_id"]}
    assert len(ranked) == 5 and JOHNNY_KID["voice_id"] in ranked


def test_kid_bands_read_the_voices_own_words_not_its_audience():
    assert casting.kid_bands(JOHNNY_KID) == {"teen"}
    assert "child" in casting.kid_bands(VALF) and "child" in casting.kid_bands(TEDDY)
    assert casting.kid_bands(BRAYDEN) == {"teen"}
    assert casting.kid_bands(JOSH_TEACHER) == set()  # reads children's books: the audience, not the voice
    assert casting.kid_bands(CHILL) == set() and casting.kid_bands(BEN) == set()


def test_a_little_boy_gets_no_older_teen_and_an_old_commander_gets_no_kid():
    assert casting.kid_clash(BRAYDEN, PAGE)
    assert casting.kid_clash(VALF, PAGE) is None
    assert casting.kid_clash(TEDDY, COMMANDER)
    assert [r["voice_id"] for r in casting.rank(LIBRARY, COMMANDER)] == [TUCKER["voice_id"]]
    assert "teenage" in casting.design_description(SCOUT) and "boy" in casting.design_description(SCOUT)
