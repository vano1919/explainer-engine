"""Reusable before fast (OR-21, creator 2026-10-25): pod scripts and training configs live in the repo and pass the pod
lint; the rule is written where the sessions read it."""
from pathlib import Path

import yaml

from explainer_engine.cloud import runpod as R

ROOT = Path(__file__).resolve().parents[2]
PODS = ROOT / "explainer_engine" / "training" / "pods"


def test_the_rule_is_written_in_orchestration_and_claude_md():
    assert "| OR-21 | **Reusable before fast**" in (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    assert "OR-21" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def test_every_committed_pod_script_passes_the_pod_lint_and_stops_by_returning():
    scripts = sorted(PODS.glob("*.sh"))
    assert scripts
    for p in scripts:
        text = p.read_text(encoding="utf-8")
        assert R.lint_pod_script(text) == [], p.name
        assert "runpod create" in text and "sleep 3600" not in text, p.name  # the start command stops the pod


def test_every_training_config_has_its_pod_script():
    for cfg in PODS.glob("*.yaml"):
        assert cfg.with_suffix(".sh").exists(), cfg.name
        proc = yaml.safe_load(cfg.read_text(encoding="utf-8"))["config"]["process"][0]
        assert proc["network"]["linear"] <= 16 and proc["trigger_word"], cfg.name
