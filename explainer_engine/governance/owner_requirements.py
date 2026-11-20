"""The owner's requirements registry (owner, 2026-11-20 08:34 UTC: "what is the point of rules if they are not followed?").

``explainer_engine/governance/owner_requirements.json`` (schema ``owner_requirements/1``, home: docs/LAYER_GATE.md section
"The owner's requirements registry") holds every requirement the owner has put into words, quoted verbatim, with its source,
the layers it binds and the check that enforces it: a validator (module:function plus an existing test), a judge step (who and an
existing rubric) or ``unmapped`` (honest, and a BLOCK for the layers it binds). :func:`check_registry` is the schema check
(``REG-*`` codes); :func:`check_cover` is what ``layer_gate.check_record`` runs per layer record (``REQ-*`` codes): every active
entry that binds the layer must be listed in the record's ``requirements_covered`` and its check must exist, so a new entry
reopens the layers it binds. A repo without the registry file binds nothing. stdlib only."""
from __future__ import annotations

import json
import re
from pathlib import Path

from explainer_engine.governance import root_dir

SCHEMA = "owner_requirements/1"
REGISTRY = Path("explainer_engine") / "governance" / "owner_requirements.json"
DECISION_LOG = Path("docs") / "DECISIONS_AND_OPEN_QUESTIONS.md"
SOURCE_KINDS = ("chat", "memory", "decision_log", "doc")
STATUSES = ("active", "superseded")
CHECK_KINDS = ("validator", "judge", "unmapped")
LAYERS = tuple(f"L{i}" for i in range(1, 34))
_ID = re.compile(r"REQ-\d{3,}|OR-[A-Z]\d{2,}[a-z]?")   # REQ-nnn, or OR-<group letter><nn> (OR-V visual, OR-S, OR-A, OR-E, OR-Q, OR-P, OR-I; a child may add a letter: OR-V09a)
_MSG = re.compile(r"cmsg_[A-Za-z0-9]+")
_RULE_REF = re.compile(r"[A-Z]{1,3}-\d+")
_DEC = re.compile(r"D-\d+")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?( ?UTC|Z|[+-]\d{2}:\d{2})?)?")


def _when(d) -> str:
    """A sortable form of a date: ISO 8601, or the registry draft's "2026-11-19 22:08 UTC"."""
    return re.sub(r" ?UTC$", "Z", str(d)).replace(" ", "T")
_VALIDATOR_REF = re.compile(r"([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*):([A-Za-z_]\w*)")
_TEST_REF = re.compile(r"(.+\.py)::([A-Za-z_]\w*)")


def _text(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def load(root=None) -> tuple[list[dict] | None, list[str]]:
    """(entries, errors); entries is None when the registry file does not exist (then nothing binds)."""
    path = root_dir(root) / REGISTRY
    if not path.is_file():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [], [f"REG-SCHEMA: {REGISTRY.name} is not JSON ({e})"]
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("requirements"), list):
        return [], [f"REG-SCHEMA: {REGISTRY.name} needs schema {SCHEMA} and a requirements list"]
    proc = data.get("process_requirements", [])
    if not isinstance(proc, list):
        return [], [f"REG-SCHEMA: {REGISTRY.name}: process_requirements is a list"]
    rows = [e if isinstance(e, dict) else {"id": "?"} for e in data["requirements"]]
    rows += [dict(e, kind="process") if isinstance(e, dict) else {"id": "?", "kind": "process"} for e in proc]
    return rows, []


def missing(entries: list[dict] | None) -> list[str]:
    """``REG-MISSING`` when the registry file is absent or holds no entry: deleting or emptying it must never open a layer.
    Asked by a final layer record, ``require_pass``, the send gate and the CI job (the draft records of a repo without a registry
    are only reported)."""
    if entries:
        return []
    return [f"REG-MISSING: {REGISTRY.as_posix()} is absent or empty; a final layer, a send and the CI job need the owner's registry"]


