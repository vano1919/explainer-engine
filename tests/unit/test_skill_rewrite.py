"""RW-50 (owner rule 2026-11-20): every loaded skill is rewritten by at least half; the measure is code, not a claim."""
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


def test_upstream_reference_files_are_not_counted_but_our_skill_md_is(tmp_path):
    folder = tmp_path / ".claude" / "skills" / "v-demo"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text("ours\n", encoding="utf-8")
    (folder / "UPSTREAM_SKILL.md").write_text("theirs\n", encoding="utf-8")
    (folder / "references" / "a.md").write_text("theirs too\n", encoding="utf-8")
    (folder / "PROJECT_NOTES.md").write_text("ours too\n", encoding="utf-8")
    (folder / "SOURCE.md").write_text("repo: x\n\n" + "a" * 64 + "  SKILL.md\n" + "b" * 64 + "  references/a.md\n", encoding="utf-8")
    assert rw.our_files(folder) == ["SKILL.md", "PROJECT_NOTES.md"]
    text, where = rw.baseline_text(tmp_path, "v-demo")
    assert (text, where) == ("theirs\n", "upstream")


def test_every_skill_touched_on_this_branch_is_rewritten_by_at_least_half():
    """A skill is either still untouched (share 0, waiting for its wave) or rewritten to the minimum: no half-done rewrite."""
    rows = rw.report(ROOT)
    if all(r["status"] == "NOT_RUN" for r in rows):
        pytest.skip("baseline commit not in this clone (shallow checkout): RW-50 NOT_RUN")
    half_done = [(r["skill"], r["share"]) for r in rows if 0 < r["share"] < rw.MINIMUM]
    assert not half_done, half_done
    done = [r["skill"] for r in rows if r["status"] == "PASS"]
    assert len(done) >= 1


def test_every_rewritten_vendored_skill_keeps_its_upstream_text_pinned_and_names_the_folder():
    for folder in sorted((ROOT / rw.SKILLS).glob("v-*")):
        if not (folder / rw.UPSTREAM_SKILL).is_file():
            continue
        head = (folder / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        assert f"name: {folder.name}\n" in head, folder.name  # the loaded name is the folder name (no upstream name clash)
        assert "UPSTREAM_SKILL.md" in (folder / "SKILL.md").read_text(encoding="utf-8"), folder.name
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor_skill.py"), "verify"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


def test_cli_prints_the_table_and_the_rule_line():
    done = subprocess.run([sys.executable, "-m", "explainer_engine.governance.skill_rewrite"], cwd=ROOT, capture_output=True, text=True)
    assert "RW-50:" in done.stdout and "| skill |" in done.stdout
