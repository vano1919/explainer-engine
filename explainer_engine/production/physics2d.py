"""Physics for the 2.5D shots (the creator, 2026-10-22 20:32: "the problem is physics and montage, completely off from
reality"): bodies with mass, friction, slopes and collisions instead of eased keys. Built on pymunk (Chipmunk2D, MIT).

The scene lives in a vertical plane along a *lane*: ``s`` runs along the ground (px, world units), ``h`` is the
elevation (px, up). The lane maps ``s`` to the 2.5D world (lateral x and the distance away) so one simulation serves
the sled, the rope and the fall, and the picture only projects what the physics did.

- ``Terrain``: the ground profile ``h(s)`` from slope sections, as static pymunk segments.
- ``Lane``: ``s`` -> (world x, away) along a path that bends away from the camera.
- ``SledSim``: a sled dragged on a rope (SlideJoint) by a moving hand, released, bumping a foot, sliding down.
- ``Ragdoll``: a rig skeleton turned into jointed bodies with muscle tone (damped rotary springs), falling on the terrain.
- ``follow_through``: a damped spring over a sampled signal (secondary motion of heads, torsos, soft parts).
- ``Operator``: a camera that follows targets like a hand-held operator: critically damped, never stopping dead.

Units: 1 world px = 1/180 m (a 1.8 m hero is 324 px tall at depth 1); ``G`` = 9.81 m/s^2 in px/s^2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pymunk

PX_PER_M = 180.0
G = 9.81 * PX_PER_M
DT = 1.0 / 240.0


# --- terrain -------------------------------------------------------------------------------------------------------------
@dataclass
class Terrain:
    """The ground along the lane: ``sections`` = [(s_end, slope_deg), ...] from s = 0; a positive slope descends with s
    (downhill ahead). ``h(s)`` is continuous, 0 at s = 0."""
    sections: list
    friction: float = 1.0

    def __post_init__(self):
        self._s = [0.0]
        self._h = [0.0]
        s0 = 0.0
        for s1, deg in self.sections:
            self._h.append(self._h[-1] - (s1 - s0) * math.tan(math.radians(deg)))
            self._s.append(s1)
            s0 = s1

    def h(self, s: float) -> float:
        if s <= self._s[0]:
            return self._h[0]
        if s >= self._s[-1]:
            return self._h[-1]
        return float(np.interp(s, self._s, self._h))

    def slope(self, s: float) -> float:
        """Degrees, positive = descending ahead."""
        s0 = 0.0
        for s1, deg in self.sections:
            if s < s1:
                return deg
            s0 = s1
        return 0.0

    def segments(self, body: pymunk.Body, radius: float = 2.0) -> list:
        out = []
        for (sa, ha), (sb, hb) in zip(zip(self._s, self._h), zip(self._s[1:], self._h[1:])):
            seg = pymunk.Segment(body, (sa, ha), (sb, hb), radius)
            seg.friction = self.friction
            seg.elasticity = 0.05
            seg.collision_type = 1
            out.append(seg)
        # the world continues flat beyond the profile
        for a, b in (((self._s[0] - 1e5, self._h[0]), (self._s[0], self._h[0])),
                     ((self._s[-1], self._h[-1]), (self._s[-1] + 1e5, self._h[-1]))):
            seg = pymunk.Segment(body, a, b, radius)
            seg.friction = self.friction
            seg.collision_type = 1
            out.append(seg)
        return out


# --- the lane ------------------------------------------------------------------------------------------------------------
@dataclass
class Lane:
    """``s`` along the ground -> (world x, away). Straight along +x from ``x0`` until ``s_turn``, then the heading
    swings to ``heading_deg`` (degrees away from the camera) over ``turn_len`` and stays. Integrated once."""
    x0: float
    s_turn: float
    heading_deg: float
    turn_len: float
    s_max: float = 20000.0

    def __post_init__(self):
        n = int(self.s_max / 4) + 1
        ss = np.arange(n) * 4.0
        u = np.clip((ss - self.s_turn) / self.turn_len, 0, 1)
        th = np.radians(self.heading_deg) * (u * u * (3 - 2 * u))
        x = self.x0 + np.concatenate([[0.0], np.cumsum(np.cos(th[:-1]) * 4.0)])
        away = np.concatenate([[0.0], np.cumsum(np.sin(th[:-1]) * 4.0)])
        self._s, self._x, self._away, self._th = ss, x, away, np.degrees(th)

    def at(self, s: float) -> tuple[float, float]:
        s = min(max(s, 0.0), self.s_max)
        return float(np.interp(s, self._s, self._x)), float(np.interp(s, self._s, self._away))

    def heading(self, s: float) -> float:
        return float(np.interp(min(max(s, 0.0), self.s_max), self._s, self._th))

    def s_of_x(self, x: float) -> float:
        """The s of a world x on the straight part (before the turn)."""
        return x - self.x0


# --- the sled ------------------------------------------------------------------------------------------------------------
@dataclass
class SledResult:
    t: np.ndarray            # 240 Hz
    s: np.ndarray            # the sled's centre along the lane
    h: np.ndarray            # its centre's elevation
    angle: np.ndarray        # radians, positive = nose up
    v: np.ndarray            # speed along the lane (px/s, signed)
    rope_slack: np.ndarray   # rope length minus the hand-handle distance (>= 0 while attached), nan after release
    events: list = field(default_factory=list)   # (t, kind, data)

    def sample(self, t: float) -> tuple[float, float, float, float]:
        i = min(len(self.t) - 1, max(0, int(round((t - self.t[0]) * 240))))
        return float(self.s[i]), float(self.h[i]), float(self.angle[i]), float(self.v[i])


class SledSim:
    """A suitcase sled on the terrain. ``hand(t)`` -> (s, h) of the hand holding the rope while ``t < release``;
    ``foot(t, sled_front_s)`` -> (s, h, r) of a foot in the sled's way or None (the acting decides when the heel lifts
    and when the sled has passed it); every contact is recorded as a ``bump`` event. The lip's drop (the sled leaving the ground) and the
    landing are recorded too, so the sound and the acting follow what happened."""

    def __init__(self, terrain: Terrain, length: float, height: float, mass: float = 8.0, friction: float = 0.06,
                 rope: float = 230.0, s0: float = 0.0, arm_mass: float = 1.5, arm_k: float = 400.0, arm_zeta: float = 1.0):
        """``arm_*``: the arm that holds the rope gives (a damped spring between the hand's path and the grip, stiffness
        in kg/s^2 like a real shoulder's ~400 N/m), so the gait's bob does not yank the sled every step."""
        self.terrain, self.length, self.height, self.rope_len = terrain, length, height, rope
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -G)
        self.space.iterations = 20
        ground = self.space.static_body
        for seg in terrain.segments(ground):
            self.space.add(seg)
        self.sled = pymunk.Body(mass, pymunk.moment_for_box(mass, (length, height)))
        self.sled.position = (s0, terrain.h(s0) + height / 2 + 2.5)
        self.sled.angle = -math.radians(terrain.slope(s0))
        box = pymunk.Poly.create_box(self.sled, (length, height), radius=3.0)
        box.friction = friction
        box.elasticity = 0.15
        box.collision_type = 2
        self.space.add(self.sled, box)
        self.hand = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.space.add(self.hand)
        self.grip = pymunk.Body(arm_mass, float("inf"))       # the hand's mass on a giving arm (no shape, no gravity)
        self.grip.velocity_func = lambda body, g, d, dt: pymunk.Body.update_velocity(body, (0.0, 0.0), d, dt)
        self.arm = pymunk.DampedSpring(self.hand, self.grip, (0, 0), (0, 0), 0.0, arm_k,
                                       2.0 * arm_zeta * math.sqrt(arm_k * arm_mass))
        self.joint = pymunk.SlideJoint(self.grip, self.sled, (0, 0), (length / 2 - 8, height / 2), 0.0, rope)
        self.space.add(self.grip, self.arm, self.joint)
        self.foot_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.space.add(self.foot_body)
        self.foot_shape = None
        self._bumped = None
        self.space.on_collision(2, 3, begin=self._on_bump)

    def _on_bump(self, arb, space, data):
        self._bumped = self._t
        return True

    def run(self, t0: float, t1: float, hand, release: float, foot=None) -> SledResult:
        n = int(round((t1 - t0) * 240)) + 1
        ts = t0 + np.arange(n) / 240.0
        s = np.empty(n)
        h = np.empty(n)
        ang = np.empty(n)
        v = np.empty(n)
        slack = np.full(n, np.nan)
        events = []
        attached = True
        prev_hand = hand(t0)
        self.hand.position = prev_hand
        self.grip.position = prev_hand
        self.grip.velocity = (0.0, 0.0)
        airborne = False
        for i, t in enumerate(ts):
            self._t = t
            if attached and t >= release:
                self.space.remove(self.joint, self.arm, self.grip)
                attached = False
                events.append((t, "release", {}))
            if attached:
                hp = hand(t)
                self.hand.velocity = ((hp[0] - prev_hand[0]) * 240.0, (hp[1] - prev_hand[1]) * 240.0)
                self.hand.position = hp
                prev_hand = hp
                hx, hy = self.sled.local_to_world((self.length / 2 - 8, self.height / 2))
                gp = self.grip.position
                slack[i] = self.rope_len - math.hypot(gp[0] - hx, gp[1] - hy)
            else:
                self.hand.velocity = (0.0, 0.0)
            if foot is not None:
                front = self.sled.local_to_world((self.length / 2, 0)).x
                fp = foot(t, front)
                if fp is not None:
                    if self.foot_shape is None:
                        self.foot_body.position = (fp[0], fp[1])
                        self.foot_body.velocity = (0.0, 0.0)
                        # a foot that comes down inside the sled is beside it, not in its way
                        if self.sled.shapes and next(iter(self.sled.shapes)).point_query((fp[0], fp[1])).distance > fp[2]:
                            self.foot_shape = pymunk.Circle(self.foot_body, fp[2])
                            self.foot_shape.friction = 0.6
                            self.foot_shape.collision_type = 3
                            self.space.add(self.foot_shape)
                    else:
                        fb = self.foot_body.position
                        self.foot_body.velocity = ((fp[0] - fb.x) * 240.0, (fp[1] - fb.y) * 240.0)
                        self.foot_body.position = (fp[0], fp[1])
                elif self.foot_shape is not None:
                    self.space.remove(self.foot_shape)
                    self.foot_shape = None
                if self._bumped is not None:
                    events.append((self._bumped, "bump", {"v": float(self.sled.velocity.x)}))
                    self._bumped = None
            self.space.step(DT)
            p = self.sled.position
            s[i], h[i], ang[i], v[i] = p.x, p.y, self.sled.angle, self.sled.velocity.x
            # airborne when the lowest corner is well above the ground under it
            corners = [self.sled.local_to_world(c) for c in ((-self.length / 2, -self.height / 2),
                                                             (self.length / 2, -self.height / 2))]
            gap = min(c.y - self.terrain.h(c.x) for c in corners)
            if gap > 10.0 and not airborne:
                airborne = True
                events.append((t, "takeoff", {"s": float(p.x), "v": float(v[i])}))
            elif gap <= 3.0 and airborne:
                airborne = False
                events.append((t, "land", {"s": float(p.x), "vy": float(self.sled.velocity.y)}))
        # when it came to rest
        moving = np.abs(v) > 8.0
        if moving.any():
            last = int(np.nonzero(moving)[0][-1])
            events.append((float(ts[last]), "rest", {"s": float(s[last])}))
        return SledResult(ts, s, h, ang, v, slack, events)


# --- the ragdoll ---------------------------------------------------------------------------------------------------------
LIMBS = (("torso", "hip", "neck", 30.0), ("head", "neck", "head", 5.0),
         ("thigh_L", "hip_L", "knee_L", 8.0), ("shin_L", "knee_L", "ankle_L", 4.0),
         ("thigh_R", "hip_R", "knee_R", 8.0), ("shin_R", "knee_R", "ankle_R", 4.0),
         ("upper_L", "shoulder_L", "elbow_L", 2.5), ("fore_L", "elbow_L", "hand_L", 1.5),
         ("upper_R", "shoulder_R", "elbow_R", 2.5), ("fore_R", "elbow_R", "hand_R", 1.5))
JOINTS = (("hip_L", "torso", "thigh_L"), ("hip_R", "torso", "thigh_R"), ("knee_L", "thigh_L", "shin_L"),
          ("knee_R", "thigh_R", "shin_R"), ("neck", "torso", "head"), ("shoulder_L", "torso", "upper_L"),
          ("shoulder_R", "torso", "upper_R"), ("elbow_L", "upper_L", "fore_L"), ("elbow_R", "upper_R", "fore_R"))
# relative-angle limits (radians) of the child about the parent, for a hero facing +s: knees and elbows bend one way
LIMITS = {"knee": (0.0, 2.4), "elbow": (-2.4, 0.0), "hip": (-1.2, 2.0), "shoulder": (-3.0, 3.0), "neck": (-0.8, 0.8)}


@dataclass
class RagdollResult:
    t: np.ndarray
    joints: dict             # name -> (n, 2) array of (s, h)
    contacts: dict           # name -> (n,) bool: the limb touches the ground
    events: list             # (t, kind, data): "impact" with the speed, "rest"

    def at(self, t: float) -> tuple[dict, dict]:
        i = min(len(self.t) - 1, max(0, int(round((t - self.t[0]) * 240))))
        return {k: (float(v[i, 0]), float(v[i, 1])) for k, v in self.joints.items()}, {k: bool(v[i]) for k, v in
                                                                                       self.contacts.items()}


class Ragdoll:
    """Jointed bodies from a skeleton (joint name -> (s, h), ``facing`` +1 = toward +s), with muscle tone: every joint
    keeps its angle with a damped rotary spring whose stiffness ``tone(t)`` fades as the body goes slack, and the
    shoulders reach for ``reach_angle`` (the protective reflex: hands out toward the ground ahead)."""

    def __init__(self, skel: dict, facing: int, terrain: Terrain, radius: float = 9.0):
        self.terrain, self.facing = terrain, facing
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -G)
        self.space.iterations = 30
        for seg in terrain.segments(self.space.static_body, radius=2.0):
            self.space.add(seg)
        self.bodies: dict[str, pymunk.Body] = {}
        self.ends: dict[str, tuple[str, str]] = {}
        self.shapes: dict[str, pymunk.Shape] = {}
        self.touch: dict[str, bool] = {}
        self.pos0 = {}
        for name, a, b, mass in LIMBS:
            for q in (a, b):
                self.pos0[q] = skel[q] if q in skel else skel[q.rsplit("_", 1)[0]]   # a side drawing has one shoulder
        skel = self.pos0
        group = 7
        for name, a, b, mass in LIMBS:
            pa, pb = skel[a], skel[b]
            length = max(1.0, math.dist(pa, pb))
            body = pymunk.Body(mass, pymunk.moment_for_segment(mass, (-length / 2, 0), (length / 2, 0), radius))
            body.position = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            body.angle = math.atan2(pb[1] - pa[1], pb[0] - pa[0])
            r = radius * (1.8 if name == "head" else 1.3 if name == "torso" else 1.0)
            shape = pymunk.Segment(body, (-length / 2, 0), (length / 2, 0), r)
            shape.friction = 0.9
            shape.elasticity = 0.02
            shape.filter = pymunk.ShapeFilter(group=group)
            shape.collision_type = 10
            self.space.add(body, shape)
            self.bodies[name], self.ends[name], self.shapes[name] = body, (a, b), shape
            self.touch[name] = False
        self.springs: list[tuple[str, pymunk.DampedRotarySpring, float]] = []
        for jname, parent, child in JOINTS:
            pb, cb = self.bodies[parent], self.bodies[child]
            anchor = skel[jname]
            pivot = pymunk.PivotJoint(pb, cb, anchor)
            pivot.collide_bodies = False
            self.space.add(pivot)
            kind = jname.split("_")[0]
            lo, hi = LIMITS[kind]
            rel = pb.angle - cb.angle   # chipmunk's relative angle a - b
            if kind in ("knee", "elbow", "hip"):
                lo, hi = (lo, hi) if facing > 0 else (-hi, -lo)
                self.space.add(pymunk.RotaryLimitJoint(pb, cb, rel + lo, rel + hi))
            spring = pymunk.DampedRotarySpring(pb, cb, rel, 1.0, 1.0)
            self.space.add(spring)
            self.springs.append((jname, spring, rel))
        self.space.on_collision(10, 1, begin=self._touch, separate=self._untouch)
        self._impacts: list[tuple[float, float, str]] = []

    def _touch(self, arb, space, data):
        for sh in arb.shapes:
            for name, mine in self.shapes.items():
                if sh is mine:
                    self.touch[name] = True
                    v = abs(sh.body.velocity.y)
                    self._impacts.append((self._t, v, name))
        return True

    def _untouch(self, arb, space, data):
        for sh in arb.shapes:
            for name, mine in self.shapes.items():
                if sh is mine:
                    self.touch[name] = False

    def joints_now(self) -> dict:
        out = {}
        for name, (a, b) in self.ends.items():
            body = self.bodies[name]
            length = math.dist(self.pos0[a], self.pos0[b])
            pa = body.local_to_world((-length / 2, 0))
            pb = body.local_to_world((length / 2, 0))
            out.setdefault(a, (pa.x, pa.y))
            out[b] = (pb.x, pb.y)
        return out

    def run(self, t0: float, duration: float, velocity: tuple, spin: float, tone, reach_angle: float = 1.1,
            reach_k: float = 2.5e5) -> RagdollResult:
        """``velocity`` (s, h) px/s of the whole body at the trip, ``spin`` rad/s forward pitch; ``tone(t - t0)`` ->
        stiffness 0..1 of the muscle springs (1 = holding the pose, 0 = limp); the shoulders pull the arms toward
        ``reach_angle`` (radians below horizontal, ahead) while the body is in the air or falling."""
        hip = self.bodies["torso"].position
        for body in self.bodies.values():
            r = body.position - hip
            body.velocity = (velocity[0] - spin * r.y * self.facing, velocity[1] + spin * r.x * self.facing)
            body.angular_velocity = -spin * self.facing
        n = int(round(duration * 240)) + 1
        ts = t0 + np.arange(n) / 240.0
        names = sorted({j for pair in self.ends.values() for j in pair})
        rec = {k: np.empty((n, 2)) for k in names}
        contacts = {k: np.zeros(n, bool) for k in self.bodies}
        events = []
        impacted = False
        for i, t in enumerate(ts):
            self._t = t
            k = tone(t - t0)
            for jname, spring, rel in self.springs:
                kind = jname.split("_")[0]
                base = {"knee": 9e5, "hip": 1.2e6, "neck": 2.5e5, "shoulder": 2.5e5, "elbow": 1.5e5}[kind]
                spring.stiffness = base * (0.08 + 0.92 * k)
                spring.damping = base * 0.004 * (0.3 + 0.7 * k)
                if kind == "shoulder":
                    # reach ahead and down: the arm's world angle wants -reach_angle (below horizontal, ahead)
                    want = -reach_angle if self.facing > 0 else -math.pi + reach_angle
                    torso_angle = self.bodies["torso"].angle
                    spring.rest_angle = torso_angle - want if k > 0.05 else rel
                    spring.stiffness = reach_k * (0.3 + 0.7 * k)
                    spring.damping = reach_k * 0.006
                elif kind == "neck":
                    spring.rest_angle = rel
            self.space.step(DT)
            j = self.joints_now()
            for name in names:
                rec[name][i] = j[name]
            for name in self.bodies:
                contacts[name][i] = self.touch[name]
            if not impacted and self._impacts:
                heavy = [imp for imp in self._impacts if imp[2] in ("torso", "head", "thigh_L", "thigh_R")]
                if heavy:
                    impacted = True
                    events.append((heavy[0][0], "impact", {"v": heavy[0][1], "part": heavy[0][2]}))
        speed = np.hypot(*np.gradient(rec["hip"], axis=0).T) * 240.0
        slow = speed < 25.0
        if slow.any():
            first = int(np.argmax(slow & (ts > ts[0] + 0.3)))
            events.append((float(ts[first]), "rest", {}))
        return RagdollResult(ts, rec, contacts, events)


# --- follow-through ------------------------------------------------------------------------------------------------------
def follow_through(target: np.ndarray, k: float, c: float, rate: float = 240.0, x0: float | None = None) -> np.ndarray:
    """A damped spring (stiffness ``k``, damping ``c``) chasing ``target`` sampled at ``rate`` Hz: the lag and overshoot
    of a soft part behind the motion that drives it (a head nodding behind the hips' dips, a torso leaning back under
    acceleration, a scarf tail)."""
    x = float(target[0]) if x0 is None else x0
    w = 0.0
    out = np.empty(len(target))
    for i, tgt in enumerate(target):
        w += (k * (tgt - x) - c * w) / rate
        x += w / rate
        out[i] = x
    return out


# --- the camera operator -------------------------------------------------------------------------------------------------
class Operator:
    """A camera value (pan, tilt or zoom) that follows a target like a human operator: a second-order system, critically
    damped by default (``zeta``), with a top speed. It starts a shot framed on the target at the target's own speed, so
    the first frames are not a lurch, and it never comes to a dead stop on a key: it settles."""

    def __init__(self, omega: float, zeta: float = 1.0, vmax: float = float("inf")):
        self.omega, self.zeta, self.vmax = omega, zeta, vmax

    def track(self, target: np.ndarray, rate: float = 240.0, v0: float | None = None) -> np.ndarray:
        x = float(target[0])
        v = float((target[1] - target[0]) * rate) if (v0 is None and len(target) > 1) else (v0 or 0.0)
        out = np.empty(len(target))
        w = self.omega
        for i, tgt in enumerate(target):
            a = w * w * (tgt - x) - 2 * self.zeta * w * v
            v += a / rate
            v = max(-self.vmax, min(self.vmax, v))
            x += v / rate
            out[i] = x
        return out
