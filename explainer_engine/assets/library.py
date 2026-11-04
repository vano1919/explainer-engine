"""The reusable asset library (D-70 stage C; WB-06..WB-10 in docs/WORLD_BIBLE.md): ``assets/library.json`` is the one
register of every channel asset that outlives an episode: reference pictures and look anchors, hero sheets and sprites,
plates and props, collages, LoRAs, prompt templates, sounds and fonts. A record says where the file is and its hash,
under which World Bible version it was made, with which model (and version), prompt, parameters, seed, references and
LoRA, who paid for it, under what licence, whether the creator looked at it, and what it was derived from. The three
levels are bible (``world/bible.py``) -> library (this) -> episode pack (a script's ``picture_dirs``).

Searching is by tags and kind; a new record is compared with the existing ones (same bytes, same prompt + model + seed,
shared tags) and the matches come back as WARNINGS: a duplicate is pointed out, never vetoed (the brief, 2026-10-22).
Embedding search (SigLIP-2 / DINOv2) is not built: it needs a model download and lands with the stage D pilot.

The per-medium libraries stay what they are: sounds in ``audio/sfx_library.py`` (``assets/audio/library``) and, once PR #15
lands, pictures in ``imagegen/picture_library.py``; a record here may point at one of their entries through
``origin.source`` ("sound_library:<id>", "picture_library:<id>") instead of copying the file.

    python -m explainer_engine.assets.library add <file> --id sprite.newton --kind sprite --tags hero,newton
        [--description "..."] [--bible 1.0] [--provider gemini --model M --model-version V --prompt "..." --seed N
         --refs reference.a,anchor.b --lora lora.x --cost-usd 0.07] [--licence-status ...] [--episode slug] [--parent id]
    python -m explainer_engine.assets.library find --tags hero,newton [--kind sprite] [--all]
    python -m explainer_engine.assets.library approve <id> --by "ვანო" [--reject] [--note "..."]
    python -m explainer_engine.assets.library verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

import jsonschema

from explainer_engine.core.store import write_json_atomic

REPO = Path(__file__).resolve().parents[2]
PATH = REPO / "assets" / "library.json"
FILES = REPO / "assets" / "library"  # where ``record_painted`` copies a reusable paid picture
SCHEMA_PATH = REPO / "explainer_engine" / "schemas" / "asset_library.schema.json"
KINDS = ("reference", "anchor", "sheet", "sprite", "picture", "plate", "prop", "collage", "lora", "prompt", "sound", "music", "font")
ID = re.compile(r"^([a-z]+)\.[a-z0-9_]+(\.[a-z0-9_]+)?$")
RASTER = (".png", ".jpg", ".jpeg", ".webp")
APPROVALS = ("not_looked", "approved", "rejected", "superseded")
LICENCES = ("own_drawn", "own_procedural", "generated_terms_unverified", "generated_terms_verified", "licensed", "ofl", "cc0")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path | None = None) -> dict:
    p = Path(path or PATH)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"schema": "asset_library/1", "items": []}


def save(lib: dict, path: Path | None = None) -> Path:
    lib["items"].sort(key=lambda i: i["id"])
    return write_json_atomic(Path(path or PATH), lib)


def validate(lib: dict) -> None:
    jsonschema.validate(lib, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def _size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.width, im.height


def make_record(asset_id: str, kind: str, file: Path | str, *, tags: list[str], description: str = "", bible_version: str,
                made_with: dict | None = None, licence: dict | None = None, parent: str | None = None, episode: str = "",
                approval: dict | None = None, source: str = "", repo: Path | None = None, created: str | None = None) -> dict:
    """One record from a file on disk: the id is checked against its kind, the file hashed (and measured for a raster)."""
    repo = Path(repo or REPO)
    m = ID.match(asset_id)
    if not m:
        raise ValueError(f"{asset_id!r}: an asset id is <kind>.<name>[.<variant>] in lower case (P-66)")
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; known: {KINDS}")
    if m.group(1) != kind:
        raise ValueError(f"{asset_id!r} does not start with its kind {kind!r}")
    path = Path(file)
    if not path.is_absolute():
        path = repo / path
    if not path.exists():
        raise FileNotFoundError(f"{asset_id}: {path} does not exist")
    data = path.read_bytes()
    rec = {"id": asset_id, "kind": kind, "file": path.resolve().relative_to(repo.resolve()).as_posix(), "sha256": sha256(data),
           "bytes": len(data), "tags": sorted({_slug(t) for t in tags if t.strip()}), "description": description,
           "bible_version": bible_version,
           "made_with": {"provider": "", "model": "", "model_version": "", "prompt": "", "params": {}, "seed": None,
                         "refs": [], "lora": None, "cost_usd": 0.0, **(made_with or {})},
           "licence": licence or {"status": "generated_terms_unverified",
                                  "note": "registered without a licence check; verify the provider's output terms before use"},
           "approval": {"status": "not_looked", "by": None, "at": None, "note": "", **(approval or {})},
           "lineage": {"parent": parent},
           "origin": {"episode": episode, "created": created or time.strftime("%Y-%m-%dT%H:%M:%S"), "source": source}}
    if path.suffix.lower() in RASTER:
        rec["width"], rec["height"] = _size(path)
    return rec


def similar(rec: dict, lib: dict, *, min_shared_tags: int = 2) -> list[str]:
    """Warnings about records that look like this one (WB-08): same bytes, same prompt + model + seed, many shared tags.
    A warning never blocks a register; the person decides."""
    out = []
    mw = rec.get("made_with", {})
    for other in lib["items"]:
        if other["id"] == rec["id"]:
            continue
        if other["sha256"] == rec["sha256"]:
            out.append(f"{other['id']} has identical bytes")
            continue
        omw = other.get("made_with", {})
        if mw.get("prompt") and (mw.get("prompt"), mw.get("model"), mw.get("seed")) == (omw.get("prompt"), omw.get("model"), omw.get("seed")):
            out.append(f"{other['id']} was made from the same prompt, model and seed")
            continue
        shared = set(rec["tags"]) & set(other["tags"])
        need = min(min_shared_tags, len(rec["tags"]), len(other["tags"]))
        if need and len(shared) >= need and other["kind"] == rec["kind"]:
            out.append(f"{other['id']} shares the tags {', '.join(sorted(shared))}")
    return out


def register(rec: dict, *, path: Path | None = None, lib: dict | None = None, replace: bool = False) -> tuple[dict, list[str]]:
    """Add one record; returns it with the duplicate warnings. The same id is refused unless ``replace``."""
    lib = lib if lib is not None else load(path)
    warnings = similar(rec, lib)
    if any(i["id"] == rec["id"] for i in lib["items"]):
        if not replace:
            raise ValueError(f"{rec['id']} is already in the library (pass replace=True to overwrite its record)")
        lib["items"] = [i for i in lib["items"] if i["id"] != rec["id"]]
    lib["items"].append(rec)
    validate(lib)
    save(lib, path)
    return rec, warnings


def find(*, tags: list[str] | None = None, kind: str | None = None, bible_version: str | None = None, usable: bool = True,
         lib: dict | None = None, path: Path | None = None) -> list[dict]:
    """Records having ALL the tags (and the kind, and the bible version); ``usable`` hides rejected and superseded ones."""
    lib = lib if lib is not None else load(path)
    want = {_slug(t) for t in (tags or []) if t.strip()}
    out = []
    for i in lib["items"]:
        if kind and i["kind"] != kind:
            continue
        if bible_version and i["bible_version"] != bible_version:
            continue
        if want and not want <= set(i["tags"]):
            continue
        if usable and i["approval"]["status"] in ("rejected", "superseded"):
            continue
        out.append(i)
    return out


def get(asset_id: str, *, lib: dict | None = None, path: Path | None = None) -> dict:
    lib = lib if lib is not None else load(path)
    for i in lib["items"]:
        if i["id"] == asset_id:
            return i
    raise KeyError(f"{asset_id} is not in the library")


def children(asset_id: str, *, lib: dict | None = None, path: Path | None = None) -> list[dict]:
    """Records derived from this one (an edit, a recolour, a crop, a sheet cut from it)."""
    lib = lib if lib is not None else load(path)
    return [i for i in lib["items"] if i["lineage"]["parent"] == asset_id]


def derive(parent_id: str, asset_id: str, kind: str, file: Path | str, *, lib: dict | None = None, path: Path | None = None,
           **fields) -> dict:
    """A record whose lineage points at ``parent_id``; tags and bible version are inherited unless given."""
    lib = lib if lib is not None else load(path)
    parent = get(parent_id, lib=lib)
    fields.setdefault("tags", parent["tags"])
    fields.setdefault("bible_version", parent["bible_version"])
    fields.setdefault("licence", dict(parent["licence"]))
    return make_record(asset_id, kind, file, parent=parent_id, **fields)


def approve(asset_id: str, by: str, *, status: str = "approved", note: str = "", at: str | None = None,
            lib: dict | None = None, path: Path | None = None) -> dict:
    """The creator's look at an asset (WB-09): approved, rejected or superseded; a machine look never counts."""
    if status not in ("approved", "rejected", "superseded"):
        raise ValueError("status is approved, rejected or superseded")
    if not by.strip():
        raise ValueError("approve needs the name of the person who looked")
    lib = lib if lib is not None else load(path)
    rec = get(asset_id, lib=lib)
    rec["approval"] = {"status": status, "by": by, "at": at or time.strftime("%Y-%m-%dT%H:%M:%S"), "note": note}
    validate(lib)
    save(lib, path)
    return rec


