"""Voice-direction validators (final plan S11, W2): the elevenlabs-voice checklist rows. Input: audio lines
(``text``, ``delivery_direction``, ``speaker_type``) and the shots they sit in (``visual_type``, ``face_visible``)."""
from __future__ import annotations

import re

from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-VOX-05", "CRAFT-VOX-09")
_CAPS = re.compile(r"\b[A-Z]{2,}\b")
_TAG = re.compile(r"\[[^\]]+\]")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", _TAG.sub("", text).strip()) if s]


def one_stressed_word(lines: list[dict]) -> dict:
    """CRAFT-VOX-05 (critic): at most one stressed (ALL-CAPS) word per sentence; whether a tag changes the delivery is judged."""
    over = []
    for ln in lines:
        for s in _sentences(ln.get("text", "")):
            if len(_CAPS.findall(s)) > 1:
                over.append(ln.get("line_id", "?"))
                break
    return C.critic("CRAFT-VOX-05", "PF-01", [f"one stressed word in line {i}" for i in over[:10]],
                    "one stressed word per sentence; a tag only where the delivery changes", {"over": over})


def animated_line_delivery(shots: list[dict], lines_by_id: dict[str, dict]) -> dict:
    """CRAFT-VOX-09 (critic): the line of an animated shot carries a ``delivery_direction`` and the shot shows a face the lens sees
    (``face_visible`` true)."""
    missing = []
    for s in shots:
        if s.get("visual_type") not in ("cinematic_video", "animated", "video"):
            continue
        for lid in s.get("audio_line_ids") or []:
            ln = lines_by_id.get(lid) or {}
            if not str(ln.get("delivery_direction") or "").strip():
                missing.append(f"delivery_direction of {lid}")
            if s.get("face_visible") is not True:
                missing.append(f"face_visible on {s.get('shot_id', '?')}")
    return C.critic("CRAFT-VOX-09", "KP-17", sorted(set(missing))[:10],
                    "an animated shot's line carries delivery (pace, loudness, colour) and a face the lens sees")


def validate(lines: list[dict], shots: list[dict] | None = None) -> list[dict]:
    rows = [one_stressed_word(lines)]
    if shots is not None:
        rows.append(animated_line_delivery(shots, {l.get("line_id"): l for l in lines}))
    return rows
