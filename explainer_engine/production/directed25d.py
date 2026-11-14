"""Directed 2.5D: the renderer prototype that carries out a Scene Director's plan (roadmap 2026-11-14 B.4-B.6, phase P1).

PROTOTYPE (P1, round 2 on the six Stage B photos): ``episode/run.py`` does not call it, and ``production/layers25d.py`` is
unchanged. P3 folds what the owner accepts into ``layers25d``. It reads a picture's ``scene_layers/1`` folder
(``production/understand.py``) and a resolved plan (``production/direction.resolve``), and lifts the five limits the roadmap
found in ``layers25d`` (A.5):

1. Depth at full size, never blurred into planes: the BACKGROUND is one continuous sheet (the clean plate) moved per pixel by
   its own depth (a smoothed copy of it, so a slope stretches and never tears); every named OBJECT (SAM 2.1 + BiRefNet mask) is
   a rigid cut-out at its median depth, in depth order. A crane or a truck shows the ground moving continuously, so the plane
   seams of ``layers25d`` (the fill band of S01 crane 0.95) do not exist.
2. Fills from LaMa (the plate), not Telea; the renderer knows on every frame which output pixel shows plate fill
   (``telemetry.fill``) for the reveal detector (``qa/motion_intent``).
3. A camera with a target: push and pull move towards a point or a mask while they zoom (inside the picture's margin); rack
   focus pulls between two masks' depths; up to ``SEGMENTS_MAX`` word-timed segments; truck, crane (parallax), pan and tilt
   (no parallax, level 1 of B.4), orbit (small), handheld.
4. Effects with targets and instances: every flame, candle and glow is its own instance with its own phase (two braziers and
   six candles in one shot), its light spills on the surfaces round it with distance falloff and flickers with it, the flame
   itself deforms; smoke rises from a source point and the nearer objects cover it (composited depth); mist and sun shafts
   are weighted by the depth of the VISIBLE surface, so they sit behind the near wire and people.
5. ``legacy`` box effects (``fire_box``) keep the Stage B v1 behaviour for the ablations C1/C2 of the roadmap's K.1.

Every frame is a pure function of its number (all randomness from the shot's seed).
"""
from __future__ import annotations

import hashlib
import math
import subprocess
import time
from pathlib import Path

import numpy as np

from explainer_engine.production import layers25d as L
from explainer_engine.production import living_fx as LFX

VERSION = "directed25d/0.1-p1"
SEGMENTS_MAX = 3
PUSH_SCALE = L.PUSH_SCALE          # zoom change of a push at strength 1 (same as layers25d)
DEPTH_PUSH = L.DEPTH_PUSH
NEAR_TRAVEL = L.NEAR_TRAVEL        # near content travel of a truck/crane at strength 1, share of the width
RECENTRE = 0.85                    # a targeted push moves the view this share of the way to its target (inside the margin)
MARGIN = 0.004                     # never sample closer than this share of the width to the picture's edge
UNFOLD_PX = 0.5                    # the background warp may shift neighbours apart by at most this share of a pixel
UNFOLD_ITERS = 60
BG_SMOOTH = 0.006                  # the background's warp depth is the real depth blurred by this share of the width
HAND_TR, HAND_ROT = L.HAND_TR, L.HAND_ROT
RACK_SIGMA_PX = 7.0                # rack focus: blur (px at 1080p) of a surface ``RACK_SPAN`` of disparity away from focus
RACK_SPAN = 0.25
REST_GROW_PX = 3.0                 # the plate shows this far (px at 1080p) round a layered object's half-alpha edge
THIN_FILL_PX = 16.0                # a stroke narrower than this (px at 1080p) is never layered: it stays in the background
FLAT_SHARE = 0.5                   # an object that is at least this share strokes stays in the background whole
REST_ALPHA_GAIN = 6.0              # alpha 1/6 already counts as the object: its soft edge goes with the layer, not the plate
FX_OPS = ("fire", "candle", "glow", "smoke", "mist", "sun_shaft", "cloud_drift", "heat_haze", "fire_box") + LFX.OPS + (
    "subject_sway",)
CAMERA_OPS = ("hold", "push", "pull", "truck", "crane", "pan", "tilt", "orbit", "handheld", "rack_focus")


