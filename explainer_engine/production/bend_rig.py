"""A bending character rig on a painted plate: the hybrid model's proof of concept (the creator's word "კი", 2026-10-22;
docs/research/HYBRID_VISUAL_MODEL_2026-10-22.md section 7). numpy + PIL only; nothing paid.

What the ice-age test (draft PR #20) could not do and this does:

* **limbs bend instead of hinging**: a leg or an arm is one ink shape along two bones (thigh + shin, upper arm + forearm),
  outlines first and fills after, so the knee and the elbow have no seam and no hole at any angle (``draw_limb``);
* **feet are planted by inverse kinematics**: the gait is driven by the distance the hips travelled, every foot in stance
  holds one world position, the knee is solved from hip and foot (``ik2``), the hips rise and fall by what the legs can
  reach (no foot slide, no ground penetration; measured by ``check``);
* **one event table**: footsteps, takeoff, landing and the fall are read from the same poses the picture is drawn from,
  so sound can never run after a stop (the ice test's items 3 and 6);
* **a wound is data**: the scrape on the right knee appears at the impact frame, the limp is the same gait with a shorter,
  dipping stance on that leg and a hand held on the thigh.

The world stays the AI's: the plate is a painted picture we already paid for; the snowfall and the swaying trees are
code over it (free, deterministic, exact). Every frame is a pure function of its time.

* **the face is the image model's, the body is ours** (the creator, 2026-10-22 18:47): ``--heads`` takes a folder of
  painted ``head_<expression>.png`` pictures of one face; the expression timeline picks the picture, the rig carries it,
  the hands take its skin colour; without the folder the head is drawn by code;
* **a turn is three drawings**: side, front (the feet step round to their own sides), the other side;
* **the walk rolls heel -> sole -> toes**, the torso pitches with each step, the arms trail the legs and the head nods
  on a spring, so the gait does not move in lock-step.

* **the body's paint is the image model's too** (the creator, 2026-10-22 19:16, after the Wild Ink cave reference):
  ``parts.json`` in the heads folder names a painted picture and, per part, its painted bone and half-widths
  (``Sheet``); the rig carries each part's paint by a similarity onto its own bone, so a limb bends over two bones and
  keeps its paint, the ink outline stays the rig's, mirrored for the other facing. Parts cut from one painted pose
  are a stop-gap: a production sheet paints every part straight and separate (the research doc, section 8.2).

    python -m explainer_engine.production.bend_rig demo --out jobs/bend_poc --plate <plate.png> [--heads <dir>] [--fps 24]
    python -m explainer_engine.production.bend_rig check
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import wave
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FRAME_W, FRAME_H = 1920, 1080
B = 420.0                      # body height, px (feet to the top of the head)
GROUND = 950.0                 # where the snow plane meets the soles, px
ANKLE = 0.035 * B              # ankle height of a flat foot
ANK = GROUND - ANKLE           # the y of a planted ankle
THIGH, SHIN = 0.21 * B, 0.21 * B
REACH = (THIGH + SHIN) * 0.985  # hips never pull a planted leg fully straight
TORSO, NECK = 0.27 * B, 0.13 * B
UPPER, FORE = 0.16 * B, 0.15 * B
STAND = 0.435                  # hip height of a standing hero, in body heights
HEAD = 0.15 * B
FRONT_HIP = 0.055 * B          # half the hips' width in the front drawing
TQ_HIP, TQ_SHOULDER = 0.035 * B, 0.055 * B  # the three-quarter drawing: how far each side's hip and shoulder sit apart
TQ_BACK = 0.014 * B            # ... and how much higher the far side's foot and shoulder sit (it is further away)
LINE = 0.016 * B               # the ink line, bold and loose (Wild Ink)
SS = 2                         # supersampling of the character layer
SIDES = ("L", "R")
INJURED = "R"

INK = (28, 24, 30)
SKIN = (238, 186, 146)
JACKET = (34, 128, 142)
TROUSERS = (122, 86, 58)
BOOTS = (64, 46, 38)
SCARF = (204, 62, 48)
HAIR = (72, 46, 34)
WHITE = (252, 250, 244)
SCRAPE = (196, 52, 52)


# --- small maths -----------------------------------------------------------------------------------------------------
def ease(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)


def ik2(root: tuple, target: tuple, l1: float, l2: float, bend: float) -> tuple[tuple, tuple]:
    """Two-bone inverse kinematics in screen pixels (y down): returns (joint, end). ``bend`` = +1 puts the joint on the
    side of the target vector rotated a quarter turn toward the facing (a knee bends forward), -1 the other way (an
    elbow bends back). An unreachable target is approached along its line; the bone lengths never change."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        dx, dy, d = 0.0, 1.0, 1e-6
    ux, uy = dx / d, dy / d
    dc = min(max(d, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
    a = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    px, py = uy * bend, -ux * bend  # (dy, -dx): forward of a downward vector when bend = facing
    joint = (root[0] + ux * a + px * h, root[1] + uy * a + py * h)
    jx, jy = target[0] - joint[0], target[1] - joint[1]
    jd = math.hypot(jx, jy) or 1e-6
    end = (joint[0] + jx / jd * l2, joint[1] + jy / jd * l2)
    return joint, end


def fk_arm(shoulder: tuple, facing: int, angle: float, elbow: float) -> tuple[tuple, tuple]:
    """Forward kinematics: ``angle`` from straight down (degrees, positive = forward), forearm bent ``elbow`` more."""
    a, b = math.radians(angle), math.radians(angle + elbow)
    e = (shoulder[0] + facing * math.sin(a) * UPPER, shoulder[1] + math.cos(a) * UPPER)
    return e, (e[0] + facing * math.sin(b) * FORE, e[1] + math.cos(b) * FORE)


# --- a character's build: bone lengths in body heights ------------------------------------------------------------------
@dataclass(frozen=True)
class Build:
    """One character's proportions (a cartoon cast has short-legged and long-legged heroes). ``use_build`` makes them the
    rig's bones while that character is posed and drawn; the default is the PoC hero's."""
    thigh: float = 0.21
    shin: float = 0.21
    torso: float = 0.27
    neck: float = 0.13
    upper: float = 0.16
    fore: float = 0.15
    head_h: float = 0.42     # the painted head picture's height (crown to the neck stump)

    @property
    def stand(self) -> float:
        return (self.thigh + self.shin) * 0.435 / 0.42

    def gait(self, g: "Gait") -> "Gait":
        """The same gait for these legs: stride, lift and hip height scale with the leg length."""
        k = (self.thigh + self.shin) / 0.42
        return replace(g, stride=g.stride * k, lift=g.lift * k, hip=g.hip * k, bob=g.bob * k, dip=g.dip * k)


DEFAULT_BUILD = Build()


def load_build(folder: str | None) -> Build | None:
    """A character folder's build (``build`` in its ``parts_side.json``), or None."""
    path = Path(folder) / "parts_side.json" if folder else None
    if not path or not path.exists():
        return None
    spec = json.loads(path.read_text(encoding="utf-8")).get("build")
    return Build(**spec) if spec else None


@contextmanager
def use_build(b: Build | None):
    """Pose and draw with ``b``'s bones (module constants swapped for the duration; single-threaded)."""
    g = globals()
    keep = {k: g[k] for k in ("THIGH", "SHIN", "REACH", "TORSO", "NECK", "UPPER", "FORE", "STAND", "HEAD_H")}
    if b is not None:
        g.update(THIGH=b.thigh * B, SHIN=b.shin * B, REACH=(b.thigh + b.shin) * B * 0.985, TORSO=b.torso * B,
                 NECK=b.neck * B, UPPER=b.upper * B, FORE=b.fore * B, STAND=b.stand, HEAD_H=b.head_h * B)
    try:
        yield
    finally:
        g.update(keep)


# --- the pose ----------------------------------------------------------------------------------------------------------
@dataclass
class Pose:
    facing: int
    hip: tuple
    torso: float                      # lean from vertical, degrees, positive = forward
    head: float = 0.0                 # head tilt on top of the torso, positive = down/forward
    feet: dict = field(default_factory=dict)   # side -> (x, y, pitch, contact)
    arms: dict = field(default_factory=dict)   # side -> ("fk", angle, elbow) | ("ik", x, y)
    expr: str = "neutral"
    look: tuple = (0.0, 0.0)
    blink: float = 0.0                # 0 open .. 1 shut
    squash: float = 1.0               # upper body, about the hips (volume kept)
    front: bool = False               # the front drawing (the middle of a turn)
    view: str = "side"                # "side" | "three_quarter": the body turned toward the camera (a 2.5D shot)
    wound: bool = False
    scarf: float = 0.0                # the scarf tail's angle, degrees (follow-through)


@dataclass(frozen=True)
class Gait:
    stride: float           # body heights per cycle (two steps)
    stance: tuple           # share of the cycle each foot is planted (L, R)
    offset: tuple = (0.0, 0.5)
    lift: float = 0.07
    hip: float = 0.43
    bob: float = 0.0
    lean: float = 4.0
    swing: float = 24.0
    elbow: float = 12.0
    dip: float = 0.0        # extra hip drop while the injured foot is planted (limp)
    strike: float = 16.0    # heel strike: the toe up (degrees) as the foot lands, rolling down onto the sole
    toe_off: float = 28.0   # toe-off: the heel rises (degrees) as the foot leaves, rolling over the toes
    sway: float = 2.0       # torso pitch wave, twice a cycle (degrees)


WALK = Gait(0.62, (0.64, 0.64), lift=0.06, hip=0.435, lean=4, swing=26, elbow=14)
RUN = Gait(0.86, (0.38, 0.38), lift=0.16, hip=0.415, bob=0.04, lean=15, swing=48, elbow=82, strike=0.0, toe_off=34.0,
           sway=3.0)
LIMP = Gait(0.40, (0.72, 0.46), lift=0.045, hip=0.425, lean=9, swing=8, elbow=24, dip=0.03, strike=8.0, toe_off=14.0,
            sway=1.0)
HEEL = (-0.045 * B, ANKLE)   # the heel's ground point, in the foot's own frame (forward, down) from the ankle
TOE = (0.10 * B, ANKLE)      # the toes' ground point
ROLL = (0.16, 0.22)          # share of the stance spent on the heel strike and on the toe-off


def roll_ankle(pivot: tuple, local: tuple, pitch: float, f: int) -> tuple:
    """Where the ankle is when the foot pivots on one of its ground points by ``pitch`` (toe down positive)."""
    a = math.radians(pitch)
    vx, vy = -local[0], -local[1]
    rx, ry = vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
    return (pivot[0] + f * rx, pivot[1] + ry)


def _grounded(foot: tuple) -> bool:
    return foot[3] or foot[1] >= ANK - 0.03 * B


def gait_foot(g: Gait, i: int, phase: float, x_ref: float, f: int) -> tuple:
    """(x, y, pitch, contact) of foot ``i`` at gait ``phase``. The stance rolls heel -> sole -> toes: the heel lands
    with the toe up and the foot rolls down about the heel, the sole is planted flat (contact) at the hips' mid-stance
    position, then the heel rises about the toes; the swing carries the ankle from that toe-off to the next heel strike
    with a lift arc. Phase comes from the distance travelled, so speed changes never slide a foot."""
    s_px = g.stride * B
    beta = g.stance[i]
    phi = phase + g.offset[i]
    n = math.floor(phi)
    u = phi - n

    def plant(k):
        return x_ref + f * (k + beta / 2 - g.offset[i]) * s_px

    def strike_pose(k, r):  # r 0..1 through the heel strike
        x = plant(k)
        a = -g.strike * (1 - ease(r))
        return roll_ankle((x + f * HEEL[0], GROUND), HEEL, a, f) + (a,)

    def toe_pose(k, r):  # r 0..1 through the toe-off
        x = plant(k)
        a = g.toe_off * ease(r)
        return roll_ankle((x + f * TOE[0], GROUND), TOE, a, f) + (a,)

    hs, to = ROLL
    if u < beta:
        r = u / beta
        if r < hs and g.strike:
            x, y, a = strike_pose(n, r / hs)
            return (x, y, a, False)
        if r > 1 - to and g.toe_off:
            x, y, a = toe_pose(n, (r - (1 - to)) / to)
            return (x, y, a, False)
        return (plant(n), ANK, 0.0, True)
    sw = (u - beta) / (1 - beta)
    x0, y0, a0 = toe_pose(n, 1.0) if g.toe_off else (plant(n), ANK, 0.0)
    x1, y1, a1 = strike_pose(n + 1, 0.0) if g.strike else (plant(n + 1), ANK, 0.0)
    e = ease(sw)
    x = lerp(x0, x1, e)
    y = lerp(y0, y1, e) - g.lift * B * math.sin(math.pi * sw)
    pitch = lerp(a0, a1, ease(min(1.0, sw * 1.6)))
    return (x, y, pitch, False)


def gait_hip_height(g: Gait, phase: float, feet: dict) -> float:
    want = g.hip
    if g.bob:
        want += g.bob * (0.5 + 0.5 * math.cos(4 * math.pi * (phase - (g.stance[0] + 0.5) / 2)))
    if g.dip and feet[INJURED][3]:
        want -= g.dip
    return GROUND - want * B


def reach_clamp(hip: tuple, feet: dict) -> tuple:
    """Lower the hips until every planted foot is reachable (the hips' natural bob comes out of this)."""
    y = hip[1]
    for side in SIDES:
        fx, fy, _, contact = feet[side]
        if _grounded(feet[side]):
            dx = fx - hip[0]
            y = max(y, fy - math.sqrt(max(0.0, REACH * REACH - dx * dx)))
    return (hip[0], y)


# --- locomotion segments -------------------------------------------------------------------------------------------------
@dataclass
class Loco:
    g: Gait
    f: int
    t0: float
    t1: float
    speed: object            # callable (t, phase) -> px/s (>= 0)
    x0: float                # hip x at t0
    phase0: float = 0.0
    entry: dict | None = None  # feet before the segment (swing feet blend in)
    entry_arms: tuple | None = None  # (angle, elbow) the arms come from
    blend: float = 0.18
    settle: float = 0.22

    def __post_init__(self):
        # integrated at 240 Hz; the speed may depend on the phase (a limp is slower on the injured foot)
        n = int(math.ceil((self.t1 - self.t0) * 240)) + 2
        self.x_ref = self.x0 - self.f * self.phase0 * self.g.stride * B
        ts = self.t0 + np.arange(n) / 240.0
        xs = np.empty(n)
        x = self.x0
        for i, t in enumerate(ts):
            xs[i] = x
            ph = (x - self.x_ref) * self.f / (self.g.stride * B)
            x += self.f * max(0.0, self.speed(t, ph)) / 240.0
        self._ts, self._xs = ts, xs

    def x(self, t: float) -> float:
        return float(np.interp(min(t, self.t1), self._ts, self._xs))

    def phase(self, t: float) -> float:
        return (self.x(t) - self.x_ref) * self.f / (self.g.stride * B)

    def raw_feet(self, t: float) -> dict:
        p = self.phase(t)
        return {s: gait_foot(self.g, i, p, self.x_ref, self.f) for i, s in enumerate(SIDES)}

    def feet(self, t: float) -> dict:
        if t > self.t1:
            return self._settled(t)
        feet = self.raw_feet(t)
        if self.entry and t < self.t0 + self.blend:
            r = (t - self.t0) / self.blend
            u = ease(r)
            start = self.raw_feet(self.t0)
            for s in SIDES:
                e = self.entry[s]
                if not feet[s][3] or math.dist(e[:2], start[s][:2]) > 1.0:
                    # a foot the gait wants elsewhere steps there (lifts and replants), it never slides
                    arc = 0.05 * B * math.sin(math.pi * r) if feet[s][3] else 0.0
                    feet[s] = (lerp(e[0], feet[s][0], u), lerp(e[1], feet[s][1], u) - arc, lerp(e[2], feet[s][2], u),
                               False)
        return feet

    def _settled(self, t: float) -> dict:
        end = self.feet(self.t1)
        hx = self.x(self.t1)
        u = ease((t - self.t1) / self.settle)
        out = {}
        for k, s in enumerate(SIDES):
            x, y, p, c = end[s]
            if c:
                out[s] = end[s]
                continue
            other = end[SIDES[1 - k]][0]
            tx = hx + self.f * 0.07 * B * (1 if (x - other) * self.f > 0 else -1)
            arc = 0.04 * B * math.sin(math.pi * u)
            out[s] = (lerp(x, tx, u), lerp(y, ANK, u) - arc, lerp(p, 0.0, u), u >= 1.0)
        return out

    def pose(self, t: float, **kw) -> Pose:
        feet = self.feet(t)
        tt = min(t, self.t1)
        p = self.phase(tt)
        hx = self.x(tt)
        moving = t <= self.t1
        want = gait_hip_height(self.g, p, feet) if moving else GROUND - STAND * B
        if not moving:
            want = lerp(gait_hip_height(self.g, p, feet), want, ease((t - self.t1) / 0.35))
        hip = reach_clamp((hx, want), feet)
        lean = self.g.lean if moving else lerp(self.g.lean, 2.0, ease((t - self.t1) / 0.35))
        if moving:
            lean += self.g.sway * math.sin(4 * math.pi * (p + 0.1))
        if self.g.dip and feet[INJURED][3]:
            lean += 6.0
        arms = {}
        s_px = self.g.stride * B
        lag = p - 0.07  # the arms follow the legs a little late (overlap), never in lock-step
        for k, s in enumerate(SIDES):
            fl = gait_foot(self.g, k, lag, self.x_ref, self.f)[0]
            d = (fl - (self.x_ref + self.f * lag * s_px)) * self.f / (s_px / 2)
            a = -self.g.swing * max(-1.2, min(1.2, d)) * (1.0 if moving else 1 - ease((t - self.t1) / 0.4))
            e = self.g.elbow + 0.45 * max(0.0, a)
            if self.entry_arms and t < self.t0 + 0.3:
                u = ease((t - self.t0) / 0.3)
                a, e = lerp(self.entry_arms[0], a, u), lerp(self.entry_arms[1], e, u)
            arms[s] = ("fk", a, e)
        return Pose(self.f, hip, lean, feet=feet, arms=arms, **kw)


def entry_phase(g: Gait, f: int, hip_x: float, feet: dict) -> float:
    """The phase at which a gait can start from standing feet: one planted foot keeps its spot (the one closest to its
    mid-stance); the other, if the gait has it in the air, blends in."""
    best = None
    for i, s in enumerate(SIDES):
        beta = g.stance[i]
        u = beta / 2 - f * (feet[s][0] - hip_x) / (g.stride * B)
        if 0 <= u < beta:
            score = abs(u - beta / 2)
            if best is None or score < best[0]:
                best = (score, u - g.offset[i])
    if best is None:
        raise ValueError("no planted foot is within a stance of the hips")
    return best[1]


# --- keyed segments ------------------------------------------------------------------------------------------------------
@dataclass
class Key:
    t: float
    hip: tuple
    torso: float
    head: float = 0.0
    feet: dict = field(default_factory=dict)   # side -> ("abs", x, y, pitch, contact) | ("rel", dx, dy, pitch, contact)
    arms: dict = field(default_factory=dict)
    squash: float = 1.0
    linear: bool = False                         # linear in time (ballistic x), else eased
    hip_fn: object = None                        # optional t -> (x, y) until the next key


def _foot_abs(k: Key, s: str) -> tuple:
    kind, a, b, p, c = k.feet[s]
    return (k.hip[0] + a, k.hip[1] + b, p, c) if kind == "rel" else (a, b, p, c)


def keyed_pose(keys: list[Key], t: float, facing: int, shoulder_of) -> Pose:
    if t <= keys[0].t:
        k0 = k1 = keys[0]
    else:
        k0, k1 = keys[-1], keys[-1]
        for a, b in zip(keys, keys[1:]):
            if a.t <= t <= b.t:
                k0, k1 = a, b
                break
    span = (k1.t - k0.t) or 1.0
    r = min(1.0, max(0.0, (t - k0.t) / span))
    u = r if k0.linear else ease(r)
    hip = k0.hip_fn(t) if (k0.hip_fn and k0 is not k1) else lerp2(k0.hip, k1.hip, u)
    feet = {}
    for s in SIDES:
        a, b = k0.feet[s], k1.feet[s]
        if a[0] == b[0] == "rel":
            feet[s] = (hip[0] + lerp(a[1], b[1], u), hip[1] + lerp(a[2], b[2], u), lerp(a[3], b[3], u), a[4] and b[4])
        else:
            pa, pb = _foot_abs(k0, s), _foot_abs(k1, s)
            feet[s] = (lerp(pa[0], pb[0], u), lerp(pa[1], pb[1], u), lerp(pa[2], pb[2], u), pa[3] and pb[3])
    pose = Pose(facing, hip, lerp(k0.torso, k1.torso, u), lerp(k0.head, k1.head, u), feet=feet,
                squash=lerp(k0.squash, k1.squash, u))
    sh = shoulder_of(pose)
    for s in SIDES:
        a, b = k0.arms[s], k1.arms[s]
        if a[0] == b[0] == "fk":
            pose.arms[s] = ("fk", lerp(a[1], b[1], u), lerp(a[2], b[2], u))
        else:
            ha = fk_arm(sh, facing, a[1], a[2])[1] if a[0] == "fk" else (a[1], a[2])
            hb = fk_arm(sh, facing, b[1], b[2])[1] if b[0] == "fk" else (b[1], b[2])
            pose.arms[s] = ("ik",) + lerp2(ha, hb, u)
    return pose


# --- the skeleton --------------------------------------------------------------------------------------------------------
def _dir(angle: float, f: int) -> tuple:
    a = math.radians(angle)
    return (f * math.sin(a), -math.cos(a))


def near_side(f: int) -> str:
    """The side nearer the camera in a side or three-quarter drawing."""
    return "L" if f > 0 else "R"


def shoulder_of(p: Pose) -> tuple:
    d = _dir(p.torso, p.facing)
    return (p.hip[0] + d[0] * (TORSO - 0.03 * B) * p.squash, p.hip[1] + d[1] * (TORSO - 0.03 * B) * p.squash)


def skeleton(p: Pose) -> dict:
    """World positions of every joint (px). The upper body squashes about the hips; the legs are solved to the feet."""
    f = p.facing
    d = _dir(p.torso, f)
    sq = p.squash
    neck = (p.hip[0] + d[0] * TORSO * sq, p.hip[1] + d[1] * TORSO * sq)
    hd = _dir(p.torso + p.head, f)
    head = (neck[0] + hd[0] * NECK * sq, neck[1] + hd[1] * NECK * sq)
    sh = shoulder_of(p)
    j = {"hip": p.hip, "neck": neck, "head": head, "shoulder": sh, "head_angle": p.torso + p.head}
    tq = p.view == "three_quarter" and not p.front
    near = near_side(f)
    for k, s in enumerate(SIDES):
        fx, fy, pitch, contact = p.feet[s]
        side = (-1 if p.feet[s][0] <= p.feet[SIDES[1 - k]][0] else 1) if p.front else 0
        hip = (p.hip[0] + side * FRONT_HIP, p.hip[1]) if p.front else p.hip
        if tq:
            # the near side sits behind the body's middle, the far side ahead of it and a little higher (further away)
            back = 0.0 if s == near else TQ_BACK
            hip = (p.hip[0] + (-f if s == near else f) * TQ_HIP, p.hip[1] - back)
            fy -= back
        knee, ankle = ik2(hip, (fx, fy), THIGH, SHIN, side if p.front else f)  # front: knees bow out
        j["hip_" + s], j["knee_" + s], j["ankle_" + s], j["pitch_" + s] = hip, knee, ankle, pitch
        arm = p.arms[s]
        if tq:
            shs = (sh[0] + (-f if s == near else f) * TQ_SHOULDER, sh[1] - (0.0 if s == near else TQ_BACK))
            j["shoulder_" + s] = shs
            if arm[0] == "fk":
                elbow, hand = fk_arm(shs, f, arm[1], arm[2])
            else:
                elbow, hand = ik2(shs, (arm[1], arm[2]), UPPER, FORE, -f)
        elif p.front:
            shs = (sh[0] + side * 0.10 * B, sh[1] + 0.02 * B)
            elbow = (shs[0] + side * 0.05 * B, shs[1] + UPPER * 0.95)
            hand = (elbow[0] + side * 0.01 * B, elbow[1] + FORE * 0.98)
            j["shoulder_" + s] = shs
        elif arm[0] == "fk":
            elbow, hand = fk_arm(sh, f, arm[1], arm[2])
        else:
            elbow, hand = ik2(sh, (arm[1], arm[2]), UPPER, FORE, -f)
        j["elbow_" + s], j["hand_" + s] = elbow, hand
    return j


# --- the scene: one hero, eighteen seconds ------------------------------------------------------------------------------
@dataclass
class Scene:
    duration: float
    segments: list            # (t0, t1, kind, obj)
    events: list              # (t, kind, x)
    expr: list                # (t, expr, look)
    blinks: list
    wound_at: float
    turn: tuple               # (t0, t1)
    scarf: np.ndarray = None  # 240 Hz table


def _speed_walk(t, _ph=0.0):
    return 0.66 * B if t < 3.0 else 0.66 * B * max(0.0, 1 - (t - 3.0) / 0.35)


@lru_cache(maxsize=1)
def scene() -> Scene:
    walk = Loco(WALK, 1, 0.0, 3.35, _speed_walk, -190.0)
    stand1 = walk.feet(3.35 + walk.settle + 0.01)
    x1 = walk.x(3.35)
    hip_stand = (x1, GROUND - 0.435 * B)
    ph = entry_phase(RUN, 1, x1, stand1)
    t_run = 4.55
    run = Loco(RUN, 1, t_run, 6.4, lambda t, _ph: 1.05 * B * ease((t - t_run) / 0.5), x1, phase0=ph, entry=stand1, entry_arms=(-35.0, 40.0))
    # the takeoff: the first moment after 5.2 s when a foot ends its stance (the push-off)
    tj, lead, trail = None, None, None
    for k in range(int(5.2 * 240), int(6.4 * 240)):
        t = k / 240.0
        a, b = run.feet(t), run.feet(t + 1 / 240.0)
        for i, s in enumerate(SIDES):
            if a[s][3] and not b[s][3]:
                tj, trail, lead = t, s, SIDES[1 - i]
                break
        if tj:
            break
    run.t1 = tj
    pre = run.pose(tj)
    vj = run.speed(tj, run.phase(tj))
    hx, hy = pre.hip
    T, rise = 0.5, 0.24 * B
    t_land = tj + T

    def flight(t, hx=hx, hy=hy):
        tau = t - tj
        return (hx + vj * tau, hy - 4 * rise * (tau / T) * (1 - tau / T))

    xl = hx + vj * T
    land_foot = xl + 0.17 * B
    xi = xl + 0.80 * B          # hips at the impact
    hand_x = xi + 0.27 * B   # under the shoulders, beside the head (never across the face)
    pf = pre.feet

    def ab(x, y, p=0.0, c=False):
        return ("abs", x, y, p, c)

    def rel(x, y, p=0.0, c=False):
        return ("rel", x, y, p, c)

    fk = lambda a, e: ("fk", a, e)  # noqa: E731
    run_arms = {s: pre.arms[s] for s in SIDES}
    lie_y = GROUND - 0.10 * B
    k = [
        Key(tj, pre.hip, RUN.lean, 0, {s: ab(*pf[s]) for s in SIDES}, run_arms, hip_fn=flight, linear=True),
        Key(tj + 0.14, flight(tj + 0.14), 8, -6, {lead: rel(0.16 * B, 0.20 * B, -10), trail: rel(-0.20 * B, 0.30 * B, 30)},
            {s: fk(60 if s == lead else -40, 30) for s in SIDES}, squash=1.06, hip_fn=flight, linear=True),
        Key(tj + 0.36, flight(tj + 0.36), 6, -4, {lead: rel(0.24 * B, 0.36 * B, -15), trail: rel(-0.12 * B, 0.28 * B, 20)},
            {s: fk(110, 20) for s in SIDES}, squash=1.04, hip_fn=flight, linear=True),
        Key(t_land, flight(t_land), 4, 0, {lead: ab(land_foot, ANK, 0, True), trail: rel(-0.16 * B, 0.30 * B, 25)},
            {s: fk(80, 30) for s in SIDES}, squash=0.92),
        # the stumble: the trailing toe catches the snow behind
        Key(t_land + 0.14, (xl + 0.22 * B, GROUND - 0.36 * B), 32, 6,
            {lead: ab(land_foot, ANK, 0, True), trail: ab(xl + 0.02 * B, GROUND - 0.06 * B, 35, True)},
            {s: fk(40, 40) for s in SIDES}, squash=0.96),
        Key(t_land + 0.36, (xl + 0.55 * B, GROUND - 0.24 * B), 62, -10,
            {lead: ab(land_foot - 0.02 * B, GROUND - 0.10 * B, 40), trail: ab(xl + 0.10 * B, GROUND - 0.12 * B, 50)},
            {s: fk(92, 12) for s in SIDES}),
        # the impact: hands slap the snow ahead, the body lands on its belly
        Key(t_land + 0.58, (xi, lie_y), 80, -18,
            {lead: ab(xi - 0.40 * B, GROUND - 0.07 * B, 75), trail: ab(xi - 0.38 * B, GROUND - 0.06 * B, 75)},
            {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), GROUND - 0.03 * B) for s in SIDES}, squash=0.86),
        Key(t_land + 0.72, (xi, lie_y - 0.03 * B), 80, -22,
            {lead: ab(xi - 0.40 * B, GROUND - 0.07 * B, 75), trail: ab(xi - 0.38 * B, GROUND - 0.06 * B, 75)},
            {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), GROUND - 0.03 * B) for s in SIDES}, squash=1.03),
        Key(t_land + 0.88, (xi, lie_y), 80, -12,
            {lead: ab(xi - 0.40 * B, GROUND - 0.07 * B, 75), trail: ab(xi - 0.38 * B, GROUND - 0.06 * B, 75)},
            {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), GROUND - 0.03 * B) for s in SIDES}),
        Key(t_land + 1.55, (xi, lie_y), 80, -32,
            {lead: ab(xi - 0.40 * B, GROUND - 0.07 * B, 75), trail: ab(xi - 0.38 * B, GROUND - 0.06 * B, 75)},
            {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), GROUND - 0.03 * B) for s in SIDES}),
        # push up onto the knees, hands planted
        Key(t_land + 2.15, (xi - 0.06 * B, GROUND - 0.24 * B), 52, -20,
            {lead: ab(xi - 0.40 * B, GROUND - 0.07 * B, 75), trail: ab(xi - 0.38 * B, GROUND - 0.06 * B, 75)},
            {s: ("ik", hand_x + (0.04 * B if s == lead else -0.02 * B), GROUND - 0.03 * B) for s in SIDES}),
        # kneel up: the hands leave the snow, one foot comes forward
        Key(t_land + 2.75, (xi - 0.14 * B, GROUND - 0.25 * B), 10, 10,
            {lead: ab(xi + 0.10 * B, ANK, 0, True), trail: ab(xi - 0.40 * B, GROUND - 0.06 * B, 75)},
            {s: fk(25, 30) for s in SIDES}),
        # stand up over the front foot, the back foot steps in
        Key(t_land + 3.35, (xi - 0.02 * B, GROUND - 0.425 * B), 6, 6,
            {lead: ab(xi + 0.10 * B, ANK, 0, True), trail: ab(xi - 0.12 * B, ANK, 0, True)},
            {s: fk(10, 15) for s in SIDES}),
        # the knee hurts: bend, look at it, a hand on it
        Key(t_land + 3.85, (xi - 0.02 * B, GROUND - 0.41 * B), 26, 28,
            {lead: ab(xi + 0.10 * B, ANK, 0, True), trail: ab(xi - 0.12 * B, ANK, 0, True)},
            {INJURED: ("ik", xi + (0.06 if lead == INJURED else -0.02) * B, GROUND - 0.25 * B),
             SIDES[1 - SIDES.index(INJURED)]: fk(-20, 30)}),
        Key(t_land + 4.45, (xi - 0.02 * B, GROUND - 0.415 * B), 18, 18,
            {lead: ab(xi + 0.10 * B, ANK, 0, True), trail: ab(xi - 0.12 * B, ANK, 0, True)},
            {INJURED: ("ik", xi + (0.06 if lead == INJURED else -0.02) * B, GROUND - 0.25 * B),
             SIDES[1 - SIDES.index(INJURED)]: fk(-10, 20)}),
    ]
    # the turn: anticipation on the side drawing, the front drawing while the feet step round, the other side
    t_turn0 = k[-1].t + 0.05
    t_turn1 = t_turn0 + 0.55
    before_turn = keyed_pose(k, k[-1].t, 1, shoulder_of)
    hip2 = before_turn.hip
    # each foot steps to its own side of the hips (the one already on the left stays left: the legs never cross)
    left = min(SIDES, key=lambda s: before_turn.feet[s][0])
    stand2 = {s: (hip2[0] + (-1 if s == left else 1) * 0.075 * B, ANK, 0.0, True) for s in SIDES}
    limp_t0 = t_turn1 + 0.05
    ph2 = entry_phase(LIMP, -1, hip2[0], stand2)
    duration = 15.0

    def limp_speed(t, ph, base=0.30 * B):
        # slower while the injured foot carries the weight (an antalgic gait)
        planted = gait_foot(LIMP, SIDES.index(INJURED), ph, 0.0, -1)[3]
        return base * (0.55 if planted else 1.0) * min(1.0, 0.15 + (t - limp_t0) / 0.6)

    limp = Loco(LIMP, -1, limp_t0, duration, limp_speed, hip2[0], phase0=ph2, entry=stand2, blend=0.3, entry_arms=(10.0, 20.0))

    segments = [
        (0.0, 3.35 + 0.35, "loco", walk),
        (3.35 + 0.35, t_run, "idle", (hip_stand, stand1)),
        (t_run, tj, "loco", run),
        (tj, k[-1].t, "keys", k),
        (k[-1].t, limp_t0, "turn", (before_turn, t_turn0, t_turn1, stand2)),
        (limp_t0, duration, "loco", limp),
    ]
    events = [(tj, "takeoff", hx), (t_land, "land", xl), (t_land + 0.58, "impact", xi)]
    expr = [(0.0, "neutral", (0.3, 0.0)), (3.2, "neutral", (0.4, -0.5)), (3.7, "happy", (0.5, -0.6)),
            (4.25, "eager", (0.8, 0.0)), (tj + 0.1, "happy", (0.6, -0.2)), (t_land + 0.05, "shock", (0.4, 0.4)),
            (t_land + 0.55, "dazed", (0.0, 0.0)), (t_land + 1.6, "pain", (0.6, 0.0)),
            (t_land + 3.4, "pain", (0.3, 0.8)), (t_turn0, "pain", (0.6, 0.0)), (limp_t0 + 1.5, "brave", (0.6, 0.0))]
    blinks = [1.3, 2.7, 4.1, t_land + 1.1, t_land + 1.35, t_land + 2.9, limp_t0 + 0.9, limp_t0 + 3.4, limp_t0 + 5.2]
    sc = Scene(duration, segments, events, expr, blinks, wound_at=t_land + 0.58, turn=(t_turn0, t_turn1))
    sc.scarf = _scarf_table(sc)
    return sc


