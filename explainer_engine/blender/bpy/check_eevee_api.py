"""CI-only (WP-Q0): run ``apply_settings`` of render_shot.py inside the real Blender and print what it applied, so the 5.x names
(``BLENDER_EEVEE`` engine id, ``use_fast_gi`` + ``fast_gi_method`` for ambient occlusion, no ``use_gtao``) are proven on the pinned build.
Run: blender --background --factory-startup --python-exit-code 1 --python <this file>. Exits 1 if a switch is missing."""
import json
import os
import sys

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_shot.py"), encoding="utf-8").read()
ns = {"__name__": "render_shot_check"}
exec(compile(src.rstrip()[:-len("main()")], "render_shot.py", "exec"), ns)  # noqa: S102  (our own file, without its main())
import bpy  # noqa: E402  (Blender's own module)

job = {"engine": "eevee", "settings": {"samples": 64, "raytracing": True, "ambient_occlusion": True, "motion_blur": False}}
applied, missing = ns["apply_settings"](bpy.context.scene, job)
print("APPLIED " + json.dumps({"blender": bpy.app.version_string, "applied": applied, "missing": missing}))
ok = (applied.get("engine_id") == "BLENDER_EEVEE" and applied.get("eevee.use_fast_gi") is True
      and applied.get("eevee.fast_gi_method") == "AMBIENT_OCCLUSION_ONLY" and not missing)
sys.exit(0 if ok else 1)
