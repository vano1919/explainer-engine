"""Helpers of the governance tests: agent frontmatter, a throw-away repo with the config and the blueprint files."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".claude" / "agents"


def front(path: Path) -> dict:
    head = path.read_text(encoding="utf-8").split("---", 2)[1]
    out = {}
    for line in head.strip().splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def tools(path: Path) -> list[str]:
    return [t.strip() for t in front(path).get("tools", "").split(",") if t.strip()]


def make_repo(tmp: Path, *, git: bool = False) -> Path:
    """A copy of config/ and docs/blueprint/ in ``tmp`` (optionally a git repo with one commit)."""
    (tmp / "config").mkdir(parents=True)
    shutil.copy(ROOT / "config" / "model_routing.json", tmp / "config")
    shutil.copy(ROOT / "config" / "spend_caps.json", tmp / "config")
    shutil.copytree(ROOT / "docs" / "blueprint", tmp / "docs" / "blueprint")
    if git:
        run = lambda *a: subprocess.run(["git", "-C", str(tmp), *a], check=True, capture_output=True, text=True)
        run("init", "-q", "-b", "work")
        run("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return tmp


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def config() -> dict:
    return json.loads((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"))