def compare_with_base(base: list[dict] | None, now: list[dict] | None) -> list[str]:
    """What the CI job checks against the base branch (append-only): no id removed (``REG-REMOVED``), no owner ``words``
    (or ``words_verbatim``) changed (``REG-WORDS-CHANGED``); a change of status to superseded is the way to retire an entry."""
    errs = []
    cur = {e.get("id"): e for e in now or []}
    for old in base or []:
        oid = old.get("id")
        new = cur.get(oid)
        if new is None:
            errs.append(f"REG-REMOVED: {oid} was in the base branch and is gone; an entry is never deleted, it becomes superseded")
            continue
        for k in ("words", "words_verbatim"):
            if old.get(k) != new.get(k):
                errs.append(f"REG-WORDS-CHANGED: {oid}: the owner's {k} differ from the base branch; his words are never edited")
    return errs


def is_conflict(e: dict) -> bool:
    return e.get("kind") == "conflict"


def is_process(e: dict) -> bool:
    """A process requirement (``process_requirements`` of the file): it binds the way we work (model routing, thread starts), not a layer.
    The layer gate never reads it; the CI job and the registry report do, and it needs a validator or a judge step with their tests like any other."""
    return e.get("kind") == "process"


def _source_errs(e: dict, who: str, log_ids: set[str] | None) -> list[str]:
    src = e.get("source")
    kind, ref = (src.get("kind"), src.get("ref")) if isinstance(src, dict) else (None, None)
    if kind not in SOURCE_KINDS or not _text(ref):
        return [f"REG-FIELDS: {who} needs a source {{kind: {'|'.join(SOURCE_KINDS)}, ref}}"]
    if kind == "chat" and not _MSG.fullmatch(ref):
        return [f"REG-FIELDS: {who}: a chat source is a cmsg_ id, not {ref!r}"]
    if kind == "decision_log":
        refs = [t for t in re.split(r"[\s,/+;]+", ref) if t]
        if not refs or not all(_RULE_REF.fullmatch(t) for t in refs):
            return [f"REG-FIELDS: {who}: a decision_log source is one or more ids like D-139 (separated by , / or +), not {ref!r}"]
        gone = [t for t in refs if _DEC.fullmatch(t) and log_ids is not None and t not in log_ids]
        if gone:
            return [f"REG-FIELDS: {who}: {', '.join(gone)} is not in the decision log"]
    return []


def _layer_errs(e: dict, who: str) -> list[str]:
    layers = e.get("layers")
    if not isinstance(layers, list) or not layers:
        return [f"REG-LAYER: {who} binds no layer"]
    bad = [x for x in layers if x not in LAYERS]
    return [f"REG-LAYER: {who} binds {bad}, which is no layer of L1..L33"] if bad else []


def check_registry(entries: list[dict] | None, root=None) -> list[str]:
    """Schema errors of the registry (``REG-*``); empty = valid."""
    if not entries:
        return []
    root = root_dir(root)
    log = root / DECISION_LOG
    log_ids = set(_DEC.findall(log.read_text(encoding="utf-8"))) if log.is_file() else None
    errs: list[str] = []
    seen: dict[str, dict] = {}
    for e in entries:
        who = str(e.get("id", "?"))
        if not (isinstance(e.get("id"), str) and _ID.fullmatch(e["id"])):
            errs.append(f"REG-FIELDS: an entry id is REQ-nnn, not {e.get('id')!r}")
        elif e["id"] in seen:
            errs.append(f"REG-DUP: {who} appears twice (ids are append-only, one entry per requirement)")
        else:
            seen[e["id"]] = e
    for e in entries:
        who = str(e.get("id", "?"))
        if not (isinstance(e.get("date"), str) and _DATE.fullmatch(e["date"])):
            errs.append(f"REG-FIELDS: {who} needs the date of the owner's word (ISO 8601)")
        errs += _source_errs(e, who, log_ids)
        errs += _layer_errs(e, who) if not is_process(e) else ([] if e.get("layers") in (None, []) else
                                                                [f"REG-LAYER: {who} is a process requirement and binds no layer"])
        if is_conflict(e):
            errs += _conflict_errs(e, who, seen)
            continue
        if not _text(e.get("words")):
            errs.append(f"REG-FIELDS: {who} has no words: an entry quotes the owner verbatim")
        for flag in ("words_verbatim", "words_partial"):
            if e.get(flag) is not None and not isinstance(e[flag], bool):
                errs.append(f"REG-FIELDS: {who}: {flag} is true or false (true = the owner's own words, quoted)")
        parent = e.get("parent")
        if parent is not None and not (isinstance(parent, str) and parent in seen and parent != e.get("id")):
            errs.append(f"REG-FIELDS: {who}: parent {parent!r} is no other existing entry")
        if e.get("measures") is not None and not _text(e.get("measures")):
            errs.append(f"REG-FIELDS: {who}: measures is one line on what the check measures")
        if e.get("status") not in STATUSES:
            errs.append(f"REG-FIELDS: {who} status is {'|'.join(STATUSES)}")
        newer = e.get("superseded_by")
        if e.get("status") == "superseded":
            if not (isinstance(newer, str) and newer in seen) or newer == e.get("id"):
                errs.append(f"REG-SUPERSEDED: {who} is superseded but names no other existing entry in superseded_by ({newer!r})")
            elif is_conflict(seen[newer]) or _when(seen[newer].get("date", "")) < _when(e.get("date", "")):
                errs.append(f"REG-SUPERSEDED: {who}: {newer} must be a requirement that is not older than it")
        elif newer is not None:
            errs.append(f"REG-SUPERSEDED: {who} is active but carries superseded_by")
        check = e.get("check")
        if check is not None and not (isinstance(check, dict) and check.get("kind") in CHECK_KINDS):
            errs.append(f"REG-FIELDS: {who} check.kind is {'|'.join(CHECK_KINDS)}")
    return errs


