"""Foot and root paths of animation clips, for PoC 1's foot-slide line (roadmap 21.6; ICW-06). Run by
``blender/characters.py measure-clips``:

    blender --background --factory-startup --python-exit-code 1 --python measure_clips.py -- <job.json>

job = {"glb": <the UAL GLB>, "actions": [names], "bones": ["root", "pelvis", "foot_l", "foot_r", ...], "out": <json>}.
For every action: each frame of its range, the world position of each bone's head with the clip on the GLB's own armature.
stdlib + bpy only; the numbers are read by ``rigs.foot_slide``.
"""
import json
import os
import re
import sys

import bpy  # noqa: E402  (Blender's own module)

SUFFIX = re.compile(r"\.\d{3}$")


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=job["glb"])
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    acts = {SUFFIX.sub("", a.name): a for a in bpy.data.actions}
    scene = bpy.context.scene
    out = {"glb": os.path.basename(job["glb"]), "fps": scene.render.fps, "actions": {}}
    ad = arm.animation_data_create()
    for name in job["actions"]:
        act = acts[name]
        ad.action = act
        if hasattr(ad, "action_slot") and act.slots:
            ad.action_slot = act.slots[0]
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        rows = []
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            rows.append({b: [round(v, 5) for v in (arm.matrix_world @ arm.pose.bones[b].head)] for b in job["bones"]})
        out["actions"][name] = {"frames": [f0, f1], "samples": rows}
    tmp = job["out"] + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, job["out"])


main()
