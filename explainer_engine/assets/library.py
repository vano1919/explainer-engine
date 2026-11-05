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
    python -m explainer_engine.assets.library approve <id> --by "ვანო" [--reject] [--note "..."] [--commercial-use yes|no]
    python -m explainer_engine.assets.library verify

asset_library/2 (D-110; Ink Chronicle roadmap 9.3 and 21.4-21.5; ICW-05): one manager for the 3D kinds too. A record adds
``deps`` (every file a .blend or model links, by asset id + sha256), ``storage`` (git, or external for binaries over
5 MB: the file sits in the gitignored content cache ``tools/assets_cache/<sha256>/`` and its copy in the vault under
``assets/3d/``), a ``three_d`` block for meshes, rigs, animations, costumes and sets (format, skeleton, rig profile,
playable animation sets, polygons, bounds, up axis, materials) and the licence record of 21.4 (where and when the licence
was read, commercial use, redistribution, derivatives, attribution, limits). ``commercial_use: unknown`` blocks approval
(CN-19); the person who approves may record the answer with the approval. A /1 file is read as /2 (``upgrade``) and
written back as /2 by the next change. Third-party files come in through ``import``, which takes the licence facts of a
source from ``licence_sources.json`` (roadmap 21.3) and the asset's own URL and version.

    python -m explainer_engine.assets.library import <file> --id model.ubc_body_a --kind model --tags hero,body
        --source quaternius_ubc --url <asset page> --version <pack version> [--up-axis Y] [--skeleton skeleton.ubc_humanoid_v1]
        [--rig-profile ubc_humanoid] [--poly-count N] [--deps texture.x,rig.y] [--parent id]
    python -m explainer_engine.assets.library find --kind animation --skeleton skeleton.ubc_humanoid_v1
    python -m explainer_engine.assets.library fetch <id>     # an external asset's bytes from the vault into the cache
    python -m explainer_engine.assets.library upgrade        # write the library as asset_library/2
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
SOURCES_PATH = Path(__file__).with_name("licence_sources.json")
SCHEMA_V1, SCHEMA = "asset_library/1", "asset_library/2"
KINDS_V1 = ("reference", "anchor", "sheet", "sprite", "picture", "plate", "prop", "collage", "lora", "prompt", "sound", "music",
            "font")
KINDS_3D = ("model", "rig", "animation", "material", "texture", "hdri", "blend_collection", "scene_template", "costume")
KINDS = KINDS_V1 + KINDS_3D
THREE_D_REQUIRED = ("model", "rig", "animation", "costume", "scene_template", "blend_collection")  # the schema's if/then
ID = re.compile(r"^([a-z_]+)\.[a-z0-9_]+(\.[a-z0-9_]+)?$")
RASTER = (".png", ".jpg", ".jpeg", ".webp")
APPROVALS = ("not_looked", "approved", "rejected", "superseded")
LICENCES = ("own_drawn", "own_procedural", "generated_terms_unverified", "generated_terms_verified", "licensed", "ofl", "cc0",
            "cc-by-4.0", "mit-tool", "gpl-tool-only", "vendor-terms", "community-licence-revenue-capped", "restricted-territory")
COMMERCIAL = ("yes", "no", "unknown")
# commercial use that follows from the licence's own definition; every other status starts "unknown" until someone reads
# the terms (an import takes the answer from its source row, an approval may record it)
COMMERCIAL_BY_DEFINITION = {"own_drawn": "yes", "own_procedural": "yes", "generated_terms_verified": "yes", "ofl": "yes",
                            "cc0": "yes", "cc-by-4.0": "yes"}
LICENCE_FIELDS = ("source_url", "revision_or_version", "inspected_on", "redistribution", "derivatives", "attribution",
                  "geo_or_revenue_limits", "weights_vs_code_note", "outputs_note")
GIT_MAX_BYTES = 5_000_000  # D-110: binaries over 5 MB live outside git (the number moves to a BP row with ICW-07)
CACHE = Path("tools") / "assets_cache"  # relative to the repository; gitignored (tools/), one folder per sha256 (21.5 #11)
FORMATS = {".glb": "glb", ".gltf": "gltf", ".fbx": "fbx", ".blend": "blend", ".obj": "obj", ".exr": "exr", ".hdr": "hdr",
           ".png": "png", ".jpg": "jpg", ".jpeg": "jpg"}
