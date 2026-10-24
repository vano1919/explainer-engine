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