def _conflict_errs(e: dict, who: str, seen: dict[str, dict]) -> list[str]:
    errs = []
    if not (_text(e.get("summary")) or _text(e.get("title"))):
        errs.append(f"REG-FIELDS: {who} (conflict) needs a summary or title of what the entries ask")
    ids = e.get("conflicts")
    # a registry id must exist; a rule outside the registry (GC-18, RR-03, "PRODUCTION_RULES approval #2") is named as text
    if not (isinstance(ids, list) and len(set(map(str, ids))) >= 2 and all(isinstance(i, str) and i.strip() for i in ids)
            and all(i in seen and not is_conflict(seen[i]) for i in ids if _ID.fullmatch(i))):
        errs.append(f"REG-CONFLICT: {who} lists at least two things in conflict, and a requirement id among them must exist")
    if e.get("status") not in ("open", "resolved"):
        errs.append(f"REG-CONFLICT: {who} status is open|resolved")
    elif e["status"] == "resolved" and not (isinstance(e.get("resolved_by"), str) and _MSG.fullmatch(e["resolved_by"])):
        errs.append(f"REG-CONFLICT: {who} is resolved without resolved_by, the cmsg_ id of the owner's answer")
    return errs


def _anchors(path: Path) -> set[str]:
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            out.add(re.sub(r"[ ]", "-", re.sub(r"[^\w\- ]", "", m.group(1).lower())))
    return out


def _test_exists(ref, root: Path) -> bool:
    t = _TEST_REF.fullmatch(ref) if isinstance(ref, str) else None
    f = (root / t.group(1)) if t else None
    return bool(t and f.is_file() and re.search(rf"^\s*(async )?def {re.escape(t.group(2))}\(", f.read_text(encoding="utf-8"), re.M))


def _check_errs(e: dict, root: Path) -> list[str]:
    """``REQ-UNMAPPED`` / ``REQ-NOVALIDATOR`` / ``REQ-NOTEST`` / ``REQ-NONEGATIVE`` / ``REQ-NOJUDGE`` for one active entry."""
    who = e["id"]
    check = e.get("check") if isinstance(e.get("check"), dict) else {"kind": "unmapped"}
    kind = check.get("kind")
    if kind == "validator":
        errs = []
        ref = check.get("ref")
        for field, value in (("ref", ref), ("send_ref", check.get("send_ref"))):
            if field == "send_ref" and value is None:
                continue
            m = _VALIDATOR_REF.fullmatch(value) if isinstance(value, str) else None
            if not m:
                errs.append(f"REQ-NOVALIDATOR: {who}: check.{field} is module:function, not {value!r}")
                continue
            mod = root / (m.group(1).replace(".", "/") + ".py")
            if not (mod.is_file() and re.search(rf"^def {re.escape(m.group(2))}\(", mod.read_text(encoding="utf-8"), re.M)):
                errs.append(f"REQ-NOVALIDATOR: {who}: {value} does not exist (no def {m.group(2)} in {mod.relative_to(root).as_posix()})")
        if not _test_exists(check.get("test"), root):
            errs.append(f"REQ-NOTEST: {who}: check.test must be path.py::test_name of an existing test (it passes the validator on a "
                        f"compliant fixture), not {check.get('test')!r}")
        if not _test_exists(check.get("negative_test"), root):
            errs.append(f"REQ-NONEGATIVE: {who}: check.negative_test must be path.py::test_name of an existing test (the validator FAILS "
                        f"a known violation fixture), not {check.get('negative_test')!r}")
        return errs
    if kind == "judge":
        rubric = check.get("rubric")
        if not _text(check.get("who")) or not _text(rubric):
            return [f"REQ-NOJUDGE: {who}: a judge step needs who and a rubric path#anchor"]
        path, _, anchor = rubric.partition("#")
        f = root / path
        if not f.is_file():
            return [f"REQ-NOJUDGE: {who}: the rubric file {path!r} does not exist"]
        if anchor and anchor not in _anchors(f):
            return [f"REQ-NOJUDGE: {who}: the rubric {path!r} has no heading #{anchor}"]
        return []
    return [f"REQ-UNMAPPED: {who} has no check yet (\"unmapped\" is honest, and it blocks the layers it binds): "
            "build its validator or name its judge"]


