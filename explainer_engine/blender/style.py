"""The Ink Chronicle style engine (roadmap 9.1, D-102, BP-173): real 3D geometry finished as an illustrated / graphic-novel frame.

``StyleEngine(tokens).graph(path, camera=...)`` returns a ``style_graph/1`` document: plain data (node trees, the Line Art settings,
the colour management, the engine switches) that ``bpy/render_shot.py`` builds inside Blender. This file never imports ``bpy``
(only ``bpy/render_shot.py`` does, roadmap section 11), so the whole look is unit-tested as a recorded graph without Blender
(``tests/unit/test_blender_style.py``) and the same document is what the style-sheet renders on CI used.

Two paths, one look:

- ``eevee`` (the house path): Diffuse BSDF -> Shader to RGB -> luminance -> a CONSTANT ColorRamp of ``steps`` tones -> times the
  base colour -> plus a rim (Layer Weight facing -> CONSTANT ramp) -> Emission. Shader to RGB is EEVEE-only and the Blender 5.2
  manual calls it unreliable with ambient occlusion, soft shadows, screen-space reflections and render passes (roadmap 9.1), so
  this path turns EEVEE's ray tracing and AO off and keeps the sun's shadow hard (``key_light.angle_deg``).
- ``cycles_safe`` (the ``cycles_hero`` path): no Shader to RGB. The tone comes from the angle between the surface normal and the
  key light (Geometry normal . light vector -> the same CONSTANT ramp), so the steps are identical in both engines; cast shadows
  are not part of this variant (Cycles has no shader-side light readback). ICW-09 compares it with the EEVEE look before any
  Cycles shot enters an episode (roadmap 9.1).

Both paths share the Line Art (a Grease Pencil "scene" line art object, crease ``crease_deg``), the paper (a frame-wide overlay of
the paper texture in the compositor at ``paper_opacity``) and the grade (AgX, look "Medium High Contrast").

MEASURED on Blender 5.2.3 (build e13b728c6880, this package, 2026-11-05):

- the look's RNA id is ``"AgX - Medium High Contrast"`` once the view transform is AgX (the enum lists only prefixed names); the
  bare name of the bible and the manual is refused. ``LOOK_IDS`` keeps both and the Blender side tries them in order.
- Grease Pencil v3 Line Art has no screen-space thickness; its ``radius`` is in metres. A vertical edge facing the camera drew
  ``LINE_PX_PER_RADIUS`` x radius / (metres per pixel) pixels of ink (coverage, 2560x1440, lens 35 mm, distance 5 and 10 m,
  radius 0.02: 0.959 and 0.948). ``line_radius`` turns the bible's pixel weight into a radius at the camera's focus distance:
  nearer lines draw thicker, farther ones thinner, as an inked drawing does.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path


SCHEMA = "style_graph/1"
PATHS = ("eevee", "cycles_safe")
MASTER_W, MASTER_H = 2560, 1440
LINE_PX_PER_RADIUS = 0.955          # measured, see the module docstring
LOOK_IDS = {"Medium High Contrast": ("AgX - Medium High Contrast", "Medium High Contrast")}
PALETTE_PATH = Path(__file__).resolve().parents[1] / "design" / "palette.json"


def palette() -> dict[str, str]:
    """Token -> hex from ``design/palette.json`` (the only place hex values live)."""
    doc = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
    return {k: v["hex"] for k, v in doc["tokens"].items()}


def srgb_to_linear(hex_color: str) -> tuple[float, float, float]:
    """A palette hex as Blender's scene-linear RGB (the sRGB transfer of IEC 61966-2-1), rounded to 6 places for stable graphs."""
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(round(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4, 6))
    return tuple(out)  # type: ignore[return-value]


def rgba(hex_color: str) -> list[float]:
    return [*srgb_to_linear(hex_color), 1.0]


@dataclass(frozen=True)
class KeyLight:
    """The one key light per frame of the bible's camera language: a sun, hard-edged so the toon steps cut cleanly."""
    elevation_deg: float = 48.0
    azimuth_deg: float = 35.0       # around +Z, 0 = the light comes from -Y (behind the default camera)
    energy: float = 2.2
    angle_deg: float = 1.0          # the sun's disc: small = hard shadow edge (Shader to RGB + soft shadows is unreliable, 9.1)

    def direction(self) -> tuple[float, float, float]:
        """Unit vector from the surface TOWARDS the light (what the Cycles-safe tone dots with the normal)."""
        el, az = math.radians(self.elevation_deg), math.radians(self.azimuth_deg)
        return (round(math.sin(az) * math.cos(el), 6), round(-math.cos(az) * math.cos(el), 6), round(math.sin(el), 6))

    def rotation_euler(self) -> tuple[float, float, float]:
        """Blender sun rotation whose -Z axis points along -direction()."""
        return (round(math.radians(90.0 - self.elevation_deg), 6), 0.0, round(math.radians(self.azimuth_deg), 6))


