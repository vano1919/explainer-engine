"""Claude Code hooks that lint what instructions cannot enforce (P0b, D-84, MODEL_ROUTING v2 part 6). Hooks cannot set a model or an
effort (verified 2026-10-29 on the hooks page); they deny, add context or log.

    pre-bash    git force push / branch -D without a backup tag; a shell write to a protected config file
    pre-write   top-level engine/; protected config files; *.py edits at xhigh/max effort
    pre-agent   fable outside the story stages; a critic on another model than opus
    post-edit   py_compile / json / config / docs_lint findings fed back after an edit
    pre-switch  an in-thread model switch without the creator's recorded word; post-switch logs it
    prompt      one reminder line on every prompt
    stop        a done phase without its routing_log line, PROGRESS entry, files or tests; usage backup at 95 %
    statusline  prints model/effort and the 5-hour/weekly usage, records it, starts the backup at 95 %
    stop-failure the rate_limit failure: back up what is unfinished
Every hook fails open: an exception prints one line and exits 0; only a matched rule exits 2."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine.governance import BLUEPRINT, load, root_dir
from explainer_engine.governance import records, status, usage

FAMILIES = ("haiku", "sonnet", "opus", "fable")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _family(model: str | None) -> str | None:
    m = (model or "").lower()
    return next((f for f in FAMILIES if f in m), None)


def _effort(event: dict) -> str | None:
    e = event.get("effort")
    level = e.get("level") if isinstance(e, dict) else e
    return (level or os.environ.get("CLAUDE_EFFORT") or "").lower() or None


def _deny(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else ""


def _has_backup(root: Path, ref: str) -> bool:
    """True when a ``backup/*`` tag points at the commit of ``ref`` (a branch, a remote branch or a sha)."""
    sha = _git(root, "rev-parse", ref)
    return bool(sha) and bool(_git(root, "tag", "--list", "backup/*", "--points-at", sha))


def _rel(root: Path, path: str) -> str | None:
    p = Path(path)
    p = p if p.is_absolute() else root / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


# ---- PreToolUse Bash ---------------------------------------------------------------------------------------------------------

OPERATORS = {"&&", "||", ";", "|", "&", "(", ")"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
FORCE_FLAGS = {"-f", "--force", "--mirror", "--delete", "-d"}


def commands(cmd: str) -> list[list[str]]:
    """The commands of a shell line as argument lists: split on operators and unquoted newlines, quotes kept inside one argument,
    so text in a commit message never looks like a command. Unparsable input yields no commands (fail open)."""
    out, quote = [], None
    for ch in cmd:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        out.append(" ; " if ch == "\n" and not quote else ch)
    lex = shlex.shlex("".join(out), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return []
    argvs, cur = [], []
    for t in tokens:
        if t in OPERATORS:
            argvs.append(cur)
            cur = []
        else:
            cur.append(t)
    return [a for a in argvs + [cur] if a]


def git_call(argv: list[str]) -> tuple[str, list[str]] | None:
    """(subcommand, its own argv) of a ``git`` command, skipping git's global options; None for anything else."""
    i = next((k for k, a in enumerate(argv) if Path(a).name == "git"), None)
    if i is None or any("=" not in a for a in argv[:i]):  # only VAR=value may precede git
        return None
    j = i + 1
    while j < len(argv) and argv[j].startswith("-"):
        j += 2 if argv[j] in GIT_VALUE_OPTIONS else 1
    return (argv[j], argv[j + 1:]) if j < len(argv) else None


def _push_refs(args: list[str], root: Path) -> list[str]:
    """The remote branch names a push touches (``refs/heads/`` stripped, ``HEAD`` and a missing refspec = the current branch)."""
    positional = [a for a in args if not a.startswith("-")]
    specs = positional[1:] or ["HEAD"]
    refs = []
    for r in specs:
        dst = r.lstrip("+").split(":", 1)[1] if ":" in r.lstrip("+") else r.lstrip("+")
        dst = dst.removeprefix("refs/heads/")
        refs.append(_git(root, "rev-parse", "--abbrev-ref", "HEAD") if dst in ("HEAD", "") else dst)
    return refs


def check_git(argv: list[str], root: Path) -> str | None:
    call = git_call(argv)
    if not call:
        return None
    sub, args = call
    flags = [a for a in args if a.startswith("-")]
    if sub == "push":
        positional = [a for a in args if not a.startswith("-")]
        specs = positional[1:]
        forced = any(f in FORCE_FLAGS or f.startswith("--force-with-lease") for f in flags) \
            or any(r.startswith("+") or r.startswith(":") for r in specs)
        if "--mirror" in flags:
            return "refused (Lock 2): `git push --mirror` overwrites every remote ref"
        if forced:
            deleting = "--delete" in flags or "-d" in flags or any(r.startswith(":") for r in specs)
            for ref in _push_refs(args, root):
                tip_known = bool(_git(root, "rev-parse", "--verify", "-q", f"origin/{ref}"))
                if ref and (tip_known or deleting) and not _has_backup(root, f"origin/{ref}"):
                    return (f"refused (Lock 2): force push/delete of {ref} without a backup/* tag on the remote tip it overwrites "
                            f"(`git tag backup/<name> origin/{ref}` first; every force push needs one, a fast-forward too)")
    if sub == "branch":
        force_delete = "-D" in flags or ("--delete" in flags and "--force" in flags) or ({"-d", "-f"} <= set(flags))
        if force_delete:
            for name in [a for a in args if not a.startswith("-")]:
                if not _has_backup(root, name):
                    return f"refused (Lock 2): `git branch -D {name}` without a backup/* tag on its tip"
    return None


def check_protected_shell(cmd: str, cfg: dict, root: Path) -> str | None:
    text = cmd.replace("\\", "/")  # Windows paths
    for name, minutes in cfg["protected_files"].items():
        if name not in text:
            continue
        esc = re.escape(name)
        one = rf"[^|;&\n]*{esc}"
        write = (re.search(rf">>?\s*['\"]?\S*{esc}", text) or re.search(rf"\b(tee|sponge|mv|rm|truncate|dd){one}", text)
                 or re.search(rf"\b(sed|perl)\s+-[a-zA-Z]*i{one}", text) or re.search(rf"\b(Set|Add|Clear|Out)-(Content|File){one}", text)
                 or re.search(rf"\b(cp|install)\b[^|;&\n]*\s['\"]?\S*{esc}['\"]?\s*(?:[;&|\n]|$)", text)  # name is the destination
                 or re.search(rf"open\([^)]*{esc}[^)]*['\"][wax+]", text)
                 or (re.search(r"\bpython3?\b|\bnode\b", text) and re.search(rf"{esc}[^\n]*write_(text|bytes|json)|write_(text|bytes|json)[^\n]*{esc}", text))
                 or re.search(rf"\bgit\s+(checkout|restore|apply){one}", text))
        if write and not records.valid("protected_config", name, minutes, root=root, wildcard=False):
            return f"refused (Lock 2): {name} changes only on the creator's recorded word (`python -m explainer_engine.governance ok protected_config {name} <message id> \"<his words>\"`)"
    return None


def pre_bash(event: dict, root=None) -> int:
    root = root_dir(root)
    cmd = (event.get("tool_input") or {}).get("command", "")
    cfg = load(root)
    for argv in commands(cmd):
        msg = check_git(argv, root)
        if msg:
            return _deny(msg)
    msg = check_protected_shell(cmd, cfg, root)
    return _deny(msg) if msg else 0


# ---- PreToolUse Write|Edit -------------------------------------------------------------------------------------------------

def pre_write(event: dict, root=None) -> int:
    root = root_dir(root)
    ti = event.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if not path:
        return 0
    cfg = load(root)
    rel = _rel(root, path)
    if rel is None:
        return 0
    if rel.split("/")[0] == "engine":
        return _deny("refused (Lock 2): no top-level engine/ folder (Blueprint Phase 1 item 14); the code lives in explainer_engine/")
    if rel in cfg["protected_files"] and not records.valid("protected_config", rel, cfg["protected_files"][rel], root=root, wildcard=False):
        return _deny(f"refused (Lock 2): {rel} changes only on the creator's recorded word (jobs/creator_ok.jsonl, action protected_config)")
    if rel.endswith(".py"):
        level = _effort(event)
        efforts = cfg["efforts"]
        if level in efforts and efforts.index(level) > efforts.index(cfg["code"]["effort_ceiling"]) \
                and not records.valid("effort_override", "*", 60, root=root):
            return _deny(f"refused: *.py edits at effort {level} (code effort ceiling is {cfg['code']['effort_ceiling']}, MODEL_ROUTING part 4); "
                         "the creator's word is recorded with action effort_override")
    return 0


# ---- PreToolUse Agent ------------------------------------------------------------------------------------------------------

def pre_agent(event: dict, root=None) -> int:
    root = root_dir(root)
    cfg = load(root)
    ti = event.get("tool_input") or {}
    kind, fam = ti.get("subagent_type") or "", _family(ti.get("model"))
    story = cfg["fable_story_stages"]
    if fam == "fable" and not (story["enabled"] and kind in story["stages"]):
        return _deny("refused: model fable only on the story stages and only when config fable_story_stages.enabled is set by the creator (D6)")
    crit = cfg["critics"]
    if kind in crit["names"] and not fam:  # no model in the spawn: the agent file decides, and it must say opus
        page = root / ".claude" / "agents" / f"{kind}.md"
        fam = _family(next((l.split(":", 1)[1] for l in page.read_text(encoding="utf-8").splitlines() if l.startswith("model:")), "")) \
            if page.exists() else None
        if fam and fam != crit["model"]:
            return _deny(f"refused: the critic {kind} is configured for {fam}, not {crit['model']} (its agent file)")
        return 0
    if kind in crit["names"] and fam and fam != crit["model"]:
        return _deny(f"refused: the critic {kind} runs on {crit['model']} (MODEL_ROUTING part 4), not {fam}")
    return 0


# ---- PostToolUse -----------------------------------------------------------------------------------------------------------

def post_edit(event: dict, root=None) -> int:
    root = root_dir(root)
    ti = event.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    rel = _rel(root, path) if path else None
    if rel is None or not (root / rel).is_file():
        return 0
    findings: list[str] = []
    text = (root / rel).read_text(encoding="utf-8", errors="replace")
    if rel.endswith(".py"):
        try:
            compile(text, rel, "exec")
        except SyntaxError as e:
            findings.append(f"{rel}:{e.lineno}: syntax error: {e.msg}")
    elif rel.endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError as e:
            findings.append(f"{rel}: not valid JSON ({e})")
        else:
            try:
                if rel == "config/model_routing.json":
                    from explainer_engine.governance import validate
                    validate(data)
                elif rel.startswith("docs/blueprint/"):
                    findings += _blueprint_findings(rel, root)
            except Exception as e:  # ContractError or a malformed file: report, never crash
                findings.append(f"{rel}: {e}")
    elif rel.endswith(".md") and (rel.startswith("docs/") or rel.startswith(".claude/")):
        from explainer_engine import docs_lint
        name = Path(rel).name
        findings += [f"docs_lint {f['check']}: {f['detail']}" for f in docs_lint.check() if name in f["detail"]]
    if findings:
        print("post-edit findings (fix now):\n  " + "\n  ".join(findings), file=sys.stderr)
        return 2
    return 0


def _blueprint_findings(rel: str, root: Path) -> list[str]:
    if rel.endswith("phases.json"):
        return status.check_phases(status.phases(root))
    if rel.endswith("decision_queue.json"):
        return status.check_cards(status.cards(root))
    return []


# ---- model switch ----------------------------------------------------------------------------------------------------------

HUMAN_SOURCES = ("command", "picker")  # /model, the picker, /config, fast mode: the creator at his own keyboard


def pre_switch(event: dict, root=None) -> int:
    """A switch the creator types himself passes; one asked for by an SDK host or Remote Control (the hearth tool) needs his
    recorded word. ``source`` is in the event (hooks page, PreModelSwitch input)."""
    root = root_dir(root)
    cfg = load(root)
    if event.get("source") in HUMAN_SOURCES:
        return 0
    to = event.get("to_model") or ""
    minutes = cfg["model_switch"]["window_minutes"]
    for target in (to, _family(to) or "", "*"):
        if target and records.valid("model_switch", target, minutes, root=root):
            return 0
    return _deny(f"refused: a model switch inside a thread needs the creator's own word (recorded with `python -m explainer_engine.governance ok model_switch {to or '<model>'} <message id> \"<his words>\"`, valid {minutes} min)")


def post_switch(event: dict, root=None) -> int:
    """Log every switch, automatic fallbacks included, to the untracked ``jobs/switch_log.jsonl`` (the tracked routing_log holds phases)."""
    root = root_dir(root)
    to = event.get("to_model") or "?"
    word = records.last("model_switch", to, root=root) or records.last("model_switch", _family(to) or to, root=root)
    row = {"date": time.strftime("%Y-%m-%d", time.gmtime()), "at": time.strftime("%H:%M:%SZ", time.gmtime()), "from": event.get("from_model"),
           "to": to, "source": event.get("source"), "message_id": (word or {}).get("message_id")}
    path = root / "jobs" / "switch_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


# ---- prompt / stop ---------------------------------------------------------------------------------------------------------

def prompt(event: dict, root=None) -> int:
    print(load(root)["reminder"])
    return 0


def _active_phase(root: Path) -> str | None:
    f = root / "jobs" / "active_phase.json"
    return json.loads(f.read_text(encoding="utf-8")).get("phase") if f.exists() else None


def _tests_pass(root: Path, tests: list[str]) -> str | None:
    """None when the listed tests pass (cached by HEAD + diff), else a one-line reason; a missing pytest or a timeout is a note, not a block."""
    key = hashlib.sha256((_git(root, "rev-parse", "HEAD") + _git(root, "diff", "HEAD") + ",".join(tests)).encode()).hexdigest()
    cache = root / "jobs" / "_audit" / "stop_cache.json"
    seen = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    if seen.get("key") == key:
        return seen.get("fail")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", *tests], cwd=root, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode == 5 or "No module named pytest" in r.stderr:
        return None
    fail = None if r.returncode == 0 else "tests failing: " + (r.stdout.strip().splitlines() or ["?"])[-1][:200]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"key": key, "fail": fail}), encoding="utf-8")
    return fail


def stop(event: dict, root=None) -> int:
    root = root_dir(root)
    if event.get("stop_hook_active"):
        return 0
    cfg = load(root)
    hit = usage.backup_if_over(usage.current(root), root)
    if hit and "dest" in hit:
        print(f"usage limit reached: unfinished work backed up to {hit['dest']} (push: {hit['push']})", file=sys.stderr)
    problems: list[str] = []
    missing = status.missing_log(root)
    if missing:
        problems.append(f"phase(s) {', '.join(missing)} are in review/done without a routing_log line (`python -m explainer_engine.governance log ...`)")
    phase = _active_phase(root)
    row = next((r for r in status.phases(root) if r["id"] == phase), None) if phase else None
    if row and row["state"] in status.DONE_STATES and row.get("checklist"):
        cl = row["checklist"]
        for p in cl.get("paths", []):
            if not (root / p).exists():
                problems.append(f"{phase}: required path missing: {p}")
        progress = root / "docs" / "PROGRESS.md"
        if cl.get("progress") and (not progress.exists() or cl["progress"] not in progress.read_text(encoding="utf-8")):
            problems.append(f"{phase}: no docs/PROGRESS.md entry naming {cl['progress']}")
        if cl.get("tests") and not problems:
            fail = _tests_pass(root, cl["tests"])
            if fail:
                problems.append(f"{phase}: {fail}")
    if problems:
        return _deny("The phase is not finished:\n  " + "\n  ".join(problems))
    return 0


def stop_failure(event: dict, root=None) -> int:
    r = usage.backup("rate_limit reached (StopFailure)", root, window_key=f"rate_limit_{int(time.time() // 3600)}")
    print(f"rate limit reached; backup: {r.get('dest', r.get('skipped'))}", file=sys.stderr)
    return 0


def statusline(event: dict, root=None) -> int:
    root = root_dir(root)
    rec = usage.record(event, root)
    model = (event.get("model") or {}).get("display_name") or "?"
    eff = _effort(event) or "?"
    five, seven = rec.get("five_hour"), rec.get("seven_day")
    fmt = lambda w: "n/a" if not w else f"{w['pct']:.0f}%"
    print(f"{model} · effort {eff} · 5h {fmt(five)} · 7d {fmt(seven)}")
    if usage.over(rec, load(root)["usage"]["backup_at_percent"]):
        subprocess.Popen([sys.executable, "-m", "explainer_engine.governance", "backup-if-over"], cwd=root,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return 0


HOOKS = {"pre-bash": pre_bash, "pre-write": pre_write, "pre-agent": pre_agent, "post-edit": post_edit, "pre-switch": pre_switch,
         "post-switch": post_switch, "prompt": prompt, "stop": stop, "stop-failure": stop_failure, "statusline": statusline}
DENYING = {"pre-bash", "pre-write", "pre-agent", "pre-switch", "stop", "post-edit"}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    what = argv[0] if argv else ""
    if what not in HOOKS:
        raise SystemExit(__doc__)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    try:
        return HOOKS[what](event)
    except Exception as e:  # fail open: a broken check must not lock the session
        print(f"governance hook {what} skipped: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
