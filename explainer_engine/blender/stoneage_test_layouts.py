"""The stone-age pilot's approach test (the creator, 2026-11-07 12:48 UTC): three scenes built twice, to learn which way of
building a place gives Qwen the better start before the rule is written.

* **block**: every place is flat-toned primitives (boxes, spheres, cylinders, cones, a plain terrain): the blockout.
* **cc0**: the same scenes with the place built from CC0 pieces (Poly Haven rock faces, boulders, a fire pit, trunks and
  stumps on a textured terrain).

What differs between the two is only the place. The story props (the painted wall, the handprints, the fire, the mammoths, the huts,
the drum) and the cast and the camera are identical in both, so a difference in the picture comes from the way the place is built.
Scenes: ``cave`` (E3-A of VISUAL_SCRIPT_v2: the cave, a hearth, the painted wall, Ura, Marcus, three kneeling hunters), ``ice``
(E2-A: a snow plain, three mammoths, Marcus seen from behind) and ``camp`` (E4-A: the camp ring at night, huts, a fire, Marcus
sitting, Ura and two torch-bearers).

    python -m explainer_engine.blender.stoneage_test_layouts write    # adds the six ``sa_*`` layouts to world_layouts.json
    python -m explainer_engine.blender.stoneage_test_layouts list
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYOUTS = HERE / "world_layouts.json"
SCENES = ("cave", "ice", "camp")
WAYS = ("block", "flat3")   # KP-56 (creator 14:55 UTC, Argon Part 4): cc0 lost on the 6 photos and stays only as the record of that test
PRESET = {"cave": "interior_hearth", "ice": "overcast_day", "camp": "night_camp"}   # light_presets.json
SHOT = {"cave": "sa_cave_wide", "ice": "sa_ice_wide", "camp": "sa_camp_wide"}
# the creator 2026-11-07 15:04 UTC, test A (KP-57): the same place from two more angles, every named figure still in frame
ANGLES = {"cave": {"side": [[5.6, 1.6, 1.7], None, [-1.2, 6.8, 1.4], None, 20, 1], "low": [[-5.4, 1.2, 1.3], None, [1.6, 6.4, 1.6], None, 20, 1]},
          "ice": {"side": [[-10.0, -1.0, 1.5], None, [9.0, 18.0, 2.0], None, 20, 1], "low": [[0.6, -1.6, 0.9], None, [3.0, 22.0, 2.4], None, 26, 1]},
          "camp": {"side": [[6.8, 0.4, 1.7], None, [-1.6, 8.4, 1.4], None, 22, 1], "low": [[-6.8, 0.6, 1.4], None, [1.6, 8.2, 1.6], None, 22, 1]}}
PLACE = {"cave": "a dark ice-age cave", "ice": "a wide snow plain at dusk in the ice age",
         "camp": "an ice-age camp in a night snowstorm"}
LIGHT = {"cave": "orange firelight", "ice": "a low cold blue dusk glow", "camp": "firelight"}
# the shot cards: tags (two visible traits each, KP-15) and the clip's start / motion / settle (prompts() composes the Qwen and LTX prompts)
MARCUS = "the young courier in a grey hoodie and white sneakers"
URA = "the old sorcerer in a deer-antler mask and a fur cloak"
TAGS = {"cave": {"ura": URA, "marcus": MARCUS, "hunter_a": "the hunter in grey fur", "hunter_b": "the hunter in brown fur",
                 "hunter_c": "the hunter in spotted fur", "hearth_flame": "a fire",
                 "paint_panel": "a wall painted with gold towers and red handprints"},
        "ice": {"marcus": MARCUS, "mammoth_0_body": "the big woolly mammoth with long curved tusks",
                "mammoth_1_body": "the woolly mammoth", "mammoth_2_body": "the small woolly mammoth"},
        "camp": {"marcus": MARCUS, "ura": URA, "torch_a": "the hunter in grey fur with a torch",
                 "torch_b": "the hunter in brown fur with a torch", "camp_flame": "a campfire", "log_seat": "a log",
                 "hut_0_wall": "round huts with pointed roofs"}}
CARDS = {"cave": {"start": "{ura} speaks by {hearth_flame}, {marcus} stares at {paint_panel}, {hunter_a}, {hunter_b} and {hunter_c} kneel",
                  "motion": "the fire flickers and {ura} lifts one hand", "settle": "everyone stays in frame, breathing and blinking", "refs": []},
         "ice": {"start": "{mammoth_0_body}, {mammoth_1_body} and {mammoth_2_body} walk across the snow while {marcus} stands with his back to us",
                 "motion": "the mammoths stride heavily and {marcus} flinches", "settle": "the herd keeps walking and everyone stays in frame", "refs": []},
         "camp": {"start": "{marcus} sits on {log_seat} by {camp_flame}, {ura} speaks, {torch_a} and {torch_b} stand before {hut_0_wall}",
                  "motion": "the flames flicker and {ura} lifts one hand", "settle": "everyone stays in frame, breathing and blinking", "refs": []}}
SUBJECTS = {"cave": ("ura", "marcus", "hunter_a", "hunter_b", "hunter_c"), "ice": ("marcus", "mammoth_0_body", "mammoth_1_body", "mammoth_2_body"),
            "camp": ("marcus", "ura", "torch_a", "torch_b")}   # KP-50: the named figures and animals that get a screen side
COUNTED = {"camp": {"hut_0_wall": "hut_"}}   # KP-51: tag key -> name prefix of the set pieces it counts
NUMBERS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
SENSOR_MM = 36.0


PRIM = {"cube": {"size": 1}, "uv_sphere": {"radius": 0.5, "segments": 24, "ring_count": 12},
        "cylinder": {"radius": 0.5, "depth": 1, "vertices": 20}, "cone": {"radius1": 0.5, "radius2": 0, "depth": 1, "vertices": 20},
        "plane": {"size": 1}}


def shape(name, add, pos, dims, colour, yaw=0.0, pitch=0.0, texture=None, tile=1.0):
    b = {"type": "shape", "name": name, "add": add, "params": dict(PRIM[add]), "pos": [round(v, 3) for v in pos],
         "scale": [round(v, 3) for v in dims], "colour": colour}
    if yaw:
        b["yaw_deg"] = yaw
    if pitch:
        b["pitch"] = pitch
    if texture:
        b["texture"], b["tile"] = texture, tile
    return b


def dress(b):
    """KP-56 flat3 dressing: an unnamed flat-coloured shape that KP-53's clash check watches like a CC0 piece."""
    b["dress"] = True
    return b


