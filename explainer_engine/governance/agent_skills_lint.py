"""Validator for portable Agent Skills stored under ``.agents/skills/<name>/SKILL.md``."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"/mnt/project-files/"),
)
MAX_SKILL_LINES = 180


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Parse YAML frontmatter delimited by leading ``---`` lines."""
    if not text.startswith("---\n"):
        return None, text, "Missing leading YAML frontmatter delimiter '---'"
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return None, text, "Missing closing YAML frontmatter delimiter '---'"
    raw_yaml = parts[0][4:]
    body = parts[1]
    try:
        meta = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        return None, body, f"Invalid YAML frontmatter: {exc}"
    if not isinstance(meta, dict):
        return None, body, "YAML frontmatter must parse to a mapping"
    return meta, body, None


def validate_skill_file(skill_md: Path) -> list[str]:
    """Validate one portable ``.agents/skills/<name>/SKILL.md`` file."""
    errors: list[str] = []
    if not skill_md.is_file():
        return [f"Missing SKILL.md: {skill_md}"]
    text = skill_md.read_text(encoding="utf-8")
    meta, body, err = parse_frontmatter(text)
    if err or meta is None:
        return [f"{skill_md}: {err}"]

    name = meta.get("name")
    desc = meta.get("description")
    dir_name = skill_md.parent.name
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        errors.append(f"{skill_md}: invalid 'name' {name!r} (must be kebab-case)")
    elif name != dir_name:
        errors.append(f"{skill_md}: frontmatter name {name!r} does not match directory {dir_name!r}")

    if not isinstance(desc, str) or len(desc.strip()) < 20:
        errors.append(f"{skill_md}: 'description' must be a concise non-empty string (>=20 chars)")

    lines = text.splitlines()
    if len(lines) > MAX_SKILL_LINES:
        errors.append(f"{skill_md}: exceeds progressive-disclosure line budget ({len(lines)} > {MAX_SKILL_LINES})")
    if not body.strip():
        errors.append(f"{skill_md}: body is empty")

    for pat in SECRET_PATTERNS:
        if pat.search(text):
            errors.append(f"{skill_md}: matched forbidden secret or hardcoded path pattern {pat.pattern!r}")
    return errors


def validate_all_skills(skills_dir: Path | None = None) -> dict[str, Any]:
    """Validate all portable skills under ``.agents/skills``."""
    root = skills_dir or AGENT_SKILLS_DIR
    if not root.is_dir():
        return {"ok": False, "skills": [], "errors": [f"Agent skills directory not found: {root}"]}
    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        return {"ok": False, "skills": [], "errors": [f"No skills found under {root}"]}
    errors: list[str] = []
    names: list[str] = []
    for d in skill_dirs:
        names.append(d.name)
        errors.extend(validate_skill_file(d / "SKILL.md"))
    return {"ok": len(errors) == 0, "skills": names, "errors": errors}


def main() -> int:
    res = validate_all_skills()
    if res["ok"]:
        print(f"agent_skills_lint: OK ({len(res['skills'])} skills: {', '.join(res['skills'])})")
        return 0
    for e in res["errors"]:
        print(f"ERROR: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
