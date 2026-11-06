"""J5 dialogue test, step 2 (creator 2026-11-06 17:25 UTC: "create the animation of the background as much as possible, with Python"):
the four frames of ``j5_collage`` made to move. Free: numpy + OpenCV + ffmpeg, no model, no paid call.

    python -m explainer_engine.blender.j5_background render --collage C --inputs D --out O [--shots S1,S2] [--fps 24] [--size 2560x1440]

``C`` is the output folder of ``j5_collage render`` (its ``work/<shot>/pass_<hero>`` layers are the cards); ``D`` holds ``A1_tent.png``.
Per shot one mp4 segment is written (the chunk of RULE-R1: a finished segment is skipped on a re-run); the segments are joined with
the synthesised camp ambience (``ambience``) into ``j5_dialogue_step2.mp4``.

What moves (all of it a pure function of the time ``t``, so a frame can be re-rendered alone):

- **fire**: the flame of the painted plate is cut out by colour (``flame_mask``) and licked upward by a scrolling noise displacement; its
  brightness and the warm pool of light on the ground breathe with ONE shared flicker ``flicker(t)``; the cards' warm side takes the
  same flicker, so the light on the heroes and the fire agree;
- **smoke** from the fire (fractal noise scrolled upward, widening, cooling in colour), **embers** (70 particles that rise, drift and
  die) and **floating dust/bokeh** in front of everything (depth);
- **banners** of the camp wave from their poles (a travelling sine displacement under each banner's colour mask) and a low **ground
  fog** drifts across the horizon band;
- **camera**: a slow push-in or truck per shot; the plate, the middle hero and the foreground shoulder move by different amounts
  (parallax 0.3 : 0.65 : 1.0), the heroes breathe (0.5 % at 0.25 Hz about the frame bottom);
- one grain layer: fine grain new on every frame, paper mottling fixed.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.blender import j5_collage as J
from explainer_engine.blender import j5_face as F

FPS = 24
OVER = 1.12                                   # the plate is built 12 % larger than the frame so the camera can move on it
FIRE_A1 = (1010.0, 610.0)                     # the flame's centre on the painted A1 (2048 x 1024)
FIRE_BOX_A1 = (920, 490, 1135, 700)           # where the flame colour is looked for
# banners of A1: box (x0, y0, x1, y1), the pole's x and which side of the pole the cloth hangs
BANNERS = [((262, 290, 380, 480), 258, "right"), ((505, 212, 578, 342), 502, "right"), ((1775, 245, 1880, 390), 1772, "right"),
           ((1448, 290, 1525, 414), 1446, "right"), ((1318, 270, 1366, 346), 1362, "left")]
PARALLAX = {"plate": 0.3, "mid": 0.65, "fg": 1.0}
# the spoken lines: (speaker, start in the 12.5 s clip, stem of <stem>.wav / <stem>.cues.json); the starts keep every line clear of the dips
LINES = [("H2", 0.35, "l1_scout"), ("H1", 3.65, "l2_commander"), ("H2", 10.05, "l3_scout")]
DIP = "cut"                                   # between shots: "cut" (straight, as in a film; the creator, 19:14 UTC, dropped the dip to black), or an ffmpeg xfade type
DISSOLVE = 10                                 # frames of the dissolve between two shots (0.42 s); the earlier shot carries them as a tail
# idle motion of a figure, as shares of its card's height (so it scales with the shot): sway of the top, head turn, nod, breath, cloth
IDLE = {"sway": 0.0050, "head_dx": 0.0030, "nod": 0.0022, "breath": 0.0020, "cloth": 0.0012}
# emotion of the faces (brow lift in units of ~2 px at 2560; negative = down): the commander is stern and squints a little while he speaks,
# a listener's brows stay a little raised
EXPR = {"speak_brow": -0.35, "speak_lift": 0.55, "listen_brow": 0.40, "squint": 0.14, "bob": 0.0028}   # bob: the head dips with every open sound (share of card height)
HEAD_M = 0.24                                 # a head is about 0.24 m tall; the head share of a card is HEAD_M / the card's height in metres
SECONDS = {"S1_two_shot": 3.5, "S2_ots_h2_to_h1": 3.0, "S4_close_up_h1": 3.0, "S3_ots_h1_to_h2": 3.0}   # the cut order of the dialogue
# camera per shot: plate zoom, card zoom (start, end), the foreground card's shift in px at 2560 (end - start, x and y) and the pivot
CAMERA = {
    "S1_two_shot": {"zoom_plate": (1.0, 1.04), "zoom_card": (1.0, 1.09), "shift_fg": (0, 0), "pivot": (0.5, 1.0)},
    "S2_ots_h2_to_h1": {"zoom_plate": (1.0, 1.035), "zoom_card": (1.0, 1.06), "shift_fg": (-110, 0), "pivot": (0.5, 1.0)},
    "S4_close_up_h1": {"zoom_plate": (1.0, 1.05), "zoom_card": (1.0, 1.10), "shift_fg": (0, 0), "pivot": (0.5, 1.0)},
    "S3_ots_h1_to_h2": {"zoom_plate": (1.0, 1.035), "zoom_card": (1.0, 1.06), "shift_fg": (110, 0), "pivot": (0.5, 1.0)},
}
# which hero is the foreground shoulder (the one with sigma > 0), the rest are "mid"


def _cv2():
    import cv2
    return cv2


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


# --- the one flicker ------------------------------------------------------------------------------------------------------------

def _vnoise(x: np.ndarray | float, seed: int) -> np.ndarray:
    """1-D value noise in -1..1 (hash of the integer lattice, smoothstep between)."""
    x = np.asarray(x, dtype=np.float64)
    i = np.floor(x).astype(np.int64)
    f = x - i
    def h(k):
        v = np.sin((k + seed * 131) * 12.9898) * 43758.5453
        return (v - np.floor(v)) * 2 - 1
    u = f * f * (3 - 2 * f)
    return h(i) * (1 - u) + h(i + 1) * u


def flicker(t: float) -> float:
    """The fire's light at time t, about -1..1: fast licks (7-17 Hz) over a slow swell (2 Hz)."""
    v = 0.50 * _vnoise(t * 9.0, 1) + 0.30 * _vnoise(t * 17.0 + 3.1, 2) + 0.20 * math.sin(2 * math.pi * 2.1 * t + 0.7)
    return float(np.clip(v * 1.15, -1, 1))


