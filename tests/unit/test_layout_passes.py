"""Layout passes for J2/J4 (D-116, guide step 2.3): the clips' frame ranges and geometry (CN-08), the pass blocks, the jobs, the
mp4 cut, the upload check, and the Blender side's material rewrite on a recorded node graph (no bpy)."""
import importlib.util
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from explainer_engine.blender import layout_passes as LP
from explainer_engine.blender import render as R
from explainer_engine.core.errors import ContractError

ROOT = Path(__file__).resolve().parents[2]


# ---- host side ------------------------------------------------------------------------------------------------------------------

def test_battle_is_two_145_frame_clips_that_share_8_frames_and_the_duel_one_121_frame_clip():
    b, d = LP.plan("battle"), LP.plan("duel")
    assert [(c["first"], c["last"], c["frames"]) for c in b["clips"]] == [(0, 144, 145), (137, 281, 145)]
    assert b["frames"] == 282 and b["clips"][1]["first"] == b["clips"][0]["last"] - 7   # 8 shared frames: 137..144
    assert [(c["first"], c["last"]) for c in d["clips"]] == [(0, 120)] and d["frames"] == 121
    for p in (b, d):
        assert p["fps"] == 24 and p["size"] == [1920, 1088]
        assert all((c["frames"] - 1) % 8 == 0 for c in p["clips"])          # 8k+1 (BP-139)
    assert b["clips"][0]["seconds"] == pytest.approx(6.04, abs=0.01)        # inside one LTX clip's 3-8 s


def test_geometry_passes_cn08_with_no_fail_and_bad_ranges_are_refused():
    for s in LP.SCENES:
        assert [f for f in LP.geometry_findings(s) if f["severity"] == "FAIL"] == []
    with pytest.raises(ContractError):
        LP.clip_ranges(145, 2, 145)
    with pytest.raises(ContractError):
        LP.clip_ranges(145, 0, 8)
    with pytest.raises(ContractError):
        LP.plan("parade")


def test_routes_take_their_passes_j2_clay_j4_colour_depth_line():
    assert LP.ROUTE_PASSES == {"J2": ("clay",), "J4": ("colour", "depth", "line")}
    assert LP.plan("battle")["route"] == "J4" and LP.plan("battle")["passes"] == ["colour", "depth", "line"]
    assert LP.plan("duel")["route"] == "J2" and LP.plan("duel")["passes"] == ["clay"]
    assert {k: LP.engine_of(k) for k in LP.PASSES} == {"clay": "workbench", "depth": "eevee", "line": "eevee", "colour": "eevee"}


def test_pass_blocks_carry_their_settings_and_the_battle_background_gets_no_lines():
    clay, depth, line = LP.block("clay", "duel"), LP.block("depth", "battle"), LP.block("line", "battle")
    assert clay["clay_rgb"] == list(LP.CLAY_RGB) and clay["background_rgb"] == list(LP.CLAY_BACKGROUND)
    assert depth["near_m"] < depth["far_m"] and depth["kind"] == "depth"
    assert line["line_px"] == LP.LINE_PX and "EE_Crowd_t2" in line["no_line"]   # plan 9.3: lines on the fore and mid planes only
    assert LP.block("line", "duel")["no_line"] == []
    with pytest.raises(ContractError):
        LP.block("normal", "duel")


def test_a_pass_job_is_the_render_shot_job_with_the_pass_engine_and_block(tmp_path):
    doc = {"kind": "described", "objects": [], "camera": {}, "style": {}}
    spec = {"render": {"profile": "eevee_fast", "samples": 4, "motion_blur": False, "denoise": False}, "seed": 1}
    j = LP.job("battle", "line", doc, spec, tmp_path, "5.2.3", frames=[0, 144], scale=0.25)
    assert j["job"] == "render_shot/1" and j["engine"] == "eevee" and (j["width"], j["height"]) == (480, 272)
    assert j["scene"]["layout_pass"] == LP.block("line", "battle") and "layout_pass" not in doc   # the shared doc stays as built
    assert j["frames"] == [0, 144] and j["fps"] == 24 and j["frame_name"] == R.FRAME_NAME
    assert Path(j["frames_dir"]) == tmp_path / "battle" / "line" / "frames"
    assert LP.job("duel", "clay", doc, spec, tmp_path, "5.2.3", frames=[0])["engine"] == "workbench"


