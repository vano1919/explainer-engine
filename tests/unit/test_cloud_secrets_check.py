"""CR-19: the pre-pod secrets gate prints only present / MISSING, never a value, and fails when one is missing or blank."""
import re
from pathlib import Path

from explainer_engine.cloud import secrets_check as S

ROOT = Path(__file__).resolve().parents[2]


def test_present_and_missing_are_told_apart_and_blank_is_missing():
    rows = S.check(("A", "B", "C", "D"), {"A": "x", "B": "", "C": "   \n", "E": "y"})
    assert rows == [("A", True), ("B", False), ("C", False), ("D", False)]


def test_the_report_never_contains_a_value_a_prefix_or_a_length(capsys):
    secret = "hf_SECRETVALUE0123456789"
    code = S.main(["HF_TOKEN", "RUNPOD_API_KEY"], {"HF_TOKEN": secret})
    out = capsys.readouterr().out
    assert code == 1 and "HF_TOKEN: present" in out and "RUNPOD_API_KEY: MISSING" in out
    assert "SECRETVALUE" not in out and "hf_" not in out and str(len(secret)) not in out


def test_exit_is_zero_only_when_every_required_secret_is_there(capsys):
    assert S.main(env={n: "v" for n in S.REQUIRED}) == 0
    assert S.main(env={n: "v" for n in S.REQUIRED[1:]}) == 1                              # HF_TOKEN first in the list, missing
    assert "missing repository secret(s): HF_TOKEN" in capsys.readouterr().out
    assert S.REQUIRED[0] == "HF_TOKEN"


def test_the_workflow_maps_exactly_the_required_names_and_is_manual_only():
    text = (ROOT / ".github" / "workflows" / "secrets_check.yml").read_text(encoding="utf-8")
    mapped = re.findall(r"^\s+(\w+): \$\{\{ secrets\.(\w+) \}\}\s*$", text, re.M)
    assert all(a == b for a, b in mapped) and [a for a, _ in mapped] == list(S.REQUIRED)
    assert re.search(r"^on:\n  workflow_dispatch:\n", text, re.M) and "pull_request" not in text and "schedule" not in text
    assert "python -m explainer_engine.cloud.secrets_check" in text


def test_the_watchdog_workflow_reads_the_same_secrets():
    text = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(encoding="utf-8")
    assert all(f"secrets.{n}" in text for n in S.REQUIRED)
