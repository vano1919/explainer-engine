"""The Blender render lanes of the Ink Chronicle (D-96, roadmap section 11): the pinned binary (``project``), the render profiles
(``profiles``), the headless adapter with the frame-recovery protocol of roadmap 10.4 (``render``) and the cost estimate from
measured rows (``cost``), the library assets of a shot with their import settings (``assets``) and the mouths and rig checks
(``rigs``: Rhubarb cues to shape-key tracks). Only ``bpy/render_shot.py`` imports ``bpy``; it runs inside Blender, never in this interpreter."""