def flat_tooth(name, x, y, h, w, colour, down=False, top=0.0):
    """A jagged rock tooth (stalagmite, or a stalactite hanging from ``top`` when ``down``): a cone of 5 sides, flat colour."""
    b = shape(name, "cone", [x, y, (top - h / 2) if down else h / 2], [w, w * 0.8, h], colour, yaw=17.0 * (x + y), pitch=180.0 if down else 0.0)
    b["params"] = dict(b["params"], vertices=5)
    return dress(b)


def textured(blocks: list) -> list[str]:
    """KP-56: CC0 meshes and texture maps in a still (none allowed in a Qwen way)."""
    return [b["name"] for b in blocks if b.get("type") == "piece" or b.get("texture")]


def piece(name, asset, pos, yaw=0.0, scale=1.0):
    return {"type": "piece", "name": name, "asset": asset, "pos": [round(v, 3) for v in pos], "yaw_deg": yaw, "scale": scale}


def lamp(name, pos, energy, colour, radius=0.2, shadow=True):
    return {"type": "light", "name": name, "pos": pos,
            "light": {"type": "POINT", "energy": energy, "color": colour, "radius_m": radius, "shadow": shadow}}


def mammoth(tag, x, y, yaw, big=1.0):
    """A mammoth of primitives (the same in both ways): body, hump, head, trunk, two tusks, four legs."""
    import math
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def at(dx, dy, dz):   # local (right, forward, up) -> world
        return [x + (dx * c - dy * s) * big, y + (dx * s + dy * c) * big, dz * big]
    fur, dark, ivory = "#5A3E2B", "#47301F", "#E6DCC2"
    out = [shape(f"{tag}_body", "uv_sphere", at(0, 0, 2.0), [2.3 * big, 4.0 * big, 2.4 * big], fur, yaw),
           shape(f"{tag}_hump", "uv_sphere", at(0, 0.7, 3.0), [1.7 * big, 1.9 * big, 1.5 * big], dark, yaw),
           shape(f"{tag}_head", "uv_sphere", at(0, 2.0, 2.2), [1.6 * big, 1.6 * big, 1.8 * big], fur, yaw),
           shape(f"{tag}_trunk", "cylinder", at(0, 2.9, 1.3), [0.45 * big, 0.45 * big, 2.0 * big], dark, yaw, pitch=20.0)]
    for k, sx in enumerate((-0.55, 0.55)):
        out.append(shape(f"{tag}_tusk_{k}", "cone", at(sx, 3.0, 1.5), [0.2 * big, 0.2 * big, 2.0 * big], ivory, yaw + (8 if sx > 0 else -8), pitch=-60.0))
    for k, (lx, ly) in enumerate(((-0.8, 1.2), (0.8, 1.2), (-0.8, -1.2), (0.8, -1.2))):
        out.append(shape(f"{tag}_leg_{k}", "cylinder", at(lx, ly, 0.9), [0.7 * big, 0.7 * big, 1.8 * big], dark, yaw))
    return out


