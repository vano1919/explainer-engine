"""Gate T0 (build item 7, GC-20): the Task route is off until T0 is recorded as passed.

``render_t0`` writes the T0 message (the six anchor candidates of PROMPT_CLAUSES.md, the main style picture attached);
``record_t0`` reads the answer and the downloaded pictures (in answer order) and writes the record
``config/gemini_t0_record.json``:

- PASS with batch size 6 when one answer on Flash in Task mode holds six generated pictures, none drawn by code, each
  16:9 and at least 1376 wide; four or five: PASS with that batch size; three or fewer, or another model: FAIL and a
  card for the creator (spec section 6);
- batch mode ``queue_on_drive`` only when DRIVE READ quoted the exported pack version AND every line came back
  ``prompt: AS GIVEN`` (Q3); otherwise ``self_contained``.

``require`` is called by everything that sends Gemini a message other than T0 itself.
"""
from __future__ import annotations

from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import prompts as PR
from explainer_engine.gemini_task import report as RP
from explainer_engine.gemini_task import texts as TX

SCHEMA = "gemini_t0_record/1"
T0_IDS = ("t0_B2", "t0_C3", "t0_D2", "t0_E", "t0_F", "t0_G")
T0_PEOPLE = {"t0_B2": True, "t0_C3": True, "t0_D2": False, "t0_E": True, "t0_F": True, "t0_G": True}
FULL, MIN_PASS = 6, 4


def record_path() -> Path:
    return EP.REPO / EP.config()["t0_record"]


def state() -> dict:
    """The current T0 state: ``{"status": NOT_RUN|PASS|FAIL, "batch_size", "batch_mode"}`` (defaults until recorded)."""
    rec = EP.read_json(record_path())
    if not rec:
        return {"status": "NOT_RUN", "batch_size": int(EP.config()["batch_size_default"]), "batch_mode": "self_contained"}
    return {"status": rec["status"], "batch_size": int(rec.get("batch_size") or EP.config()["batch_size_default"]),
            "batch_mode": rec.get("batch_mode") or "self_contained"}


def require(what: str) -> dict:
    st = state()
    if st["status"] != "PASS":
        raise ContractError(f"{what}: the Gemini Task route is off until T0 is recorded as PASS (GC-20); T0 is "
                            f"{st['status']}. Send the T0 message first (gemini_task t0) and record its answer.")
    return st


def t0_items(lk: dict, era: str) -> list[dict]:
    main = EP.config()["main_style"]
    out = []
    for cid in T0_IDS:
        subject = TX.clause(cid)
        prompt = PR.assemble(lk, era, "anchor", subject, people=T0_PEOPLE[cid])
        checks = PR.check(prompt, lk, era, "anchor", subject=subject)
        if T0_PEOPLE[cid] and lk["face_sentence"] not in prompt:
            raise ContractError(f"{cid}: a picture with people lacks the face sentence")
        out.append({"id": cid, "target": f"{cid}.jpg", "references": [{"file": main["drive_name"], "role": "style",
                                                                       "ref_id": "style_main"}],
                    "prompt": prompt, "checks": checks})
    return out


def render_t0(root: Path) -> dict:
    """The T0 message for the episode (its era line), its attachment and the pack version it must quote."""
    from explainer_engine.gemini_task import pack as PK
    root = Path(root)
    man, _ = EP.load(root)
    lk = EP.look(man)
    era = EP.era_line(man, lk)
    items = t0_items(lk, era)
    bad = [(it["id"], c) for it in items for c in it["checks"] if c["severity"] == "FAIL"]
    if bad:
        raise ContractError(f"T0 prompt rule(s) FAIL: {bad}")
    blocks = [PR.block(k, len(items), it["id"], it["target"], [(r["file"], r["role"]) for r in it["references"]],
                      it["prompt"]) for k, it in enumerate(items, 1)]
    picture_blocks = "\n\n".join(blocks)
    s8 = TX.sha8("\n".join(it["prompt"] for it in items))
    values = {"episode_id": man["episode_id"], "sha8": s8, "drive_root": EP.config()["drive_root"], "era_line": era,
              "picture_blocks": picture_blocks}
    text = TX.render("T0", values, lk["never_words"])
    out = EP.work(root) / "messages" / "T0.md"
    from explainer_engine.core.store import write_text_atomic
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(out, text + "\n")
    main = EP.config()["main_style"]
    sent = {"schema": "gemini_t0_sent/1", "episode_id": man["episode_id"], "sha8": s8, "made_at": EP.now(),
            "pack_version": PK.current_version(root), "attach": [{"file": main["file"], "drive_name": main["drive_name"],
                                                                   "sha256": main["sha256"]}],
            "ids": [it["id"] for it in items], "message": str(out.relative_to(root))}
    EP.save_json(EP.work(root) / "messages" / "T0.sent.json", sent)
    return sent


