"""The shot queue (build item 3): ``planning/gemini_task/shot_queue.json`` from the approved video script.

Per shot: route and bucket (10 map / 30 still / 60 video, measured by seconds and reported, never forced: RT-04, the
+-10 % frame), its measured length (voice first, ``timing``), shot type and its style anchor (GC-21, Q4), cast and place,
and the pictures it needs (start frame, end frame of a chained Wan shot; a map shot needs none, Python draws it).
Per picture: references in order [style anchor, heroes (portrait, then full body where the shot shows bodies), place];
an end frame takes its own start frame as image 2 after the style anchor (GC-09 as amended by GC-21, A1b open item 3);
the prompt assembled from PROMPT_CLAUSES.md and gated (``prompts.check``).

Order of making (GC-23): round R1 (portraits and places, the main style picture only), round R2 (full bodies with
their own portrait), then the scene batches, grouped by place and style anchor (Q10), start frames before end frames
(an end frame never shares a batch with its start frame). A picture whose anchor, hero or place reference is not
approved is ``blocked``: it stays in the plan, and ``batch`` refuses to send it.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import router as RO
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import prompts as PR
from explainer_engine.gemini_task import texts as TX
from explainer_engine.gemini_task import timing as TM
from explainer_engine.imagegen import turn_pack as TP

SCHEMA = "shot_queue/1"
BUCKET = {"map_action": 10, "still_25d": 30, "wan": 60}
MIX_KEYS = {"map_action": "map_visualization_target", "still_25d": "composed_illustration_target",
            "wan": "cinematic_video_target"}


def ref_id(kind: str, subject_id: str) -> str:
    return f"ref_{subject_id}_{kind}"


def ref_target(rid: str) -> str:
    return f"refs/{rid}.jpg"


def picture_target(pid: str) -> str:
    return f"{pid}.jpg"


def references_state(root: Path) -> dict:
    """Approved references of the episode (``refs_approved.json``: ref id -> {file, sha256, approved_by}), written by
    ``batch.approve`` from the creator's word."""
    return EP.read_json(EP.work(root) / "refs_approved.json", {}) or {}


def anchors() -> list[dict]:
    return EP.config()["style_pack"]["types"]


def anchor_of(t: str) -> dict:
    for a in anchors():
        if a["type"] == t:
            return a
    raise ContractError(f"no style anchor type {t!r} in config/gemini_task.json")


def shot_type(shot: dict) -> str:
    """The style-pack type of a shot: its own ``shot_type`` or the first matching rule of the table (GC-21)."""
    if shot.get("shot_type"):
        anchor_of(shot["shot_type"])
        return shot["shot_type"]
    size = str((shot.get("camera_spec") or {}).get("shot_size", "")).lower()
    people = len(shot.get("character_ids") or [])
    light = str(shot.get("lighting_and_time") or "").lower()
    for a in anchors():
        m = a.get("match") or {}
        if "sizes" in m and size not in m["sizes"]:
            continue
        if people < m.get("min_people", 0) or people > m.get("max_people", 99):
            continue
        if "shot_roles" in m and shot.get("shot_role") not in m["shot_roles"]:
            continue
        if "light_words" in m and not any(w in light.split() or w in light for w in m["light_words"]):
            continue
        return a["type"]
    raise ContractError(f"{shot['shot_id']}: no style-pack type fits (size {size!r}, {people} people); "
                        "give the shot a shot_type")


def _registry(script: dict) -> dict:
    return TP.registry(script)


