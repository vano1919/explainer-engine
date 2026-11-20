#!/usr/bin/env python
"""Mutation spot-check of a new module against its acceptance tests (tester, 2026-11-20; Gemini code lane, review step 6).

Why: a Gemini PR is green when its tests pass; that says nothing about whether the tests would notice a wrong implementation. This script makes
small deliberate mistakes in the implementation (a ``<`` turned into ``<=``, a ``+`` into ``-``, a constant doubled, ``and`` into ``or``, a
branch sign flipped) one at a time, runs the task's tests against each broken copy and reports the mistakes the tests did NOT notice (survivors).
Generic: it reads only the implementation's syntax tree, so it works on code written by anyone.

    python scripts/mutation_spot_check.py explainer_engine/production/fx25d/breath_embers.py tests/unit/test_breath_embers.py
        [--max 40] [--seed 1] [--timeout 180] [--min-score 0.75] [--json out.json] [--base <git sha>] [--repo <root>] [--boundaries]

The implementation file is overwritten with each mutant IN PLACE (the tests import it from its package path) and always restored from a backup,
also on Ctrl-C or a crash; do not run two checks on the same file at once. Free, offline, numpy-era speed: one pytest run per mutant.
A survivor is not proof of a weak test: some mutations change nothing observable (equivalent mutants), so the report prints the line and the
change and a human reads each one. Mark a line the check must skip with ``# nomutate``. Exit code 0 = score at or above ``--min-score`` and, with
``--base``, no existing test file changed; 1 otherwise; 2 = the unmutated tests already fail (nothing to measure).
``--base`` also checks invariant 10: it lists tests/ files that existed at that commit and were edited or deleted (new test files are fine)."""
from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Div, ast.Mod: ast.Mult, ast.Pow: ast.Mult}
BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


@dataclass
class Site:
    index: int
    line: int
    kind: str
    before: str
    after: str


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _annotation_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        anns = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            anns += [a.annotation for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs if a.annotation]
            anns += [node.returns] if node.returns else []
        elif isinstance(node, ast.AnnAssign):
            anns.append(node.annotation)
        for a in anns:
            ids.update(id(n) for n in ast.walk(a))
    return ids


class _Walker(ast.NodeTransformer):
    """Counts the mutation sites; when ``target`` is set, changes exactly that one."""

    def __init__(self, skip_lines: set[int], skip_ids: set[int], target: int | None = None, boundaries: bool = False):
        self.skip_lines, self.skip_ids, self.target, self.boundaries = skip_lines, skip_ids, target, boundaries
        self.n = 0
        self.sites: list[Site] = []

    def _take(self, node, kind: str, before: str, after: str) -> bool:
        if getattr(node, "lineno", 0) in self.skip_lines or id(node) in self.skip_ids:
            return False
        self.sites.append(Site(self.n, node.lineno, kind, before, after))
        hit = self.target == self.n
        self.n += 1
        return hit

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            new = CMP_SWAP.get(type(op))
            if new and not self.boundaries and type(op) in (ast.Lt, ast.LtE, ast.Gt, ast.GtE) and new in (ast.Lt, ast.LtE, ast.Gt, ast.GtE):
                continue                                                           # < <-> <= is nearly always an equivalent mutant on floats (--boundaries)
            if new and self._take(node, "compare", type(op).__name__, new.__name__):
                node.ops[i] = new()
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        new = BIN_SWAP.get(type(node.op))
        if new and self._take(node, "arith", type(node.op).__name__, new.__name__):
            node.op = new()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        new = BOOL_SWAP.get(type(node.op))
        if new and self._take(node, "boolop", type(node.op).__name__, new.__name__):
            node.op = new()
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, (ast.USub, ast.Not)) and self._take(node, "unary", type(node.op).__name__, "removed"):
            return node.operand
        return node

    def visit_Constant(self, node):
        v = node.value
        if isinstance(v, bool):
            if self._take(node, "bool", str(v), str(not v)):
                return ast.copy_location(ast.Constant(value=not v), node)
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0:      # zeros are guards and starting values: equivalent mutants
            new = v * 2 if v not in (0, 0.0) else 1
            if v == 1:
                new = 2
            if self._take(node, "number", repr(v), repr(new)):
                return ast.copy_location(ast.Constant(value=new), node)
        return node


def collect(src: str, boundaries: bool = False) -> tuple[ast.Module, list[Site]]:
    tree = ast.parse(src)
    skip_lines = {i + 1 for i, line in enumerate(src.splitlines()) if "nomutate" in line}
    skip_ids = _docstring_ids(tree) | _annotation_ids(tree)
    w = _Walker(skip_lines, skip_ids, boundaries=boundaries)
    w.visit(copy.deepcopy(tree))
    return tree, w.sites


