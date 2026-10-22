# from vano1919/tmr-video-script-engine@1c33878:cloud/store.py
"""The durable store: every output of a cloud job is copied here with its sha256 before any pod disk may go (master brief
2026-10-22: never a sole copy on a pod disk; TMR lost 35 pictures that way, RISK_REGISTER R-29).

    python -m explainer_engine.cloud.store push <local_dir> <repo_path>      # damaged files are never pushed
    python -m explainer_engine.cloud.store pull <repo_path> <local_root>
    python -m explainer_engine.cloud.store ls [<repo_path>]
    python -m explainer_engine.cloud.store check <local_dir>                 # damaged files in a folder
    python -m explainer_engine.cloud.store verify <local_dir> <repo_path>    # size + sha256 of every file == local

Backends: a private Hugging Face dataset (``EXPLAINER_STORE_REPO``, default vano1919/tmr-artifacts, token ``HF_TOKEN`` or
``tools/runpod/hf_token.txt``), or a folder (``EXPLAINER_STORE_LOCAL=<dir>``: tests, dry runs, a mounted R2 bucket). The job
record (``cloud/jobs.py``) is pushed with the outputs, so a new machine can read where a job stands. ``verify`` is what
``jobs.Job.mark_stored`` needs before an output counts as stored.

Changed from TMR: stdlib-only backend switch, sha256 sidecar (``.sha256.json``) written with every push so the local store
verifies by hash too, ``verify`` never deletes (a mismatch is reported; deletion is the creator's word), env names.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import struct
import sys
from pathlib import Path

DEFAULT_REPO = "vano1919/tmr-artifacts"
IGNORE = ["*.tmp", "*.tmp-*", "*.part", "*.partial", "*.incomplete", "__pycache__/*", "*.pyc", ".sha256.json"]
KEEP_EMPTY = {"KEEP", ".gitkeep", "__init__.py"}
SIDECAR = ".sha256.json"
ROOT = Path(__file__).resolve().parents[2]


def repo_id():
    return os.environ.get("EXPLAINER_STORE_REPO", DEFAULT_REPO)


def local_store():
    d = os.environ.get("EXPLAINER_STORE_LOCAL")
    return Path(d) if d else None


def hf_token():
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    p = ROOT / "tools" / "runpod" / "hf_token.txt"
    return p.read_text().strip() if p.exists() else None


def _ignored(rel):
    name = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(name, p) for p in IGNORE)


def _mp4_problem(path):
    """A truncated or half-written MP4: the top-level boxes must add up to the file size and include moov."""
    size = path.stat().st_size
    pos, kinds = 0, set()
    with open(path, "rb") as f:
        while pos < size:
            f.seek(pos)
            head = f.read(16)
            if len(head) < 8:
                return "cut off inside a box header"
            n, kind = struct.unpack(">I4s", head[:8])
            if n == 1 and len(head) == 16:
                n = struct.unpack(">Q", head[8:16])[0]
            elif n == 0:
                n = size - pos
            if n < 8:
                return "bad box size"
            kinds.add(kind)
            pos += n
    if pos != size:
        return f"boxes end at {pos}, the file is {size} bytes (cut off)"
    if b"moov" not in kinds:
        return "no moov box (never finalised)"
    return ""


def problem_of(path):
    """Why a file is damaged ('' = looks fine). Cheap content checks by extension; other types only need to be non-empty."""
    path = Path(path)
    ext = path.suffix.lower()
    if path.stat().st_size == 0:
        return "" if path.name in KEEP_EMPTY else "empty file"
    try:
        if ext == ".json":
            json.loads(path.read_text(encoding="utf-8-sig"))
        elif ext == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            from PIL import Image

            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
        elif ext == ".wav":
            import wave

            with wave.open(str(path), "rb") as w:
                if w.getnframes() <= 0:
                    return "wav without audio"
        elif ext == ".flac":
            with open(path, "rb") as f:
                if f.read(4) != b"fLaC":
                    return "not a flac file"
        elif ext == ".mp3":
            with open(path, "rb") as f:
                head = f.read(2)
            if not (head[:2] == b"ID3"[:2] or (len(head) == 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)):
                return "not an mp3 file"
        elif ext in (".mp4", ".m4a", ".mov"):
            return _mp4_problem(path)
    except Exception as e:  # noqa: BLE001 - any reader failure means the file is not usable
        return f"unreadable ({type(e).__name__}: {str(e)[:60]})"
    return ""


def damaged_local(folder):
    """{relative path: reason} for every damaged file under ``folder`` (ignored names are skipped)."""
    folder = Path(folder)
    out = {}
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(folder).as_posix()
        if _ignored(rel):
            continue
        why = problem_of(f)
        if why:
            out[rel] = why
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest(folder, skip=()):
    """{relative path: {bytes, sha256}} of every pushable file."""
    folder = Path(folder)
    out = {}
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(folder).as_posix()
        if _ignored(rel) or rel in skip:
            continue
        out[rel] = {"bytes": f.stat().st_size, "sha256": sha256(f)}
    return out


class StoreError(RuntimeError):
    pass


def push(local_dir, repo_path, api=None):
    """Copy a folder into the store under ``repo_path`` with a sha256 sidecar. Damaged files are skipped and reported.
    Returns {"pushed": [...], "skipped": {rel: why}, "where": str}. Raises StoreError when the store cannot be reached."""
    folder = Path(local_dir)
    if not folder.is_dir():
        raise StoreError(f"not a folder: {folder}")
    bad = damaged_local(folder)
    files = manifest(folder, skip=set(bad))
    prefix = repo_path.strip("/")
    side = folder / SIDECAR
    side.write_text(json.dumps(files, indent=1), encoding="utf-8")
    if (local := local_store()):
        dest = local / prefix
        try:
            dest.mkdir(parents=True, exist_ok=True)
            for rel in list(files) + [SIDECAR]:
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(folder / rel, dest / rel)
        except OSError as e:
            raise StoreError(f"local store {local} not writable: {e}") from e
        return {"pushed": sorted(files), "skipped": bad, "where": str(dest)}
    try:
        from huggingface_hub import HfApi
    except ImportError as e:
        raise StoreError("huggingface_hub is not installed and EXPLAINER_STORE_LOCAL is not set") from e
    api = api or HfApi(token=hf_token())
    try:
        api.create_repo(repo_id(), repo_type="dataset", private=True, exist_ok=True)
        api.upload_folder(folder_path=str(folder), path_in_repo=prefix, repo_id=repo_id(), repo_type="dataset",
                          ignore_patterns=[p for p in IGNORE if p != SIDECAR] + list(bad),
                          commit_message=f"{prefix}: {len(files)} files")
    except Exception as e:  # noqa: BLE001 - network, auth, quota: all mean "not stored"
        raise StoreError(f"push to {repo_id()}:{prefix} failed: {type(e).__name__}: {str(e)[:120]}") from e
    return {"pushed": sorted(files), "skipped": bad, "where": f"hf://{repo_id()}/{prefix}"}


def pull(repo_path, local_root, download=None):
    prefix = repo_path.strip("/")
    if (local := local_store()):
        src = local / prefix
        if not src.is_dir():
            raise StoreError(f"not in the local store: {repo_path}")
        dest = Path(local_root) / prefix
        shutil.copytree(src, dest, dirs_exist_ok=True)
        return dest
    from huggingface_hub import snapshot_download

    download = download or snapshot_download
    path = download(repo_id=repo_id(), repo_type="dataset", allow_patterns=[prefix + "/*"], local_dir=str(local_root),
                    token=hf_token())
    return Path(path) / prefix


def remote_files(prefix="", api=None):
    """{repo path: (size, sha256 or '')} of the store under ``prefix``."""
    prefix = prefix.strip("/")
    if (local := local_store()):
        base = local / prefix if prefix else local
        out = {}
        for f in sorted(base.rglob("*")) if base.exists() else []:
            if f.is_file():
                rel = f.relative_to(local).as_posix()
                out[rel] = (f.stat().st_size, sha256(f))
        return out
    from huggingface_hub import HfApi

    api = api or HfApi(token=hf_token())
    out = {}
    for e in api.list_repo_tree(repo_id(), path_in_repo=prefix or None, recursive=True, repo_type="dataset"):
        if not hasattr(e, "size"):
            continue  # a folder
        lfs = getattr(e, "lfs", None)
        sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", "")) if lfs else ""
        out[e.path] = (e.size or 0, sha or "")
    return out


def ls(prefix="", api=None):
    return sorted(remote_files(prefix, api))


def verify(local_dir, repo_path, api=None):
    """Every pushable local file must be in the store with the same size (and sha256 when the store keeps one).
    Returns {"missing": [...], "damaged": [...], "ok": n}. Nothing is deleted here: a mismatch is reported."""
    prefix = repo_path.strip("/")
    try:
        have = remote_files(prefix, api)
    except Exception as e:  # noqa: BLE001
        raise StoreError(f"store not readable: {type(e).__name__}: {str(e)[:120]}") from e
    skip = damaged_local(local_dir)
    out = {"missing": [], "damaged": [], "ok": 0}
    for rel, info in manifest(local_dir, skip=set(skip)).items():
        remote = have.get(f"{prefix}/{rel}")
        if remote is None:
            out["missing"].append(rel)
        elif remote[0] != info["bytes"] or (remote[1] and remote[1] != info["sha256"]):
            out["damaged"].append(rel)
        else:
            out["ok"] += 1
    return out


def store_job(job, extra_dirs=(), api=None):
    """Push a job's record and its output folders, verify, and mark the outputs stored. Raises StoreError (the job is
    then RECOVERY_REQUIRED, never released) when the copy cannot be confirmed."""
    prefix = f"jobs/{job.state['slug']}/{job.state['id']}"
    res = push(job.dir, prefix, api)
    bad = verify(job.dir, prefix, api)
    if bad["missing"] or bad["damaged"]:
        raise StoreError(f"record not confirmed in the store: missing {bad['missing']}, damaged {bad['damaged']}")
    stored = []
    for d in extra_dirs:
        sub = f"{prefix}/{Path(d).name}"
        push(d, sub, api)
        v = verify(d, sub, api)
        if v["missing"] or v["damaged"]:
            raise StoreError(f"{d}: missing {v['missing']}, damaged {v['damaged']}")
        stored += [str(Path(d) / rel) for rel in manifest(d)]
    outputs = [o["path"] for o in job.state["outputs"] if o["path"] in stored or Path(o["path"]).is_relative_to(job.dir)]
    job.mark_stored(res["where"], outputs or None)
    return res["where"]


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "push" and len(argv) == 3:
        res = push(argv[1], argv[2])
        for rel, why in res["skipped"].items():
            print(f"NOT pushed (damaged): {rel}: {why}")
        print(f"pushed {len(res['pushed'])} files -> {res['where']}")
        return 1 if res["skipped"] else 0
    if cmd == "pull" and len(argv) == 3:
        print("pulled to", pull(argv[1], argv[2]))
    elif cmd == "ls":
        print("\n".join(ls(argv[1] if len(argv) > 1 else "")))
    elif cmd == "check" and len(argv) == 2:
        bad = damaged_local(argv[1])
        print("\n".join(f"{r}: {w}" for r, w in bad.items()) or "no damaged files")
        return 1 if bad else 0
    elif cmd == "verify" and len(argv) == 3:
        res = verify(argv[1], argv[2])
        print(f"ok {res['ok']} | missing: {res['missing'] or 'none'} | differs: {res['damaged'] or 'none'}")
        return 1 if res["missing"] or res["damaged"] else 0
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
