"""Gemini's checks of the short story, the script and the video script (build item 2; GC-26, spec Q13-Q15, P1-P4).

- ``render_check``: the P1, P2 or P3 message for the episode's current artefact, plus its Drive copies
  (``drive/episodes/<id>/short_story.md``, ``script.md``, ``claim_map.md``) that the later checks read.
- ``intake_review``: Gemini's answer in the form of ``07_REVIEW_PROTOCOL.md`` -> ``reviews/<stage>_round<n>_gemini.md``
  (the answer as it came) and the record ``reviews/<stage>.json`` (findings and their state).
- ``reply``: Claude's ACCEPT / REJECT / NOTED per finding -> the P4 message; every REJECT is a disagreement record
  (the claim, Gemini's source, Claude's source and reason).
- ``intake_reply``: FIXED / NOT FIXED / CONCEDE / HOLD and DEADLOCK blocks; a deadlock (or anything still held after reply
  round 2: there is no round 3) becomes a decision card for the creator, ``reviews/<stage>_card_<F>.json``.
- ``decide``: the creator's pick on a card, with his message id.
- ``stage_status``: PASS only when no BLOCKER and no disagreement is open, and the artefact is the one that was checked.

Finding states: open -> accepted | rejected | noted -> fixed | conceded | held | deadlock -> decided.
Closed = fixed, conceded, noted, decided (and every finding of an APPROVE or APPROVE_WITH_NOTES review that is not a
BLOCKER and that Claude did not reject).
"""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_text_atomic
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import gate as GT
from explainer_engine.gemini_task import report as RP
from explainer_engine.gemini_task import texts as TX

STAGES = {"short_story": "P1", "script": "P2", "video_script": "P3"}
BEFORE = {"script": "short_story", "video_script": "script"}
CLOSED = ("fixed", "conceded", "noted", "decided")


def reviews_dir(root: Path) -> Path:
    return Path(root) / "reviews"


def record_path(root: Path, stage: str) -> Path:
    return reviews_dir(root) / f"{stage}.json"


def record(root: Path, stage: str) -> dict:
    _stage(stage)
    return EP.read_json(record_path(root, stage), {"stage": stage, "rounds": [], "findings": {}, "replies": [],
                                                   "deadlocks": [], "sha8": None})


def _save(root: Path, stage: str, rec: dict) -> None:
    EP.save_json(record_path(root, stage), rec)


def _stage(stage: str) -> None:
    if stage not in STAGES:
        raise ContractError(f"stage must be one of {tuple(STAGES)}, not {stage!r}")


# --- the artefacts -------------------------------------------------------------------------------------------------
def script_text(script: dict) -> str:
    """The script as P2 reads it: one line per spoken line, ``S03 | NARRATOR | ...`` or ``S03 | KAEL to MIRA | ...``, each
    scene's header on the line before its first spoken line."""
    names = {c["character_id"]: c["name"] for c in (script.get("world_bible") or {}).get("characters", [])}
    segs = {s["segment_id"]: s for s in script.get("segments", [])}
    out, last = [], None
    for ln in script.get("audio_lines", []):
        sid = ln.get("segment_id")
        if sid != last:
            seg = segs.get(sid, {})
            out.append(f"{sid} | SCENE | {seg.get('title', '')}: {seg.get('narrative_purpose', '')}".rstrip())
            last = sid
        if ln.get("speaker_type") == "narrator":
            who = "NARRATOR"
        else:
            who = names.get(ln.get("speaker_id"), ln.get("speaker_id") or "?").upper()
            if ln.get("addressee_id"):
                who += " to " + names.get(ln["addressee_id"], ln["addressee_id"]).upper()
        out.append(f"{sid} | {who} | {ln.get('text', '').strip()}")
    return "\n".join(out)


def artefact(root: Path, stage: str) -> str:
    root = Path(root)
    if stage == "short_story":
        p = root / "story" / "short_story.md"
        if not p.is_file():
            raise ContractError(f"{p} does not exist: the short story comes first (OR-15)")
        return p.read_text(encoding="utf-8").strip()
    if stage == "script":
        p = root / "story" / "script.md"
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
        _, script = EP.load(root)
        return script_text(script)
    from explainer_engine.gemini_task import queue as QU
    return json.dumps(QU.shot_list(QU.load(root)), ensure_ascii=False, indent=1)