def _cast(name, mats):
    return {"name": name, "append": {"path": "/x.blend"}, "_materials": dict(mats)}


def test_the_duel_keeps_the_yard_drops_the_table_and_merges_the_cast_materials():
    base = {"objects": [{"name": "ground", "material": "ground"}, {"name": "wall", "material": "brick"},
                        {"name": "table", "material": "table"}, {"name": "speaker_a_body", "material": "coat"}],
            "materials": {"ground": {"base": "paper"}, "brick": {"base": "paper"}, "table": {"base": "paper"}, "coat": {"base": "x"}}}
    sc = LP.duel_objects(base, [_cast("duelist_a", {"skin": {"base": "kit_card"}}), _cast("duelist_b", {"skin": {"base": "kit_card"}})])
    assert [o["name"] for o in sc["objects"]] == ["ground", "wall", "duelist_a", "duelist_b"]
    assert sorted(sc["materials"]) == ["brick", "ground", "skin"] and sc["camera"] == LP.DUEL_CAMERA
    assert all("_materials" not in o for o in sc["objects"])
    with pytest.raises(ContractError):
        LP.duel_objects(base, [_cast("a", {"skin": {"base": "1"}}), _cast("b", {"skin": {"base": "2"}})])
    a, b = LP.DUEL_CAST
    assert a[4][0] < b[4][0] and a[5] == -b[5] == 90.0 and {a[6], b[6]} == {"Sword_Attack", "Sword_Idle"}   # face to face, one attacks


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")
def test_a_clip_is_an_h264_of_exactly_its_frames(tmp_path):
    from PIL import Image
    frames = []
    for i in range(9):
        f = tmp_path / f"frame_{i:06d}.png"
        Image.new("RGB", (64, 32), (i * 20, 0, 0)).save(f)
        frames.append(f)
    row = LP._mp4(frames, tmp_path / "c.mp4")
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames,codec_name", "-of", "json", str(tmp_path / "c.mp4")], capture_output=True, text=True)
    s = json.loads(out.stdout)["streams"][0]
    assert s["codec_name"] == "h264" and int(s["nb_read_frames"]) == 9 == row["frames"] and len(row["sha256"]) == 64
    assert not (tmp_path / ".c_list").exists()


