"""Parsers of Gemini's answers in the fixed forms of the messages (T0 REPORT, BATCH REPORT, REVIEW, REPLY).

Strict about structure, tolerant about decoration: Markdown bold, backticks, code fences and blank lines are ignored;
a missing header, a count that disagrees with its lines or an unknown status is a ContractError (the intake never
guesses, Q9).
"""
from __future__ import annotations

import re

from explainer_engine.core.errors import ContractError

SEVERITIES = ("BLOCKER", "SHOULD", "IDEA")
VERDICTS = ("APPROVE", "APPROVE_WITH_NOTES", "REVISE")


def _lines(text: str) -> list[str]:
    out = []
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line.startswith("```"):
            continue
        line = re.sub(r"^(?:>+\s*|[*\-]\s+)", "", line)   # a quote mark or a list bullet in front of a report line
        line = line.replace("**", "").replace("`", "").strip()
        if line:
            out.append(line)
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


# --- batch reports -----------------------------------------------------------------------------------------------------
BATCH_HEAD = re.compile(r"^BATCH REPORT\s+(.+?)\s*$", re.I)
MADE_LINE = re.compile(r"^MADE\s+(\d+)\s+of\s+(\d+)\s*$", re.I)
PIC_LINE = re.compile(r"^(\d+)\s*\|")


def parse_batch_report(text: str, expect: str | None = None) -> dict:
    """``{"batch": str, "items": [{k, id, status MADE|NOT MADE, refs, prompt AS GIVEN|CHANGED, changed, note, reason,
    limit}], "made": n, "total": m}``. ``expect`` (e.g. "3", "R1", "redo 2") must match the header."""
    lines = _lines(text)
    head = next((i for i, l in enumerate(lines) if BATCH_HEAD.match(l)), None)
    if head is None:
        raise ContractError("no BATCH REPORT line in the answer")
    batch = BATCH_HEAD.match(lines[head]).group(1).strip()
    if expect is not None and batch.lower() != str(expect).lower():
        raise ContractError(f"the answer reports batch {batch!r}, this intake is for {expect!r}")
    items, made_line = [], None
    for l in lines[head + 1:]:
        if MADE_LINE.match(l):
            made_line = MADE_LINE.match(l)
            break
        if not PIC_LINE.match(l):
            continue
        c = _cells(l)
        if len(c) < 3:
            raise ContractError(f"a report line has too few fields: {l!r}")
        status = c[2].upper()
        it = {"k": int(c[0]), "id": c[1], "status": status, "refs": None, "prompt": None, "changed": None, "note": None,
              "reason": None, "limit": False}
        if status == "MADE":
            for cell in c[3:]:
                key, _, val = cell.partition(":")
                key, val = key.strip().lower(), val.strip()
                if key == "refs":
                    it["refs"] = val
                elif key == "prompt":
                    up = val.upper()
                    if up.startswith("AS GIVEN"):
                        it["prompt"] = "AS GIVEN"
                    elif up.startswith("CHANGED"):
                        it["prompt"], it["changed"] = "CHANGED", val[len("CHANGED"):].strip() or "not said"
                    else:
                        raise ContractError(f"{it['id']}: prompt must be AS GIVEN or CHANGED, not {val!r}")
                elif key == "note":
                    it["note"] = None if val in ("", "-") else val
            if it["prompt"] is None:
                raise ContractError(f"{it['id']}: a MADE line must say prompt: AS GIVEN|CHANGED (GC-24)")
        elif status == "NOT MADE":
            rest = " | ".join(c[3:])
            reason = rest.split(":", 1)[1].strip() if ":" in rest else rest.strip()
            it["reason"] = reason or "not said"
            it["limit"] = "limit" in it["reason"].lower()
        else:
            raise ContractError(f"{it['id']}: status must be MADE or NOT MADE, not {c[2]!r}")
        items.append(it)
    if made_line is None:
        raise ContractError("the BATCH REPORT has no 'MADE <n> of <m>' line")
    made, total = int(made_line.group(1)), int(made_line.group(2))
    if [it["k"] for it in items] != list(range(1, len(items) + 1)):
        raise ContractError(f"report lines are not numbered 1..{len(items)} in order")
    if total != len(items):
        raise ContractError(f"the report says {total} pictures but has {len(items)} lines")
    if made != sum(it["status"] == "MADE" for it in items):
        raise ContractError(f"the report says MADE {made} but {sum(it['status'] == 'MADE' for it in items)} lines are MADE")
    return {"batch": batch, "items": items, "made": made, "total": total}


