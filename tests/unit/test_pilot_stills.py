"""The pilot's Blender stills (the creator, 2026-11-06 15:25 UTC): the furnished room layout from the libraries, its cameras, the
own-material pieces and the stills manifest. Offline: no Blender, no network."""
import json
import math
from pathlib import Path

import pytest

from explainer_engine.assets import library as L
from explainer_engine.blender import pilot_stills as PS
from explainer_engine.blender import world_kits as W
from explainer_engine.core.errors import ContractError

ROOM = W.layouts()["layouts"]["pilot_room"]


def test_the_room_is_closed_furnished_and_built_only_from_registered_cc0_pieces():
    ps = {p["name"]: p for p in W.placements("pilot_room")}
    walls = [n for n in ps if ps[n]["role"] == "wall"]
    assert len(walls) == 2 * 4 + 2 * 3   # four sides, no open side: every reverse angle sees a wall
    for need in ("clock", "mantel_clock", "table", "chair_n", "chair_s", "bookshelf", "stove", "cabinet", "jug", "candle"):
        assert need in ps, need
    lib = L.load()
    for p in ps.values():
        if p["asset"]:
            rec = L.get(p["asset"], lib=lib)
            assert rec["licence"]["status"] == "cc0", p["asset"]
    assert ps["mantel_clock"]["pos"][2] > 1.0 and ps["candle"]["pos"][2] == pytest.approx(0.8)   # on the drawers, on the table top
    assert W.scene_set("pilot_room")["objects"]


def test_the_new_pieces_are_poly_haven_rows_with_their_download_date_and_no_id_clash():
    t = W.table()
    new = [a for a in t["assets"] if "pilot_room" in a["tags"]]
    assert len(new) == 18 and all(a["source"] == "polyhaven" for a in new)
    for a in new:
        assert t["polyhaven"][a["slug"]]["downloaded_on"] == "2026-11-06" and t["polyhaven"][a["slug"]]["files_md5"]
    # the style sheets' Wooden Table 02 (.blend) keeps its id: the kit's glb is a separate record
    lib = L.load()
    assert L.get("model.ph_wooden_table_02", lib=lib)["file"].endswith(".blend")
    assert L.get("model.ph_plain_wooden_table_02", lib=lib)["file"].endswith(".glb")


def test_every_character_faces_who_they_talk_to():
    cast = {r[0]: r for r in ROOM["cast"]}
    for a, b in (("host", "guest"), ("guest", "host")):
        (x0, y0), (x1, y1), yaw = cast[a][4], cast[b][4], math.radians(cast[a][5])
        front = (math.sin(yaw), -math.cos(yaw))   # a UBC character faces -Y at yaw 0
        d = math.hypot(x1 - x0, y1 - y0)
        assert front[0] * (x1 - x0) / d + front[1] * (y1 - y0) / d > 0.99, a


def test_the_over_the_shoulder_pair_keeps_one_side_of_the_line_and_every_camera_is_inside_the_room():
    cams = PS.cameras()
    assert set(cams) == set(PS.ROLE) and all(c["size"] == [2560, 1440] for c in cams.values())
    cast = {r[0]: r[4] for r in ROOM["cast"]}
    (hx, hy), (gx, gy) = cast["host"], cast["guest"]

    def side(p):
        return (gx - hx) * (p[1] - hy) - (gy - hy) * (p[0] - hx)
    sides = {sid: side(cams[sid]["location"]) > 0 for sid in ("room_two_shot", "room_close_host", "room_close_guest")}
    assert len(set(sides.values())) == 1, sides   # the 180-degree rule: all three on one side of the host-guest line
    for c in cams.values():
        x, y, z = c["location"]
        assert -3.8 < x < 3.8 and -2.8 < y < 2.8 and 0 < z < 3.1   # inside the walls' inner faces and under the ceiling


def test_a_moving_shot_is_refused_as_a_pilot_still():
    bad = json.loads(json.dumps(ROOM))
    bad["shots"]["room_two_shot"][1] = [0, 0, 1]
    with pytest.raises(ContractError):
        PS.cameras(bad)


def test_own_material_pieces_keep_their_gltf_materials(tmp_path):
    t = W.table()
    own = {a["id"] for a in t["assets"] if a.get("own_materials")}
    assert own == {"model.ph_wall_clock"}   # kept as a row; the pilot uses the clocks with their glass dropped instead
    drop = {a["slug"]: a["drop_materials"] for a in t["assets"] if a.get("drop_materials")}
    assert drop == {"vintage_grandfather_clock_01": ["vintage_grandfather_clock_01_glass"], "mantel_clock_01": ["mantel_clock_01_glass"]}
    glb = tmp_path / "x.glb"
    from tests.unit.test_world_kits import synthetic
    gltf, files = synthetic()
    glb.write_bytes(W.pack_piece(gltf, files.get, 32)[0])
    objs, mats = W.expand("pilot_room", {a["id"]: glb for a in t["assets"]}, repo=tmp_path, ground_textures=None)
    by = {o["name"]: o for o in objs}
    assert by["table"]["material"] in mats
    assert by["mantel_clock"]["gltf"].get("drop_materials") == ["mantel_clock_01_glass"]   # the toon glass hid the dial (r3)


