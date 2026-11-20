"""Focused tests of the Gemini code lane tools (skill ``gemini-coding``, creator 2026-11-20): ``tools/gemini_pack.py`` and
``tools/gemini_intake.py``. Every refusal of skill section 5 has its own negative test, and the pack refusals of section 3 too.
Each test builds a throw-away git repo, so nothing here touches the real one."""
from __future__ import annotations

import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import gemini_intake as I  # noqa: E402
import gemini_lane as L  # noqa: E402
import gemini_pack as P  # noqa: E402

MOD = "".join(f"def f{i}(x):\n    return x + {i}\n\n" for i in range(12)) + (
    "class Thing:\n    def run(self):\n        return 1\n\n    def stop(self):\n        return 2\n")
OLD_TEST = "from explainer_engine.mod import f1\n\n\ndef test_f1():\n    assert f1(1) == 2\n"
NEW_CODE = "def double(x):\n    return 2 * x\n"
NEW_TEST = "from explainer_engine.fx.new import double\n\n\ndef test_double():\n    assert double(2) == 4\n"
IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.com"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    files = {"explainer_engine/__init__.py": "", "explainer_engine/mod.py": MOD, "tests/unit/test_mod.py": OLD_TEST,
             "explainer_engine/governance/gate.py": "X = 1\n", "config/spend_caps.json": "{}\n",
             "docs/note.md": "hello\n", ".claude/settings.json": "{}\n", "explainer_engine/cloud/modal_run.py": "Y = 1\n",
             "explainer_engine/other.py": "def keep():\n    return 1\n"}
    for p, text in files.items():
        (r / p).parent.mkdir(parents=True, exist_ok=True)
        (r / p).write_text(text)
    git(r, "add", "-A")
    git(r, *IDENT, "commit", "-q", "-m", "base")
    return r


@pytest.fixture()
def sha(repo):
    return git(repo, "rev-parse", "HEAD")


def task_json(sha, **over):
    t = {"schema": "gemini_task/1", "task": "T-1", "base_sha": sha, "team_branch": "claude/team-x",
         "create": ["explainer_engine/fx/new.py"], "change": ["explainer_engine/mod.py"], "read": [], "tests": [], "suites": []}
    t.update(over)
    return t


def make_task(tmp_path, sha, **over) -> Path:
    d = tmp_path / "T-1"
    (d / "in").mkdir(parents=True)
    (d / "out").mkdir()
    (d / "in" / "task.json").write_text(json.dumps(task_json(sha, **over)))
    return d


def diff(path: str, old: str, new: str) -> bytes:
    lines = difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}")
    return "".join(lines).encode()


def answer(d: Path, entries, base_sha=None, extra=None, sha_override=None):
    """entries: (path, kind, bytes). Writes out/<path> and out/MANIFEST.json."""
    files = []
    for path, kind, data in entries:
        if kind != "delete":
            f = d / "out" / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        files.append({"path": path, "kind": kind, "sha256": (sha_override or {}).get(path, L.sha256_bytes(data))})
    manifest = {"base_sha": base_sha or json.loads((d / "in" / "task.json").read_text())["base_sha"], "files": files}
    (d / "out" / "MANIFEST.json").write_text(json.dumps(manifest))
    for name, data in (extra or {}).items():
        (d / "out" / name).write_bytes(data)


def codes(report) -> list[str]:
    return [r["code"] for r in report["refusals"]]


def run_intake(d, repo, **kw):
    return I.intake(d, repo, **kw)


def untouched(repo, sha):
    assert git(repo, "rev-parse", "HEAD") == sha
    assert git(repo, "branch", "--list", "claude/*") == ""
    assert git(repo, "status", "--short") == ""


# ---- intake: the accepted path -------------------------------------------------------------------------------------------------

