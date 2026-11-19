"""Fetch the inputs an episode run needs from the Hugging Face dataset into the episode's working area (reusable, free).

``python -m explainer_engine.episode.hf_inputs fetch <episode> [--manifest planning/hf_inputs.json] [--only audio/,assets/]``

The manifest (``planning/hf_inputs.json``, committed; the binaries never are) lists every file as ``{"dest": <path inside the
episode folder>, "hf_path": <path in the dataset>, "sha256": <hex>}``. A file already at ``dest`` with the right hash is kept; a
download whose hash differs from the manifest is refused and removed (a wrong file never lands in the working area); a
``dest`` outside the episode folder is refused (R-F). Nothing here is paid: it reads a public dataset with the user's token.

``python -m explainer_engine.episode.hf_inputs add <episode> <dest> <hf_path>`` appends a row after downloading it once and
recording its hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Callable

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.store import write_json_atomic

SCHEMA = "hf_inputs/1"
DEFAULT_MANIFEST = "planning/hf_inputs.json"
DEFAULT_REPO = "vano1919/tmr-artifacts"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(root: Path, rel: str = DEFAULT_MANIFEST) -> dict:
    p = Path(root) / rel
    if not p.is_file():
        raise ConfigError(f"{p} is missing: list the HF inputs of this episode first")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA or not isinstance(doc.get("files"), list):
        raise ContractError(f"{p}: not an {SCHEMA} manifest")
    for f in doc["files"]:
        if not {"dest", "hf_path", "sha256"} <= set(f):
            raise ContractError(f"{p}: a file row needs dest, hf_path and sha256: {f}")
    return doc


def _hub_download(repo: str, hf_path: str, repo_type: str, local_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, hf_path, repo_type=repo_type, local_dir=str(local_dir)))


def fetch(root: Path, manifest_rel: str = DEFAULT_MANIFEST, only: list[str] | None = None,
          download: Callable[[str, str, str, Path], Path] | None = None, cache: Path | None = None) -> dict:
    """Bring every listed file to its ``dest``. Returns ``{fetched, kept, refused, missing_dest}`` (lists of dests)."""
    root = Path(root).resolve()
    doc = load_manifest(root, manifest_rel)
    repo, repo_type = doc.get("repo") or DEFAULT_REPO, doc.get("repo_type") or "dataset"
    download = download or _hub_download
    cache = Path(cache) if cache else root / ".hf_cache"
    out = {"fetched": [], "kept": [], "refused": []}
    for f in doc["files"]:
        dest = (root / f["dest"]).resolve()
        if not dest.is_relative_to(root):
            raise ContractError(f"{f['dest']} is outside the episode folder (R-F)")
        if only and not any(f["dest"].startswith(o) for o in only):
            continue
        if dest.is_file() and _sha(dest) == f["sha256"]:
            out["kept"].append(f["dest"])
            continue
        got = download(repo, f["hf_path"], repo_type, cache)
        if _sha(got) != f["sha256"]:
            out["refused"].append({"dest": f["dest"], "why": f"sha256 {_sha(got)[:12]} differs from the manifest "
                                                            f"{f['sha256'][:12]}"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(got, dest)
        out["fetched"].append(f["dest"])
    return out


def add(root: Path, dest: str, hf_path: str, manifest_rel: str = DEFAULT_MANIFEST, download=None) -> dict:
    """Download ``hf_path`` once, record its hash, and append the row (an existing row for ``dest`` is replaced)."""
    root = Path(root).resolve()
    mp = root / manifest_rel
    doc = load_manifest(root, manifest_rel) if mp.is_file() else {"schema": SCHEMA, "repo": DEFAULT_REPO,
                                                                  "repo_type": "dataset", "files": []}
    got = (download or _hub_download)(doc["repo"], hf_path, doc["repo_type"], root / ".hf_cache")
    row = {"dest": dest, "hf_path": hf_path, "sha256": _sha(got), "bytes": got.stat().st_size}
    doc["files"] = [f for f in doc["files"] if f["dest"] != dest] + [row]
    write_json_atomic(mp, doc)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("episode", type=Path)
    f.add_argument("--manifest", default=DEFAULT_MANIFEST)
    f.add_argument("--only", action="append", help="a dest prefix (repeatable)")
    a_ = sub.add_parser("add")
    a_.add_argument("episode", type=Path)
    a_.add_argument("dest")
    a_.add_argument("hf_path")
    a_.add_argument("--manifest", default=DEFAULT_MANIFEST)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        res = fetch(a.episode, a.manifest, a.only)
        print(json.dumps({k: (len(v) if k != "refused" else v) for k, v in res.items()}, indent=1))
        return 1 if res["refused"] else 0
    print(json.dumps(add(a.episode, a.dest, a.hf_path, a.manifest), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
