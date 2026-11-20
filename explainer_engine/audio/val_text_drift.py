"""Validator for text drift between frozen narration and performed TTS script.

Requirement IDs:
- OR-A26: tone, interjections and sounds matter in script writing, but the agent must not stray from the common text.
- Project rule (performance-director stage): delivery is added "without changing the words".
"""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import re

# NOTE: the Drive export garbled these two regexes (markdown escapes); reconstructed from the TASK description
# and Gemini's NOTES: non-nested [..] tags, and runs of letters/digits with inner apostrophes.
_TAG_RE = re.compile(r"\[[^\]]*\]")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*")


@dataclass(frozen=True)
class Limits:
    """Configuration limits for text drift validation."""

    allowed_interjections: frozenset[str] = frozenset()
    severity: str = "REVIEW"


def _format_tokens(tokens: list[str]) -> str:
    return f'"{" ".join(tokens)}"'


def words_of(text: str) -> list[str]:
    """Extract lower-case word tokens after stripping non-nested [bracketed tags]."""
    if not isinstance(text, str):
        raise ValueError(f"Expected str for text, got {type(text).__name__}")

    without_tags = _TAG_RE.sub(" ", text)
    return [match.group(0).lower() for match in _WORD_RE.finditer(without_tags)]


def check(frozen: str, performed: str, limits: Limits = Limits()) -> list[dict]:
    """Compare spoken word tokens of frozen and performed text for drift (DRIFT-01..03)."""
    if not isinstance(frozen, str):
        raise ValueError(f"Expected str for frozen text, got {type(frozen).__name__}")
    if not isinstance(performed, str):
        raise ValueError(f"Expected str for performed text, got {type(performed).__name__}")
    if not isinstance(limits, Limits):
        raise ValueError(f"Expected Limits instance, got {type(limits).__name__}")
    if not isinstance(limits.severity, str) or not limits.severity.strip():
        raise ValueError("limits.severity must be a non-empty str")

    try:
        allowed = frozenset(str(token).lower() for token in limits.allowed_interjections)
    except TypeError as exc:
        raise ValueError("limits.allowed_interjections must be an iterable of strings") from exc

    frozen_words = words_of(frozen)
    performed_words = words_of(performed)

    matcher = difflib.SequenceMatcher(a=frozen_words, b=performed_words, autojunk=False)
    indexed_findings: list[tuple[int, str, dict]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        where = f"word {i1}"

        if tag == "delete":
            removed = frozen_words[i1:i2]
            finding = {
                "rule": "DRIFT-01",
                "severity": limits.severity,
                "where": where,
                "detail": f"Removed {_format_tokens(removed)} from frozen narration.",
            }
            indexed_findings.append((i1, "DRIFT-01", finding))

        elif tag == "insert":
            added = performed_words[j1:j2]
            if all(token in allowed for token in added):
                continue
            finding = {
                "rule": "DRIFT-02",
                "severity": limits.severity,
                "where": where,
                "detail": f"Added {_format_tokens(added)} to performed narration.",
            }
            indexed_findings.append((i1, "DRIFT-02", finding))

        elif tag == "replace":
            removed = frozen_words[i1:i2]
            added = performed_words[j1:j2]
            finding = {
                "rule": "DRIFT-03",
                "severity": limits.severity,
                "where": where,
                "detail": f"Replaced {_format_tokens(removed)} with {_format_tokens(added)} in performed narration.",
            }
            indexed_findings.append((i1, "DRIFT-03", finding))

    indexed_findings.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed_findings]
