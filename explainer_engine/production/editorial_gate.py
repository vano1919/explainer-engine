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
# EG-18: the rubric gate of docs/SCRIPTING_SPEC.md section 5 on a reviewer's 1-5 scores. These are process thresholds on a
# person's judgement, not a measurement of the video, so they are engineering constants outside the BP registry (like the
# episode rulebook's process numbers); the spec is their one home and changes there first.
REQUIRED_MINIMUMS = {"factual_reliability": 4, "source_coverage": 4, "title_thumbnail_alignment": 4}
MIN_SCORE = 3  # no other criterion below this
MIN_MEAN = 3.8  # the mean of all criteria
CONTENT_KINDS = {"fact", "analysis", "speculation", "joke", "transition"}
CLAIM_TYPES = {"fact", "estimate", "interpretation", "allegation", "speculation"}
CONFIDENCE = {"verified", "corroborated", "single-source", "unverified"}

# The integrated production-coherence review (D-60): editorial_review/2 adds an `integrated` object that proves the one
# planned viewing experience was read across every production layer, with findings a machine can route and block on.
# A production_script/3 requires it (D-58 scripts are written as played scenes, so the review must read them as one);
# a /1 or /2 script keeps accepting editorial_review/1 unchanged. Contract: docs/SCRIPTING_SPEC.md section 5.2.
REVIEW_SCHEMAS = {"editorial_review/1", "editorial_review/2"}
SCENE_SCHEMA = "production_script/3"
INTEGRATED_LAYERS = ("story", "entrances", "dialogue", "visual", "performance", "audio", "timing")
ALWAYS_INSPECTED = {"story", "visual", "audio", "timing"}  # only people-layers may be not_applicable (no dialogue)
LAYER_STATUS = {"inspected", "not_applicable"}
FINDING_BASIS = {"data", "estimate", "instructions"}  # what the judgement rests on (never a claim to have seen a render)
FINDING_CONFIDENCE = {"high", "medium", "low"}
FINDING_SEVERITIES = {"FAIL", "REVIEW"}
FINDING_OWNERS = {"architect", "writer", "beats", "performer", "editor", "caster", "shorts", "research"}
FINDING_TEXT_KEYS = ("expected", "instructed", "conflict", "consequence", "fix")  # each concrete, never generic advice
MIN_EVIDENCE_CHARS = 12


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


def _script_ids(doc: dict) -> set[str]:
    """Every name a finding's reference may anchor on: segments, lines' speakers, shorts, cast, pictures, music, voice."""
    ids: set[str] = {"voice", "narrator"}
    for seg in doc.get("segments", []) if isinstance(doc.get("segments"), list) else []:
        if isinstance(seg, dict):
            ids.add(str(seg.get("id")))
            for sh in seg.get("shots", []) if isinstance(seg.get("shots"), list) else []:
                pic = sh.get("picture") if isinstance(sh, dict) else None
                ids.add(pic if isinstance(pic, str) else str((pic or {}).get("id")) if isinstance(pic, dict) else "")
    for sh in doc.get("shorts", []) if isinstance(doc.get("shorts"), list) else []:
        if isinstance(sh, dict):
            ids.add(str(sh.get("id")))
    ids |= set(doc.get("cast", {}) or {})
    ids |= set(doc.get("library", {}) or {})
    for m in doc.get("music", []) if isinstance(doc.get("music"), list) else []:
        if isinstance(m, dict):
            ids.add(str(m.get("track")))
    return {i for i in ids if i and i != "None"}


