from pathlib import Path
import json
import pytest

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "tests" / "unit" / "data" / "retired_refs_baseline.json"
TERMS = ("Qwen-Image", "xworld_v2")
ALLOWED_WORDS = ("legacy", "retired", "deprecated")


def _line_has_term(line: str) -> bool:
    return any(term in line for term in TERMS)


def _line_has_allowed_word(line: str) -> bool:
    lowered = line.lower()
    return any(word in lowered for word in ALLOWED_WORDS)


def _is_heading(line: str) -> bool:
    return line.lstrip().startswith("#")


def _paragraph_allowed(lines, index):
    start = index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = index
    while end < len(lines) - 1 and lines[end + 1].strip():
        end += 1
    return any(_line_has_allowed_word(lines[i]) for i in range(start, end + 1))


def _heading_allowed(lines, index):
    heading_idx = None
    for idx in range(index, -1, -1):
        if _is_heading(lines[idx]):
            heading_idx = idx
            break
    if heading_idx is None:
        return False
    return _line_has_allowed_word(lines[heading_idx])


def _line_is_violation(lines, index):
    line = lines[index]
    if not _line_has_term(line):
        return False
    return not (_paragraph_allowed(lines, index) or _heading_allowed(lines, index))


def violation_lines(path: Path) -> list[int]:
    """Return 1-indexed line numbers of retired-term violations in path."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [idx + 1 for idx, line in enumerate(lines) if _line_is_violation(lines, idx)]


def current_violations(root: Path = ROOT) -> dict[str, int]:
    """Return {relative path: violation count} for files with at least one violation."""
    candidate_files = []
    docs = root / "docs"
    if docs.exists():
        candidate_files.extend(docs.rglob("*.md"))
    skills = root / ".claude" / "skills"
    if skills.exists():
        candidate_files.extend(skills.rglob("*.md"))
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        candidate_files.append(claude_md)

    unique_files = list(dict.fromkeys(candidate_files))
    violations = {}
    for file_path in unique_files:
        count = len(violation_lines(file_path))
        if count:
            rel = file_path.relative_to(root)
            violations[str(rel)] = count
    return violations


def test_baseline_file_exists_and_is_valid_json():
    assert BASELINE_PATH.exists(), f"baseline file missing: {BASELINE_PATH}"
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "baseline must be a JSON object"
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in data.items()), \
        "baseline must map relative paths to ints"


def test_no_new_retired_references():
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    current = current_violations()
    failing = []
    for rel_path, current_count in current.items():
        allowed = baseline.get(rel_path, 0)
        if current_count > allowed:
            lines = violation_lines(ROOT / rel_path)
            failing.append(
                f"{rel_path}: baseline allows {allowed}, found {current_count}; "
                f"violation lines {lines}"
            )
    if failing:
        pytest.fail("New retired-term references found:\n" + "\n".join(failing))


def test_legacy_wording_is_allowed(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    allowed_file = docs / "allowed.md"
    allowed_file.write_text("## Legacy route\nQwen-Image is mentioned.\n", encoding="utf-8")
    disallowed_file = docs / "disallowed.md"
    disallowed_file.write_text("## Plain route\nQwen-Image is mentioned.\n", encoding="utf-8")

    result = current_violations(tmp_path)

    assert str(allowed_file.relative_to(tmp_path)) not in result
    assert result[str(disallowed_file.relative_to(tmp_path))] == 1
