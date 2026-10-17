"""The universe thread for generated art (UR-22, the primary visual rule).

Every image prompt (pod pictures and Gemini cast sprites) carries the same drawing rules from the episode look, so characters,
props and places look drawn by one artist for one scene, in every era and every place. ``sprite_prompt`` builds the Gemini
prompt of a cast sprite from the look; ``assert_thread`` is the guard the generators call before any paid image.
"""

from __future__ import annotations

KEY = ("Full body, one figure only, feet visible, no text, no letters, no logo. Flat solid pure green #00FF00 background, no "
       "shadow on the background, no green on the figure.")


def thread(look: dict) -> str:
    t = str(look.get("universe_thread", "")).strip(" ,.")
    if not t:
        raise ValueError("the look has no universe_thread (UR-22)")
    return t


def assert_thread(prompt: str, look: dict) -> None:
    if thread(look).lower() not in prompt.lower():
        raise ValueError("the image prompt lacks the universe thread (UR-22): refusing to spend on it")


def sprite_prompt(who: str, look_of_person: str, pose: str, look: dict) -> str:
    """A cast sprite in the episode's universe: the person (from historical portraits), the emotional pose, the thread."""
    text = (f"A friendly CARICATURE of the historical figure {who}: {look_of_person}. Pose and expression: {pose}. "
            f"Adult, dignified-comic. Drawn in {thread(look)}. {KEY}")
    assert_thread(text, look)
    return text
