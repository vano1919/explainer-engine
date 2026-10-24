"""The vault: nothing we made is lost, and every copy is the creator's (D-73, docs/VAULT.md). stdlib only, so it runs on a pod,
in a cloud session and on the creator's PC alike.

    python -m explainer_engine.vault snapshot [--out docs/VAULT_MANIFEST.json]      # list the primary copy with hashes
    python -m explainer_engine.vault verify [--manifest M]                           # every manifest file still there, same hash
    python -m explainer_engine.vault pull --dest D:\\wldnk_vault [--all] [--only GLOB]  # second copy on a disk, hash-checked
    python -m explainer_engine.vault check-uploaded <local dir> --to <prefix> [--repo datasets/o/r]   # before a pod stops

The primary copy is the creator's private Hugging Face dataset (``config/vault.json`` "primary"). Hugging Face stores an LFS
file's sha256 (``lfs.oid``) and a small file's git blob id, so a hash is checked without downloading. ``check-uploaded`` exits 1
when any local file of a training output is missing on Hugging Face or differs there: a pod script runs it before the pod
stops (``lint_pod_script`` refuses a training script that does not). Nothing here deletes anything, ever.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "vault.json"
HUB = "https://huggingface.co"
CHUNK = 1 << 20


class VaultError(RuntimeError):
    pass


def config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def token():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    p = ROOT / "tools" / "hf_token.txt"
    if not t and p.exists():
        t = p.read_text().strip()
    return t or ""


def _open(url, tok, timeout, retries, sleep):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"} if tok else {})
    for i in range(retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == retries:
                raise VaultError(f"{url}: HTTP {e.code}") from None
        except OSError as e:
            if i == retries:
                raise VaultError(f"{url}: {e}") from None
        sleep(2 ** (i + 1))


def _get(url, tok, timeout=120, retries=4, sleep=time.sleep):
    """(body, the next page's URL from the Link header or None)."""
    with _open(url, tok, timeout, retries, sleep) as r:
        link = r.headers.get("Link") or ""
        body = r.read()
    nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
    return body, (nxt.group(1) if nxt else None)


def _download(url, tok, target, timeout=1800, retries=4, sleep=time.sleep):
    with _open(url, tok, timeout, retries, sleep) as r, open(target, "wb") as f:
        for chunk in iter(lambda: r.read(CHUNK), b""):
            f.write(chunk)


def _split(repo):
    kind, _, rid = repo.partition("/")
    if kind not in ("datasets", "models", "spaces") or rid.count("/") != 1:
        raise VaultError(f"repo must look like datasets/<owner>/<name>, got {repo!r}")
    return kind, rid


def remote_files(repo, prefix="", *, tok=None, get=_get, rev="main"):
    """{path: {"size", "sha256" or None, "blob"}} for every file under ``prefix`` of the repo (paginated tree API)."""
    kind, rid = _split(repo)
    tok = token() if tok is None else tok
    path = urllib.parse.quote(prefix.strip("/"))
    url = f"{HUB}/api/{kind}/{rid}/tree/{rev}/{path}?recursive=true&expand=false&limit=1000"
    out, seen = {}, set()
    while url and url not in seen:
        seen.add(url)
        body, url = get(url, tok)
        for r in json.loads(body):
            if r.get("type") == "file":
                out[r["path"]] = {"size": r.get("size"), "sha256": (r.get("lfs") or {}).get("oid"), "blob": r.get("oid")}
    return out


def file_hashes(path):
    """(sha256, git blob id, size) of a local file, streamed."""
    size = os.path.getsize(path)
    s, b = hashlib.sha256(), hashlib.sha1(b"blob %d\0" % size)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            s.update(chunk)
            b.update(chunk)
    return s.hexdigest(), b.hexdigest(), size


def same(local, remote):
    sha, blob, size = local
    if remote is None or remote.get("size") != size:
        return False
    return remote.get("sha256") == sha if remote.get("sha256") else remote.get("blob") == blob


def is_critical(path, cfg):
    return any(fnmatch.fnmatchcase(path, g) for g in cfg.get("critical", []))


def snapshot(cfg, files, now=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now or time.time()))
    rows = [{"path": p, "size": m["size"], "sha256": m["sha256"], "blob": m["blob"], "critical": is_critical(p, cfg)}
            for p, m in sorted(files.items())]
    crit = [r for r in rows if r["critical"]]
    return {"schema": "vault_manifest/1", "primary": cfg["primary"], "taken": now,
            "totals": {"files": len(rows), "bytes": sum(r["size"] or 0 for r in rows),
                       "critical_files": len(crit), "critical_bytes": sum(r["size"] or 0 for r in crit)},
            "files": rows}


def verify(manifest, files):
    """Problems: a manifest file gone from the primary copy or changed there. New files are fine (snapshot again)."""
    bad = []
    for r in manifest["files"]:
        m = files.get(r["path"])
        if m is None:
            bad.append(f"MISSING {r['path']}")
        elif m["size"] != r["size"] or (m["sha256"] or m["blob"]) != (r["sha256"] or r["blob"]):
            bad.append(f"CHANGED {r['path']}")
    return bad


