"""ICW-05 style sheets and PoC 3 (roadmap 15 ICW-05, 21.6): the CC0 sources agree with the library, nothing is stored in git,
the five scenes reference only materials their style graph builds, every sheet is a valid one-frame shot_spec/2 with its own
cache key, and the collage lays out a row per variant."""
import json
from pathlib import Path

import pytest
from PIL import Image

from explainer_engine.assets import library as L
from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core import contracts as C
from explainer_engine.core import shot_cache
from explainer_engine.standards import sourced_rules as SR


def fake_paths(tmp_path):
    out = {}
    for a in SS.sources():
        p = tmp_path / a["name"]
        if p.suffix in (".jpg", ".png"):
            Image.new("RGB", (8, 8), (120, 90, 60)).save(p)
        else:
            p.write_bytes(b"x")
        out[a["id"]] = p
    return out


def test_sources_match_the_library_and_stay_out_of_git():
    lib = L.load()
    for a in SS.sources():
        rec = L.get(a["id"], lib=lib)
        assert rec["sha256"] == a["sha256"] and rec["bytes"] == a["bytes"] and rec["kind"] == a["kind"]
        assert rec["storage"]["location"] == "external" and rec["file"].startswith(L.CACHE.as_posix() + "/")
        assert rec["licence"]["status"] == "cc0" and rec["licence"]["commercial_use"] == "yes"
        assert rec["licence"]["source_url"] == a["page"] and rec["licence"]["revision_or_version"] == a["version"]
        assert a["url"].startswith("https://")
        for d in a.get("deps", []):
            assert any(x["asset_id"] == d for x in rec["deps"])
    assert L.verify() == []


def test_poc3_set_is_three_models_two_materials_one_hdri_and_the_paper():
    kinds = [a["kind"] for a in SS.sources()]
    assert kinds.count("model") == 3 and kinds.count("material") == 2 and kinds.count("hdri") == 1
    assert "texture.acg_paper003" in {a["id"] for a in SS.sources()}


def test_ingest_external_keeps_a_small_file_out_of_git(tmp_path):
    lib_path = tmp_path / "library.json"
    lib_path.write_text(json.dumps({"schema": "asset_library/2", "items": []}), encoding="utf-8")
    src = tmp_path / "small.jpg"
    Image.new("RGB", (4, 4)).save(src)
    rec, _ = L.ingest(src, "texture.t_small", "texture", path=lib_path, repo=tmp_path, external=True, tags=["t"],
                      bible_version="1.5", licence=L.licence_from_source("polyhaven", url="https://polyhaven.com/a/x", version="1k"))
    assert rec["storage"]["location"] == "external"
    assert rec["storage"]["external_path"] == "assets/3d/texture/texture.t_small/small.jpg"
    assert rec["file"].startswith(L.CACHE.as_posix() + "/")


def test_scenes_use_only_materials_their_graph_builds(tmp_path):
    paths = fake_paths(tmp_path)
    scs = SS.scenes(paths)
    assert tuple(scs) == SS.SCENE_IDS
    for sid, sc in scs.items():
        used = {o["material"] for o in sc["objects"] if o.get("material")}
        assert used == set(sc["materials"]), sid
        for o in sc["objects"]:
            assert ("add" in o) != ("append" in o)
            if "add" in o:
                assert o["add"] in ("plane", "cube", "cylinder", "uv_sphere", "cone", "ico_sphere")
        assert {"location", "look_at", "lens_mm", "focus_distance_m"} <= set(sc["camera"])


def test_every_sheet_is_a_valid_master_spec_with_its_own_cache_key(tmp_path):
    paths = fake_paths(tmp_path)
    scs = SS.scenes(paths)
    keys = set()
    for sid in SS.SCENE_IDS:
        for vid in SS.VARIANT_IDS:
            scene, graph = SS.job_scene(sid, vid, scs[sid], paths)
            assert S.check(graph) == []
            assert graph["path"] == ("cycles_safe" if vid == "S" else "eevee")
            _, tokens = SS.style_for(vid)
            spec = SS.spec_for(sid, vid, tokens, scene=scene)
            assert [f for f in C.errors(spec) if f["severity"] == "FAIL"] == [], (sid, vid)
            assert spec["look"]["line_weight_px"] == tokens.line_px
            assert spec["clock"]["frames"] == 1 and spec["lane"] == "STILL_3D"
            keys.add(shot_cache.key(spec))
    assert len(keys) == len(SS.SCENE_IDS) * len(SS.VARIANT_IDS)


def test_scene_hash_ignores_the_machine_path_but_not_the_scene(tmp_path):
    a = {"objects": [{"name": "x", "path": str(L.REPO.resolve()) + "/tools/assets_cache/aa/f.blend"}]}
    b = {"objects": [{"name": "x", "path": "tools/assets_cache/aa/f.blend"}]}
    assert SS.scene_sha256(a) == SS.scene_sha256(b)
    assert SS.scene_sha256(b) != SS.scene_sha256({"objects": [{"name": "y", "path": "tools/assets_cache/aa/f.blend"}]})


