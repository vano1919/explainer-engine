"""The hybrid model's thirty-second test cartoon (the creator, 2026-10-22 19:35 and 19:38): an Ice Age valley painted in
layers by the image model, two heroes painted as turnarounds and expression sheets and moved by the bending rig
(``bend_rig``), a 2.5D camera, a sled that slides away down the slope. Everything after the pictures is code and free.

Second version (the creator, 2026-10-22 20:32: "the physics and the montage are completely off from reality"): the motion
is simulated, not eased. The scene lies along a *lane* with a terrain profile (``physics2d``): the sled is a body with
mass and friction on a rope, held back by Dev's heel until his indignant stamp lifts it; the fall is a ragdoll with
muscle tone that fades; heads and torsos lag the hips with damped springs; every planted foot is a fixed world point
(so a foot never slides on screen, whatever the depth); turns pass through an edge-on in-between; expressions cross
over three frames; the camera is an operator who follows subjects with lead room and never stops dead; the story is cut
into shots (a reaction shot on each line, cuts on the actions).

The story (English for the viewer): two of the hundred people dropped into the Ice Age. Dev walks down the slope
dragging the sled he made from a suitcase; when he stops it runs into his heel and stays there, resting on it. He
presents it to Marta; she is not impressed; he throws up his arms and stamps, the heel lifts, the sled slides away down
the slope past him; he chases it, trips and tumbles; Marta walks over and helps him up; they watch it vanish. "Great
plan."

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
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from explainer_engine.production import bend_rig as R
from explainer_engine.production import physics2d as P

W, H = 1920, 1080
DURATION = 30.0
RATE = 240                # the simulations' and tables' rate, Hz
S0 = 0.77                 # world px per rig px for a full-size hero at depth 1
STAND_WORLD = 731.5       # the world y of the depth-1 ground at elevation 0
HORIZON_WORLD = 376.0     # the world y of the far snow ridge (where depth runs out)
D1 = 2000.0               # ground px of distance per unit of depth (the camera stands D1 behind the depth-1 line)
MID_SCALE = 1.316         # world px per px of the middle layer's picture
MID_ROW, MID_COL = 1100, 1100   # the picture's pixel that sits at (world 0, STAND_WORLD)
SIZES = {"dev": 1.0, "marta": 0.86}

# --- the ground: a lane down the valley with its elevation profile ----------------------------------------------------------
# the lip of the slope is at s = 1735: Dev stops just below it with the sled's weight already over the edge, held by his
# heel; the lane bends away from the camera after the fall
TERRAIN = P.Terrain([(1620.0, 0.0), (2800.0, 10.0), (3400.0, 14.0), (5500.0, 5.0), (8000.0, 2.0), (12000.0, 0.0)])
LANE = P.Lane(x0=-1500.0, s_turn=2800.0, heading_deg=75.0, turn_len=900.0)
MARTA_SPOT = (900.0, 600.0)   # world x and distance away: she waits up the hillside, off the sled's lane


def depth_of(away: float) -> float:
    return 1.0 + away / D1


def lane_point(s: float) -> tuple[float, float, float]:
    """(world x, away, elevation) of the lane at ``s``."""
    x, away = LANE.at(s)
    return x, away, TERRAIN.h(s)


def ground_h(x: float, away: float) -> float:
    """The elevation of a point off the lane: the hillside descends toward the camera as well as to the right, so a
    point further away stands as high as the lane does 0.8 of that distance uphill."""
    return TERRAIN.h(LANE.s_of_x(x) - 0.8 * away)


def to_screen(wx: float, wy_at_depth1: float, d: float, cam) -> tuple[float, float, float]:
    """A point of depth ``d`` (its height above the ground given at depth-1 scale) -> (screen x, screen y, scale)."""
    cx, cy, z = cam
    ground1 = (STAND_WORLD - cy) * z + H / 2
    horizon = (HORIZON_WORLD - cy) * z + H / 2
    gd = horizon + (ground1 - horizon) / d
    k = z / d
    return (wx - cx) * k + W / 2, gd + (wy_at_depth1 - STAND_WORLD) * k, k


def world_screen(x: float, away: float, h: float, lift: float, cam) -> tuple[float, float, float]:
    """A ground point (x, away) at elevation ``h`` plus ``lift`` world px above it -> screen."""
    return to_screen(x, STAND_WORLD - h - lift, depth_of(away), cam)


def frame_for(point: tuple, z: float, sx: float, sy: float) -> tuple[float, float, float]:
    """The camera (cx, cy, z) that puts the world point (x, away, world y) at screen (sx, sy)."""
    x, away, wy = point
    d = depth_of(away)
    cx = x - (sx - W / 2) * d / z
    cy = HORIZON_WORLD + (H / 2 + (STAND_WORLD - HORIZON_WORLD) * z / d + (wy - STAND_WORLD) * z / d - sy) / z
    return cx, cy, z


# --- the actors -----------------------------------------------------------------------------------------------------------
@dataclass
class Actor:
    name: str
    folder: str
    build: R.Build
    size: float
    path: object              # callable s (world px along the actor's own path) -> (world x, away, elevation)
    segments: list            # (t0, t1, kind, obj): "loco" Loco | "keys" (keys, facing) | "fn" callable t -> Pose
    look: list                # (t, expr) timeline; a change crosses over CROSS seconds
    views: list               # (t, view, facing) timeline: the drawing and the side it faces; a change is a turn
    blinks: tuple = ()
    secondary: np.ndarray | None = None   # 240 Hz rows: head nod, torso lag (follow-through of the hips' motion)
    mouth: list = field(default_factory=list)   # (t, expr) lip flaps from the voice, on top of ``look``

    @property
    def sc(self) -> float:
        return S0 * self.size

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
        prev = None
        for te, e in self.look:
            if t >= te:
                p.expr, p.expr_from = e, prev
                p.expr_mix = min(1.0, (t - te) / CROSS)
            prev = e
        for tm, e in self.mouth:
            if t >= tm:
                if e:
                    p.expr, p.expr_from, p.expr_mix = e, None, 1.0
        for tv, v, f in self.views:
            if t >= tv:
                p.view = v
                if f:
                    p.facing = f
        p.blink = max([max(0.0, 1 - abs(t - b) / 0.07) for b in self.blinks] + [0.0])
        if self.secondary is not None:
            i = min(self.secondary.shape[1] - 1, max(0, int(round(t * RATE))))
            p.head += float(self.secondary[0, i])
            p.torso += float(self.secondary[1, i])
        return p

    def turn(self, t: float) -> float:
        """Width of the drawing, 1 = full: a change of view or facing passes through an edge-on in-between."""
        w = 1.0
        for tv, v, f in self.views[1:]:
            w = min(w, 1.0 - 0.65 * max(0.0, 1 - abs(t - tv) / TURN))
        return w

    def hip_world(self, t: float) -> tuple[float, float, float, float]:
        """(x, away, elevation, lift) of the hips."""
        p = self.raw(t)
        x, away, h = self.path(p.hip[0] * self.sc)
        return x, away, h, (R.GROUND - p.hip[1]) * self.sc


CROSS = 3 / 24.0          # an expression crosses over three frames
TURN = 2.5 / 24.0         # the edge-on in-between of a turn lasts about five frames in all


@dataclass
class Placed:
    pose: R.Pose              # in the hips' frame: rig px, every foot where the terrain and the depth put it
    anchor: tuple             # the raw hips (rig px): the frame's origin
    screen: tuple             # where the anchor is on screen
    k: float                  # screen px per rig px at the hips' depth


def place(actor: Actor, p: R.Pose, cam) -> Placed:
    """The pose on screen: the body is drawn at its hips' depth and elevation, and each foot is moved to where its own
    ground point projects, so a planted foot stays put on screen while the hips move in depth (a walk toward the camera,
    a run down a slope). The hips come down if a foot would be out of reach (walking downhill)."""
    sc = actor.sc
    x_h, a_h, h_h = actor.path(p.hip[0] * sc)
    hx, hy, k = world_screen(x_h, a_h, h_h, (R.GROUND - p.hip[1]) * sc, cam)
    K = k * sc
    p2 = replace(p, feet=dict(p.feet), arms=dict(p.arms))
    for s in R.SIDES:
        fx, fy, pitch, c = p.feet[s]
        x_f, a_f, h_f = actor.path(fx * sc)
        sx, sy, _ = world_screen(x_f, a_f, h_f, (R.GROUND - fy) * sc, cam)
        p2.feet[s] = (p.hip[0] + (sx - hx) / K, p.hip[1] + (sy - hy) / K, pitch, c)
    with R.use_build(actor.build):
        p2.hip = R.reach_clamp(p.hip, p2.feet)
        if p.view == "three_quarter" and not p.front:
            # the three-quarter drawing solves each leg from a hip shifted sideways: clamp from there too
            y = p2.hip[1]
            for s in R.SIDES:
                fx, fy, _, _ = p2.feet[s]
                hx_s = p.hip[0] + (-p.facing if s == R.near_side(p.facing) else p.facing) * R.TQ_HIP
                if R._grounded(p2.feet[s]):
                    y = max(y, fy - math.sqrt(max(0.0, R.REACH ** 2 - (fx - hx_s) ** 2)))
            p2.hip = (p2.hip[0], y)
    return Placed(p2, p.hip, (hx, hy), K)


def _ab(x, y, p=0.0, c=False):
    return ("abs", x, y, p, c)


def _stand_feet(x: float, f: int, gap: float = 0.07) -> dict:
    return {R.near_side(f): (x - f * gap * R.B, R.ANK, 0.0, True), R.SIDES[1 - R.SIDES.index(R.near_side(f))]:
            (x + f * gap * R.B, R.ANK, 0.0, True)}


def _idle(feet: dict, x: float, b: R.Build, f: int, arms_fn=None, torso_fn=None, head_fn=None, hip_fn=None):
    """A standing pose that breathes; ``arms_fn``/``torso_fn``/``head_fn`` (t -> value) add the acting."""
    def fn(t):
        breath = 0.006 * R.B * math.sin(2 * math.pi * t / 2.4)
        p = R.Pose(f, (x, R.GROUND - b.stand * R.B + breath), torso_fn(t) if torso_fn else 2.0,
                   head_fn(t) if head_fn else 0.0, feet=dict(feet))
        if hip_fn:
            dx, dy = hip_fn(t)
            p.hip = (p.hip[0] + dx, p.hip[1] + dy)
        p.hip = R.reach_clamp(p.hip, p.feet)
        p.arms = arms_fn(t) if arms_fn else {s: ("fk", 4.0, 12.0) for s in R.SIDES}
        return p
    return fn


# the times of the story
T_STOP = 5.0          # Dev arrives
T_LINE1 = 6.8         # "Behold! The first sled of the Ice Age." (the take is 3.4 s)
T_LINE2 = 10.4        # Marta: "It's a suitcase."
T_THROW = 11.6        # Dev throws up his arms: the rope leaves his hand, the heel lifts in a stamp
T_RUN = 13.2          # Dev runs after the sled
T_LINE3 = 26.4        # Marta: "Great plan."
LINES = [(T_LINE1, "dev", "Behold! The first sled of the Ice Age."), (T_LINE2, "marta", "It's a suitcase."),
         (T_LINE3, "marta", "Great plan.")]
SLED_LEN = 0.50           # body heights (Dev's)
SLED_H = 0.14


def _straight_path(p0: tuple, p1: tuple):
    """A path across the ground from (x, away) to (x, away): s -> (x, away, elevation), elevation from the lane's
    profile at either end."""
    h0, h1 = ground_h(*p0), ground_h(*p1)
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1.0

    def path(s):
        u = min(1.0, max(0.0, s / length))
        return R.lerp(p0[0], p1[0], u), R.lerp(p0[1], p1[1], u), R.lerp(h0, h1, u)
    path.length = length
    return path


def _polyline_path(points: list):
    """A path through ground points (x, away): s -> (x, away, elevation), elevation from the lane's profile."""
    legs = [_straight_path(p, q) for p, q in zip(points, points[1:])]
    starts = np.concatenate([[0.0], np.cumsum([lg.length for lg in legs])])

    def path(s):
        s = min(max(s, 0.0), starts[-1])
        i = int(np.searchsorted(starts, s, side="right") - 1)
        i = min(i, len(legs) - 1)
        return legs[i](s - starts[i])
    path.length = float(starts[-1])
    return path


