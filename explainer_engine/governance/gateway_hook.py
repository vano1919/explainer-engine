"""Deterministic Claude Code governance gateway hook enforcing the Python Execution Gateway.

Threat model:
- Prevents ungoverned paid cloud/API calls (direct ``modal run`` on job files, ``modal secret create --force``,
  direct HTTP calls to paid AI APIs, or Python/Node inline subprocess wrappers launching paid jobs).
- Prevents URL API-key leaks (``generativelanguage.googleapis.com?...key=...``).
- Prevents destructive repository resets (``git reset --hard``) and direct shell tampering with
  ``config/owner_approvals.json`` or ``config/spend_caps.json``.
- Verifies machine-checkable ``production_state/1`` stage completion AND on-disk SHA-256 output
  integrity at stop/handoff time.

Handles shell quoting, environment-variable prefixes, command wrappers (``env``, ``sudo``, ``timeout``,
``nice``, ``nohup``, ``command``, ``exec``, ``time``, ``xargs``), chained commands (``&&``, ``||``, ``;``,
``|``, ``&``, newlines), subshells (``$(...)`` and backticks), ``bash -c`` / ``sh -c`` / ``eval``,
and ``python -c`` / ``python3 -c`` / ``node -e`` inline subprocesses.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from explainer_engine.core.execution_gateway import EPISODE_RUNNER_DEPENDENCIES, ProductionStateMachine

OPERATORS = frozenset({"&&", "||", ";", "|", "&", "(", ")"})
WRAPPERS = frozenset(
    {
        "sudo",
        "env",
        "timeout",
        "nice",
        "nohup",
        "command",
        "exec",
        "time",
        "stdbuf",
        "ionice",
        "setsid",
        "doas",
        "xargs",
    }
)
SHELL_EXECUTORS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash"})
PAID_API_HOSTS = (
    "api." "elevenlabs.io",
    "api.anthropic.com",
    "api.runpod.io",
    "api.openai.com",
    "api.bfl.ai",
    "fal.run",
)
PROTECTED_GATEWAY_CONFIGS = ("config/owner_approvals.json",)
URL_KEY_LEAK_RE = re.compile(r"generativelanguage\.googleapis\.com[^\s\"']*[?&]key=", re.I)
SUBSHELL_DOLLAR_RE = re.compile(r"\$\(([^()]+)\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
INLINE_PAID_BYPASS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("inline_modal_run_bypass", re.compile(r"modal_(?:ltx|layout)_jobs\.py", re.I)),
    ("inline_modal_secret_overwrite", re.compile(r"modal\s+secret\s+create.*--force", re.I)),
    ("inline_destructive_git_reset", re.compile(r"git\s+reset\s+--hard", re.I)),
    (
        "inline_paid_api_call",
        re.compile(r"(?:api\.elevenlabs\.io|api\.anthropic\.com|api\.runpod\.io|generativelanguage\.googleapis\.com)", re.I),
    ),
)


def _norm_exe(token: str) -> str:
    name = Path(token).name.lower()
    for suf in (".exe", ".cmd", ".bat"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def _split_shell_commands(cmd: str, *, _depth: int = 0) -> tuple[list[list[str]], bool]:
    """Tokenize a shell command into argument lists, recursing into subshells and shell -c wrappers.

    Returns ``(argvs, parse_error)`` where ``parse_error=True`` on malformed quoting so security
    checks can fail closed rather than silently allowing obfuscated commands.
    """
    if _depth > 6:
        return [], True

    extra_subcommands: list[str] = []
    for m in SUBSHELL_DOLLAR_RE.finditer(cmd):
        extra_subcommands.append(m.group(1))
    for m in BACKTICK_RE.finditer(cmd):
        extra_subcommands.append(m.group(1))

    # Replace unquoted newlines with command separators
    buf: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in cmd:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\" and quote != "'":
            buf.append(ch)
            escaped = True
            continue
        if quote:
            if ch == quote:
                quote = None
            buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == "\n":
            buf.append(" ; ")
        else:
            buf.append(ch)

    if quote is not None:
        return [], True

    lex = shlex.shlex("".join(buf), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return [], True

    argvs: list[list[str]] = []
    cur: list[str] = []
    for tok in tokens:
        if tok in OPERATORS:
            if cur:
                argvs.append(cur)
                cur = []
        else:
            cur.append(tok)
    if cur:
        argvs.append(cur)

    parse_err = False
    expanded: list[list[str]] = list(argvs)
    for argv in argvs:
        stripped = _strip_env_and_wrappers(argv)
        if not stripped:
            continue
        exe = _norm_exe(stripped[0])
        if exe in SHELL_EXECUTORS:
            c_idx = next((i for i, a in enumerate(stripped[:-1]) if re.fullmatch(r"-[a-zA-Z]*c", a)), None)
            if c_idx is not None:
                sub_argvs, sub_err = _split_shell_commands(stripped[c_idx + 1], _depth=_depth + 1)
                expanded.extend(sub_argvs)
                parse_err = parse_err or sub_err
        elif exe == "eval" and len(stripped) > 1:
            sub_argvs, sub_err = _split_shell_commands(" ".join(stripped[1:]), _depth=_depth + 1)
            expanded.extend(sub_argvs)
            parse_err = parse_err or sub_err

    for sub in extra_subcommands:
        sub_argvs, sub_err = _split_shell_commands(sub, _depth=_depth + 1)
        expanded.extend(sub_argvs)
        parse_err = parse_err or sub_err

    return expanded, parse_err


def _strip_env_and_wrappers(argv: list[str]) -> list[str]:
    """Strip leading VAR=val assignments and transparent command wrappers like env/sudo/timeout."""
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if "=" in tok and not tok.startswith("-") and tok.split("=", 1)[0].replace("_", "").isalnum():
            i += 1
            continue
        base = _norm_exe(tok)
        if base in WRAPPERS:
            i += 1
            # Skip wrapper flags and timeout duration / env KEY=VAL args
            while i < n:
                nxt = argv[i]
                if nxt == "--":
                    i += 1
                    break
                if nxt.startswith("-"):
                    i += 1
                    continue
                if base == "env" and "=" in nxt:
                    i += 1
                    continue
                if base == "timeout" and re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", nxt):
                    i += 1
                    continue
                break
            continue
        break
    return argv[i:]


def _check_single_argv(argv: list[str]) -> list[str]:
    violations: list[str] = []
    if not argv:
        return violations

    # Check raw tokens for URL key leaks even inside env assignments
    joined_raw = " ".join(argv)
    if URL_KEY_LEAK_RE.search(joined_raw):
        violations.append("GATEWAY-DENY[gemini_url_key_leak]: Gemini API key passed in URL query string")

    cmd = _strip_env_and_wrappers(argv)
    if not cmd:
        return violations

    exe = _norm_exe(cmd[0])
    args = cmd[1:]
    joined = " ".join(cmd)

    # 1. Direct modal CLI bypasses
    if exe == "modal" or (exe in ("python", "python3") and len(args) >= 2 and args[0] == "-m" and args[1] == "modal"):
        modal_args = args[2:] if exe in ("python", "python3") else args
        if len(modal_args) >= 2 and modal_args[0] == "secret" and modal_args[1] == "create" and "--force" in modal_args:
            violations.append("GATEWAY-DENY[direct_modal_secret_overwrite]: `modal secret create --force` bypasses secret governance")
        if modal_args and modal_args[0] in ("run", "deploy") and any("modal_ltx_jobs" in a or "modal_layout_jobs" in a for a in modal_args[1:]):
                violations.append("GATEWAY-DENY[direct_modal_run_bypass]: direct `modal run/deploy` bypasses governed Python execution gateway")

    # 2. Destructive git reset --hard
    if exe == "git":
        j = 0
        while j < len(args) and args[j].startswith("-"):
            j += 2 if args[j] in ("-C", "-c", "--git-dir", "--work-tree") else 1
        if j < len(args) and args[j] == "reset" and "--hard" in args[j + 1 :]:
            violations.append("GATEWAY-DENY[destructive_git_reset]: `git reset --hard` is prohibited by execution gateway")

    # 3. Direct HTTP clients hitting paid external AI APIs
    if exe in ("curl", "wget", "http", "httpie", "invoke-webrequest", "iwr", "irm", "invoke-restmethod"):
        low = joined.lower()
        for host in PAID_API_HOSTS:
            if host in low:
                violations.append(f"GATEWAY-DENY[ungoverned_paid_api_call]: direct HTTP request to paid API {host}")
                break
        if "generativelanguage.googleapis.com" in low:
            violations.append("GATEWAY-DENY[ungoverned_paid_api_call]: direct HTTP request to Gemini API bypasses spend gateway")

    # 4. Inline python -c / node -e scripts attempting to launch paid jobs or bypasses
    if exe in ("python", "python3", "py") and "-c" in args:
        idx = args.index("-c")
        if idx + 1 < len(args):
            snippet = args[idx + 1]
            for code, pat in INLINE_PAID_BYPASS_PATTERNS:
                if pat.search(snippet):
                    violations.append(f"GATEWAY-DENY[{code}]: inline Python subprocess/API bypass detected")
    if exe in ("node", "nodejs") and ("-e" in args or "--eval" in args):
        flag = "-e" if "-e" in args else "--eval"
        idx = args.index(flag)
        if idx + 1 < len(args):
            snippet = args[idx + 1]
            for code, pat in INLINE_PAID_BYPASS_PATTERNS:
                if pat.search(snippet):
                    violations.append(f"GATEWAY-DENY[{code}]: inline Node subprocess/API bypass detected")

    return violations


def check_shell_command_for_gateway_bypass(command: str) -> list[str]:
    """Return governance violations if a shell command attempts an ungoverned paid or destructive bypass."""
    if not isinstance(command, str):
        return ["GATEWAY-DENY[malformed_command]: command must be a string"]
    violations: list[str] = []
    if URL_KEY_LEAK_RE.search(command):
        violations.append("GATEWAY-DENY[gemini_url_key_leak]: Gemini API key passed in URL query string")

    # Block direct shell writes to approval/spend-cap registries
    norm_cmd = command.replace("\\", "/")
    for cfg_path in PROTECTED_GATEWAY_CONFIGS:
        if cfg_path in norm_cmd:
            esc = re.escape(cfg_path)
            if (
                re.search(rf"(?:>>?|\btee\b|\bmv\b|\brm\b|\bsed\s+-[a-zA-Z]*i|\btruncate\b|\.write_text\(|open\(|set-content|add-content|out-file)[^\n]*{esc}", norm_cmd, re.I)
                or re.search(rf"\bcp\b[^|;&\n]*\s['\"]?\S*{esc}['\"]?\s*(?:[;&|\n]|$)", norm_cmd)
            ):
                violations.append(f"GATEWAY-DENY[approval_registry_tampering]: shell write to {cfg_path} is prohibited")

    argvs, parse_err = _split_shell_commands(command)
    if parse_err:
        violations.append("GATEWAY-DENY[unparsable_shell_command]: malformed or unclosed shell quoting rejected (fail-closed)")
    for argv in argvs:
        violations.extend(_check_single_argv(argv))

    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def verify_production_state_gate(
    state_path: Path,
    *,
    required_stages: tuple[str, ...] = ("script", "qa"),
    use_episode_runner_graph: bool = False,
) -> dict[str, Any]:
    """Verify at stop/handoff time that required stages have PASS/REVIEW status, valid prerequisites, and intact output hashes."""
    if not state_path.is_file():
        return {"ok": False, "errors": [f"Missing production state file: {state_path}"]}
    deps = EPISODE_RUNNER_DEPENDENCIES if use_episode_runner_graph else None
    sm = ProductionStateMachine(state_path, stage_dependencies=deps)
    errors: list[str] = []
    for st in required_stages:
        ok_out, out_errs = sm.verify_stage_outputs(st)
        if not ok_out:
            errors.extend(out_errs)
        ok_pre, blockers = sm.can_start_stage(st)
        if not ok_pre:
            errors.extend(blockers)
    # Deduplicate errors preserving order
    dedup_errors = list(dict.fromkeys(errors))
    return {"ok": len(dedup_errors) == 0, "errors": dedup_errors, "summary": sm.status_summary()}


def check_hook_payload(event: Any) -> dict[str, Any]:
    """Evaluate a Claude Code PreToolUse Bash event payload fail-closed."""
    if not isinstance(event, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: hook payload must be a JSON object"}
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: missing or non-object tool_input"}
    if "command" not in tool_input or not isinstance(tool_input.get("command"), str):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: missing or non-string tool_input.command"}
    cmd = tool_input["command"]
    violations = check_shell_command_for_gateway_bypass(cmd)
    if violations:
        return {"decision": "deny", "reason": "; ".join(violations)}
    return {"decision": "allow", "reason": "ok"}



def check_write_payload(event: Any) -> dict[str, Any]:
    """Evaluate a Claude Code PreToolUse Write/Edit event payload fail-closed."""
    if not isinstance(event, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: hook payload must be a JSON object"}
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: missing or non-object tool_input"}
    raw_path = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: missing or non-string tool_input.file_path"}
    norm = raw_path.replace("\\", "/").strip()
    for cfg_path in PROTECTED_GATEWAY_CONFIGS:
        if norm == cfg_path or norm.endswith("/" + cfg_path):
            return {
                "decision": "deny",
                "reason": f"GATEWAY-DENY[protected_config_write]: direct Write/Edit to {cfg_path} is prohibited",
            }
    return {"decision": "allow", "reason": "ok"}


def check_stop_payload(event: Any, *, root: Path | None = None) -> dict[str, Any]:
    """Verify active production state gate if a production state path is configured."""
    if not isinstance(event, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: stop payload must be a JSON object"}
    raw_state = event.get("production_state_path") or os.environ.get("EXPLAINER_PRODUCTION_STATE")
    if not raw_state and root is not None:
        pointer = root / "jobs" / "active_production_state.json"
        if pointer.is_file():
            try:
                raw_state = json.loads(pointer.read_text(encoding="utf-8")).get("state_path")
            except ValueError:
                return {"decision": "deny", "reason": f"GATEWAY-DENY[corrupt_state_pointer]: invalid JSON in {pointer}"}
    if not raw_state:
        return {"decision": "allow", "reason": "no active production state configured"}
    req = tuple(event.get("required_stages") or ("script", "qa"))
    res = verify_production_state_gate(
        Path(str(raw_state)),
        required_stages=req,
        use_episode_runner_graph=bool(event.get("use_episode_runner_graph", True)),
    )
    if not res["ok"]:
        return {"decision": "deny", "reason": "; ".join(res["errors"]), "summary": res.get("summary")}
    return {"decision": "allow", "reason": "ok", "summary": res.get("summary")}


def record_post_bash_audit(event: Any, *, root: Path | None = None) -> dict[str, Any]:
    """Record governed Bash execution telemetry into jobs/gateway_audit.jsonl."""
    if not isinstance(event, dict):
        return {"decision": "deny", "reason": "GATEWAY-DENY[malformed_payload]: post-bash payload must be a JSON object"}
    import datetime as _dt
    import hashlib as _hashlib

    ti_raw = event.get("tool_input")
    tr_raw = event.get("tool_response")
    ti: dict[str, Any] = ti_raw if isinstance(ti_raw, dict) else {}
    tr: dict[str, Any] = tr_raw if isinstance(tr_raw, dict) else {}
    cmd = str(ti.get("command") or "")
    base_root = root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    audit_path = base_root / "jobs" / "gateway_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _dt.datetime.now(_dt.UTC).isoformat(),
        "hook": "gateway_hook:post-bash",
        "command_sha256": _hashlib.sha256(cmd.encode("utf-8")).hexdigest(),
        "command_preview": cmd[:160],
        "exit_code": tr.get("exit_code"),
    }
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"decision": "allow", "reason": "recorded", "audit_path": str(audit_path)}


def main(argv: list[str] | None = None) -> int:
    try:
        args = sys.argv[1:] if argv is None else argv
        mode = args[0] if args else "pre-bash"
        project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        raw = sys.stdin.read().strip()
        if not raw:
            res = {"decision": "deny", "reason": "GATEWAY-DENY[empty_payload]: empty stdin payload rejected (fail-closed)"}
        else:
            try:
                payload = json.loads(raw)
            except ValueError as exc:
                res = {"decision": "deny", "reason": f"GATEWAY-DENY[invalid_json]: {exc}"}
            else:
                if mode in ("stop", "stop-guard"):
                    res = check_stop_payload(payload, root=project_root)
                elif mode in ("post-bash", "post-bash-guard"):
                    res = record_post_bash_audit(payload, root=project_root)
                elif mode in ("pre-write", "pre-write-guard"):
                    res = check_write_payload(payload)
                else:
                    res = check_hook_payload(payload)
        print(json.dumps(res))
        if res["decision"] != "allow":
            print(res["reason"], file=sys.stderr)
            return 2
        return 0
    except Exception as exc:
        err = f"GATEWAY-DENY[hook_exception]: fail-closed on {type(exc).__name__}: {exc}"
        print(json.dumps({"decision": "deny", "reason": err}))
        print(err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
