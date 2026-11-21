"""Picture batches (build items 4 and 5; GC-23..GC-27, spec Q1, Q3, Q7-Q12).

- ``render``: one batch of the queue as the message to paste (P6 for the reference rounds R1/R2, P7 for a scene batch in
  ``self_contained`` mode, P8 in ``queue_on_drive`` mode) plus ``batch_NN.attach.json``: the local files to attach, in
  the order of the ATTACHED line. Refused while T0 has not passed, while the video script's review is open, while any
  of the batch's references is not approved, and (scene batches) before the read is timed (voice first).
- ``intake``: the answer's BATCH REPORT plus the downloads IN ANSWER ORDER: mapped by position (Q9; a count that differs
  from MADE, or ids out of the sent order, is refused), each file gated for free (decodes, 16:9, at least 1376 wide, no
  letterbox, no duplicate, not a flat card drawn by code), copied under its target name and written to the ledger the
  moment it is checked. ``NOT MADE: limit`` leaves the batch ``partial`` for ``resume`` (P9, the next day); any other
  gap or a failed gate goes to the redo list. Nothing is redone inside a batch.
- ``verdict``: Claude's look at each picture: ``ok`` or ``redo`` with ONE positive correction sentence (Q11).
- ``approve``: the creator's word on a reference (portrait, full body, place), with his message id; a scene batch
  attaches only approved references.
- ``redo``: the redo list in batches of the batch size (P10), only when every batch of that phase (R1, R2, scenes) is
  done; a redo prompt is the original plus the correction sentence; the failed picture is never attached; a picture
  that fails its redo goes to the creator, never into a second redo (GC-25).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_text_atomic
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import gate as GT
from explainer_engine.gemini_task import prompts as PR
from explainer_engine.gemini_task import queue as QU
from explainer_engine.gemini_task import report as RP
from explainer_engine.gemini_task import texts as TX
from explainer_engine.imagegen import turn_pack as TP

STATE = "batches.json"
CARD_MAX_COLOURS = 48          # a 64x36 thumbnail of a generated picture has hundreds of colours; a code-drawn card a few
CARD_FLAT_SHARE = 0.55         # or one colour covering more than half of it
BLANK_STD = 3.0


# --- state ---------------------------------------------------------------------------------------------------------
def state(root: Path) -> dict:
    return EP.read_json(EP.work(root) / STATE, {"batches": {}, "pictures": {}, "redo": [], "redo_batches": {}})


def save_state(root: Path, st: dict) -> None:
    EP.save_json(EP.work(root) / STATE, st)


def _ledger(root: Path, row: dict) -> None:
    p = EP.work(root) / "picture_ledger.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:   # one line per file, the moment it is checked (OR-33)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ledger_rows(root: Path) -> list[dict]:
    p = EP.work(root) / "picture_ledger.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


# --- free gates ----------------------------------------------------------------------------------------------------
def looks_drawn(path: Path) -> dict:
    """A blank picture or a flat card drawn by code (F2: 164 text cards came back once) shows in a tiny thumbnail: very
    few colours, or one colour over most of it. A heuristic, so a miss is FAIL only for the plain cases it targets."""
    from PIL import Image
    with Image.open(path) as im:
        small = im.convert("RGB").resize((64, 36))
    import numpy as np
    a = np.asarray(small, dtype=np.int32)
    if float(a.std()) < BLANK_STD:
        return {"gate": "not_a_card", "status": "FAIL", "detail": "a blank picture"}
    q = (a // 16).reshape(-1, 3)
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    top = float(counts.max()) / keys.size
    if len(vals) <= CARD_MAX_COLOURS or top > CARD_FLAT_SHARE:
        return {"gate": "not_a_card", "status": "FAIL",
                "detail": f"{len(vals)} colours, the most common covers {top:.0%}: looks like a card drawn by code"}
    return {"gate": "not_a_card", "status": "PASS", "detail": f"{len(vals)} colours"}


def free_gates(path: Path | None, item: dict, seen: dict | None = None) -> list[dict]:
    """The free checks of one download: turn_pack's GC-12 gates (decodes, 16:9, native size, letterbox, duplicate) and
    the card check. Identity and lettering are Claude's look (``verdict``), listed NOT_RUN here."""
    if path is None:
        return [{"gate": "file", "status": "FAIL", "detail": "no file"}]
    try:
        rows = TP.gate_file(Path(path), dict(item, people=[]), TP.NATIVE_CHAT_SIZE, seen)
    except ModuleNotFoundError as e:     # imagehash is optional on a bare machine: the duplicate gate says NOT_RUN
        rows = TP.gate_file(Path(path), dict(item, people=[]), TP.NATIVE_CHAT_SIZE, None)
        rows.append({"gate": "not_duplicate", "status": "NOT_RUN", "detail": f"{e.name} is not installed"})
    if rows and rows[0]["status"] == "PASS":
        rows.append(looks_drawn(Path(path)))
    return rows