@lru_cache(maxsize=2)
def cast(assets: str) -> dict:
    a = Path(assets)
    dev_b, marta_b = R.load_build(str(a / "dev")), R.load_build(str(a / "marta"))
    B = R.B
    sc_d = S0 * SIZES["dev"]
    world = {}      # the simulations' results, read by the acting closures
    # --- Dev: walks in dragging the sled, presents, throws up his arms, chases, trips, is helped up -------------------
    with R.use_build(dev_b):
        walk_g = dev_b.gait(R.measured("walk"))      # CMU 07_01, retargeted (mocap.py)
        v_walk = 0.62 * B * (dev_b.thigh + dev_b.shin) / 0.42

        def walk_speed(t, _ph):
            return v_walk if t < T_STOP - 0.35 else v_walk * max(0.0, 1 - (t - (T_STOP - 0.35)) / 0.35)

        walk_loco = R.Loco(walk_g, 1, 0.0, T_STOP, walk_speed, 1040.0 / sc_d)

        def walk(t):
            # the near arm holds the rope behind him, steady (a swinging arm would jerk the sled along)
            p = walk_loco.pose(t)
            p.arms[near] = ("fk", -42.0, 10.0)
            return p

        stand_feet = walk_loco.feet(T_STOP + walk_loco.settle + 0.01)
        xs = walk_loco.x(T_STOP)
        near, far = R.near_side(1), R.SIDES[1 - R.SIDES.index(R.near_side(1))]
        trail = min(stand_feet, key=lambda s: stand_feet[s][0])     # the uphill foot: the sled rests on its heel
        lead_ft = R.SIDES[1 - R.SIDES.index(trail)]

        def shove(t):
            """The sled runs into his heel when he stops: a lurch forward and a flail, then he gathers himself."""
            tb = world.get("bump", 99.0)
            u = (t - tb) / 0.5
            if not 0 <= u <= 1:
                return 0.0
            return math.sin(math.pi * min(1.0, u * 1.6)) * (1 - 0.5 * u)

        def present_arms(t):
            # the presenting sweep toward the sled behind him, then the indignant throw, then the anticipation
            sh = shove(t)
            if t < T_LINE1 - 0.3:
                u = R.ease((t - (T_STOP + 0.4)) / 0.8)
                # the near arm keeps holding the rope behind him (from the walk's -42) and sweeps a little further back
                return {near: ("fk", R.lerp(-42, -55, u) + 30 * sh, R.lerp(10, 8, u)),
                        far: ("fk", R.lerp(4, 70, u) + 40 * sh, R.lerp(12, 30, u))}
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
                return 2.0 - 4.0 * R.ease((t - T_STOP) / 0.6) + 14.0 * shove(t)   # chest out; the shove lurches him
            if t < T_RUN - 0.45:
                return -6.0 + 10.0 * R.ease((t - (T_THROW + 0.6)) / 0.4)          # he leans to look at the sled going
            return R.lerp(4.0, 22.0, R.ease((t - (T_RUN - 0.45)) / 0.4))          # the crouch before the run

        def present_head(t):
            if T_LINE1 < t < T_LINE1 + 2.4:
                return -10.0
            if T_THROW + 0.5 < t < T_RUN - 0.2:
                return 16.0 * R.ease((t - (T_THROW + 0.5)) / 0.3)                 # looking down at the sled going
            return 0.0

        def stamp_feet(t):
            """The trailing foot lifts in the stamp (T_THROW + 0.2 .. + 0.7): the sled it was holding slips away under it."""
            feet = dict(stand_feet)
            u = (t - (T_THROW + 0.2)) / 0.5
            if 0 <= u <= 1:
                x0, y0, _, _ = stand_feet[trail]
                feet[trail] = (x0, y0 - 0.14 * B * math.sin(math.pi * u), -25.0 * math.sin(math.pi * u), False)
            return feet

        def present(t):
            p = _idle(stamp_feet(t), xs, dev_b, 1, present_arms, present_torso, present_head,
                      lambda t: (0.0, 0.0))(t)
            u = (t - (T_THROW + 0.2)) / 0.5
            if 0 <= u <= 1:   # the stamp's hop: the hips rise on the planted leg
                p.hip = (p.hip[0], p.hip[1] - 0.03 * B * math.sin(math.pi * u))
            return p

        run_g = dev_b.gait(R.measured("run"))         # CMU 09_01
        ph = R.entry_phase(run_g, 1, xs, stamp_feet(T_RUN))
        v_run = 1.05 * B * (dev_b.thigh + dev_b.shin) / 0.42
        run = R.Loco(run_g, 1, T_RUN, T_RUN + 4.0, lambda t, _ph: v_run * R.ease((t - T_RUN) / 0.5), xs, phase0=ph,
                     entry=stamp_feet(T_RUN), entry_arms=(-35.0, 40.0))
        # the trip: the first foot to leave the ground after 2.4 s of running
        tj = None
        for k in range(int((T_RUN + 2.4) * RATE), int((T_RUN + 4.0) * RATE)):
            t = k / RATE
            fa, fb = run.feet(t), run.feet(t + 1 / RATE)
            for s in R.SIDES:
                if fa[s][3] and not fb[s][3]:
                    tj = t
                    break
            if tj:
                break
        run.t1 = tj
        pre = run.pose(tj)
        skel = R.skeleton(pre)
    dev = Actor("dev", str(a / "dev"), dev_b, SIZES["dev"], lane_point, [], look=[], views=[],
                blinks=(1.8, 4.2, 6.6, 9.4, 13.9, 21.0, 25.2, 28.4))

    # --- the sled: dragged on the rope, stopped by the heel, freed by the stamp --------------------------------------------
    def hand(t):
        with R.use_build(dev_b):
            p = walk(t) if t < T_STOP + 0.4 else present(t)
            j = R.skeleton(p)
        hd = j["hand_" + near]
        s = hd[0] * sc_d
        return (s, TERRAIN.h(p.hip[0] * sc_d) + (R.GROUND - hd[1]) * sc_d)

    heel_r = 0.045 * B * sc_d

    def foot(t, sled_front):
        if t < T_STOP - 0.3:
            return None
        with R.use_build(dev_b):
            p = walk(t) if t < T_STOP + 0.4 else present(t)
        fx, fy, _, contact = p.feet[trail]
        if not contact:
            return None
        s = (fx - 0.045 * B) * sc_d
        if sled_front > s + 2.0:    # once past the heel the sled slides on beside the leg
            return None
        return (s, TERRAIN.h(s) + heel_r, heel_r)

    sled_len, sled_h = SLED_LEN * B * sc_d, SLED_H * B * sc_d
    s_hand0 = hand(0.0)[0]
    sim = P.SledSim(TERRAIN, sled_len, sled_h, mass=10.0, friction=0.05, rope=0.55 * B * sc_d,
                    s0=s_hand0 - 0.55 * B * sc_d * 0.92 - sled_len / 2 + 8)
    sim.joint.anchor_b = (sled_len / 2 - 8, 0.0)
    sim.sled.velocity = (v_walk * sc_d, 0.0)          # it is already moving with him: no yank on the first frame
    sled_res = sim.run(0.0, DURATION, hand, release=T_THROW - 0.05, foot=foot)
    ev = {kind: t for t, kind, _ in sled_res.events}
    world["bump"] = ev.get("bump", T_STOP + 0.3)
    world["sled"] = sled_res

    # --- the fall: a ragdoll from the trip, on the slope --------------------------------------------------------------------
    def rig_to_world(q):
        s = q[0] * sc_d
        return (s, TERRAIN.h(pre.hip[0] * sc_d) + (R.GROUND - q[1]) * sc_d)

    skel_w = {k: rig_to_world(v) for k, v in skel.items() if isinstance(v, tuple)}
    slope = math.radians(TERRAIN.slope(pre.hip[0] * sc_d))
    v_w = v_run * sc_d
    rag = P.Ragdoll(skel_w, 1, TERRAIN)
    rag_res = rag.run(tj, 1.8, (v_w * math.cos(slope), -v_w * math.sin(slope)), 3.0, lambda dt: max(0.0, 1 - dt / 0.35),
                      reach_k=6e5)
    rev = {kind: t for t, kind, _ in rag_res.events}
    t_impact = rev.get("impact", tj + 0.35)
    t_rest = rev.get("rest", tj + 1.0)
    world["ragdoll"] = rag_res
    rest_j, rest_c = rag_res.at(t_rest)

    def rag_pose(t):
        j, contacts = rag_res.at(t)
        return _pose_from_joints(j, contacts, 1, sc_d, dev_b, squash=_impact_squash(t, t_impact))

    # --- the get-up with Marta's hand, from where the ragdoll came to rest --------------------------------------------------
    t_help = 22.8
    with R.use_build(dev_b):
        p_rest = _pose_from_joints(rest_j, rest_c, 1, sc_d, dev_b)
        xi = p_rest.hip[0]
        stand_y = R.GROUND - dev_b.stand * B
        fk = lambda a, e: ("fk", a, e)  # noqa: E731
        lead = max(p_rest.feet, key=lambda s: p_rest.feet[s][0])
        trail2 = R.SIDES[1 - R.SIDES.index(lead)]
        kneel_feet = {lead: _ab(xi + 0.30 * B, R.ANK, 0, True), trail2: _ab(xi - 0.14 * B, R.GROUND - 0.06 * B, 75)}
        grip0 = (xi + 0.40 * B, R.GROUND - 0.52 * B)
        grip1 = (xi + 0.42 * B, R.GROUND - 0.66 * B)
        hands_rest = {s: ("ik",) + p_rest.arms[s][1:] for s in R.SIDES}
        keys = [
            R.Key(t_rest, p_rest.hip, p_rest.torso, p_rest.head, {s: _ab(*p_rest.feet[s]) for s in R.SIDES}, hands_rest),
            R.Key(t_rest + 0.9, p_rest.hip, p_rest.torso, p_rest.head - 18, {s: _ab(*p_rest.feet[s]) for s in R.SIDES},
                  hands_rest),                                        # a dazed moment, then the head lifts
            R.Key(t_help - 0.9, (xi - 0.04 * B, R.GROUND - 0.24 * B), 52, -22,
                  {lead: _ab(xi + 0.10 * B, R.GROUND - 0.08 * B, 40), trail2: _ab(xi - 0.22 * B, R.GROUND - 0.07 * B, 70)},
                  {s: ("ik", xi + 0.22 * B + (0.04 * B if s == near else 0.0), R.GROUND - 0.03 * B) for s in R.SIDES}),
            R.Key(t_help, (xi - 0.02 * B, R.GROUND - 0.25 * B), 14, -8, kneel_feet, {near: ("ik",) + grip0, far: fk(25, 30)}),
            R.Key(t_help + 0.5, (xi - 0.02 * B, R.GROUND - 0.25 * B), 12, -8, kneel_feet,
                  {near: ("ik",) + grip0, far: fk(25, 30)}),
            R.Key(t_help + 1.2, (xi + 0.06 * B, stand_y), 6, 6,
                  {lead: _ab(xi + 0.30 * B, R.ANK, 0, True), trail2: _ab(xi + 0.02 * B, R.ANK, 0, True)},
                  {near: ("ik",) + grip1, far: fk(10, 15)}),
            R.Key(t_help + 1.7, (xi + 0.06 * B, stand_y), 4, 4,
                  {lead: _ab(xi + 0.30 * B, R.ANK, 0, True), trail2: _ab(xi + 0.02 * B, R.ANK, 0, True)},
                  {near: ("ik",) + grip1, far: fk(10, 15)}),
            R.Key(t_help + 2.1, (xi + 0.06 * B, stand_y), 2, 6,
                  {lead: _ab(xi + 0.30 * B, R.ANK, 0, True), trail2: _ab(xi + 0.02 * B, R.ANK, 0, True)},
                  {s: fk(6, 14) for s in R.SIDES}),
        ]
        end_feet = {lead: (xi + 0.30 * B, R.ANK, 0.0, True), trail2: (xi + 0.02 * B, R.ANK, 0.0, True)}
        after = _idle(end_feet, xi + 0.06 * B, dev_b, 1,
                      lambda t: {near: ("fk", 8.0, 16.0), far: ("fk", -6.0 + 3 * math.sin(t * 1.3), 40.0)},
                      lambda t: 4.0, lambda t: 6.0 if t < T_LINE3 + 0.6 else 12.0)
    dev.segments = [(0.0, T_STOP + 0.4, "fn", walk), (T_STOP + 0.4, T_RUN, "fn", present), (T_RUN, tj, "loco", run),
                    (tj, t_rest, "fn", rag_pose), (t_rest, keys[-1].t, "keys", (keys, 1)), (keys[-1].t, DURATION, "fn", after)]
    dev.look = [(0.0, "neutral"), (world["bump"] + 0.05, "shock"), (world["bump"] + 0.6, "proud"), (T_LINE2 + 0.4, "sheepish"),
                (T_THROW, "shock"), (T_THROW + 0.7, "scared"), (tj + 0.1, "shock"), (t_impact + 0.1, "pain"),
                (t_help - 0.5, "neutral"), (t_help + 2.2, "sheepish")]
    dev.views = [(0.0, "side", 1), (T_STOP + 0.5, "three_quarter", 1), (T_RUN - 0.45, "side", 1), (t_help + 2.3, "three_quarter", 1)]
    dev.trip, dev.impact, dev.rest, dev.xi, dev.grips, dev.t_help = tj, t_impact, t_rest, xi, (grip0, grip1), t_help
    dev.stand_feet, dev.trail = stand_feet, trail

    # --- Marta: waits, is not impressed, turns to watch, walks over, helps him up -------------------------------------------
    sc_m = S0 * SIZES["marta"]
    with R.use_build(marta_b):
        t_turn = ev.get("release", T_THROW) + 1.4          # she turns when the sled passes
        t_walk0 = max(t_impact + 0.9, 18.2)
        # her path: from her spot to Dev's hands' side, where she can reach him
        with R.use_build(dev_b):
            hand_x_w = lane_point((rest_j["hand_" + near][0]))[0]
        target_s = (rest_j["hand_" + near][0] + 0.30 * B * sc_m)
        tx, taway, _ = lane_point(target_s)
        hip_x_w, hip_away_w, _ = lane_point(rest_j["hip"][0])
        mpath = _polyline_path([MARTA_SPOT, (hip_x_w - 60.0, hip_away_w - 230.0), (tx, taway - 40.0)])
        mfeet = _stand_feet(0.0, -1, 0.05)
        wait = _idle(mfeet, 0.0, marta_b, -1,
                     lambda t: {s: ("fk", 6.0 if t < T_LINE2 else 30.0, 14.0 if t < T_LINE2 else 70.0) for s in R.SIDES},
                     lambda t: 3.0, lambda t: 8.0 if T_LINE2 < t < T_LINE2 + 1.2 else 0.0)
        mfeet2 = _stand_feet(0.0, 1, 0.05)

        def turn_fn(t):
            """The turn to watch the sled: the feet step round (lift and replant), the body swings through edge-on."""
            u = (t - t_turn) / 0.5
            f = -1 if u < 0.5 else 1
            feet = dict(mfeet if f < 0 else mfeet2)
            stepping = R.near_side(f)
            x0, y0, _, _ = feet[stepping]
            lift = 0.05 * R.B * math.sin(math.pi * min(1.0, max(0.0, (u - (0.0 if f < 0 else 0.5)) / 0.5)))
            feet[stepping] = (x0, y0 - lift, 0.0, lift < 1.0)
            p = _idle(feet, 0.0, marta_b, f, lambda t: {s: ("fk", 20.0, 70.0) for s in R.SIDES}, lambda t: 5.0)(t)
            return p

        def watch_head(t):
            """She follows the sled down the slope with her eyes: the head tilts down as it goes."""
            s, _, _, _ = sled_res.sample(t)
            return 6.0 + 10.0 * R.ease((s - 2600.0) / 3000.0)

        watch = _idle(mfeet2, 0.0, marta_b, 1, lambda t: {s: ("fk", 20.0, 80.0) for s in R.SIDES}, lambda t: 6.0,
                      watch_head)
        mwalk_g = marta_b.gait(R.WALK)
        dist = mpath.length / sc_m
        dur = t_help - 0.6 - t_walk0
        v_mw = dist / (dur * 0.91)   # the speed ramps in over 8 % of the walk and out over 10 %

        def mwalk_speed(t, _ph):
            u = (t - t_walk0) / dur
            return v_mw * min(1.0, u / 0.08) * (1.0 if u < 0.9 else max(0.0, 1 - (u - 0.9) / 0.1))

        mwalk = R.Loco(mwalk_g, 1, t_walk0, t_help - 0.6, mwalk_speed, 0.0,
                       phase0=R.entry_phase(mwalk_g, 1, 0.0, mfeet2), entry=mfeet2, entry_arms=(20.0, 80.0), blend=0.3)
        mend = mwalk.feet(t_help - 0.6 + mwalk.settle + 0.01)
        mxe = mwalk.x(t_help - 0.6)
    marta = Actor("marta", str(a / "marta"), marta_b, SIZES["marta"], mpath, [], look=[], views=[],
                  blinks=(2.6, 5.9, 9.0, 12.3, 15.2, 18.4, 24.4, 27.6))
    marta.look = [(0.0, "neutral"), (T_LINE1 + 0.8, "unimpressed"), (T_LINE2, "talk"), (T_LINE2 + 1.2, "smirk"),
                  (t_turn + 0.3, "worried"), (t_help - 0.2, "smile"), (t_help + 2.2, "smirk"), (T_LINE3, "talk"),
                  (T_LINE3 + 0.8, "smirk")]
    marta.views = [(0.0, "three_quarter", -1), (t_turn + 0.25, "three_quarter", 1), (t_help - 0.45, "three_quarter", -1)]
    marta.segments = [(0.0, t_turn, "fn", wait), (t_turn, t_turn + 0.5, "fn", turn_fn), (t_turn + 0.5, t_walk0, "fn", watch),
                      (t_walk0, t_help - 0.2, "loco", mwalk), (t_help - 0.2, DURATION, "fn", None)]
    marta.segments[-1] = (t_help - 0.2, DURATION, "fn", _helper(marta, dev, mend, mxe))
    marta.t_turn, marta.t_walk0 = t_turn, t_walk0
    actors = {"dev": dev, "marta": marta, "world": world}
    for act in (dev, marta):
        act.secondary = _secondary(act)
    world["camera"] = _camera_table(actors)
    return actors


