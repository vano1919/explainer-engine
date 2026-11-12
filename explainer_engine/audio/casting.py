
"""Voice casting from a character's traits (VC rules, docs/STORY_ENGINE.md, D-48): the search an ElevenLabs voice
library query needs, the description a designed voice needs, and a ranking of the voices that come back. Free;
the agent passes ``query(...)`` to the connector's ``creative_list_voices`` and the result to ``rank(...)``.

The creator's ask (2026-10-19): find the needed ElevenLabs voices automatically from the hero's character, and for a
real public figure or a known character from what they really were. The line we hold (PV-10, ElevenLabs' prohibited
use policy on impersonation): a real person's *documented* traits (age at the time of the story, region, temperament,
station) choose a fitting library voice; age is a filter and a voice labelled two bands off (or young for a
middle-aged hero) is never ranked (``age_of`` reads ``traits.age`` or the style and card); a voice is never searched, designed or described as that person's voice,
never cloned, never a "famous" library category, and never prompted with the person's name.

    q = query(cast["einstein"])                      # -> kwargs for creative_list_voices
    ranked = rank(voices_from_connector, cast["einstein"])
    text = design_description(cast["einstein"])      # -> voice_description for creative_design_voice
"""

from __future__ import annotations

import re

# the connector's descriptive vocabulary (creative_list_voices.descriptives)
DESCRIPTIVES = {"anxious", "calm", "casual", "chill", "classy", "confident", "crisp", "cute", "deep", "excited", "formal",
                "gentle", "grumpy", "hyped", "husky", "intense", "mature", "meditative", "modulated", "neutral",
                "pleasant", "professional", "raspy", "relaxed", "robotic", "rough", "sad", "sassy", "serious", "soft",
                "upbeat", "whispery", "wise"}
# temperament words a character card uses -> the connector's words
SYNONYMS = {"nervous": "anxious", "worried": "anxious", "fussy": "anxious", "proud": "confident", "bold": "confident",
            "arrogant": "confident", "cheerful": "upbeat", "optimistic": "upbeat", "playful": "upbeat",
            "sarcastic": "sassy", "witty": "sassy", "cheeky": "sassy", "fierce": "intense", "driven": "intense",
            "stubborn": "intense", "kind": "gentle", "warm": "gentle", "gruff": "rough", "tough": "rough",
            "aristocratic": "classy", "elegant": "classy", "pompous": "formal", "stern": "serious", "grave": "serious",
            "dry": "serious", "hyper": "excited", "eager": "excited", "lazy": "relaxed", "easygoing": "relaxed",
            "dreamy": "meditative", "shy": "soft", "quiet": "soft", "old": "mature", "seasoned": "mature",
            "grumbling": "grumpy", "cranky": "grumpy", "smoky": "husky", "hoarse": "raspy", "sharp": "crisp"}
ROLE_USE = {"narrator": ["narrative_story"], "hero": ["characters_animation"], "rival": ["characters_animation"],
            "mentor": ["characters_animation", "narrative_story"], "comic": ["characters_animation"],
            "villain": ["characters_animation"], "everyman": ["conversational", "characters_animation"]}
ACCENTS = {"american", "british", "australian", "irish", "scottish", "indian", "canadian", "german", "french", "italian",
           "spanish", "russian", "swedish", "polish", "greek", "nigerian", "south african", "new zealand", "japanese",
           "chinese", "korean", "welsh", "jamaican"}
# a region inside an accent the library cannot filter on: it goes into the free-text search and the ranking (the creator,
# 2026-10-19: "Shelby must have a Birmingham accent")
REGIONS = {"birmingham": "midlands", "west midlands": "midlands", "black country": "midlands", "midlands": "midlands",
           "yorkshire": "yorkshire", "liverpool": "liverpool", "manchester": "manchester", "glasgow": "glasgow",
           "cockney": "cockney", "geordie": "geordie", "texas": "texan", "brooklyn": "brooklyn", "chicago": "chicago"}