def _drive_copies(root: Path, episode_id: str, stage: str) -> None:
    d = EP.drive_dir(root) / "episodes" / episode_id
    d.mkdir(parents=True, exist_ok=True)
    for cand in (Path(root) / "story" / "claim_map.md", Path(root) / "research" / "claim_map.md"):
        if cand.is_file():
            write_text_atomic(d / "claim_map.md", cand.read_text(encoding="utf-8"))
            break
    if stage in ("script", "video_script"):      # the approved story is on Drive before the script is checked
        write_text_atomic(d / "short_story.md", artefact(root, "short_story") + "\n")
    if stage == "video_script":
        write_text_atomic(d / "script.md", artefact(root, "script") + "\n")


def render_check(root: Path, stage: str) -> dict:
    _stage(stage)
    root = Path(root)
    GT.require(f"the {stage} check")
    if stage in BEFORE and stage_status(root, BEFORE[stage])["status"] != "PASS":
        raise ContractError(f"the {BEFORE[stage]} check has not passed: {stage} waits (GC-26)")
    man, _ = EP.load(root)
    lk = EP.look(man)
    era = EP.era_line(man, lk)
    text = artefact(root, stage)
    s8 = TX.sha8(text)
    rec = record(root, stage)
    rounds = rec["rounds"]
    rnd = rounds[-1]["round"] if rounds and rounds[-1]["sha8"] == s8 and not rounds[-1].get("answered") else len(rounds) + 1
    key = {"short_story": "short_story", "script": "script", "video_script": "shot_list_json"}[stage]
    vals = {"episode_id": man["episode_id"], "sha8": s8, "round": rnd, "era_line": era, key: text,
            "drive_root": EP.config()["drive_root"]}
    msg = TX.render(STAGES[stage], vals, lk["never_words"])
    _drive_copies(root, man["episode_id"], stage)
    out = EP.work(root) / "messages" / f"{stage}_round{rnd}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(out, msg + "\n")
    if not (rounds and rounds[-1]["round"] == rnd):
        rounds.append({"round": rnd, "sha8": s8, "sent_at": EP.now()})
    _save(root, stage, rec)
    return {"stage": stage, "round": rnd, "sha8": s8, "message": str(out.relative_to(root))}


# --- intake of a review ----------------------------------------------------------------------------------------------
def intake_review(root: Path, stage: str, answer_text: str) -> dict:
    _stage(stage)
    root = Path(root)
    man, _ = EP.load(root)
    rec = record(root, stage)
    if not rec["rounds"]:
        raise ContractError(f"no {stage} check was sent")
    last = rec["rounds"][-1]
    rv = RP.parse_review(answer_text)
    if rv["stage"] != stage or rv["episode_id"] != man["episode_id"]:
        raise ContractError(f"the answer is a review of {rv['stage']} / {rv['episode_id']}, not {stage} / {man['episode_id']}")
    if rv["sha8"] != last["sha8"] or rv["round"] != last["round"]:
        raise ContractError(f"the answer reviews sha {rv['sha8']} round {rv['round']}; the check sent was sha "
                            f"{last['sha8']} round {last['round']}")
    raw = reviews_dir(root) / f"{stage}_round{rv['round']}_gemini.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(raw, answer_text.strip() + "\n")
    last.update({"answered": EP.now(), "verdict": rv["verdict"], "story_first": rv["story_first"],
                 "measured": rv["measured"], "not_checked": rv["not_checked"], "notes": rv["notes"],
                 "file": str(raw.relative_to(root))})
    rec["findings"] = {f["id"]: dict(f, state="open", round=rv["round"]) for f in rv["findings"]}
    rec["replies"], rec["deadlocks"] = [], []
    rec["sha8"] = rv["sha8"]
    _save(root, stage, rec)
    return {"stage": stage, "verdict": rv["verdict"], "findings": len(rv["findings"]),
            "blockers": [f["id"] for f in rv["findings"] if f["severity"] == "BLOCKER"],
            "downgraded": [f["id"] for f in rv["findings"] if f.get("downgraded")], "status": stage_status(root, stage)}


