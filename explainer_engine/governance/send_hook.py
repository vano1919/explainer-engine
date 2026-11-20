"""Claude Code hooks that keep an unchecked trial or comparison output from reaching the owner (spec section 7.1, owner 2026-11-20
08:37 UTC: "words are not enough, Claude still skips"). They extend the D-84 hooks of ``governance/hooks.py``, and unlike them they
FAIL CLOSED: an exception, a missing scope file or a broken command exits 2 (the command in ``.claude/settings.json`` adds ``|| exit 2``
for a hook that cannot even start).

    pre-bash        a Bash command that uploads a file under a trial or comparison path (``send_scope.json``) to the Hugging Face vault
                    is refused unless ``send_gate`` recorded that file's sha256 as PASS (or labelled with the owner's ``--owner-asked``);
                    a trial command (``scene_run``, ``episode run``) is refused unless the layer gate lets its layers through
    stop            a turn that wrote files under a trial or comparison path (from the transcript, newer than the last user message)
                    without a passing send record cannot end; after 3 refusals in a row it lets go, QUARANTINES the files (``send_gate.quarantine``:
                    the send gate and the upload hook refuse them until a newer PASS record) and writes an incident line to
                    ``jobs/send_gate/incidents.jsonl`` so that a stuck loop never hides (``stop_hook_active``)
    subagent-stop   the same for a sub-agent's turn
    pre-tool        the MCP routes a file leaves by (post_message attached_outputs, GitHub push_files / create_or_update_file, Drive create_file):
                    the same check as an upload; a GitHub merge needs the owner's recorded merge_approval
    prompt          shows every incident not shown yet at the start of the next turn (fails open: an exit 2 would erase the owner's prompt)

Paths outside the trial pattern (a log, a vault file, a handoff note) pass. stdlib only."""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from explainer_engine.governance import layer_gate, records, root_dir, send_gate

SCOPE = Path(__file__).with_name("send_scope.json")
INCIDENTS = Path("jobs") / "send_gate" / "incidents.jsonl"
STOP_COUNT = Path("jobs") / "send_gate" / "stop_blocks.json"
MAX_STOP_BLOCKS = 3
_PATHISH = re.compile(r"""(?:"([^"\n]+)"|'([^'\n]+)'|([^\s"'<>|;&()=]+))""")


class Refused(Exception):
    """Raised with the message the hook prints on exit 2."""


def scope() -> dict:
    return json.loads(SCOPE.read_text(encoding="utf-8"))   # a missing or broken scope file raises: closed


def in_scope(path: str, sc: dict | None = None) -> bool:
    sc = sc or scope()
    return bool(re.search(sc["trial_path"], str(path).replace("\\", "/"), re.I))


def layer_of(path: str, sc: dict | None = None) -> str | None:
    sc = sc or scope()
    m = re.search(sc["layer_in_path"], str(path).replace("\\", "/"))
    return m.group(2) if m else None


MAX_FILES = 20000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}


