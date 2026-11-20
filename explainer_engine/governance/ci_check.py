"""The CI job ``owner-requirements`` (spec section 7.3, owner 2026-11-20 08:37 UTC): fails the pull request when the owner's registry is
missing or empty (REG-MISSING), invalid (REG-*), has an active entry that is unmapped (REQ-UNMAPPED), a validator without its code, its
test or its negative test (REQ-NOVALIDATOR, REQ-NOTEST, REQ-NONEGATIVE), a judge without a rubric (REQ-NOJUDGE), lost an id or changed an
owner's words against the base branch (REG-REMOVED, REG-WORDS-CHANGED), or when any test the registry names fails (REQ-TESTFAIL).
An open conflict is printed, not failed (it blocks layers, not merges).

    python -m explainer_engine.governance.ci_check [--base origin/main] [--no-tests]

stdlib only; the workflow ``.github/workflows/owner-requirements.yml`` runs it and the owner makes the job a required status check
(docs/OWNER_REQUIREMENTS_CI_STEPS.md)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from explainer_engine.governance import owner_requirements as OR
from explainer_engine.governance import root_dir


def base_entries(base: str, root: Path) -> list[dict] | None:
    """The registry as the base branch has it (None: the base has no registry yet, nothing to compare)."""
    r = subprocess.run(["git", "-C", str(root), "show", f"{base}:{OR.REGISTRY.as_posix()}"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    rows = [e for e in data.get("requirements", []) if isinstance(e, dict)]
    return rows + [dict(e, kind="process") for e in data.get("process_requirements", []) if isinstance(e, dict)]   # R3: process rows count too


def named_tests(entries: list[dict]) -> list[str]:
    out = []
    for e in entries:
        c = e.get("check") if isinstance(e.get("check"), dict) else {}
        if e.get("status") == "active" and c.get("kind") == "validator":
            out += [t for t in (c.get("test"), c.get("negative_test")) if isinstance(t, str)]
    return list(dict.fromkeys(out))


def problems(root=None, *, base: str | None = None, run_tests: bool = True) -> tuple[list[str], list[str]]:
    """(failures, notes) of the job."""
    root = root_dir(root)
    entries, errs = OR.load(root)
    fails = errs + OR.missing(entries) + OR.check_registry(entries, root)
    notes = []
    for e in entries or []:
        if OR.is_conflict(e):
            if e.get("status") == "open":
                notes.append(f"open conflict {e.get('id')}: blocks its layers until the owner answers ({e.get('summary', '')[:80]})")
            continue
        if e.get("status") == "active":
            fails += OR._check_errs(e, root)
    if base:
        prior = base_entries(base, root)
        if prior is not None:
            fails += OR.compare_with_base(prior, entries)
        else:
            notes.append(f"{base} has no registry yet: nothing to compare (append-only starts with this one)")
    if run_tests and entries:
        tests = named_tests(entries)
        if tests:
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests], cwd=root, capture_output=True,
                               text=True, timeout=1800)
            if r.returncode != 0:
                fails.append("REQ-TESTFAIL: a test named by the registry fails:\n" + "\n".join((r.stdout + r.stderr).splitlines()[-25:]))
    return fails, notes


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.governance.ci_check")
    ap.add_argument("--base", help="the base branch ref to compare the registry with, e.g. origin/main")
    ap.add_argument("--no-tests", action="store_true", help="skip running the tests the registry names (they run in the next step)")
    a = ap.parse_args(argv)
    fails, notes = problems(base=a.base, run_tests=not a.no_tests)
    for n in notes:
        print(f"note: {n}")
    for f in fails:
        print(f"FAIL {f}")
    print("owner-requirements: " + ("FAIL" if fails else "ok"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