T0_HEAD = re.compile(r"^T0 REPORT\s+([0-9a-f]{8})\s*$", re.I)


def parse_t0_report(text: str) -> dict:
    """The T0 answer: header sha, MODEL/MODE, DRIVE READ/WRITE, BATCH REPORT 0, LIMIT."""
    lines = _lines(text)
    head = next((l for l in lines if T0_HEAD.match(l)), None)
    if head is None:
        raise ContractError("no 'T0 REPORT <sha8>' line in the answer")
    out = {"sha8": T0_HEAD.match(head).group(1).lower(), "model": None, "mode": None,
           "drive_read": {"ok": False, "detail": "not reported"}, "drive_write": {"ok": False, "detail": "not reported"},
           "limit": None}
    for l in lines:
        m = re.match(r"^MODEL:\s*(.*?)\s*\|\s*MODE:\s*(.*)$", l, re.I)
        if m:
            out["model"], out["mode"] = m.group(1).strip(), m.group(2).strip()
        m = re.match(r"^DRIVE (READ|WRITE):\s*(OK|FAILED)\s*(.*)$", l, re.I)
        if m:
            key = "drive_read" if m.group(1).upper() == "READ" else "drive_write"
            detail = m.group(3).strip()
            if key == "drive_read":
                q = re.search(r'"(.*)"', detail)
                detail = q.group(1) if q else detail
            out[key] = {"ok": m.group(2).upper() == "OK", "detail": detail}
        m = re.match(r"^LIMIT:\s*(.*)$", l, re.I)
        if m:
            out["limit"] = m.group(1).strip()
    if out["model"] is None:
        raise ContractError("the T0 answer has no 'MODEL: <name> | MODE: <name>' line")
    out["batch"] = parse_batch_report(text, expect="0")
    return out


# --- reviews and replies -----------------------------------------------------------------------------------------------
REVIEW_HEAD = re.compile(r"^REVIEW\s+(short_story|script|video_script)\s+(\S+)\s+([0-9a-f]{8})\s+round\s+(\d+)\s*$", re.I)
FINDING = re.compile(r"^(F\d+)\s*\|")


def parse_review(text: str) -> dict:
    """The review form of 07_REVIEW_PROTOCOL.md. A BLOCKER without a source becomes an IDEA (07: "a finding without a
    source is an IDEA"), marked ``downgraded``; a verdict that disagrees with the findings is noted, never trusted over
    them (REVISE iff a BLOCKER)."""
    lines = _lines(text)
    head = next((l for l in lines if REVIEW_HEAD.match(l)), None)
    if head is None:
        raise ContractError("no 'REVIEW <stage> <episode> <sha8> round <n>' line in the answer")
    m = REVIEW_HEAD.match(head)
    out = {"stage": m.group(1).lower(), "episode_id": m.group(2), "sha8": m.group(3).lower(), "round": int(m.group(4)),
           "verdict": None, "story_first": "", "findings": [], "measured": "", "not_checked": "", "notes": []}
    for l in lines:
        if l.upper().startswith("VERDICT:"):
            v = l.split(":", 1)[1].strip().upper().split()[0] if l.split(":", 1)[1].strip() else ""
            if v not in VERDICTS:
                raise ContractError(f"verdict must be one of {VERDICTS}, not {v!r}")
            out["verdict"] = v
        elif l.upper().startswith("STORY FIRST:"):
            out["story_first"] = l.split(":", 1)[1].strip()
        elif l.upper().startswith("MEASURED:"):
            out["measured"] = l.split(":", 1)[1].strip()
        elif l.upper().startswith("NOT CHECKED:"):
            out["not_checked"] = l.split(":", 1)[1].strip()
        elif FINDING.match(l):
            c = _cells(l)
            if len(c) < 6:
                raise ContractError(f"a finding needs id | severity | source | quote | problem | fix: {l!r}")
            sev = c[1].upper()
            if sev not in SEVERITIES:
                raise ContractError(f"{c[0]}: severity must be one of {SEVERITIES}, not {c[1]!r}")
            src = c[2].strip()
            f = {"id": c[0].upper(), "severity": sev, "source": "" if src in ("-", "") else src,
                 "quote": c[3].strip().strip('"'), "problem": c[4], "fix": " | ".join(c[5:])}
            if f["severity"] == "BLOCKER" and not f["source"]:
                f["severity"], f["downgraded"] = "IDEA", True
            out["findings"].append(f)
    if out["verdict"] is None:
        raise ContractError("the review has no VERDICT line")
    ids = [f["id"] for f in out["findings"]]
    if len(ids) != len(set(ids)):
        raise ContractError(f"finding ids repeat: {ids}")
    blockers = any(f["severity"] == "BLOCKER" for f in out["findings"])
    if blockers != (out["verdict"] == "REVISE"):
        out["notes"].append(f"the verdict {out['verdict']} does not match the findings (REVISE iff a BLOCKER); "
                            "the findings decide")
        out["verdict"] = "REVISE" if blockers else ("APPROVE_WITH_NOTES" if out["findings"] else "APPROVE")
    return out


