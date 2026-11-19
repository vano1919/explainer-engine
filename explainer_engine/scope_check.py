"""V4.1 slice scope check (D-139, plan Step 0.4b): a pull request of one V4.1 slice may change only the paths its slice lists.

The slices live in ``docs/architecture/v4_1_allowlists.json``. The list is read from the BASE ref, so a pull request cannot widen
its own scope; only the slice that introduces the file (no copy on the base yet) reads its own copy. A head branch that is no
slice branch is exempt (ordinary work, PR #195 and hotfixes); binding is the exact head branch of a slice, and a head branch
under ``slice_branch_prefix`` that no slice lists fails (unknown slice id). The control files themselves (the list, this checker, the
workflow) may appear only in the allowlist of the slice named in ``control_slice``.

CLI (CI): ``python -m explainer_engine.scope_check --base origin/<base> --head HEAD --head-ref <branch>``; exit 1 on a path
outside the slice. Needs full history (``fetch-depth: 0``)."""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

ALLOWLIST = "docs/architecture/v4_1_allowlists.json"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    """Every path the PR touches (three-dot diff from the merge base; renames count as delete + add)."""
    out = _git(root, "diff", "--name-only", "--no-renames", f"{base}...{head}")
    return sorted({p for p in out.splitlines() if p})


def load_allowlists(root: Path, base: str) -> dict:
    """The list from the base ref; the working copy only when the base has none (the slice that adds the file)."""
    try:
        return json.loads(_git(root, "show", f"{base}:{ALLOWLIST}"))
    except subprocess.CalledProcessError:
        return json.loads((root / ALLOWLIST).read_text(encoding="utf-8"))


def slice_for(cfg: dict, head_ref: str) -> tuple[str, dict] | None:
    for sid, entry in cfg["slices"].items():
        if entry["branch"] == head_ref:
            return sid, entry
    return None


def check(cfg: dict, head_ref: str, paths: list[str]) -> list[str]:
    """Problems (empty = pass). Pure function over the config, so it is testable without git."""
    found = slice_for(cfg, head_ref)
    if found is None:
        prefix = cfg.get("slice_branch_prefix")
        if prefix and head_ref.startswith(prefix):   # a V4.1 slice branch with an id nobody listed
            return [f"branch {head_ref} looks like a V4.1 slice branch ({prefix}*) but names no slice of the allowlist"]
        return []
    sid, entry = found
    problems = []
    control = set(cfg["control_files"])
    for sid2, e2 in cfg["slices"].items():
        if sid2 != cfg["control_slice"] and control & set(e2["paths"]):
            problems.append(f"slice {sid2} lists a control file; only slice {cfg['control_slice']} may")
    for p in paths:
        if not any(fnmatch.fnmatchcase(p, pat) for pat in entry["paths"]):
            problems.append(f"{p} is outside the allowlist of slice {sid}")
    return problems


def main(argv=None) -> int:
    a = argparse.ArgumentParser(prog="python -m explainer_engine.scope_check")
    a.add_argument("--base", required=True)
    a.add_argument("--head", default="HEAD")
    a.add_argument("--head-ref", required=True)
    a.add_argument("--root", default=".")
    args = a.parse_args(argv)
    root = Path(args.root)
    cfg = load_allowlists(root, args.base)
    if slice_for(cfg, args.head_ref) is None and not args.head_ref.startswith(cfg.get("slice_branch_prefix") or "\0"):
        print(f"scope: branch {args.head_ref} is no V4.1 slice branch; not enforced")
        return 0
    problems = check(cfg, args.head_ref, changed_paths(root, args.base, args.head))
    print("\n".join(problems) or "scope: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