def map_by_order(rep: dict, files: list[Path]) -> list[tuple[dict, Path | None]]:
    """Q9: the MADE lines, in report order, take the downloads in answer order; a count mismatch is refused."""
    made = [it for it in rep["items"] if it["status"] == "MADE"]
    if len(files) != len(made):
        raise ContractError(f"{len(files)} downloaded file(s) but the report says MADE {len(made)}: refused, nothing is "
                            "guessed (Q9). Download every picture of the answer, in its order.")
    it_files = iter(files)
    return [(it, next(it_files) if it["status"] == "MADE" else None) for it in rep["items"]]


def drop_files(folder: Path) -> list[Path]:
    """The downloads of one answer, in answer order: the PC session saves them as 01.jpg, 02.jpg, ... (sorted by name)."""
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in TP.IMAGE_EXTS)


# --- blocking --------------------------------------------------------------------------------------------------------
def needs(root: Path, doc: dict, it: dict, st: dict) -> list[str]:
    """What this picture still waits for: unapproved anchors and references, and an end frame's start frame that was not
    accepted."""
    approved = QU.references_state(root)
    anchors = {f"style_{a['type']}" for a in QU.anchors() if a.get("status") == "approved" and a.get("sha256")}
    out = []
    for r in it["references"]:
        rid = r["ref_id"]
        if rid == "style_main":
            continue
        if rid.startswith("style_"):
            if rid not in anchors:
                out.append(rid)
        elif rid.startswith("ref_"):
            if rid not in approved:
                out.append(rid)
        else:
            p = st["pictures"].get(rid) or {}
            if p.get("verdict") != "ok":
                out.append(rid)
    return out


def local_file(root: Path, doc: dict, ref: dict, st: dict) -> Path:
    """Where the file to attach lives on this machine (main style in the repo, anchors from the config, references and
    start frames from the episode)."""
    rid = ref["ref_id"]
    if rid == "style_main":
        return EP.REPO / EP.config()["main_style"]["file"]
    if rid.startswith("style_"):
        a = QU.anchor_of(rid[len("style_"):])
        return EP.REPO / a["file"]
    if rid.startswith("ref_"):
        return Path(root) / QU.references_state(root)[rid]["file"]
    return Path(root) / st["pictures"][rid]["file"]


# --- rendering -------------------------------------------------------------------------------------------------------
def _blocks(items: list[dict], redo: dict | None = None) -> str:
    out = []
    for k, it in enumerate(items, 1):
        refs = [(r["file"], r["role"]) for r in it["references"]]
        if redo:
            r = redo[it["id"]]
            out.append(PR.block(k, len(items), it["id"], r["target"], refs, r["prompt"], replaces=it["target"]))
        else:
            out.append(PR.block(k, len(items), it["id"], it["target"], refs, it["prompt"]))
    return "\n\n".join(out)