UP_BY_FORMAT = {"glb": "Y", "gltf": "Y", "blend": "Z"}  # glTF 2.0 is +Y up by its specification; Blender is +Z up


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    """The hash of a file read in 1 MB blocks (meshes and HDRIs can be hundreds of MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _upgrade_item(item: dict) -> dict:
    it = json.loads(json.dumps(item))
    it.setdefault("deps", [])
    it.setdefault("storage", {"location": "git", "external_path": None})
    it["licence"].setdefault("commercial_use", COMMERCIAL_BY_DEFINITION.get(it["licence"]["status"], "unknown"))
    return it


def upgrade(lib: dict) -> dict:
    """An asset_library/1 document as /2: no dependencies, stored in git, commercial use as the licence status defines it
    (a Gemini picture whose terms were never verified stays ``unknown``). A /2 document comes back unchanged."""
    if lib.get("schema") != SCHEMA_V1:
        return lib
    return {"schema": SCHEMA, "items": [_upgrade_item(i) for i in lib.get("items", [])]}


def load(path: Path | None = None) -> dict:
    """The library as asset_library/2 (a /1 file is upgraded in memory; the next save writes /2)."""
    p = Path(path or PATH)
    return upgrade(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else {"schema": SCHEMA, "items": []}


def save(lib: dict, path: Path | None = None) -> Path:
    lib["items"].sort(key=lambda i: i["id"])
    return write_json_atomic(Path(path or PATH), lib)


def contract_findings(lib: dict) -> list[dict]:
    """CN-19 (``core/contracts.py``) on the document: deps, storage, third-party licence records, unknown commercial use on
    an approved record, costume lineage, animation skeletons."""
    from explainer_engine.core import contracts as C
    return [f for f in C.errors(lib) if f["rule"] != "CN-01"]


def validate(lib: dict) -> None:
    """The schema (raises ``jsonschema.ValidationError``), then CN-19 (raises ``ValueError`` on a FAIL)."""
    jsonschema.validate(lib, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    bad = [f for f in contract_findings(lib) if f["severity"] == "FAIL"]
    if bad:
        raise ValueError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))


def sources(path: Path | None = None) -> dict:
    """The licence rows of third-party sources (roadmap 21.3), by key."""
    return json.loads(Path(path or SOURCES_PATH).read_text(encoding="utf-8"))["sources"]


def licence_from_source(key: str, *, url: str | None = None, version: str | None = None, note: str = "",
                        path: Path | None = None) -> dict:
    """A record's licence block from a source row plus the asset's own page and pack version (CN-19 wants both for a
    third-party licence). The row's evidence becomes the note; nothing is inferred beyond the row."""
    rows = sources(path)
    if key not in rows:
        raise KeyError(f"no licence row for source {key!r}; known: {', '.join(sorted(rows))} (add one from a read licence page)")
    row = rows[key]
    doc = json.loads(Path(path or SOURCES_PATH).read_text(encoding="utf-8"))
    lic = {"status": row["status"], "commercial_use": row["commercial_use"],
           "note": "; ".join(x for x in (f"{row['label']}: {row['evidence']}", "check this pack's own page" if row.get("per_pack_check")
                                         else "", note) if x)}
    for k in LICENCE_FIELDS:
        lic[k] = row.get(k)
    lic["source_url"] = url or row["source_url"]
    lic["revision_or_version"] = version
    lic["inspected_on"] = doc.get("inspected_on")
    return lic


def vault_path(kind: str, asset_id: str, name: str) -> str:
    """Where an external binary's copy lives on the vault (``config/vault.json`` critical prefix ``assets/3d/**`` for the
    3D kinds; the media backup ``library/`` for the others)."""
    return f"assets/3d/{kind}/{asset_id}/{name}" if kind in KINDS_3D else f"library/{kind}/{asset_id}/{name}"


