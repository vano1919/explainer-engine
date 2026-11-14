"""Helper visuals fit their words (MA-09, the creator 2026-11-14): the director picks the form of every ``map_action`` shot from
what the narration says at that moment, and writes why.

D-93 (the creator, 2026-11-01) made 10 % of the runtime "Python helper visuals: maps, progress, calculations or anything else".
In the Truce 1914 demo every helper shot was a map, because no rule looked at the form. The creator's word on the fix
(2026-11-14 14:15 UTC): variety matters, but it must be logical; nothing goes into a video for the sake of variety, the topic
and the script must call for it. So this module is a director criterion, never a quota:

- ``cues(text, places)``: what the words of the shot call for: ``place`` (a place of the episode or a word of geography or
  movement), ``number`` (a quantity: digits that are not a year, hundred, thousand, percent, counted, estimate), ``comparison``
  (than, versus, twice, outnumbered ...) and ``time`` (a month, a date, days, weeks, until, a deadline).
- ``shown(shot)``: the forms the shot's ``actions`` draw: ``map`` (anything anchored to a place, or a zoom), ``counter``,
  ``comparison`` (``bar_grow``, ``split_compare``), ``progress`` (``progress_bar``, ``milestone``) and ``date`` (a label that is a
  date).
- ``choose(shot, script, places)``: the director's pick with its reason, deterministic: a number the words name is shown as a
  number (a comparison when the words compare), time running out is a progress bar, places and movement are a map; a map under
  number words stays the ground when the words also name a place.
- ``findings`` / ``check_rows(script, places)``: REVIEW rows where the form does not serve the words. Repeating maps is right when the script is
  about places and movement: no row ever counts forms or asks for a minimum of types.

The forms are the ones the map renderer draws (``maps/actions.KINDS``): a form the renderer lacks (a timeline axis) is never
asked for.
"""
from __future__ import annotations

import re

from explainer_engine.maps import actions as MA

FORMS = ("map", "counter", "comparison", "progress")
CUES = ("place", "number", "comparison", "time")

PLACE_ACTIONS = set(MA.PLACE_KINDS) | {"zoom", "marker_travel", "supply_state", "snap"}
FORM_OF = {"counter": "counter", "bar_grow": "comparison", "split_compare": "comparison", "progress_bar": "progress",
           "milestone": "progress"}

MONTHS = r"january|february|march|april|may|june|july|august|september|october|november|december"
GEO = re.compile(r"\b(north|south|east|west|northern|southern|eastern|western|front|frontier|border\w*|river\w*|sea|seas|coast\w*|"
                 r"shore\w*|trench\w*|line of|lines? of trenches|march\w*|advanc\w+|retreat\w*|spread\w*|route\w*|across|along|"
                 r"sector\w*|region\w*|province\w*|valley\w*|mountain\w*|island\w*|city|cities|town\w*|village\w*|countr\w+|"
                 r"continent\w*|territor\w+|miles? (away|apart|from)|kilomet\w+ (away|apart|from)|from \w+ to \w+)\b", re.I)
YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
NUMBER = re.compile(r"\b(\d[\d,.]*|hundreds?|thousands?|millions?|billions?|dozens?|percent|per cent|counted|estimate\w*|"
                    r"tally|casualt\w+|toll)\b", re.I)
COMPARE = re.compile(r"\b(than|versus|vs|twice|double\w*|half as|times (as|more|fewer|larger|smaller)|compared|outnumber\w*|"
                     r"ratio|against\s+(?:\w+\s+){0,2}?(?:\d[\d,]*|hundreds?|thousands?|millions?))\b", re.I)
TIME = re.compile(rf"\b({MONTHS}|christmas|easter|new year|days?|weeks?|months?|years?|hours?|until|deadline|countdown|"
                  r"over by|by (the )?(end|spring|summer|autumn|fall|winter|dawn|nightfall|morning|evening))\b", re.I)
DATE_LABEL = re.compile(rf"\b({MONTHS})\b|\b(1[0-9]{{3}}|20[0-9]{{2}})\b", re.I)


def shot_text(shot: dict, script: dict) -> str:
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    return " ".join(lines.get(i, {}).get("text", "") for i in shot.get("audio_line_ids", []))


def _place_names(places: dict | None) -> list[str]:
    out = []
    for pid, p in (places or {}).items():
        for n in {str(pid).replace("_", " "), str((p or {}).get("name") or "")}:
            if len(n) >= 3:
                out.append(n.lower())
    return out


def cues(text: str, places: dict | None = None) -> dict[str, list[str]]:
    """What the words call for, with the words that show it (empty lists are left out)."""
    low = text.lower()
    found: dict[str, list[str]] = {}
    named = [n for n in _place_names(places) if re.search(rf"\b{re.escape(n)}\b", low)]
    geo = [m.group(0) for m in GEO.finditer(text)]
    if named or geo:
        found["place"] = named + geo
    nums = [m.group(0) for m in NUMBER.finditer(YEAR.sub(" ", text))]
    if nums:
        found["number"] = nums
    cmp_ = [m.group(0) for m in COMPARE.finditer(text)]
    if cmp_:
        found["comparison"] = cmp_
    tm = [m.group(0) for m in TIME.finditer(text)] + YEAR.findall(text)
    if tm:
        found["time"] = tm
    return found


def shown(shot: dict) -> set[str]:
    """The forms the shot's actions draw; ``date`` for a label that is a date."""
    out: set[str] = set()
    for a in shot.get("actions") or []:
        k = a.get("kind")
        if k in FORM_OF:
            out.add(FORM_OF[k])
        if k in PLACE_ACTIONS and (k != "label" or a.get("from")):
            out.add("map")
        if k == "label" and DATE_LABEL.search(str(a.get("label") or "")):
            out.add("date")
    return out