def _raw_pose(sc: Scene, t: float) -> Pose:
    for t0, t1, kind, obj in sc.segments:
        if t0 <= t < t1 or (t >= t1 and (t0, t1, kind, obj) == sc.segments[-1]):
            break
    if kind == "loco":
        return obj.pose(t)
    if kind == "keys":
        return keyed_pose(obj, t, 1, shoulder_of)
    if kind == "idle":
        hip, feet = obj
        breath = 0.006 * B * math.sin(2 * math.pi * (t - t0) / 2.2)
        u = ease((t - (t1 - 0.35)) / 0.35)  # the anticipation: a crouch before the run
        hip_y = hip[1] + breath + 0.06 * B * u
        p = Pose(1, (hip[0], hip_y), lerp(2.0, 22.0, u), lerp(-12.0, -4.0, ease((t - t0) / 0.5)), feet=dict(feet))
        p.hip = reach_clamp(p.hip, p.feet)
        p.arms = {s: ("fk", lerp(0.0, -35.0, u), lerp(12.0, 40.0, u)) for s in SIDES}
        return p
    if kind == "turn":
        before, ta, tb, after = obj
        p = replace(before, feet=dict(before.feet), arms=dict(before.arms))
        if t < ta:
            return p
        r = (t - ta) / (tb - ta)
        if r < 0.18:  # anticipation: sink and lean back on the side drawing
            u = ease(r / 0.18)
            p.squash = 1.0 - 0.07 * u
            p.torso = lerp(before.torso, 4.0, u)
            p.hip = (p.hip[0], p.hip[1] + 0.02 * B * u)
            return p
        if r < 0.68:  # the front drawing; the feet step round to their new places
            u = ease((r - 0.18) / 0.5)
            feet = {}
            for s in SIDES:
                a, b = before.feet[s], after[s]
                lift = 0.05 * B * math.sin(math.pi * u)
                feet[s] = (lerp(a[0], b[0], u), lerp(a[1], b[1], u) - lift, 0.0, u >= 1.0)
            p.feet, p.front, p.torso, p.head = feet, True, 0.0, 0.0
            p.hip = (p.hip[0], GROUND - 0.44 * B + 0.02 * B * (1 - u))  # legs nearly straight: no knock knees
            p.squash = 1.0 + 0.04 * math.sin(math.pi * u)
            return p
        u = ease((r - 0.68) / 0.32)  # the other side: overshoot a touch, settle
        p.facing, p.feet = -1, dict(after)
        p.torso, p.head = lerp(-4.0, 9.0, u), lerp(0.0, 6.0, u)
        p.squash = 1.0 + 0.03 * (1 - u)
        p.arms = {s: ("fk", lerp(4.0, 10.0, u), lerp(10.0, 20.0, u)) for s in SIDES}
        p.hip = reach_clamp((p.hip[0], GROUND - 0.425 * B), p.feet)
        return p
    raise ValueError(kind)