def _deps(deps: list, lib: dict | None) -> list[dict]:
    out = []
    for d in deps or []:
        if isinstance(d, dict):
            out.append({"asset_id": d["asset_id"], "sha256": d["sha256"]})
            continue
        lib = lib if lib is not None else load()
        out.append({"asset_id": d, "sha256": get(d, lib=lib)["sha256"]})
    return sorted(out, key=lambda d: d["asset_id"])


def _three_d(kind: str, path: Path, three_d: dict | None) -> dict | None:
    if three_d is None:
        if kind in THREE_D_REQUIRED:
            raise ValueError(f"a {kind} record needs its three_d block (format, skeleton, rig profile, up axis, ...; D-110)")
        return None
    fmt = three_d.get("format") or FORMATS.get(path.suffix.lower())
    if fmt is None:
        raise ValueError(f"{path.name}: unknown 3D file format; name it in three_d.format")
    up = three_d.get("up_axis") or UP_BY_FORMAT.get(fmt)
    if up is None:
        raise ValueError(f"{path.name}: a {fmt} file does not fix its up axis; give three_d.up_axis (Y or Z) as read from the file")
    return {"format": fmt, "skeleton_id": None, "rig_profile": None, "compatible_animation_sets": [], "poly_count": None,
            "bounds_m": None, "units": "m", "materials": [], **three_d, "up_axis": up}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def _size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.width, im.height


def make_record(asset_id: str, kind: str, file: Path | str, *, tags: list[str], description: str = "", bible_version: str,
                made_with: dict | None = None, licence: dict | None = None, parent: str | None = None, episode: str = "",
                approval: dict | None = None, source: str = "", repo: Path | None = None, created: str | None = None,
                deps: list | None = None, three_d: dict | None = None, external_path: str | None = None,
                lib: dict | None = None) -> dict:
    """One asset_library/2 record from a file on disk: the id is checked against its kind, the file hashed (and measured
    for a raster). ``deps`` are asset ids (their sha256 read from ``lib``) or {asset_id, sha256} pairs; a file over
    ``GIT_MAX_BYTES`` is stored externally under ``external_path`` (default ``vault_path``); the 3D kinds need ``three_d``."""
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
    size = path.stat().st_size
    lic = dict(licence or {"status": "generated_terms_unverified",
                           "note": "registered without a licence check; verify the provider's output terms before use"})
    lic.setdefault("commercial_use", COMMERCIAL_BY_DEFINITION.get(lic["status"], "unknown"))
    external = size > GIT_MAX_BYTES or external_path is not None
    rec = {"id": asset_id, "kind": kind, "file": path.resolve().relative_to(repo.resolve()).as_posix(), "sha256": sha256_file(path),
           "bytes": size, "tags": sorted({_slug(t) for t in tags if t.strip()}), "description": description,
           "bible_version": bible_version,
           "made_with": {"provider": "", "model": "", "model_version": "", "prompt": "", "params": {}, "seed": None,
                         "refs": [], "lora": None, "cost_usd": 0.0, **(made_with or {})},
           "licence": lic,
           "approval": {"status": "not_looked", "by": None, "at": None, "note": "", **(approval or {})},
           "lineage": {"parent": parent},
           "origin": {"episode": episode, "created": created or time.strftime("%Y-%m-%dT%H:%M:%S"), "source": source},
           "deps": _deps(deps, lib),
           "storage": {"location": "external" if external else "git",
                       "external_path": (external_path or vault_path(kind, asset_id, path.name)) if external else None}}
    td = _three_d(kind, path, three_d)
    if td is not None:
        rec["three_d"] = td
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
         skeleton_id: str | None = None, rig_profile: str | None = None, lib: dict | None = None,
         path: Path | None = None) -> list[dict]:
    """Records having ALL the tags (and the kind, the bible version, the skeleton and rig profile of their ``three_d``);
    ``usable`` hides rejected and superseded ones. ``find(kind="animation", skeleton_id=...)`` is the clips that play on
    that skeleton without a retarget (21.5 #4)."""
    lib = lib if lib is not None else load(path)
    want = {_slug(t) for t in (tags or []) if t.strip()}
    out = []
    for i in lib["items"]:
        if kind and i["kind"] != kind:
            continue
        if bible_version and i["bible_version"] != bible_version:
            continue
        td = i.get("three_d") or {}
        if skeleton_id and td.get("skeleton_id") != skeleton_id:
            continue
        if rig_profile and td.get("rig_profile") != rig_profile:
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
    if kind in THREE_D_REQUIRED and parent.get("three_d"):
        fields.setdefault("three_d", {k: v for k, v in parent["three_d"].items() if k not in ("format", "up_axis")})
    fields.setdefault("lib", lib)
    return make_record(asset_id, kind, file, parent=parent_id, **fields)