def _impact_squash(t: float, t_impact: float) -> float:
    """The body squashes on the ground contact and overshoots back (volume kept by the rig)."""
    u = t - t_impact
    if u < 0:
        return 1.0
    if u < 0.1:
        return R.lerp(1.0, 0.86, u / 0.1)
    if u < 0.28:
        return R.lerp(0.86, 1.03, R.ease((u - 0.1) / 0.18))
    return R.lerp(1.03, 1.0, R.ease((u - 0.28) / 0.25))


def _pose_from_joints(j: dict, contacts: dict, f: int, sc: float, b: R.Build, squash: float = 1.0) -> R.Pose:
    """A rig pose (in the lane's rig frame) from simulated joints (s, h): the torso's lean from hip -> neck, the head's
    from neck -> head, the feet and hands where the simulation put them (the legs are solved to the feet)."""
    with R.use_build(b):
        hs, hh = j["hip"]
        hip = (hs / sc, R.GROUND - (hh - TERRAIN.h(hs)) / sc)
        ns, nh = j["neck"]
        torso = math.degrees(math.atan2(f * (ns - hs), nh - hh))
        hd_s, hd_h = j["head"]
        head = math.degrees(math.atan2(f * (hd_s - ns), hd_h - nh)) - torso
        feet, arms = {}, {}
        for s in R.SIDES:
            a_s, a_h = j["ankle_" + s]
            on = contacts.get("shin_" + s, False) or (a_h - TERRAIN.h(a_s)) < 0.04 * R.B * sc
            feet[s] = (a_s / sc, R.GROUND - (a_h - TERRAIN.h(a_s)) / sc, 0.0, bool(on))
            w_s, w_h = j["hand_" + s]
            arms[s] = ("ik", hip[0] + (w_s - hs) / sc, hip[1] + (hh - w_h) / sc)
        return R.Pose(f, hip, torso, head, feet=feet, arms=arms, squash=squash)