def _spring(targets: np.ndarray, k: float, c: float) -> np.ndarray:
    ang, w = float(targets[0]), 0.0
    out = np.empty(len(targets))
    for i, tgt in enumerate(targets):
        w += (k * (tgt - ang) - c * w) / 240.0
        ang += w / 240.0
        out[i] = ang
    return out


def _scarf_table(sc: Scene) -> np.ndarray:
    """Follow-through (240 Hz from t = 0): row 0 the scarf tail, a damped spring on the hips' horizontal speed; row 1 the
    head's nod, a stiffer spring on their vertical speed (the head lags each step's dip, so the walk breathes)."""
    n = int(sc.duration * 240) + 2
    hips = np.array([_raw_pose(sc, i / 240.0).hip for i in range(n)])
    vx = np.gradient(hips[:, 0]) * 240.0
    vy = np.gradient(hips[:, 1]) * 240.0
    scarf = _spring(np.clip(vx / B * 38.0, -70, 70), 70.0, 9.0)
    nod = _spring(np.clip(vy / B * 9.0, -7, 7), 160.0, 14.0)
    return np.stack([scarf, nod])


def pose_at(t: float) -> Pose:
    sc = scene()
    p = _raw_pose(sc, t)
    expr, look = sc.expr[0][1], sc.expr[0][2]
    for te, e, lk in sc.expr:
        if t >= te:
            expr, look = e, lk
    p.expr, p.look = expr, look
    p.blink = max([max(0.0, 1 - abs(t - b) / 0.07) for b in sc.blinks] + [0.0])
    if expr == "dazed":
        p.blink = max(p.blink, 0.45)
    p.wound = t >= sc.wound_at
    grid = np.arange(sc.scarf.shape[1]) / 240.0
    p.scarf = float(np.interp(t, grid, sc.scarf[0]))
    if not p.front:
        p.head += float(np.interp(t, grid, sc.scarf[1]))
    return p


