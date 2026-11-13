"""The pilot's three new environments (the creator, 2026-11-06 17:15 UTC, card 17:17): a castle courtyard with the commander and the scout
crossing it, a column marching on a dirt road, a night camp at a forest edge. Built clip-first like the room (every still holds only its
in_shot list, PR #148), from registered CC0 pieces, the registered cast and the terrain code; one still each, prompts from the cards, the
stills added to the vault's manifest without re-rendering the room. Offline: no Blender, no network."""
import json
import math

import pytest

from explainer_engine.assets import library as L
from explainer_engine.blender import pilot_stills as PS
from explainer_engine.blender import style as S
from explainer_engine.blender import terrain as TR
from explainer_engine.blender import world_kits as W
from explainer_engine.core.errors import ContractError

LAY = W.layouts()["layouts"]
ENVS = tuple(PS.ENV_LAYOUTS)
SHOT = {"pilot_courtyard": "courtyard_cross", "pilot_march": "march_side", "pilot_camp": "camp_fire"}


def test_the_three_environments_are_registered_with_one_still_each_and_the_looks_the_ci_renders():
    assert set(ENVS) == set(SHOT) and set(PS.ENV_ROLE) == set(SHOT.values())
    for lid, sid in SHOT.items():
        assert list(LAY[lid]["shots"]) == [sid]
        scene, look = PS.ENV_LAYOUTS[lid]
        S.look_tokens(look)   # the look id resolves (an unknown light preset or look raises)
    assert set(PS.all_cameras()) == set(PS.ROLE) | set(SHOT.values())
    assert all(c["size"] == [2560, 1440] for c in PS.all_cameras().values())
    assert [PS.layout_of(s) for s in ("room_two_shot", "courtyard_cross", "march_side", "camp_fire", "battle_f000_colour")] == [
        "pilot_room", "pilot_courtyard", "pilot_march", "pilot_camp", "battle"]
    with pytest.raises(ContractError):
        PS.layout_of("harbour_wide")


def test_the_environments_use_only_registered_cc0_pieces_and_the_registered_cast():
    lib = L.load()
    from explainer_engine.blender import characters as C
    chars, costumes = C.registry()["characters"], C.registry()["costumes"]
    for lid in ENVS:
        for p in W.placements(lid):
            if p["asset"]:
                assert L.get(p["asset"], lib=lib)["licence"]["status"] == "cc0", (lid, p["asset"])
        for name, char, costume, tint, xy, yaw, action, off in LAY[lid]["cast"]:
            assert char in chars and costume in costumes, (lid, name)
            assert action in ("Walk_Formal_Loop", "Sitting_Idle_Loop", "Sitting_Talking_Loop"), (lid, name)
        assert W.scene_set(lid)["objects"] or lid == "pilot_march"   # the march has only shapes, a wood and a cast


def test_every_still_holds_only_its_listed_cast_props_and_the_place(tmp_path):
    t = W.table()
    from tests.unit.test_world_kits import synthetic
    gltf, files = synthetic()
    glb = tmp_path / "x.glb"
    glb.write_bytes(W.pack_piece(gltf, files.get, 32)[0])
    for lid, sid in SHOT.items():
        objs, _ = W.expand(lid, {a["id"]: glb for a in t["assets"]}, repo=tmp_path, ground_textures=None)
        cast = [{"name": r[0]} for r in LAY[lid]["cast"]]
        listed = W.dressing(lid, sid)
        assert listed and all(isinstance(v, str) and v.strip() for v in listed.values())   # a reason for every entry
        room = W.structure(lid)
        assert not room & set(listed), lid   # a listed prop is never also "structure"
        names = {o["name"] for o in W.dress(objs + cast, lid, sid)}
        assert names - room <= set(listed) and set(listed) <= names, (lid, sorted(names - room - set(listed)), sorted(set(listed) - names))
        everything = {o["name"] for o in objs + cast}
        assert everything - names == set(), lid   # nothing is cut: the layouts hold no prop the clip does not use
    # the courtyard has no wagon, crates, barrel or lantern, the camp no tent, the march no cart: the clips do not use them
    assert not {"wagon", "crate_a", "crate_b", "barrel", "lantern"} & {p["name"] for p in W.placements("pilot_courtyard")}