def _refs_for_shot(shot: dict, stype: str, reg: dict, start_ref: str | None) -> list[dict]:
    cfg = EP.config()["reference_sizes"]
    size = str((shot.get("camera_spec") or {}).get("shot_size", "")).lower()
    bodies = size in cfg["full_body_sizes"] or stype in cfg["full_body_types"]
    a = anchor_of(stype)
    head = [{"file": a["drive_name"], "role": "style", "ref_id": f"style_{stype}"}]
    if start_ref:
        head.append({"file": picture_target(start_ref), "role": "start frame", "ref_id": start_ref})
    place = []
    if shot.get("location_id"):
        rid = ref_id("place", shot["location_id"])
        place = [{"file": ref_target(rid), "role": shot["location_id"], "ref_id": rid}]
    maxr = int(EP.config()["max_references"])
    for with_bodies in ((True, False) if bodies else (False,)):
        heroes = []
        for cid in shot.get("character_ids") or []:
            if cid not in reg:
                raise ContractError(f"{shot['shot_id']}: {cid} has no world_bible entry (GC-02)")
            rid = ref_id("portrait", cid)
            heroes.append({"file": ref_target(rid), "role": cid, "ref_id": rid})
            if with_bodies:
                fid = ref_id("full_body", cid)
                heroes.append({"file": ref_target(fid), "role": f"{cid} full body", "ref_id": fid})
        refs = head + heroes + place
        if len(refs) <= maxr:
            return refs
    raise ContractError(f"{shot['shot_id']} needs {len(refs)} references, more than {maxr} (GC-02): split the shot")


def _reference_items(script: dict, used_chars: list[str], used_places: list[str], lk: dict, era: str, reg: dict) -> list[dict]:
    main = EP.config()["main_style"]
    style = [{"file": main["drive_name"], "role": "style", "ref_id": "style_main"}]
    out = []
    for cid in used_chars:
        out.append({"id": ref_id("portrait", cid), "kind": "portrait", "subject": cid, "round": "R1",
                    "references": list(style), "people": [cid]})
    for lid in used_places:
        out.append({"id": ref_id("place", lid), "kind": "place", "subject": lid, "round": "R1",
                    "references": list(style), "people": []})
    for cid in used_chars:
        pid = ref_id("portrait", cid)
        out.append({"id": ref_id("full_body", cid), "kind": "full_body", "subject": cid, "round": "R2",
                    "references": style + [{"file": ref_target(pid), "role": f"{cid} portrait", "ref_id": pid}],
                    "people": [cid], "after": pid})
    for it in out:
        text = reg[it["subject"]]["text"]
        subject = PR.subject_of(it["kind"], text)
        it["target"] = ref_target(it["id"])
        it["prompt"] = PR.assemble(lk, era, it["kind"], subject, people=bool(it["people"]))
        it["checks"] = PR.check(it["prompt"], lk, era, it["kind"], [text] if it["people"] else [], subject=subject)
    return out