def hut(tag, x, y, r=1.6, h=2.2, yaw=0.0):
    return [shape(f"{tag}_wall", "cylinder", [x, y, h * 0.3], [r * 2, r * 2, h * 0.6], "#7A5A3C", yaw),
            shape(f"{tag}_roof", "cone", [x, y, h * 0.6 + h * 0.5], [r * 2.3, r * 2.3, h], "#5E452E", yaw)]


def fire(tag, x, y, z=0.0, big=1.0):
    return [shape(f"{tag}_flame", "cone", [x, y, z + 0.55 * big], [0.55 * big, 0.55 * big, 1.1 * big], "#FFB347"),
            shape(f"{tag}_core", "cone", [x, y, z + 0.4 * big], [0.28 * big, 0.28 * big, 0.8 * big], "#FFF1B8"),
            shape(f"{tag}_log_a", "cylinder", [x, y, z + 0.12], [0.16, 0.16, 0.95], "#4A3524", 35.0, pitch=90.0),
            shape(f"{tag}_log_b", "cylinder", [x, y, z + 0.2], [0.16, 0.16, 0.95], "#3E2C1E", -40.0, pitch=90.0),
            lamp(f"{tag}_glow", [x, y, z + 0.8], 420.0, [1.0, 0.55, 0.24], 0.25)]


GOLD, RED = "#D8A93A", "#A63A22"


def painted_wall(x0, y, z0):
    """The wall of the story, one build for both ways: a pale panel, a gold skyline, a row of red handprints and one empty place."""
    out = [shape("paint_panel", "cube", [x0, y, z0 + 1.3], [7.0, 0.12, 2.6], "#8A7656")]
    heights = [1.1, 1.8, 1.3, 2.1, 1.5, 1.9, 1.2]
    for k, h in enumerate(heights):
        out.append(shape(f"sky_{k}", "cube", [x0 - 2.7 + k * 0.9, y - 0.08, z0 + 0.25 + h / 2], [0.55, 0.05, h], GOLD))
    for k, hx in enumerate((-2.9, -2.3, -1.7, -1.1, -0.5, 0.1)):
        out.append(shape(f"hand_{k}", "cube", [x0 + hx, y - 0.08, z0 + 0.5], [0.28, 0.05, 0.34], RED))
    out.append(shape("hand_ura", "cube", [x0 + 0.9, y - 0.08, z0 + 0.5], [0.36, 0.05, 0.42], "#C0452A"))
    return out


