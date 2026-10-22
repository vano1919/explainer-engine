"""The hybrid model's thirty-second test cartoon (the creator, 2026-10-22 19:35 and 19:38): an Ice Age valley painted in
layers by the image model, two heroes painted as turnarounds and expression sheets and moved by the bending rig
(``bend_rig``), a 2.5D camera, a sled that slides away into the depth. Everything after the pictures is code and free.

The story (English for the viewer): two of the hundred people dropped into the Ice Age. Dev drags the sled he made from a
suitcase to Marta and presents it; she is not impressed; he throws up his arms, lets go of the rope, the sled slides away
down the slope; he chases it, trips and lands in the snow; Marta helps him up; they watch it vanish. "Great plan."

The world is 2.5D: the far layer (sky and glaciers) moves with a fifth of the camera, the middle layer (the snowfield the
heroes stand on) with the camera, the near layer (rocks) faster; an object at depth ``d`` is drawn ``1/d`` the size and
moves ``1/d`` as much, so the sled shrinks toward the horizon. Every frame is a pure function of its time.

    python -m explainer_engine.production.ice_short render --assets <dir> --out <dir> [--fps 24] [--voice <dir>]
    python -m explainer_engine.production.ice_short check --assets <dir>

``<assets>``: ``world/`` (far.png, mid.png and near.png keyed to alpha, sled_side.png), ``dev/`` and ``marta/`` (character
folders as ``bend_rig`` reads them: ``turn.png``, ``parts_<view>.json`` with the build, ``head_<expr>_<view>.png``).
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import wave
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from explainer_engine.production import bend_rig as R

W, H = 1920, 1080
DURATION = 30.0
S0 = 0.77                 # world px per rig px for a full-size hero at depth 1
STAND_WORLD = 731.5       # the world y the heroes stand on (depth 1)
HORIZON_WORLD = 376.0     # the world y of the far snow ridge (where depth runs out)
MID_SCALE = 1.316         # world px per px of the middle layer's picture
MID_ROW, MID_COL = 1100, 1100   # the picture's pixel that sits at (world 0, STAND_WORLD)
GROUND_SCREEN = 0.82 * H  # the camera keeps the depth-1 ground here
SIZES = {"dev": 1.0, "marta": 0.86}

# --- the camera: keys (t, cx, zoom), eased between ------------------------------------------------------------------------
CAMERA = [(0.0, -250.0, 1.0), (5.0, 60.0, 1.0), (7.0, 380.0, 1.5), (11.5, 390.0, 1.55), (13.0, 560.0, 1.2),
          (16.0, 1060.0, 1.15), (17.5, 1330.0, 1.25), (21.0, 1380.0, 1.2), (25.0, 1420.0, 1.4), (30.0, 1440.0, 1.5)]


def camera(t: float) -> tuple[float, float, float]:
    """(cx, cy, zoom) at ``t``; cy keeps the depth-1 ground at GROUND_SCREEN."""
    for (t0, x0, z0), (t1, x1, z1) in zip(CAMERA, CAMERA[1:]):
        if t0 <= t <= t1:
            u = R.ease((t - t0) / (t1 - t0))
            cx, z = R.lerp(x0, x1, u), R.lerp(z0, z1, u)
            break
    else:
        cx, z = CAMERA[-1][1], CAMERA[-1][2]
    return cx, STAND_WORLD - (GROUND_SCREEN - H / 2) / z, z


def to_screen(wx: float, wy_at_depth1: float, d: float, cam) -> tuple[float, float, float]:
    """A point of depth ``d`` (its height above the ground given at depth-1 scale) -> (screen x, screen y, scale)."""
    cx, cy, z = cam
    ground1 = (STAND_WORLD - cy) * z + H / 2
    horizon = (HORIZON_WORLD - cy) * z + H / 2
    gd = horizon + (ground1 - horizon) / d
    k = z / d
    return (wx - cx) * k + W / 2, gd + (wy_at_depth1 - STAND_WORLD) * k, k


# --- the actors -----------------------------------------------------------------------------------------------------------
@dataclass
class Actor:
    name: str
    folder: str
    build: R.Build
    size: float
    segments: list            # (t0, t1, kind, obj): "loco" Loco | "keys" (keys, facing) | "fn" callable t -> Pose
    look: list                # (t, expr) timeline
    views: list               # (t, view, facing) timeline: the drawing and the side it faces
    depth: object             # callable t -> depth
    blinks: tuple = ()

    def raw(self, t: float) -> R.Pose:
        with R.use_build(self.build):
            for t0, t1, kind, obj in self.segments:
                if t0 <= t < t1 or (t0, t1, kind, obj) == self.segments[-1]:
                    break
            if kind == "loco":
                return obj.pose(t)
            if kind == "keys":
                keys, f = obj
                return R.keyed_pose(keys, t, f, R.shoulder_of)
            return obj(t)

    def pose(self, t: float) -> R.Pose:
        p = self.raw(t)
        for te, e in self.look:
            if t >= te:
                p.expr = e
        for tv, v, f in self.views:
            if t >= tv:
                p.view = v
                if f:
                    p.facing = f
        p.blink = max([max(0.0, 1 - abs(t - b) / 0.07) for b in self.blinks] + [0.0])
        return p


def _ab(x, y, p=0.0, c=False):
    return ("abs", x, y, p, c)


def _stand_feet(x: float, f: int, gap: float = 0.07) -> dict:
    return {R.near_side(f): (x - f * gap * R.B, R.ANK, 0.0, True), R.SIDES[1 - R.SIDES.index(R.near_side(f))]:
            (x + f * gap * R.B, R.ANK, 0.0, True)}


def _idle(feet: dict, x: float, b: R.Build, f: int, arms_fn=None, torso_fn=None, head_fn=None):
    """A standing pose that breathes; ``arms_fn``/``torso_fn``/``head_fn`` (t -> value) add the acting."""
    def fn(t):
        breath = 0.006 * R.B * math.sin(2 * math.pi * t / 2.4)
        p = R.Pose(f, (x, R.GROUND - b.stand * R.B + breath), torso_fn(t) if torso_fn else 2.0,
                   head_fn(t) if head_fn else 0.0, feet=dict(feet))
        p.hip = R.reach_clamp(p.hip, p.feet)
        p.arms = arms_fn(t) if arms_fn else {s: ("fk", 4.0, 12.0) for s in R.SIDES}
        return p
    return fn


def _world_x(rig_x: float, size: float) -> float:
    return rig_x * S0 * size


def _rig_x(world_x: float, size: float) -> float:
    return world_x / (S0 * size)


# the times of the story
T_STOP = 5.0          # Dev arrives
T_LINE1 = 6.8         # "Behold! The first sled of the Ice Age." (the take is 3.4 s)
T_LINE2 = 10.4        # Marta: "It's a suitcase."
T_THROW = 11.6        # Dev throws up his arms: the rope drops
T_SLIDE = 12.0        # the sled starts to slide
T_RUN = 13.0          # Dev runs after it
T_LINE3 = 26.4        # Marta: "Great plan."
LINES = [(T_LINE1, "dev", "Behold! The first sled of the Ice Age."), (T_LINE2, "marta", "It's a suitcase."),
         (T_LINE3, "marta", "Great plan.")]


@lru_cache(maxsize=2)
def cast(assets: str) -> dict:
    a = Path(assets)
    dev_b, marta_b = R.load_build(str(a / "dev")), R.load_build(str(a / "marta"))
    B = R.B
    # --- Dev: walks in dragging the sled, presents, throws up his arms, chases, trips, is helped up -------------------
    with R.use_build(dev_b):
        walk_g = dev_b.gait(R.WALK)
        v_walk = 0.62 * B * (dev_b.thigh + dev_b.shin) / 0.42

        def walk_speed(t, _ph):
            return v_walk if t < T_STOP - 0.35 else v_walk * max(0.0, 1 - (t - (T_STOP - 0.35)) / 0.35)

        walk = R.Loco(walk_g, 1, 0.0, T_STOP, walk_speed, _rig_x(-760.0, 1.0))
        stand_feet = walk.feet(T_STOP + walk.settle + 0.01)
        xs = walk.x(T_STOP)
        near, far = R.near_side(1), R.SIDES[1 - R.SIDES.index(R.near_side(1))]

        def present_arms(t):
            # the presenting sweep toward the sled behind him, then the indignant throw, then the anticipation
            if t < T_LINE1 - 0.3:
                u = R.ease((t - (T_STOP + 0.4)) / 0.8)
                return {near: ("fk", R.lerp(4, -55, u), R.lerp(12, 8, u)), far: ("fk", R.lerp(4, 70, u), R.lerp(12, 30, u))}
            if t < T_THROW:
                w = 6 * math.sin(2 * math.pi * (t - T_LINE1) / 0.9) if t < T_LINE1 + 2.2 else 0.0
                return {near: ("fk", -55 + w * 0.5, 8), far: ("fk", 70 + w, 30)}
            if t < T_RUN - 0.45:
                u = R.ease((t - T_THROW) / 0.25)
                return {near: ("fk", R.lerp(-55, 160, u), R.lerp(8, 20, u)), far: ("fk", R.lerp(70, 165, u), R.lerp(30, 20, u))}
            u = R.ease((t - (T_RUN - 0.45)) / 0.3)
            return {s: ("fk", R.lerp(160, -35, u), R.lerp(20, 40, u)) for s in R.SIDES}

        def present_torso(t):
            if t < T_THROW:
                return 2.0 - 4.0 * R.ease((t - T_STOP) / 0.6)  # chest out
            if t < T_RUN - 0.45:
                return -6.0
            return R.lerp(-6.0, 22.0, R.ease((t - (T_RUN - 0.45)) / 0.4))  # the crouch before the run

        present = _idle(stand_feet, xs, dev_b, 1, present_arms, present_torso,
                        lambda t: -10.0 if T_LINE1 < t < T_LINE1 + 2.4 else 0.0)
        run_g = dev_b.gait(R.RUN)
        ph = R.entry_phase(run_g, 1, xs, stand_feet)
        v_run = 1.05 * B * (dev_b.thigh + dev_b.shin) / 0.42
        run = R.Loco(run_g, 1, T_RUN, T_RUN + 4.0, lambda t, _ph: v_run * R.ease((t - T_RUN) / 0.5), xs, phase0=ph,
                     entry=stand_feet, entry_arms=(-35.0, 40.0))
        # the trip: the first foot to leave the ground after 3.0 s of running
        tj = None
        for k in range(int((T_RUN + 3.0) * 240), int((T_RUN + 4.0) * 240)):
            t = k / 240.0
            fa, fb = run.feet(t), run.feet(t + 1 / 240.0)
            for s in R.SIDES:
                if fa[s][3] and not fb[s][3]:
                    tj, trail = t, s
                    break
            if tj:
                break
        lead = R.SIDES[1 - R.SIDES.index(trail)]
        run.t1 = tj
        pre = run.pose(tj)
        hx = pre.hip[0]
        xi = hx + 1.0 * B          # the hips at the impact
        hand_x = xi + 0.27 * B
        lie_y = R.GROUND - 0.10 * B
        stand_y = R.GROUND - dev_b.stand * B
        fk = lambda a, e: ("fk", a, e)  # noqa: E731
        planted = {lead: _ab(xi - 0.36 * B, R.GROUND - 0.07 * B, 75), trail: _ab(xi - 0.34 * B, R.GROUND - 0.06 * B, 75)}
        hands = {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), R.GROUND - 0.03 * B) for s in R.SIDES}
        t_help = 22.6
        # where Marta's hand meets his (Dev's rig px): reaching up from the knees, then up with him as he stands
        grip0 = (xi + 0.12 * B, R.GROUND - 0.50 * B)
        grip1 = (xi + 0.16 * B, R.GROUND - 0.66 * B)
        keys = [
            R.Key(tj, pre.hip, run_g.lean, 0, {s: _ab(*pre.feet[s]) for s in R.SIDES}, dict(pre.arms)),
            R.Key(tj + 0.16, (hx + 0.30 * B, R.GROUND - 0.34 * B), 34, 6,
                  {lead: _ab(hx + 0.42 * B, R.ANK, 0, True), trail: _ab(hx + 0.02 * B, R.GROUND - 0.06 * B, 35, True)},
                  {s: fk(50, 40) for s in R.SIDES}, squash=0.96),
            R.Key(tj + 0.38, (hx + 0.66 * B, R.GROUND - 0.24 * B), 62, -10,
                  {lead: _ab(hx + 0.36 * B, R.GROUND - 0.10 * B, 40), trail: _ab(hx + 0.20 * B, R.GROUND - 0.12 * B, 50)},
                  {s: fk(95, 10) for s in R.SIDES}),
            R.Key(tj + 0.58, (xi, lie_y), 80, -18, planted, hands, squash=0.86),
            R.Key(tj + 0.72, (xi, lie_y - 0.03 * B), 80, -22, planted, hands, squash=1.03),
            R.Key(tj + 0.88, (xi, lie_y), 80, -12, planted, hands),
            R.Key(t_help - 1.4, (xi, lie_y), 80, -30, planted, hands),
            R.Key(t_help - 0.6, (xi - 0.06 * B, R.GROUND - 0.22 * B), 50, -20, planted, hands),
            R.Key(t_help, (xi - 0.10 * B, R.GROUND - 0.23 * B), 12, -8,
                  {lead: _ab(xi + 0.08 * B, R.ANK, 0, True), trail: _ab(xi - 0.34 * B, R.GROUND - 0.06 * B, 75)},
                  {near: ("ik",) + grip0, far: fk(25, 30)}),
            R.Key(t_help + 0.5, (xi - 0.10 * B, R.GROUND - 0.23 * B), 12, -8,
                  {lead: _ab(xi + 0.08 * B, R.ANK, 0, True), trail: _ab(xi - 0.34 * B, R.GROUND - 0.06 * B, 75)},
                  {near: ("ik",) + grip0, far: fk(25, 30)}),
            R.Key(t_help + 1.2, (xi - 0.02 * B, stand_y), 6, 6,
                  {lead: _ab(xi + 0.08 * B, R.ANK, 0, True), trail: _ab(xi - 0.12 * B, R.ANK, 0, True)},
                  {near: ("ik",) + grip1, far: fk(10, 15)}),
            R.Key(t_help + 1.7, (xi - 0.02 * B, stand_y), 4, 4,
                  {lead: _ab(xi + 0.08 * B, R.ANK, 0, True), trail: _ab(xi - 0.12 * B, R.ANK, 0, True)},
                  {near: ("ik",) + grip1, far: fk(10, 15)}),
            R.Key(t_help + 2.1, (xi - 0.02 * B, stand_y), 2, 6,
                  {lead: _ab(xi + 0.08 * B, R.ANK, 0, True), trail: _ab(xi - 0.12 * B, R.ANK, 0, True)},
                  {s: fk(6, 14) for s in R.SIDES}),
        ]
        end_feet = {lead: (xi + 0.08 * B, R.ANK, 0.0, True), trail: (xi - 0.12 * B, R.ANK, 0.0, True)}
        after = _idle(end_feet, xi - 0.02 * B, dev_b, 1,
                      lambda t: {near: ("fk", 8.0, 16.0), far: ("fk", -6.0 + 3 * math.sin(t * 1.3), 40.0)},
                      lambda t: 4.0, lambda t: 6.0 if t < T_LINE3 + 0.6 else 12.0)
    dev = Actor("dev", str(a / "dev"), dev_b, SIZES["dev"], [
        (0.0, T_STOP + 0.4, "loco", walk), (T_STOP + 0.4, T_RUN, "fn", present), (T_RUN, tj, "loco", run),
        (tj, keys[-1].t, "keys", (keys, 1)), (keys[-1].t, DURATION, "fn", after)],
        look=[(0.0, "neutral"), (T_STOP + 0.3, "proud"), (T_LINE2 + 0.4, "sheepish"), (T_THROW, "shock"),
              (T_SLIDE + 0.5, "scared"), (tj + 0.3, "shock"), (tj + 0.9, "pain"), (t_help - 0.5, "neutral"),
              (t_help + 2.2, "sheepish")],
        views=[(0.0, "side", 1), (T_STOP + 0.5, "three_quarter", 1), (T_RUN - 0.45, "side", 1), (t_help + 2.3, "three_quarter", 1)],
        depth=lambda t: 1.0, blinks=(1.8, 4.2, 6.6, 9.4, 13.9, 21.0, 25.2, 28.4))
    dev.trip, dev.impact, dev.xi, dev.grips, dev.t_help = tj, tj + 0.58, xi, (grip0, grip1), t_help

    # --- Marta: waits, is not impressed, watches, walks over, helps him up ------------------------------------------------
    with R.use_build(marta_b):
        mx = _rig_x(560.0, SIZES["marta"])
        mfeet = _stand_feet(mx, -1, 0.05)
        wait = _idle(mfeet, mx, marta_b, -1,
                     lambda t: {s: ("fk", 6.0 if t < T_LINE2 else 30.0, 14.0 if t < T_LINE2 else 70.0) for s in R.SIDES},
                     lambda t: 3.0, lambda t: 8.0 if T_LINE2 < t < T_LINE2 + 1.2 else 0.0)
        # she turns to watch the sled, then walks to Dev: to where she can reach him
        t_walk0 = 17.4
        # she walks round behind him and stops on his far side, facing him, an arm's length from where he reaches
        target = _rig_x(_world_x(grip0[0], SIZES["dev"]), SIZES["marta"]) + 0.42 * R.B
        mfeet2 = _stand_feet(mx, 1, 0.05)
        watch = _idle(mfeet2, mx, marta_b, 1, lambda t: {s: ("fk", 20.0, 80.0) for s in R.SIDES}, lambda t: 6.0)
        mwalk_g = marta_b.gait(R.WALK)
        v_mw = 0.55 * R.B * (marta_b.thigh + marta_b.shin) / 0.42
        dist = target - mx
        dur = t_help - 0.6 - t_walk0
        v_mw = dist / (dur * 0.95)

        def mwalk_speed(t, _ph):
            u = (t - t_walk0) / dur
            return v_mw * min(1.0, u / 0.08) * (1.0 if u < 0.9 else max(0.0, 1 - (u - 0.9) / 0.1))

        mwalk = R.Loco(mwalk_g, 1, t_walk0, t_help - 0.6, mwalk_speed, mx,
                       phase0=R.entry_phase(mwalk_g, 1, mx, mfeet2), entry=mfeet2, blend=0.3)
        mend = mwalk.feet(t_help - 0.6 + mwalk.settle + 0.01)
        mxe = mwalk.x(t_help - 0.6)
    marta = Actor("marta", str(a / "marta"), marta_b, SIZES["marta"], [], look=[(0.0, "neutral"), (T_LINE1 + 0.8, "unimpressed"),
        (T_LINE2, "talk"), (T_LINE2 + 1.2, "smirk"), (T_SLIDE + 0.6, "worried"), (t_help - 0.2, "smile"), (t_help + 2.2, "smirk"),
        (T_LINE3, "talk"), (T_LINE3 + 0.8, "smirk")],
        views=[(0.0, "three_quarter", -1), (T_SLIDE + 1.6, "three_quarter", 1), (t_walk0, "side", 1), (t_help - 0.4, "three_quarter", -1),
               (t_help + 2.3, "three_quarter", 1)],
        depth=lambda t: 1.35 - 0.35 * R.ease((t - t_walk0) / (t_help - 0.6 - t_walk0)),
        blinks=(2.6, 5.9, 9.0, 12.3, 15.2, 18.4, 24.4, 27.6))
    marta.mx_end = mxe
    marta.mend = mend
    marta.segments = [(0.0, T_SLIDE + 1.6, "fn", wait), (T_SLIDE + 1.6, t_walk0, "fn", watch),
                      (t_walk0, t_help - 0.2, "loco", mwalk), (t_help - 0.2, DURATION, "fn", None)]
    marta.segments[-1] = (t_help - 0.2, DURATION, "fn", _helper(marta, dev, mend, mxe))
    return {"dev": dev, "marta": marta}


def _helper(marta: Actor, dev: Actor, feet: dict, x: float):
    """Marta bends and holds out her hand where Dev reaches, rises with him, then stands with him."""
    b = marta.build
    near = R.near_side(-1)
    far = R.SIDES[1 - R.SIDES.index(near)]

    def fn(t):
        with R.use_build(dev.build):
            dj = R.skeleton(dev.raw(t))
        hand = dj["hand_" + R.near_side(1)]
        # Dev's hand in Marta's rig px (both at depth 1 by now)
        tx = _rig_x(_world_x(hand[0], dev.size), marta.size)
        ty = R.GROUND + (hand[1] - R.GROUND) * dev.size / marta.size
        holding = dev.t_help - 0.1 <= t <= dev.t_help + 1.8
        bend = 26.0 * R.ease((t - (dev.t_help - 0.6)) / 0.5) * (1 - R.ease((t - (dev.t_help + 1.2)) / 0.6))
        p = _idle(feet, x, b, -1, None, lambda t: 2.0 + bend)(t)
        p.arms = {near: ("ik", tx, ty) if holding else ("fk", 8.0, 14.0), far: ("fk", -8.0 + 0.5 * bend, 30.0)}
        return p
    return fn


# --- the sled ------------------------------------------------------------------------------------------------------------
SLED_LEN = 0.50           # body heights (Dev's)
SLED_ACC, SLED_VMAX = 190.0, 1000.0


def sled_at(t: float, actors: dict) -> tuple[float, float, float]:
    """(world x, depth, tilt degrees). Dragged behind Dev on its rope until he lets go, then it slides: along the
    ground past the two of them, then away into the depth."""
    dev = actors["dev"]
    if t < T_SLIDE:
        tt = min(t, T_SLIDE)
        hx = _world_x(dev.raw(max(0.0, tt - 0.25)).hip[0], dev.size)
        return hx - 250.0, 0.97, 2.0 * math.sin(2 * math.pi * t * 1.7) if t < T_STOP else 0.0
    hx = _world_x(dev.raw(T_SLIDE - 0.25).hip[0], dev.size)
    tau = t - T_SLIDE
    t_max = SLED_VMAX / SLED_ACC
    s = 0.5 * SLED_ACC * min(tau, t_max) ** 2 + SLED_VMAX * max(0.0, tau - t_max)
    lane = 1150.0
    d = 0.97 if s < lane else 0.97 + (s - lane) / 380.0
    x = hx - 250.0 + min(s, lane) + max(0.0, s - lane) * 0.35
    return x, d, -4.0 + 2.0 * math.sin(tau * 9.0) * math.exp(-tau * 0.4)


# --- the layers ----------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=8)
def _img(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _place(frame: Image.Image, img: Image.Image, x: float, y: float, k: float, rot: float = 0.0, flip: bool = False):
    """Paste ``img`` scaled by ``k`` with its top-left at (x, y) (clipped to the frame)."""
    w, h = max(1, int(round(img.width * k))), max(1, int(round(img.height * k)))
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    vx0, vy0, vx1, vy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if vx1 <= vx0 or vy1 <= vy0:
        return
    # crop the source to the visible part first (a zoomed layer is large)
    sx0, sy0 = (vx0 - x0) / k, (vy0 - y0) / k
    sx1, sy1 = (vx1 - x0) / k, (vy1 - y0) / k
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    box = (max(0.0, sx0), max(0.0, sy0), min(float(img.width), sx1), min(float(img.height), sy1))
    part = img.resize((vx1 - vx0, vy1 - vy0), Image.BICUBIC, box=box)
    if rot:
        part = part.rotate(rot, resample=Image.BICUBIC, expand=False)
    frame.alpha_composite(part, (vx0, vy0))


def draw_world(frame: Image.Image, assets: Path, cam, t: float):
    cx, cy, z = cam
    far = _img(str(assets / "world" / "far.png"))
    # the far layer: a fifth of the camera's pan, a fifth of its zoom; its glaciers' foot sits on the horizon
    zf = 0.9 * (1 + (z - 1) * 0.2)
    horizon = (HORIZON_WORLD - cy) * z + H / 2
    fx = min(0.0, max(W - far.width * zf, W / 2 - (cx * 0.2) * zf - far.width * zf / 2))
    fy = horizon + 40 - 900 * zf
    frame.paste((214, 230, 244), (0, 0, W, H))
    _place(frame, far, fx, fy, zf)
    mid = _img(str(assets / "world" / "mid.png"))
    k = MID_SCALE * z
    _place(frame, mid, (0 - MID_COL * MID_SCALE - cx) * z + W / 2, (STAND_WORLD - MID_ROW * MID_SCALE - cy) * z + H / 2, k)


NEAR_ROCKS = (-420.0, 820.0, 2050.0)   # world x of the foreground rocks (they pass 1.35x faster than the ground)


@lru_cache(maxsize=2)
def _near_parts(path: str):
    """The near picture is a frame of rocks round an empty middle: its bottom-middle rock is the passing foreground
    rock; the whole frame is the opening's vignette."""
    near = _img(path)
    w, h = near.size
    rock = near.crop((int(0.235 * w), int(0.72 * h), int(0.455 * w), h))
    a = np.asarray(rock).copy()
    ramp = np.clip(np.minimum(np.arange(a.shape[1]), a.shape[1] - 1 - np.arange(a.shape[1])) / (0.12 * a.shape[1]), 0, 1)
    a[:, :, 3] = (a[:, :, 3] * ramp[None, :]).astype(np.uint8)   # no straight cut edges at the sides
    rock = Image.fromarray(a)
    return near, rock.crop(rock.getbbox())


