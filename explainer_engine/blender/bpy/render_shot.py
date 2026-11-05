"""Runs INSIDE Blender, the only file of the repository that imports ``bpy`` (roadmap section 11). ``blender/render.py`` starts it:

    blender --background --factory-startup --python-exit-code 1 --python render_shot.py -- <job.json>

It reads the render job (``render_shot/1``, written by ``render.HeadlessRender``), checks that it runs on the pinned Blender, builds
or opens the scene, applies the profile's settings, renders exactly the frame indices the job lists and, after EACH frame, moves
the finished PNG into place (written under a temporary name first) and appends one line to the progress file, flushed to disk:
the host side commits frames from those lines while Blender keeps rendering (roadmap 10.4, ``RENDERED``). It ends with a report
(Blender version, build hash, engine, what was applied and what this Blender lacks, object counts). Any error raises, and
``--python-exit-code 1`` turns it into a non-zero exit (the 2026-11-04 PoC script raised and Blender still exited 0).

Scene kinds: ``smoke`` (a few primitives under a moving camera, built here: the CI smoke of roadmap 12.4 step 1) and ``blend``
(a .blend file written by the scene builder, ICW-06, opened as it is). stdlib + bpy only.
"""
import json
import os
import sys
import time

import bpy  # noqa: E402  (Blender's own module; this file never runs outside Blender)

