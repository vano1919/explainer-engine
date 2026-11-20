"""RW-50 (owner rule, 2026-11-20): every loaded skill is rewritten by at least half against the baseline of 2026-11-20.

The owner's words (cmsg_01Hnu5zB86sjUj5GtTgaUkPWNNvx3o1PK2FXoWi85XNDV9): every skill must be rewritten by at least 50 %, as a
minimum. The measure is the loaded instruction text of each skill folder ``.claude/skills/<name>/``: ``SKILL.md`` plus every other
``.md`` file that is ours (a vendored folder's upstream reference files are byte-pinned third-party text listed in its
``SOURCE.md`` and are not counted; the owner chose "SKILL.md only" for them on 2026-11-20).

Baseline text per skill:
- a vendored folder that carries ``UPSTREAM_SKILL.md`` (the upstream ``SKILL.md`` moved aside, byte-pinned by
  ``tools/vendor_skill.py verify``): that file;
- otherwise the folder's ``SKILL.md`` (and our other ``.md`` files) at the git commit ``BASELINE`` (the branch point of the
  rewrite, 2026-11-20); a skill absent at the baseline is new and counts 1.0.

Share: lines are compared after whitespace is collapsed, blank lines dropped. ``kept`` is the number of lines in matching blocks
(difflib, no autojunk). ``replaced = 1 - kept/old`` (how much of the old text is gone) and ``new = 1 - kept/new`` (how much of
the new text is new). The rewrite share is the smaller of the two, so neither appending to an untouched text nor cutting a text
down passes. stdlib only.

    python -m explainer_engine.governance.skill_rewrite            # table, exit 1 if any skill is under the minimum
    python -m explainer_engine.governance.skill_rewrite --json
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = Path(".claude") / "skills"
BASELINE = "5e6dc41aabe8b981957bd32700570347b1598614"  # W8 phase B head, the base of the RW-50 branch (2026-11-20)
MINIMUM = 0.5
UPSTREAM_SKILL = "UPSTREAM_SKILL.md"
NOT_LOADED = {"_archive"}  # Claude Code loads .claude/skills/<name>/SKILL.md only; _archive is never loaded


def lines(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        ln = re.sub(r"\s+", " ", raw).strip()
        if ln:
            out.append(ln)
    return out


def measure(old: str, new: str) -> dict:
    """Share of rewritten text between two versions (see the module doc)."""
    a, b = lines(old), lines(new)
    if not a:
        return {"old": 0, "new": len(b), "kept": 0, "replaced": 1.0, "new_share": 1.0, "share": 1.0}
    kept = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    replaced = 1 - kept / len(a)
    new_share = 1 - kept / len(b) if b else 0.0
    return {"old": len(a), "new": len(b), "kept": kept, "replaced": round(replaced, 4), "new_share": round(new_share, 4),
            "share": round(min(replaced, new_share), 4)}


def _upstream_files(folder: Path) -> set[str]:
    src = folder / "SOURCE.md"
    if not src.is_file():
        return set()
    return {m.group(1) for m in re.finditer(r"^[0-9a-f]{64}  (.+)$", src.read_text(encoding="utf-8"), re.M)}


def our_files(folder: Path) -> list[str]:
    """The .md files of a skill folder that are ours: SKILL.md first, then the rest sorted (upstream-pinned files left out)."""
    upstream = _upstream_files(folder)
    rels = []
    for p in sorted(folder.rglob("*.md")):
        rel = p.relative_to(folder).as_posix()
        if rel in ("SOURCE.md", UPSTREAM_SKILL):
            continue
        if rel in upstream and rel != "SKILL.md":  # the loaded SKILL.md always counts, rewritten or not
            continue
        rels.append(rel)
    return sorted(rels, key=lambda r: (r != "SKILL.md", r))


def _git_show(root: Path, baseline: str, rel: str) -> str | None:
    done = subprocess.run(["git", "show", f"{baseline}:{rel}"], cwd=root, capture_output=True)
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


def baseline_text(root: Path, name: str, baseline: str = BASELINE) -> tuple[str, str]:
    """(text, where) of a skill's baseline; where is 'upstream', 'git', 'new' or 'git-missing'."""
    folder = root / SKILLS / name
    if (folder / UPSTREAM_SKILL).is_file():
        return (folder / UPSTREAM_SKILL).read_text(encoding="utf-8"), "upstream"
    done = subprocess.run(["git", "cat-file", "-e", baseline], cwd=root, capture_output=True)
    if done.returncode != 0:
        return "", "git-missing"
    parts = []
    tree = subprocess.run(["git", "ls-tree", "-r", "--name-only", baseline, f"{(SKILLS / name).as_posix()}/"], cwd=root,
                          capture_output=True, text=True).stdout.split()
    upstream = _upstream_files(folder)
    for rel in sorted(tree, key=lambda r: (not r.endswith("/SKILL.md"), r)):
        short = rel.split(f"{name}/", 1)[1]
        if not rel.endswith(".md") or short == "SOURCE.md" or (short in upstream and short != "SKILL.md"):
            continue
        text = _git_show(root, baseline, rel)
        if text is not None:
            parts.append(text)
    return ("\n".join(parts), "git") if parts else ("", "new")


def skill_names(root: Path) -> list[str]:
    base = root / SKILLS
    return sorted(d.name for d in base.iterdir() if d.is_dir() and d.name not in NOT_LOADED and (d / "SKILL.md").is_file())


def report(root: Path | str = ROOT, baseline: str = BASELINE, minimum: float = MINIMUM) -> list[dict]:
    root = Path(root)
    rows = []
    for name in skill_names(root):
        folder = root / SKILLS / name
        old, where = baseline_text(root, name, baseline)
        new = "\n".join((folder / rel).read_text(encoding="utf-8") for rel in our_files(folder))
        row = {"skill": name, "baseline": where, "files": our_files(folder), **measure(old, new)}
        if where == "git-missing":
            row["status"] = "NOT_RUN"
        else:
            row["status"] = "PASS" if row["share"] >= minimum else "FAIL"
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--min", type=float, default=MINIMUM)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rows = report(args.root, args.baseline, args.min)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        print("| skill | baseline | old lines | new lines | kept | replaced | new | share | status |")
        print("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| `{r['skill']}` | {r['baseline']} | {r['old']} | {r['new']} | {r['kept']} | {r['replaced']:.0%} | "
                  f"{r['new_share']:.0%} | {r['share']:.0%} | {r['status']} |")
        bad = [r["skill"] for r in rows if r["status"] != "PASS"]
        print(f"\nRW-50: {len(rows) - len(bad)} of {len(rows)} skills at or above {args.min:.0%}; not passing: {', '.join(bad) or 'none'}")
    return 1 if any(r["status"] != "PASS" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
