"""The send gate (spec section 4, owner 2026-11-20 08:36 UTC): nothing goes to the owner as a candidate unless the validators of the layer's
registered requirements have measured it.

    python -m explainer_engine.governance.send_gate <layer> <files...> [--owner-asked <cmsg id>]

For every file, every active requirement of the layer whose check is a validator (``check.send_ref``, else ``check.ref``, a ``module:function``, see
:mod:`explainer_engine.governance.owner_requirements`) is run when it is a send validator (it carries ``fn.kinds``; a pipeline function
such as ``plan_turns(queue)`` cannot measure a file and is NOT_RUN with a note to name an adapter in ``check.send_ref``): ``fn(path) -> {"status": PASS|FAIL|NOT_RUN, "value": number|None,
"detail": str}``; a function may carry ``fn.kinds = (".mp4", ...)`` to say which files it applies to (a file of another kind is not
measured by it; no file of its kind is NOT_RUN). Printed per requirement id: PASS / FAIL / NOT_RUN / BLOCK with the measured number.
**FAIL** (a validator measured a violation) and **BLOCK** (the registry is missing, invalid or has an open conflict for the layer,
or an active requirement is ``unmapped``, or a validator does not exist / raised) exit 1: such a candidate is never sent. **NOT_RUN**
(a judge step, or no file of the validator's kind) is shown, never hidden, and does not fail the gate. A candidate that fails may go
only as a labelled record when the owner asked to see failures: ``--owner-asked <cmsg id>`` stores his message id, prints the label
"fails REQ-xxx", and the record then lets the hooks pass the upload; the exit code stays 1. Every run appends one line to
``jobs/send_gate/records.jsonl`` (layer, the sha256 of each file, the rows, the verdict): the hooks (``send_hook``) read it. stdlib only."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

from explainer_engine.governance import layer_gate, root_dir
from explainer_engine.governance import owner_requirements as OR

RECORDS = Path("jobs") / "send_gate" / "records.jsonl"
QUARANTINE = Path("jobs") / "send_gate" / "quarantine.jsonl"
PASS, FAIL, NOT_RUN, BLOCK = "PASS", "FAIL", "NOT_RUN", "BLOCK"
_ORDER = {BLOCK: 3, FAIL: 2, NOT_RUN: 1, PASS: 0}
_MSG = re.compile(r"cmsg_[A-Za-z0-9]+")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---- sealed logs (S2, S3): a hand-written or deleted line must not release a file --------------------------------------------------
# Every row of records.jsonl and quarantine.jsonl carries ``seal`` = sha256(previous valid seal + the row without its seal). A reader
# keeps a row only when its seal fits the chain, so a line a thread typed by hand, an edited line and every line after a deleted one
# are ignored. The log is tamper-evident, not secret: a thread that reads this code can still compute a seal, which is why the
# hooks also refuse any Write/Edit/Bash that touches ``jobs/send_gate/`` or ``jobs/creator_ok.jsonl`` (``hooks.NEVER_HAND_WRITTEN``).
GENESIS = "genesis"


def _seal(prev: str, row: dict) -> str:
    body = json.dumps({k: v for k, v in row.items() if k != "seal"}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev + "\n" + body).encode("utf-8")).hexdigest()


def read_sealed(path: Path) -> list[dict]:
    """The rows of a sealed log that fit the chain, oldest first."""
    prev, out = GENESIS, []
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("seal") == _seal(prev, row):
            out.append(row)
            prev = row["seal"]
    return out


def append_sealed(path: Path, rows: list[dict]) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = (read_sealed(path) or [{"seal": GENESIS}])[-1]["seal"]
    out = []
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            row = dict(row)
            row["seal"] = prev = _seal(prev, {k: v for k, v in row.items() if k != "seal"})
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.append(row)
    return out


def _load_validator(ref: str, root: Path):
    mod, _, fn = ref.partition(":")
    file = root / (mod.replace(".", "/") + ".py")
    if root.resolve() == Path(__file__).resolve().parents[2]:
        return getattr(importlib.import_module(mod), fn)
    spec = importlib.util.spec_from_file_location("_send_gate_" + hashlib.sha1(str(file).encode()).hexdigest()[:10], file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, fn)


def _worst(rows: list[dict]) -> str:
    return max((r["status"] for r in rows), key=_ORDER.get, default=NOT_RUN)


def _measure(e: dict, files: list[Path], root: Path, soft: bool = False) -> dict:
    """One row for one requirement: the worst file result, the number and what was seen."""
    rid = e["id"]
    check = e.get("check") if isinstance(e.get("check"), dict) else {"kind": "unmapped"}
    base = {"id": rid, "measures": e.get("measures") or ""}
    if check.get("kind") == "judge":
        return dict(base, status=NOT_RUN, value=None, detail=f"judge step: {check.get('who')} against {check.get('rubric')}")
    if check.get("kind") != "validator":
        if soft:                                                          # a runner stage (owner 2026-11-20 09:11): listed, never a stop
            return dict(base, status=NOT_RUN, value=None, detail="unmapped: no validator and no judge step yet (listed, does not stop production)")
        return dict(base, status=BLOCK, value=None, detail="unmapped: no validator and no judge step yet; the registry entry blocks the send")
    bad = OR._check_errs(e, root)
    if bad:
        return dict(base, status=BLOCK, value=None, detail="; ".join(bad))
    ref = check.get("send_ref") or check["ref"]
    try:
        fn = _load_validator(ref, root)
    except Exception as exc:                                              # a validator that cannot be loaded fails closed
        return dict(base, status=BLOCK, value=None, detail=f"the validator {ref} cannot be loaded ({type(exc).__name__}: {exc})")
    if not hasattr(fn, "kinds"):                                          # a pipeline function (a queue, frames), not a check of a file
        return dict(base, status=NOT_RUN, value=None, detail=f"{ref} runs inside the pipeline and cannot measure a file: no send adapter "
                    "yet (check.send_ref names a function fn(path) with fn.kinds)")
    kinds = tuple(getattr(fn, "kinds", ()) or ())
    mine = [f for f in files if not kinds or f.suffix.lower() in kinds]
    if not mine:
        return dict(base, status=NOT_RUN, value=None, detail=f"no file of kind {', '.join(kinds)} in this send")
    rows = []
    for f in mine:
        try:
            r = fn(f)
            st = r["status"]
            if st not in (PASS, FAIL, NOT_RUN):
                raise ValueError(f"status {st!r}")
            rows.append({"file": str(f), "status": st, "value": r.get("value"), "detail": str(r.get("detail", ""))})
        except Exception as exc:
            rows.append({"file": str(f), "status": BLOCK, "value": None, "detail": f"the validator raised {type(exc).__name__}: {exc}"})
    worst = _worst(rows)
    pick = next(r for r in rows if r["status"] == worst)
    return dict(base, status=worst, value=pick["value"], detail=f"{pick['detail']} [{Path(pick['file']).name}]", files=rows)


def run(layer: str, files, *, root=None, owner_asked: str | None = None, now: float | None = None, record: bool = True,
        soft: bool = False) -> dict:
    """The report: ``{layer, status, rows, files, label}``; ``status`` is the worst of BLOCK > FAIL > NOT_RUN > PASS. ``soft`` (the runner's
    stage check, never the send to the owner) lists an unmapped entry and an open conflict as NOT_RUN instead of BLOCK."""
    root = root_dir(root)
    paths = [Path(f) for f in files]
    rows: list[dict] = []
    entries, errs = OR.load(root)
    gate = errs + OR.check_registry(entries, root) + OR.missing(entries)
    if layer not in OR.LAYERS:
        gate.append(f"REG-LAYER: {layer!r} is no layer of L1..L33")
    for p in paths:
        if not p.is_file():
            gate.append(f"SEND-NOFILE: {p} is not a file")
    if not paths:
        gate.append("SEND-NOFILE: nothing to send")
    for g in gate:
        rows.append({"id": g.split(":", 1)[0], "status": BLOCK, "value": None, "detail": g, "measures": ""})
    if not gate:
        for e in OR.bound(entries, layer):
            if OR.is_conflict(e):
                if e.get("status") == "open":
                    rows.append({"id": e["id"], "status": NOT_RUN if soft else BLOCK, "value": None, "measures": "", "detail":
                                 f"open conflict ({e.get('summary', '')[:80]}): " +
                                 ("listed, the owner has not answered" if soft else "blocked until the owner answers")})
                continue
            rows.append(_measure(e, paths, root, soft))
        if not rows:
            rows.append({"id": "-", "status": NOT_RUN, "value": None, "measures": "", "detail": f"no active requirement binds {layer}"})
    if not gate and _worst(rows) != PASS:
        for p in paths:
            q = quarantined(sha256(p), root=root) if p.is_file() else None
            if q:
                rows.append({"id": "QUARANTINE", "status": BLOCK, "value": None, "measures": "", "detail":
                             f"{p.name} was let go unchecked by the stop hook ({q.get('reason')}) and is quarantined: it can be a candidate only "
                             "after a send gate run that PASSES"})
    status = _worst(rows)
    failed = sorted(r["id"] for r in rows if r["status"] in (FAIL, BLOCK))
    label = None
    if owner_asked is not None:
        if not _MSG.fullmatch(owner_asked) or not failed:
            raise ValueError("--owner-asked takes the cmsg_ id of the owner's own message and only labels a send that fails")
        label = {"owner_asked": owner_asked, "text": "fails " + ", ".join(failed)}
    out = {"layer": layer, "status": status, "rows": rows, "label": label,
           "files": [{"path": str(p), "sha256": sha256(p)} for p in paths if p.is_file()]}
    if record and not gate:
        append_sealed(root / RECORDS, [dict(out, at=now if now is not None else time.time())])
    return out


def stage_check(layers, files, *, root=None) -> dict:
    """The runner's validator check on a stage's output files (owner 2026-11-20 09:11, the soft layer gate): every active requirement of the
    stage's layers whose validator can measure these files is run. Returns ``{"failed": [...], "passed": [...], "not_run": [...],
    "waived": [...]}``, each item ``"<layer> <id>: <detail>"``. Only ``failed`` stops production: a validator FAIL (or one that raised or
    cannot be loaded, or a broken registry) on a layer without the owner's recorded ``layer_waiver``. Unmapped entries, judge steps, open
    conflicts, validators without a send adapter and files of no validator's kind are ``not_run``: listed in every report, never a stop."""
    root = root_dir(root)
    out = {"failed": [], "passed": [], "not_run": [], "waived": []}
    paths = [Path(f) for f in files if Path(f).is_file()]
    if not paths:
        out["not_run"].append("no output file to measure")
        return out
    for layer in layers:
        rep = run(layer, paths, root=root, soft=True)
        for r in rep["rows"]:
            line = f"{layer} {r['id']}: {r['detail']}"
            if r["status"] in (FAIL, BLOCK):
                (out["waived"] if layer_gate.waived(layer, root=root) else out["failed"]).append(line)
            elif r["status"] == PASS:
                out["passed"].append(line)
            else:
                out["not_run"].append(line)
    return out