# --- Claude's reply (P4) ---------------------------------------------------------------------------------------------
def reply(root: Path, stage: str, decisions: dict) -> dict:
    """``decisions``: finding id -> {"action": ACCEPT, "change": "..."} | {"action": REJECT, "source": "...", "reason":
    "..."} | {"action": NOTED}. Round 1 answers every open finding; round 2 answers the held and NOT FIXED ones."""
    _stage(stage)
    root = Path(root)
    GT.require(f"the {stage} reply")
    man, _ = EP.load(root)
    lk = EP.look(man)
    rec = record(root, stage)
    if not rec["findings"]:
        raise ContractError(f"{stage}: no findings to reply to")
    rnd = len(rec["replies"]) + 1
    if rnd > 2:
        raise ContractError(f"{stage}: there is no reply round 3; open findings go to the creator as cards")
    if rnd == 1:     # a REVISE review: every finding; an approving one: Claude may let a SHOULD or IDEA stand
        due = [fid for fid, f in rec["findings"].items() if f["state"] == "open"
               and (f["severity"] == "BLOCKER" or not _approving(rec))]
    else:
        due = [fid for fid, f in rec["findings"].items() if f["state"] in ("held", "open")]
    if not decisions:
        raise ContractError(f"{stage}: nothing to reply")
    missing = [fid for fid in due if fid not in decisions]
    if missing:
        raise ContractError(f"{stage} reply round {rnd}: no answer for {missing}")
    lines, changed = [], False
    for fid in sorted(decisions, key=lambda x: int(x[1:])):
        f = rec["findings"].get(fid)
        if f is None:
            raise ContractError(f"{stage}: no finding {fid}")
        d = decisions[fid]
        act = str(d.get("action", "")).upper()
        if act == "ACCEPT":
            if not d.get("change"):
                raise ContractError(f"{fid}: ACCEPT names the change made, in one line")
            lines.append(f"{fid} | ACCEPT | {d['change']}")
            f["state"], f["claude"] = "accepted", {"action": "ACCEPT", "change": d["change"], "round": rnd}
            changed = True
        elif act == "REJECT":
            if not d.get("source") or not d.get("reason"):
                raise ContractError(f"{fid}: REJECT needs Claude's source and a reason (Q14)")
            lines.append(f"{fid} | REJECT | {d['source']} | {d['reason']}")
            f["state"] = "rejected"
            f["claude"] = {"action": "REJECT", "source": d["source"], "reason": d["reason"], "round": rnd}
            f["disagreement"] = {"claim": f"{f['quote']}: {f['problem']}", "gemini_source": f.get("source"),
                                 "claude_source": d["source"], "claude_reason": d["reason"]}
        elif act == "NOTED":
            if f["severity"] != "IDEA":
                raise ContractError(f"{fid}: NOTED is only for an IDEA; a {f['severity']} is accepted or rejected")
            lines.append(f"{fid} | NOTED")
            f["state"], f["claude"] = "noted", {"action": "NOTED", "round": rnd}
        else:
            raise ContractError(f"{fid}: action must be ACCEPT, REJECT or NOTED")
    text = artefact(root, stage)
    s8 = TX.sha8(text)
    if changed and s8 == rec["sha8"]:
        raise ContractError(f"{stage}: changes were accepted but the artefact is unchanged; make the change first")
    vals = {"episode_id": man["episode_id"], "stage": stage, "sha8": s8, "review_sha8": rec["sha8"], "reply_round": rnd,
            "replies": "\n".join(lines), "revised_text": text if changed else "NO CHANGE",
            "drive_root": EP.config()["drive_root"]}
    msg = TX.render("P4", vals, lk["never_words"])
    out = EP.work(root) / "messages" / f"{stage}_reply{rnd}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(out, msg + "\n")
    rec["replies"].append({"round": rnd, "sha8": s8, "sent_at": EP.now(), "lines": lines})
    _save(root, stage, rec)
    return {"stage": stage, "reply_round": rnd, "sha8": s8, "message": str(out.relative_to(root))}


