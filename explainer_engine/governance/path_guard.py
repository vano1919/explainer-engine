"""Path-based guard of the hooks (T2.7, tester findings S2, S3, W2, R7): which FILES a command or an edit touches, not which words it uses.

Two lists of protected files:

* ``NEVER`` - the owner's recorded word (``jobs/creator_ok.jsonl``) and the send gate's records (``jobs/send_gate/``). They are written
  only by their own code (``governance ok``, ``send_gate``), never by hand, so no recorded word can unlock them: a Write/Edit on them and
  a Bash command that writes to them are refused unconditionally.
* gate files (``gate_files.json``) - the enforcement code itself (hook config, ``governance/**``, the layer records, the registry, the
  CI workflow). SHIPPED SWITCHED OFF (``"enabled": false``): until the owner switches it on, an edit of a gate file is NOT ENFORCED here.
  Switched on, such a file changes only on his recorded ``protected_config`` word, like ``config/spend_caps.json`` (``hooks.py``).

A Bash command is judged by the paths it names, after ``cd`` and ``VAR=value`` are followed and globs are expanded: a command that names a
protected path is refused unless every command that names it is read-only (``cat``, ``grep``, ``git diff`` ...) and no redirect, ``tee`` or
interpreter write reaches it. An interpreter (python, node, perl ...) that names a protected path is refused when the same command text holds
a write (``open(.., 'w')``, ``write_text``, ``shutil``, ``os.replace`` ...). This is static analysis: a path built from string pieces at run
time can still get past it, which is why the logs are also sealed (``send_gate.append_sealed``) and the owner reads them. stdlib only."""
from __future__ import annotations

import fnmatch
import glob
import json
import re
from pathlib import Path

from explainer_engine.governance import root_dir

GATE_CONFIG = Path(__file__).with_name("gate_files.json")
NEVER_FILES = ("jobs/creator_ok.jsonl",)
NEVER_DIRS = ("jobs/send_gate",)
NEVER_LITERALS = ("jobs/creator_ok.jsonl", "jobs/send_gate/records.jsonl", "jobs/send_gate/quarantine.jsonl",
                  "jobs/send_gate/incidents.jsonl", "jobs/send_gate/incidents_seen.json", "jobs/send_gate/stop_blocks.json")
SEND_NAMES = ("records.jsonl", "quarantine.jsonl", "incidents.jsonl", "incidents_seen.json", "stop_blocks.json")
HOOK_OFF = ("disableAllHooks",)                       # a setting that turns every hook off: no command may name it unless read-only
READ_ONLY = {"cat", "head", "tail", "less", "more", "ls", "wc", "grep", "egrep", "fgrep", "rg", "diff", "cmp", "stat", "file", "sha256sum",
             "sha1sum", "md5sum", "du", "test", "[", "echo", "printf", "true", "pwd", "cd", "realpath", "readlink", "basename", "dirname",
             "jq", "nl", "tac", "sort", "uniq", "cut", "tr", "awk", "xxd", "od", "strings", "which", "command"}
GIT_READ_ONLY = {"status", "diff", "log", "show", "blame", "ls-files", "rev-parse", "grep", "check-ignore", "cat-file", "describe", "shortlog"}
INTERPRETERS = {"python", "python3", "node", "nodejs", "perl", "ruby", "php", "lua", "deno", "bun", "pwsh", "powershell"}
WRITE_TOKENS = re.compile(
    r"""open\s*\([^,)]+,\s*(?:mode\s*=\s*)?['"][^'"]*[wax+][^'"]*['"]|open\s*\([^)]*mode\s*=\s*['"][^'"]*[wax+]|\.write\w*\s*\(|write_text|write_bytes|writeFile|appendFile|createWriteStream|shutil\.|"""
    r"""os\.(replace|rename|remove|unlink|truncate|symlink|link)|\.(unlink|touch|rename|replace|truncate|symlink_to|hardlink_to)\s*\(|"""
    r"""\bsed\b[^|;\n]*\s-[a-zA-Z]*i|\bln\b|\bmv\b|\bcp\b|\brm\b|\btee\b|\bdd\b|\binstall\b|\bsponge\b|\btruncate\b|\bperl\b[^|;\n]*-[a-zA-Z]*i|"""
    r"""json\.dump\s*\(|\bsetattr\b|Set-Content|Add-Content|Out-File|\bcurl\b[^|;\n]*\s-[a-zA-Z]*[oO]\b|\bwget\b[^|;\n]*\s-[a-zA-Z]*O\b|"""
    r"""\brsync\b|\bscp\b|\bgit\s+(checkout|restore|apply|stash|reset|clean)\b|\bex\b|\bed\b|\bvi\b|\bvim\b|\bnano\b|\bsponge\b""")
