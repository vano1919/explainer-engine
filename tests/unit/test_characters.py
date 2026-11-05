"""ICW-06 characters (roadmap 15 ICW-06, 21.6 PoC 1, D-101): the deterministic GLB packer, the itch.io free-pack button, the
character registry and the cast object of ``bpy/render_shot.py`` (head + hair + costume on one UBC skeleton, toon materials,
the mouth), the turnaround job. No Blender and no pack download: tiny GLBs are made here."""
import io
import json
import struct
import urllib.error
import zlib

import pytest

from explainer_engine.assets import itch
from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import rigs
from explainer_engine.blender import turnaround as T


def png(rgb=(200, 120, 90), w=2, h=2):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    raw = zlib.compress((b"\x00" + bytes(rgb) * w) * h)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw)
            + chunk(b"IEND", b""))


def gltf_with(materials, *, missing=()):
    """A glTF naming one image per material (``missing`` ones are not shipped), and its reader."""
    doc = {"asset": {"version": "2.0"}, "buffers": [{"uri": "m.bin", "byteLength": 4}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 4}],
           "images": [{"uri": f"{m}.png"} for m in materials], "textures": [{"source": i} for i in range(len(materials))],
           "materials": [{"name": m, "pbrMetallicRoughness": {"baseColorTexture": {"index": i}}} for i, m in enumerate(materials)]}
    files = {"m.bin": b"\x01\x02\x03\x04", **{f"{m}.png": png((40 + 20 * i, 90, 160)) for i, m in enumerate(materials)
                                              if m not in missing}}
    return doc, files.get


