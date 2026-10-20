"""The reusable picture library (D-61): channel assets — props, backgrounds, textures, character art, thumbnail parts —
stored once in ``assets/pictures/library/``, described in ``manifest.json`` and found by tags, so an episode looks here
before any paid paint (OR-17). Episode-bound pictures (a scene of one story) do not belong here; they live in the
episode's picture folders.

Layout: ``<root>/manifest.json`` and ``<root>/<kind>/<id>.<ext>`` (png, jpg or webp; the files are committed like the
character assets, and backed up to HF ``datasets/vano1919/tmr-artifacts/library/pictures/``). Entries carry where the
picture came from (provider, model, prompt, which episode paid for it), the cost, the licence status and whether a
person has looked at it (a machine look never counts as the creator's approval, as in the sound library).

CLI:
    python -m explainer_engine.imagegen.picture_library add <file> --name camp_fire --kind prop --tags fire,night,camp
        [--prompt "..."] [--model M] [--provider gemini] [--episode slug] [--cost-usd 0.04]
        [--licence-status generated_terms_unverified] [--licence-note "..."] [--take 1]
    python -m explainer_engine.imagegen.picture_library find --tags fire,night [--kind prop]
    python -m explainer_engine.imagegen.picture_library fetch <id> --to <episode pictures dir> [--as w_0142.png]
    python -m explainer_engine.imagegen.picture_library validate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import jsonschema

from explainer_engine.core.store import write_json_atomic

ROOT = Path(__file__).resolve().parents[2] / "assets" / "pictures" / "library"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "picture_manifest.schema.json"
KINDS = ("prop", "background", "texture", "character", "thumbnail_part")
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def load_manifest(root: Path = ROOT) -> dict:
    path = Path(root) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "items": []}


def _size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.width, im.height


def add(root: Path, *, file: Path, name: str, take: int, kind: str, tags: list[str], source: dict, licence: dict,
        machine_review: str = "none") -> dict:
    """Copy one picture into the library and register it. Replaces an entry with the same id."""
    root, file = Path(root), Path(file)
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; known: {KINDS}")
    ext = file.suffix.lower()
    if ext not in EXTS:
        raise ValueError(f"{ext}: library pictures are {', '.join(EXTS)}")
    item_id = f"{name}__v{take}"
    rel = f"{kind}/{item_id}{ext}"
    (root / kind).mkdir(parents=True, exist_ok=True)
    data = file.read_bytes()
    (root / rel).write_bytes(data)
    w, h = _size(root / rel)
    entry = {"id": item_id, "file": rel, "kind": kind, "tags": sorted(set(tags)), "width": w, "height": h,
             "sha256": hashlib.sha256(data).hexdigest(), "source": source, "licence": licence,
             "review": {"machine": machine_review, "human": "not_looked"}}
    manifest = load_manifest(root)
    manifest["items"] = [i for i in manifest["items"] if i["id"] != item_id] + [entry]
    manifest["items"].sort(key=lambda i: i["id"])
    write_json_atomic(root / "manifest.json", manifest)
    return entry


def find(root: Path = ROOT, *, tags: list[str] | None = None, kind: str | None = None, usable: bool = True) -> list[dict]:
    """Entries having ALL the tags. ``usable`` hides pictures the creator rejected."""
    out = []
    for item in load_manifest(root)["items"]:
        if kind and item["kind"] != kind:
            continue
        if tags and not set(tags) <= set(item["tags"]):
            continue
        if usable and item["review"]["human"] == "rejected":
            continue
        out.append(item)
    return out


def find_for_prompt(prompt: str, root: Path = ROOT, *, min_overlap: int = 2) -> list[dict]:
    """Library pictures whose tags appear as words of a paint prompt (``paint plan`` lists them, PP-08): at least
    ``min_overlap`` of an entry's tags, or all of them when it has fewer. Best overlap first."""
    words = set(prompt.lower().replace(",", " ").replace(".", " ").split())
    scored = []
    for item in find(root):
        hit = sum(1 for t in item["tags"] if t in words)
        if hit >= min(min_overlap, len(item["tags"])) and hit > 0:
            scored.append((hit, item))
    return [item for hit, item in sorted(scored, key=lambda x: -x[0])]