# --- drawing -----------------------------------------------------------------------------------------------------------
def _capsule(p0, p1, r0, r1, n=10) -> list:
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy) or 1e-6
    ux, uy = dx / d, dy / d
    base = math.atan2(uy, ux)
    pts = []
    for k in range(n + 1):
        a = base - math.pi / 2 + math.pi * k / n
        pts.append((p1[0] + math.cos(a) * r1, p1[1] + math.sin(a) * r1))
    for k in range(n + 1):
        a = base + math.pi / 2 + math.pi * k / n
        pts.append((p0[0] + math.cos(a) * r0, p0[1] + math.sin(a) * r0))
    return pts


def _shade(c, k=0.78):
    return tuple(int(v * k) for v in c)


class Canvas:
    """The character's own layer, supersampled; world px -> layer px."""

    def __init__(self, x0: int, y0: int, w: int, h: int):
        self.x0, self.y0 = x0, y0
        self.img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def p(self, q):
        return ((q[0] - self.x0) * SS, (q[1] - self.y0) * SS)

    def caps(self, segs, color, width=LINE, shade=None):
        """Segments [(p0, p1, r0, r1)] as one shape: all outlines first, then all fills (no seam at the joints)."""
        for p0, p1, r0, r1 in segs:
            self.d.polygon(_capsule(self.p(p0), self.p(p1), (r0 + width) * SS, (r1 + width) * SS), fill=INK)
        for p0, p1, r0, r1 in segs:
            self.d.polygon(_capsule(self.p(p0), self.p(p1), r0 * SS, r1 * SS), fill=color)
        if shade:
            lx, ly = shade
            for p0, p1, r0, r1 in segs:
                o0 = (p0[0] + lx * r0 * 0.45, p0[1] + ly * r0 * 0.45)
                o1 = (p1[0] + lx * r1 * 0.45, p1[1] + ly * r1 * 0.45)
                self.d.polygon(_capsule(self.p(o0), self.p(o1), r0 * 0.5 * SS, r1 * 0.5 * SS), fill=_shade(color, 0.86))

    def tex_caps(self, segs, sheet: "Sheet", far: bool, f: int, width=LINE):
        """Segments [(p0, p1, part)] as one ink shape whose fills are the painted parts of ``sheet``: each part's picture
        is carried by a similarity from its painted bone onto the rig's bone (mirrored for facing -1), so a limb bends over
        two bones and keeps its paint. Outlines first, then the fills, so the joints have no seam."""
        shapes = []
        for p0, p1, part in segs:
            r0, r1 = sheet.radii(part, p0, p1)
            shapes.append((p0, p1, r0, r1, part))
        for p0, p1, r0, r1, _ in shapes:
            self.d.polygon(_capsule(self.p(p0), self.p(p1), (r0 + width) * SS, (r1 + width) * SS), fill=INK)
        for p0, p1, r0, r1, part in shapes:
            mask = Image.new("L", self.img.size, 0)
            ImageDraw.Draw(mask).polygon(_capsule(self.p(p0), self.p(p1), r0 * SS, r1 * SS), fill=255)
            tex = sheet.warp(part, self.p(p0), self.p(p1), f, self.img.size)
            base = Image.new("RGBA", self.img.size, sheet.base[part] + (255,))
            base.alpha_composite(tex)
            if far:
                base = Image.merge("RGBA", [c.point(lambda v: int(v * 0.78)) for c in base.split()[:3]] + [base.split()[3]])
            self.img.paste(base, (0, 0), mask)

    def cut_parts(self, segs, sheet: "Sheet", far: bool, f: int):
        """Segments [(p0, p1, part)] drawn as the sheet's painted cut-outs, in order (a later part overlaps the joint)."""
        for p0, p1, part in segs:
            if part not in sheet.parts:
                continue
            layer = sheet.place(part, self.p(p0), self.p(p1), f, self.img.size)
            if far:
                r, g, b, a = layer.split()
                layer = Image.merge("RGBA", [c.point(lambda v: int(v * 0.8)) for c in (r, g, b)] + [a])
            self.img.alpha_composite(layer)

    def poly(self, pts, color, width=LINE):
        self.d.polygon([self.p(q) for q in pts], fill=color, outline=INK, width=max(1, int(width * SS)))

    def line(self, pts, width, color=INK):
        self.d.line([self.p(q) for q in pts], fill=color, width=max(1, int(width * SS)), joint="curve")

    def ellipse(self, c, rx, ry, color, width=LINE):
        x, y = self.p(c)
        self.d.ellipse([x - rx * SS, y - ry * SS, x + rx * SS, y + ry * SS], fill=color, outline=INK,
                       width=max(1, int(width * SS)) if width else 0)