@dataclass(frozen=True)
class StyleTokens:
    """The structured style tokens of world bible v1.5 (roadmap 9.1). Bible-fixed: steps, crease, paper opacity, view transform and
    look. Variant knobs (the collage): line weight inside BP-173's band, the tone values and the rim strength."""
    line_px: float = 2.25                                   # at 2560x1440 (BP-173 weight_px_1440 band)
    crease_deg: float = 134.0                               # BP-173
    steps: int = 3
    tones: tuple[float, ...] = (0.46, 0.72, 1.0)            # light multipliers of the three steps, dark -> lit
    thresholds: tuple[float, ...] = (0.12, 0.45)            # where the next step starts (light luminance / N.L)
    rim: bool = True
    rim_strength: float = 0.22                              # added light at the silhouette
    rim_width: float = 0.25                                 # Layer Weight blend
    rim_cut: float = 0.62                                   # facing value where the rim starts
    paper_opacity: float = 0.12
    texture_strength: float = 0.15                          # how much of an imported photo texture survives over its mean colour
    view_transform: str = "AgX"
    look: str = "Medium High Contrast"
    ink: str = "ink"                                        # palette token of the line
    paper: str = "paper"                                    # palette token of the backdrop
    ambient: float = 0.05                                   # world light strength (the backdrop colour is for camera rays only)
    key_light: KeyLight = field(default_factory=KeyLight)
    # The light profile (the creator, 2026-11-05: frame quality and palette first, shadows and reflections secondary, nothing that
    # makes the video renders heavy): no cast shadows by default; the steps come from the key light's angle alone.
    shadows: bool = False
    # Emit the colours AgX turns back into the palette hex (grade.py, agx_palette_match.json) instead of the raw hex.
    palette_match: bool = False

    def __post_init__(self) -> None:
        # BP-173's weight band is enforced where the registry lists it (core/contracts.py, CN-17 on every shot_spec/2 the
        # tokens go into); this module reads no threshold until ICW-07 adds it to BP-173's enforced_by.
        if not self.line_px > 0:
            raise ValueError(f"line weight {self.line_px} px is not a width")
        if len(self.tones) != self.steps or len(self.thresholds) != self.steps - 1:
            raise ValueError(f"{self.steps} steps need {self.steps} tones and {self.steps - 1} thresholds")
        if list(self.thresholds) != sorted(self.thresholds) or not all(0 < t < 1 for t in self.thresholds):
            raise ValueError("thresholds rise strictly inside 0..1")
        if not 0 <= self.paper_opacity <= 1:
            raise ValueError("paper opacity is a share 0..1")
        if self.look not in LOOK_IDS:
            raise ValueError(f"unknown look {self.look!r} (known: {', '.join(LOOK_IDS)})")

    @classmethod
    def from_look(cls, look: dict, **over) -> "StyleTokens":
        """Tokens from a shot_spec/2 ``look`` block (line_weight_px, crease_deg, shading_steps, view_transform, grade_look, paper)."""
        steps = look.get("shading_steps", 3)
        if steps != 3:
            raise ValueError("bible v1.5 shades in three steps; another count needs a bible bump")
        return cls(line_px=look["line_weight_px"], crease_deg=look["crease_deg"], view_transform=look["view_transform"],
                   look=look["grade_look"], paper_opacity=look["paper"]["opacity"], **over)

    @classmethod
    def from_bible(cls, bible: dict | None = None) -> "StyleTokens":
        """Tokens from the bible's ``style`` block (missing keys keep the defaults above)."""
        if bible is None:
            from explainer_engine.world import bible as B
            bible = B.load()
        st = bible.get("style") or {}
        kw: dict = {}
        line, shading, paper, grade = st.get("line", {}), st.get("shading", {}), st.get("paper", {}), st.get("grade", {})
        if "weight_px_1440" in line:
            kw["line_px"] = line["weight_px_1440"]
        if "crease_deg" in line:
            kw["crease_deg"] = line["crease_deg"]
        for k in ("steps", "rim_strength"):
            if k in shading:
                kw[k] = shading[k]
        if "tones" in shading:
            kw["tones"] = tuple(shading["tones"])
        if "thresholds" in shading:
            kw["thresholds"] = tuple(shading["thresholds"])
        if "rim" in shading:
            kw["rim"] = bool(shading["rim"])
        if "opacity" in paper:
            kw["paper_opacity"] = paper["opacity"]
        if "view_transform" in grade:
            kw["view_transform"] = grade["view_transform"]
        if "look" in grade:
            kw["look"] = grade["look"]
        return cls(**kw)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tones"], d["thresholds"] = list(self.tones), list(self.thresholds)
        return d


