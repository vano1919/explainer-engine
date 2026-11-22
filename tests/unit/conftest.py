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


@pytest.fixture(autouse=True)
def _overnight_isolated(request, tmp_path, monkeypatch):
    """The overnight ledger (core/spend_caps.overnight_reserve) writes into a temp dir, never into the real jobs/overnight; the
    runner tests use fake spend-cap files without a night, so their calls are not counted there. The ceiling itself is tested
    with the ``real_overnight`` fixture (tests/unit/test_spend_caps_overnight.py)."""
    from explainer_engine.core import spend_caps as SC
    monkeypatch.setenv("EXPLAINER_OVERNIGHT_DIR", str(tmp_path / "overnight_default"))
    if "real_overnight" not in request.fixturenames:
        monkeypatch.setattr(SC, "overnight_reserve", lambda *a, **k: None)
        monkeypatch.setattr(SC, "overnight_settle", lambda *a, **k: None)
    yield


@pytest.fixture
def real_overnight():
    """Ask for this fixture to run the real overnight reserve and settle against the file's own night."""