def _attached(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        for r in it["references"]:
            if r["file"] not in seen:
                seen.add(r["file"])
                out.append(r)
    return out


def _write_message(root: Path, name: str, text: str, attach: list[dict], meta: dict) -> dict:
    d = EP.work(root) / "messages"
    d.mkdir(parents=True, exist_ok=True)
    write_text_atomic(d / f"{name}.md", text + "\n")
    meta = dict(meta, message=f"planning/gemini_task/messages/{name}.md", attach=attach)
    EP.save_json(d / f"{name}.attach.json", meta)
    return meta


def _preconditions(root: Path, doc: dict, b: dict) -> None:
    from explainer_engine.gemini_task import review as RV
    GT.require(f"batch {b['no']}")
    rv = RV.stage_status(root, "video_script")
    if rv["status"] != "PASS":
        raise ContractError(f"batch {b['no']}: the video script's review is {rv['status']} ({rv['why']}); no picture "
                            "batch before the shot queue has passed its check (GC-26)")
    if rv.get("sha8") and rv["sha8"] != TX.sha8(json.dumps(QU.shot_list(doc), ensure_ascii=False, indent=1)):
        raise ContractError(f"batch {b['no']}: the queue changed after its review (sha {rv['sha8']}); check it again (P3)")
    if b["kind"] == "scene" and not doc["timed"]:
        raise ContractError(f"batch {b['no']}: the read is not timed yet; voice comes first (build item 6, RN-03)")


def render(root: Path, no: int) -> dict:
    root = Path(root)
    doc = QU.load(root)
    man, _ = EP.load(root)
    lk = EP.look(man)
    st = state(root)
    b = next((x for x in doc["batches"] if x["no"] == no), None)
    if b is None:
        raise ContractError(f"the queue has no batch {no}")
    if st["batches"].get(str(no), {}).get("status") in ("done", "partial"):
        raise ContractError(f"batch {no} is {st['batches'][str(no)]['status']}: use resume for a partial batch, never send it twice")
    _preconditions(root, doc, b)
    items_by = QU.items_by_id(doc)
    items = [items_by[i] for i in b["ids"]]
    waiting = {it["id"]: needs(root, doc, it, st) for it in items}
    waiting = {k: v for k, v in waiting.items() if v}
    if waiting:
        raise ContractError(f"batch {no} waits for approvals: {waiting} (GC-23: references first)")
    for it in items:
        bad = PR.fails(it["checks"])
        if bad:
            raise ContractError(f"{it['id']}: prompt rule FAIL {bad}")
    attach = _attached(items)
    blocks = _blocks(items)
    s8 = TX.sha8(blocks)
    common = {"episode_id": man["episode_id"], "sha8": s8, "n": len(items), "era_line": doc["era_line"],
              "drive_root": EP.config()["drive_root"], "attached_list": ", ".join(r["file"] for r in attach),
              "picture_blocks": blocks}
    if b["kind"] in ("R1", "R2"):
        msg = "P6"
        vals = dict(common, round=b["kind"], round_note=TX.ROUND_NOTES[b["kind"]])
        expect = b["kind"]
    elif doc["mode"] == "queue_on_drive":
        if not st.get("queue_saved") or st["queue_saved"].get("sha8") != TX.sha8(QU.path(root).read_text(encoding="utf-8")):
            raise ContractError("queue_on_drive: the queue on Drive is not this queue (send P5 and record its answer first)")
        msg = "P8"
        vals = {"episode_id": man["episode_id"], "sha8": st["queue_saved"]["sha8"], "batch_no": no,
                "batch_total": len(doc["batches"]), "n": len(items), "picture_ids": ", ".join(b["ids"]),
                "era_line": doc["era_line"], "drive_root": EP.config()["drive_root"]}
        expect = str(no)
    else:
        msg = "P7"
        vals = dict(common, batch_no=no, batch_total=len(doc["batches"]))
        expect = str(no)
    text = TX.render(msg, vals, lk["never_words"])
    attach_rows = [{"n": k, "drive_name": r["file"], "local": str(local_file(root, doc, r, st))}
                   for k, r in enumerate(attach, 1)]
    meta = _write_message(root, f"batch_{no:03d}", text, attach_rows,
                          {"batch": no, "kind": b["kind"], "msg": msg, "sha8": s8, "ids": b["ids"], "expect": expect})
    st["batches"][str(no)] = {"status": "sent", "sent_at": EP.now(), "sha8": s8, "msg": msg, "ids": b["ids"],
                              "expect": expect}
    save_state(root, st)
    return meta


# --- intake ----------------------------------------------------------------------------------------------------------
def _seen(root: Path) -> dict:
    out = {}
    for r in ledger_rows(root):
        if r.get("phash") is not None and r.get("ok"):
            out[r["id"]] = r["phash"]
    return out


def _take(root: Path, it: dict, rep_it: dict, f: Path | None, seen: dict, where: str, target: str) -> dict:
    gates = free_gates(f, it, seen)
    ok = f is not None and all(g["status"] != "FAIL" for g in gates)
    dest = None
    if f is not None:
        dest = EP.work(root) / "pictures" / Path(target).with_suffix(Path(f).suffix.lower()).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if Path(f).resolve() != dest.resolve():
            shutil.copy2(f, dest)
    row = {"id": it["id"], "where": where, "file": str(dest.relative_to(root)) if dest else None,
           "sha256": EP.sha256_file(dest) if dest else None, "ok": ok, "gates": gates, "prompt": rep_it.get("prompt"),
           "changed": rep_it.get("changed"), "note": rep_it.get("note"), "phash": seen.get(it["id"]), "at": EP.now()}
    _ledger(root, row)
    return row


def intake(root: Path, no: int, answer_text: str, files: list[Path]) -> dict:
    root = Path(root)
    doc = QU.load(root)
    st = state(root)
    sent = st["batches"].get(str(no))
    if not sent or sent["status"] not in ("sent", "resumed"):
        raise ContractError(f"batch {no} was not sent (or is already taken in): nothing to take in")
    rep = RP.parse_batch_report(answer_text, expect=sent["expect"])
    want = sent.get("resume_ids") or sent["ids"]
    if [it["id"] for it in rep["items"]] != want:
        raise ContractError(f"the report lists {[it['id'] for it in rep['items']]}, the batch sent {want} in that order (Q9)")
    mapped = map_by_order(rep, files)
    items_by = QU.items_by_id(doc)
    seen = _seen(root)
    taken, limit, redo = [], [], []
    for rep_it, f in mapped:
        it = items_by[rep_it["id"]]
        if rep_it["status"] == "NOT MADE":
            if rep_it["limit"]:
                limit.append(it["id"])
                st["pictures"][it["id"]] = {"status": "limit", "batch": no}
            else:
                redo.append({"id": it["id"], "why": f"not made: {rep_it['reason']}", "kind": "not_made", "correction": None})
                st["pictures"][it["id"]] = {"status": "not_made", "batch": no, "reason": rep_it["reason"]}
            _ledger(root, {"id": it["id"], "where": f"batch {no}", "file": None, "ok": False, "not_made": rep_it["reason"],
                           "at": EP.now()})
            continue
        row = _take(root, it, rep_it, f, seen, f"batch {no}", it["target"])
        st["pictures"][it["id"]] = {"status": "made", "batch": no, "file": row["file"], "sha256": row["sha256"],
                                    "gates_ok": row["ok"], "prompt": rep_it["prompt"], "changed": rep_it["changed"],
                                    "note": rep_it["note"], "verdict": None}
        if not row["ok"]:
            failed = [g["gate"] for g in row["gates"] if g["status"] == "FAIL"]
            redo.append({"id": it["id"], "why": f"free gate FAIL: {failed}", "kind": "gate", "correction": None})
            st["pictures"][it["id"]]["verdict"] = "redo"
        taken.append(row)
    for r in redo:
        _add_redo(st, r)
    sent["status"] = "partial" if limit else "done"
    sent["taken_at"] = EP.now()
    sent["limit_ids"] = limit
    sent.pop("resume_ids", None)
    save_state(root, st)
    sheet = TP.contact_sheet(root, [((root / r["file"]) if r["file"] else Path("-"), r["id"], r["ok"]) for r in taken]) \
        if taken else None
    return {"batch": no, "made": rep["made"], "of": rep["total"], "taken": [r["id"] for r in taken if r["ok"]],
            "gate_fail": [r["id"] for r in taken if not r["ok"]], "limit": limit, "redo": [r["id"] for r in redo],
            "changed_prompts": [r["id"] for r in taken if r["prompt"] == "CHANGED"],
            "sheet": str(sheet.relative_to(root)) if sheet else None,
            "next": "resume tomorrow from " + limit[0] if limit else "Claude looks at every picture (verdict)"}


def _add_redo(st: dict, r: dict) -> None:
    prior = [x for x in st["redo"] if x["id"] == r["id"]]
    if any(x.get("status") in ("sent", "done") for x in prior):      # failed its redo: to the creator (GC-25)
        st["pictures"].setdefault(r["id"], {})["status"] = "creator"
        st.setdefault("creator", []).append(dict(r, at=EP.now()))
        return
    if prior:
        prior[0].update({k: v for k, v in r.items() if v is not None})
        return
    st["redo"].append(dict(r, status="listed", at=EP.now()))


def verdict(root: Path, pid: str, ok: bool, reason: str = "", correction: str | None = None) -> dict:
    """Claude's look at one taken-in picture. A redo needs ONE positive correction sentence, gated with the prompt."""
    root = Path(root)
    doc = QU.load(root)
    st = state(root)
    p = st["pictures"].get(pid)
    if not p or p.get("status") != "made":
        raise ContractError(f"{pid} has no taken-in picture to judge")
    if ok:
        if not p.get("gates_ok"):
            raise ContractError(f"{pid} failed a free gate; it cannot be passed by eye")
        p["verdict"], p["verdict_reason"] = "ok", reason or "-"
    else:
        it = QU.items_by_id(doc)[pid]
        man, _ = EP.load(root)
        lk = EP.look(man)
        if not correction:
            raise ContractError(f"{pid}: a redo needs one correction sentence in positive words (Q11)")
        rows = PR.check(it["prompt"] + " " + correction, lk, doc["era_line"], it["kind"],
                        [], subject="", correction=correction)   # the original passed at queue time
        bad = [r for r in PR.fails(rows) if r["rule"] in ("GC-25", "GC-18", "GC-07", "GC-11", "GC-22")]
        if bad:
            raise ContractError(f"{pid}: the correction sentence fails {bad}")
        p["verdict"], p["verdict_reason"] = "redo", reason
        _add_redo(st, {"id": pid, "why": reason, "kind": "look", "correction": correction})
    save_state(root, st)
    return p


def approve(root: Path, ref: str, approved_by: str) -> dict:
    """The creator's word on a reference picture (GC-23). Only a reference Claude passed (``verdict ok``) can be approved."""
    root = Path(root)
    if not ref.startswith("ref_"):
        raise ContractError(f"{ref} is not a reference (portrait, full body or place)")
    if not approved_by:
        raise ContractError("the creator's message id is required")
    st = state(root)
    p = st["pictures"].get(ref) or {}
    if p.get("verdict") != "ok":
        raise ContractError(f"{ref}: Claude has not passed it (verdict ok) yet")
    refs = QU.references_state(root)
    refs[ref] = {"file": p["file"], "sha256": p["sha256"], "approved_by": approved_by, "at": EP.now()}
    EP.save_json(EP.work(root) / "refs_approved.json", refs)
    return refs[ref]


def approve_anchor(stype: str, file: str, approved_by: str) -> dict:
    """The creator's pick of a style anchor after T0 (spec section 6): writes its file, sha256 and his message id into
    config/gemini_task.json. ``file`` is repo-relative."""
    if not approved_by:
        raise ContractError("the creator's message id is required")
    src = EP.REPO / file
    if not src.is_file():
        raise ContractError(f"{file} does not exist in the repo")
    doc = json.loads(EP.CONFIG.read_text(encoding="utf-8"))
    for a in doc["style_pack"]["types"]:
        if a["type"] == stype:
            a.update({"file": file, "sha256": EP.sha256_file(src), "status": "approved", "approved_by": approved_by})
            EP.save_json(EP.CONFIG, doc)
            EP.config.cache_clear()
            return a
    raise ContractError(f"no style anchor type {stype!r}")


# --- resume after the limit (P9) -------------------------------------------------------------------------------------
def resume(root: Path, no: int) -> dict:
    root = Path(root)
    doc = QU.load(root)
    man, _ = EP.load(root)
    lk = EP.look(man)
    st = state(root)
    sent = st["batches"].get(str(no))
    if not sent or sent["status"] != "partial" or not sent.get("limit_ids"):
        raise ContractError(f"batch {no} has nothing left from a limit")
    GT.require(f"resume of batch {no}")
    items_by = QU.items_by_id(doc)
    items = [items_by[i] for i in sent["limit_ids"]]
    attach = _attached(items)
    blocks = _blocks(items)
    vals = {"episode_id": man["episode_id"], "sha8": TX.sha8(blocks), "batch_no": no, "batch_total": len(doc["batches"]),
            "n": len(items), "first_missing_id": items[0]["id"], "era_line": doc["era_line"],
            "attached_list": ", ".join(r["file"] for r in attach), "picture_blocks": blocks,
            "drive_root": EP.config()["drive_root"]}
    text = TX.render("P9", vals, lk["never_words"])
    attach_rows = [{"n": k, "drive_name": r["file"], "local": str(local_file(root, doc, r, st))} for k, r in enumerate(attach, 1)]
    meta = _write_message(root, f"batch_{no:03d}_resume", text, attach_rows,
                          {"batch": no, "msg": "P9", "ids": sent["limit_ids"], "expect": str(no)})
    sent.update({"status": "resumed", "resume_ids": list(sent["limit_ids"]), "expect": str(no) if sent["msg"] != "P6" else sent["expect"]})
    save_state(root, st)
    return meta


# --- the redo list at the end (P10) ----------------------------------------------------------------------------------
def phase_of(doc: dict, pid: str) -> str:
    it = QU.items_by_id(doc)[pid]
    return it.get("round") or "scene"


def phase_done(doc: dict, st: dict, phase: str) -> bool:
    for b in doc["batches"]:
        if (b["kind"] if b["kind"] in ("R1", "R2") else "scene") != phase:
            continue
        if st["batches"].get(str(b["no"]), {}).get("status") != "done":
            return False
    return True


def redo(root: Path, phase: str) -> list[dict]:
    """The redo batches of one phase (R1, R2 or scene), written as P10 messages, at most the batch size each."""
    root = Path(root)
    doc = QU.load(root)
    man, _ = EP.load(root)
    lk = EP.look(man)
    st = state(root)
    GT.require("a redo batch")
    if not phase_done(doc, st, phase):
        raise ContractError(f"phase {phase} still has batches to send or resume: no redo inside the run (GC-25)")
    listed = [r for r in st["redo"] if r.get("status") == "listed" and phase_of(doc, r["id"]) == phase]
    missing = [r["id"] for r in listed if r["kind"] == "look" and not r.get("correction")]
    if missing:
        raise ContractError(f"redo items without a correction sentence: {missing}")
    items_by = QU.items_by_id(doc)
    size = int(doc["batch_size"])
    out = []
    for k in range(0, len(listed), size):
        chunk = listed[k:k + size]
        no = len(st["redo_batches"]) + 1
        items = [items_by[r["id"]] for r in chunk]
        waiting = {it["id"]: needs(root, doc, it, st) for it in items}
        waiting = {k2: v for k2, v in waiting.items() if v}
        if waiting:
            raise ContractError(f"redo items wait for approvals: {waiting}")
        rd = {}
        for r, it in zip(chunk, items):
            prompt = it["prompt"] + (" " + r["correction"].strip() if r.get("correction") else "")
            rows = PR.check(prompt, lk, doc["era_line"], it["kind"], [], subject="",
                            correction=r.get("correction")) if r.get("correction") else []
            bad = [x for x in PR.fails(rows) if x["rule"] in ("GC-25", "GC-18", "GC-07", "GC-11", "GC-22")]
            if bad:
                raise ContractError(f"{it['id']}: redo prompt fails {bad}")
            failed = (st["pictures"].get(it["id"]) or {}).get("file")
            if failed and any(failed.endswith(ref["file"]) for ref in it["references"]):
                raise ContractError(f"{it['id']}: the failed picture would be attached (Q11)")
            rd[it["id"]] = {"target": Path(it["target"]).stem + "_redo1.jpg", "prompt": prompt}
        attach = _attached(items)
        blocks = _blocks(items, rd)
        total = no + -(-(len(listed) - k - len(chunk)) // size)
        vals = {"episode_id": man["episode_id"], "sha8": TX.sha8(blocks), "redo_no": no, "redo_total": total,
                "n": len(items), "era_line": doc["era_line"], "attached_list": ", ".join(r2["file"] for r2 in attach),
                "picture_blocks": blocks, "drive_root": EP.config()["drive_root"]}
        text = TX.render("P10", vals, lk["never_words"])
        attach_rows = [{"n": j, "drive_name": r2["file"], "local": str(local_file(root, doc, r2, st))}
                       for j, r2 in enumerate(attach, 1)]
        meta = _write_message(root, f"redo_{no:03d}", text, attach_rows,
                              {"redo": no, "phase": phase, "msg": "P10", "ids": [it["id"] for it in items],
                               "expect": f"redo {no}", "redo_prompts": rd})
        st["redo_batches"][str(no)] = {"status": "sent", "phase": phase, "ids": [it["id"] for it in items], "redo": rd,
                                       "sent_at": EP.now(), "expect": f"redo {no}"}
        for r in chunk:
            r["status"], r["redo_no"] = "sent", no
        out.append(meta)
    save_state(root, st)
    return out


def intake_redo(root: Path, no: int, answer_text: str, files: list[Path]) -> dict:
    root = Path(root)
    doc = QU.load(root)
    st = state(root)
    rb = st["redo_batches"].get(str(no))
    if not rb or rb["status"] != "sent":
        raise ContractError(f"redo batch {no} was not sent")
    rep = RP.parse_batch_report(answer_text, expect=rb["expect"])
    if [it["id"] for it in rep["items"]] != rb["ids"]:
        raise ContractError(f"the report lists {[it['id'] for it in rep['items']]}, redo {no} sent {rb['ids']} (Q9)")
    items_by = QU.items_by_id(doc)
    seen = _seen(root)
    out = {"redo": no, "taken": [], "to_creator": []}
    for rep_it, f in map_by_order(rep, files):
        it = items_by[rep_it["id"]]
        entry = next(x for x in st["redo"] if x["id"] == it["id"] and x.get("redo_no") == no)
        entry["status"] = "done"
        if rep_it["status"] == "NOT MADE":
            st["pictures"][it["id"]] = {"status": "creator", "reason": f"redo not made: {rep_it['reason']}"}
            out["to_creator"].append(it["id"])
            continue
        row = _take(root, it, rep_it, f, seen, f"redo {no}", rb["redo"][it["id"]]["target"])
        st["pictures"][it["id"]] = {"status": "made", "redo": no, "file": row["file"], "sha256": row["sha256"],
                                    "gates_ok": row["ok"], "prompt": rep_it["prompt"], "changed": rep_it["changed"],
                                    "note": rep_it["note"], "verdict": None if row["ok"] else "creator"}
        (out["taken"] if row["ok"] else out["to_creator"]).append(it["id"])
    rb["status"] = "done"
    save_state(root, st)
    return out


def status(root: Path) -> dict:
    doc = QU.load(root)
    st = state(root)
    pics = st["pictures"]
    allids = [it["id"] for it in doc["references"] + doc["pictures"]]
    return {"episode_id": doc["episode_id"], "t0": GT.state(), "batches": len(doc["batches"]),
            "sent": sum(1 for b in st["batches"].values() if b["status"] != "planned"),
            "ok": sum(1 for i in allids if (pics.get(i) or {}).get("verdict") == "ok"),
            "to_judge": [i for i in allids if (pics.get(i) or {}).get("status") == "made" and not pics[i].get("verdict")],
            "redo_listed": [r["id"] for r in st["redo"] if r.get("status") == "listed"],
            "to_creator": [i for i in allids if (pics.get(i) or {}).get("status") == "creator"],
            "open": [i for i in allids if (pics.get(i) or {}).get("verdict") != "ok"]}


# --- P5: the queue saved on Gemini's side (queue_on_drive only) ------------------------------------------------------
def render_save_queue(root: Path) -> dict:
    root = Path(root)
    GT.require("saving the queue on Drive")
    doc = QU.load(root)
    man, _ = EP.load(root)
    lk = EP.look(man)
    from explainer_engine.gemini_task import review as RV
    if RV.stage_status(root, "video_script")["status"] != "PASS":
        raise ContractError("the video script's check has not passed: the queue is not approved yet (GC-26)")
    text = QU.path(root).read_text(encoding="utf-8")
    s8 = TX.sha8(text)
    vals = {"episode_id": man["episode_id"], "sha8": s8, "n": len(doc["references"]) + len(doc["pictures"]),
            "shot_queue_json": text.strip(), "drive_root": EP.config()["drive_root"]}
    msg = TX.render("P5", vals, lk["never_words"])
    meta = _write_message(root, "save_queue", msg, [], {"msg": "P5", "sha8": s8, "n": vals["n"]})
    st = state(root)
    st["queue_save_sent"] = {"sha8": s8, "n": vals["n"], "sent_at": EP.now()}
    save_state(root, st)
    return meta


def intake_save_queue(root: Path, answer_text: str) -> dict:
    import re
    st = state(root)
    sent = st.get("queue_save_sent")
    if not sent:
        raise ContractError("no P5 was sent")
    saved = re.search(r"^\W*SAVED:\s*(.+)$", answer_text, re.M | re.I)
    count = re.search(r"^\W*PICTURES:\s*(\d+)", answer_text, re.M | re.I)
    sha = re.search(r"^\W*SHA:\s*([0-9a-f]{8})", answer_text, re.M | re.I)
    ok = bool(saved and not saved.group(1).strip().upper().startswith("FAILED") and count and int(count.group(1)) == sent["n"]
              and sha and sha.group(1).lower() == sent["sha8"])
    st["queue_saved"] = {"sha8": sent["sha8"], "ok": ok, "path": saved.group(1).strip() if saved else None,
                         "at": EP.now()} if ok else None
    save_state(root, st)
    return {"saved": ok, "detail": answer_text.strip()[:300]}