def _cave(way):
    cast = [["ura", "ink_test_m", "costume.mco_male_peasant", "faction_b", [-1.0, 5.6], 25.0, "Idle_Talking_Loop", 0],
            ["marcus", "ink_test_m2", "costume.mco_male_ranger", "faction_a", [1.0, 4.0], -20.0, "Idle_Loop", 6],
            ["hunter_a", "ink_test_m", "costume.mco_male_peasant", "support_blue", [-3.6, 4.6], 35.0, "Fixing_Kneeling", 3],
            ["hunter_b", "ink_test_m2", "costume.mco_male_peasant", "support_blue", [-2.6, 3.4], 25.0, "Fixing_Kneeling", 9],
            ["hunter_c", "ink_test_m", "costume.mco_male_peasant", "support_blue", [3.2, 3.2], -30.0, "Fixing_Kneeling", 14]]
    blocks, structure = [], []
    if way == "block":
        rock = "#4A3F37"
        blocks += [shape("floor", "plane", [0, 5, 0], [14, 16, 1], "#3A3028"),
                   shape("back_wall", "cube", [0, 11.2, 2.6], [14, 1.4, 5.2], rock),
                   shape("wall_l", "cube", [-7.2, 5, 2.6], [1.4, 16, 5.2], "#443A32"),
                   shape("wall_r", "cube", [7.2, 5, 2.6], [1.4, 16, 5.2], "#443A32"),
                   shape("ceiling", "cube", [0, 5, 5.5], [15, 17, 0.7], "#392F28")]
        structure = ["floor", "back_wall", "wall_l", "wall_r", "ceiling"]
    elif way == "flat3":   # KP-56: three flat planes, dark teeth in front, asymmetric walls, a lit back wall
        blocks += [shape("floor", "plane", [0, 5, 0], [14, 16, 1], "#3A3028"),
                   shape("wall_l", "cube", [-7.2, 5, 2.6], [1.4, 16, 5.2], "#54473B"),
                   shape("ceiling", "cube", [0, 5, 5.5], [15, 17, 0.7], "#392F28")]
        structure = ["floor", "wall_l", "ceiling"]
        for k, (x, h, yw) in enumerate(((-5.6, 5.2, 6.0), (-2.6, 6.0, -4.0), (0.4, 5.6, 3.0), (3.2, 6.4, -7.0), (6.0, 5.0, 5.0))):
            blocks.append(shape(f"back_slab_{k}", "cube", [x, 11.3 + 0.25 * (k % 2), h / 2], [3.2, 1.2, h], "#7A6450", yaw=yw))
            structure.append(f"back_slab_{k}")
        blocks += [shape("wall_r_front", "cube", [7.2, 2.6, 2.6], [1.4, 5.2, 5.2], "#54473B"),   # the east wall's fissure at y ~ 6
                   shape("wall_r_back", "cube", [7.2, 9.0, 2.6], [1.4, 5.6, 5.2], "#54473B"),
                   shape("west_ledge", "cube", [-6.1, 9.8, 2.3], [1.0, 2.6, 0.3], "#6A5745", yaw=4.0)]
        structure += ["wall_r_front", "wall_r_back", "west_ledge"]
        for k, y in enumerate((9.0, 9.8, 10.6)):
            blocks.append(dress(shape(f"talisman_{k}", "cylinder", [-5.8, y, 1.85], [0.08, 0.08, 0.55], "#E6DCC2")))
        for k, (x, y, h, w) in enumerate(((-4.0, 3.0, 1.4, 0.7), (3.4, 2.4, 1.2, 0.6), (-4.6, 8.6, 1.5, 0.7), (4.4, 8.8, 1.3, 0.6))):
            blocks.append(flat_tooth(f"stalactite_{k}", x, y, h, w, "#2E2620", down=True, top=5.15))
        for k, (x, y, h, w) in enumerate(((-2.3, 0.6, 2.6, 0.9), (2.5, 0.5, 2.2, 0.8), (-1.6, 0.2, 1.3, 0.6))):
            blocks.append(flat_tooth(f"tooth_{k}", x, y, h, w, "#2A221C"))
        import math
        for k in range(8):
            a = k * math.pi / 4
            blocks.append(dress(shape(f"ring_{k}", "uv_sphere", [0.75 * math.cos(a), 5.0 + 0.75 * math.sin(a), 0.08], [0.36, 0.36, 0.2], "#4A3B2C")))
        blocks += [dress(shape("ochre_bowl", "cylinder", [2.8, 8.6, 0.1], [0.42, 0.42, 0.2], "#B8332A")),
                   lamp("fissure_rim", [8.6, 6.0, 2.6], 300.0, [1.0, 0.62, 0.32], 0.4, False)]
        structure.append("fissure_rim")
    else:
        tex = "texture.ph_rocky_terrain_diff"
        blocks += [shape("floor", "plane", [0, 5, 0], [14, 16, 1], "#5A5148", texture=tex, tile=6.0)]
        structure = ["floor"]
        blocks += [shape("back_fill", "cube", [0, 12.6, 3.0], [18, 1.0, 7], "#2B231D"), shape("side_fill_l", "cube", [-9.4, 5, 3.0], [1.0, 20, 7], "#2B231D"),
                   shape("side_fill_r", "cube", [9.4, 5, 3.0], [1.0, 20, 7], "#2B231D")]
        structure += ["back_fill", "side_fill_l", "side_fill_r"]
        for k, x in enumerate((-4.6, 0.0, 4.6)):   # the back wall: three rock faces, 2.5 x, behind the painted panel
            blocks.append(piece(f"back_rock_{k}", "model.ph_rock_face_01", [x, 12.3, 0.0], 180.0, 2.5))
            structure.append(f"back_rock_{k}")
        for k, y in enumerate((1.0, 5.0, 9.0)):
            blocks.append(piece(f"left_rock_{k}", "model.ph_rock_face_02", [-6.6, y, 0.0], -90.0, 3.2))
            blocks.append(piece(f"right_rock_{k}", "model.ph_rock_face_02", [6.6, y, 0.0], 90.0, 3.2))
            structure += [f"left_rock_{k}", f"right_rock_{k}"]
        blocks += [shape("ceiling", "cube", [0, 5, 6.2], [15, 17, 0.7], "#2E2620")]
        structure.append("ceiling")
        blocks += [piece("boulder_l", "model.ph_boulder_01", [-5.6, 9.8, 0.0], 30.0, 1.4), piece("boulder_r", "model.ph_namaqualand_boulder_04", [5.0, 8.0, 0.0], -40.0, 0.9)]
        structure += ["boulder_l", "boulder_r"]
    blocks += painted_wall(0.0, 8.9 if way == "cc0" else 10.4, 0.2)
    blocks += fire("hearth", 0.0, 5.0)
    if way == "cc0":
        blocks.append(piece("fire_pit", "model.ph_stone_fire_pit", [0.0, 5.0, 0.0], 0.0, 1.2))
    blocks += [lamp("cave_fill", [0.0, 3.0, 4.2], 520.0, [1.0, 0.72, 0.5], 1.2, False),
               lamp("cave_fill_r", [3.6, 1.2, 2.6], 260.0, [1.0, 0.7, 0.48], 1.0, False)]   # BL-01: the right hunter was too dark
    structure += ["cave_fill", "cave_fill_r"]
    return blocks, cast, structure, [[0.0, -1.8, 1.7], None, [0.0, 6.0, 1.5], None, 22, 1]


