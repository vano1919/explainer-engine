"""blender/assets.py (roadmap 11, 21.5 #6 and #8, ICW-05): a shot_spec/2's assets resolve to verified local files with their
deps, a stale hash or a put-away asset is refused, an animation must match its rig's skeleton, the import settings are
recorded per format, and importing the same file twice gives the same snapshot (a recorded fake of bpy)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from explainer_engine.assets import library as L
from explainer_engine.blender import assets as BA

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "tests" / "fixtures" / "contracts" / "shot_spec" / "valid_v2.json"
SKEL = "skeleton.ubc_humanoid_v1"
CC0 = {"status": "cc0", "note": "test", "commercial_use": "yes", "source_url": "https://example.org", "revision_or_version": "1",
       "inspected_on": "2026-11-05"}


@pytest.fixture
def world(tmp_path):
    """A library holding every asset of the fixture spec (+ one dependency), and the spec re-pointed at their hashes."""
    files = {"scene_template.tent_1812": ("tent.blend", {}), "model.camp_table": ("table.glb", {}),
             "model.napoleon": ("napoleon.glb", {"skeleton_id": SKEL}),
             "rig.ubc_humanoid": ("ubc.blend", {"skeleton_id": SKEL, "rig_profile": "ubc_humanoid"}),
             "animation.talk_gesture": ("talk.fbx", {"skeleton_id": SKEL, "up_axis": "Y"}), "prop.candle": ("candle.obj", None),
             "texture.paper_grain": ("paper.png", None), "texture.wood": ("wood.jpg", None)}
    (tmp_path / "a").mkdir()
    lib = {"schema": L.SCHEMA, "items": []}
    for aid, (name, td) in sorted(files.items(), key=lambda kv: kv[0] != "texture.wood"):  # the dependency first
        if name.endswith((".png", ".jpg")):
            Image.new("RGB", (8, 8), (len(aid), 40, 40)).save(tmp_path / "a" / name)
        else:
            (tmp_path / "a" / name).write_bytes(aid.encode() * 4)
        kw = {"three_d": td} if td is not None else {}
        if aid == "model.camp_table":
            kw["deps"] = ["texture.wood"]
        lib["items"].append(L.make_record(aid, aid.split(".")[0], f"a/{name}", repo=tmp_path, tags=["t"], bible_version="1.5",
                                          licence=dict(CC0), lib=lib, **kw))
    L.validate(lib)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    by = {r["id"]: r["sha256"] for r in lib["items"]}

    def point(ref):
        ref["sha256"] = by[ref["id"]]

    sc = spec["scene"]
    point(sc["template_asset"])
    for r in sc["set_assets"] + sc["props"]:
        point(r)
    for c in sc["characters"]:
        for k in ("asset", "rig", "animation"):
            point(c[k])
    point(spec["look"]["paper"]["asset"])
    return SimpleNamespace(repo=tmp_path, lib=lib, spec=spec)


def test_collect_resolves_every_asset_and_its_deps_with_the_import_settings(world):
    got = BA.AssetResolver(world.lib, repo=world.repo).collect(world.spec)
    assert list(got["files"]) == sorted(got["files"]) and "texture.wood" in got["files"]
    assert got["files"]["texture.wood"]["roles"] == ["dep:model.camp_table"]
    assert got["files"]["model.napoleon"]["path"] == world.repo / "a" / "napoleon.glb"
    assert {a["id"] for a in got["assets"]} == {r["id"] for r in world.lib["items"]}
    assert sorted(got["import_settings"]) == ["blend", "fbx", "gltf", "obj"]  # images load in materials, not as objects
    assert got["import_settings"]["gltf"]["operator"] == "import_scene.gltf"
    assert got["import_settings"]["obj"]["options"]["forward_axis"] == "NEGATIVE_Z"


def test_a_changed_hash_a_changed_file_and_a_put_away_asset_are_refused(world):
    r = BA.AssetResolver(world.lib, repo=world.repo)
    spec = json.loads(json.dumps(world.spec))
    spec["scene"]["props"][0]["sha256"] = "f" * 64
    with pytest.raises(BA.AssetError, match="rebuild the spec"):
        r.collect(spec)
    (world.repo / "a" / "candle.obj").write_bytes(b"edited")
    with pytest.raises(BA.AssetError, match="changed since it was registered"):
        r.collect(world.spec)
    (world.repo / "a" / "candle.obj").write_bytes(b"prop.candle" * 4)
    L.get("texture.wood", lib=world.lib)["approval"] = {"status": "rejected", "by": "ვანო", "at": "2026-11-05", "note": ""}
    with pytest.raises(BA.AssetError, match="rejected by ვანო"):
        BA.AssetResolver(world.lib, repo=world.repo).collect(world.spec)


def test_an_animation_for_another_skeleton_needs_a_retarget_first(world):
    L.get("animation.talk_gesture", lib=world.lib)["three_d"]["skeleton_id"] = "skeleton.mixamo_v1"
    with pytest.raises(BA.AssetError, match="retarget it first"):
        BA.AssetResolver(world.lib, repo=world.repo).collect(world.spec)


def test_an_external_asset_not_cached_is_named_or_fetched(world, monkeypatch):
    import explainer_engine.vault as V
    rec = L.get("model.napoleon", lib=world.lib)
    rec["storage"] = {"location": "external", "external_path": "assets/3d/model/model.napoleon/napoleon.glb"}
    body = (world.repo / rec["file"]).read_bytes()
    (world.repo / rec["file"]).unlink()
    with pytest.raises(BA.AssetError, match="library fetch model.napoleon"):
        BA.AssetResolver(world.lib, repo=world.repo).collect(world.spec)
    monkeypatch.setattr(V, "config", lambda *a, **k: {"primary": "datasets/vano1919/tmr-artifacts"})
    monkeypatch.setattr(V, "token", lambda: "")
    got = BA.AssetResolver(world.lib, repo=world.repo, fetch=True, download=lambda u, t, p: p.write_bytes(body)).collect(world.spec)
    assert got["files"]["model.napoleon"]["path"].read_bytes() == body


# ---- a recorded fake of the bpy surface the import functions touch ---------------------------------------------------

class _Matrix:
    def __matmul__(self, v):
        return tuple(v)


class _Obj:
    def __init__(self, name, typ, bones=(), material=None):
        self.name, self.type = name, typ
        self.data = SimpleNamespace(bones=[SimpleNamespace(name=b) for b in bones])
        self.matrix_world = _Matrix()
        self.bound_box = [(0, 0, 0), (1, 2, 3)]
        self.material_slots = [SimpleNamespace(material=SimpleNamespace(name=material))] if material else []


class FakeBpy:
    """Each importer call adds the objects the 'file' holds; ``wobble`` makes the second import differ."""

    def __init__(self, wobble=False):
        self.calls, self.n, self.wobble = [], 0, wobble
        self.data = SimpleNamespace(objects={})
        self.ops = SimpleNamespace(import_scene=SimpleNamespace(gltf=self._imp("gltf"), fbx=self._imp("fbx")),
                                   wm=SimpleNamespace(obj_import=self._imp("obj"), read_factory_settings=self._reset))

    def _reset(self, use_empty):
        self.calls.append(("reset", use_empty))
        self.data.objects = {}

    def _imp(self, fmt):
        def run(filepath, **opts):
            self.calls.append((fmt, filepath, tuple(sorted(opts))))
            self.n += 1
            extra = "_2" if self.wobble and self.n == 2 else ""
            for o in (_Obj("Armature", "ARMATURE", ("hips", "spine")), _Obj("Body" + extra, "MESH", material="skin")):
                self.data.objects[o.name] = o
        return run


def test_import_uses_the_fixed_settings_and_twice_gives_the_same_snapshot():
    bpy = FakeBpy()
    snap = BA.check_deterministic(bpy, "/x/hero.glb", "glb")
    assert snap == {"objects": [["Armature", "ARMATURE"], ["Body", "MESH"]], "bones": {"Armature": ["hips", "spine"]},
                    "bounds": {"Body": {"min": [0, 0, 0], "max": [1, 2, 3]}}, "materials": ["skin"]}
    imports = [c for c in bpy.calls if c[0] == "gltf"]
    assert len(imports) == 2 and imports[0][2] == tuple(sorted(BA.IMPORT_SETTINGS["gltf"]["options"]))
    assert [c for c in bpy.calls if c[0] == "reset"] == [("reset", True), ("reset", True)]
    with pytest.raises(BA.AssetError, match="two imports differ in bounds, objects"):
        BA.check_deterministic(FakeBpy(wobble=True), "/x/hero.fbx", "fbx")
    with pytest.raises(BA.AssetError, match="no import settings"):
        BA.import_asset(FakeBpy(), "/x/a.usd", "usd")


def test_this_module_runs_without_blender():
    text = Path(BA.__file__).read_text(encoding="utf-8")
    assert "import bpy" not in text and "bpy" not in BA.__dict__
