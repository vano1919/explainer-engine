"""Library assets for a Blender shot (roadmap section 11 ``AssetResolver``, 21.5 #6 and #8; D-110; ICW-05).

``AssetResolver.collect(spec)`` turns the asset references of a ``shot_spec/2`` (the scene template, the set assets, each
character's model, rig and animation, the props and the paper grain of the look) into verified local files:

1. every reference is a record of the asset library (``assets/library.py``, asset_library/2) with the SAME sha256 as the
   spec names: a changed asset is a new cache key, never a silent swap;
2. a rejected or superseded record is refused (a machine never revives what the creator put away);
3. a record's ``deps`` (textures, HDRIs and rigs a ``.blend`` or model links) are collected too, each at its recorded hash;
4. a character's animation must be authored for the skeleton of the character's rig (``three_d.skeleton_id``); anything
   else needs a retarget first (``rigs.RigAdapter.plan``), so the resolver refuses it;
5. the bytes on disk are re-hashed; an external asset (over 5 MB, D-110) is read from the content cache
   ``tools/assets_cache/<sha256>/``; one that is not cached is reported, or fetched from the vault when ``fetch`` is on.

The result also carries what the scene manifest (``blender_scene_manifest/1``) records: the ``assets`` list (id, sha256,
kind) and the fixed ``import_settings`` of every file format in the shot.

``import_asset(bpy, path, fmt)`` and ``check_deterministic(bpy, path, fmt)`` run INSIDE Blender (the bpy job script or a
validation script hands them the ``bpy`` module; this file never imports it, so the package still runs without Blender).
They import with the settings below, then read back object names and types, bone names, world bounds and material names;
importing the same file twice into an empty scene must give the same snapshot (21.5 #8, roadmap 21.11).

IMPORT_SETTINGS are Blender 5.2.3's own operator defaults, written out so that a changed default in a later Blender cannot
change an import silently. Read from the v5.2.3 sources on 2026-11-05: ``scripts/addons_core/io_scene_gltf2/__init__.py``
(``ImportGLTF2``, ``import_scene.gltf``), ``scripts/addons_core/io_scene_fbx/__init__.py`` (``ImportFBX``,
``import_scene.fbx``, orientation helper axis_forward '-Z', axis_up 'Y') and ``source/blender/editors/io/io_obj.cc``
(``WM_OT_obj_import``; axis names from ``io_transform_axis`` in ``source/blender/io/common/intern/orientation.cc``). A ``.blend`` is appended (``bpy.data.libraries.load(link=False)``), its collections and objects.
"""
from __future__ import annotations

from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.core.errors import ContractError

IMPORT_SETTINGS = {
    "gltf": {"operator": "import_scene.gltf",
             "options": {"import_pack_images": True, "merge_vertices": False, "import_shading": "NORMALS",
                         "bone_heuristic": "BLENDER", "disable_bone_shape": False, "bone_shape_scale_factor": 1.0,
                         "guess_original_bind_pose": True, "import_webp_texture": False, "import_unused_materials": False,
                         "import_select_created_objects": True, "import_scene_extras": True,
                         "import_scene_as_collection": True, "import_merge_material_slots": True,
                         "import_point_as_pointcloud": False}},
    "fbx": {"operator": "import_scene.fbx",
            "options": {"use_manual_orientation": False, "global_scale": 1.0, "bake_space_transform": False,
                        "use_custom_normals": True, "colors_type": "SRGB", "use_image_search": True, "use_alpha_decals": False,
                        "decal_offset": 0.0, "use_anim": True, "anim_offset": 1.0, "use_subsurf": False,
                        "use_custom_props": True, "use_custom_props_enum_as_string": True, "ignore_leaf_bones": False,
                        "force_connect_children": False, "automatic_bone_orientation": False, "primary_bone_axis": "Y",
                        "secondary_bone_axis": "X", "use_prepost_rot": True, "mtl_name_collision_mode": "MAKE_UNIQUE",
                        "axis_forward": "-Z", "axis_up": "Y"}},
    "obj": {"operator": "wm.obj_import",
            "options": {"global_scale": 1.0, "clamp_size": 0.0, "forward_axis": "NEGATIVE_Z", "up_axis": "Y",
                        "use_split_objects": True, "use_split_groups": False, "import_vertex_groups": False,
                        "validate_meshes": True, "close_spline_loops": True, "mtl_name_collision_mode": "MAKE_UNIQUE"}},
    "blend": {"operator": "bpy.data.libraries.load", "options": {"link": False, "collections": "all", "objects": "all"}},
}
IMPORT_SETTINGS["glb"] = IMPORT_SETTINGS["gltf"]
IMAGE_FORMATS = ("png", "jpg", "exr", "hdr")  # loaded as images by the material or world, not imported as objects
UNUSABLE = ("rejected", "superseded")


