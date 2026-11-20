"""RW-50 (owner 2026-11-20): the share of new text per skill is measured in code and reported for information (team plan MS-6)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from explainer_engine.governance import skill_rewrite as rw

ROOT = Path(__file__).resolve().parents[2]
OLD = "\n".join(f"old rule number {i}" for i in range(20))


def test_identical_text_scores_zero_and_a_full_rewrite_scores_one():
    assert rw.measure(OLD, OLD)["share"] == 0.0
    assert rw.measure(OLD, "\n".join(f"new line {i}" for i in range(20)))["share"] == 1.0
    assert rw.measure("", "anything")["share"] == 1.0  # a new skill counts as new


def test_whitespace_and_blank_lines_do_not_count_as_change():
    spaced = "\n\n".join("  " + ln.replace(" ", "   ") for ln in OLD.splitlines())
    assert rw.measure(OLD, spaced)["share"] == 0.0


def test_appending_to_an_untouched_text_does_not_pass():
    padded = OLD + "\n" + "\n".join(f"padding {i}" for i in range(200))
    m = rw.measure(OLD, padded)
    assert m["new_share"] > 0.9 and m["replaced"] == 0.0 and m["share"] == 0.0


def test_cutting_a_text_down_does_not_pass():
    m = rw.measure(OLD, "\n".join(OLD.splitlines()[:3]))
    assert m["replaced"] > 0.8 and m["new_share"] == 0.0 and m["share"] == 0.0


def test_half_replaced_text_sits_on_the_line():
    half = "\n".join(OLD.splitlines()[:10] + [f"fresh {i}" for i in range(10)])
    assert rw.measure(OLD, half)["share"] == pytest.approx(0.5)


def test_vendored_upstream_files_are_not_counted_but_our_overlay_is(tmp_path):
    folder = tmp_path / ".claude" / "skills" / "v-demo"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text("theirs\n", encoding="utf-8")
    (folder / "OVERLAY.md").write_text("ours\n", encoding="utf-8")
    (folder / "references" / "a.md").write_text("theirs too\n", encoding="utf-8")
    (folder / "PROJECT_NOTES.md").write_text("ours too\n", encoding="utf-8")
    (folder / "SOURCE.md").write_text("repo: x\n\n" + "a" * 64 + "  SKILL.md\n" + "b" * 64 + "  references/a.md\n", encoding="utf-8")
    assert rw.our_files(folder) == ["OVERLAY.md", "PROJECT_NOTES.md"]


def test_the_report_is_information_only_and_strict_is_opt_in():
    rows = rw.report(ROOT)
    if all(r["status"] == "NOT_RUN" for r in rows):
        pytest.skip("baseline commit not in this clone (shallow checkout): RW-50 NOT_RUN")
    assert {r["status"] for r in rows} <= {"PASS", "FAIL", "NOT_RUN"}
    assert rw.main([]) == 0  # a share under 50 % never fails the suite (owner 07:14 UTC: MS-1..MS-7 are the rule)


def test_every_vendored_skill_md_is_the_upstream_text_and_overlays_are_ours():
    """Team plan rule 4: public text whole, never paraphrased; our rules for a vendored skill live in OVERLAY.md."""
    for folder in sorted((ROOT / rw.SKILLS).glob("v-*")):
        assert not (folder / "UPSTREAM_SKILL.md").exists(), folder.name  # the loaded SKILL.md is the upstream one again
        if (folder / rw.OVERLAY).is_file():
            assert "SKILL.md" in rw._upstream_files(folder), folder.name
            text = (folder / rw.OVERLAY).read_text(encoding="utf-8")
            assert text.startswith("# Overlay"), folder.name
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor_skill.py"), "verify"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


def test_cli_prints_the_table_and_the_rule_line():
    done = subprocess.run([sys.executable, "-m", "explainer_engine.governance.skill_rewrite"], cwd=ROOT, capture_output=True, text=True)
    assert "RW-50 (information):" in done.stdout and "| skill |" in done.stdout