def _approving(rec: dict) -> bool:
    return bool(rec["rounds"]) and rec["rounds"][-1].get("verdict") in ("APPROVE", "APPROVE_WITH_NOTES")


def intake_reply(root: Path, stage: str, answer_text: str) -> dict:
    _stage(stage)
    root = Path(root)
    man, _ = EP.load(root)
    rec = record(root, stage)
    if not rec["replies"] or rec["replies"][-1].get("answered"):
        raise ContractError(f"{stage}: no reply is waiting for Gemini's answer")
    last = rec["replies"][-1]
    rp = RP.parse_reply(answer_text)
    if rp["stage"] != stage or rp["round"] != last["round"] or rp["sha8"] != last["sha8"]:
        raise ContractError(f"the answer is for {rp['stage']} round {rp['round']} sha {rp['sha8']}; the reply sent was "
                            f"{stage} round {last['round']} sha {last['sha8']}")
    raw = reviews_dir(root) / f"{stage}_reply{rp['round']}_gemini.md"
    write_text_atomic(raw, answer_text.strip() + "\n")
    cards = []
    for fid, a in rp["answers"].items():
        f = rec["findings"].get(fid)
        if f is None:
            continue
        ans = a["answer"]
        if ans == "FIXED" and f["state"] == "accepted":
            f["state"] = "fixed"
        elif ans == "NOT FIXED" and f["state"] == "accepted":
            f["state"] = "open" if rp["round"] == 1 else "deadlock"
            f["not_fixed"] = a.get("quote")
            if f["state"] == "deadlock":
                cards.append(_card(root, stage, man["episode_id"], f, {
                    "claude": f"the change is made: {f['claude'].get('change')}", "claude_source": "the revised text",
                    "gemini": f"not fixed: \"{a.get('quote')}\"", "gemini_source": f.get("source"), "for_viewer": ""}))
        elif ans == "CONCEDE" and f["state"] == "rejected":
            f["state"] = "conceded"
        elif ans == "HOLD" and f["state"] == "rejected":
            same = a.get("source") and a["source"].strip() in (f.get("source") or "", f.get("disagreement", {}).get("claude_source", ""))
            if same:                                            # 07: holding on the same source is a CONCEDE
                f["state"] = "conceded"
            elif rp["round"] == 1:
                f["state"], f["hold"] = "held", {"source": a.get("source"), "why": a.get("why")}
            else:                                               # round 2 allows no HOLD: the creator decides
                f["state"] = "deadlock"
                cards.append(_card(root, stage, man["episode_id"], f, {
                    "claude": f["claude"]["reason"], "claude_source": f["claude"]["source"],
                    "gemini": a.get("why") or f["problem"], "gemini_source": a.get("source"), "for_viewer": ""}))
    for dl in rp["deadlocks"]:
        f = rec["findings"].get(dl["finding"])
        if f is None:
            continue
        f["state"] = "deadlock"
        cards.append(_card(root, stage, man["episode_id"], f, dl))
    for n in rp["new"]:
        rec["findings"][n["id"]] = dict(n, state="open", round=rp["round"], quote=n["quote"])
    last.update({"answered": EP.now(), "open": rp["open"], "stage_state": rp["stage_state"], "file": str(raw.relative_to(root))})
    if not any(f["state"] in ("accepted",) for f in rec["findings"].values()):
        rec["sha8"] = last["sha8"]                              # Gemini has seen the revised text
    rec["deadlocks"] += [c["finding"] for c in cards]
    _save(root, stage, rec)
    return {"stage": stage, "round": rp["round"], "cards": [c["path"] for c in cards], "status": stage_status(root, stage)}


