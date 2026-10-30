"""CR-16: no unit test writes into the real ``tools/runpod/`` (session files, notify log, incidents)."""
import pytest

from explainer_engine.cloud import runpod as R


@pytest.fixture(autouse=True)
def _isolated_runpod_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp_default")
    yield


@pytest.fixture
def real_dryrun():
    """Ask for this fixture to run the real ``dryrun.passed``: every other unit test treats the dry run (P1b, CR-18) as done, so the
    older tests of the create flow stay about what they test."""


@pytest.fixture(autouse=True)
def _dryrun_isolated(request, tmp_path, monkeypatch):
    from explainer_engine.cloud import dryrun as D
    monkeypatch.setattr(D, "DIR", tmp_path / "dryrun_default")
    if "real_dryrun" not in request.fixturenames:
        monkeypatch.setattr(D, "passed", lambda text, **kw: [])
    yield


@pytest.fixture(autouse=True)
def _job_speeds_isolated(tmp_path, monkeypatch):
    """P1c: ``runpod cost`` writes measured speed rows; a unit test never writes the committed config/job_speeds.json."""
    import shutil

    from explainer_engine.cloud import speeds as S
    copy = tmp_path / "job_speeds.json"
    shutil.copy(S.FILE, copy)
    monkeypatch.setattr(S, "FILE", copy)
    yield