def choose(shot: dict, script: dict, places: dict | None = None) -> dict:
    """The director's pick for one helper shot: ``{form, also, reason, cues}``. ``also`` is a second form the words call for
    (a map as the ground under a number whose place the words name, a date chip when time moves on a map)."""
    c = cues(shot_text(shot, script), places)

    def said(k: str) -> str:
        return ", ".join(repr(w) for w in dict.fromkeys(c[k]))[:120]

    also: list[str] = []
    if "number" in c and "comparison" in c:
        form, reason = "comparison", f"the words compare quantities ({said('comparison')}; {said('number')}): bars side by side"
    elif "number" in c:
        form, reason = "counter", f"the words name a quantity ({said('number')}): the number counts up on screen"
    elif "place" in c:
        form, reason = "map", f"the words are about places or movement ({said('place')}): a map shows where"
    elif "time" in c:
        form, reason = "progress", f"the words are about time running on ({said('time')}): a bar fills or a milestone ticks"
    elif "comparison" in c:
        form, reason = "comparison", f"the words compare ({said('comparison')}): two cards side by side"
    else:
        form, reason = "map", "the words name no place, number, comparison or time: keep the episode's map as the ground"
    if form in ("counter", "comparison") and "place" in c:
        also.append("map")
    if form == "map" and "time" in c:
        also.append("date")
    return {"form": form, "also": also, "reason": reason, "cues": c}


def _helpers(script: dict) -> list[dict]:
    return [s for s in script.get("shots", []) if s.get("route") == "map_action"]


def findings(script: dict, places: dict | None = None) -> list[dict]:
    """Per helper shot: the mismatches between what the words call for and what the shot draws (all REVIEW)."""
    out = []
    for s in _helpers(script):
        sid = s["shot_id"]
        text = shot_text(s, script)
        c = cues(text, places)
        have = shown(s)
        pick = choose(s, script, places)

        def add(check: str, msg: str) -> None:
            out.append({"rule": "MA-09", "check": check, "shot_id": sid, "level": "REVIEW", "message": msg, "suggest": pick["form"],
                        "suggest_reason": pick["reason"], "helper_reason": s.get("helper_reason")})
        if not s.get("helper_reason"):
            add("reason_missing", "no helper_reason: the director writes why this form serves these words")
        if "number" in c and not have & {"counter", "comparison", "progress"}:
            add("number_not_shown", f"the words name a quantity ({', '.join(c['number'][:3])}) but the shot shows no number")
        if "comparison" in c and "number" in c and "comparison" not in have and "counter" not in have:
            add("comparison_not_shown", f"the words compare quantities ({', '.join(c['comparison'][:3])}) but nothing on screen compares them")
        if have == {"map"} or have == {"map", "date"}:
            if "place" not in c:
                called = ", ".join(f"{k} {c[k][:2]}" for k in c) or "nothing a helper can show"
                add("map_without_place", f"a map under words that name no place or movement (they call for {called})")
        if have and "map" not in have and "place" in c and not c.keys() - {"place"}:
            add("card_under_place_words", f"a card under words that are only about places ({', '.join(c['place'][:3])}): a map shows where")
    return out


def check_rows(script: dict, places: dict | None = None) -> list[dict]:
    """The G1 rows: ``helper_form_fits_words`` (REVIEW on any mismatch) and ``helper_forms_seen`` (information only, always
    PASS: the forms are counted for a person to read, never against a quota)."""
    from explainer_engine.qa import gates as G
    helpers = _helpers(script)
    if not helpers:
        return [G.row("helper_form_fits_words", True, "no map_action shot", 0)]
    f = findings(script, places)
    seen: dict[str, int] = {}
    for s in helpers:
        for k in sorted(shown(s) - {"date"}) or ["none"]:
            seen[k] = seen.get(k, 0) + 1
    detail = "; ".join(f"{x['shot_id']} {x['check']}: {x['message']} -> {x['suggest']}" for x in f[:8])
    return [G.row("helper_form_fits_words", not f, f"{len(f)} finding(s) on {len(helpers)} helper shot(s)"
                  + (f": {detail}" if detail else ""), [f"{x['shot_id']}:{x['check']}" for x in f][:20], level=G.REVIEW),
            G.row("helper_forms_seen", True, "forms drawn by the helper shots (information, no quota): "
                  + ", ".join(f"{k} {v}" for k, v in sorted(seen.items())), seen)]


def report(script: dict, places: dict | None = None) -> list[dict]:
    """One row per helper shot for the director's table: words, cues, what it draws, the pick and its reason."""
    rows = []
    for s in _helpers(script):
        pick = choose(s, script, places)
        rows.append({"shot_id": s["shot_id"], "words": shot_text(s, script), "cues": pick["cues"], "shown": sorted(shown(s)),
                     "pick": pick["form"], "also": pick["also"], "reason": pick["reason"],
                     "helper_form": s.get("helper_form"), "helper_reason": s.get("helper_reason")})
    return rows


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description="MA-09: does each helper shot's form fit its words? (no quota)")
    ap.add_argument("episode", help="episode folder (episodes/<id>)")
    a = ap.parse_args(argv)
    root = Path(a.episode)
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    places = json.loads((root / "episode.json").read_text(encoding="utf-8")).get("places") or {}
    out = {"shots": report(script, places), "findings": findings(script, places)}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
