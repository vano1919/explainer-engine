"""The hyped read of ONE narrator (BP-171, BP-169): which ElevenLabs audio tags a zone allows, how a line is formatted for
the read, a plan check before any credit is paid, and the score of an audition take. stdlib only; no network, no credit.

The narrator is one voice whose tempo and energy follow the zones of the rhythm profile. The tags cost credits (1 per
character, tags included), so the formatter puts AT MOST ONE tag at the start of a line (a tag holds until the next one, EL-05);
BP-171's ``max_tags_per_clause`` is a ceiling, not a target. The capital letters of a stressed word are limited to BP-171's
``caps_words_per_sentence`` (EL-06's single stress is the calm zone's rule; the hyped zones may stress two).

A line is ``{"text": str, "start_s": float?, "zone": str?}``; the zone is the line's own or the one at ``start_s``.

    allowed_tags("hook_0_30s")                               -> ["excited", "shouting", "rushed", "amazed"]
    format_line_for_tts(line, total_s=720)                   -> "[excited] This is the GREATEST trade in history."
    check_prosody_plan(lines, total_s=720)                   -> findings HR-01..HR-04
    hype_score({"f0_iqr_st": 6.1, "speaking_wps": 3.7, "dynamic_range_db": 11})  -> {"score": 3, "of": 3, ...}
    rank_audition_takes([{"voice": "x", "profile": {...}}])  -> best first
"""

from __future__ import annotations

import re

from explainer_engine.edit import rhythm_profile
from explainer_engine.standards import sourced_rules as SR

TAG = re.compile(r"\[([a-z][a-z ]{1,24})\]")
CAPS = re.compile(r"\b[A-Z]{2,}\b")
ACRONYMS = frozenset({"US", "USA", "UK", "EU", "UN", "TV", "AI", "DNA", "BC", "AD", "NATO", "USSR", "OK", "CEO", "GDP", "CIA", "FBI"})


def _zone_of(line: dict, total_s: float, profile_name: str) -> dict:
    prof = rhythm_profile.get_profile(profile_name)
    if line.get("zone"):
        for z in prof["zones"]:
            if z["id"] == line["zone"]:
                return z
        raise KeyError(f"unknown zone {line['zone']!r}")
    return rhythm_profile.zone_at_time(float(line.get("start_s", 0.0)), total_s=total_s, profile_name=profile_name)


def allowed_tags(zone_id: str, *, profile_name: str = "mrbeast_animated") -> list[str]:
    for z in rhythm_profile.get_profile(profile_name)["zones"]:
        if z["id"] == zone_id:
            return list(z["tts_tags"])
    raise KeyError(f"unknown zone {zone_id!r}")


def stressed_words(sentence: str) -> list[str]:
    return [w for w in CAPS.findall(sentence) if w not in ACRONYMS]


def format_line_for_tts(line: dict, *, total_s: float = 720.0, profile_name: str = "mrbeast_animated") -> str:
    """The text to send: the line's own tags kept, else the zone's first tag once at the start. The calm zone gets none
    unless the line carries one (its default read is the narrator's own)."""
    text = line["text"].strip()
    zone = _zone_of(line, total_s, profile_name)
    if TAG.search(text) or zone["mode"] == "calm_story":
        return text
    return f"[{zone['tts_tags'][0]}] {text}"


def check_prosody_plan(lines: list[dict], *, total_s: float = 720.0, profile_name: str = "mrbeast_animated") -> list[dict]:
    """HR-01 a tag the zone does not allow; HR-02 too many stressed words in a sentence; HR-03 more tags in a clause than
    BP-171 allows; HR-04 a read chunk over BP-171's character or second limit (lines with ``chunk`` ids are summed)."""
    caps_lo, caps_hi = SR.T("BP-171", "caps_words_per_sentence")
    max_tags = SR.T("BP-171", "max_tags_per_clause")
    out: list[dict] = []

    def add(rule, where, detail):
        out.append({"rule": rule, "severity": SR.level("BP-171", "REVIEW"), "where": where, "detail": detail})

    chunks: dict[str, list[float]] = {}
    for i, line in enumerate(lines):
        where = str(line.get("id", i))
        zone = _zone_of(line, total_s, profile_name)
        text = line["text"]
        for tag in TAG.findall(text):
            if tag not in zone["tts_tags"]:
                add("HR-01", where, f"[{tag}] is not in the {zone['id']} palette {zone['tts_tags']}")
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            n = len(stressed_words(sentence))
            if n > caps_hi:
                add("HR-02", where, f"{n} stressed capital words in one sentence (max {caps_hi}): the read clips or distorts")
            for clause in re.split(r"[,;:]", sentence):
                if len(TAG.findall(clause)) > max_tags:
                    add("HR-03", where, f"{len(TAG.findall(clause))} tags in one clause (max {max_tags})")
        if "chunk" in line:
            c = chunks.setdefault(str(line["chunk"]), [0, 0.0])
            c[0] += len(text)
            c[1] += float(line.get("seconds", 0.0))
    for cid, (chars, secs) in chunks.items():
        if chars > SR.T("BP-171", "chunk_reset_max_chars") or secs > SR.T("BP-171", "chunk_reset_max_s"):
            add("HR-04", f"chunk {cid}", f"{chars} characters / {secs:.0f} s: reset the read before "
                                          f"{SR.T('BP-171', 'chunk_reset_max_chars')} characters or {SR.T('BP-171', 'chunk_reset_max_s'):.0f} s")
    return out


def hype_score(profile: dict) -> dict:
    """Three measured properties of an audition take against BP-171: pitch range, active speech pace, loudness range."""
    wlo, whi = SR.T("BP-171", "speaking_wps_band")
    dlo, dhi = SR.T("BP-171", "dynamic_range_db_band")
    checks = {"f0_range": profile.get("f0_iqr_st", 0.0) >= SR.T("BP-171", "f0_range_st_min"),
              "speaking_pace": wlo <= profile.get("speaking_wps", 0.0) <= whi,
              "dynamic_range": dlo <= profile.get("dynamic_range_db", 0.0) <= dhi}
    return {"score": sum(checks.values()), "of": len(checks), "checks": checks}


def rank_audition_takes(takes: list[dict]) -> list[dict]:
    """Best first by hype score, then by the pitch range; each take is ``{"voice", "profile"}``. The ear of the creator decides (VC-08)."""
    scored = [dict(t, hype=hype_score(t["profile"])) for t in takes]
    return sorted(scored, key=lambda t: (-t["hype"]["score"], -t["profile"].get("f0_iqr_st", 0.0)))