def test_accepts_new_file_and_hunks_on_a_branch_and_runs_the_tests(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, create=["explainer_engine/fx/new.py", "tests/unit/test_fx_new.py"], suites=["tests/unit/test_mod.py"])
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode()), ("tests/unit/test_fx_new.py", "new", NEW_TEST.encode()),
               ("explainer_engine/mod.py", "patch", diff("explainer_engine/mod.py", MOD, MOD + "\n\ndef extra():\n    return 3\n"))])
    rep = run_intake(d, repo, trailers=("Co-Authored-By: T <t@example.com>",))
    assert rep["status"] == "accepted" and rep["refusals"] == [] and rep["branch"] == "claude/team-x-gemini-T-1"
    assert rep["tests"]["ok"] is True and rep["metrics"]["files_new"] == 2 and rep["metrics"]["files_patched"] == 1
    assert git(repo, "rev-parse", "HEAD") == sha and git(repo, "status", "--short") == ""          # team branch + tree untouched
    assert "def extra" in git(repo, "show", f"{rep['branch']}:explainer_engine/mod.py")
    assert "Co-Authored-By: T" in git(repo, "log", "-1", "--format=%B", rep["branch"])
    assert json.loads((d / "out" / "INTAKE.json").read_text())["status"] == "accepted"
    assert "Gemini task T-1" in (d / "out" / "PR_BODY.md").read_text()


def test_red_tests_are_reported_not_hidden(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, create=["explainer_engine/fx/new.py", "tests/unit/test_fx_new.py"])
    answer(d, [("explainer_engine/fx/new.py", "new", b"def double(x):\n    return x\n"), ("tests/unit/test_fx_new.py", "new", NEW_TEST.encode())])
    rep = run_intake(d, repo)
    assert rep["status"] == "accepted_red" and rep["tests"]["ok"] is False
    assert I.main([str(d), "--repo", str(repo), "--no-apply"]) == 0           # judged only: no branch, exit 0


def test_the_testers_files_newer_than_the_pinned_commit_are_run_but_not_committed(tmp_path, repo, sha):
    (repo / "tests/unit").mkdir(parents=True, exist_ok=True)
    (repo / "tests/unit/test_acceptance.py").write_text(NEW_TEST)                  # untracked: written after the pin
    d = make_task(tmp_path, sha, tests=["tests/unit/test_acceptance.py"])
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    rep = run_intake(d, repo)
    assert rep["status"] == "accepted" and rep["tests"]["ran"] and rep["tests"]["ok"] is True
    assert rep["tests"]["acceptance_tests"] == {"tests/unit/test_acceptance.py": L.sha256_bytes(NEW_TEST.encode())}
    assert "test_acceptance" not in git(repo, "ls-tree", "-r", "--name-only", rep["branch"])


def test_a_missing_acceptance_test_is_not_a_green_intake(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, tests=["tests/unit/test_absent.py"])
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    rep = run_intake(d, repo)
    assert rep["status"] == "accepted_untested" and "not found" in rep["tests"]["detail"]


def test_no_apply_judges_only(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    rep = run_intake(d, repo, apply=False)
    assert rep["status"] == "accepted_not_applied"
    untouched(repo, sha)


def test_existing_branch_stops_the_intake(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    git(repo, "branch", "claude/team-x-gemini-T-1")
    with pytest.raises(L.LaneError, match="already exists"):
        run_intake(d, repo)


# ---- intake: one negative test per refusal (skill section 5) -------------------------------------------------------------------

def test_refuses_path_outside_task_list(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode()), ("explainer_engine/fx/extra.py", "new", NEW_CODE.encode())])
    rep = run_intake(d, repo)
    assert rep["status"] == "refused" and "outside_task_list" in codes(rep)
    assert [r["path"] for r in rep["refusals"] if r["code"] == "outside_task_list"] == ["explainer_engine/fx/extra.py"]
    untouched(repo, sha)