class AssetError(ContractError):
    """An asset reference that cannot be used as it is: unknown, at another hash, put away, missing, or unplayable."""


def file_format(rec: dict) -> str:
    """The import format of a record: its ``three_d.format``, else the file suffix."""
    fmt = (rec.get("three_d") or {}).get("format") or L.FORMATS.get(Path(rec["file"]).suffix.lower())
    if fmt is None:
        raise AssetError(f"{rec['id']}: no import format for {rec['file']}")
    return "gltf" if fmt == "glb" else fmt


def spec_refs(spec: dict) -> list[tuple[str, dict]]:
    """(role, {id, sha256}) for every asset a ``shot_spec/2`` names, in a fixed order."""
    sc = spec["scene"]
    out = [("template", sc["template_asset"])]
    out += [("set", a) for a in sc["set_assets"]]
    for c in sc["characters"]:
        out += [(f"character:{c['cast_id']}", c["asset"]), (f"rig:{c['cast_id']}", c["rig"])]
        if c.get("animation"):
            out.append((f"animation:{c['cast_id']}", c["animation"]))
    out += [("prop", a) for a in sc["props"]]
    out.append(("paper", spec["look"]["paper"]["asset"]))
    return out


class AssetResolver:
    """Asset ids of a shot -> verified local paths (roadmap section 11)."""

    def __init__(self, lib: dict | None = None, *, repo: Path | None = None, fetch: bool = False, download=None):
        self.lib = lib if lib is not None else L.load()
        self.repo = Path(repo or L.REPO)
        self.fetch = fetch
        self.download = download
        self.by_id = {r["id"]: r for r in self.lib["items"]}

    def record(self, ref: dict, role: str = "") -> dict:
        rec = self.by_id.get(ref["id"])
        where = f"{role} {ref['id']}".strip()
        if rec is None:
            raise AssetError(f"{where}: not in the asset library")
        if rec["sha256"] != ref["sha256"]:
            raise AssetError(f"{where}: the spec names sha256 {ref['sha256'][:12]}, the library {rec['sha256'][:12]}: rebuild the spec")
        if rec["approval"]["status"] in UNUSABLE:
            raise AssetError(f"{where}: {rec['approval']['status']} by {rec['approval']['by']}; not used in a new shot")
        return rec

    def path(self, rec: dict) -> Path:
        have = L.cached(rec, repo=self.repo)
        if have is not None:
            return have
        if rec.get("storage", {}).get("location") == "external" and self.fetch:
            return L.fetch(rec["id"], lib=self.lib, repo=self.repo, download=self.download)
        f = self.repo / rec["file"]
        state = "changed since it was registered" if f.exists() else "not here"
        hint = " (python -m explainer_engine.assets.library fetch " + rec["id"] + ")" \
            if rec.get("storage", {}).get("location") == "external" else ""
        raise AssetError(f"{rec['id']}: {rec['file']} is {state}{hint}")

    def _check_animations(self, spec: dict) -> None:
        for c in spec["scene"]["characters"]:
            if not c.get("animation"):
                continue
            rig = self.by_id[c["rig"]["id"]]
            anim = self.by_id[c["animation"]["id"]]
            want = (rig.get("three_d") or {}).get("skeleton_id")
            have = (anim.get("three_d") or {}).get("skeleton_id")
            if anim["kind"] != "animation" or rig["kind"] != "rig":
                raise AssetError(f"{c['cast_id']}: the rig is a {rig['kind']} and the animation a {anim['kind']}")
            if not want or want != have:
                raise AssetError(f"{c['cast_id']}: {anim['id']} is authored for {have}, the rig {rig['id']} is {want}: "
                                 "retarget it first (rigs.RigAdapter.plan)")

    def collect(self, spec: dict) -> dict:
        """{"files": {id: {path, sha256, kind, format, roles}}, "assets": [...], "import_settings": {...}} for one spec;
        the deps of every record are collected at their recorded hash."""
        files: dict[str, dict] = {}

        def add(ref: dict, role: str, chain: tuple = ()) -> None:
            if ref["id"] in chain:
                raise AssetError(f"{ref['id']}: a dependency cycle ({' -> '.join(chain + (ref['id'],))})")
            if ref["id"] in files:
                if role not in files[ref["id"]]["roles"]:
                    files[ref["id"]]["roles"].append(role)
                return
            rec = self.record(ref, role)
            files[rec["id"]] = {"path": self.path(rec), "sha256": rec["sha256"], "kind": rec["kind"],
                                "format": file_format(rec), "roles": [role]}
            for d in rec.get("deps", []):
                add({"id": d["asset_id"], "sha256": d["sha256"]}, f"dep:{rec['id']}", chain + (rec["id"],))

        for role, ref in spec_refs(spec):
            add(ref, role)
        self._check_animations(spec)
        ordered = dict(sorted(files.items()))
        fmts = sorted({f["format"] for f in ordered.values() if f["format"] not in IMAGE_FORMATS})
        return {"files": ordered,
                "assets": [{"id": i, "sha256": f["sha256"], "kind": f["kind"]} for i, f in ordered.items()],
                "import_settings": {fmt: IMPORT_SETTINGS[fmt] for fmt in fmts}}