def test_the_card_prompts_are_clean_say_each_tag_once_and_name_the_heroes():
    from explainer_engine.qa import style_prompt as SP
    for lid, sid in SHOT.items():
        spec = LAY[lid]
        p = PS.prompts(sid)
        q = p["qwen"].lower()
        assert q.startswith(SP.TRIGGER) and p["qwen_words"] <= PS.QWEN_MAX_WORDS, sid
        assert not [f for f in SP.check(q, sub_category=spec.get("sub_category")) if f["severity"] in ("FAIL", "REVIEW")], sid
        listed = set(W.dressing(lid, sid))
        for name, tag in spec["tags"].items():
            assert q.count(tag.lower()) <= 1, (sid, name)
            if q.count(tag.lower()):
                assert name in listed, (sid, name)
        assert p["ltx"].startswith(PS.VIDEO_SENTENCE) and p["ltx"].endswith("Static camera."), sid
        assert "camera" not in q.split("keep every place, size and pose.")[1], sid   # no camera words after the image list
    assert PS.prompts("courtyard_cross")["hero_refs"] == ["B_H1_front", "B_H2_front"]
    assert PS.prompts("camp_fire")["hero_refs"] == ["B_H1_front", "B_H2_front"]   # at most two hero sheets: three images, as the room's
    assert PS.prompts("march_side")["hero_refs"] == []
    assert "image 2 is the commander. image 3 is the scout." in PS.prompts("camp_fire")["qwen"].lower()
    assert "from left to right" in PS.prompts("march_side")["ltx"]
    # the three prompt styles differ only in the head, as in the room
    s1, s2, s3 = (PS.ltx_prompt("camp_fire", style=k) for k in ("S1", "S2", "S3"))
    assert s1 == PS.prompts("camp_fire")["ltx"] and s1.endswith(s3) and s2.endswith(s3) and s3.startswith("A campfire")


def _screen(cam, look, lens, p, aspect=16 / 9):
    """Where a point lands in the frame: x, y in -1..1 are inside (a pinhole camera, 36 mm sensor)."""
    dx, dy, dz = (look[i] - cam[i] for i in range(3))
    yaw, pitch = math.atan2(dx, dy), math.atan2(dz, math.hypot(dx, dy))
    px, py, pz = (p[i] - cam[i] for i in range(3))
    a = (math.atan2(px, py) - yaw + math.pi) % (2 * math.pi) - math.pi
    el = math.atan2(pz, math.hypot(px, py)) - pitch
    hf = 2 * math.atan(18 / lens)
    vf = 2 * math.atan(math.tan(hf / 2) / aspect)
    return math.tan(a) / math.tan(hf / 2), math.tan(el) / math.tan(vf / 2)


def test_everyone_in_the_cast_is_inside_the_frame_and_not_cut_by_its_edge():
    for lid, sid in SHOT.items():
        c0, _, a0, _, lens, _ = LAY[lid]["shots"][sid]
        for name, char, costume, tint, xy, yaw, action, off in LAY[lid]["cast"]:
            for z in (0.1, 1.0, 1.7):   # feet, chest, head: the whole figure is in the frame
                x, y = _screen(c0, a0, lens, (xy[0], xy[1], z))
                assert abs(x) < 0.95 and abs(y) < 0.95, (sid, name, z, round(x, 2), round(y, 2))


def _front(yaw_deg):
    """The direction a UBC character faces at this yaw (it faces -Y at yaw 0, the room test's rule)."""
    return math.sin(math.radians(yaw_deg)), -math.cos(math.radians(yaw_deg))


def test_the_heroes_cross_towards_the_gate_the_column_marches_left_to_right_and_the_two_by_the_fire_face_each_other():
    cast = {r[0]: r for r in LAY["pilot_courtyard"]["cast"]}
    gate = next(p for p in W.placements("pilot_courtyard") if p["name"] == "wall_north_1")
    assert gate["asset"].endswith("door_round")   # the door module of the north wall the heroes walk towards
    for who in ("commander", "scout"):
        fx, fy = _front(cast[who][5])
        assert fx == pytest.approx(-1.0) and abs(fy) < 1e-9   # both walk to -X, the gate's side of the frame (x = -1 of the wall)
        assert cast[who][4][0] > gate["pos"][0] and cast[who][6] == "Walk_Formal_Loop"
    assert cast["scout"][4][0] > cast["commander"][4][0]   # the scout follows a step behind
    march = LAY["pilot_march"]["cast"]
    assert len(march) == 14 and all(_front(r[5])[0] == pytest.approx(1.0) and r[6] == "Walk_Formal_Loop" for r in march)
    assert len({tuple(r[4]) for r in march}) == 14 and len({r[7] for r in march}) > 6   # nobody steps in the same place or the same cycle
    near = sorted(r[4][0] for r in march if r[4][1] < 9)
    assert all(b - a >= 1.9 for a, b in zip(near, near[1:]))   # no two share a stride
    camp = {r[0]: r for r in LAY["pilot_camp"]["cast"]}
    fire = next(b for b in LAY["pilot_camp"]["blocks"] if b.get("name") == "fire")
    for who, other in (("commander", "scout"), ("scout", "commander")):
        (x0, y0), (x1, y1) = camp[who][4], camp[other][4]
        fx, fy = _front(camp[who][5])
        d = math.hypot(x1 - x0, y1 - y0)
        assert fx * (x1 - x0) / d + fy * (y1 - y0) / d > 0.99, who   # each faces the other, across the fire
        assert camp[who][6].startswith("Sitting")
    assert abs((camp["commander"][4][0] + camp["scout"][4][0]) / 2 - fire["pos"][0]) < 1e-6   # the fire is midway between them
    assert abs(camp["commander"][4][1] - fire["pos"][1]) < 0.5


