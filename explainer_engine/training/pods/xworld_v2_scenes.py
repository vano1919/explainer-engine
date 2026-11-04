# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_scenes.py`
# Target Module : explainer_engine/training/pods/xworld_v2_scenes.py
# Target Classes/Symbols : def frame_desc(), def frame_extras(), def prompt(), def jobs(), def load(), def main()
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

"""The xworld_v2 round test (D-80; ვანო 2026-10-26 13:26 Tbilisi): after every training round, three scenes of five shots in
three worlds (stories/v2: tent = inside, tundra = outside, rome = a city street) are drawn with the round's checkpoint (or
the base model in round 0), in three prompt forms, so we see whether learning the style damages the scene logic and which
description gives each shot best:
  P1  the form that won the 10-26 held-out test (LT-75 "D"): previous drawn shot + full description + change + keep line
  P2  P1 + where the camera stands, what is left / right / behind, the light, the shot size (the shot's "layout")
  P3  every shot from text alone: full description + layout, no picture (answers "D copies a drawn master")
  P2F shot 0 as the picture of every shot (a fixed previous frame: no chained errors; review 2026-10-26), asked in the form the
      cut pairs are trained with (xworld_v2_build.cut_caption): master sentence + description + the cut + keep line, no
      layout sentence (ვანო 2026-10-26 12:42; round 0's P2F carried the layout sentence)
  P2R P2F under `rm style` (the cut skill is trained under that trigger: does it show only there?)
Every scene is drawn with each seed of SEEDS (review 2026-10-26: one seed cannot tell a form from luck).
Shot 0 of a scene is drawn once from text (description + layout) and is the master of P1 and P2. People are described the
way people picture their era (ვანო 13:26) plus an LT-79 face; every scene passes `face_problems`.

    python xworld_v2_scenes.py <scene dir> <out dir> <lora .safetensors | base> [weight] [round|one]   (round = ROUND_TESTS only, one = ONE_SCENE_TESTS)
writes <out>/<scene>_<form>_<shot>.png, jobs.json and scenes.log; drawn pictures are skipped on a rerun.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v1_story import face_problems
    from .xworld_v1_test import KEEP, MASTER, TRIGGER
    from .xworld_v2_data import RM_TRIGGER
else:
    from xworld_v1_story import face_problems
    from xworld_v1_test import KEEP, MASTER, TRIGGER
    from xworld_v2_data import RM_TRIGGER

FORMS = ("P1", "P2", "P3", "P2F")
# what a training round draws (reduced test, ვანო 2026-10-26): (form, scenes or None = all, seeds)
ROUND_TESTS = (("P3", None, (11,)), ("P2F", None, (11, 23)), ("P2R", ("tent",), (11,)))
# the short test (ვანო 2026-10-26 16:39: the aim is the best way, not round-to-round comparison): one scene (tundra, the decisive one; the Opus thread 16:39)
ONE_SCENE_TESTS = (("P3", ("tundra",), (11,)), ("P2F", ("tundra",), (11, 23)))
MODES = {"round": ROUND_TESTS, "one": ONE_SCENE_TESTS}
FIXED_REF = ("P2F", "P2R")  # forms whose every shot edits shot 0
SEEDS = (11, 23)
WEIGHT = 1.0  # ვანო 2026-10-26 12:13 Tbilisi: weight 1.0 once the system differs from the show (the v2 world)


# E7-E9 (ვანო 2026-10-26 17:14; the Opus thread): a close-up or medium shot must not name parts that are out of frame (the cast text
# names sandals and boots, and the model then draws feet where the hands are), the place behind the subject is stated, and an
# over-the-shoulder shot says exactly who is in it. Used by the P2S, S2 and S3 prompts; the standard rows stay as they were.
FOOT = re.compile(r",? (?:and )?(?:leather sandals|tall black riding boots|feet wrapped in hide)")
LEGS = re.compile(r",? (?:and )?(?:white )?breeches")
SHOULDER = re.compile(r"over (?:the )?(\w+)'s shoulder")


def frame_desc(shot):
    """The shot's description without the parts the camera cannot see (close: no footwear or legs; medium: no footwear)."""
    d = shot["desc"]
    if shot.get("size") in ("medium", "close"):
        d = FOOT.sub("", d)
    if shot.get("size") == "close":
        d = LEGS.sub("", d)
    return d