def _helper(marta: Actor, dev: Actor, feet: dict, x: float):
    """Marta bends and holds out her hand where Dev reaches, rises with him, then stands with him."""
    b = marta.build
    near = R.near_side(-1)
    far = R.SIDES[1 - R.SIDES.index(near)]

    def fn(t):
        with R.use_build(dev.build):
            dp = dev.raw(t)
            dj = R.skeleton(dp)
        hand = dj["hand_" + R.near_side(1)]
        # Dev's hand in Marta's rig frame: both stand on the lane at the same depth by now
        hx_w = lane_point(hand[0] * dev.sc)[0]
        hh_w = TERRAIN.h(dp.hip[0] * dev.sc) + (R.GROUND - hand[1]) * dev.sc
        mx_w, _, mh_w = marta.path(x * marta.sc)
        tx = x + (hx_w - mx_w) / marta.sc
        ty = R.GROUND - (hh_w - mh_w) / marta.sc
        holding = dev.t_help - 0.1 <= t <= dev.t_help + 1.8
        bend = 26.0 * R.ease((t - (dev.t_help - 0.6)) / 0.5) * (1 - R.ease((t - (dev.t_help + 1.2)) / 0.6))
        p = _idle(feet, x, b, -1, None, lambda t: 2.0 + bend)(t)
        p.arms = {near: ("fk", 8.0, 14.0), far: ("fk", -8.0 + 0.5 * bend, 30.0)}
        rest_hand = R.fk_arm(R.shoulder_of(p), -1, 8.0, 14.0)[1]
        if holding:
            p.arms[near] = ("ik", tx, ty)
        elif t > dev.t_help + 1.8:   # she lets go: the hand eases back to her side, it does not snap
            u = R.ease((t - (dev.t_help + 1.8)) / 0.4)
            if u < 1.0:
                p.arms[near] = ("ik",) + R.lerp2((tx, ty), rest_hand, u)
        return p
    return fn


