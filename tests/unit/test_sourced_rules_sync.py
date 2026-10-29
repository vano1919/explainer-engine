"""Code and registry agree (D-59, CN-12): every module that reads a threshold with ``T("BP-xx", "key")`` is listed in that rule's
``enforced_by``, and the key exists. A threshold read by an unlisted module is a rule the registry does not know is enforced."""

from __future__ import annotations

from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_every_reader_of_a_threshold_is_listed_in_enforced_by():
    enforced = {r["id"]: {e.split(":")[0] for e in r["enforced_by"]} for r in SR.rules()}
    missing = []
    for p in sorted((ROOT / "explainer_engine").rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if rel == "explainer_engine/standards/sourced_rules.py":
            continue
        for rid, _key, line in SR.threshold_reads(p.read_text(encoding="utf-8")):
            if rel not in enforced.get(rid, set()):
                missing.append(f"{rel}:{line} reads {rid} but is not in its enforced_by")
    assert missing == [], "add the module to the rule's enforced_by in standards/sourced_rules.json:\n" + "\n".join(missing)


def test_every_key_read_exists_in_the_rule():
    bad = []
    for p in sorted((ROOT / "explainer_engine").rglob("*.py")):
        for rid, key, line in SR.threshold_reads(p.read_text(encoding="utf-8")):
            if key not in SR.rule(rid)["thresholds"]:
                bad.append(f"{p.relative_to(ROOT).as_posix()}:{line} {rid}.{key}")
    assert bad == []


def test_the_detector_sees_a_reader_and_a_missing_key():
    src = 'from explainer_engine.standards import sourced_rules as SR\nX = SR.T("BP-01", "wpm_target")\nY = T("BP-02", "nope")\n'
    assert [(r, k) for r, k, _ in SR.threshold_reads(src)] == [("BP-01", "wpm_target"), ("BP-02", "nope")]
