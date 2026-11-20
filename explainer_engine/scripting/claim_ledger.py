# explainer_engine/scripting/claim_ledger.py
# Source: Gemini chat https://gemini.google.com/app/555f8cdbcf6f833d (VAL-CLAIM-LEDGER)
# Text copied from the chat page (page text), not byte-exact. Review before use.
"""Evidence ledger and extended claim verification (VAL-CLAIM-LEDGER).

Extends PV-37 (`explainer_engine.scripting.claims`) by parsing optional ledger
columns from `claim_map.md` and evaluating rules CL-01 through CL-08 against
script documents without network or LLM dependencies.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

from explainer_engine.scripting import claims

try:
    from explainer_engine.scripting import story_lint
except ImportError:  # pragma: no cover - standalone fallback if story_lint unavailable
    story_lint = None  # type: ignore[assignment]

VALID_TYPES: frozenset[str] = frozenset({
    "factual",
    "statistical",
    "implied",
    "opinion",
    "prediction",
})

DEFAULT_ABSOLUTE_WORDS: tuple[str, ...] = (
    "always",
    "never",
    "every",
    "all",
    "none",
    "no one",
    "nobody",
    "only",
    "first",
    "last",
    "largest",
    "smallest",
    "most",
    "least",
    "impossible",
    "proved",
    "proven",
    "undefeated",
    "unprecedented",
)

VALID_VERDICTS: frozenset[str] = frozenset({"supported", "contradicted", "unverified", "mixed"})

DEFAULT_SUPPORT_OVERLAP_MIN: float = 0.25

# CL-01 patterns: year (1000-2999), percent (e.g. 90%, 12.5 %), or currency ($100, €50, £20, USD 100)
_YEAR_RE = re.compile(r"\b(?:1\d{3}|2\d{3})\b")
_PERCENT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%")
_CURRENCY_RE = re.compile(
    r"(?:[$€£¥]\s*\d[\d,.]*|\b\d[\d,.]*\s*(?:USD|EUR|GBP|GEL)\b)",
    re.IGNORECASE,
)

# Inline claim citations in script lines, e.g. [E-01], [M12], [I-03], [G-04]
_CITE_ID_RE = re.compile(r"\[([A-Z]-?\d{2,3})\]")

_FALLBACK_STOP: frozenset[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "doing", "done", "for", "from", "had",
    "has", "have", "having", "he", "her", "here", "hers", "him", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "just", "me", "more", "my",
    "no", "nor", "not", "now", "of", "on", "or", "other", "our", "out", "over",
    "own", "s", "same", "she", "should", "so", "some", "such", "t", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "would", "you", "your",
})

_WORD_RE = re.compile(r"[a-z0-9]+")


def _load_rules(rules_path: str | Path | None = None) -> dict[str, Any]:
    """Load rules configuration from claim_ledger_rules.json if present, else defaults."""
    defaults: dict[str, Any] = {
        "absolute_words": list(DEFAULT_ABSOLUTE_WORDS),
        "support_overlap_min": DEFAULT_SUPPORT_OVERLAP_MIN,
        "cl07a_severity": "FAIL",
    }
    candidates: list[Path] = []
    if rules_path is not None:
        candidates.append(Path(rules_path))
    else:
        here = Path(__file__).resolve().parent
        candidates.extend([
            here / "claim_ledger_rules.json",
            here.parent / "claim_ledger_rules.json",
            Path.cwd() / "claim_ledger_rules.json",
        ])

    for path in candidates:
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    merged = dict(defaults)
                    merged.update(loaded)
                    return merged
            except (OSError, json.JSONDecodeError):
                pass
    return defaults


def _finding(
    out: list[dict[str, Any]],
    rule: str,
    where: str,
    detail: str,
    sev: str = "REVIEW",
) -> None:
    """Append a finding in the repo shape ``{rule, severity, where, detail}`` (claims.py, story_lint._f)."""
    out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})


def _parse_bool_or_none(raw: str | None) -> bool | None:
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("", "-", "none", "null", "n/a", "na"):
        return None
    if val in ("true", "yes", "y", "1", "opened"):
        return True
    if val in ("false", "no", "n", "0", "unopened", "not opened"):
        return False
    return None


def _parse_optional_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    val = raw.strip()
    if val.lower() in ("", "-", "none", "null", "n/a", "na"):
        return None
    return val


def _parse_optional_float(raw: str | None) -> float | None:
    val = _parse_optional_str(raw)
    if val is None:
        return None
    try:
        return float(val.rstrip("%"))
    except ValueError:
        return None


def _parse_iso_date(raw: str | None) -> date | None:
    val = _parse_optional_str(raw)
    if val is None:
        return None
    try:
        return datetime.strptime(val[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _split_md_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def parse_ledger(text: str) -> dict[str, dict[str, Any]]:
    """Parse claim_map.md into an evidence ledger.

    Calls `claims.parse_map(text)` first to preserve all base fields, then parses
    optional ledger columns (`type`, `opened`, `verdict`, `confidence`, `checked`,
    `counter_source`). Legacy 4-column maps parse cleanly with optional fields set
    to `None`.
    """
    base_map = claims.parse_map(text)
    ledger: dict[str, dict[str, Any]] = {}
    for cid, entry in base_map.items():
        copied = dict(entry)
        copied.setdefault("type", None)
        copied.setdefault("opened", None)
        copied.setdefault("verdict", None)
        copied.setdefault("confidence", None)
        copied.setdefault("checked", None)
        copied.setdefault("counter_source", None)
        ledger[cid] = copied

    header_cols: list[str] | None = None
    extra_keys = ("type", "opened", "verdict", "confidence", "checked", "counter_source")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = _split_md_row(line)
        if not cells:
            continue

        # Detect header row if present
        lowered = [c.lower() for c in cells]
        if header_cols is None and (
            "id" in lowered or "claim" in lowered or any(k in lowered for k in extra_keys)
        ):
            header_cols = lowered
            continue

        # Skip markdown separator rows like | --- | --- |
        if all(set(c) <= {"-", ":", " "} for c in cells if c):
            continue

        match = claims.ROW.match(line)
        if not match:
            continue
        cid = match.group(1)
        if cid not in ledger:
            ledger[cid] = {
                "id": cid,
                "type": None,
                "opened": None,
                "verdict": None,
                "confidence": None,
                "checked": None,
                "counter_source": None,
            }

        row_values: dict[str, str] = {}
        if header_cols and len(header_cols) >= len(cells):
            for idx, col_name in enumerate(header_cols):
                row_values[col_name] = cells[idx]
        else:
            # Positional fallback for 4 base columns + up to 6 optional ledger columns:
            # [id, sentence/claim, source, notes/link, type, opened, verdict, confidence, checked, counter_source]
            for idx, key in enumerate(extra_keys):
                col_idx = 4 + idx
                if col_idx < len(cells):
                    row_values[key] = cells[col_idx]

        if "type" in row_values:
            raw_type = _parse_optional_str(row_values.get("type"))
            ledger[cid]["type"] = raw_type.lower() if raw_type is not None else None
        if "opened" in row_values:
            ledger[cid]["opened"] = _parse_bool_or_none(row_values.get("opened"))
        if "verdict" in row_values:
            raw_verdict = _parse_optional_str(row_values.get("verdict"))
            ledger[cid]["verdict"] = raw_verdict.lower() if raw_verdict is not None else None
        if "confidence" in row_values:
            raw_conf = _parse_optional_str(row_values.get("confidence"))
            ledger[cid]["confidence"] = raw_conf.lower() if raw_conf is not None else None  # low / medium / high
        if "checked" in row_values:
            ledger[cid]["checked"] = _parse_optional_str(row_values.get("checked"))
        if "counter_source" in row_values:
            ledger[cid]["counter_source"] = _parse_optional_str(row_values.get("counter_source"))

    return ledger


def _extract_claim_text(entry: dict[str, Any]) -> str:
    for key in ("sentence", "claim", "text", "statement", "summary"):
        val = entry.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _extract_claim_source(entry: dict[str, Any]) -> str:
    for key in ("source", "link", "url", "notes", "evidence"):
        val = entry.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _has_url(entry: dict[str, Any]) -> bool:
    src = entry.get("source")
    return isinstance(src, str) and bool(claims.URL.search(src))


def _claim_kind_prefix(cid: str, entry: dict[str, Any]) -> str:
    """The claim-map LABEL (E/M/R/G/I); claim ids are C-01 style, so the id prefix says nothing."""
    label = entry.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip().upper()[0]
    return ""


def _normalize_number(token: str) -> str:
    cleaned = token.replace(",", "").strip()
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    return cleaned


def _extract_numbers(text: str) -> set[str]:
    return {_normalize_number(m.group(0)) for m in claims.NUMBER.finditer(text)}


def _content_words(text: str) -> set[str]:
    if story_lint is not None and hasattr(story_lint, "content_words"):
        return set(story_lint.content_words(text))
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in _FALLBACK_STOP and len(w) > 2}


def _overlap_score(text_a: str, text_b: str) -> float:
    """Share of the content words of ``text_a`` found in ``text_b`` (story_lint.overlap takes SETS)."""
    said, seen = _content_words(text_a), _content_words(text_b)
    if story_lint is not None and hasattr(story_lint, "overlap"):
        return float(story_lint.overlap(said, seen))
    return len(said & seen) / len(said) if said else 0.0


def _iter_script_lines(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract normalized script lines with `where`, `text`, `cites`, and `is_fact`."""
    results: list[dict[str, Any]] = []
    segments = doc.get("segments") or doc.get("sections") or []
    if not isinstance(segments, list):
        return results

    for seg_idx, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        seg_id = str(seg.get("id") or seg.get("seg_id") or f"seg{seg_idx}")
        seg_label = str(seg.get("label") or seg.get("kind") or seg.get("type") or "").lower()
        drama = seg.get("drama") if isinstance(seg.get("drama"), dict) else {}
        seg_is_fact = (
            seg_label == "fact" or bool(seg.get("is_fact")) or str(drama.get("claim_share") or "").lower() == "fact"
        )

        lines = seg.get("lines") or seg.get("sentences") or []
        if isinstance(lines, str):
            lines = [lines]

        for line_idx, line_obj in enumerate(lines):
            where = f"{seg_id}#{line_idx + 1}"  # PV-37 spelling, 1-based
            if isinstance(line_obj, str):
                text = line_obj
                cites = _CITE_ID_RE.findall(text)
                line_is_fact = seg_is_fact
            elif isinstance(line_obj, dict):
                text = str(line_obj.get("text") or line_obj.get("line") or line_obj.get("sentence") or "")
                raw_cites = line_obj.get("claims") or line_obj.get("cites") or line_obj.get("claim_ids")
                if isinstance(raw_cites, list):
                    cites = [str(c).strip() for c in raw_cites if str(c).strip()]
                elif isinstance(raw_cites, str) and raw_cites.strip():
                    cites = [c.strip() for c in raw_cites.split(",") if c.strip()]
                else:
                    cites = _CITE_ID_RE.findall(text)
                line_label = str(line_obj.get("label") or line_obj.get("kind") or "").lower()
                line_is_fact = seg_is_fact or line_label == "fact" or bool(line_obj.get("is_fact"))
                if "where" in line_obj and line_obj["where"]:
                    where = str(line_obj["where"])
            else:
                continue

            results.append({
                "where": where,
                "text": text,
                "cites": cites,
                "is_fact": line_is_fact,
            })

    return results


