# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/maps/timeline.py`
# Target Module : explainer_engine/maps/timeline.py
# Target Classes/Symbols : class Event (methods: ), class Timeline (methods: of, by_target), class WordClock (methods: __init__, abs_frame, frame_of), def build(), def progress()
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

"""Words to frames: the spine is the clock of every map and HUD item (word lock, CMP-04).

An item starts at the first frame of its trigger word; each event starts at the first frame of its own word, counted from the
item's start. A word index that is missing from the spine, or one that comes before the trigger, is a finding, never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_EVENT_FRAMES = 12


# TODO [CLAUDE-CLASS-SYNC: Event] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `Event` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
@dataclass(frozen=True)
class Event:
    id: str
    op: str
    target: str | None
    start: int      # item-relative frame
    frames: int
    args: dict = field(default_factory=dict)
    word_index: int | None = None


# TODO [CLAUDE-CLASS-SYNC: Timeline] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `Timeline` (methods: of, by_target) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
@dataclass(frozen=True)
class Timeline:
    fps: int
    duration: int                 # frames of the item
    events: tuple[Event, ...]
    trigger_frame: int            # spine frame of the trigger word

    def of(self, op: str) -> list[Event]:
        return [e for e in self.events if e.op == op]

    def by_target(self, target: str, op: str | None = None) -> list[Event]:
        return [e for e in self.events if e.target == target and (op is None or e.op == op)]


# TODO [CLAUDE-CLASS-SYNC: WordClock] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `WordClock` (methods: __init__, abs_frame, frame_of) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class WordClock:
    """The spine's words as a clock: ``frame_of(i)`` is the first frame of word ``i``, relative to the item's trigger word."""

    def __init__(self, spine: dict, trigger_word_index: int):
        self.words = spine["words"]
        self.fps = spine["fps"]
        if not 0 <= trigger_word_index < len(self.words):
            raise ValueError(f"trigger word {trigger_word_index} is not in the spine's {len(self.words)} words")
        self.origin = self.words[trigger_word_index]["start_frame"]
        self.trigger = trigger_word_index

    def abs_frame(self, word_index: int) -> int:
        if not 0 <= word_index < len(self.words):
            raise ValueError(f"word {word_index} is not in the spine's {len(self.words)} words")
        return self.words[word_index]["start_frame"]

    def frame_of(self, word_index: int) -> int:
        """The first frame of the word, counted from the item's first frame; a word before the trigger word is an error, not frame 0."""
        if word_index < self.trigger:
            raise ValueError(f"word {word_index} is before the item's trigger word {self.trigger}")
        return self.abs_frame(word_index) - self.origin


def build(spec: dict, spine: dict, trigger_word_index: int, duration_frames: int) -> tuple[Timeline, WordClock]:
    clock = WordClock(spine, trigger_word_index)
    events = tuple(Event(e["id"], e["op"], e.get("target"), clock.frame_of(e["word_index"]), e.get("frames", DEFAULT_EVENT_FRAMES),
                         e.get("args", {}), e["word_index"]) for e in spec["events"])
    return Timeline(clock.fps, duration_frames, events, clock.origin), clock


def progress(ev: Event, f: float) -> float:
    """0 before the event, 1 after it, linear between (the caller eases)."""
    if f <= ev.start:
        return 0.0
    if f >= ev.start + ev.frames:
        return 1.0
    return (f - ev.start) / ev.frames
