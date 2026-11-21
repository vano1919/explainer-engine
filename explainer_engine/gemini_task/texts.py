"""The Gemini Task texts as data (A1 spec acceptance 1-6; manifest ``texts/manifest.json``).

Reads the MESSAGE and CLAUSE blocks, fills ``{{name}}`` and ``{{bp:<rule>.<threshold>[|percent]}}`` placeholders, strips
operator notes (``<!-- -->``) from pack files, and refuses: a placeholder the manifest does not declare, a declared one
left without a value, and (for anything that reaches the image tool) a never-word of the preset outside a "never" phrase.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.imagegen import turn_pack as TP

TEXTS = Path(__file__).resolve().parent / "texts"
PLACEHOLDER = re.compile(r"\{\{([^{}]+)\}\}")
MESSAGE = re.compile(r"=====BEGIN MESSAGE=====\n(.*?)\n=====END MESSAGE=====", re.S)
CLAUSE = re.compile(r"=====BEGIN CLAUSE (\w+)=====\n(.*?)\n=====END CLAUSE=====", re.S)
COMMENT = re.compile(r"<!--.*?-->\n?", re.S)
MESSAGE_FILES = {"T0": "T0_GATE_TEST.md", "P0": "P0_OPEN_EPISODE_CHAT.md", "P1": "P1_CHECK_SHORT_STORY.md",
                 "P2": "P2_CHECK_SCRIPT.md", "P3": "P3_CHECK_VIDEO_SCRIPT.md", "P4": "P4_REPLY_TO_FINDINGS.md",
                 "P5": "P5_SAVE_SHOT_QUEUE.md", "P6": "P6_REFERENCE_BATCH.md", "P7": "P7_SCENE_BATCH.md",
                 "P8": "P8_NEXT_BATCH.md", "P9": "P9_RESUME_AFTER_LIMIT.md", "P10": "P10_REDO_BATCH.md"}
# P6's two round notes, word for word from its operator notes (the manifest: "chosen by the exporter")
ROUND_NOTES = {"R1": "Round R1: portraits and places. Each picture uses only the main style picture.",
               "R2": "Round R2: full bodies. Each picture uses the main style picture and its own portrait only; it never "
                     "sees the other portraits."}
SECRET = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_\-]{20,}|ghp_[A-Za-z0-9]{30,}|"
                    r"resourcekey=|[?&](key|token|access_token)=|usp=sharing)", re.I)
GEORGIAN = re.compile(r"[Ⴀ-ჿᲐ-Ჿⴀ-⴯]")


@lru_cache(maxsize=1)
def manifest() -> dict:
    return json.loads((TEXTS / "manifest.json").read_text(encoding="utf-8"))


def declared() -> set[str]:
    m = manifest()
    return set(m["placeholders"]) | {f"bp:{k}" for k in m["bp_placeholders"]}


def sha8(text: str | bytes) -> str:
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()[:8]


def message(msg_id: str) -> str:
    """The one MESSAGE block of a message file (only this is ever sent)."""
    path = TEXTS / "messages" / MESSAGE_FILES[msg_id]
    blocks = MESSAGE.findall(path.read_text(encoding="utf-8"))
    if len(blocks) != 1:
        raise ContractError(f"{path.name}: exactly one MESSAGE block expected, found {len(blocks)}")
    return blocks[0]


@lru_cache(maxsize=1)
def clauses() -> dict[str, str]:
    return dict(CLAUSE.findall((TEXTS / "messages" / "PROMPT_CLAUSES.md").read_text(encoding="utf-8")))


def clause(name: str, **values) -> str:
    text = clauses().get(name)
    if text is None:
        raise ContractError(f"PROMPT_CLAUSES.md has no clause {name!r}")
    return fill(text, values, where=f"clause {name}")


def pack_file(name: str) -> str:
    """A Drive pack file without its operator notes."""
    return COMMENT.sub("", (TEXTS / "drive_pack" / name).read_text(encoding="utf-8"))


def bp_value(key: str):
    """``BP-105.nominal_narrator_share|percent`` -> the registry number (D-59: never copied into code)."""
    from explainer_engine.standards import sourced_rules
    base, _, fmt = key.partition("|")
    entry = manifest()["bp_placeholders"].get(base)
    if entry is None:
        raise ContractError(f"bp:{base} is not declared in texts/manifest.json")
    v = sourced_rules.T(entry["rule"], entry["threshold"])
    if fmt == "percent":
        return f"{round(float(v) * 100):g} %"
    if fmt:
        raise ContractError(f"unknown bp format {fmt!r}")
    return f"{v:g}" if isinstance(v, float) else str(v)


def fill(text: str, values: dict, where: str = "text") -> str:
    """Every placeholder declared and filled, or ContractError (spec acceptance 2)."""
    names = PLACEHOLDER.findall(text)
    known = declared()
    undeclared = sorted({n for n in names if n.split("|")[0] not in known})
    if undeclared:
        raise ContractError(f"{where}: placeholders not declared in texts/manifest.json: {undeclared}")
    missing = sorted({n for n in names if not n.startswith("bp:") and values.get(n) in (None, "")})
    if missing:
        raise ContractError(f"{where}: placeholders without a value: {missing}")

    def sub(m: re.Match) -> str:
        n = m.group(1)
        return bp_value(n[3:]) if n.startswith("bp:") else str(values[n])
    out = PLACEHOLDER.sub(sub, text)
    if PLACEHOLDER.search(out):
        raise ContractError(f"{where}: a value itself holds a placeholder: {PLACEHOLDER.search(out).group(0)}")
    return out


def never_gate(text: str, never_words: list[str], where: str) -> None:
    """Acceptance 1 / GC-18: no never-word outside a "never" phrase in anything that reaches the image tool."""
    hits = TP.never_hits({"never_words": never_words}, text)
    if hits:
        raise ContractError(f"{where}: words the image tool redraws as a camera picture: {hits} (GC-18)")


def clean_gate(text: str, where: str) -> None:
    """Acceptance 5 for anything written for Drive or Gemini: no secret, no keyed link, English only."""
    if SECRET.search(text):
        raise ContractError(f"{where}: holds what looks like a secret or a keyed link ({SECRET.search(text).group(0)[:12]}...)")
    if GEORGIAN.search(text):
        raise ContractError(f"{where}: holds Georgian text; everything Gemini reads is English")


TOOL_VALUES = ("picture_blocks", "era_line", "hero_text", "place_text")   # values that reach the image tool


def render(msg_id: str, values: dict, never_words: list[str]) -> str:
    """One paste-ready message: filled, gated, and nothing outside its MESSAGE block. The never-word gate runs on the
    message's own words and on every value that reaches the image tool; an artefact under check (a story, a script) is
    Claude's text for the viewer and is not held to the picture words."""
    tpl = message(msg_id)
    never_gate(PLACEHOLDER.sub(" ", tpl), never_words, msg_id)
    for k in TOOL_VALUES:
        if values.get(k):
            never_gate(str(values[k]), never_words, f"{msg_id} {k}")
    out = fill(tpl, values, where=msg_id)
    clean_gate(out, msg_id)
    return out