def _secondary(act: Actor) -> np.ndarray:
    """Follow-through of the hips' motion (240 Hz): row 0 the head's nod behind each dip (a stiff spring on the vertical
    speed), row 1 the torso's lag behind accelerations (it leans back when the hips speed up, forward when they brake)."""
    n = int(DURATION * RATE) + 2
    hips = np.array([act.raw(i / RATE).hip for i in range(n)])
    vx = np.gradient(hips[:, 0]) * RATE
    vy = np.gradient(hips[:, 1]) * RATE
    ax = np.gradient(vx) * RATE
    nod = P.follow_through(np.clip(vy / R.B * 9.0, -7, 7), 160.0, 14.0)
    lag = P.follow_through(np.clip(-ax / R.B * 0.9, -9, 9), 60.0, 11.0)
    return np.stack([nod, lag])


# --- the shots and the camera operator ---------------------------------------------------------------------------------------
@dataclass
class Shot:
    t0: float
    t1: float
    zoom: float
    subjects: list            # (actor name | "sled", part): their world points are averaged
    sy: float = 0.62          # where the subjects' point sits on screen (fraction of H)
    sx: float = 0.5           # ... and of W (before the lead room)
    lead: float = 0.0         # lead room: the subjects sit this fraction of W behind the centre, ahead of their motion
    push: float = 0.012       # a slow push-in per second (a hold is never dead)
    zeta: float = 1.0         # the operator's damping (under 1 overshoots: caught off guard)
    fit: float = 0.0          # if set, the zoom also keeps the subjects within this fraction of the frame
    omega: float = 2 * math.pi * 0.9


def shots(actors: dict) -> list[Shot]:
    dev, marta, w = actors["dev"], actors["marta"], actors["world"]
    t_rel = {k: t for t, k, _ in w["sled"].events}.get("release", T_THROW)
    return [
        Shot(0.0, T_STOP + 0.4, 1.0, [("dev", "hip")], sy=0.66, lead=0.14),                    # wide: he walks in with the sled
        Shot(T_STOP + 0.4, 8.4, 1.45, [("dev", "chest"), ("marta", "chest")], sy=0.58),        # two-shot: the presentation
        Shot(8.4, T_LINE2 - 0.1, 3.4, [("marta", "head")], sy=0.42),                           # close: not impressed
        Shot(T_LINE2 - 0.1, T_THROW, 2.8, [("dev", "head")], sy=0.42),                          # close: his grin goes (the line off)
        Shot(T_THROW, t_rel + 1.6, 1.5, [("dev", "chest")], sy=0.6, lead=0.05),                # medium: the throw, the sled slips away
        Shot(t_rel + 1.6, T_RUN + 1.9, 1.0, [("dev", "hip"), ("sled", "")], sy=0.64, lead=0.1),  # wide: the chase starts
        Shot(T_RUN + 1.9, dev.impact + 1.1, 1.35, [("dev", "hip")], sy=0.62, lead=0.16, zeta=0.7),   # tracking: the fall
        Shot(dev.impact + 1.1, dev.t_help - 0.8, 1.25, [("dev", "hip"), ("marta", "hip")], sy=0.6, sx=0.46, fit=0.55),  # she comes
        Shot(dev.t_help - 0.8, T_LINE3 - 0.2, 1.5, [("dev", "chest"), ("marta", "chest")], sy=0.6),   # medium: the help up
        Shot(T_LINE3 - 0.2, DURATION, 1.4, [("dev", "chest"), ("marta", "chest")], sy=0.58, sx=0.4, push=0.02),  # they watch it go
    ]


