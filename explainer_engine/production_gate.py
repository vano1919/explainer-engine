"""Where is this episode on the production gates? (docs/PRODUCTION_RULES.md section 2)

    python -m explainer_engine.production_gate examples/stone_age/day1_v4

Reads the episode folder (``narration_tts.txt``, ``narration.txt``, ``words.json``, ``shots.json``, the ``look.json`` one level
up, ``pod_job.json``, ``pictures/report.json``) and prints one line per gate: PASS, BLOCKED (a rule fails: fix it) or WAIT
(the step is not done yet, or needs the creator's yes first) with the next action. Exit code 1 when any gate is BLOCKED.
Free: it reads files and runs the free checks only.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from .audio.scribe_words import norm, strip_tags
from .edit import shot_rules
from .scripting import narration_lint

MIN_COVERAGE = 0.97


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _words_of(text: str) -> list[str]:
    out: list[str] = []
    for tok in strip_tags(text).split():
        out += norm(tok)
    return out


def rulebook_state(rules_path: Path, script: Path) -> tuple[str, str, str]:
    """How far the episode rulebook's checkpoints pass (docs/EPISODE_STANDARDS.md section 1)."""
    from .standards import rulebook as R
    reached = None
    for cp in R.CHECKPOINTS:
        fails = [f for f in R.gate(rules_path, cp, script) if f["severity"] == "FAIL"]
        if fails:
            rules = sorted({f["rule"] for f in fails})
            if reached is None:
                return "BLOCKED", f"provisional: {len(fails)} FAIL ({', '.join(rules)})", "standards check, fix the FAILs"
            return "PASS", f"passes up to {reached}; {cp}: {len(fails)} FAIL ({', '.join(rules)})", \
                f"before {cp}: re-check, then standards stamp --at {cp}"
        reached = cp
    return "PASS", "passes every checkpoint up to final_qa", ""


