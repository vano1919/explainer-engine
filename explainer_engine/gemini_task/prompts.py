"""Picture prompts of the Task route, assembled from PROMPT_CLAUSES.md in its order (Q2: the engine writes the prompt,
Gemini passes it on) and gated before any message holds them (GC-03, GC-04, GC-06, GC-07, GC-11, GC-18, GC-21, GC-22).

Assembly: style_sentence, face_sentence (people), style_reference_clause, keep_scene | keep_full_body, the subject,
era_line, tail. A redo prompt is the original plus ONE correction sentence after the tail (Q11, GC-25).
"""
from __future__ import annotations

import re

from explainer_engine.core.errors import ContractError
from explainer_engine.gemini_task import texts as TX
from explainer_engine.imagegen import turn_pack as TP

KINDS = ("anchor", "portrait", "full_body", "place", "scene")
LOOK_WORDS = re.compile(r"\b(illustration|docudrama|chiaroscuro|realism|cinematic|35 ?mm|anamorphic|render(ed)?|"
                        r"portrait of|concept art|matte painting|style)\b", re.I)
SENTENCE_END = re.compile(r"[.!?](\s|$)")


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def assemble(lk: dict, era: str, kind: str, subject: str, people: bool) -> str:
    if kind not in KINDS:
        raise ContractError(f"unknown picture kind {kind!r}")
    parts = [lk["style_sentence"]]
    if people:
        parts.append(lk["face_sentence"])
    parts.append(lk["style_reference_clause"])
    if kind == "scene":
        parts.append(TX.clause("keep_scene"))
    elif kind == "full_body":
        parts.append(TX.clause("keep_full_body"))
    parts += [subject, era, TX.clause("tail")]
    return _join(parts)


def subject_of(kind: str, text: str) -> str:
    """The subject clause of a reference picture with the hero's or place's verbatim registry text (GC-04)."""
    if kind == "portrait":
        return TX.clause("portrait", hero_text=text)
    if kind == "full_body":
        return TX.clause("full_body", hero_text=text)
    if kind == "place":
        return TX.clause("place", place_text=text)
    raise ContractError(f"{kind} has no registry subject clause")


def scene_subject(shot: dict, reg: dict, which: str) -> str:
    """One moment in scene language from the shot's own fields (GC-06), the heroes' verbatim texts (GC-04)."""
    state = shot["action_end_state"] if which == "end" else shot["action_start_state"]
    cam = shot.get("camera_spec") or {}
    comp = shot.get("screen_composition") or {}
    size = str(cam.get("shot_size", "")).replace("_", " ")
    parts = [f"A {size} shot. {state.rstrip('.')}." if size else f"{state.rstrip('.')}."]
    place = reg.get(shot.get("location_id"))
    if place:
        parts.append(f"The place is {place['name']}, as in its reference image.")
    if comp.get("background"):
        parts.append(f"Behind: {comp['background'].rstrip('.')}.")
    if shot.get("lighting_and_time"):
        parts.append(f"Light: {shot['lighting_and_time'].rstrip('.')}.")
    for cid in shot.get("character_ids", []):
        if cid in reg:
            parts.append(f"{reg[cid]['name']}: {reg[cid]['text'].rstrip('.')}.")
    return _join(parts)


def check(prompt: str, lk: dict, era: str, kind: str, people_texts: list[str] = (), moment: str = "",
          subject: str = "", correction: str | None = None) -> list[dict]:
    """GC rows for one assembled prompt (empty = clean). FAIL rows stop the message; REVIEW rows are listed."""
    out = []

    def row(rule, sev, detail):
        out.append({"rule": rule, "severity": sev, "detail": detail})
    if not prompt.startswith(lk["style_sentence"]):
        row("GC-03", "FAIL", "the prompt does not open with the style sentence")
    if lk["style_reference_clause"] not in prompt:
        row("GC-21", "FAIL", "the prompt lacks the style-reference clause (image 1 is a style picture)")
    if people_texts and lk["face_sentence"] not in prompt:
        row("GC-11", "FAIL", "a prompt with people lacks the face sentence")
    for t in people_texts:
        if t.rstrip(".") not in prompt:
            row("GC-04", "FAIL", f"a hero's registry text is not in the prompt word for word: {t[:40]!r}...")
    keep = TX.clause("keep_scene")
    if (kind == "scene") != (keep in prompt):
        row("GC-21", "FAIL", "keep_scene belongs to scene pictures only")
    if (kind == "full_body") != (TX.clause("keep_full_body") in prompt):
        row("GC-23", "FAIL", "keep_full_body belongs to full-body references only")
    if era not in prompt:
        row("GC-22", "FAIL", "the episode's era line is not in the prompt word for word")
    if TX.clause("tail") not in prompt:
        row("GC-07", "FAIL", "the prompt lacks the tail (16:9, no text)")
    variable = _join([subject, era, correction or ""])     # our fixed clauses say "no text" on purpose
    asks = [m.group(0) for m in TP.TEXT_WORDS.finditer(TP.NEGATED.sub("", variable))]
    if asks:
        row("GC-07", "FAIL", f"the subject asks for lettering: {asks[:3]}")
    if TP.ROUND_FACE_WORDS.search(TP._affirmative(prompt)):
        row("GC-11", "FAIL", f"round, modern-cartoon face words: {TP.ROUND_FACE_WORDS.search(TP._affirmative(prompt)).group(0)!r}")
    hits = TP.never_hits(lk, prompt)
    if hits:
        row("GC-18", "FAIL", f"words the tool redraws as a camera picture: {hits}")
    if re.search(r"\blantern\b", TP._affirmative(prompt), re.I):
        row("GC-22", "FAIL", "the prompt asks for a lantern (preset era_rule)")
    if moment and (moment.count(",") > TP.MAX_COMMAS or TP.SECOND_ACTION.search(moment)):
        row("GC-06", "REVIEW", "the moment reads as a list or as two actions")
    for t in people_texts:
        lw = LOOK_WORDS.search(t)
        if lw:
            row("GC-04", "REVIEW", f"a registry text carries look words of its own ({lw.group(0)!r}); the look comes "
                                   "from the style sentence only")
    if correction is not None:
        c = correction.strip()
        if not c or len(SENTENCE_END.findall(c)) != 1 or not SENTENCE_END.search(c[-1] + " "):
            row("GC-25", "FAIL", "a redo needs exactly ONE correction sentence")
        if re.search(r"\b(no|not|never|without|remove|instead|wrong|don't|do not)\b", c, re.I):
            row("GC-25", "FAIL", "the correction sentence must say what the picture shows, in positive words")
    return out


def fails(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["severity"] == "FAIL"]


def block(k: int, n: int, pid: str, target: str, refs: list[tuple[str, str]], prompt: str,
          replaces: str | None = None) -> str:
    """One picture block exactly as PROMPT_CLAUSES.md shows it."""
    lines = [f"PICTURE {k} of {n} | id {pid} | save as {target}"]
    if replaces:
        lines.append(f"REPLACES: {replaces}")
    lines.append("REFERENCES, in this order: " + ", ".join(f"{i} = {f} ({role})" for i, (f, role) in enumerate(refs, 1)))
    lines.append(f"PROMPT: {prompt}")
    return "\n".join(lines)
