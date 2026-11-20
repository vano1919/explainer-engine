"""Shared rules of the Gemini code lane (skill ``gemini-coding``, creator 2026-11-20): the never-list, the secret scan, the
task file, and the git helpers that ``gemini_pack.py`` and ``gemini_intake.py`` both use.

Gemini cannot see GitHub, cannot run our tests and cannot see later commits, so nothing it returns is trusted by itself
(PR #154/#155, 2026-11-07: whole files from an older base would have reverted newer docs). The pack reads only from a PINNED
commit (``git show <sha>:<path>``), never from the working tree, and the intake takes only new files or hunks against that
commit. The lane tools themselves, governance, money, secrets, CI and the registry never go to Gemini (skill section 2).

stdlib plus ``explainer_engine.core.store`` only. Files under ``tools/`` are force-added (``tools/`` is gitignored)."""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from explainer_engine.core import store  # noqa: E402

TASK_SCHEMA = "gemini_task/1"
MANIFEST_KINDS = ("new", "patch")
MAX_FILE_BYTES = 3_000_000          # the Drive connector refuses files over about 3.1 MB per call (plan section 1)
SHRINK_MAX_PCT = 30                 # skill section 5: an existing file may not shrink by more than 30 %
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# The never-list (skill section 2). fnmatch on the lower-cased posix path; "*" also crosses "/".
NEVER_GLOBS: tuple[tuple[str, str], ...] = (
    # secrets and auth
    (".env", "secrets"), ("*/.env", "secrets"), (".env.*", "secrets"), ("*/.env.*", "secrets"),
    ("*.pem", "secrets"), ("*.key", "secrets"), ("*.p12", "secrets"), ("*.pfx", "secrets"),
    ("*/id_rsa*", "secrets"), ("*/id_ed25519*", "secrets"), ("*credentials*.json", "secrets"),
    ("*secrets*.json", "secrets"), ("*client_secret*", "secrets"), ("*token*.json", "secrets"),
    ("tools/*", "secrets and the lane's own tools (tools/ holds secrets and gemini_pack/gemini_intake)"),
    # governance, hooks, CI, registry, thresholds
    ("explainer_engine/governance/*", "governance and the owner-requirements registry"),
    (".claude/settings*", "hooks and settings.json"), (".claude/hooks/*", "hooks and settings.json"),
    (".claude/rules/*", "rules"), (".claude/agents/*", "agent files"),
    ("docs/layers/*", "layer records"), ("docs/blueprint/*", "blueprint decision cards"),
    ("claude.md", "CLAUDE.md"), ("config/model_routing.json", "models and effort"),
    (".github/*", "CI workflows"), ("jobs/*", "job records"),
    ("explainer_engine/qa/send_validators.py", "send validators and thresholds"),
    ("explainer_engine/standards/sourced_rules.json", "sourced rules (thresholds)"),
    # money and paid launchers (OR-34)
    ("config/spend_caps.json", "spend caps"), ("config/*caps*", "spend caps"),
    ("explainer_engine/core/ledger.py", "the ledger"), ("explainer_engine/cloud/*", "paid launchers (cloud)"),
    ("explainer_engine/training/pods/*", "paid launchers (pods)"), ("explainer_engine/publish/*", "upload and auth"),
    ("explainer_engine/imagegen/gemini.py", "paid Gemini API client"), ("explainer_engine/llm/*", "paid API clients"),
    ("*modal*", "paid launcher (Modal)"), ("*runpod*", "paid launcher (RunPod)"),
    ("*elevenlabs*", "paid launcher (ElevenLabs)"), ("*ledger*", "the ledger"),
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("API key (sk-)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("AWS key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("assigned secret", re.compile(r"""(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['"][A-Za-z0-9_\-/+=]{20,}['"]""")),
)


class LaneError(Exception):
    """A refusal that stops the tool before it writes anything."""


# ---- small helpers ---------------------------------------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(p: str) -> str | None:
    """The repo-relative posix path ``p`` when it is plain (no absolute path, no ``..``, no backslash), else None."""
    if not isinstance(p, str) or not p or "\\" in p or p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        return None
    pp = PurePosixPath(p)
    if pp.as_posix() != p or any(part in ("", ".", "..") for part in pp.parts):
        return None
    return p


def never_reason(path: str) -> str | None:
    """Why ``path`` may never go to or come from Gemini (skill section 2), or None."""
    low = path.lower()
    for pattern, why in NEVER_GLOBS:
        if fnmatch.fnmatch(low, pattern):
            return why
    return None


def secret_hits(data: bytes) -> list[str]:
    """Names of the secret patterns found in ``data`` (never the secret itself)."""
    text = data.decode("utf-8", errors="replace")
    return [name for name, rx in SECRET_PATTERNS if rx.search(text)]


def write_json(path: Path, payload: object) -> Path:
    return store.write_json_atomic(path, payload)


# ---- git -------------------------------------------------------------------------------------------------------------------

def git(repo: Path, *args: str, input: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=input, capture_output=True)
    if check and proc.returncode != 0:
        raise LaneError(f"git {' '.join(args[:2])} failed: {proc.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return proc


def commit_exists(repo: Path, sha: str) -> bool:
    return bool(SHA_RE.match(sha)) and git(repo, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def blob_at(repo: Path, sha: str, path: str) -> bytes | None:
    """The bytes of ``path`` at commit ``sha``, or None when the commit has no such file."""
    proc = git(repo, "show", f"{sha}:{path}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def mode_at(repo: Path, sha: str, path: str) -> str | None:
    proc = git(repo, "ls-tree", sha, "--", path, check=False)
    out = proc.stdout.decode("utf-8", "replace").split()
    return out[0] if proc.returncode == 0 and out else None


def head_sha(repo: Path, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", ref).stdout.decode().strip()


# ---- the task file ---------------------------------------------------------------------------------------------------------

def load_task(path: Path) -> dict:
    """Read and check ``task.json`` (``gemini_task/1``): task id, pinned base_sha and the path lists."""
    try:
        task = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LaneError(f"task.json unreadable: {exc}") from exc
    errs: list[str] = []
    if task.get("schema") != TASK_SCHEMA:
        errs.append(f"schema must be {TASK_SCHEMA}")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,40}$", str(task.get("task", ""))):
        errs.append("task id must be letters, digits, dot, dash or underscore")
    if not SHA_RE.match(str(task.get("base_sha", ""))):
        errs.append("base_sha must be a full 40-character lower-case sha (fill it with the head sha at packing)")
    for key in ("create", "change", "read", "tests", "suites"):
        vals = task.get(key, [])
        if not isinstance(vals, list) or any(safe_path(v) is None for v in vals):
            errs.append(f"{key} must be a list of plain repo-relative posix paths")
    if not task.get("team_branch"):
        errs.append("team_branch is required (the branch the draft PR goes against)")
    if errs:
        raise LaneError("; ".join(errs))
    for key in ("create", "change", "read", "tests", "suites"):
        task.setdefault(key, [])
    return task


def allowed_paths(task: dict) -> set[str]:
    return set(task["create"]) | set(task["change"])


# ---- python surface (for the shrink and public-function checks) ------------------------------------------------------------

def public_names(source: str) -> set[str]:
    """Top-level public functions and classes and the public methods of those classes, as ``name`` / ``Class.name``."""
    names: set[str] = set()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            names.add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_"):
                        names.add(f"{node.name}.{sub.name}")
    return names
