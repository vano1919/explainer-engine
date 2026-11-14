"""The living effects of the directed 2.5D renderer (P1 round 2, the owner 2026-11-14: "the director missed the sun's glints
and rays, the wind, the trees and the snow"; Fable's LIVING_PHOTO_RULES, BP-200): the old ``layers25d`` effects brought into
``directed25d`` (particles, sway, cloth, water) and the new ones the inventory needs (snow in three depth layers, a sun
glint with a flare, ice and snow sparkle, stars, breath, spindrift, the light going).

Every effect is a pure function of the frame number (seeded by the shot id), sits in the picture's space (it moves with the
camera like the surface it belongs to) and is covered by what stands in front of it (the frame's depth). Strength 1.0 is
meant to be clearly visible at 1080p on a phone; 0.5 is subtle. Each effect reads its target from the plan entry:
``point`` / ``light`` (a source), ``box`` (a region, shares), ``mask`` (an object of the layers), and ``params``.
The wind is one vector per shot (``plan["wind"]``, shares of the width per second, default a light breeze to the right),
so smoke, snow, grass and cloth lean the same way.
"""
from __future__ import annotations

import math

import numpy as np

from explainer_engine.production import layers25d as L

OPS = ("snow", "rain", "embers", "dust", "spindrift", "sun_glint", "glint", "stars", "steam", "breath", "light_fade",
       "foliage_sway", "cloth_flap", "wire_sway", "water_shimmer")
PARTICLE_LAYERS = (0.25, 0.6, 0.92)     # nearness of the three particle layers (1 = at the lens)
WIND_DEFAULT = (0.02, 0.0)              # shares of the width per second: a light breeze to the right


def _rng(st, key: str):
    return np.random.default_rng(L._seed(f"{st.p.get('shot_id')}:{key}"))


def wind(st) -> tuple[float, float]:
    w = st.p.get("wind")
    return (float(w[0]), float(w[1])) if w else WIND_DEFAULT


