"""Story rules ST-01..ST-10 (docs/STORY_ENGINE.md, D-48) on a production script's story layer (``drama`` at the top,
``drama`` per segment). Free, run by ``production validate`` before any paid step.

The creator's note on the first video (2026-10-19): the script told a less interesting story and missed what viewers
want; facts and basic human needs must be balanced. The rules turn screenwriting craft into checks a model can be held
to: one dramatic question, causality between beats (but / therefore, never "and then"), heroes with a want and a
flaw, rising stakes with a turn of value in every segment, open loops that are paid off, set-ups with pay-offs, the
needs the episode serves, and what is fact, reasoning or invention. Structure FAILs (a loop that does not exist, a
pay-off before its plant); craft is REVIEW (the creator judges the story).

    python -m explainer_engine.scripting.story_lint production_script.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MIN_NEEDS = 3
MAX_AND_THEN_SHARE = 0.0
TURN_FUNCS = {"reversal", "midpoint", "crisis", "twist", "climax"}
OPENERS = {"cold_open", "hook"}
AND_THEN = re.compile(r"^\s*(and then|after that|next,|then,|also,)", re.I)


def _f(out, rule, where, detail, sev="REVIEW"):
    out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})


def lint(doc: dict) -> list[dict]:
    out: list[dict] = []
    drama = doc.get("drama")
    segs = doc.get("segments", [])
    if not drama:
        _f(out, "ST-00", "drama", "no story layer: write drama (premise, question, promise, arcs, loops) before the lines")
        return out
    order = {s["id"]: i for i, s in enumerate(segs)}
    sd = [(s["id"], s.get("drama")) for s in segs]
    missing = [sid for sid, d in sd if not d]
    if missing:
        _f(out, "ST-00", ",".join(missing[:6]), f"{len(missing)} segment(s) without drama (function, turn)")
    # ST-01 one dramatic question, asked in the opening, answered at the end
    first = next((d for _, d in sd if d), None)
    if first and first["function"] not in OPENERS:
        _f(out, "ST-01", segs[0]["id"], "the first segment is not a cold open or hook: the question must be asked at once")
    if not drama["question"].rstrip().endswith("?"):
        _f(out, "ST-01", "drama.question", "the dramatic question is not a question")
    last = next((d for _, d in reversed(sd) if d), None)
    if last and last["function"] not in {"resolution", "button", "twist", "climax"}:
        _f(out, "ST-01", segs[-1]["id"], "the last segment does not resolve the dramatic question")
    # ST-02 causality: but / therefore, never and-then
    for i, (sid, d) in enumerate(sd):
        if not d:
            continue
        if i and d["turn"] == "start":
            _f(out, "ST-02", sid, "only the first segment may be 'start'; later ones follow by BUT or THEREFORE")
        lines = segs[i].get("lines", [])
        if i and lines and AND_THEN.match(lines[0]["text"]):
            _f(out, "ST-02", sid, f"opens with {lines[0]['text'][:24]!r}: an 'and then' join; give the cause (but / therefore)")
    turns = [d["turn"] for _, d in sd[1:] if d]
    if turns and turns.count("but") < max(1, len(turns) // 4):
        _f(out, "ST-02", "segments", f"{turns.count('but')} BUT turn(s) in {len(turns)} joins: without obstacles the story only lists "
           "(about one join in three is a BUT)")
    # ST-03 stakes and a turn of value in every segment
    for sid, d in sd:
        if d and d["function"] not in OPENERS and not d.get("stakes"):
            _f(out, "ST-03", sid, "no stakes: say what is lost if this goes wrong")
        if d and d["function"] not in {"button"} and not d.get("shift"):
            _f(out, "ST-03", sid, "no value turns (shift 'safe -> hunted'): a segment where nothing changes is cut or merged")
    # ST-04 heroes: a want and a flaw, and they speak
    arcs = drama.get("arcs", {})
    cast = doc.get("cast", {})
    for who in arcs:
        if who not in cast:
            _f(out, "ST-04", who, "arc for someone not in the cast", "FAIL")
    speakers = {ln.get("speaker") for s in segs for ln in s.get("lines", []) if ln.get("speaker")}
    for who in speakers:
        if who not in arcs:
            _f(out, "ST-04", who, "a speaking hero without an arc (want, flaw): their lines have nothing to push against")
    if not arcs:
        _f(out, "ST-04", "drama.arcs", "no hero arcs: a what-if needs someone who wants something in it")
    # ST-05 open loops opened and paid off in order, none left hanging
    loops = {lp["id"]: lp for lp in drama.get("loops", [])}
    opened, closed = {}, {}
    for sid, d in sd:
        for lid in (d or {}).get("opens", []):
            if lid not in loops:
                _f(out, "ST-05", sid, f"opens unknown loop {lid}", "FAIL")
            opened.setdefault(lid, sid)
        for lid in (d or {}).get("closes", []):
            if lid not in loops:
                _f(out, "ST-05", sid, f"closes unknown loop {lid}", "FAIL")
            elif lid not in opened:
                _f(out, "ST-05", sid, f"closes {lid} before it is opened", "FAIL")
            closed.setdefault(lid, sid)
    for lid in loops:
        if lid in opened and lid not in closed:
            _f(out, "ST-05", opened[lid], f"loop {lid} ({loops[lid]['question'][:40]!r}) is never paid off")
        if lid not in opened:
            _f(out, "ST-05", "drama.loops", f"loop {lid} is never opened")
    for i, (sid, d) in enumerate(sd[:-1]):
        if d and d["function"] not in {"resolution", "button"}:
            still_open = [x for x in opened if order[opened[x]] <= i and (x not in closed or order[closed[x]] > i)]
            if not still_open:
                _f(out, "ST-05", sid, "no loop is open at the end of this segment: nothing pulls the viewer into the next one")
    # ST-06 set-ups and pay-offs
    for p in drama.get("setups", []):
        if p["plant"] not in order or p["payoff"] not in order:
            _f(out, "ST-06", p["id"], "plant or pay-off segment does not exist", "FAIL")
        elif order[p["payoff"]] <= order[p["plant"]]:
            _f(out, "ST-06", p["id"], "paid off before (or where) it is planted", "FAIL")
    if len(segs) >= 6 and not drama.get("setups"):
        _f(out, "ST-06", "drama.setups", "no set-up / pay-off pair: plant one early detail that decides the end")
    # ST-07 turning points spread through the story
    funcs = [d["function"] for _, d in sd if d]
    if len(funcs) >= 6:
        n_turn = sum(f in TURN_FUNCS for f in funcs)
        if n_turn < 2:
            _f(out, "ST-07", "segments", f"{n_turn} turning point(s) (reversal, midpoint, crisis, twist, climax): at least 2")
        third = len(funcs) // 3
        if not any(f in TURN_FUNCS for f in funcs[third:2 * third + 1]):
            _f(out, "ST-07", "segments", "no turn in the middle third: the middle sags")
    # ST-08 human needs
    needs = drama.get("needs", [])
    if len(needs) < MIN_NEEDS:
        _f(out, "ST-08", "drama.needs", f"{len(needs)} need(s) served; name at least {MIN_NEEDS} (curiosity, stakes, humour, wonder...)")
    used = {d.get("need") for _, d in sd if d and d.get("need")}
    for n in needs:
        if n not in used:
            _f(out, "ST-08", "drama.needs", f"need {n!r} is promised but no segment serves it")
    # ST-09 objectivity: what carries each segment is labelled; invention is never the majority, facts carry claims
    shares = [d.get("claim_share") for _, d in sd if d and d.get("claim_share")]
    if shares and shares.count("invented") > len(shares) / 2:
        _f(out, "ST-09", "segments", f"{shares.count('invented')} of {len(shares)} segments are invention: the what-if must stand on facts")
    for i, (sid, d) in enumerate(sd):
        if d and d.get("claim_share") == "fact" and not any(ln.get("claims") for ln in segs[i].get("lines", [])):
            _f(out, "ST-09", sid, "labelled fact but no line carries a claim id", "FAIL")
    # ST-10 the ending pays the promise
    end = drama.get("ending")
    if not end:
        _f(out, "ST-10", "drama.ending", "no ending kind (twist, reversal, bookend, callback, open question)")
    return out


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    doc = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    found = lint(doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    n_fail = sum(f["severity"] == "FAIL" for f in found)
    print(f"{n_fail} FAIL, {len(found) - n_fail} REVIEW")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