def _files_below(folder: Path, suff: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        out += [Path(dirpath) / n for n in sorted(names) if Path(n).suffix.lower() in suff]
        if len(out) > MAX_FILES:
            break
    return out[:MAX_FILES]


def paths_in(text: str, *, root: Path, sc: dict | None = None, _depth: int = 0, expand_dirs: bool = False) -> list[Path]:
    """Existing files named in a command or a script text (a directory yields the files under it with a known suffix); a quoted
    script (``python -c "...upload_file('x')..."``) is searched inside, three levels deep."""
    sc = sc or scope()
    suff = tuple(sc["file_suffixes"])
    out: list[Path] = []
    for m in _PATHISH.finditer(text):
        tok = next((g for g in m.groups() if g), "")
        if _depth < 3 and re.search(r"[\s'\"]", tok):
            out.extend(paths_in(tok, root=root, sc=sc, _depth=_depth + 1, expand_dirs=expand_dirs))
        if "/" not in tok and "." not in tok:
            continue
        p = Path(tok).expanduser()
        p = p if p.is_absolute() else root / p
        try:
            if p.is_file():
                out.append(p)
            elif p.is_dir() and (expand_dirs or in_scope(str(p) + "/", sc)):   # an upload of a PARENT folder sends what is inside (S4)
                out.extend(_files_below(p, suff))
        except OSError:
            continue
    return list(dict.fromkeys(out))


def outgoing(root: Path, sc: dict, *, since: float | None = None) -> list[Path]:
    """Trial or comparison files whose path names a layer, that a push would send (git: tracked or not ignored; no git: every file under
    the root), optionally only those changed since ``since``. Used for commands that name no file (``git push``) and by the stop hook."""
    suff = tuple(sc["file_suffixes"])
    names: list[Path] = []
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            names = [root / n for n in r.stdout.splitlines() if n]
    if not names:
        names = _files_below(root, suff)
    out = []
    for f in names:
        if f.suffix.lower() in suff and in_scope(str(f), sc) and layer_of(str(f), sc) and f.is_file():
            if since is None or f.stat().st_mtime >= since:
                out.append(f)
    return out


def laundered(files: list[Path], *, root: Path, sc: dict) -> list[str]:
    """Named files outside the trial scope whose BYTES are those of a trial output with no passing record (a copy to a neutral path, S4)."""
    cands = [f for f in outgoing(root, sc) if send_gate.passing_record(f, root=root) is None]
    if not cands:
        return []
    by_size: dict[int, list[Path]] = {}
    for c in cands:
        by_size.setdefault(c.stat().st_size, []).append(c)
    bad = []
    for f in files:
        if in_scope(str(f), sc) or not f.is_file():
            continue
        same = by_size.get(f.stat().st_size)
        if same and send_gate.sha256(f) in {send_gate.sha256(c) for c in same}:
            bad.append(f"{f}: the same bytes as a trial output with no passing send record ({same[0].name}); run the send gate on the trial file first")
    return bad


def check_files(files: list[Path], *, root: Path, sc: dict | None = None, with_paths: bool = False):
    """Problems for the trial or comparison files among ``files`` (empty = they may go); ``with_paths`` returns ``(file, problem)`` pairs."""
    sc = sc or scope()
    bad = []
    for f in files:
        if not in_scope(str(f), sc):
            continue
        layer = layer_of(str(f), sc)
        if layer is None:
            bad.append((f, f"{f}: a trial output must sit under a path that names its layer (.../trials/L14/...) so its validators can run"))
        elif send_gate.passing_record(f, root=root) is None:
            bad.append((f, f"{f}: no passing send record; run `python -m explainer_engine.governance.send_gate {layer} {f}` first "
                           f"(a failing candidate goes only labelled, with --owner-asked <cmsg id>)"))
    return bad if with_paths else [m for _, m in bad]


def pre_bash(event: dict, *, root: Path | None = None) -> None:
    root = root_dir(root)
    sc = scope()
    cmd = ((event.get("tool_input") or {}).get("command")) or ""
    if not isinstance(cmd, str):
        cmd = ""
    if re.search(sc["upload_command"], cmd):
        files = paths_in(cmd, root=root, sc=sc, expand_dirs=True)
        bad = check_files(files, root=root, sc=sc)
        bad += laundered(files, root=root, sc=sc)
        if not bad and not any(in_scope(str(f), sc) for f in files) and re.search(sc["trial_path"], cmd.replace("\\", "/"), re.I):
            bad = ["an upload names a trial or comparison path that does not resolve to a file here; the send gate cannot check what it "
                   "cannot find (use the real file paths)"]
        if not bad and re.search(sc["push_command"], cmd):                 # a push names no file: judge what it would send
            bad = check_files(outgoing(root, sc), root=root, sc=sc)
        if bad:
            raise Refused("send gate (spec 7.1): " + " | ".join(bad))
    layers = trial_layers(cmd, sc)
    if layers:
        try:
            layer_gate.require_layers(layers, root=root)
        except Exception as exc:
            raise Refused(f"layer gate (spec 7.1): this trial command needs {', '.join(layers)}: {exc}") from exc


WRAPPERS = {"nohup", "time", "env", "sudo", "nice", "setsid", "command", "exec", "stdbuf", "ionice", "xargs", "timeout", "uv", "poetry",
            "pipenv", "conda", "pdm", "hatch", "doas", "chronic", "unbuffer", "caffeinate", "script", "flock", "parallel"}


def _unwrap(argv: list[str]) -> list[str]:
    """The command a wrapper (nohup, timeout 1800, time, env X=1, uv run, xargs -n1 ...) starts: argv from its first python token."""
    while argv and re.fullmatch(r"\w+=.*", argv[0]):
        argv = argv[1:]
    if argv and Path(argv[0]).name in WRAPPERS:
        k = next((i for i, a in enumerate(argv) if re.fullmatch(r"python[\d.]*", Path(a).name)), None)
        return _unwrap(argv[k:]) if k is not None else []
    return argv


def _trial_text(text: str, sc: dict) -> tuple[str, ...]:
    """The layers an actual invocation (python -m scene_run, python scene_run.py, episode run) needs; ``text`` starts with that python."""
    py = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*(?:cd\s+\S+\s*&&\s*)?\S*python[\d.]*\s+(?:-(?!m\b)\S+\s+)*"
    if re.search(py + r"(?:-m\s+\S*scene_run\b|\S*scene_run\.py\b)", text, re.M):
        return tuple(sc["trial_command"]["scene_run"])
    if re.search(py + r"(?:-m\s+explainer_engine\.episode\s+run\b|\S*episode/run\.py\s+run\b)", text, re.M):
        stages = re.findall(r"--(?:stage|to)\s+(\w+)", text)
        order = layer_gate.STAGE_LAYERS
        wanted: list[str] = []
        names = list(order)
        for st in stages or [names[-1]]:
            st = {"G1": "script", "G4": "sound_plan", "G5": "pictures", "G6": "voice", "G7": "clips", "G8": "sound", "G9": "assemble",
                  "G10": "qa"}.get(st, st)
            if st in order:
                upto = names[: names.index(st) + 1] if "--to" in text else [st]
                wanted += [layer for s2 in upto for layer in order[s2]]
        return tuple(dict.fromkeys(wanted))
    return ()


def _runpy_layers(text: str, sc: dict) -> tuple[str, ...]:
    """A ``python -c`` that starts the trial by ``runpy`` / ``import_module`` / ``subprocess`` instead of ``-m``."""
    if re.search(r"runpy|import_module|__import__|subprocess|os\.system|os\.exec", text):
        if re.search(r"scene_run", text):
            return tuple(sc["trial_command"]["scene_run"])
        if re.search(r"explainer_engine[./]episode", text) and re.search(r"\brun\b", text):
            return _trial_text("python -m explainer_engine.episode run " + text, sc) or _trial_text(
                "python -m explainer_engine.episode run --to qa", sc)
    return ()


def _strings(v, depth: int = 0):
    if isinstance(v, str):
        yield v
    elif depth < 6 and isinstance(v, dict):
        for x in v.values():
            yield from _strings(x, depth + 1)
    elif depth < 6 and isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x, depth + 1)