IMITATION = re.compile(r"\b(sound(s|ing)? like|in the voice of|voice of|imitat\w*|impersonat\w*|clon\w*|famous|celebrity|"
                       r"real voice|exact voice|soundalike)\b", re.I)


def _descriptives(traits: dict, style: str) -> list[str]:
    words = [w.lower().strip() for w in traits.get("temperament", [])] + re.findall(r"[a-z]+", style.lower())
    out: list[str] = []
    for w in words:
        d = w if w in DESCRIPTIVES else SYNONYMS.get(w)
        if d and d not in out:
            out.append(d)
    return out[:3]


PLACES = {"england": "british", "london": "british", "usa": "american", "new york": "american", "boston": "american",
          "dublin": "irish", "japan": "japanese", "tokyo": "japanese", "birmingham": "british", "midlands": "british",
          "yorkshire": "british", "liverpool": "british", "manchester": "british", "wales": "welsh", "chicago": "american", "glasgow": "scottish", "edinburgh": "scottish", "germany": "german", "france": "french",
          "italy": "italian", "spain": "spanish", "russia": "russian", "greece": "greek"}


AGES = ("young", "middle_aged", "old")
# a hero under 18 (VC-10, the creator 2026-11-07: "yesterday a child had a 40-year-old man's voice"): the library's age
# filter knows only young / middle_aged / old, and its "young" is a young ADULT (Ben Young Man, Cam), so a child or a
# teen is never searched with the age filter; the voice must say it is a kid in its own name, description or labels
KID_AGES = ("child", "teen")
# words in the voice style or the picture card that say the hero's age (the creator, 2026-10-19: "ages matter most");
# the kid bands are read before "young" so "a young boy" is a teen, never a young adult
AGE_WORDS = [("old", r"\b(elderly|old man|old woman|older|aged|grandfather|grandmother|patriarch|matriarch|sixties|seventies|"
                     r"eighties|white[- ]haired)\b"),
             ("middle_aged", r"\b(middle[- ]aged|forties|fifties|thirties|mature)\b"),
             ("child", r"\b(child|kid|little (boy|girl)|small (boy|girl)|([4-9]|1[01])[- ]years?[- ]old|"
                       r"(five|six|seven|eight|nine|ten|eleven)[- ]years?[- ]old)\b"),
             ("teen", r"\b(teen\w*|adolescent|boy|girl|lad|lass|(1[2-7])[- ]years?[- ]old|"
                      r"(twelve|thirteen|fourteen|fifteen|sixteen|seventeen)[- ]years?[- ]old)\b"),
             ("young", r"\b(young|youthful|twenties|boyish|girlish)\b")]
# a voice that says it is a kid (VC-10): read from its description and labels, after the words that only name the
# AUDIENCE ("for kids", "children's books", "kids storyteller") are struck out; a name alone ("Johnny Boy") is no evidence
KID_VOICE = {"child": r"\b(child(like)?|kids?|little (cartoon )?(boy|girl)|cartoon (boy|girl)|very young|actual kid|"
                      r"([4-9]|1[01])[- ]?(years?[- ]old|yo)?)\b",
             "teen": r"\b(teen\w*|adolescent|(1[2-7])[- ]?(years?[- ]old|yo)?|orphan boy|schoolboy|boy|girl)\b"}
KID_AUDIENCE = re.compile(r"\b(for (young )?(kids|children)|kids'?\s*(content|stor\w+|learning|educat\w*|bedtime|audio\w*|"
                          r"cartoons?|apps?|channels?|platforms?|series|characters? voiceover)|children'?s\s*(books?|content|"
                          r"stor\w+|educat\w*|audiobooks?|animations?|podcasts?|nonfiction|learning|channels?)|young listeners|"
                          r"teen and young adult audiobooks|teen audiobooks|kid characters|kid-friendly|youtube kids|"
                          r"kids? (narrator|storyteller|educator|bedtime)|boyfriend|boy[- ]next[- ]door|good ol'? boys?|"
                          r"with your boys|the boys)\b", re.I)
