"""Tactile historical war-room map renderer and frame-locked AudioEventEmitter (Step 4).

Upgrades the map/helper lane with:
1. Parchment vignette and warm oil-lamp lighting falloff over the relief plate.
2. Frame-locked ``AudioEventEmitter`` that binds ``pencil_line__v1``, ``chalk_line__v1``,
   ``thud_soft__v1``, and ``ui_click_kenney__v1`` strictly to the frames where ``ds/df > 0``
   (fixing Pass-1 defect where ``mix.py`` played drawing sounds during static map holds).
3. Exact terminal counter landing (``100,000 men (estimate)`` at ``end_frame - 18``).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from explainer_engine.maps import actions as MA
from explainer_engine.maps import draw as D


class AudioEventEmitter:
    """Collects and queries frame-locked audio events from a resolved map plan."""

    def __init__(self, plan_doc: dict):
        self.plan_doc = plan_doc
        self.events = list(plan_doc.get("frame_locked_audio_events") or MA.emit_frame_locked_audio_events(plan_doc))

    def active_at_frame(self, f: int) -> list[dict]:
        return [ev for ev in self.events if int(ev["start_frame"]) <= f < int(ev["end_frame"])]

    def drawing_spans_s(self) -> list[tuple[float, float]]:
        return [(float(ev["start_s"]), float(ev["end_s"])) for ev in self.events if ev["class"] == "map_route_draw"]


class TactileMapRenderer:
    """Renders a map_action plan with warm war-room vignette and frame-locked audio event emission."""

    def __init__(self, plan_doc: dict, width: int = 1920, height: int = 1080, look: dict | None = None, ss: int = D.SS):
        self.plan = plan_doc
        self.width = width
        self.height = height
        self.look = look
        self.ss = ss
        self.base = MA.card_base(width, height, look) if plan_doc.get("card") else MA.Plate(plan_doc, width, height, look)
        self.emitter = AudioEventEmitter(plan_doc)
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        rx = (xx - width * 0.5) / (width * 0.5)
        ry = (yy - height * 0.5) / (height * 0.5)
        r2 = rx * rx + ry * ry
        self._vignette = np.clip(1.0 - 0.14 * (r2 ** 1.25), 0.78, 1.0)[..., None]

    def render_frame(self, f: int) -> Image.Image:
        im = MA.render_frame(self.plan, f, self.base, self.width, self.height, look=self.look, ss=self.ss)
        arr = np.asarray(im, dtype=np.float32) * self._vignette
        return Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), "RGB")

    def audio_events(self) -> list[dict]:
        return self.emitter.events