MERGE_TOOLS = re.compile(r"mcp__github__(merge_pull_request|enable_pr_auto_merge)")


def pre_tool(event: dict, *, root: Path | None = None) -> None:
    """PreToolUse on the MCP routes a file leaves by (S6): ``post_message(attached_outputs)``, GitHub ``push_files`` and
    ``create_or_update_file``, Drive ``create_file``: every local trial or comparison file the call names needs its passing send record, and
    a GitHub merge needs the owner's recorded ``merge_approval`` word for that pull request (the owner keeps merges)."""
    root = root_dir(root)
    sc = scope()
    name = str(event.get("tool_name") or "")
    ti = event.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    if MERGE_TOOLS.fullmatch(name):
        number = str(ti.get("pullNumber") or ti.get("pull_number") or ti.get("number") or "")
        if not number or not records.valid("merge_approval", number, 60 * 24, root=root, wildcard=False):
            raise Refused(f"merge guard (T2.7): {name} on pull request {number or '?'} needs the owner's recorded merge_approval word "
                          f"(`python -m explainer_engine.governance ok merge_approval {number or '<number>'} <cmsg id> \"<his words>\"`); "
                          "the owner keeps merges")
        return
    files: list[Path] = []
    for text in _strings(ti):
        if len(text) < 4096:
            files += paths_in(text, root=root, sc=sc, expand_dirs=True)
    bad = check_files(list(dict.fromkeys(files)), root=root, sc=sc) + laundered(files, root=root, sc=sc)
    if bad:
        raise Refused(f"send gate (spec 7.1): {name} would send files no validator measured: " + " | ".join(bad))


