"""A check may FAIL only on a binding rule, an invariant, or a house rule that quotes the creator's dated words; a check that is
driven by a hypothesis rule is REVIEW at most (D-59, CN-11). Two guards: the registry's own severities, and an AST walk over
the validators for an ``if`` on a hypothesis threshold that emits the literal "FAIL"."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def hypothesis_fails(source: str, status: dict[str, str]) -> list[tuple[int, str]]:
    """(line, rule) of every ``if`` whose test reads a hypothesis threshold (directly or through a module constant) and whose
    body emits the string "FAIL"."""
    tree = ast.parse(source)
    consts: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            ids = {rid for rid, _k, _l in SR.threshold_reads(ast.unparse(node.value))}
            if ids:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            consts[n.id] = ids
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = ast.unparse(node.test)
        ids = {rid for rid, _k, _l in SR.threshold_reads(test)}
        ids |= set().union(*[consts.get(n.id, set()) for n in ast.walk(node.test) if isinstance(n, ast.Name)])
        hyp = sorted(r for r in ids if status.get(r) == "hypothesis")
        if hyp and any(isinstance(n, ast.Constant) and n.value == "FAIL" for s in node.body for n in ast.walk(s)):
            found.append((node.lineno, hyp[0]))
    return found


def test_no_validator_fails_on_a_hypothesis_threshold():
    status = {r["id"]: r["status"] for r in SR.rules()}
    bad = []
    for p in sorted((ROOT / "explainer_engine").rglob("*.py")):
        bad += [f"{p.relative_to(ROOT).as_posix()}:{line} FAILs on hypothesis {rid}" for line, rid in hypothesis_fails(p.read_text(encoding="utf-8"), status)]
    assert bad == [], "a hypothesis is REVIEW at most (use sourced_rules.level):\n" + "\n".join(bad)


def test_the_walk_catches_a_hypothesis_fail_and_lets_a_binding_one_through():
    src = ('LIMIT = SR.T("BP-108", "clip_max_s")\n'
           'def a(s, out):\n    if s > LIMIT:\n        out.append("FAIL")\n'
           'def b(s, out):\n    if s > SR.T("BP-108", "keypose_after_s"):\n        out.append(("x", "FAIL"))\n'
           'def c(s, out):\n    if s > SR.T("BP-12", "slack"):\n        out.append("FAIL")\n'
           'def d(s, out):\n    if s > LIMIT:\n        out.append(SR.level("BP-108"))\n')
    status = {"BP-108": "hypothesis", "BP-12": "binding"}
    assert [rid for _l, rid in hypothesis_fails(src, status)] == ["BP-108", "BP-108"]


def test_level_caps_a_hypothesis_and_leaves_binding_and_house():
    hyp = next(r["id"] for r in SR.rules() if r["status"] == "hypothesis")
    binding = next(r["id"] for r in SR.rules() if r["status"] == "binding")
    house = next(r["id"] for r in SR.rules() if r["status"] == "house")
    assert SR.level(hyp) == "REVIEW" and SR.level(binding) == "FAIL" and SR.level(house) == "FAIL"
    assert SR.level(hyp, "INFO") == "INFO"


def test_only_binding_or_house_rules_declare_fail():
    for r in SR.rules():
        if r.get("severity") == "FAIL":
            assert r["status"] in {"binding", "house"}, r["id"]
        if r["status"] == "house" and r.get("severity") == "FAIL":
            assert r.get("decided"), f"{r['id']}: a house FAIL quotes the creator's dated words"


def test_the_blueprint_numbers_stay_below_fail():
    """BP-29 (safe zone), BP-114 (clip geometry): one source type each, so REVIEW. The P3/P5 rules named in the plan are pinned
    when they arrive: a map-share rule is REVIEW, the register word tier is a house FAIL with the creator's dated words."""
    assert SR.severity("BP-29") == "REVIEW" and SR.severity("BP-114") == "REVIEW"
    for r in SR.rules():
        if any(k.startswith("map_pure") for k in r["thresholds"]):
            assert r["status"] == "hypothesis" and r.get("severity") == "REVIEW", r["id"]
        if "register_words" in r["thresholds"]:
            assert r["status"] == "house" and r.get("severity") == "FAIL" and r.get("decided"), r["id"]


@pytest.mark.parametrize("rid", ["BP-114"])
def test_a_new_rule_names_its_two_source_urls(rid):
    assert len(SR.rule(rid)["sources"]) >= 2