def _local(origin, angle_deg, f, q):
    """A point of the head's own frame (x forward, y down, px) into the world."""
    a = math.radians(angle_deg)
    x, y = q[0] * f, q[1]
    return (origin[0] + x * math.cos(a) - y * math.sin(a) * f, origin[1] + x * math.sin(a) * f + y * math.cos(a))


class Sheet:
    """The painted parts of one character (the hybrid's route B): ``parts.json`` next to the head pictures names the
    source picture and, per part, the painted bone ``p0 -> p1`` (source px) and its half-widths ``r`` at both ends.
    The rig carries each part by a similarity from the painted bone onto its own bone, so the paint follows the bend."""

    PARTS = ("torso", "upper_arm", "fore_arm", "thigh", "shin")

    def __init__(self, folder: str, name: str = "parts.json"):
        spec = json.loads((Path(folder) / name).read_text(encoding="utf-8"))
        self.src = Image.open(Path(folder) / spec["source"]).convert("RGBA")
        self.mode = spec.get("mode", "fill")
        self.parts = {k: spec["parts"][k] for k in self.PARTS + ("foot",) if k in spec["parts"]}
        self.foot = tuple(spec.get("foot_rgb", SKIN))
        if self.mode == "cut":
            # every part is its own painted cut-out (the picture's alpha inside the part's region), carried whole: the
            # painting keeps its outline, the rig only moves it; widths scale with the figure (``height`` = crown to sole)
            self.k = B / float(spec["height"])
            self.cuts = {k: self._cut(q) for k, q in self.parts.items()}
            return
        # each part's own colour, under the paint where the picture has no pixels (the cut-out's edge)
        a = np.asarray(self.src)
        self.base = {}
        for k, q in self.parts.items():
            box = Image.new("L", self.src.size, 0)
            ImageDraw.Draw(box).polygon(_capsule(q["p0"], q["p1"], q["r"][0], q["r"][1]), fill=255)
            m = (np.asarray(box) > 0) & (a[:, :, 3] > 200)
            self.base[k] = tuple(int(v) for v in np.median(a[m][:, :3], axis=0)) if m.any() else SKIN

    def _cut(self, q: dict) -> tuple:
        mask = Image.new("L", self.src.size, 0)
        d = ImageDraw.Draw(mask)
        if "poly" in q:
            for poly in (q["poly"] if isinstance(q["poly"][0][0], (list, tuple)) else [q["poly"]]):
                d.polygon([tuple(v) for v in poly], fill=255)
        else:
            (x0, y0), (x1, y1) = q["p0"], q["p1"]
            ln = max(1e-6, math.hypot(x1 - x0, y1 - y0))
            e0, e1 = q.get("ext", (0, 0))
            ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
            d.polygon(_capsule((x0 - ux * e0, y0 - uy * e0), (x1 + ux * e1, y1 + uy * e1), q["r"][0], q["r"][1]), fill=255)
        a = self.src.copy()
        a.putalpha(Image.fromarray(np.minimum(np.asarray(a.getchannel("A")), np.asarray(mask))))
        box = a.getbbox() or (0, 0, 1, 1)
        return a.crop(box), box[:2]

    def place(self, part: str, c0: tuple, c1: tuple, f: int, size: tuple) -> Image.Image:
        """The part's cut-out on a layer of ``size``: its painted bone lands on ``c0 -> c1`` (layer px); along the bone
        it stretches to the rig's length, across it keeps the figure's scale; ``f`` < 0 mirrors."""
        q = self.parts[part]
        img, (ox, oy) = self.cuts[part]
        s0, s1 = np.array(q["p0"], float) - (ox, oy), np.array(q["p1"], float) - (ox, oy)
        c0, c1 = np.array(c0, float), np.array(c1, float)
        us = (s1 - s0) / max(1e-6, np.linalg.norm(s1 - s0))
        uc = (c1 - c0) / max(1e-6, np.linalg.norm(c1 - c0))
        ns, nc = np.array([-us[1], us[0]]), np.array([-uc[1], uc[0]]) * f
        kp = self.k * SS
        src = np.array([s0, s1, s0 + ns * 100.0])
        dst = np.array([c0, c1, c0 + nc * 100.0 * kp])
        coef = np.linalg.solve(np.c_[dst, np.ones(3)], src)
        a, d = coef[:, 0], coef[:, 1]
        return img.transform(size, Image.AFFINE, (a[0], a[1], a[2], d[0], d[1], d[2]), resample=Image.BICUBIC)

    def radii(self, part: str, p0: tuple, p1: tuple) -> tuple:
        """Half-widths of the part on the rig: the painted ones scaled with the bone, or ``rig_r`` (shares of B) when
        the picture's part is narrower than the rig's (a strip of paint is then stretched across)."""
        q = self.parts[part]
        if "rig_r" in q:
            return q["rig_r"][0] * B, q["rig_r"][1] * B
        k = math.dist(p0, p1) / max(1e-6, math.dist(q["p0"], q["p1"]))
        return q["r"][0] * k, q["r"][1] * k

    def warp(self, part: str, c0: tuple, c1: tuple, f: int, size: tuple) -> Image.Image:
        """The source picture mapped so the part's painted bone lands on ``c0 -> c1`` (layer px) and its painted
        half-width on the rig's; ``f`` < 0 mirrors."""
        q = self.parts[part]
        s0, s1 = q["p0"], q["p1"]
        ls, lc = max(1e-6, math.dist(s0, s1)), max(1e-6, math.dist(c0, c1))
        rs, rc = q["r"][0], self.radii(part, (0.0, 0.0), (lc / SS, 0.0))[0] * SS
        src = np.array([s0, s1, [s0[0] - (s1[1] - s0[1]) * rs / ls, s0[1] + (s1[0] - s0[0]) * rs / ls]], float)
        dst = np.array([c0, c1, [c0[0] - f * (c1[1] - c0[1]) * rc / lc, c0[1] + f * (c1[0] - c0[0]) * rc / lc]], float)
        A = np.c_[dst, np.ones(3)]
        coef = np.linalg.solve(A, src)  # layer (x, y, 1) -> source (x, y), per column
        a, d = coef[:, 0], coef[:, 1]
        return self.src.transform(size, Image.AFFINE, (a[0], a[1], a[2], d[0], d[1], d[2]), resample=Image.BILINEAR)


