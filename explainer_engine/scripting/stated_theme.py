"""Text-level heuristic check for stated themes and unopposed obstacles.

Implements TASK VAL-STATED-THEME (owner requirement OR-S04: show, don't tell)
as a non-blocking REVIEW pass for the script critic and owner:
- STH-01: Character dialogue states the theme via content-word overlap or moral
  phrasing.
- STH-02: STH-01 occurs in a segment with fewer than two distinct speakers.
- STH-03: Segment declares a non-empty `scene.obstacle_want` with no opposing
  character speaking or reacting.
- STH-00: Informational NOT_RUN finding when no theme text is provided
  (moral-phrase matching and STH-03 still execute).

Note: This is a text-level heuristic (token overlap and phrase matching); it
does not parse semantic meaning or narrative subtext.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REVIEW_SUFFIX = "(REVIEW: a reading flag for the script critic, not a block)"

DEFAULT_RULES_PATH = Path(__file__).with_name("stated_theme_rules.json")

_DEFAULT_RULES: dict[str, Any] = {
    "kind": "hypothesis",
    "theme_cover_min": 0.5,
    "min_line_words": 6,
    "moral_phrases": [
        "the lesson is",
        "what really matters is",
        "we learned that",
        "the truth is that",
        "at the end of the day",
        "the real moral is",
        "what this teaches us is",
        "the point of all this is",
        "that is why we must",
        "true strength comes from",
    ],
}

# Stop-word set aligned with story_lint._STOP convention for content-word extraction.
_STOP: set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "doing", "done", "for", "from", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "itself", "just", "me", "might", "more", "most", "must", "my", "myself",
    "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shall", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "we", "were",
    "what", "when", "where", "which", "while", "who", "whom", "why", "will",
    "with", "would", "you", "your", "yours", "yourself", "yourselves",
}

_WORD_RE = re.compile(r"[a-z']+")


def load_rules(rules_path: Path | None = None) -> dict[str, Any]:
    """Load threshold and moral-phrase configuration from JSON, falling back to defaults."""
    path = rules_path or DEFAULT_RULES_PATH
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(_DEFAULT_RULES)
        merged.update(data)
        return merged
    return dict(_DEFAULT_RULES)


def _lexicon(phrases: list[str] | tuple[str, ...]) -> re.Pattern[str] | None:
    """Compile a case-insensitive phrase-boundary regex matching scene_lint._lexicon style."""
    cleaned = [re.escape(p.strip()) for p in phrases if p and p.strip()]
    if not cleaned:
        return None
    cleaned.sort(key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(cleaned) + r")\b", re.IGNORECASE)


def content_words(text: str) -> set[str]:
    """Extract lowercase non-stopword content tokens."""
    if not text:
        return set()
    tokens = [tok.strip("'") for tok in _WORD_RE.findall(text.lower())]
    return {tok for tok in tokens if tok and tok not in _STOP and len(tok) > 2}  # story_lint.content_words: 3+ letters


def _f(
    out: list[dict[str, str]],
    rule: str,
    where: str,
    detail: str,
    sev: str = "REVIEW",
) -> None:
    """Append a normalized finding ensuring the required REVIEW suffix."""
    msg = detail.strip()
    if not msg.endswith(REVIEW_SUFFIX):
        msg = f"{msg} {REVIEW_SUFFIX}"
    out.append(
        {
            "rule": rule,
            "severity": sev,
            "where": where,
            "detail": msg,
        }
    )


def _resolve_theme(doc: dict[str, Any], theme_text: str | None) -> str:
    """Resolve theme text from drama.theme, then drama.controlling_idea, then theme_text=."""
    drama = doc.get("drama")
    if isinstance(drama, dict):
        for key in ("theme", "controlling_idea"):
            val = drama.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if isinstance(theme_text, str) and theme_text.strip():
        return theme_text.strip()
    return ""


def _is_shorts(doc: dict[str, Any]) -> bool:
    """Detect whether the document is a Shorts script (exempt)."""
    fmt = str(doc.get("format") or doc.get("kind") or doc.get("video_type") or "").lower()
    if "short" in fmt:
        return True
    if doc.get("is_shorts") is True or doc.get("shorts") is True:
        return True
    meta = doc.get("meta")
    if isinstance(meta, dict):
        meta_fmt = str(meta.get("format") or meta.get("type") or "").lower()
        if "short" in meta_fmt or meta.get("is_shorts") is True:
            return True
    return False


def _is_cold_open(seg: dict[str, Any]) -> bool:
    """Detect whether a segment is a cold open (exempt)."""
    seg_type = str(seg.get("type") or seg.get("role") or seg.get("section") or "").lower()
    if seg_type in {"cold_open", "cold-open", "cold open", "hook"}:
        return True
    if seg.get("is_cold_open") is True or seg.get("cold_open") is True:
        return True
    scene = seg.get("scene")
    if isinstance(scene, dict):
        func = str(scene.get("function") or scene.get("role") or "").lower()
        if func in {"cold_open", "cold-open", "cold open"}:
            return True
    return False


def _seg_where(seg: dict[str, Any], fallback_idx: int) -> str:
    """Format PV-37 segment location identifier (`seg#n`)."""
    raw_id = seg.get("id") or seg.get("seg") or seg.get("seg_id") or seg.get("index")
    if isinstance(raw_id, str) and raw_id.strip():
        return raw_id.strip()
    if isinstance(raw_id, int) and not isinstance(raw_id, bool):
        return f"S{raw_id:02d}"
    return f"S{fallback_idx:02d}"


def _speaker_identity(turn: dict[str, Any]) -> tuple[str, str]:
    """Normalize production_script/3 (`speaker`) and v4 (`speaker_type`, `speaker_id`).

    Returns `(role_kind, canonical_speaker_id)` where `role_kind` is one of
    `'narrator'`, `'on_screen'`, or `'character'`.
    """
    raw_type = str(turn.get("speaker_type") or "").strip().lower()
    raw_id = str(turn.get("speaker_id") or "").strip()
    raw_speaker = str(turn.get("speaker") or "").strip()

    if raw_type in {"narrator", "narration", "vo", "voiceover"}:
        return ("narrator", "narrator")
    if raw_type in {"on_screen", "onscreen", "text", "title", "caption", "chyron", "super"}:
        return ("on_screen", "on_screen")

    label = raw_id or raw_speaker
    lower_label = label.lower()

    if lower_label in {"narrator", "narration", "vo", "voiceover", "voice-over"}:
        return ("narrator", "narrator")
    if lower_label in {
        "on_screen",
        "onscreen",
        "on-screen",
        "on screen",
        "text",
        "title",
        "caption",
        "chyron",
        "super",
    }:
        return ("on_screen", "on_screen")

    if raw_type in {"character", "dialogue", "cast", "actor", "person"} or label:
        return ("character", lower_label or "unknown_character")

    return ("narrator", "narrator")


def _extract_turns(seg: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect dialogue/speech turns from a segment across v3 and v4 layouts."""
    turns: list[dict[str, Any]] = []
    for key in ("dialogue", "turns", "lines", "beats"):
        items = seg.get(key)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if key == "beats" and item.get("kind") not in (None, "dialogue", "line", "speech"):
                    continue
                if any(k in item for k in ("text", "line", "dialogue", "words")):
                    turns.append(item)

    scene = seg.get("scene")
    if isinstance(scene, dict):
        for key in ("dialogue", "turns", "lines"):
            items = scene.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and any(
                        k in item for k in ("text", "line", "dialogue", "words")
                    ):
                        turns.append(item)

    if not turns and isinstance(seg.get("text"), str) and (
        "speaker" in seg or "speaker_id" in seg or "speaker_type" in seg
    ):
        turns.append(seg)

    return turns


