#!/usr/bin/env python3
"""Vendor a public skill folder byte-for-byte at a pinned commit, and re-check it later (P-2, W1).

    python tools/vendor_skill.py add <owner/repo> <path-in-repo> <commit> --as v-<name> [options]
    python tools/vendor_skill.py verify [--skills-dir .claude/skills]
    python tools/vendor_skill.py table     # markdown rows for docs/VENDORED_SKILLS.md

``add`` fetches the repository at the exact commit (``git fetch --depth 1 <sha>``, public HTTPS, no credentials),
copies the folder ``<path-in-repo>`` ("." = repo root) to ``.claude/skills/v-<name>/`` and writes ``SOURCE.md`` there:
repo, path, commit, commit date, author, licence, stars seen, what was left out and a ``files:`` list of
``sha256  path``. The upstream files are never edited. ``verify`` re-hashes every vendored file and exits 1 on any
changed, missing or extra file or a missing SOURCE.md.

Left out on purpose (always listed in SOURCE.md ``excluded:``): ``.git``, ``.github``, ``.claude`` (a nested
``.claude/skills`` would load as a project skill), ``node_modules``, ``__pycache__``; media and model binaries
(``tests/unit/test_repo_hygiene.py`` forbids them in git); files whose names look like secrets; files larger than
``--max-bytes`` (default 1 MiB); and every ``--exclude`` glob (tests, demo media, sites).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
SKIP_DIRS = {".git", ".github", ".claude", "node_modules", "__pycache__", ".pytest_cache"}
MEDIA_EXT = (".mp4", ".wav", ".mp3", ".flac", ".onnx", ".gguf", ".bin", ".pyc")
SECRET_NAMES = re.compile(r"(api_key|token[^/]*\.json$|secret|credentials|id_ed25519|\.pem$|^\.env$)", re.I)
LICENCE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "NOTICE", "COPYING")
FILES_MARK = "files:"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def fetch(repo: str, commit: str, cache: Path) -> Path:
    """Checkout of ``repo`` at ``commit`` under ``cache`` (reused between calls)."""
    dest = cache / f"{repo.replace('/', '--')}@{commit[:12]}"
    if (dest / ".fetched").exists():
        return dest
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    _git("init", "-q", cwd=dest)
    _git("fetch", "-q", "--depth", "1", f"https://github.com/{repo}", commit, cwd=dest)
    _git("checkout", "-q", "FETCH_HEAD", cwd=dest)
    head = _git("rev-parse", "HEAD", cwd=dest)
    if not head.startswith(commit) and head != commit:
        raise SystemExit(f"{repo}: asked for {commit}, got {head}")
    (dest / ".fetched").write_text(head, encoding="utf-8")
    return dest


def _excluded(rel: str, size: int, patterns: list[str], max_bytes: int) -> str | None:
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return "skip-dir"
    name = parts[-1]
    if name.lower().endswith(MEDIA_EXT):
        return "media/binary"
    if SECRET_NAMES.search(name):
        return "secret-like name"
    if size > max_bytes:
        return f"larger than {max_bytes} bytes"
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or any(fnmatch.fnmatch("/".join(parts[: i + 1]), pat) for i in range(len(parts))):
            return f"--exclude {pat}"
    return None


def frontmatter_name(skill_md: Path) -> str | None:
    m = re.match(r"---\s*\n(.*?)\n---", skill_md.read_text(encoding="utf-8", errors="replace"), re.S)
    if not m:
        return None
    n = re.search(r"^name:\s*['\"]?([^'\"\n]+)", m.group(1), re.M)
    return n.group(1).strip() if n else None


def add(args: argparse.Namespace) -> int:
    name = args.as_name
    if not name.startswith("v-"):
        raise SystemExit("--as must start with v-")
    cache = Path(args.cache or tempfile.gettempdir()) / "vendor_skill_cache"
    cache.mkdir(parents=True, exist_ok=True)
    checkout = fetch(args.repo, args.commit, cache)
    commit = (checkout / ".fetched").read_text(encoding="utf-8").strip()
    src = checkout if args.path in (".", "") else checkout / args.path
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"{args.repo}:{args.path} has no SKILL.md")
    dest = Path(args.skills_dir) / name
    shutil.rmtree(dest, ignore_errors=True)
    copied: list[tuple[str, str]] = []
    left: dict[str, list[str]] = {}
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(src).as_posix()
        why = _excluded(rel, p.stat().st_size, args.exclude, args.max_bytes)
        if why:
            left.setdefault(why, []).append(rel)
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out)
        copied.append((sha256(out), rel))
    # licence files that live above the skill folder travel with it
    if src != checkout:
        for lic in LICENCE_NAMES:
            if (checkout / lic).is_file() and not (dest / lic).exists():
                shutil.copyfile(checkout / lic, dest / lic)
                copied.append((sha256(dest / lic), lic))
    licence_file = next((n for n in LICENCE_NAMES if (dest / n).is_file()), None)
    commit_date = _git("log", "-1", "--format=%cs", cwd=checkout)
    fm = frontmatter_name(dest / "SKILL.md")
    lines = [
        f"# SOURCE: {name}",
        "",
        f"repo: https://github.com/{args.repo}",
        f"path: {args.path}",
        f"commit: {commit}",
        f"commit_date: {commit_date}",
        f"retrieved: {args.retrieved}",
        f"author: {args.author or args.repo.split('/')[0]}",
        f"licence: {args.licence} ({licence_file or 'NO LICENCE FILE COPIED'})",
        f"stars_seen: {args.stars}",
        f"stage: {args.stage}",
        f"tool: tools/vendor_skill.py (byte-for-byte copy; upstream files are never edited)",
    ]
    if fm and fm != name:
        lines.append(f"name_clash: upstream frontmatter name '{fm}' differs from folder '{name}'; Claude Code uses the folder name")
    if args.note:
        lines.append(f"note: {args.note}")
    lines.append("excluded:")
    if not left:
        lines.append("  (nothing)")
    for why, items in sorted(left.items()):
        top = sorted({i.split("/")[0] for i in items})
        lines.append(f"  - {why}: {len(items)} files ({', '.join(top[:6])}{', ...' if len(top) > 6 else ''})")
    lines += ["", FILES_MARK]
    lines += [f"{h}  {rel}" for h, rel in sorted(copied, key=lambda t: t[1])]
    (dest / "SOURCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{name}: {len(copied)} files copied, {sum(len(v) for v in left.values())} left out @ {commit[:10]}")
    return 0


def read_source(skill_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    meta: dict[str, str] = {}
    files: dict[str, str] = {}
    in_files = False
    for line in (skill_dir / "SOURCE.md").read_text(encoding="utf-8").splitlines():
        if in_files:
            m = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if m:
                files[m.group(2)] = m.group(1)
        elif line.strip() == FILES_MARK:
            in_files = True
        else:
            m = re.match(r"([a-z_]+): (.*)", line)
            if m:
                meta[m.group(1)] = m.group(2)
    return meta, files


def verify_dir(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    if not (skill_dir / "SOURCE.md").is_file():
        return [f"{skill_dir.name}: SOURCE.md missing"]
    meta, files = read_source(skill_dir)
    for key in ("repo", "commit", "commit_date", "licence"):
        if not meta.get(key):
            problems.append(f"{skill_dir.name}: SOURCE.md has no '{key}'")
    if not re.fullmatch(r"[0-9a-f]{40}", meta.get("commit", "")):
        problems.append(f"{skill_dir.name}: commit is not a full sha")
    if not files:
        problems.append(f"{skill_dir.name}: SOURCE.md lists no files")
    on_disk = {p.relative_to(skill_dir).as_posix() for p in skill_dir.rglob("*") if p.is_file()} - {"SOURCE.md"}
    for rel in sorted(files):
        f = skill_dir / rel
        if not f.is_file():
            problems.append(f"{skill_dir.name}: missing {rel}")
        elif sha256(f) != files[rel]:
            problems.append(f"{skill_dir.name}: changed {rel}")
    for rel in sorted(on_disk - set(files)):
        problems.append(f"{skill_dir.name}: extra file not in SOURCE.md {rel}")
    return problems


def verify(args: argparse.Namespace) -> int:
    base = Path(args.skills_dir)
    dirs = sorted(d for d in base.glob("v-*") if d.is_dir())
    problems = [p for d in dirs for p in verify_dir(d)]
    for p in problems:
        print("FAIL", p)
    print(f"verify: {len(dirs)} vendored skills, {len(problems)} problems")
    return 1 if problems else 0


def table(args: argparse.Namespace) -> int:
    """Markdown table of every vendored skill (for docs/VENDORED_SKILLS.md)."""
    print("| Folder | Stage | Upstream | Path | Commit | Commit date | Licence | Files |")
    print("|---|---|---|---|---|---|---|---|")
    for d in sorted(Path(args.skills_dir).glob("v-*")):
        meta, files = read_source(d)
        repo = meta["repo"].replace("https://github.com/", "")
        print(f"| `{d.name}` | {meta.get('stage', '')} | {repo} | `{meta['path']}` | `{meta['commit'][:10]}` | "
              f"{meta['commit_date']} | {meta['licence'].split(' (')[0]} | {len(files)} |")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("repo")
    a.add_argument("path")
    a.add_argument("commit")
    a.add_argument("--as", dest="as_name", required=True)
    a.add_argument("--licence", default="MIT")
    a.add_argument("--author", default="")
    a.add_argument("--stars", default="not obtainable (GitHub API blocked in the session)")
    a.add_argument("--stage", default="")
    a.add_argument("--note", default="")
    a.add_argument("--exclude", action="append", default=[])
    a.add_argument("--max-bytes", type=int, default=1 << 20)
    a.add_argument("--cache", default="")
    a.add_argument("--retrieved", default=date.today().isoformat())
    a.add_argument("--skills-dir", default=str(SKILLS))
    v = sub.add_parser("verify")
    v.add_argument("--skills-dir", default=str(SKILLS))
    t = sub.add_parser("table")
    t.add_argument("--skills-dir", default=str(SKILLS))
    args = ap.parse_args(argv)
    return {"add": add, "verify": verify, "table": table}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