REDIRECT = re.compile(r"(?:^|[\s;&|()])(?:\d*|&)>>?\|?\s*(['\"]?)([^\s;&|()<>'\"]+)\1")
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
_VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}|([A-Za-z_][A-Za-z0-9_]*))")


# ---- the lists -------------------------------------------------------------------------------------------------------------

def gate_config() -> dict:
    """``gate_files.json``; a missing or broken file counts as SWITCHED OFF (the mechanism is not the owner's switch)."""
    try:
        cfg = json.loads(GATE_CONFIG.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def gate_enabled() -> bool:
    return gate_config().get("enabled") is True


def gate_patterns() -> list[str]:
    return [p for p in gate_config().get("paths", []) if isinstance(p, str)] if gate_enabled() else []


def rel_of(root: Path, path: str | Path, cwd: Path | None = None) -> str | None:
    """The repo-relative posix path of ``path`` (symlinks followed), or None when it lies outside the repo."""
    p = Path(str(path).replace("\\", "/")).expanduser()
    p = p if p.is_absolute() else (cwd or root) / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError, RuntimeError):
        return None


def never(rel: str | None) -> bool:
    return rel is not None and (rel in NEVER_FILES or any(rel == d or rel.startswith(d + "/") for d in NEVER_DIRS))


def gate_file(rel: str | None) -> bool:
    """True when switched ON and ``rel`` matches a gate pattern (``dir/**`` = everything below; no ``*`` = exactly that file)."""
    if rel is None:
        return False
    for pat in gate_patterns():
        if pat.endswith("/**"):
            if rel == pat[:-3] or rel.startswith(pat[:-2]):
                return True
        elif fnmatch.fnmatch(rel, pat):
            return True
    return False


def protected_edit(root: Path, path: str | Path) -> tuple[str, str] | None:
    """For a Write/Edit target: ``("never", rel)``, ``("gate", rel)`` or None."""
    rel = rel_of(root, path)
    if never(rel):
        return ("never", rel)
    if gate_file(rel):
        return ("gate", rel)
    return None


def _literals(root: Path) -> list[str]:
    """Every protected file that can be named: the fixed ones, plus (switched on) the files below the gate patterns."""
    out = list(NEVER_LITERALS)
    for pat in gate_patterns():
        base = pat[:-3] if pat.endswith("/**") else pat
        if pat.endswith("/**"):
            p = root / base
            out += [q.relative_to(root).as_posix() for q in p.rglob("*") if q.is_file()] if p.is_dir() else []
        elif "*" in pat or "?" in pat:
            out += [Path(g).relative_to(root).as_posix() for g in glob.glob(str(root / pat))]
        else:
            out.append(pat)
    return list(dict.fromkeys(out))


# ---- the shell ------------------------------------------------------------------------------------------------------------

def _expand(tok: str, env: dict[str, str]) -> str:
    def sub(m):
        name = m.group(1) or m.group(3)
        return env.get(name, m.group(2) or "") if name else ""
    return _VAR.sub(sub, tok)


def _hit(tok: str, root: Path, cwd: Path, lits: list[str], dirs: set[str]) -> str | None:
    """The protected file this token names (None when none): a path, a glob, or the directory that holds one."""
    tok = tok.strip("'\"")
    if tok.startswith("-"):                                    # an option: only --opt=path names a path
        if "=" not in tok:
            return None
        tok = tok.split("=", 1)[1]
    if not tok:
        return None
    if re.search(r"[*?\[]", tok):
        base = tok if Path(tok).is_absolute() else (cwd / tok).as_posix()
        try:
            rel_pat = Path(base).relative_to(root.resolve()).as_posix() if Path(base).is_absolute() else base
        except ValueError:
            try:
                rel_pat = Path(base).relative_to(root).as_posix()
            except ValueError:
                return None
        for lit in lits:
            if fnmatch.fnmatch(lit, rel_pat):
                return lit
        return None
    rel = rel_of(root, tok, cwd)
    if rel is None:
        return None
    if rel in lits or never(rel) or gate_file(rel):
        return rel
    if rel in dirs:
        return rel
    return None