ADULT_VOICE = re.compile(r"\b(young adult|adult|man|men|woman|grown|mid-?\d0s|[2-9]0s|middle[- ]aged|millennial|gen z|"
                         r"father|dad|mother|mom|grandpa|grandfather|uncle|aunt|senior|elder\w*|\d{2,3}\+|age 3\d)\b", re.I)


def age_of(hero: dict) -> str | None:
    """The hero's age band in the library's labels: ``traits.age`` first, else read from the voice style and the card."""
    t = hero.get("voice", {}).get("traits", {}).get("age")
    if t:
        return {"kid": "child", "boy": "teen", "girl": "teen", "teenager": "teen", "teenage": "teen"}.get(t, t)
    text = " ".join([hero.get("voice", {}).get("style", ""), hero.get("card", "")]).lower()
    return next((band for band, rx in AGE_WORDS if re.search(rx, text)), None)


# the library's own age words (labels are free text: "Senior", "middle aged", "elderly") -> our three bands
AGE_LABELS = {"senior": "old", "elderly": "old", "old": "old", "middle_aged": "middle_aged", "middle-aged": "middle_aged",
              "mature": "middle_aged", "adult": "middle_aged", "young": "young", "youthful": "young", "young_adult": "young",
              "teen": "teen", "teenager": "teen", "child": "child", "kid": "child"}


def voice_text(v: dict) -> str:
    """A returned voice's description and labels (keys and values: the library's free labels put words in both)."""
    lab = v.get("labels") or {}
    return " ".join([str(v.get("description", ""))] + [f"{k} {x}" for k, x in lab.items()])


def kid_bands(v: dict) -> set[str]:
    """The kid bands a voice claims for itself (VC-10): ``child``, ``teen`` or both, from its description and labels with
    the audience phrases struck out; a voice that also calls itself an adult (``young adult``, ``mid-30s``) claims none."""
    text = KID_AUDIENCE.sub(" ", voice_text(v))
    name = str(v.get("name", ""))
    if ADULT_VOICE.search(text) or ADULT_VOICE.search(KID_AUDIENCE.sub(" ", name)):
        return set()
    if any(int(n) >= 18 for n in re.findall(r"\b(\d{2})[- ]?years?[- ]old\b", name, re.I)):
        return set()  # "Kuya Boy: The 20-Year-Old Narrator": the name says the age
    bands = {band for band, rx in KID_VOICE.items() if re.search(rx, text, re.I)}
    for n in re.findall(r"\b(\d{1,2})\b", text):
        if 4 <= int(n) <= 11:
            bands.add("child")
        elif 12 <= int(n) <= 17:
            bands.add("teen")
        elif int(n) >= 18:
            return set()
    return bands


def _age_label(label: str) -> str:
    key = label.strip().lower().replace(" ", "_")
    return AGE_LABELS.get(key, key)


def _age_clash(want: str, label: str) -> bool:
    """A labelled voice two bands away (a young voice for an old hero) or a young voice for a middle-aged one."""
    label = _age_label(label)
    if want in KID_AGES or label in KID_AGES:
        return False  # kid bands are judged by kid_clash on the voice's own words, never by the library's adult labels
    if want not in AGES or label not in AGES:
        return False
    return abs(AGES.index(want) - AGES.index(label)) == 2 or (want == "middle_aged" and label == "young")


def region_of(hero: dict) -> str | None:
    """The regional accent word (``midlands``...) from the origin, the ethnicity or the voice style."""
    voice = hero.get("voice", {})
    t = voice.get("traits", {})
    text = " ".join([t.get("origin", ""), t.get("ethnicity", ""), voice.get("style", "")]).lower()
    return next((r for place, r in sorted(REGIONS.items(), key=lambda x: -len(x[0])) if place in text), None)


def _accent(origin: str) -> str | None:
    o = origin.lower()
    for a in sorted(ACCENTS, key=len, reverse=True):
        if a in o:
            return a
    return next((acc for place, acc in PLACES.items() if place in o), None)


def accent_of(traits: dict) -> str | None:
    """The accent the voice must carry: from ``origin`` first, then ``ethnicity`` (the creator, 2026-10-19: "add the
    ethnicity to the rules too": a Japanese businessman speaks English with a Japanese accent, not an American one)."""
    return _accent(traits.get("origin", "")) or _accent(traits.get("ethnicity", ""))