def draw_near(frame: Image.Image, assets: Path, cam, t: float):
    cx, cy, z = cam
    near, rock = _near_parts(str(assets / "world" / "near.png"))
    if t < 5.5:  # the wide opening is framed by the rocks, which slide out as the camera moves in
        u = R.ease((t - 3.5) / 2.0)
        k = W / near.width * (1 + 0.5 * u)
        _place(frame, near, W / 2 - near.width * k / 2, H / 2 - near.height * k / 2, k)
    k = 0.75 * z
    for wx in NEAR_ROCKS:
        x = (wx - cx) * 1.35 * z + W / 2 - rock.width * k / 2
        _place(frame, rock, x, H - rock.height * k * 0.78, k)


# --- particles: snowfall and the snow puff of the fall ----------------------------------------------------------------------
@lru_cache(maxsize=1)
def _flakes():
    rng = np.random.default_rng(23)
    return rng.uniform(0, 1, (140, 5))


def draw_snow(frame: Image.Image, t: float, cam):
    d = ImageDraw.Draw(frame, "RGBA")
    for x0, y0, sp, ph, sz in _flakes():
        y = (y0 * (H + 40) + (40 + 50 * sp) * t) % (H + 40) - 20
        x = (x0 * W + 20 * math.sin(2 * math.pi * (0.2 * t + ph)) - cam[0] * 0.3 * (0.5 + sz)) % W
        r = 1.6 + 2.6 * sz
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 170))