REPLY_HEAD = re.compile(r"^REPLY\s+(short_story|script|video_script)\s+(\S+)\s+([0-9a-f]{8})\s+round\s+([12])\s*$", re.I)
DEADLOCK_HEAD = re.compile(r"^DEADLOCK\s+(short_story|script|video_script)\s+(\S+)\s+(F\d+)\s*$", re.I)


def parse_reply(text: str) -> dict:
    """The P4 answer: per finding FIXED / NOT FIXED / CONCEDE / HOLD, new findings BROKEN BY, DEADLOCK blocks, OPEN."""
    lines = _lines(text)
    head = next((l for l in lines if REPLY_HEAD.match(l)), None)
    if head is None:
        raise ContractError("no 'REPLY <stage> <episode> <sha8> round <n>' line in the answer")
    m = REPLY_HEAD.match(head)
    out = {"stage": m.group(1).lower(), "episode_id": m.group(2), "sha8": m.group(3).lower(), "round": int(m.group(4)),
           "answers": {}, "new": [], "deadlocks": [], "open": [], "stage_state": None}
    i = 0
    while i < len(lines):
        l = lines[i]
        dl = DEADLOCK_HEAD.match(l)
        if dl:
            block = {"finding": dl.group(3).upper(), "claude": "", "claude_source": "", "gemini": "", "gemini_source": "",
                     "for_viewer": ""}
            for nxt in lines[i + 1:i + 4]:
                for who in ("CLAUDE", "GEMINI"):
                    if nxt.upper().startswith(who + ":"):
                        pos, _, src = nxt.split(":", 1)[1].partition("| SOURCE:")
                        block[who.lower()] = pos.strip()
                        block[who.lower() + "_source"] = src.strip()
                if nxt.upper().startswith("FOR THE VIEWER:"):
                    block["for_viewer"] = nxt.split(":", 1)[1].strip()
            out["deadlocks"].append(block)
            i += 1
            continue
        if re.match(r"^F\d+\s*\|", l):
            c = _cells(l)
            word = c[1].upper() if len(c) > 1 else ""
            if word.startswith("NOT FIXED"):
                out["answers"][c[0].upper()] = {"answer": "NOT FIXED", "quote": (c[1][len("NOT FIXED"):] or "").strip().strip('"')}
            elif word in ("FIXED", "CONCEDE"):
                out["answers"][c[0].upper()] = {"answer": word}
            elif word == "HOLD":
                src = c[2] if len(c) > 2 else ""
                out["answers"][c[0].upper()] = {"answer": "HOLD", "source": src, "why": " | ".join(c[3:])}
            else:
                raise ContractError(f"{c[0]}: answer must be FIXED, NOT FIXED, CONCEDE or HOLD, not {c[1] if len(c) > 1 else ''!r}")
        elif re.match(r"^N\d+\s*\|", l):
            c = _cells(l)
            if len(c) < 7:
                raise ContractError(f"a new finding needs id | severity | BROKEN BY F<n> | source | quote | problem | fix: {l!r}")
            out["new"].append({"id": c[0].upper(), "severity": c[1].upper(), "broken_by": c[2].upper().replace("BROKEN BY", "").strip(),
                               "source": c[3], "quote": c[4].strip('"'), "problem": c[5], "fix": " | ".join(c[6:])})
        elif l.upper().startswith("OPEN:"):
            body = l.split(":", 1)[1]
            opened, _, st = body.partition("|")
            out["open"] = [x.strip().upper() for x in re.split(r"[,\s]+", opened) if re.match(r"^[FN]\d+$", x.strip(), re.I)]
            st = st.split(":", 1)[1].strip().upper() if ":" in st else st.strip().upper()
            out["stage_state"] = st or None
        i += 1
    return out