def fetch(root: Path, item_id: str, dest_dir: Path, as_name: str | None = None) -> Path:
    """Copy one library picture into an episode's picture folder (reuse instead of a paid paint)."""
    items = {i["id"]: i for i in load_manifest(root)["items"]}
    if item_id not in items:
        raise KeyError(f"{item_id} is not in the library")
    src = Path(root) / items[item_id]["file"]
    dest = Path(dest_dir) / (as_name or src.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return dest


def validate(root: Path = ROOT, *, check_files: bool = True) -> list[str]:
    """Manifest problems; with ``check_files`` also every file (present, unchanged, the manifest's size)."""
    root = Path(root)
    problems: list[str] = []
    manifest = load_manifest(root)
    try:
        jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        return [f"manifest: {exc.message}"]
    seen = set()
    for item in manifest["items"]:
        if item["id"] in seen:
            problems.append(f"{item['id']}: duplicate id")
        seen.add(item["id"])
        if not item["file"].startswith(item["kind"] + "/"):
            problems.append(f"{item['id']}: file is not under its kind folder")
        if not check_files:
            continue
        path = root / item["file"]
        if not path.exists():
            problems.append(f"{item['id']}: file missing")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            problems.append(f"{item['id']}: file changed since it was registered")
            continue
        w, h = _size(path)
        if (w, h) != (item["width"], item["height"]):
            problems.append(f"{item['id']}: size differs from the manifest")
    if check_files and root.exists():
        want = {i["file"] for i in manifest["items"]}
        for path in root.rglob("*"):
            if path.suffix.lower() in EXTS and path.relative_to(root).as_posix() not in want:
                problems.append(f"{path.relative_to(root).as_posix()}: not in the manifest")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=str(ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("--name", required=True)
    a.add_argument("--take", type=int, default=1)
    a.add_argument("--kind", required=True, choices=KINDS)
    a.add_argument("--tags", required=True, help="comma-separated")
    a.add_argument("--provider", default="gemini")
    a.add_argument("--model", default="")
    a.add_argument("--prompt", default="")
    a.add_argument("--episode", default="", help="which episode paid for it")
    a.add_argument("--cost-usd", type=float, default=0.0)
    a.add_argument("--licence-status", default="generated_terms_unverified",
                   choices=["own_drawn", "generated_terms_unverified", "generated_terms_verified", "licensed", "cc0"])
    a.add_argument("--licence-note", default="registered by picture_library add; verify the provider's output terms")
    a.add_argument("--machine-review", default="none")
    f = sub.add_parser("find")
    f.add_argument("--tags", default="")
    f.add_argument("--kind", default=None, choices=KINDS)
    g = sub.add_parser("fetch")
    g.add_argument("id")
    g.add_argument("--to", required=True)
    g.add_argument("--as", dest="as_name", default=None)
    sub.add_parser("validate")
    args = p.parse_args(argv)
    root = Path(args.root)
    if args.cmd == "add":
        source = {"kind": args.provider, "model": args.model, "prompt": args.prompt,
                  "episode": args.episode, "cost_usd_estimate": args.cost_usd}
        entry = add(root, file=Path(args.file), name=args.name, take=args.take, kind=args.kind,
                    tags=[t for t in args.tags.split(",") if t], source=source,
                    licence={"status": args.licence_status, "note": args.licence_note},
                    machine_review=args.machine_review)
        print(f"registered {entry['id']} ({entry['file']}, {entry['width']}x{entry['height']})")
        return 0
    if args.cmd == "find":
        hits = find(root, tags=[t for t in args.tags.split(",") if t], kind=args.kind)
        for i in hits:
            print(f"{i['id']:40} {i['kind']:14} {','.join(i['tags'])}")
        print(f"{len(hits)} picture(s)")
        return 0
    if args.cmd == "fetch":
        print(fetch(root, args.id, Path(args.to), args.as_name))
        return 0
    problems = validate(root)
    for x in problems:
        print("FAIL", x)
    print(f"{len(load_manifest(root)['items'])} pictures, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
