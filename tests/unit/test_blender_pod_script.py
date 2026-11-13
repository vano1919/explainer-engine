"""ICW-04 (OR-21, OR-33, VT-01/02): the Blender render pod script passes the pod lint and the free dry-run rules, installs only the
pinned archive, ends with the vault check, and cannot start before the DRY gate fills its code-bundle pin. The CI smoke workflow
is the roadmap's (ubuntu-24.04, the pinned archive by sha256, Workbench 8 frames at 320x180, 15-minute cap). No network, no pod."""
import hashlib
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from explainer_engine.cloud import dryrun as D, pins, runpod as R

ROOT = Path(__file__).resolve().parents[2]
PODS = ROOT / "explainer_engine" / "training" / "pods"
SH = (PODS / "blender_render.sh").read_text(encoding="utf-8")
WF = ROOT / ".github" / "workflows" / "blender-smoke.yml"


def test_the_pod_script_passes_the_lint_and_the_static_dryrun_rules():
    assert subprocess.run(["bash", "-n", str(PODS / "blender_render.sh")]).returncode == 0
    assert R.is_wrapper_script(SH) and R.lint_pod_script(SH) == [] and D.static_problems(SH, pins.load()) == []
    assert D.needs_problems(SH) == []
    assert R.heartbeat_of_script(SH) == "datasets/vano1919/tmr-artifacts:runs/blender_render/beat.txt"
    assert R.stall_minutes_of_script(SH) == 20
    assert "runpod create" in SH and "sleep 3600" not in SH          # test_reusable_first's OR-21 rule for top-level pod scripts


def test_the_pod_installs_the_pinned_blender_renders_through_the_adapter_and_ends_with_the_vault_check():
    code = [ln for ln in SH.splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(code)
    assert "explainer_engine.blender.project install" in body and "--device gpu" in body
    assert "explainer_engine.training.pods.blender_render render" in body
    check = [ln for ln in code if "explainer_engine.vault check-uploaded" in ln]
    assert check and "|| true" not in check[0] and "exit 5" in check[0]                  # VT-01, VT-02
    assert body.index("blender_render render") < body.index("vault check-uploaded")
    assert body.index("DRY:-0") < body.index("blender_render render")                    # the DRY gate stops before any render
    assert "beat.txt" not in body and "echo DONE" not in body                             # the wrapper owns the end word
    for ln in code:
        for m in re.finditer(r'pip install -q (.*?) \|\|', ln):
            assert all("==" in p for p in m.group(1).replace('"', "").split()), ln          # pinned versions only


def test_the_code_bundle_pin_is_a_placeholder_until_the_dry_gate_fills_it():
    assert "code/blender_render/ee_src.tar.gz" in SH and "sha256sum -c" in SH
    assert D.placeholder_problems(SH, PODS) == ["script: PLACEHOLDER_SHA_EE_SRC_TAR_GZ (a pin that was never filled)"]


@pytest.mark.xfail(strict=True, reason="ICW-09: the DRY gate writes the bundle's sha256 into blender_render.sh before the first pod; "
                   "remove this marker then (strict: it fails the day the pin is real, as a reminder)")
def test_the_pod_is_runnable_only_when_no_placeholder_is_left():
    assert "PLACEHOLDER" not in SH


def test_the_ci_smoke_workflow_is_the_roadmaps():
    wf = yaml.safe_load(WF.read_text(encoding="utf-8"))
    job = wf["jobs"]["smoke"]
    assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == 15
    text = WF.read_text(encoding="utf-8")
    assert "config/cloud_pins.json" in text and "blender.project install" in text and "--archive" in text
    assert "blender.render smoke" in text and "actions/upload-artifact" in text and "actions/cache" in text
    assert "key: blender-${{ steps.pin.outputs.sha256 }}" in text                       # the cache is keyed by the pin
    assert "len(frames) == 8" in text and "check_png(f, 320, 180)" in text


def test_the_bundle_is_a_git_archive_of_the_package_and_config(tmp_path):
    from explainer_engine.training.pods import blender_render as POD
    assert POD.BUNDLE_PATHS == ("explainer_engine", "config")
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True).returncode != 0:
        pytest.skip("not a git checkout")
    a = POD.bundle(tmp_path / "a" / "ee_src.tar.gz")
    b = POD.bundle(tmp_path / "b" / "ee_src.tar.gz")
    assert a == b == hashlib.sha256((tmp_path / "a" / "ee_src.tar.gz").read_bytes()).hexdigest()   # byte-stable for one commit