def test_pack_glb_is_deterministic_and_drops_an_image_the_pack_does_not_ship():
    doc, read = gltf_with(["MI_A", "MI_B"], missing=("MI_B",))
    one, rep = C.pack_glb(doc, read)
    two, _ = C.pack_glb(json.loads(json.dumps(doc)), read)
    assert one == two and rep["dropped_images"] == ["MI_B.png"] and rep["images"] == 1
    back, binc = C.read_glb(one)
    assert back["buffers"] == [{"byteLength": len(binc)}] and "uri" not in json.dumps(back["images"])
    a, b = back["materials"]
    assert a["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0
    assert "baseColorTexture" not in b["pbrMetallicRoughness"]  # its texture went with the missing image
    assert C.glb_summary(one)["materials"] == ["MI_A", "MI_B"]


def test_pack_glb_refuses_a_missing_or_short_buffer():
    doc, read = gltf_with(["MI_A"])
    with pytest.raises(C.CharacterError, match="missing"):
        C.pack_glb(doc, lambda uri: None if uri == "m.bin" else read(uri))
    doc["buffers"][0]["byteLength"] = 99
    with pytest.raises(C.CharacterError, match="byteLength|bytes"):
        C.pack_glb(doc, read)


def fake_cast(tmp_path, monkeypatch):
    """Every character asset as a tiny GLB holding every material the registry names; the derived cache under tmp_path."""
    monkeypatch.setattr(L, "REPO", tmp_path)
    reg = C.registry()
    names = sorted({m for x in (*reg["characters"].values(), *reg["costumes"].values()) for m in x["materials"]}
                   | {s["texture"] for x in (*reg["characters"].values(), *reg["costumes"].values()) for s in x["materials"].values()})
    data, _ = C.pack_glb(*gltf_with(names))
    paths = {}
    for a in C.assets()["assets"]:
        p = tmp_path / f"{a['id']}.glb"
        p.write_bytes(data)
        paths[a["id"]] = p
    return reg, paths


def test_registry_ties_each_costume_to_its_body_and_every_asset_is_in_the_library():
    reg, lib, table = C.registry(), L.load(), C.assets()
    assert reg["schema"] == "character/1"
    for a in table["assets"]:
        rec = L.get(a["id"], lib=lib)
        assert rec["sha256"] == a["sha256"] and rec["storage"]["external_path"]  # GLBs stay out of git
    for cid in reg["characters"]:
        for co in reg["costumes"]:
            same = C.get(cid, reg=reg)["body"] == C.costume(co, reg=reg)["body"]
            if same:
                ids = C.asset_ids(cid, co, reg=reg)
                assert C.get(cid, reg=reg)["head"] in ids and co in ids
            else:
                with pytest.raises(C.CharacterError):
                    C.asset_ids(cid, co, reg=reg)
    # CN-19: a costume names its body model as lineage parent
    for co in reg["costumes"]:
        assert L.get(co, lib=lib)["lineage"]["parent"].startswith("model.ubc_superhero_")


def test_scene_object_assembles_head_hair_costume_with_one_skin_and_a_tinted_costume(tmp_path, monkeypatch):
    reg, paths = fake_cast(tmp_path, monkeypatch)
    lip = rigs.LipSync(24).plan({"metadata": {"duration": 1.0}, "mouthCues": [{"start": 0.0, "end": 0.5, "value": "D"}]}, 12)
    obj, mats = C.scene_object("speaker_a", "ink_test_m", "costume.mco_male_ranger", paths, location=(1, 2, 0), yaw_deg=30,
                               action="Idle_Loop", action_offset=5, tint="support_blue", lipsync=lip, reg=reg)
    ch = obj["character"]
    assert [p["path"] for p in ch["parts"]] == [str(paths["model.ubc_superhero_male"]), str(paths["model.ubc_hair_simpleparted"]),
                                                str(paths["costume.mco_male_ranger"])]
    assert ch["parts"][0]["keep_bones"] == ["Head", "neck_01"] and "Male_Ranger_Head_Hood" in ch["parts"][2]["drop"]
    assert ch["animation"] == {"path": str(paths["animation.ual1_standard"]), "action": "Idle_Loop", "offset": 5, "speed": 1.0}
    assert obj["rotation_deg"] == [0.0, 0.0, 30.0] and ch["lipsync"]["shapes"].startswith("DDDDDD")
    assert set(ch["mouth"]["keys"]) >= set("ABCDEFGHX") and ch["mouth"]["rest"] == "X"
    skin = {ch["materials"][m] for m, s in {**C.get("ink_test_m")["materials"],
                                           **C.costume("costume.mco_male_ranger")["materials"]}.items() if s["slot"] == "skin"}
    assert skin == {"ink_test_m_skin"} and "texture" not in mats["ink_test_m_skin"]  # hands match the face: one flat mean
    coat = mats["mco_male_ranger_support_blue"]
    assert coat["base"] == "support_blue" and coat["strength"] == 0.5 and coat["texture"].endswith(".png")
    assert mats["ink_test_m_hair"]["base"] == "night"
    assert mats[reg["mouth"]["interior_material"]] == {"base": reg["mouth"]["interior_token"]}
    with pytest.raises(C.CharacterError):
        C.scene_object("x", "ink_test_m", "costume.mco_male_ranger", paths, action="Idle_Loop", action_speed=0, reg=reg)


def test_turnaround_is_four_views_and_nine_mouths_tracked_on_the_head(tmp_path, monkeypatch):
    reg, paths = fake_cast(tmp_path, monkeypatch)
    vs = T.views("ink_test_m", reg=reg)
    assert len(vs) == T.FRAMES == 13 and [v["view"] for v in vs[:4]] == ["front", "three_quarter", "side", "back"]
    assert [v["mouth"] for v in vs[4:]] == list(T.MOUTHS) and all(v.get("track") for v in vs[4:])
    tr = T.lipsync_tracks(vs, reg=reg)["tracks"]
    assert len(tr) == 8 and all(sum(val for _, val in pts) == 1.0 for pts in tr.values())  # one view per open shape
    sc = T.scene("ink_test_m", "costume.mco_male_ranger", paths, tint="support_blue", reg=reg)
    assert sc["frames_total"] == 13 and len(sc["camera"]["keys"]) == 13 and sc["camera"]["interp"] == "CONSTANT"
    assert sc["objects"][1]["character"]["animation"]["speed"] < 0.01  # the idle pose held, never the bind pose


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def open(self, req, timeout=None):
        self.calls.append((req.get_method(), req.full_url, req.data))
        for key, body in self.pages:
            if key in req.full_url:
                if isinstance(body, Exception):
                    raise body
                return FakeResp(body if isinstance(body, bytes) else body.encode())
        raise AssertionError(f"unexpected {req.full_url}")


PAGE = '<input name="csrf_token" value="tok1"><script>{"min_price":0}</script>'
DL = ('<input name="csrf_token" value="tok2"><a data-upload_id="11" class="x" title="Pack[Standard].zip">'
      '<a data-upload_id="12" title="Pack[Source].zip">')


def test_itch_download_uses_the_page_button_and_streams_the_chosen_file(tmp_path):
    op = FakeOpener([("/download_url", json.dumps({"url": "https://q.itch.io/pack/download/abc"})),
                     ("/download/abc", DL), ("/file/11", json.dumps({"url": "https://cdn.example/pack.zip"})),
                     ("cdn.example/pack.zip", b"ZIPDATA"), ("https://q.itch.io/pack", PAGE)])
    done = itch.download("https://q.itch.io/pack/", tmp_path, match="standard", session=itch.Session(op, backoff_s=0))
    assert [d["name"] for d in done] == ["Pack[Standard].zip"] and (tmp_path / "Pack[Standard].zip").read_bytes() == b"ZIPDATA"
    posts = [c for c in op.calls if c[0] == "POST"]
    assert b"csrf_token=tok1" in posts[0][2] and b"csrf_token=tok2" in posts[1][2]
    assert "after_download_lightbox=1" in posts[1][1] and not list(tmp_path.glob("*.part"))


def test_itch_refuses_a_paid_pack_and_retries_a_rate_limit(tmp_path):
    paid = FakeOpener([("https://q.itch.io/pack", PAGE.replace('"min_price":0', '"min_price":500'))])
    with pytest.raises(itch.ItchError, match="not a free pack"):
        itch.uploads("https://q.itch.io/pack", session=itch.Session(paid, backoff_s=0))
    n = {"k": 0}

    class Flaky(FakeOpener):
        def open(self, req, timeout=None):
            n["k"] += 1
            if n["k"] == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)
            return super().open(req, timeout)
    s = itch.Session(Flaky([("https://q.itch.io/pack", PAGE)]), backoff_s=0)
    assert "tok1" in s.get("https://q.itch.io/pack") and n["k"] == 2