def mutate(src: str, index: int, boundaries: bool = False) -> str:
    tree = ast.parse(src)
    skip_lines = {i + 1 for i, line in enumerate(src.splitlines()) if "nomutate" in line}
    w = _Walker(skip_lines, _docstring_ids(tree) | _annotation_ids(tree), target=index, boundaries=boundaries)
    out = w.visit(tree)
    ast.fix_missing_locations(out)
    return ast.unparse(out)


def run_tests(repo: Path, tests: list[str], timeout: int) -> tuple[bool, str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--tb=line", *tests]
    try:
        env = {**os.environ, "PYTHONPATH": str(repo)}
        p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "timeout (counts as killed: the mutant hangs)"
    last = (p.stdout.strip().splitlines() or [""])[-1]
    return p.returncode == 0, last


def tests_changed_since(repo: Path, base: str) -> list[str]:
    p = subprocess.run(["git", "diff", "--name-status", base, "--", "tests/"], cwd=repo, capture_output=True, text=True)
    bad = []
    for row in p.stdout.splitlines():
        status, _, path = row.partition("\t")
        if status[:1] in ("M", "D", "R"):
            bad.append(f"{status} {path}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("impl")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--max", type=int, default=40, help="mutants to try (a seeded sample spread over the sites)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--min-score", type=float, default=0.75)
    ap.add_argument("--json", default="")
    ap.add_argument("--repo", default="", help="root holding the package and the tests (default: this repository; a scratch copy works too)")
    ap.add_argument("--boundaries", action="store_true", help="also mutate < <-> <= and > <-> >= (mostly equivalent mutants on floats)")
    ap.add_argument("--base", default="", help="git sha: also list existing tests/ files edited or deleted since it (invariant 10)")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve() if a.repo else Path(__file__).resolve().parents[1]
    impl = (repo / a.impl) if not Path(a.impl).is_absolute() else Path(a.impl)
    original = impl.read_text()
    _, sites = collect(original, a.boundaries)
    if not sites:
        print("no mutation sites found")
        return 1
    ok0, last0 = run_tests(repo, a.tests, a.timeout * 2)
    if not ok0:
        print("the unmutated tests already fail, nothing to measure:", last0)
        return 2
    rnd = random.Random(a.seed)
    chosen = sorted(rnd.sample(sites, min(a.max, len(sites))), key=lambda s: s.index)
    backup = impl.with_suffix(impl.suffix + ".mutbak")
    shutil.copy2(impl, backup)
    rows = []
    t0 = time.time()
    try:
        for s in chosen:
            try:
                src = mutate(original, s.index, a.boundaries)
                compile(src, str(impl), "exec")
            except Exception as e:  # a mutation that is not valid code is skipped, not counted
                rows.append({**s.__dict__, "result": "invalid", "note": repr(e)})
                continue
            impl.write_text(src)
            passed, last = run_tests(repo, a.tests, a.timeout)
            rows.append({**s.__dict__, "result": "SURVIVED" if passed else "killed", "note": last})
            print(f"  line {s.line:4d} {s.kind:8s} {s.before:>9s} -> {s.after:<9s} {'SURVIVED' if passed else 'killed'}", flush=True)
    finally:
        shutil.copy2(backup, impl)
        backup.unlink(missing_ok=True)
    assert impl.read_text() == original, "the implementation was not restored"
    killed = sum(r["result"] == "killed" for r in rows)
    survived = [r for r in rows if r["result"] == "SURVIVED"]
    score = killed / max(1, killed + len(survived))
    print(f"\nmutants tried {len(rows)} of {len(sites)} sites: killed {killed}, survived {len(survived)}, score {score:.0%} "
          f"({time.time() - t0:.0f} s); threshold {a.min_score:.0%}")
    lines = original.splitlines()
    for r in survived:
        print(f"  SURVIVOR line {r['line']}: {r['kind']} {r['before']} -> {r['after']}   | {lines[r['line'] - 1].strip()[:110]}")
    weakened = tests_changed_since(repo, a.base) if a.base else []
    if a.base:
        print("existing tests edited or deleted since base:", weakened or "none")
    if a.json:
        Path(a.json).write_text(json.dumps({"impl": a.impl, "tests": a.tests, "sites": len(sites), "tried": len(rows), "killed": killed,
                                            "survived": len(survived), "score": score, "min_score": a.min_score,
                                            "tests_weakened": weakened, "rows": rows}, indent=1))
    return 0 if score >= a.min_score and not weakened else 1


if __name__ == "__main__":
    raise SystemExit(main())
