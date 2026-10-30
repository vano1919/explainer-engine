"""Compile a production script (D-43): fill every picture's prompt from its subject (``edit/prompt_v2.compose``, the D-41
slots) at the moment the segment is written, and derive the files the paid steps take:

* ``narration.txt`` (what is said) and ``narration_tts.txt`` (what the voice gets),
* ``pictures_gemini.json`` (pictures painted by Gemini: prompt + style references),
* ``pod_job.json`` (pictures painted by the RunPod reference painter, ``cloud/gen_ref_pictures.py``'s format),
* with ``--film-shots``, ``screenplay_spine.json`` (``compile_spine``: the spine of the approved script and its shot cards, never
  written by hand, ZI-10).

Prompts live in the script itself (``picture.prompt``); ``validate`` FAILs a prompt that no longer matches its subject
(PV-11: someone changed the subject and did not compile, or hand-edited a prompt).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.edit import prompt_v2
from explainer_engine.production import script as S
from explainer_engine.production import staging as STAGING
from explainer_engine.scripting import claims as CLAIMS
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


def compose(doc: dict, pid: str, pic: dict, world: dict | None = None, staged: dict | None = None) -> str | None:
    """The prompt of one picture, or None for a picture that is not painted (engine existing). In a staged scene the
    continuity block (production/staging.py) follows: ``staged`` is ``staging.plan(doc)``, computed once by the caller."""
    engine = pic.get("engine", "existing" if pic.get("file") else (doc.get("look", {}).get("default_engine") or "gemini"))
    if engine == "existing":
        return None
    world = world or world_of(doc)
    kind, beat = shot_type_of(doc, pid)
    if engine == "pod_ref":
        sub, _ = subject_with_cast(doc, pic)
        return (pic.get("edit") or sub).strip() + POD_SUFFIX
    sub, people = subject_with_cast(doc, pic)
    hint = pic.get("costume") or (_visitor_costume(doc) if world["visitors"] else "")
    prompt = prompt_v2.compose(kind, sub, world, beat, people=people, costume_hint=hint if people else "")
    block = STAGING.prompt_block(doc, pid, staged) if _staged_doc(doc) else ""  # D-69: what stays, what this shot changes
    return f"{prompt}. {block}" if block else prompt


def _staged_doc(doc: dict) -> bool:
    """A script that stages any scene (D-69); an unstaged script compiles exactly as before."""
    return (doc.get("look") or {}).get("continuity") == "auto" or any("staging" in s for s in doc.get("segments", []))


def _visitor_costume(doc: dict) -> str:
    """The visitors' clothing words: the episode's ``world.visitor_costume``, else the Day 1 default (audit 2026-10-19)."""
    return (doc.get("world") or {}).get("visitor_costume") or VISITOR_COSTUME


def compile_doc(doc: dict) -> dict:
    """A copy of ``doc`` with every painted picture's ``prompt`` filled (inline and library pictures alike)."""
    world = world_of(doc)
    out = json.loads(json.dumps(doc))
    pics, _ = S.pictures(out)
    staged = STAGING.plan(out) if _staged_doc(out) else None
    for seg in out["segments"]:
        for shot in seg["shots"]:
            pic = shot["picture"]
            if isinstance(pic, dict):
                p = compose(out, pic["id"], pic, world, staged)
                if p is None:
                    pic.pop("prompt", None)
                else:
                    pic["prompt"] = p
    for pid, pic in out.get("library", {}).items():
        if pid in pics and pics[pid].get("uses"):
            p = compose(out, pid, pic, world, staged)
            if p is not None:
                pic["prompt"] = p
    return out


def engine_of(doc: dict, pic: dict) -> str:
    return pic.get("engine", "existing" if pic.get("file") else (doc.get("look", {}).get("default_engine") or "gemini"))


def hero_refs(doc: dict, pic: dict, style: list[str]) -> list[str]:
    """The style references plus the approved reference picture of every hero the picture draws (invariant 6, OR-16):
    a Gemini picture of a hero is painted against that hero's chosen face, never from the prompt alone."""
    from explainer_engine.imagegen.gemini import MAX_REFERENCES
    out = list(style)
    for who in pic.get("heroes", []):
        ref = ((doc.get("cast", {}).get(who) or {}).get("reference") or {}).get("picture")
        if ref and ref not in out and ref in doc.get("library", {}):
            out.append(ref)
    env = ((doc.get("look") or {}).get("environment") or {}).get("picture")
    if not out and env in doc.get("library", {}):  # a picture with no hero still carries the approved world's look
        out.append(env)
    return out[:MAX_REFERENCES]


