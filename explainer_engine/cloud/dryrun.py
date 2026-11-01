"""``runpod dryrun --script <pod.sh>``: everything about a pod script that can be known before a pod bills (P1b, CR-18). No pod,
no GPU, no money: ``bash -n``, the pod-script lint (``runpod.lint_pod_script``), four static rules of the install steps, and an
existence check of every Hugging Face repo id the script names, and the ``# needs:`` list of a script that downloads (CR-18). The result is written under ``tools/runpod/dryrun/<sha256 of the
script>.json`` and ``preflight_create`` refuses a script pod without a passing record for exactly that text.

The static rules come from what each cost a pod (docs/PROGRESS.md 2026-10-24..29): an unpinned ``pip install -U`` or ``git clone``
made the same script a different job each day, ``|| true`` on an install let a pod train on a half-installed stack, and a script that
cannot stop after its install stage cannot be proved on a cheap pod first (``DRY=1``).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from explainer_engine.cloud import pins as pins_mod
from explainer_engine.core import store

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "tools" / "runpod" / "dryrun"

INSTALL = re.compile(r"\bpip3?\s+install\b|\bgit\s+clone\b|\bapt(-get)?\s+install\b")
FETCH = re.compile(r"\bsnapshot_download\b|\bhf_hub_download\b|\bhf\s+download\b|\bhuggingface-cli\s+download\b")
SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
REPO_ID = r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*"


GIT_URL = re.compile(r"git\+https?://\S+")
PINNED_GIT_URL = re.compile(r"^git\+https?://[^@\s]+@[0-9a-f]{40}(?:[#\"'&;)]|$)")  # the FIRST `@` of the url carries the ref: only a lowercase 40-hex sha pins
DRY_VAR = r"""(?:["']?\$\{DRY(?::?-\w*)?\}["']?|["']?\$DRY["']?)"""
DRY_IS_ONE = rf"""\[\[?\s+{DRY_VAR}\s+(?:=|==|-eq)\s+["']?1["']?\s+\]\]?"""  # a test that is true when DRY is 1, and only then
DRY_ONE_LINE = re.compile(rf"^\s*{DRY_IS_ONE}\s*&&\s*exit\s+0\s*$")
DRY_IF = re.compile(rf"^\s*if\s+{DRY_IS_ONE}\s*;?\s*(?:then\b(.*))?$")


NEEDS_LINE = re.compile(r"^#\s*needs:\s*(\S.*?)\s*$", re.M)
NEEDS_CALL = re.compile(r"^\s*ee_needs_check\b", re.M)


def needs_of(text):
    """[(path, min_bytes)] of the script's ``# needs: <path> [min_bytes]`` lines (CR-18); ``# needs: none`` gives []. A path may use
    ``$VAR`` (the pod's env). min_bytes defaults to 1."""
    out = []
    for m in NEEDS_LINE.finditer(text or ""):
        parts = m.group(1).split()
        if parts[0] == "none":
            continue
        out.append((parts[0], int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1))
    return out


def needs_problems(text):
    """CR-18: a pod script that downloads (a weight, a code file) lists what it needs on disk afterwards as ``# needs: <path> [min_bytes]``
    lines (or ``# needs: none``, said on purpose) and calls ``ee_needs_check`` (the wrapper's function) right after its downloads, so a
    missing file ends the pod ``FAILED rc=66`` before any GPU step. A script that downloads nothing needs neither."""
    body = "\n".join(ln for _, ln in logical_lines(text))
    if not FETCH.search(body):
        return []
    lines = NEEDS_LINE.findall(text or "")
    if not lines:
        return ["no `# needs: <path> [min_bytes]` list (or `# needs: none`) although the script downloads: a missing weight would be "
                "found by the first GPU step instead of before it (CR-18, T22)"]
    if any(x.split()[0] == "none" for x in lines):
        return []
    if not NEEDS_CALL.search(body):
        return ["`# needs:` is listed but `ee_needs_check` is never called after the downloads: the list is not checked (CR-18)"]
    return []


def sha256_of(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def logical_lines(text):
    """(first line number, text) of each shell command, backslash continuations joined, comments dropped."""
    out, buf, start = [], "", 0
    for i, raw in enumerate((text or "").splitlines(), 1):
        if not buf:
            start = i
        ln = raw.rstrip()
        if ln.endswith("\\"):
            buf += ln[:-1] + " "
            continue
        buf += ln
        if not buf.lstrip().startswith("#") and buf.strip():
            out.append((start, buf))
        buf = ""
    if buf.strip():
        out.append((start, buf))
    return out


def _pip_packages(line):
    """The package arguments of the ``pip install`` in a line (flags and their values dropped)."""
    m = re.search(r"\bpip3?\s+install\b(.*?)(?:\|\||&&|;|\)|$)", line)
    if not m:
        return []
    toks, out, skip = re.findall(r"""(?:[^\s"']+|"[^"]*"|'[^']*')+""", m.group(1)), [], False
    for t in toks:
        if skip:
            skip = False
            continue
        if t in ("-r", "--requirement", "-c", "--constraint", "-i", "--index-url", "--extra-index-url", "-f", "--find-links", "-t", "--target"):
            skip = True
            continue
        if t.startswith("-"):
            continue
        out.append(t.strip("\"'"))
    return out


def _git_url_pinned(url):
    return bool(PINNED_GIT_URL.match(url.lstrip("\"'")))


def _dry_if_exits_zero(cmds, i):
    """True when ``cmds[i]`` is ``if <DRY is 1>; then`` and its THEN branch (not an else, not a nested ``if``) runs ``exit 0``.
    The block is read statement by statement (split on ``;`` and newlines) up to its own ``fi``."""
    m = DRY_IF.match(cmds[i][1])
    if not m:
        return False
    chunks = [m.group(1)] if m.group(1) is not None else []
    seen_then = m.group(1) is not None
    for _, ln in cmds[i + 1:i + 40]:
        chunks.append(ln)
    depth = 0
    for chunk in chunks:
        for stmt in re.split(r";|\n", chunk):
            st = stmt.strip()
            if not seen_then:
                if st == "then":
                    seen_then = True
                    continue
                if st.startswith("then "):
                    seen_then, st = True, st[5:].strip()
                else:
                    return False  # something other than `then` follows the condition
            if re.match(r"if\b", st):
                depth += 1
            elif re.match(r"fi\b", st):
                if depth == 0:
                    return False  # the block ended without an exit 0
                depth -= 1
            elif depth == 0 and re.match(r"(else|elif)\b", st):
                return False  # whatever follows belongs to the other branch
            elif depth == 0 and re.fullmatch(r"exit\s+0", st):
                return True
    return False


def static_problems(text, pins=None):
    """Problems found by reading the script (empty = fine). Line numbers are those of the first physical line of the command."""
    pins = pins or pins_mod.load()
    cmds = logical_lines(text)
    out = []
    last_install = None
    pinned_sha = {e["sha"] for e in pins["git"].values() if e.get("sha")}
    for n, ln in cmds:
        is_install = bool(INSTALL.search(ln))
        if is_install:
            last_install = n
        upgrade = re.search(r"\bpip3?\s+install\b[^|;&]*?\s(-U|--upgrade)\b", ln)
        if upgrade:
            loose = [p for p in _pip_packages(ln) if "==" not in p and not any(_git_url_pinned(u) for u in GIT_URL.findall(p))]
            if loose:
                out.append(f"line {n}: `pip install -U` without `==` for {', '.join(loose)}: the same script would install a different "
                           "version every day (pin it in config/cloud_pins.json)")
        for url in GIT_URL.findall(ln):
            if not _git_url_pinned(url):  # a branch, a tag or a short sha after @ moves: only a 40-hex sha pins
                out.append(f"line {n}: `{url.strip(chr(34) + chr(39))[:70]}` has no `@<40-hex sha>`: a branch or no ref is the repo's HEAD of the day")
        if re.search(r"\bgit\s+clone\b", ln):
            later = [c for m, c in cmds if m >= n and re.search(r"\bgit\b[^|;&]*\b(checkout|reset|fetch)\b", c) and SHA40.search(c)]
            shas = {s for c in later for s in SHA40.findall(c)} | set(SHA40.findall(ln))
            if not shas:
                out.append(f"line {n}: `git clone` without a pinned sha (no `git checkout <40-hex sha>` after it): the repo's HEAD of the "
                           "day is not a reproducible job (sha in config/cloud_pins.json)")
            elif not shas & pinned_sha:
                out.append(f"line {n}: `git clone` is pinned to {sorted(shas)[0][:12]}, which is not a sha of config/cloud_pins.json "
                           "(a changed pin is a PR)")
        if (is_install or FETCH.search(ln)) and re.search(r"\|\|\s*true\b", ln):
            out.append(f"line {n}: `|| true` on an install or download step ({ln.strip()[:50]}): a failed install must stop the pod, "
                       "not train on a half-installed stack")
    if last_install is not None:
        # a real gate: `[ "${DRY:-0}" = 1 ] && exit 0`, or an `if` over DRY = 1 whose THEN branch runs `exit 0`
        gates = [n for i, (n, ln) in enumerate(cmds) if n > last_install and (DRY_ONE_LINE.match(ln) or _dry_if_exits_zero(cmds, i))]
        if not gates:
            out.append("no `DRY=1` gate after the install stage (e.g. `[ \"${DRY:-0}\" = 1 ] && exit 0`): the script cannot be proved on a "
                       "cheap pod up to its install steps before the long stages are paid")
    return out


def repo_ids(text):
    """[(repo_id, repo_type)] the script names literally: ``snapshot_download`` / ``hf_hub_download`` (also under an alias) /
    ``hf download`` / ``repo_id=...`` and the heartbeat's dataset. Ids with a ``$`` or ``{`` (computed at run time) are skipped."""
    body = "\n".join(ln for _, ln in logical_lines(text))
    aliases = {"snapshot_download", "hf_hub_download"} | set(re.findall(r"(?:snapshot_download|hf_hub_download)\s+as\s+(\w+)", body))
    found = {}

    def call(start, end):  # the call a match sits in: from its "(" to its ")"; repo_type may come before or after the id
        lo, hi = body.rfind("(", 0, start), body.find(")", end)
        return body[lo if lo >= 0 and "\n" not in body[lo:start] else start:hi if hi >= 0 else end + 200]

    def add(rid, window):
        if "$" in rid or "{" in rid:
            return
        t = re.search(r"repo_type\s*=\s*[\"'](dataset|model|space)[\"']", window) or re.search(r"--repo-type[ =](dataset|model|space)", window)
        found.setdefault(rid, t.group(1) if t else "model")

    for m in re.finditer(r"\b(%s)\(\s*[\"'](%s)[\"']" % ("|".join(map(re.escape, aliases)), REPO_ID), body):
        add(m.group(2), call(m.start(), m.end()))
    for m in re.finditer(r"\brepo_id\s*=\s*[\"'](%s)[\"']" % REPO_ID, body):
        add(m.group(1), call(m.start(), m.end()))
    for m in re.finditer(r"\b(?:hf|huggingface-cli)\s+download\s+(%s)" % REPO_ID, body):
        add(m.group(1), body[m.end():body.find("\n", m.end()) if "\n" in body[m.end():] else len(body)])
    hb = re.search(r"^#\s*heartbeat:\s*datasets/([^/\s:]+/[^/\s:]+):", text or "", re.M)
    if hb:
        found[hb.group(1)] = "dataset"
    return sorted(found.items())


def job_repo_ids(text, folder):
    """The Hub repos the job files of a script name (audit 2026-11-01 #15: p12b.sh fetches only its own job files, every weight repo is
    in p12b.json, so ``repo_ids`` of the script text alone proved nothing about them). Reads the json files of ``folder`` whose name the
    script mentions; every dict with a ``repo`` or ``hf`` id counts. Type: an explicit ``repo_type``; else by the dict's OWN keys:
    ``path``/``paths``/``dir`` = dataset, ``file``/``files``/``revision`` = model; else dataset when a nested ``path`` exists."""
    found = {}
    if folder is None or not Path(folder).is_dir():
        return []

    def has_path(o):
        if isinstance(o, dict):
            return any(k in ("path", "paths", "dir") or has_path(v) for k, v in o.items())
        return isinstance(o, list) and any(has_path(v) for v in o)

    def walk(o):
        if isinstance(o, dict):
            rid = o.get("repo") if isinstance(o.get("repo"), str) else o.get("hf") if isinstance(o.get("hf"), str) else None
            if rid and re.fullmatch(REPO_ID, rid):
                own = set(o)
                kind = (o.get("repo_type") or ("dataset" if own & {"path", "paths", "dir"} else
                        "model" if own & {"file", "files", "revision"} else "dataset" if has_path(o) else "model"))
                found.setdefault(rid, kind)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in sorted(Path(folder).glob("*.json")):
        if f.name in (text or ""):
            try:
                walk(json.loads(f.read_text(encoding="utf-8")))
            except ValueError:
                continue
    return sorted(found.items())


def all_repo_ids(text, folder=None):
    """``repo_ids`` of the script text plus ``job_repo_ids`` of its job files (a model beats a dataset on the same id)."""
    merged = dict(job_repo_ids(text, folder))
    merged.update(dict(repo_ids(text)))
    return sorted(merged.items())


def hf_exists(repo_id, repo_type):
    """Default existence check against the Hub (HfApi.repo_info with HF_TOKEN when set): (ok, note)."""
    try:
        from huggingface_hub import HfApi
        from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError
    except ImportError as e:
        return False, f"huggingface_hub is not installed here ({e})"
    token = os.environ.get("HF_TOKEN") or None
    api = HfApi(token=token)
    try:
        info = api.repo_info(repo_id, repo_type=repo_type)
        if getattr(info, "gated", False):
            # repo_info of a gated repo succeeds without access: only auth_check (a file-level probe) says whether THIS token may download
            api.auth_check(repo_id, repo_type=repo_type, token=token)
    except RepositoryNotFoundError:
        return False, "no such repo (or private and this token cannot see it)"
    except GatedRepoError:
        return False, "gated: this token has not been granted access (a pod would bill its install and then fail the download)"
    except Exception as e:  # noqa: BLE001 - network, auth: the check could not run, which is not a pass
        return False, f"could not be checked ({str(e)[:80]})"
    return True, "gated: access proved with this token" if getattr(info, "gated", False) else ""


def bash_syntax(text):
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(text)
        name = f.name
    try:
        r = subprocess.run(["bash", "-n", name], capture_output=True, text=True, timeout=30)
        return [r.stderr.strip().replace(name, "script")] if r.returncode else []
    finally:
        os.unlink(name)


def run(text, *, exists=None, pins=None, offline=False, now=None, folder=None):
    """The dry run of a script text: a record ``{sha256, ok, problems, repos, pins_sha, at}``. ``offline`` skips the Hub check and
    can never produce an ``ok`` record (a script whose repos were not seen is not proved)."""
    from explainer_engine.cloud import runpod
    pins = pins or pins_mod.load()
    problems = [f"bash -n: {p}" for p in bash_syntax(text)]
    problems += [f"lint: {p}" for p in runpod.lint_pod_script(text)]
    problems += static_problems(text, pins)
    problems += [f"needs: {p}" for p in needs_problems(text)]
    repos = []
    for rid, kind in all_repo_ids(text, folder):
        if offline:
            repos.append({"id": rid, "type": kind, "ok": None, "note": "not checked (--offline)"})
            continue
        ok, note = (exists or hf_exists)(rid, kind)
        repos.append({"id": rid, "type": kind, "ok": bool(ok), "note": note})
        if not ok:
            problems.append(f"{kind} repo {rid}: {note}")
    if offline:
        problems.append("the Hugging Face repos were not checked (--offline): a dry run that did not look is not a pass")
    return {"sha256": sha256_of(text), "ok": not problems, "problems": problems, "repos": repos,
            "pins_sha": sha256_of(Path(pins_mod.PINS_FILE).read_text(encoding="utf-8")) if Path(pins_mod.PINS_FILE).exists() else "",
            "at": time.time() if now is None else now}


def record(rec):
    DIR.mkdir(parents=True, exist_ok=True)
    store.write_json_atomic(DIR / f"{rec['sha256']}.json", rec)
    return DIR / f"{rec['sha256']}.json"


PLACEHOLDER = re.compile(r"\bPLACEHOLDER\w*")


def placeholder_problems(text, folder=None):
    """A pod must never start on a pin that was never filled (audit 2026-11-01: a sha256 line read PLACEHOLDER_SHA_*, so the pod would
    bill its install and then exit at ``sha256sum -c``). Looks in the script text and, when ``folder`` is given, in every file of that
    folder (not below it) whose name the script mentions: the job files it fetches. Empty = no placeholder left."""
    out = [f"script: {m.group(0)} (a pin that was never filled)" for m in PLACEHOLDER.finditer(text or "")]
    if folder is not None and Path(folder).is_dir():
        for f in sorted(Path(folder).iterdir()):
            if f.is_file() and f.suffix in (".py", ".json", ".sh", ".yaml", ".toml") and f.name in (text or "") and f.read_text(encoding="utf-8", errors="replace") != text:
                hits = sorted({m.group(0) for m in PLACEHOLDER.finditer(f.read_text(encoding="utf-8", errors="replace"))})
                out += [f"{f.name}: {h} (a pin that was never filled)" for h in hits]
    return out


def passed(text, *, pins_path=None):
    """Refusals for a script pod without a passing dry run of exactly this text (empty = it passed, against today's pins)."""
    sha = sha256_of(text)
    p = DIR / f"{sha}.json"
    if not p.exists():
        return [f"no dry run of this script (sha256 {sha[:12]}): run `python -m explainer_engine.cloud.runpod dryrun --script <file>` first (CR-18)"]
    rec = json.loads(p.read_text(encoding="utf-8"))
    if not rec.get("ok"):
        return [f"the dry run of this script (sha256 {sha[:12]}) failed: {'; '.join(rec.get('problems', []))[:200]}"]
    pf = Path(pins_path or pins_mod.PINS_FILE)
    if pf.exists() and rec.get("pins_sha") != sha256_of(pf.read_text(encoding="utf-8")):
        return [f"config/cloud_pins.json changed after the dry run of this script (sha256 {sha[:12]}): run it again"]
    return []
