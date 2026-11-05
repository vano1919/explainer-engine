"""Real characters for the Blender lanes (roadmap 15 ICW-06, 9.2, 21.5-21.6 PoC 1; D-101): approved 3D assets carry identity.

A character is assembled, never modelled: a head-and-body model of Quaternius' Universal Base Characters (CC0), one of its hair
meshes rigged to the Head bone, and a costume of Quaternius' Modular Character Outfits (CC0, built on the same skeleton); motion
comes from the Universal Animation Library (CC0) on the very same 65-bone skeleton, so playing a clip needs no retarget
(``rigs.RigAdapter``); the mouth is eight shape keys built on the head mesh at build time (``mouth.py``), keyed from Rhubarb
cues (``rigs.LipSync``). Everything the viewer sees is re-materialled by ``style.py`` (D-102): skin, hair and costume keep their
own texture only as a trace over a palette tone, eyes keep their texture.

Identity (D-101): a ``character/1`` entry of ``characters.json`` names the head model, the hair, the material map and the mouth
centre; its costume may change per shot (``costume`` assets, invariant 6: the face and hair never change). The raster carrier is
the turnaround sheet (``turnaround.py``) registered as a ``sheet`` asset whose lineage names the character's assets.

The asset files are the third-party originals packed into single self-contained GLB files (``pack_glb``: the glTF's JSON, its
.bin and its images in one file, byte-identical on every machine), registered in ``assets/library.json`` as external records
(tools/assets_cache/<sha256>/, vault copy under assets/3d/); ``character_assets.json`` lists each one with its pack and member,
so ``fetch`` can rebuild it from the free itch.io pack (``assets/itch.py``) when the vault is out of reach (a CI runner).

    python -m explainer_engine.blender.characters prepare --packs D     # pack + register the GLBs from downloaded pack zips
    python -m explainer_engine.blender.characters fetch                  # the registered GLBs into tools/assets_cache
    python -m explainer_engine.blender.characters list
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import sys
import zipfile
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.core.store import write_json_atomic

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "character_assets.json"
REGISTRY = HERE / "characters.json"
SKELETON = "skeleton.ubc_humanoid_v1"
DERIVED = L.CACHE / "derived"  # textures read out of a registered GLB (keyed by the GLB's sha256), never registered themselves
GLB_MAGIC, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942


class CharacterError(ValueError):
    pass


# --- GLB packing -----------------------------------------------------------------------------------------------------------------

def _pad(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((4 - len(data) % 4) % 4)


def pack_glb(gltf: dict, read) -> tuple[bytes, dict]:
    """A glTF document and ``read(relative uri) -> bytes | None`` -> (GLB bytes, report). Every buffer and every image found is
    embedded in one BIN chunk; an image the pack does not ship (Quaternius' glTFs name a few ``*_png.png`` normal maps that are
    not in the zip) is dropped together with its texture and the material slots that used it, and listed in the report. The
    output depends only on the input bytes (the JSON keeps its key order, no time stamps), so two machines pack the same file."""
    doc = json.loads(json.dumps(gltf))
    blob = bytearray()
    views = []
    buf_base = []
    for b in doc.get("buffers", []):
        data = read(b["uri"]) if "uri" in b else None
        if data is None:
            raise CharacterError(f"buffer {b.get('uri')!r} is missing from the pack")
        if len(data) < b["byteLength"]:
            raise CharacterError(f"buffer {b['uri']}: {len(data)} bytes, the glTF says {b['byteLength']}")
        buf_base.append(len(blob))
        blob += _pad(data[: b["byteLength"]], b"\x00")
    for v in doc.get("bufferViews", []):
        v["byteOffset"] = v.get("byteOffset", 0) + buf_base[v.get("buffer", 0)]
        v["buffer"] = 0
        views.append(v)
    dropped = []
    keep_images = {}
    for i, im in enumerate(doc.get("images", [])):
        if "uri" not in im:
            keep_images[i] = im
            continue
        data = read(im["uri"])
        if data is None:
            dropped.append(im["uri"])
            continue
        mime = "image/png" if im["uri"].lower().endswith(".png") else "image/jpeg"
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
        blob += _pad(data, b"\x00")
        keep_images[i] = {**{k: v for k, v in im.items() if k != "uri"}, "bufferView": len(views) - 1, "mimeType": mime}
    image_map = {old: new for new, old in enumerate(sorted(keep_images))}
    doc["bufferViews"] = views
    if "images" in doc:
        doc["images"] = [keep_images[i] for i in sorted(keep_images)]
    tex_map = {}
    textures = []
    for t, tex in enumerate(doc.get("textures", [])):
        if "source" in tex and tex["source"] not in image_map:
            continue
        if "source" in tex:
            tex["source"] = image_map[tex["source"]]
        tex_map[t] = len(textures)
        textures.append(tex)
    if "textures" in doc:
        doc["textures"] = textures

    def fix(o):
        if isinstance(o, dict):
            for k in list(o):
                v = o[k]
                if isinstance(v, dict) and "index" in v and k.endswith("Texture"):
                    if v["index"] in tex_map:
                        v["index"] = tex_map[v["index"]]
                    else:
                        del o[k]
                        continue
                fix(v)
        elif isinstance(o, list):
            for x in o:
                fix(x)
    fix(doc.get("materials", []))
    doc["buffers"] = [{"byteLength": len(blob)}]
    js = _pad(json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), b" ")
    binc = _pad(bytes(blob), b"\x00")
    total = 12 + 8 + len(js) + 8 + len(binc)
    out = (struct.pack("<III", GLB_MAGIC, 2, total) + struct.pack("<II", len(js), CHUNK_JSON) + js
           + struct.pack("<II", len(binc), CHUNK_BIN) + binc)
    return out, {"dropped_images": dropped, "images": len(doc.get("images", [])), "bytes": len(out)}


def read_glb(data: bytes) -> tuple[dict, bytes]:
    """(JSON document, BIN chunk) of a GLB."""
    magic, version, total = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC or version != 2 or total != len(data):
        raise CharacterError("not a glTF 2.0 binary")
    off, doc, binc = 12, None, b""
    while off < total:
        length, kind = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + length]
        if kind == CHUNK_JSON:
            doc = json.loads(chunk.decode("utf-8"))
        elif kind == CHUNK_BIN:
            binc = chunk
        off += 8 + length
    if doc is None:
        raise CharacterError("GLB without a JSON chunk")
    return doc, binc


def glb_summary(data: bytes) -> dict:
    """What a packed file holds (read without Blender): meshes, materials, joints, animation names, triangles."""
    doc, _ = read_glb(data)
    tris = 0
    for m in doc.get("meshes", []):
        for p in m["primitives"]:
            if "indices" in p:
                tris += doc["accessors"][p["indices"]]["count"] // 3
    joints = [doc["nodes"][j]["name"] for j in doc["skins"][0]["joints"]] if doc.get("skins") else []
    return {"meshes": [m["name"] for m in doc.get("meshes", [])], "materials": [m["name"] for m in doc.get("materials", [])],
            "joints": joints, "animations": [a.get("name") for a in doc.get("animations", [])], "triangles": tris}


def embedded_image(glb: Path, material: str, *, repo: Path | None = None, slot: str = "baseColorTexture") -> Path:
    """The image a GLB material uses in ``slot`` (pbrMetallicRoughness.baseColorTexture by default), written once to the
    derived cache under the GLB's sha256: the style graph needs a file path for a toon material's texture trace."""
    data = Path(glb).read_bytes()
    doc, binc = read_glb(data)
    mat = next((m for m in doc.get("materials", []) if m["name"] == material), None)
    if mat is None:
        raise CharacterError(f"{Path(glb).name}: no material {material!r}")
    ref = (mat.get("pbrMetallicRoughness") or {}).get(slot) or mat.get(slot)
    if ref is None:
        raise CharacterError(f"{Path(glb).name}: material {material!r} has no {slot}")
    im = doc["images"][doc["textures"][ref["index"]]["source"]]
    v = doc["bufferViews"][im["bufferView"]]
    png = binc[v.get("byteOffset", 0): v.get("byteOffset", 0) + v["byteLength"]]
    dest = Path(repo or L.REPO) / DERIVED / hashlib.sha256(data).hexdigest() / f"{material}_{slot}.png"
    if not dest.exists() or dest.read_bytes() != png:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(png)
        tmp.replace(dest)
    return dest


# --- the asset table and the packs -----------------------------------------------------------------------------------------------

def assets(path: Path | None = None) -> dict:
    return json.loads(Path(path or ASSETS).read_text(encoding="utf-8"))


def _zip_reader(zf: zipfile.ZipFile, member: str):
    base = member.rsplit("/", 1)[0]
    names = set(zf.namelist())

    def read(uri: str) -> bytes | None:
        import urllib.parse
        p = f"{base}/{urllib.parse.unquote(uri)}"
        return zf.read(p) if p in names else None
    return read


def pack_member(zip_path: Path, member: str) -> tuple[bytes, dict]:
    """One glTF of a pack zip as a self-contained GLB (a member that is already a GLB is taken byte for byte)."""
    with zipfile.ZipFile(zip_path) as zf:
        if member.lower().endswith(".glb"):
            data = zf.read(member)
            read_glb(data)
            return data, {"dropped_images": [], "bytes": len(data), "packed": False}
        gltf = json.loads(zf.read(member).decode("utf-8"))
        return pack_glb(gltf, _zip_reader(zf, member))


def pack_path(pack: dict, packs_dir: Path) -> Path:
    return Path(packs_dir) / pack["file"]


def prepare(packs_dir: Path, *, path: Path | None = None, repo: Path | None = None, table: dict | None = None,
            check_sha: bool = True) -> list[dict]:
    """Every GLB of ``character_assets.json`` packed from its downloaded pack zip and registered as an external asset_library/2
    record (licence from the pack's source row + the pack page and version). The pack zip must be the one the table names."""
    from explainer_engine.world import bible as B
    table = table or assets()
    bv = B.cite()["version"]
    out = []
    for key, pack in table["packs"].items():
        z = pack_path(pack, packs_dir)
        if L.sha256_file(z) != pack["sha256"]:
            raise CharacterError(f"{key}: {z} is not the registered pack (sha256 differs)")
    work = Path(repo or L.REPO) / L.CACHE / "packing"
    work.mkdir(parents=True, exist_ok=True)
    for a in table["assets"]:
        pack = table["packs"][a["pack"]]
        data, rep = pack_member(pack_path(pack, packs_dir), a["member"])
        digest = hashlib.sha256(data).hexdigest()
        if check_sha and a.get("sha256") and digest != a["sha256"]:
            raise CharacterError(f"{a['id']}: packing gave {digest}, the table says {a['sha256']} (packer or pack changed)")
        f = work / a["name"]
        f.write_bytes(data)
        summ = glb_summary(data)
        three_d = {"format": "glb", "skeleton_id": SKELETON if summ["joints"] else None,
                   "rig_profile": "ubc_humanoid" if summ["joints"] else None,
                   "compatible_animation_sets": [table["animation_set"]] if summ["joints"] else [],
                   "poly_count": summ["triangles"], "materials": summ["materials"]}
        rec, _ = L.ingest(f, a["id"], a["kind"], path=path, repo=repo, replace=True, external=True, tags=a["tags"],
                          description=a["description"], bible_version=bv, three_d=three_d, parent=a.get("parent"),
                          made_with={"provider": "third_party", "params": {"packed_from": a["member"], "pack_sha256": pack["sha256"],
                                                                           "dropped_images": rep["dropped_images"]}},
                          source=f"import {pack['source']} {pack['page']} :: {a['member']}",
                          licence=L.licence_from_source(pack["source"], url=pack["page"], version=pack["version"]))
        f.unlink()
        out.append({"id": rec["id"], "sha256": rec["sha256"], "bytes": rec["bytes"], **summ})
    return out


def fetch(*, repo: Path | None = None, packs_dir: Path | None = None, table: dict | None = None, vault_first: bool = True,
          download_pack=None) -> dict[str, Path]:
    """Asset id -> the cached GLB at its registered sha256: from the cache, else the vault, else rebuilt from the pack zip
    (``packs_dir``, or downloaded into the cache with ``assets/itch.py``; free packs only)."""
    repo = Path(repo or L.REPO)
    table = table or assets()
    lib = L.load()
    got, missing = {}, []
    for a in table["assets"]:
        rec = L.get(a["id"], lib=lib)
        if a.get("sha256") and rec["sha256"] != a["sha256"]:
            raise CharacterError(f"{a['id']}: character_assets.json and the library disagree on the sha256")
        have = L.cached(rec, repo=repo)
        if have is None and vault_first:
            try:
                have = L.fetch(a["id"], lib=lib, repo=repo)
            except Exception:  # noqa: BLE001  (no token or no network: the pack is the fallback)
                have = None
        if have is None:
            missing.append((a, rec))
        else:
            got[a["id"]] = Path(have)
    if missing:
        pdir = Path(packs_dir or repo / L.CACHE / "packs")
        for key in sorted({a["pack"] for a, _ in missing}):
            pack = table["packs"][key]
            z = pack_path(pack, pdir)
            if not z.exists() or L.sha256_file(z) != pack["sha256"]:
                (download_pack or _download_pack)(pack, pdir)
            if L.sha256_file(z) != pack["sha256"]:
                raise CharacterError(f"{key}: the downloaded pack has another sha256; nothing kept")
        for a, rec in missing:
            data, _ = pack_member(pack_path(table["packs"][a["pack"]], pdir), a["member"])
            if hashlib.sha256(data).hexdigest() != rec["sha256"]:
                raise CharacterError(f"{a['id']}: packing the pack member gave other bytes than the registered file")
            dest = repo / rec["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            got[a["id"]] = dest
    return got


def _download_pack(pack: dict, pdir: Path) -> None:
    from explainer_engine.assets import itch
    done = itch.download(pack["page"], pdir, match=pack["match"])
    if not any(d["name"] == pack["file"] for d in done):
        raise CharacterError(f"{pack['page']}: no file named {pack['file']} in the pack")


# --- the character registry ------------------------------------------------------------------------------------------------------

def registry(path: Path | None = None) -> dict:
    doc = json.loads(Path(path or REGISTRY).read_text(encoding="utf-8"))
    if doc.get("schema") != "character/1":
        raise CharacterError(f"{path or REGISTRY}: not a character/1 registry")
    return doc


def get(char_id: str, *, reg: dict | None = None) -> dict:
    reg = reg or registry()
    if char_id not in reg["characters"]:
        raise CharacterError(f"unknown character {char_id!r} (known: {', '.join(sorted(reg['characters']))})")
    return reg["characters"][char_id]


def costume(costume_id: str, *, reg: dict | None = None) -> dict:
    reg = reg or registry()
    if costume_id not in reg["costumes"]:
        raise CharacterError(f"unknown costume {costume_id!r} (known: {', '.join(sorted(reg['costumes']))})")
    return reg["costumes"][costume_id]


def asset_ids(char_id: str, costume_id: str, *, reg: dict | None = None) -> list[str]:
    ch, co = get(char_id, reg=reg), costume(costume_id, reg=reg)
    if co["body"] != ch["body"]:
        raise CharacterError(f"costume {costume_id} is cut for the {co['body']} body, {char_id} has {ch['body']}")
    return [ch["head"], ch["hair"], co["asset"]]


def materials(name: str, char_id: str, costume_id: str, paths: dict[str, Path], *, tint: str | None = None,
              reg: dict | None = None) -> tuple[dict[str, str], dict[str, dict]]:
    """(GLB material name -> toon material name, toon material name -> StyleEngine.material kwargs) of one cast member.

    A slot of characters.json says ``from`` (``head`` or ``costume``: whose GLB holds the image), ``texture`` (that GLB's
    material whose base colour image is read) and ``strength`` (how much of the image survives over its mean, 0 = the flat
    mean colour: skin, so the face and the hands of a costume match). A costume slot takes ``tint`` (a palette token, e.g. a
    faction colour) as the colour its image is laid over; without a tint its own mean colour."""
    reg = reg or registry()
    ch, co = get(char_id, reg=reg), costume(costume_id, reg=reg)
    owner = {"head": ch["head"], "costume": co["asset"]}
    matmap, mats = {}, {}
    skin = next((v for v in ch["materials"].values() if v["slot"] == "skin"), None)
    for glb_mat, s in sorted({**ch["materials"], **co["materials"]}.items()):
        if s["slot"] == "skin" and skin is not None:
            s = skin   # a costume's bare hands take the face's skin, never their own texture's tone
        src = embedded_image(paths[owner[s["from"]]], s["texture"])
        mean = _mean(src)
        if s["slot"] == "costume":
            mname = f"{costume_id.split('.', 1)[1]}_{tint or 'own'}"
            spec = {"base": tint or mean + [1.0], "texture": str(src), "strength": s["strength"]}
            if not tint:
                spec["texture_mean"] = mean
        elif s.get("tint"):   # hair: the pack's grey strand map laid over the character's palette tone
            mname = f"{char_id}_{s['slot']}"
            spec = {"base": s["tint"], "texture": str(src), "strength": s["strength"]}
        else:
            mname = f"{char_id}_{s['slot']}"
            spec = {"base": mean + [1.0]}
            if s["strength"] > 0:
                spec.update(texture=str(src), texture_mean=mean, strength=s["strength"])
        if mname in mats and mats[mname] != spec:
            raise CharacterError(f"{char_id}/{costume_id}: two slots make {mname} differently")
        mats[mname] = spec
        matmap[glb_mat] = mname
    return matmap, mats


def scene_object(name: str, char_id: str, costume_id: str, paths: dict[str, Path], *, location=(0.0, 0.0, 0.0),
                 yaw_deg: float = 0.0, action: str | None = None, action_offset: int = 0, action_speed: float = 1.0,
                 tint: str | None = None, lipsync: dict | None = None, mouth_rest: str = "X",
                 reg: dict | None = None) -> tuple[dict, dict[str, dict]]:
    """A ``described`` scene object of ``bpy/render_shot.py`` for one cast member, and the toon materials it needs (name ->
    StyleEngine.material kwargs). ``paths`` maps asset ids to local files (``fetch``). ``action`` is a clip of the animation
    set (``rigs.RigAdapter.plan`` decides it plays on this skeleton); ``lipsync`` is ``rigs.LipSync.plan``'s output."""
    reg = reg or registry()
    ch, co = get(char_id, reg=reg), costume(costume_id, reg=reg)
    ids = asset_ids(char_id, costume_id, reg=reg)
    matmap, mats = materials(name, char_id, costume_id, paths, tint=tint, reg=reg)
    mouth = {**reg["mouth"], **ch["mouth"], "rest": mouth_rest}
    mats.setdefault(mouth["interior_material"], {"base": reg["mouth"]["interior_token"]})
    parts = [{"path": str(paths[ch["head"]]), "keep_bones": ch["keep_bones"], "drop": ch.get("drop", [])},
             {"path": str(paths[ch["hair"]])},
             {"path": str(paths[co["asset"]]), "drop": co.get("drop", [])}]
    anim = None
    if action:
        if not 0 < action_speed <= 4:
            raise CharacterError(f"{name}: clip speed {action_speed} outside 0..4")
        anim = {"path": str(paths[reg["animation_asset"]]), "action": action, "offset": int(action_offset),
                "speed": float(action_speed)}
    obj = {"name": name, "character": {"id": char_id, "costume": costume_id, "assets": ids, "parts": parts, "materials": matmap,
                                       "mouth": mouth, "animation": anim, "lipsync": lipsync},
           "location": list(location), "rotation_deg": [0.0, 0.0, float(yaw_deg)]}
    return obj, mats


def _mean(path: Path) -> list[float]:
    from explainer_engine.blender import style_sheets
    return style_sheets.texture_mean(path)


# --- PoC 1: the clips' foot slide (roadmap 21.6) ---------------------------------------------------------------------------------

POC1_CLIPS = {  # the 8 clips of PoC 1 (walk, run, idle, turn, combat, sit, emote + the formal walk of the battle shots); UAL1 has
    # no turn-in-place clip, so the talking idle stands in for it
    "Walk_Loop": "walk", "Jog_Fwd_Loop": "run", "Idle_Loop": "idle", "Idle_Talking_Loop": "idle (talking)",
    "Sword_Attack": "combat", "Sitting_Idle_Loop": "sit", "Dance_Loop": "emote", "Walk_Formal_Loop": "walk (formal)"}
FOOT_BONES = ("root", "pelvis", "foot_l", "foot_r", "ball_l", "ball_r")


def measure_clips(out: Path, *, binary: str | None = None, actions=tuple(POC1_CLIPS), run=None, cpaths=None) -> dict:
    """PoC 1's foot-slide line: Blender samples every frame of each clip on the UAL armature (``bpy/measure_clips.py``),
    ``rigs.foot_slide`` reads the planted feet. Writes ``out/poc1_clips.json``; free (a local Blender run)."""
    import subprocess
    from explainer_engine.blender import rigs
    from explainer_engine.blender.project import BlenderProject
    run = run or subprocess.run
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cpaths = cpaths or fetch()
    reg = registry()
    glb = cpaths[reg["animation_asset"]]
    samples = out / "clip_samples.json"
    job = out / "measure_job.json"
    write_json_atomic(job, {"glb": str(glb), "actions": list(actions), "bones": list(FOOT_BONES), "out": str(samples)})
    b = BlenderProject().resolve(binary)
    script = Path(__file__).resolve().parent / "bpy" / "measure_clips.py"
    p = run([b.path, "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(script), "--", str(job)],
            capture_output=True, text=True)
    if p.returncode != 0:
        raise CharacterError(f"measure_clips failed: {(p.stderr or p.stdout or '').strip()[-600:]}")
    data = json.loads(samples.read_text(encoding="utf-8"))
    rows = {}
    for name, a in data["actions"].items():
        moving = POC1_CLIPS.get(name, "").startswith(("walk", "run"))   # a stationary clip is judged with the body standing still
        r = rigs.foot_slide(a["samples"], data["fps"], root_speed_mps=None if moving else 0.0)
        rows[name] = {"kind": POC1_CLIPS.get(name, ""), "frames": len(a["samples"]), **{k: r[k] for k in
                      ("natural_speed_mps", "root_speed_mps", "root_travel_m", "in_place", "slide_m", "passed")}}
    doc = {"schema": "poc1_clips/1", "blender": b.version, "animation_asset": reg["animation_asset"],
           "sha256": L.get(reg["animation_asset"])["sha256"], "line_m": rigs.POC1_SLIDE_M,
           "usable": sum(1 for r in rows.values() if r["passed"]), "of": len(rows), "clips": rows}
    write_json_atomic(out / "poc1_clips.json", doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.characters", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--packs", required=True)
    sub.add_parser("fetch").add_argument("--packs")
    sub.add_parser("list")
    mc = sub.add_parser("measure-clips")
    mc.add_argument("--out", required=True)
    mc.add_argument("--binary")
    args = ap.parse_args(argv)
    if args.cmd == "measure-clips":
        doc = measure_clips(Path(args.out), binary=args.binary)
        print(json.dumps(doc, indent=1))
        return 0 if doc["usable"] >= 6 else 1
    if args.cmd == "prepare":
        print(json.dumps(prepare(Path(args.packs)), indent=1))
    elif args.cmd == "fetch":
        print(json.dumps({k: str(v) for k, v in fetch(packs_dir=Path(args.packs) if args.packs else None).items()}, indent=1))
    else:
        reg = registry()
        for cid, c in sorted(reg["characters"].items()):
            print(f"{cid}: {c['label']} (head {c['head']}, hair {c['hair']})")
        for cid, c in sorted(reg["costumes"].items()):
            print(f"costume {cid}: {c['label']} ({c['asset']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