def problems(hero: dict, names: list[str] | None = None) -> list[str]:
    """Why a cast voice may not be searched or designed (PV-10): imitation words, the person's own name in the voice
    text, a real person without documented traits, a 'famous' category."""
    voice = hero.get("voice", {})
    traits = voice.get("traits", {})
    text = " ".join([voice.get("style", ""), traits.get("origin", ""), " ".join(traits.get("temperament", []))])
    out = []
    if IMITATION.search(text):
        out.append("the voice text asks for an imitation or a famous voice (PV-10)")
    for n in names if names is not None else hero.get("names", []):
        if n and re.search(rf"\b{re.escape(n)}\b", text, re.I):
            out.append(f"the voice text names {n!r}: describe the sound, never the person (PV-10)")
    if traits.get("real_person") and not traits.get("documented"):
        out.append("a real person: list the documented traits (sources) the casting stands on (VC-02)")
    return out


def query(hero: dict, language: str = "en") -> dict:
    """kwargs for the connector's ``creative_list_voices``: a library search built only from traits and the style."""
    voice = hero.get("voice", {})
    traits = voice.get("traits", {})
    style = voice.get("style", "")
    if problems(hero):
        raise ValueError("; ".join(problems(hero)))
    q: dict = {"languages": [language], "context": "cast a voice for an animated explainer character from its traits"}
    if traits.get("gender"):
        q["gender"] = traits["gender"]
    age = age_of(hero)
    if age in AGES:
        q["age"] = age  # never for a child or a teen: the library's "young" is a young adult (VC-10)
    d = _descriptives(traits, style)
    if d:
        q["descriptives"] = d
    q["use_cases"] = ROLE_USE.get(traits.get("role", "hero"), ["characters_animation"])
    acc = accent_of(traits)
    if acc:
        q["accent"] = acc
    energy = {"low": "slow measured", "medium": "", "high": "energetic fast"}.get(traits.get("energy", "medium"), "")
    reg = region_of(hero)
    q["search"] = " ".join(x for x in [reg, energy, " ".join(d[:2]), "character" if traits.get("role") != "narrator" else "storyteller"] if x).strip()
    if age in KID_AGES:
        q["search"] = kid_search(hero)[0]
        q.pop("descriptives", None)  # descriptives narrow to labelled library voices; most kid voices carry no labels
    return q


def kid_search(hero: dict) -> list[str]:
    """The free-text searches for a child or teen hero, best first (VC-10); run each with ``query``'s other filters and
    pool the results: the library has no kid age band, so the words in the voice's own name and description find it."""
    age = age_of(hero)
    gender = hero.get("voice", {}).get("traits", {}).get("gender", "")
    who = {"male": "boy", "female": "girl"}.get(gender, "kid")
    if age == "child":
        return [f"kid {who}", "child", f"little {who}", f"cartoon {who}"]
    if age == "teen":
        return [f"teen {who}", "teenager", who, "kid"]
    return []


def kid_clash(v: dict, hero: dict) -> str | None:
    """Why a voice cannot speak for this hero by age (VC-10): a child or a teen hero needs a voice that says it is a kid
    in its own description or labels; an adult hero never gets a voice that says it is a kid."""
    age = age_of(hero)
    bands = kid_bands(v)
    lab = _age_label(_labels(v).get("age", ""))
    if age in KID_AGES and lab in ("middle_aged", "old"):
        return f"the hero is a {age}; the library labels the voice {lab!r} (VC-10)"   # "an old boy scout leader" says "boy"
    if age in KID_AGES and not bands:
        return f"the hero is a {age}; the voice never says it is a child or a teen (VC-10)"
    if age == "child" and bands == {"teen"} and re.search(r"\b1[6-7]\b|older teen|deep-voiced", voice_text(v), re.I):
        return "the hero is a child; the voice is an older teen (VC-10)"
    if age in AGES and bands:
        return f"the hero is {age}; the voice says it is a {'/'.join(sorted(bands))} (VC-10)"
    return None