def test_a_crash_on_exit_after_every_frame_is_saved_still_counts_as_finished(tmp_path):
    (tmp_path / "frames").mkdir()
    assert not LP.finished(tmp_path, [0, 1])
    (tmp_path / "bpy_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "progress.jsonl").write_text('{"index": 0}\n{"index": 1}\n', encoding="utf-8")
    (tmp_path / "frames" / R.FRAME_NAME.format(index=0)).write_bytes(b"png")
    assert not LP.finished(tmp_path, [0, 1])                     # frame 1 is listed but its file is missing
    (tmp_path / "frames" / R.FRAME_NAME.format(index=1)).write_bytes(b"png")
    assert LP.finished(tmp_path, [0, 1]) and not LP.finished(tmp_path, [0, 1, 2])


def _manifest(d: Path, *, subset=False, scale=1.0):
    (d / "line").mkdir(parents=True)
    (d / "line" / "battle_c1_line.mp4").write_bytes(b"clip")
    man = {"schema": LP.SCHEMA, "subset": subset, "scale": scale, "passes": {"line": {"clips": {"battle_c1": {"path": "battle_c1_line.mp4"}}}}}
    (d / "layout_manifest.json").write_text(json.dumps(man), encoding="utf-8")


def test_upload_puts_clips_and_manifest_under_the_route_test_prefix_and_checks_their_hashes(tmp_path):
    _manifest(tmp_path / "out" / "battle")
    vault = R.LocalVault(tmp_path / "vault")
    got = LP.upload(tmp_path / "out", "battle", vault=vault)
    assert got == ["route_test_2026-11/layouts/battle/layout_manifest.json", "route_test_2026-11/layouts/battle/line/battle_c1_line.mp4"]
    assert (tmp_path / "vault" / got[1]).read_bytes() == b"clip"

    class Lossy(R.LocalVault):
        def upload_many(self, pairs, message=""):
            super().upload_many(pairs[:1], message)
    with pytest.raises(ContractError, match="not on the vault"):
        LP.upload(tmp_path / "out", "battle", vault=Lossy(tmp_path / "vault2"))


def test_a_review_subset_or_a_scaled_render_is_never_uploaded(tmp_path):
    for i, kw in enumerate(({"subset": True}, {"scale": 0.25})):
        _manifest(tmp_path / f"o{i}" / "duel", **kw)
        with pytest.raises(ContractError, match="full-size"):
            LP.upload(tmp_path / f"o{i}", "duel", vault=R.LocalVault(tmp_path / "v"))


# ---- Blender side on a recorded node graph -------------------------------------------------------------------------------------

class Sock:
    def __init__(self, node, name, value=0.0):
        self.node, self.name, self.default_value, self.links = node, name, value, []

    @property
    def is_linked(self):
        return bool(self.links)


class Socks(list):
    def __getitem__(self, k):
        if isinstance(k, str):
            return next(s for s in self if s.name == k)
        return list.__getitem__(self, k)

    def __contains__(self, k):
        return any(s.name == k for s in self) if isinstance(k, str) else list.__contains__(self, k)

    def get(self, k):
        return next((s for s in self if s.name == k), None)


NODE_SOCKETS = {
    "ShaderNodeOutputMaterial": (["Surface", "Volume", "Displacement"], []),
    "ShaderNodeBsdfPrincipled": (["Base Color", "Alpha"], ["BSDF"]),
    "ShaderNodeBsdfTransparent": (["Color"], ["BSDF"]),
    "ShaderNodeMixShader": (["Fac", "Shader", "Shader_001"], ["Shader"]),
    "ShaderNodeEmission": (["Color", "Strength"], ["Emission"]),
    "ShaderNodeMath": (["Value", "Value_001"], ["Value"]),
    "ShaderNodeCameraData": ([], ["View Vector", "View Z Depth", "View Distance"]),
    "ShaderNodeMapRange": (["Value", "From Min", "From Max", "To Min", "To Max"], ["Result"]),
    "ShaderNodeTexImage": (["Vector"], ["Color", "Alpha"]),
}


class Node:
    def __init__(self, kind):
        ins, outs = NODE_SOCKETS[kind]
        self.bl_idname, self.is_active_output = kind, kind == "ShaderNodeOutputMaterial"
        self.inputs = Socks(Sock(self, n, (1.0, 1.0, 1.0, 1.0) if "Color" in n else 1.0) for n in ins)
        self.outputs = Socks(Sock(self, n) for n in outs)
        self.operation, self.clamp = None, False


class Link:
    def __init__(self, a, b):
        self.from_socket, self.to_socket, self.from_node, self.to_node = a, b, a.node, b.node


class Tree:
    def __init__(self):
        self.nodes = types.SimpleNamespace(items=[], new=self._new, __iter__=None)
        self._nodes = []
        self.links = types.SimpleNamespace(new=self._link, remove=self._unlink)

    def _new(self, kind):
        n = Node(kind)
        self._nodes.append(n)
        return n

    def _link(self, a, b):
        for old in list(b.links):
            self._unlink(old)
        lk = Link(a, b)
        a.links.append(lk)
        b.links.append(lk)
        return lk

    def _unlink(self, lk):
        lk.from_socket.links.remove(lk)
        lk.to_socket.links.remove(lk)


class Nodes(list):
    pass


def _tree():
    t = Tree()
    t.nodes = type("N", (), {"__iter__": lambda s: iter(t._nodes), "new": lambda s, k: t._new(k)})()
    return t


def _src(sock):
    return sock.links[0].from_socket if sock.links else None


@pytest.fixture()
def lp(monkeypatch):
    monkeypatch.setitem(sys.modules, "bpy", types.ModuleType("bpy"))
    spec = importlib.util.spec_from_file_location("layout_pass_t", ROOT / "explainer_engine/blender/bpy/layout_pass.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mat(tree):
    return types.SimpleNamespace(use_nodes=True, node_tree=tree)


def test_a_billboard_keeps_its_cutout_alpha_and_shows_its_texture_flat_in_the_colour_pass(lp):
    t = _tree()
    out, tex, tr, bsdf, mix = (t.nodes.new(k) for k in ("ShaderNodeOutputMaterial", "ShaderNodeTexImage", "ShaderNodeBsdfTransparent",
                                                     "ShaderNodeBsdfPrincipled", "ShaderNodeMixShader"))
    t.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    t.links.new(tex.outputs["Alpha"], mix.inputs[0])
    t.links.new(tr.outputs[0], mix.inputs[1])
    t.links.new(bsdf.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs["Surface"])
    used = lp.rewrite_material(_mat(t), {"kind": "colour"})
    assert used == {"shader": "ShaderNodeBsdfPrincipled", "alpha": "linked"}
    new_mix = _src(out.inputs["Surface"]).node
    assert new_mix is not mix and _src(new_mix.inputs[0]) is tex.outputs["Alpha"]
    assert _src(new_mix.inputs[1]).node.bl_idname == "ShaderNodeBsdfTransparent"
    emit = _src(new_mix.inputs[2]).node
    assert emit.bl_idname == "ShaderNodeEmission" and _src(emit.inputs["Color"]) is tex.outputs["Color"]


def test_transparent_on_the_second_side_inverts_the_factor_and_a_plain_principled_keeps_its_alpha(lp):
    t = _tree()
    out, tr, bsdf, mix = (t.nodes.new(k) for k in ("ShaderNodeOutputMaterial", "ShaderNodeBsdfTransparent", "ShaderNodeBsdfPrincipled",
                                                "ShaderNodeMixShader"))
    mix.inputs[0].default_value = 0.3
    t.links.new(bsdf.outputs[0], mix.inputs[1])
    t.links.new(tr.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs["Surface"])
    lp.rewrite_material(_mat(t), {"kind": "line"})
    inv = _src(_src(out.inputs["Surface"]).node.inputs[0]).node
    assert inv.bl_idname == "ShaderNodeMath" and inv.operation == "SUBTRACT" and inv.inputs[1].default_value == 0.3
    t2 = _tree()
    out2, p = t2.nodes.new("ShaderNodeOutputMaterial"), t2.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Alpha"].default_value, p.inputs["Base Color"].default_value = 0.5, (0.2, 0.4, 0.6, 1.0)
    t2.links.new(p.outputs[0], out2.inputs["Surface"])
    assert lp.rewrite_material(_mat(t2), {"kind": "colour"}) == {"shader": "ShaderNodeBsdfPrincipled", "alpha": 0.5}
    new_mix = _src(out2.inputs["Surface"]).node
    assert new_mix.inputs[0].default_value == 0.5 and _src(new_mix.inputs[2]).node.inputs["Color"].default_value == (0.2, 0.4, 0.6, 1.0)


def test_depth_is_inverse_view_depth_mapped_from_far_to_near_onto_black_to_white(lp):
    t = _tree()
    out, p = t.nodes.new("ShaderNodeOutputMaterial"), t.nodes.new("ShaderNodeBsdfPrincipled")
    t.links.new(p.outputs[0], out.inputs["Surface"])
    lp.rewrite_material(_mat(t), {"kind": "depth", "near_m": 2.0, "far_m": 400.0})
    emit = _src(_src(out.inputs["Surface"]).node.inputs[2]).node
    rng = _src(emit.inputs["Color"]).node
    inv = _src(rng.inputs["Value"]).node
    assert rng.bl_idname == "ShaderNodeMapRange" and rng.clamp
    assert (rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value) == (1 / 400.0, 1 / 2.0)
    assert (rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value) == (0.0, 1.0)
    assert inv.operation == "DIVIDE" and inv.inputs[0].default_value == 1.0
    assert _src(inv.inputs[1]).name == "View Z Depth"
    for z in (2.0, 20.0, 400.0):   # the mapping the graph computes: near white, far black
        v = min(max((1 / z - 1 / 400.0) / (1 / 2.0 - 1 / 400.0), 0.0), 1.0)
        assert v == {2.0: 1.0, 400.0: 0.0}.get(z, v) and 0.0 <= v <= 1.0


def test_the_blender_side_knows_the_same_passes_as_the_host(lp):
    assert tuple(lp.KINDS) == LP.PASSES
    text = (ROOT / "explainer_engine/blender/bpy/layout_pass.py").read_text(encoding="utf-8")
    assert '"Raw" if kind == "depth"' in text and "collection_negation" in text and "dither_intensity = 0.0" in text
    assert "compositing_node_group = None" in text and "use_compositing = False" in text   # no paper or haze over a pass
    rs = (ROOT / "explainer_engine/blender/bpy/render_shot.py").read_text(encoding="utf-8")
    assert rs.index("build_crowd(scene, sc[\"crowds\"]") < rs.index("apply_layout_pass(scene, sc[\"layout_pass\"]")