@lru_cache(maxsize=8)
def load_sheet(folder: str | None, view: str = "side") -> Sheet | None:
    """``parts_<view>.json`` (side, front, three_quarter) when the folder has one, else ``parts.json``."""
    if not folder:
        return None
    for name in (f"parts_{view}.json", "parts.json"):
        if (Path(folder) / name).exists():
            return Sheet(folder, name)
    return None


def draw_leg(cv: Canvas, j: dict, s: str, far: bool, f: int, wound: bool, sheet: Sheet | None = None):
    col, boot = (_shade(TROUSERS), _shade(BOOTS)) if far else (TROUSERS, BOOTS)
    hip, knee, ank = j["hip_" + s], j["knee_" + s], j["ankle_" + s]
    pitch = j["pitch_" + s]
    if sheet and sheet.mode == "cut":
        toe = _local(ank, pitch, f, (0.10 * B, 0.03 * B))
        cv.cut_parts([(hip, knee, "thigh"), (ank, toe, "foot"), (knee, ank, "shin")], sheet, far, f)
        return
    if sheet:
        cv.tex_caps([(hip, knee, "thigh"), (knee, ank, "shin")], sheet, far, f)
        boot = _shade(sheet.foot) if far else sheet.foot
    else:
        cv.caps([(hip, knee, 0.050 * B, 0.042 * B), (knee, ank, 0.042 * B, 0.034 * B)], col,
                shade=None if far else (-f * 0.4, 0.9))
    if wound and s == INJURED:
        # a torn trouser knee with a red scrape: data on the part, drawn at the knee
        kx, ky = knee
        tear = [(kx + dx * B, ky + dy * B) for dx, dy in
                ((-0.03, -0.02), (-0.01, -0.035), (0.012, -0.022), (0.03, -0.03), (0.034, 0.0), (0.02, 0.028),
                 (0.0, 0.018), (-0.025, 0.03))]
        cv.poly(tear, _shade(SKIN, 0.9) if far else SKIN, width=LINE * 0.6)
        for k in range(3):
            y = ky - 0.012 * B + k * 0.011 * B
            cv.line([(kx - 0.016 * B, y), (kx + 0.018 * B, y + 0.004 * B)], LINE * 0.55, SCRAPE)
    pitch = j["pitch_" + s]
    shoe = [(-0.045, -0.025), (0.02, -0.035), (0.075, -0.005), (0.11, 0.012), (0.108, 0.035), (-0.05, 0.035)]
    pts = [_local(ank, pitch, f, (x * B, y * B)) for x, y in shoe]
    cv.poly(pts, boot)


def draw_arm(cv: Canvas, j: dict, s: str, far: bool, f: int, skin: tuple = SKIN, sheet: Sheet | None = None,
             shoulder: str = "shoulder"):
    col = _shade(JACKET) if far else JACKET
    sh, el, ha = j[shoulder], j["elbow_" + s], j["hand_" + s]
    if sheet and sheet.mode == "cut":
        cv.cut_parts([(sh, el, "upper_arm"), (el, ha, "fore_arm")], sheet, far, f)
        return
    if sheet:
        cv.tex_caps([(sh, el, "upper_arm"), (el, ha, "fore_arm")], sheet, far, f)
    else:
        cv.caps([(sh, el, 0.040 * B, 0.035 * B), (el, ha, 0.035 * B, 0.029 * B)], col,
                shade=None if far else (-f * 0.4, 0.9))
    cv.ellipse(ha, 0.032 * B, 0.030 * B, _shade(skin) if far else skin)


def draw_torso(cv: Canvas, j: dict, f: int, front: bool, sheet: Sheet | None, view: str = "side"):
    hip, neck = j["hip"], j["neck"]
    if sheet and sheet.mode == "cut":
        cv.cut_parts([(hip, neck, "torso")], sheet, False, 1 if front else f)
        return
    if sheet:
        cv.tex_caps([(hip, neck, "torso")], sheet, False, 1 if front else f)
        return
    r0, r1 = (0.115 * B, 0.105 * B) if front else (0.104 * B, 0.096 * B) if view == "three_quarter" else \
        (0.088 * B, 0.080 * B)
    cv.caps([(hip, neck, r0, r1)], JACKET, shade=(0.5, 0.85) if front else (-f * 0.5, 0.85))
    cv.line([lerp2(hip, neck, 0.25 if front else 0.35), lerp2(hip, neck, 0.95)], LINE * 0.6)  # the zip


MOUTHS = {
    "neutral": "line", "happy": "smile", "eager": "grin", "shock": "o", "dazed": "wavy", "pain": "grimace",
    "brave": "grimace",
}
BROWS = {"neutral": 0, "happy": -8, "eager": 10, "shock": -22, "dazed": 4, "pain": 24, "brave": 14}


def draw_head(cv: Canvas, j: dict, p: Pose):
    f, c, ang = p.facing, j["head"], j["head_angle"]
    L = lambda x, y: _local(c, ang * 0.6, f, (x * B, y * B))  # noqa: E731
    hair_back = [L(-0.15, -0.02), L(-0.19, -0.09), L(-0.13, -0.12), L(-0.16, -0.17), L(-0.07, -0.16),
                 L(-0.06, -0.21), L(0.01, -0.165), L(0.06, -0.19), L(0.07, -0.13), L(-0.05, -0.05)]
    cv.poly(hair_back, HAIR)
    head = [L(0.145 * math.cos(a) + (0.02 if math.sin(a) > 0.2 and math.cos(a) > 0 else 0.0), 0.15 * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    cv.poly(head, SKIN)
    cv.ellipse(L(-0.035, 0.015), 0.025 * B, 0.035 * B, _shade(SKIN, 0.92), width=LINE * 0.7)
    fringe = [L(-0.12, -0.08), L(-0.08, -0.15), L(0.0, -0.17), L(0.06, -0.15), L(0.11, -0.11), L(0.05, -0.10),
              L(0.07, -0.13), L(0.0, -0.11), L(-0.03, -0.14), L(-0.06, -0.09)]
    cv.poly(fringe, HAIR, width=LINE * 0.8)
    # bulging eyes: the far one first, the near one overlapping it
    for ex, ey, rx, ry in ((0.105, -0.045, 0.048, 0.060), (0.045, -0.050, 0.058, 0.068)):
        ec = L(ex, ey)
        cv.ellipse(ec, rx * B, ry * B, WHITE, width=LINE * 0.8)
        lx, ly = p.look
        pc = L(ex + 0.016 * lx + 0.01, ey + 0.02 * ly)
        cv.ellipse(pc, 0.014 * B, 0.016 * B, INK, width=0)
        if p.blink > 0.02:
            lid = [L(ex + rx * math.cos(a), ey + ry * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 12)]
            yb = ey - ry + 2 * ry * p.blink
            lid += [L(ex + rx, yb), L(ex - rx, yb)]
            cv.poly(lid, SKIN, width=LINE * 0.7)
        tilt = BROWS.get(p.expr, 0)
        bx = ex
        cv.line([L(bx - 0.04, ey - ry - 0.015 + 0.0006 * tilt), L(bx + 0.04, ey - ry - 0.015 - 0.0006 * tilt)],
                LINE * 1.3)
    cv.ellipse(L(0.15, 0.025), 0.042 * B, 0.034 * B, _shade(SKIN, 0.95), width=LINE * 0.9)  # the nose
    m = MOUTHS.get(p.expr, "line")
    mx, my = 0.085, 0.085
    if m == "line":
        cv.line([L(mx - 0.035, my), L(mx + 0.03, my - 0.004)], LINE * 0.9)
    elif m == "smile":
        cv.line([L(mx - 0.04, my - 0.012), L(mx - 0.01, my + 0.012), L(mx + 0.035, my - 0.006)], LINE * 0.9)
    elif m == "grin":
        cv.poly([L(mx - 0.045, my - 0.012), L(mx + 0.04, my - 0.012), L(mx + 0.02, my + 0.03), L(mx - 0.03, my + 0.03)],
                (120, 30, 40))
        cv.poly([L(mx - 0.04, my - 0.01), L(mx + 0.035, my - 0.01), L(mx + 0.03, my + 0.005), L(mx - 0.035, my + 0.005)],
                WHITE, width=LINE * 0.5)
    elif m == "o":
        cv.ellipse(L(mx, my + 0.01), 0.026 * B, 0.034 * B, (110, 28, 36), width=LINE * 0.9)
    elif m == "wavy":
        cv.line([L(mx - 0.035, my), L(mx - 0.015, my + 0.01), L(mx + 0.005, my), L(mx + 0.03, my + 0.01)], LINE * 0.8)
    elif m == "grimace":
        cv.poly([L(mx - 0.04, my - 0.008), L(mx + 0.035, my - 0.014), L(mx + 0.035, my + 0.016),
                 L(mx - 0.04, my + 0.02)], WHITE, width=LINE * 0.8)
        cv.line([L(mx - 0.04, my + 0.004), L(mx + 0.035, my + 0.0)], LINE * 0.5)


# the painted head sheet: one picture per expression, all of the same face (the hybrid's route B)
SHEET_FOR = {"neutral": "happy", "happy": "happy", "eager": "happy", "shock": "scared", "dazed": "scared",
             "pain": "angry", "brave": "angry"}
HEAD_H = 0.42 * B              # crown to the bottom of the neck stump


VIEWS = ("side", "three_quarter", "front")


@lru_cache(maxsize=4)
def load_heads(folder: str | None) -> dict | None:
    """``head_<name>.png`` (RGBA, the neck stump at the bottom centre, drawn facing right) for the names in SHEET_FOR,
    plus ``head_<name>_<view>.png`` per drawing when the sheet has them (keys ``name`` and ``name/view``); None = the
    head is drawn by code. The names come from SHEET_FOR and from the files themselves (a sheet may name more)."""
    if not folder:
        return None
    heads = {}
    for path in sorted(Path(folder).glob("head_*.png")):
        stem = path.stem[5:]
        for v in VIEWS:
            if stem.endswith("_" + v):
                heads[stem[:-len(v) - 1] + "/" + v] = Image.open(path).convert("RGBA")
                break
        else:
            heads[stem] = Image.open(path).convert("RGBA")
    return heads or None


def head_picture(heads: dict, expr: str, view: str) -> Image.Image:
    """The expression's picture for this drawing: its own view, else the plain one, else any of the face."""
    name = SHEET_FOR.get(expr, expr)
    for key in (f"{expr}/{view}", f"{name}/{view}", expr, name):
        if key in heads:
            return heads[key]
    same_view = [v for k, v in heads.items() if k.endswith("/" + view)]
    return (same_view or list(heads.values()))[0]


@lru_cache(maxsize=2)
def _sheet_skin(folder: str) -> tuple:
    a = np.asarray(next(iter(load_heads(folder).values()))).reshape(-1, 4).astype(int)
    m = (a[:, 3] > 220) & (a[:, 0] > 120) & (a[:, 0] > a[:, 1] + 25) & (a[:, 1] > a[:, 2])
    return tuple(int(v) for v in np.median(a[m, :3], axis=0)) if m.any() else SKIN


def paste_head(cv: Canvas, j: dict, p: Pose, folder: str):
    heads = load_heads(folder)
    img = head_picture(heads, p.expr, "front" if p.front else p.view)
    h = HEAD_H * SS
    w = img.width * h / img.height
    img = img.resize((max(2, int(round(w))), max(2, int(round(h)))), Image.LANCZOS)
    if p.facing < 0 and not p.front:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    side = int(round(h * 2))
    pad = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    pad.alpha_composite(img, (int(round(side / 2 - img.width / 2)), int(round(side / 2 - img.height))))
    ang = 0.0 if p.front else j["head_angle"] * 0.55
    pad = pad.rotate(-ang * p.facing, resample=Image.BICUBIC)
    neck = j["neck"]
    fwd = 0.0 if p.front else p.facing * 0.025 * B
    ax, ay = cv.p((neck[0] + fwd, neck[1] + 0.035 * B))
    cv.img.alpha_composite(pad, (int(round(ax - side / 2)), int(round(ay - side / 2))))


def draw_front(cv: Canvas, j: dict, p: Pose, heads: str | None):
    """The front drawing: legs apart with the boots turned out, the jacket square to camera, arms at the sides."""
    sheet = load_sheet(heads, "front")
    for s in SIDES:
        draw_leg(cv, j, s, False, -1 if j["hip_" + s][0] < j["hip"][0] else 1, p.wound, sheet)
    neck = j["neck"]
    draw_torso(cv, j, 1, True, sheet)
    skin = _sheet_skin(heads) if heads else SKIN
    for s in SIDES:
        draw_arm(cv, j, s, False, -1 if j["shoulder_" + s][0] < j["shoulder"][0] else 1, skin, sheet, "shoulder_" + s)
    if heads:
        paste_head(cv, j, p, heads)
    else:
        draw_head(cv, j, replace(p, facing=1))
    if not sheet:
        cv.caps([((neck[0] - 0.07 * B, neck[1] + 0.01 * B), (neck[0] + 0.07 * B, neck[1] + 0.01 * B), 0.032 * B,
                  0.032 * B)], SCARF)


def draw_character(p: Pose, heads: str | None = None) -> tuple[Image.Image, tuple[int, int]]:
    """The hero on a transparent layer and where its top-left goes on the frame. ``heads`` = a folder of painted head
    pictures (the face from the image model, the body from the rig); without it the head is drawn by code."""
    j = skeleton(p)
    pts = [v for k, v in j.items() if isinstance(v, tuple)]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    m = 0.36 * B
    x0, y0 = int(math.floor(min(xs) - m)), int(math.floor(min(ys) - m))
    x1, y1 = int(math.ceil(max(xs) + m)), int(math.ceil(max(ys) + m))
    cv = Canvas(x0, y0, x1 - x0, y1 - y0)
    if p.front:
        draw_front(cv, j, p, heads)
        return cv.img.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0)
    f = p.facing
    near = near_side(f)
    far = SIDES[1 - SIDES.index(near)]
    skin = _sheet_skin(heads) if heads else SKIN
    sheet = load_sheet(heads, p.view)
    tq = p.view == "three_quarter"
    draw_arm(cv, j, far, True, f, skin, sheet, "shoulder_" + far if tq else "shoulder")
    draw_leg(cv, j, far, True, f, p.wound, sheet)
    draw_leg(cv, j, near, False, f, p.wound, sheet)
    neck = j["neck"]
    if not sheet:
        # the scarf tail behind the body, then the puffy jacket over the hips
        a = math.radians(max(-70.0, min(70.0, p.scarf)))
        lift = max(0.0, math.sin(abs(a)))  # the faster the run, the higher the tail flies behind
        t1 = (neck[0] - f * 0.10 * B * (0.4 + 0.6 * lift), neck[1] + 0.05 * B + 0.06 * B * (1 - lift))
        t2 = (t1[0] - f * 0.09 * B * (0.3 + 0.7 * lift), t1[1] + 0.08 * B * (1 - lift) + 0.01 * B)
        cv.caps([(neck, t1, 0.026 * B, 0.022 * B), (t1, t2, 0.022 * B, 0.018 * B)], SCARF)
    draw_torso(cv, j, f, False, sheet, p.view)

    def head():
        if heads:
            paste_head(cv, j, p, heads)
        else:
            draw_head(cv, j, p)
        if not sheet:
            cv.caps([((neck[0] - 0.035 * B, neck[1] + 0.012 * B), (neck[0] + 0.04 * B, neck[1] + 0.005 * B),
                      0.03 * B, 0.03 * B)], SCARF)  # the collar covers the neck stump

    if p.torso > 40:  # lying or falling: the near arm goes under the head, never across the face
        draw_arm(cv, j, near, False, f, skin, sheet, "shoulder_" + near if tq else "shoulder")
        head()
    else:
        head()
        draw_arm(cv, j, near, False, f, skin, sheet, "shoulder_" + near if tq else "shoulder")
    return cv.img.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0)