# The collage variants (invariant 6: a new style is one collage of variants for the creator's choice). Every variant stays inside
# the bible's fixed tokens (three steps, crease 134, paper 0.12, AgX Medium High Contrast); they differ only in line weight, tone
# depth and rim, the knobs the bible leaves as a band.
VARIANTS = {
    "A": {"label": "A  fine ink, soft shade", "line_px": 1.5, "tones": (0.58, 0.80, 1.0), "rim_strength": 0.14},
    "B": {"label": "B  medium ink, balanced shade", "line_px": 2.25, "tones": (0.46, 0.72, 1.0), "rim_strength": 0.22},
    "C": {"label": "C  bold ink, deep shade", "line_px": 3.0, "tones": (0.32, 0.62, 1.0), "rim_strength": 0.30},
}


def variant(name: str, base: StyleTokens | None = None) -> StyleTokens:
    if name not in VARIANTS:
        raise KeyError(f"unknown style variant {name!r} (known: {', '.join(VARIANTS)})")
    v = {k: val for k, val in VARIANTS[name].items() if k != "label"}
    return replace(base or StyleTokens(), **v)


def line_radius(px: float, distance_m: float, lens_mm: float, *, sensor_mm: float = 36.0, width: int = MASTER_W,
                out_width: int | None = None) -> float:
    """The Line Art radius (metres) that draws ``px`` pixels of ink at ``distance_m`` from the camera on the 2560-wide master.
    ``out_width`` < 2560 (a smaller test render) keeps the same look: the radius is in metres, so the line scales with the frame."""
    if distance_m <= 0 or lens_mm <= 0:
        raise ValueError("distance and lens are positive")
    metres_per_px = 2 * distance_m * (sensor_mm / 2) / lens_mm / width
    return round(px * metres_per_px / LINE_PX_PER_RADIUS, 6)


# --- node graphs ---------------------------------------------------------------------------------------------------------------
# A graph is {"nodes": [{"id", "type", "props"?, "inputs"?, "ramp"?}], "links": [[from_id, out_socket, to_id, in_socket]]}.
# Sockets are names, or integers where Blender's Mix node repeats a name per data type (inputs 6/7 = A/B colour, output 2 =
# Result colour). ``ramp`` = {"interpolation", "stops": [[position, rgba], ...]}. The Blender side builds exactly this.

def _keys(graph: dict) -> dict:
    """Input keys as strings (JSON objects need them; ``"6"`` is socket index 6 on the Blender side)."""
    for n in graph["nodes"]:
        if "inputs" in n:
            n["inputs"] = {str(k): v for k, v in n["inputs"].items()}
    return graph


def _ramp(positions: list[float], values: list[float]) -> dict:
    return {"interpolation": "CONSTANT", "stops": [[round(p, 6), [round(v, 6)] * 3 + [1.0]] for p, v in zip(positions, values)]}


