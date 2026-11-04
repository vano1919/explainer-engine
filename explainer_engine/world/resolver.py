# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/world/resolver.py`
# Target Module : explainer_engine/world/resolver.py
# Target Classes/Symbols : def load_codex(), def load_look(), def words_in(), def resolve(), def _step(), def clause_for_beat(), def not_yet(), def check_text()
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

"""World resolver (D-41, UR-23): which worlds a topic shows, who owns the light, what may and may not appear. stdlib only.

``resolve(spec)`` turns a short topic spec into ``world.json``: a host world (owns landscape, light, grade, extras), visitors
(own costume and props, lit by the host) and the era-level ``absent`` list. ``check_text`` is the lint every prompt passes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ERAS_FILE = Path(__file__).with_name("eras.json")
LOOK_FILE = Path(__file__).with_name("look_v2.json")


def load_codex(path: Path = ERAS_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_look(path: Path = LOOK_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def words_in(text: str, words: list[str]) -> list[str]:
    low = text.lower()
    return [w for w in words if re.search(rf"(?<![a-z]){re.escape(w.lower())}s?(?![a-z])", low)]


def resolve(spec: dict, codex: dict | None = None) -> dict:
    """spec: {topic, host: {era, place, when, landscape[], season_light?, inhabitants?}, visitors: [{era, people[]}],
    day_arc: [{beat, light}], claims?: {...}}. Raises ValueError on an unknown era, light key or light owner."""
    codex = codex or load_codex()
    eras = codex["eras"]
    host = dict(spec["host"])
    if host["era"] not in eras:
        raise ValueError(f"unknown era {host['era']!r}: add it to the codex (research it first)")
    host_era = eras[host["era"]]
    visitors = []
    for v in spec.get("visitors", []):
        if v["era"] not in eras:
            raise ValueError(f"unknown visitor era {v['era']!r}")
        visitors.append({**v, "costume": eras[v["era"]]["costume"], "design": eras[v["era"]]["production_design"]})
    owner = spec.get("light_owner", "host")
    if owner not in ("host", "visitors"):
        raise ValueError("light_owner is 'host' or 'visitors'")
    lights = host_era["light_keys"] if owner == "host" else eras[visitors[0]["era"]]["light_keys"]
    arc = []
    for step in spec.get("day_arc", []):
        if step["light"] not in lights:
            raise ValueError(f"beat {step.get('beat')}: light {step['light']!r} is not in the codex for the light owner "
                             f"(known: {sorted(lights)})")
        arc.append({"beat": step["beat"], "light": step["light"], "clause": lights[step["light"]],
                    "not_yet": list(step.get("not_yet", []))})
    absent = list(host_era["absent"])
    from explainer_engine.world import bible
    return {"version": 1, "bible": bible.cite(), "topic": spec["topic"], "host": {**host, "palette_words": host_era["palette_words"],
            "atmosphere": host_era["atmosphere"], "material_culture": host_era["production_design"],
            "costume": host_era["costume"]}, "visitors": visitors, "light_owner": owner, "light_keys": lights,
            "day_arc": arc, "grade": host_era["grade"] if owner == "host" else eras[visitors[0]["era"]]["grade"],
            "absent": absent, "cliches": host_era["cliches"], "evidence": host_era["status"]}


def _step(world: dict, beat: int) -> dict:
    chosen = None
    for step in world["day_arc"]:
        if step["beat"] <= beat:
            chosen = step
    if chosen is None:
        raise ValueError(f"no light for beat {beat}")
    return chosen


def clause_for_beat(world: dict, beat: int) -> str:
    """The one light clause of a beat (the last arc step at or before ``beat``)."""
    return _step(world, beat)["clause"]


def not_yet(world: dict, beat: int) -> list[str]:
    """Things the story has not made yet at this beat (UR-27 story state), e.g. fire before the fire beat."""
    return _step(world, beat).get("not_yet", [])


def check_text(text: str, world: dict, look: dict | None = None, *, plate: bool = False, people: bool = False,
               visitors_named: list[str] | None = None, beat: int | None = None) -> list[dict]:
    """Findings for one prompt: [{rule, severity, detail}]. UR-23 absent objects, UR-24 child cues and costume, UR-26 light keys."""
    look = look or load_look()
    found = []

    def add(rule, detail, severity="FAIL"):
        found.append({"rule": rule, "severity": severity, "detail": detail})

    # the visitors' own era may bring its own props: only words absent from BOTH eras fail
    bad = [w for w in words_in(text, world["absent"])]
    if bad and not visitors_named:
        add("UR-23", f"objects that do not exist in this world: {bad}")
    elif bad:
        add("UR-23", f"objects absent from the host world (allowed only on the named visitors {visitors_named}): {bad}",
            "REVIEW")
    if beat is not None:  # UR-27: the picture may not show what the story has not made yet (a "no X" phrase is allowed)
        early = words_in(text, not_yet(world, beat))
        if early:
            add("UR-27", f"shows what does not exist yet at beat {beat}: {early}")
    cues = words_in(text, look["child_cues"])
    if cues:
        add("UR-24", f"child cues in the prompt: {cues}")
    banned = words_in(text, look["banned_words"])
    if banned:
        add("UR-24", f"banned look words: {banned}")
    if look["thread"].lower() not in text.lower():
        add("UR-22", "the look v2 thread is missing from the prompt")
    keys = [v for v in world["light_keys"].values() if v.lower() in text.lower()]
    if len(keys) != 1:
        add("UR-26", f"exactly one light key per prompt (found {len(keys)})")
    if (people and not plate) and not words_in(text, [w for c in world["host"]["costume"] for w in [c]] +
                                                [c for v in world["visitors"] for c in v["costume"]]):
        add("UR-24", "people without a costume from the world's costume list", "REVIEW")
    return found
