"""A cut-out character rig (the creator's muse, 2026-10-22: simple and beautiful, but the emotion and the physics must be
good). numpy + PIL only; every frame is a pure function of its number, so a chunked render draws the same pixels.

A ``Puppet`` is a tree of PNG pieces (head, torso, arms, legs, scarf...) with a pivot on each piece and an attach point on
its parent; a ``pose`` gives every joint an angle. ``CYCLES`` are keyframed poses with easing (idle, walk, run, point, fall,
react, turn) that any character of the same build reuses. The free animation principles ride on top of the poses:

* follow-through / overlapping action: pieces marked ``secondary`` (scarf, hair, coat tail) are a damped spring that lags
  behind the joint they hang from and settles after it stops (``Spring``);
* squash and stretch with preserved volume from the body's vertical speed (``squash``);
* slow-in / slow-out: keyframes are eased (``ease``), never linear;
* talk: the mouth piece is chosen from the narration's word timings (``mouth_at``: vowels open, m/b/p close, rest between
  words), the Hanna-Barbera economy of a few mouth shapes;
* physics for props: a dropped object falls, bounces and comes to rest by closed-form ballistics (``drop_y``), so no
  integration state is kept between frames.

``demo`` renders a 20-second proof of concept from procedurally drawn placeholder pieces over three parallax layers (no
paid picture): the figure walks in, stops, turns, points at a sign that drops and bounces, speaks two lines, reacts with a
jump. It is the smallest experiment of docs/research/ANIMATION_UNIVERSE_2026-10-22.md section 8; the beat kind that puts a
puppet into ``assemble.finish_frame`` comes after the creator has seen it.

    python -m explainer_engine.production.rig demo --out jobs/rig_poc [--seconds 20] [--fps 24] [--size 1280x720]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

MOUTHS = ("rest", "half", "open_e", "open_o")
VOWEL_O, VOWEL_E, CLOSED = set("ou"), set("aeiy"), set("mbp")


# --- easing, poses, cycles ------------------------------------------------------------------------------------------
def ease(u: float) -> float:
    """Slow in, slow out (smoothstep); u clamped to 0..1."""
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def lerp_pose(a: dict, b: dict, u: float) -> dict:
    keys = set(a) | set(b)
    return {k: a.get(k, 0.0) + (b.get(k, 0.0) - a.get(k, 0.0)) * u for k in keys}


# a cycle: duration (s), loop, keys [(time share 0..1, pose)]; angles in degrees (positive = clockwise on screen),
# ``dy`` the body's lift in body heights (negative = up), ``dx`` the travel per cycle in body heights
_STAND = {"torso": 0, "head": 0, "arm_l": 8, "arm_r": -8, "fore_l": 10, "fore_r": -10, "leg_l": 0, "leg_r": 0, "shin_l": 0, "shin_r": 0, "dy": 0.0}
CYCLES: dict[str, dict] = {
    "idle": {"duration": 3.0, "loop": True, "dx": 0.0, "keys": [
        (0.0, {**_STAND}), (0.5, {**_STAND, "torso": 1.5, "head": -2, "dy": -0.006}), (1.0, {**_STAND})]},
    "walk": {"duration": 1.0, "loop": True, "dx": 0.3, "keys": [
        (0.0, {**_STAND, "leg_l": 28, "shin_l": 10, "leg_r": -22, "shin_r": -30, "arm_l": -25, "arm_r": 25, "fore_l": -20, "fore_r": 30, "torso": 3, "dy": -0.01}),
        (0.25, {**_STAND, "leg_l": 5, "shin_l": 30, "leg_r": -5, "shin_r": -5, "arm_l": 0, "arm_r": 0, "torso": 3, "dy": -0.03}),
        (0.5, {**_STAND, "leg_l": -22, "shin_l": -30, "leg_r": 28, "shin_r": 10, "arm_l": 25, "arm_r": -25, "fore_l": 30, "fore_r": -20, "torso": 3, "dy": -0.01}),
        (0.75, {**_STAND, "leg_l": -5, "shin_l": -5, "leg_r": 5, "shin_r": 30, "arm_l": 0, "arm_r": 0, "torso": 3, "dy": -0.03}),
        (1.0, {**_STAND, "leg_l": 28, "shin_l": 10, "leg_r": -22, "shin_r": -30, "arm_l": -25, "arm_r": 25, "fore_l": -20, "fore_r": 30, "torso": 3, "dy": -0.01})]},
    "run": {"duration": 0.6, "loop": True, "dx": 1.6, "keys": [
        (0.0, {**_STAND, "torso": 12, "head": -6, "leg_l": 45, "shin_l": 20, "leg_r": -40, "shin_r": -70, "arm_l": -50, "arm_r": 50, "fore_l": -60, "fore_r": 60, "dy": -0.02}),
        (0.5, {**_STAND, "torso": 12, "head": -6, "leg_l": -40, "shin_l": -70, "leg_r": 45, "shin_r": 20, "arm_l": 50, "arm_r": -50, "fore_l": 60, "fore_r": -60, "dy": -0.08}),
        (1.0, {**_STAND, "torso": 12, "head": -6, "leg_l": 45, "shin_l": 20, "leg_r": -40, "shin_r": -70, "arm_l": -50, "arm_r": 50, "fore_l": -60, "fore_r": 60, "dy": -0.02})]},
    "point": {"duration": 1.2, "loop": False, "dx": 0.0, "keys": [
        (0.0, {**_STAND}), (0.35, {**_STAND, "arm_r": 20, "fore_r": 40, "torso": -2, "head": 3}),  # anticipation: the arm drops back a little
        (0.7, {**_STAND, "arm_r": -95, "fore_r": -20, "torso": -6, "head": 8, "dy": -0.01}),
        (1.0, {**_STAND, "arm_r": -88, "fore_r": -12, "torso": -5, "head": 6})]},
    "react": {"duration": 0.9, "loop": False, "dx": 0.0, "keys": [
        (0.0, {**_STAND}), (0.2, {**_STAND, "torso": 6, "head": 8, "dy": 0.03}),  # anticipation: crouch
        (0.45, {**_STAND, "torso": -12, "head": -14, "arm_l": 60, "arm_r": -60, "fore_l": 50, "fore_r": -50, "leg_l": 12, "leg_r": -12, "dy": -0.22}),
        (0.75, {**_STAND, "torso": -4, "head": -4, "arm_l": 30, "arm_r": -30, "dy": 0.0}),
        (1.0, {**_STAND, "torso": -8, "head": -8, "arm_l": 20, "arm_r": -20})]},
    "fall": {"duration": 0.8, "loop": False, "dx": 0.4, "keys": [
        (0.0, {**_STAND, "torso": 10}), (0.5, {**_STAND, "torso": 60, "head": 20, "arm_l": -80, "arm_r": -70, "leg_l": -30, "leg_r": 20, "dy": 0.1}),
        (1.0, {**_STAND, "torso": 88, "head": 30, "arm_l": -100, "arm_r": -60, "leg_l": -40, "leg_r": 10, "shin_l": 20, "dy": 0.42})]},
}


def pose_at(cycle: str, t: float, cycles: dict | None = None) -> dict:
    """The eased pose of ``cycle`` at ``t`` seconds (looping or holding the last key)."""
    c = (cycles or CYCLES)[cycle]
    u = t / c["duration"]
    u = u - math.floor(u) if c["loop"] else min(1.0, max(0.0, u))
    keys = c["keys"]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= u <= t1:
            return lerp_pose(p0, p1, ease((u - t0) / (t1 - t0)) if t1 > t0 else 1.0)
    return dict(keys[-1][1])


def travel(cycle: str, t: float, cycles: dict | None = None) -> float:
    """How far (in body heights) a cycle has carried the body by ``t``."""
    c = (cycles or CYCLES)[cycle]
    return c["dx"] * (t / c["duration"] if c["loop"] else min(1.0, t / c["duration"]))


# --- the principles --------------------------------------------------------------------------------------------------
def squash(vy: float, k: float = 0.35, limit: float = 0.22) -> tuple[float, float]:
    """Vertical speed (body heights per second, positive = down) -> (sx, sy): stretched when flying, squashed on landing;
    the area is preserved (sx * sy = 1)."""
    s = 1.0 - max(-limit, min(limit, k * vy))
    return 1.0 / s, s


@dataclass
class Spring:
    """A damped spring that follows a target angle: follow-through for a scarf, hair or a coat tail. Simulated at a fixed
    step from t = 0, so the state at frame f depends only on f (``angle_at`` replays; callers cache per clip)."""
    stiffness: float = 60.0
    damping: float = 7.0
    gravity: float = 0.0  # a resting offset (a scarf hangs down)

    def series(self, targets: np.ndarray, dt: float) -> np.ndarray:
        x, v = float(targets[0]) + self.gravity, 0.0
        out = np.empty(len(targets), dtype=np.float32)
        for i, tgt in enumerate(targets):
            a = self.stiffness * (float(tgt) + self.gravity - x) - self.damping * v
            v += a * dt
            x += v * dt
            out[i] = x
        return out


def drop_y(t: float, y0: float, floor: float, g: float = 2200.0, bounce: float = 0.45, min_v: float = 40.0) -> float:
    """Where a dropped object is at ``t`` (px, y down): free fall from ``y0`` to ``floor``, then bounces that lose
    ``bounce`` of their speed, resting once the bounce speed is under ``min_v``. Closed form: no state between frames."""
    if t <= 0:
        return y0
    h = max(0.0, floor - y0)
    t_fall = math.sqrt(2 * h / g)
    if t < t_fall:
        return y0 + 0.5 * g * t * t
    t -= t_fall
    v = math.sqrt(2 * g * h) * bounce
    while v >= min_v:
        t_air = 2 * v / g
        if t < t_air:
            return floor - (v * t - 0.5 * g * t * t)
        t -= t_air
        v *= bounce
    return floor


def mouth_at(words: list[dict], t: float, rate: float = 12.0) -> str:
    """The mouth shape at ``t`` from word timings ({text, start, end}): the letters of the word are spoken evenly across
    its time (at most ``rate`` shapes a second); vowels open the mouth (o/u round, a/e/i wide), m/b/p close it, other
    consonants half-open; silence rests."""
    for w in words:
        if w["start"] <= t < w["end"]:
            letters = [c for c in w["text"].lower() if c.isalpha()] or ["a"]
            n = max(1, min(len(letters), int((w["end"] - w["start"]) * rate)))
            step = (w["end"] - w["start"]) / n
            i = min(n - 1, int((t - w["start"]) / step))
            c = letters[int(i * len(letters) / n)]
            if c in CLOSED:
                return "rest"
            if c in VOWEL_O:
                return "open_o"
            if c in VOWEL_E:
                return "open_e"
            return "half"
    return "rest"


# --- the puppet ------------------------------------------------------------------------------------------------------
@dataclass
class Piece:
    image: Image.Image            # RGBA, drawn upright at rest
    pivot: tuple[float, float]    # where it turns, in its own pixels
    parent: str | None = None
    attach: tuple[float, float] = (0.0, 0.0)  # where its pivot sits on the parent, in the parent's pixels
    z: int = 0
    secondary: Spring | None = None  # follow-through instead of a posed angle
    rest: float = 0.0             # resting angle (degrees)


@dataclass
class Puppet:
    pieces: dict[str, Piece]
    height: float                 # body height in px at scale 1 (for dy / dx / squash)
    root: str = "torso"
    mouths: dict[str, Image.Image] = field(default_factory=dict)
    mouth_at_: tuple[float, float] = (0.0, 0.0)  # where the mouth sits on the head

    def order(self) -> list[str]:
        return sorted(self.pieces, key=lambda n: self.pieces[n].z)

    def world(self, pose: dict, root_xy: tuple[float, float], scale: tuple[float, float], flip: bool = False) -> dict:
        """Every piece's (angle, pivot position) in frame pixels from the pose: angles add down the tree, attach points
        turn with their parent. ``scale`` is (sx, sy) about the root's pivot; ``flip`` mirrors the figure."""
        out = {}
        sx, sy = scale
        f = -1.0 if flip else 1.0

        def place(name):
            if name in out:
                return out[name]
            p = self.pieces[name]
            ang = p.rest + pose.get(name, 0.0)
            if p.parent is None:
                out[name] = (ang * f, root_xy)
                return out[name]
            pang, ppos = place(p.parent)
            par = self.pieces[p.parent]
            dx, dy = (p.attach[0] - par.pivot[0]) * sx * f, (p.attach[1] - par.pivot[1]) * sy
            r = math.radians(pang)
            x = ppos[0] + dx * math.cos(r) - dy * math.sin(r)
            y = ppos[1] + dx * math.sin(r) + dy * math.cos(r)
            out[name] = (pang + ang * f, (x, y))
            return out[name]

        for n in self.pieces:
            place(n)
        return out

    def draw(self, frame: Image.Image, pose: dict, root_xy: tuple[float, float], scale=(1.0, 1.0), flip=False,
             mouth: str = "rest") -> Image.Image:
        """Composite the posed puppet onto ``frame`` (RGB or RGBA); back to front by z."""
        W = self.world(pose, root_xy, scale, flip)
        canvas = frame.convert("RGBA")
        sx, sy = scale
        for name in self.order():
            p = self.pieces[name]
            img = p.image
            if name == "head" and mouth in self.mouths:
                img = img.copy()
                m = self.mouths[mouth]
                img.alpha_composite(m, (int(self.mouth_at_[0] - m.width / 2), int(self.mouth_at_[1] - m.height / 2)))
            if flip:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            pivot = ((img.width - p.pivot[0]) if flip else p.pivot[0], p.pivot[1])
            if (sx, sy) != (1.0, 1.0):
                img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.BILINEAR)
                pivot = (pivot[0] * sx, pivot[1] * sy)
            ang, (x, y) = W[name]
            # rotate about the image centre (PIL's expand keeps that centre at the new centre), then find where the
            # pivot went: the centre plus the pivot's offset turned by the same screen rotation world() uses
            rot = img.rotate(-ang, resample=Image.BICUBIC, expand=True)
            cx, cy = img.width / 2, img.height / 2
            r = math.radians(ang)
            px = rot.width / 2 + (pivot[0] - cx) * math.cos(r) - (pivot[1] - cy) * math.sin(r)
            py = rot.height / 2 + (pivot[0] - cx) * math.sin(r) + (pivot[1] - cy) * math.cos(r)
            canvas.alpha_composite(rot, (int(round(x - px)), int(round(y - py))))
        return canvas.convert(frame.mode) if frame.mode != "RGBA" else canvas


