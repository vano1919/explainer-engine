"""WP-Q8 terrain: a deterministic height field (pure Python, no Blender) for the epic sets.

One function ``Terrain.height(x, y)`` says where the ground is, so the layout code (castle, houses, trees, the cast) and the mesh the
renderer builds agree to the centimetre. The field is data: a ``terrain`` block of a layout (seed, a hill with the castle on its crest, a
river that bends away from the hill, a road polyline, a raised causeway at the bridge, noise amplitudes). ``mesh`` turns it into the
grid ``bpy/render_shot.py`` builds (heights + one material class per face: grass, meadow, forest floor, dirt road, rock, snow).
No library is copied: it is a value-noise fBm over a hashed lattice, the standard construction (Perlin 1985; Musgrave 1994)."""
from __future__ import annotations

import math

CLASSES = ("grass", "meadow", "forest", "road", "rock", "snow")


def _hash(ix: int, iy: int, seed: int) -> float:
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def _smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def _vnoise(x: float, y: float, seed: int) -> float:
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy


def fbm(x: float, y: float, seed: int, octaves: int = 5) -> float:
    """0..1 fractal noise."""
    v, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        v += amp * _vnoise(x, y, seed + 31 * o)
        tot += amp
        x, y, amp = x * 2.03, y * 2.03, amp * 0.5
    return v / tot


def ridged(x: float, y: float, seed: int, octaves: int = 5) -> float:
    """0..1 ridged noise (sharp crests, the mountain ranges)."""
    v, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        n = 1.0 - abs(2 * _vnoise(x, y, seed + 17 * o) - 1)
        v += amp * n * n
        tot += amp
        x, y, amp = x * 2.1, y * 2.1, amp * 0.5
    return v / tot


