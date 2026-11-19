"""W5 (D-132): the byte-stable code bundle and batch tarball of the A/B pods and the sha pins in their scripts. No upload here."""
from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from explainer_engine.training.pods.klein import klein_jobs as K
from explainer_engine.training.pods.ltx import ab_bundle as B
from explainer_engine.training.pods.ltx import runpod_ltx_jobs as R

SHA = "ab" * 32


def _names(path):
    with tarfile.open(path, "r:gz") as t:
        return t.getnames()


def test_the_code_bundle_is_byte_stable_and_leaves_the_pod_scripts_out(tmp_path):
    a, b = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    sa, sb = B.build_code(a), B.build_code(b)
    assert sa == sb == hashlib.sha256(a.read_bytes()).hexdigest() and a.read_bytes() == b.read_bytes()
    names = _names(a)
    assert "explainer_engine/training/pods/klein/klein_jobs.py" in names and "explainer_engine/training/pods/ltx/launch.json" in names
    assert "config/retired_era.json" in names
    assert not set(B.EXCLUDE) & set(names)                                   # a pinned script never changes the bundle it pins
    with tarfile.open(a, "r:gz") as t:
        m = t.getmember("explainer_engine/training/pods/klein/launch.json")
        assert (m.mtime, m.mode, m.uid, m.gid) == (0, 0o644, 0, 0)


def test_the_batch_tarball_is_byte_stable(tmp_path):
    d = tmp_path / "batch"
    (d / "pics").mkdir(parents=True)
    (d / "batch.json").write_text('{"jobs": []}')
    (d / "pics" / "a.png").write_bytes(b"png")
    s1, s2 = B.build_batch(tmp_path / "1.tar.gz", d), B.build_batch(tmp_path / "2.tar.gz", d)
    assert s1 == s2 and _names(tmp_path / "1.tar.gz") == ["batch.json", "pics/a.png"]
    (d / "batch.json").write_text('{"jobs": [1]}')
    assert B.build_batch(tmp_path / "3.tar.gz", d) != s1


def test_pin_fills_one_placeholder_once_and_pinned_reads_it(tmp_path):
    s = tmp_path / "pod.sh"
    s.write_text("printf '%s  %s\\n' @@EE_SRC_SHA256@@ \"$JOB/ee_src.tar.gz\" > x\nprintf '%s  %s\\n' @@BATCH_SHA256@@ \"$JOB/batch.tar.gz\" >> x\n")
    assert B.pinned(s, "EE_SRC_SHA256") is None
    B.pin(s, "EE_SRC_SHA256", SHA)
    assert B.pinned(s, "EE_SRC_SHA256") == SHA and B.pinned(s, "BATCH_SHA256") is None and "@@BATCH_SHA256@@" in s.read_text()
    with pytest.raises(SystemExit):
        B.pin(s, "EE_SRC_SHA256", SHA)                                       # no placeholder left: found 0 times
    with pytest.raises(SystemExit):
        B.pin(s, "BATCH_SHA256", "nothex")


def test_code_problems_catch_a_stale_or_missing_pin(tmp_path, monkeypatch):
    s = tmp_path / "pod.sh"
    s.write_text("printf '%s  %s\\n' @@EE_SRC_SHA256@@ \"$JOB/ee_src.tar.gz\" > x\n")
    assert "not filled in" in B.code_problems(s)[0]
    B.pin(s, "EE_SRC_SHA256", SHA)
    monkeypatch.setattr(B, "build_code", lambda out, ref=None: "cd" * 32)
    assert "not the one the current tree builds" in B.code_problems(s)[0]
    monkeypatch.setattr(B, "build_code", lambda out, ref=None: SHA)
    assert B.code_problems(s) == []


def test_both_pod_scripts_carry_the_two_pins_and_download_both_files():
    for script in B.SCRIPTS:
        text = script.read_text(encoding="utf-8")
        assert text.count("ee_src.tar.gz") >= 3 and "batch.tar.gz" in text and "sha256sum --strict -c" in text
        assert "# needs: /workspace/job/batch.tar.gz" in text and "# needs: /workspace/job/ee_src.tar.gz" in text
        assert "@@BATCH_SHA256@@" in text or B.pinned(script, "BATCH_SHA256")     # the batch pin stays open until the plan thread's batch exists
    assert "run /workspace/batch/batch.json" in R.LAUNCHER.read_text(encoding="utf-8")
    assert "run /workspace/batch/batch.json" in K.LAUNCHER.read_text(encoding="utf-8")


def test_both_scripts_pin_the_same_uploaded_code_bundle():
    pins = {s.name: B.pinned(s, "EE_SRC_SHA256") for s in B.SCRIPTS}
    assert all(p and len(p) == 64 for p in pins.values()) and len(set(pins.values())) == 1   # one bundle, uploaded to both paths


def test_both_scripts_constrain_pip_to_the_images_torch_before_any_install():
    for script in B.SCRIPTS:
        lines = script.read_text(encoding="utf-8").splitlines()
        code = [ln for ln in lines if not ln.lstrip().startswith("#")]
        first_pip = next(i for i, ln in enumerate(code) if "pip install" in ln)
        c = next(i for i, ln in enumerate(code) if "torch.__version__" in ln and "constraints.txt" in ln)
        e = next(i for i, ln in enumerate(code) if "export PIP_CONSTRAINT=" in ln)
        assert c < e < first_pip, script.name                      # read at run time on the pod, set before the first pip install


def test_the_klein_batch_pin_is_the_plan_threads_uploaded_file():
    klein = next(s for s in B.SCRIPTS if s.name == "klein_pod.sh")
    assert B.pinned(klein, "BATCH_SHA256") == "e177fcd1407c9ea24a9b21733f2cf00a41db9fa3b3ff051550f24c2470ab090b"
    assert K.script_problems(klein.read_text(encoding="utf-8")) == []
    ltx = next(s for s in B.SCRIPTS if s.name == "runpod_ltx_pod.sh")
    assert B.pinned(ltx, "BATCH_SHA256") is None or len(B.pinned(ltx, "BATCH_SHA256")) == 64     # the LTX batch needs the end keyframes first