def ledger_check(
    doc: dict[str, Any],
    cmap: dict[str, dict[str, Any]],
    strict: bool = False,
    today: date | None = None,
    rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run PV-37 `claims.check(doc, cmap)` first, then evaluate rules CL-01..CL-08."""
    findings: list[dict[str, Any]] = list(claims.check(doc, cmap))
    pv37_flagged_wheres: set[str] = {
        str(f.get("where")) for f in findings if isinstance(f, dict) and f.get("where")
    }

    cfg = rules if rules is not None else _load_rules()
    raw_abs_words = cfg.get("absolute_words", DEFAULT_ABSOLUTE_WORDS)
    abs_words = {str(w).strip().lower() for w in raw_abs_words if str(w).strip()}
    abs_pattern = (
        re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(abs_words)) + r")\b", re.IGNORECASE)
        if abs_words
        else None
    )
    support_overlap_min = float(cfg.get("support_overlap_min", DEFAULT_SUPPORT_OVERLAP_MIN))
    cl07a_sev = str(cfg.get("cl07a_severity", "FAIL")).upper()
    ref_today = today if today is not None else date.today()

    # Claim-level checks (CL-02, CL-03, CL-04, CL-05, CL-06)
    for cid, entry in cmap.items():
        claim_text = _extract_claim_text(entry)
        claim_type = entry.get("type")
        opened = entry.get("opened")
        verdict = (entry.get("verdict") or "").strip().lower() if isinstance(entry.get("verdict"), str) else None
        checked_raw = entry.get("checked")
        counter_source = entry.get("counter_source")
        linked = _has_url(entry)

        # CL-02: missing type -> REVIEW (FAIL under strict); invalid type -> FAIL;
        # statistical claim with no number -> FAIL.
        if claim_type is None or str(claim_type).strip() == "":
            _finding(
                findings,
                "CL-02",
                cid,
                f"Claim {cid} is missing a claim type.",
                sev="FAIL" if strict else "REVIEW",
            )
        else:
            norm_type = str(claim_type).strip().lower()
            if norm_type not in VALID_TYPES:
                _finding(
                    findings,
                    "CL-02",
                    cid,
                    f"Claim {cid} has invalid type '{claim_type}'; expected one of {sorted(VALID_TYPES)}.",
                    sev="FAIL",
                )
            elif norm_type == "statistical" and not _extract_numbers(claim_text):
                _finding(
                    findings,
                    "CL-02",
                    cid,
                    f"Statistical claim {cid} contains no numeric value.",
                    sev="FAIL",
                )

        # CL-03: absolute word in sentence AND (not opened OR no source link) -> FAIL.
        abs_hit = abs_pattern.search(claim_text) if (abs_pattern is not None and claim_text) else None
        if abs_hit is not None:
            not_opened = opened is False or (strict and opened is None)
            if not_opened or not linked:
                _finding(
                    findings,
                    "CL-03",
                    cid,
                    f"{cid} says '{abs_hit.group(0).lower()}' but is not opened or has no link "
                    f"(opened={opened}, linked={linked}): OR-S12 blocks absolute and unverified claims.",
                    sev="FAIL",
                )

        # CL-04: opened missing -> REVIEW (FAIL under strict).
        if opened is None:
            _finding(
                findings,
                "CL-04",
                cid,
                f"Claim {cid} is missing 'opened' status.",
                sev="FAIL" if strict else "REVIEW",
            )

        # CL-05: a verdict outside the four allowed values -> FAIL.
        if verdict and verdict not in VALID_VERDICTS:
            _finding(findings, "CL-05", cid, f"Claim {cid} has invalid verdict '{verdict}'.", sev="FAIL")

        # CL-05: contradicted without counter_source -> FAIL.
        if verdict == "contradicted" and not (isinstance(counter_source, str) and counter_source.strip()):
            _finding(
                findings,
                "CL-05",
                cid,
                f"Claim {cid} is marked contradicted without a counter_source.",
                sev="FAIL",
            )

        # CL-06: checked date missing on a linked claim -> REVIEW; future date -> FAIL.
        if linked and not (isinstance(checked_raw, str) and checked_raw.strip()):
            _finding(
                findings,
                "CL-06",
                cid,
                f"Linked claim {cid} is missing a checked date.",
                sev="REVIEW",
            )
        elif isinstance(checked_raw, str) and checked_raw.strip():
            parsed_date = _parse_iso_date(checked_raw)
            if parsed_date is not None and parsed_date > ref_today:
                _finding(
                    findings,
                    "CL-06",
                    cid,
                    f"Claim {cid} has a future checked date ({parsed_date.isoformat()} > {ref_today.isoformat()}).",
                    sev="FAIL",
                )

    # Line-level checks (CL-01, CL-05 cited contradicted, CL-07a, CL-07b, CL-08)
    for line_info in _iter_script_lines(doc):
        where = line_info["where"]
        text = line_info["text"]
        cites: list[str] = line_info["cites"]
        is_fact: bool = line_info["is_fact"]

        # CL-01: line with year, percent, or currency amount and no claim id (skip PV-37 flagged lines).
        if not cites and where not in pv37_flagged_wheres:
            if _YEAR_RE.search(text) or _PERCENT_RE.search(text) or _CURRENCY_RE.search(text):
                _finding(
                    findings,
                    "CL-01",
                    where,
                    "Line contains a year, percentage, or currency figure without a claim citation.",
                    sev="REVIEW",
                )

        cited_entries: list[tuple[str, dict[str, Any]]] = [
            (cid, cmap[cid]) for cid in cites if cid in cmap
        ]
        if not cited_entries:
            continue

        # CL-05 (line-level): line citing a contradicted claim -> FAIL (never call claim "false").
        for cid, entry in cited_entries:
            verdict = (entry.get("verdict") or "").strip().lower() if isinstance(entry.get("verdict"), str) else ""
            if verdict == "contradicted":
                _finding(
                    findings,
                    "CL-05",
                    where,
                    f"Line cites {cid}, which is contradicted-with-source in the ledger.",
                    sev="FAIL",
                )

        # CL-08: I (invention) or G (guess) claim cited by a fact-labelled segment -> REVIEW.
        if is_fact:
            for cid, entry in cited_entries:
                prefix = _claim_kind_prefix(cid, entry)
                if prefix in ("I", "G"):
                    _finding(
                        findings,
                        "CL-08",
                        where,
                        f"Fact-labelled segment cites {prefix}-claim {cid} (unverified invention/guess).",
                        sev="REVIEW",
                    )

        # CL-07a: every number in line must occur in a cited claim's sentence, else FAIL/REVIEW.
        # Opinion and prediction claims are exempt from (a).
        line_numbers = _extract_numbers(text)
        if line_numbers:
            exempt_only = all(
                str(entry.get("type") or "").strip().lower() in ("opinion", "prediction")
                for _, entry in cited_entries
            )
            if not exempt_only:
                cited_numbers: set[str] = set()
                for _, entry in cited_entries:
                    cited_numbers.update(_extract_numbers(_extract_claim_text(entry)))
                missing_nums = sorted(line_numbers - cited_numbers)
                if missing_nums:
                    _finding(
                        findings,
                        "CL-07a",
                        where,
                        f"Line number(s) {missing_nums} do not appear in any cited claim sentence.",
                        sev=cl07a_sev,
                    )

        # CL-07b: content-word overlap of line vs best cited claim below support_overlap_min -> REVIEW.
        best_overlap = max(
            (_overlap_score(text, _extract_claim_text(entry)) for _, entry in cited_entries),
            default=0.0,
        )
        if best_overlap < support_overlap_min:
            _finding(
                findings,
                "CL-07b",
                where,
                f"Content-word overlap ({best_overlap:.2f}) with cited claim(s) is below {support_overlap_min:.2f}.",
                sev="REVIEW",
            )

    return findings


def ledger_report(
    cmap: dict[str, dict[str, Any]],
    doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate summary counts, not_opened claim IDs, and uncited claim IDs."""
    not_opened: list[str] = []
    verdict_counts: dict[str, int] = {
        "supported": 0,
        "unverified": 0,
        "contradicted-with-source": 0,
    }
    type_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}

    for cid, entry in cmap.items():
        lab = str(entry.get("label") or "?").strip()[:1].upper() or "?"
        label_counts[lab] = label_counts.get(lab, 0) + 1
        if entry.get("opened") is not True:
            not_opened.append(cid)

        raw_verdict = (entry.get("verdict") or "").strip().lower() if isinstance(entry.get("verdict"), str) else ""
        if raw_verdict == "supported":
            verdict_counts["supported"] += 1
        elif raw_verdict == "contradicted":
            verdict_counts["contradicted-with-source"] += 1
        else:
            verdict_counts["unverified"] += 1

        ctype = str(entry.get("type") or "untyped").strip().lower() or "untyped"
        type_counts[ctype] = type_counts.get(ctype, 0) + 1

    uncited: list[str] = []
    if doc is not None:
        cited_ids: set[str] = set()
        for line_info in _iter_script_lines(doc):
            cited_ids.update(line_info["cites"])
        uncited = [cid for cid in cmap if cid not in cited_ids]

    return {
        "total_claims": len(cmap),
        "opened_count": len(cmap) - len(not_opened),
        "not_opened_count": len(not_opened),
        "not_opened": not_opened,
        "uncited_count": len(uncited),
        "uncited": uncited,
        "verdicts": verdict_counts,
        "types": type_counts,
        "labels": label_counts,
    }