def script_gates(day: Path, run_path: Path | None = None) -> list[dict]:
    """The gates of a D-43 episode, read from what that flow writes: the production script, ``words.json``, ``timed.json``,
    the paint plans in ``pictures/plans`` and the run ledger (audit 2026-10-19 M2: gates 1-6 used to read ``shots.json`` and
    ``pictures/report.json``, which this flow never writes, so they could never pass)."""
    from .core.ledger import Run
    from .imagegen import plan as _plan
    from .production import script as _ps
    from .production import timing as _pt
    from .production import validate as _pv
    out: list[dict] = []

    def add(n, name, status, detail, nxt=""):
        out.append({"gate": n, "name": name, "status": status, "detail": detail, "next": nxt})

    rules_path = day / "episode_rules.json"  # R: the episode rulebook (D-51)
    if rules_path.exists():
        add("R", "episode rulebook", *rulebook_state(rules_path, day / "production_script.json"))
    else:
        add("R", "episode rulebook", "WAIT", "no episode_rules.json", "agent episode-standards-director (OR-11)")
    doc = _ps.load(day / "production_script.json")
    if _ps.schema_errors(doc):
        add(0, "production script", "BLOCKED", f"{len(_ps.schema_errors(doc))} schema errors", "python -m explainer_engine.production validate")
        return out
    pic_dirs = [day / d for d in doc.get("picture_dirs", [])]
    from .scripting import claims as _claims
    found = _pv.check_script(doc, picture_dirs=pic_dirs or None, claim_map=_claims.load_map(day / "production_script.json"))
    fails = [f for f in found if f["severity"] == "FAIL"]
    add(0, "production script", "BLOCKED" if fails else "PASS", f"{_pv.summary(found)} (PV rules)",
        "fix the FAILs: python -m explainer_engine.production validate" if fails else "answer every REVIEW")
    from .production import editorial_gate as _eg  # 0.5: sources and an independent review bound to this script's hash
    eg = _eg.check(day / "production_script.json", day / "editorial_review.json")
    ef = [f for f in eg if f["severity"] == "FAIL"]
    add(0.5, "editorial quality", "BLOCKED" if ef else "WAIT" if eg else "PASS", f"{len(ef)} FAIL, {len(eg) - len(ef)} REVIEW (EG rules)",
        "add editorial v1 and editorial_review.json: python -m explainer_engine.production.editorial_gate" if eg else "approved for production")
    lint = narration_lint.lint(_ps.tts_text(doc))
    lf = [f for f in lint if f["severity"] == "FAIL"]
    add(1, "script for the ear", "BLOCKED" if lf else "PASS", f"{len(lf)} FAIL, {len(lint) - len(lf)} REVIEW (narration_lint)",
        "fix the FAILs" if lf else "answer every REVIEW in one line")
    words = _json(day / "words.json")
    if not words:
        add(2, "full read and timings", "WAIT", "no words.json", "test read, then the full read (estimate, ask first)")
    else:
        a = _words_of(_ps.narration_text(doc))
        b = [x for w in words["words"] for x in norm(w["w"])]
        ratio = difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()
        cov = float(words.get("coverage", 1.0))
        if ratio < MIN_COVERAGE:
            add(2, "full read and timings", "WAIT", f"words.json matches this text only {ratio:.0%}: timings of another read",
                "full read of this text, then production words")
        elif cov < MIN_COVERAGE:
            add(2, "full read and timings", "BLOCKED", f"coverage {cov:.1%} < {MIN_COVERAGE:.0%}", "listen and repair")
        else:
            add(2, "full read and timings", "PASS", f"text match {ratio:.0%}, coverage {cov:.1%}")
    if not words:
        add(3, "shot plan on the read", "WAIT", "no read yet; the board runs on the estimated read inside gate 0")
    else:
        timed = _pt.time_script(doc, words)
        tf = [f for f in _pv.check_timed(timed, doc, picture_dirs=pic_dirs or None) if f["severity"] == "FAIL"]
        add(3, "shot plan on the read", "BLOCKED" if tf else "PASS", f"{len(timed['shots'])} shots, {len(tf)} FAIL",
            "; ".join(sorted({f["rule"] for f in tf})))
    heroes = [f for f in fails if f["rule"] == "PV-26"]
    add(4, "style bridge and hero references", "BLOCKED" if heroes else "PASS" if not fails else "WAIT",
        f"{len(heroes)} pictures without a reference of their hero (PV-26)" if heroes else
        "PV-26 references in place" if not fails else "waits for gate 0",
        "the creator approves the style bridge once per episode")
    pics, _ = _ps.pictures(doc)
    used = {k: v for k, v in pics.items() if v.get("uses")}
    have = {k for k, v in used.items() if v.get("file") or any((d / f"{k}.png").exists() for d in pic_dirs + [day / "pictures"])}
    todo = sorted(set(used) - have)
    run = Run.open(run_path) if run_path and Path(run_path).exists() else None
    plans = [_json(f) for f in sorted((day / "pictures" / "plans").glob("*.json"))]
    waiting = [p for p in plans if not (run and run.approved(p["id"], p["hash"]))]
    add(5, "picture plans", "PASS" if not todo else "WAIT",
        f"{len(todo)} pictures to paint, {len(plans)} plans, {len(waiting)} waiting for the creator's provider choice",
        "" if not todo else "paint plan (free), ask the creator which provider, paint approve, paint run")
    if todo:
        add(6, "pictures", "WAIT", f"{len(have)} of {len(used)} pictures exist", "contact sheet looked at after each batch")
    else:
        add(6, "pictures", "PASS", f"all {len(used)} pictures exist", "review the contact sheet by eye")
    add(7, "animatic and render", "WAIT", "production run, after gates 0-6")
    add(8, "QA", *qa_state(day))
    add(9, "approval #2", *approval_state(day))
    return out


def _find(day: Path, name: str) -> Path | None:
    for p in (day / name, day / "render" / name):
        if p.exists():
            return p
    return next(iter(sorted(day.glob(f"**/{name}"))), None)