def ids_for_files(paths: list[Path], *, lib: dict | None = None, path: Path | None = None) -> dict[str, str]:
    """{file name: asset id} for the files whose bytes are a library asset (how a paint plan names the references it uses)."""
    lib = lib if lib is not None else load(path)
    by_hash = {i["sha256"]: i["id"] for i in lib["items"]}
    out = {}
    for p in paths:
        p = Path(p)
        if p.exists():
            h = sha256(p.read_bytes())
            if h in by_hash:
                out[p.name] = by_hash[h]
    return out


def verify(*, path: Path | None = None, repo: Path | None = None, lib: dict | None = None, versions: list[str] | None = None,
           check_files: bool = True) -> list[str]:
    """Problems with the register: schema, duplicate ids, kind/id mismatch, unknown parent, a bible version that never
    existed, an approval without a name, a file missing or changed since it was registered. Reports, never deletes."""
    lib = lib if lib is not None else load(path)
    repo = Path(repo or REPO)
    try:
        validate(lib)
    except jsonschema.ValidationError as exc:
        return [f"library: {exc.message}"]
    if versions is None:
        from explainer_engine.world import bible
        versions = bible.versions()
    ids = [i["id"] for i in lib["items"]]
    problems = [f"{i}: duplicate id" for i in sorted({x for x in ids if ids.count(x) > 1})]
    known = set(ids)
    for i in lib["items"]:
        if ID.match(i["id"]).group(1) != i["kind"]:
            problems.append(f"{i['id']}: id does not start with its kind {i['kind']}")
        if i["lineage"]["parent"] and i["lineage"]["parent"] not in known:
            problems.append(f"{i['id']}: parent {i['lineage']['parent']} is not in the library")
        if i["bible_version"] not in versions:
            problems.append(f"{i['id']}: bible version {i['bible_version']} never existed (known: {', '.join(versions)})")
        if i["approval"]["status"] != "not_looked" and not i["approval"]["by"]:
            problems.append(f"{i['id']}: {i['approval']['status']} without the name of who looked")
        if not check_files:
            continue
        f = repo / i["file"]
        if not f.exists():
            problems.append(f"{i['id']}: file {i['file']} is missing")
        elif sha256(f.read_bytes()) != i["sha256"]:
            problems.append(f"{i['id']}: file {i['file']} changed since it was registered")
    return problems