def frame_extras(sc, shot):
    """The 'behind' line (the card's layout sentence) and, in an over-the-shoulder shot, the exactly-two-people line."""
    out = [f"Behind and around the subject: {shot['layout']}"] if shot.get("layout") else []
    m = SHOULDER.search(shot.get("change") or "")
    if m:
        back = next((r for r in sc["cast"] if r.lower() == m.group(1).lower()), None)
        front = next((r for r in shot.get("faces", []) if r != back), None)
        if back and front:
            out.append(f"Exactly two people are in the frame: {back}, seen from behind with his back to the camera ("
                       f"{FOOT.sub('', sc['cast'][back]['look'])}), and {front} facing the camera.")
    return " ".join(out)


def prompt(form, shot):
    """The prompt of one shot in one form (shot 0 is always drawn from text)."""
    d, lay, ch = shot["desc"], shot["layout"], shot.get("change")
    if not ch or form == "P3":
        return f"{TRIGGER}, {d} {lay}"
    if form == "P1":
        return f"{TRIGGER}, {MASTER} {d} {ch} {KEEP}"
    if form == "P2":
        return f"{TRIGGER}, {MASTER} {d} {lay} {ch} {KEEP}"
    if form in FIXED_REF:  # the cut sentence as trained: "Cut to the next shot: <change>" (xworld_v2_build.cut_caption)
        cut = ch[len("Cut to "):] if ch.startswith("Cut to ") else ch
        return f"{RM_TRIGGER if form == 'P2R' else TRIGGER}, {MASTER} {d} Cut to the next shot: {cut} {KEEP}"
    raise ValueError(form)


def jobs(scenes, seeds=SEEDS, tests=None):
    """[{name, scene, seed, form, shot, prompt, ref}] in drawing order; ref = the name of a drawn picture, or None.
    ``tests`` = ROUND_TESTS-like (form, scenes or None, seeds); without it every form is drawn with every seed."""
    out = []
    for sc in scenes:
        bad = face_problems(sc)
        if bad:
            raise ValueError(f"{sc['name']}: " + "; ".join(bad))
        first = sc["shots"][0]
        want = [(f, sd) for f in FORMS for sd in seeds] if tests is None else \
            [(f, sd) for f, only, sds in tests if only is None or sc["name"] in only for sd in sds]
        for seed in dict.fromkeys(sd for _, sd in want):
            s0 = f"{sc['name']}_{seed}_s0"
            out.append({"name": s0, "scene": sc["name"], "seed": seed, "form": "all", "shot": first["id"],
                        "prompt": prompt("P1", first), "ref": None})
            for form in [f for f, sd in want if sd == seed]:
                prev = s0
                for s in sc["shots"][1:]:
                    name = f"{sc['name']}_{seed}_{form}_{s['id']}"
                    ref = None if form == "P3" else s0 if form in FIXED_REF else prev
                    out.append({"name": name, "scene": sc["name"], "seed": seed, "form": form, "shot": s["id"],
                                "prompt": prompt(form, s), "ref": ref})
                    prev = name
    return out


def load(scene_dir):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(scene_dir).glob("*.json"))]


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, outd, lora = argv[:3]
    weight = float(argv[3]) if len(argv) > 3 else WEIGHT
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs(load(scene_dir), tests=MODES.get(argv[4]) if len(argv) > 4 else None)
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = t.logger(outd, "scenes.log")
    pipe, tr = t.load_pipeline()
    loras = t.Loras(pipe, tr, {} if lora == "base" else {"R": lora}, say)
    p = loras.use(None if lora == "base" else "R", weight)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{j['ref']}.png").convert("RGB")] if j["ref"] else []
        t0 = time.time()
        t.SEED = j["seed"]  # draw() reads the module's seed
        t.draw(p, j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t0), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
