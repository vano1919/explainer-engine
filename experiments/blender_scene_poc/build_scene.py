import bpy
import math
from mathutils import Vector
from pathlib import Path

OUT = Path(__file__).resolve().parent / "render_output"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

def material(name, color, roughness=0.78):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

ink = material("Ink | deep outline", (0.035, 0.025, 0.03))
skin = material("Skin | warm", (0.72, 0.36, 0.22))
steel = material("Steel | blue grey", (0.20, 0.29, 0.36), 0.42)
gold = material("Gold", (0.88, 0.56, 0.12), 0.38)
red = material("Cape | vermilion", (0.58, 0.055, 0.045))
dark_red = material("Cape shadow", (0.25, 0.025, 0.03))
stone = material("Castle | warm stone", (0.56, 0.43, 0.31))
stone_light = material("Stone highlights", (0.76, 0.62, 0.45))
grass = material("Ground", (0.16, 0.25, 0.16))
sky = material("Sky", (0.34, 0.55, 0.73))

def assign(obj, mat):
    obj.data.materials.append(mat)
    return obj

def attach(obj, parent):
    if parent:
        world_matrix = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world_matrix
    return obj

def uv(name, loc, scale, mat, parent=None, segments=16, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, mat)
    attach(obj, parent)
    return obj