def bound(entries: list[dict] | None, layer: str) -> list[dict]:
    return [e for e in entries or [] if layer in (e.get("layers") or []) and e.get("status") not in ("superseded", "resolved")]


def check_cover(rec: dict, layer: str, entries: list[dict] | None, root=None) -> list[str]:
    """``REQ-*`` errors of one layer record against the registry (the registry's own errors come from :func:`check_registry`)."""
    if not entries:
        return []
    root = root_dir(root)
    errs: list[str] = []
    by_id = {e.get("id"): e for e in entries}
    rows = rec.get("requirements_covered")
    listed: dict[str, dict] = {}
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        errs.append("REQ-COVER-FIELD: requirements_covered is a list of {id, evidence}")
        rows = []
    for r in rows:
        rid = r.get("id") if isinstance(r, dict) else None
        if not isinstance(rid, str) or not rid or not (isinstance(r, dict) and _text(r.get("evidence"))):
            errs.append(f"REQ-COVER-FIELD: a requirements_covered row needs an id and a line of evidence ({rid!r})")
        elif rid in listed:
            errs.append(f"REQ-COVER-FIELD: {rid} is listed twice in requirements_covered")
        else:
            listed[rid] = r
    for rid in listed:
        e = by_id.get(rid)
        if e is None:
            errs.append(f"REQ-UNKNOWN: requirements_covered names {rid}, which is not in the owner's registry")
        elif e.get("status") == "superseded":
            errs.append(f"REQ-SUPERSEDED-USED: {rid} is superseded by {e.get('superseded_by')}; cite the owner's newer word")
    for e in bound(entries, layer):
        who = e.get("id", "?")
        if is_conflict(e):
            if e.get("status") == "open":
                errs.append(f"REQ-CONFLICT-OPEN: {who} ({e.get('summary', '')[:80]}) binds {layer}; blocked until the owner answers")
            continue
        if who not in listed:
            errs.append(f"REQ-UNCOVERED: {who} binds {layer} and the record does not list it in requirements_covered")
        errs += _check_errs(e, root)
    return errs


def report(root=None) -> dict:
    """What the CLI prints: the count per layer and the unmapped entries (the developer's backlog)."""
    entries, errs = load(root)
    entries = entries or []
    active = [e for e in entries if e.get("status") == "active" and not is_conflict(e)]
    process = [e["id"] for e in active if is_process(e)]
    unmapped = [e["id"] for e in active if not (isinstance(e.get("check"), dict) and e["check"].get("kind") in ("validator", "judge"))]
    per: dict[str, dict] = {}
    for e in active:
        for layer in e.get("layers") or []:
            row = per.setdefault(layer, {"active": 0, "unmapped": 0})
            row["active"] += 1
            row["unmapped"] += e["id"] in unmapped
    open_conflicts = [e["id"] for e in entries if is_conflict(e) and e.get("status") == "open"]
    return {"total": len(entries), "active": len(active), "unmapped": unmapped, "per_layer": per,
            "open_conflicts": open_conflicts, "process": process, "errors": errs + check_registry(entries, root)}