ENGINE_IDS = {"eevee": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"), "cycles": ("CYCLES",), "workbench": ("BLENDER_WORKBENCH",)}


def job_path():
    argv = sys.argv
    if "--" not in argv or len(argv) <= argv.index("--") + 1:
        raise SystemExit("render_shot.py needs: -- <job.json>")
    return argv[argv.index("--") + 1]


def write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def engine_id(engine):
    items = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    for cand in ENGINE_IDS[engine]:
        if cand in items:
            return cand
    raise RuntimeError(f"this Blender has no {engine} engine (has: {sorted(items)})")


def set_attr(obj, name, value, applied, missing, label):
    if value is None:
        return
    if hasattr(obj, name):
        setattr(obj, name, value)
        applied[label] = value
    else:
        missing.append(label)


def build_smoke(scene, frames_total):
    """A floor, three coloured primitives and a sun under a camera that dollies in and pans: every frame differs, none is black."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("smoke_world")
    scene.world.color = (0.62, 0.58, 0.50)

    def mat(name, rgba):
        m = bpy.data.materials.new(name)
        m.diffuse_color = rgba
        return m

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(mat("floor", (0.80, 0.74, 0.60, 1)))
    shapes = ((bpy.ops.mesh.primitive_cube_add, (-2.0, 0, 1), (0.70, 0.18, 0.12, 1)),
              (bpy.ops.mesh.primitive_uv_sphere_add, (0, 1.5, 1), (0.15, 0.35, 0.60, 1)),
              (bpy.ops.mesh.primitive_cone_add, (2.0, 0, 1), (0.20, 0.50, 0.25, 1)))
    for add, loc, rgba in shapes:
        add(location=loc)
        bpy.context.active_object.data.materials.append(mat(f"m{loc[0]:g}", rgba))
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    bpy.ops.object.camera_add(location=(0, -12, 4), rotation=(1.30, 0, 0))
    cam = bpy.context.active_object
    scene.camera = cam
    last = scene.frame_start + max(frames_total - 1, 1)
    cam.keyframe_insert("location", frame=scene.frame_start)
    cam.keyframe_insert("rotation_euler", frame=scene.frame_start)
    cam.location = (3, -8, 3)
    cam.rotation_euler = (1.30, 0, 0.35)
    cam.keyframe_insert("location", frame=last)
    cam.keyframe_insert("rotation_euler", frame=last)


def apply_settings(scene, job):
    applied, missing = {}, []
    s, eng = job["settings"], job["engine"]
    scene.render.engine = engine_id(eng)
    applied["engine_id"] = scene.render.engine
    if eng == "eevee":
        ee = scene.eevee
        set_attr(ee, "taa_render_samples", s.get("samples"), applied, missing, "eevee.taa_render_samples")
        set_attr(ee, "use_raytracing", s.get("raytracing"), applied, missing, "eevee.use_raytracing")
        set_attr(ee, "use_gtao", s.get("ambient_occlusion"), applied, missing, "eevee.use_gtao")
    elif eng == "cycles":
        cy = scene.cycles
        set_attr(cy, "samples", s.get("samples"), applied, missing, "cycles.samples")
        set_attr(cy, "use_denoising", s.get("denoise"), applied, missing, "cycles.use_denoising")
        set_attr(cy, "seed", job.get("seed"), applied, missing, "cycles.seed")
        if job["device"] == "gpu":
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for kind in ("OPTIX", "CUDA"):
                try:
                    prefs.compute_device_type = kind
                    prefs.get_devices()
                    if any(d.type == kind for d in prefs.devices):
                        break
                except TypeError:
                    continue
            else:
                raise RuntimeError("device gpu: Cycles finds no OPTIX or CUDA device")
            for d in prefs.devices:
                d.use = d.type == prefs.compute_device_type
            cy.device = "GPU"
            applied["cycles.device"] = f"GPU/{prefs.compute_device_type}"
    else:
        sh = scene.display.shading
        set_attr(sh, "light", "STUDIO", applied, missing, "display.shading.light")
        set_attr(sh, "color_type", "MATERIAL", applied, missing, "display.shading.color_type")
    set_attr(scene.render, "use_motion_blur", s.get("motion_blur"), applied, missing, "render.use_motion_blur")
    return applied, missing


def gpu_backend():
    try:
        import gpu
        return gpu.platform.backend_type_get()
    except Exception:  # noqa: BLE001  (informational only: a missing field never fails a render)
        return None


def main():
    path = job_path()
    with open(path, encoding="utf-8") as f:
        job = json.load(f)
    if job.get("job") != "render_shot/1":
        raise RuntimeError(f"{path} is not a render_shot/1 job")
    have = bpy.app.version_string.split()[0]
    if have != job["pin_version"]:
        raise RuntimeError(f"Blender {have} is not the pinned {job['pin_version']} (BP-175)")
    sc = job["scene"]
    if sc["kind"] == "blend":
        bpy.ops.wm.open_mainfile(filepath=sc["path"])
    scene = bpy.context.scene
    scene.frame_start = job["frame_start"]
    scene.render.fps, scene.render.fps_base = job["fps"], 1.0
    if sc["kind"] == "smoke":
        build_smoke(scene, sc["frames_total"])
    elif sc["kind"] != "blend":
        raise RuntimeError(f"unknown scene kind {sc['kind']!r}")
    if scene.camera is None:
        raise RuntimeError("the scene has no camera")
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = job["width"], job["height"], int(job["percent"])
    r.pixel_aspect_x = r.pixel_aspect_y = 1.0
    r.film_transparent = False
    r.use_file_extension = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.color_depth = "8"
    applied, missing = apply_settings(scene, job)
    os.makedirs(job["frames_dir"], exist_ok=True)
    with open(job["progress"], "a", encoding="utf-8") as prog:
        for idx in job["frames"]:
            name = job["frame_name"].format(index=idx)
            final = os.path.join(job["frames_dir"], name)
            tmp = os.path.join(job["frames_dir"], ".part_" + name)
            scene.frame_set(job["frame_start"] + idx)
            r.filepath = tmp
            t0 = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
                raise RuntimeError(f"frame {idx}: Blender wrote no image at {tmp}")
            os.replace(tmp, final)
            secs = time.perf_counter() - t0
            prog.write(json.dumps({"index": idx, "file": name, "seconds": round(secs, 4)}) + "\n")
            prog.flush()
            os.fsync(prog.fileno())
    kinds = {}
    for ob in scene.objects:
        kinds[ob.type] = kinds.get(ob.type, 0) + 1
    write_json(job["report"], {
        "blender_version": bpy.app.version_string,
        "build_hash": bpy.app.build_hash.decode("ascii", "replace") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "engine_id": scene.render.engine, "applied": applied, "missing": missing, "objects": kinds,
        "frames": len(job["frames"]), "gpu_backend": gpu_backend(),
    })


main()
