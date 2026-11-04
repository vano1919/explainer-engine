# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v1_story.py`
# Target Module : explainer_engine/training/pods/xworld_v1_story.py
# Target Classes/Symbols : def show_traits(), def face_parts(), def face_problems(), def jobs(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Draw a short story with xworld_v1 from frame 0 (D-80; ვანო 2026-10-26 10:32 Tbilisi); run by xworld_v1_story.sh (OR-21).

A story file (stories/<name>.json) lists shots: a shot with "master": null is drawn from its description alone (frame 0 of a
place); every other shot uses the prompt form that won the held-out test (LT-75: D = master + full description + change
line + "Keep everything else the same.") with its master's DRAWN picture as the only reference. A run picks the LoRA (or
null = the base model), its "weight" (default WEIGHT, LT-79) and the shots; "text_master" lists masters that the run also
draws from text alone, as a second branch (`<run>_t_<shot>`) for every shot built on them. Same sampler as the test
(1280x720, 30 steps, true_cfg 4, seed 11).

LT-79 (ვანო 2026-10-26 11:49 Tbilisi, after the faces test): the LoRA alone gives every person the training show's default
face, so every person of a story has a written face in "cast" (role -> {"face": ...} naming at least FACE_PARTS_MIN of face
shape, eyes, nose, brows, jaw or chin, mouth), every shot lists in "faces" the people whose face is seen, and its
description carries that face text word for word; the face must differ from the training show's people (no SHOW_FACE
trait, no name of theirs); runs default to WEIGHT. `face_problems` checks it and `jobs` refuses a
story with problems. Stories drawn before the rule carry "before_lt79": true.

    python xworld_v1_story.py <story.json> <out dir> <lora A>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v1_test import TRIGGER, prompt
else:
    from xworld_v1_test import TRIGGER, prompt


WEIGHT = 0.7
FACE_PARTS = {"shape": ("face is", "face,", "round face", "square", "long face", "narrow face", "oval", "fleshy", "gaunt",
                        "chubby", "bony"),
              "eyes": ("eye",), "nose": ("nose",), "brows": ("brow",), "jaw": ("jaw", "chin"), "mouth": ("mouth", "lips")}
FACE_PARTS_MIN = 4
# The training show's own faces (the LoRA's default people, measured on the 2026-10-26 sheets and the captions): a written
# face must differ from them, so it may not use these traits or name the show's people (ვანო 2026-10-26 11:49 Tbilisi)
SHOW_FACE = ("round head", "round eyes", "big round", "dot pupil", "tiny pupil", "pinpoint pupil", "unibrow", "drool",
             "spiky", "light-blue hair", "blue hair", "grey-blue hair", "wavy mouth", "wobbly mouth", "lab coat",
             "yellow shirt", "rick", "morty", "summer", "beth", "jerry", "birdperson", "squanchy")


def show_traits(text):
    """The SHOW_FACE traits and names in a text, as whole words ("Elizabethan" is not "beth", "brick" is not "rick")."""
    import re
    t = text.lower()
    return [w for w in SHOW_FACE if re.search(rf"\b{re.escape(w)}\b", t)]


def face_parts(text):
    t = text.lower()
    return sorted(k for k, words in FACE_PARTS.items() if any(w in t for w in words))


def face_problems(story):
    """LT-79: every cast face names enough parts, and every shot that shows a face carries its text word for word."""
    if story.get("before_lt79"):
        return []
    cast, out = story.get("cast") or {}, []
    if not cast:
        out.append("no cast: every person needs a written face (LT-79)")
    for role, c in cast.items():
        if len(face_parts(c.get("face", ""))) < FACE_PARTS_MIN:
            out.append(f"{role}: face names {face_parts(c.get('face', ''))}, needs {FACE_PARTS_MIN} of {sorted(FACE_PARTS)}")
        show = show_traits(c.get("face", "") + " " + c.get("look", ""))
        if show:
            out.append(f"{role}: face too close to the training show's people ({', '.join(show)})")
    for s in story["shots"]:
        for role in s.get("faces", []):
            if role not in cast:
                out.append(f"{s['id']}: {role} is not in the cast")
            elif cast[role].get("face", "") not in s["desc"]:
                out.append(f"{s['id']}: the description lacks {role}'s face text")
    return out


def jobs(story):
    """[{name, run, shot, lora, weight, prompt, ref}] in run order; ref = the name of the drawn master, or None."""
    problems = face_problems(story)
    if problems:
        raise ValueError("; ".join(problems))
    shots = {s["id"]: s for s in story["shots"]}
    out = []
    for run in story["runs"]:
        ids = [s["id"] for s in story["shots"]] if run["shots"] == "all" else run["shots"]
        missing = [m for i in ids if (m := shots[i]["master"]) and m not in ids]
        if missing:
            raise ValueError(f"run {run['name']}: masters not drawn in the run: {missing}")
        branches = [("", None)] + [("t_", m) for m in run.get("text_master", [])]
        for tag, alt in branches:
            for i in ids:
                s = shots[i]
                if alt and i != alt and s["master"] != alt:
                    continue
                name = f"{run['name']}_{tag}{i}"
                if s["master"] is None or i == alt:
                    text, ref = f"{TRIGGER}, {s['desc']}", None
                else:
                    text = prompt("D", s["desc"], s["change"])
                    ref = f"{run['name']}_{tag if s['master'] == alt else ''}{s['master']}"
                out.append({"name": name, "run": run["name"], "shot": i, "lora": run["lora"],
                            "weight": run.get("weight", WEIGHT), "prompt": text, "ref": ref})
    return out


def main(argv):
    from PIL import Image
    if __package__:
        from .xworld_v1_test import Loras, draw, load_pipeline, logger
    else:
        from xworld_v1_test import Loras, draw, load_pipeline, logger
    story_path, outd, lora_a = argv[:3]
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs(json.loads(Path(story_path).read_text(encoding="utf-8")))
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = logger(outd, "story.log")
    pipe, tr = load_pipeline()
    loras = Loras(pipe, tr, {"A": lora_a}, say)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{j['ref']}.png").convert("RGB")] if j["ref"] else []
        t = time.time()
        draw(loras.use(j["lora"], j.get("weight", WEIGHT)), j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
