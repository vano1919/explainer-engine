"""Render profiles of the Blender lanes (roadmap section 11 and 12.3-12.4; D-105 replaced the LTX tiers with them).

A profile is the engine and its default quality switches; the shot spec's own ``render`` block (samples, motion blur, denoise)
wins over the defaults for that shot. The numbers are the roadmap's, every one HYP until the ICW-09 benchmark measures it:

- ``eevee_fast``: EEVEE, 16 samples, no screen-space ray tracing (12.3 scenario A);
- ``eevee_full``: EEVEE, 64 samples, ambient occlusion (Blender 5.x Fast GI, ambient-occlusion-only method; ``use_gtao`` no longer exists) and
  screen-space ray tracing (12.3 scenario B); a series above 10 s/frame at
  1440p stops and reports (12.4 rule 5);
- ``cycles_hero``: Cycles, 64 samples with denoise (12.4 scene S6), only with a written ``why`` (CN-17).

Settings the roadmap leaves open (ambient occlusion on ``eevee_fast``, a time budget for ``eevee_fast`` and ``cycles_hero``) are
``None`` here: Blender keeps its own default and ICW-09's pod plan (OR-23) names the value before a paid run. ``SMOKE`` is not a
profile: it is the CI override of 12.4 step 1 (Workbench, 8 frames, 320x180 = 12.5 % of the 2560x1440 master), recorded as engine
``workbench`` in the render manifest so a smoke row can never pass for a profile's speed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

ENGINES = ("eevee", "cycles", "workbench")


@dataclass(frozen=True)
class RenderProfile:
    name: str
    engine: str                       # eevee | cycles | workbench
    recipe: str                       # shot_spec/2 recipe this profile renders (CN-17)
    samples: int
    ambient_occlusion: bool | None    # None = Blender's default (not set)
    raytracing: bool | None           # EEVEE's screen-space ray tracing (the SSR of older EEVEE)
    denoise: bool
    max_s_per_frame_1440: float | None  # a series slower than this stops and reports (12.4 rule 5); None = no stop rule yet

    def job_type(self, tier: str = "1440") -> str:
        """The ``config/job_speeds.json`` job type this profile's measured rows live under."""
        return f"blender_frame_{self.name}_{tier}"

    def settings(self, render: dict | None = None) -> dict:
        """What ``bpy/render_shot.py`` applies: the profile's switches, with the shot spec's ``render`` block over them."""
        out = asdict(self)
        r = render or {}
        for k in ("samples", "denoise", "motion_blur"):
            if k in r:
                out[k] = r[k]
        out.setdefault("motion_blur", False)
        return out


PROFILES = {
    "eevee_fast": RenderProfile("eevee_fast", "eevee", "blender_eevee/1", 16, None, False, False, None),
    "eevee_full": RenderProfile("eevee_full", "eevee", "blender_eevee/1", 64, True, True, False, 10.0),
    "cycles_hero": RenderProfile("cycles_hero", "cycles", "blender_cycles/1", 64, None, None, True, None),
}


@dataclass(frozen=True)
class SmokeOverride:
    engine: str = "workbench"
    frames: int = 8
    percent: float = 12.5            # of the 2560x1440 master: 320x180
    width: int = 320
    height: int = 180


SMOKE = SmokeOverride()


def get(name: str) -> RenderProfile:
    if name not in PROFILES:
        raise KeyError(f"unknown render profile {name!r} (known: {', '.join(PROFILES)})")
    return PROFILES[name]
