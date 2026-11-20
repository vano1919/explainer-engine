"""docs/progress.d: one fragment file per change instead of appending to docs/PROGRESS.md (which every parallel branch edited at the same
spot, so each PR conflicted with the next one). The checker keeps the fragments uniform; ``assemble`` joins them in filename order."""
import pytest

from explainer_engine import progress_fragments as PF

OK = "## 2026-11-20 — A change\n- Done: x. Tests: y. Cost $0.\n"


def put(d, name, text):
    (d / name).write_text(text, encoding="utf-8")


def test_the_repo_fragments_are_valid():
    assert PF.check(PF.DIR) == []


def test_good_fragment_passes(tmp_path):
    put(tmp_path, "2026-11-20-claude-lipsync.md", OK)
    assert PF.check(tmp_path) == []


@pytest.mark.parametrize("name,text,code", [
    ("lipsync.md", OK, "PF-01"),                                              # name lacks the date and branch slug
    ("2026-11-20-Bad Name.md", OK, "PF-01"),                                  # spaces and capitals
    ("2026-13-45-x.md", OK.replace("2026-11-20", "2026-13-45"), "PF-01"),                                         # not a date
    ("2026-11-20-x.md", "no heading\n- text\n", "PF-02"),                     # must start with '## YYYY-MM-DD — '
    ("2026-11-20-x.md", "## 2026-11-20 — T\n", "PF-03"),                      # heading only, no body
    ("2026-11-20-x.md", OK + "<<<<<<< HEAD\n", "PF-04"),                      # conflict marker
    ("2026-11-20-x.md", "## 2026-11-19 — T\n- body\n", "PF-05"),              # heading date differs from the file's date
])
def test_each_code_triggers_exactly_once(tmp_path, name, text, code):
    put(tmp_path, name, text)
    assert [f["rule"] for f in PF.check(tmp_path)] == [code]


def test_non_utf8_is_a_finding_not_a_crash(tmp_path):
    (tmp_path / "2026-11-20-x.md").write_bytes(b"\xff\xfe\x00bad")
    assert [f["rule"] for f in PF.check(tmp_path)] == ["PF-06"]


def test_readme_and_other_files_are_ignored(tmp_path):
    put(tmp_path, "README.md", "how it works")
    put(tmp_path, "notes.txt", "x")
    assert PF.check(tmp_path) == []


def test_assemble_orders_by_filename_and_keeps_every_body(tmp_path):
    put(tmp_path, "2026-11-21-b.md", "## 2026-11-21 — B\n- b\n")
    put(tmp_path, "2026-11-20-a.md", "## 2026-11-20 — A\n- a\n")
    out = PF.assemble(tmp_path)
    assert out.index("— A") < out.index("— B") and "- a" in out and "- b" in out


def test_two_fragments_never_touch_the_same_file(tmp_path):
    # the point of the mechanism: different branches write different files
    put(tmp_path, "2026-11-20-claude-one.md", OK)
    put(tmp_path, "2026-11-20-claude-two.md", OK)
    assert len(list(tmp_path.glob("*.md"))) == 2 and PF.check(tmp_path) == []


def test_main_exit_codes(tmp_path, capsys):
    put(tmp_path, "2026-11-20-x.md", OK)
    assert PF.main(["check", "--dir", str(tmp_path)]) == 0
    put(tmp_path, "bad.md", OK)
    assert PF.main(["check", "--dir", str(tmp_path)]) == 1
    assert "PF-01" in capsys.readouterr().out
    assert PF.main(["assemble", "--dir", str(tmp_path / "none")]) == 2