def _card(root: Path, stage: str, episode_id: str, f: dict, dl: dict) -> dict:
    """The decision card of a deadlock (GC-26): both positions with their sources; the creator picks A or B."""
    card = {"schema": "gemini_deadlock_card/1", "episode_id": episode_id, "stage": stage, "finding": f["id"],
            "severity": f["severity"], "quote": f.get("quote"), "problem": f.get("problem"),
            "question": f"{stage} {f['id']}: which version stays?",
            "options": [{"label": "A: Claude's version", "consequence": dl.get("for_viewer") and dl["for_viewer"].split(";")[0]
                         or dl.get("claude") or "", "position": dl.get("claude"), "source": dl.get("claude_source")},
                        {"label": "B: Gemini's version", "consequence": (dl.get("for_viewer") or "").split(";")[-1].strip()
                         or dl.get("gemini") or "", "position": dl.get("gemini"), "source": dl.get("gemini_source")}],
            "recommended": None, "made_at": EP.now()}
    p = reviews_dir(root) / f"{stage}_card_{f['id']}.json"
    EP.save_json(p, card)
    return {"finding": f["id"], "path": str(p.relative_to(root))}


def decide(root: Path, stage: str, fid: str, choice: str, decided_by: str) -> dict:
    """The creator's pick (A = Claude's version, B = Gemini's) on a deadlock card, with his message id."""
    _stage(stage)
    if choice.upper() not in ("A", "B"):
        raise ContractError("choice is A (Claude's version) or B (Gemini's)")
    if not decided_by:
        raise ContractError("the creator's message id is required")
    rec = record(root, stage)
    f = rec["findings"].get(fid)
    if f is None or f["state"] != "deadlock":
        raise ContractError(f"{stage} {fid} is not a deadlock")
    f["state"], f["decision"] = "decided", {"choice": choice.upper(), "by": decided_by, "at": EP.now()}
    _save(root, stage, rec)
    return {"stage": stage, "finding": fid, "choice": choice.upper(),
            "next": "make Gemini's change and check the stage again" if choice.upper() == "B" else "keep Claude's version"}


def stage_status(root: Path, stage: str) -> dict:
    """PASS when the last review is answered, no BLOCKER is open, no disagreement is open, every accepted change was
    confirmed FIXED, and the artefact is the one Gemini saw last."""
    _stage(stage)
    rec = record(root, stage)
    if not rec["rounds"] or not rec["rounds"][-1].get("answered"):
        return {"status": "NOT_RUN", "why": "no answered check", "sha8": None}
    approving = _approving(rec)
    open_ = []
    for fid, f in rec["findings"].items():
        st = f["state"]
        if st in CLOSED:
            continue
        if st == "open" and f["severity"] != "BLOCKER" and approving:
            continue                       # a SHOULD or IDEA of an approving review that Claude let stand
        open_.append(f"{fid} {f['severity']} {st}")
    if rec["replies"] and not rec["replies"][-1].get("answered"):
        open_.append("a reply is waiting for Gemini's answer")
    try:
        current = TX.sha8(artefact(root, stage))
    except ContractError as e:
        return {"status": "NOT_RUN", "why": str(e), "sha8": rec["sha8"]}
    if current != rec["sha8"]:
        return {"status": "STALE", "why": f"the {stage} changed after Gemini's last look (sha {current} vs {rec['sha8']})",
                "sha8": rec["sha8"]}
    if open_:
        return {"status": "OPEN", "why": "; ".join(open_), "sha8": rec["sha8"]}
    return {"status": "PASS", "why": "closed", "sha8": rec["sha8"]}


def render_open(root: Path) -> dict:
    """P0: the first message of the episode's one chat (GC-10); no picture, no episode text."""
    root = Path(root)
    GT.require("opening the episode chat")
    man, _ = EP.load(root)
    lk = EP.look(man)
    era = EP.era_line(man, lk)
    vals = {"episode_id": man["episode_id"], "episode_title": man.get("title") or man["episode_id"], "era_line": era,
            "sha8": TX.sha8(era + "\n" + (man.get("title") or "")), "drive_root": EP.config()["drive_root"]}
    msg = TX.render("P0", vals, lk["never_words"])
    out = EP.work(root) / "messages" / "P0_open.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(out, msg + "\n")
    return {"message": str(out.relative_to(root)), "sha8": vals["sha8"]}