def _seed(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


class Stage:
    """Everything the frames of one shot need that does not depend on the frame number."""

    def __init__(self, picture: Path, layers: dict, plan: dict, size=(1920, 1080), fps: int = 24):
        import cv2
        from PIL import Image
        self.cv2 = cv2
        self.p = plan
        self.W, self.H = size
        self.fps = fps
        self.n = int(plan["frames"])
        self.seed = _seed(plan.get("shot_id", "shot"))
        rgb0 = np.asarray(Image.open(picture).convert("RGB"))
        h0, w0 = rgb0.shape[:2]
        self.cover = max(self.W / w0, self.H / h0)
        sw = min(w0, int(math.ceil(w0 * self.cover * 1.25)))
        sh = int(round(h0 * sw / w0))
        self.sw, self.sh = sw, sh
        self.k_src = sw / w0
        rs = lambda a, interp=cv2.INTER_AREA: cv2.resize(a, (sw, sh), interpolation=interp)   # noqa: E731
        self.src = rs(rgb0)
        self.plate = rs(layers["plate"])
        self.depth = np.clip(rs(layers["depth"].astype(np.float32), cv2.INTER_LINEAR), 0, 1)
        hole = layers.get("hole")
        self.hole = rs(hole.astype(np.float32), cv2.INTER_LINEAR) if hole is not None else np.zeros((sh, sw), np.float32)
        # the background's depth: the real depth with the objects' area filled from round it (what is BEHIND them), smoothed
        bgd = self.depth.copy()
        if self.hole.max() > 0:
            hb = (self.hole > 0.05).astype(np.uint8)
            bgd = cv2.inpaint(bgd.astype(np.float32), hb, 5, cv2.INPAINT_TELEA)
        self.bg_depth = cv2.GaussianBlur(bgd, (0, 0), max(1.0, BG_SMOOTH * sw)).astype(np.float32)
        # objects: rigid cut-outs at their median depth, far to near
        # None = every object of the scene_layers folder that is a layer there ("layer": false = a mask for targeting only,
        # left in the picture, e.g. a crowd SAM cannot cut cleanly)
        want = plan.get("layers")
        if want is None:
            rows = layers["manifest"].get("masks", {}).get("objects", [])
            want = [r["id"] for r in rows if r.get("layer", True)] if rows else None
        self.objects = []
        for oid, m in layers["masks"].items():
            if want is not None and oid not in want:
                continue
            a = np.clip(rs(m.astype(np.float32), cv2.INTER_LINEAR), 0, 1)
            if (a > 0.5).sum() < 20:
                continue
            d = float(np.median(self.depth[a > 0.5]))
            ys, xs = np.nonzero(a > 0.5)
            rgba = np.dstack([self.src, (a * 255 + 0.5).astype(np.uint8)])
            self.objects.append({"id": oid, "rgba": rgba, "d": d, "centroid": (float(xs.mean()), float(ys.mean())),
                                 "alpha": a})
        self.objects.sort(key=lambda o: o["d"])
        self.lights = {}
        for li in layers["manifest"].get("lights", []):
            entry = {"id": li["id"], "kind": li.get("kind"), "point": (li["point"][0] * sw, li["point"][1] * sh)}
            if li["id"] in layers["lights"]:
                m = np.clip(rs(layers["lights"][li["id"]].astype(np.float32), cv2.INTER_LINEAR), 0, 1)
                ys, xs = np.nonzero(m > 0.3)
                entry["mask"] = m
                if len(xs):
                    entry["point"] = (float(xs.mean()), float(ys.mean()))
                    entry["height"] = float(ys.max() - ys.min() + 1)
                    entry["d"] = float(np.median(self.depth[m > 0.3]))
            self.lights[li["id"]] = entry
        self._rest_background(layers)
        self.masks_src = {o["id"]: o["alpha"] for o in self.objects}
        for oid, m in layers["masks"].items():
            if oid not in self.masks_src:
                self.masks_src[oid] = np.clip(rs(m.astype(np.float32), cv2.INTER_LINEAR), 0, 1)
        rng = np.random.default_rng(self.seed)
        self.tiles = {"a": L._noise_tile(rng, 144, 256, 6.0), "b": L._noise_tile(rng, 144, 256, 10.0),
                      "c": L._noise_tile(rng, 144, 256, 14.0), "f": L._noise_tile(rng, 128, 128, 9.0)}
        self.phases = {}
        for i, e in enumerate(plan.get("effects", [])):
            self.phases[i] = rng.uniform(0, 2 * np.pi, 8)
        self.sky = self._sky()
        self.focus_d = self._focus_depth()
        self.z0 = self._fit_zoom()
        self._unfold_background()
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.oxx, self.oyy = xx - self.W / 2, yy - self.H / 2

    def _rest_background(self, layers: dict) -> None:
        """Frame 0 must be the picture, and nothing may be drawn that the picture does not have (Fable's audit 2026-11-14,
        S01 C3: a post cut on the first frame where the grown LaMa hole reached past what SAM cut out, and wire rings that
        appeared behind the moving wire). Two rules:

        - the background shows the plate only under the layered objects (their alpha, grown by ``REST_GROW_PX``) and the
          picture itself everywhere else;
        - a thin stroke (a wire, a twig: narrower than ``THIN_FILL_PX``) is never layered, because no fill behind a moving
          wire is right: the strokes stay in the background and move with it. An object that is mostly strokes
          (``FLAT_SHARE``) stays in the background whole (``self.flat``)."""
        cv2 = self.cv2
        self.flat = []
        if not self.objects:
            return
        A = np.zeros((self.sh, self.sw), np.float32)
        g = max(1, int(round(REST_GROW_PX * self.sw / 1920)))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1))
        r = max(1, int(round(THIN_FILL_PX / 2 * self.sw / 1920)))
        disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        keep = []
        for o in self.objects:
            hard = (o["alpha"] > 0.5).astype(np.uint8)
            parts = hard & (1 - cv2.morphologyEx(hard, cv2.MORPH_OPEN, disc))   # what an opening removes is thin
            share = float(parts.sum() / max(1, hard.sum()))
            o["thin_share"] = round(share, 3)
            if share >= FLAT_SHARE:
                self.flat.append(o["id"])
                continue
            if parts.any():
                strip = cv2.dilate(parts.astype(np.float32), disc)
                o["alpha"] = o["alpha"] * (1.0 - strip)
                o["rgba"][..., 3] = (o["alpha"] * 255 + 0.5).astype(np.uint8)
            if (o["alpha"] > 0.5).sum() < 20:
                self.flat.append(o["id"])
                continue
            keep.append(o)
            A = np.maximum(A, cv2.dilate(np.clip(o["alpha"] * REST_ALPHA_GAIN, 0, 1), k))
        self.objects = keep
        self.plate = (self.src.astype(np.float32) * (1 - A[..., None]) + self.plate.astype(np.float32) * A[..., None]).astype(np.uint8)
        self.hole = A

    # --- what the plan points at ----------------------------------------------------------------------------------------
    def point_of(self, target: dict | None) -> tuple[float, float] | None:
        """A target -> its point in working pixels: an explicit point, a mask's centroid or a light's point."""
        if not target:
            return None
        if target.get("point") is not None:
            return target["point"][0] * self.sw, target["point"][1] * self.sh
        mid = target.get("mask")
        if mid and mid in self.masks_src:
            ys, xs = np.nonzero(self.masks_src[mid] > 0.5)
            return float(xs.mean()), float(ys.mean())
        lid = target.get("light")
        if lid and lid in self.lights:
            return self.lights[lid]["point"]
        return None

    def depth_of(self, target: dict | None) -> float | None:
        if not target:
            return None
        mid = target.get("mask")
        if mid and mid in self.masks_src:
            return float(np.median(self.depth[self.masks_src[mid] > 0.5]))
        lid = target.get("light")
        if lid and lid in self.lights and "d" in self.lights[lid]:
            return self.lights[lid]["d"]
        pt = self.point_of(target)
        if pt is not None:
            x, y = int(np.clip(pt[0], 0, self.sw - 1)), int(np.clip(pt[1], 0, self.sh - 1))
            return float(self.depth[y, x])
        return None

    def _focus_depth(self) -> float:
        for seg in self.p.get("cameras", []):
            if seg["op"] == "orbit" and seg.get("target"):
                return self.depth_of(seg["target"]) or 0.5
        return 0.5

    def _sky(self) -> np.ndarray:
        top = (np.arange(self.sh, dtype=np.float32) < 0.6 * self.sh)[:, None]
        sky = ((self.depth <= 0.03) & top).astype(np.float32)
        return self.cv2.GaussianBlur(sky, (0, 0), 0.012 * self.sw)

    # --- the camera ---------------------------------------------------------------------------------------------------------
    def view(self, f: int, z0: float | None = None) -> dict:
        """The camera at frame ``f``: zoom ``s``, view centre (share of the picture), parallax translation ``T`` (share of
        the width, for the nearest depth), orbit ``O``, rotation (degrees), depth push ``dp``."""
        z0 = self.z0 if z0 is None else z0
        s, dp = 1.0, 0.0
        cx, cy = 0.5, 0.5
        tx = ty = ox = 0.0
        rot = 0.0
        pulls = []
        far = self.p.get("far_share", 0.2)
        for seg in self.p.get("cameras", []):
            u = L.segment_u({"from": seg["from"], "to": seg["to"], "easing": seg.get("easing", "ease_in_out")}, f, self.n)
            st = float(seg.get("strength", 1.0))
            d = seg.get("direction")
            if seg["op"] == "push":
                s *= 1 + PUSH_SCALE * st * u
                dp += DEPTH_PUSH * st * u
                pulls.append((seg, u))
            elif seg["op"] == "pull":
                s *= 1 + PUSH_SCALE * st * (1 - u)
                dp += DEPTH_PUSH * st * (1 - u)
                pulls.append((seg, 1 - u))
            elif seg["op"] == "truck":
                tx += NEAR_TRAVEL * st * u * (-1 if d == "left" else 1)
            elif seg["op"] == "crane":
                ty += NEAR_TRAVEL * st * u * (1 if d == "down" else -1)
            elif seg["op"] == "pan":
                cx += NEAR_TRAVEL * st * u * (-1 if d == "left" else 1)
            elif seg["op"] == "tilt":
                cy += NEAR_TRAVEL * st * u * (1 if d == "down" else -1) * self.sw / self.sh
            elif seg["op"] == "orbit":
                ox += NEAR_TRAVEL * st * u * (-1 if d == "left" else 1)
        # a push/pull with a target moves the view towards it, but never further than the zoom's own margin allows
        zs = z0 * s
        half_x = (1 - 1 / zs) / 2 - MARGIN
        half_y = (1 - 1 / zs) / 2 - MARGIN * self.sw / self.sh
        for seg, amount in pulls:
            pt = self.point_of(seg.get("target"))
            if pt is None:
                continue
            gx, gy = pt[0] / self.sw - cx, pt[1] / self.sh - cy
            cx += float(np.clip(RECENTRE * amount * gx, -max(0, half_x), max(0, half_x)))
            cy += float(np.clip(RECENTRE * amount * gy, -max(0, half_y), max(0, half_y)))
        h = self.p.get("handheld")
        if h:
            t = f / self.fps
            cx += HAND_TR * h * L._wave(t, self.seed, 0)
            cy += HAND_TR * h * L._wave(t, self.seed, 1) * self.sw / self.sh
            rot += HAND_ROT * h * L._wave(t, self.seed, 2)
        return {"s": s, "cx": cx, "cy": cy, "tx": tx, "ty": ty, "ox": ox, "rot": rot, "dp": dp, "far": far, "z0": z0}

    def _coef(self, v: dict, d):
        """For depth ``d`` (scalar or array): the source point (working px) under the frame centre."""
        par = v["far"] + (1 - v["far"]) * d
        orb = np.maximum(-1.0, (d - self.focus_d) / max(1e-3, 1 - self.focus_d))
        ccx = v["cx"] * self.sw + (v["tx"] * par + v["ox"] * orb) * self.sw
        ccy = v["cy"] * self.sh + v["ty"] * par * self.sw
        return ccx, ccy

    def matrix(self, v: dict, d: float) -> np.ndarray:
        """2x3 output->source affine for a rigid layer at depth ``d``."""
        ccx, ccy = self._coef(v, d)
        k = self.cover_k(v, d)
        th = math.radians(v["rot"])
        a, b = k * math.cos(th), k * math.sin(th)
        return np.array([[a, -b, ccx - a * self.W / 2 + b * self.H / 2],
                         [b, a, ccy - b * self.W / 2 - a * self.H / 2]], dtype=np.float64)

    def cover_k(self, v: dict, d):
        """Working pixels per output pixel at depth ``d``."""
        base = max(self.sw / self.W, self.sh / self.H)
        return base / (v["z0"] * v["s"] * (1 + v["dp"] * d))

    def bg_maps(self, v: dict):
        """Per-pixel output->source maps of the background (its own smoothed depth, two fixed-point steps)."""
        cv2 = self.cv2
        th = math.radians(v["rot"])
        c, s_ = math.cos(th), math.sin(th)
        rx = c * self.oxx - s_ * self.oyy
        ry = s_ * self.oxx + c * self.oyy
        d = np.full((self.H, self.W), 0.5, np.float32)
        for _ in range(3):
            k = self.cover_k(v, d)
            ccx, ccy = self._coef(v, d)
            mx = (k * rx + ccx).astype(np.float32)
            my = (k * ry + ccy).astype(np.float32)
            d = cv2.remap(self.bg_depth, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return mx, my, d

    def _unfold_background(self) -> None:
        """The background is one sheet warped by its depth. Where the depth jumps (a near post against the far field) a
        strong move makes the warp fold over itself, and the fold draws mirrored strokes that the picture does not have
        (S01 C3, the crane: a wire loop beside the right post). The depth is softened only where its slope times the
        largest parallax of the shot would pass ``UNFOLD_PX`` pixels per pixel: the sheet then stretches instead of folding.
        ``self.unfold`` records the largest parallax and the share of the picture that was softened."""
        cv2 = self.cv2
        fr = sorted(set(list(range(0, self.n, max(1, self.n // 24))) + [self.n - 1]))
        pts = np.array([[0, 0, 1], [self.W - 1, 0, 1], [0, self.H - 1, 1], [self.W - 1, self.H - 1, 1],
                        [self.W / 2, self.H / 2, 1]], float).T
        P = 0.0
        for f in fr:
            v = self.view(f)
            P = max(P, float(np.abs(self.matrix(v, 1.0) @ pts - self.matrix(v, 0.0) @ pts).max()))
        bd = self.bg_depth
        softened = np.zeros(bd.shape, bool)
        if P > 0:
            gmax = UNFOLD_PX / P
            sig = max(1.0, 0.002 * self.sw)
            for _ in range(UNFOLD_ITERS):
                gy, gx = np.gradient(bd)
                steep = (np.hypot(gx, gy) > gmax).astype(np.uint8)
                if not steep.any():
                    break
                softened |= steep > 0
                r = int(3 * sig) | 1
                m = cv2.GaussianBlur(cv2.dilate(steep, np.ones((r, r), np.uint8)).astype(np.float32), (0, 0), sig)
                bd = bd * (1 - m) + cv2.GaussianBlur(bd, (0, 0), sig) * m
                sig = min(sig * 1.25, 0.03 * self.sw)
        self.bg_depth = bd.astype(np.float32)
        self.unfold = {"parallax_px": round(P, 1), "softened_share": round(float(softened.mean()), 4)}

    def _fit_zoom(self) -> float:
        """The smallest base zoom that keeps every depth's view inside the picture on every frame."""
        ds = [0.0, 0.5, 1.0] + [o["d"] for o in self.objects]
        corners = np.array([[0, 0, 1], [self.W - 1, 0, 1], [0, self.H - 1, 1], [self.W - 1, self.H - 1, 1]], float).T
        fr = sorted(set(list(range(0, self.n, max(1, self.n // 24))) + [self.n - 1]))

        def fits(z):
            for f in fr:
                v = self.view(f, z)
                for d in ds:
                    q = self.matrix(v, d) @ corners
                    if q[0].min() < 0 or q[1].min() < 0 or q[0].max() > self.sw - 1 or q[1].max() > self.sh - 1:
                        return False
            return True
        lo, hi = 1.0, 1.6
        if fits(lo):
            return lo
        for _ in range(16):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if fits(mid) else (mid, hi)
        return hi

    # --- one frame ----------------------------------------------------------------------------------------------------------
    def render(self, f: int, tele: dict | None = None) -> np.ndarray:
        cv2 = self.cv2
        v = self.view(f)
        mx, my, dbg = self.bg_maps(v)
        rgb = cv2.remap(self.plate, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        fill = cv2.remap(self.hole, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        depth = dbg.copy()
        layers = []
        sway = {e.get("mask"): float(e.get("strength", 1.0)) for e in self.p.get("effects", []) if e["op"] == "subject_sway"}
        for o in self.objects:
            m = self.matrix(v, o["d"])
            if o["id"] in sway:            # a figure breathes and sways a little about its feet (no body animation: LP-02)
                ys, xs = np.nonzero(o["alpha"] > 0.5)
                m = L._sway(m, {"fps": self.fps}, f, (float(xs.mean()), float(ys.max())), sway[o["id"]])
            w = cv2.warpAffine(o["rgba"], m, (self.W, self.H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
            a = w[..., 3] / 255.0
            rgb = rgb * (1 - a[..., None]) + w[..., :3] * a[..., None]
            depth = depth * (1 - a) + o["d"] * a
            fill = fill * (1 - a)
            layers.append({"id": o["id"], "alpha": a, "m": m})
        rgb = self._effects(rgb, depth, f, v, mx, my, layers)
        rgb = self._rack(rgb, depth, f)
        if tele is not None:
            tele.update({"view": v, "fill": fill, "depth": depth, "layers": layers, "bg_maps": (mx, my)})
        return np.clip(rgb + 0.5, 0, 255).astype(np.uint8)

    # --- effects ------------------------------------------------------------------------------------------------------------
    def _to_out(self, src_xy, mx=None, my=None, v=None, d=None):
        """A working-pixel point -> output pixels (inverse of the layer's affine at depth ``d``)."""
        if d is None:
            x, y = int(np.clip(src_xy[0], 0, self.sw - 1)), int(np.clip(src_xy[1], 0, self.sh - 1))
            d = float(self.bg_depth[y, x])
        m = self.matrix(v, d)
        inv = self.cv2.invertAffineTransform(m)
        q = inv @ np.array([src_xy[0], src_xy[1], 1.0])
        return float(q[0]), float(q[1]), d

    def _layer_of_light(self, li: dict, layers: list[dict]):
        """The object a light sits on (its matrix), or None for the background."""
        x, y = int(np.clip(li["point"][0], 0, self.sw - 1)), int(np.clip(li["point"][1], 0, self.sh - 1))
        for o in reversed(self.objects):
            if o["alpha"][y, x] > 0.5:
                return o
        return None

    def _warp_mask(self, mask, mx, my, v, li, layers):
        cv2 = self.cv2
        host = self._layer_of_light(li, layers)
        if host is None:
            return cv2.remap(mask, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        m = self.matrix(v, host["d"])
        return cv2.warpAffine(mask, m, (self.W, self.H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                              borderMode=cv2.BORDER_CONSTANT)

    def _effects(self, rgb, depth, f, v, mx, my, layers):
        cv2 = self.cv2
        t = f / self.fps
        W, H = self.W, self.H
        far = np.clip(1.0 - depth, 0, 1)
        zoom = 1.0 / self.cover_k(v, 0.5)
        for i, e in enumerate(self.p.get("effects", [])):
            op, s = e["op"], float(e.get("strength", 1.0))
            prm = e.get("params", {})
            if op in ("fire", "candle", "glow"):
                for lid in e["lights"]:
                    li = self.lights.get(lid)
                    if li is None:
                        continue
                    speed = {"fire": 1.0, "candle": 0.55, "glow": 0.8}[op]
                    g = self._flicker_id(i, lid, t, speed)
                    ox, oy, _ = self._to_out(li["point"], v=v, d=li.get("d"))
                    host = self._layer_of_light(li, layers)
                    if host is not None:
                        ox, oy, _ = self._to_out(li["point"], v=v, d=host["d"])
                    # the flame: brightness flicker and a small upward-flowing deformation inside its mask
                    if "mask" in li:
                        fm = self._warp_mask(li["mask"], mx, my, v, li, layers)
                        amp = {"fire": 0.22, "candle": 0.14, "glow": 0.25}[op] * s
                        rgb = rgb * (1 + amp * g * fm[..., None] * np.array([1.0, 0.85, 0.6], np.float32))
                        if op != "glow" and fm.max() > 0.05:
                            rgb = self._deform_flame(rgb, fm, li, t, i, s, zoom, op)
                    # the spill: the flicker of the light on the surfaces round it, falling off with distance
                    R = float(prm.get("spill_radius", {"fire": 0.10, "candle": 0.05, "glow": 0.03}[op])) * W
                    R = R * zoom
                    spill_amp = float(prm.get("spill", {"fire": 0.10, "candle": 0.07, "glow": 0.05}[op])) * s
                    qs = 4
                    yy, xx = np.mgrid[0:H // qs, 0:W // qs].astype(np.float32) * qs
                    fall = np.exp(-(((xx - ox) ** 2 + (yy - oy) ** 2) / (R * R)))
                    fall = cv2.resize(fall.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
                    warm = np.array([1.0, 0.72, 0.42], np.float32)
                    base = float(prm.get("spill_base", 0.0)) * s
                    rgb = rgb * (1 + (base + spill_amp * (0.5 + 0.5 * g)) * fall[..., None] * warm)
            elif op == "fire_box":    # Stage B v1 behaviour: one feathered box flickers as a whole
                x0, y0, x1, y1 = e["box"]
                field = self._box_field(e["box"], mx, my)
                g = s * (0.10 * math.sin(2 * math.pi * 4.3 * t + 0.7) + 0.06 * math.sin(2 * math.pi * 7.9 * t + 2.1)
                         + 0.05 * L._wave(t * 3.0, self.seed, 3))
                rgb = rgb * (1 + g * field[..., None] * np.array([1.0, 0.78, 0.5], np.float32))
            elif op == "mist":
                n = L._tile_at(self, self.tiles["a"], 0.012 * t, 0.004 * t)
                keep = 1.0 - 0.97 * cv2.remap(self.sky, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                col = np.array(prm.get("colour", [206, 209, 214]), np.float32)
                a = s * (0.10 + 0.22 * n) * far ** float(prm.get("power", 1.5)) * keep
                if e.get("box"):
                    a = a * self._box_field(e["box"], mx, my, feather=0.06)
                rgb = rgb * (1 - a[..., None]) + col * a[..., None]
            elif op == "smoke":
                rgb = self._smoke(rgb, depth, e, i, t, v, s, zoom)
            elif op == "sun_shaft":
                li = self.lights.get(e.get("light", "sun"))
                pt = li["point"] if li else (e["origin"][0] * self.sw, e["origin"][1] * self.sh)
                fx, fy, _ = self._to_out(pt, v=v, d=0.0)
                qs = 4
                yy, xx = np.mgrid[0:H // qs, 0:W // qs].astype(np.float32) * qs
                ang = np.arctan2(yy - fy, xx - fx)
                rad = np.hypot(yy - fy, xx - fx) / W
                ph = self.phases[i]
                rays = sum(np.cos(nn * ang + ph[j] + 0.25 * (j + 1) * t) for j, nn in enumerate((3, 5, 8)))
                rays = np.clip(rays / 3.0 + 0.15, 0, 1) ** 1.5 * (0.7 + 0.3 * math.sin(2 * math.pi * 0.2 * t + ph[0]))
                gate = (1 - np.exp(-(rad / 0.06) ** 2)) * np.exp(-(rad / 0.6) ** 2)
                rays = cv2.GaussianBlur((rays * gate).astype(np.float32), (0, 0), 6.0)
                rays = cv2.resize(rays, (W, H), interpolation=cv2.INTER_LINEAR)
                # only the far, visible surfaces take the shaft: the people and the near wire stand in front of it
                rgb = rgb + np.array([255, 228, 180], np.float32) * (0.40 * s * rays * far ** 1.2)[..., None]
            elif op == "cloud_drift":
                sky = cv2.remap(self.sky, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                if e.get("box"):
                    sky = np.maximum(sky, self._box_field(e["box"], mx, my, feather=0.06) * (far > 0.9))
                n_ = L._tile_at(self, self.tiles["a"], 0.006 * t, 0.002 * t) - 0.5
                dx = -0.012 * W * s * float(L.smooth(t / max(1e-3, self.n / self.fps))) + 6.0 * s * n_
                dy = 2.5 * s * n_
                yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                moved = cv2.remap(np.clip(rgb, 0, 255), xx + dx * sky, yy + dy * sky, cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REFLECT)
                rgb = moved
            elif op in LFX.OPS:
                rgb = LFX.apply(self, rgb, depth, e, i, t, v, mx, my, layers, zoom)
            elif op == "heat_haze":
                for lid in e["lights"]:
                    li = self.lights.get(lid)
                    if li is None or "mask" not in li:
                        continue
                    fm = self._warp_mask(li["mask"], mx, my, v, li, layers)
                    hgt = max(8.0, li.get("height", 20.0) * zoom * (self.W / self.sw) * float(prm.get("rise", 3.0)))
                    col = cv2.dilate((fm > 0.2).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=3).astype(np.float32)
                    up = np.zeros_like(col)
                    sh_ = int(hgt)
                    for kk in range(0, sh_, max(1, sh_ // 8)):
                        up[: H - kk] = np.maximum(up[: H - kk], col[kk:] * (1 - kk / sh_))
                    up = cv2.GaussianBlur(up, (0, 0), 3.0)
                    n = L._tile_at(self, self.tiles["c"], 0.0, 0.5 * t) - 0.5
                    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                    rgb = cv2.remap(np.clip(rgb, 0, 255), xx + 3.0 * s * n * up, yy + 1.5 * s * n * up, cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT)
        return rgb

    def _flicker_id(self, i: int, lid: str, t: float, speed: float) -> float:
        k = _seed(f"{self.p.get('shot_id')}:{lid}")
        ph = [((k >> (4 * j)) % 628) / 100.0 for j in range(3)]
        sp = speed * (0.85 + 0.3 * ((k >> 13) % 100) / 100.0)
        return float(0.5 * math.sin(2 * math.pi * 4.1 * sp * t + ph[0]) + 0.3 * math.sin(2 * math.pi * 7.3 * sp * t + ph[1])
                     + 0.2 * math.sin(2 * math.pi * 11.9 * sp * t + ph[2]))

    def _deform_flame(self, rgb, fm, li, t, i, s, zoom, op):
        """The flame's own motion: an upward-flowing sideways wobble, strongest at its tip, only inside (and just round) it."""
        cv2 = self.cv2
        ys, xs = np.nonzero(fm > 0.2)
        if len(xs) < 4:
            return rgb
        pad = 12
        x0, x1 = max(0, xs.min() - pad), min(self.W, xs.max() + pad + 1)
        y0, y1 = max(0, ys.min() - pad), min(self.H, ys.max() + pad + 1)
        sub = rgb[y0:y1, x0:x1]
        hh, ww = sub.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        tip = np.clip(1.0 - yy / max(1, hh - 1), 0, 1)            # 1 at the top of the flame, 0 at its base
        k = _seed(f"{li['id']}:{i}")
        speed = 2.6 if op == "fire" else 1.4
        wob = np.sin(2 * math.pi * (yy / max(6.0, hh * 0.45) + speed * t) + (k % 628) / 100.0)
        amp = (0.10 if op == "fire" else 0.06) * ww * s
        field = cv2.GaussianBlur(cv2.dilate(fm[y0:y1, x0:x1], np.ones((3, 3), np.uint8), iterations=3), (0, 0), 2.0)
        dx = amp * wob * tip * field
        dy = -0.04 * hh * s * (0.5 + 0.5 * np.sin(2 * math.pi * 1.7 * speed * t + k % 7)) * tip * field
        moved = cv2.remap(np.ascontiguousarray(sub), (xx + dx).astype(np.float32), (yy + dy).astype(np.float32),
                          cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out = rgb.copy()
        out[y0:y1, x0:x1] = moved
        return out

    def _smoke(self, rgb, depth, e, i, t, v, s, zoom):
        """A plume from a source point: rising, widening, drifting; the surfaces nearer than the source cover it."""
        cv2 = self.cv2
        W, H = self.W, self.H
        if e.get("light") and e["light"] in self.lights:
            li = self.lights[e["light"]]
            src, ds = li["point"], li.get("d")
        else:
            src = (e["point"][0] * self.sw, e["point"][1] * self.sh)
            ds = None
        sx, sy, ds = self._to_out(src, v=v, d=ds)
        prm = e.get("params", {})
        height = float(prm.get("height", 0.35)) * H * zoom
        width0 = float(prm.get("width", 0.012)) * W * zoom
        drift = float(prm.get("drift", 0.25))
        qs = 2
        yy, xx = np.mgrid[0:H // qs, 0:W // qs].astype(np.float32) * qs
        up = np.clip((sy - yy) / max(1.0, height), 0, 1.2)
        cx = sx + drift * (sy - yy).clip(0) * (0.6 + 0.4 * math.sin(0.4 * t)) + 0.02 * W * zoom * np.sin(3.0 * up - 0.7 * t)
        wid = width0 * (1 + 5.0 * up)
        core = np.exp(-((xx - cx) / wid) ** 2) * (up > 0) * np.clip(1.15 - up, 0, 1)
        n = L._tile_at(self, self.tiles["b"], 0.004 * t, 0.06 * t)
        n2 = L._tile_at(self, self.tiles["a"], -0.01 * t, 0.03 * t)
        dens = cv2.resize(core.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR) * np.clip(n * n2 * 2.6 - 0.15, 0, 1)
        behind = np.clip((ds + 0.02 - depth) / 0.04, 0, 1)    # 1 where the visible surface is farther than the smoke
        a = np.clip(float(prm.get("opacity", 0.55)) * s * dens * behind, 0, 0.8)
        col = np.array(prm.get("colour", [150, 146, 150]), np.float32)
        return rgb * (1 - a[..., None]) + col * a[..., None]

    def _box_field(self, box, mx, my, feather=0.04):
        cv2 = self.cv2
        if not hasattr(self, "_boxes"):
            self._boxes = {}
        key = (tuple(box), feather)
        if key not in self._boxes:
            x0, y0, x1, y1 = box
            xs = np.linspace(0, 1, self.sw, dtype=np.float32)[None, :]
            ys = np.linspace(0, 1, self.sh, dtype=np.float32)[:, None]
            m = (L.smooth(np.minimum(xs - x0, x1 - xs) / feather) * L.smooth(np.minimum(ys - y0, y1 - ys) / feather))
            m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.02 * self.sw) if feather == 0.04 else m.astype(np.float32)
            self._boxes[key] = m / max(1e-6, float(m.max()))
        return cv2.remap(self._boxes[key], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    # --- rack focus ---------------------------------------------------------------------------------------------------------
    def rack_focus_at(self, f: int) -> float | None:
        r = self.p.get("rack")
        if not r:
            return None
        d0 = self.depth_of(r["from"])
        d1 = self.depth_of(r["to"])
        span = max(1, int(r.get("frames", round(L.RACK_S * self.fps))))
        u = float(L.smooth((f - r["at"]) / span))
        return d0 + (d1 - d0) * u

    def _rack(self, rgb, depth, f):
        fd = self.rack_focus_at(f)
        if fd is None:
            return rgb
        cv2 = self.cv2
        r = self.p["rack"]
        sig = float(r.get("sigma_px", RACK_SIGMA_PX)) * self.H / 1080.0 * float(r.get("strength", 1.0))
        span = float(r.get("span", RACK_SPAN))
        lvl = np.clip(np.abs(depth - fd) / span, 0, 1) * 3.0
        pyr = [rgb] + [cv2.GaussianBlur(rgb, (0, 0), sig * (j + 1) / 3) for j in range(3)]
        out = np.zeros_like(rgb)
        for j in range(3):
            wgt = np.clip(1 - np.abs(lvl - j), 0, 1)
            out += pyr[j] * wgt[..., None]
        out += pyr[3] * np.clip(lvl - 2, 0, 1)[..., None]
        return out


def render_clip(picture: Path, layers: dict, plan: dict, out_mp4: Path, size=(1920, 1080), fps: int = 24,
                watch=None, ghost_every: int = 4) -> dict:
    """Render one directed shot to ``out_mp4``; a ``qa.motion_intent.Watch`` (optional) receives every frame with its fill
    map and, on the sampled frames, each object's visible mask and shift against the background under it since frame 0."""
    import cv2
    t0 = time.time()
    st = Stage(picture, layers, plan, size, fps)
    prep = time.time() - t0
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.with_name(out_mp4.stem + ".part.mp4")
    W, H = size
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-frames:v", str(st.n), "-c:v", "libx264", "-preset", "medium",
                             "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    first = last = None
    views = []
    p0 = {}
    an = (960, 540)
    t1 = time.time()
    try:
        for f in range(st.n):
            tl: dict = {}
            fr = st.render(f, tl)
            proc.stdin.write(fr.tobytes())
            if f == 0:
                first = fr
            last = fr
            v = tl["view"]
            views.append({k: (round(float(x), 5) if isinstance(x, float) else x) for k, x in v.items()})
            rows = None
            if watch is not None:
                rows = []
                sample = f % ghost_every == 0
                for lay in tl["layers"]:
                    o = next(x for x in st.objects if x["id"] == lay["id"])
                    cx, cy = o["centroid"]
                    p_obj = cv2.invertAffineTransform(lay["m"]) @ np.array([cx, cy, 1.0])
                    d_bg = float(st.bg_depth[int(cy), int(cx)])
                    p_bg = cv2.invertAffineTransform(st.matrix(v, d_bg)) @ np.array([cx, cy, 1.0])
                    rel = p_obj - p_bg
                    p0.setdefault(lay["id"], rel)
                    if sample:
                        dv = (rel - p0[lay["id"]]) * (an[0] / W)
                        rows.append({"id": lay["id"], "alpha": cv2.resize(lay["alpha"], an, interpolation=cv2.INTER_AREA),
                                     "v": (float(dv[0]), float(dv[1]))})
                watch.add(f, fr, tl["fill"], rows if sample else None)
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {plan.get('shot_id')}")
    tmp.replace(out_mp4)
    spf = (time.time() - t1) / max(1, st.n)
    return {"renderer": VERSION, "shot_id": plan.get("shot_id"), "frames": st.n, "fps": fps, "resolution": [W, H],
            "path": str(out_mp4), "prep_s": round(prep, 2), "sec_per_frame": round(spf, 3), "base_zoom": round(st.z0, 4),
            "objects": [{"id": o["id"], "depth": round(o["d"], 3)} for o in st.objects],
            "cost_usd": 0.0, "output_sha256": hashlib.sha256(out_mp4.read_bytes()).hexdigest(),
            "views": views, "stage": st, "first": first, "last": last}
