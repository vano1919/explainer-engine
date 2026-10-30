"""Words to frames: the spine is the clock of every map and HUD item (word lock, CMP-04).

An item starts at the first frame of its trigger word; each event starts at the first frame of its own word, counted from the
item's start. A word index that is missing from the spine, or one that comes before the trigger, is a finding, never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_EVENT_FRAMES = 12


@dataclass(frozen=True)
class Event:
    id: str
    op: str
    target: str | None
    start: int      # item-relative frame
    frames: int
    args: dict = field(default_factory=dict)
    word_index: int | None = None


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
        return max(0, self.abs_frame(word_index) - self.origin)


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
