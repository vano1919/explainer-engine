"""CR-16: no unit test writes into the real ``tools/runpod/`` (session files, notify log, incidents)."""
import pytest

from explainer_engine.cloud import runpod as R


@pytest.fixture(autouse=True)
def _isolated_runpod_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp_default")
    yield
