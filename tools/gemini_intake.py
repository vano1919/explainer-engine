"""Take in a Gemini code answer (skill ``gemini-coding`` section 5): judge ``out/MANIFEST.json`` and the files beside it against the
packed task, refuse what is unsafe, and only then apply the rest on a branch, run the tests and write ``out/INTAKE.json``.

usage: python tools/gemini_intake.py <task_dir> [--repo .] [--from REF] [--no-apply] [--push] [--trailer 'K: v' ...]

``<task_dir>/in/task.json`` (what Gemini was given) names the pinned ``base_sha`` and the only paths the answer may touch.
Gemini's answer is never trusted by itself: only NEW files in full and unified-diff hunks against the pinned commit are taken.

Refusals, each one a code in ``INTAKE.json`` (exit 2, the repo is not touched):
  manifest_invalid, base_sha_mismatch, bad_kind, deleted, duplicate_path, path_unsafe, never_list, outside_task_list,
  edited_test, file_missing, unlisted_file, sha_mismatch, secret_in_content, whole_file_rewrite, patch_of_missing,
  hunk_does_not_apply, shrinks, loses_public_function, syntax_error.

Accepted: the change is committed on ``claude/<team-branch>-gemini-<task>`` in a throw-away worktree (the working tree and the team
branch are not touched), the task tests and the listed affected suites run there, ``out/PR_BODY.md`` and ``out/INTAKE.json`` are
written. Opening the DRAFT PR against the team branch is the thread's step (``mcp__github__create_pull_request``; no ``gh`` here)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_lane as L  # noqa: E402

AUTHOR = ("vano1919", "122537395+vano1919@users.noreply.github.com")
OWN_FILES = {"MANIFEST.json", "NOTES.md", "INTAKE.json", "PR_BODY.md", "SHA256SUMS", "RAW_ANSWER.txt"}
ZERO_SHA = "0" * 64
DIFF_FILE = re.compile(r"^(---|\+\+\+) (?:[ab]/)?(\S+)", re.M)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", re.M)


def branch_name(task: dict) -> str:
    team = task["team_branch"]
    team = team[len("claude/"):] if team.startswith("claude/") else team
    return f"claude/{team}-gemini-{task['task']}"


def _refuse(refusals: list[dict], code: str, path: str | None, detail: str) -> None:
    refusals.append({"code": code, "path": path, "detail": detail})


def _apply_hunks(base: bytes, diff: bytes, path: str) -> tuple[bytes | None, str]:
    """Apply a unified diff to ``base`` in a scratch folder with ``git apply`` (no repo needed). (new bytes, error)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base)
        (root / "answer.patch").write_bytes(diff)
        proc = subprocess.run(["git", "apply", "--recount", "--whitespace=nowarn", "answer.patch"], cwd=root, capture_output=True)
        if proc.returncode != 0:
            return None, proc.stderr.decode("utf-8", "replace").strip()[:300]
        return target.read_bytes(), ""


def _read_sums(path: Path) -> dict[str, str]:
    """``sha256sum`` format (``<hex>  <path>``) written by the driver from the exported files."""
    sums: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                sums[parts[1].strip().lstrip("*")] = parts[0]
    return sums