# --- tileable noise ----------------------------------------------------------------------------------------------------------------

def tile_noise(n: int, seed: int, *, octaves=(1, 2, 4, 8)) -> np.ndarray:
    """A tileable fractal noise square, 0..1 (FFT-filtered white noise per octave)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    fx = np.fft.fftfreq(n)[:, None]
    fy = np.fft.fftfreq(n)[None, :]
    r = np.sqrt(fx * fx + fy * fy) + 1e-9
    amp = 1.0
    for o in octaves:
        spec = np.fft.fft2(rng.standard_normal((n, n))) * np.exp(-((r * n / (o * 1.5)) ** 2)) / (r ** 0.2)
        layer = np.real(np.fft.ifft2(spec)).astype(np.float32)
        layer = (layer - layer.mean()) / (layer.std() + 1e-9)
        out += layer * amp
        amp *= 0.55
    out = (out - out.min()) / (out.max() - out.min() + 1e-9)
    return out


def scroll(tile: np.ndarray, x0: float, y0: float, w: int, h: int, scale: float) -> np.ndarray:
    """A w x h window of the (wrapping) tile starting at (x0, y0) tile px, sampled at 1/scale."""
    cv2 = _cv2()
    xs = (np.arange(w, dtype=np.float32)[None, :] / scale + x0) % tile.shape[1]
    ys = (np.arange(h, dtype=np.float32)[:, None] / scale + y0) % tile.shape[0]
    return cv2.remap(tile, np.broadcast_to(xs, (h, w)).copy(), np.broadcast_to(ys, (h, w)).copy(), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


# --- the plate and its masks (built once per shot) ---------------------------------------------------------------------------------------

def flame_mask(a1: np.ndarray) -> np.ndarray:
    """The painted flame of A1 as a soft 0..1 mask (colour test inside the fire's box)."""
    cv2 = _cv2()
    a = a1.astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    x0, y0, x1, y1 = FIRE_BOX_A1
    box = np.zeros(r.shape, bool)
    box[y0:y1, x0:x1] = True
    m = (box & (r > 190) & (g > 70) & ((r - b) > 110)).astype(np.float32)
    return cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 2.0)


def banner_masks(a1: np.ndarray) -> list[dict]:
    cv2 = _cv2()
    a = a1.astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    out = []
    for (x0, y0, x1, y1), pole, side in BANNERS:
        m = np.zeros(r.shape, bool)
        m[y0:y1, x0:x1] = True
        m &= (r > 110) & (g > 35) & (g < 125) & (b < 95) & ((r - g) > 55)
        mf = cv2.GaussianBlur(cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32), (0, 0), 2.0)
        out.append({"box": (x0, y0, x1, y1), "pole": pole, "side": side, "mask": mf})
    return out


def pad_reflect(img: np.ndarray, pad: int, mode: int | None = None) -> np.ndarray:
    cv2 = _cv2()
    return cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT if mode is None else mode)