def cube(name, loc, scale, mat, parent=None, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft illustrated edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    assign(obj, mat)
    attach(obj, parent)
    return obj

def cylinder(name, loc, radius, depth, mat, parent=None, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    attach(obj, parent)
    return obj

def rod(name, a, b, radius, mat, parent=None):
    mid = (Vector(a) + Vector(b)) / 2
    direction = Vector(b) - Vector(a)
    obj = cylinder(name, mid, radius, direction.length, mat, parent)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    return obj

# Stage and background
cube("Ground plane", (0, 0, -0.35), (28, 22, 0.5), grass, bevel=0)
cube("Sky backdrop", (0, 7, 5), (30, 0.3, 14), sky, bevel=0)

# Castle silhouette
cube("Castle keep", (4.6, 1.0, 2.0), (3.0, 1.5, 4.0), stone)
for x in (3.0, 6.2):
    cylinder("Castle tower", (x, 1.0, 3.0), 0.82, 5.5, stone_light)
    cylinder("Tower roof", (x, 1.0, 5.9), 0.95, 0.8, dark_red, vertices=4)
    for z in (1.0, 2.0, 3.0, 4.0):
        cube("Arrow slit", (x, 0.19, z), (0.16, 0.06, 0.42), ink, bevel=0.01)
cube("Castle gate", (4.6, 0.19, 0.8), (1.0, 0.08, 1.7), ink, bevel=0.02)
for x in [3.1, 3.7, 4.3, 4.9, 5.5, 6.1]:
    cube("Battlement", (x, 1.0, 4.15), (0.38, 1.55, 0.45), stone_light)

# Hero root: reusable character placeholder, not an AI mesh import.
root = bpy.data.objects.new("HERO_ROOT", None)
bpy.context.collection.objects.link(root)
root.location = (-2.2, -0.8, 0)

uv("Head", (-2.2, -0.8, 2.65), (0.55, 0.48, 0.62), skin, root)
uv("Hair", (-2.2, -0.75, 3.02), (0.59, 0.49, 0.35), ink, root)
cube("Torso armour", (-2.2, -0.82, 1.72), (1.05, 0.58, 1.15), steel, root, 0.18)
cube("Chest plate", (-2.2, -1.13, 1.83), (0.62, 0.08, 0.68), gold, root, 0.1)
uv("Shoulder left", (-2.88, -0.82, 2.12), (0.34, 0.38, 0.3), gold, root)
uv("Shoulder right", (-1.52, -0.82, 2.12), (0.34, 0.38, 0.3), gold, root)
cube("Cape", (-2.2, -0.42, 1.55), (1.15, 0.16, 1.55), red, root, 0.12)
cube("Cape shadow", (-2.2, -0.31, 1.45), (0.82, 0.08, 1.22), dark_red, root, 0.08)

# Arms and legs as separate controllable parts.
arm_l = rod("Arm left", (-2.75, -0.82, 2.08), (-3.2, -0.9, 1.48), 0.19, steel, root)
arm_r = rod("Arm right", (-1.65, -0.82, 2.08), (-1.1, -0.95, 1.75), 0.19, steel, root)
uv("Hand left", (-3.2, -0.9, 1.48), (0.19, 0.18, 0.19), skin, root)
uv("Hand right", (-1.1, -0.95, 1.75), (0.19, 0.18, 0.19), skin, root)
rod("Leg left", (-2.55, -0.82, 1.2), (-2.7, -0.95, 0.35), 0.22, steel, root)
rod("Leg right", (-1.85, -0.82, 1.2), (-1.7, -0.95, 0.35), 0.22, steel, root)
cube("Boot left", (-2.72, -1.0, 0.22), (0.55, 0.65, 0.28), ink, root)
cube("Boot right", (-1.68, -1.0, 0.22), (0.55, 0.65, 0.28), ink, root)

# Sword and shield props.
rod("Sword blade", (-0.98, -0.98, 1.8), (-0.5, -0.98, 2.65), 0.055, stone_light, root)
rod("Sword grip", (-1.08, -0.98, 1.62), (-0.92, -0.98, 1.9), 0.09, gold, root)
uv("Shield", (-3.25, -1.1, 1.1), (0.42, 0.12, 0.55), red, root)
uv("Shield boss", (-3.25, -1.23, 1.1), (0.12, 0.06, 0.12), gold, root)

# Small background soldiers create scale without a crowd simulation.
for i, x in enumerate((0.0, 1.1, 2.2)):
    soldier = bpy.data.objects.new(f"SOLDIER_{i}", None)
    bpy.context.collection.objects.link(soldier)
    soldier.location = (x, -0.3, 0)
    uv(f"Soldier {i} head", (x, -0.3, 1.55), (0.22, 0.2, 0.24), skin, soldier, 12, 8)
    cube(f"Soldier {i} body", (x, -0.3, 1.0), (0.42, 0.35, 0.65), steel, soldier)
    rod(f"Soldier {i} spear", (x + 0.28, -0.3, 0.8), (x + 0.28, -0.3, 2.25), 0.035, gold, soldier)

# Animation: a short, repeatable hero entrance and pointing gesture.
root.location = (-3.2, -0.8, 0)
root.keyframe_insert(data_path="location", frame=1)
root.location = (-2.2, -0.8, 0)
root.keyframe_insert(data_path="location", frame=36)
root.location = (-2.2, -0.8, 0)
root.keyframe_insert(data_path="location", frame=72)
root.keyframe_insert(data_path="location", frame=120)
arm_r.rotation_mode = "XYZ"
arm_r.rotation_euler[1] = 0
arm_r.keyframe_insert(data_path="rotation_euler", frame=1)
arm_r.rotation_euler[1] = math.radians(-24)
arm_r.keyframe_insert(data_path="rotation_euler", frame=36)
arm_r.rotation_euler[1] = math.radians(-8)
arm_r.keyframe_insert(data_path="rotation_euler", frame=72)
arm_r.keyframe_insert(data_path="rotation_euler", frame=120)

# Camera, light and render.
bpy.ops.object.camera_add(location=(0.0, -13.5, 6.2))
camera = bpy.context.object
camera.name = "SHOT_CAMERA"
target = Vector((0.4, 0.0, 2.3))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 14.0
camera.data.keyframe_insert(data_path="ortho_scale", frame=1)
camera.data.ortho_scale = 12.8
camera.data.keyframe_insert(data_path="ortho_scale", frame=120)
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type="AREA", location=(-4, -7, 10))
key = bpy.context.object
key.name = "KEY_LIGHT"
key.data.energy = 1500
key.data.shape = "DISK"
key.data.size = 7
key.rotation_euler = (Vector((0, 0, 1.5)) - key.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 120
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = str(OUT / "blender_poc_video")
scene.world.color = (0.18, 0.18, 0.18)
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.frame_set(36)

assert scene.camera is not None
assert len(scene.objects) >= 35
assert root.animation_data is not None
assert scene.frame_end == 120
assert abs(scene.render.fps - 24) < 0.001

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "blender_poc.blend"))

scene.frame_set(60)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "blender_poc_frame.png")
bpy.ops.render.render(write_still=True)

scene.render.image_settings.file_format = "FFMPEG"
scene.render.filepath = str(OUT / "blender_poc_video")
bpy.ops.render.render(animation=True)

video = OUT / "blender_poc_video.mp4"
assert video.exists() and video.stat().st_size > 10_000, "MP4 output missing or unexpectedly small"
print(f"BLENDER_POC_OK objects={len(scene.objects)} frames={scene.frame_end} seconds={scene.frame_end / scene.render.fps:.2f} video={video}")
