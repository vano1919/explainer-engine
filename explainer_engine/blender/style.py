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
    # ICW-05c: the look round's knobs (``Look``, ``look_variants.json``). None = the ICW-05 toon graph, byte for byte as before.
    art: "Look | None" = None

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
        if self.art is None:
            d.pop("art")   # the ICW-05 graphs keep their bytes and hashes
        else:
            d["art"] = self.art.to_dict()
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


# --- the look round (ICW-05c, 2026-11-05) ------------------------------------------------------------------------------------
# The creator's reference (a stylized 3D-animation sheet, "like this, but less 3D"): soft painterly shading, a warm key with a
# cool fill and a bright rim, matte painted materials, soft-focus painted backgrounds, a warm limited palette, no hard outline.
# ``Look`` holds the independent knobs of that slider (look_variants.json, schema look_variants/1); every knob is plain data here
# and plain nodes in the graph, so a blend of two variants is one more JSON entry. Hex values still come only from the palette
# (or, for the reference-swatch map, from the proposal colours that look_variants.json lists until ICW-07 decides on them).

SHADE_MODES = ("toon", "soft", "feathered", "flat", "painted_light")
LIGHT_RIGS = ("cinematic", "key_rim", "flat_key", "ambient_only")
LINE_MODES = ("none", "faint", "dark", "ink")
BG_MODES = ("set", "dof", "plate", "flat")
SKIES = ("paper", "gradient", "hdri")
PALETTE_MAPS = ("raw", "warm_cinematic", "reference_swatches")
KUWAHARA_SCOPES = ("frame", "background")


def _tup(x) -> tuple:
    return tuple(tuple(v) if isinstance(v, list) else v for v in x)