def qa_state(day: Path) -> tuple[str, str, str]:
    """Gate 8 from what QA writes: ``assemble_report.json`` (the mix's verdicts, BP-50 / BP-51) and ``scorecard.json`` (the
    seven-point test). Missing = WAIT, any FAIL = BLOCKED."""
    rep, card = _find(day, "assemble_report.json"), _find(day, "scorecard.json")
    if rep is None and card is None:
        return "WAIT", "no assemble_report.json and no scorecard.json", "render, then python -m explainer_engine.qa.scorecard <folder>"
    problems, notes = [], []
    if rep is None:
        notes.append("no assemble_report.json")
    else:
        audio = (_json(rep) or {}).get("audio", {})
        for key in ("loudness_verdict", "true_peak_verdict", "ldr_verdict"):
            if audio.get(key) == "FAIL":
                problems.append(key.replace("_verdict", ""))
        notes.append(f"mix {audio.get('lufs', '?')} LUFS {audio.get('loudness_verdict', 'unjudged')}, "
                     f"true peak {audio.get('true_peak', '?')} {audio.get('true_peak_verdict', 'unjudged')}")
    if card is None:
        notes.append("no scorecard.json")
    else:
        rows = (_json(card) or {}).get("rows", [])
        bad = [f"{r['id']} {r['name']}" for r in rows if r.get("status") == "FAIL"]
        problems += bad
        notes.append(f"scorecard {len(rows)} rows, {len(bad)} FAIL, {sum(r.get('status') == 'REVIEW' for r in rows)} REVIEW")
    if problems:
        return "BLOCKED", "; ".join(notes), "fix: " + ", ".join(problems)
    if rep is None or card is None:
        return "WAIT", "; ".join(notes), "render and run the scorecard"
    return "PASS", "; ".join(notes), "the creator watches the whole video once (rows marked 'creator decides')"


def approval_state(day: Path) -> tuple[str, str, str]:
    """Gate 9: the creator's recorded approval #2 in ``publish.json`` (PC-08, invariant 4)."""
    pub = _json(day / "publish.json")
    if pub is None:
        return "WAIT", "no publish.json", "write the publish/1 package (qa/publish_check), then the creator's approval"
    ok = pub.get("approval") or {}
    if ok.get("by") and ok.get("ref"):
        return "PASS", f"approved by {ok['by']} ({ok['ref']})", "publish stage (unlisted, D-57); public is the creator's click"
    return "WAIT", "publish.json has no approval {by, ref}", "the creator's recorded approval #2 (PC-08)"