class StyleEngine:
    """Tokens -> the style_graph/1 document of one path. Pure data, deterministic: the same tokens give the same bytes."""

    def __init__(self, tokens: StyleTokens | None = None) -> None:
        self.t = tokens or StyleTokens()
        self.pal = palette()

    # -- materials --
    def _tone_nodes(self, path: str) -> tuple[list[dict], list[list], str]:
        """Nodes that end in a node ``tone`` whose Color output is the stepped light value (grey)."""
        t = self.t
        ramp = _ramp([0.0, *t.thresholds], list(t.tones))
        if path == "eevee":
            nodes = [{"id": "diffuse", "type": "ShaderNodeBsdfDiffuse", "inputs": {"Color": [1.0, 1.0, 1.0, 1.0], "Roughness": 0.0}},
                     {"id": "to_rgb", "type": "ShaderNodeShaderToRGB"},
                     {"id": "luma", "type": "ShaderNodeRGBToBW"},
                     {"id": "tone", "type": "ShaderNodeValToRGB", "ramp": ramp}]
            links = [["diffuse", "BSDF", "to_rgb", "Shader"], ["to_rgb", "Color", "luma", "Color"], ["luma", "Val", "tone", "Fac"]]
        elif path == "cycles_safe":
            d = list(self.t.key_light.direction())
            nodes = [{"id": "geo", "type": "ShaderNodeNewGeometry"},
                     {"id": "ndotl", "type": "ShaderNodeVectorMath", "props": {"operation": "DOT_PRODUCT"}, "inputs": {1: d}},
                     {"id": "clamp", "type": "ShaderNodeMath", "props": {"operation": "MAXIMUM"}, "inputs": {1: 0.0}},
                     {"id": "tone", "type": "ShaderNodeValToRGB", "ramp": ramp}]
            links = [["geo", "Normal", "ndotl", 0], ["ndotl", "Value", "clamp", 0], ["clamp", "Value", "tone", "Fac"]]
        else:
            raise ValueError(f"unknown style path {path!r} (known: {', '.join(PATHS)})")
        return nodes, links, "tone"

    def colour(self, name_or_hex: str) -> list[float]:
        """A palette token or hex as the RGBA the frame emits: the hex in linear RGB, or (``palette_match``) the value whose AgX
        display is the hex (grade.matched; a stale or missing table entry is refused)."""
        h = self.pal.get(name_or_hex, name_or_hex)
        if self.t.palette_match:
            from explainer_engine.blender import grade
            return [*grade.matched(h), 1.0]
        return rgba(h)

    def material(self, name: str, base: str | list[float], *, path: str = "eevee", texture: str | None = None,
                 texture_mean: list[float] | None = None, tile: float | None = None) -> dict:
        """One toon material. ``base`` is a palette token, a hex or a linear RGBA; ``texture`` (an image path, the library file of
        a converted asset) is kept at ``texture_strength`` over ``texture_mean`` (its mean colour, linear), so a photo texture
        becomes a flat colour field with a trace of its grain (no raw PBR look, D-102); ``tile`` repeats it over the UVs (a
        ground plane), else the asset's own UVs are used."""
        t = self.t
        if isinstance(base, str):
            base_rgba = self.colour(base)
        else:
            base_rgba = [round(float(x), 6) for x in base][:3] + [1.0]
        nodes, links, tone = self._tone_nodes(path)
        nodes.append({"id": "base", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                      "inputs": {"Factor": 1.0, 6: base_rgba}})
        links.append([tone, "Color", "base", 7])
        if texture is not None:
            mean = [round(float(x), 6) for x in (texture_mean or base_rgba[:3])][:3] + [1.0]
            nodes += [{"id": "tex", "type": "ShaderNodeTexImage", "props": {"interpolation": "Linear"}, "image": texture},
                      {"id": "flatten", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MIX"},
                       "inputs": {"Factor": t.texture_strength, 6: mean}}]
            links += [["tex", "Color", "flatten", 7], ["flatten", 2, "base", 6]]
            if tile is not None:
                nodes += [{"id": "uv", "type": "ShaderNodeTexCoord"},
                          {"id": "tiling", "type": "ShaderNodeMapping", "inputs": {"Scale": [float(tile), float(tile), 1.0]}}]
                links += [["uv", "UV", "tiling", "Vector"], ["tiling", "Vector", "tex", "Vector"]]
        last = "base"
        if t.rim:
            rim = round(t.rim_strength, 6)
            nodes += [{"id": "facing", "type": "ShaderNodeLayerWeight", "inputs": {"Blend": t.rim_width}},
                      {"id": "rim_cut", "type": "ShaderNodeValToRGB",
                       "ramp": {"interpolation": "CONSTANT", "stops": [[0.0, [0.0, 0.0, 0.0, 1.0]], [t.rim_cut, [1.0, 1.0, 1.0, 1.0]]]}},
                      {"id": "rim", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "ADD"},
                       "inputs": {7: [rim, rim, rim, 1.0]}}]
            links += [["facing", "Facing", "rim_cut", "Fac"], ["rim_cut", "Color", "rim", "Factor"], ["base", 2, "rim", 6]]
            last = "rim"
        nodes += [{"id": "emit", "type": "ShaderNodeEmission", "inputs": {"Strength": 1.0}},
                  {"id": "out", "type": "ShaderNodeOutputMaterial"}]
        links += [[last, 2, "emit", "Color"], ["emit", "Emission", "out", "Surface"]]
        return _keys({"name": name, "path": path, "nodes": nodes, "links": links})

    # -- world, line, paper, scene --
    def world(self, *, hdri: str | None = None) -> dict:
        """Camera rays see the paper colour; lighting is a weak ambient (or the HDRI at the same strength, for its colour only)."""
        t = self.t
        paper = rgba(self.pal[t.paper])  # the ambient light keeps the plain paper value (a matched one is a display target)
        nodes = [{"id": "light", "type": "ShaderNodeBackground", "inputs": {"Color": paper, "Strength": t.ambient}},
                 {"id": "backdrop", "type": "ShaderNodeBackground", "inputs": {"Color": self.colour(t.paper), "Strength": 1.0}},
                 {"id": "is_cam", "type": "ShaderNodeLightPath"},
                 {"id": "mix", "type": "ShaderNodeMixShader"},
                 {"id": "out", "type": "ShaderNodeOutputWorld"}]
        links = [["is_cam", "Is Camera Ray", "mix", "Fac"], ["light", "Background", "mix", 1], ["backdrop", "Background", "mix", 2],
                 ["mix", "Shader", "out", "Surface"]]
        if hdri is not None:
            nodes.insert(0, {"id": "env", "type": "ShaderNodeTexEnvironment", "image": hdri})
            links.insert(0, ["env", "Color", "light", "Color"])
        return _keys({"nodes": nodes, "links": links})

    def line_art(self, *, distance_m: float, lens_mm: float, sensor_mm: float = 36.0) -> dict:
        t = self.t
        return {"radius": line_radius(t.line_px, distance_m, lens_mm, sensor_mm=sensor_mm), "line_px_1440": t.line_px,
                "focus_distance_m": round(distance_m, 4), "crease_threshold_rad": round(math.radians(t.crease_deg), 6),
                "crease_deg": t.crease_deg, "ink_rgba": self.colour(t.ink), "opacity": 1.0}

    def paper(self, texture: str | None) -> dict:
        """The frame-wide paper: the compositor stretches the texture's grain to 0..1 (Normalize: a paper scan is ~3 % grey
        variation) and overlays it at ``paper_opacity``. With ``palette_match`` the frame holds values above 1 (AgX's white needs
        them), where Overlay breaks, so the grain is a gain instead: frame x (1 + opacity x (2 x grain - 1)), the same +-opacity
        around the paper. Without a texture there is no paper pass (never a fake grain)."""
        t = self.t
        if texture is None:
            return {"enabled": False, "opacity": t.paper_opacity}
        nodes = [{"id": "render", "type": "CompositorNodeRLayers"},
                 {"id": "paper", "type": "CompositorNodeImage", "image": texture},
                 {"id": "fit", "type": "CompositorNodeScale", "inputs": {"Type": "Render Size", "Frame Type": "Crop"}},  # 5.2: menu inputs
                 {"id": "grey", "type": "CompositorNodeRGBToBW"},
                 {"id": "stretch", "type": "CompositorNodeNormalize"},
                 {"id": "out", "type": "NodeGroupOutput"}]
        links = [["paper", "Image", "fit", "Image"], ["fit", "Image", "grey", "Image"], ["grey", "Val", "stretch", 0]]
        if t.palette_match:
            o = round(t.paper_opacity, 6)
            nodes[-1:-1] = [{"id": "gain", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY_ADD"},
                             "inputs": {1: round(2 * o, 6), 2: round(1 - o, 6)}},
                            {"id": "overlay", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                             "inputs": {"Factor": 1.0}}]
            links += [["stretch", 0, "gain", 0], ["render", "Image", "overlay", 6], ["gain", "Value", "overlay", 7],
                      ["overlay", 2, "out", "Image"]]
        else:
            nodes[-1:-1] = [{"id": "overlay", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "OVERLAY"},
                             "inputs": {"Factor": t.paper_opacity}}]
            links += [["render", "Image", "overlay", 6], ["stretch", 0, "overlay", 7], ["overlay", 2, "out", "Image"]]
        return _keys({"enabled": True, "opacity": t.paper_opacity, "texture": texture, "nodes": nodes, "links": links})

    def scene_settings(self, path: str) -> dict:
        t = self.t
        out = {"view_transform": t.view_transform, "look": t.look, "look_ids": list(LOOK_IDS[t.look]),
               "film_transparent": False}
        if path == "eevee":
            out["engine"] = "eevee"
            # 9.1: no screen-space ray tracing / AO under Shader to RGB (EEVEE 5.2 has no separate AO switch: ``use_gtao`` is gone,
            # its horizon scan belongs to ray tracing and fast GI)
            out["eevee"] = {"use_raytracing": False, "use_fast_gi": False, "use_shadows": t.shadows}
        else:
            out["engine"] = "cycles"
            out["cycles"] = {"max_bounces": 0, "use_denoising": False}  # emission-only shading: no light bounces to compute
        return out

    def graph(self, path: str = "eevee", *, camera: dict, materials: dict[str, dict] | None = None, hdri: str | None = None,
              paper_texture: str | None = None) -> dict:
        """The whole style_graph/1 document. ``camera`` = {lens_mm, focus_distance_m[, sensor_mm]}; ``materials`` = name ->
        material() kwargs (``base`` and optional ``texture``/``texture_mean``)."""
        if path not in PATHS:
            raise ValueError(f"unknown style path {path!r} (known: {', '.join(PATHS)})")
        kl = self.t.key_light
        doc = {"schema": SCHEMA, "path": path, "tokens": self.t.to_dict(),
               "scene": self.scene_settings(path),
               "key_light": {"type": "SUN", "energy": kl.energy, "angle_rad": round(math.radians(kl.angle_deg), 6),
                             "rotation_euler": list(kl.rotation_euler()), "direction": list(kl.direction()),
                             "use_shadow": self.t.shadows},
               "world": self.world(hdri=hdri),
               "line_art": self.line_art(distance_m=camera["focus_distance_m"], lens_mm=camera["lens_mm"],
                                         sensor_mm=camera.get("sensor_mm", 36.0)),
               "paper": self.paper(paper_texture),
               "materials": [self.material(n, path=path, **kw) for n, kw in sorted((materials or {}).items())]}
        doc["sha256"] = digest(doc)
        return doc