def judge(task_dir: Path, repo: Path) -> tuple[dict, list[dict], dict[str, tuple[str, bytes]]]:
    """Check the answer. Returns (task, refusals, accepted) where accepted maps path -> (kind, final bytes)."""
    task_dir, repo = Path(task_dir), Path(repo)
    in_dir, out_dir = task_dir / "in", task_dir / "out"
    task = L.load_task(in_dir / "task.json" if (in_dir / "task.json").is_file() else task_dir / "task.json")
    sha = task["base_sha"]
    if not L.commit_exists(repo, sha):
        raise L.LaneError(f"base_sha {sha} is not a commit of {repo}")
    refusals: list[dict] = []
    accepted: dict[str, tuple[str, bytes]] = {}
    try:
        manifest = json.loads((out_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        assert isinstance(manifest, dict) and isinstance(manifest.get("files"), list) and manifest["files"]
    except (OSError, ValueError, AssertionError):
        _refuse(refusals, "manifest_invalid", None, "out/MANIFEST.json is missing, not JSON, or has no files list")
        return task, refusals, accepted
    claimed = str(manifest.get("base_sha"))
    if not (claimed == sha or (re.fullmatch(r"[0-9a-f]{8,39}", claimed) and sha.startswith(claimed))):   # TASK.md may give a short sha
        _refuse(refusals, "base_sha_mismatch", None,
                f"MANIFEST base_sha {str(manifest.get('base_sha'))[:12]} is not the pinned {sha[:12]}")

    sums = _read_sums(out_dir / "SHA256SUMS")
    allowed = L.allowed_paths(task)
    locked_tests = set(task["tests"])
    seen: set[str] = set()
    listed = set()
    for entry in manifest["files"]:
        path, kind = (entry.get("path") if isinstance(entry, dict) else None), (entry.get("kind") if isinstance(entry, dict) else None)
        if not isinstance(path, str) or L.safe_path(path) is None:
            _refuse(refusals, "path_unsafe", str(path), "absolute, '..', backslash or empty path")
            continue
        listed.add(path)
        if path in seen:
            _refuse(refusals, "duplicate_path", path, "listed twice in MANIFEST")
            continue
        seen.add(path)
        existing_test = path in locked_tests or (path.startswith("tests/") and L.blob_at(repo, sha, path) is not None)
        if kind == "delete" or entry.get("deleted") is True:
            _refuse(refusals, "edited_test" if existing_test else "deleted", path, "deleting a file is never taken")
            continue
        if kind not in L.MANIFEST_KINDS:
            _refuse(refusals, "bad_kind", path, f"kind must be new or patch, got {kind!r}")
            continue
        n_before = len(refusals)
        why = L.never_reason(path)
        if why:
            _refuse(refusals, "never_list", path, why)
        if path not in allowed:
            _refuse(refusals, "outside_task_list", path, "not among the task's create/change paths")
        if existing_test:
            _refuse(refusals, "edited_test", path, "the tests are the acceptance contract: edited tests are refused (invariant 10)")
        f = out_dir / path
        if len(refusals) > n_before:
            continue
        if f.is_symlink() or not f.is_file():
            _refuse(refusals, "file_missing", path, "named in MANIFEST but absent from out/ (or a symlink)")
            continue
        data = f.read_bytes()
        want = entry.get("sha256")
        if want == ZERO_SHA:                                  # Gemini cannot hash: the driver's SHA256SUMS stands in
            want = sums.get(path)
        if L.sha256_bytes(data) != want:
            _refuse(refusals, "sha_mismatch", path, "sha256 of the file differs from MANIFEST (a cut or edited upload)")
            continue
        hits = L.secret_hits(data)
        if hits:
            _refuse(refusals, "secret_in_content", path, f"secret pattern in the answer ({', '.join(hits)})")
            continue
        base = L.blob_at(repo, sha, path)
        if kind == "new":
            if base is not None:
                _refuse(refusals, "whole_file_rewrite", path, "kind new for a file that exists at the pinned commit: hunks only")
                continue
            if path not in task["create"]:
                _refuse(refusals, "outside_task_list", path, "a new file must be listed under create")
                continue
            final = data
        else:
            if base is None:
                _refuse(refusals, "patch_of_missing", path, "a patch for a file the pinned commit does not have")
                continue
            if path not in task["change"]:
                _refuse(refusals, "outside_task_list", path, "a patch must be for a path listed under change")
                continue
            text = data.decode("utf-8", "replace")
            if not HUNK.search(text) or "--- " not in text or "+++ " not in text:
                _refuse(refusals, "whole_file_rewrite", path, "an existing file came back as a body, not as unified-diff hunks")
                continue
            named = {m.group(2) for m in DIFF_FILE.finditer(text)} - {"/dev/null"}
            if "+++ /dev/null" in text or "deleted file mode" in text:
                _refuse(refusals, "deleted", path, "the diff deletes the file")
                continue
            if named - {path} or "rename from" in text or "new file mode" in text:
                _refuse(refusals, "outside_task_list", path, f"the diff names other paths: {sorted(named - {path})}")
                continue
            final, err = _apply_hunks(base, data, path)
            if final is None:
                _refuse(refusals, "hunk_does_not_apply", path, f"does not apply to the pinned {sha[:12]}: {err}")
                continue
            shrink = 100.0 * (len(base) - len(final)) / max(len(base), 1)
            if shrink > L.SHRINK_MAX_PCT:
                _refuse(refusals, "shrinks", path, f"the file shrinks by {shrink:.0f} % (limit {L.SHRINK_MAX_PCT} %)")
                continue
            if path.endswith(".py"):
                try:
                    lost = sorted(L.public_names(base.decode("utf-8")) - L.public_names(final.decode("utf-8")))
                except (SyntaxError, UnicodeDecodeError):
                    lost = []                                  # the syntax check below names the real fault
                if lost:
                    _refuse(refusals, "loses_public_function", path, f"public names gone after the patch: {lost}")
                    continue
        if path.endswith(".py"):
            try:
                compile(final.decode("utf-8"), path, "exec")
            except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                _refuse(refusals, "syntax_error", path, f"does not compile: {exc}")
                continue
        accepted[path] = (kind, final)

    if out_dir.is_dir():
        for f in sorted(out_dir.rglob("*")):
            rel = f.relative_to(out_dir).as_posix()
            if f.is_file() and rel not in listed and rel not in OWN_FILES:
                _refuse(refusals, "unlisted_file", rel, "a file in out/ that MANIFEST does not list")
    return task, refusals, accepted


def _stage_tests(task: dict, task_dir: Path, repo: Path, wt: Path) -> dict[str, str | None]:
    """Copy the task's acceptance tests into the worktree (untracked): from ``in/`` as packed, else from the repo's working tree.
    They are newer than the pinned commit (the tester writes them first), so the worktree does not have them. {path: sha256|None}."""
    staged: dict[str, str | None] = {}
    for p in task["tests"]:
        src = next((c for c in (task_dir / "in" / p, repo / p) if c.is_file() and not c.is_symlink()), None)
        if src is None:
            staged[p] = None
            continue
        data = src.read_bytes()
        (wt / p).parent.mkdir(parents=True, exist_ok=True)
        (wt / p).write_bytes(data)
        staged[p] = L.sha256_bytes(data)
    return staged


def _run_tests(wt: Path, paths: list[str]) -> dict:
    if not paths:
        return {"ran": False, "ok": None, "detail": "no tests listed in the task"}
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths], cwd=wt, capture_output=True,
                          text=True, env={**__import__("os").environ, "PYTHONPATH": str(wt), "PYTHONDONTWRITEBYTECODE": "1"})
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
    return {"ran": True, "ok": proc.returncode == 0, "returncode": proc.returncode, "seconds": round(time.time() - t0, 1),
            "paths": paths, "tail": tail}