def jobs(doc: dict) -> tuple[list[dict], dict]:
    """(Gemini pictures, pod job) for every used picture that has no file yet."""
    pics, _ = S.pictures(doc)
    gemini, pod = [], []
    refs = doc.get("look", {}).get("style_refs", [])
    staged = STAGING.plan(doc) if _staged_doc(doc) else None
    for pid, pic in pics.items():
        if not pic.get("uses") or pic.get("file"):
            continue
        eng = engine_of(doc, pic)
        if eng == "gemini":
            gemini.append({"id": pid, "prompt": pic["prompt"],
                           "refs": STAGING.refs_for(doc, pid, hero_refs(doc, pic, refs), staged) if staged else hero_refs(doc, pic, refs), "first_use": pic["first_use"],
                           "tier": pic.get("tier", "standard")})
        elif eng == "pod_ref":
            pod.append({"id": pid, "seed": 600 + len(pod) * 11, "refs": [f"{r}.png" for r in pic.get("refs", [])],
                        "prompt": pic["prompt"].replace(POD_SUFFIX, ""), "first_use": pic["first_use"],
                        "tier": pic.get("tier", "standard")})
    pod_job = {"name": f"{doc['episode']['id']}_pod_refs", "note": "made by explainer_engine.production.compile",
               "width": 1792, "height": 1008, "variants": 2, "suffix": POD_SUFFIX, "negative": POD_NEGATIVE, "pictures": pod}
    return gemini, pod_job


def canva_pending(doc: dict) -> list[str]:
    """Filler pictures (engine canva, PV-43) still to be made by hand in Canva and placed as files."""
    if "segments" not in doc:
        return []
    pics, _ = S.pictures(doc)
    return [k for k, p in pics.items() if p.get("uses") and not p.get("file") and p.get("engine") == "canva"]


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


# --- the screenplay spine (Blueprint P3, ZI-10): derived, never hand-written -----------------------------------------------
CONNECTOR = {"start": "OPEN", "but": "BUT", "therefore": "THEREFORE"}  # the schema allows nothing else: "and then" cannot be declared
FACT_LABELS = ("E", "M")  # the claim map's labels that say the world says so; R, G and I are our reasoning, a guess or our invention


def compile_spine(script_path: Path | str, film_shots_path: Path | str, base: Path | str | None = None) -> dict:
    """``screenplay_spine/1`` of an approved production script and its shot cards. ``base`` is the folder the ``derived_from`` paths
    are relative to (the folder the spine is written to; the script's folder by default). Raises ContractError on any mismatch:
    a script segment with no shots, a shot scene with no segment, a cited claim not in the claim map, missing promises."""
    script_path, film_shots_path = Path(script_path), Path(film_shots_path)
    base = Path(base) if base else script_path.parent
    doc = json.loads(script_path.read_text(encoding="utf-8"))
    shots = json.loads(film_shots_path.read_text(encoding="utf-8"))
    drama = doc.get("drama") or {}
    if not drama.get("packaging_promises"):
        raise ContractError("the spine needs the three packaging promises (drama.packaging_promises): run stage 1b first")
    if not drama.get("profile_id"):
        raise ContractError("the spine needs the structure profile (drama.profile_id): stage 1b records it with the promises")
    seconds: dict[str, float] = {}
    for sh in shots["shots"]:
        seconds[sh["scene"]] = seconds.get(sh["scene"], 0.0) + float(sh["seconds"])
    ids = [seg["id"] for seg in doc["segments"]]
    if sorted(set(seconds) - set(ids)):
        raise ContractError(f"shot cards for scenes the script does not have: {sorted(set(seconds) - set(ids))}")
    if [i for i in ids if i not in seconds]:
        raise ContractError(f"script segments with no shot cards: {[i for i in ids if i not in seconds]}")
    cmap = CLAIMS.load_map(script_path) or CLAIMS.from_editorial(doc)
    cited, segments, t = [], [], 0.0
    for seg in doc["segments"]:
        turn = (seg.get("drama") or {}).get("turn")
        if turn not in CONNECTOR:
            raise ContractError(f"{seg['id']}: drama.turn {turn!r} is not start, but or therefore")
        lines = []
        for k, ln in enumerate(seg["lines"]):
            ids_ = list(ln.get("claims", []))
            cited += [c for c in ids_ if c not in cited]
            lines.append({"index": k, "speaker": ln.get("speaker") or "narrator", "text": ln["text"], "claim_ids": ids_})
        segments.append({"id": seg["id"], "est_duration_sec": seconds[seg["id"]], "causal_connector": CONNECTOR[turn],
                         "clock_window_sec": [t, t + seconds[seg["id"]]], "lines": lines})
        t += seconds[seg["id"]]
    missing = [c for c in cited if c not in (cmap or {})]
    if missing:
        raise ContractError(f"claims cited in the script but not in the claim map: {missing}")
    claims = [{"claim_id": c, "status": "FACT" if cmap[c]["label"][:1] in FACT_LABELS else "ALTERNATE",
               "source_ref": cmap[c]["source"] or f"claim_map.md#{c}"} for c in cited]

    def ref(p: Path) -> dict:
        return {"path": Path(os.path.relpath(p, base)).as_posix(), "sha256": contracts.sha256_file(p)}

    spine = {"schema": "screenplay_spine/1", "derived_from": {"production_script": ref(script_path), "film_shots": ref(film_shots_path)},
             "episode_slug": doc["episode"]["id"], "structure_profile_id": drama["profile_id"],
             "packaging_promises": list(drama["packaging_promises"]), "segments": segments, "claims": claims}
    contracts.validate(spine, base)
    return spine