def render(rep: dict) -> str:
    lines = [f"send gate {rep['layer']}: {rep['status']}"]
    for r in rep["rows"]:
        num = "" if r["value"] is None else f" {r['value']}"
        lines.append(f"  {r['id']:9} {r['status']:8}{num}  {r['detail']}")
    if rep.get("label"):
        lines.append(f"  LABEL: {rep['label']['text']} (the owner asked to see failures: {rep['label']['owner_asked']})")
    return "\n".join(lines)


def quarantine(files, reason: str, *, root=None, now: float | None = None) -> list[dict]:
    """Quarantine files a stop hook let go unchecked: the send gate and the upload hook refuse them as candidates until a PASS record that is
    newer than the quarantine exists for the same bytes (a labelled owner-asked record does not lift it). The row is written to the sealed
    quarantine log AND to the sealed records log, so deleting one file does not lift it (S3)."""
    root = root_dir(root)
    at = now if now is not None else time.time()
    rows = [{"path": str(f), "sha256": sha256(f), "reason": reason, "at": at} for f in files if Path(f).is_file()]
    append_sealed(root / QUARANTINE, rows)
    if rows:
        append_sealed(root / RECORDS, [{"layer": "-", "status": "QUARANTINE", "rows": [], "label": None, "at": at, "reason": reason,
                                        "files": [{"path": r["path"], "sha256": r["sha256"]} for r in rows]}])
    return rows


