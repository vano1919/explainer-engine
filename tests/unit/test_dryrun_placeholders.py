"""Audit 2026-11-01 (#7): a pod never starts on a pin that was never filled; the check reads the script and the job files it names."""
from pathlib import Path

from explainer_engine.cloud import dryrun as D

RUNPOD = Path(__file__).resolve().parents[2] / "explainer_engine" / "cloud" / "runpod.py"
P12 = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"


def test_a_placeholder_in_the_script_text_is_refused():
    assert D.placeholder_problems("echo ok\n") == []
    probs = D.placeholder_problems('printf %s PLACEHOLDER_SHA_P12B_PY "$JOB/p12b.py"')
    assert len(probs) == 1 and "PLACEHOLDER_SHA_P12B_PY" in probs[0]


def test_a_placeholder_in_a_job_file_the_script_names_is_refused_and_an_unnamed_file_is_not(tmp_path):
    (tmp_path / "job.json").write_text('{"sha256": "PLACEHOLDER_SHA", "voice_id": "PLACEHOLDER"}', encoding="utf-8")
    (tmp_path / "other.json").write_text('{"x": "PLACEHOLDER"}', encoding="utf-8")
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    script = "fetch job.json clean.py\n"
    probs = D.placeholder_problems(script, tmp_path)
    assert [p.split(":")[0] for p in probs] == ["job.json", "job.json"] and all("PLACEHOLDER" in p for p in probs)
    (tmp_path / "job.json").write_text('{"sha256": "ab"}', encoding="utf-8")
    assert D.placeholder_problems(script, tmp_path) == []


def test_runpod_create_asks_for_it_before_any_money():
    t = RUNPOD.read_text(encoding="utf-8")
    assert "dryrun.placeholder_problems(script, Path(script_file).parent)" in t and 'f"placeholder: {w}"' in t


def test_the_p12_pod_is_refused_until_its_pins_are_filled():
    """True today (WP-1e fills them); when it fails the pins are filled and this test is deleted with the xfail of test_p12b_pod_script."""
    script = (P12 / "p12b.sh").read_text(encoding="utf-8")
    probs = D.placeholder_problems(script, P12)
    assert any(p.startswith("script: PLACEHOLDER_SHA_P12B_PY") for p in probs) and any(p.startswith("p12b.json:") for p in probs)
