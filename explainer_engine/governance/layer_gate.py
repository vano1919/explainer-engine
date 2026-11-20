"""MS-6 of the skills team plan (2026-11-20): a layer's record is checked in code, so no mandatory step can be skipped.

``docs/layers/<layer>.json`` (schema ``layer_record/1``, home: docs/LAYER_GATE.md) holds, for one layer of the film pipeline:
MS-1 the owner's requirements (each with its source) and the capabilities of every tool in the layer (each used or not, with why);
MS-2 at least three public candidates per sub-question (url, author, stars, pinned commit; licence, licence_source and
monetised_ok are information only, never required and never a blocker: the owner, 2026-11-20 08:10 UTC);
MS-3 the trials, each looked at, each output with a line on what was seen; MS-4 one decision per sub-question ("keep ours" only
with a run trial that beats every candidate); MS-5 the mapping of every requirement and every used capability to a skill line or a
rule. :func:`check_record` returns a :class:`GateResult`: BLOCK when a part is missing or wrong, NOT_RUN when the record is complete
but a sub-question has only trials that were not run (never a pass), PASS otherwise. A ``draft`` record is reported only; a
``final`` one carries the team lead's signature, the MS-7 owner check and a BLOCK in it fails ``governance check``. Layers belong to
the ten groups of the team plan; a layer of group N waits (``require_pass`` raises NeedsReview) while a layer of a lower group is
not final. stdlib only."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from explainer_engine.core.errors import ContractError, NeedsReview
from explainer_engine.governance import owner_requirements as OR
from explainer_engine.governance import records
from explainer_engine.governance import root_dir
from explainer_engine.qa import status as S

SCHEMA = "layer_record/1"
LAYERS_DIR = Path("docs") / "layers"
DECISION_LOG = Path("docs") / "DECISIONS_AND_OPEN_QUESTIONS.md"
STATES = ("draft", "final")
SOURCE_KINDS = ("message", "decision", "memory", "rule")
USES = ("used", "not_used")
CHOICES = ("adopt", "enrich", "keep_ours", "idea_only")
TRIAL_STATUS = ("RUN", "NOT_RUN")
TARGET_KINDS = ("skill_line", "validator", "validator_planned", "sourced_rule")
MIN_CANDIDATES = 3
LINK_KINDS = ("file", "page")
# the logical groups of the skills team plan (section 3); a layer's record must carry its group
GROUPS: dict[int, tuple[str, ...]] = {
    1: ("L9", "L10", "L11", "L16"), 2: ("L12", "L13", "L14"), 3: ("L15",), 4: ("L1", "L2", "L3", "L7", "L8", "L29", "L30"),
    5: ("L4", "L5", "L6", "L17"), 6: ("L18", "L19", "L20"), 7: ("L21", "L22", "L25"), 8: ("L23", "L24"),
    9: ("L26", "L27", "L28", "L32"), 10: ("L31", "L33"),
}
GROUP_OF = {layer: g for g, layers in GROUPS.items() for layer in layers}

_MSG = re.compile(r"cmsg_[A-Za-z0-9]+")
_DEC = re.compile(r"D-\d+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class GateResult:
    layer: str
    status: str
    errors: list[str] = field(default_factory=list)      # "CODE: what is wrong" - the codes are listed in docs/LAYER_GATE.md
    not_run: list[str] = field(default_factory=list)     # sub-questions without a trial that ran
    planned: list[str] = field(default_factory=list)     # validators that are mapped but not built yet (wave 2)
    pending: list[str] = field(default_factory=list)     # open MS-7 items of a final record (owner_seen "pending")
    waived: bool = False                                 # not_run_waiver: the owner's cmsg_ id that lets a NOT_RUN layer open the next group
    state: str = "draft"
    group: int | None = None

    def to_dict(self) -> dict:
        return {"layer": self.layer, "status": self.status, "state": self.state, "errors": self.errors,
                "not_run": self.not_run, "planned": self.planned, "pending": self.pending, "waived": self.waived, "group": self.group}


def _text(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _https(v) -> bool:
    """An https url that names a host (a bare ``https://`` is not one)."""
    if not (isinstance(v, str) and v.startswith("https://") and not any(c.isspace() for c in v)):
        return False
    from urllib.parse import urlsplit
    try:
        return bool(urlsplit(v).hostname)
    except ValueError:
        return False


def _real_date(v) -> bool:
    import datetime as dt
    if not (isinstance(v, str) and _DATE.fullmatch(v)):
        return False
    try:
        dt.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _int(v) -> bool:
    """An integer that is not a bool (``True`` is an int in Python and must never read as 1)."""
    return isinstance(v, int) and not isinstance(v, bool)


def _ids(rows, errs: list[str], what: str) -> set[str]:
    seen: set[str] = set()
    for r in rows:
        i = r.get("id") if isinstance(r, dict) else None
        if not _text(i):
            errs.append(f"LG-DUP: a {what} has no id")
        elif i in seen:
            errs.append(f"LG-DUP: {what} id {i} is used twice")
        else:
            seen.add(i)
    return seen


def _rows(rec: dict, key: str) -> list[dict]:
    v = rec.get(key)
    return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []


def _decision_ids(root: Path) -> set[str] | None:
    path = root / DECISION_LOG
    return set(_DEC.findall(path.read_text(encoding="utf-8"))) if path.exists() else None


def _check_requirements(rec, root, errs) -> set[str]:
    rows = _rows(rec, "requirements")
    if not rows:
        errs.append("MS1-REQ-NONE: the layer lists no requirement of the owner")
    ids = _ids(rows, errs, "requirement")
    known = _decision_ids(root)
    for r in rows:
        who = r.get("id", "?")
        if not _text(r.get("text")):
            errs.append(f"MS1-REQ-FIELD: requirement {who} has no text")
        src = r.get("source")
        kind, ref = (src.get("kind"), src.get("ref")) if isinstance(src, dict) else (None, None)
        if kind not in SOURCE_KINDS or not _text(ref):
            errs.append(f"MS1-REQ-SOURCE: requirement {who} needs a source {{kind: {'|'.join(SOURCE_KINDS)}, ref}}")
        elif kind == "message" and not _MSG.fullmatch(ref):
            errs.append(f"MS1-REQ-SOURCE: requirement {who}: a message source is a cmsg_ id, not {ref!r}")
        elif kind == "decision" and not _DEC.fullmatch(ref):
            errs.append(f"MS1-REQ-SOURCE: requirement {who}: a decision source is a D-nn id, not {ref!r}")
        elif kind == "decision" and known is not None and ref not in known:
            errs.append(f"MS1-REQ-SOURCE: requirement {who}: {ref} is not in the decision log")
    return ids


def _check_capabilities(rec, errs) -> set[str]:
    rows = _rows(rec, "tool_capabilities")
    if not rows:
        errs.append("MS1-CAP-NONE: the layer lists no capability of its tools")
    ids = _ids(rows, errs, "capability")
    for r in rows:
        who = r.get("id", "?")
        if r.get("use") not in USES or not _text(r.get("reason")) or not _text(r.get("tool")) or not _text(r.get("capability")):
            errs.append(f"MS1-CAP-FIELD: capability {who} needs tool, capability, use ({'|'.join(USES)}) and a reason")
    return ids


def _check_candidates(rec, sqs: dict[str, dict], errs) -> dict[str, dict]:
    rows = _rows(rec, "candidates")
    _ids(rows, errs, "candidate")
    if len(rows) < MIN_CANDIDATES:
        errs.append(f"MS2-CAND-MIN: {len(rows)} candidates in the layer, at least {MIN_CANDIDATES} are needed")
    out: dict[str, dict] = {}
    per: dict[str, int] = {}
    for c in rows:
        who = c.get("id", "?")
        bad = []
        url = c.get("url")
        if not _https(url):
            bad.append("an https url with a host")
        if not _text(c.get("author")):
            bad.append("author")
        if c.get("monetised_ok") is not None and not isinstance(c.get("monetised_ok"), bool):
            bad.append("monetised_ok true or false (or left out)")   # licence, licence_source, monetised_ok: information only
        if not _text(c.get("teaches")):
            bad.append("teaches")
        if not (_int(c.get("fit")) and 1 <= c["fit"] <= 5):
            bad.append("fit 1-5")
        kind = c.get("kind")
        if kind == "repo":
            if not (_int(c.get("stars")) and c["stars"] >= 0):
                bad.append("stars")
            if not (isinstance(c.get("commit"), str) and _COMMIT.fullmatch(c["commit"])):
                bad.append("a pinned commit hash")
        elif kind == "doc":
            if not _real_date(c.get("retrieved")):
                bad.append("retrieved date YYYY-MM-DD")
        else:
            bad.append("kind (repo|doc)")
        if c.get("sub_question") not in sqs:
            bad.append("a sub_question of the layer")
        else:
            per[c["sub_question"]] = per.get(c["sub_question"], 0) + 1
        if bad:
            errs.append(f"MS2-CAND-FIELD: candidate {who} lacks {', '.join(bad)}")
        if _text(c.get("id")):
            out.setdefault(c["id"], c)
    urls: dict[str, set[str]] = {}
    for c in rows:
        if _text(c.get("sub_question")) and _https(c.get("url")):
            urls.setdefault(c["sub_question"], set()).add(c["url"].strip().rstrip("/").lower())
    for sid, sq in sqs.items():
        per[sid] = min(per.get(sid, 0), len(urls.get(sid, ())))      # three rows with one url are one candidate (F3)
        if per.get(sid, 0) < MIN_CANDIDATES and not _text(sq.get("few_candidates_reason")):
            errs.append(f"MS2-CAND-MIN: sub-question {sid} has {per.get(sid, 0)} candidates (at least {MIN_CANDIDATES}, "
                        f"or a few_candidates_reason)")
    return out


def _effective_run(t: dict) -> bool:
    """A trial that ran and was configured well (``config_ok`` false makes it NOT_RUN for its candidates)."""
    return t.get("status") == "RUN" and t.get("config_ok") is not False


def _check_trials(rec, sqs, cands, errs, res: GateResult) -> dict[str, dict]:
    rows = _rows(rec, "trials")
    _ids(rows, errs, "trial")
    by_id: dict[str, dict] = {}
    ran: dict[str, int] = {}
    seen_sq: set[str] = set()
    for t in rows:
        who = t.get("id", "?")
        if _text(t.get("id")):
            by_id.setdefault(t["id"], t)
        sq = t.get("sub_question")
        if sq in sqs:
            seen_sq.add(sq)
        st = t.get("status")
        if st not in TRIAL_STATUS or sq not in sqs:
            errs.append(f"MS3-TRIAL-FIELD: trial {who} needs status {'|'.join(TRIAL_STATUS)} and a sub_question of the layer")
            continue
        ids = t.get("candidate_ids")
        if ids is not None and (not isinstance(ids, list) or any(cands.get(i, {}).get("sub_question") != sq for i in ids)):
            errs.append(f"MS3-TRIAL-FIELD: trial {who} candidate_ids must name candidates of {sq}")
        if t.get("config_ok") is not None and not isinstance(t.get("config_ok"), bool):
            errs.append(f"MS3-TRIAL-FIELD: trial {who} config_ok is true or false")
        if st == "NOT_RUN":
            if not _text(t.get("not_run_reason")):
                errs.append(f"MS3-TRIAL-FIELD: trial {who} was not run and gives no not_run_reason")
            continue
        if _effective_run(t):                       # a run with a bad configuration counts as NOT_RUN (owner's rule (c))
            ran[sq] = ran.get(sq, 0) + 1
        if not _text(t.get("looked_at_by")) or not _text(t.get("observation")):
            errs.append(f"MS3-TRIAL-FIELD: trial {who} needs looked_at_by and an observation (every output is looked at)")
        links = t.get("links")
        if not isinstance(links, list) or not links:
            errs.append(f"MS3-TRIAL-FIELD: trial {who} has no output links")
            continue
        for i, link in enumerate(links):
            link = link if isinstance(link, dict) else {}
            if not _text(link.get("ref")) or not _text(link.get("seen")):
                errs.append(f"MS3-TRIAL-FIELD: trial {who} link {i} needs ref and a seen line")
            if link.get("kind", "file") not in LINK_KINDS:
                errs.append(f"MS3-TRIAL-FIELD: trial {who} link {i} has kind {link.get('kind')!r}, it is {' or '.join(LINK_KINDS)}")
            if link.get("kind", "file") == "file" and not (isinstance(link.get("sha256"), str) and _SHA256.fullmatch(link["sha256"])):
                errs.append(f"MS3-TRIAL-FIELD: trial {who} link {i} is a file and needs its sha256")
    for sid in sqs:
        if sid not in seen_sq:
            errs.append(f"MS3-TRIAL-NONE: sub-question {sid} has no trial record (a trial run, or one with its not_run_reason)")
        elif not ran.get(sid):
            res.not_run.append(f"{sid}: no trial has run (or every run had a bad configuration)")
    # F5 (the lead, 2026-11-20 09:43): a candidate the record marks state_of_the_art keeps the layer at NOT_RUN until a RUN trial ran it or a
    # NOT_RUN trial row names it with its reason (SeedVR: GPU, priced, owner thread, date)
    ran_ids = {i for t in rows if _effective_run(t) and isinstance(t.get("candidate_ids"), list) for i in t["candidate_ids"] if _text(i)}
    named = {i for t in rows if t.get("status") == "NOT_RUN" and _text(t.get("not_run_reason")) and isinstance(t.get("candidate_ids"), list)
             for i in t["candidate_ids"] if _text(i)}
    for cid, c in sorted(cands.items()):
        if c.get("state_of_the_art") is True and cid not in ran_ids and cid not in named:
            res.not_run.append(f"{c.get('sub_question')}: state_of_the_art candidate {cid} was never run and no NOT_RUN trial row names it "
                               f"with a reason")
    return by_id


def _file_ref(v) -> bool:
    """A link with its sha256: ``{ref|link: https url or path, sha256}``."""
    return isinstance(v, dict) and _text(v.get("ref") or v.get("link")) and isinstance(v.get("sha256"), str) \
        and bool(_SHA256.fullmatch(v["sha256"]))


def _check_keep_ours(rec, d, sid, cands, trials, errs) -> None:
    """The owner's rule for "keep ours" (2026-11-20 08:07 UTC): (a) to (e), each its own error code."""
    who = f"decision for {sid}"
    # (a) ours meets every requirement of the layer, no complaint is open
    for r in _rows(rec, "requirements"):
        c = r.get("complaint")
        fixed = isinstance(c, dict) and c.get("open") is False and _MSG.fullmatch(str(c.get("fix_seen") or ""))
        if r.get("ours_meets") is not True or (c is not None and not fixed):
            errs.append(f"MS4-KEEP-REQ: {who}: requirement {r.get('id', '?')} needs ours_meets true and no open complaint "
                        f"(a complaint carries open false and the fix_seen message id of the owner)")
    # (b) three strong candidates were run, among them the most-starred and a state-of-the-art one
    run = {i for t in trials.values() if _effective_run(t) and t.get("sub_question") == sid for i in (t.get("candidate_ids") or [])
           if cands.get(i, {}).get("sub_question") == sid}
    run_urls = {str(cands[i].get("url")).strip().rstrip("/").lower() for i in run}      # one repo under three ids is one candidate (F3)
    if len(run) < 3 or len(run_urls) < 3:
        errs.append(f"MS4-KEEP-RUN3: {who}: {min(len(run), len(run_urls))} candidates were run, at least 3 are needed (trials with status RUN, "
                    f"config_ok not false, naming them in candidate_ids)")
    mine = {i: c for i, c in cands.items() if c.get("sub_question") == sid}
    stars = {i: c["stars"] for i, c in mine.items() if c.get("kind") == "repo" and isinstance(c.get("stars"), int)}
    top = {i for i, c in mine.items() if c.get("top") is True}
    best = {i for i, n in stars.items() if n == max(stars.values())} if stars else set()
    if not (top or best) or not top <= run or (best and not best & run):
        errs.append(f"MS4-KEEP-TOP: {who}: the most-starred candidate ({', '.join(sorted(top | best)) or 'none defined'}) "
                    f"must be among those run")
    if not any(mine[i].get("state_of_the_art") is True for i in run):
        errs.append(f"MS4-KEEP-SOTA: {who}: a candidate marked state_of_the_art true must be among those run")
    # (c) each run candidate configured per its own docs, with a log
    for i in sorted(run):
        c = mine[i]
        per = c.get("configured_per")
        if not (isinstance(per, str) and per.startswith("https://")) or not _file_ref(c.get("config_log")):
            errs.append(f"MS4-KEEP-CONFIG: {who}: candidate {i} needs configured_per (https docs url) and config_log (a link with sha256)")
    # (d) a blind judge who did not write our code
    j = d.get("blind_judge")
    j = j if isinstance(j, dict) else {}
    author = d.get("ours_author")
    bad = []
    if not _text(author):
        bad.append("ours_author")
    if not _text(j.get("judge")) or (_text(author) and str(j["judge"]).strip().lower() == str(author).strip().lower()):
        bad.append("a judge other than ours_author")
    if j.get("wrote_our_code") is not False:
        bad.append("wrote_our_code false")
    if j.get("labels_sealed_before_scoring") is not True:
        bad.append("labels_sealed_before_scoring true")
    if not _file_ref(j.get("labels_sealed")):
        bad.append("labels_sealed (link with sha256)")
    if not _file_ref(j.get("scores")):
        bad.append("scores (link with sha256)")
    if not _text(j.get("method")):
        bad.append("method")
    if bad:
        errs.append(f"MS4-KEEP-JUDGE: {who} needs ours_author and a blind_judge with: {', '.join(bad)}")
    # (e) the owner saw the side-by-side and agreed: his message id, never pending
    if not (isinstance(rec.get("owner_seen"), str) and _MSG.fullmatch(rec["owner_seen"])):
        errs.append(f"MS4-KEEP-OWNER: {who}: owner_seen must be the owner's cmsg_ id, not {rec.get('owner_seen')!r}")


def _check_decisions(rec, sqs, cands, trials, errs) -> None:
    rows = _rows(rec, "decisions")
    made: dict[str, int] = {}
    for d in rows:
        sid = d.get("sub_question")
        made[sid] = made.get(sid, 0) + 1
    for sid in sqs:
        if not made.get(sid):
            errs.append(f"MS4-DEC-MISSING: sub-question {sid} has no decision")
    for d in rows:
        sid, choice = d.get("sub_question"), d.get("choice")
        who = f"decision for {sid}"
        if sid not in sqs or made[sid] > 1:
            errs.append(f"MS4-DEC-FIELD: {who}: the sub-question is unknown or decided twice")
            continue
        if choice not in CHOICES or not _text(d.get("reason")):
            errs.append(f"MS4-DEC-FIELD: {who} needs a choice ({'|'.join(CHOICES)}) and a reason")
            continue
        ev = d.get("evidence") or []
        for tid in ev:
            if tid not in trials:
                errs.append(f"MS4-DEC-FIELD: {who}: evidence {tid} names no trial")
        if choice == "keep_ours":
            mine = {c for c, row in cands.items() if row.get("sub_question") == sid}
            ran = [tid for tid in ev if tid in trials and trials[tid].get("status") == "RUN" and trials[tid].get("sub_question") == sid]
            if not ran or not mine <= set(d.get("beats") or []):
                errs.append(f"MS4-KEEP-EVIDENCE: {who}: keeping ours needs a run trial of this sub-question as evidence and "
                            f"beats listing every candidate ({', '.join(sorted(mine))})")
            _check_keep_ours(rec, d, sid, cands, trials, errs)
            continue
        picked = d.get("candidate_ids") or []
        if not picked or any(c not in cands or cands[c].get("sub_question") != sid for c in picked):
            errs.append(f"MS4-DEC-FIELD: {who}: {choice} names candidates of this sub-question that exist")


def _check_owner(rec, errs, res: GateResult) -> None:
    """MS-7: the links the owner can watch, and whether he has seen them (``pending`` is allowed but reported)."""
    links = rec.get("owner_check")
    ok = isinstance(links, list) and bool(links)
    for link in links if ok else []:
        link = link if isinstance(link, dict) else {}
        url, sha = link.get("url"), link.get("sha256")
        good_url = isinstance(url, str) and url.startswith("https://")
        good_sha = isinstance(sha, str) and bool(_SHA256.fullmatch(sha))
        if (url is not None and not good_url) or (sha is not None and not good_sha) or not (good_url or good_sha):
            ok = False
    if not ok:
        errs.append("LG-OWNER: a final record lists owner_check links (each an https url and/or a sha256) the owner can watch")
    seen = rec.get("owner_seen")
    if seen == "pending":
        res.pending.append("owner_seen: the owner has not looked at the trial links yet")
    elif not (isinstance(seen, str) and _MSG.fullmatch(seen)):
        errs.append('LG-OWNER: owner_seen is a cmsg_ id of the owner\'s message or "pending"')


def _check_target(t, root: Path, res: GateResult, strict: bool) -> str | None:
    """None when the mapping target is good, else what is wrong."""
    t = t if isinstance(t, dict) else {}
    kind, ref = t.get("kind"), t.get("ref")
    if kind not in TARGET_KINDS or not _text(ref):
        return f"target needs kind ({'|'.join(TARGET_KINDS)}) and ref"
    if kind == "skill_line":
        path, _, line = ref.rpartition(":")
        if not path or not line.isdigit() or int(line) < 1:
            return f"skill_line {ref!r} must be path:line"
        file = (root / path).resolve()
        if root.resolve() not in file.parents or not file.is_file():
            return f"skill_line {ref!r}: the file is not inside the repo"
        lines = file.read_text(encoding="utf-8").splitlines()
        if int(line) > len(lines) or not lines[int(line) - 1].strip():
            return f"skill_line {ref!r}: line {line} does not exist or is blank"
    elif kind == "validator":
        from explainer_engine import validators
        if ref not in validators.rule_index():
            return f"validator {ref!r} is in no validators/ module RULE_IDS"
    elif kind == "validator_planned":
        if strict:
            return f"validator_planned {ref!r} is refused in strict mode (build it first)"
        if not _int(t.get("wave")):
            return f"validator_planned {ref!r} needs the wave that builds it"
        res.planned.append(f"{ref} (wave {t['wave']})")
    elif kind == "sourced_rule":
        from explainer_engine.standards import sourced_rules as SR
        try:
            SR.rule(ref)
        except KeyError:
            return f"sourced rule {ref!r} is not in standards/sourced_rules.json"
    return None


def _check_mapping(rec, req_ids, cap_rows, root, errs, res, strict) -> None:
    rows = _rows(rec, "mapping")
    need = set(req_ids) | {c["id"] for c in cap_rows if c.get("use") == "used" and _text(c.get("id"))}
    known, mapped = need, set()
    for m in rows:
        who = m.get("requirement")
        if who not in known:
            errs.append(f"MS5-MAP-TARGET: mapping names {who!r}, which is no requirement or used capability of the layer")
            continue
        bad = _check_target(m.get("target"), root, res, strict)
        if bad:
            errs.append(f"MS5-MAP-TARGET: {who}: {bad}")
        else:
            mapped.add(who)
    for who in sorted(need - mapped):
        errs.append(f"MS5-MAP-MISSING: {who} is not mapped to a skill line or a rule")


def check_record(rec, *, root=None, strict: bool = False, layer: str | None = None) -> GateResult:
    """Check one record dict. ``strict`` also refuses ``validator_planned`` targets (the wave-2 gate). A record of the wrong shape is a
    BLOCK (LG-SCHEMA), never an exception: a malformed file must not stop the check of the other layers (F1)."""
    try:
        return _check_record(rec, root=root, strict=strict, layer=layer)
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as e:
        name = layer or (str(rec.get("layer")) if isinstance(rec, dict) else "?")
        state = rec.get("state") if isinstance(rec, dict) and rec.get("state") in STATES else "draft"
        return GateResult(name, S.BLOCK, [f"LG-SCHEMA: the record has a field of the wrong type ({type(e).__name__}: {e})"], state=state)


def _check_record(rec, *, root=None, strict: bool = False, layer: str | None = None) -> GateResult:
    root = root_dir(root)
    errs: list[str] = []
    res = GateResult(layer or str(rec.get("layer") if isinstance(rec, dict) else "?"), S.BLOCK)
    if not isinstance(rec, dict):
        res.errors = ["LG-SCHEMA: the record is not an object"]
        return res
    res.state = rec.get("state") if rec.get("state") in STATES else "draft"
    if _text(rec.get("layer")) and rec["layer"] not in GROUP_OF:
        errs.append(f"LG-SCHEMA: {rec['layer']!r} is not one of the 33 layers L1..L33")
    if rec.get("schema") != SCHEMA or not _text(rec.get("layer")) or not _text(rec.get("name")) or rec.get("state") not in STATES \
            or not _int(rec.get("group")) or not 1 <= rec["group"] <= 10:
        errs.append(f"LG-SCHEMA: needs schema {SCHEMA}, layer, name, group 1-10 and state {'|'.join(STATES)}")
    if layer and rec.get("layer") != layer:
        errs.append(f"LG-SCHEMA: the file is for {layer} but the record says {rec.get('layer')!r}")
    if rec.get("state") == "final" and not (_text(rec.get("signed_by")) and _text(rec.get("signed_at"))):
        errs.append("LG-SIGN: a final record carries the team lead's signed_by and signed_at")
    res.group = rec.get("group") if _int(rec.get("group")) else None
    if rec.get("layer") in GROUP_OF and rec.get("group") != GROUP_OF[rec["layer"]]:
        errs.append(f"LG-SCHEMA: layer {rec['layer']} belongs to group {GROUP_OF[rec['layer']]}, the record says {rec.get('group')!r}")
    waiver = rec.get("not_run_waiver")
    if waiver is not None and not (isinstance(waiver, str) and _MSG.fullmatch(waiver)):
        errs.append("LG-OWNER: not_run_waiver is the cmsg_ id of the owner's own word")
    res.waived = isinstance(waiver, str) and bool(_MSG.fullmatch(waiver))
    if rec.get("state") == "final":
        _check_owner(rec, errs, res)
    sq_rows = _rows(rec, "sub_questions")
    sq_ids = _ids(sq_rows, errs, "sub-question")
    if not sq_ids or any(not _text(s.get("text")) for s in sq_rows):
        errs.append("MS2-SUBQ: the layer names its sub-questions, each with an id and text")
    sqs = {s["id"]: s for s in sq_rows if _text(s.get("id"))}
    req_ids = _check_requirements(rec, root, errs)
    _check_capabilities(rec, errs)
    cands = _check_candidates(rec, sqs, errs)
    trials = _check_trials(rec, sqs, cands, errs, res)
    _check_decisions(rec, sqs, cands, trials, errs)
    _check_mapping(rec, req_ids, _rows(rec, "tool_capabilities"), root, errs, res, strict)
    entries, reg_errs = OR.load(root)                 # the owner's registry: every active entry that binds the layer (spec section 3)
    errs += reg_errs + OR.check_registry(entries, root)
    if rec.get("state") == "final":                    # deleting or emptying the registry must never open a layer
        errs += OR.missing(entries)
    errs += OR.check_cover(rec, str(rec.get("layer")), entries, root)
    res.errors = errs
    res.status = S.BLOCK if errs else (S.NOT_RUN if res.not_run else S.PASS)
    return res


def check_layer(layer: str, *, root=None, strict: bool = False) -> GateResult:
    path = root_dir(root) / LAYERS_DIR / f"{layer}.json"
    if not path.is_file():
        return GateResult(layer, S.BLOCK, [f"LG-SCHEMA: there is no record {LAYERS_DIR / (layer + '.json')}"])
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return GateResult(layer, S.BLOCK, [f"LG-SCHEMA: {path.name} is not JSON ({e})"])
    return check_record(rec, root=root, strict=strict, layer=layer)


def check_all(*, root=None, strict: bool = False) -> list[GateResult]:
    folder = root_dir(root) / LAYERS_DIR
    return [check_layer(p.stem, root=root, strict=strict) for p in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def problems(results: list[GateResult]) -> list[str]:
    """What fails ``governance check``: the BLOCKs of final records. Drafts and NOT_RUN are reported, not failing."""
    return [f"layer {r.layer}: {e}" for r in results if r.state == "final" and r.status == S.BLOCK for e in r.errors]


def _ready(res: GateResult) -> bool:
    """A layer lets the next group start when its record is final and PASS; a final NOT_RUN does so only with the owner's
    own word on it (``not_run_waiver``, a cmsg_ id); a BLOCK never does."""
    return res.state == "final" and (res.status == S.PASS or (res.status == S.NOT_RUN and res.waived))


def _lower_open(layer: str, group: int, root) -> list[str]:
    return [l for g in range(1, group) for l in GROUPS[g] if not _ready(check_layer(l, root=root))]


def group_report(*, root=None) -> list[dict]:
    """Per group: its layers that are not ready (``open``), whether the group is ready, and which lower groups it waits on."""
    ready = {l: _ready(check_layer(l, root=root)) for layers in GROUPS.values() for l in layers}
    rows = []
    for g, layers in GROUPS.items():
        open_ = [l for l in layers if not ready[l]]
        rows.append({"group": g, "layers": list(layers), "open": open_, "ready": not open_,
                     "waiting_on": [x["group"] for x in rows if not x["ready"]],
                     "waiting_layers": [l for x in rows for l in x["open"]]})
    return rows


def require_pass(layer: str, *, root=None, strict: bool = False) -> GateResult:
    """The step before a layer is vendored or run (MS-5): only a final, signed, PASS record goes on. A BLOCK raises ContractError,
    a layer of a higher group waits (NeedsReview) while any layer of a lower group is not final, a draft raises ContractError,
    a NOT_RUN raises NeedsReview (a trial still has to run)."""
    res = check_layer(layer, root=root, strict=strict)
    if res.status == S.BLOCK:
        raise ContractError(f"layer {layer} is BLOCK: " + "; ".join(res.errors))
    waiting = _lower_open(layer, GROUP_OF[layer], root) if layer in GROUP_OF else []
    if waiting:
        raise NeedsReview(f"layer {layer} (group {GROUP_OF[layer]}) waits: not final yet in a lower group: {', '.join(waiting)}")
    if res.state != "final":
        raise ContractError(f"layer {layer} is a draft: the team lead signs it final first")
    if res.status != S.PASS:
        raise NeedsReview(f"layer {layer} is {res.status}: " + "; ".join(res.not_run))
    return res


# ---- the layers a runner stage or a trial script needs (spec section 7.2: code, not a brief) ------------------------------------
# The layers whose records must be final and PASS before the stage starts (the router table of .claude/skills/film-direction).
# A design choice of the developer, for the team lead to confirm.
STAGE_LAYERS: dict[str, tuple[str, ...]] = {
    "script": ("L1", "L2", "L3", "L4", "L7", "L8", "L29", "L30"),
    "sound_plan": ("L18", "L19", "L20"),
    "pictures": ("L9", "L10", "L11", "L16"),
    "voice": ("L5", "L6", "L17"),
    "clips": ("L12", "L13", "L14", "L15"),
    "sound": ("L18", "L19", "L20"),
    "assemble": ("L21", "L22", "L25"),
    "qa": ("L23", "L24"),
}
WAIVER_MINUTES = 24 * 60     # the owner's recorded word on one layer holds for a day, then he is asked again


def waived(layer: str, *, root=None) -> dict | None:
    """The owner's recorded ``layer_waiver`` for exactly this layer (jobs/creator_ok.jsonl, the D-84 pattern), or None."""
    row = records.last("layer_waiver", layer, root=root)
    return row if row and row.get("target") == layer and records.valid("layer_waiver", layer, WAIVER_MINUTES, root=root, wildcard=False) \
        else None


MODE = "fail_only"   # the owner's word (2026-11-20 09:11 UTC, cmsg_01Hnu5zB86sjUj5GtTgaUkPWMd8fDv9ExMX3zJq6nwZXau, recorded in jobs/creator_ok.jsonl):
# "turn on the soft mode: production stops only on a validator that failed". The one behaviour of the layer gate; no flag, no strict mode.


def require_layers(layers, *, root=None) -> list[str]:
    """The soft layer gate. Raises ContractError ONLY when the owner's requirements registry is missing or invalid (REG-MISSING and the
    REG-* codes: with no registry nothing is measured at all). A layer whose record is not final, not PASS or BLOCK does not stop
    production: it is a ``NOT_RUN <layer>: why`` note in the returned list, which every runner record and send-gate report carries
    (the layer records decide when a layer's skill work is final, not whether production runs). A layer waived by the owner's recorded
    ``layer_waiver`` is a note too. What stops production is a validator that FAILED on a stage's output (``send_gate.stage_check``)."""
    root = root_dir(root)
    entries, errs = OR.load(root)
    problems_ = errs + OR.check_registry(entries, root) + OR.missing(entries)
    if problems_:
        raise ContractError("the layer gate refuses (the registry is missing or invalid, nothing could be measured): " + " | ".join(problems_))
    notes = [f"layer gate: {MODE}"]
    for layer in layers:
        w = waived(layer, root=root)
        if w:
            notes.append(f"{layer} waived by the owner ({w.get('message_id')})")
            continue
        try:
            require_pass(layer, root=root)
        except (ContractError, NeedsReview) as e:
            notes.append(f"NOT_RUN {layer}: {e}")
    return notes


def require_stage(stage: str, *, root=None) -> list[str]:
    """``require_layers`` for a runner stage (``STAGE_LAYERS``)."""
    return require_layers(STAGE_LAYERS[stage], root=root)