def build(root: Path, batch_size: int | None = None) -> dict:
    """The queue of an episode (deterministic for the same inputs). Writes nothing; ``write`` saves it."""
    from explainer_engine.gemini_task import gate as GT
    root = Path(root)
    man, script = EP.load(root)
    lk = EP.look(man)
    era = EP.era_line(man, lk)
    reg = _registry(script)
    t0 = GT.state()
    size = int(batch_size or t0["batch_size"])
    if not 1 <= size <= TP.MAX_TURN:
        raise ContractError(f"a batch holds 1..{TP.MAX_TURN} pictures, not {size}")
    tim = TM.durations(root, script)
    approved = references_state(root)
    lines = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}

    shots, pictures, used_chars, used_places = [], [], [], []
    for s in script.get("shots", []):
        route = s.get("route")
        if route not in BUCKET:
            raise ContractError(f"{s['shot_id']}: route {route!r} is not one of {tuple(BUCKET)} (RT-01; run the router)")
        d = tim["shots"][s["shot_id"]]
        row = {"shot_id": s["shot_id"], "segment_id": s.get("segment_id"), "route": route,
               "route_reason": s.get("route_reason", ""), "bucket": BUCKET[route], "duration_s": d["seconds"],
               "duration_planned_s": d["planned_seconds"], "duration_source": d["source"], "frame": d["frame"],
               "lines": [{"line_id": lid, "speaker": (lines.get(lid) or {}).get("speaker_id"),
                          "text": (lines.get(lid) or {}).get("text", "")} for lid in s.get("audio_line_ids") or []],
               "cast": list(s.get("character_ids") or []), "place": s.get("location_id"), "pictures": []}
        if route == "wan":
            row["wan_clip"] = TM.wan_clip(d["seconds"])
        is_map = route == "map_action" or s.get("visual_type") == "map_visualization"
        if not is_map:
            st = shot_type(s)
            row["shot_type"] = st
            for c in row["cast"]:
                if c not in used_chars:
                    used_chars.append(c)
            if row["place"] and row["place"] not in used_places:
                used_places.append(row["place"])
            kp = s.get("keyframe_plan") or {}
            whiches = (["start"] if kp.get("needs_start_frame", True) else []) + (["end"] if kp.get("needs_end_frame") else [])
            for which in whiches:
                pid = f"{s['shot_id']}_{which}"
                start_ref = f"{s['shot_id']}_start" if which == "end" and "start" in whiches else None
                subject = PR.scene_subject(s, reg, which)
                prompt = PR.assemble(lk, era, "scene", subject, people=bool(row["cast"]))
                texts = [reg[c]["text"] for c in row["cast"] if c in reg]
                moment = s["action_end_state"] if which == "end" else s["action_start_state"]
                pictures.append({"id": pid, "shot_id": s["shot_id"], "which": which, "kind": "scene", "shot_type": st,
                                 "place": row["place"], "people": row["cast"], "target": picture_target(pid),
                                 "references": _refs_for_shot(s, st, reg, start_ref), "prompt": prompt,
                                 "checks": PR.check(prompt, lk, era, "scene", texts, moment=moment, subject=subject),
                                 **({"after": start_ref} if start_ref else {})})
                row["pictures"].append(pid)
        shots.append(row)

    refs = _reference_items(script, used_chars, used_places, lk, era, reg)
    # blocked: a reference this picture attaches is neither approved nor made earlier in this plan
    approved_anchor = {f"style_{a['type']}" for a in anchors() if a.get("status") == "approved" and a.get("sha256")}
    for it in refs + pictures:
        need = []
        for r in it["references"]:
            rid = r["ref_id"]
            if rid == "style_main":
                continue
            if rid.startswith("style_"):
                if rid not in approved_anchor:
                    need.append(rid)
            elif rid.startswith("ref_"):
                if rid not in approved:
                    need.append(rid)
        it["needs_approval"] = need

    batches = plan_batches(refs, pictures, size)
    pos = {pid: b["no"] for b in batches for pid in b["ids"]}
    for it in refs + pictures:
        it["batch"] = pos[it["id"]]
    mix = RO.mix_report(script, {k: v["seconds"] for k, v in tim["shots"].items()} if tim["timed"] else None)
    guide = script.get("visual_mix_target") or {}
    mix["frame"] = {}
    for r, key in MIX_KEYS.items():
        if key in guide:
            ok = TM.in_band(mix["shares"][r], float(guide[key]))
            mix["frame"][r] = {"status": "PASS" if ok else "REVIEW", "guide": float(guide[key]),
                               "measured": mix["shares"][r],
                               "detail": "within the 10 % frame" if ok else "outside the 10 % frame: reported, never forced (RT-04)"}
    fails = [(it["id"], c) for it in refs + pictures for c in it["checks"] if c["severity"] == "FAIL"]
    doc = {"schema": SCHEMA, "episode_id": man["episode_id"], "made_at": EP.now(), "repo_commit": EP.commit(),
           "preset": lk["id"], "era_line": era, "batch_size": size, "mode": t0["batch_mode"], "t0_status": t0["status"],
           "timed": tim["timed"], "duration_source": tim["source"], "mix": mix,
           "counts": {"shots": len(shots), "references": len(refs), "pictures": len(pictures), "batches": len(batches),
                      "blocked": sum(bool(it["needs_approval"]) for it in refs + pictures),
                      "days_at_limit": _days(len(refs) + len(pictures), lk)},
           "prompt_fails": [{"id": i, **c} for i, c in fails],
           "review": [{"id": it["id"], **c} for it in refs + pictures for c in it["checks"] if c["severity"] == "REVIEW"]
           + [{"id": s["shot_id"], "rule": "RN-03", "severity": "REVIEW", "detail": s["frame"]["detail"]}
              for s in shots if s["frame"]["status"] == "REVIEW"]
           + [{"id": s["shot_id"], "rule": "Wan native", "severity": "REVIEW", "detail": s["wan_clip"]["detail"]}
              for s in shots if s.get("wan_clip", {}).get("status") == "REVIEW"],
           "references": refs, "shots": shots, "pictures": pictures, "batches": batches}
    return doc