def _ice(way):
    cast = [["marcus", "ink_test_m2", "costume.mco_male_ranger", "faction_a", [1.4, 1.6], 180.0, "Idle_Loop", 4]]
    blocks, structure = [], []
    if way == "block":
        blocks += [shape("ground", "plane", [0, 40, 0], [220, 220, 1], "#DDE4EA"),
                   shape("hill_l", "uv_sphere", [-45, 90, 0], [90, 60, 24], "#C9D3DB"),
                   shape("hill_r", "uv_sphere", [40, 110, 0], [110, 70, 30], "#C1CBD4"),
                   shape("ridge", "cube", [0, 150, 16], [700, 12, 32], "#AEB9C4")]
        structure = ["ground", "hill_l", "hill_r", "ridge"]
    elif way == "flat3":   # KP-56: ice-blue drifts in front (never brown rocks), jagged ice blocks in the middle, hills and a ridge behind
        blocks += [shape("ground", "plane", [0, 40, 0], [220, 220, 1], "#DDE4EA"),
                   shape("hill_l", "uv_sphere", [-45, 90, 0], [90, 60, 24], "#C9D3DB"),
                   shape("hill_r", "uv_sphere", [40, 110, 0], [110, 70, 30], "#C1CBD4")]
        structure = ["ground", "hill_l", "hill_r"]
        for k, (x, w, h, yw) in enumerate(((-60, 40, 18, 8), (-20, 30, 26, -6), (15, 36, 22, 10), (55, 44, 30, -4))):
            blocks.append(shape(f"ridge_{k}", "cube", [x, 150 + 6 * (k % 2), h / 2], [w, 10, h], "#A9BDD0", yaw=yw))
            structure.append(f"ridge_{k}")
        for n, x, y, d in (("drift_l", -7.0, 5.0, [7.0, 3.2, 1.3]), ("drift_r", 9.5, 6.0, [8.0, 3.6, 1.5]), ("drift_c", -2.8, 2.2, [3.0, 1.6, 0.5])):
            blocks.append(dress(shape(n, "uv_sphere", [x, y, 0], d, "#B8D0E8")))
        for k, (x, y, h, w, yw) in enumerate(((-20, 36, 3.6, 3.0, 20), (-23, 38, 2.4, 2.2, -15), (32, 46, 4.0, 3.4, 10))):
            blocks.append(dress(shape(f"ice_block_{k}", "cube", [x, y, h / 2], [w, w * 0.8, h], "#9FBBD6", yaw=yw)))
    else:
        blocks += [shape("ground", "plane", [0, 40, 0], [220, 220, 1], "#DDE4EA"),
                   shape("hill_l", "uv_sphere", [-45, 90, 0], [90, 60, 24], "#C9D3DB"),
                   shape("hill_r", "uv_sphere", [40, 110, 0], [110, 70, 30], "#C1CBD4")]
        structure = ["ground", "hill_l", "hill_r"]
        spots = [("rock_a", "model.ph_namaqualand_boulder_02", [-9, 14, 0], 20, 2.2), ("rock_b", "model.ph_namaqualand_boulder_04", [12, 20, 0], -30, 1.5),
                 ("rock_c", "model.ph_boulder_01", [-16, 27, 0], 80, 2.4), ("rock_d", "model.ph_namaqualand_boulder_02", [-24, 40, 0], 10, 3.0),
                 ("trunk_a", "model.ph_dead_tree_trunk", [-14, 8, 0], 70, 1.4), ("trunk_b", "model.ph_dead_tree_trunk", [8, 6, 0], -20, 1.0),
                 ("stump_a", "model.ph_tree_stump_01", [-6, 6, 0], 0, 1.3)]
        for n, a, p, yw, sc in spots:
            blocks.append(piece(n, a, p, yw, sc))
            structure.append(n)
    for k, (x, y, yw, big) in enumerate(((-6.0, 19.0, 70.0, 1.25), (3.0, 25.0, 100.0, 1.0), (18.0, 30.0, 80.0, 0.9))):
        blocks += mammoth(f"mammoth_{k}", x, y, yw, big)
    return blocks, cast, structure, [[-1.5, -6.0, 1.3], None, [3.0, 18.0, 2.2], None, 24, 1]