def subject_point(actors: dict, name: str, part: str, t: float) -> tuple[float, float, float]:
    """(world x, away, world y) of an actor's part or the sled."""
    if name == "sled":
        s, h, _, _ = actors["world"]["sled"].sample(t)
        x, away, _ = lane_point(s)
        return x, away, STAND_WORLD - h - 0.07 * R.B * S0
    act = actors[name]
    p = act.raw(t)
    with R.use_build(act.build):
        j = R.skeleton(p)
    q = {"hip": p.hip, "chest": R.lerp2(p.hip, j["neck"], 0.6), "head": j["head"]}[part]
    x, away, h = act.path(q[0] * act.sc)
    return x, away, STAND_WORLD - h - (R.GROUND - q[1]) * act.sc


def _camera_table(actors: dict) -> np.ndarray:
    """(4, n) at 240 Hz: cx, cy, zoom and the shot index. Each shot's operator starts framed on its subjects and follows
    them, critically damped, with lead room from the subjects' motion and a slow push-in; a cut is a new operator."""
    n = int(DURATION * RATE) + 2
    out = np.zeros((5, n))     # cx, cy, zoom, shot index, the operator's target cx
    ts = np.arange(n) / RATE
    for si, sh in enumerate(shots(actors)):
        i0, i1 = int(round(sh.t0 * RATE)), min(n, int(round(sh.t1 * RATE)) + 1)
        if i1 <= i0:
            continue
        tt = ts[i0:i1]
        pts = np.array([[subject_point(actors, nm, part, t) for nm, part in sh.subjects] for t in tt]).mean(axis=1)
        vx = np.gradient(pts[:, 0]) * RATE if len(tt) > 1 else np.zeros(len(tt))
        vsm = P.follow_through(np.clip(vx / 300.0, -1, 1), 40.0, 9.0) if len(tt) > 1 else vx
        zoom = sh.zoom * (1 + sh.push * (tt - sh.t0))
        if sh.fit and len(sh.subjects) > 1:
            allp = np.array([[subject_point(actors, nm, part, t) for nm, part in sh.subjects] for t in tt])
            for k in range(len(tt)):
                # the spread of the subjects on screen at zoom 1 (x by depth, y by the world y and the depth)
                xs = [(q[0] - pts[k, 0]) / depth_of(q[1]) for q in allp[k]]
                ys = [(q[2] - pts[k, 2]) / depth_of(q[1]) + (STAND_WORLD - HORIZON_WORLD) * (1 / depth_of(q[1]) - 1 / depth_of(pts[k, 1]))
                      for q in allp[k]]
                need = max((max(xs) - min(xs)) / (sh.fit * W), (max(ys) - min(ys)) / (sh.fit * H), 1e-6)
                zoom[k] = min(zoom[k], 1.0 / need)
            zoom = P.follow_through(zoom, 30.0, 11.0, x0=float(zoom[0]))
        cxs, cys = np.empty(len(tt)), np.empty(len(tt))
        for k in range(len(tt)):
            sx = sh.sx * W - sh.lead * W * vsm[k]
            cxs[k], cys[k], _ = frame_for(tuple(pts[k]), zoom[k], sx, sh.sy * H)
        op = P.Operator(sh.omega, sh.zeta, vmax=2600.0)
        out[0, i0:i1] = op.track(cxs)
        out[1, i0:i1] = P.Operator(sh.omega * 0.8, 1.0).track(cys)
        out[2, i0:i1] = zoom
        out[3, i0:i1] = si
        out[4, i0:i1] = cxs
    return out


def camera(t: float, assets: str | None = None) -> tuple[float, float, float]:
    """(cx, cy, zoom) at ``t`` from the cast's camera table."""
    table = cast(assets or _ASSETS[0])["world"]["camera"]
    i = min(table.shape[1] - 1, max(0, int(round(t * RATE))))
    return float(table[0, i]), float(table[1, i]), float(table[2, i])


def shot_index(t: float, assets: str) -> int:
    table = cast(assets)["world"]["camera"]
    i = min(table.shape[1] - 1, max(0, int(round(t * RATE))))
    return int(table[3, i])


_ASSETS = [""]


# --- the sled on screen --------------------------------------------------------------------------------------------------------
def sled_world(t: float, actors: dict) -> tuple[float, float, float, float, float]:
    """(world x, away, elevation of the centre, tilt degrees, speed) from the simulation."""
    s, h, ang, v = actors["world"]["sled"].sample(t)
    x, away, _ = lane_point(s)
    return x, away, h, math.degrees(ang), v