def test_the_manifest_names_every_still_with_its_hash_and_seconds(tmp_path):
    room = tmp_path / "room"
    (room / "frames").mkdir(parents=True)
    rows = []
    for sid in PS.cameras():
        f = room / "frames" / f"{sid}_v01.png"
        f.write_bytes(sid.encode())
        rows.append({"scene": sid, "variant": "v01", "engine": "eevee", "seconds_per_frame": 40.0, "frame_rel": f"frames/{f.name}"})
    (room / "looks.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    bat = tmp_path / "bat" / "battle"
    for kind in ("colour", "depth"):
        (bat / kind / "frames").mkdir(parents=True)
        (bat / kind / "frames" / "frame_000000.png").write_bytes(kind.encode())
    (bat / "layout_manifest.json").write_text(json.dumps({"plan": {"size": [1920, 1088]}, "passes": {
        k: {"engine": "eevee", "seconds_per_frame": 300.0, "wall_seconds": 600.0, "frame_sha256": {"frame_000000.png": "x"}}
        for k in ("colour", "depth")}}), encoding="utf-8")
    doc = PS.manifest(room, tmp_path / "bat", tmp_path / "out")
    assert set(doc["shots"]) == set(PS.cameras()) | {"battle_f000_colour", "battle_f000_depth"}
    assert all((tmp_path / "out" / s["file"]).exists() and len(s["sha256"]) == 64 for s in doc["shots"].values())
    assert doc["hf_prefix"] == "route_test_2026-11/pilot/blender"
    assert json.loads((tmp_path / "out" / "pilot_room_layout.json").read_text())["layout_id"] == "pilot_room"
    rows.pop()
    (room / "looks.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    with pytest.raises(ContractError, match="without a still"):
        PS.manifest(room, None, tmp_path / "out2")


# the creator, 2026-11-06 15:53 UTC: every Blender still is the first frame of a planned LTX clip; it holds only the characters and
# props that act in that clip or set its place (each with its reason), plus the room itself
def test_every_still_holds_only_its_listed_cast_and_props(tmp_path):
    t = W.table()
    glb = tmp_path / "x.glb"
    from tests.unit.test_world_kits import synthetic
    gltf, files = synthetic()
    glb.write_bytes(W.pack_piece(gltf, files.get, 32)[0])
    objs, _ = W.expand("pilot_room", {a["id"]: glb for a in t["assets"]}, repo=tmp_path, ground_textures=None)
    cast = [{"name": r[0]} for r in ROOM["cast"]]
    room = W.structure("pilot_room")
    assert {"floor", "ceiling", "door"} <= room and not room & {"table", "clock", "host"}
    for sid in ROOM["shots"]:
        listed = W.dressing("pilot_room", sid)
        assert listed and all(isinstance(v, str) and v.strip() for v in listed.values()), sid   # a reason for every entry
        names = {o["name"] for o in W.dress(objs + cast, "pilot_room", sid)}
        assert names - room <= set(listed), (sid, sorted(names - room - set(listed)))
        assert set(listed) <= names, sid
    two = {o["name"] for o in W.dress(objs + cast, "pilot_room", "room_two_shot")}
    assert "clock" not in two and "stove" not in two and "elder" not in two   # not in that clip, so not in its still


def test_a_prop_that_is_not_in_the_room_or_has_no_reason_is_refused():
    bad = json.loads(json.dumps(W.layouts()))
    bad["layouts"]["pilot_room"]["in_shot"]["room_two_shot"]["wall_tv"] = "nothing"
    with pytest.raises(Exception, match="wall_tv"):
        W.dressing("pilot_room", "room_two_shot", doc=bad)
    bad = json.loads(json.dumps(W.layouts()))
    bad["layouts"]["pilot_room"]["in_shot"]["room_two_shot"]["table"] = " "
    with pytest.raises(Exception):
        W.dressing("pilot_room", "room_two_shot", doc=bad)


# Fable, 2026-11-06 15:57 UTC: each still's Qwen prompt and its LTX prompt come from the shot card, never by hand
def test_every_shot_card_gives_a_clean_qwen_prompt_and_an_ltx_prompt():
    from explainer_engine.qa import style_prompt as SP
    tags = ROOM["tags"]
    for sid in ROOM["shots"]:
        p = PS.prompts(sid)
        q = p["qwen"].lower()
        assert q.startswith(SP.TRIGGER) and len(q.split()) <= PS.QWEN_MAX_WORDS, sid
        assert not [f for f in SP.check(q) if f["severity"] in ("FAIL", "REVIEW")], sid
        listed = set(W.dressing("pilot_room", sid))
        for name, tag in tags.items():
            n = q.count(tag.lower())
            assert n <= 1, (sid, name)   # each tag said once
            if n:
                assert name in listed, (sid, name)   # only what is in the still
        assert p["ltx"].startswith(PS.VIDEO_SENTENCE) and p["ltx"].endswith("Static camera."), sid
    two = PS.prompts("room_two_shot")
    q = two["qwen"].lower()
    assert tags["host"] in q and tags["guest"] in q and "clock" not in q
    assert two["hero_refs"] == ["B_H1_front", "B_H2_front"] and "image 2 is the commander. image 3 is the scout." in q
    bat = PS.prompts("battle_f000_colour")   # the soldiers' card: a crowd prompt stays under the clone limit (CROWD_REVIEW_WORDS)
    assert not [f for f in SP.check(bat["qwen"], sub_category="V1") if f["severity"] in ("FAIL", "REVIEW")]
    assert bat["hero_refs"] == [] and bat["ltx"].startswith(PS.VIDEO_SENTENCE)


def test_a_card_that_names_a_prop_outside_the_shot_is_refused():
    bad = json.loads(json.dumps(ROOM))
    bad["cards"]["room_two_shot"]["start"] += " under {clock}"
    with pytest.raises(ContractError, match="clock"):
        PS.prompts("room_two_shot", bad)
    bad = json.loads(json.dumps(ROOM))
    bad["cards"]["room_two_shot"]["start"] = "{host} looks at {host}"
    with pytest.raises(ContractError, match="twice"):
        PS.prompts("room_two_shot", bad)


# P1 (the 60 s pilot): three more soldiers stills, two of them from named static cameras
def test_the_extra_battle_cards_are_clean_one_per_camera_and_under_the_clone_limit():
    from explainer_engine.qa import style_prompt as SP
    from explainer_engine.blender import layout_passes as LP
    assert set(LP.BATTLE_CAMERAS) == {"wide_high", "front_mid"}
    for sid, key in (("battle_f200_colour", "f200"), ("battle_wide_high_f096_colour", "wide_high"),
                     ("battle_front_mid_f100_colour", "front_mid")):
        assert PS.battle_card(sid) is PS.BATTLE_CARDS[key]
        p = PS.prompts(sid)
        assert p["qwen_words"] <= PS.QWEN_MAX_WORDS and p["hero_refs"] == []
        assert not [f for f in SP.check(p["qwen"], sub_category="V1") if f["severity"] in ("FAIL", "REVIEW")], sid
        assert p["ltx"].startswith(PS.VIDEO_SENTENCE) and p["ltx"].endswith("Static camera."), sid
        q = p["qwen"].lower()
        for name, tag in PS.BATTLE_CARDS[key]["tags"].items():
            assert q.count(tag.lower()) <= 1, (sid, name)
    assert PS.battle_card("battle_f000_colour") is PS.BATTLE
    with pytest.raises(ContractError, match="not a battle"):
        PS.battle_card("room_two_shot")


def test_the_extra_manifest_keeps_the_pinned_one_and_hashes_the_new_stills(tmp_path):
    def render(name, frames):
        d = tmp_path / name / "battle"
        (d / "colour" / "frames").mkdir(parents=True)
        for i in frames:
            (d / "colour" / "frames" / f"frame_{i:06d}.png").write_bytes(f"{name}{i}".encode())
        (d / "layout_manifest.json").write_text(json.dumps({"camera": name, "passes": {"colour": {
            "engine": "eevee", "seconds_per_frame": 250.0, "wall_seconds": 700.0,
            "frame_sha256": {f"frame_{i:06d}.png": "x" for i in frames}}}}), encoding="utf-8")
        return tmp_path / name
    dirs = {"wide_high": render("wide_high", [96, 112]), "front_mid": render("front_mid", [100, 112])}
    doc = PS.extra_manifest(dirs, {"wide_high": [96], "front_mid": [100]}, tmp_path / "out")
    assert set(doc["shots"]) == {"battle_wide_high_f096_colour", "battle_front_mid_f100_colour"}
    assert all((tmp_path / "out" / s["file"]).exists() and len(s["sha256"]) == 64 and s["prompts"]["qwen"] for s in doc["shots"].values())
    assert (tmp_path / "out" / PS.EXTRA_FILE).exists() and not (tmp_path / "out" / "pilot_stills.json").exists()
    with pytest.raises(ContractError, match="was not rendered"):
        PS.extra_manifest(dirs, {"wide_high": [50], "front_mid": [100]}, tmp_path / "out2")
    with pytest.raises(ContractError, match="rendered with camera"):
        PS.extra_manifest({"wide_high": dirs["front_mid"]}, {"wide_high": [100]}, tmp_path / "out3")


def test_a_named_battle_camera_reaches_the_crowd_plan():
    from explainer_engine.blender import crowd as CR
    from explainer_engine.blender import layout_passes as LP
    import inspect
    assert "camera_override" in inspect.signature(CR.scene).parameters
    for cam in LP.BATTLE_CAMERAS.values():
        assert {"location", "look_at", "lens_mm", "focus_distance_m"} <= set(cam)
    with pytest.raises(ContractError, match="unknown battle camera"):
        LP.battle_scene(24, camera="nope")