def main(argv: list[str] | None = None) -> int:
    """``python -m explainer_engine.scripting.claim_ledger <script.json> [--strict]``; 1 on a FAIL, 2 on an error."""
    parser = argparse.ArgumentParser(prog="claim_ledger", description="Evidence-ledger check of a script's claim map.")
    parser.add_argument("script", help="Path to the production script JSON (claim_map.md is read next to it)")
    parser.add_argument("--strict", action="store_true", help="Promote the strict REVIEW rules to FAIL")
    parser.add_argument("--map", default=None, help="Explicit claim_map.md (default: next to the script)")
    parser.add_argument("--rules", default=None, help="Path to claim_ledger_rules.json")
    parser.add_argument("--today", default=None, help="Override today's date (YYYY-MM-DD)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return 0 if code == 0 else 2

    try:
        script_path = Path(args.script)
        if not script_path.is_file():
            print(f"Error: script file not found: {script_path}", file=sys.stderr)
            return 2
        doc = json.loads(script_path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            print("Error: script JSON root must be an object", file=sys.stderr)
            return 2
        map_path = Path(args.map) if args.map else script_path.parent / "claim_map.md"
        if map_path.is_file():
            cmap = parse_ledger(map_path.read_text(encoding="utf-8"))
        else:
            cmap = claims.from_editorial(doc)
            if cmap is None:
                print(f"Error: no claim map at {map_path} and no editorial claims in the script", file=sys.stderr)
                return 2
            cmap = {k: dict(v, type=None, opened=None, verdict=None, confidence=None, checked=None,
                            counter_source=None) for k, v in cmap.items()}

        ref_today: date | None = None
        if args.today is not None:
            ref_today = _parse_iso_date(args.today)
            if ref_today is None:
                print(f"Error: invalid --today date: {args.today}", file=sys.stderr)
                return 2

        rules = _load_rules(args.rules) if args.rules else None
        findings = ledger_check(doc, cmap, strict=args.strict, today=ref_today, rules=rules)
        report = ledger_report(cmap, doc=doc)

        if args.as_json:
            print(json.dumps({"findings": findings, "report": report}, indent=2, ensure_ascii=False))
        else:
            for f in findings:
                print(f"[{f.get('severity', 'REVIEW')}] {f.get('rule', '')} ({f.get('where', '')}): {f.get('detail', '')}")
            print(
                f"Summary: total={report['total_claims']} opened={report['opened_count']} "
                f"not_opened={report['not_opened']} uncited={report['uncited']}"
            )

        has_fail = any(str(f.get("severity", "")).upper() == "FAIL" for f in findings)
        return 1 if has_fail else 0
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