def _turn_text(turn: dict[str, Any]) -> str:
    for key in ("text", "line", "dialogue", "words"):
        val = turn.get(key)
        if isinstance(val, str):
            return val
    return ""


def _normalize_id(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip().lower()


def _has_expression_reaction(seg: dict[str, Any], scene: dict[str, Any], excluded_who: set[str]) -> bool:
    """Check whether visual_beats contains an `expression` beat by another present character."""
    beat_containers: list[Any] = [seg.get("visual_beats"), scene.get("visual_beats")]
    for key in ("lines", "dialogue", "turns"):  # repo shape: visual_beats live on each line (scene_lint SC-05)
        for ln in seg.get(key) or []:
            if isinstance(ln, dict):
                beat_containers.append(ln.get("visual_beats"))
    for container in beat_containers:
        if not isinstance(container, list):
            continue
        for beat in container:
            if not isinstance(beat, dict):
                continue
            kind = _normalize_id(beat.get("kind") or beat.get("type"))
            if kind != "expression":
                continue
            who = _normalize_id(beat.get("who") or beat.get("character") or beat.get("speaker_id"))
            if who and who not in excluded_who:
                return True
    return False


def check(
    doc: dict[str, Any],
    theme_text: str | None = None,
    rules_path: Path | None = None,
) -> list[dict[str, str]]:
    """Run stated-theme and unopposed-obstacle REVIEW checks on a script document."""
    findings: list[dict[str, str]] = []
    if not isinstance(doc, dict) or _is_shorts(doc):
        return findings

    rules = load_rules(rules_path)
    theme_cover_min = float(rules.get("theme_cover_min", 0.5))
    min_line_words = int(rules.get("min_line_words", 6))
    moral_rx = _lexicon(rules.get("moral_phrases", []))

    resolved_theme = _resolve_theme(doc, theme_text)
    theme_tokens = content_words(resolved_theme)
    has_theme = bool(resolved_theme and theme_tokens)

    if not has_theme:
        _f(
            findings,
            rule="STH-00",
            where="doc",
            detail="the stated-theme rule was not run (no theme text); the moral-phrase lexicon and STH-03 ran.",
            sev="NOT_RUN",
        )

    segments = doc.get("segments")
    if not isinstance(segments, list):
        return findings

    for idx, seg in enumerate(segments, start=1):
        if not isinstance(seg, dict):
            continue
        if _is_cold_open(seg):
            continue

        where = _seg_where(seg, idx)
        scene = seg.get("scene")
        has_scene = isinstance(scene, dict)
        turns = _extract_turns(seg)

        # Evaluate STH-01 and STH-02 on character dialogue turns.
        char_speakers: set[str] = set()
        sth01_triggered_in_seg = False
        sth01_reasons: list[str] = []

        for turn_no, turn in enumerate(turns, start=1):
            role_kind, speaker_id = _speaker_identity(turn)
            if role_kind != "character":
                continue
            char_speakers.add(speaker_id)

            line_text = _turn_text(turn)
            line_tokens = content_words(line_text)
            if len(line_tokens) < min_line_words:
                continue

            matched_moral = moral_rx.search(line_text) if moral_rx else None
            overlap_ratio = 0.0
            if has_theme and theme_tokens:
                overlap_ratio = len(line_tokens & theme_tokens) / len(theme_tokens)

            if overlap_ratio >= theme_cover_min or matched_moral is not None:
                sth01_triggered_in_seg = True
                reasons: list[str] = []
                if overlap_ratio >= theme_cover_min:
                    reasons.append(f"covers {overlap_ratio:.0%} of theme content words")
                if matched_moral is not None:
                    reasons.append(f"matches moral phrase '{matched_moral.group(0)}'")
                reason_str = " and ".join(reasons)
                sth01_reasons.append(f"{speaker_id} ({reason_str})")
                snippet = line_text.strip().replace("\n", " ")[:80]
                _f(
                    findings,
                    rule="STH-01",
                    where=f"{where}#{turn_no}",
                    detail=(
                        f'"{snippet}" ({speaker_id}; {reason_str}): a hero states the theme '
                        "(OR-S04 show don't tell): play it as an action or a choice."
                    ),
                    sev="REVIEW",
                )

        if sth01_triggered_in_seg and len(char_speakers) < 2:
            speakers_desc = ", ".join(sorted(char_speakers)) if char_speakers else "none"
            _f(
                findings,
                rule="STH-02",
                where=where,
                detail=(
                    f"no one in the scene can answer it: theme stated by the only voice present "
                    f"(speakers: {speakers_desc}; triggered by {'; '.join(sth01_reasons)})."
                ),
                sev="REVIEW",
            )

        # Evaluate STH-03: requires both a scene dict and dialogue turns.
        if not has_scene or not turns:
            continue

        obstacle_want = scene.get("obstacle_want")
        has_obstacle = (
            isinstance(obstacle_want, str) and bool(obstacle_want.strip())
        ) or (isinstance(obstacle_want, (list, dict)) and len(obstacle_want) > 0)

        if not has_obstacle:
            continue

        pov = _normalize_id(scene.get("pov"))
        present_raw = scene.get("present")
        present_chars = {
            _normalize_id(p)
            for p in (present_raw if isinstance(present_raw, list) else [])
            if _normalize_id(p)
        }

        fewer_than_two_speakers = len(char_speakers) < 2

        all_speakers_are_pov_and_no_other_reacts = False
        if pov and char_speakers and char_speakers.issubset({pov}):
            other_present = present_chars - {pov}
            other_spoke = bool(char_speakers - {pov})
            other_reacted = _has_expression_reaction(seg, scene, excluded_who={pov})
            if not other_spoke and not other_reacted:
                # Fires when either no other present member exists or none of them spoke/reacted.
                if not other_present or not other_reacted:
                    all_speakers_are_pov_and_no_other_reacts = True

        # If fewer than two speakers spoke, check whether another present character reacted via expression beat.
        if fewer_than_two_speakers:
            excluded = set(char_speakers)
            if pov:
                excluded.add(pov)
            other_present = present_chars - excluded
            other_reacted = bool(other_present) and _has_expression_reaction(
                seg, scene, excluded_who=excluded
            )
            if other_reacted and not all_speakers_are_pov_and_no_other_reacts:
                fewer_than_two_speakers = False

        if fewer_than_two_speakers or all_speakers_are_pov_and_no_other_reacts:
            _f(
                findings,
                rule="STH-03",
                where=where,
                detail=(
                    "Scene declares obstacle_want without an opposing character speaking or "
                    "reacting via an expression beat."
                ),
                sev="REVIEW",
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Exits 0 even when findings exist; exits 2 on unreadable input file."""
    parser = argparse.ArgumentParser(
        description="Run stated-theme and unopposed-obstacle REVIEW checks on a script JSON."
    )
    parser.add_argument("script_path", help="Path to script JSON file.")
    parser.add_argument(
        "--theme",
        dest="theme_text",
        default=None,
        help="Optional fallback theme text if drama.theme / drama.controlling_idea are absent.",
    )
    parser.add_argument(
        "--rules",
        dest="rules_path",
        default=None,
        help="Optional path to stated_theme_rules.json.",
    )
    args = parser.parse_args(argv)

    script_file = Path(args.script_path)
    try:
        raw = script_file.read_text(encoding="utf-8")
        doc = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"Error reading {script_file}: {exc}", file=sys.stderr)
        return 2

    rules_path = Path(args.rules_path) if args.rules_path else None
    findings = check(doc, theme_text=args.theme_text, rules_path=rules_path)
    print(json.dumps(findings, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