def trial_layers(cmd: str, sc: dict) -> tuple[str, ...]:
    """The layers a trial command needs. Every simple command of the line is looked at (``bash -c`` and ``eval`` are opened by
    ``hooks.commands``), wrappers are stripped (S7), a word in a grep, a commit message or a quoted text is not an invocation."""
    from explainer_engine.governance.hooks import commands
    found: list[str] = list(_trial_text(cmd, sc))
    for argv in commands(cmd):
        argv = _unwrap(argv)
        if not argv or not re.fullmatch(r"python[\d.]*", Path(argv[0]).name):
            continue
        found += _trial_text(" ".join(argv), sc)
        if "-c" in argv:
            found += _runpy_layers(argv[argv.index("-c") + 1] if argv.index("-c") + 1 < len(argv) else "", sc)
    return tuple(dict.fromkeys(found))


def _turn_start(lines: list[dict]) -> float:
    """The time of the last real user message of the transcript (not a tool result)."""
    start = 0.0
    for row in lines:
        msg = row.get("message") or {}
        content = msg.get("content")
        if row.get("type") != "user" or msg.get("role", "user") != "user":
            continue
        if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            continue
        ts = row.get("timestamp")
        if isinstance(ts, str):
            try:
                start = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
    return start


def turn_outputs(transcript: Path, *, root: Path, sc: dict | None = None) -> list[Path]:
    """Trial or comparison files this turn named (a Write/Edit target or a path in a Bash command) that exist and are newer than the
    last user message."""
    sc = sc or scope()
    rows = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    start = _turn_start(rows)
    seen = [r for r in rows if _after(r, start)]
    texts: list[str] = []
    ran_code = False
    for row in seen:
        content = (row.get("message") or {}).get("content")
        for c in content if isinstance(content, list) else []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                ran_code = ran_code or c.get("name") in ("Bash", "PowerShell", "Task", "Agent")
                inp = c.get("input") or {}
                texts += [str(inp.get(k)) for k in ("file_path", "path", "command", "notebook_path") if inp.get(k)]
    found = []
    for t in texts:
        for p in paths_in(t, root=root, sc=sc):
            try:
                if in_scope(str(p), sc) and p.stat().st_mtime >= start - 1:
                    found.append(p)
            except OSError:
                continue
    if start > 0 and ran_code:                      # S5: a script wrote a trial output without naming it: look at what is new on disk
        found += outgoing(root, sc, since=start - 1)
    return list(dict.fromkeys(found))


def _after(row: dict, start: float) -> bool:
    ts = row.get("timestamp")
    if not isinstance(ts, str):
        return True
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() >= start
    except ValueError:
        return True