def _call(bpy, dotted: str, **kw):
    head, name = dotted.split(".")
    return getattr(getattr(bpy.ops, head), name)(**kw)


def import_asset(bpy, path: Path | str, fmt: str) -> list:
    """Import one file into the current scene with the fixed settings; returns the new objects (runs inside Blender)."""
    if fmt == "glb":
        fmt = "gltf"
    if fmt not in IMPORT_SETTINGS:
        raise AssetError(f"no import settings for {fmt!r} (known: {', '.join(sorted(IMPORT_SETTINGS))})")
    before = set(bpy.data.objects.keys())
    if fmt == "blend":
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.collections = list(src.collections)
            dst.objects = list(src.objects)
        scene = bpy.context.scene
        for coll in dst.collections:
            if coll is not None and coll.name not in scene.collection.children.keys():
                scene.collection.children.link(coll)
        for obj in dst.objects:
            if obj is not None and not obj.users_collection:
                scene.collection.objects.link(obj)
    else:
        _call(bpy, IMPORT_SETTINGS[fmt]["operator"], filepath=str(path), **IMPORT_SETTINGS[fmt]["options"])
    return [bpy.data.objects[n] for n in sorted(set(bpy.data.objects.keys()) - before)]


def _bounds(obj) -> dict:
    pts = [obj.matrix_world @ _vector(c) for c in obj.bound_box]
    return {"min": [round(min(p[i] for p in pts), 5) for i in range(3)], "max": [round(max(p[i] for p in pts), 5) for i in range(3)]}


def _vector(corner):
    try:
        from mathutils import Vector  # Blender's own math module, present wherever bpy is
    except ImportError:  # the recorded fake of the tests
        return tuple(corner)
    return Vector(corner)


def snapshot(objects) -> dict:
    """What an import produced, in a stable order: objects (name, type), bones per armature, world bounds, materials."""
    objs = sorted(objects, key=lambda o: o.name)
    return {"objects": [[o.name, o.type] for o in objs],
            "bones": {o.name: sorted(b.name for b in o.data.bones) for o in objs if o.type == "ARMATURE"},
            "bounds": {o.name: _bounds(o) for o in objs if o.type == "MESH"},
            "materials": sorted({s.material.name for o in objs for s in getattr(o, "material_slots", []) if s.material})}


def check_deterministic(bpy, path: Path | str, fmt: str) -> dict:
    """Import twice, each time into an empty factory scene, and compare the snapshots; raises when they differ."""
    shots = []
    for _ in range(2):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        shots.append(snapshot(import_asset(bpy, path, fmt)))
    if shots[0] != shots[1]:
        diff = sorted(k for k in shots[0] if shots[0][k] != shots[1][k])
        raise AssetError(f"{Path(path).name}: two imports differ in {', '.join(diff)}")
    return shots[0]