def gates(day: Path, look_path: Path | None = None, run_path: Path | None = None) -> list[dict]:
    if (day / "production_script.json").exists():
        return script_gates(day, run_path)
    look_path = look_path or day.parent / "look.json"
    look = _json(look_path) or {}
    out: list[dict] = []

    def add(n, name, status, detail, nxt=""):
        out.append({"gate": n, "name": name, "status": status, "detail": detail, "next": nxt})

    # legacy day folders (narration_tts.txt, shots.json, look.json): the D-43 flow goes through script_gates
    if (day / "episode_rules.json").exists():  # R: a rulebook written before the script (D-51)
        add("R", "episode rulebook", *rulebook_state(day / "episode_rules.json", day / "production_script.json"))
    # 1 script
    tts = day / "narration_tts.txt"
    if not tts.exists():
        add(1, "script for the ear", "WAIT", "no narration_tts.txt", "write it with the narration-script skill")
    else:
        found = narration_lint.lint(tts.read_text(encoding="utf-8"))
        fails = [f for f in found if f["severity"] == "FAIL"]
        add(1, "script for the ear", "BLOCKED" if fails else "PASS",
            f"{len(fails)} FAIL, {len(found) - len(fails)} REVIEW (narration_lint)",
            "fix the FAILs" if fails else "answer every REVIEW in one line")
    # 2 timings belong to this text
    words = _json(day / "words.json")
    plain = day / "narration.txt"
    if not words or not plain.exists():
        add(2, "full read and timings", "WAIT", "no words.json or narration.txt", "test read, then the full read (ask first)")
    else:
        a = _words_of(plain.read_text(encoding="utf-8"))
        b = [x for w in words["words"] for x in norm(w["w"])]
        ratio = difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()
        cov = float(words.get("coverage", 1.0))
        if ratio < MIN_COVERAGE:
            add(2, "full read and timings", "WAIT", f"words.json matches this text only {ratio:.0%}: provisional timings of "
                "another read", "full read of this text, Scribe, pause_pad (ask first)")
        elif cov < MIN_COVERAGE:
            add(2, "full read and timings", "BLOCKED", f"Scribe coverage {cov:.1%} < {MIN_COVERAGE:.0%}", "listen and repair")
        else:
            add(2, "full read and timings", "PASS", f"text match {ratio:.0%}, coverage {cov:.1%}")
    # 3 shot plan
    shots = _json(day / "shots.json")
    if not shots or not words:
        add(3, "shot plan", "WAIT", "no shots.json", "run build_shots.py")
    else:
        found = shot_rules.check_shots(shots["shots"], words["words"], look)
        fails = [f for f in found if f["severity"] == "FAIL"]
        add(3, "shot plan", "BLOCKED" if fails else "PASS",
            f"{len(shots['shots'])} shots, rule base {look.get('rule_base', 1)}: {len(fails)} FAIL, {len(found) - len(fails)} REVIEW",
            "; ".join(sorted({f"{f['rule']}" for f in fails})) or "")
    # 4 style bridge
    sb = (look.get("style_bridge") or {}).get("approved")
    add(4, "style bridge", "PASS" if sb else "WAIT", f"approved {sb}" if sb else "not approved",
        "" if sb else "6 test pictures (about $0.15, ask first), composite, creator approves")
    # 5 sprites
    bank, caric = look.get("pose_bank", {}), look.get("caricatures", [])
    missing_heroes, missing_poses = set(), set()
    for s in (shots or {}).get("shots", []):
        for h in s.get("heroes", []):
            if h["name"] not in caric:
                missing_heroes.add(h["name"])
            elif h["pose"] not in bank.get(h["name"], []):
                missing_poses.add((h["name"], h["pose"]))
    if shots is None:
        add(5, "sprites", "WAIT", "no shot plan yet")
    elif missing_heroes or missing_poses:
        add(5, "sprites", "WAIT", f"{len(missing_heroes)} new heroes, {len(missing_poses)} poses to make", "sprite_needs.md (ask first)")
    else:
        add(5, "sprites", "PASS", "every hero and pose of the plan exists")
    # 6 pictures
    job, report = _json(day / "pod_job.json"), _json(day / "pictures" / "report.json")
    if report:
        bad = [r["id"] for r in report if r.get("defective")]
        add(6, "pictures", "BLOCKED" if bad else "PASS", f"{len(report)} painted, {len(bad)} defective",
            "repaint the defective ones" if bad else "review the contact sheet by eye")
    else:
        add(6, "pictures", "WAIT", f"{len((job or {}).get('pictures', []))} pictures planned, none painted",
            "after gates 4 and 5: pod run with price, units x seconds x margin and caps (ask first)")
    for n, name, hint in ((7, "animatic and render", "after gates 2, 3, 5, 6 and the compositor (D-32)"),
                          (8, "QA", "technical and editorial QA"), (9, "approval #2", "the creator's recorded approval")):
        add(n, name, "WAIT", hint)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("day")
    p.add_argument("--look")
    p.add_argument("--run", help="the run ledger (approvals of the paint plans)")
    a = p.parse_args(argv)
    rows = gates(Path(a.day), Path(a.look) if a.look else None, Path(a.run) if a.run else None)
    for r in rows:
        print(f"{r['gate']} {r['status']:7} {r['name']:24} {r['detail']}" + (f"  -> {r['next']}" if r["next"] else ""))
    return 1 if any(r["status"] == "BLOCKED" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