def draw_puff(frame: Image.Image, t: float, t0: float, sx: float, sy: float, k: float):
    """A burst of snow where the body hits the ground: discs flying out and fading in 0.9 s."""
    u = (t - t0) / 0.9
    if not 0 <= u <= 1:
        return
    rng = np.random.default_rng(5)
    d = ImageDraw.Draw(frame, "RGBA")
    for _ in range(40):
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        v = rng.uniform(120, 380) * k
        r = rng.uniform(3, 9) * k * (1 + 0.6 * u)
        x = sx + math.cos(a) * v * u
        y = sy + math.sin(a) * v * u + 260 * k * u * u
        d.ellipse([x - r, y - r, x + r, y + r], fill=(246, 250, 255, int(230 * (1 - u))),
                  outline=(70, 90, 130, int(200 * (1 - u))), width=max(1, int(2.5 * k)))


def draw_shadow(frame: Image.Image, sx: float, sy: float, w: float, h: float, alpha: int):
    if alpha <= 0:
        return
    sh = Image.new("RGBA", (int(w * 2.4) + 4, int(h * 4) + 4), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([w * 0.2, h, w * 2.2, h * 3], fill=(70, 90, 140, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(h * 0.6))
    frame.alpha_composite(sh, (int(sx - w * 1.2), int(sy - h * 2)), ) if 0 <= sx - w * 1.2 < W else None


# --- one frame -----------------------------------------------------------------------------------------------------------
def actor_on_screen(actor: Actor, t: float, cam):
    """(layer, x, y, pose, skeleton, k): the actor drawn by the rig, scaled for its depth, and where it goes."""
    p = actor.pose(t)
    d = actor.depth(t)
    with R.use_build(actor.build):
        j = R.skeleton(p)
        layer, (x0, y0) = R.draw_character(p, actor.folder)
    sx, sy, k = to_screen(_world_x(x0, actor.size), STAND_WORLD + (y0 - R.GROUND) * S0 * actor.size, d, cam)
    return layer, sx, sy, p, j, k * S0 * actor.size


def joint_screen(actor: Actor, q: tuple, t: float, cam) -> tuple[float, float]:
    sx, sy, _ = to_screen(_world_x(q[0], actor.size), STAND_WORLD + (q[1] - R.GROUND) * S0 * actor.size, actor.depth(t), cam)
    return sx, sy


def render_frame(t: float, assets: str, captions: bool = True) -> Image.Image:
    a = Path(assets)
    actors = cast(assets)
    cam = camera(t)
    frame = Image.new("RGBA", (W, H))
    draw_world(frame, a, cam, t)
    sled_x, sled_d, tilt = sled_at(t, actors)
    sled = _img(str(a / "world" / "sled_side.png"))
    ssx, ssy, sk = to_screen(sled_x, STAND_WORLD, sled_d, cam)
    sscale = SLED_LEN * R.B * S0 * sk / sled.width
    items = []
    for name in ("marta", "dev"):
        act = actors[name]
        items.append((act.depth(t), name))
    items.append((sled_d, "sled"))
    drawn = {}
    for d, name in sorted(items, key=lambda it: -it[0]):
        if name == "sled":
            draw_shadow(frame, ssx, ssy, sled.width * sscale * 0.5, 10 * sk, 90)
            _place(frame, sled, ssx - sled.width * sscale / 2, ssy - sled.height * sscale * 0.92, sscale, rot=tilt, flip=True)
            drawn["sled_handle"] = (ssx + sled.width * sscale * 0.42, ssy - sled.height * sscale * 0.55)
            continue
        act = actors[name]
        layer, lx, ly, p, j, k = actor_on_screen(act, t, cam)
        hx, hy = joint_screen(act, p.hip, t, cam)
        gx, gy = joint_screen(act, (p.hip[0], R.GROUND), t, cam)
        lift = max(0.0, (gy - hy) / (k * R.B) - act.build.stand)
        draw_shadow(frame, gx, gy, 0.32 * R.B * k * (1.7 if p.torso > 45 else 1.0), 9 * k, int(110 * max(0.0, 1 - lift * 3)))
        _place(frame, layer, lx, ly, k)
        drawn[name] = (p, j)
    # the rope: from Dev's near hand to the sled's handle, until he lets go
    if t < T_THROW + 0.05 and "sled_handle" in drawn:
        p, j = drawn["dev"]
        hand = joint_screen(actors["dev"], j["hand_" + R.near_side(p.facing)], t, cam)
        hx2, hy2 = drawn["sled_handle"]
        sag = 30 * cam[2]
        pts = [(R.lerp(hand[0], hx2, u), R.lerp(hand[1], hy2, u) + sag * 4 * u * (1 - u)) for u in np.linspace(0, 1, 16)]
        ImageDraw.Draw(frame).line(pts, fill=(52, 36, 24, 255), width=max(2, int(5 * cam[2])), joint="curve")
    elif t < T_THROW + 0.6 and "sled_handle" in drawn:  # the dropped rope trails behind the sled
        hx2, hy2 = drawn["sled_handle"]
        ImageDraw.Draw(frame).line([(hx2, hy2), (hx2 + 60 * cam[2], hy2 + 30 * cam[2])], fill=(52, 36, 24, 255),
                                   width=max(2, int(5 * cam[2])))
    dev = actors["dev"]
    with R.use_build(dev.build):
        pi = dev.raw(dev.impact).hip
    px, py = joint_screen(dev, (pi[0] + 0.3 * R.B, R.GROUND), t, cam)
    draw_puff(frame, t, dev.impact, px, py, cam[2])
    draw_near(frame, a, cam, t)
    draw_snow(frame, t, cam)
    out = frame.convert("RGB")
    if captions:
        out = draw_caption(out, t)
    return fade(out, t)


def layer_scale(act: Actor, t: float, cam) -> float:
    """Screen px per rig px for the actor at its depth."""
    return cam[2] / act.depth(t) * S0 * act.size


def fade(img: Image.Image, t: float) -> Image.Image:
    a = min(1.0, t / 0.6, max(0.0, (DURATION - t) / 0.8))
    if a >= 1.0:
        return img
    return Image.blend(Image.new("RGB", img.size, (12, 14, 22)), img, a)


# --- captions (the lines on screen until the voice is approved) ------------------------------------------------------------
@lru_cache(maxsize=1)
def _font(size: int):
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_caption(img: Image.Image, t: float) -> Image.Image:
    for k, (t0, who, text) in enumerate(LINES):
        end = t0 + 0.6 + 0.07 * len(text)
        if k + 1 < len(LINES):
            end = min(end, LINES[k + 1][0] - 0.15)
        if t0 <= t <= end:
            d = ImageDraw.Draw(img)
            f = _font(46)
            w = d.textlength(text, font=f)
            x, y = (W - w) / 2, H - 120
            d.text((x, y), text, font=f, fill=(255, 255, 255), stroke_width=5, stroke_fill=(20, 20, 30))
    return img


# --- sound ---------------------------------------------------------------------------------------------------------------
def events(fps: int = 24, assets: str = "") -> list[dict]:
    actors = cast(assets)
    out = []
    n = int(DURATION * fps)
    for name, act in actors.items():
        prev = act.raw(0.0)
        for i in range(1, n):
            t = i / fps
            p = act.raw(t)
            for s in R.SIDES:
                if R._grounded(p.feet[s]) and not R._grounded(prev.feet[s]):
                    out.append({"t": round(t, 4), "kind": "step", "who": name, "loud": 1.3 if T_RUN < t < actors["dev"].trip else 0.8})
            prev = p
    dev = actors["dev"]
    out += [{"t": T_THROW + 0.1, "kind": "rope", "who": "dev", "loud": 1.0},
            {"t": dev.trip, "kind": "trip", "who": "dev", "loud": 1.0},
            {"t": dev.impact, "kind": "impact", "who": "dev", "loud": 1.0}]
    return sorted(out, key=lambda e: e["t"])


def _noise(rng, n, lo, hi, sr):
    x = rng.normal(0, 1, n)
    spec = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    spec[(fr < lo) | (fr > hi)] = 0
    y = np.fft.irfft(spec, n)
    return y / (np.abs(y).max() + 1e-9)


def make_audio(path: Path, assets: str, voice: Path | None = None, fps: int = 24, sr: int = 48000):
    actors = cast(assets)
    n = int(DURATION * sr)
    rng = np.random.default_rng(3)
    out = np.zeros((n, 2))
    tt = np.arange(n) / sr
    wind = _noise(rng, n, 60, 700, sr) * (0.10 + 0.05 * np.sin(2 * np.pi * 0.06 * tt))
    out[:, 0] += wind
    out[:, 1] += np.roll(wind, 700)
    # the sled's hiss on the snow: louder with speed, quieter with depth
    hiss = _noise(rng, n, 1500, 9000, sr)
    env = np.zeros(n)
    for i in range(0, n, sr // 50):
        t = i / sr
        if t >= T_SLIDE:
            x0, d0, _ = sled_at(t, actors)
            x1, d1, _ = sled_at(t + 0.02, actors)
            v = math.hypot(x1 - x0, (d1 - d0) * 400) / 0.02
            env[i:i + sr // 50] = min(1.0, v / 600.0) / max(1.0, d0) ** 1.2
        elif T_STOP > t > 0.3:
            env[i:i + sr // 50] = 0.35
    out[:, 0] += hiss * env * 0.16
    out[:, 1] += hiss * env * 0.16
    for e in events(fps, assets):
        i0 = int(e["t"] * sr)
        if e["kind"] == "step":
            m = int(0.12 * sr)
            s = _noise(rng, m, 900, 6000, sr) * np.exp(-np.arange(m) / (0.03 * sr)) * 0.30 * e["loud"]
        elif e["kind"] == "rope":
            m = int(0.25 * sr)
            s = _noise(rng, m, 200, 1500, sr) * np.exp(-np.arange(m) / (0.04 * sr)) * 0.25
        elif e["kind"] == "trip":
            m = int(0.4 * sr)
            s = _noise(rng, m, 300, 3000, sr) * np.sin(np.pi * np.arange(m) / m) * 0.25
        else:
            m = int(0.6 * sr)
            t2 = np.arange(m) / sr
            s = np.sin(2 * np.pi * (65 - 25 * t2) * t2) * np.exp(-t2 / 0.13) * 0.9
            s += _noise(rng, m, 500, 7000, sr) * np.exp(-t2 / 0.08) * 0.5
        m = min(len(s), n - i0)
        if m > 0:
            out[i0:i0 + m, 0] += s[:m]
            out[i0:i0 + m, 1] += s[:m]
    if voice:
        for k, (t0, who, text) in enumerate(LINES):
            f = voice / f"line_{k + 1}.wav"
            if f.exists():
                with wave.open(str(f)) as wf:
                    v = np.frombuffer(wf.readframes(wf.getnframes()), "<i2").astype(float) / 32768.0
                    if wf.getnchannels() == 2:
                        v = v.reshape(-1, 2).mean(axis=1)
                i0 = int(t0 * sr)
                m = min(len(v), n - i0)
                out[i0:i0 + m, 0] += v[:m] * 1.4
                out[i0:i0 + m, 1] += v[:m] * 1.4
    out = out / (np.abs(out).max() + 1e-9) * 0.9   # peak only: the render levels to -14 LUFS with a limiter
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((out * 32767).astype("<i2").tobytes())


# --- checks --------------------------------------------------------------------------------------------------------------
def check(assets: str, fps: int = 24) -> dict:
    """The rig's motion checks per hero (BR-1 planted feet hold, BR-3 a planted foot is reached, BR-4 bones keep their
    length, BR-5 no joint jumps, BR-7 every footfall sounds) plus the shot's: the heroes stay in frame while they act
    (IS-1) and the sled never runs through a hero's feet while on the same depth (IS-2)."""
    actors = cast(assets)
    n = int(DURATION * fps)
    findings = []
    steps = {(e["who"], round(e["t"], 4)) for e in events(fps, assets) if e["kind"] == "step"}
    for name, act in actors.items():
        prev_p = prev_j = None
        for i in range(n):
            t = i / fps
            p = act.pose(t)
            with R.use_build(act.build):
                j = R.skeleton(p)
                for s in R.SIDES:
                    ax, ay = j["ankle_" + s]
                    want = p.feet[s][1] - (R.TQ_BACK if p.view == "three_quarter" and s != R.near_side(p.facing) else 0.0)
                    if p.feet[s][3] and math.hypot(ax - p.feet[s][0], ay - want) > 2.0:
                        findings.append({"rule": "BR-3", "who": name, "t": t, "what": f"planted foot {s} not reached"})
                    for a_, b_, ln in (("hip_" + s, "knee_" + s, R.THIGH), ("knee_" + s, "ankle_" + s, R.SHIN)):
                        if abs(math.dist(j[a_], j[b_]) - ln) > 0.5:
                            findings.append({"rule": "BR-4", "who": name, "t": t, "what": f"{a_}-{b_} length changed"})
                    if prev_p and p.feet[s][3] and prev_p.feet[s][3] and p.facing == prev_p.facing:
                        if math.dist(p.feet[s][:2], prev_p.feet[s][:2]) > 1.0:
                            findings.append({"rule": "BR-1", "who": name, "t": t, "what": f"planted foot {s} slid"})
            if prev_j and p.view == prev_p.view and p.facing == prev_p.facing:
                for key, v in j.items():
                    if isinstance(v, tuple) and key in prev_j and math.dist(v, prev_j[key]) > 0.22 * R.B:
                        findings.append({"rule": "BR-5", "who": name, "t": t, "what": f"{key} jumped"})
            if t > 1.2:
                cam = camera(t)
                hx, hy = joint_screen(act, p.hip, t, cam)
                if not (0 < hx < W and 0 < hy < H):
                    findings.append({"rule": "IS-1", "who": name, "t": t, "what": "the hero's hips leave the frame"})
            if prev_p:
                landed = [s for s in R.SIDES if R._grounded(p.feet[s]) and not R._grounded(prev_p.feet[s])]
                if landed and (name, round(t, 4)) not in steps:
                    findings.append({"rule": "BR-7", "who": name, "t": t, "what": "a footfall without its sound"})
            prev_p, prev_j = p, j
    return {"verdict": "PASS" if not findings else "FAIL", "frames": n, "fps": fps, "count": len(findings),
            "findings": findings[:200]}


def render(assets: str, out: Path, fps: int = 24, voice: Path | None = None, crf: int = 18) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    n = int(DURATION * fps)
    silent = out / "ice_short_silent.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-frames:v", str(n), "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    stills = {}
    marks = np.linspace(0.5, DURATION - 0.5, 24)
    for i in range(n):
        t = i / fps
        img = render_frame(t, assets, captions=voice is None)
        proc.stdin.write(img.tobytes())
        for m in marks:
            if abs(m - t) < 0.5 / fps:
                stills[m] = img.resize((480, 270), Image.LANCZOS)
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed")
    wav = out / "ice_short.wav"
    make_audio(wav, assets, voice, fps)
    final = out / "ice_short.mp4"
    gain = -14.0 - R.loudness(wav)
    for _ in range(5):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-af",
                        f"volume={gain:.2f}dB,alimiter=limit=0.7:level=false", "-ar", "48000", "-ac", "2", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", str(final)], check=True)
        miss = -14.0 - R.loudness(final)
        if abs(miss) < 0.5:
            break
        gain += miss
    sheet = Image.new("RGB", (480 * 6, 270 * 4), (20, 20, 20))
    for k, m in enumerate(sorted(stills)):
        sheet.paste(stills[m], ((k % 6) * 480, (k // 6) * 270))
    sheet.save(out / "ice_short_frames.jpg", quality=88)
    report = check(assets, fps)
    report["loudness_lufs"] = round(R.loudness(final), 1)
    (out / "ice_short_check.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    silent.unlink(missing_ok=True)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.ice_short")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--assets", required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--fps", type=int, default=24)
    r.add_argument("--voice", type=Path, default=None)
    c = sub.add_parser("check")
    c.add_argument("--assets", required=True)
    a = ap.parse_args(argv)
    rep = render(a.assets, a.out, a.fps, a.voice) if a.cmd == "render" else check(a.assets)
    print(json.dumps({k: v for k, v in rep.items() if k != "findings"} | {"first": rep["findings"][:8]}, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