def intake(task_dir: Path, repo: Path, *, apply: bool = True, push: bool = False, from_ref: str | None = None,
           trailers: tuple[str, ...] = ()) -> dict:
    t0 = time.time()
    task_dir, repo = Path(task_dir), Path(repo)
    task, refusals, accepted = judge(task_dir, repo)
    out_dir = task_dir / "out"
    report: dict = {"schema": "gemini_intake/1", "task": task["task"], "base_sha": task["base_sha"], "model": task.get("model"),
                    "status": "refused" if refusals else "accepted", "refusals": refusals,
                    "files": {p: k for p, (k, _) in accepted.items()}}
    if refusals or not apply:
        report["status"] = "refused" if refusals else "accepted_not_applied"
        report["metrics"] = {"intake_seconds": round(time.time() - t0, 1)}
        out_dir.mkdir(parents=True, exist_ok=True)
        L.write_json(out_dir / "INTAKE.json", report)
        return report

    branch = branch_name(task)
    if L.git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
        raise L.LaneError(f"branch {branch} already exists: delete it or pick another task id")
    with tempfile.TemporaryDirectory() as tmp:
        wt = Path(tmp) / "wt"
        L.git(repo, "worktree", "add", "-q", "-b", branch, str(wt), from_ref or task["base_sha"])
        try:
            for p, (_, data) in accepted.items():
                dest = wt / p
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            L.git(wt, "add", "--", *accepted)
            msg = f"Gemini {task['task']}: {len(accepted)} file(s) from Drive, intake passed\n\nbase_sha {task['base_sha']}\n"
            if trailers:
                msg += "\n" + "\n".join(trailers) + "\n"
            L.git(wt, "-c", f"user.name={AUTHOR[0]}", "-c", f"user.email={AUTHOR[1]}", "commit", "-q", "-m", msg)
            commit = L.head_sha(wt)
            staged = _stage_tests(task, task_dir, repo, wt)          # the tester's files, not part of Gemini's commit
            test_paths = list(dict.fromkeys([p for p in task["tests"] if (wt / p).is_file()] +
                                            [p for p in task["create"] if p.startswith("tests/") and (wt / p).is_file()] +
                                            [s for s in task["suites"] if (wt / s).exists()]))
            tests = _run_tests(wt, test_paths)
            tests["acceptance_tests"] = staged
            if any(v is None for v in staged.values()):
                tests["ok"] = None
                tests["detail"] = f"acceptance tests not found: {[p for p, v in staged.items() if v is None]}"
        finally:
            L.git(repo, "worktree", "remove", "--force", str(wt), check=False)
    report.update(status="accepted" if tests["ok"] else ("accepted_untested" if tests["ok"] is None else "accepted_red"),
                  branch=branch, commit=commit, tests=tests, team_branch=task["team_branch"])
    if push:
        for attempt in range(4):
            if L.git(repo, "push", "-u", "origin", branch, check=False).returncode == 0:
                report["pushed"] = True
                break
            time.sleep(2 ** (attempt + 1))
        else:
            report["pushed"] = False
    nbytes = sum(len(d) for _, d in accepted.values())
    report["metrics"] = {"files_new": sum(1 for k, _ in accepted.values() if k == "new"),
                         "files_patched": sum(1 for k, _ in accepted.values() if k == "patch"), "bytes": nbytes,
                         "tests_first_try": tests["ok"], "intake_seconds": round(time.time() - t0, 1)}
    out_dir.mkdir(parents=True, exist_ok=True)
    L.write_json(out_dir / "INTAKE.json", report)
    L.store.write_text_atomic(out_dir / "PR_BODY.md", _pr_body(report, accepted))
    return report


