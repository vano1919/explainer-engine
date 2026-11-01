"""The sourced-rules registry (D-59, docs/SOURCED_RULES.md): integrity, the generated table, and the code that reads it."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_the_registry_is_consistent():
    assert SR.check() == []


def test_every_binding_rule_has_two_source_types_and_code():
    for r in SR.rules():
        if r["status"] == "binding":
            assert len(SR.source_types(r)) >= 2, r["id"]
            assert r["enforced_by"], r["id"]
        if r["status"] == "hypothesis":
            assert r.get("severity", "REVIEW") != "FAIL", r["id"]


def test_the_doc_table_matches_the_registry():
    text = SR.DOC.read_text(encoding="utf-8")
    block = SR.doc_block(text)
    assert block is not None, "docs/SOURCED_RULES.md lost its generated block markers"
    assert block.strip() == SR.render().strip(), "run: python -m explainer_engine.standards.sourced_rules write"


def test_every_bp_id_cited_in_code_or_claude_exists():
    ids = {r["id"] for r in SR.rules()}
    cited = set()
    for folder in (ROOT / "explainer_engine", ROOT / ".claude", ROOT / "docs"):
        for p in folder.rglob("*"):
            if p.suffix in {".py", ".md", ".json"} and p.name != "sourced_rules.json":
                cited |= set(re.findall(r"\bBP-\d{2,3}\b", p.read_text(encoding="utf-8", errors="ignore")))
    assert cited - ids == set(), f"undefined BP ids cited: {sorted(cited - ids)}"


def test_thresholds_are_read_not_copied():
    assert SR.T("BP-06", "max_words") == SR.rule("BP-06")["thresholds"]["max_words"]
    with pytest.raises(KeyError):
        SR.rule("BP-99")


def test_the_cli_check_and_render(tmp_path):
    out = subprocess.run([sys.executable, "-m", "explainer_engine.standards.sourced_rules", "check"], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
    out = subprocess.run([sys.executable, "-m", "explainer_engine.standards.sourced_rules", "render"], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.stdout.startswith("| ID | area |")


def test_the_check_catches_a_rule_without_sources(monkeypatch):
    bad = json.loads(json.dumps(SR.load()))
    bad["rules"][0]["sources"] = [bad["rules"][0]["sources"][0]]
    bad["rules"][0]["status"] = "binding"
    bad["rules"][0]["enforced_by"] = ["explainer_engine/nope.py"]
    monkeypatch.setattr(SR, "load", lambda: bad)
    found = SR.check()
    details = " ".join(f["detail"] for f in found)
    assert "source type" in details and "does not exist" in details


def test_an_unverified_source_does_not_count_as_a_source_type():
    rule = {"sources": [{"type": "A", "title": "x", "url": "http://x"},
                        {"type": "B", "title": "origin only", "url": "http://y", "verified": False}]}
    assert SR.source_types(rule) == {"A"}
    assert SR.source_types({"sources": [{"type": "B", "title": "b", "url": "http://z"}]}) == {"B"}
    unverified = [s for r in SR.rules() for s in r["sources"] if s["title"].startswith("Blueprint 2026-10 (unverified)")]
    assert unverified and all(s.get("verified") is False for s in unverified)
    assert not any("project-thread-abo4it" in s["url"] for r in SR.rules() for s in r["sources"])


def test_bp141_a_and_d_non_character_max_follows_the_d93_lane_mix():
    """D-93 (the creator, 2026-11-01): 30 % still + 10 % helper are non-character; with BP-109's lane tolerance a plan that meets
    the mix exactly passes profiles A and D."""
    from explainer_engine.standards import sourced_rules as SR
    lanes = SR.T("BP-109", "lane_share")
    want = lanes["still"] + lanes["helper"] + SR.T("BP-109", "lane_tolerance")
    profiles = SR.T("BP-141", "episode_structure_profiles")
    assert profiles["A"]["non_character_max"] == profiles["D"]["non_character_max"] == pytest.approx(want)


# --- BP-169..BP-172: the rhythm rows (Argon roadmap WP-R1, 2026-11-01) ---

def _schema(name):
    return json.loads((ROOT / "explainer_engine" / "schemas" / name).read_text(encoding="utf-8"))


def test_bp169_to_bp172_rhythm_rules_are_valid():
    import jsonschema
    ids = {r["id"] for r in SR.rules()}
    assert {"BP-169", "BP-170", "BP-171", "BP-172"} <= ids
    t = SR.rule("BP-169")["thresholds"]
    assert t["default_profile"] == "mrbeast_animated"
    prof = t["profiles"]["mrbeast_animated"]
    jsonschema.validate(prof, _schema("rhythm_profile.schema.json"))
    zones = prof["zones"]
    assert zones[0]["window_s"][0] == 0 and zones[-1]["window_s"][1] == t["episode_s"]
    for a, b in zip(zones, zones[1:]):
        assert a["window_s"][1] == b["window_s"][0], "zones must be contiguous"
    assert len(SR.source_types(SR.rule("BP-169"))) >= 2
    assert SR.rule("BP-169")["severity"] == "REVIEW"
    assert SR.rule("BP-170")["status"] == "house" and SR.rule("BP-170")["decided"]
    # one home: the still caps of BP-170 equal the zones' static holds in BP-169
    held = SR.T("BP-170", "static_still_max_s_by_zone")
    assert {z["id"]: z["static_still_max_s"] for z in zones} == held
    assert all(z["still_max_s"] <= SR.T("BP-109", "still_shot_max_s") for z in zones)


def test_bp169_rejects_missing_zone_coverage():
    import jsonschema
    prof = json.loads(json.dumps(SR.T("BP-169", "profiles")["mrbeast_animated"]))
    prof["zones"] = prof["zones"][:4]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(prof, _schema("rhythm_profile.schema.json"))
    prof = json.loads(json.dumps(SR.T("BP-169", "profiles")["mrbeast_animated"]))
    prof["zones"][0]["still_max_s"] = 6.0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(prof, _schema("rhythm_profile.schema.json"))


def test_dramatic_still_schema_rejects_small_dot_or_tiny_move():
    import jsonschema
    schema = _schema("dramatic_still.schema.json")
    good = {"kind": "cutout_relocation", "subject_layer": "hero", "from_box": [0.1, 0.4, 0.3, 0.9],
            "to_box": [0.6, 0.4, 0.8, 0.9], "relocation_distance_frac": 0.5, "subject_area_frac": 0.1, "at_s": 2.0}
    jsonschema.validate(good, schema)
    for key, bad in (("relocation_distance_frac", 0.05), ("subject_area_frac", 0.02)):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**good, key: bad}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"kind": "plate_swap", "at_s": 1.0}, schema)


def test_bp172_fast_verbs_are_lowercase_third_person_words():
    verbs = SR.T("BP-172", "fast_action_verbs")
    assert verbs and all(v == v.lower() and v.endswith("s") for v in verbs)