# --- the world: the painted plate + code-made weather ------------------------------------------------------------------
@lru_cache(maxsize=2)
def load_plate(path: str | None) -> np.ndarray:
    if path:
        im = Image.open(path).convert("RGB").resize((FRAME_W, FRAME_H), Image.LANCZOS)
        return np.asarray(im).copy()
    y = np.linspace(0, 1, FRAME_H)[:, None, None]
    sky = np.array([200, 218, 236]) * (1 - y) + np.array([246, 248, 252]) * y
    return np.broadcast_to(sky, (FRAME_H, FRAME_W, 3)).astype(np.uint8).copy()


TREE_BOX = (1400, 230, 1920, 660)  # x0, y0, x1, y1 of the plate's trees


@lru_cache(maxsize=2)
def _tree_weight(path: str | None) -> np.ndarray:
    plate = load_plate(path)
    x0, y0, x1, y1 = TREE_BOX
    reg = plate[y0:y1, x0:x1].astype(np.float32)
    lum = reg.mean(axis=2)
    blue = reg[..., 2] - reg[..., 0]
    m = ((lum < 150) | (blue > 26)).astype(np.float32)
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4))
    w = np.asarray(im).astype(np.float32) / 255.0
    rows = np.clip((y1 - np.arange(y0, y1)) / (y1 - y0), 0, 1)[:, None] ** 1.6
    return w * rows


def wind(t: float) -> float:
    return 2.6 * math.sin(2 * math.pi * 0.31 * t) + 1.2 * math.sin(2 * math.pi * 0.83 * t + 1.3) + \
        2.0 * max(0.0, math.sin(2 * math.pi * 0.07 * t - 0.6)) ** 6


def world_at(t: float, plate_path: str | None) -> np.ndarray:
    """The plate with its trees bending in the wind (px shift grows with height, anchored at the roots)."""
    plate = load_plate(plate_path).copy()
    if plate_path:
        x0, y0, x1, y1 = TREE_BOX
        w = _tree_weight(plate_path) * wind(t)
        src = load_plate(plate_path)[y0:y1, x0:x1].astype(np.float32)
        cols = np.arange(x1 - x0)[None, :] - w
        c0 = np.clip(np.floor(cols).astype(int), 0, x1 - x0 - 1)
        c1 = np.clip(c0 + 1, 0, x1 - x0 - 1)
        fr = (cols - np.floor(cols))[..., None]
        rr = np.arange(y1 - y0)[:, None]
        plate[y0:y1, x0:x1] = (src[rr, c0] * (1 - fr) + src[rr, c1] * fr).astype(np.uint8)
    return plate


@lru_cache(maxsize=1)
def _flakes():
    rng = np.random.default_rng(7)
    back = rng.uniform(0, 1, (170, 5))
    front = rng.uniform(0, 1, (22, 5))
    return back, front


def draw_snow(img: Image.Image, t: float, front: bool):
    back, fr = _flakes()
    arr = fr if front else back
    d = ImageDraw.Draw(img, "RGBA")
    for x0, y0, sp, ph, sz in arr:
        speed = (90 + 70 * sp) * (1.8 if front else 1.0)
        y = (y0 * (FRAME_H + 60) + speed * t) % (FRAME_H + 60) - 30
        x = (x0 * FRAME_W + 25 * math.sin(2 * math.pi * (0.25 * t + ph)) + 18 * wind(t) * (2 if front else 1)) % FRAME_W
        r = (4.5 + 2.5 * sz) if front else (1.4 + 1.4 * sz)
        a = 150 if front else 210
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))