def digest(doc: dict) -> str:
    body = {k: v for k, v in doc.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check(doc: dict) -> list[str]:
    """Problems with a style_graph/1 document: unknown nodes in links, a missing output, a path whose rules it breaks."""
    out = []
    if doc.get("schema") != SCHEMA:
        return [f"not a {SCHEMA} document"]
    if doc.get("sha256") != digest(doc):
        out.append("sha256 does not match the document (edited after it was made)")
    trees = [(f"material {m['name']}", m) for m in doc["materials"]] + [("world", doc["world"])]
    if doc["paper"].get("enabled"):
        trees.append(("paper", doc["paper"]))
    for where, g in trees:
        ids = [n["id"] for n in g["nodes"]]
        if len(ids) != len(set(ids)):
            out.append(f"{where}: duplicate node ids")
        for a, _, b, _ in g["links"]:
            if a not in ids or b not in ids:
                out.append(f"{where}: link {a} -> {b} names a node that is not in the graph")
    for m in doc["materials"]:
        types = {n["type"] for n in m["nodes"]}
        if doc["path"] == "cycles_safe" and "ShaderNodeShaderToRGB" in types:
            out.append(f"material {m['name']}: Shader to RGB on the Cycles-safe path (EEVEE-only, 9.1)")
        if "ShaderNodeOutputMaterial" not in types or "ShaderNodeEmission" not in types:
            out.append(f"material {m['name']}: no emission output")
        if "ShaderNodeBsdfPrincipled" in types:
            out.append(f"material {m['name']}: a Principled BSDF is the raw PBR look (D-102)")
    if doc["path"] == "eevee":
        ee = doc["scene"]["eevee"]
        if ee.get("use_raytracing") or ee.get("use_gtao") or ee.get("use_fast_gi"):
            out.append("EEVEE ray tracing / AO on under Shader to RGB (unreliable, 9.1)")
    if not doc["line_art"]["line_px_1440"] > 0:
        out.append(f"line weight {doc['line_art']['line_px_1440']} px is not a width")
    return out


def with_paths(doc: dict, mapping: dict[str, str]) -> dict:
    """The same graph with image paths replaced (the CI runner's cache differs from the machine that planned the job)."""
    d = copy.deepcopy(doc)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("image", "texture") and isinstance(v, str) and v in mapping:
                    o[k] = mapping[v]
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    d["sha256"] = digest(d)
    return d