def test_turnaround_compare_is_zero_for_the_same_sheet_and_grows_with_a_change(tmp_path):
    from PIL import Image
    for d, shade in (("a", 100), ("b", 100), ("c", 160)):
        (tmp_path / d / "views").mkdir(parents=True)
        for m in T.MOUTHS:
            Image.new("RGB", (8, 8), (shade, shade, shade)).save(tmp_path / d / "views" / f"mouth_{m}.png")
    assert T.compare(tmp_path / "a", tmp_path / "b")["mean_rms"] == 0.0
    c = T.compare(tmp_path / "a", tmp_path / "c")
    assert c["mean_rms"] > 0.2 and c["severity"] == "INFO" and len(c["views"]) == 9


def test_measure_clips_reads_the_blender_samples_into_the_poc1_line(tmp_path, monkeypatch):
    from explainer_engine.blender import project as PJ
    from test_lipsync_map import _walk
    reg, paths = fake_cast(tmp_path, monkeypatch)
    monkeypatch.setattr(PJ.BlenderProject, "resolve", lambda self, b=None, **k: PJ.BlenderBinary("blender", "5.2.3", None, "cpu", None))

    def run(argv, **kw):
        job = json.loads(open(argv[-1]).read())
        still = [{"root": [0, 0, 0], "pelvis": [0, 0, 1], "foot_l": [0.1, 0, 0.1], "foot_r": [-0.1, 0, 0.1]}] * 20
        acts = {a: {"frames": [0, 31], "samples": _walk() if "Walk" in a or "Jog" in a else still} for a in job["actions"]}
        open(job["out"], "w").write(json.dumps({"fps": 24, "actions": acts}))
        return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
    doc = C.measure_clips(tmp_path / "m", run=run, cpaths=paths)
    assert doc["of"] == 8 and doc["usable"] == 8 and doc["clips"]["Walk_Loop"]["natural_speed_mps"] == 0.8
    assert doc["clips"]["Idle_Loop"]["root_speed_mps"] == 0.0 and (tmp_path / "m" / "poc1_clips.json").exists()
