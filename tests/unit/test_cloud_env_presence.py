"""CR-19: the pre-pod secrets gate prints only present / MISSING, never a value, and fails when one is missing or blank."""
import re
from pathlib import Path

from explainer_engine.cloud import env_presence as S

ROOT = Path(__file__).resolve().parents[2]


def test_present_and_missing_are_told_apart_and_blank_is_missing():
    rows = S.check(("A", "B", "C", "D"), {"A": "x", "B": "", "C": "   \n", "E": "y"})
    assert rows == [("A", True), ("B", False), ("C", False), ("D", False)]


CANARY = "zq7x9kwj2486"     # none of its characters occurs anywhere in the legitimate output (checked below), so a single leaked character shows


def _pieces(text, n=4):
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def test_nothing_of_a_value_reaches_stdout_or_stderr_in_any_case(capsys):
    S.main(env={}), S.main(env={n: "v" for n in S.REQUIRED})                               # the legitimate vocabulary of the output
    legit = capsys.readouterr()
    assert not set(CANARY) & set(legit.out + legit.err), "pick a canary outside the output's alphabet"
    cases = [{"HF_TOKEN": CANARY}, {"HF_TOKEN": CANARY, "RUNPOD_API_KEY": "  " + CANARY + "  \n"},
             {"HF_TOKEN": "\n" + CANARY, "RUNPOD_API_KEY": "", "NTFY_TOPIC": "   "}, {"RUNPOD_API_KEY": CANARY * 3}, {n: CANARY for n in S.REQUIRED}]
    for env in cases:
        S.main(env=env)
        out = capsys.readouterr()
        seen = out.out + out.err
        assert not set(CANARY) & set(seen), (env, seen)                                    # not one character of it, so no prefix, tail or piece
        assert not (_pieces(CANARY) & _pieces(seen)), (env, seen)
        assert str(len(CANARY)) not in seen and "hf_" not in seen
        assert set(re.findall(r"^(\w+): (present|MISSING)$", out.out, re.M)) <= {(n, w) for n in S.REQUIRED for w in ("present", "MISSING")}
    S.main(["HF_TOKEN", "RUNPOD_API_KEY"], {"HF_TOKEN": CANARY})
    out = capsys.readouterr().out
    assert "HF_TOKEN: present" in out and "RUNPOD_API_KEY: MISSING" in out


def test_exit_is_zero_only_when_every_required_secret_is_there(capsys):
    assert S.main(env={n: "v" for n in S.REQUIRED}) == 0
    assert S.main(env={n: "v" for n in S.REQUIRED[1:]}) == 1                              # HF_TOKEN first in the list, missing
    assert "missing repository secret(s): HF_TOKEN" in capsys.readouterr().out
    assert S.REQUIRED[0] == "HF_TOKEN"


def test_the_workflow_maps_exactly_the_required_names_and_is_manual_only():
    text = (ROOT / ".github" / "workflows" / "presence_check.yml").read_text(encoding="utf-8")
    mapped = re.findall(r"^\s+(\w+): \$\{\{ secrets\.(\w+) \}\}\s*$", text, re.M)
    assert all(a == b for a, b in mapped) and [a for a, _ in mapped] == list(S.REQUIRED)
    assert text.index("env:") > text.index("steps:")                                       # the secrets are on the one step that needs them
    assert re.search(r"^on:\n  workflow_dispatch:\n", text, re.M) and "pull_request" not in text and "schedule" not in text
    assert "python -m explainer_engine.cloud.env_presence" in text


def test_the_watchdog_workflow_reads_the_same_secrets():
    text = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(encoding="utf-8")
    assert all(f"secrets.{n}" in text for n in S.REQUIRED)
