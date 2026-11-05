"""Fable/Opus build loop for one work package (creator 2026-11-01, API line ``build_loop``; OR-35, OR-36).

    python -m explainer_engine.llm.build_loop run <wp.json> [--no-check]

The session orchestrates and reads only the printed summary (file names, test result, verdict lines, cost). A work package file::

    {"id": "WP-1a", "goal": "...", "wp_text_file": "path to the WP's section", "inputs": ["repo paths passed verbatim"],
     "files": ["repo paths the coder must write"], "tests": ["pytest args"], "check_question": "one line",
     "coder_max_tokens": 64000, "fix_max_tokens": 48000, "check_max_tokens": 16000}

Steps: coder (Opus, high) -> place files -> py_compile + tests -> check (Fable, high, short verdict) -> fix (Opus) up to twice.
Every call goes through ``llm/claude_api.py`` (caps, ledger, streams saved), never directly. A truncated coder answer is
continued per missing file only. Nothing here edits protected config.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOB = "build_loop"
FILE_RE = re.compile(r"^=== FILE: (.+?) ===\n", re.M)
RULES_CODER = (
    "You are the coder (Opus, high). Implement the work package exactly; do not re-decide. Verify facts with the read-only tools "
    "(list_dir, read_file, grep over the repo) or mark `# UNVERIFIED:`; never invent an API, flag, class or path. Match the repo "
    "style (line length ~120, Python 3.12). Output ONLY file blocks: a line `=== FILE: <repo-relative path> ===` then the complete "
    "file, no fences, no diffs. Write the files in the order given; if you cannot finish all, finish the current file fully and "
    "end with a line `TRUNCATED_AFTER <path>`. Think briefly: the answer must arrive.")
RULES_CHECK = (
    "You are the checker (Fable, high). Judge the files against the work package. Output lines only: `PASS <file>` or "
    "`FIX <file>:<line-or-symbol> - <one sentence>`, and the last line `VERDICT PASS` or `VERDICT FIX` or `VERDICT STOP` "
    "(STOP = the coder took a money or goal decision that belongs to the creator). Think briefly; no other text.")


def _run_job(work: Path, name: str, model: str, effort: str, max_tokens: int, system: dict, user: str, task_class: str) -> dict:
    d = work / name
    (d / "in").mkdir(parents=True, exist_ok=True)
    (d / "out").mkdir(exist_ok=True)
    names = []
    for i, (title, text) in enumerate(t for t in system.items() if t[1].strip()):   # the API refuses an empty block
        f = d / "in" / f"{i:02d}_{title}.txt"
        f.write_text(text, encoding="utf-8")
        names.append(f"in/{f.name}")
    job = {"job": JOB, "task_class": task_class, "model": model, "effort": effort, "max_tokens": max_tokens, "cache_ttl": "5m",
           "system_files": names, "requests": [{"id": name.upper().replace("-", "_"), "user": user}],
           "tools_root": str(ROOT), "max_turns": 5}
    (d / "job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    p = subprocess.run([sys.executable, "-m", "explainer_engine.llm.claude_api", "run", str(d / "job.json"), "--out", str(d / "out")],
                       cwd=ROOT, capture_output=True, text=True)
    (d / "run.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    out = sorted((d / "out").glob("*.md"))
    text = ""
    for f in out:
        if not f.name.endswith(".thinking.md"):
            text = f.read_text(encoding="utf-8")
    cost = re.findall(r'"usd":\s*([0-9.]+)', p.stdout)
    return {"text": text, "truncated": any(f.name.endswith(".truncated.md") for f in out), "rc": p.returncode,
            "usd": sum(float(c) for c in cost), "dir": str(d)}


def parse_files(text: str) -> dict[str, str]:
    parts = FILE_RE.split(text)
    files = {}
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        body = re.sub(r"\nTRUNCATED_AFTER [^\n]*\n?\Z", "\n", body)
        files[parts[i]] = body.rstrip("\n") + "\n"
    return files


def complete_files(text: str, truncated: bool) -> dict[str, str]:
    """Files whose body is whole: all of them, except the last block of a truncated answer."""
    parts = FILE_RE.split(text)
    names = parts[1::2]
    files = parse_files(text)
    if (truncated or "TRUNCATED_AFTER" in text) and names:
        files.pop(names[-1], None)
    return files


def place(files: dict[str, str], allowed: list[str]) -> list[str]:
    placed = []
    for rel, body in files.items():
        if rel not in allowed:
            continue                                                  # the coder may write only the package's files
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        placed.append(rel)
    return placed


def verify(files: list[str], tests: list[str]) -> tuple[bool, str]:
    log = []
    ok = True
    for rel in files:
        if rel.endswith(".py"):
            r = subprocess.run([sys.executable, "-m", "py_compile", rel], cwd=ROOT, capture_output=True, text=True)
            if r.returncode:
                ok = False
                log.append(f"py_compile {rel}: {r.stderr.strip()[-300:]}")
    if tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "--no-header", *tests], cwd=ROOT, capture_output=True, text=True)
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-25:])
        log.append(tail)
        ok = ok and r.returncode == 0
    return ok, "\n".join(log)


def read_inputs(paths: list[str]) -> dict[str, str]:
    return {Path(p).name.replace(".", "_"): f"### {p}\n" + (ROOT / p).read_text(encoding="utf-8") for p in paths if (ROOT / p).exists()}


def run(wp: dict, check: bool = True) -> dict:
    work = ROOT / "jobs" / "build_loop" / wp["id"]
    work.mkdir(parents=True, exist_ok=True)
    wp_text = (ROOT / wp["wp_text_file"]).read_text(encoding="utf-8") if wp.get("wp_text_file") else wp.get("goal", "")
    system = {"rules": RULES_CODER, "wp": wp_text, **read_inputs(wp.get("inputs", []))}
    user = "Write these files, complete, in this order:\n" + "\n".join(f"- {f}" for f in wp["files"])
    total, steps = 0.0, []
    r = _run_job(work, "coder", "opus", "high", wp.get("coder_max_tokens", 64000), system, user, "new-method-code")
    total += r["usd"]
    text, truncated = r["text"], r["truncated"]
    got = complete_files(text, truncated)
    for _ in range(2):                                                # continue only the missing files
        missing = [f for f in wp["files"] if f not in got]
        if not missing:
            break
        c = _run_job(work, f"cont{len(steps)}", "opus", "high", wp.get("coder_max_tokens", 64000), system,
                     "Write ONLY these files, complete, nothing else:\n" + "\n".join(f"- {f}" for f in missing), "new-method-code")
        total += c["usd"]
        got.update(complete_files(c["text"], c["truncated"]))
        steps.append("continued: " + ", ".join(missing))
    placed = place(got, wp["files"])
    ok, log = verify(placed, wp.get("tests", []))
    verdict = ["(check skipped)"]
    for rnd in range(3):
        if not check:
            break
        files_text = {Path(p).name.replace(".", "_"): f"### {p}\n" + (ROOT / p).read_text(encoding="utf-8") for p in placed}
        k = _run_job(work, f"check{rnd}", "fable", "high", wp.get("check_max_tokens", 16000),
                     {"rules": RULES_CHECK, "wp": wp_text, "test_output": log, **files_text},
                     wp.get("check_question", "Does the code satisfy the work package?"), "research-synthesis")
        total += k["usd"]
        verdict = [ln for ln in k["text"].splitlines() if ln.startswith(("PASS", "FIX", "VERDICT"))]
        last = verdict[-1] if verdict else "VERDICT FIX"
        if last.endswith("PASS") and ok or last.endswith("STOP") or rnd == 2:
            break
        fixes = "\n".join(ln for ln in verdict if ln.startswith("FIX")) + ("\nTest output:\n" + log if not ok else "")
        f = _run_job(work, f"fix{rnd}", "opus", "high", wp.get("fix_max_tokens", 48000),
                     {"rules": RULES_CODER, "wp": wp_text, "fixes": fixes, **files_text},
                     "Fix only what the FIX lines and the test output name. Write the changed files complete.", "new-method-code")
        total += f["usd"]
        place(complete_files(f["text"], f["truncated"]), wp["files"])
        ok, log = verify(placed, wp.get("tests", []))
        steps.append(f"fix round {rnd + 1}")
    summary = {"id": wp["id"], "placed": placed, "missing": [f for f in wp["files"] if f not in placed], "tests_ok": ok,
               "verdict": verdict, "steps": steps, "usd": round(total, 3)}
    (work / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "run":
        print(__doc__)
        return 2
    wp = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(run(wp, check="--no-check" not in argv), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
