"""modal_p15d.py: the parts that need no Modal SDK and no GPU."""
import pytest

from explainer_engine.training.pods.p15 import modal_p15d as M


def test_nothing_starts_without_the_creators_card(monkeypatch):
    with pytest.raises(SystemExit):
        M.go_gate({})
    with pytest.raises(SystemExit):
        M.go_gate({"EE_MODAL_GO": "yes"})
    assert M.go_gate({"EE_MODAL_GO": "cmsg_abc"}) == "cmsg_abc"


def test_link_hf_cache_builds_snapshots_from_volume_folders(tmp_path):
    vol, home = tmp_path / "vol", tmp_path / "hf"
    f = vol / "model" / "Qwen" / "Qwen-Image-2.1" / "transformer" / "a.safetensors"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    (vol / "model" / "Qwen" / "Qwen-Image-2.1" / ".cache").mkdir()
    (vol / "model" / "Qwen" / "Qwen-Image-2.1" / ".cache" / "skip").write_bytes(b"y")
    d = vol / "dataset" / "vano1919" / "tmr-artifacts" / "lora" / "l.safetensors"
    d.parent.mkdir(parents=True)
    d.write_bytes(b"z")
    made = M.link_hf_cache(vol, home)
    assert len(made) == 2
    rev = "d26bb61231c349cf6b7896fa83353113880e1ba3"
    base = home / "hub" / "models--Qwen--Qwen-Image-2.1"
    assert (base / "refs" / "main").read_text() == rev
    assert (base / "snapshots" / rev / "transformer" / "a.safetensors").read_bytes() == b"x"
    assert (home / "hub" / "datasets--vano1919--tmr-artifacts" / "snapshots" / "local" / "lora" / "l.safetensors").is_symlink()
    assert M.link_hf_cache(vol, home) == []   # idempotent


def test_battle_frame_is_drawn_first_and_order_is_otherwise_kept():
    jobs = [{"name": n} for n in ("a__S1", f"{M.FIRST}", "b__S2", "c__S3")]
    out = M.reorder_first(jobs)
    assert out[0]["name"] == M.FIRST and [j["name"] for j in out[1:]] == ["a__S1", "b__S2", "c__S3"]


def test_upload_loop_sees_new_and_changed_files_once(tmp_path):
    tmp_path = tmp_path / "out"
    tmp_path.mkdir()
    seen = {}
    (tmp_path / "a.txt").write_text("1")
    assert [p.name for p in M.new_files(tmp_path, seen)] == ["a.txt"]
    assert M.new_files(tmp_path, seen) == []
    (tmp_path / "a.txt").write_text("22")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    assert sorted(p.name for p in M.new_files(tmp_path, seen)) == ["a.txt", "b.txt"]


def test_pins_match_the_pilot_config_and_caps_fit():
    import json
    from pathlib import Path
    root = Path(M.__file__).parent
    cfg = json.loads((root / "p15.json").read_text())
    assert M.LTX_JOB in [j["id"] for j in cfg["ltx_jobs"]]
    assert any(j["shot"] == M.FIRST.split("__")[0] for j in cfg["qwen_jobs"])
    bundle_line = [ln for ln in (root / "p15c1.sh").read_text().splitlines() if "ee_src.tar.gz" in ln and "printf" in ln][0]
    assert M.BUNDLE_SHA in bundle_line
    pins = json.loads((root.parents[3] / "config" / "cloud_pins.json").read_text())
    assert M.BASE_IMAGE.endswith(pins["images"]["tmr_pod"]["digest"])
    # the hard brakes (timeouts at list price + ~$0.4 CPU/RAM) stay under the cap
    brakes = M.CAPS["qwen_timeout_s"] * 0.001097 + M.CAPS["ltx_timeout_s"] * 0.000694 + 0.4
    assert brakes <= M.CAPS["max_usd"] and M.CAPS["stop_usd"] == pytest.approx(0.8 * M.CAPS["max_usd"])


def test_token_comes_from_the_secret_env_and_the_secret_name_is_the_existing_one():
    assert M.SECRET_NAME == "huggingface-secret"
    assert M._tok({"HF_TOKEN": "a"}) == "a" and M._tok({"HUGGING_FACE_HUB_TOKEN": "b"}) == "b"
    with pytest.raises(SystemExit):
        M._tok({})


# ---- the in-container code must run against the PINNED bundle (commit 5ed640c), which does not contain modal_p15d.py ----
import py_compile
import re
import subprocess
import sys
from pathlib import Path

PINNED = "5ed640c"
REPO = Path(M.__file__).resolve().parents[4]


def _unpack_pinned(tmp_path):
    ok = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", PINNED + "^{commit}"], capture_output=True).returncode == 0
    if not ok:
        pytest.skip("pinned commit not in this clone")
    dest = tmp_path / "bundle"
    dest.mkdir()
    ar = subprocess.run(["git", "-C", str(REPO), "archive", PINNED], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=ar, check=True)
    return dest


def test_runner_script_imports_nothing_from_this_file_and_compiles(tmp_path):
    assert "modal_p15d" not in M.QWEN_RUNNER
    f = tmp_path / "runner.py"
    f.write_text(M.QWEN_RUNNER)
    py_compile.compile(str(f), doraise=True)


def test_runner_runs_against_the_pinned_bundle_and_draws_the_battle_frame_first(tmp_path):
    root = _unpack_pinned(tmp_path)
    assert not (root / "explainer_engine/training/pods/p15/modal_p15d.py").exists()   # what the container really has
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "EE_BUNDLE_ROOT": str(root), "HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, "-c", M.QWEN_RUNNER, str(tmp_path / "out"), "--variants", "--list"], env=env, cwd=str(root),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    names = [ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()]
    assert names[0] == M.FIRST and len(names) == 24, names[:3]


def test_every_module_the_container_runs_is_in_the_pinned_bundle(tmp_path):
    root = _unpack_pinned(tmp_path)
    src = (Path(M.__file__)).read_text()
    mods = set(re.findall(r'"(explainer_engine\.[a-z0-9_.]+)"', src)) | set(re.findall(r"import (explainer_engine[a-z0-9_.]+)", M.QWEN_RUNNER))
    mods -= {"explainer_engine.training.pods.p15.modal_p15d"}
    assert mods, "no module names found"
    for m in mods:
        assert (root / (m.replace(".", "/") + ".py")).is_file(), m + " is not in the pinned bundle"
    # the bundle's own p15.json is what _prepare reads
    assert (root / "explainer_engine/training/pods/p15/p15.json").is_file()


def test_failed_signal_ends_the_video_function(monkeypatch):
    import inspect
    body = inspect.getsource(M.ltx_body)
    assert '"failed" not in signal' in body
    assert 'signal["failed"]' in inspect.getsource(M.qwen_body)
