"""Regression tests for Workstreams I (pyproject), J (portable .agents/skills), and K (Golden Prompt Evaluation)."""
from __future__ import annotations

import tomllib
from pathlib import Path

from explainer_engine.governance import agent_skills_lint as ASL
from explainer_engine.qa import prompt_eval as PE

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_toml_valid_and_configures_ruff_pyright_pytest_timeout():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "explainer-engine"
    assert data["tool"]["pytest"]["ini_options"]["timeout"] == 120
    assert "ruff" in data["tool"]
    assert "basedpyright" in data["tool"]


def test_portable_agent_skills_pass_lint_validator():
    res = ASL.validate_all_skills()
    assert res["ok"] is True, res["errors"]
    assert len(res["skills"]) >= 5
    for expected in (
        "explainer-architecture",
        "multimodal-qa-review",
        "spending-and-approvals",
        "prompt-evaluation",
        "security-and-workflows",
    ):
        assert expected in res["skills"]


def test_agent_skills_lint_rejects_bad_frontmatter_and_secrets(tmp_path: Path):
    bad = tmp_path / "broken-skill"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\nname: wrong-name\ndescription: short\n---\nAIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n", encoding="utf-8")
    errs = ASL.validate_skill_file(bad / "SKILL.md")
    assert any("does not match directory" in e for e in errs)
    assert any("forbidden secret" in e for e in errs)


def test_prompt_inventory_exists_and_golden_dataset_passes_offline_eval():
    inv = (REPO_ROOT / "docs" / "architecture" / "PROMPT_INVENTORY.md").read_text(encoding="utf-8")
    assert "PERCEPTUAL_QA_V2" in inv
    assert "LTX_MOTION_PROMPT" in inv

    ds_path = REPO_ROOT / "tests" / "fixtures" / "prompts" / "golden_dataset.json"
    report = PE.evaluate_golden_dataset(ds_path)
    assert report["ok"] is True, report["results"]
    assert report["total"] >= 6
    assert report["matched"] == report["total"]