def _field(st, e, mx, my, v, layers, feather=0.04):
    """The effect's region in the frame: its object mask (moving with its layer), its box, or the whole frame."""
    cv2 = st.cv2
    mid = e.get("mask")
    if mid and mid in st.masks_src:
        m = st.masks_src[mid]
        host = next((o for o in st.objects if o["id"] == mid), None)
        if host is not None:
            mat = st.matrix(v, host["d"])
            return cv2.warpAffine(m, mat, (st.W, st.H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                  borderMode=cv2.BORDER_CONSTANT)
        return cv2.remap(m, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if e.get("box"):
        return st._box_field(e["box"], mx, my, feather=feather)
    return None


def _source(st, e, v):
    if e.get("light") and e["light"] in st.lights:
        li = st.lights[e["light"]]
        return st._to_out(li["point"], v=v, d=li.get("d"))
    if e.get("point"):
        return st._to_out((e["point"][0] * st.sw, e["point"][1] * st.sh), v=v)
    if e.get("origin"):
        return st._to_out((e["origin"][0] * st.sw, e["origin"][1] * st.sh), v=v, d=0.0)
    return None


# --- particles ----------------------------------------------------------------------------------------------------------------

def _particles(st, rgb, depth, e, t, v, op):
    """Snow, rain, embers, dust and spindrift in three depth layers: a particle is drawn only where the scene behind it is
    farther than its layer (a man in front hides the far flakes), it is larger and faster the nearer it is, and its layer
    follows the camera with that layer's parallax."""
    cv2 = st.cv2
    W, H = st.W, st.H
    k = H / 1080.0
    s = float(e.get("strength", 1.0))
    prm = e.get("params", {})
    wx, wy = wind(st)
    wx *= float(prm.get("wind_gain", 1.0))
    base = {"snow": 260, "rain": 420, "embers": 70, "dust": 110, "spindrift": 180}[op]
    lit = rgb.mean(axis=2) / 255.0 if op == "dust" else None
    box = e.get("box")
    src = _source(st, e, v) if op == "embers" else None
    out = rgb
    for li, z in enumerate(PARTICLE_LAYERS):
        n = int(round(base * s * float(prm.get("density", 1.0)) * (0.6 + 0.4 * li) / 2))
        if n <= 0:
            continue
        r = _rng(st, f"{op}:{li}")
        px, py = r.uniform(0, 1, n), r.uniform(0, 1, n)
        ph, wob = r.uniform(0, 2 * np.pi, n), r.uniform(0.5, 1.5, n)
        speed = 0.35 + 0.65 * z
        if op == "snow":
            x = px + (wx * speed) * t + 0.012 * np.sin(wob * 1.3 * t + ph)
            y = py + (0.045 + 0.06 * z) * t * (1 + 0.2 * np.sin(ph))
        elif op == "rain":
            x = px + (0.10 + wx) * speed * t
            y = py + 1.4 * speed * t
        elif op == "spindrift":                         # snow blown low along the ground
            x = px + (3.0 * wx + 0.08) * speed * t + 0.01 * np.sin(wob * 2 * t + ph)
            y = 0.62 + 0.38 * py + 0.006 * np.sin(wob * 3 * t + ph)
        elif op == "embers":
            x = px + wx * speed * t + 0.012 * np.sin(wob * 1.7 * t + ph)
            y = py - (0.06 + 0.05 * z) * t
        else:                                           # dust motes drifting in the light
            x = px + 0.3 * wx * t + 0.008 * np.sin(wob * 0.6 * t + ph)
            y = py + 0.006 * np.cos(wob * 0.5 * t + ph * 1.3)
        x, y = x % 1.0, y % 1.0
        if src is not None:                             # embers rise from their fire in a narrow, widening column
            sx, sy, _ = src
            spread = 0.01 + 0.08 * (1 - y)
            x = sx / W + (px - 0.5) * spread + wx * (1 - y) * 0.5
            y = sy / H - (((py + (0.10 + 0.06 * z) * t) % 1.0) * float(prm.get("height", 0.35)))
        if box is not None:
            x0, y0, x1, y1 = box
            x, y = x0 + x * (x1 - x0), y0 + y * (y1 - y0)
        # the layer moves with the camera at its own depth: picture space -> frame
        m = st.matrix(v, z)
        inv = cv2.invertAffineTransform(m)
        q = inv @ np.vstack([x * st.sw, y * st.sh, np.ones_like(x)])
        alpha = np.zeros((H, W), np.float32)
        rad = {"snow": 1.2 + 3.2 * z, "rain": 1.0, "embers": 1.0 + 1.8 * z, "dust": 0.9 + 0.8 * z,
               "spindrift": 0.8 + 1.6 * z}[op] * k * (1.0 / max(0.5, st.cover_k(v, z)))
        for j in range(n):
            qx, qy = int(q[0, j]), int(q[1, j])
            if not (-8 <= qx < W + 8 and -8 <= qy < H + 8):
                continue
            if op == "rain":
                ln = (16 + 34 * z) * k
                cv2.line(alpha, (qx, qy), (int(qx + ln * 0.12), int(qy + ln)), 0.35 + 0.35 * z, max(1, int(round(k))),
                         cv2.LINE_AA)
            else:
                a = 0.55 + 0.45 * z
                if op == "embers":
                    a *= 0.6 + 0.4 * math.sin(6.0 * wob[j] * t + ph[j])
                if op == "dust" and lit is not None:
                    a *= 0.15 + 0.85 * float(lit[min(H - 1, max(0, qy)), min(W - 1, max(0, qx))])
                cv2.circle(alpha, (qx, qy), max(1, int(round(rad))), float(a), -1, cv2.LINE_AA)
        if op in ("snow", "spindrift"):
            alpha = cv2.GaussianBlur(alpha, (0, 0), (0.5 + 1.2 * z) * k)
        behind = np.clip((z + 0.04 - depth) / 0.08, 0, 1)        # only where the scene is farther than the layer
        alpha = np.clip(alpha, 0, 1) * behind
        if op == "embers":
            glow = alpha + cv2.GaussianBlur(alpha, (0, 0), 4 * k) * 1.5
            out = out + np.array([255, 150, 60], np.float32) * np.clip(glow, 0, 1)[..., None] * 0.9 * s
        elif op == "dust":
            out = out + np.array([255, 240, 215], np.float32) * alpha[..., None] * 0.6 * s
        else:
            col = np.array(prm.get("colour", {"snow": [246, 247, 252], "rain": [190, 200, 214],
                                              "spindrift": [236, 239, 246]}[op]), np.float32)
            a3 = (alpha * (0.9 if op == "snow" else 0.6))[..., None]
            out = out * (1 - a3) + col * a3
    return out


# --- light ------------------------------------------------------------------------------------------------------------------

def _sun_glint(st, rgb, depth, e, t, v):
    """The sun breathes: a soft disc of light that swells and shimmers, a horizontal streak through it and two faint ghosts
    on the line to the frame's centre (a lens flare); the near objects stand in front of the disc."""
    cv2 = st.cv2
    W, H = st.W, st.H
    src = _source(st, e, v)
    if src is None:
        return rgb
    sx, sy, _ = src
    s = float(e.get("strength", 1.0))
    ph = (L._seed(f"{st.p.get('shot_id')}:sun") % 628) / 100.0
    pulse = 0.75 + 0.25 * math.sin(2 * math.pi * 0.45 * t + ph) + 0.08 * math.sin(2 * math.pi * 2.3 * t)
    qs = 2
    yy, xx = np.mgrid[0:H // qs, 0:W // qs].astype(np.float32) * qs
    r = np.hypot(xx - sx, yy - sy) / W
    disc = np.exp(-(r / (0.035 * (0.9 + 0.2 * pulse))) ** 2) * 0.9 + np.exp(-(r / 0.12) ** 2) * 0.35
    streak = np.exp(-((yy - sy) / (0.006 * H)) ** 2) * np.exp(-(np.abs(xx - sx) / (0.28 * W)) ** 1.2) * 0.5
    ang = np.arctan2(yy - sy, xx - sx)
    spikes = (np.cos(6 * ang + 0.3 * t) ** 8) * np.exp(-(r / 0.07) ** 2) * 0.4 * (0.6 + 0.4 * pulse)
    glow = disc * pulse + streak * (0.6 + 0.4 * pulse) + spikes
    cx, cy = W / 2, H / 2
    for g, (frac, size, a) in enumerate(((0.55, 0.018, 0.16), (1.35, 0.03, 0.10))):
        gx, gy = sx + (cx - sx) * frac, sy + (cy - sy) * frac
        glow = glow + a * pulse * np.exp(-((np.hypot(xx - gx, yy - gy) / W) / size) ** 2)
    glow = cv2.resize(glow.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    front = np.clip((depth - 0.35) / 0.2, 0, 1)                # a post or a man in front blocks the disc
    glow = glow * (1 - 0.85 * front * (cv2.resize(disc.astype(np.float32), (W, H)) > 0.05))
    return rgb + np.array([255, 236, 196], np.float32) * (0.45 * s * glow)[..., None]


def _points(st, key, region, n, pick):
    """Up to ``n`` sparkle points in picture space: the brightest local spots inside ``region`` (a working-size weight map)."""
    cv2 = st.cv2
    cache = st.__dict__.setdefault("_fx_points", {})
    if key in cache:
        return cache[key]
    lum = st.src.astype(np.float32).mean(axis=2)
    sat = st.src.astype(np.float32).max(axis=2) - st.src.astype(np.float32).min(axis=2)
    score = pick(lum, sat) * region
    peaks = (score == cv2.dilate(score, np.ones((7, 7), np.uint8))) & (score > 0)
    ys, xs = np.nonzero(peaks)
    order = np.argsort(-score[ys, xs])[: n * 4]
    r = _rng(st, key)
    if len(order) > n:
        order = r.choice(order, n, replace=False)
    pts = [(float(xs[i]), float(ys[i])) for i in order]
    cache[key] = (pts, r.uniform(0, 2 * np.pi, len(pts)), r.uniform(0.6, 1.6, len(pts)))
    return cache[key]


def _sparkle(st, rgb, depth, e, t, v, mx, my, layers, op):
    """Ice and snow glints (bright, pale spots of the picture) and stars (pale points of the far sky): each point flashes on
    its own clock, a small four-point star, moving with its surface."""
    cv2 = st.cv2
    W, H = st.W, st.H
    k = H / 1080.0
    s = float(e.get("strength", 1.0))
    prm = e.get("params", {})
    if e.get("mask") and e["mask"] in st.masks_src:
        region = st.masks_src[e["mask"]]
    elif e.get("box"):
        x0, y0, x1, y1 = e["box"]
        region = np.zeros((st.sh, st.sw), np.float32)
        region[int(y0 * st.sh):int(y1 * st.sh), int(x0 * st.sw):int(x1 * st.sw)] = 1
    elif op == "stars":
        region = st.sky
    else:
        region = np.ones((st.sh, st.sw), np.float32)
    n = int(prm.get("count", 60 if op == "stars" else 90) * max(0.3, s))
    if op == "stars":
        pick = lambda lum, sat: np.clip(lum - 90, 0, None) * (sat < 60)          # noqa: E731
    else:
        pick = lambda lum, sat: np.clip(lum - 175, 0, None) * (sat < 70)         # noqa: E731
    pts, ph, sp = _points(st, f"{op}:{e.get('mask')}:{e.get('box')}", region, n, pick)
    if not pts:
        return rgb
    layer = np.zeros((H, W), np.float32)
    rate = 1.1 if op == "stars" else 1.6
    for j, (x, y) in enumerate(pts):
        a = max(0.0, math.sin(2 * math.pi * rate * sp[j] * t + ph[j])) ** (2 if op == "stars" else 6)
        if a < 0.05:
            continue
        ox, oy, d = st._to_out((x, y), v=v)
        ox, oy = int(ox), int(oy)
        if not (0 <= ox < W and 0 <= oy < H) or depth[oy, ox] > d + 0.06:
            continue
        rr = (2.0 if op == "stars" else 5.0 + 5.0 * a) * k
        cv2.circle(layer, (ox, oy), max(1, int(round(1.4 * k))), float(a), -1, cv2.LINE_AA)
        if op != "stars":
            cv2.line(layer, (int(ox - rr), oy), (int(ox + rr), oy), float(0.7 * a), 1, cv2.LINE_AA)
            cv2.line(layer, (ox, int(oy - rr)), (ox, int(oy + rr)), float(0.7 * a), 1, cv2.LINE_AA)
    layer = layer + cv2.GaussianBlur(layer, (0, 0), 2.5 * k) * 1.2
    col = np.array([255, 252, 240] if op != "stars" else [235, 240, 255], np.float32)
    return rgb + col * np.clip(layer * (0.9 * s), 0, 1.5)[..., None]


def _light_fade(st, rgb, t):
    """The light going (late afternoon): exposure and warmth fall slowly over the shot."""
    s = float(st._cur_e.get("strength", 1.0))
    u = float(L.smooth(t / max(1e-3, st.n / st.fps)))
    gain = 1.0 - 0.16 * s * u
    tint = np.array([1.0 - 0.06 * s * u, 1.0 - 0.03 * s * u, 1.0 + 0.04 * s * u], np.float32)
    return rgb * gain * tint


# --- air ----------------------------------------------------------------------------------------------------------------------

def _breath(st, rgb, depth, e, i, t, v, zoom, op):
    """Breath in the cold (a short puff from a mouth every few seconds) and steam (a thin steady wisp from a mug): the
    smoke plume, small, pale, and for breath gated by an exhale clock. ``params.points`` gives several mouths or mugs at
    once (each on its own clock)."""
    if e.get("params", {}).get("points"):
        prm = {k: v_ for k, v_ in e["params"].items() if k != "points"}
        for pt in e["params"]["points"]:
            rgb = _breath(st, rgb, depth, {**e, "point": pt, "params": prm}, i, t, v, zoom, op)
        return rgb
    prm = dict(e.get("params", {}))
    if op == "breath":
        period = float(prm.pop("period_s", 3.4))
        ph = (L._seed(f"{st.p.get('shot_id')}:{e.get('point')}{e.get('light')}") % 100) / 100.0 * period
        u = ((t + ph) % period) / period
        puff = math.sin(math.pi * min(1.0, u / 0.45)) if u < 0.45 else 0.0
        if puff <= 0.01:
            return rgb
        prm.setdefault("height", 0.06)
        prm.setdefault("width", 0.006)
        prm.setdefault("opacity", 0.55 * puff)
    else:
        prm.setdefault("height", 0.10)
        prm.setdefault("width", 0.004)
        prm.setdefault("opacity", 0.45)
    prm.setdefault("colour", [232, 234, 238])
    prm.setdefault("drift", 0.4 + 6 * wind(st)[0])
    return st._smoke(rgb, depth, {**e, "params": prm}, i, t, v, float(e.get("strength", 1.0)), zoom)


# --- surfaces -----------------------------------------------------------------------------------------------------------------

def _surface(st, rgb, e, t, v, mx, my, layers, op):
    """Trees and grass sway (the top moves, the base holds), cloth flaps (waves run from its fixed side), wire trembles
    (a small, quick shiver), water shimmers (ripples and glints). Displacements inside the region only; the wind gust
    swells them together every few seconds."""
    cv2 = st.cv2
    W, H = st.W, st.H
    k = H / 1080.0
    s = float(e.get("strength", 1.0))
    mm = _field(st, e, mx, my, v, layers)
    if mm is None:
        mm = np.ones((H, W), np.float32)
    ys, xs = np.nonzero(mm > 0.3)
    if len(ys) == 0:
        return rgb
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wx = wind(st)[0]
    gust = 0.7 + 0.3 * math.sin(2 * math.pi * 0.23 * t + 0.6) + 0.15 * math.sin(2 * math.pi * 0.61 * t + 1.9)
    lean = 1.0 if wx >= 0 else -1.0
    if op == "foliage_sway":
        tip = np.clip((y1 - yy) / max(1, y1 - y0), 0, 1) ** 1.5           # 0 at the base, 1 at the top
        dx = 6.0 * k * s * gust * tip * (lean * 0.5 + np.sin(2 * math.pi * 0.42 * t + xx / (160 * k))
                                         + 0.35 * np.sin(2 * math.pi * 1.1 * t + xx / (45 * k) + 1.3))
        dy = 0.25 * np.abs(dx) * tip
    elif op == "cloth_flap":
        fixed_left = e.get("params", {}).get("fixed", "left") == "left"
        along = np.clip((xx - x0) / max(1, x1 - x0), 0, 1) if fixed_left else np.clip((x1 - xx) / max(1, x1 - x0), 0, 1)
        phase = 2 * math.pi * (along * 2.2 - 1.6 * t)
        dy = 6.0 * k * s * gust * along * np.sin(phase)
        dx = 2.0 * k * s * gust * along * np.cos(phase + 0.7)
    elif op == "wire_sway":
        dy = 1.6 * k * s * gust * np.sin(2 * math.pi * (xx / (220 * k) - 1.3 * t)) \
            + 0.6 * k * s * np.sin(2 * math.pi * 7.0 * t + xx / (30 * k))
        dx = 0.3 * dy
    else:                                                                     # water
        dx = 0.8 * k * s * np.sin(2 * math.pi * (yy / (9 * k)) + 3.1 * t)
        dy = 2.0 * k * s * np.sin(2 * math.pi * (yy / (23 * k) + xx / (140 * k)) - 2.3 * t)
    soft = cv2.GaussianBlur(mm.astype(np.float32), (0, 0), 3 * k)
    moved = cv2.remap(np.clip(rgb, 0, 255).astype(np.float32), (xx + dx * soft).astype(np.float32),
                      (yy + dy * soft).astype(np.float32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REFLECT)
    if op == "water_shimmer":
        lum = moved.mean(axis=2) / 255.0
        glint = np.clip(np.sin(2 * math.pi * (xx / (37 * k) + yy / (11 * k)) + 4.0 * t) - 0.85, 0, 1) * 6.0
        moved = moved + (glint * lum * soft * 45.0 * s)[..., None]
    return moved


def apply(st, rgb, depth, e, i, t, v, mx, my, layers, zoom):
    op = e["op"]
    st._cur_e = e
    if op in ("snow", "rain", "embers", "dust", "spindrift"):
        return _particles(st, rgb, depth, e, t, v, op)
    if op == "sun_glint":
        return _sun_glint(st, rgb, depth, e, t, v)
    if op in ("glint", "stars"):
        return _sparkle(st, rgb, depth, e, t, v, mx, my, layers, op)
    if op == "light_fade":
        return _light_fade(st, rgb, t)
    if op in ("steam", "breath"):
        return _breath(st, rgb, depth, e, i, t, v, zoom, op)
    return _surface(st, rgb, e, t, v, mx, my, layers, op)
