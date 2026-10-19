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
           "spanish", "russian", "swedish", "polish", "greek", "nigerian", "south african", "new zealand"}
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
          "dublin": "irish", "glasgow": "scottish", "edinburgh": "scottish", "germany": "german", "france": "french",
          "italy": "italian", "spain": "spanish", "russia": "russian", "greece": "greek"}


AGES = ("young", "middle_aged", "old")
# words in the voice style or the picture card that say the hero's age (the creator, 2026-10-19: "ages matter most")
AGE_WORDS = [("old", r"\b(elderly|old man|old woman|older|aged|grandfather|grandmother|patriarch|matriarch|sixties|seventies|"
                     r"eighties|white[- ]haired)\b"),
             ("middle_aged", r"\b(middle[- ]aged|forties|fifties|thirties|mature)\b"),
             ("young", r"\b(young|youthful|teen\w*|twenties|boyish|girlish)\b")]


def age_of(hero: dict) -> str | None:
    """The hero's age band in the library's labels: ``traits.age`` first, else read from the voice style and the card."""
    t = hero.get("voice", {}).get("traits", {}).get("age")
    if t:
        return t
    text = " ".join([hero.get("voice", {}).get("style", ""), hero.get("card", "")]).lower()
    return next((band for band, rx in AGE_WORDS if re.search(rx, text)), None)


def _age_clash(want: str, label: str) -> bool:
    """A labelled voice two bands away (a young voice for an old hero) or a young voice for a middle-aged one."""
    label = label.replace(" ", "_")
    if want not in AGES or label not in AGES:
        return False
    return abs(AGES.index(want) - AGES.index(label)) == 2 or (want == "middle_aged" and label == "young")


def _accent(origin: str) -> str | None:
    o = origin.lower()
    for a in sorted(ACCENTS, key=len, reverse=True):
        if a in o:
            return a
    return next((acc for place, acc in PLACES.items() if place in o), None)


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
    if age_of(hero):
        q["age"] = age_of(hero)
    d = _descriptives(traits, style)
    if d:
        q["descriptives"] = d
    q["use_cases"] = ROLE_USE.get(traits.get("role", "hero"), ["characters_animation"])
    acc = _accent(traits.get("origin", ""))
    if acc:
        q["accent"] = acc
    energy = {"low": "slow measured", "medium": "", "high": "energetic fast"}.get(traits.get("energy", "medium"), "")
    q["search"] = " ".join(x for x in [energy, " ".join(d[:2]), "character" if traits.get("role") != "narrator" else "storyteller"] if x).strip()
    return q


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
    if want["age"] and _age_clash(want["age"], lab.get("age", "")):
        return 0.0  # a voice of the wrong age is never a candidate, however well the rest fits
    s, total = 0.0, 0.0
    for key, w in (("gender", 3.0), ("age", 2.0)):
        if want[key]:
            total += w
            s += w * (want[key].replace("_", " ") in lab.get(key, "").replace("_", " "))
    acc = _accent(traits.get("origin", ""))
    if acc:
        total += 1.0
        s += 1.0 * (acc in lab.get("accent", ""))
    for d in _descriptives(traits, hero.get("voice", {}).get("style", "")):
        total += 1.0
        s += 1.0 * (d in text)
    return round(s / total, 3) if total else 0.0


def rank(voices: list[dict], hero: dict, taken: set[str] | None = None, top: int = 3) -> list[dict]:
    """The best ``top`` voices as cast candidates {voice_id, name, why}; voices another speaker already has are skipped
    (two speakers never share a voice, PV-32)."""
    taken = taken or set()
    scored = []
    for v in voices:
        vid = v.get("voice_id") or v.get("id")
        if not vid or vid in taken:
            continue
        sc = score(v, hero)
        if sc > 0:
            scored.append((sc, vid, v))
    scored.sort(key=lambda x: -x[0])
    return [{"voice_id": vid, "name": v.get("name", vid), "why": f"trait match {sc:.2f}"} for sc, vid, v in scored[:top]]


def design_description(hero: dict) -> str:
    """A voice_description for ``creative_design_voice`` from the traits only (used when no library voice fits)."""
    if problems(hero):
        raise ValueError("; ".join(problems(hero)))
    voice = hero.get("voice", {})
    t = voice.get("traits", {})
    age = {"young": "young adult", "middle_aged": "middle-aged", "old": "elderly"}.get(age_of(hero) or "", "")
    parts = [p for p in [age, t.get("gender", ""), "voice"] if p]
    desc = " ".join(parts)
    acc = _accent(t.get("origin", ""))
    if acc:
        desc += f" with a light {acc} accent"
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
