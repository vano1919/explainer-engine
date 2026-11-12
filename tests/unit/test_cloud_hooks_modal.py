"""The session money hooks know Modal (v4.3 final audit A7, D-131): a raw ``modal deploy``/``serve``, a ``modal run`` of
anything but a committed worker, or a paid entrypoint without the creator's GO is refused before Bash runs it; the session
start lists every Modal app that is not stopped and the stop hook refuses the first end of a turn while one is. No Modal CLI
or account is used: the app list is a fake runner."""
from __future__ import annotations

import json

import pytest

from explainer_engine.cloud import hooks as H

WAN = "explainer_engine/training/pods/wan/modal_wan_jobs.py"
BAKE = "explainer_engine/training/pods/bakeoff/modal_bakeoff.py"
GO = "cmsg_01AbC:" + "a1b2c3d4e5f6"


@pytest.mark.parametrize("cmd, why", [
    ("modal deploy explainer_engine/x.py", "leaves an app up"),
    ("cd /repo && modal serve app.py", "leaves an app up"),
    ("modal run /tmp/oneoff.py", "committed worker"),
    ("python -m modal run scratch.py::main", "committed worker"),
    (f"modal run --detach {WAN}::main --job s.json", "EE_MODAL_GO"),
    (f"EE_MODAL_GO=cmsg_1 modal run {WAN}::smoke --picture p.png", "sha256"),      # the Wan GO carries the plan's hash
    (f"modal run {WAN}::stage --plan p.json", "EE_MODAL_GO"),                    # A6: the stage-in bills CPU, it needs the GO
    ("modal run explainer_engine/cloud/modal_j5_smoke.py::main", "EE_MODAL_GO"),
    (f"modal run {BAKE}::check", "bake-off bills"),                               # its CPU check bills too
    (f"EE_MODAL_GO=cmsg_1 modal run {BAKE}::run --variant ltx_distilled", "bake-off bills"),
    (f"EE_MODAL_GO={GO} modal run {BAKE}::run --variant ltx_distilled", "another plan or worker"),   # A4: the GO binds the bytes
    (f"EE_MODAL_GO={GO} modal run {BAKE}::run_ltx_distilled --rid x", "only through its entrypoints"),  # A4: no direct call
    (f"EE_MODAL_GO={GO} modal run {BAKE}::stage_fn", "only through its entrypoints"),
    ("modal shell --gpu H100", "outside any plan"),
    ("modal launch jupyter --gpu H100", "outside any plan"),
    ("echo ok; `modal deploy x.py`", "leaves an app up"),
    ("bash <<'EOF'\nmodal deploy x.py\nEOF", "leaves an app up"),                  # a heredoc fed to a shell is a command
])
def test_raw_modal_launches_are_refused(cmd, why):
    assert why in (H.modal_refusal(cmd, env={}) or "")
    assert H.pre_bash({"tool_input": {"command": cmd}}) == 2


@pytest.mark.parametrize("cmd", [
    f"modal run {WAN}::check",                                                     # L1/L2: CPU, the entrypoint gates itself
    f"modal run {WAN}::weights",
    f"EE_MODAL_GO={GO} modal run --detach {WAN}::main --job s.json",
    "EE_MODAL_GO=cmsg_9 modal run explainer_engine/cloud/modal_j5_smoke.py",
    "modal app list --json", "modal app stop ap-123", "grep -rn 'modal run' docs", "git log -S 'modal deploy'",
    "cat > notes.md <<'EOF'\nrun it with: modal deploy x.py\nEOF",                 # a heredoc that only writes text is data
    "python3 - <<'EOF'\ns = '``modal serve``'\nEOF",
])
def test_committed_workers_with_their_gates_and_readers_pass(cmd):
    assert H.modal_refusal(cmd, env={}) is None


def _runner(rows, rc=0):
    return lambda argv: (rc, json.dumps(rows))


def test_session_start_lists_the_modal_apps_that_are_not_stopped(monkeypatch, capsys):
    monkeypatch.setattr(H, "_check", lambda: None)
    H.session_start(_runner([{"App ID": "ap-1", "Description": "ee-wan-jobs", "State": "ephemeral"},
                             {"App ID": "ap-2", "Description": "old", "State": "stopped"}]))
    out = capsys.readouterr().out
    assert "1 app(s) not stopped" in out and "ap-1 ee-wan-jobs is ephemeral" in out and "ap-2" not in out
    H.session_start(lambda argv: (_ for _ in ()).throw(TimeoutError()))       # a broken check never blocks
    assert "cannot look" in capsys.readouterr().out


def test_stop_refuses_the_first_end_of_a_turn_while_an_app_runs(monkeypatch, capsys):
    monkeypatch.setattr(H, "_stop_runpod", lambda: 0)
    live = _runner([{"App ID": "ap-1", "Description": "ee-wan-jobs", "State": "ephemeral"}])
    assert H.stop({}, live) == 2 and "ap-1" in capsys.readouterr().err
    assert H.stop({"stop_hook_active": True}, live) == 0                       # the turn after may end: no deadlock
    assert H.stop({}, _runner([{"App ID": "ap-1", "Description": "x", "State": "stopped"}])) == 0
    assert H.stop({}, _runner([], rc=1)) == 0                                    # cannot look: never blocks by itself


def test_the_bakeoff_go_binds_the_plan_and_the_worker_on_disk():
    from explainer_engine.training.pods.bakeoff import modal_bakeoff as B
    assert H.bakeoff_go_sha() == B.go_sha()
    go = "cmsg_01AbC:" + B.go_sha()[:12]
    for entry in ("check", "stage", "run --variant wan_ti2v_5b"):
        assert H.modal_refusal(f"EE_MODAL_GO={go} modal run {BAKE}::{entry}", env={}) is None
