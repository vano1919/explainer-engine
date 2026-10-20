from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CRITERIA = (
    "factual_reliability", "clarity", "story_coherence", "hook", "relevance", "originality",
    "spoken_naturalness", "visual_potential", "humour_fit", "pacing_potential", "source_coverage",
    "title_thumbnail_alignment", "shorts_potential",
)
REQUIRED_MINIMUMS = {"factual_reliability": 4, "source_coverage": 4, "title_thumbnail_alignment": 4}
CONTENT_KINDS = {"fact", "analysis", "speculation", "joke", "transition"}
CLAIM_TYPES = {"fact", "estimate", "interpretation", "allegation", "speculation"}
CONFIDENCE = {"verified", "corroborated", "single-source", "unverified"}


def finding(rule: str, where: str, detail: str, severity: str = "FAIL") -> dict:
    return {"rule": rule, "where": where, "detail": detail, "severity": severity}


def script_hash(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract_findings(doc: dict) -> list[dict]:
    out = []
    editorial = doc.get("editorial")
    if not isinstance(editorial, dict) or editorial.get("version") != 1:
        return [finding("EG-01", "editorial", "missing editorial.version=1 source and claim contract")]
    sources, claims = editorial.get("sources"), editorial.get("claims")
    if not isinstance(sources, list) or not sources:
        out.append(finding("EG-02", "editorial.sources", "at least one source is required"))
        sources = []
    if not isinstance(claims, list) or not claims:
        out.append(finding("EG-03", "editorial.claims", "at least one claim is required"))
        claims = []

    source_by_id = {}
    for i, source in enumerate(sources):
        where = f"editorial.sources[{i}]"
        if not isinstance(source, dict):
            out.append(finding("EG-04", where, "source must be an object"))
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid.strip():
            out.append(finding("EG-04", where, "source id is required"))
            continue
        if sid in source_by_id:
            out.append(finding("EG-04", where, f"duplicate source id {sid!r}"))
        source_by_id[sid] = source
        for key in ("url", "title", "publisher", "accessed_at", "grade", "passage"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                out.append(finding("EG-04", f"{where}.{key}", f"{key} must be a non-empty string"))
        published = source.get("published_at", "__missing__")
        if published == "__missing__":
            out.append(finding("EG-04", f"{where}.published_at", "published_at is required; use null when unknown"))
        elif published is not None and (not isinstance(published, str) or not published.strip()):
            out.append(finding("EG-04", f"{where}.published_at", "published_at must be a non-empty string or null"))
        if not str(source.get("url", "")).startswith(("https://", "http://")):
            out.append(finding("EG-04", f"{where}.url", "source URL must use HTTP or HTTPS"))
        if not isinstance(source.get("grade"), str) or source.get("grade") not in {"A", "B", "C", "D"}:
            out.append(finding("EG-04", f"{where}.grade", "source grade must be A, B, C or D"))
        if source.get("grade") == "D":
            out.append(finding("EG-05", where, "grade-D material is unverified; do not rely on it alone", "REVIEW"))

    claim_by_id = {}
    claim_evidence_supported = {}
    for i, claim in enumerate(claims):
        where = f"editorial.claims[{i}]"
        if not isinstance(claim, dict):
            out.append(finding("EG-06", where, "claim must be an object"))
            continue
        cid = claim.get("id")
        if not isinstance(cid, str) or not cid.strip():
            out.append(finding("EG-06", where, "claim id is required"))
            continue
        if cid in claim_by_id:
            out.append(finding("EG-06", where, f"duplicate claim id {cid!r}"))
        claim_by_id[cid] = claim
        for key in ("text", "type", "source_ids", "confidence", "uncertainty"):
            if key not in claim:
                out.append(finding("EG-06", f"{where}.{key}", f"{key} is required"))
        if not isinstance(claim.get("type"), str) or claim.get("type") not in CLAIM_TYPES:
            out.append(finding("EG-06", f"{where}.type", f"type must be one of {sorted(CLAIM_TYPES)}"))
        if not isinstance(claim.get("confidence"), str) or claim.get("confidence") not in CONFIDENCE:
            out.append(finding("EG-06", f"{where}.confidence", "invalid confidence label"))
        if not isinstance(claim.get("text"), str) or not claim.get("text", "").strip():
            out.append(finding("EG-06", f"{where}.text", "claim text is required"))
        if not isinstance(claim.get("uncertainty"), str):
            out.append(finding("EG-06", f"{where}.uncertainty", "uncertainty must be a string"))
        source_ids = claim.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            out.append(finding("EG-07", where, "claim must reference at least one source"))
            continue
        invalid_source_ids = [sid for sid in source_ids if not isinstance(sid, str) or not sid.strip()]
        if invalid_source_ids:
            out.append(finding("EG-07", where, "source IDs must be non-empty strings"))
        source_ids = [sid for sid in source_ids if isinstance(sid, str) and sid.strip()]
        missing = [sid for sid in source_ids if sid not in source_by_id]
        if missing:
            out.append(finding("EG-07", where, f"unknown source IDs: {missing}"))
        used_sources = [source_by_id[sid] for sid in source_ids if sid in source_by_id]
        primary = any(s.get("grade") == "A" for s in used_sources)
        secondary_publishers = {
            str(s.get("publisher", "")).strip().casefold()
            for s in used_sources if s.get("grade") in {"B", "C"} and str(s.get("publisher", "")).strip()
        }
        claim_evidence_supported[cid] = primary or len(secondary_publishers) >= 2
        if claim.get("type") != "speculation" and not claim_evidence_supported[cid]:
            out.append(finding("EG-10", where, f"claim {cid} needs one grade-A source or two independent grade-B/C publishers"))
        if claim.get("type") == "fact" and claim.get("confidence") == "unverified":
            out.append(finding("EG-10", where, f"claim {cid} cannot be classified as a fact while unverified"))

    used_claims = set()
    for si, segment in enumerate(doc.get("segments", [])):
        if not isinstance(segment, dict):
            out.append(finding("EG-08", f"segments[{si}]", "segment must be an object"))
            continue
        for li, line in enumerate(segment.get("lines", [])):
            where = f"{segment.get('id', f'S{si + 1:02d}')}#L{li + 1:02d}"
            if not isinstance(line, dict):
                out.append(finding("EG-08", where, "narration line must be an object"))
                continue
            kind = line.get("kind")
            if not isinstance(kind, str) or kind not in CONTENT_KINDS:
                out.append(finding("EG-08", where, f"line kind must be one of {sorted(CONTENT_KINDS)}"))
                continue
            ids = line.get("claims", [])
            if not isinstance(ids, list):
                out.append(finding("EG-09", where, "claims must be an array"))
                continue
            if kind in {"fact", "analysis", "speculation"} and not ids:
                out.append(finding("EG-09", where, f"{kind} lines must reference claim IDs"))
            for cid in ids:
                if not isinstance(cid, str) or not cid.strip():
                    out.append(finding("EG-09", where, "claim IDs must be non-empty strings"))
                    continue
                if cid not in claim_by_id:
                    out.append(finding("EG-09", where, f"unknown claim ID {cid!r}"))
                    continue
                used_claims.add(cid)
                claim = claim_by_id[cid]
                if kind == "fact":
                    if claim.get("type") in {"speculation", "allegation"}:
                        out.append(finding("EG-10", where, f"fact line cannot rely on a {claim.get('type')} claim {cid}"))
                    if claim.get("confidence") == "unverified":
                        out.append(finding("EG-10", where, f"fact line cannot present unverified claim {cid} as fact"))
                    if not claim_evidence_supported.get(cid, False):
                        out.append(finding("EG-10", where, f"claim {cid} needs one grade-A source or two independent grade-B/C publishers"))
    for cid, claim in claim_by_id.items():
        if cid not in used_claims:
            out.append(finding("EG-11", f"editorial.claims.{cid}", "claim is unused by every narration line", "REVIEW"))
    if not doc.get("segments"):
        out.append(finding("EG-08", "segments", "script must contain narration segments"))
    return out


def review_findings(script_path: Path | str, review_path: Path | str) -> list[dict]:
    path = Path(review_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("EG-12", str(path), f"cannot read review JSON: {exc}")]
    if not isinstance(report, dict) or report.get("schema") != "editorial_review/1":
        return [finding("EG-12", str(path), "review schema must be editorial_review/1")]
    out = []
    if report.get("script_sha256") != script_hash(script_path):
        out.append(finding("EG-13", "script_sha256", "review is stale or belongs to a different script; review the exact current file"))
    if report.get("reviewer_role") != "independent_critic" or report.get("independent") is not True:
        out.append(finding("EG-14", "reviewer", "review must be marked as an independent_critic review"))
    scores = report.get("scores")
    if not isinstance(scores, dict):
        return out + [finding("EG-15", "scores", "review scores must be an object")]
    missing, extra = sorted(set(CRITERIA) - set(scores)), sorted(set(scores) - set(CRITERIA))
    if missing:
        out.append(finding("EG-15", "scores", f"missing rubric criteria: {missing}"))
    if extra:
        out.append(finding("EG-15", "scores", f"unknown rubric criteria: {extra}"))
    values = {}
    for key in CRITERIA:
        item = scores.get(key)
        if not isinstance(item, dict):
            out.append(finding("EG-16", f"scores.{key}", "score must be an object with score and evidence"))
            continue
        score, evidence = item.get("score"), item.get("evidence")
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            out.append(finding("EG-16", f"scores.{key}.score", "score must be an integer from 1 to 5"))
        else:
            values[key] = score
        if not isinstance(evidence, str) or len(evidence.strip()) < 12:
            out.append(finding("EG-16", f"scores.{key}.evidence", "evidence must cite a concrete script location or passage"))
    blockers, revisions = report.get("critical_blockers"), report.get("required_revisions")
    if not isinstance(blockers, list) or blockers:
        out.append(finding("EG-17", "critical_blockers", "critical blockers must be an empty array"))
    if not isinstance(revisions, list) or revisions:
        out.append(finding("EG-17", "required_revisions", "required revisions must be an empty array; revise and re-review the script"))
    if len(values) == len(CRITERIA):
        for criterion, minimum in REQUIRED_MINIMUMS.items():
            if values[criterion] < minimum:
                out.append(finding("EG-18", criterion, f"score {values[criterion]}/5 is below required {minimum}/5"))
        for criterion, score in values.items():
            if criterion not in REQUIRED_MINIMUMS and score < 3:
                out.append(finding("EG-18", criterion, f"score {score}/5 is below required 3/5"))
        mean = sum(values.values()) / len(values)
        if mean < 3.8:
            out.append(finding("EG-18", "mean", f"mean score {mean:.2f}/5 is below required 3.80/5"))
    return out


def check(script_path: Path | str, review_path: Path | str) -> list[dict]:
    path = Path(script_path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("EG-01", str(path), f"cannot read production script JSON: {exc}")]
    return contract_findings(doc) + review_findings(path, review_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate source/claim coverage and independent script review.")
    parser.add_argument("script", help="production_script.json")
    parser.add_argument("--review", required=True, help="editorial_review.json bound to the script SHA-256")
    args = parser.parse_args(argv)
    findings = check(args.script, args.review)
    for item in findings:
        print(f"{item['severity']:6} {item['rule']:6} {item['where']}: {item['detail']}")
    fails = [item for item in findings if item["severity"] == "FAIL"]
    reviews = [item for item in findings if item["severity"] == "REVIEW"]
    if fails:
        print(f"BLOCKED: {len(fails)} FAIL, {len(reviews)} REVIEW")
        return 1
    if reviews:
        print(f"REVIEW REQUIRED: {len(reviews)} review item(s)")
        return 2
    print("PASS: source/claim contract and independent review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
