"""Read the pinned file list of a Hub model revision (size + LFS sha256, or git blob id for small files) for ``launch_a100.json``.

    python -m explainer_engine.training.pods.judge.pin_models Qwen/Qwen3-VL-8B-Instruct <revision>

stdlib only; one GET of ``/api/models/<repo>/revision/<revision>?blobs=true`` (read-only, free). The revision must be a full commit
sha: a branch name is refused (a later upload could replace it)."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

# what the judge needs to run: weights, config, tokenizer and processor files (no README, no .gitattributes)
KEEP = re.compile(r"(\.safetensors|\.safetensors\.index\.json|config\.json|tokenizer.*|vocab\.json|merges\.txt|chat_template\.json|"
                  r"preprocessor_config\.json|video_preprocessor_config\.json|generation_config\.json)$")


def fetch(repo: str, revision: str, token: str | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("the revision must be a full 40-hex commit sha")
    req = urllib.request.Request(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true")
    tok = token or os.environ.get("HF_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def pins(info: dict) -> dict:
    """``{file: {"size": n, "id": sha256 | blob oid, "kind": "sha256" | "git_blob"}}`` for the files the judge needs."""
    out = {}
    for s in info.get("siblings", []):
        name = s["rfilename"]
        if not KEEP.search(name):
            continue
        lfs = s.get("lfs") or {}
        out[name] = {"size": int(s["size"]), "id": lfs.get("sha256") or s.get("blobId"), "kind": "sha256" if lfs.get("sha256") else "git_blob"}
        if not out[name]["id"]:
            raise ValueError(f"{name}: the API returned no hash")
    return dict(sorted(out.items()))


if __name__ == "__main__":
    repo, rev = sys.argv[1], sys.argv[2]
    info = fetch(repo, rev)
    if info.get("sha") != rev:
        raise SystemExit(f"the API answered revision {info.get('sha')}, not {rev}")
    print(json.dumps({"repo": repo, "revision": rev, "files": pins(info)}, indent=1))
