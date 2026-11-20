"""Claude Code hooks that keep an unchecked trial or comparison output from reaching the owner (spec section 7.1, owner 2026-11-20
08:37 UTC: "words are not enough, Claude still skips"). They extend the D-84 hooks of ``governance/hooks.py``, and unlike them they
FAIL CLOSED: an exception, a missing scope file or a broken command exits 2 (the command in ``.claude/settings.json`` adds ``|| exit 2``
for a hook that cannot even start).

    pre-bash        a Bash command that uploads a file under a trial or comparison path (``send_scope.json``) to the Hugging Face vault
                    is refused unless ``send_gate`` recorded that file's sha256 as PASS (or labelled with the owner's ``--owner-asked``);
                    a trial command (``scene_run``, ``episode run``) is refused unless the layer gate lets its layers through
    stop            a turn that wrote files under a trial or comparison path (from the transcript, newer than the last user message)
                    without a passing send record cannot end; after 3 refusals in a row it lets go and writes an incident line to
                    ``jobs/send_gate/incidents.jsonl`` so that a stuck loop never hides (``stop_hook_active``)
    subagent-stop   the same for a sub-agent's turn

Paths outside the trial pattern (a log, a vault file, a handoff note) pass. stdlib only."""
from __future__ import annotations

import json
import re
import shlex
import sys
import time
from datetime import datetime
from pathlib import Path

from explainer_engine.governance import layer_gate, root_dir, send_gate

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


def paths_in(text: str, *, root: Path, sc: dict | None = None, _depth: int = 0) -> list[Path]:
    """Existing files named in a command or a script text (a directory yields the files under it with a known suffix); a quoted
    script (``python -c "...upload_file('x')..."``) is searched inside, three levels deep."""
    sc = sc or scope()
    suff = tuple(sc["file_suffixes"])
    out: list[Path] = []
    for m in _PATHISH.finditer(text):
        tok = next((g for g in m.groups() if g), "")
        if _depth < 3 and re.search(r"[\s'\"]", tok):
            out.extend(paths_in(tok, root=root, sc=sc, _depth=_depth + 1))
        if "/" not in tok and "." not in tok:
            continue
        p = Path(tok).expanduser()
        p = p if p.is_absolute() else root / p
        try:
            if p.is_file():
                out.append(p)
            elif p.is_dir() and in_scope(str(p) + "/", sc):
                out.extend(sorted(q for q in p.rglob("*") if q.is_file() and q.suffix.lower() in suff))
        except OSError:
            continue
    return list(dict.fromkeys(out))


def check_files(files: list[Path], *, root: Path, sc: dict | None = None) -> list[str]:
    """Problems for the trial or comparison files among ``files`` (empty = they may go)."""
    sc = sc or scope()
    bad = []
    for f in files:
        if not in_scope(str(f), sc):
            continue
        layer = layer_of(str(f), sc)
        if layer is None:
            bad.append(f"{f}: a trial output must sit under a path that names its layer (.../trials/L14/...) so its validators can run")
        elif send_gate.passing_record(f, root=root) is None:
            bad.append(f"{f}: no passing send record; run `python -m explainer_engine.governance.send_gate {layer} {f}` first "
                       f"(a failing candidate goes only labelled, with --owner-asked <cmsg id>)")
    return bad


def pre_bash(event: dict, *, root: Path | None = None) -> None:
    root = root_dir(root)
    sc = scope()
    cmd = ((event.get("tool_input") or {}).get("command")) or ""
    if re.search(sc["upload_command"], cmd):
        files = paths_in(cmd, root=root, sc=sc)
        bad = check_files(files, root=root, sc=sc)
        if not bad and not any(in_scope(str(f), sc) for f in files) and re.search(sc["trial_path"], cmd.replace("\\", "/"), re.I):
            bad = ["an upload names a trial or comparison path that does not resolve to a file here; the send gate cannot check what it "
                   "cannot find (use the real file paths)"]
        if bad:
            raise Refused("send gate (spec 7.1): " + " | ".join(bad))
    layers = trial_layers(cmd, sc)
    if layers:
        try:
            layer_gate.require_layers(layers, root=root)
        except Exception as exc:
            raise Refused(f"layer gate (spec 7.1): this trial command needs {', '.join(layers)}: {exc}") from exc


def trial_layers(cmd: str, sc: dict) -> tuple[str, ...]:
    # an actual invocation at the start of a command (after ; & | ( or a line break, with env assignments allowed), not a word in a
    # grep, a commit message or a quoted text
    py = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*(?:cd\s+\S+\s*&&\s*)?\S*python[\d.]*\s+(?:-(?!m\b)\S+\s+)*"
    if re.search(py + r"(?:-m\s+\S*scene_run\b|\S*scene_run\.py\b)", cmd, re.M):
        return tuple(sc["trial_command"]["scene_run"])
    if re.search(py + r"(?:-m\s+explainer_engine\.episode\s+run\b|\S*episode/run\.py\s+run\b)", cmd, re.M):
        stages = re.findall(r"--(?:stage|to)\s+(\w+)", cmd)
        order = layer_gate.STAGE_LAYERS
        wanted: list[str] = []
        names = list(order)
        for s in stages or [names[-1]]:
            s = {"G1": "script", "G4": "sound_plan", "G5": "pictures", "G6": "voice", "G7": "clips", "G8": "sound", "G9": "assemble",
                 "G10": "qa"}.get(s, s)
            if s in order:
                upto = names[: names.index(s) + 1] if "--to" in cmd else [s]
                wanted += [layer for st in upto for layer in order[st]]
        return tuple(dict.fromkeys(wanted))
    return ()


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
    for row in seen:
        content = (row.get("message") or {}).get("content")
        for c in content if isinstance(content, list) else []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
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
    bad = check_files(turn_outputs(Path(path), root=root, sc=sc), root=root, sc=sc)
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
        with (root / INCIDENTS).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.time(), "session": key, "unchecked": bad}, ensure_ascii=False) + "\n")
        state.pop(key, None)
        counter.write_text(json.dumps(state), encoding="utf-8")
        print("send gate: let go after 3 refusals; the unchecked outputs are in jobs/send_gate/incidents.jsonl", file=sys.stderr)
        return
    state[key] = n
    counter.write_text(json.dumps(state), encoding="utf-8")
    raise Refused("send gate (spec 7.1): this turn produced trial or comparison outputs without a passing validator record: "
                  + " | ".join(bad))


def main(argv=None) -> int:
    """Exit 0 = allowed, 2 = refused; ANY failure of the hook itself is a refusal (closed)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        cmd = argv[0]
        event = json.loads(sys.stdin.read() or "{}")
        if cmd == "pre-bash":
            pre_bash(event)
        elif cmd == "stop":
            stop(event)
        elif cmd == "subagent-stop":
            stop(event, sub=True)
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
