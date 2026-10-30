"""The four doors around the money layer (plan_v2 T1): retired launchers, library create, paid BFL without a ledger, approvals
that do not bind to their artifact. No network, no pod, no money."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from explainer_engine.cloud import hooks

ROOT = Path(__file__).resolve().parents[2]

# --- CP-01: the retired launchers never run; the hook refuses them and a library create outside the CLI --------------------------

LAUNCHERS = ["explainer_engine/aivideo/pod/launch.py", "explainer_engine/aivideo/pod/launch_clips.py"]


@pytest.mark.parametrize("rel", LAUNCHERS)
def test_retired_launcher_exits_before_any_pod_client(rel):
    txt = (ROOT / rel).read_text(encoding="utf-8")
    guard = txt.index('raise SystemExit("RETIRED by D-80')
    assert guard < txt.index("rp.Api(") and guard < txt.index("rp.create(")
    env = {**os.environ, "RUNPOD_API_KEY": "", "HF_TOKEN": ""}
    r = subprocess.run([sys.executable, str(ROOT / rel)], capture_output=True, text=True, env=env, timeout=60, cwd=ROOT)
    assert r.returncode != 0 and "RETIRED by D-80" in (r.stdout + r.stderr)


@pytest.mark.parametrize("cmd", [
    "python explainer_engine/aivideo/pod/launch.py",
    "python explainer_engine/aivideo/pod/launch_clips.py --dry",
    "python -m explainer_engine.aivideo.pod.launch",
    "python3 explainer_engine\\aivideo\\pod\\launch_clips.py",
    'python -c "from explainer_engine.cloud import runpod as rp; rp.create(api, body)"',
    'python -c "import explainer_engine.cloud.runpod as runpod; runpod.create(a, b, max_price=0.8)"',
    "python3 - <<'EOF'\nfrom explainer_engine.cloud import runpod as rp\nrp.create(rp.Api(), body)\nEOF",
])
def test_pre_bash_refuses_retired_launchers_and_library_create(cmd):
    assert hooks.pre_bash({"tool_input": {"command": cmd}}) == 2, cmd


@pytest.mark.parametrize("cmd", [
    "cat explainer_engine/aivideo/pod/launch.py",
    'grep -n "rp.create(" explainer_engine/cloud/runpod.py',
    "python -m explainer_engine.cloud.runpod check",
    "python -m explainer_engine.cloud.runpod create --yes --max-usd 0.5",
    "python -m pytest -q tests/unit/test_runpod.py",
    "python -m pytest -q tests/unit/test_aivideo_shotplan.py",
])
def test_pre_bash_still_allows_readers_and_the_cli(cmd):
    assert hooks.pre_bash({"tool_input": {"command": cmd}}) == 0, cmd
