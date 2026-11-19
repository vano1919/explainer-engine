"""Slice scope check (D-139, Step 0.4b): a slice PR may change only its own paths; the list cannot widen itself."""
import json
import subprocess

from explainer_engine import scope_check as S

CFG = {
    "control_slice": "0.4b",
    "control_files": ["docs/architecture/v4_1_allowlists.json"],
    "slices": {
        "0.4b": {"branch": "b-ctl", "paths": ["docs/architecture/v4_1_allowlists.json", "pkg/*.py"]},
        "1.1": {"branch": "b-11", "paths": ["pkg/scene.py", "tests/test_*.py"]},
    },
}


def test_path_outside_the_slice_is_red():
    assert S.check(CFG, "b-11", ["pkg/scene.py", "pkg/other.py"]) == ["pkg/other.py is outside the allowlist of slice 1.1"]


def test_paths_inside_pass_and_other_branches_are_exempt():
    assert S.check(CFG, "b-11", ["pkg/scene.py", "tests/test_a.py"]) == []
    assert S.check(CFG, "some-hotfix", ["anything/at/all.py"]) == []


def test_an_unknown_slice_id_under_the_prefix_fails_and_other_branches_stay_free():
    cfg = dict(CFG, slice_branch_prefix="b-")
    assert S.check(cfg, "b-99", ["x.py"]) and "names no slice" in S.check(cfg, "b-99", ["x.py"])[0]
    assert S.check(cfg, "hotfix-1", ["x.py"]) == []


def test_only_the_control_slice_may_list_a_control_file():
    bad = json.loads(json.dumps(CFG))
    bad["slices"]["1.1"]["paths"].append("docs/architecture/v4_1_allowlists.json")
    assert any("lists a control file" in p for p in S.check(bad, "b-11", []))
    assert S.check(CFG, "b-11", ["docs/architecture/v4_1_allowlists.json"]) != []  # a slice PR cannot edit the list


def test_real_list_is_consistent():
    import pathlib
    cfg = json.loads((pathlib.Path(__file__).parents[2] / S.ALLOWLIST).read_text(encoding="utf-8"))
    assert S.check(cfg, cfg["slices"]["0.4b"]["branch"], []) == []
    assert len({e["branch"] for e in cfg["slices"].values()}) == len(cfg["slices"])


def _git(cwd, *a):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True, capture_output=True)


def test_list_comes_from_the_base_so_a_pr_cannot_widen_itself(tmp_path):
    (tmp_path / "docs/architecture").mkdir(parents=True)
    f = tmp_path / S.ALLOWLIST
    f.write_text(json.dumps(CFG))
    _git(tmp_path, "init", "-q", "-b", "base")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-qb", "b-11")
    widened = json.loads(json.dumps(CFG))
    widened["slices"]["1.1"]["paths"].append("pkg/other.py")
    f.write_text(json.dumps(widened))
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/other.py").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "pr")
    assert S.main(["--root", str(tmp_path), "--base", "base", "--head", "HEAD", "--head-ref", "b-11"]) == 1
    assert S.main(["--root", str(tmp_path), "--base", "base", "--head", "HEAD", "--head-ref", "unrelated"]) == 0