# --- the layers ----------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=8)
def _img(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _place(frame: Image.Image, img: Image.Image, x: float, y: float, k: float, rot: float = 0.0, flip: bool = False,
           kx: float = 1.0):
    """Paste ``img`` scaled by ``k`` (``kx`` more horizontally) with its top-left at (x, y) (clipped to the frame)."""
    w, h = max(1, int(round(img.width * k * kx))), max(1, int(round(img.height * k)))
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    vx0, vy0, vx1, vy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if vx1 <= vx0 or vy1 <= vy0:
        return
    sx0, sy0 = (vx0 - x0) / (k * kx), (vy0 - y0) / k
    sx1, sy1 = (vx1 - x0) / (k * kx), (vy1 - y0) / k
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
    mx = (0 - MID_COL * MID_SCALE - cx) * z + W / 2
    my = (STAND_WORLD - MID_ROW * MID_SCALE - cy) * z + H / 2
    _place(frame, mid, mx, my, k)
    if mx + mid.width * k < W:   # the valley continues: the plain mirrored beyond the picture's right edge
        _place(frame, mid, mx + mid.width * k, my, k, flip=True)


NEAR_ROCKS = (-420.0, 820.0, 2050.0)   # world x of the foreground rocks (they pass 1.35x faster than the ground)


@lru_cache(maxsize=2)
def _near_parts(path: str):
    """The near picture is a frame of rocks round an empty middle: its bottom-middle rock is the passing foreground rock."""
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
    if z > 1.7:   # a close-up: the operator has moved in past the foreground rocks
        return
    _, rock = _near_parts(str(assets / "world" / "near.png"))
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
    sx, sy, w, h = float(sx), float(sy), float(w), float(h)
    if alpha <= 0 or not (-w * 2 < sx < W + w * 2) or not (-h * 4 < sy < H + h * 4):
        return
    sh = Image.new("RGBA", (int(w * 2.4) + 4, int(h * 4) + 4), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([w * 0.2, h, w * 2.2, h * 3], fill=(70, 90, 140, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(h * 0.6))
    frame.alpha_composite(sh, (int(sx - w * 1.2), int(sy - h * 2)))


# --- one frame -----------------------------------------------------------------------------------------------------------
def actor_on_screen(actor: Actor, t: float, cam):
    """(layer, x, y, placed pose, skeleton, k): the actor drawn by the rig at its depth, and where its layer goes."""
    p = actor.pose(t)
    pl = place(actor, p, cam)
    with R.use_build(actor.build):
        j = R.skeleton(pl.pose)
        layer, (x0, y0) = R.draw_character(pl.pose, actor.folder)
    hx, hy = pl.screen
    return layer, hx + (x0 - pl.anchor[0]) * pl.k, hy + (y0 - pl.anchor[1]) * pl.k, pl, j


def joint_screen(pl: Placed, q: tuple) -> tuple[float, float]:
    """A rig point of a placed pose -> screen."""
    return pl.screen[0] + (q[0] - pl.anchor[0]) * pl.k, pl.screen[1] + (q[1] - pl.anchor[1]) * pl.k


def render_frame(t: float, assets: str, captions: bool = True) -> Image.Image:
    a = Path(assets)
    actors = cast(assets)
    cam = camera(t, assets)
    frame = Image.new("RGBA", (W, H))
    draw_world(frame, a, cam, t)
    sx_w, saway, sh, tilt, sv = sled_world(t, actors)
    sled = _img(str(a / "world" / "sled_side.png"))
    ssx, ssy, sk = world_screen(sx_w, saway, sh, 0.0, cam)
    sscale = SLED_LEN * R.B * S0 * sk / sled.width
    items = [(depth_of(actors[nm].hip_world(t)[1]), nm) for nm in ("marta", "dev")] + [(depth_of(saway), "sled")]
    drawn = {}
    for d, name in sorted(items, key=lambda it: -it[0]):
        if name == "sled":
            gx, gy, _ = world_screen(sx_w, saway, TERRAIN.h(LANE.s_of_x(sx_w)) if saway < 1 else sh, 0.0, cam)
            draw_shadow(frame, ssx, ssy + sled.height * sscale * 0.45, sled.width * sscale * 0.5, 10 * sk, 90)
            _place(frame, sled, ssx - sled.width * sscale / 2, ssy - sled.height * sscale / 2, sscale, rot=tilt, flip=True)
            drawn["sled_handle"] = (ssx + sled.width * sscale * 0.42, ssy - sled.height * sscale * 0.1)
            continue
        act = actors[name]
        layer, lx, ly, pl, j = actor_on_screen(act, t, cam)
        p = pl.pose
        hx, hy = joint_screen(pl, p.hip)
        gx, gy = joint_screen(pl, (p.hip[0], R.GROUND))
        lift = max(0.0, (gy - hy) / (pl.k * R.B) - act.build.stand)
        draw_shadow(frame, gx, gy, 0.32 * R.B * pl.k * (1.7 if p.torso > 45 else 1.0), 9 * pl.k, int(110 * max(0.0, 1 - lift * 3)))
        kx = act.turn(t)
        if kx < 1.0:
            # the edge-on in-between of a turn: the drawing narrows about the hips
            lx = hx + (lx - hx) * kx
        _place(frame, layer, lx, ly, pl.k, kx=kx)
        drawn[name] = (pl, j)
    # the rope: from Dev's near hand to the sled's handle while attached, sagging by its slack
    res = actors["world"]["sled"]
    i = min(len(res.t) - 1, max(0, int(round(t * RATE))))
    if not math.isnan(res.rope_slack[i]) and "sled_handle" in drawn and "dev" in drawn:
        pl, j = drawn["dev"]
        hand = joint_screen(pl, j["hand_" + R.near_side(pl.pose.facing)])
        hx2, hy2 = drawn["sled_handle"]
        sag = max(6.0, float(res.rope_slack[i])) * 0.5 * cam[2]
        pts = [(R.lerp(hand[0], hx2, u), R.lerp(hand[1], hy2, u) + sag * 4 * u * (1 - u)) for u in np.linspace(0, 1, 16)]
        ImageDraw.Draw(frame).line(pts, fill=(52, 36, 24, 255), width=max(2, int(5 * cam[2])), joint="curve")
    elif t < T_THROW + 0.8 and "sled_handle" in drawn:  # the dropped rope trails behind the sled
        hx2, hy2 = drawn["sled_handle"]
        ImageDraw.Draw(frame).line([(hx2, hy2), (hx2 - 60 * cam[2], hy2 - 20 * cam[2])], fill=(52, 36, 24, 255),
                                   width=max(2, int(5 * cam[2])))
    dev = actors["dev"]
    if "dev" in drawn and abs(t - dev.impact) < 1.0:
        pl, j = drawn["dev"]
        px, py = joint_screen(pl, (pl.pose.hip[0] + 0.25 * R.B, R.GROUND))
        draw_puff(frame, t, dev.impact, px, py, cam[2])
    draw_near(frame, a, cam, t)
    draw_snow(frame, t, cam)
    out = frame.convert("RGB")
    if captions:
        out = draw_caption(out, t)
    return fade(out, t)


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


# --- the voice's lip flaps ------------------------------------------------------------------------------------------------------
def mouth_timeline(voice: Path | None, who: str, open_expr: str, closed_expr: str) -> list:
    """(t, expr) flaps for a speaker from the loudness of their takes: the mouth opens on the loud 80 ms windows."""
    if not voice:
        return []
    out = []
    for k, (t0, speaker, _) in enumerate(LINES):
        f = voice / f"line_{k + 1}.wav"
        if speaker != who or not f.exists():
            continue
        with wave.open(str(f)) as wf:
            sr = wf.getframerate()
            v = np.frombuffer(wf.readframes(wf.getnframes()), "<i2").astype(float) / 32768.0
            if wf.getnchannels() == 2:
                v = v.reshape(-1, 2).mean(axis=1)
        win = int(0.08 * sr)
        n = len(v) // win
        rms = np.sqrt((v[:n * win].reshape(n, win) ** 2).mean(axis=1))
        thr = 0.35 * (rms.max() or 1.0)
        state = None
        for i, r in enumerate(rms):
            want = open_expr if r > thr else closed_expr
            if want != state:
                out.append((t0 + i * win / sr, want))
                state = want
        out.append((t0 + n * win / sr, None))
    return out


# --- sound ---------------------------------------------------------------------------------------------------------------
def events(fps: int = 24, assets: str = "") -> list[dict]:
    actors = cast(assets)
    w = actors["world"]
    out = []
    n = int(DURATION * fps)
    for name in ("dev", "marta"):
        act = actors[name]
        prev = act.raw(0.0)
        for i in range(1, n):
            t = i / fps
            p = act.raw(t)
            for s in R.SIDES:
                if R._grounded(p.feet[s]) and not R._grounded(prev.feet[s]):
                    out.append({"t": round(t, 4), "kind": "step", "who": name, "loud": 1.3 if T_RUN < t < actors["dev"].trip else 0.8})
            prev = p
    dev = actors["dev"]
    for t, kind, data in w["sled"].events:
        if kind in ("bump", "takeoff", "land"):
            out.append({"t": round(float(t), 4), "kind": kind, "who": "sled", "loud": 1.0})
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
    # the sled's hiss on the snow: with its simulated speed, quieter with depth
    hiss = _noise(rng, n, 1500, 9000, sr)
    env = np.zeros(n)
    for i in range(0, n, sr // 50):
        t = i / sr
        x, away, _, _, v = sled_world(t, actors)
        env[i:i + sr // 50] = min(1.0, abs(v) / 600.0) / depth_of(away) ** 1.2
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
        elif e["kind"] in ("bump", "land"):
            m = int(0.3 * sr)
            t2 = np.arange(m) / sr
            s = np.sin(2 * np.pi * (90 - 30 * t2) * t2) * np.exp(-t2 / 0.07) * 0.6
            s += _noise(rng, m, 300, 4000, sr) * np.exp(-t2 / 0.05) * 0.3
        elif e["kind"] == "takeoff":
            m = int(0.2 * sr)
            s = _noise(rng, m, 2000, 9000, sr) * np.sin(np.pi * np.arange(m) / m) * 0.15
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
    """Motion checks per hero: BR-3 a planted foot is reached, BR-4 bones keep their length, BR-5 no joint jumps, BR-7
    every footfall sounds, BR-11 a planted foot is a fixed world point (it never slides on screen, whatever the depth),
    BR-13 a change of view or facing happens inside a turn (an edge-on in-between is drawn); and the shot's: IS-1 the
    heroes stay in frame while they act, BR-8 the sled never runs through a hero (a contact is a simulated one), BR-9
    the hips' speed never jumps outside a simulated impact, BR-10 the camera never stops dead while its subjects move,
    BR-12 nothing that stands on the ground is drawn above the horizon. IS-1 applies to the shot's subjects (a
    close-up leaves the other hero out on purpose)."""
    actors = cast(assets)
    w = actors["world"]
    n = int(DURATION * fps)
    findings = []
    steps = {(e["who"], round(e["t"], 4)) for e in events(fps, assets) if e["kind"] == "step"}
    contacts = [t for t, k, _ in w["sled"].events if k == "bump"]
    shot_list = shots(actors)
    dev = actors["dev"]
    for name in ("dev", "marta"):
        act = actors[name]
        prev_p = prev_j = prev_hip = None
        prev_world = {}
        for i in range(n):
            t = i / fps
            cam = camera(t, assets)
            p = act.pose(t)
            pl = place(act, p, cam)
            with R.use_build(act.build):
                j = R.skeleton(pl.pose)
                for s in R.SIDES:
                    ax, ay = j["ankle_" + s]
                    fx, fy, _, c = pl.pose.feet[s]
                    want = fy - (R.TQ_BACK if pl.pose.view == "three_quarter" and s != R.near_side(p.facing) else 0.0)
                    if c and math.hypot(ax - fx, ay - want) > 2.0:
                        findings.append({"rule": "BR-3", "who": name, "t": t, "what": f"planted foot {s} not reached"})
                    for a_, b_, ln in (("hip_" + s, "knee_" + s, R.THIGH), ("knee_" + s, "ankle_" + s, R.SHIN)):
                        if abs(math.dist(j[a_], j[b_]) - ln) > 0.5:
                            findings.append({"rule": "BR-4", "who": name, "t": t, "what": f"{a_}-{b_} length changed"})
                    wx, waway, _ = act.path(p.feet[s][0] * act.sc)
                    if c and s in prev_world and prev_world[s][2] and math.dist((wx, waway), prev_world[s][:2]) > 1.0 \
                            and not (name == "dev" and dev.trip <= t <= dev.rest + 1 / fps):
                        findings.append({"rule": "BR-11", "who": name, "t": t, "what": f"planted foot {s} moved in the world"})
                    prev_world[s] = (wx, waway, c)
            simulated = name == "dev" and dev.trip <= t <= dev.rest + 1 / fps   # the ragdoll: contacts slide, limbs whip
            if prev_j and p.view == prev_p.view and p.facing == prev_p.facing and not simulated:
                for key, v in j.items():
                    lim = 0.4 * R.B if key.startswith("hand") else 0.22 * R.B
                    if isinstance(v, tuple) and key in prev_j and math.dist(v, prev_j[key]) > lim:
                        findings.append({"rule": "BR-5", "who": name, "t": t, "what": f"{key} jumped"})
            if prev_p and (p.view != prev_p.view or p.facing != prev_p.facing) and act.turn(t) > 0.6:
                findings.append({"rule": "BR-13", "who": name, "t": t, "what": "a change of view without a turn"})
            hx, hy = joint_screen(pl, pl.pose.hip)
            in_shot = any(nm == name for nm, _ in shot_list[shot_index(t, assets)].subjects)
            if t > 1.2 and in_shot and not (0 < hx < W and 0 < hy < H):
                findings.append({"rule": "IS-1", "who": name, "t": t, "what": "the hero's hips leave the frame"})
            x_h, a_h, h_h, lift = act.hip_world(t)
            if prev_hip is not None:
                v = math.hypot(x_h - prev_hip[0], a_h - prev_hip[1]) * fps
                if prev_hip[2] is not None and abs(v - prev_hip[2]) > 900.0 and not (
                        abs(t - dev.impact) < 0.15 or abs(t - w["bump"]) < 0.15 or abs(t - dev.trip) < 0.1):
                    findings.append({"rule": "BR-9", "who": name, "t": t, "what": f"the hips' speed jumped by {abs(v - prev_hip[2]):.0f} px/s"})
                prev_hip = (x_h, a_h, v)
            else:
                prev_hip = (x_h, a_h, None)
            gx, gy, _ = world_screen(x_h, a_h, h_h, 0.0, cam)
            _, horizon, _ = world_screen(x_h, 1e9, 0.0, 0.0, cam)
            if gy < horizon + 2:
                findings.append({"rule": "BR-12", "who": name, "t": t, "what": "standing above the horizon"})
            if prev_p:
                landed = [s for s in R.SIDES if R._grounded(p.feet[s]) and not R._grounded(prev_p.feet[s])]
                if landed and (name, round(t, 4)) not in steps:
                    findings.append({"rule": "BR-7", "who": name, "t": t, "what": "a footfall without its sound"})
            prev_p, prev_j = p, j
    # the sled against the heroes, the camera, the horizon
    table = w["camera"]
    prev_v = None
    still = 0.0
    for i in range(n):
        t = i / fps
        cam = camera(t, assets)
        sx_w, saway, sh, _, _ = sled_world(t, actors)
        s_sled = LANE.s_of_x(sx_w) if saway < 1 else None
        for name in ("dev", "marta"):
            act = actors[name]
            x_h, a_h, h_h, _ = act.hip_world(t)
            if abs(depth_of(a_h) - depth_of(saway)) < 0.06 and abs(x_h - sx_w) < SLED_LEN * R.B * S0 * 0.5 + 0.1 * R.B * S0:
                if not any(abs(t - tc) < 0.3 for tc in contacts) and not (name == "dev" and T_STOP < t < T_RUN + 0.4):
                    findings.append({"rule": "BR-8", "who": name, "t": t, "what": "the sled runs through the hero"})
        _, gy, _ = world_screen(sx_w, saway, sh, 0.0, cam)
        _, horizon, _ = world_screen(sx_w, 1e9, 0.0, 0.0, cam)
        if gy < horizon + 2:
            findings.append({"rule": "BR-12", "who": "sled", "t": t, "what": "the sled is above the horizon"})
        if i > 0:
            k0, k1 = int(round((t - 1 / fps) * RATE)), int(round(t * RATE))
            if table[3, k0] == table[3, k1]:
                v = (table[0, k1] - table[0, k0]) * fps
                if prev_v is not None and abs(v - prev_v) > 1500.0:
                    findings.append({"rule": "BR-10", "who": "camera", "t": t, "what": "the pan's speed jumped"})
                moving = abs(table[4, k1] - table[4, k0]) * fps > 20.0   # the subjects move
                still = still + 1 / fps if (abs(v) < 0.5 and moving) else 0.0
                if still > 0.3:
                    findings.append({"rule": "BR-10", "who": "camera", "t": t, "what": "the camera stopped dead while its subjects moved"})
                prev_v = v
            else:
                prev_v, still = None, 0.0
    return {"verdict": "PASS" if not findings else "FAIL", "frames": n, "fps": fps, "count": len(findings),
            "findings": findings[:200], "events": [(round(float(t), 3), k, {a: (round(b, 1) if isinstance(b, float) else b)
                                                                            for a, b in d.items()})
                                                    for t, k, d in w["sled"].events + w["ragdoll"].events]}


def render(assets: str, out: Path, fps: int = 24, voice: Path | None = None, crf: int = 18, span: tuple | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    _ASSETS[0] = assets
    actors = cast(assets)
    actors["marta"].mouth = mouth_timeline(voice, "marta", "talk", "smirk")
    t0, t1 = span or (0.0, DURATION)
    n = int(round((t1 - t0) * fps))
    silent = out / "ice_short_silent.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-frames:v", str(n), "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    stills = {}
    marks = np.linspace(t0 + 0.5, t1 - 0.5, 24)
    for i in range(n):
        t = t0 + i / fps
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
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-ss", f"{t0:.3f}", "-i", str(wav), "-c:v", "copy", "-af",
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
    r.add_argument("--span", type=float, nargs=2, default=None, help="render only t0 t1 (a clip for a test)")
    c = sub.add_parser("check")
    c.add_argument("--assets", required=True)
    a = ap.parse_args(argv)
    _ASSETS[0] = a.assets
    rep = render(a.assets, a.out, a.fps, a.voice, span=tuple(a.span) if a.span else None) if a.cmd == "render" else check(a.assets)
    print(json.dumps({k: v for k, v in rep.items() if k != "findings"} | {"first": rep["findings"][:8]}, indent=1, default=str))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