def integrated_findings(report: dict, doc: dict) -> list[dict]:
    """EG-20..EG-22 on an editorial_review/2's `integrated` object (D-60): every layer of the planned viewing experience
    inspected with evidence and an honest basis, findings concrete enough to route, and a blocking finding blocks."""
    out: list[dict] = []
    integ = report.get("integrated")
    if not isinstance(integ, dict):
        return [finding("EG-19", "integrated", "editorial_review/2 must carry the integrated production-coherence review "
                        "(integrated.layers and integrated.findings; docs/SCRIPTING_SPEC.md section 5.2)")]
    layers = integ.get("layers")
    if not isinstance(layers, dict):
        out.append(finding("EG-20", "integrated.layers", f"layers must map each of {list(INTEGRATED_LAYERS)} to its inspection"))
        layers = {}
    missing = sorted(set(INTEGRATED_LAYERS) - set(layers))
    extra = sorted(set(layers) - set(INTEGRATED_LAYERS))
    if missing:
        out.append(finding("EG-20", "integrated.layers", f"layers not reviewed: {missing}; every layer of the planned "
                           "viewing experience is inspected (or declared not_applicable with a reason)"))
    if extra:
        out.append(finding("EG-20", "integrated.layers", f"unknown layers: {extra}"))
    for name in INTEGRATED_LAYERS:
        layer = layers.get(name)
        if name in missing or not isinstance(layer, dict):
            if name not in missing:
                out.append(finding("EG-20", f"integrated.layers.{name}", "layer must be an object"))
            continue
        where = f"integrated.layers.{name}"
        status = layer.get("status")
        if status not in LAYER_STATUS:
            out.append(finding("EG-20", where, f"status must be one of {sorted(LAYER_STATUS)}"))
            continue
        if status == "not_applicable":
            if name in ALWAYS_INSPECTED:
                out.append(finding("EG-20", where, f"{name} is never not_applicable: every episode has a {name} layer"))
            elif not isinstance(layer.get("reason"), str) or len(layer["reason"].strip()) < MIN_EVIDENCE_CHARS:
                out.append(finding("EG-20", f"{where}.reason", "a not_applicable layer says why, concretely"))
            continue
        if not isinstance(layer.get("evidence"), str) or len(layer["evidence"].strip()) < MIN_EVIDENCE_CHARS:
            out.append(finding("EG-20", f"{where}.evidence", "an inspected layer cites what was read (segments, shots, "
                               "beats, cues) as evidence it was actually reviewed"))
        if layer.get("basis") not in FINDING_BASIS:
            out.append(finding("EG-20", f"{where}.basis", f"basis must be one of {sorted(FINDING_BASIS)}: say whether the "
                               "judgement rests on real data, an estimated read, or instructions for assets that do not exist yet"))
    found = integ.get("findings")
    if not isinstance(found, list):
        out.append(finding("EG-21", "integrated.findings", "findings must be an array (empty when the review found nothing)"))
        found = []
    ids = _script_ids(doc)
    seen_ids: set[str] = set()
    for i, item in enumerate(found):
        where = f"integrated.findings[{i}]"
        if not isinstance(item, dict):
            out.append(finding("EG-21", where, "finding must be an object"))
            continue
        fid = item.get("id")
        if not isinstance(fid, str) or not fid.strip():
            out.append(finding("EG-21", where, "finding id is required"))
        elif fid in seen_ids:
            out.append(finding("EG-21", where, f"duplicate finding id {fid!r}"))
        else:
            seen_ids.add(fid)
            where = f"integrated.findings.{fid}"
        f_layers = item.get("layers")
        if not isinstance(f_layers, list) or not f_layers or not set(f_layers) <= set(INTEGRATED_LAYERS):
            out.append(finding("EG-21", where, f"layers must name at least one of {list(INTEGRATED_LAYERS)}"))
        if item.get("severity") not in FINDING_SEVERITIES:
            out.append(finding("EG-21", where, "severity must be FAIL (blocks production) or REVIEW (the creator answers); "
                               "a taste note goes in integrated.notes, never in findings"))
        refs = item.get("refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r.strip() for r in refs):
            out.append(finding("EG-21", where, "refs must list the exact segment, line, shot, beat, hero or audio event"))
        elif ids and not any(any(x in r for x in ids) for r in refs):
            out.append(finding("EG-21", where, f"no ref names anything of this script ({refs}): generic advice is not a finding"))
        for key in FINDING_TEXT_KEYS:
            if not isinstance(item.get(key), str) or len(item[key].strip()) < MIN_EVIDENCE_CHARS:
                out.append(finding("EG-21", f"{where}.{key}", f"{key} must say it concretely (what the story intends, what "
                                   "the spec instructs, where they conflict, what the viewer gets, the smallest correction)"))
        if item.get("confidence") not in FINDING_CONFIDENCE:
            out.append(finding("EG-21", f"{where}.confidence", f"confidence must be one of {sorted(FINDING_CONFIDENCE)}"))
        if item.get("basis") not in FINDING_BASIS:
            out.append(finding("EG-21", f"{where}.basis", f"basis must be one of {sorted(FINDING_BASIS)}; never claim to have "
                               "seen a picture or heard a voice that only exists as an instruction"))
        if item.get("owner") not in FINDING_OWNERS:
            out.append(finding("EG-21", f"{where}.owner", f"owner must be the stage that owns the fields: {sorted(FINDING_OWNERS)}"))
        if item.get("severity") == "FAIL":
            out.append(finding("EG-22", where, f"unresolved blocking integrated finding ({', '.join(item.get('layers') or [])}): "
                               f"{str(item.get('conflict', ''))[:90]} -> fix at stage {item.get('owner')}, then re-review"))
        elif item.get("severity") == "REVIEW":
            out.append(finding("EG-22", where, f"integrated finding for the creator: {str(item.get('conflict', ''))[:90]}",
                               "REVIEW"))
    notes = integ.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
        out.append(finding("EG-21", "integrated.notes", "notes must be an array of strings (subjective observations that "
                           "block nothing)"))
    return out


def review_findings(script_path: Path | str, review_path: Path | str) -> list[dict]:
    path = Path(review_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [finding("EG-12", str(path), f"cannot read review JSON: {exc}")]
    if not isinstance(report, dict) or report.get("schema") not in REVIEW_SCHEMAS:
        return [finding("EG-12", str(path), f"review schema must be one of {sorted(REVIEW_SCHEMAS)}")]
    try:
        doc = json.loads(Path(script_path).read_text(encoding="utf-8"))
        doc = doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        doc = {}
    out = []
    if doc.get("schema") == SCENE_SCHEMA and report.get("schema") != "editorial_review/2":
        out.append(finding("EG-19", "schema", "a production_script/3 is reviewed as one planned viewing experience: the "
                           "review must be editorial_review/2 with its integrated section (D-60)"))
    if report.get("schema") == "editorial_review/2":
        out += integrated_findings(report, doc)
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
            if criterion not in REQUIRED_MINIMUMS and score < MIN_SCORE:
                out.append(finding("EG-18", criterion, f"score {score}/5 is below required {MIN_SCORE}/5"))
        mean = sum(values.values()) / len(values)
        if mean < MIN_MEAN:
            out.append(finding("EG-18", "mean", f"mean score {mean:.2f}/5 is below required {MIN_MEAN:.2f}/5"))
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