def test_the_seats_stand_under_the_seated_and_the_road_is_level_under_the_soldiers():
    ps = {p["name"]: p for p in W.placements("pilot_camp")}
    for stool, who in (("stool_a", "commander"), ("stool_b", "scout")):
        row = next(r for r in LAY["pilot_camp"]["cast"] if r[0] == who)
        assert ps[stool]["pos"][:2] == row[4] and ps[stool]["pos"][2] == 0.0   # the figure's root is the seat's origin, as the room's chairs
    T = TR.Terrain(LAY["pilot_camp"]["terrain"])
    assert all(T.height(*ps[s]["pos"][:2]) == 0.0 for s in ("stool_a", "stool_b")) and T.height(0.0, 6.0) == 0.0   # the clearing is level
    M = TR.Terrain(LAY["pilot_march"]["terrain"])
    for r in LAY["pilot_march"]["cast"]:
        x, y = r[4]
        assert abs(M.height(x, y)) < 0.05, r[0]   # a level strip along the road: the figures' feet meet the ground
        assert M.road_dist(x, y) < LAY["pilot_march"]["terrain"]["road_half"], r[0]   # and they stay on the road
    trees = [p for p in W.placements("pilot_march") if p["role"] == "scatter"]
    assert len(trees) == 48 and all(M.road_dist(p["pos"][0], p["pos"][1]) >= 4.0 for p in trees)   # the wood stands off the road
    assert all(p["pos"][1] >= 16 for p in trees)   # behind the column, never between it and the camera


def test_the_fire_is_a_light_independent_flame_with_its_own_light_and_the_night_has_its_own_sky():
    g = W.raw_graph("flame")
    ids = {n["id"] for n in g["nodes"]}
    assert {"emit", "out", "heat"} <= ids and all(link[0] in ids and link[2] in ids for link in g["links"])
    assert not [n for n in g["nodes"] if "Principled" in n["type"]]   # outside the toon path, never a Principled BSDF
    blocks = {b["name"]: b for b in LAY["pilot_camp"]["blocks"]}
    assert blocks["fire"]["raw"] == blocks["fire_core"]["raw"] == "flame"
    lights = {n: b["light"] for n, b in blocks.items() if b["type"] == "light"}
    assert lights["fire_glow"]["shadow"] is True and lights["fire_glow"]["color"][0] > lights["fire_glow"]["color"][2]   # warm, casts shadows
    lift = lights["fire_lift"]
    assert lift["shadow"] is False and abs(blocks["fire_glow"]["pos"][1] - blocks["fire"]["pos"][1]) < 0.2   # at the flame, not off in the wood
    pr = S.light_presets()["night_camp"]
    assert pr["sky"]["top"][2] < 0.1 and max(pr["sky"]["tint"]) < 0.25   # a night sky, not the day HDRI's
    assert pr["key"]["energy"] < S.light_presets()["night_moon"]["key"]["energy"]   # dimmer than the generic night: the fire is the light
    assert PS.ENV_LAYOUTS["pilot_camp"][1].endswith("@night_camp")


def _poc_dir(tmp, lid, sid, colour):
    from PIL import Image
    d = tmp / lid
    (d / "frames").mkdir(parents=True)
    Image.new("RGB", (64, 36), colour).save(d / "frames" / f"{sid}_v.png")
    (d / "looks.json").write_text(json.dumps({"rows": [{"scene": sid, "variant": PS.ENV_LAYOUTS[lid][1], "engine": "eevee",
                                                        "seconds_per_frame": 50.0, "frame_rel": f"frames/{sid}_v.png"}]}), encoding="utf-8")
    return d