def approve(asset_id: str, by: str, *, status: str = "approved", note: str = "", at: str | None = None,
            commercial_use: str | None = None, lib: dict | None = None, path: Path | None = None) -> dict:
    """The creator's look at an asset (WB-09): approved, rejected or superseded; a machine look never counts. An approval
    of a record whose commercial use is ``unknown`` is refused (CN-19, roadmap 21.4) unless the person names the answer in
    ``commercial_use``, which is then written into the licence block with who said it."""
    if status not in ("approved", "rejected", "superseded"):
        raise ValueError("status is approved, rejected or superseded")
    if not by.strip():
        raise ValueError("approve needs the name of the person who looked")
    if commercial_use is not None and commercial_use not in COMMERCIAL:
        raise ValueError(f"commercial_use is one of {COMMERCIAL}")
    lib = lib if lib is not None else load(path)
    rec = get(asset_id, lib=lib)
    when = at or time.strftime("%Y-%m-%dT%H:%M:%S")
    if commercial_use is not None:
        rec["licence"]["commercial_use"] = commercial_use
        rec["licence"]["note"] = f"{rec['licence']['note']}; commercial use {commercial_use} per {by} ({when})"
    if status == "approved" and rec["licence"].get("commercial_use") == "unknown":
        raise ValueError(f"{asset_id}: commercial use is unknown, so it cannot be approved (CN-19, roadmap 21.4); "
                         "pass commercial_use (--commercial-use yes|no) with the approval once the terms are read")
    rec["approval"] = {"status": status, "by": by, "at": when, "note": note}
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
        jsonschema.validate(lib, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        return [f"library: {exc.message}"]
    if versions is None:
        from explainer_engine.world import bible
        versions = bible.versions()
    ids = [i["id"] for i in lib["items"]]
    problems = [f"{i}: duplicate id" for i in sorted({x for x in ids if ids.count(x) > 1})]
    problems += [f"{f['where']}: {f['rule']} {f['detail']}" for f in contract_findings(lib)
                 if f["severity"] == "FAIL" and f["detail"] != "the id is used twice"]
    known = set(ids)
    for i in lib["items"]:
        st = i.get("storage") or {"location": "git"}
        if st["location"] == "git" and i["bytes"] > GIT_MAX_BYTES:
            problems.append(f"{i['id']}: {i['bytes']} bytes in git; a binary over {GIT_MAX_BYTES} bytes is stored externally (D-110)")
        if st["location"] == "external" and not i["file"].startswith(CACHE.as_posix() + "/"):
            problems.append(f"{i['id']}: an external binary lives in the gitignored cache {CACHE.as_posix()}/<sha256>/, not {i['file']}")
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
            if st["location"] != "external":  # an external binary not cached here is in the vault (``fetch`` brings it)
                problems.append(f"{i['id']}: file {i['file']} is missing")
        elif sha256_file(f) != i["sha256"]:
            problems.append(f"{i['id']}: file {i['file']} changed since it was registered")
    return problems


def cached(rec: dict, *, repo: Path | None = None) -> Path | None:
    """The local file of a record when it is present with the registered bytes, else None."""
    f = Path(repo or REPO) / rec["file"]
    return f if f.exists() and sha256_file(f) == rec["sha256"] else None


def fetch(asset_id: str, *, lib: dict | None = None, path: Path | None = None, repo: Path | None = None, download=None,
          tok=None, primary: str | None = None) -> Path:
    """An external asset's bytes from the vault (``storage.external_path`` on the primary of ``config/vault.json``) into
    the cache, kept only when the sha256 matches. Called explicitly; nothing downloads on its own."""
    from explainer_engine import vault as V
    lib = lib if lib is not None else load(path)
    rec = get(asset_id, lib=lib)
    repo = Path(repo or REPO)
    have = cached(rec, repo=repo)
    if have is not None:
        return have
    if rec["storage"]["location"] != "external":
        raise FileNotFoundError(f"{asset_id}: stored in git but {rec['file']} is missing or changed")
    kind, rid = V._split(primary or V.config()["primary"])
    url = f"{V.HUB}/{kind}/{rid}/resolve/main/{rec['storage']['external_path']}"
    target = repo / rec["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    (download or V._download)(url, V.token() if tok is None else tok, part)
    if sha256_file(part) != rec["sha256"]:
        part.unlink()
        raise ValueError(f"{asset_id}: the vault copy at {rec['storage']['external_path']} has another sha256; nothing kept")
    part.replace(target)
    return target


def ingest(src: Path | str, asset_id: str, kind: str, *, path: Path | None = None, repo: Path | None = None,
           replace: bool = False, **fields) -> tuple[dict, list[str]]:
    """Bring a file into the library (``import``): a binary over ``GIT_MAX_BYTES`` is copied into the content cache
    ``tools/assets_cache/<sha256>/`` and recorded as external (its vault copy under ``vault_path``; run ``vault
    check-uploaded`` after the batch, VT-01); a smaller one is copied to ``assets/3d/<kind>/`` (or ``assets/library/<kind>/``)
    and stays in git. The source file is never moved or changed."""
    repo = Path(repo or REPO)
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(src)
    digest = sha256_file(src)
    if src.stat().st_size > GIT_MAX_BYTES:
        dest = repo / CACHE / digest / src.name
    else:
        dest = repo / ("assets/3d" if kind in KINDS_3D else "assets/library") / kind / src.name
    if dest.exists() and sha256_file(dest) != digest:
        raise FileExistsError(f"{dest} exists with other bytes; rename the source file")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copyfile(src, dest)
    lib = load(path)
    rec = make_record(asset_id, kind, dest, repo=repo, lib=lib, **fields)
    return register(rec, path=path, lib=lib, replace=replace)


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
    a.add_argument("--commercial-use", default=None, choices=COMMERCIAL, help="default: what the licence status defines")
    a.add_argument("--parent", default=None)
    a.add_argument("--replace", action="store_true")
    im = sub.add_parser("import", help="a third-party or 3D file with its source's licence row (licence_sources.json)")
    im.add_argument("file")
    im.add_argument("--id", required=True)
    im.add_argument("--kind", required=True, choices=KINDS)
    im.add_argument("--tags", required=True, help="comma-separated")
    im.add_argument("--description", default="")
    im.add_argument("--bible", default=None, help="World Bible version (default: the current one)")
    im.add_argument("--source", required=True, help="a key of licence_sources.json, e.g. polyhaven, quaternius_ubc")
    im.add_argument("--url", default=None, help="the asset's own page (default: the source's page)")
    im.add_argument("--version", required=True, help="the pack's version or revision as its page shows it")
    im.add_argument("--format", default=None, help="glb, gltf, fbx, blend, obj, exr, hdr, png, jpg (default: the suffix)")
    im.add_argument("--up-axis", default=None, choices=("Y", "Z"), help="needed for fbx/obj (glTF is Y, .blend Z)")
    im.add_argument("--skeleton", default=None, help="skeleton.<name> the rig or animation is authored for")
    im.add_argument("--rig-profile", default=None, choices=("ubc_humanoid", "rigify", "mixamo", "mpfb2"))
    im.add_argument("--animation-sets", default="", help="comma-separated sets a model or rig plays")
    im.add_argument("--poly-count", type=int, default=None)
    im.add_argument("--materials", default="", help="comma-separated material names")
    im.add_argument("--retargeted-from", default=None)
    im.add_argument("--deps", default="", help="comma-separated asset ids this file links")
    im.add_argument("--parent", default=None)
    im.add_argument("--replace", action="store_true")
    f = sub.add_parser("find")
    f.add_argument("--tags", default="")
    f.add_argument("--kind", default=None, choices=KINDS)
    f.add_argument("--skeleton", default=None)
    f.add_argument("--rig-profile", default=None)
    f.add_argument("--all", action="store_true", help="include rejected and superseded assets")
    ap = sub.add_parser("approve")
    ap.add_argument("id")
    ap.add_argument("--by", required=True)
    ap.add_argument("--reject", action="store_true")
    ap.add_argument("--supersede", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--commercial-use", default=None, choices=COMMERCIAL, help="the approver's answer when it is unknown")
    fe = sub.add_parser("fetch")
    fe.add_argument("id")
    sub.add_parser("upgrade")
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
                          licence={"status": args.licence_status, "note": args.licence_note,
                                   **({"commercial_use": args.commercial_use} if args.commercial_use else {})})
        rec, warnings = register(rec, path=path, replace=args.replace)
        print(f"registered {rec['id']} ({rec['file']}, {rec['sha256'][:12]}, bible v{rec['bible_version']})")
        for w in warnings:
            print("WARNING possible duplicate:", w)
        return 0
    if args.cmd == "import":
        if args.bible is None:
            from explainer_engine.world import bible
            args.bible = bible.cite()["version"]
        lists = lambda v: [x for x in v.split(",") if x]
        three_d = None
        if args.kind in KINDS_3D and (args.kind in THREE_D_REQUIRED or args.format or args.up_axis):
            three_d = {k: v for k, v in {"format": args.format, "up_axis": args.up_axis, "skeleton_id": args.skeleton,
                                         "rig_profile": args.rig_profile, "compatible_animation_sets": lists(args.animation_sets),
                                         "poly_count": args.poly_count, "materials": lists(args.materials),
                                         "retargeted_from": args.retargeted_from}.items() if v not in (None, [])}
        rec, warnings = ingest(args.file, args.id, args.kind, path=path, repo=Path(args.repo), replace=args.replace,
                               tags=lists(args.tags), description=args.description, bible_version=args.bible,
                               parent=args.parent, deps=lists(args.deps), three_d=three_d,
                               made_with={"provider": "third_party"}, source=f"import {args.source}",
                               licence=licence_from_source(args.source, url=args.url, version=args.version))
        where = rec["storage"]["external_path"] or "git"
        print(f"imported {rec['id']} ({rec['file']}, {rec['sha256'][:12]}, {rec['bytes']} bytes, storage {where})")
        if rec["storage"]["location"] == "external":
            print(f"upload it to the vault at {where}, then: python -m explainer_engine.vault check-uploaded (VT-01)")
        for w in warnings:
            print("WARNING possible duplicate:", w)
        return 0
    if args.cmd == "fetch":
        print(fetch(args.id, path=path, repo=Path(args.repo)))
        return 0
    if args.cmd == "upgrade":
        lib = load(path)
        validate(lib)
        save(lib, path)
        print(f"{path}: {lib['schema']}, {len(lib['items'])} assets")
        return 0
    if args.cmd == "find":
        hits = find(tags=args.tags.split(","), kind=args.kind, skeleton_id=args.skeleton, rig_profile=args.rig_profile,
                    usable=not args.all, path=path)
        for i in hits:
            print(f"{i['id']:40} {i['kind']:10} {i['approval']['status']:11} v{i['bible_version']:5} {','.join(i['tags'])}")
        print(f"{len(hits)} asset(s)")
        return 0
    if args.cmd == "approve":
        status = "rejected" if args.reject else "superseded" if args.supersede else "approved"
        rec = approve(args.id, args.by, status=status, note=args.note, commercial_use=args.commercial_use, path=path)
        print(f"{rec['id']}: {status} by {rec['approval']['by']}")
        return 0
    problems = verify(path=path, repo=Path(args.repo))
    for x in problems:
        print("FAIL", x)
    print(f"{len(load(path)['items'])} assets, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
