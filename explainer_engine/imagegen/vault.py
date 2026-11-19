"""The ASSET vault: records + untouched local originals of every generated picture, clip and take; the HF copy layer stays
``explainer_engine/vault.py`` (D-73), which this module calls for every Hugging Face fact and never replaces with a client of its own.

One original per asset, never changed: ingest copies the bytes as they are, hashes them, makes the copy read-only and writes
one JSON line (``schemas/asset_record.schema.json``, plan 5.3). A new picture of the same shot is the next version with
``parent`` = the previous asset_id; the same bytes ingested again return the existing record. Originals live at
``assets/originals/<ep>/<shot>_<kind>_v<N>.<ext>`` (gitignored, primary copy on the D-73 dataset); only the JSONL records
``episodes/<ep>/assets/asset_records.jsonl`` are committed.

    python -m explainer_engine.imagegen.vault ingest <file> --ep E --shot S --kind image_start [--provider P --model M --prompt T ...]
    python -m explainer_engine.imagegen.vault list --ep E [--shot S] [--kind K]
    python -m explainer_engine.imagegen.vault verify --ep E [--hf]          # local file hash = record; --hf: HF copy = record
    python -m explainer_engine.imagegen.vault migrate --ep E --inventory asset_inventory.csv   # records from HF, no download
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path
from urllib.parse import unquote

from explainer_engine import vault as D73
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_text_atomic

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "asset_record/1"


def records_path(ep: str, root: Path | None = None) -> Path:
    return Path(root or ROOT) / "episodes" / ep / "assets" / "asset_records.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path: Path | str) -> str:
    return D73.file_hashes(path)[0]


def prompt_hash(prompt: str | None) -> str | None:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else None


def load(ep: str, root: Path | None = None) -> list[dict]:
    p = records_path(ep, root)
    if not p.is_file():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _append(ep: str, rec: dict, root: Path | None) -> None:
    contracts.validate(rec)
    p = records_path(ep, root)
    old = p.read_text(encoding="utf-8") if p.is_file() else ""
    if old and not old.endswith("\n"):
        old += "\n"
    write_text_atomic(p, old + json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def get(asset_id: str, ep: str | None = None, root: Path | None = None) -> dict | None:
    ep = ep or asset_id.split(":", 1)[0]
    return next((r for r in load(ep, root) if r["asset_id"] == asset_id), None)


def latest(ep: str, shot: str, kind: str, root: Path | None = None) -> dict | None:
    rows = [r for r in load(ep, root) if r["shot_id"] == shot and r["type"] == kind]
    return max(rows, key=lambda r: r["version"]) if rows else None


def _make_readonly(p: Path) -> None:
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def ingest(path, ep: str, shot: str, kind: str, provider: str | None = None, model: str | None = None,
           prompt: str | None = None, refs: list[str] | None = None, seed=None, params: dict | None = None,
           cost: float | None = None, *, root: Path | None = None, note: str | None = None) -> dict:
    """Copy ``path`` byte-for-byte into ``assets/originals/``, read-only, and record it. Same bytes already recorded for this
    (episode, shot, kind) -> that record, nothing written. Different bytes -> version N+1 whose ``parent`` is version N."""
    root = Path(root or ROOT)
    src = Path(path)
    if not src.is_file():
        raise ContractError(f"ingest: {src} is not a file")
    sha = sha256_file(src)
    rows = [r for r in load(ep, root) if r["shot_id"] == shot and r["type"] == kind]
    for r in rows:
        if r["sha256"] == sha:
            return r
    prev = max(rows, key=lambda r: r["version"]) if rows else None
    version = prev["version"] + 1 if prev else 1
    ext = src.suffix.lower() or ".bin"
    rel = f"assets/originals/{ep}/{shot}_{kind}_v{version}{ext}"
    dest = root / rel
    if dest.exists():   # never overwrite an original, even one with no record
        raise ContractError(f"ingest: {rel} already exists; originals are never overwritten")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    shutil.copyfile(src, tmp)
    if sha256_file(tmp) != sha:
        tmp.unlink()
        raise ContractError(f"ingest: the copy of {src} does not match its hash")
    os.replace(tmp, dest)
    _make_readonly(dest)
    rec = {"schema": SCHEMA, "asset_id": f"{ep}:{shot}:{kind}:v{version}", "episode_id": ep, "shot_id": shot, "type": kind,
           "sha256": sha, "size": dest.stat().st_size, "path": rel, "hf_path": None,
           "version": version, "parent": prev["asset_id"] if prev else None, "provider": provider, "model": model,
           "prompt_hash": prompt_hash(prompt), "references": list(refs or []), "seed": seed, "parameters": dict(params or {}),
           "cost": cost, "created": _now(), "observation_record_id": None, "creator_approval": None, "note": note}
    _append(ep, rec, root)
    return rec


def remote_listing(prefix: str = "", repo: str | None = None, get=None) -> dict:
    """{hf path: {size, sha256, blob}} from the D-73 listing (``lfs.oid`` is the sha256, no download)."""
    cfg = D73.config()
    kw = {} if get is None else {"get": get}
    return D73.remote_files(repo or cfg["primary"], prefix, **kw)


def verify(ep: str, *, root: Path | None = None, files: dict | None = None) -> list[str]:
    """Problems, [] when sound: a local original gone, changed or writable; with ``files`` (a D-73 listing) also every record
    that names an ``hf_path`` is on the primary copy with the recorded hash."""
    root = Path(root or ROOT)
    bad = []
    for r in load(ep, root):
        if r.get("path"):
            p = root / r["path"]
            if not p.is_file():
                if not r.get("hf_path"):
                    bad.append(f"MISSING {r['asset_id']} {r['path']}")
            elif sha256_file(p) != r["sha256"]:
                bad.append(f"CHANGED {r['asset_id']} {r['path']}")
            elif p.stat().st_mode & 0o222 and os.name != "nt":
                bad.append(f"WRITABLE {r['asset_id']} {r['path']}")
        if files is not None and r.get("hf_path"):
            m = files.get(r["hf_path"])
            if m is None:
                bad.append(f"NOT ON HF {r['asset_id']} {r['hf_path']}")
            elif not D73.same((r["sha256"], None, r.get("size")), m):
                bad.append(f"DIFFERS ON HF {r['asset_id']} {r['hf_path']}")
    return bad


# --- migration of what exists only on Hugging Face (no bytes fetched, no bytes changed) ------------------------------
_HF = re.compile(r"/datasets/vano1919/tmr-artifacts/resolve/main/(.+)$")
_PICTURE = re.compile(r"^pic:(S\d+_SH\d+)_(start|end)$")
_RAW = re.compile(r"^ltx_raw:(S\d+_SH\d+)$")


def hf_path_of(url: str) -> str | None:
    m = _HF.search(url or "")
    return unquote(m.group(1)) if m else None


def migrate_inventory(ep: str, inventory: Path, files: dict, *, root: Path | None = None, extra: list[dict] | None = None) -> dict:
    """Records for the inventory's start pictures and raw LTX takes that have an ``hf_location``, hashed by the D-73 listing
    ``files`` (``lfs.oid``). ``extra`` rows ``{shot, kind, hf_path, note}`` add other known HF files. Idempotent. Returns
    {recorded, already, no_hash, missing: [{asset_id, category, subtype, path, why}]}."""
    root = Path(root or ROOT)
    have = {(r["shot_id"], r["type"], r["hf_path"]) for r in load(ep, root) if r.get("hf_path")}
    out = {"recorded": [], "already": [], "no_hash": [], "missing": []}
    todo = []
    for row in csv.DictReader(open(inventory, encoding="utf-8")):
        cat, aid = row["category"], row["asset_id"]
        m = _PICTURE.match(aid) if cat == "start_photo" else (_RAW.match(aid) if cat == "ltx_clip" and row["subtype"] == "raw" else None)
        if m is None:
            if cat in ("start_photo", "ltx_clip", "rendered_clip"):
                out["missing"].append({"asset_id": aid, "category": cat, "subtype": row["subtype"], "path": row["path"],
                                       "why": "no hf_location (Mac only)"})
            continue
        hp = hf_path_of(row["hf_location"])
        if hp is None:
            out["missing"].append({"asset_id": aid, "category": cat, "subtype": row["subtype"], "path": row["path"],
                                   "why": "no hf_location (Mac only)"})
            continue
        kind = f"image_{m.group(2)}" if cat == "start_photo" else "clip_raw"
        todo.append({"shot": m.group(1), "kind": kind, "hf_path": hp, "provider": row["source_kind"] or None,
                     "note": f"inventory {aid}; {row['route']}"})
    todo += list(extra or [])
    for t in todo:
        if (t["shot"], t["kind"], t["hf_path"]) in have:
            out["already"].append(f"{t['shot']}:{t['kind']}")
            continue
        meta = files.get(t["hf_path"])
        if not meta or not meta.get("sha256"):
            out["no_hash"].append(t["hf_path"])
            continue
        rows = [r for r in load(ep, root) if r["shot_id"] == t["shot"] and r["type"] == t["kind"]]
        prev = max(rows, key=lambda r: r["version"]) if rows else None
        v = prev["version"] + 1 if prev else 1
        rec = {"schema": SCHEMA, "asset_id": f"{ep}:{t['shot']}:{t['kind']}:v{v}", "episode_id": ep, "shot_id": t["shot"],
               "type": t["kind"], "sha256": meta["sha256"], "size": meta["size"], "path": None, "hf_path": t["hf_path"],
               "version": v, "parent": prev["asset_id"] if prev else None, "provider": t.get("provider"), "model": None,
               "prompt_hash": None, "references": [], "seed": None, "parameters": {}, "cost": None, "created": _now(),
               "observation_record_id": None, "creator_approval": None, "note": t.get("note")}
        _append(ep, rec, root)
        out["recorded"].append(rec["asset_id"])
    return out


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.imagegen.vault")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest")
    a.add_argument("file")
    a.add_argument("--ep", required=True)
    a.add_argument("--shot", required=True)
    a.add_argument("--kind", required=True)
    for k in ("provider", "model", "prompt", "note"):
        a.add_argument(f"--{k}")
    a.add_argument("--seed")
    a.add_argument("--cost", type=float)
    ls = sub.add_parser("list")
    ls.add_argument("--ep", required=True)
    ls.add_argument("--shot")
    ls.add_argument("--kind")
    v = sub.add_parser("verify")
    v.add_argument("--ep", required=True)
    v.add_argument("--hf", action="store_true")
    mg = sub.add_parser("migrate")
    mg.add_argument("--ep", required=True)
    mg.add_argument("--inventory", required=True)
    mg.add_argument("--hf-prefix", default="explainer-engine/demo_truce_1914")
    mg.add_argument("--missing-out")
    n = ap.parse_args(argv)
    if n.cmd == "ingest":
        r = ingest(n.file, n.ep, n.shot, n.kind, n.provider, n.model, n.prompt, None, n.seed, None, n.cost, note=n.note)
        print(json.dumps(r, indent=1, ensure_ascii=False))
        return 0
    if n.cmd == "list":
        for r in load(n.ep):
            if (not n.shot or r["shot_id"] == n.shot) and (not n.kind or r["type"] == n.kind):
                print(f"{r['asset_id']}\t{r['sha256'][:12]}\t{r.get('path') or 'hf:' + str(r.get('hf_path'))}")
        return 0
    if n.cmd == "verify":
        bad = verify(n.ep, files=remote_listing() if n.hf else None)
        for b in bad:
            print(b)
        print("PASS" if not bad else f"FAIL: {len(bad)} problems")
        return 1 if bad else 0
    files = remote_listing(n.hf_prefix)
    extra = []
    for p in sorted(files):   # the new-style pictures taken in Gemini Chat (2026-11-19), recorded the same way
        m = re.search(r"new_style_B_2026-11-19/(S\d+_SH\d+)\.jpe?g$", p)
        if m:
            extra.append({"shot": m.group(1), "kind": "image_newstyle_B", "hf_path": p, "provider": "gemini_chat_image",
                          "note": "new_style_B_2026-11-19"})
        m = re.search(r"new_style_B_2026-11-19/round0/(thomas_v\d)\.jpe?g$", p)
        if m:
            extra.append({"shot": "round0", "kind": f"image_{m.group(1)}", "hf_path": p, "provider": "gemini_chat_image",
                          "note": "new_style_B_2026-11-19 round0 character test"})
    out = migrate_inventory(n.ep, Path(n.inventory), files, extra=extra)
    if n.missing_out:
        write_text_atomic(Path(n.missing_out), json.dumps(out["missing"], indent=1, ensure_ascii=False))
    print({k: len(v) for k, v in out.items()})
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