def record_t0(root: Path, answer_text: str, files: list[Path], recorded_by: str, code_drawn: int = 0,
              elapsed_s: float | None = None, hf: dict | None = None, write: bool = True) -> dict:
    """Read the T0 answer and the downloads (in answer order), gate them and write the record. ``code_drawn`` = pictures
    the operator saw drawn by code (A3 looks at the answer)."""
    from explainer_engine.gemini_task import batch as BT
    root = Path(root)
    sent = EP.read_json(EP.work(root) / "messages" / "T0.sent.json")
    if not sent:
        raise ContractError("no T0.sent.json: render the T0 message first")
    rep = RP.parse_t0_report(answer_text)
    if rep["sha8"] != sent["sha8"]:
        raise ContractError(f"the answer is for sha {rep['sha8']}, the T0 sent was {sent['sha8']}")
    if [it["id"] for it in rep["batch"]["items"]] != sent["ids"]:
        raise ContractError(f"the report's ids {[it['id'] for it in rep['batch']['items']]} are not the sent order {sent['ids']}")
    mapped = BT.map_by_order(rep["batch"], [Path(f) for f in files])
    pictures, real = [], 0
    for it, f in mapped:
        gates = BT.free_gates(f, {"id": it["id"], "kind": "anchor", "people": []})
        ok = all(g["status"] != "FAIL" for g in gates)
        real += ok
        pictures.append({"k": it["k"], "id": it["id"], "file": str(f), "sha256": EP.sha256_file(f) if f else None,
                         "prompt": it["prompt"], "gates": gates, "ok": ok, "hf": (hf or {}).get(it["id"])})
    real = max(0, real - int(code_drawn))
    model_ok = "flash" in (rep["model"] or "").lower() and not any(
        w in (rep["model"] or "").lower() for w in ("pro", "argon", "carbon"))
    as_given = all(it.get("prompt") == "AS GIVEN" for it in rep["batch"]["items"] if it["status"] == "MADE") and \
        all(it["status"] == "MADE" for it in rep["batch"]["items"])
    read_ok = rep["drive_read"]["ok"] and sent.get("pack_version") and sent["pack_version"] in rep["drive_read"]["detail"]
    if not model_ok:
        status, size, why = "FAIL", None, f"model {rep['model']!r} is not Flash"
    elif real >= FULL:
        status, size, why = "PASS", FULL, "six generated pictures in one answer"
    elif real >= MIN_PASS:
        status, size, why = "PASS", real, f"{real} generated pictures: the batch size becomes {real}"
    else:
        status, size, why = "FAIL", None, f"only {real} usable generated pictures"
    rec = {"schema": SCHEMA, "status": status, "why": why, "recorded_at": EP.now(), "recorded_by": recorded_by,
           "episode_id": sent["episode_id"], "sha8": sent["sha8"], "model": rep["model"], "mode": rep["mode"],
           "drive_read": dict(rep["drive_read"], matches_pack=bool(read_ok), pack_version=sent.get("pack_version")),
           "drive_write": rep["drive_write"], "made": rep["batch"]["made"], "real_pictures": real,
           "code_drawn": int(code_drawn), "prompts_as_given": as_given, "limit": rep["limit"], "elapsed_s": elapsed_s,
           "batch_size": size, "batch_mode": "queue_on_drive" if status == "PASS" and read_ok and as_given else "self_contained",
           "pictures": pictures}
    if status == "FAIL":
        rec["card"] = {"question": "T0 failed: how do we make the pictures?",
                       "facts": why, "options": [
                           {"label": "Chat route (GC-17)", "consequence": "One prompt per message in the normal Flash chat, as in reference round 1."},
                           {"label": "Retry T0 once tomorrow", "consequence": "Same message after the daily limit resets; nothing else changes."},
                           {"label": "Smaller batches", "consequence": "Batches of the number T0 made, if at least one picture came back."},
                           {"label": "Stop the Task route", "consequence": "The route stays off; the creator decides the next step."}]}
    if write:
        EP.save_json(record_path(), rec)
    return rec