def smoothstep(a: float, b: float, x: float) -> float:
    if b == a:
        return 1.0 if x >= b else 0.0
    return _smooth(min(1.0, max(0.0, (x - a) / (b - a))))


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Terrain:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.seed = int(cfg.get("seed", 1))
        self.hill = cfg.get("hill")
        self.river = cfg.get("river")
        self.road = [tuple(p) for p in cfg.get("road", [])]
        self.causeway = cfg.get("causeway")
        self.rolling = cfg.get("rolling", 1.6)
        self.flat = [tuple(f) for f in cfg.get("flat", [])]   # [x, y, r, z, falloff]: level ground (a camp, a forum, a quay)
        self.sea = cfg.get("sea")                              # {"y0", "y1", "drop"}: the ground falls away to a sea bed

    # -- the ground ----------------------------------------------------------------------------------------------------------
    def river_x(self, y: float) -> float:
        r = self.river
        return r["bend_x"] * smoothstep(r["bend_y0"], r["bend_y1"], y) if r else 0.0

    def road_dist(self, x: float, y: float) -> float:
        return min((_seg_dist(x, y, *a, *b) for a, b in zip(self.road, self.road[1:])), default=1e9)

    def height(self, x: float, y: float) -> float:
        s = self.seed
        h = self.rolling * (fbm(x / 55.0, y / 55.0, s, 4) - 0.5) * 2 + 0.6 * (fbm(x / 9.0, y / 9.0, s + 5, 3) - 0.5)
        if self.hill:
            c = self.hill
            d = ((x - c["x"]) / c["rx"]) ** 2 + ((y - c["y"]) / c["ry"]) ** 2
            k = smoothstep(0.0, 1.0, 1.0 - d)
            lump = c["h"] * k * (0.78 + 0.22 * fbm(x / 14.0, y / 14.0, s + 9, 4))   # a lumpy slope
            crown = smoothstep(0.55, 0.8, k) * c.get("crown", 0.9)   # a level crown the castle can stand on
            h += lump + (c["h"] * 0.86 - lump) * crown
        if self.river:
            r = self.river
            dist = abs(x - self.river_x(y))
            h -= r["depth"] * (1.0 - smoothstep(r["width"], r["width"] * 2.6, dist))
        if self.sea:
            h -= self.sea["drop"] * smoothstep(self.sea["y0"], self.sea["y1"], y)
        if self.causeway:
            w = self.causeway
            near = ((1.0 - smoothstep(w["half_y"], w["half_y"] * 2.2, abs(y - w["y"]))) * (1.0 - smoothstep(w["x0"], w["x1"], abs(x)))
                    * smoothstep(w.get("x_in", 6.5), w.get("x_in", 6.5) + 2.5, abs(x)))   # not across the river under the bridge
            h = h + (w["z"] - h) * near
        for fx, fy, fr, fz, fo in self.flat:
            w = 1.0 - smoothstep(fr, fr + fo, math.hypot(x - fx, y - fy))
            h += (fz - h) * w
        return round(h, 3)

    # -- what a face is made of ----------------------------------------------------------------------------------------------
    def face_class(self, x: float, y: float, z: float, slope: float) -> int:
        c = self.cfg
        if self.road and self.road_dist(x, y) < c.get("road_half", 2.0) + 1.2 * (fbm(x / 3.0, y / 3.0, self.seed + 3, 2) - 0.5):
            return CLASSES.index("road")
        if z > c.get("snow_line", 1e9) + 6 * (fbm(x / 20.0, y / 20.0, self.seed + 4, 3) - 0.5):
            return CLASSES.index("snow")
        if slope > c.get("rock_slope", 0.9) or z > c.get("rock_line", 1e9):
            return CLASSES.index("rock")
        n = fbm(x / 18.0, y / 18.0, self.seed + 6, 3)
        if self.hill and ((x - self.hill["x"]) / self.hill["rx"]) ** 2 + ((y - self.hill["y"]) / self.hill["ry"]) ** 2 < 1.1 and n > 0.58:
            return CLASSES.index("forest")
        return CLASSES.index("meadow" if n > 0.5 else "grass")

    def mesh(self, x0: float, x1: float, y0: float, y1: float, nx: int, ny: int) -> dict:
        """Grid of nx x ny vertices over the rectangle: ``heights`` row-major (y rows), ``face_class`` per quad."""
        xs = [x0 + (x1 - x0) * i / (nx - 1) for i in range(nx)]
        ys = [y0 + (y1 - y0) * j / (ny - 1) for j in range(ny)]
        hs = [[self.height(x, y) for x in xs] for y in ys]
        fc = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                z = (hs[j][i] + hs[j][i + 1] + hs[j + 1][i] + hs[j + 1][i + 1]) / 4
                sl = max(abs(hs[j][i + 1] - hs[j][i]) / (xs[1] - xs[0]), abs(hs[j + 1][i] - hs[j][i]) / (ys[1] - ys[0]))
                fc.append(self.face_class((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2, z, sl))
        return {"x0": x0, "x1": x1, "y0": y0, "y1": y1, "nx": nx, "ny": ny, "heights": [round(v, 2) for row in hs for v in row],
                "face_class": fc, "weights": self.weights(xs, ys, hs)}

    def weights(self, xs, ys, hs) -> dict:
        """Per-VERTEX class weights (0..1, the shader interpolates them): the ground blends per pixel instead of per face."""
        c, s = self.cfg, self.seed
        nx, ny = len(xs), len(ys)
        w = {k: [] for k in ("meadow", "forest", "rock", "road", "snow")}
        for j in range(ny):
            for i in range(nx):
                x, y, z = xs[i], ys[j], hs[j][i]
                sl = max(abs(hs[j][min(i + 1, nx - 1)] - hs[j][max(i - 1, 0)]) / (xs[min(i + 1, nx - 1)] - xs[max(i - 1, 0)]),
                         abs(hs[min(j + 1, ny - 1)][i] - hs[max(j - 1, 0)][i]) / (ys[min(j + 1, ny - 1)] - ys[max(j - 1, 0)]))
                n = fbm(x / 18.0, y / 18.0, s + 6, 3)
                inside = 1.0
                if self.hill:
                    d = ((x - self.hill["x"]) / self.hill["rx"]) ** 2 + ((y - self.hill["y"]) / self.hill["ry"]) ** 2
                    inside = 1.0 - smoothstep(0.9, 1.3, d)
                jit = 1.2 * (fbm(x / 3.0, y / 3.0, s + 3, 2) - 0.5)
                rh = c.get("road_half", 2.0)
                w["road"].append(round(1.0 - smoothstep(rh - 0.4, rh + 1.2, self.road_dist(x, y) + jit), 3) if self.road else 0.0)
                sn = c.get("snow_line", 1e9) + 6 * (fbm(x / 20.0, y / 20.0, s + 4, 3) - 0.5)
                w["snow"].append(round(smoothstep(sn - 2.5, sn + 2.5, z), 3))
                w["rock"].append(round(max(smoothstep(c.get("rock_slope", 0.9) - 0.15, c.get("rock_slope", 0.9) + 0.2, sl),
                                           smoothstep(c.get("rock_line", 1e9) - 3, c.get("rock_line", 1e9) + 3, z)), 3))
                w["meadow"].append(round(smoothstep(0.42, 0.56, n), 3))
                w["forest"].append(round(smoothstep(0.54, 0.66, n) * inside if self.hill else 0.0, 3))
        return w


class Ranges:
    """A far mountain range: ridged noise under an envelope that is 0 at the near edge and fades at the far edge."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def height(self, x: float, y: float) -> float:
        c = self.cfg
        env = smoothstep(c["y0"], c["y0"] + c["ramp"], y) * (1.0 - smoothstep(c["y1"] - c["ramp"], c["y1"], y))
        r = ridged(x / c["scale"], y / c["scale"], c["seed"], 5)
        base = fbm(x / (c["scale"] * 2.5), y / (c["scale"] * 2.5), c["seed"] + 2, 3)
        return round(c["floor"] + env * c["peak"] * (0.25 + 0.9 * r) * (0.55 + 0.7 * base), 2)

    def mesh(self, nx: int, ny: int) -> dict:
        c = self.cfg
        xs = [c["x0"] + (c["x1"] - c["x0"]) * i / (nx - 1) for i in range(nx)]
        ys = [c["y0"] + (c["y1"] - c["y0"]) * j / (ny - 1) for j in range(ny)]
        hs = [[self.height(x, y) for x in xs] for y in ys]
        fc = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                z = (hs[j][i] + hs[j][i + 1] + hs[j + 1][i] + hs[j + 1][i + 1]) / 4
                sl = max(abs(hs[j][i + 1] - hs[j][i]) / (xs[1] - xs[0]), abs(hs[j + 1][i] - hs[j][i]) / (ys[1] - ys[0]))
                n = fbm(xs[i] / 30, ys[j] / 30, c["seed"] + 8, 3)
                fc.append(CLASSES.index("snow") if z > c["snow_line"] + 12 * (n - 0.5) else
                          CLASSES.index("rock") if z > c["rock_line"] or sl > c.get("rock_slope", 0.8) else
                          CLASSES.index("forest") if n > 0.5 else CLASSES.index("grass"))
        w = {k: [] for k in ("meadow", "forest", "rock", "road", "snow")}
        for j in range(ny):
            for i in range(nx):
                z = hs[j][i]
                sl = max(abs(hs[j][min(i + 1, nx - 1)] - hs[j][max(i - 1, 0)]) / (xs[min(i + 1, nx - 1)] - xs[max(i - 1, 0)]),
                         abs(hs[min(j + 1, ny - 1)][i] - hs[max(j - 1, 0)][i]) / (ys[min(j + 1, ny - 1)] - ys[max(j - 1, 0)]))
                n = fbm(xs[i] / 30, ys[j] / 30, c["seed"] + 8, 3)
                sn = c["snow_line"] + 12 * (n - 0.5)
                w["snow"].append(round(smoothstep(sn - 4, sn + 4, z) * (1.0 - smoothstep(0.55, 0.95, sl)), 3))   # steep faces stay rock
                w["rock"].append(round(max(smoothstep(c["rock_line"] - 4, c["rock_line"] + 4, z),
                                           smoothstep(c.get("rock_slope", 0.8) - 0.15, c.get("rock_slope", 0.8) + 0.2, sl)), 3))
                w["forest"].append(round(smoothstep(0.45, 0.58, n), 3))
                w["meadow"].append(0.0)
                w["road"].append(0.0)
        return {"x0": c["x0"], "x1": c["x1"], "y0": c["y0"], "y1": c["y1"], "nx": nx, "ny": ny,
                "heights": [round(v, 1) for row in hs for v in row], "face_class": fc, "weights": w}
