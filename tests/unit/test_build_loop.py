"""The Fable/Opus build loop (llm/build_loop.py): parsing, placing and truncation handling; no API call."""
from explainer_engine.llm import build_loop as B

ANSWER = "=== FILE: a/x.py ===\nprint(1)\n=== FILE: a/y.py ===\nprint(2)\nTRUNCATED_AFTER a/y.py\n"


def test_parse_files_reads_every_block_and_drops_the_marker():
    files = B.parse_files(ANSWER)
    assert list(files) == ["a/x.py", "a/y.py"] and files["a/y.py"] == "print(2)\n"


def test_a_truncated_answer_keeps_only_the_whole_files():
    assert list(B.complete_files(ANSWER, truncated=True)) == ["a/x.py"]
    assert list(B.complete_files("=== FILE: a/x.py ===\nprint(1)\n", truncated=False)) == ["a/x.py"]


def test_place_writes_only_the_packages_files(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "ROOT", tmp_path)
    placed = B.place({"ok.txt": "1\n", "other.txt": "2\n"}, ["ok.txt"])
    assert placed == ["ok.txt"] and (tmp_path / "ok.txt").exists() and not (tmp_path / "other.txt").exists()
