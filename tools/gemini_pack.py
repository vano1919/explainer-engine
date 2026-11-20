"""Pack one Gemini code task (skill ``gemini-coding`` section 3): ``TASK.md``, the tests and ONE ``CONTEXT_<task>.md`` holding the
files the task reads or changes, read from the PINNED commit (never the working tree), each with its path and sha256.

usage: python tools/gemini_pack.py <task_dir> [--repo .] [--out <task_dir>/in] [--pin REF]

``<task_dir>`` holds ``task.json`` (``gemini_task/1``: task, base_sha, team_branch, create, change, read, tests, suites) and
``TASK.md``. ``--pin REF`` writes the commit REF resolves to into a placeholder ``base_sha`` (a valid sha is never overwritten).

Refuses (exit 2, nothing written): a path on the never-list (secrets, ``.env``, ``config/spend_caps.json``, governance, hooks,
settings, CI, the registry, the lane tools, paid launchers); a path that is not plain; a ``read``/``change`` file missing at the
pinned commit; a ``create`` file that already exists there; a symlink or binary file; a secret pattern inside any file; a file or
context over 3 MB (the Drive limit); a TASK.md that names another base sha. Output is deterministic: same commit, same bytes."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_lane as L  # noqa: E402

PLACEHOLDER = re.compile(r"<FILL[^>]*>")
BASE_IN_TASK = re.compile(r"base_sha\W{0,6}([0-9a-f]{40})")


def _check_path(path: str, role: str) -> None:
    if L.safe_path(path) is None:
        raise L.LaneError(f"{role} path is not plain (absolute, '..' or backslash): {path}")
    why = L.never_reason(path)
    if why:
        raise L.LaneError(f"{role} path is on the never-list ({why}): {path}")


def _text_file(data: bytes, path: str) -> str:
    if len(data) > L.MAX_FILE_BYTES:
        raise L.LaneError(f"{path} is {len(data)} bytes, over the Drive limit of {L.MAX_FILE_BYTES}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise L.LaneError(f"{path} is not UTF-8 text (binary files do not go to Gemini)") from exc
    hits = L.secret_hits(data)
    if hits:
        raise L.LaneError(f"{path} holds a secret pattern ({', '.join(hits)}); it never goes to Gemini")
    return text


def _fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _resolve_pin(task_json: Path, repo: Path, ref: str | None) -> None:
    raw = json.loads(task_json.read_text(encoding="utf-8"))
    if L.SHA_RE.match(str(raw.get("base_sha", ""))):
        return                                             # a pinned sha is never overwritten
    if not ref:
        raise L.LaneError("base_sha is a placeholder: pass --pin <ref> to pin it to a commit")
    raw["base_sha"] = L.head_sha(repo, ref)
    L.write_json(task_json, raw)


def pack(task_dir: Path, repo: Path, out: Path | None = None, pin: str | None = None) -> dict:
    task_dir, repo = Path(task_dir), Path(repo)
    out = Path(out) if out else task_dir / "in"
    task_json = task_dir / "task.json"
    _resolve_pin(task_json, repo, pin)
    task = L.load_task(task_json)
    sha, tid = task["base_sha"], task["task"]
    if not L.commit_exists(repo, sha):
        raise L.LaneError(f"base_sha {sha} is not a commit of {repo}")
    for role in ("create", "change", "read", "tests"):
        for p in task[role]:
            _check_path(p, role)
    both = set(task["create"]) & set(task["change"])
    if both:
        raise L.LaneError(f"a path is both create and change: {sorted(both)}")

    context: list[tuple[str, str, bytes]] = []             # (role, path, bytes) read at the pinned commit
    for role in ("change", "read"):
        for p in task[role]:
            if L.mode_at(repo, sha, p) == "120000":
                raise L.LaneError(f"{p} is a symlink at the pinned commit")
            data = L.blob_at(repo, sha, p)
            if data is None:
                raise L.LaneError(f"{role} file {p} does not exist at {sha[:12]}")
            _text_file(data, p)
            context.append((role, p, data))
    for p in task["create"]:
        if L.blob_at(repo, sha, p) is not None:
            raise L.LaneError(f"create path {p} already exists at {sha[:12]}: a new file may not overwrite it (use change)")

    tests: list[tuple[str, bytes]] = []                    # the acceptance contract, from the working tree (new files)
    for p in task["tests"]:
        f = repo / p
        if f.is_symlink() or not f.is_file():
            raise L.LaneError(f"test file {p} is missing in the working tree (the tester writes it before packing)")
        data = f.read_bytes()
        _text_file(data, p)
        tests.append((p, data))

    task_md_src = task_dir / "TASK.md"
    if not task_md_src.is_file():
        raise L.LaneError("TASK.md is missing in the task folder")
    task_md = PLACEHOLDER.sub(sha, task_md_src.read_text(encoding="utf-8"))
    others = {m for m in BASE_IN_TASK.findall(task_md) if m != sha}
    if others or sha not in task_md:
        raise L.LaneError(f"TASK.md must name the pinned base sha {sha} (found other shas: {sorted(others)})")
    _text_file(task_md.encode("utf-8"), "TASK.md")

    parts = [f"# CONTEXT_{tid}.md\n\nPinned commit: `{sha}`. Every file below is its content AT THAT COMMIT, not a later one. "
             f"Answer with unified-diff hunks against these exact bytes (check the sha256).\n"]
    files: list[dict] = []
    for role, p, data in context:
        text = data.decode("utf-8")
        fence = _fence(text)
        digest = L.sha256_bytes(data)
        parts.append(f"\n## `{p}`\nrole: {role}  sha256: `{digest}`  bytes: {len(data)}\n\n{fence}\n{text}"
                     f"{'' if text.endswith(chr(10)) else chr(10)}{fence}\n")
        files.append({"path": p, "role": role, "sha256": digest, "bytes": len(data)})
    context_md = "".join(parts)
    if len(context_md.encode("utf-8")) > L.MAX_FILE_BYTES:
        raise L.LaneError(f"CONTEXT_{tid}.md would be over {L.MAX_FILE_BYTES} bytes: cut the read list")

    out.mkdir(parents=True, exist_ok=True)
    L.store.write_text_atomic(out / "TASK.md", task_md)
    L.store.write_text_atomic(out / f"CONTEXT_{tid}.md", context_md)
    for p, data in tests:
        target = out / p
        L.store.write_text_atomic(target, data.decode("utf-8"))
        files.append({"path": p, "role": "test", "sha256": L.sha256_bytes(data), "bytes": len(data)})
    L.write_json(out / "task.json", task)
    pack_json = {"schema": "gemini_pack/1", "task": tid, "base_sha": sha, "context": f"CONTEXT_{tid}.md",
                 "context_sha256": L.sha256_bytes(context_md.encode("utf-8")), "files": files}
    L.write_json(out / "PACK.json", pack_json)
    return pack_json


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("task_dir", type=Path)
    ap.add_argument("--repo", type=Path, default=L.ROOT)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--pin", help="ref to pin base_sha to when task.json still holds a placeholder")
    args = ap.parse_args(argv)
    try:
        result = pack(args.task_dir, args.repo, args.out, args.pin)
    except L.LaneError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"task": result["task"], "base_sha": result["base_sha"], "files": len(result["files"]),
                      "context_sha256": result["context_sha256"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