def _days(n: int, lk: dict) -> int:
    per = int(lk.get("pictures_per_day") or TP.PICTURES_PER_DAY)
    return -(-n // per) if n else 0


def plan_batches(refs: list[dict], pictures: list[dict], size: int) -> list[dict]:
    """R1, R2, then scene start frames and end frames, each grouped by (place, style anchor) in order of first
    appearance and cut into batches of at most ``size`` pictures and ``max_attachments_per_message`` files (Q10, GC-23)."""
    out: list[dict] = []
    max_attach = int(EP.config()["max_attachments_per_message"])

    def cut(kind: str, items: list[dict], key) -> None:
        groups: "OrderedDict[tuple, list[dict]]" = OrderedDict()
        for it in items:
            groups.setdefault(key(it), []).append(it)
        for g, its in groups.items():
            chunk, attached = [], []
            for it in its:
                files = [r["file"] for r in it["references"]]
                union = attached + [f for f in files if f not in attached]
                if chunk and (len(chunk) >= size or len(union) > max_attach):
                    out.append({"no": len(out) + 1, "kind": kind, "group": list(g), "ids": [x["id"] for x in chunk],
                                "attached": attached})
                    chunk, attached = [], []
                    union = list(dict.fromkeys(files))
                chunk.append(it)
                attached = union
            if chunk:
                out.append({"no": len(out) + 1, "kind": kind, "group": list(g), "ids": [x["id"] for x in chunk],
                            "attached": attached})
    cut("R1", [r for r in refs if r["round"] == "R1"], lambda it: (it["kind"],))
    cut("R2", [r for r in refs if r["round"] == "R2"], lambda it: (it["kind"],))
    cut("scene", [p for p in pictures if p["which"] == "start"], lambda it: (it["place"] or "-", it["shot_type"]))
    cut("scene", [p for p in pictures if p["which"] == "end"], lambda it: (it["place"] or "-", it["shot_type"]))
    return out


def path(root: Path) -> Path:
    return EP.work(root) / "shot_queue.json"


def write(root: Path, doc: dict) -> Path:
    if doc["prompt_fails"]:
        raise ContractError(f"{len(doc['prompt_fails'])} prompt rule(s) FAIL, no queue written: {doc['prompt_fails'][:3]}")
    p = EP.save_json(path(root), doc)
    TX.clean_gate(p.read_text(encoding="utf-8"), "shot_queue.json")
    return p


def load(root: Path) -> dict:
    doc = EP.read_json(path(root))
    if doc is None:
        raise ContractError(f"{path(root)} does not exist: build the queue first (gemini_task queue)")
    return doc


def items_by_id(doc: dict) -> dict:
    return {it["id"]: it for it in doc["references"] + doc["pictures"]}


def shot_list(doc: dict) -> list[dict]:
    """The video script as P3 checks it: one object per shot, the fields of 04_VIDEO_SCRIPT_RULES.md."""
    pics = items_by_id(doc)
    out = []
    for s in doc["shots"]:
        first = pics[s["pictures"][0]] if s["pictures"] else None
        out.append({"shot_id": s["shot_id"], "lines": [f"{ln['line_id']} | {ln['speaker']} | {ln['text']}" for ln in s["lines"]],
                    "route": s["route"], "route_reason": s["route_reason"], "duration_s": s["duration_s"],
                    "shot_type": s.get("shot_type"), "cast": s["cast"], "place": s["place"],
                    "pictures": [{"id": p, "references": [r["file"] for r in pics[p]["references"]],
                                  "prompt": pics[p]["prompt"], "target": pics[p]["target"]} for p in s["pictures"]],
                    "note": None if first else "map_action: drawn by Python, no picture"})
    return out