def _camp(way):
    cast = [["marcus", "ink_test_m2", "costume.mco_male_ranger", "faction_a", [-1.8, 5.2], 70.0, "Sitting_Idle_Loop", 5],
            ["ura", "ink_test_m", "costume.mco_male_peasant", "faction_b", [1.8, 5.6], -70.0, "Idle_Talking_Loop", 11],
            ["torch_a", "ink_test_m", "costume.mco_male_peasant", "support_blue", [-4.2, 8.4], 30.0, "Idle_Torch_Loop", 2],
            ["torch_b", "ink_test_m2", "costume.mco_male_peasant", "support_blue", [4.6, 8.2], -30.0, "Idle_Torch_Loop", 7]]
    blocks, structure = [], []
    if way == "block":
        blocks += [shape("ground", "plane", [0, 20, 0], [900, 900, 1], "#59606A")]
        structure = ["ground"]
        blocks += [shape("log_seat", "cylinder", [-2.4, 5.2, 0.25], [0.5, 0.5, 2.0], "#4A3524", 0.0, pitch=90.0)]
    elif way == "flat3":   # KP-56: log and fire ring in front, four different huts (tusk arch, hide rack, the chief's, the bone gate)
        blocks += [shape("ground", "plane", [0, 20, 0], [900, 900, 1], "#59606A"),
                   shape("horizon_band", "cube", [0, 160, 5], [900, 1, 10], "#3A506B")]
        structure = ["ground", "horizon_band"]
        blocks += [shape("log_seat", "cylinder", [-2.4, 5.2, 0.25], [0.5, 0.5, 2.0], "#5C3A21", 0.0, pitch=90.0)]
        import math
        for k in range(8):
            a = k * math.pi / 4
            blocks.append(dress(shape(f"ring_{k}", "uv_sphere", [0.8 * math.cos(a), 5.5 + 0.8 * math.sin(a), 0.08], [0.38, 0.38, 0.22], "#4A3B2C")))
        ivory, wood = "#E6DCC2", "#5C3A21"
        blocks += [dress(shape("tusk_arch_l", "cone", [-10.3, 12.6, 1.3], [0.3, 0.3, 2.6], ivory, pitch=-14.0)),
                   dress(shape("tusk_arch_r", "cone", [-7.9, 12.6, 1.3], [0.3, 0.3, 2.6], ivory, pitch=14.0)),
                   dress(shape("rack_post_a", "cylinder", [-1.4, 15.6, 0.9], [0.12, 0.12, 1.8], wood)),
                   dress(shape("rack_post_b", "cylinder", [0.2, 15.6, 0.9], [0.12, 0.12, 1.8], wood)),
                   dress(shape("rack_hide", "cube", [-0.6, 15.6, 1.25], [1.4, 0.05, 0.95], "#C9A36B")),
                   dress(shape("gate_post_a", "cone", [11.4, 12.0, 1.6], [0.34, 0.34, 3.2], ivory)),
                   dress(shape("gate_post_b", "cone", [13.0, 12.0, 1.6], [0.34, 0.34, 3.2], ivory)),
                   dress(shape("gate_bar", "cylinder", [12.2, 12.0, 3.0], [0.16, 0.16, 2.0], ivory, 90.0, pitch=90.0)),
                   dress(shape("spear_a", "cylinder", [10.4, 10.8, 1.1], [0.07, 0.07, 2.4], wood, 0.0, pitch=22.0)),
                   dress(shape("spear_b", "cylinder", [10.4, 10.8, 1.1], [0.07, 0.07, 2.4], wood, 0.0, pitch=-22.0))]
    else:
        blocks += [shape("ground", "plane", [0, 20, 0], [900, 900, 1], "#59606A")]
        structure = ["ground"]
        for n, a, p, yw, sc in (("log_seat", "model.ph_dead_tree_trunk", [-2.6, 5.2, 0.0], 90, 0.7), ("stump_a", "model.ph_tree_stump_01", [7.6, 5.4, 0.0], 0, 1.0),
                                ("rock_a", "model.ph_boulder_01", [-9.0, 11.0, 0.0], 30, 1.8), ("rock_b", "model.ph_namaqualand_boulder_04", [10.0, 12.0, 0.0], -50, 1.3),
                                ("trunk_a", "model.ph_dead_tree_trunk", [-7.0, 15.0, 0.0], 15, 1.6), ("trunk_b", "model.ph_dead_tree_trunk", [8.5, 16.0, 0.0], -25, 1.6),
                                ("fire_pit", "model.ph_stone_fire_pit", [0.0, 5.5, 0.0], 0.0, 1.3)):
            blocks.append(piece(n, a, p, yw, sc))
            structure.append(n)
    for k, (x, y, r) in enumerate(((-8.5, 14.0, 1.8), (-3.0, 17.0, 1.6), (3.5, 18.0, 1.7), (9.0, 14.5, 1.8))):
        big = way == "flat3" and k == 2   # KP-56: the chief's hut is the largest
        blocks += hut(f"hut_{k}", x, y, 2.3 if big else r, 3.0 if big else 2.2)
    blocks += fire("camp", 0.0, 5.5)
    blocks += [lamp("storm_fill", [0.0, 4.0, 6.0], 2400.0, [0.55, 0.65, 0.95], 2.0, False),   # BL-01: the camp measured luma 0.06-0.09
               lamp("fire_key", [0.0, 3.0, 2.2], 900.0, [1.0, 0.6, 0.3], 0.6, False),
               lamp("torch_fill", [4.0, 6.6, 2.4], 260.0, [1.0, 0.62, 0.32], 0.6, False),   # BL-01: torch_b measured 0.144
               lamp("torch_fill_l", [-3.6, 6.8, 2.4], 300.0, [1.0, 0.62, 0.32], 0.6, False)]   # BL-01: then torch_a 0.140
    structure += ["storm_fill", "fire_key", "torch_fill", "torch_fill_l"]
    return blocks, cast, structure, [[0.0, -3.4, 1.6], None, [0.0, 8.0, 1.5], None, 24, 1]