def record_painted(plan: dict, out: Path, painted: list[str], *, bible_version: str | None = None, path: Path | None = None,
                   files_dir: Path | None = None, repo: Path | None = None) -> list[dict]:
    """A reusable paint plan's outputs become library records (WB-10): each painted picture is copied under
    ``assets/library/picture/`` and registered with the plan's provider, model, prompt and references. Plans for one
    episode's own pictures (not ``reusable``) register nothing."""
    if not plan.get("reusable") or not painted:
        return []
    repo = Path(repo or REPO)
    files_dir = Path(files_dir or FILES) / "picture"
    files_dir.mkdir(parents=True, exist_ok=True)
    if bible_version is None:
        bible_version = (plan.get("bible") or {}).get("version")
        if bible_version is None:
            from explainer_engine.world import bible
            bible_version = bible.cite()["version"]
    lib = load(path)
    by_id = {i["id"]: i for i in plan["items"]}
    assets = plan.get("assets", {})
    recs = []
    for key in painted:
        src = Path(out) / f"{key}.png"
        if key not in by_id or not src.exists():
            continue
        item = by_id[key]
        asset_id = f"picture.{_slug(plan['episode'])}_{_slug(key)}"
        dest = files_dir / f"{asset_id}.png"
        shutil.copyfile(src, dest)
        rec = make_record(asset_id, "picture", dest, tags=[_slug(plan["episode"]), plan["provider"]] + ([_slug(plan["model"])] if plan.get("model") else []),
                          description=plan.get("purpose", ""), bible_version=bible_version,
                          made_with={"provider": plan["provider"], "model": plan.get("model") or "", "prompt": item["prompt"],
                                     "params": {"size": plan.get("size"), "batch": bool(plan.get("batch"))},
                                     "refs": [assets[r] for r in item.get("refs", []) if r in assets],
                                     "cost_usd": round(plan["estimate_usd"] / max(1, len(plan["items"])), 4)},
                          episode=plan["episode"], source=f"paint plan {plan['id']}", repo=repo)
        rec["made_with"]["unresolved_refs"] = [r for r in item.get("refs", []) if r not in assets]
        lib["items"] = [i for i in lib["items"] if i["id"] != asset_id] + [rec]
        recs.append(rec)
    validate(lib)
    save(lib, path)
    return recs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--path", default=str(PATH))
    p.add_argument("--repo", default=str(REPO), help="the root that file paths are recorded relative to")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("--id", required=True)
    a.add_argument("--kind", required=True, choices=KINDS)
    a.add_argument("--tags", required=True, help="comma-separated")
    a.add_argument("--description", default="")
    a.add_argument("--bible", default=None, help="World Bible version (default: the current one)")
    a.add_argument("--provider", default="")
    a.add_argument("--model", default="")
    a.add_argument("--model-version", default="")
    a.add_argument("--prompt", default="")
    a.add_argument("--seed", type=int, default=None)
    a.add_argument("--refs", default="", help="comma-separated asset ids used as references")
    a.add_argument("--lora", default=None)
    a.add_argument("--cost-usd", type=float, default=0.0)
    a.add_argument("--licence-status", default="generated_terms_unverified", choices=LICENCES)
    a.add_argument("--licence-note", default="registered by library add; verify the provider's output terms before use")
    a.add_argument("--episode", default="", help="which episode paid for it")
    a.add_argument("--parent", default=None)
    a.add_argument("--replace", action="store_true")
    f = sub.add_parser("find")
    f.add_argument("--tags", default="")
    f.add_argument("--kind", default=None, choices=KINDS)
    f.add_argument("--all", action="store_true", help="include rejected and superseded assets")
    ap = sub.add_parser("approve")
    ap.add_argument("id")
    ap.add_argument("--by", required=True)
    ap.add_argument("--reject", action="store_true")
    ap.add_argument("--supersede", action="store_true")
    ap.add_argument("--note", default="")
    sub.add_parser("verify")
    args = p.parse_args(argv)
    path = Path(args.path)
    if args.cmd == "add":
        if args.bible is None:
            from explainer_engine.world import bible
            args.bible = bible.cite()["version"]
        rec = make_record(args.id, args.kind, args.file, tags=args.tags.split(","), description=args.description,
                          bible_version=args.bible, parent=args.parent, episode=args.episode, repo=Path(args.repo),
                          made_with={"provider": args.provider, "model": args.model, "model_version": args.model_version,
                                     "prompt": args.prompt, "seed": args.seed, "lora": args.lora, "cost_usd": args.cost_usd,
                                     "refs": [r for r in args.refs.split(",") if r]},
                          licence={"status": args.licence_status, "note": args.licence_note})
        rec, warnings = register(rec, path=path, replace=args.replace)
        print(f"registered {rec['id']} ({rec['file']}, {rec['sha256'][:12]}, bible v{rec['bible_version']})")
        for w in warnings:
            print("WARNING possible duplicate:", w)
        return 0
    if args.cmd == "find":
        hits = find(tags=args.tags.split(","), kind=args.kind, usable=not args.all, path=path)
        for i in hits:
            print(f"{i['id']:40} {i['kind']:10} {i['approval']['status']:11} v{i['bible_version']:5} {','.join(i['tags'])}")
        print(f"{len(hits)} asset(s)")
        return 0
    if args.cmd == "approve":
        status = "rejected" if args.reject else "superseded" if args.supersede else "approved"
        rec = approve(args.id, args.by, status=status, note=args.note, path=path)
        print(f"{rec['id']}: {status} by {rec['approval']['by']}")
        return 0
    problems = verify(path=path, repo=Path(args.repo))
    for x in problems:
        print("FAIL", x)
    print(f"{len(load(path)['items'])} assets, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