def relaxed(q: dict) -> list[dict]:
    """Fallback searches when a query returns nothing: drop the accent, then the descriptives, then the use case."""
    out = []
    for drop in (["accent"], ["accent", "descriptives"], ["accent", "descriptives", "use_cases"]):
        r = {k: v for k, v in q.items() if k not in drop}
        if r != q and r not in out:
            out.append(r)
    return out


def _labels(v: dict) -> dict:
    lab = {k.lower(): str(x).lower() for k, x in (v.get("labels") or {}).items()}
    for k in ("gender", "age", "accent", "descriptive", "use_case", "category"):
        if k in v and k not in lab:
            lab[k] = str(v[k]).lower()
    return lab


def score(v: dict, hero: dict) -> float:
    """0..1: how well a returned voice matches the traits (gender and age weigh most); 0 for a famous-category voice."""
    traits = hero.get("voice", {}).get("traits", {})
    lab = _labels(v)
    text = " ".join([lab.get("descriptive", ""), lab.get("use_case", ""), str(v.get("description", "")).lower(),
                     str(v.get("name", "")).lower()])
    if "famous" in lab.get("category", "") or IMITATION.search(str(v.get("description", ""))):
        return 0.0
    want = {"gender": traits.get("gender"), "age": age_of(hero)}
    if want["age"] and (_age_clash(want["age"], lab.get("age", "")) or kid_clash(v, hero)):
        return 0.0  # a voice of the wrong age is never a candidate, however well the rest fits
    s, total = 0.0, 0.0
    if want["age"] in KID_AGES:
        total += 2.0
        s += 2.0 if want["age"] in kid_bands(v) else 1.0  # a teen voice for a child (or the reverse) is a weaker fit
    for key, w in (("gender", 3.0), ("age", 2.0)):
        if key == "age" and want["age"] in KID_AGES:
            continue
        if want[key]:
            total += w
            have = _age_label(lab.get(key, "")) if key == "age" else lab.get(key, "")
            if key == "gender" and not have and want["age"] in KID_AGES:  # most kid voices carry no labels
                text_v = KID_AUDIENCE.sub(" ", voice_text(v) + " " + str(v.get("name", "")))
                have = ("male" if re.search(r"\b(boy|lad|schoolboy|male)\b", text_v, re.I) else
                        "female" if re.search(r"\b(girl|lass|schoolgirl|female)\b", text_v, re.I) else "")
            s += w * (want[key].replace("_", " ") in have.replace("_", " "))
    acc = accent_of(traits)
    if acc:
        total += 1.0
        s += 1.0 * (acc in lab.get("accent", ""))
    reg = region_of(hero)
    if reg:
        total += 2.0  # a region the labels cannot carry is read from the voice's own description and name
        s += 2.0 * (reg in text)
    for d in _descriptives(traits, hero.get("voice", {}).get("style", "")):
        total += 1.0
        s += 1.0 * (d in text)
    return round(s / total, 3) if total else 0.0


def eligible(v: dict, hero: dict, taken: set[str] | None = None) -> list[str]:
    """Why a returned voice may not be a candidate for this hero (VC-02, VC-04, VC-05); an empty list = eligible. A voice
    the library has not labelled is eligible but judged on its preview alone (``fit`` says so)."""
    vid = v.get("voice_id") or v.get("id")
    lab = _labels(v)
    out = []
    if not vid:
        out.append("no voice_id")
    if taken and vid in taken:
        out.append("another speaker already has this voice (PV-32)")
    if "famous" in lab.get("category", "") or IMITATION.search(str(v.get("description", ""))):
        out.append("a famous or imitation voice (VC-02)")
    want_age = age_of(hero)
    if want_age and _age_clash(want_age, lab.get("age", "")):
        out.append(f"labelled {lab.get('age')!r}, the hero is {want_age} (VC-05)")
    if want_age and kid_clash(v, hero):
        out.append(kid_clash(v, hero))
    return out