class ShotAssets:
    """Everything a shot needs that does not change with time: the over-sized plate with its masks (flame, banners, glow) in plate
    pixels, the cards' premultiplied layers (blurred by their depth sigma), the static finishing arrays."""

    def __init__(self, name: str, collage: Path, inputs: Path, size, voice: Path | None = None):
        cv2 = _cv2()
        shot = json.loads(json.dumps(J.SHOTS[name]))
        rep = json.loads((collage / "report.json").read_text(encoding="utf-8"))["shots"][name]["cards"]
        for c in shot["cards"]:
            c["lateral"] = next(x["lateral"] for x in rep if x["id"] == c["id"])   # the side the fire is on, from the collage run
        self.name, self.shot, self.size = name, shot, size
        order_ = list(SECONDS)
        self.start = sum(SECONDS[n] for n in order_[:order_.index(name)])             # where this shot begins in the clip
        self.lines = []                                                               # [{"hero", "start", "cues"}] when a voice is given
        if voice:
            for hero, st, stem in LINES:
                cues = F.load_cues(Path(voice) / f"{stem}.cues.json")
                self.lines.append({"hero": hero, "start": st, "cues": cues})
        W, H = size
        self.Wp, self.Hp = int(round(W * OVER)), int(round(H * OVER))
        a1 = np.asarray(Image.open(inputs / "A1_tent.png").convert("RGB"))
        x0, y0, x1, y1 = shot["plate"]
        cw, ch = x1 - x0, y1 - y0
        ex, ey = cw * (OVER - 1) / 2, ch * (OVER - 1) / 2
        self.crop_e = (x0 - ex, y0 - ey, x1 + ex, y1 + ey)        # A1 coordinates of the over-sized plate (may leave the image)
        self.sx, self.sy = self.Wp / (x1 - x0 + 2 * ex), self.Hp / (y1 - y0 + 2 * ey)
        pad = 600
        padded = pad_reflect(a1, pad)
        self.plate = self._crop(padded, pad, "rgb").astype(np.float32) / 255.0
        self.plate = self._unsharp(self.plate)
        fm = pad_reflect(flame_mask(a1), pad, _cv2().BORDER_CONSTANT)
        self.flame = self._crop(fm, pad, "mask")
        self.fire_xy = ((FIRE_A1[0] - self.crop_e[0]) * self.sx, (FIRE_A1[1] - self.crop_e[1]) * self.sy)
        self.banners = []
        for b in banner_masks(a1):
            bm = self._crop(pad_reflect(b["mask"], pad, _cv2().BORDER_CONSTANT), pad, "mask")
            if bm.max() > 0.05:
                self.banners.append({"mask": bm, "pole_x": (b["pole"] - self.crop_e[0]) * self.sx, "side": b["side"],
                                     "w": (b["box"][2] - b["box"][0]) * self.sx})
        # glow weight: a pool of light on the ground around the fire (wider than tall), in plate pixels
        yy, xx = np.mgrid[0:self.Hp, 0:self.Wp].astype(np.float32)
        rx, ry = 520 * self.sx, 190 * self.sy
        self.glow = np.exp(-(((xx - self.fire_xy[0]) / rx) ** 2 + ((yy - self.fire_xy[1]) / ry) ** 2)).astype(np.float32)
        self.horizon_y = (450 - self.crop_e[1]) * self.sy                    # A1's horizon row
        self.noise = tile_noise(256, 5)
        self.noise2 = tile_noise(256, 9)
        self.smoke_noise = tile_noise(256, 12, octaves=(1, 2, 4))
        self.fog_noise = tile_noise(256, 21, octaves=(1, 2))
        # cards
        s = W / 2560.0
        order = sorted(shot["cards"], key=lambda c: -math.hypot(c["pos"][0] - shot["cam"][0], c["pos"][1] - shot["cam"][1]))
        self.cards = []
        for c in order:
            la = np.asarray(Image.open(self._layer_path(collage, name, c["id"])).convert("RGBA"), np.float32) / 255.0
            a = la[..., 3:4]
            pm = np.dstack([la[..., :3] * a, a])
            pm = J._blur(pm, c["sigma"] * s)
            fg = c["sigma"] > 0
            self.cards.append({"id": c["id"], "pm": pm, "depth": PARALLAX["fg" if fg else "mid"], "fg": fg,
                               "lateral": self._lateral(shot, c), "idle": self._idle_setup(pm, c, fg, shot),
                               "face": None if fg else F.setup(pm, c["img"], self._mapper(shot, c, Path(inputs), W, H)),
                               "blinks": F.blink_times(f"{name}:{c['id']}", self.start, SECONDS[name] + 0.5)})
        # static finishing: vignette, paper (mid + long grain)
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xx2 / W - 0.5) * 1.1, (yy2 / H - 0.5) * 1.25)
        self.vignette = (1 - 0.32 * smooth((r - 0.35) / 0.65))[..., None].astype(np.float32)
        rng = np.random.default_rng(7)
        mid = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 5.0 * s) * 0.045 * s
        long = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 40.0 * s) * 0.26 * s
        self.paper = (mid + long).astype(np.float32)
        self.s = s

    @staticmethod
    def _mapper(shot: dict, c: dict, inputs: Path, W: int, H: int):
        """Sheet pixel -> frame pixel for a hero card, from the same geometry the Blender job gets (``assemble_25d.card_geometry`` on the
        graded card, the card turned to face the camera, then the camera's projection)."""
        cut = J.clean_cut(inputs / f"{c['img']}.cut.png", mirror=c.get("mirror", False))
        ys, xs = np.where(cut[..., 3] > 0.5)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        hero = J.HERO[c["id"]]
        m = hero["height"] / (y1 - y0)
        feet_x = (x0 + x1) / 2
        yaw = math.radians(J.A._facing(c["pos"], shot["cam"]))
        right = np.array([math.cos(yaw), math.sin(yaw)])

        def mapper(x: float, y: float) -> tuple[float, float]:
            wx, wy = np.array(c["pos"], float) + right * ((x - feet_x) * m)
            ndcx, ndcy, _ = J.project(shot["cam"], shot["aim"], shot["lens"], (wx, wy, hero["z0"] + (y1 - y) * m))
            return (ndcx + 1) / 2 * W, (1 - ndcy) / 2 * H
        return mapper

    @staticmethod
    def _idle_setup(pm: np.ndarray, c: dict, fg: bool, shot: dict) -> dict | None:
        """The card's alpha box (padded) and, per row of it, the height above the card's bottom (0..1): what the idle motion needs."""
        ys, xs = np.where(pm[..., 3] > 0.02)
        if not len(ys):
            return None
        pad = 40
        H, W = pm.shape[:2]
        x0, x1, y0, y1 = max(0, xs.min() - pad), min(W, xs.max() + pad), max(0, ys.min() - pad), min(H, ys.max() + pad)
        top, bot = ys.min(), ys.max()
        h = np.clip((bot - np.arange(y0, y1)) / max(1.0, bot - top), -0.2, 1.2).astype(np.float32)
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dist = math.hypot(c["pos"][0] - shot["cam"][0], c["pos"][1] - shot["cam"][1])
        px_per_m = shot["lens"] / 36.0 * W / dist                                   # the card's pixels per metre in this shot
        seen_m = min(J.HERO[c["id"]]["height"], (bot - top) / px_per_m)             # a card cut by the frame shows less than its height
        head = min(0.45, HEAD_M / seen_m)
        return {"box": (x0, y0, x1, y1), "crop": np.ascontiguousarray(pm[y0:y1, x0:x1]), "h": h[:, None], "gx": gx, "gy": gy,
                "Hc": float(bot - top), "head": head, "amp": 0.55 if fg else 1.0,
                "ph": (zlib.crc32(c["id"].encode()) % 628) / 100.0}

    @staticmethod
    def _layer_path(collage: Path, name: str, hero: str) -> Path:
        return next((collage / "work" / name / f"pass_{hero}" / "frames").glob("frame_*.png"))

    @staticmethod
    def _lateral(shot: dict, c: dict) -> float:
        return float(c.get("lateral", 0.0))

    def _crop(self, arr: np.ndarray, pad: int, kind: str) -> np.ndarray:
        cv2 = _cv2()
        x0, y0, x1, y1 = self.crop_e
        # affine from over-sized-plate pixels to padded-A1 pixels
        M = np.array([[1 / self.sx, 0, x0 + pad], [0, 1 / self.sy, y0 + pad]], np.float32)
        interp = cv2.INTER_LANCZOS4 if kind == "rgb" else cv2.INTER_LINEAR
        return cv2.warpAffine(arr, M, (self.Wp, self.Hp), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)

    @staticmethod
    def _unsharp(img: np.ndarray) -> np.ndarray:
        cv2 = _cv2()
        soft = cv2.GaussianBlur(img, (0, 0), 1.6)
        return np.clip(cv2.addWeighted(img, 1.35, soft, -0.35, 0), 0, 1)