def test_refuses_new_file_body_for_an_existing_file(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/mod.py", "new", MOD.encode() + b"# whole file again\n")])
    rep = run_intake(d, repo)
    assert "whole_file_rewrite" in codes(rep)
    untouched(repo, sha)


def test_refuses_patch_kind_that_is_a_whole_body(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/mod.py", "patch", MOD.encode() + b"# no hunks, a body\n")])
    rep = run_intake(d, repo)
    assert "whole_file_rewrite" in codes(rep)
    untouched(repo, sha)


def test_refuses_hunk_that_does_not_apply_to_the_pinned_sha(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    older = MOD.replace("return x + 3", "return x + 33")                    # Gemini saw different bytes than the pinned commit
    answer(d, [("explainer_engine/mod.py", "patch", diff("explainer_engine/mod.py", older, older.replace("x + 33", "x + 99")))])
    rep = run_intake(d, repo)
    assert "hunk_does_not_apply" in codes(rep)
    untouched(repo, sha)


def test_refuses_file_shrinking_over_30_percent(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    # a valid body that keeps every public name but is far shorter than the original
    shrunk = "".join(f"def f{i}(x):pass\n" for i in range(12)) + "class Thing:\n def run(self):pass\n def stop(self):pass\n"
    assert len(shrunk) < 0.7 * len(MOD)
    answer(d, [("explainer_engine/mod.py", "patch", diff("explainer_engine/mod.py", MOD, shrunk))])
    rep = run_intake(d, repo)
    assert codes(rep) == ["shrinks"]
    untouched(repo, sha)


def test_refuses_file_that_loses_a_public_function(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/mod.py", "patch", diff("explainer_engine/mod.py", MOD, MOD.replace("def f11(x):", "def _f11(x):")))])
    rep = run_intake(d, repo)
    assert codes(rep) == ["loses_public_function"] and "f11" in rep["refusals"][0]["detail"]
    answer(d, [("explainer_engine/mod.py", "patch", diff("explainer_engine/mod.py", MOD, MOD.replace("def stop", "def _stop")))])
    assert "Thing.stop" in run_intake(d, repo)["refusals"][0]["detail"]            # a public method counts too
    untouched(repo, sha)


@pytest.mark.parametrize("path", ["explainer_engine/governance/gate.py", ".claude/settings.json", "config/spend_caps.json",
                                  "explainer_engine/cloud/modal_run.py", ".github/workflows/ci.yml", "tools/gemini_intake.py",
                                  "explainer_engine/governance/owner_requirements.json", ".env", "CLAUDE.md",
                                  "explainer_engine/qa/send_validators.py", "explainer_engine/core/ledger.py",
                                  "explainer_engine/audio/elevenlabs_client.py", ".claude/hooks/pre.py"])
def test_refuses_every_never_list_path_even_when_the_task_names_it(tmp_path, repo, sha, path):
    d = make_task(tmp_path, sha, create=["explainer_engine/fx/new.py", path])
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode()), (path, "new", b"X = 2\n")])
    rep = run_intake(d, repo)
    assert rep["status"] == "refused" and [r["path"] for r in rep["refusals"] if r["code"] == "never_list"] == [path]
    untouched(repo, sha)


def test_refuses_a_patch_of_a_governance_file(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, change=["explainer_engine/governance/gate.py"])
    answer(d, [("explainer_engine/governance/gate.py", "patch", diff("explainer_engine/governance/gate.py", "X = 1\n", "X = 1\nY = 2\n"))])
    assert "never_list" in codes(run_intake(d, repo))
    untouched(repo, sha)


def test_refuses_edited_tests(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, change=["explainer_engine/mod.py", "tests/unit/test_mod.py"], tests=["tests/unit/test_mod.py"])
    answer(d, [("tests/unit/test_mod.py", "patch", diff("tests/unit/test_mod.py", OLD_TEST, OLD_TEST.replace("== 2", "== 99")))])
    assert codes(run_intake(d, repo)) == ["edited_test"]
    untouched(repo, sha)


def test_refuses_a_new_body_for_an_existing_test_even_when_not_in_the_tests_list(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, create=["tests/unit/test_mod.py"])             # exists at the pinned commit
    answer(d, [("tests/unit/test_mod.py", "new", b"def test_f1():\n    assert True\n")])
    assert "edited_test" in codes(run_intake(d, repo))
    untouched(repo, sha)


def test_refuses_deleted_files_and_deleted_tests(tmp_path, repo, sha):
    d = make_task(tmp_path, sha, tests=["tests/unit/test_mod.py"], change=["explainer_engine/mod.py", "explainer_engine/other.py"])
    answer(d, [("tests/unit/test_mod.py", "delete", b""), ("explainer_engine/other.py", "delete", b"")])
    rep = run_intake(d, repo)
    assert sorted(codes(rep)) == ["deleted", "edited_test"]
    answer(d, [("explainer_engine/other.py", "patch",
                b"--- a/explainer_engine/other.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-def keep():\n-    return 1\n")])
    assert "deleted" in codes(run_intake(d, repo))
    untouched(repo, sha)


def test_refuses_sha_mismatch_with_manifest(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())], sha_override={"explainer_engine/fx/new.py": "0" * 64})
    assert codes(run_intake(d, repo)) == ["sha_mismatch"]
    untouched(repo, sha)


