"""Free checks of the one-place route (D-120, docs/SCENE_REUSE_RULES.md: LV-01, LV-07, RF-01, RF-04, HI-01, HI-04, HI-08).
Pure functions over a Qwen jobs file (qwen_jobs.py) and a place register; every result is a list of ``(rule, severity, text)``."""
from __future__ import annotations

STYLE_HEAD = "xworld style"
WORD_CEILING_REVIEW = 280      # HI-08 proposal, the creator decides
RENDER_MARKS = ("blender", "render", "flat3", "clay")


def check_refs(doc: dict) -> list[tuple]:
    """RF-01 (no rendered picture is an input), RF-04 (at most 3 images per picture)."""
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
    return out


def check_prompts(doc: dict) -> list[tuple]:
    """HI-04 shape (style head, 'Scene:' part, then appearance blocks), HI-01 (registry text verbatim, never a part of one),
    HI-08 (word ceiling, REVIEW). A prompt of an edit job (it has refs) is a change note and is only counted."""
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
            used = [k for k, t in reg.items() if t in p]
            for k in used:
                if p.find(reg[k]) < i:
                    out.append(("HI-04", "FAIL", f"{n}: the {k} block comes before the scene part"))
            if len(p.split()) > WORD_CEILING_REVIEW:
                out.append(("HI-08", "REVIEW", f"{n}: {len(p.split())} words (proposal {WORD_CEILING_REVIEW})"))
    return out


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