def test_fetch_from_source_keeps_only_the_registered_bytes(tmp_path, monkeypatch):
    a = next(x for x in SS.sources() if x["id"] == "material.ph_brick_wall_001")
    monkeypatch.setattr(SS, "sources", lambda path=None: [a])
    monkeypatch.setattr(L, "cached", lambda rec, repo=None: None)
    with pytest.raises(ValueError, match="other bytes"):
        SS.fetch(repo=tmp_path, download=lambda url: b"not the file", vault_first=False)
    rec = L.get(a["id"])
    assert not (tmp_path / rec["file"]).exists()


def test_collage_has_a_row_per_variant_and_a_column_per_scene(tmp_path):
    rows = []
    for vid in ("A", "B"):
        for sid in ("dialogue_cu", "travel"):
            f = tmp_path / f"{sid}_{vid}.png"
            Image.new("RGB", (256, 144), (200, 100, 50)).save(f)
            rows.append({"scene": sid, "variant": vid, "frame": str(f), "scaled": False})
    (tmp_path / "style_sheets.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    path = SS.collage(tmp_path, cell_w=320)
    with Image.open(path) as im:
        assert im.width == 360 + 2 * (320 + 12) + 12 and im.height == 70 + 2 * (180 + 12) + 12
    assert (tmp_path / "collage_preview.jpg").exists()


def test_a_line_outside_bp173_fails_the_spec_contract():
    lo, hi = SR.T("BP-173", "weight_px_1440")
    for px in (lo - 0.5, hi + 0.5):
        spec = SS.spec_for("travel", "B", S.StyleTokens(line_px=px), scene={"objects": []})
        assert any(f["severity"] == "FAIL" and "BP-173" in f["detail"] for f in C.errors(spec)), px


# --- round 2: clips, the light profile, the palette under AgX -------------------------------------------------------------------

def test_clips_are_valid_video_specs_with_motion_and_their_own_cache_keys(tmp_path):
    paths = fake_paths(tmp_path)
    base = SS.scenes(paths)
    keys = set()
    for sid in SS.CLIP_SCENES:
        sc = SS.motion(sid, base[sid])
        assert sc["camera"]["to"] and sc["frames_total"] == SS.CLIP_FRAMES
        for vid in SS.CLIP_VARIANTS:
            scene, graph = SS.job_scene(sid, vid, sc, paths)
            assert scene["frames_total"] == SS.CLIP_FRAMES and S.check(graph) == []
            _, tokens = SS.style_for(vid)
            spec = SS.spec_for(sid, vid, tokens, scene=scene, frames=SS.CLIP_FRAMES)
            assert [f for f in C.errors(spec) if f["severity"] == "FAIL"] == [], (sid, vid)
            assert spec["lane"] == "VIDEO_3D" and spec["clock"]["frames"] == 48 and spec["clock"]["fps"] == 24
            assert spec["scene"]["camera"]["rig"] in ("push", "dolly")
            keys.add(shot_cache.key(spec))
    assert len(keys) == len(SS.CLIP_SCENES) * len(SS.CLIP_VARIANTS)
    battle = SS.motion("battle_wide", base["battle_wide"])
    movers = [o for o in battle["objects"] if o.get("to")]
    assert movers and all(o["interp"] == "LINEAR" and o["name"].startswith("a") for o in movers)
    assert not any(o.get("to") for o in base["battle_wide"]["objects"])  # motion() copies, the sheets stay still


def test_clip_variants_show_shadows_on_against_the_light_default():
    on, light = SS.style_for("B_shadow")[1], SS.style_for("B_light")[1]
    assert on.shadows and not light.shadows and not light.palette_match
    assert SS.style_for("B_match")[1].palette_match and SS.style_for("A_match")[1].line_px == S.variant("A").line_px


def test_frame_times_split_the_first_frame_from_the_steady_rest(tmp_path):
    (tmp_path / "render_times.json").write_text(json.dumps({"0": 30.0, "1": 5.0, "2": 6.0, "3": 4.0}), encoding="utf-8")
    t = SS.frame_times(tmp_path)
    assert t == {"first_s": 30.0, "steady_median_s": 5.0, "mean_s": 11.25, "frames": 4}


def test_mp4_is_a_review_copy_from_the_frames(tmp_path):
    calls = []

    class Done:
        returncode, stderr = 0, ""

    def run(cmd, **kw):
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"mp4")
        return Done()
    rec = SS.mp4(tmp_path / "frames", tmp_path / "clips" / "x.mp4", run=run)
    assert rec["path"].endswith("x.mp4") and (tmp_path / "clips" / "x.mp4").read_bytes() == b"mp4"
    cmd = calls[0]
    assert cmd[cmd.index("-c:v") + 1] == "libx264" and cmd[cmd.index("-pix_fmt") + 1] == "yuv420p"
    assert cmd[cmd.index("-framerate") + 1] == "24"


def test_clip_collage_has_a_row_per_clip_variant(tmp_path):
    rows = []
    for vid in ("B_shadow", "B_light"):
        for sid in SS.CLIP_SCENES:
            f = tmp_path / f"{sid}_{vid}.png"
            Image.new("RGB", (256, 144), (90, 120, 200)).save(f)
            rows.append({"scene": sid, "variant": vid, "frame": str(f), "times": {"steady_median_s": 3.0}})
    (tmp_path / "style_clips.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    path = SS.clip_collage(tmp_path, cell_w=320)
    with Image.open(path) as im:
        assert im.width == 360 + 2 * (320 + 12) + 12 and im.height == 70 + 2 * (180 + 12) + 12
