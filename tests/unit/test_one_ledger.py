"""One ledger for pods and API calls (docs/CONTRACTS.md, CN-10): a RunPod reservation and a Gemini charge live in the same
episode ``run.json``, each stops at 80 % of its own cap, and a pod's billing settles over its reservation."""

from __future__ import annotations

import json

import pytest

from explainer_engine.core.ledger import CapReached, Run


@pytest.fixture
def caps_file(tmp_path, monkeypatch):
    p = tmp_path / "caps.json"
    p.write_text(json.dumps({"per_episode": {"runpod_usd": 10.0, "gemini_usd": 5.0}}), encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(p))
    return p


def test_pod_and_api_money_share_one_run_file(tmp_path, caps_file):
    run = Run.open(tmp_path / "run.json")
    run.reserve("runpod_usd", 2.0, item="pod:pending")
    run.rename_reservation("pod:pending", "pod:abc")
    run.reserve("gemini_usd", 0.5, item="pic_01")
    data = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert set(data["reserved"]) == {"pod:abc", "pic_01"} and data["spent"] == {"runpod_usd": 2.0, "gemini_usd": 0.5}
    run.settle("runpod_usd", "pod:abc", 1.25)  # the pod's real billing replaces its reservation
    assert run.spent("runpod_usd") == 1.25 and run.spent("gemini_usd") == 0.5


def test_each_service_stops_at_80_percent_of_its_own_cap(tmp_path, caps_file):
    run = Run.open(tmp_path / "run.json")
    run.reserve("runpod_usd", 8.0, item="pod:a")  # exactly 80 % of 10
    with pytest.raises(CapReached):
        run.reserve("runpod_usd", 0.01, item="pod:b")
    run.reserve("gemini_usd", 4.0, item="pic_a")  # 80 % of 5: the other service is not affected
    with pytest.raises(CapReached):
        run.reserve("gemini_usd", 0.01, item="pic_b")


def test_a_cap_above_the_creators_ceiling_is_refused(tmp_path, caps_file):
    from explainer_engine.core.spend_caps import OverCeiling
    with pytest.raises(OverCeiling):
        Run.open(tmp_path / "run.json", caps={"runpod_usd": 11.0})