def draw_shadows(base: Image.Image, p: Pose):
    """Soft bluish contact shadows on the snow: under the hips and under each foot, fading with height."""
    sh = Image.new("L", (FRAME_W // 4, FRAME_H // 4), 0)
    d = ImageDraw.Draw(sh)
    j = skeleton(p)
    hx = p.hip[0]
    lift = max(0.0, (GROUND - 0.43 * B) - p.hip[1])
    k = max(0.0, 1 - lift / (0.5 * B))
    w = 0.30 * B * (1.6 if p.torso > 45 else 1.0)
    cx = hx + (p.facing * 0.25 * B if p.torso > 45 else 0)
    d.ellipse([(cx - w) / 4, (GROUND - 0.035 * B) / 4, (cx + w) / 4, (GROUND + 0.035 * B) / 4], fill=int(120 * k))
    for s in SIDES:
        ax, ay = j["ankle_" + s]
        h = max(0.0, ANK - ay)
        kk = max(0.0, 1 - h / (0.25 * B))
        toe = 0.11 * B * p.facing
        lo, hi = sorted((ax - 0.06 * B * p.facing, ax + toe))
        d.ellipse([lo / 4, (GROUND - 0.018 * B) / 4, hi / 4, (GROUND + 0.018 * B) / 4], fill=int(150 * kk))
    sh = sh.filter(ImageFilter.GaussianBlur(2.5)).resize((FRAME_W, FRAME_H), Image.BILINEAR)
    a = np.asarray(sh).astype(np.float32)[..., None] / 255.0
    arr = np.asarray(base).astype(np.float32)
    tint = np.array([120, 140, 190], dtype=np.float32)
    out = arr * (1 - a * 0.55) + (arr * tint / 255.0) * (a * 0.55)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def render_frame(t: float, plate_path: str | None = None, heads: str | None = None) -> Image.Image:
    p = pose_at(t)
    frame = Image.fromarray(world_at(t, plate_path)).convert("RGBA")
    draw_snow(frame, t, front=False)
    frame = draw_shadows(frame.convert("RGB"), p).convert("RGBA")
    char, (x0, y0) = draw_character(p, heads)
    _paste(frame, char, x0, y0)
    draw_snow(frame, t, front=True)
    return frame.convert("RGB")


def _paste(frame: Image.Image, layer: Image.Image, x0: int, y0: int):
    cx, cy = max(0, -x0), max(0, -y0)
    if cx >= layer.width or cy >= layer.height:
        return
    frame.alpha_composite(layer.crop((cx, cy, layer.width, layer.height)), (max(0, x0), max(0, y0)))


# --- events, sound, checks ----------------------------------------------------------------------------------------------
def events(fps: int = 24) -> list[dict]:
    """Every sound-worthy moment, read from the poses: a foot touching down, the takeoff, the landing, the impact."""
    sc = scene()
    out = []
    n = int(sc.duration * fps)
    prev = pose_at(0.0)
    for i in range(1, n):
        t = i / fps
        p = pose_at(t)
        for s in SIDES:
            if _grounded(p.feet[s]) and not _grounded(prev.feet[s]):
                out.append({"t": round(t, 4), "kind": "step", "x": p.feet[s][0],
                            "loud": 1.0 if t < 3.6 or t > sc.turn[1] else 1.3})
        prev = p
    for t, kind, x in sc.events:
        out.append({"t": round(t, 4), "kind": kind, "x": x, "loud": 1.0})
    return sorted(out, key=lambda e: e["t"])


def _bandpass_noise(rng, n, lo, hi, sr):
    x = rng.normal(0, 1, n)
    spec = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    spec[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(spec, n)


def make_audio(path: Path, fps: int = 24, sr: int = 48000):
    """Wind under everything, a snow crunch at every footfall, a whoosh at the takeoff, thuds at the landing and the
    impact; panned by where it happens."""
    sc = scene()
    n = int(sc.duration * sr)
    rng = np.random.default_rng(11)
    out = np.zeros((n, 2))
    w = _bandpass_noise(rng, n, 80, 900, sr)
    t = np.arange(n) / sr
    env = 0.55 + 0.25 * np.sin(2 * np.pi * 0.07 * t) + 0.2 * np.sin(2 * np.pi * 0.19 * t + 1)
    w = w / (np.abs(w).max() + 1e-9) * 0.14 * env
    out[:, 0] += w
    out[:, 1] += np.roll(w, 900)
    for e in events(fps):
        i0 = int(e["t"] * sr)
        pan = min(1.0, max(0.0, e["x"] / FRAME_W))
        if e["kind"] == "step":
            m = int(0.13 * sr)
            s = _bandpass_noise(rng, m, 1200, 7000, sr)
            crackle = (rng.uniform(0, 1, m) > 0.985) * rng.normal(0, 3, m)
            s = (s / (np.abs(s).max() + 1e-9) + crackle * 0.3) * np.exp(-np.arange(m) / (0.035 * sr)) * 0.35 * e["loud"]
        elif e["kind"] == "takeoff":
            m = int(0.45 * sr)
            s = _bandpass_noise(rng, m, 300, 3000, sr)
            s = s / (np.abs(s).max() + 1e-9) * np.sin(np.pi * np.arange(m) / m) * 0.18
        else:
            m = int(0.5 * sr)
            tt = np.arange(m) / sr
            s = np.sin(2 * np.pi * (70 - 30 * tt) * tt) * np.exp(-tt / 0.12) * (0.9 if e["kind"] == "impact" else 0.6)
            nz = _bandpass_noise(rng, m, 600, 6000, sr)
            s += nz / (np.abs(nz).max() + 1e-9) * np.exp(-tt / 0.05) * 0.4
        m = min(len(s), n - i0)
        if m <= 0:
            continue
        out[i0:i0 + m, 0] += s[:m] * math.cos(pan * math.pi / 2)
        out[i0:i0 + m, 1] += s[:m] * math.sin(pan * math.pi / 2)
    out = np.tanh(4.0 * out / (np.abs(out).max() + 1e-9)) / math.tanh(4.0) * 0.7  # soft-clip the thuds' crest
    pcm = (out * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def check(fps: int = 24) -> dict:
    """The shot's motion checks (the ice test's lessons as numbers): planted feet do not slide (BR-1), nothing goes under
    the snow (BR-2), a planted foot is really reached (BR-3), bones keep their length (BR-4), no joint jumps between
    frames (BR-5), the hero stays in frame once he has walked in (BR-6), every footfall has its sound (BR-7)."""
    sc = scene()
    n = int(sc.duration * fps)
    findings = []
    prev_p, prev_j = None, None
    ta, tb = sc.turn
    for i in range(n):
        t = i / fps
        p = pose_at(t)
        j = skeleton(p)
        turning = ta - 1e-6 <= t <= tb + 1.0 / fps
        for s in SIDES:
            ax, ay = j["ankle_" + s]
            if ay > ANK + 1.0:
                findings.append({"rule": "BR-2", "t": t, "what": f"foot {s} {ay - ANK:.1f} px under the snow"})
            if p.feet[s][3] and math.hypot(ax - p.feet[s][0], ay - p.feet[s][1]) > 2.0:
                findings.append({"rule": "BR-3", "t": t, "what": f"planted foot {s} not reached"})
            for a, b, ln in (("hip_" + s, "knee_" + s, THIGH), ("knee_" + s, "ankle_" + s, SHIN)):
                if abs(math.dist(j[a], j[b]) - ln) > 0.5:
                    findings.append({"rule": "BR-4", "t": t, "what": f"{a}-{b} length changed"})
            if prev_p and not turning and p.feet[s][3] and prev_p.feet[s][3]:
                if math.dist(p.feet[s][:2], prev_p.feet[s][:2]) > 1.0:
                    findings.append({"rule": "BR-1", "t": t, "what": f"planted foot {s} slid"})
        if prev_j and not turning:
            for key, v in j.items():
                if isinstance(v, tuple) and math.dist(v, prev_j[key]) > 0.22 * B:
                    findings.append({"rule": "BR-5", "t": t, "what": f"{key} jumped {math.dist(v, prev_j[key]):.0f} px"})
        if t > 2.2:
            xs = [v[0] for v in j.values() if isinstance(v, tuple)]
            ys = [v[1] for v in j.values() if isinstance(v, tuple)]
            if min(xs) - HEAD < 0 or max(xs) + HEAD > FRAME_W or min(ys) - HEAD < 0:
                findings.append({"rule": "BR-6", "t": t, "what": "hero leaves the frame"})
        prev_p, prev_j = p, j
    steps = {round(e["t"], 4) for e in events(fps) if e["kind"] == "step"}
    prev = pose_at(0.0)
    for i in range(1, n):
        t = i / fps
        p = pose_at(t)
        if any(_grounded(p.feet[s]) and not _grounded(prev.feet[s]) for s in SIDES) and round(t, 4) not in steps:
            findings.append({"rule": "BR-7", "t": t, "what": "a footfall without its sound"})
        prev = p
    return {"verdict": "PASS" if not findings else "FAIL", "frames": n, "fps": fps, "findings": findings[:200],
            "count": len(findings)}


def loudness(path: Path) -> float:
    """Integrated loudness (LUFS) by ffmpeg's EBU R128 meter."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "a:0", "-af", "ebur128", "-f",
                        "null", "-"], capture_output=True, text=True)
    vals = [ln.split("I:")[1].split("LUFS")[0] for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    return float(vals[-1])


def demo(out: Path, plate: str | None, fps: int = 24, crf: int = 18, heads: str | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    sc = scene()
    n = int(sc.duration * fps)
    silent = out / "bend_poc_silent.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FRAME_W}x{FRAME_H}",
           "-r", str(fps), "-i", "-", "-frames:v", str(n), "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p",
           str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    sheet_times = np.linspace(0.5, sc.duration - 0.5, 24)
    stills = {}
    for i in range(n):
        t = i / fps
        img = render_frame(t, plate, heads)
        proc.stdin.write(img.tobytes())
        for st in sheet_times:
            if abs(st - t) < 0.5 / fps:
                stills[st] = img.resize((480, 270), Image.LANCZOS)
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed")
    wav = out / "bend_poc.wav"
    make_audio(wav, fps)
    final = out / "bend_poc.mp4"
    # the channel's loudness (-14 LUFS): measure, raise by the difference, a limiter keeps the true peak under -1.5 dBTP
    gain = -14.0 - loudness(wav)
    for _ in range(5):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy",
                        "-af", f"volume={gain:.2f}dB,alimiter=limit=0.7:level=false", "-ar", "48000", "-ac", "2",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)], check=True)
        miss = -14.0 - loudness(final)
        if abs(miss) < 0.5:
            break
        gain += miss
    sheet = Image.new("RGB", (480 * 6, 270 * 4), (20, 20, 20))
    for k, st in enumerate(sorted(stills)):
        sheet.paste(stills[st], ((k % 6) * 480, (k // 6) * 270))
    sheet.save(out / "bend_poc_frames.jpg", quality=88)
    report = check(fps)
    report["loudness_lufs"] = round(loudness(final), 1)
    report["events"] = events(fps)
    (out / "bend_poc_check.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    silent.unlink(missing_ok=True)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.bend_rig")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--plate", default=None)
    d.add_argument("--fps", type=int, default=24)
    d.add_argument("--heads", default=None, help="folder of painted head_<expression>.png pictures")
    c = sub.add_parser("check")
    c.add_argument("--fps", type=int, default=24)
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        r = demo(a.out, a.plate, a.fps, heads=a.heads)
    else:
        r = check(a.fps)
    print(json.dumps({k: v for k, v in r.items() if k != "events"}, indent=1)[:4000])
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