def _pr_body(report: dict, accepted: dict[str, tuple[str, bytes]]) -> str:
    rows = "\n".join(f"- `{p}` ({k}, {len(d)} bytes, sha256 `{L.sha256_bytes(d)[:16]}`)" for p, (k, d) in accepted.items())
    t = report["tests"]
    tests = ("no tests ran" if not t["ran"] else f"{'green' if t['ok'] else 'RED'} in {t['seconds']} s: `{t['tail'][-1] if t['tail'] else ''}`")
    return (f"## Gemini task {report['task']} (draft, intake passed)\n\nBase commit `{report['base_sha']}`; branch `{report['branch']}`; "
            f"PR goes against `{report['team_branch']}`.\n\n### Files taken in\n{rows}\n\n### Tests\n{tests}\n\n"
            f"### Metrics (skill gemini-coding section 8)\n{json.dumps(report['metrics'])}\n\n"
            "Review by the tester: mutation spot-check, layer validators, no test weakened. Merge only after green.\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("task_dir", type=Path)
    ap.add_argument("--repo", type=Path, default=L.ROOT)
    ap.add_argument("--from", dest="from_ref", help="ref to branch from (default: the pinned base_sha)")
    ap.add_argument("--no-apply", action="store_true", help="judge only: write INTAKE.json, create no branch")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--trailer", action="append", default=[], help="commit trailer line, e.g. 'Co-Authored-By: ...'")
    args = ap.parse_args(argv)
    try:
        report = intake(args.task_dir, args.repo, apply=not args.no_apply, push=args.push, from_ref=args.from_ref,
                        trailers=tuple(args.trailer))
    except L.LaneError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: report.get(k) for k in ("task", "status", "branch", "commit", "refusals")}, indent=1))
    return 2 if report["status"] == "refused" else (1 if report["status"] == "accepted_red" else 0)


if __name__ == "__main__":
    sys.exit(main())