@dataclass(frozen=True)
class Look:
    """One spot on the reference -> flat-painting slider. Shares are 0..1; colours are RGB multipliers (never hex)."""
    id: str = "custom"
    slider: int = 0                                         # 0 = the reference's stylized 3D, 10 = a flat painting of it
    shade_mode: str = "soft"
    ramp: tuple = ((0.0, 0.42), (0.35, 0.72), (0.9, 1.0))  # (light luminance, tone) stops; soft = blended between them
    feather: float = 0.0                                    # feathered: the width of each step's soft edge (luminance)
    shadow_tint: tuple = (0.86, 0.88, 1.0)                  # the dark end leans cool (the fill), the lit end warm (the key)
    light_tint: tuple = (1.0, 0.97, 0.9)
    brush: float = 0.0                                      # painted brush-stroke texture on the fills (share of value)
    halftone: float = 0.0                                   # dots in the darkest step (share darkened under a dot)
    texture_keep: float | None = None                       # at least this much of a set's photo texture survives (grounds, walls)
    costume_keep: float | None = None                       # how much of a costume's own painted atlas survives over its tint
    palette_map: str = "warm_cinematic"
    saturation: float = 0.9
    value: float = 1.0
    warmth: float = 0.25                                    # share of a warm multiply over every surface
    light_rig: str = "key_rim"
    shadow_softness_deg: float = 6.0                        # the sun's disc when the rig casts shadows (soft edge)
    fill: float = 0.45                                      # fill light energy (adds luminance on the shadow side)
    rim_strength: float = 0.3
    rim_tint: tuple = (1.0, 0.86, 0.66)
    rim_soft: float = 0.08                                  # facing band over which the rim fades in
    line_mode: str = "none"
    line_px: float = 1.5
    line_opacity: float = 1.0
    line_colour: str = "ink"                                # a palette token (faint/coloured lines use a warm dark token)
    bg_mode: str = "dof"
    fstop: float = 2.8
    sky: str = "gradient"
    kuwahara: int = 0                                       # Kuwahara size in px at 1440p (0 = off)
    kuwahara_scope: str = "frame"
    plate_kuwahara: int = 0                                 # Kuwahara size on the far background only (bg_mode plate)
    bleed: int = 0                                          # edge-aware blur of the fills, px at 1440p
    paper: float = 0.0                                      # paper as a multiply base, share
    grain: float = 0.0                                      # fine paint grain, share
    vignette: float = 0.0
    feel: str = ""

    def __post_init__(self) -> None:
        for name, val, known in (("shade_mode", self.shade_mode, SHADE_MODES), ("light_rig", self.light_rig, LIGHT_RIGS),
                                 ("line_mode", self.line_mode, LINE_MODES), ("bg_mode", self.bg_mode, BG_MODES),
                                 ("sky", self.sky, SKIES), ("palette_map", self.palette_map, PALETTE_MAPS),
                                 ("kuwahara_scope", self.kuwahara_scope, KUWAHARA_SCOPES)):
            if val not in known:
                raise ValueError(f"{self.id}: unknown {name} {val!r} (known: {', '.join(known)})")
        for name in ("brush", "halftone", "warmth", "paper", "grain", "vignette", "line_opacity", "feather", "rim_strength"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{self.id}: {name} {getattr(self, name)} is not a share 0..1")
        for name in ("texture_keep", "costume_keep"):
            if getattr(self, name) is not None and not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{self.id}: {name} is a share 0..1")
        pos = [p for p, _ in self.ramp]
        if not self.ramp or pos != sorted(pos) or len(set(pos)) != len(pos) or not all(0 <= p <= 1 for p in pos):
            raise ValueError(f"{self.id}: ramp positions rise strictly inside 0..1")
        if not all(0 < t <= 1.5 for _, t in self.ramp):
            raise ValueError(f"{self.id}: ramp tones are light multipliers 0..1.5")
        if not 0 <= self.slider <= 10:
            raise ValueError(f"{self.id}: slider is 0..10")
        if self.line_mode != "none" and not self.line_px > 0:
            raise ValueError(f"{self.id}: a drawn line needs a width")
        if not 0.5 <= self.fstop <= 64:
            raise ValueError(f"{self.id}: f-stop {self.fstop} outside 0.5..64")
        for name in ("kuwahara", "plate_kuwahara", "bleed"):
            if not 0 <= getattr(self, name) <= 40:
                raise ValueError(f"{self.id}: {name} {getattr(self, name)} px outside 0..40")

    @classmethod
    def from_dict(cls, d: dict) -> "Look":
        kw = {k: v for k, v in d.items() if k not in ("label",)}
        for k in ("ramp", "shadow_tint", "light_tint", "rim_tint"):
            if k in kw:
                kw[k] = _tup(kw[k])
        return cls(**kw)

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    @property
    def casts_shadows(self) -> bool:
        return self.light_rig == "cinematic" or self.shade_mode == "flat" and self.light_rig != "ambient_only"


def _mul(a, b) -> list[float]:
    return [round(x * y, 6) for x, y in zip(a, b)]


def _lerp(a, b, t) -> list[float]:
    return [round(x + (y - x) * t, 6) for x, y in zip(a, b)]


def _hex_scaled(hex_color: str, sat: float = 1.0, val: float = 1.0) -> str:
    import colorsys
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(hh, min(1.0, ss * sat), min(1.0, vv * val))
    return "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))


def _warm_neutral(hex_color: str) -> str:
    """The warm cinematic map on a token: a near-neutral (grey stone, the night blue-grey, the ink) turns to a warm neutral of the
    same value (the reference's stone and shadows are warm); saturated tokens keep their hue (the shader warms them)."""
    import colorsys
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    if ss >= 0.35:
        return hex_color
    r, g, b = colorsys.hsv_to_rgb(0.08, min(1.0, ss * 0.9 + 0.06), vv)
    return "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))


VARIANTS_PATH = Path(__file__).resolve().parent / "look_variants.json"
LOOK_SCHEMA = "look_variants/1"
SWATCH_SUFFIX = "_swatch"


def look_variants(path: Path | None = None) -> dict:
    """The look round's document (``look_variants.json``): ``variants`` (id -> knobs + label + feel), ``swatch_map`` (palette token
    -> the reference sheet's swatch, proposal colours), ``base`` (StyleTokens overrides every look shares)."""
    doc = json.loads(Path(path or VARIANTS_PATH).read_text(encoding="utf-8"))
    if doc.get("schema") != LOOK_SCHEMA:
        raise ValueError(f"{path or VARIANTS_PATH} is not a {LOOK_SCHEMA} document")
    return doc


def look_tokens(variant_id: str, *, doc: dict | None = None) -> StyleTokens:
    """StyleTokens for one look variant: the ICW-05 B tokens with the look attached (its line width as ``line_px``)."""
    doc = doc or look_variants()
    twin = variant_id.endswith(SWATCH_SUFFIX)
    vid = variant_id[: -len(SWATCH_SUFFIX)] if twin else variant_id
    v = next((x for x in doc["variants"] if x["id"] == vid), None)
    if twin and vid not in doc.get("swatch_twins", []):
        v = None
    if v is not None and twin:
        v = {**v, "id": variant_id, "palette_map": "reference_swatches", "label": v["label"] + ", reference swatches"}
    if v is None:
        raise KeyError(f"unknown look variant {variant_id!r} (known: {', '.join(x['id'] for x in doc['variants'])})")
    art = Look.from_dict(v)
    base = variant("B")
    return replace(base, line_px=art.line_px if art.line_mode != "none" else base.line_px, shadows=art.casts_shadows,
                   rim=art.rim_strength > 0, rim_strength=art.rim_strength, art=art)


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
        self.swatches = look_variants().get("swatch_map", {}) if self.t.art is not None else {}

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
                 texture_mean: list[float] | None = None, tile: float | None = None, strength: float | None = None,
                 slot: str | None = None) -> dict:
        """One toon material. ``base`` is a palette token, a hex or a linear RGBA; ``texture`` (an image path, the library file of
        a converted asset) is kept at ``texture_strength`` over ``texture_mean`` (its mean colour, linear), so a photo texture
        becomes a flat colour field with a trace of its grain (no raw PBR look, D-102); ``tile`` repeats it over the UVs (a
        ground plane), else the asset's own UVs are used. ``strength`` overrides the token's ``texture_strength`` for this material
        (a character's costume atlas keeps more of its own parts than a photo ground does; ICW-06). ``slot`` names a character
        material's role (``costume``): only the look round reads it (``Look.costume_keep``)."""
        if self.t.art is not None:
            if path != "eevee":
                raise ValueError(f"{name}: the look round's graphs are EEVEE-only (Shader to RGB)")
            return self._art_material(name, base, texture=texture, texture_mean=texture_mean, tile=tile, strength=strength, slot=slot)
        t = self.t
        if strength is not None and not 0 <= strength <= 1:
            raise ValueError(f"{name}: texture strength {strength} is not a share 0..1")
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
                       "inputs": {"Factor": t.texture_strength if strength is None else round(float(strength), 6), 6: mean}}]
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

    # -- the look round (ICW-05c): the same document shape, other node trees --
    def _art_colour(self, name_or_hex: str) -> list[float]:
        """A token through the look's palette map: ``reference_swatches`` swaps a token for its swatch (proposal colours of
        look_variants.json); the warm map is applied in the shader (it must reach textures too)."""
        a = self.t.art
        if a.palette_map == "reference_swatches" and name_or_hex in self.swatches:
            return rgba(self.swatches[name_or_hex])
        h = self.pal.get(name_or_hex, name_or_hex)
        return rgba(_warm_neutral(h) if a.palette_map == "warm_cinematic" else h)

    def _art_ramp(self) -> dict:
        a = self.t.art
        tone_of = lambda v: _lerp(a.shadow_tint, a.light_tint, min(1.0, max(0.0, (v - 0.4) / 0.6)))  # noqa: E731
        stop = lambda p, v: [round(p, 6), [*[round(v * c, 6) for c in tone_of(v)], 1.0]]  # noqa: E731
        if a.shade_mode == "feathered" and a.feather > 0:
            stops = [stop(a.ramp[0][0], a.ramp[0][1])]
            for (p0, v0), (p, v) in zip(a.ramp, a.ramp[1:]):
                lo, hi = max(p0 + 1e-3, p - a.feather / 2), min(1.0, p + a.feather / 2)
                stops += [stop(lo, v0), stop(hi, v)]
            return {"interpolation": "LINEAR", "stops": stops}
        interp = {"soft": "EASE", "painted_light": "LINEAR"}.get(a.shade_mode, "CONSTANT")
        return {"interpolation": interp, "stops": [stop(p, v) for p, v in a.ramp]}

    def _art_material(self, name: str, base, *, texture=None, texture_mean=None, tile=None, strength=None, slot=None) -> dict:
        t, a = self.t, self.t.art
        keep = t.texture_strength if strength is None else float(strength)
        if texture is not None:
            if slot == "costume" and a.costume_keep is not None:   # the costume's own painted atlas over the shot's tint
                keep = a.costume_keep
            elif strength is None and a.texture_keep is not None:  # a set's photo texture (grounds, walls, props)
                keep = max(keep, a.texture_keep)
        if not 0 <= keep <= 1:
            raise ValueError(f"{name}: texture strength {keep} is not a share 0..1")
        base_rgba = self._art_colour(base) if isinstance(base, str) else [round(float(x), 6) for x in base][:3] + [1.0]
        if a.shade_mode == "painted_light":   # light painted onto the form: a soft top-to-bottom gradient, no live light
            nodes = [{"id": "coords", "type": "ShaderNodeTexCoord"},
                     {"id": "xyz", "type": "ShaderNodeSeparateXYZ"},
                     {"id": "tone", "type": "ShaderNodeValToRGB", "ramp": self._art_ramp()}]
            links = [["coords", "Generated", "xyz", "Vector"], ["xyz", "Z", "tone", "Fac"]]
        else:
            nodes = [{"id": "diffuse", "type": "ShaderNodeBsdfDiffuse", "inputs": {"Color": [1.0, 1.0, 1.0, 1.0], "Roughness": 0.0}},
                     {"id": "to_rgb", "type": "ShaderNodeShaderToRGB"},
                     {"id": "luma", "type": "ShaderNodeRGBToBW"},
                     {"id": "tone", "type": "ShaderNodeValToRGB", "ramp": self._art_ramp()}]
            links = [["diffuse", "BSDF", "to_rgb", "Shader"], ["to_rgb", "Color", "luma", "Color"], ["luma", "Val", "tone", "Fac"]]
        nodes.append({"id": "base", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                      "inputs": {"Factor": 1.0, 6: base_rgba}})
        links.append(["tone", "Color", "base", 7])
        if texture is not None:
            mean = [round(float(x), 6) for x in (texture_mean or base_rgba[:3])][:3] + [1.0]
            nodes += [{"id": "tex", "type": "ShaderNodeTexImage", "props": {"interpolation": "Linear"}, "image": texture},
                      {"id": "flatten", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MIX"},
                       "inputs": {"Factor": round(keep, 6), 6: mean}}]
            links += [["tex", "Color", "flatten", 7], ["flatten", 2, "base", 6]]
            if tile is not None:
                nodes += [{"id": "uv", "type": "ShaderNodeTexCoord"},
                          {"id": "tiling", "type": "ShaderNodeMapping", "inputs": {"Scale": [float(tile), float(tile), 1.0]}}]
                links += [["uv", "UV", "tiling", "Vector"], ["tiling", "Vector", "tex", "Vector"]]
        last = "base"
        if a.brush > 0:   # brush strokes: a stretched object-space noise modulates the fill's value by +-brush
            b = round(a.brush, 6)
            nodes += [{"id": "brush_uv", "type": "ShaderNodeTexCoord"},
                      {"id": "brush_dir", "type": "ShaderNodeMapping", "inputs": {"Scale": [3.0, 3.0, 18.0]}},
                      {"id": "brush_noise", "type": "ShaderNodeTexNoise", "inputs": {"Scale": 4.0, "Detail": 3.0, "Roughness": 0.6}},
                      {"id": "brush_gain", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY_ADD"},
                       "inputs": {1: round(2 * b, 6), 2: round(1 - b, 6)}},
                      {"id": "brush", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": 1.0}}]
            links += [["brush_uv", "Object", "brush_dir", "Vector"], ["brush_dir", "Vector", "brush_noise", "Vector"],
                      ["brush_noise", "Fac", "brush_gain", 0], [last, 2, "brush", 6], ["brush_gain", "Value", "brush", 7]]
            last = "brush"
        if a.halftone > 0 and a.shade_mode != "painted_light":   # print dots, only where the light is in the darkest step
            k = 900.0
            nodes += [{"id": "ht_uv", "type": "ShaderNodeTexCoord"},
                      {"id": "ht_xyz", "type": "ShaderNodeSeparateXYZ"},
                      {"id": "ht_x", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY"}, "inputs": {1: round(k * 16 / 9, 3)}},
                      {"id": "ht_y", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY"}, "inputs": {1: k}},
                      {"id": "ht_sx", "type": "ShaderNodeMath", "props": {"operation": "SINE"}},
                      {"id": "ht_sy", "type": "ShaderNodeMath", "props": {"operation": "SINE"}},
                      {"id": "ht_prod", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY"}},
                      {"id": "ht_dot", "type": "ShaderNodeMath", "props": {"operation": "GREATER_THAN"}, "inputs": {1: 0.3}},
                      {"id": "ht_dark", "type": "ShaderNodeMath", "props": {"operation": "LESS_THAN"},
                       "inputs": {1: round(a.ramp[1][0] if len(a.ramp) > 1 else 0.2, 6)}},
                      {"id": "ht_mask", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY"}},
                      {"id": "halftone", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {7: [round(1 - a.halftone, 6)] * 3 + [1.0]}}]
            links += [["ht_uv", "Window", "ht_xyz", "Vector"], ["ht_xyz", "X", "ht_x", 0], ["ht_xyz", "Y", "ht_y", 0],
                      ["ht_x", "Value", "ht_sx", 0], ["ht_y", "Value", "ht_sy", 0], ["ht_sx", "Value", "ht_prod", 0],
                      ["ht_sy", "Value", "ht_prod", 1], ["ht_prod", "Value", "ht_dot", 0], ["luma", "Val", "ht_dark", 0],
                      ["ht_dot", "Value", "ht_mask", 0], ["ht_dark", "Value", "ht_mask", 1], ["ht_mask", "Value", "halftone", "Factor"],
                      [last, 2, "halftone", 6]]
            last = "halftone"
        if a.palette_map == "warm_cinematic" or a.saturation != 1 or a.value != 1:
            nodes += [{"id": "grade", "type": "ShaderNodeHueSaturation",
                       "inputs": {"Hue": 0.5, "Saturation": round(a.saturation, 6), "Value": round(a.value, 6), "Fac": 1.0}}]
            links += [[last, 2, "grade", "Color"]]
            last, out_sock = "grade", "Color"
        else:
            out_sock = 2
        if a.warmth > 0:
            nodes += [{"id": "warm", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": round(a.warmth, 6), 7: [1.0, 0.86, 0.68, 1.0]}}]
            links += [[last, out_sock, "warm", 6]]
            last, out_sock = "warm", 2
        if a.rim_strength > 0:
            rim = [round(a.rim_strength * c, 6) for c in a.rim_tint] + [1.0]
            cut = t.rim_cut
            nodes += [{"id": "facing", "type": "ShaderNodeLayerWeight", "inputs": {"Blend": t.rim_width}},
                      {"id": "rim_cut", "type": "ShaderNodeValToRGB",
                       "ramp": {"interpolation": "LINEAR", "stops": [[round(max(0.0, cut - a.rim_soft), 6), [0.0, 0.0, 0.0, 1.0]],
                                                                       [cut, [1.0, 1.0, 1.0, 1.0]]]}},
                      {"id": "rim", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "ADD"}, "inputs": {7: rim}}]
            links += [["facing", "Facing", "rim_cut", "Fac"], ["rim_cut", "Color", "rim", "Factor"], [last, out_sock, "rim", 6]]
            last, out_sock = "rim", 2
        nodes += [{"id": "emit", "type": "ShaderNodeEmission", "inputs": {"Strength": 1.0}},
                  {"id": "out", "type": "ShaderNodeOutputMaterial"}]
        links += [[last, out_sock, "emit", "Color"], ["emit", "Emission", "out", "Surface"]]
        return _keys({"name": name, "path": "eevee", "nodes": nodes, "links": links})

    def _art_world(self, hdri: str | None) -> dict:
        """Lighting = the weak paper ambient (as the toon world); camera rays see the look's sky: the paper, a painted gradient
        sky (warm horizon to a soft blue, with noise clouds) or the HDRI's own sky, warmed."""
        t, a = self.t, self.t.art
        paper = rgba(self.pal[t.paper])
        nodes = [{"id": "light", "type": "ShaderNodeBackground", "inputs": {"Color": paper, "Strength": t.ambient}},
                 {"id": "backdrop", "type": "ShaderNodeBackground", "inputs": {"Color": paper, "Strength": 1.0}},
                 {"id": "is_cam", "type": "ShaderNodeLightPath"},
                 {"id": "mix", "type": "ShaderNodeMixShader"},
                 {"id": "out", "type": "ShaderNodeOutputWorld"}]
        links = [["is_cam", "Is Camera Ray", "mix", "Fac"], ["light", "Background", "mix", 1], ["backdrop", "Background", "mix", 2],
                 ["mix", "Shader", "out", "Surface"]]
        if a.sky == "gradient" or a.sky == "hdri" and hdri is None:
            top = rgba(_hex_scaled(self.pal["support_blue"], 0.62, 0.86))
            horizon = _lerp(rgba(_hex_scaled(self.pal[t.paper], 2.2, 0.97)), top, 0.3)   # a warm haze already leaning blue
            cloud = rgba(self.pal[t.paper])
            nodes += [{"id": "dir", "type": "ShaderNodeTexCoord"},
                      {"id": "dir_xyz", "type": "ShaderNodeSeparateXYZ"},
                      {"id": "height", "type": "ShaderNodeMapRange", "inputs": {"From Min": -0.02, "From Max": 0.14}},
                      {"id": "sky", "type": "ShaderNodeValToRGB",
                       "ramp": {"interpolation": "EASE", "stops": [[0.0, horizon], [1.0, top]]}},
                      {"id": "clouds", "type": "ShaderNodeTexNoise", "inputs": {"Scale": 2.2, "Detail": 4.0, "Roughness": 0.55}},
                      {"id": "cloud_cut", "type": "ShaderNodeMapRange", "inputs": {"From Min": 0.52, "From Max": 0.72,
                                                                                    "To Max": 0.7}},
                      {"id": "sky_mix", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MIX"},
                       "inputs": {7: cloud}}]
            links += [["dir", "Generated", "dir_xyz", "Vector"], ["dir_xyz", "Z", "height", "Value"], ["height", "Result", "sky", "Fac"],
                      ["dir", "Generated", "clouds", "Vector"], ["clouds", "Fac", "cloud_cut", "Value"],
                      ["cloud_cut", "Result", "sky_mix", "Factor"], ["sky", "Color", "sky_mix", 6], ["sky_mix", 2, "backdrop", "Color"]]
        elif a.sky == "hdri":   # the HDRI's sky above the horizon, a warm haze below it (a "puresky" HDRI is blank down there)
            haze = rgba(_hex_scaled(self.pal[t.paper], 2.2, 0.97))
            nodes += [{"id": "env", "type": "ShaderNodeTexEnvironment", "image": hdri},
                      {"id": "sky_warm", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": 1.0, 7: [0.62, 0.56, 0.48, 1.0]}},
                      {"id": "dir", "type": "ShaderNodeTexCoord"},
                      {"id": "dir_xyz", "type": "ShaderNodeSeparateXYZ"},
                      {"id": "above", "type": "ShaderNodeMapRange", "inputs": {"From Min": -0.01, "From Max": 0.03}},
                      {"id": "sky_mix", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MIX"},
                       "inputs": {6: haze}}]
            links += [["env", "Color", "sky_warm", 6], ["dir", "Generated", "dir_xyz", "Vector"], ["dir_xyz", "Z", "above", "Value"],
                      ["above", "Result", "sky_mix", "Factor"], ["sky_warm", 2, "sky_mix", 7], ["sky_mix", 2, "backdrop", "Color"]]
        return _keys({"nodes": nodes, "links": links})

    def _art_line(self, distance_m: float, lens_mm: float, sensor_mm: float) -> dict:
        a = self.t.art
        if a.line_mode == "none":
            return {"enabled": False, "line_px_1440": 0.0, "mode": "none"}
        return {"enabled": True, "mode": a.line_mode, "radius": line_radius(a.line_px, distance_m, lens_mm, sensor_mm=sensor_mm),
                "line_px_1440": a.line_px, "focus_distance_m": round(distance_m, 4),
                "crease_threshold_rad": round(math.radians(self.t.crease_deg), 6), "crease_deg": self.t.crease_deg,
                "ink_rgba": self._art_colour(a.line_colour), "opacity": round(a.line_opacity, 6)}

    def _art_finish(self, texture: str | None, *, focus_m: float) -> dict:
        """The compositor finish of a look, in order: Kuwahara (whole frame, brush strokes), the far background painted as a plate
        (a bigger Kuwahara mixed in by depth), bleed (edge-aware blur), paper as a multiply base, paint grain, vignette."""
        a = self.t.art
        nodes = [{"id": "render", "type": "CompositorNodeRLayers"}]
        links: list[list] = []
        cur, sock, passes = "render", "Image", []

        def kuw(nid, size, src, ssock):
            nodes.append({"id": nid, "type": "CompositorNodeKuwahara",
                          "inputs": {"Type": "Anisotropic", "Size": int(size), "Uniformity": 4, "Sharpness": 0.5, "Eccentricity": 1.0}})
            links.append([src, ssock, nid, "Image"])

        if a.kuwahara and a.kuwahara_scope == "frame":
            kuw("kuwahara", a.kuwahara, cur, sock)
            cur, sock = "kuwahara", "Image"
        if a.bg_mode == "plate" and (a.plate_kuwahara or a.kuwahara and a.kuwahara_scope == "background"):
            passes.append("z")
            kuw("plate", a.plate_kuwahara or a.kuwahara, cur, sock)
            nodes += [{"id": "far", "type": "ShaderNodeMapRange",
                       "inputs": {"From Min": round(focus_m * 1.15, 4), "From Max": round(focus_m * 2.2, 4)}},
                      {"id": "plate_mix", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MIX"}}]
            links += [["render", "Depth", "far", "Value"], ["far", "Result", "plate_mix", "Factor"], [cur, sock, "plate_mix", 6],
                      ["plate", "Image", "plate_mix", 7]]
            cur, sock = "plate_mix", 2
        if a.bleed:
            nodes.append({"id": "bleed", "type": "CompositorNodeBilateralblur", "inputs": {"Size": int(a.bleed), "Threshold": 0.12}})
            links += [[cur, sock, "bleed", "Image"], [cur, sock, "bleed", "Determinator"]]
            cur, sock = "bleed", "Image"
        if a.paper > 0 and texture is not None:   # paper as the base: the frame is multiplied into the sheet's grain
            p = round(a.paper, 6)
            nodes += [{"id": "paper", "type": "CompositorNodeImage", "image": texture},
                      {"id": "fit", "type": "CompositorNodeScale", "inputs": {"Type": "Render Size", "Frame Type": "Crop"}},
                      {"id": "grey", "type": "CompositorNodeRGBToBW"},
                      {"id": "stretch", "type": "CompositorNodeNormalize"},
                      {"id": "paper_gain", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY_ADD"}, "inputs": {1: p, 2: round(1 - p, 6)}},
                      {"id": "paper_mul", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": 1.0}}]
            links += [["paper", "Image", "fit", "Image"], ["fit", "Image", "grey", "Image"], ["grey", "Val", "stretch", 0],
                      ["stretch", 0, "paper_gain", 0], [cur, sock, "paper_mul", 6], ["paper_gain", "Value", "paper_mul", 7]]
            cur, sock = "paper_mul", 2
        if a.grain > 0 or a.vignette > 0:
            nodes.append({"id": "coords", "type": "CompositorNodeImageCoordinates"})
            links.append(["render", "Image", "coords", "Image"])
        if a.grain > 0:   # static paint grain in screen space (it stays put frame to frame, like the paper)
            g = round(a.grain, 6)
            nodes += [{"id": "grain_noise", "type": "ShaderNodeTexNoise", "inputs": {"Scale": 0.35, "Detail": 2.0, "Roughness": 0.7}},
                      {"id": "grain_gain", "type": "ShaderNodeMapRange",
                       "inputs": {"From Min": 0.3, "From Max": 0.7, "To Min": round(1 - g, 6), "To Max": round(1 + g * 0.4, 6)}},
                      {"id": "grain_mul", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": 1.0}}]
            links += [["coords", "Pixel", "grain_noise", "Vector"], ["grain_noise", "Factor", "grain_gain", "Value"],
                      [cur, sock, "grain_mul", 6], ["grain_gain", "Result", "grain_mul", 7]]
            cur, sock = "grain_mul", 2
        if a.vignette > 0:
            v = round(a.vignette, 6)
            nodes += [{"id": "radius", "type": "ShaderNodeVectorMath", "props": {"operation": "LENGTH"}},
                      {"id": "vig_gain", "type": "ShaderNodeMapRange",
                       "inputs": {"From Min": 0.55, "From Max": 1.45, "To Min": 1.0, "To Max": round(1 - v, 6)}},
                      {"id": "vig_mul", "type": "ShaderNodeMix", "props": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                       "inputs": {"Factor": 1.0}}]
            links += [["coords", "Normalized", "radius", 0], ["radius", "Value", "vig_gain", "Value"], [cur, sock, "vig_mul", 6],
                      ["vig_gain", "Result", "vig_mul", 7]]
            cur, sock = "vig_mul", 2
        nodes.append({"id": "out", "type": "NodeGroupOutput"})
        links.append([cur, sock, "out", "Image"])
        return _keys({"enabled": True, "opacity": a.paper, "texture": texture if a.paper > 0 else None, "passes": passes,
                      "nodes": nodes, "links": links})

    # -- world, line, paper, scene --
    def world(self, *, hdri: str | None = None) -> dict:
        """Camera rays see the paper colour; lighting is a weak ambient (or the HDRI at the same strength, for its colour only)."""
        if self.t.art is not None:
            return self._art_world(hdri)
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
        if self.t.art is not None:
            return self._art_line(distance_m, lens_mm, sensor_mm)
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
        a = self.t.art
        if a is not None:
            if path != "eevee":
                raise ValueError("the look round's graphs are EEVEE-only (Shader to RGB)")
            doc["paper"] = self._art_finish(paper_texture, focus_m=camera["focus_distance_m"])
            kd = doc["key_light"]
            if a.casts_shadows:
                kd["angle_rad"] = round(math.radians(a.shadow_softness_deg), 6)
            # the key is a probe of N.L here (the ramp positions are N.L): energy 1; no live key at all on ambient_only
            kd["energy"] = 0.0 if a.light_rig == "ambient_only" else 1.0
            if a.light_rig == "cinematic" or a.light_rig == "key_rim":   # a cool fill from the other side, no shadow (cheap)
                el, az = 22.0, kl.azimuth_deg + 160.0
                doc["fill_light"] = {"type": "SUN", "energy": round(a.fill, 6), "use_shadow": False,
                                     "rotation_euler": [round(math.radians(90.0 - el), 6), 0.0, round(math.radians(az), 6)]}
            if a.bg_mode in ("dof", "plate") and a.fstop:
                doc["camera_dof"] = {"use_dof": True, "focus_distance_m": round(camera["focus_distance_m"], 4),
                                     "fstop": round(a.fstop, 4)}
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
    if doc["line_art"].get("enabled", True) and not doc["line_art"]["line_px_1440"] > 0:
        out.append(f"line weight {doc['line_art']['line_px_1440']} px is not a width")
    art = doc["tokens"].get("art")
    if art is not None:
        if doc["path"] != "eevee":
            out.append("a look-round graph off the EEVEE path")
        if art["light_rig"] != "cinematic" and doc["key_light"]["use_shadow"] and art["shade_mode"] != "flat":
            out.append(f"look {art['id']}: cast shadows on outside the cinematic rig (the light profile)")
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
