"""Validator for TASK VAL-SHIFT-LINE-ID.

Checks that every segment declaring a ``drama.shift`` (excluding ``button``
segments) binds that dramatic turn to one or more concrete line identifiers
within the same segment via ``drama.shift_line``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from explainer_engine.scripting import story_lint
except ImportError:  # pragma: no cover - fallback when executed as a standalone script
    import story_lint  # type: ignore

DEFAULT_RULES_PATH = Path(__file__).with_name("shift_line_id_rules.json")

DEFAULT_RULES: dict[str, Any] = {
    "after_overlap_min": 0.2,
    "neighbour_window": 1,
    "kind": "hypothesis",
}

_SHIFT_ARROWS = ("—>", "->", "→", "=>")
_SEG_LINE_ADDR_RE = re.compile(r"^([A-Za-z0-9_-]+)#(\d+)$")
_NARRATOR_ROLES = {"narrator", "vo", "voiceover", "voice_over"}


def load_rules(rules_path: Path | str | None = None) -> dict[str, Any]:
    """Load threshold rules from JSON, falling back to built-in hypotheses."""
    path = Path(rules_path) if rules_path is not None else DEFAULT_RULES_PATH
    rules = dict(DEFAULT_RULES)
    if path.is_file():
        with path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            rules.update(loaded)
    return rules


def _seg_id(seg: dict[str, Any], fallback_idx: int) -> str:
    return str(seg.get("id") or seg.get("segment_id") or f"S{fallback_idx:02d}")


def _line_text(line: dict[str, Any]) -> str:
    for key in ("text", "dialogue", "line", "narration", "content"):
        val = line.get(key)
        if isinstance(val, str):
            return val
    return ""


def _is_narrator_line(line: dict[str, Any]) -> bool:
    """Repo convention (scene_lint, story_lint): a character line has ``speaker`` (script /3) or
    ``speaker_type == "character"`` (v4); every other line is the narrator."""
    if line.get("is_narrator") is True:
        return True
    stype = str(line.get("speaker_type") or "").strip().lower()
    if stype:
        return stype != "character"
    speaker = line.get("speaker") or line.get("speaker_id") or line.get("character")
    if isinstance(speaker, str) and speaker.strip():
        return speaker.strip().lower() in _NARRATOR_ROLES
    return True


def _quote_line(line: dict[str, Any], addr: str) -> str:
    snippet = _line_text(line).strip().replace("\n", " ")[:80]
    return f'{addr} "{snippet}"'


def _extract_shot_ids(line: dict[str, Any], seg: dict[str, Any], line_idx_0: int) -> list[str]:
    shot_ids: list[str] = []

    def _collect(item: Any) -> None:
        if isinstance(item, str) and item.strip():
            shot_ids.append(item.strip())
        elif isinstance(item, dict):
            sid = item.get("id") or item.get("shot_id")
            if isinstance(sid, str) and sid.strip():
                shot_ids.append(sid.strip())

    for key in ("shot_id", "shot", "shots"):
        val = line.get(key)
        if isinstance(val, list):
            for entry in val:
                _collect(entry)
        elif val is not None:
            _collect(val)

    # Also support segment-level shots referencing line numbers/ids
    seg_shots = seg.get("shots")
    if isinstance(seg_shots, list):
        line_no_1 = line_idx_0 + 1
        own_id = line.get("id") or line.get("line_id")
        for shot in seg_shots:
            if not isinstance(shot, dict):
                continue
            sid = shot.get("id") or shot.get("shot_id")
            if not isinstance(sid, str) or not sid.strip():
                continue
            ref_line = shot.get("line") or shot.get("line_no")
            ref_line_id = shot.get("line_id")
            ref_lines = shot.get("lines")
            if (
                ref_line == line_no_1
                or (own_id is not None and ref_line_id == own_id)
                or (isinstance(ref_lines, list) and (line_no_1 in ref_lines or own_id in ref_lines))
            ):
                shot_ids.append(sid.strip())

    return shot_ids


def line_index(seg: dict[str, Any]) -> dict[str, tuple[int, dict[str, Any]]]:
    """Index all resolvable line identifiers in a segment to ``(1_based_line_no, line_dict)``.

    Supports:
    1. Explicit line id (``line["id"]`` or ``line["line_id"]``)
    2. Canonical segment-line address (e.g. ``S05#4``)
    3. Associated shot ids (e.g. ``SH012``)
    """
    index: dict[str, tuple[int, dict[str, Any]]] = {}
    lines = seg.get("lines")
    if not isinstance(lines, list):
        return index

    sid = seg.get("id") or seg.get("segment_id")

    for idx0, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        line_no = idx0 + 1
        entry = (line_no, line)

        # 1. Own line id
        for key in ("id", "line_id"):
            raw_id = line.get(key)
            if isinstance(raw_id, str) and raw_id.strip():
                index.setdefault(raw_id.strip(), entry)

        # 2. Segment#LineNo address
        if isinstance(sid, str) and sid.strip():
            index.setdefault(f"{sid.strip()}#{line_no}", entry)

        # 3. Shot id(s)
        for shot_id in _extract_shot_ids(line, seg, idx0):
            index.setdefault(shot_id, entry)

    return index


def parse_shift(text: str) -> tuple[str, str] | None:
    """Split a ``drama.shift`` string on ``->``, ``→``, ``=>``, or ``—>``.

    Returns ``(before, after)`` stripped strings, or ``None`` if no arrow is present.
    """
    if not isinstance(text, str):
        return None
    for arrow in _SHIFT_ARROWS:
        if arrow in text:
            before, after = text.split(arrow, 1)
            return (before.strip(), after.strip())
    return None


def _overlap_score(after_text: str, candidate_text: str) -> float:
    """Share of the content words of ``after_text`` found in ``candidate_text``.

    story_lint.overlap(said: set, seen: set) takes SETS (verified in the repo copy); the original passed strings.
    """
    cw = getattr(story_lint, "content_words", None)
    ov = getattr(story_lint, "overlap", None)
    if callable(cw) and callable(ov):
        return float(ov(cw(after_text), cw(candidate_text)))
    words = lambda t: {w for w in re.findall(r"[a-z']+", t.lower()) if len(w) > 2}  # noqa: E731
    said, seen = words(after_text), words(candidate_text)
    return len(said & seen) / len(said) if said else 0.0


def _normalize_shift_line_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        val = raw.strip()
        return [val] if val else []
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif item is not None:
                out.append(str(item).strip())
        return [x for x in out if x]
    return [str(raw).strip()] if str(raw).strip() else []


def _finding(
    out: list[dict[str, str]],
    rule: str,
    where: str,
    detail: str,
    severity: str,
) -> None:
    out.append(
        {
            "rule": rule,
            "severity": severity,
            "where": where,
            "detail": detail,
        }
    )


def check(
    doc: dict[str, Any],
    strict: bool = False,
    rules_path: Path | str | None = None,
) -> list[dict[str, str]]:
    """Validate ``drama.shift_line`` declarations across all segments of ``doc``."""
    findings: list[dict[str, str]] = []
    if not isinstance(doc, dict):
        return findings

    segments = doc.get("segments")
    if not isinstance(segments, list):
        return findings

    rules = load_rules(rules_path)
    after_overlap_min = float(rules.get("after_overlap_min", 0.2))
    neighbour_window = int(rules.get("neighbour_window", 1))

    # Pre-index every segment so cross-segment resolution (SL-02) is exact
    seg_records: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        sid = _seg_id(seg, idx + 1)
        seg_records.append(
            {
                "seg": seg,
                "sid": sid,
                "index": line_index(seg),
                "lines": seg.get("lines") if isinstance(seg.get("lines"), list) else [],
            }
        )

    # SL-03: a named line id may be claimed by one segment only (keyed by the id across segments)
    claimed_refs: dict[str, str] = {}

    for rec in seg_records:
        seg = rec["seg"]
        sid = rec["sid"]
        idx_map: dict[str, tuple[int, dict[str, Any]]] = rec["index"]
        seg_lines: list[Any] = rec["lines"]

        drama = seg.get("drama")
        if not isinstance(drama, dict) or not drama:
            continue

        func = str(drama.get("function") or "").strip().lower()
        if func == "button":
            continue

        shift = drama.get("shift")
        if not isinstance(shift, str) or not shift.strip():
            continue

        # SL-01: drama.shift present but drama.shift_line missing or empty
        if "shift_line" not in drama or drama.get("shift_line") is None:
            _finding(
                findings,
                "SL-01",
                sid,
                "drama.shift is declared without drama.shift_line",
                "FAIL" if strict else "REVIEW",
            )
            continue

        target_ids = _normalize_shift_line_ids(drama.get("shift_line"))
        if not target_ids:
            _finding(
                findings,
                "SL-01",
                sid,
                "drama.shift_line is empty",
                "FAIL" if strict else "REVIEW",
            )
            continue

        resolved_entries: list[tuple[str, int, dict[str, Any]]] = []

        for raw_ref in target_ids:
            if raw_ref in idx_map:
                line_no, line_obj = idx_map[raw_ref]
                resolved_entries.append((raw_ref, line_no, line_obj))
                continue

            # SL-02: id not in THIS segment; check if it resolves in another segment
            other_match: tuple[str, int, dict[str, Any]] | None = None
            for other in seg_records:
                if other["sid"] == sid:
                    continue
                if raw_ref in other["index"]:
                    o_no, o_line = other["index"][raw_ref]
                    other_match = (other["sid"], o_no, o_line)
                    break

            if other_match is None:
                m = _SEG_LINE_ADDR_RE.match(raw_ref)
                if m and m.group(1) != sid:
                    target_sid = m.group(1)
                    target_no = int(m.group(2))
                    for other in seg_records:
                        if other["sid"] == target_sid:
                            if 1 <= target_no <= len(other["lines"]) and isinstance(
                                other["lines"][target_no - 1], dict
                            ):
                                other_match = (
                                    target_sid,
                                    target_no,
                                    other["lines"][target_no - 1],
                                )
                            else:
                                other_match = (target_sid, 0, {})
                            break

            if other_match is not None:
                o_sid, o_no, o_line = other_match
                if o_no > 0:
                    quote = _quote_line(o_line, f"{o_sid}#{o_no}")
                    detail = f"shift_line '{raw_ref}' belongs to segment {o_sid} ({quote}), not {sid}"
                else:
                    detail = f"shift_line '{raw_ref}' references segment {o_sid}, not {sid}"
            else:
                detail = f"shift_line '{raw_ref}' does not resolve to any line in {sid}"

            _finding(findings, "SL-02", sid, detail, "FAIL")

        if not resolved_entries:
            continue

        # Deduplicate resolved lines within the same segment while preserving order
        unique_resolved: list[tuple[str, int, dict[str, Any]]] = []
        seen_line_nos: set[int] = set()
        for raw_ref, line_no, line_obj in resolved_entries:
            if line_no not in seen_line_nos:
                seen_line_nos.add(line_no)
                unique_resolved.append((raw_ref, line_no, line_obj))

        # SL-03: two segments declare the same line id
        for raw_ref, line_no, line_obj in unique_resolved:
            addr = f"{sid}#{line_no}"
            prev_sid = claimed_refs.get(raw_ref)
            if prev_sid is not None and prev_sid != sid:
                _finding(
                    findings,
                    "SL-03",
                    addr,
                    f"duplicate shift_line '{raw_ref}' ({_quote_line(line_obj, addr)}) already declared by {prev_sid}",
                    "FAIL",
                )
            else:
                claimed_refs[raw_ref] = sid

        parsed = parse_shift(shift)

        # SL-04: named line has no text, or is the first line while shift has a before-state
        for raw_ref, line_no, line_obj in unique_resolved:
            addr = f"{sid}#{line_no}"
            text = _line_text(line_obj).strip()
            if not text:
                _finding(
                    findings,
                    "SL-04",
                    addr,
                    f"named shift_line '{raw_ref}' has no text ({_quote_line(line_obj, addr)})",
                    "REVIEW",
                )
            elif line_no == 1 and parsed is not None and bool(parsed[0]):
                _finding(
                    findings,
                    "SL-04",
                    addr,
                    f"shift has before-state '{parsed[0]}' but turn occurs on first line ({_quote_line(line_obj, addr)})",
                    "REVIEW",
                )

        # SL-05: segment has dialogue, but every named line is narrator
        dict_lines = [ln for ln in seg_lines if isinstance(ln, dict)]
        has_dialogue = any(not _is_narrator_line(ln) and bool(_line_text(ln).strip()) for ln in dict_lines)
        if has_dialogue and all(_is_narrator_line(ln) for _, _, ln in unique_resolved):
            first_no = unique_resolved[0][1]
            first_line = unique_resolved[0][2]
            addr = f"{sid}#{first_no}"
            _finding(
                findings,
                "SL-05",
                addr,
                f"played, not told: segment {sid} has dialogue but shift_line resolves only to narrator ({_quote_line(first_line, addr)})",
                "REVIEW",
            )

        # SL-06: after-part of shift must overlap named line or neighbour within window
        first_no = unique_resolved[0][1]
        first_line = unique_resolved[0][2]
        primary_addr = f"{sid}#{first_no}"

        if parsed is None:
            _finding(
                findings,
                "SL-06",
                primary_addr,
                f"unparsable shift '{shift}' (no arrow); reader must confirm turn at {_quote_line(first_line, primary_addr)}",
                "REVIEW",
            )
            continue

        _, after_state = parsed
        if not after_state:
            _finding(
                findings,
                "SL-06",
                primary_addr,
                f"shift after-state is empty in '{shift}'; reader must confirm turn at {_quote_line(first_line, primary_addr)}",
                "REVIEW",
            )
            continue

        candidate_indices: set[int] = set()
        for _, line_no, _ in unique_resolved:
            idx0 = line_no - 1
            lo = max(0, idx0 - neighbour_window)
            hi = min(len(seg_lines) - 1, idx0 + neighbour_window)
            for c_idx in range(lo, hi + 1):
                candidate_indices.add(c_idx)

        best_score = 0.0
        for c_idx in sorted(candidate_indices):
            cand = seg_lines[c_idx]
            if not isinstance(cand, dict):
                continue
            cand_text = _line_text(cand)
            if not cand_text.strip():
                continue
            score = _overlap_score(after_state, cand_text)
            if score > best_score:
                best_score = score

        if best_score < after_overlap_min:
            _finding(
                findings,
                "SL-06",
                primary_addr,
                (
                    f"after-state '{after_state}' overlap {best_score:.2f} < {after_overlap_min:.2f} "
                    f"within window ±{neighbour_window}; reader must confirm at {_quote_line(first_line, primary_addr)}"
                ),
                "REVIEW",
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Exit 0 on pass/review-only, 1 on FAIL, 2 on unreadable input."""
    parser = argparse.ArgumentParser(description="Validate drama.shift_line bindings.")
    parser.add_argument("script", help="Path to production script JSON file")
    parser.add_argument("--strict", action="store_true", help="Treat SL-01 as FAIL")
    parser.add_argument("--rules", default=None, help="Optional path to shift_line_id_rules.json")
    args = parser.parse_args(argv)

    script_path = Path(args.script)
    try:
        raw_text = script_path.read_text(encoding="utf-8")
        doc = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: unreadable script '{script_path}': {exc}", file=sys.stderr)
        return 2

    if not isinstance(doc, dict):
        print(f"ERROR: root of '{script_path}' must be a JSON object", file=sys.stderr)
        return 2

    try:
        findings = check(doc, strict=args.strict, rules_path=args.rules)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: failed to check '{script_path}': {exc}", file=sys.stderr)
        return 2

    print(json.dumps(findings, indent=2, ensure_ascii=False))
    has_fail = any(f.get("severity") == "FAIL" for f in findings)
    return 1 if has_fail else 0


if __name__ == "__main__":
    sys.exit(main())