def check_uploaded(local_dir, prefix, files):
    """Problems: a local file under ``local_dir`` that is not on the primary copy at ``prefix/<relative path>`` with the same
    hash. An empty directory is itself a problem (a training that wrote nothing has nothing to prove)."""
    local_dir, bad, n = Path(local_dir), [], 0
    for p in sorted(local_dir.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or ".cache" in p.parts:
            continue
        n += 1
        rel = p.relative_to(local_dir).as_posix()
        key = f"{prefix.strip('/')}/{rel}" if prefix.strip("/") else rel
        if not same(file_hashes(p), files.get(key)):
            bad.append(f"NOT ON HF {key}" if key not in files else f"DIFFERS ON HF {key}")
    if n == 0:
        bad.append(f"EMPTY {local_dir}")
    return bad


def pull(manifest, dest, *, everything=False, only=None, download=_download, tok=None, log=print):
    """Second copy: download the manifest's critical files (or all) into ``dest``; a file already there with the right hash
    is skipped, a wrong one is downloaded again beside it and swapped in only after its hash checks out."""
    kind, rid = _split(manifest["primary"])
    tok = token() if tok is None else tok
    dest, done, bad, have = Path(dest), 0, [], {}
    for r in manifest["files"]:
        if not (everything or r["critical"]) or (only and not fnmatch.fnmatchcase(r["path"], only)):
            continue
        target = dest / r["path"]
        if target.exists() and same(file_hashes(target), r):
            have[r["sha256"] or r["blob"]] = target
            done += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        twin = have.get(r["sha256"] or r["blob"])
        if twin is not None:  # the same bytes under another name (an approved copy of a checkpoint): copy, do not download
            shutil.copyfile(twin, part)
            os.replace(part, target)
            done += 1
            continue
        url = f"{HUB}/{kind}/{rid}/resolve/main/{urllib.parse.quote(r['path'])}" if kind != "models" else \
              f"{HUB}/{rid}/resolve/main/{urllib.parse.quote(r['path'])}"
        download(url, tok, part)
        if not same(file_hashes(part), r):
            bad.append(f"HASH {r['path']}")
            continue
        os.replace(part, target)
        have[r["sha256"] or r["blob"]] = target
        done += 1
        log(f"ok {r['path']}")
    return done, bad


TRAIN_MARKERS = ("ai-toolkit", "run.py", "accelerate launch", "train_network", "musubi", ".safetensors", "trainer")
CHECK_MARKER = "explainer_engine.vault check-uploaded"


def lint_pod_script(text):
    """A pod script that trains (or writes weights) must prove its outputs are on Hugging Face before the pod ends: it calls
    ``python -m explainer_engine.vault check-uploaded`` after its last upload, and that call is not muted with ``|| true``."""
    if not any(m in text for m in TRAIN_MARKERS):
        return []
    lines = [ln for ln in text.splitlines() if CHECK_MARKER in ln and not ln.lstrip().startswith("#")]
    if not lines:
        return ["VT-01 a training pod script must end with `python -m explainer_engine.vault check-uploaded <out> --to <prefix>`"]
    if all("|| true" in ln or "||true" in ln for ln in lines):
        return ["VT-02 the vault check is muted with `|| true`: a failed upload must keep the pod's data until someone looks"]
    return []


def _opt(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv=None, get=_get, download=_download):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    cfg = config()
    cmd, repo = argv[0], _opt(argv, "--repo", cfg["primary"])
    if cmd == "snapshot":
        out = Path(_opt(argv, "--out", ROOT / cfg["manifest"]))
        m = snapshot(cfg, remote_files(repo, get=get))
        out.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        t = m["totals"]
        print(f"{t['files']} files, {t['bytes'] / 1e9:.2f} GB; critical {t['critical_files']} files, "
              f"{t['critical_bytes'] / 1e9:.2f} GB -> {out}")
        return 0
    manifest_path = Path(_opt(argv, "--manifest", ROOT / cfg["manifest"]))
    if cmd == "verify":
        bad = verify(json.loads(manifest_path.read_text(encoding="utf-8")), remote_files(repo, get=get))
        for b in bad:
            print(b)
        print("PASS: every manifest file is on the primary copy" if not bad else f"FAIL: {len(bad)} problems")
        return 1 if bad else 0
    if cmd == "pull":
        dest = _opt(argv, "--dest")
        if not dest:
            raise SystemExit("pull needs --dest <folder>")
        done, bad = pull(json.loads(manifest_path.read_text(encoding="utf-8")), dest, everything="--all" in argv,
                         only=_opt(argv, "--only"), download=download)
        for b in bad:
            print(b)
        print(f"{done} files in {dest}" + (f"; FAIL {len(bad)}" if bad else "; PASS"))
        return 1 if bad else 0
    if cmd == "check-uploaded":
        prefix = _opt(argv, "--to")
        if len(argv) < 2 or not prefix:
            raise SystemExit("check-uploaded <local dir> --to <prefix on the repo>")
        bad = check_uploaded(argv[1], prefix, remote_files(repo, prefix, get=get))
        for b in bad:
            print(b)
        print("PASS: every output is on Hugging Face with the same hash" if not bad else
              f"FAIL: {len(bad)} outputs not safe; do not stop or delete this pod")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