# --- a placeholder puppet drawn by code (no paid picture): the proof of concept's actor ----------------------------------
def _piece(w: int, h: int, draw_fn, pivot, **kw) -> Piece:
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im), w, h)
    return Piece(im, pivot, **kw)


def demo_puppet(ink=(38, 30, 24), skin=(236, 190, 150), coat=(58, 96, 128), pants=(70, 60, 70), scarf=(214, 84, 60)) -> Puppet:
    """A stylised adult figure (about six and a half heads) in the ink-and-cel manner: one dark outline, flat colour."""
    L = 6

    def rrect(d, box, fill):
        d.rounded_rectangle(box, radius=min(box[2] - box[0], box[3] - box[1]) // 3, fill=fill, outline=ink, width=L)

    def torso(d, w, h):
        rrect(d, (4, 4, w - 4, h - 4), coat)
    def head(d, w, h):
        d.ellipse((4, 4, w - 4, h - 4), fill=skin, outline=ink, width=L)
        d.ellipse((w * 0.56, h * 0.36, w * 0.68, h * 0.5), fill=ink)   # eye (profile-ish three-quarter)
        d.line((w * 0.5, h * 0.3, w * 0.72, h * 0.28), fill=ink, width=L)  # brow
    def limb(fill):
        return lambda d, w, h: rrect(d, (4, 4, w - 4, h - 4), fill)
    def hand(d, w, h):
        d.ellipse((4, 4, w - 4, h - 4), fill=skin, outline=ink, width=L)
    def scarf_fn(d, w, h):
        d.polygon([(w * 0.2, 4), (w * 0.8, 4), (w * 0.95, h - 4), (w * 0.05, h - 4)], fill=scarf, outline=ink)
        d.line([(w * 0.2, 4), (w * 0.8, 4), (w * 0.95, h - 4), (w * 0.05, h - 4), (w * 0.2, 4)], fill=ink, width=L)

    P = {
        "torso": _piece(120, 190, torso, (60, 170), z=5),
        "head": _piece(130, 150, head, (65, 140), parent="torso", attach=(60, 18), z=6),
        "arm_l": _piece(44, 120, limb(coat), (22, 16), parent="torso", attach=(22, 34), z=3),
        "fore_l": _piece(40, 110, limb(coat), (20, 14), parent="arm_l", attach=(22, 104), z=3),
        "hand_l": _piece(44, 44, hand, (22, 10), parent="fore_l", attach=(20, 96), z=3),
        "arm_r": _piece(44, 120, limb(coat), (22, 16), parent="torso", attach=(98, 34), z=7),
        "fore_r": _piece(40, 110, limb(coat), (20, 14), parent="arm_r", attach=(22, 104), z=7),
        "hand_r": _piece(44, 44, hand, (22, 10), parent="fore_r", attach=(20, 96), z=7),
        "leg_l": _piece(48, 130, limb(pants), (24, 14), parent="torso", attach=(38, 176), z=2),
        "shin_l": _piece(44, 125, limb(pants), (22, 14), parent="leg_l", attach=(24, 116), z=2),
        "leg_r": _piece(48, 130, limb(pants), (24, 14), parent="torso", attach=(82, 176), z=4),
        "shin_r": _piece(44, 125, limb(pants), (22, 14), parent="leg_r", attach=(24, 116), z=4),
        "scarf": _piece(50, 150, scarf_fn, (25, 8), parent="torso", attach=(60, 22), z=8,
                        secondary=Spring(stiffness=40.0, damping=5.0, gravity=0.0), rest=0.0),
    }
    pup = Puppet(P, height=190 + 130 + 110 + 120)
    for name, (w, h, open_) in {"rest": (34, 8, False), "half": (34, 18, True), "open_e": (44, 22, True), "open_o": (28, 30, True)}.items():
        m = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(m)
        if open_:
            d.ellipse((4, 4, w + 4, h + 4), fill=(90, 30, 40), outline=ink, width=4)
        else:
            d.line((4, h // 2 + 4, w + 4, h // 2 + 4), fill=ink, width=5)
        pup.mouths[name] = m
    pup.mouth_at_ = (88, 100)
    return pup


# --- the proof-of-concept clip ---------------------------------------------------------------------------------------
DEMO_WORDS = [("Nobody", 11.2, 11.7), ("told", 11.75, 12.0), ("them", 12.05, 12.35), ("the", 12.5, 12.6), ("bridge", 12.65, 13.1),
              ("was", 13.15, 13.35), ("gone.", 13.4, 13.9), ("So", 14.6, 14.85), ("they", 14.9, 15.1), ("kept", 15.15, 15.45),
              ("walking", 15.5, 16.0), ("anyway.", 16.1, 16.8)]


def demo_script(seconds: float) -> list[tuple[float, float, str]]:
    """(start, end, cycle): walk in, stop, point at the sign, speak, react, idle."""
    return [(0.0, 5.0, "walk"), (5.0, 7.0, "idle"), (7.0, 8.2, "point"), (8.2, 17.0, "idle"), (17.0, 17.9, "react"), (17.9, seconds, "idle")]


def demo_layers(size: tuple[int, int], palette=((28, 40, 64), (52, 72, 104), (96, 120, 140), (160, 140, 110))) -> list[Image.Image]:
    """Three flat layers (sky with a moon, far towers, near street) for parallax; the near layer is drawn last."""
    W, H = size
    sky = Image.new("RGB", (W + W // 10, H), palette[0])
    d = ImageDraw.Draw(sky)
    d.ellipse((W * 0.72, H * 0.12, W * 0.8, H * 0.12 + W * 0.08), fill=(235, 225, 190))
    far = Image.new("RGBA", (W + W // 6, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(far)
    rng = np.random.default_rng(7)
    x = 0
    while x < far.width:
        w, h = int(rng.integers(60, 160)), int(rng.integers(int(H * 0.25), int(H * 0.6)))
        d.rectangle((x, H - h - H * 0.18, x + w, H), fill=palette[1])
        for wy in range(int(H - h - H * 0.18) + 20, int(H - H * 0.2), 36):
            for wx in range(x + 12, x + w - 12, 28):
                if rng.random() < 0.35:
                    d.rectangle((wx, wy, wx + 10, wy + 14), fill=(230, 200, 120))
        x += w + int(rng.integers(10, 40))
    near = Image.new("RGBA", (W + W // 3, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(near)
    d.rectangle((0, H * 0.82, near.width, H), fill=palette[2])
    d.rectangle((0, H * 0.82, near.width, H * 0.84), fill=(40, 40, 50))
    for lx in range(80, near.width, 420):  # lamp posts
        d.rectangle((lx, H * 0.45, lx + 10, H * 0.82), fill=(40, 40, 50))
        d.ellipse((lx - 18, H * 0.41, lx + 28, H * 0.47), fill=(250, 220, 150))
    return [sky, far, near]


def demo_frame(f: int, fps: int, size: tuple[int, int], pup: Puppet, layers: list[Image.Image], script, scarf_series: np.ndarray) -> Image.Image:
    """One frame of the proof of concept: a pure function of f (the scarf's spring series was replayed once)."""
    W, H = size
    t = f / fps
    cam = 0.08 * W * ease(min(1.0, t / 6.0))  # the camera drifts right as the figure enters, then holds
    frame = Image.new("RGB", size, (0, 0, 0))
    for depth, layer in zip((0.1, 0.35, 1.0), layers):
        off = int(cam * depth)
        if layer.mode == "RGBA":
            frame.paste(layer, (-off, 0), layer)
        else:
            frame.paste(layer, (-off, 0))
    # the sign: hangs from a lamp post; at 6.5 s it drops and bounces on the pavement (physics, closed form)
    sign_x = W * 0.62 - cam
    sign_y0, floor = H * 0.47, H * 0.80
    sy_ = drop_y(t - 6.5, sign_y0, floor) if t >= 6.5 else sign_y0
    d = ImageDraw.Draw(frame)
    d.rectangle((sign_x - 60, sy_ - 70, sign_x + 60, sy_), fill=(222, 196, 130), outline=(38, 30, 24), width=5)
    d.rectangle((sign_x - 36, sy_ - 50, sign_x + 36, sy_ - 40), fill=(38, 30, 24))
    d.rectangle((sign_x - 44, sy_ - 30, sign_x + 44, sy_ - 22), fill=(38, 30, 24))
    # the figure
    scale_body = (H * 0.62) / pup.height
    x = -W * 0.08  # enters from off screen
    cyc, t_in = "idle", 0.0
    for s0, s1, c in script:
        if s0 <= t < s1 or (t >= s1 and s1 == script[-1][1]):
            cyc, t_in = c, t - s0
            break
        x += travel(c, s1 - s0) * pup.height * scale_body
    x += travel(cyc, t_in) * pup.height * scale_body - cam
    pose = pose_at(cyc, t_in)
    dt = 1.0 / fps
    vy = (pose_at(cyc, t_in + dt).get("dy", 0.0) - pose.get("dy", 0.0)) / dt
    sx, sy = squash(vy)
    pose["scarf"] = float(scarf_series[min(f, len(scarf_series) - 1)])
    root = (x, H * 0.80 + pose.get("dy", 0.0) * pup.height * scale_body)
    mouth = mouth_at([{"text": w, "start": a, "end": b} for w, a, b in DEMO_WORDS], t)
    flip = 7.0 <= t < 17.0 and False  # the figure points to the right: no flip needed in this staging
    return pup.draw(frame, pose, root, (scale_body * sx, scale_body * sy), flip=flip, mouth=mouth)


def scarf_targets(fps: int, seconds: float, script) -> np.ndarray:
    """The scarf's spring follows the torso's swing (so it lags behind the walk and settles after the stop)."""
    n = int(round(seconds * fps))
    tg = np.zeros(n, dtype=np.float32)
    for f in range(n):
        t = f / fps
        for s0, s1, c in script:
            if s0 <= t < s1:
                p = pose_at(c, t - s0)
                tg[f] = -2.5 * p.get("torso", 0.0) - 60.0 * travel(c, 1.0 / fps) * (1 if CYCLES[c]["dx"] else 0)
                break
    return tg


def demo(out: Path, *, seconds: float = 20.0, fps: int = 24, size: tuple[int, int] = (1280, 720), sheet_every: float = 2.0) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pup, layers, script = demo_puppet(), demo_layers(size), demo_script(seconds)
    series = pup.pieces["scarf"].secondary.series(scarf_targets(fps, seconds, script), 1.0 / fps)
    n = int(round(seconds * fps))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out / "rig_poc.mp4")]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    thumbs = []
    for f in range(n):
        fr = demo_frame(f, fps, size, pup, layers, script, series)
        proc.stdin.write(fr.tobytes())
        if f % int(sheet_every * fps) == 0:
            th = fr.copy()
            th.thumbnail((320, 180))
            thumbs.append((f / fps, th))
    proc.stdin.close()
    proc.wait()
    cols = 5
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (320 * cols, (180 + 20) * rows), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (tt, th) in enumerate(thumbs):
        sheet.paste(th, ((i % cols) * 320, (i // cols) * 200))
        d.text(((i % cols) * 320 + 6, (i // cols) * 200 + 182), f"{tt:.0f} s", fill=(230, 230, 230))
    sheet.save(out / "rig_poc_sheet.jpg", quality=88)
    rep = {"frames": n, "fps": fps, "size": size, "seconds": seconds, "cycles": [c for _, _, c in script], "ffmpeg_rc": proc.returncode,
           "mp4": str(out / "rig_poc.mp4"), "sheet": str(out / "rig_poc_sheet.jpg")}
    (out / "rig_poc.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("demo")
    s.add_argument("--out", required=True)
    s.add_argument("--seconds", type=float, default=20.0)
    s.add_argument("--fps", type=int, default=24)
    s.add_argument("--size", default="1280x720")
    a = ap.parse_args(argv)
    w, h = (int(v) for v in a.size.split("x"))
    rep = demo(Path(a.out), seconds=a.seconds, fps=a.fps, size=(w, h))
    print(json.dumps(rep, indent=1))
    return 0 if rep["ffmpeg_rc"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