def test_zero_sha_is_taken_only_with_a_matching_sums_file(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    path = "explainer_engine/fx/new.py"
    answer(d, [(path, "new", NEW_CODE.encode())], sha_override={path: "0" * 64})
    assert codes(run_intake(d, repo, apply=False)) == ["sha_mismatch"]                    # a zero sha alone proves nothing
    (d / "out" / "SHA256SUMS").write_text(f"{'1' * 64}  {path}\n")
    assert codes(run_intake(d, repo, apply=False)) == ["sha_mismatch"]                    # wrong sum
    (d / "out" / "SHA256SUMS").write_text(f"{L.sha256_bytes(NEW_CODE.encode())}  {path}\n")
    assert run_intake(d, repo, apply=False)["status"] == "accepted_not_applied"          # the driver's sum matches the file


def test_a_placeholder_word_instead_of_a_sha_is_taken_only_with_a_matching_sums_file(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    path = "explainer_engine/fx/new.py"
    answer(d, [(path, "new", NEW_CODE.encode())], sha_override={path: "computed_at_write_time"})
    assert codes(run_intake(d, repo, apply=False)) == ["sha_mismatch"]
    (d / "out" / "SHA256SUMS").write_text(f"{L.sha256_bytes(NEW_CODE.encode())}  ./{path}\n")
    assert run_intake(d, repo, apply=False)["status"] == "accepted_not_applied"
    answer(d, [(path, "new", NEW_CODE.encode())], sha_override={path: "2" * 64})                # a real-looking wrong sha stays a refusal
    assert codes(run_intake(d, repo, apply=False)) == ["sha_mismatch"]
    answer(d, [(path, "new", NEW_CODE.encode())], sha_override={path: L.sha256_bytes(b"")})      # the hash of nothing is a writer's placeholder
    assert run_intake(d, repo, apply=False)["status"] == "accepted_not_applied"


def test_a_short_base_sha_of_the_pinned_commit_is_taken_but_another_is_not(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())], base_sha=sha[:8])
    assert run_intake(d, repo, apply=False)["status"] == "accepted_not_applied"
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())], base_sha=sha[:3])
    assert codes(run_intake(d, repo, apply=False)) == ["base_sha_mismatch"]


def test_refuses_manifest_for_another_base(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())], base_sha="f" * 40)
    assert codes(run_intake(d, repo)) == ["base_sha_mismatch"]
    untouched(repo, sha)


def test_refuses_a_file_that_is_not_in_the_manifest(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())], extra={"stray.py": b"x = 1\n", "NOTES.md": b"ok\n"})
    rep = run_intake(d, repo)
    assert [r["path"] for r in rep["refusals"]] == ["stray.py"] and codes(rep) == ["unlisted_file"]
    untouched(repo, sha)


