"""Free checks of the one-place route (D-120, docs/SCENE_REUSE_RULES.md: LV-01, LV-07, RF-01, RF-04, RF-05, HI-01, HI-02, HI-04,
HI-05, HI-07, HI-08; the cut-level rules are in production/cut_plan.py).
Pure functions over a Qwen jobs file (qwen_jobs.py) and a place register; every result is a list of ``(rule, severity, text)``."""
from __future__ import annotations

import re

STYLE_HEAD = "xworld style"
WORD_CEILING = 280             # HI-08: the creator, 2026-11-07 22:23 UTC (answer 4a): FAIL above 280 words
RENDER_MARKS = ("blender", "render", "flat3", "clay")


def check_refs(doc: dict) -> list[tuple]:
    """RF-01 (no rendered picture is an input), RF-04 (at most 3 images per picture), RF-05 (a generated picture is a reference only
    for a variant of itself: ``out:X`` needs ``variant_of: X``, one step deep)."""
    out = []
    inputs = doc.get("inputs", {})
    for g in doc["groups"]:
        for j in g["jobs"]:
            refs = j.get("refs", [])
            if len(refs) > 3:
                out.append(("RF-04", "FAIL", f"{j['name']}: {len(refs)} reference images (max 3)"))
            for r in refs:
                kind, _, name = r.partition(":")
                if kind == "in":
                    src = str(inputs.get(name, name)).lower()
                    if any(m in src or m in name.lower() for m in RENDER_MARKS):
                        out.append(("RF-01", "FAIL", f"{j['name']}: {name} looks like a rendered picture"))
                elif kind == "out" and j.get("variant_of") != name:
                    out.append(("RF-05", "FAIL", f"{j['name']}: out:{name} is a generated picture; only a variant of it "
                                                 f"(variant_of: {name}) may use it"))
    return out


def check_prompts(doc: dict) -> list[tuple]:
    """HI-04 shape (style head, 'Scene:' part, then appearance blocks), HI-01 (every entity of the job's ``in_shot`` list has its
    registry block verbatim in the prompt; a job without ``in_shot`` cannot be checked and fails), HI-08 (word ceiling, FAIL).
    A prompt of an edit job (it has refs) is a change note and is only counted."""
    out, reg = [], doc.get("registry", {})
    for g in doc["groups"]:
        for j in g["jobs"]:
            p, n = j["prompt"], j["name"]
            if j.get("refs"):
                continue
            head = p[p.find(STYLE_HEAD):] if p.startswith("Style:") and STYLE_HEAD in p else p  # HI-04: a leading scene-style sentence
            if not head.startswith(STYLE_HEAD):
                out.append(("HI-04", "FAIL", f"{n}: the prompt must start with the style line"))
            i = p.find("Scene:")
            if i < 0:
                out.append(("HI-04", "FAIL", f"{n}: no 'Scene:' part"))
            in_shot = j.get("in_shot")
            if in_shot is None:
                out.append(("HI-01", "FAIL", f"{n}: no in_shot list: the registry blocks cannot be checked"))
            else:
                for k in in_shot:
                    if k not in reg:
                        out.append(("HI-01", "FAIL", f"{n}: {k} has no registry block"))
                    elif reg[k] not in p:
                        out.append(("HI-01", "FAIL", f"{n}: the {k} block is not copied word for word"))
                for k, t in reg.items():
                    if k not in in_shot and t in p:
                        out.append(("HI-04", "FAIL", f"{n}: {k} is described but not in the shot"))
            used = [k for k, t in reg.items() if t in p]
            for k in used:
                if p.find(reg[k]) < i:
                    out.append(("HI-04", "FAIL", f"{n}: the {k} block comes before the scene part"))
            if len(p.split()) > WORD_CEILING:
                out.append(("HI-08", "FAIL", f"{n}: {len(p.split())} words (ceiling {WORD_CEILING})"))
    return out


HEIGHT = re.compile(r"\b\d(?:\.\d+)?\s?m\b")
FACE = re.compile(r"\b(nose|brows?|eyebrows?|beard\w*|clean-shaven|jaw|chin|face)\b", re.I)


def check_registry(doc: dict) -> list[tuple]:
    """HI-02 (a height in metres in every registry block), HI-05 (faces are written: a face word in every block of a person).
    Blocks of animals and props say ``"kind": "thing"`` in ``registry_kinds`` and skip the face words."""
    out, kinds = [], doc.get("registry_kinds", {})
    for k, t in doc.get("registry", {}).items():
        if not HEIGHT.search(t):
            out.append(("HI-02", "REVIEW", f"{k}: no height in metres"))
        if kinds.get(k, "person") == "person" and not FACE.search(t):
            out.append(("HI-05", "REVIEW", f"{k}: no face words (face shape, nose, brows, beard or clean-shaven)"))
    return out


def check_lora_weight(doc: dict) -> list[tuple]:
    """HI-07: one LoRA weight per episode (recorded 1.0, the creator 2026-11-07 19:25 UTC)."""
    ws = {g.get("lora_weight") for g in doc["groups"]}
    return [] if len(ws) <= 1 else [("HI-07", "REVIEW", f"{len(ws)} LoRA weights in one jobs file: {sorted(map(str, ws))}")]


def check_all(doc: dict) -> list[tuple]:
    return check_refs(doc) + check_prompts(doc) + check_registry(doc) + check_lora_weight(doc)


def check_place_register(shots: list[dict]) -> list[tuple]:
    """LV-01 / LV-07. Each shot: {id, place, drawing, kind: sharp|blurred|insert}. A second drawing of a place is allowed only when
    the earlier drawing's last sharp shot and the new drawing's first sharp shot have a shot of another place, an insert or a
    blurred shot between them."""
    out, last = [], {}          # place -> (drawing, index of its last sharp shot)
    for i, s in enumerate(shots):
        if s["kind"] != "sharp":
            continue
        prev = last.get(s["place"])
        if prev and prev[0] != s["drawing"]:
            between = shots[prev[1] + 1:i]
            if not any(b["place"] != s["place"] or b["kind"] != "sharp" for b in between):
                out.append(("LV-01", "FAIL", f"{s['id']}: a second drawing of {s['place']} ({s['drawing']}) follows "
                                             f"{shots[prev[1]]['id']} with nothing between"))
        last[s["place"]] = (s["drawing"], i)
    return out
