"""WP-Q4 glue: the Rain scene description (no Blender): objects, material map covering every Rain material, viseme tracks on real
CloudRig bone names, the lattice deltas only when asked, and the pose table being complete."""
from pathlib import Path

from explainer_engine.blender import character_benchmark as C
from explainer_engine.blender import rigs


def test_pose_table_is_complete_and_uses_the_face_main_controls():
    p = C.poses()
    assert set(p) == set(rigs.SHAPES)
    bones = {b for pose in p.values() for b in pose}
    assert bones <= {"MSTR-Jaw", "MSTR-Mouth", "MSTR-LowerLip", "MSTR-UpperLip"}
    rigs.ActionVisemes(p)  # validates the channels


def test_scene_has_rain_a_wall_a_push_and_a_toon_material_for_every_slot_name():
    lip = rigs.LipSync(24).plan({"metadata": {"duration": 0.5}, "mouthCues": [{"start": 0, "end": 0.25, "value": "D"},
                                                                         {"start": 0.25, "end": 0.5, "value": "X"}]}, 12)
    sc = C.scene(Path("rain.blend"), 12, lip=lip, angular=1.0)
    rb = sc["objects"][1]["rig_blend"]
    assert rb["rig"] == "RIG-rain" and sc["camera"]["to"]["location"][1] > sc["camera"]["location"][1]
    assert set(C.MATERIAL_MAP.values()) <= set(sc["materials"])
    assert "MSTR-Jaw|rotation_euler|0" in rb["visemes"] and rb["lattice"]["object"] == C.LATTICE
    assert C.scene(Path("rain.blend"), 12)["objects"][1]["rig_blend"]["lattice"] is None


def test_class_names_reach_the_style_tints():
    from explainer_engine.blender.style import material_class
    assert material_class("rain_skin") == "skin" and material_class("rain_hair") == "hair" and material_class("rain_eyes") == "eyes"
    assert material_class("rain_costume", "costume") == "costume"