def project(cam: list, point: list) -> tuple[float, float, float]:
    """(screen x 0..1 left->right, screen y 0..1 top->bottom, depth m) of a world point seen by the shot's camera
    [pos, _, look_at, _, lens_mm, frames] on a 36 mm wide sensor at 16:9 (pinhole, Blender's convention)."""
    import math
    c, t, lens = cam[0], cam[2], cam[4]
    f = [t[i] - c[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [f[1], -f[0], 0.0]
    rn = math.sqrt(r[0] ** 2 + r[1] ** 2) or 1.0
    r = [v / rn for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [point[i] - c[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    x = sum(d[i] * r[i] for i in range(3)) / z * lens / SENSOR_MM
    y = sum(d[i] * u[i] for i in range(3)) / z * lens / (SENSOR_MM * 9 / 16)
    return 0.5 + x, 0.5 - y, z


def screen_side(sx: float) -> str:
    """KP-50: the side word of a screen x."""
    return "on the left" if sx < 0.38 else ("in the middle" if sx <= 0.62 else "on the right")


def _subject_point(blocks: list, cast: list, name: str) -> list:
    for c in cast:
        if c[0] == name:
            return [c[4][0], c[4][1], 1.1]
    b = next(b for b in blocks if b.get("name") == name)
    return list(b["pos"])


def subject_tags(scene: str, blocks: list, cast: list, cam: list) -> dict:
    """KP-50/51: the scene's tags with each named subject's screen side from the camera and each counted piece's number word."""
    tags = dict(TAGS[scene])
    for n in SUBJECTS[scene]:
        sx = project(cam, _subject_point(blocks, cast, n))[0]
        tags[n] = f"{tags[n]} {screen_side(sx)}"
    for key, prefix in COUNTED.get(scene, {}).items():
        k = len({b["name"].split("_")[1] for b in blocks if b.get("name", "").startswith(prefix)})
        if k >= 2:
            tags[key] = f"{NUMBERS[k]} {tags[key]}"
    missing = [n for n in SUBJECTS[scene] if not any(w in tags[n] for w in ("on the left", "in the middle", "on the right"))]
    if missing:
        raise ValueError(f"{scene}: no screen side for {missing} (KP-50)")
    return tags


def count_words(tags: dict, scene: str) -> dict:
    return {k: tags[k] for k in COUNTED.get(scene, {})}


PROXY = {"ura": ("antlers", "#C8B598", "#5B3F2A"), "marcus": ("hood", "#7A7F85", None), "hunter_a": ("cap", "#5A5E63", None),
         "hunter_b": ("cap", "#6E4726", None), "hunter_c": ("cap", "#C2A675", None), "torch_a": ("cap", "#5A5E63", None),
         "torch_b": ("cap", "#6E4726", None)}
HEAD_Z = {"Idle_Loop": 1.62, "Idle_Talking_Loop": 1.62, "Idle_Torch_Loop": 1.62, "Fixing_Kneeling": 1.05, "Sitting_Idle_Loop": 1.2}


def proxies(cast: list) -> list:
    """KP-52: a head proxy per named person so no two share a head in Image 1: the sorcerer an antler crown and a cloak cone,
    the courier a grey hood, each hunter a cap in his fur colour (positions from the cast row and the pose's head height)."""
    out = []
    for name, _ch, _co, _fa, (x, y), _yaw, anim, _off in cast:
        if name not in PROXY:
            continue
        kind, col, extra = PROXY[name]
        z = HEAD_Z.get(anim, 1.6)
        out.append(shape(f"{name}_head_proxy", "uv_sphere", [x, y, z + 0.05], [0.3, 0.3, 0.28], col))
        if kind == "antlers":
            for k, sx in enumerate((-0.16, 0.16)):
                out.append(shape(f"{name}_antler_{k}", "cone", [x + sx, y, z + 0.32], [0.07, 0.07, 0.5], col, 0.0, pitch=(-25 if sx < 0 else 25)))
                out.append(shape(f"{name}_tine_{k}", "cone", [x + sx * 1.9, y, z + 0.38], [0.05, 0.05, 0.3], col, 0.0, pitch=(-60 if sx < 0 else 60)))
            out.append(shape(f"{name}_cloak", "cone", [x, y, z * 0.48], [0.95, 0.95, z * 0.92], extra))
    return out


def clutter_clashes(blocks: list, cast: list, cam: list, scene: str, structure: list) -> list[str]:
    """KP-53: unnamed CC0 pieces within 0.10 of the frame width and max(4 m, a quarter of its depth) of a named subject (Qwen merges them)."""
    subj = [(n, project(cam, _subject_point(blocks, cast, n))) for n in SUBJECTS[scene]]
    out = []
    for b in blocks:
        if not (b.get("type") == "piece" or b.get("dress")) or b["name"] in TAGS[scene] or b["name"] in ("fire_pit",) or b["name"].startswith("ring_"):   # the fire's own ring
            continue
        px = project(cam, [b["pos"][0], b["pos"][1], max(0.6, b["pos"][2])])   # a hanging stalactite is judged where it hangs
        if px[2] <= 0 or not (-0.05 <= px[0] <= 1.05):
            continue
        for n, sp in subj:
            if abs(px[0] - sp[0]) < 0.10 and abs(px[2] - sp[2]) < max(4.0, 0.25 * sp[2]) and abs(px[1] - sp[1]) < 0.3:
                out.append(f"{b['name']} next to {n}")
    return out


def shot_id(scene: str, angle: str = "wide") -> str:
    return SHOT[scene] if angle == "wide" else f"sa_{scene}_{angle}"


def layout(scene: str, way: str, angle: str = "wide") -> dict:
    blocks, cast, structure, cam = {"cave": _cave, "ice": _ice, "camp": _camp}[scene](way)
    if angle != "wide":
        cam = ANGLES[scene][angle]
    blocks = blocks + proxies(cast)
    if way != "cc0" and textured(blocks):
        raise ValueError(f"sa_{scene}_{way}: CC0 mesh or texture in a Qwen still (KP-56): {textured(blocks)}")
    clash = clutter_clashes(blocks, cast, cam, scene, structure)
    if clash:
        raise ValueError(f"sa_{scene}_{way}_{angle}: unnamed pieces next to named subjects (KP-53): {clash}")
    names = [b["name"] for b in blocks]
    in_shot = {n: "the place or the story's prop: held identical in both ways except the place's own build" for n in names}
    tags = {**{c[0]: c[0].replace("_", " ") for c in cast}, **subject_tags(scene, blocks, cast, cam)}
    in_shot.update({c[0]: "a person of the scene" for c in cast})
    return {"label": f"Stone-age pilot test, scene {scene}, way {way} (the creator, 2026-11-07 12:48 UTC): {PLACE[scene]}",
            "landmarks": [], "axis": {"deg": 0, "origin": [0, 0]}, "structure": structure, "blocks": blocks, "cast": cast,
            "shots": {shot_id(scene, angle): cam}, "in_shot": {shot_id(scene, angle): in_shot},
            "heroes": {c[0]: f"H{i + 1}" for i, c in enumerate(cast)}, "tags": tags,
            "cards": {shot_id(scene, angle): CARDS[scene]}, "hero_refs": {}, "sub_category": "S1",
            "place": PLACE[scene], "light": LIGHT[scene]}


def ids() -> list[str]:
    return [f"sa_{s}_{w}" for s in SCENES for w in WAYS]


def angle_ids() -> list[str]:
    """Test A (creator 15:04 UTC): the rich way (flat3, creator 15:05 UTC: always the rich Blender build) from the two more angles."""
    return [f"sa_{s}_flat3_{a}" for s in SCENES for a in ANGLES[s]]


def write() -> list[str]:
    doc = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    for s in SCENES:
        for w in WAYS:
            doc["layouts"][f"sa_{s}_{w}"] = layout(s, w)
        for a in ANGLES[s]:
            doc["layouts"][f"sa_{s}_flat3_{a}"] = layout(s, "flat3", a)
    LAYOUTS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return ids() + angle_ids()


def main(argv: list[str] | None = None) -> int:
    cmd = (argv or sys.argv[1:] or ["list"])[0]
    if cmd == "write":
        print("\n".join(write()))
    else:
        print("\n".join(ids()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