def _segments(cmd: str):
    from explainer_engine.governance.hooks import commands
    return commands(cmd)


_REDIR_TOKEN = re.compile(r"\d*>>?|&>>?|>\||\d*<>")


def refusal_bash(cmd: str, root: Path) -> tuple[str, str, str] | None:
    """``(kind, file, message)`` for a Bash command that writes a protected file (kind ``never`` = no word unlocks it, ``gate`` = the owner's
    ``protected_config`` word on that file does), or None."""
    root = Path(root).resolve()
    text = cmd.replace("\\", "/")
    lits = _literals(root)
    dirs = {"jobs", "jobs/send_gate"}
    env: dict[str, str] = {}
    cwd = root
    segs = _segments(cmd)

    def refuse(what: str):
        is_never = never(what) or what in dirs or what.endswith("/")
        why = ("the owner's recorded word and the send gate's records are written only by their own code (jobs/creator_ok.jsonl, "
               "jobs/send_gate/*: never by hand)" if is_never else "a gate file changes only on the owner's recorded protected_config word")
        return ("never" if is_never else "gate", what, f"refused (T2.7 path guard): this command writes {what}; {why}")

    for argv in segs:
        i = 0
        while i < len(argv) and _ASSIGN.match(argv[i]):
            i += 1
        if i == len(argv):                                     # only assignments: they hold for the rest of the line
            for a in argv:
                k, v = _ASSIGN.match(a).groups()
                env[k] = _expand(v, env)
            continue
        args = [_expand(a, env) for a in argv[i:]]
        name = Path(args[0]).name
        if name == "export":
            for a in args[1:]:
                m = _ASSIGN.match(a)
                if m:
                    env[m.group(1)] = _expand(m.group(2), env)
            continue
        if name == "cd":
            if len(args) > 1 and args[1] != "-":
                target = Path(args[1]).expanduser()
                cwd = (target if target.is_absolute() else cwd / target).resolve()
            continue
        for k, a in enumerate(args[:-1]):                      # a redirect writes its target, whatever the command is
            if _REDIR_TOKEN.fullmatch(a):
                h = _hit(args[k + 1], root, cwd, lits, dirs)
                if h:
                    return refuse(h)
        hits = [h for a in args[1:] for h in [_hit(a, root, cwd, lits, dirs)] if h]
        if not hits or _read_only(name, args):
            continue
        if name in INTERPRETERS and not WRITE_TOKENS.search(text):
            continue                                           # an interpreter that names the file but writes nothing
        return refuse(hits[0])
    # words that no path analysis resolves: a protected path inside a script text, a setting that turns the hooks off
    if _interpreter_writes(segs, text):
        for lit in _literals(root) + ["jobs/send_gate/"]:
            if lit in text and (never(lit) or gate_file(lit) or lit.endswith("/")):
                return refuse(lit)
        if "creator_ok" in text:
            return refuse("jobs/creator_ok.jsonl")
    for w in HOOK_OFF:
        if w in text and not all(_read_only(Path(a[0]).name, a) for a in segs if a):
            return ("never", w, f"refused (T2.7 path guard): a command that names {w}; the hooks are not switched off by a thread")
    return None


def _read_only(name: str, args: list[str]) -> bool:
    if name == "git":
        sub = next((a for a in args[1:] if not a.startswith("-")), "")
        return sub in GIT_READ_ONLY
    if name == "find":
        return not any(a in ("-delete", "-exec", "-execdir", "-ok", "-fprint", "-fprintf", "-fls") for a in args)
    if name == "sed":
        return not any(re.fullmatch(r"-[a-zA-Z]*i\S*", a) or a == "--in-place" for a in args)
    if name == "awk":
        return not any("system(" in a or "print >" in a or "printf >" in a for a in args)
    return name in READ_ONLY and name not in ("command",)


def _interpreter_writes(segs, text: str) -> bool:
    """True when the command is (or starts) an interpreter or a shell script text and the text holds a write."""
    uses = any(Path(a[0]).name in INTERPRETERS or Path(a[0]).name in ("bash", "sh", "zsh", "dash") for a in segs if a) or "<<" in text
    return uses and bool(WRITE_TOKENS.search(text))