def test_export_noise_is_ignored_and_never_applied(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())],
           extra={"RAW_chat1.txt": b"raw", "SHA256SUMS": b""})
    (d / "out" / "__pycache__").mkdir(exist_ok=True)
    (d / "out" / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\x00")
    (d / "out" / "pkg").mkdir(exist_ok=True)
    (d / "out" / "pkg" / "y.pyc").write_bytes(b"\x00")
    rep = run_intake(d, repo)
    assert rep["status"] == "accepted" or rep["status"] == "accepted_untested"
    assert rep["refusals"] == [] and list(rep["files"]) == ["explainer_engine/fx/new.py"]
    assert git(repo, "ls-tree", "-r", "--name-only", rep["branch"]).count("RAW_") == 0 and "pyc" not in git(repo, "ls-tree", "-r", "--name-only", rep["branch"])


def test_refuses_a_listed_file_that_is_absent(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    (d / "out" / "explainer_engine/fx/new.py").unlink()
    assert codes(run_intake(d, repo)) == ["file_missing"]


def test_refuses_secrets_in_the_answer(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    token = "hf_" + "A1b2C3d4E5" * 4
    answer(d, [("explainer_engine/fx/new.py", "new", f'TOKEN = "{token}"\n'.encode())])
    rep = run_intake(d, repo)
    assert codes(rep) == ["secret_in_content"] and token not in json.dumps(rep)           # the report never repeats the secret


def test_refuses_code_that_does_not_compile(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", b"def broken(:\n    pass\n")])
    assert codes(run_intake(d, repo)) == ["syntax_error"]


def test_refuses_a_diff_that_names_another_path(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    sneaky = diff("explainer_engine/other.py", "def keep():\n    return 1\n", "def keep():\n    return 2\n")
    answer(d, [("explainer_engine/mod.py", "patch", sneaky)])
    assert "outside_task_list" in codes(run_intake(d, repo))
    untouched(repo, sha)


def test_refuses_a_kind_that_does_not_match_the_task_lists(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "patch", diff("explainer_engine/fx/new.py", "", NEW_CODE))])
    assert "patch_of_missing" in codes(run_intake(d, repo))


def test_refuses_unsafe_duplicate_and_bad_entries(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    answer(d, [("explainer_engine/fx/new.py", "new", NEW_CODE.encode()), ("explainer_engine/fx/new.py", "new", NEW_CODE.encode())])
    assert "duplicate_path" in codes(run_intake(d, repo))
    manifest = {"base_sha": sha, "files": [{"path": "../evil.py", "kind": "new", "sha256": "0"}, {"path": "/abs.py", "kind": "new", "sha256": "0"},
                                           {"path": "explainer_engine/fx/new.py", "kind": "rename", "sha256": "0"}]}
    (d / "out" / "MANIFEST.json").write_text(json.dumps(manifest))
    assert codes(run_intake(d, repo)).count("path_unsafe") == 2 and "bad_kind" in codes(run_intake(d, repo))


def test_refuses_a_missing_or_broken_manifest(tmp_path, repo, sha):
    d = make_task(tmp_path, sha)
    assert codes(run_intake(d, repo)) == ["manifest_invalid"]
    (d / "out" / "MANIFEST.json").write_text("not json")
    assert codes(run_intake(d, repo)) == ["manifest_invalid"]
    (d / "out" / "MANIFEST.json").write_text(json.dumps({"base_sha": sha, "files": []}))
    assert codes(run_intake(d, repo)) == ["manifest_invalid"]
    assert I.main([str(d), "--repo", str(repo)]) == 2


def test_task_json_with_a_placeholder_sha_is_refused(tmp_path, repo):
    d = make_task(tmp_path, "<FILL>")
    with pytest.raises(L.LaneError, match="base_sha"):
        run_intake(d, repo)


# ---- pack ----------------------------------------------------------------------------------------------------------------------

def pack_dir(tmp_path, sha, task_md=None, **over) -> Path:
    d = tmp_path / "pack-T-1"
    d.mkdir()
    (d / "task.json").write_text(json.dumps(task_json(sha, **over)))
    (d / "TASK.md").write_text(task_md or f"# TASK\nbase_sha = `{sha}`\n")
    return d


def test_pack_writes_the_pinned_bytes_with_a_sha_per_file_and_is_deterministic(tmp_path, repo, sha):
    (repo / "tests/unit").mkdir(parents=True, exist_ok=True)
    (repo / "tests/unit/test_new.py").write_text(NEW_TEST)
    d = pack_dir(tmp_path, sha, change=["explainer_engine/mod.py"], read=["docs/note.md"], tests=["tests/unit/test_new.py"], create=["explainer_engine/fx/new.py"])
    (repo / "explainer_engine/mod.py").write_text("CHANGED AFTER THE PIN\n")            # the working tree moves on
    res = P.pack(d, repo)
    ctx = (d / "in" / "CONTEXT_T-1.md").read_text()
    assert "CHANGED AFTER THE PIN" not in ctx and "def f11(x):" in ctx and "hello" in ctx
    by = {f["path"]: f for f in res["files"]}
    assert by["explainer_engine/mod.py"]["sha256"] == L.sha256_bytes(MOD.encode()) and f"`{by['docs/note.md']['sha256']}`" in ctx
    assert by["tests/unit/test_new.py"]["role"] == "test" and (d / "in/tests/unit/test_new.py").read_text() == NEW_TEST
    assert json.loads((d / "in/PACK.json").read_text())["base_sha"] == sha and (d / "in/task.json").is_file()
    first = {p.name: p.read_bytes() for p in (d / "in").iterdir() if p.is_file()}
    P.pack(d, repo)
    assert first == {p.name: p.read_bytes() for p in (d / "in").iterdir() if p.is_file()}


def test_pack_pins_a_placeholder_and_replaces_it_in_task_md(tmp_path, repo, sha):
    d = pack_dir(tmp_path, "<FILL>", task_md="base_sha = `<FILL: head at packing>`\n")
    P.pack(d, repo, pin="HEAD")
    assert json.loads((d / "task.json").read_text())["base_sha"] == sha and f"`{sha}`" in (d / "in/TASK.md").read_text()
    sub = tmp_path / "x"
    sub.mkdir()
    other = pack_dir(sub, sha)
    git(repo, *IDENT, "commit", "--allow-empty", "-q", "-m", "later")
    P.pack(other, repo, pin="HEAD")                                                    # a valid pin is never overwritten
    assert json.loads((other / "task.json").read_text())["base_sha"] == sha


def test_pack_without_pin_refuses_a_placeholder(tmp_path, repo):
    with pytest.raises(L.LaneError, match="--pin"):
        P.pack(pack_dir(tmp_path, "<FILL>"), repo)


@pytest.mark.parametrize("path", [".env", "config/spend_caps.json", "explainer_engine/governance/gate.py", ".claude/settings.json",
                                  "tools/secrets.py", ".github/workflows/x.yml", "explainer_engine/cloud/modal_run.py", "keys/server.pem"])
def test_pack_refuses_secrets_spend_caps_governance_and_launchers(tmp_path, repo, sha, path):
    d = pack_dir(tmp_path, sha, read=[path])
    with pytest.raises(L.LaneError, match="never-list"):
        P.pack(d, repo)
    assert not (d / "in").exists()                                                      # nothing written


def test_pack_refuses_secret_content_binary_symlink_and_oversize(tmp_path, repo, sha):
    (repo / "docs/leak.md").write_text('api_key = "' + "x" * 30 + '"\n')
    (repo / "docs/bin.dat").write_bytes(b"\xff\xfe\x00\x01")
    (repo / "docs/big.txt").write_text("a" * (L.MAX_FILE_BYTES + 10))
    os.symlink("note.md", repo / "docs/link.md")
    git(repo, "add", "-A")
    git(repo, *IDENT, "commit", "-q", "-m", "more")
    new = git(repo, "rev-parse", "HEAD")
    for name, msg in (("docs/leak.md", "secret pattern"), ("docs/bin.dat", "not UTF-8"), ("docs/big.txt", "Drive limit"), ("docs/link.md", "symlink")):
        d = tmp_path / name.replace("/", "_")
        d.mkdir()
        (d / "task.json").write_text(json.dumps(task_json(new, read=[name])))
        (d / "TASK.md").write_text(f"base_sha = `{new}`\n")
        with pytest.raises(L.LaneError, match=msg):
            P.pack(d, repo)


def test_pack_refuses_missing_existing_create_and_missing_tests(tmp_path, repo, sha):
    with pytest.raises(L.LaneError, match="does not exist"):
        P.pack(pack_dir(tmp_path, sha, read=["docs/nope.md"]), repo)
    other = tmp_path / "b"
    other.mkdir()
    with pytest.raises(L.LaneError, match="already exists"):
        P.pack(pack_dir(other, sha, create=["explainer_engine/mod.py"], change=[]), repo)
    c = tmp_path / "c"
    c.mkdir()
    with pytest.raises(L.LaneError, match="missing in the working tree"):
        P.pack(pack_dir(c, sha, tests=["tests/unit/test_absent.py"]), repo)
    e = tmp_path / "e"
    e.mkdir()
    with pytest.raises(L.LaneError, match="both create and change"):
        P.pack(pack_dir(e, sha, create=["a.py"], change=["a.py"]), repo)


def test_pack_refuses_unknown_commit_unsafe_path_and_foreign_sha_in_task_md(tmp_path, repo, sha):
    with pytest.raises(L.LaneError, match="not a commit"):
        P.pack(pack_dir(tmp_path, "a" * 40), repo)
    b = tmp_path / "b"
    b.mkdir()
    with pytest.raises(L.LaneError, match="plain"):
        P.pack(pack_dir(b, sha, read=["../outside.txt"]), repo)
    c = tmp_path / "c"
    c.mkdir()
    with pytest.raises(L.LaneError, match="pinned base sha"):
        P.pack(pack_dir(c, sha, task_md=f"base_sha = `{'b' * 40}`\n"), repo)


def test_pack_fences_content_that_holds_backticks(tmp_path, repo, sha):
    (repo / "docs/ticks.md").write_text("````\nnested\n````\n")
    git(repo, "add", "-A")
    git(repo, *IDENT, "commit", "-q", "-m", "ticks")
    new = git(repo, "rev-parse", "HEAD")
    d = pack_dir(tmp_path, new, read=["docs/ticks.md"])
    P.pack(d, repo)
    ctx = (d / "in/CONTEXT_T-1.md").read_text()
    assert "`````\n````\nnested\n````\n`````\n" in ctx


# ---- the shared rules ----------------------------------------------------------------------------------------------------------

def test_the_new_effect_module_paths_of_g01_are_allowed():
    for p in ("explainer_engine/production/fx25d/__init__.py", "explainer_engine/production/fx25d/breath_embers.py",
              "tests/unit/test_breath_embers.py", "explainer_engine/production/living_fx.py"):
        assert L.never_reason(p) is None


def test_safe_path_and_secret_scan():
    assert L.safe_path("a/b.py") == "a/b.py"
    for bad in ("", "/a", "a/../b", "a\\b", "./a", "a//b", "C:/x", "a/./b"):
        assert L.safe_path(bad) is None
    assert L.secret_hits(b"nothing here") == [] and L.secret_hits(b"-----BEGIN RSA PRIVATE KEY-----") == ["private key block"]