# --- the animated elements (in plate pixels) ------------------------------------------------------------------------------------

def animate_plate(A: ShotAssets, t: float) -> np.ndarray:
    """The over-sized plate at time t: flame licked, fire light flickering, smoke, embers, banners, fog."""
    cv2 = _cv2()
    img = A.plate.copy()
    f = flicker(t)
    sx, sy = A.sx, A.sy
    fx, fy = A.fire_xy
    # 1. ground glow and the flame's own brightness
    warm = np.array([1.0 + 0.55 * f, 1.0 + 0.25 * f, 1.0 + 0.04 * f], np.float32)
    img *= 1 + (warm - 1)[None, None, :] * (A.glow * 0.30)[..., None]
    # 2. flame: lick it upward with a scrolling displacement over a window around the fire
    wx0, wx1 = int(max(0, fx - 150 * sx)), int(min(A.Wp, fx + 150 * sx))
    wy0, wy1 = int(max(0, fy - 270 * sy)), int(min(A.Hp, fy + 120 * sy))
    if wx1 - wx0 > 8 and wy1 - wy0 > 8:
        w, h = wx1 - wx0, wy1 - wy0
        patch = img[wy0:wy1, wx0:wx1]
        n1 = scroll(A.noise, 17 + 40 * t, 90 * t, w, h, 0.06 / sx) - 0.5
        n2 = scroll(A.noise2, 61 - 22 * t, 150 * t, w, h, 0.09 / sx) - 0.5
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        env = np.exp(-(((xx + wx0 - fx) / (110 * sx)) ** 2) - (((yy + wy0 - (fy - 60 * sy)) / (150 * sy)) ** 2))
        up = smooth(((fy + 20 * sy) - (yy + wy0)) / (90 * sy))                    # licks grow with height above the logs
        disp_x = (n1 * 2 * 9.0 * sx) * env * up * (1 + 0.5 * f)
        disp_y = (-(np.abs(n2) * 2) * 8.0 * sy - 3.0 * sy * (1 + f)) * env * up
        warped = cv2.remap(patch, xx + disp_x.astype(np.float32), yy + disp_y.astype(np.float32), cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
        fm = A.flame[wy0:wy1, wx0:wx1][..., None]
        bright = 1 + 0.16 * f
        warped = np.clip(warped * (1 + (bright - 1) * np.clip(fm * 1.5, 0, 1)), 0, 1.2)
        img[wy0:wy1, wx0:wx1] = warped
        # 3. smoke rising from the flame tip
        sh, sw = int(380 * sy), int(300 * sx)
        sxo, syo = int(fx - sw / 2), int(fy - 60 * sy - sh)
        if sxo >= 0 and syo >= 0 and sxo + sw <= A.Wp and syo + sh <= A.Hp:
            ys, xs = np.mgrid[0:sh, 0:sw].astype(np.float32)
            hh = (sh - ys) / sh                                         # 0 at the bottom (flame), 1 at the top
            drift = 14 * sx * np.sin(0.8 * t + hh * 4.0) * hh
            nz = scroll(A.smoke_noise, 30 + 8 * t, -60 * t, sw, sh, 0.05 / sx)
            nz2 = scroll(A.smoke_noise, 100 - 5 * t, -35 * t, sw, sh, 0.11 / sx)
            col = np.exp(-(((xs - sw / 2 - drift) / ((34 + hh * 62) * sx)) ** 2))
            prof = smooth(hh * 6) * np.exp(-hh * 2.4)
            al = np.clip(((nz * 0.65 + nz2 * 0.35) - 0.50) * 3.2, 0, 1) * col * prof * 0.42
            al = cv2.GaussianBlur(al, (0, 0), 2.5 * sx)[..., None]
            tint = np.array([0.62, 0.40, 0.30], np.float32) * (1 - hh[..., None]) + np.array([0.34, 0.28, 0.42], np.float32) * hh[..., None]
            tint = tint * (1 + 0.25 * f * (1 - hh[..., None]))
            reg = img[syo:syo + sh, sxo:sxo + sw]
            img[syo:syo + sh, sxo:sxo + sw] = reg * (1 - al) + tint * al
        # 4. embers
        img = embers(img, A, t, f)
    # 5. banners
    for b in A.banners:
        img = wave_banner(img, A, b, t)
    # 6. ground fog on the horizon band
    fw, fh = A.Wp, int(220 * sy)
    fy0 = int(max(0, A.horizon_y - 60 * sy))
    fh = min(fh, A.Hp - fy0)
    nz = scroll(A.fog_noise, 5 * t, 0, fw, fh, 0.45 / sx)
    band = np.exp(-(((np.arange(fh, dtype=np.float32) - 70 * sy) / (60 * sy)) ** 2))[:, None]
    al = (np.clip((nz - 0.45) * 2.0, 0, 1) * band * 0.14)[..., None]
    img[fy0:fy0 + fh] = img[fy0:fy0 + fh] * (1 - al) + np.array([0.30, 0.24, 0.40], np.float32) * al
    return np.clip(img, 0, 1)


def embers(img: np.ndarray, A: ShotAssets, t: float, f: float, n: int = 70) -> np.ndarray:
    cv2 = _cv2()
    fx, fy = A.fire_xy
    sx, sy = A.sx, A.sy
    rng = np.random.default_rng(3)
    ph, vy, amp, om, psi, rad, x0 = (rng.random(n), rng.uniform(55, 130, n), rng.uniform(4, 20, n), rng.uniform(1.5, 4.0, n),
                                     rng.uniform(0, 6.28, n), rng.uniform(0.9, 2.3, n), rng.normal(0, 14, n))
    life = 2.8
    win = (int(fx - 260 * sx), int(fy - 480 * sy), int(520 * sx), int(560 * sy))
    if win[0] < 0 or win[1] < 0 or win[0] + win[2] > A.Wp or win[1] + win[3] > A.Hp:
        return img
    canvas = np.zeros((win[3], win[2]), np.uint8)
    for i in range(n):
        age = ((t / life + ph[i]) % 1.0) * life
        x = fx + (x0[i] + amp[i] * math.sin(om[i] * age + psi[i]) + 9 * age) * sx - win[0]
        y = fy - 55 * sy - vy[i] * age * sy - win[1]
        k = (1 - age / life) ** 1.5 * (0.75 + 0.25 * math.sin(14 * age + psi[i]))
        if k <= 0.02:
            continue
        cv2.circle(canvas, (int(round(x)), int(round(y))), max(1, int(round(rad[i] * sx))), int(255 * min(1, k)), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(canvas.astype(np.float32) / 255.0, (0, 0), 1.2 * sx)
    halo = cv2.GaussianBlur(canvas.astype(np.float32) / 255.0, (0, 0), 5.0 * sx) * 1.6
    add = (glow + halo)[..., None] * np.array([1.0, 0.55, 0.16], np.float32) * (0.9 + 0.2 * f)
    img[win[1]:win[1] + win[3], win[0]:win[0] + win[2]] += add
    return img


def wave_banner(img: np.ndarray, A: ShotAssets, b: dict, t: float) -> np.ndarray:
    """A banner waves from its pole: a travelling sine displacement, zero at the pole, under the banner's own mask."""
    cv2 = _cv2()
    m = b["mask"]
    ys, xs = np.nonzero(m > 0.05)
    if len(xs) == 0:
        return img
    x0, x1, y0, y1 = max(0, xs.min() - 30), min(A.Wp, xs.max() + 30), max(0, ys.min() - 30), min(A.Hp, ys.max() + 30)
    h, w = y1 - y0, x1 - x0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.abs(xx + x0 - b["pole_x"]) / max(1.0, b["w"])                 # 0 at the pole, ~1 at the free edge
    sign = 1.0 if b["side"] == "right" else -1.0
    phase = 2 * math.pi * (0.85 * t - 1.6 * dist - yy / (90 * A.sy)) + b["pole_x"]
    dx = sign * 9.0 * A.sx * dist ** 1.2 * np.sin(phase)
    dy = 3.0 * A.sy * dist * np.sin(phase * 1.3)
    mm = m[y0:y1, x0:x1]
    mm = cv2.GaussianBlur(cv2.dilate(mm, np.ones((9, 9), np.uint8)), (0, 0), 3.0)
    reg = img[y0:y1, x0:x1]
    warped = cv2.remap(reg, xx - (dx * mm).astype(np.float32), yy - (dy * mm).astype(np.float32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    img[y0:y1, x0:x1] = warped
    return img


# --- camera, cards, finishing ----------------------------------------------------------------------------------------------------------

def idle(c: dict, t: float, f: float, A: ShotAssets | None = None) -> np.ndarray:
    """The card's premultiplied layer with its idle motion at time t (a function of t only): the body sways about its bottom edge, the
    chest breathes, the head turns and nods a little, loose cloth and fur ripple with the fire's flicker. Shares of the card's height
    (``IDLE``); two sines of unrelated frequencies per movement so nothing repeats visibly. Returns a card-sized layer."""
    cv2 = _cv2()
    d = c["idle"]
    x0, y0, x1, y1 = d["box"]
    H = d["Hc"] * d["amp"]
    h, ph, tau = d["h"], d["ph"], 2 * math.pi
    sway = math.sin(tau * 0.11 * t + ph) * 0.65 + math.sin(tau * 0.19 * t + 2 * ph) * 0.35
    turn = math.sin(tau * 0.17 * t + 3 * ph) * 0.6 + math.sin(tau * 0.29 * t + ph) * 0.4
    nod = math.sin(tau * 0.23 * t + 5 * ph) * 0.6 + math.sin(tau * 0.41 * t) * 0.4
    breath = math.sin(tau * 0.27 * t + ph)
    body = np.clip(h, 0, 1) ** 1.6
    head = smooth((h - (1 - d["head"] * 1.25)) / (d["head"] * 0.6))                  # 0 on the body, 1 over the head
    dx = IDLE["sway"] * H * sway * body + IDLE["head_dx"] * H * turn * head
    chest = np.exp(-(((h - (1 - d["head"] * 2.6)) / 0.16) ** 2))                      # the shoulders and chest, below the head
    dy = -IDLE["breath"] * H * breath * chest + IDLE["nod"] * H * nod * head
    cloth = IDLE["cloth"] * H * (0.6 + 0.4 * f) * np.sin(tau * (0.8 * t + 3.2 * h) + ph) * (1 - head) * (h < 0.8)
    face = c.get("face")
    if face is None or A is None:
        mx = (d["gx"] - x0 - (dx + cloth)).astype(np.float32)
        my = (d["gy"] - y0 - dy).astype(np.float32)
        return cv2.remap(d["crop"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    T = A.start + t
    dv = F.drive(A.lines, c["id"], T, ph, EXPR)
    op, wf, brow = dv["op"], dv["wf"], dv["brow"]
    close = max(F.closure(T, c["blinks"]), EXPR["squint"] * dv["spk"] if c["id"] == "H1" else 0.0)
    fdx, fdy = F.displacement(face, d["gx"], d["gy"], T, 0.6 * op + 0.4 * dv["op_s"], brow)   # the chin follows a softened opening
    DX = (dx + cloth) + fdx
    DY = dy + fdy - EXPR["bob"] * H * dv["bob"] * head
    mx = (d["gx"] - x0 - DX).astype(np.float32)
    my = (d["gy"] - y0 - DY).astype(np.float32)
    out = cv2.remap(d["crop"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    iy = int(np.clip(face["mouth"]["y"] - y0, 0, DX.shape[0] - 1))
    ix = int(np.clip(face["mouth"]["x"] - x0, 0, DX.shape[1] - 1))
    F.paint(out, face, d["box"], T, close, op, wf, (float(DX[iy, ix]), float(DY[iy, ix])))
    return out


def lerp(a, b, u):
    return a + (b - a) * u


def affine(zoom: float, zoom_y: float, pivot: tuple[float, float], shift: tuple[float, float]) -> np.ndarray:
    """Forward 2x3 matrix: scale about ``pivot`` (px) then shift."""
    px, py = pivot
    return np.array([[zoom, 0, px - zoom * px + shift[0]], [0, zoom_y, py - zoom_y * py + shift[1]]], np.float32)


def render_frame(A: ShotAssets, t: float, u: float, frame: int) -> np.ndarray:
    """Frame at time t into the shot (u = t / duration, 0..1) as uint8 RGB."""
    cv2 = _cv2()
    W, H = A.size
    cam = CAMERA[A.name]
    s = A.s
    f = flicker(t)
    base = animate_plate(A, t)
    zp = lerp(*cam["zoom_plate"], u)
    sh = np.array(cam["shift_fg"], np.float32) * s * u
    px = sh[0] * PARALLAX["plate"]
    py = sh[1] * PARALLAX["plate"]
    cxo, cyo = A.Wp / 2.0, A.Hp / 2.0
    M = np.array([[1 / zp, 0, cxo - px - W / 2 / zp], [0, 1 / zp, cyo - py - H / 2 / zp]], np.float32)
    plate = cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    img = J._blur(plate, A.shot["sigma_plate"] * s)
    zc = lerp(*cam["zoom_card"], u)
    pivot = (cam["pivot"][0] * W, cam["pivot"][1] * H)
    for c in A.cards:
        d = c["depth"]
        z = 1 + (zc - 1) * d
        Mc = affine(z, z, pivot, (sh[0] * d, sh[1] * d))
        src = c["pm"]
        if c["idle"]:
            x0, y0, x1, y1 = c["idle"]["box"]
            src = np.zeros_like(c["pm"])
            src[y0:y1, x0:x1] = idle(c, t, f, A)
        pm = cv2.warpAffine(src, Mc, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        # the fire's flicker on the warm side of the card
        side = 0.5 + 0.5 * c["lateral"] * np.linspace(-1, 1, W, dtype=np.float32)[None, :, None]
        gain = 1 + 0.12 * f * smooth(side * 1.2 - 0.1)
        rgb = pm[..., :3] * gain * np.array([1.0, 0.97 - 0.02 * f, 0.92 - 0.05 * f], np.float32)
        a2 = pm[..., 3:4]
        img = img * (1 - a2) + rgb
    img = dust(img, A, t, f, frame)
    return finish(img, A, frame)


def dust(img: np.ndarray, A: ShotAssets, t: float, f: float, frame: int, n: int = 16) -> np.ndarray:
    """Out-of-focus embers and dust drifting in front of everything (half-resolution bokeh)."""
    cv2 = _cv2()
    W, H = A.size
    hw, hh = W // 2, H // 2
    rng = np.random.default_rng(11)
    x0, y0, vx, vy, rad, ph = (rng.random(n) * hw, rng.random(n) * hh, rng.uniform(-6, 10, n), rng.uniform(-22, -8, n),
                               rng.uniform(10, 38, n) * A.s, rng.random(n) * 6.28)
    canvas = np.zeros((hh, hw), np.uint8)
    for i in range(n):
        x = (x0[i] + vx[i] * t * A.s * 3) % hw
        y = (y0[i] + vy[i] * t * A.s * 3) % hh
        k = 0.5 + 0.5 * math.sin(0.9 * t + ph[i])
        cv2.circle(canvas, (int(x), int(y)), max(2, int(rad[i])), int(60 + 70 * k), -1, cv2.LINE_AA)
    blur = cv2.GaussianBlur(canvas.astype(np.float32) / 255.0, (0, 0), 6 * A.s)
    blur = cv2.resize(blur, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return img + blur * np.array([1.0, 0.62, 0.30], np.float32) * (0.10 + 0.04 * f)


def finish(img: np.ndarray, A: ShotAssets, frame: int) -> np.ndarray:
    cv2 = _cv2()
    s = A.s
    hi = np.clip(img - np.array([0.62, 0.40, 0.18], np.float32), 0, 1) * np.array([1.0, 0.75, 0.4], np.float32)
    small = cv2.resize(hi, (A.size[0] // 4, A.size[1] // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(cv2.GaussianBlur(small, (0, 0), 30 * s / 4), A.size, interpolation=cv2.INTER_LINEAR)
    x = 1 - (1 - np.clip(img, 0, 1)) * (1 - bloom * 0.55)
    x = x * A.vignette
    rng = np.random.default_rng(1000 + frame)
    W, H = A.size
    fine = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8 * s) * 0.017 * math.sqrt(s)
    g = fine * 2.2 + A.paper
    lum = x.mean(-1, keepdims=True)
    x = x + g[..., None] * (0.55 + 0.9 * (1 - np.abs(2 * lum - 1)))
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


# --- ambience (synthesised, free) -----------------------------------------------------------------------------------------------------

def ambience(seconds: float, sr: int = 48000, seed: int = 4) -> np.ndarray:
    """Stereo camp ambience, float -1..1: fire crackle (Poisson clicks of filtered noise), a low roar and slow wind. No voice."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    out = np.zeros((2, n), np.float64)
    for ch in range(2):
        crack = np.zeros(n)
        for rate, amp in ((16.0, 0.10), (1.4, 0.45)):
            for tt in rng.uniform(0, seconds, int(rate * seconds)):
                i = int(tt * sr)
                ln = int(rng.uniform(0.002, 0.012) * sr)
                burst = rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 4)) * amp * rng.pareto(3.0) * 0.8
                crack[i:i + ln] += burst[: max(0, min(ln, n - i))]
        crack = sosfilt(butter(2, [900, 7000], "band", fs=sr, output="sos"), crack)
        roar = sosfilt(butter(2, 260, "low", fs=sr, output="sos"), rng.standard_normal(n)) * 0.55
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * np.arange(n) / sr + rng.uniform(0, 6))
        wind = sosfilt(butter(2, [120, 520], "band", fs=sr, output="sos"), rng.standard_normal(n)) * lfo * 0.45
        out[ch] = crack * 1.0 + roar * 0.35 + wind * 0.30
    out /= np.max(np.abs(out)) + 1e-9
    out *= 0.5
    fade = int(0.25 * sr)
    out[:, :fade] *= np.linspace(0, 1, fade)
    out[:, -fade:] *= np.linspace(1, 0, fade)
    return out.T.astype(np.float32)


# --- render ---------------------------------------------------------------------------------------------------------------------------

def render_segment(name: str, collage: Path, inputs: Path, out: Path, *, size=(2560, 1440), fps=FPS, seconds=None, tail: int = 0, voice: Path | None = None) -> Path:
    """One shot as an mp4. ``tail`` frames more than the shot lasts are drawn with the camera at rest: the dissolve into the next shot
    uses them. The camera moves on an ease-in-out curve, so every shot starts and ends slowly."""
    mp4 = out / "segments" / f"{name}.mp4"
    if mp4.exists():
        return mp4
    mp4.parent.mkdir(parents=True, exist_ok=True)
    A = ShotAssets(name, collage, inputs, size, voice)
    secs = seconds or SECONDS[name]
    n = round(secs * fps)
    tmp = mp4.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n + tail):
        frame = render_frame(A, i / fps, float(smooth(min(1.0, i / max(1, n - 1)))), i)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError(f"ffmpeg failed on {name}")
    tmp.replace(mp4)
    return mp4


def _room_ir(sr: int) -> np.ndarray:
    """A short synthetic room: exponentially decaying noise, 0.3 s tail, a few early reflections; unit energy (the same for every line)."""
    rng = np.random.default_rng(3)
    n = int(0.3 * sr)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.07 * sr))
    for d, g in ((0.011, 0.5), (0.019, 0.35), (0.031, 0.25)):
        ir[int(d * sr)] += g * 8
    ir[0] = 0.0
    return (ir / np.sqrt((ir ** 2).sum())).astype(np.float64)


def mix_voice(amb: np.ndarray, voice: Path, sr: int = 48000) -> np.ndarray:
    """The camp ambience under the spoken lines: each line is placed at its start (``LINES``), the ambience is lowered by 6 dB while anyone
    speaks (0.2 s ramps), the mix is peak-limited to 0.9. A rough mix for review, not the audio spine's levelling."""
    from math import gcd
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    mix = amb.astype(np.float64) * 0.55
    duck = np.ones(len(amb))
    voices = np.zeros_like(mix)
    for hero, st, stem in LINES:
        rate, x = wavfile.read(str(Path(voice) / f"{stem}.wav"))
        x = x.astype(np.float64) / 32768.0
        g = gcd(sr, rate)
        x = resample_poly(x, sr // g, rate // g)
        act = x[np.abs(x) > 0.02 * np.abs(x).max()]                # every line to the same speech RMS: no level jump between speakers
        x *= 0.16 / (np.sqrt((act ** 2).mean()) + 1e-9)
        x = np.tanh(x * 1.2) / 1.2                              # soft limit instead of a hard peak scale
        fade = int(0.02 * sr)                                    # 20 ms in and out: no click at the edges of a line
        x[:fade] *= np.linspace(0, 1, fade)
        x[-fade:] *= np.linspace(1, 0, fade)
        i = int(st * sr)
        n = min(len(x), len(voices) - i)
        voices[i:i + n, :] += x[:n, None]
        ramp = int(0.4 * sr)
        lo, hi = max(0, i - ramp), min(len(duck), i + n + ramp)
        env = np.ones(hi - lo)
        env[:] = 10 ** (-6 / 20)
        env[:ramp] = np.linspace(1, 10 ** (-6 / 20), ramp)[: len(env[:ramp])]
        env[-ramp:] = np.linspace(10 ** (-6 / 20), 1, ramp)[-len(env[-ramp:]):]
        duck[lo:hi] = np.minimum(duck[lo:hi], env)
    room = _room_ir(sr)                                          # one small room for every voice, so the lines share a space
    wet = np.stack([np.convolve(voices[:, c], room)[: len(voices)] for c in range(2)], axis=1)
    voices = voices * 0.88 + wet * 0.22
    out = mix * duck[:, None] + voices
    return (out / max(1.0, np.abs(out).max() / 0.9)).astype(np.float32)


def join(out: Path, names: list[str], *, fps=FPS, transition: str = DIP, crf: int = 14, name: str = "j5_dialogue_step3.mp4",
         voice: Path | None = None) -> Path:
    import wave
    total = sum(SECONDS[n] for n in names)
    amb = ambience(total)
    if voice:
        amb = mix_voice(amb, Path(voice))
    wav = out / ("dialogue_mix.wav" if voice else "ambience.wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(48000)
        w.writeframes((np.clip(amb, -1, 1) * 32767).astype("<i2").tobytes())
    final = out / name
    if transition == "cut":                                     # straight cuts: the segments are joined as they are
        lst = out / "segments" / "list.txt"
        lst.write_text("".join(f"file '{(out / 'segments' / (n + '.mp4')).resolve()}'\n" for n in names))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav), "-c:v", "libx264",
                        "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
                       check=True)
        return final
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for n in names:
        cmd += ["-i", str(out / "segments" / (n + ".mp4"))]
    cmd += ["-i", str(wav)]
    d = DISSOLVE / fps
    chain, last, at = [], "[0:v]", 0.0
    for k in range(1, len(names)):
        at += SECONDS[names[k - 1]]                     # each shot's tail carries the dissolve, so the cuts stay on the nominal clock
        lab = f"[x{k}]"
        chain.append(f"{last}[{k}:v]xfade=transition={transition}:duration={d:.4f}:offset={at:.4f}{lab}")
        last = lab
    cmd += ["-filter_complex", ";".join(chain) if chain else "[0:v]null[x0]", "-map", last if chain else "[x0]",
            "-map", f"{len(names)}:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-b:a", "192k", "-shortest", str(final)]
    subprocess.run(cmd, check=True)
    return final


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--collage", required=True)
    r.add_argument("--inputs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--size", default="2560x1440")
    r.add_argument("--shots", default=None)
    r.add_argument("--seconds", type=float, default=None)
    r.add_argument("--no-join", action="store_true")
    r.add_argument("--transition", default=DIP, help="ffmpeg xfade type between shots: fade, fadeblack, fadegrays, ...")
    r.add_argument("--crf", type=int, default=14)
    r.add_argument("--voice", default=None, help="folder with <stem>.wav and <stem>.cues.json of the lines (LINES)")
    r.add_argument("--name", default="j5_dialogue_step3.mp4")
    a = ap.parse_args(argv)
    W, H = (int(x) for x in a.size.split("x"))
    names = a.shots.split(",") if a.shots else list(SECONDS)
    out = Path(a.out)
    join_names = list(SECONDS)
    for n in names:
        tail = DISSOLVE if (n != list(SECONDS)[-1] and a.transition != "cut") else 0       # the last shot of the cut order has nothing to dissolve into
        print("segment", n, render_segment(n, Path(a.collage), Path(a.inputs), out, size=(W, H), seconds=a.seconds, tail=tail,
                                           voice=Path(a.voice) if a.voice else None), flush=True)
    if not a.no_join and not a.seconds:
        print("final", join(out, join_names, transition=a.transition, crf=a.crf, name=a.name, voice=Path(a.voice) if a.voice else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
