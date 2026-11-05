"""WP-Q8: world kits (Quaternius MegaKit + Poly Haven pieces, layouts) and the Poly Haven code taken from Blender-MCP.
Offline: downloads go through recorded fake openers; packing uses a synthetic glTF."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import polyhaven as PH
from explainer_engine.blender import world_kits as W

ROOT = Path(__file__).resolve().parents[2]


# --- polyhaven.py -------------------------------------------------------------------------------------------------------------------

class Resp:
    def __init__(self, body: bytes, headers=None):
        self.buf, self.headers = io.BytesIO(body), headers or {}

    def read(self, n=-1):
        return self.buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_slug_guard_and_zip_slip(tmp_path):
    assert PH.valid_slug("modular_fort_01") and PH.valid_slug("GothicCabinet_01")
    assert not PH.valid_slug("../x") and not PH.valid_slug("a/b") and not PH.valid_slug("")
    assert PH.safe_include(tmp_path, "textures/a.jpg") == tmp_path / "textures" / "a.jpg"
    assert PH.safe_include(tmp_path, "../evil") is None and PH.safe_include(tmp_path, "/etc/passwd") is None


def test_download_checks_the_md5_and_removes_a_bad_file(tmp_path):
    body = b"glTF bytes"
    ok = PH.download({"url": "https://x/y.bin", "md5": hashlib.md5(body).hexdigest()}, tmp_path / "y.bin", opener=lambda r, timeout: Resp(body))
    assert ok.read_bytes() == body
    with pytest.raises(PH.PolyHavenError, match="Checksum"):
        PH.download({"url": "https://x/z.bin", "md5": "0" * 32}, tmp_path / "z.bin", opener=lambda r, timeout: Resp(body))
    assert not (tmp_path / "z.bin").exists()


def test_api_get_caches_and_names_this_project(monkeypatch):
    PH._cache.clear()
    seen = []

    def opener(req, timeout):
        seen.append((req.full_url, req.headers.get("User-agent")))
        return Resp(json.dumps({"a": 1}).encode(), {"ETag": "e1"})
    assert PH.api_get("assets", {"t": "models"}, cache=True, opener=opener) == {"a": 1}
    assert PH.api_get("assets", {"t": "models"}, cache=True, opener=opener) == {"a": 1}
    assert len(seen) == 1 and seen[0][0] == "https://api.polyhaven.com/assets?t=models" and "explainer-engine" in seen[0][1]


def test_texture_map_selection_and_available():
    files = {"Diffuse": {"1k": {"jpg": {}}}, "nor_gl": {"1k": {"jpg": {}}}, "nor_dx": {"1k": {"jpg": {}}}, "Rough": {"2k": {"jpg": {}}}}
    assert PH.select_texture_maps(files, "1k", "jpg") == {"Diffuse": "base_color", "nor_gl": "normal"}
    assert PH.select_texture_maps({"col_1": {"1k": {"jpg": {}}}}, "1k", "jpg") == {"col_1": "base_color"}
    assert "1k" in PH.available({"Diffuse": {"1k": {"jpg": {}}}, "x": {"4k": {"png": {}}}}, "textures")


def test_model_fetch_records_every_file_and_skips_unsafe_includes(tmp_path):
    bodies = {"https://cdn/m.gltf": b"{}", "https://cdn/m.bin": b"BIN", "https://cdn/t.jpg": b"JPG", "https://cdn/bad": b"BAD"}
    md5 = lambda u: hashlib.md5(bodies[u]).hexdigest()  # noqa: E731
    files = {"gltf": {"1k": {"gltf": {"url": "https://cdn/m.gltf", "md5": md5("https://cdn/m.gltf"), "include": {
        "m.bin": {"url": "https://cdn/m.bin", "md5": md5("https://cdn/m.bin")},
        "textures/t.jpg": {"url": "https://cdn/t.jpg", "md5": md5("https://cdn/t.jpg")},
        "../bad": {"url": "https://cdn/bad", "md5": md5("https://cdn/bad")}}}}}}
    got = PH.fetch_model_files(files, "1k", "gltf", tmp_path, opener=lambda r, timeout: Resp(bodies[r.full_url]))
    assert [f["name"] for f in got["files"]] == ["m.gltf", "m.bin", "textures/t.jpg"] and not (tmp_path.parent / "bad").exists()
    assert PH.fetch_model_files(files, "8k", "gltf", tmp_path) is None


def test_hdri_world_builds_a_new_world_and_keeps_the_old_one():
    made = []

    class Nodes(list):
        def new(self, type):
            n = SimpleNamespace(type=type, inputs={"Vector": 1, "Color": 2, "Surface": 7}, outputs={"Generated": 3, "Vector": 4, "Color": 5, "Background": 6},
                                image=None)
            self.append(n)
            return n
    tree = SimpleNamespace(nodes=Nodes(), links=SimpleNamespace(new=lambda a, b: made.append((a, b))))
    nodes_clear = tree.nodes.clear
    world = SimpleNamespace(use_nodes=False, node_tree=tree)
    img = SimpleNamespace(name="", pack=lambda: made.append("packed"))
    old = object()
    bpy = SimpleNamespace(data=SimpleNamespace(worlds=SimpleNamespace(new=lambda n: world),
                                               images=SimpleNamespace(load=lambda p, check_existing: img)),
                          context=SimpleNamespace(scene=SimpleNamespace(world=old)))
    out = PH.hdri_world(bpy, "x.hdr", "sky", "1k")
    assert out is world and bpy.context.scene.world is world and img.name == "sky_1k" and "packed" in made
    assert [n.type for n in tree.nodes] == ["ShaderNodeTexCoord", "ShaderNodeMapping", "ShaderNodeTexEnvironment",
                                            "ShaderNodeBackground", "ShaderNodeOutputWorld"] and len(made) == 5
    del nodes_clear


# --- packing ----------------------------------------------------------------------------------------------------------------------

def png_bytes(size, colour):
    b = io.BytesIO()
    Image.new("RGB", size, colour).save(b, "PNG")
    return b.getvalue()


def synthetic():
    """A one-triangle glTF with a base-colour and a normal image (a stand-in for a kit piece)."""
    import base64
    import struct
    pos = struct.pack("<9f", 0, 0, 0, 2, 0, 0, 0, 3, 0)
    gltf = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "piece"}],
            "meshes": [{"name": "piece", "primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [2, 3, 0]}],
            "bufferViews": [{"buffer": 0, "byteLength": len(pos)}], "buffers": [{"uri": "p.bin", "byteLength": len(pos)}],
            "materials": [{"name": "MI_Brick", "normalTexture": {"index": 1}, "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
            "textures": [{"source": 0}, {"source": 1}],
            "images": [{"uri": "T_Brick_BaseColor.png", "name": "T_Brick_BaseColor"}, {"uri": "T_Brick_Normal.png", "name": "T_Brick_Normal"}]}
    files = {"p.bin": pos, "T_Brick_BaseColor.png": png_bytes((256, 256), (180, 90, 60)), "T_Brick_Normal.png": png_bytes((256, 256), (128, 128, 255))}
    del base64
    return gltf, files


def test_pack_piece_keeps_only_the_base_colour_scaled_and_is_deterministic():
    gltf, files = synthetic()
    a, rep = W.pack_piece(gltf, files.get, 64)
    b, _ = W.pack_piece(gltf, files.get, 64)
    assert a == b and rep["dropped_images"] == ["T_Brick_Normal.png"]
    doc, binc = C.read_glb(a)
    assert [i["name"] for i in doc["images"]] == ["T_Brick_BaseColor"] and "normalTexture" not in doc["materials"][0]
    v = doc["bufferViews"][doc["images"][0]["bufferView"]]
    im = Image.open(io.BytesIO(binc[v["byteOffset"]: v["byteOffset"] + v["byteLength"]]))
    assert im.size == (64, 64)
    assert W.glb_extent(a) == [2.0, 0.0, 3.0]   # Blender frame: x, depth (-z), height (y)


def test_the_packed_piece_gives_a_toon_material_with_a_trace_of_its_texture(tmp_path):
    gltf, files = synthetic()
    data, _ = W.pack_piece(gltf, files.get, 64)
    glb = tmp_path / "p.glb"
    glb.write_bytes(data)
    name, spec = W.kit_material(glb, {"id": "model.mvk_piece"}, strength=0.3, repo=tmp_path)
    assert name == "kit_mvk_piece" and spec["strength"] == 0.3 and Path(spec["texture"]).exists()
    assert [round(x * 255) for x in spec["texture_mean"]] != [0, 0, 0]


# --- layouts / table ----------------------------------------------------------------------------------------------------------------

def test_table_matches_the_library_and_the_licence_rows():
    t = W.table()
    lib = L.load()
    rows = L.sources()
    assert len(t["assets"]) == len({a["id"] for a in t["assets"]}) >= 20
    for a in t["assets"]:
        rec = L.get(a["id"], lib=lib)
        assert rec["sha256"] == a["sha256"] and rec["storage"]["location"] == "external", a["id"]
        assert rec["licence"]["status"] == "cc0" and rec["licence"]["commercial_use"] == "yes", a["id"]
        assert rec["licence"]["source_url"] and rec["licence"]["inspected_on"], a["id"]
        assert rec["three_d"]["format"] == "glb" and len(rec["three_d"]["bounds_m"]) == 3, a["id"]
        assert a["source"] == "polyhaven" or t["packs"][a["source"]]["source"] in rows
    assert "quaternius_medieval_village_megakit" in rows and rows["polyhaven"]["status"] == "cc0"
    for p in t["polyhaven"].values():
        assert p["resolution"] == "1k" and p["files_md5"]


def test_courtyard_ring_turns_every_wall_inward_and_leaves_the_camera_side_open():
    ps = {p["name"]: p for p in W.placements("castle_courtyard")}
    walls = [n for n in ps if n.startswith("wall_") and "corner" not in n]
    assert len(walls) == 4 + 3 + 3 and not any("south" in n for n in walls)
    assert ps["wall_north_0"]["yaw"] == 0 and ps["wall_west_0"]["yaw"] == 90 and ps["wall_east_0"]["yaw"] == -90
    assert ps["wall_north_1"]["asset"] == "model.mvk_wall_uneven_brick_door_round"
    assert [ps[f"wall_north_{i}"]["pos"][0] for i in range(4)] == [-3.0, -1.0, 1.0, 3.0]
    assert sum(1 for n in ps if n.startswith("cobble_")) == 12 and sum(1 for n in ps if "corner" in n) == 4


def test_layouts_are_deterministic_and_refuse_unknown_pieces():
    assert W.placements("castle_courtyard") == W.placements("castle_courtyard")
    doc = {"schema": "world_layout/1", "layouts": {"bad": {"blocks": [{"type": "piece", "name": "x", "asset": "model.nope", "pos": [0, 0, 0]}]}}}
    with pytest.raises(W.WorldKitError, match="not in world_kits.json"):
        W.placements("bad", doc=doc)
    with pytest.raises(W.WorldKitError, match="unknown layout"):
        W.placements("missing")
    street = W.placements("village_street")
    assert [p["pos"][1] for p in street if p["name"].startswith("left_")] == [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0]


def test_scene_set_is_a_valid_scene_set_with_y_up_and_landmarks():
    ss = W.scene_set("castle_courtyard")
    assert ss["schema"] == "scene_set/1" and len(ss["objects"]) == 33
    fort = next(o for o in ss["objects"] if o["id"] == "fort")
    assert fort["landmark"] and fort["pos"] == [2.0, 0.0, 16.0]   # Blender (x, y, z) -> scene_set (x, up, forward)
    wall_w = next(o for o in ss["objects"] if o["id"] == "wall_west_0")
    assert wall_w["size"][0] < 1.0 and wall_w["size"][2] == 2.0   # a quarter turn trades width and depth


def test_expand_makes_gltf_objects_with_toon_materials(tmp_path, monkeypatch):
    gltf, files = synthetic()
    data, _ = W.pack_piece(gltf, files.get, 32)
    t = W.table()
    paths = {}
    for a in t["assets"]:
        f = tmp_path / (a["name"])
        f.write_bytes(data)
        paths[a["id"]] = f
    objs, mats = W.expand("castle_courtyard", paths, repo=tmp_path)
    assert len(objs) == 33 and all("gltf" in o and o["material"] in mats for o in objs)
    o = next(x for x in objs if x["name"] == "wall_north_1")
    assert o["rotation_deg"] == [0, 0, 0] and o["location"] == [-1.0, 3.0, 0.0] and o["gltf"]["asset"] == "model.mvk_wall_uneven_brick_door_round"
    assert all(set(m) >= {"base", "texture"} for m in mats.values())


def test_the_bpy_job_script_knows_the_gltf_object_kind():
    src = (ROOT / "explainer_engine/blender/bpy/render_shot.py").read_text(encoding="utf-8")
    assert '"gltf" in o' in src and "def _gltf(" in src


def test_hill_castle_is_a_static_epic_set_with_a_deterministic_wood():
    ps = W.placements("hill_castle")
    assert ps == W.placements("hill_castle")
    names = [p["name"] for p in ps]
    assert {"castle", "hill", "river", "ground"} <= set(names) and sum(n.startswith("house") for n in names) >= 8 * 4
    trees = [p for p in ps if p["role"] == "scatter"]
    assert len(trees) == 114 and all(abs(p["pos"][0]) >= 7.5 or not -40 < p["pos"][1] < 60 for p in trees)   # none in the river bed
    assert any(p["pos"][2] > 1.0 for p in trees)   # trees on the hill follow its surface
    ss = W.scene_set("hill_castle")
    assert ss["set_id"] == "hill_castle" and any(o["landmark"] and o["id"] == "castle" for o in ss["objects"])


def test_hill_shots_have_a_still_and_a_push_and_shapes_become_flat_toon_primitives(tmp_path):
    gltf, files = synthetic()
    data, _ = W.pack_piece(gltf, files.get, 32)
    paths = {}
    for a in W.table()["assets"]:
        f = tmp_path / a["name"]
        f.write_bytes(data)
        paths[a["id"]] = f
    sc = W.poc_scenes(paths, None, 24, "hill_castle")
    assert sc["castle_still"]["frames_total"] == 1 and sc["castle_push"]["frames_total"] == 24 and "to" in sc["castle_push"]["camera"]
    hill = next(o for o in sc["castle_push"]["objects"] if o["name"] == "hill")
    assert hill["add"] == "uv_sphere" and sc["castle_push"]["materials"][hill["material"]] == {"base": "#8FA262"}
    tree = next(o for o in sc["castle_push"]["objects"] if o["name"].startswith("pine_"))
    assert sc["castle_push"]["materials"][tree["material"]]["base"].startswith("#")   # foliage: one flat tone, no raw PBR


def test_overnight_layouts_have_six_characters_and_valid_pieces_and_shots():
    doc = W.layouts()["layouts"]
    for lid, era in (("antique_forum", "E1"), ("hill_castle", "E2"), ("harbour_square", "E3"), ("field_camp", "E4")):
        assert W.placements(lid)   # every asset is in world_kits.json, no two names alike
        cast = doc[lid]["cast"]
        assert len(cast) >= 6 and len({r[0] for r in cast}) == len(cast), lid
        for sid, (c0, c1, a0, a1, lens, n) in doc[lid]["shots"].items():
            assert len(c0) == 3 and len(a0) == 3 and lens > 0 and n >= 0 and (c1 is None) == (a1 is None), (lid, sid)
        assert W.scene_set(lid)