def quarantined(digest: str, *, root=None) -> dict | None:
    """The newest quarantine row of these bytes in either sealed log (None when there is none)."""
    root = root_dir(root)
    last = None
    rows = read_sealed(root / QUARANTINE)
    for row in read_sealed(root / RECORDS):
        if row.get("status") == "QUARANTINE":
            rows += [{"sha256": f.get("sha256"), "reason": row.get("reason"), "at": row.get("at")} for f in row.get("files", [])]
    for row in rows:
        if row.get("sha256") == digest and (last is None or float(row.get("at", 0)) >= float(last.get("at", 0))):
            last = row
    return last


def passing_record(path: Path | str, *, root=None) -> dict | None:
    """The newest send record that covers this file's sha256 and lets it go: PASS (or NOT_RUN: nothing measurable failed) or a record
    labelled with the owner's ``owner_asked``; None when there is none (the hooks then refuse)."""
    root = root_dir(root)
    if not Path(path).is_file():
        return None
    digest = sha256(path)
    best = None
    for row in read_sealed(root / RECORDS):
        if any(f.get("sha256") == digest for f in row.get("files", [])) and \
                (row.get("status") in (PASS, NOT_RUN) or (row.get("label") or {}).get("owner_asked")):
            best = row
    q = quarantined(digest, root=root)
    if best is not None and q is not None and not (best.get("status") == PASS and float(best.get("at", 0)) > float(q.get("at", 0))):
        return None                                                        # a quarantined file needs a newer PASS, nothing weaker
    return best


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.governance.send_gate")
    ap.add_argument("layer")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--owner-asked", help="cmsg_ id of the owner's message asking to see a failing candidate (labels the record)")
    a = ap.parse_args(argv)
    try:
        rep = run(a.layer, a.files, owner_asked=a.owner_asked)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(render(rep))
    return 0 if rep["status"] in (PASS, NOT_RUN) else 1


if __name__ == "__main__":
    sys.exit(main())