def _base(tmp):
    from PIL import Image
    shots = {}
    for sid, c in (("room_two_shot", (200, 120, 60)), ("room_close_host", (180, 110, 70)), ("battle_f000_colour", (90, 120, 160))):
        Image.new("RGB", (64, 36), c).save(tmp / f"{sid}.png")
        shots[sid] = {"file": f"{sid}.png", "sha256": "a" * 64}
    return {"schema": PS.SCHEMA, "layout": "pilot_room_layout.json", "shots": shots, "hf_prefix": PS.HF_PREFIX}


def test_extend_adds_the_environments_to_the_vaults_manifest_and_leaves_the_base_untouched(tmp_path):
    base = _base(tmp_path)
    envs = {lid: _poc_dir(tmp_path, lid, sid, (30 * i + 40, 90, 60)) for i, (lid, sid) in enumerate(SHOT.items())}
    out = tmp_path / "out"
    doc = PS.extend(base, envs, out)
    assert set(doc["shots"]) == set(base["shots"]) | set(SHOT.values()) and doc["carried"] == sorted(base["shots"])
    for sid in base["shots"]:
        assert doc["shots"][sid] == base["shots"][sid]   # same file, same hash: nothing re-rendered
    for lid, sid in SHOT.items():
        row = doc["shots"][sid]
        assert row["layout"] == lid and row["in_shot"] == W.dressing(lid, sid) and row["prompts"]["qwen"] == PS.prompts(sid)["qwen"]
        assert len(row["sha256"]) == 64 and (out / row["file"]).is_file()
        assert json.loads((out / doc["layouts"][lid]).read_text())["layout_id"] == lid
    assert json.loads((out / "pilot_stills.json").read_text()) == doc
    assert not (out / "room_two_shot.png").exists()   # the base's files are on the vault, not copied
    with pytest.raises(ContractError, match="already in the base"):
        PS.extend(doc, envs, tmp_path / "out2")
    with pytest.raises(ContractError, match="not a pilot environment"):
        PS.extend(base, {"hill_castle": envs["pilot_camp"]}, tmp_path / "out3")
    gone = dict(envs)
    (gone["pilot_march"] / "looks.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    with pytest.raises(ContractError, match="without a still"):
        PS.extend(base, gone, tmp_path / "out4")


def test_upload_sends_only_the_new_files_and_checks_their_hashes(tmp_path):
    base = _base(tmp_path)
    envs = {lid: _poc_dir(tmp_path, lid, sid, (30 * i + 40, 90, 60)) for i, (lid, sid) in enumerate(SHOT.items())}
    out = tmp_path / "out"
    PS.extend(base, envs, out)
    sent = {}

    class Vault:
        def upload_many(self, pairs, message):
            sent.update({r: loc for loc, r in pairs})

        def listing(self, prefix):
            from explainer_engine import vault as V
            return {r: {"sha256": V.file_hashes(loc)[0]} for r, loc in sent.items()}
    got = PS.upload(out, vault=Vault())
    names = sorted(r.rsplit("/", 1)[1] for r in got)
    assert names == sorted([*(f"{s}.png" for s in SHOT.values()), *(f"{lid}_layout.json" for lid in ENVS), "pilot_stills.json"])
    assert all(r.startswith(PS.HF_PREFIX + "/") for r in got)


def test_the_contact_sheet_has_one_tile_per_starting_still_labelled_with_its_clips(tmp_path):
    from PIL import Image
    from explainer_engine.training.pods.p15 import build as B
    base = _base(tmp_path)
    envs = {lid: _poc_dir(tmp_path, lid, sid, (30 * i + 40, 90, 60)) for i, (lid, sid) in enumerate(SHOT.items())}
    doc = PS.extend(base, envs, tmp_path / "out")
    labels = PS.clip_labels(B.CLIPS)
    assert labels["room_two_shot"] == "c1 S1 · c2 S2 · c3 S3" and labels["march_side"] == "c5 S1" and labels["courtyard_cross"] == "c6 S2"
    assert labels["camp_fire"] == "c8 S2" and len(labels) == 6 and sum(len(v.split(" · ")) for v in labels.values()) == 8   # 8 clips, 6 stills
    f = PS.sheet(doc, [tmp_path / "out", tmp_path], labels, tmp_path / "sheet.png", tile=(160, 90))
    im = Image.open(f)
    assert im.size[0] > 3 * 160 and im.size[1] > 2 * 90
    with pytest.raises(ContractError, match="is in none of"):
        PS.sheet(doc, [tmp_path / "out"], labels, tmp_path / "x.png", tile=(160, 90))
