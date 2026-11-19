"""W1 (P-2, P-4): vendored public skills are byte-pinned, every archived rule id is mapped once, the stage index names them."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
spec = importlib.util.spec_from_file_location("vendor_skill", ROOT / "tools" / "vendor_skill.py")
vendor = importlib.util.module_from_spec(spec)
sys.modules["vendor_skill"] = vendor
spec.loader.exec_module(vendor)

VENDORED = sorted(d for d in SKILLS.glob("v-*") if d.is_dir())
ARCHIVED = ["video-editing-architect", "shot-visuals", "animation-principles", "animated-universe", "editing-style", "lora-training"]
ID = re.compile(r"\b[A-Z]{2,5}-[0-9]{2,3}[a-z]?\b")


def test_there_are_vendored_skills_and_each_loads_at_depth_one_with_a_source_file():
    assert len(VENDORED) >= 39
    for d in VENDORED:
        assert (d / "SKILL.md").is_file(), d.name  # Claude Code finds a project skill only at .claude/skills/<name>/SKILL.md
        assert (d / "SOURCE.md").is_file(), d.name
        assert not (d / ".claude").exists(), f"{d.name}: a nested .claude/skills would load as a project skill"
        meta, files = vendor.read_source(d)
        assert re.fullmatch(r"[0-9a-f]{40}", meta["commit"]) and files, d.name
        assert "NO LICENCE FILE" not in meta["licence"], d.name


def test_verify_passes_on_the_repository_and_the_cli_exits_zero():
    assert [p for d in VENDORED for p in vendor.verify_dir(d)] == []
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor_skill.py"), "verify"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


def test_verify_fails_on_a_changed_missing_or_extra_file(tmp_path):
    src = VENDORED[0]
    for kind in ("changed", "missing", "extra"):
        copy = tmp_path / kind / src.name
        shutil.copytree(src, copy)
        target = next(p for p in sorted(copy.rglob("*")) if p.is_file() and p.name != "SOURCE.md")
        if kind == "changed":
            target.write_bytes(target.read_bytes() + b"x")
        elif kind == "missing":
            target.unlink()
        else:
            (copy / "added.txt").write_text("x", encoding="utf-8")
        assert vendor.verify_dir(copy), kind
        done = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor_skill.py"), "verify", "--skills-dir", str(tmp_path / kind)],
                              capture_output=True, text=True)
        assert done.returncode == 1, kind
    broken = tmp_path / "nosource" / src.name
    shutil.copytree(src, broken)
    (broken / "SOURCE.md").unlink()
    assert vendor.verify_dir(broken) == [f"{src.name}: SOURCE.md missing"]


def test_the_six_skills_are_archived_not_deleted_and_no_longer_load():
    for name in ARCHIVED:
        assert (SKILLS / "_archive" / name / "SKILL.md").is_file(), name
        assert not (SKILLS / name).exists(), name


def _rows(path: Path) -> list[str]:
    return re.findall(r"^\|\s*`([A-Z]{2,5}(?:-[A-Z]{3})?-[0-9]{2,3}[a-z]?)`\s*\|", path.read_text(encoding="utf-8"), re.M)


def test_every_rule_id_of_the_archived_skills_is_in_the_rule_map_exactly_once():
    rows = _rows(ROOT / "docs" / "SKILL_RULE_MAP.md")
    ids: set[str] = set()
    for name in ARCHIVED:
        text = (SKILLS / "_archive" / name / "SKILL.md").read_text(encoding="utf-8")
        ids |= set(re.findall(r"CRAFT-[A-Z]{3}-[0-9]{2}", text))
        ids |= set(ID.findall(re.sub(r"CRAFT-[A-Z]{3}-[0-9]{2}", "", text)))
    assert len(ids) > 150
    missing = sorted(i for i in ids if rows.count(i) != 1)
    assert not missing, f"not exactly one row in docs/SKILL_RULE_MAP.md: {missing}"


def test_every_craft_checklist_rule_is_mapped_once_to_an_allowed_target_that_exists():
    text = (ROOT / "docs" / "SKILL_RULE_MAP.md").read_text(encoding="utf-8")
    ids = [c["id"] for f in sorted((ROOT / "explainer_engine" / "standards" / "craft_checklists").glob("*.json"))
           for c in json.loads(f.read_text(encoding="utf-8"))["criteria"]]
    assert len(ids) == 102
    for cid in ids:
        (row,) = [ln for ln in text.splitlines() if ln.startswith(f"| `{cid}` |")]
        cells = [c.strip() for c in row.strip("|").split("|")]
        mapping, target = cells[4], cells[5].strip("`")
        assert mapping in {"validator", "existing", "judgement", "hypothesis"}, cid
        if mapping == "validator":
            assert re.fullmatch(r"explainer_engine/validators/(story|narration|shots|prompts|pictures|clips|voice|timing|mix|edit|color|tech_qa|observe|subtitles|thumbnail|shorts)\.py", target), cid
        if mapping == "existing":
            assert (ROOT / target).is_file(), (cid, target)
        if mapping == "judgement":
            first = target.split(" ")[0]
            assert (SKILLS / first).is_dir() or first.startswith("cartography"), (cid, target)
    for ln in text.splitlines():  # section B: every home exists
        m = re.match(r"^\| `[A-Z]{2,5}-\d{2,3}[a-z]?` \| existing \| `([^`]+)`", ln)
        if m:
            assert (ROOT / m.group(1)).is_file(), ln


def test_the_docs_and_the_stage_index_name_every_vendored_skill():
    doc = (ROOT / "docs" / "VENDORED_SKILLS.md").read_text(encoding="utf-8")
    index = (SKILLS / "INDEX.md").read_text(encoding="utf-8")
    for d in VENDORED:
        assert f"`{d.name}`" in doc, d.name
        meta, _ = vendor.read_source(d)
        assert meta["commit"][:10] in doc, d.name
        assert d.name in index, d.name
    for stage in [f"S{i}" for i in range(1, 20)]:
        assert re.search(rf"^\| {stage} ", index, re.M), stage
