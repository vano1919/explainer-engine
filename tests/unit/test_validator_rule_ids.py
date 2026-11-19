"""W2: every validator module declares unique RULE_IDS; the 33 planned CRAFT rules are owned; docs/SKILL_RULE_MAP.md (W1) agrees."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from explainer_engine import validators as V

ROOT = Path(__file__).resolve().parents[2]


def _planned_ids() -> set[str]:
    """The CRAFT ids whose checklist row says ``(planned`` in the skills of this branch (and in the archived skills)."""
    out = set()
    for md in list((ROOT / ".claude" / "skills").rglob("SKILL.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            m = re.search(r"\|\s*(CRAFT-[A-Z]+-\d+)\s*\|", line)
            if m and "(planned" in line:
                out.add(m.group(1))
    return out


def test_every_rule_id_is_unique_across_modules():
    seen: dict[str, str] = {}
    for stage in V.MODULES:
        mod = V.load(stage)
        assert isinstance(mod.RULE_IDS, tuple) and mod.RULE_IDS, stage
        assert len(set(mod.RULE_IDS)) == len(mod.RULE_IDS), f"{stage}: a rule id twice in one module"
        for rid in mod.RULE_IDS:
            assert rid not in seen, f"{rid} is in both {seen[rid]} and {stage}"
            seen[rid] = stage
    assert seen == V.rule_index()


def test_modules_use_the_fixed_stage_names():
    assert set(V.MODULES) <= set(V.STAGES)
    for stage in V.MODULES:
        assert (ROOT / "explainer_engine" / "validators" / f"{stage}.py").is_file()


def test_all_33_planned_craft_rules_have_a_validator():
    planned = _planned_ids()
    if not planned:
        pytest.skip("the skills no longer carry '(planned' rows (W1 moved or archived them)")
    owned = {r for r in V.rule_index() if r.startswith("CRAFT-")}
    assert planned <= owned, f"planned rules without a validator: {sorted(planned - owned)}"
    assert planned == owned and len(owned) == 33, sorted(owned)   # the brief says 34: its grep also matched an editing-style prose line, "(planned on the cuts)", which is no rule row; 21+5+2+2+1+1+1 = 33


def test_every_enforced_by_path_of_a_validator_rule_exists():
    from explainer_engine.standards import sourced_rules as SR
    assert SR.check() == []


def test_skill_rule_map_is_bidirectional_with_rule_ids():
    """W1's docs/SKILL_RULE_MAP.md: every row marked ``validator`` names ``validators/<stage>.py`` and its id is in that module's RULE_IDS;
    every RULE_IDS id the map lists is marked ``validator`` there, with its own module."""
    path = ROOT / "docs" / "SKILL_RULE_MAP.md"
    if not path.is_file():
        pytest.skip("docs/SKILL_RULE_MAP.md is W1's file and is not on this branch")
    idx = V.rule_index()
    listed, wrong = set(), []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`((?:CRAFT|VAL)-[A-Z]+-\d+)`\s*\|", line)
        if not m:
            continue
        rid, cells = m.group(1), [c.strip() for c in line.split("|")]
        mapping, target = cells[5], cells[6].strip("`")
        listed.add(rid)
        if mapping == "validator":
            mod = re.fullmatch(r"explainer_engine/validators/(\w+)\.py", target)
            if not mod or idx.get(rid) != mod.group(1):
                wrong.append(f"{rid}: marked validator -> {target}, but RULE_IDS puts it in {idx.get(rid)}")
        elif rid in idx:
            wrong.append(f"{rid}: is in validators/{idx[rid]}.py but the map says {mapping}")
    assert not wrong, wrong
    assert {r for r in idx if r.startswith("CRAFT-")} <= listed, "a CRAFT rule id of RULE_IDS is missing from the map"


def test_the_validators_read_thresholds_never_copy_them():
    """Every ``T("BP-xx", "key")`` a validator reads exists in the registry (a typo would silently become REVIEW)."""
    from explainer_engine.standards import sourced_rules as SR
    bad = []
    for f in (ROOT / "explainer_engine" / "validators").glob("*.py"):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"C\.T\(\"(BP-\d+)\",\s*\"(\w+)\"\)", src):
            try:
                SR.T(m.group(1), m.group(2))
            except KeyError:
                bad.append(f"{f.name}: {m.group(1)}.{m.group(2)}")
    assert not bad, bad
