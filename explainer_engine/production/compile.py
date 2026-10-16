"""Compile a production script (D-43): fill every picture's prompt from its subject (``edit/prompt_v2.compose``, the D-41
slots) at the moment the segment is written, and derive the files the paid steps take:

* ``narration.txt`` (what is said) and ``narration_tts.txt`` (what the voice gets),
* ``pictures_gemini.json`` (pictures painted by Gemini: prompt + style references),
* ``pod_job.json`` (pictures painted by the RunPod reference painter, ``cloud/gen_ref_pictures.py``'s format).

Prompts live in the script itself (``picture.prompt``); ``validate`` FAILs a prompt that no longer matches its subject
(PV-11: someone changed the subject and did not compile, or hand-edited a prompt).
"""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.edit import prompt_v2
from explainer_engine.production import script as S
from explainer_engine.world import resolver

POD_SUFFIX = (" Keep exactly the same painted graphic-novel style as the reference: thick dark ink outlines, textured painted "
              "colour, the same faces, clothes, light and palette. Adult proportions. No text, no letters, no speech bubbles.")
POD_NEGATIVE = "photo, 3d render, cartoon for children, big heads, text, letters, watermark"
VISITOR_COSTUME = "muddy frock coats, waistcoats, long skirts and spectacles of the 1700s to 1900s"  # the v5 hint (Day 1)
PEOPLE_WORDS = ("hand", "hands", "fist", "fingers", "palms", "people", "crowd", "strangers", "man", "men", "woman",
                "sleeve", "coat", "figure", "figures")


def world_of(doc: dict) -> dict:
    return resolver.resolve(doc["world"])


def shot_type_of(doc: dict, pid: str) -> tuple[str, int]:
    """(shot type, light beat) of the first shot that uses picture ``pid``."""
    for sh in S.shots(doc):
        if sh["picture_id"] == pid:
            return sh["shot"]["type"], sh["light_beat"]
    raise KeyError(pid)


def subject_with_cast(doc: dict, pic: dict) -> tuple[str, bool]:
    sub = pic["subject"].strip(" ,.")
    heroes = pic.get("heroes", [])
    if heroes:
        cards = "; ".join(doc["cast"][h]["card"] for h in heroes)
        sub = f"{sub}. {'Two named heroes' if len(heroes) == 2 else 'Named heroes' if len(heroes) > 2 else 'One named hero'}: {cards}"
    people = pic.get("people", bool(heroes) or bool(resolver.words_in(sub, list(PEOPLE_WORDS))))
    return sub, people


def compose(doc: dict, pid: str, pic: dict, world: dict | None = None) -> str | None:
    """The prompt of one picture, or None for a picture that is not painted (engine existing)."""
    engine = pic.get("engine", "existing" if pic.get("file") else (doc.get("look", {}).get("default_engine") or "gemini"))
    if engine == "existing":
        return None
    world = world or world_of(doc)
    kind, beat = shot_type_of(doc, pid)
    if engine == "pod_ref":
        sub, _ = subject_with_cast(doc, pic)
        return (pic.get("edit") or sub).strip() + POD_SUFFIX
    sub, people = subject_with_cast(doc, pic)
    hint = pic.get("costume") or (VISITOR_COSTUME if world["visitors"] else "")
    return prompt_v2.compose(kind, sub, world, beat, people=people, costume_hint=hint if people else "")


def compile_doc(doc: dict) -> dict:
    """A copy of ``doc`` with every painted picture's ``prompt`` filled (inline and library pictures alike)."""
    world = world_of(doc)
    out = json.loads(json.dumps(doc))
    pics, _ = S.pictures(out)
    for seg in out["segments"]:
        for shot in seg["shots"]:
            pic = shot["picture"]
            if isinstance(pic, dict):
                p = compose(out, pic["id"], pic, world)
                if p is None:
                    pic.pop("prompt", None)
                else:
                    pic["prompt"] = p
    for pid, pic in out.get("library", {}).items():
        if pid in pics and pics[pid].get("uses"):
            p = compose(out, pid, pic, world)
            if p is not None:
                pic["prompt"] = p
    return out


def engine_of(doc: dict, pic: dict) -> str:
    return pic.get("engine", "existing" if pic.get("file") else (doc.get("look", {}).get("default_engine") or "gemini"))


def jobs(doc: dict) -> tuple[list[dict], dict]:
    """(Gemini pictures, pod job) for every used picture that has no file yet."""
    pics, _ = S.pictures(doc)
    gemini, pod = [], []
    refs = doc.get("look", {}).get("style_refs", [])
    for pid, pic in pics.items():
        if not pic.get("uses") or pic.get("file"):
            continue
        eng = engine_of(doc, pic)
        if eng == "gemini":
            gemini.append({"id": pid, "prompt": pic["prompt"], "refs": refs, "first_use": pic["first_use"]})
        elif eng == "pod_ref":
            pod.append({"id": pid, "seed": 600 + len(pod) * 11, "refs": [f"{r}.png" for r in pic.get("refs", [])],
                        "prompt": pic["prompt"].replace(POD_SUFFIX, ""), "first_use": pic["first_use"]})
    pod_job = {"name": f"{doc['episode']['id']}_pod_refs", "note": "made by explainer_engine.production.compile",
               "width": 1792, "height": 1008, "variants": 2, "suffix": POD_SUFFIX, "negative": POD_NEGATIVE, "pictures": pod}
    return gemini, pod_job


def write_outputs(doc: dict, out_dir: Path) -> list[Path]:
    from explainer_engine.core.store import write_json_atomic, write_text_atomic
    out_dir.mkdir(parents=True, exist_ok=True)
    gemini, pod_job = jobs(doc)
    paths = [write_text_atomic(out_dir / "narration.txt", S.narration_text(doc)),
             write_text_atomic(out_dir / "narration_tts.txt", S.tts_text(doc)),
             write_json_atomic(out_dir / "tts_chunks.json", S.tts_chunks(doc)),
             write_json_atomic(out_dir / "pictures_gemini.json", gemini),
             write_json_atomic(out_dir / "pod_job.json", pod_job)]
    return paths