def stop(event: dict, *, root: Path | None = None, sub: bool = False) -> None:
    root = root_dir(root)
    path = event.get("agent_transcript_path") if sub and event.get("agent_transcript_path") else event.get("transcript_path")
    if not path or not Path(path).is_file():
        raise Refused("send gate (spec 7.1): the transcript of this turn is not readable, so the turn's outputs cannot be checked")
    sc = scope()
    pairs = check_files(turn_outputs(Path(path), root=root, sc=sc), root=root, sc=sc, with_paths=True)
    bad = [m for _, m in pairs]
    counter = root / STOP_COUNT
    state = json.loads(counter.read_text(encoding="utf-8")) if counter.is_file() else {}
    key = str(event.get("session_id") or "session")
    if not bad:
        if key in state:
            state.pop(key)
            counter.write_text(json.dumps(state), encoding="utf-8")
        return
    n = int(state.get(key, 0)) + 1
    counter.parent.mkdir(parents=True, exist_ok=True)
    if n > MAX_STOP_BLOCKS:                                               # a loop that never ends hides nothing: record it, let go
        q = send_gate.quarantine([f for f, _ in pairs], "the stop hook let the turn end after 3 refusals", root=root)
        with (root / INCIDENTS).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.time(), "session": key, "unchecked": bad, "quarantined": [r["sha256"] for r in q]},
                               ensure_ascii=False) + "\n")
        state.pop(key, None)
        counter.write_text(json.dumps(state), encoding="utf-8")
        print("send gate: let go after 3 refusals; the unchecked outputs are QUARANTINED (jobs/send_gate/quarantine.jsonl): the send gate and the "
              "upload hook refuse them until a send gate run passes; the incident is shown at the next prompt", file=sys.stderr)
        return
    state[key] = n
    counter.write_text(json.dumps(state), encoding="utf-8")
    raise Refused("send gate (spec 7.1): this turn produced trial or comparison outputs without a passing validator record: "
                  + " | ".join(bad))


SEEN = Path("jobs") / "send_gate" / "incidents_seen.json"


def prompt(event: dict, *, root: Path | None = None) -> str:
    """The lines to show at the start of the next turn (UserPromptSubmit adds stdout as context): every incident not shown yet."""
    root = root_dir(root)
    log = root / INCIDENTS
    rows = [r for r in log.read_text(encoding="utf-8").splitlines() if r.strip()] if log.is_file() else []
    seen_file = root / SEEN
    seen = int(json.loads(seen_file.read_text(encoding="utf-8")).get("n", 0)) if seen_file.is_file() else 0
    new = rows[seen:]
    if new:
        seen_file.parent.mkdir(parents=True, exist_ok=True)
        seen_file.write_text(json.dumps({"n": len(rows)}), encoding="utf-8")
    out = []
    for line in new:
        r = json.loads(line)
        out.append("SEND GATE INCIDENT: a turn ended with trial or comparison outputs no validator measured; they are quarantined and may not "
                   "go to the owner as candidates until `send_gate` passes them: " + "; ".join(r.get("unchecked", []))[:600])
    return "\n".join(out)


def main(argv=None) -> int:
    """Exit 0 = allowed, 2 = refused; ANY failure of the hook itself is a refusal (closed)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        cmd = argv[0]
        event = json.loads(sys.stdin.read() or "{}")
        if cmd == "pre-bash":
            pre_bash(event)
        elif cmd == "pre-tool":
            pre_tool(event)
        elif cmd == "stop":
            stop(event)
        elif cmd == "subagent-stop":
            stop(event, sub=True)
        elif cmd == "prompt":                                              # fails OPEN: exit 2 would erase the owner's prompt
            try:
                text = prompt(event)
                if text:
                    print(text)
            except Exception as exc:
                print(f"send hook prompt could not read the incidents ({type(exc).__name__}: {exc})", file=sys.stderr)
            return 0
        else:
            raise Refused(f"unknown hook command {cmd!r}")
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:                                               # fail closed
        print(f"send hook failed closed ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
