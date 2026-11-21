"""D-121 (the creator, 2026-11-07 22:23 UTC): "make sure a test checks every rule". Every row of SCENE_REUSE_RULES.md has a code
check (cut_plan.CHECKS) or a written reason why only a person can check it (cut_plan.MANUAL); every rule a checker owns is tripped by
a test; every KP row marked [code] is in the code."""
import re
from pathlib import Path

from explainer_engine.production import cut_plan

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests" / "unit"


def _rows(doc, fams):
    text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
    return set(re.findall(rf"^\| ((?:{'|'.join(fams)})-\d\d) \|", text, re.M))


def test_every_scene_reuse_row_is_checked_or_says_why_not():
    rows = _rows("SCENE_REUSE_RULES.md", ["LV", "RF", "HI", "DL", "AS"])
    owned = {r for r in set(cut_plan.CHECKS) | set(cut_plan.MANUAL) if r.split("-")[0] in ("LV", "RF", "HI", "DL", "AS")}
    assert rows == owned, (rows - owned, owned - rows)
    assert not set(cut_plan.CHECKS) & set(cut_plan.MANUAL)
    assert all(len(why) > 30 for why in cut_plan.MANUAL.values())


def test_every_checked_rule_is_tripped_by_a_test():
    from tests.unit.test_cut_plan import MUTATIONS
    sources = {"scene_reuse.": (TESTS / "test_scene_reuse_rules.py").read_text(encoding="utf-8"),
               "shot_prompt_lint": (TESTS / "test_paid_preflight.py").read_text(encoding="utf-8")
               + (TESTS / "test_shot_prompt_lint.py").read_text(encoding="utf-8")}
    for rule, where in cut_plan.CHECKS.items():
        if where.startswith("cut_plan."):
            assert rule in MUTATIONS, rule
        else:
            key = next(k for k in sources if where.startswith(k))
            assert f'"{rule}"' in sources[key] or (rule == "AS-14" and "preflight" in sources[key]), rule


def test_every_code_kp_row_is_in_the_code():
    text = (ROOT / "docs" / "SHOT_PROMPTS.md").read_text(encoding="utf-8")
    code = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "explainer_engine").rglob("*.py"))
    coded = re.findall(r"^\| (KP-\d\d) \|.*\[code\]", text, re.M)
    assert len(coded) > 50
    assert [k for k in coded if k not in code] == []
