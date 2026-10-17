import hashlib
import json
from pathlib import Path

from explainer_engine.production.editorial_gate import check, contract_findings, review_findings


def valid_doc():
    return {
        "editorial": {
            "version": 1,
            "sources": [
                {"id": "S1", "url": "https://example.com/primary", "title": "Primary record", "publisher": "Archive A",
                 "published_at": "2026-01-01", "accessed_at": "2026-10-18", "grade": "A", "passage": "The recorded passage supporting claim C1."}
            ],
            "claims": [
                {"id": "C1", "text": "A sourced factual claim.", "type": "fact", "source_ids": ["S1"],
                 "confidence": "verified", "uncertainty": ""}
            ]
        },
        "segments": [{"id": "S01", "lines": [{"text": "A sourced factual claim.", "kind": "fact", "claims": ["C1"]}]}]
    }


def valid_review(script_path: Path):
    criteria = (
        "factual_reliability", "clarity", "story_coherence", "hook", "relevance", "originality",
        "spoken_naturalness", "visual_potential", "humour_fit", "pacing_potential", "source_coverage",
        "title_thumbnail_alignment", "shorts_potential"
    )
    return {
        "schema": "editorial_review/1",
        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "reviewer_role": "independent_critic",
        "independent": True,
        "scores": {name: {"score": 4, "evidence": f"Concrete script evidence for {name} is recorded here."} for name in criteria},
        "critical_blockers": [],
        "required_revisions": []
    }


def test_supported_script_and_hash_bound_review_pass(tmp_path):
    script = tmp_path / "production_script.json"
    review = tmp_path / "editorial_review.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    review.write_text(json.dumps(valid_review(script)), encoding="utf-8")
    assert contract_findings(valid_doc()) == []
    assert check(script, review) == []


def test_factual_line_without_claim_is_blocked():
    doc = valid_doc()
    doc["segments"][0]["lines"][0]["claims"] = []
    assert any(row["rule"] == "EG-09" for row in contract_findings(doc))


def test_fact_with_unverified_claim_is_blocked():
    doc = valid_doc()
    doc["editorial"]["claims"][0]["confidence"] = "unverified"
    assert any(row["rule"] == "EG-10" for row in contract_findings(doc))


def test_review_is_rejected_after_script_changes(tmp_path):
    script = tmp_path / "production_script.json"
    review = tmp_path / "editorial_review.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    review.write_text(json.dumps(valid_review(script)), encoding="utf-8")
    script.write_text(json.dumps(valid_doc() | {"edited": True}), encoding="utf-8")
    assert any(row["rule"] == "EG-13" for row in review_findings(script, review))


def test_critical_blocker_prevents_pass(tmp_path):
    script = tmp_path / "production_script.json"
    review = tmp_path / "editorial_review.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    report = valid_review(script)
    report["critical_blockers"] = ["The payoff is unsupported."]
    review.write_text(json.dumps(report), encoding="utf-8")
    assert any(row["rule"] == "EG-17" for row in review_findings(script, review))


def test_required_scores_are_enforced(tmp_path):
    script = tmp_path / "production_script.json"
    review = tmp_path / "editorial_review.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    report = valid_review(script)
    report["scores"]["source_coverage"]["score"] = 3
    report["script_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
    review.write_text(json.dumps(report), encoding="utf-8")
    assert any(row["rule"] == "EG-18" for row in review_findings(script, review))