def fit(v: dict, hero: dict, usage_rank: int | None = None, listed: int | None = None) -> dict:
    """How a voice fits: ``trait`` 0..1 (``score``), its ``usage_rank`` (0 = the most used of the ``listed`` voices the
    connector returned sorted by ``usage_character_count_1y``: the popularity prior, a tie-break and never a score), and
    whether the library labelled it at all."""
    lab = _labels(v)
    return {"trait": score(v, hero), "usage_rank": usage_rank, "listed": listed,
            "unlabelled": not any(lab.get(k) for k in ("gender", "age", "accent"))}


def rank(voices: list[dict], hero: dict, taken: set[str] | None = None, top: int = 3, by_usage: bool = False) -> list[dict]:
    """The best ``top`` voices as cast candidates {voice_id, name, why}; voices another speaker already has are skipped
    (two speakers never share a voice, PV-32). Equal trait scores go to the more used voice: with ``by_usage`` the list
    order IS the usage order (call ``creative_list_voices`` with ``sort: usage_character_count_1y``)."""
    scored = []
    for i, v in enumerate(voices):
        if eligible(v, hero, taken):
            continue
        f = fit(v, hero, i if by_usage else None, len(voices) if by_usage else None)
        if f["trait"] > 0:
            scored.append((f["trait"], i, v, f))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for sc, i, v, f in scored[:top]:
        why = f"trait match {sc:.2f}"
        if by_usage:
            why += f"; most-used #{i + 1} of {len(voices)} listed"
        if f["unlabelled"]:
            why += "; unlabelled: judge the preview"
        out.append({"voice_id": v.get("voice_id") or v.get("id"), "name": v.get("name", v.get("voice_id")), "why": why})
    return out


def design_description(hero: dict) -> str:
    """A voice_description for ``creative_design_voice`` from the traits only (used when no library voice fits)."""
    if problems(hero):
        raise ValueError("; ".join(problems(hero)))
    voice = hero.get("voice", {})
    t = voice.get("traits", {})
    age = {"young": "young adult", "middle_aged": "middle-aged", "old": "elderly", "child": "child's (about 8 to 11)",
           "teen": "young teenage (about 12 to 15)"}.get(age_of(hero) or "", "")
    who = {"child": {"male": "boy", "female": "girl"}, "teen": {"male": "boy", "female": "girl"}}.get(age_of(hero) or "", {})
    parts = [p for p in [age, who.get(t.get("gender", ""), t.get("gender", "")), "voice"] if p]
    desc = " ".join(parts)
    acc = accent_of(t)
    if acc:
        desc += f" with a {region_of(hero) + ' ' if region_of(hero) else ''}{acc} accent"
    temper = ", ".join(t.get("temperament", []))
    if temper:
        desc += f"; {temper}"
    energy = {"low": "slow, measured pacing", "medium": "natural conversational pacing", "high": "quick, energetic pacing"}
    desc += f"; {energy.get(t.get('energy', 'medium'))}. {voice.get('style', '')}".rstrip()
    return desc[:1000]


def distinct(cast: dict) -> list[str]:
    """Pairs of speaking heroes whose traits would cast the same kind of voice (same gender, age and energy, and no
    voice id yet that tells them apart): the ear cannot follow a dialogue between them (VC-04)."""
    heroes = [(k, dict(h["voice"].get("traits", {}), age=age_of(h)), h["voice"].get("voice_id")) for k, h in cast.items()
              if h.get("voice")]
    out = []
    for i, (a, ta, va) in enumerate(heroes):
        for b, tb, vb in heroes[i + 1:]:
            same = all(ta.get(x) and ta.get(x) == tb.get(x) for x in ("gender", "age")) and ta.get("energy", "medium") == tb.get("energy", "medium")
            if same and (not va or va == vb):
                out.append(f"{a} and {b}: same gender, age and energy; give them different temperaments and voices")
    return out


def ltx_voice_text(hero: dict) -> str:
    """The voice in words for an LTX cast card (docs/SCRIPT_ENGINE.md, dialogue audio): the sound from the traits only, under
    the same PV-10 guard as a designed voice; no name, no imitation, so a card never asks a model for a person's voice."""
    return design_description(hero)
