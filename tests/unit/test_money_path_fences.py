"""The four doors around the money layer (plan_v2 T1): retired launchers, library create, paid BFL without a ledger, approvals
that do not bind to their artifact. No network, no pod, no money."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_cloud_stop_paths import BEAT, env  # noqa: F401 - the create tests' fixture
from test_runpod import NEW_SH, live_ok, script_pod

from explainer_engine.cloud import hooks, pins, runpod as rp
from explainer_engine.core.ledger import Run

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


# --- N-01: cloud/runpod.py, --script required, the image pin on every creation, create() only sends a preflight-stamped body -----

class NoNetwork:
    def __getattr__(self, name):
        raise AssertionError(f"network touched: {name}")


def _script_body(**kw):
    return rp.create_body("ee-x-until-9999999999", "cheap", volume=0, image=kw.pop("image", pins.image_ref(pins.DEFAULT_IMAGE)),
                          script_url="https://huggingface.co/x/pod.sh", heartbeat=BEAT, max_usd=0.5, **kw)


def _preflight(api, body, script=NEW_SH):
    return rp.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="cheap", now=10**6, script=script, heartbeat=BEAT, pod_key=True,
                               body=body)


def test_create_refuses_an_unstamped_body_before_any_network():
    with pytest.raises(rp.RunPodError, match="preflight_create"):
        rp.create(NoNetwork(), _script_body(), max_price=0.95)


def test_preflight_stamps_exactly_the_body_and_create_refuses_it_once_changed(env):
    fake, api, tmp = env
    body = _script_body()
    assert _preflight(api, body) == [] and body[rp.PREFLIGHT_KEY] == rp.preflight_stamp(body)
    body["gpu"]["id"] = "NVIDIA H100 80GB HBM3"  # changed after the preflight
    with pytest.raises(rp.RunPodError, match="preflight_create"):
        rp.create(NoNetwork(), body, max_price=0.95)
    body = _script_body()
    _preflight(api, body)
    body["image"] = "ghcr.io/vano1919/tmr-pod:latest"
    with pytest.raises(rp.RunPodError, match="preflight_create"):
        rp.create(NoNetwork(), body, max_price=0.95)
    assert not fake.pods


def test_preflight_with_a_body_refuses_no_script_an_unpinned_image_and_a_boot_pod(env):
    fake, api, tmp = env
    body = _script_body()
    why = _preflight(api, body, script=None)
    assert any("OR-21" in w for w in why) and rp.PREFLIGHT_KEY not in body
    body = _script_body(image="ghcr.io/vano1919/tmr-pod:latest")
    why = _preflight(api, body)
    assert any("cloud_pins.json" in w for w in why) and rp.PREFLIGHT_KEY not in body
    boot = rp.create_body("ee-x-until-9999999999", "cheap", volume=0, image=pins.image_ref(pins.DEFAULT_IMAGE), boot="cloud/x.json")
    why = _preflight(api, boot)
    assert any("pod_wrapper.sh" in w for w in why) and rp.PREFLIGHT_KEY not in boot  # the TMR boot pod can never be sent
    with pytest.raises(rp.RunPodError, match="preflight_create"):
        rp.create(NoNetwork(), boot, max_price=0.95)


@pytest.mark.parametrize("argv", [
    ["create", "--ledger", "/tmp/x", "--gpu", "big"],
    ["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", "/tmp/x", "--boot", "cloud/x.json"],
    ["create", "--yes", "--max-usd", "0.07", "--max-hours", "0.3", "--vram", "24", "--cloud", "COMMUNITY", "--ledger", "/tmp/x"],
])
def test_cli_create_without_script_refuses_before_any_call(argv):
    with pytest.raises(SystemExit, match="OR-21"):
        rp.main(argv, api=NoNetwork())


def test_cli_create_with_script_sends_one_body_without_the_stamp(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    ledger = tmp / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    posted = []
    orig = fake._handle

    def spy(method, path, body):
        if method == "POST" and path.startswith("/pods"):
            posted.append(json.loads(body))
        return orig(method, path, body)
    fake._handle = spy
    rp.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(ledger), *script_pod(tmp)], api=api, live=live_ok())
    assert len(posted) == 1 and rp.PREFLIGHT_KEY not in posted[0] and posted[0]["cmd"] == rp.script_cmd()
    assert "@sha256:" in posted[0]["image"] and len(fake.pods) == 1
