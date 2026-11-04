# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/casting.py`
# Target Module : explainer_engine/audio/casting.py
# Target Classes/Symbols : def _descriptives(), def age_of(), def _age_label(), def _age_clash(), def region_of(), def _accent(), def accent_of(), def problems(), def query(), def relaxed(), def _labels(), def score(), def eligible(), def fit(), def rank(), def design_description(), def distinct(), def ltx_voice_text()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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


# the library's own age words (labels are free text: "Senior", "middle aged", "elderly") -> our three bands
AGE_LABELS = {"senior": "old", "elderly": "old", "old": "old", "middle_aged": "middle_aged", "middle-aged": "middle_aged",
              "mature": "middle_aged", "young": "young", "youthful": "young", "teen": "young"}


def _age_label(label: str) -> str:
    key = label.strip().lower().replace(" ", "_")
    return AGE_LABELS.get(key, key)


def _age_clash(want: str, label: str) -> bool:
    """A labelled voice two bands away (a young voice for an old hero) or a young voice for a middle-aged one."""
    label = _age_label(label)
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
    if age_of(hero):
        q["age"] = age_of(hero)
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
            have = _age_label(lab.get(key, "")) if key == "age" else lab.get(key, "")
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
    age = {"young": "young adult", "middle_aged": "middle-aged", "old": "elderly"}.get(age_of(hero) or "", "")
    parts = [p for p in [age, t.get("gender", ""), "voice"] if p]
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
