"""Prompt v2 (D-41, UR-22..UR-26): fixed slots, one light key, costume, the look v2 thread. stdlib only.

Order: shot type, subject (with its action and one emotion), world (costume, materials), ONE light key from the beat,
atmosphere, the look thread, the suffix. ``compose`` builds it; ``lint`` is ``world.resolver.check_text``.
"""

from __future__ import annotations

from explainer_engine.world.resolver import check_text, clause_for_beat, load_look

SHOT_WORDS = {"A": "wide cinematic establishing shot", "B": "medium cinematic shot", "C": "tight cinematic insert"}


def compose(shot_type: str, subject: str, world: dict, beat: int, *, people: bool = False, plate: bool = False,
            costume_hint: str = "", look: dict | None = None) -> str:
    look = look or load_look()
    parts = [SHOT_WORDS[shot_type], subject.strip(" ,.")]
    if people and not plate:
        parts.append(look["figure"])
        parts.append(costume_hint or "dressed in " + ", ".join(world["host"]["costume"][:2]))
    parts.append(", ".join(world["host"]["material_culture"][:3]))
    parts.append(clause_for_beat(world, beat))
    parts.append(", ".join(world["host"]["atmosphere"][:2]))
    return ", ".join(parts) + ", " + look["thread"] + look["suffix"]


def lint(prompt: str, world: dict, *, plate: bool = False, people: bool = False, visitors_named: list[str] | None = None,
         look: dict | None = None) -> list[dict]:
    return check_text(prompt, world, look, plate=plate, people=people, visitors_named=visitors_named)
