"""Layered 2.5D that reads as movement (v4.3 plan P5, RT-05 in docs/EPISODE_FIRST.md).

One picture becomes a shot that is alive beyond the camera:

1. Real depth: Depth-Anything V2 Small (``production/depth.py``, free, CPU). Without the model the depth is a plain
   bottom-near ramp and the report says ``depth_basis: formula`` (REVIEW), never silently.
2. Planes, not one warped sheet: the depth is split into up to ``PLANES`` planes (1-D k-means on the disparity, so each
   plane holds real content). Plane ``k`` is drawn as an RGBA sheet whose alpha is "this depth or nearer" (feathered) and
   whose colours under the nearer planes are filled by OpenCV Telea inpainting (radius from BP-182), so when a near plane
   moves the strip it uncovers shows a fill, never a hole or a smeared copy of the near object. Each plane moves with its
   own affine transform, its parallax proportional to its disparity; the near plane travels ``NEAR_TRAVEL`` of the width.
3. Faces stay rigid: YuNet face boxes (``tools/yunet``) move the plane thresholds out of every face's depth range, so a face
   sits in one plane and moves with one affine transform (no per-pixel warp inside it). The report measures it.
4. Motion imitation (``shot.motion_imitation``): camera (push, pull, truck, crane, orbit_small, handheld, rack_focus), light
   (fire_flicker, lightning, sun_shaft_drift), atmosphere (ash_fall, smoke_drift, mist, rain, embers, dust), surface
   (water_shimmer, heat_haze, foliage_sway: masked displacement inside a region), subject (subject_sway: the face's plane
   breathes and sways rigidly) and impact (shake). The creator's rule (plan 0.4, Q4, 2026-11-12) asks for at least two
   moving systems from different families among atmosphere, light, surface and subject (BP-185).
5. Sound events drive effects (plan P5.6): a ``boom`` at frame N gives ``shake`` + ``lightning`` at N (``EVENT_EFFECTS``).
6. Every frame is a pure function of its number: all randomness is drawn once from the shot's seed, so a chunk rendered in
   another process gives the same pixels (the report proves it on two frames of a fresh scene).

W2 (2026-11-13, D-135; L25-01..L25-06 in docs/EPISODE_FIRST.md): the camera takes up to two ordered path segments
(``from_frame``/``to_frame`` or the words of ``episode/events``, the one resolver), each with its easing and an optional
``hold_frames`` rest; their moves add up frame by frame, so a second segment starts where the first ended (no jump). A
``motion_profile`` (portrait, landscape, battle, architecture, document, object) says which moves suit the picture, caps their
strength and sets how far the far planes follow the near one (a document is flat; a battle has depth); the gates and their
bands are the same for every profile. ``cloth_flap`` (a flag or a sail ripples inside its region, waves running from the pole)
and ``cloud_drift`` (the sky inside its region drifts and slowly changes shape) are new surface and atmosphere effects; both
need a region. A shake and a timed lightning come only from an authored event (an item's frame or word, or an authored sound
event), never from a word of the read.

A start/end picture pair is cross-moved only when the two share the layout (``layout_similarity``); otherwise the end
picture is not faked into the shot and the report asks for two shots.
"""
from __future__ import annotations

import hashlib
import math
import subprocess
import time
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ContractError
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

FAMILIES = {
    "camera": ("push", "pull", "truck", "crane", "orbit_small", "handheld", "rack_focus"),
    "light": ("fire_flicker", "lightning", "sun_shaft_drift"),
    "atmosphere": ("ash_fall", "smoke_drift", "mist", "rain", "embers", "dust", "cloud_drift"),
    "surface": ("water_shimmer", "heat_haze", "foliage_sway", "cloth_flap"),
    "subject": ("subject_sway",),
    "impact": ("shake",),
}
FAMILY_OF = {e: fam for fam, effects in FAMILIES.items() for e in effects}
EFFECTS = tuple(FAMILY_OF)
PATH_MOVES = ("push", "pull", "truck", "crane", "orbit_small")
ALIVE_FAMILIES = ("atmosphere", "light", "surface", "subject")
ALIVE_MIN = int(SR.T("BP-185", "families_min"))
NEEDS_REGION = ("water_shimmer", "heat_haze", "foliage_sway", "cloth_flap", "cloud_drift")
SEGMENTS_MAX = 2
EASINGS = ("ease_in_out", "ease_in", "ease_out", "linear")
# W2 motion profiles (house defaults, D-135): the moves that suit the picture, their strength cap, how far the farthest plane
# follows the near one in a truck or a crane (a document is flat: everything moves together), and the handheld cap
PROFILES = {
    "portrait": {"moves": ("push", "pull", "orbit_small", "crane"), "strength_max": 1.0, "far_share": 0.25, "handheld_max": 0.6},
    "landscape": {"moves": ("push", "pull", "truck", "crane", "orbit_small"), "strength_max": 1.2, "far_share": 0.15,
                  "handheld_max": 0.8},
    "battle": {"moves": ("push", "pull", "truck", "crane", "orbit_small"), "strength_max": 1.5, "far_share": 0.2,
               "handheld_max": 1.5},
    "architecture": {"moves": ("push", "pull", "truck", "crane"), "strength_max": 1.0, "far_share": 0.3, "handheld_max": 0.3},
    "document": {"moves": ("push", "pull", "truck", "crane"), "strength_max": 1.0, "far_share": 0.85, "handheld_max": 0.2},
    "object": {"moves": ("push", "pull", "orbit_small", "truck"), "strength_max": 1.0, "far_share": 0.2, "handheld_max": 0.5},
}
TIMED = ("shake", "lightning", "rack_focus")
EVENT_EFFECTS = {"boom": ("shake", "lightning"), "eruption": ("shake", "lightning"), "impact": ("shake",),
                 "thunder": ("lightning",), "flash": ("lightning",)}

PLANES = 4
RENDERER_VERSION = "layers25d/2"          # W2 (D-135): the clip cache keys on it
LAYERS_MIN = int(SR.T("BP-181", "parallax_layers_min"))
NEAR_TRAVEL = 0.05          # the near plane's travel end to end, share of the width (plan P5.2: target 4-6 %)
TRAVEL_BAND = (0.04, 0.06)
TRAVEL_MAX = float(SR.T("BP-182", "parallax_factor_max"))
FAR_SHARE = 0.2             # a truck moves the farthest plane this share of the near plane (a real camera pans a little)
PUSH_SCALE = 0.06           # camera scale change of a push at strength 1 (BP-181 range below)
MOVE_MIN, MOVE_MAX = float(SR.T("BP-181", "still_move_min")), float(SR.T("BP-181", "still_move_max"))
DEPTH_PUSH = 0.04           # the near plane grows this much more than the far one during a push
BAND = 0.03                 # margin round a face's depth range, in disparity units (0..1)
EDGE_SIGMA = 1.2            # plane edges are hard in depth and feathered this much in pixels (at 1920 wide), so a depth
                            # slope never shows a mix of a plane and its fill (the first renders smeared every slope)
INPAINT_R = float(SR.T("BP-182", "inpaint_radius_px"))
HAND_TR, HAND_ROT = 0.003, 0.15   # handheld: share of the width, degrees, at strength 1
SWAY_DEG, BREATH = 0.35, 0.003
RACK_S = float(SR.T("BP-129", "rack_focus_s"))
RACK_SIGMA = 5.0            # blur (px at 1080p) of a plane one full disparity away from focus
SHAKE_S = float(SR.T("BP-24", "house_decay_s"))
SHAKE_H = float(SR.T("BP-24", "house_amplitude_h"))
SHAKE_MAX_H = float(SR.T("BP-24", "amplitude_max_h"))
FLASH_WHITE = float(SR.T("BP-26", "flash_white_max"))
FLASHES_PER_S = int(SR.T("BP-26", "flashes_per_s_max"))
FLASH_FRAMES_MAX = int(SR.T("BP-183", "impact_flash_frames_max"))
FROZEN_FRAMES_MAX = int(SR.T("BP-174", "frozen_frames_max"))
FROZEN_DIFF = float(SR.T("BP-164", "frozen_diff_max"))
ANALYSIS = tuple(SR.T("BP-164", "analysis_size"))
CPU_SPF = float(SR.T("BP-182", "cpu_sec_per_frame_max"))
LAYOUT_SAME_MIN = 0.6       # engineering default: start and end pictures with less layout correlation are two shots
TEAR_REVIEW = 1.25          # engineering default: seam gradient against frame 0's
FACE_DRIFT_REVIEW = 0.20    # engineering default: landmark geometry drift. YuNet's own noise on a RIGID copy of the Toba close-up
                            # (S01_SH004: scaled 1.03-1.10, turned up to 1 degree, blurred) measured up to 0.135 (median 0.07),
                            # so 0.08 flagged the detector, not the face; 0.20 is 1.5x that noise
FACE_SURE = 0.85            # engineering default: a YuNet score the hero's face reaches (0.94 on the Toba close-up) and a
                            # storm cloud does not (0.72 on S01_SH009); faces under it stay rigid but steer nothing
FACE_ONE_PLANE = 0.98
START_DIFF_REVIEW = 2.0     # engineering default: frame 0's planes are the picture (only the edge feather differs)


def _seed(sid: str) -> int:
    return int(hashlib.sha256(sid.encode("utf-8")).hexdigest()[:8], 16)


def smooth(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


# --- the plan: the script's motion imitation, checked ---------------------------------------------------------------------

def _region(e: dict, sid: str):
    r = e.get("region")
    if r is None:
        return None
    if not (isinstance(r, (list, tuple)) and len(r) == 4 and all(isinstance(v, (int, float)) for v in r)
            and 0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1):
        raise ContractError(f"{sid}: {e['effect']} region must be [x0, y0, x1, y1] in 0..1 with x0 < x1, y0 < y1, not {r!r}")
    return [float(v) for v in r]


def plan(shot: dict, fps: int = 24, events: list[dict] | None = None, script: dict | None = None,
         spine: list[dict] | None = None) -> dict:
    """Resolve ``shot.motion_imitation`` (and the sound plan's ``events``: ``[{frame, kind}]``) into frames and strengths.

    An unknown effect, a surface effect without a region, two path moves, or an ``at_word`` that is not spoken is a
    ``ContractError``; a shot without motion imitation plans nothing and its ``alive`` gate FAILs."""
    from explainer_engine.episode import events as E
    sid = str(shot.get("shot_id") or "shot")
    frames = max(1, int(round(float(shot.get("target_duration_seconds", 4.0)) * fps)))
    evs = [e for e in E.visual_events(shot, script or {}, spine, fps) if e["source"] == "motion_imitation"] \
        if shot.get("motion_imitation") else []
    profile_name = shot.get("motion_profile")
    if profile_name is not None and profile_name not in PROFILES:
        raise ContractError(f"{sid}: motion_profile {profile_name!r} is not one of {', '.join(PROFILES)}")
    prof = PROFILES.get(profile_name or "", None)
    cameras, handheld, rack, effects, impacts, capped = [], None, None, [], [], []
    for j, e in enumerate(shot.get("motion_imitation") or []):
        name = e.get("effect")
        if name not in FAMILY_OF:
            raise ContractError(f"{sid}: unknown motion imitation {name!r} (known: {', '.join(EFFECTS)})")
        s = float(e.get("strength", 1.0))
        if not 0.0 < s <= 1.5:
            raise ContractError(f"{sid}: {name} strength {s} is outside (0, 1.5]")
        ev = evs[j] if j < len(evs) else None
        at = (ev["start_frame"] if ev else None) if (e.get("at_frame") is not None or e.get("at_word")) else None
        if at is not None and not 0 <= int(at) < frames:
            raise ContractError(f"{sid}: {name} at frame {at} is outside the shot's {frames} frames")
        if name in PATH_MOVES:
            d = e.get("direction", "right" if name in ("truck", "orbit_small") else "up")
            if d not in ("left", "right", "up", "down"):
                raise ContractError(f"{sid}: {name} direction {d!r}")
            easing = e.get("easing", "ease_in_out")
            if easing not in EASINGS:
                raise ContractError(f"{sid}: {name} easing {easing!r} is not one of {', '.join(EASINGS)}")
            if prof is not None:
                if name not in prof["moves"]:
                    raise ContractError(f"{sid}: the {profile_name} profile does not move by {name} (it allows "
                                        f"{', '.join(prof['moves'])})")
                if s > prof["strength_max"]:
                    capped.append(f"{name} {s} -> {prof['strength_max']}")
                    s = prof["strength_max"]
            cameras.append({"move": name, "strength": s, "direction": d, "from": int(ev["start_frame"]) if ev else 0,
                            "to": int(ev["end_frame"]) if ev else frames, "easing": easing,
                            "hold": int(e.get("hold_frames", 0)), "event_id": ev["event_id"] if ev else None,
                            "timed": e.get("from_frame") is not None or e.get("at_word") is not None
                            or e.get("at_frame") is not None})
        elif name == "handheld":
            handheld = min(s, prof["handheld_max"]) if prof else s
        elif name == "rack_focus":
            to = e.get("to", "near")
            if to not in ("near", "far"):
                raise ContractError(f"{sid}: rack_focus to {to!r} (near or far)")
            rack = {"at": int(at) if at is not None else frames // 2, "to": to, "strength": s}
        elif name == "shake":
            if at is None:
                raise ContractError(f"{sid}: shake needs at_frame, at_word or a sound event (BP-24: only on an impact)")
            impacts.append({"frame": int(at), "effects": ["shake"], "strength": s, "kind": "script"})
        else:
            if name in NEEDS_REGION and e.get("region") is None:
                raise ContractError(f"{sid}: {name} is a masked displacement and needs a region [x0, y0, x1, y1]")
            fx = {"effect": name, "family": FAMILY_OF[name], "strength": s, "region": _region(e, sid)}
            if e.get("origin") is not None:
                fx["origin"] = [float(v) for v in e["origin"]]
            if name == "lightning" and at is not None:
                impacts.append({"frame": int(at), "effects": ["lightning"], "strength": s, "kind": "script"})
                fx["timed"] = True
            effects.append(fx)
    if events is None:   # the script's sound events that the picture answers (plan P5.6)
        events = [{"frame": int(round(float(e["at_s"]) * fps)), "kind": e["picture_event"]}
                  for e in shot.get("sound_events") or [] if e.get("picture_event") and e.get("at_s") is not None]
    for ev in events:
        kind = ev.get("kind")
        if kind in EVENT_EFFECTS and 0 <= int(ev["frame"]) < frames:
            impacts.append({"frame": int(ev["frame"]), "effects": list(EVENT_EFFECTS[kind]), "strength": 1.0,
                            "kind": kind})
    if any("lightning" in i["effects"] for i in impacts) and not any(f["effect"] == "lightning" for f in effects):
        effects.append({"effect": "lightning", "family": "light", "strength": 1.0, "region": None, "timed": True})
    impacts.sort(key=lambda i: i["frame"])
    if len(cameras) > SEGMENTS_MAX:
        raise ContractError(f"{sid}: {len(cameras)} camera paths; a shot has at most {SEGMENTS_MAX} ordered segments")
    if len(cameras) == 2:
        if not all(c["timed"] for c in cameras):
            raise ContractError(f"{sid}: two camera paths ({cameras[0]['move']}, {cameras[1]['move']}) need their frames "
                                "(from_frame/to_frame or at_word/until_word): one shot has one path otherwise")
        cameras.sort(key=lambda c: c["from"])
        a, b = cameras
        if a["to"] + a["hold"] > b["from"]:
            raise ContractError(f"{sid}: camera segment {b['move']} starts at frame {b['from']}, before {a['move']} ends and "
                                f"rests (frame {a['to'] + a['hold']})")
    for c in cameras:
        if not 0 <= c["from"] < c["to"] <= frames:
            raise ContractError(f"{sid}: camera segment {c['move']} [{c['from']}, {c['to']}) is outside the shot's {frames} frames")
    fams = sorted({f["family"] for f in effects} | ({"subject"} if any(f["effect"] == "subject_sway" for f in effects)
                                                    else set()))
    return {"shot_id": sid, "frames": frames, "fps": fps, "seed": _seed(sid), "camera": cameras[0] if cameras else None,
            "cameras": cameras, "handheld": handheld, "profile": profile_name, "far_share": prof["far_share"] if prof
            else FAR_SHARE, "capped": capped, "events": evs,
            "rack": rack, "effects": effects, "impacts": impacts, "families": [f for f in fams if f in ALIVE_FAMILIES]}


# --- the camera: one affine per plane and frame -----------------------------------------------------------------------

def _wave(t: float, seed: int, k: int, freqs=(0.31, 0.53, 0.97)) -> float:
    """A smooth, seeded, bounded (-1..1) wave: three sines with phases from the seed (pure in t)."""
    ph = [((seed >> (3 * i + k)) % 628) / 100.0 for i in range(3)]
    return sum(math.sin(2 * math.pi * f * t + p) * w for f, p, w in zip(freqs, ph, (0.55, 0.3, 0.15)))


def shake_offset(p: dict, f: int, height: float) -> tuple[float, float]:
    """BP-24: the house shake (amplitude and decay from the registry) after each impact; nothing before it."""
    dx = dy = 0.0
    for imp in p["impacts"]:
        if "shake" not in imp["effects"] or f < imp["frame"]:
            continue
        t = (f - imp["frame"]) / p["fps"]
        if t > SHAKE_S:
            continue
        a = min(SHAKE_H * imp["strength"], SHAKE_MAX_H) * height * math.exp(-3.0 * t / SHAKE_S)
        dx += a * math.sin(2 * math.pi * 11.0 * t + 0.4)
        dy += 0.7 * a * math.cos(2 * math.pi * 13.0 * t)
    return dx, dy


def _ease(name: str, u: float) -> float:
    u = min(1.0, max(0.0, u))
    if name == "ease_in":
        return u * u
    if name == "ease_out":
        return 1.0 - (1.0 - u) ** 2
    if name == "linear":
        return u
    return float(smooth(u))


def segment_u(seg: dict, f: int, n: int) -> float:
    """A segment's eased progress at ``f``: 0 before its first frame, 1 from its last frame on (half-open [from, to))."""
    a, b = seg.get("from", 0), seg.get("to", n)
    return _ease(seg.get("easing", "ease_in_out"), (f - a) / max(1, b - 1 - a))


def plane_view(p: dict, f: int, w_k: float, w_focus: float) -> dict:
    """The camera for one plane at frame ``f``: centre offset (share of the width), scale, rotation (degrees). The segments'
    moves add up (scale multiplies), so the view is continuous across a segment change."""
    n = p["frames"]
    t = f / p["fps"]
    cx = cy = 0.0
    scale, rot = 1.0, 0.0
    far = p.get("far_share", FAR_SHARE)
    segs = p.get("cameras") if p.get("cameras") is not None else ([p["camera"]] if p.get("camera") else [])
    for cam in segs:
        u = segment_u(cam, f, n)
        s, d = cam["strength"], cam["direction"]
        sx = {"left": -1, "right": 1}.get(d, 0)
        sy = {"up": -1, "down": 1}.get(d, 0)
        if cam["move"] == "push":
            scale *= (1 + PUSH_SCALE * s * u) * (1 + DEPTH_PUSH * s * w_k * u)
        elif cam["move"] == "pull":
            scale *= (1 + PUSH_SCALE * s * (1 - u)) * (1 + DEPTH_PUSH * s * w_k * (1 - u))
        elif cam["move"] == "truck":
            cx += NEAR_TRAVEL * s * u * (far + (1 - far) * w_k) * (sx or 1)
        elif cam["move"] == "crane":
            cy += NEAR_TRAVEL * s * u * (far + (1 - far) * w_k) * (sy or -1)
        elif cam["move"] == "orbit_small":
            # the near plane travels NEAR_TRAVEL past the focus (BP-182); the far side turns the other way, never further
            cx += NEAR_TRAVEL * s * u * max(-1.0, (w_k - w_focus) / max(1e-3, 1 - w_focus)) * (sx or 1)
            scale *= 1 + 0.02 * s * u
    if p["handheld"]:
        h = p["handheld"]
        cx += HAND_TR * h * _wave(t, p["seed"], 0)
        cy += HAND_TR * h * _wave(t, p["seed"], 1)
        rot += HAND_ROT * h * _wave(t, p["seed"], 2)
    return {"cx": cx, "cy": cy, "scale": scale, "rot": rot}


def _matrix(v: dict, out_w: int, out_h: int, src_w: int, src_h: int, z0: float, shake=(0.0, 0.0)) -> np.ndarray:
    """2x3 output->source affine (cv2 WARP_INVERSE_MAP): cover-crop, base zoom ``z0``, the plane's view and the shake."""
    cover = max(src_w / out_w, src_h / out_h)
    k = cover / (z0 * v["scale"])
    th = math.radians(v["rot"])
    a, b = k * math.cos(th), k * math.sin(th)
    ccx = src_w / 2 + v["cx"] * src_w - shake[0] * cover
    ccy = src_h / 2 + v["cy"] * src_w - shake[1] * cover
    return np.array([[a, -b, ccx - a * out_w / 2 + b * out_h / 2],
                     [b, a, ccy - b * out_w / 2 - a * out_h / 2]], dtype=np.float64)


def _sway(m: np.ndarray, p: dict, f: int, pivot: tuple[float, float], strength: float) -> np.ndarray:
    """subject_sway: a rigid rotation about the plane's pivot and a breath of scale (source coordinates)."""
    t = f / p["fps"]
    ang = math.radians(SWAY_DEG * strength * math.sin(2 * math.pi * 0.22 * t))   # zero at frame 0: the shot starts on its picture
    sc = 1 + BREATH * strength * math.sin(2 * math.pi * 0.25 * t)
    c, s = math.cos(-ang) / sc, math.sin(-ang) / sc
    px, py = pivot
    inv = np.array([[c, -s, px - c * px + s * py], [s, c, py - s * px - c * py], [0, 0, 1]])
    return (inv @ np.vstack([m, [0, 0, 1]]))[:2]


def base_zoom(p: dict, weights: list[float], w_focus: float, out_w: int, out_h: int, src_w: int, src_h: int,
              sway_plane: int | None = None) -> float:
    """The smallest base zoom that keeps every plane's frame inside its picture on every frame (no edge ever shows)."""
    # the outer pixel centres must sample inside the picture's pixel centres (bilinear never reads past the edge)
    corners = np.array([[0, 0, 1], [out_w - 1, 0, 1], [0, out_h - 1, 1], [out_w - 1, out_h - 1, 1]], dtype=np.float64).T

    def fits(z0: float) -> bool:
        for f in range(p["frames"]):
            sh = shake_offset(p, f, out_h)
            for k, w in enumerate(weights):
                m = _matrix(plane_view(p, f, w, w_focus), out_w, out_h, src_w, src_h, z0, sh)
                if k == sway_plane:
                    m = _sway(m, p, f, (src_w / 2, src_h), 1.5)
                q = m @ corners
                if q[0].min() < 0 or q[1].min() < 0 or q[0].max() > src_w - 1 or q[1].max() > src_h - 1:
                    return False
        return True

    lo, hi = 1.0, 1.6
    if fits(lo):
        return lo
    for _ in range(18):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if fits(mid) else (mid, hi)
    return hi


# --- the scene: planes, fills, faces, the effects' fixed fields -----------------------------------------------------

def formula_depth(h: int, w: int) -> np.ndarray:
    return np.repeat(np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None], w, axis=1)


def picture_depth(picture: Path) -> tuple[np.ndarray | None, str]:
    """The real depth map of a picture (made once, stored next to it), or None when no model is installed."""
    from PIL import Image
    from explainer_engine.production import depth as DEPTH
    m = DEPTH.ensure(Path(picture))
    if m is None:
        return None, "formula"
    return np.asarray(Image.open(m).convert("L"), dtype=np.float32) / 255.0, "depth_anything_v2_small"


def picture_faces(rgb: np.ndarray) -> list[dict] | None:
    """YuNet faces of an RGB picture: box (x0, y0, x1, y1) and five landmarks, in its pixels; None without the model."""
    from explainer_engine.qa import pixels as PX
    model = PX.yunet_path()
    cv2 = PX._cv2()
    if model is None or cv2 is None:
        return None
    h, w = rgb.shape[:2]
    cv2.setLogLevel(2) if hasattr(cv2, "setLogLevel") else None
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h), PX.FACE_SCORE_MIN, 0.3, 50)
    _, faces = det.detect(np.ascontiguousarray(rgb[..., ::-1]))
    out = []
    for r in faces if faces is not None else []:
        out.append({"box": (float(r[0]), float(r[1]), float(r[0] + r[2]), float(r[1] + r[3])),
                    "landmarks": [(float(r[4 + 2 * i]), float(r[5 + 2 * i])) for i in range(5)], "score": float(r[14])})
    return out


def _kmeans_1d(values: np.ndarray, k: int) -> list[float]:
    """Plane thresholds: midpoints between 1-D k-means centres of the disparity (deterministic quantile start)."""
    c = np.quantile(values, np.linspace(0.1, 0.9, k))
    for _ in range(25):
        lab = np.argmin(np.abs(values[:, None] - c[None, :]), axis=1)
        new = np.array([values[lab == i].mean() if (lab == i).any() else c[i] for i in range(k)])
        if np.allclose(new, c, atol=1e-4):
            break
        c = new
    c = np.sort(c)
    return [float((c[i] + c[i + 1]) / 2) for i in range(k - 1)]


def thresholds(depth: np.ndarray, faces: list[dict] | None, k: int = PLANES) -> list[float]:
    """Plane thresholds that never cut a face: a threshold inside a face's depth range moves behind the face."""
    sample = depth[:: max(1, depth.shape[0] // 180), :: max(1, depth.shape[1] // 320)].ravel()
    ts = _kmeans_1d(sample.astype(np.float64), k)
    for fc in faces or []:
        x0, y0, x1, y1 = (int(round(v)) for v in _shrink(fc["box"], 0.15))
        patch = depth[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
        if patch.size == 0:
            continue
        lo, hi = float(np.quantile(patch, 0.01)), float(np.quantile(patch, 0.99))
        ts = [lo - BAND - 0.005 if lo - BAND <= t <= hi + BAND else t for t in ts]
    ts = sorted(t for t in ts if BAND < t < 1 - BAND)
    kept: list[float] = []
    for t in ts:
        if not kept or t - kept[-1] > 2 * BAND:
            kept.append(t)
    return kept


def _shrink(box, share):
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * share, (y1 - y0) * share
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def _noise_tile(rng, h: int, w: int, scale: float) -> np.ndarray:
    """A seamless (periodic) low-frequency noise tile in 0..1 (FFT-filtered white noise)."""
    f = np.fft.fft2(rng.standard_normal((h, w)))
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    f *= np.exp(-(fx ** 2 + fy ** 2) / (2 * (scale / max(h, w)) ** 2))
    n = np.real(np.fft.ifft2(f))
    return ((n - n.min()) / max(1e-6, n.max() - n.min())).astype(np.float32)


class Scene:
    """Everything a shot's frames need that does not depend on the frame number, made once from the picture."""

    def __init__(self, image, p: dict, out_size: tuple[int, int], depth: np.ndarray | None = None,
                 depth_basis: str = "given", faces: list[dict] | None = None, faces_basis: str = "given"):
        import cv2
        self.cv2 = cv2
        self.p = p
        self.W, self.H = out_size
        rgb = np.asarray(image.convert("RGB"))
        self.src_full = rgb
        self.depth_basis = depth_basis
        self.faces_basis = faces_basis
        self.faces_src = faces
        h0, w0 = rgb.shape[:2]
        if depth is None:
            depth, self.depth_basis = formula_depth(h0, w0), "formula"
        self.depth_src = depth
        # the working size: no larger than the picture, no larger than the frame needs at the closest zoom
        cover = max(self.W / w0, self.H / h0)
        need_w = int(math.ceil(w0 * cover * 1.25))
        sw = min(w0, need_w)
        sh = int(round(h0 * sw / w0))
        self.sw, self.sh = sw, sh
        src = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_AREA) if sw != w0 else rgb.copy()
        self.src = src
        d = cv2.resize(np.asarray(depth, dtype=np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR)
        self.depth = np.clip(d, 0.0, 1.0)
        fs = w0 and sw / w0
        self.faces = None if faces is None else [
            {"box": tuple(v * fs for v in fc["box"]), "landmarks": [(x * fs, y * fs) for x, y in fc["landmarks"]],
             "score": float(fc.get("score", 1.0))} for fc in faces]
        ts = thresholds(self.depth, self.faces)
        self.thresholds = ts
        edges = [0.0] + ts + [1.0]
        lab = np.searchsorted(np.array(ts), self.depth) if ts else np.zeros((sh, sw), int)
        self.labels = lab
        sig = max(0.5, EDGE_SIGMA * sw / 1920)
        alphas = [np.ones((sh, sw), np.float32)] + [cv2.GaussianBlur((lab >= k).astype(np.float32), (0, 0), sig)
                                                     for k in range(1, len(ts) + 1)]
        self.weights = []
        for k in range(len(edges) - 1):
            sel = (self.depth >= edges[k]) & (self.depth < edges[k + 1] + (1e-6 if k == len(edges) - 2 else 0))
            self.weights.append(float(self.depth[sel].mean()) if sel.any() else (edges[k] + edges[k + 1]) / 2)
        lo, hi = self.weights[0], self.weights[-1]
        self.weights = [0.0 if hi - lo < 1e-6 else (w - lo) / (hi - lo) for w in self.weights] if len(self.weights) > 1 \
            else [0.0]
        # each plane: colours with the nearer planes filled in, alpha = this depth or nearer
        self.layers = []
        kernel = np.ones((5, 5), np.uint8)
        r = max(1, int(round(INPAINT_R * sw / 1920)))
        for k in range(len(alphas)):
            if k + 1 < len(alphas):
                hole = cv2.dilate((lab >= k + 1).astype(np.uint8) * 255, kernel, iterations=1)
                col = cv2.inpaint(src, hole, r, cv2.INPAINT_TELEA)
            else:
                col = src
            self.layers.append(np.dstack([col, (alphas[k] * 255 + 0.5).astype(np.uint8)]))
        self.layer_depth = [np.where(alphas[k + 1] > 0.5, self.weights[k], self.depth).astype(np.float32)
                            if k + 1 < len(alphas) else self.depth for k in range(len(alphas))]
        # faces: which plane each sits in, and how much of it
        self.face_plane, self.face_one_plane = [], []
        for fc in self.faces or []:
            x0, y0, x1, y1 = (int(round(v)) for v in _shrink(fc["box"], 0.15))
            patch = self.depth[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
            lab = np.searchsorted(np.array(ts), patch.ravel()) if ts else np.zeros(patch.size, int)
            counts = np.bincount(lab, minlength=len(alphas))
            self.face_plane.append(int(counts.argmax()))
            self.face_one_plane.append(float(counts.max() / max(1, counts.sum())))
        n = len(self.weights)
        # the sure faces steer the focus and the sway; every face, sure or not, keeps to one plane (thresholds above)
        self.sure = [i for i, fc in enumerate(self.faces or []) if fc["score"] >= FACE_SURE]
        hero = self.face_plane[self.sure[0]] if self.sure else None
        self.focus = self.weights[hero] if hero is not None else self.weights[n // 2] if n else 0.0
        sway = next((f for f in p["effects"] if f["effect"] == "subject_sway"), None)
        self.sway = None
        if sway:
            k = hero if hero is not None else n - 1
            ys, xs = np.nonzero(self.layers[k][..., 3] > 128) if k > 0 else (np.array([sh - 1]), np.array([sw // 2]))
            self.sway = {"plane": k, "strength": sway["strength"], "pivot": (float(xs.mean()), float(ys.max()))}
        self.z0 = base_zoom(p, self.weights, self.focus, self.W, self.H, sw, sh,
                            self.sway["plane"] if self.sway else None)
        rng = np.random.default_rng(p["seed"])
        self._prepare_effects(rng, src)
        self.rack_levels = None
        if p["rack"]:
            sig = RACK_SIGMA * p["rack"]["strength"] * sw / 1920
            self.rack_sigma = sig
            self.rack_levels = [[lay] + [cv2.GaussianBlur(lay, (0, 0), sig * (i + 1) / 3) for i in range(3)]
                                for lay in self.layers]

    # effects that need fixed fields: masks, tiles, particles
    def _prepare_effects(self, rng, src):
        cv2 = self.cv2
        self.fx = {}
        luma = src.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
        self.luma = luma
        for e in self.p["effects"]:
            name = e["effect"]
            st = {}
            if name == "fire_flicker":
                if e.get("region"):
                    m = self._box_mask(e["region"], feather=0.04)
                else:
                    hsv = cv2.cvtColor(src, cv2.COLOR_RGB2HSV)   # flames: orange to yellow, saturated, bright
                    core = (hsv[..., 0] <= 25) & (hsv[..., 1] > 90) & (hsv[..., 2] > 200)
                    if core.mean() < 1e-4:
                        raise ContractError(f"{self.p['shot_id']}: fire_flicker finds no fire in the picture; give it a "
                                            "region [x0, y0, x1, y1]")
                    m = core.astype(np.float32)
                field = cv2.GaussianBlur(m, (0, 0), 0.08 * self.sw)
                st["field"] = field / max(1e-6, float(field.max()))
            elif name in ("mist", "smoke_drift", "heat_haze", "cloud_drift"):
                st["tile"] = _noise_tile(rng, 144, 256, 6.0 if name != "heat_haze" else 14.0)
                if name == "smoke_drift":
                    st["tile2"] = _noise_tile(rng, 144, 256, 10.0)
            elif name in ("ash_fall", "embers", "rain", "dust"):
                count = {"ash_fall": 220, "embers": 60, "rain": 420, "dust": 90}[name]
                count = int(round(count * e["strength"]))
                st["p"] = {"x": rng.uniform(0, 1, count), "y": rng.uniform(0, 1, count), "z": rng.uniform(0, 1, count),
                           "ph": rng.uniform(0, 2 * np.pi, count), "w": rng.uniform(0.3, 1.1, count)}
            elif name == "sun_shaft_drift":
                if e.get("origin"):
                    ox, oy = e["origin"]
                else:
                    # the sun is far: the brightest far patch of the upper half, never a lit face in front
                    up = cv2.GaussianBlur((luma * (1.0 - self.depth) ** 2)[: self.sh // 2], (0, 0), 0.03 * self.sw)
                    yy, xx = np.unravel_index(int(np.argmax(up)), up.shape)
                    ox, oy = xx / self.sw, yy / self.sh
                st["origin"] = (ox, oy)
                st["phases"] = rng.uniform(0, 2 * np.pi, 5)
            elif name in NEEDS_REGION:
                st["mask"] = self._box_mask(e["region"], feather=0.06)
                if name == "foliage_sway":
                    r, g, b = (src[..., i].astype(np.float32) for i in range(3))
                    green = np.clip((g - np.maximum(r, b) + 6) / 30.0, 0, 1)
                    st["mask"] = st["mask"] * cv2.GaussianBlur(green, (0, 0), 3)
            if e.get("region") and "mask" not in st:
                st["mask"] = self._box_mask(e["region"], feather=0.06)
            col_far = src[self.depth <= np.quantile(self.depth, 0.3)].reshape(-1, 3).mean(axis=0)
            col_dark = src[luma <= np.quantile(luma, 0.3)].reshape(-1, 3).mean(axis=0)
            st["mist_col"] = 0.6 * np.array([206, 209, 214], np.float32) + 0.4 * col_far.astype(np.float32)
            st["smoke_col"] = 0.5 * np.array([88, 82, 78], np.float32) + 0.5 * col_dark.astype(np.float32)
            self.fx[name] = st
        # where in the depth each effect's region sits: its plane carries the region with the camera
        self.region_plane = {}
        for e in self.p["effects"]:
            if e.get("region"):
                x0, y0, x1, y1 = e["region"]
                patch = self.depth[int(y0 * self.sh):max(int(y0 * self.sh) + 1, int(y1 * self.sh)),
                                   int(x0 * self.sw):max(int(x0 * self.sw) + 1, int(x1 * self.sw))]
                ts = np.array(self.thresholds)
                self.region_plane[e["effect"]] = int(np.searchsorted(ts, float(np.median(patch)))) if ts.size else 0

    def _box_mask(self, region, feather: float) -> np.ndarray:
        x0, y0, x1, y1 = region
        xs = np.linspace(0, 1, self.sw, dtype=np.float32)[None, :]
        ys = np.linspace(0, 1, self.sh, dtype=np.float32)[:, None]
        fx = smooth(np.minimum(xs - x0, x1 - xs) / feather)
        fy = smooth(np.minimum(ys - y0, y1 - ys) / feather)
        return (fx * fy).astype(np.float32)

    def matrices(self, f: int) -> list[np.ndarray]:
        sh = shake_offset(self.p, f, self.H)
        out = []
        for k, w in enumerate(self.weights):
            m = _matrix(plane_view(self.p, f, w, self.focus), self.W, self.H, self.sw, self.sh, self.z0, sh)
            if self.sway and k == self.sway["plane"]:
                m = _sway(m, self.p, f, self.sway["pivot"], self.sway["strength"])
            out.append(m)
        return out


# --- one frame ----------------------------------------------------------------------------------------------------------

def _warp(cv2, img, m, size, flags=None, border=None):
    return cv2.warpAffine(img, m, size, flags=(cv2.INTER_LINEAR if flags is None else flags) | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REFLECT if border is None else border)


def rack_level(sc: Scene, k: int, f: int) -> float:
    """Plane ``k``'s blur level at frame ``f`` (0 sharp .. 3 the full rack blur)."""
    r = sc.p["rack"]
    span = max(1, int(round(RACK_S * sc.p["fps"])))
    a = float(smooth((f - r["at"]) / span))
    far_w, near_w = sc.weights[0], sc.weights[-1]
    focus = (far_w + (near_w - far_w) * a) if r["to"] == "near" else (near_w + (far_w - near_w) * a)
    return min(3.0, 3.0 * abs(sc.weights[k] - focus))


def rack_moving(sc: Scene, f: int) -> bool:
    r = sc.p["rack"]
    return bool(r) and r["at"] <= f <= r["at"] + max(1, int(round(RACK_S * sc.p["fps"])))


def _rack_layer(sc: Scene, k: int, f: int) -> np.ndarray:
    lv = sc.rack_levels[k]
    level = rack_level(sc, k, f)
    i = int(math.floor(level))
    if i >= 3:
        return lv[3]
    t = level - i
    return lv[i] if t < 1e-3 else (lv[i].astype(np.float32) * (1 - t) + lv[i + 1].astype(np.float32) * t).astype(np.uint8)


def composite(sc: Scene, f: int) -> tuple[np.ndarray, np.ndarray, float, list[np.ndarray]]:
    """The planes composited back to front: RGB float (0..255), the frame's depth, coverage (min alpha), the matrices."""
    cv2 = sc.cv2
    size = (sc.W, sc.H)
    ms = sc.matrices(f)
    rgb = depth = None
    cover = None
    for k, m in enumerate(ms):
        lay = _rack_layer(sc, k, f) if sc.rack_levels else sc.layers[k]
        w = _warp(cv2, lay, m, size).astype(np.float32)
        a = w[..., 3:4] / 255.0
        d = _warp(cv2, sc.layer_depth[k], m, size)[..., None]
        if k == 0:
            edge = _warp(cv2, np.full((sc.sh, sc.sw), 255, np.uint8), m, size, border=cv2.BORDER_CONSTANT)
            cover = float(edge.min()) / 255.0
            rgb, depth = w[..., :3], d
        else:
            rgb = rgb * (1 - a) + w[..., :3] * a
            depth = depth * (1 - a) + d * a
    return rgb, depth[..., 0], cover, ms


def _map_field(sc: Scene, field: np.ndarray, m: np.ndarray) -> np.ndarray:
    return _warp(sc.cv2, field.astype(np.float32), m, (sc.W, sc.H), border=sc.cv2.BORDER_CONSTANT)


def _tile_at(sc: Scene, tile: np.ndarray, ox: float, oy: float, scale: float = 1.0) -> np.ndarray:
    """The periodic tile scrolled by (ox, oy) (share of its size), stretched over the frame."""
    th, tw = tile.shape
    sx, sy = int(round(ox * tw)) % tw, int(round(oy * th)) % th
    rolled = np.roll(np.roll(tile, -sy, axis=0), -sx, axis=1)
    return sc.cv2.resize(rolled, (sc.W, sc.H), interpolation=sc.cv2.INTER_CUBIC)


def _particles(sc: Scene, rgb: np.ndarray, st: dict, name: str, t: float, strength: float) -> np.ndarray:
    cv2 = sc.cv2
    W, H = sc.W, sc.H
    p = st["p"]
    k = H / 1080.0
    layer = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), np.float32)
    if name == "ash_fall":
        x = (p["x"] + 0.012 * t * (0.5 + p["z"]) + 0.01 * np.sin(p["w"] * t + p["ph"])) % 1.0
        y = (p["y"] + 0.045 * t * (0.4 + p["z"])) % 1.0
        for i in range(len(x)):
            r = max(1, int(round((1.0 + 3.0 * p["z"][i]) * k)))
            cv2.circle(alpha, (int(x[i] * W), int(y[i] * H)), r, 0.55 + 0.35 * float(p["z"][i]), -1, cv2.LINE_AA)
        alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8 * k)
        col = np.array([196, 192, 186], np.float32)
        return rgb * (1 - alpha[..., None] * 0.8) + col * (alpha[..., None] * 0.8)
    if name == "embers":
        x = (p["x"] + 0.01 * np.sin(p["w"] * 1.7 * t + p["ph"])) % 1.0
        y = (p["y"] - 0.07 * t * (0.5 + p["z"])) % 1.0
        for i in range(len(x)):
            r = max(1, int(round((1.0 + 2.0 * p["z"][i]) * k)))
            glow = 0.5 + 0.5 * math.sin(6.0 * p["w"][i] * t + p["ph"][i])
            cv2.circle(alpha, (int(x[i] * W), int(y[i] * H)), r, 0.6 + 0.4 * glow, -1, cv2.LINE_AA)
        alpha = alpha + cv2.GaussianBlur(alpha, (0, 0), 4 * k) * 1.5
        layer[...] = np.array([255, 150, 60], np.float32)
        return rgb + layer * np.clip(alpha, 0, 1)[..., None] * 0.9 * strength
    if name == "rain":
        x = (p["x"] + 0.14 * t) % 1.0
        y = (p["y"] + 1.6 * t * (0.6 + 0.4 * p["z"])) % 1.0
        for i in range(len(x)):
            ln = (18 + 40 * p["z"][i]) * k
            x0, y0 = int(x[i] * W), int(y[i] * H)
            cv2.line(alpha, (x0, y0), (int(x0 + ln * 0.14), int(y0 + ln)), 0.25 + 0.3 * float(p["z"][i]),
                     max(1, int(round(k))), cv2.LINE_AA)
        col = np.array([190, 200, 214], np.float32)
        return rgb * (1 - alpha[..., None]) + col * alpha[..., None]
    # dust: tiny motes that light up where the scene is lit
    x = (p["x"] + 0.008 * np.sin(p["w"] * 0.6 * t + p["ph"]) + 0.004 * t) % 1.0
    y = (p["y"] + 0.006 * np.cos(p["w"] * 0.5 * t + p["ph"] * 1.3)) % 1.0
    lum = rgb.mean(axis=2) / 255.0
    for i in range(len(x)):
        xi, yi = int(x[i] * (W - 1)), int(y[i] * (H - 1))
        cv2.circle(alpha, (xi, yi), max(1, int(round(1.2 * k))), float(0.2 + 0.8 * lum[yi, xi]), -1, cv2.LINE_AA)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.7 * k)
    return rgb + np.array([255, 240, 215], np.float32) * alpha[..., None] * 0.55 * strength


def lightning_envelope(p: dict, f: int) -> float:
    """A strike: one bright frame, then a smooth decay (BP-183: at most its flash frames above half). A bright-dim-bright
    flicker was tried first: it made four luminance steps of 10 % in one strike, over BP-26's three a second."""
    e = 0.0
    shape = (1.0, 0.75, 0.55, 0.38, 0.25, 0.15, 0.08, 0.03)
    for imp in p["impacts"]:
        if "lightning" in imp["effects"] and 0 <= f - imp["frame"] < len(shape):
            e = max(e, shape[f - imp["frame"]] * imp["strength"])
    return e


def render_frame(sc: Scene, f: int, out_meta: dict | None = None) -> np.ndarray:
    cv2 = sc.cv2
    p = sc.p
    t = f / p["fps"]
    rgb, depth, cover, ms = composite(sc, f)
    far = np.clip(1.0 - depth, 0.0, 1.0)
    W, H = sc.W, sc.H
    k = H / 1080.0
    for e in p["effects"]:
        name, s = e["effect"], e["strength"]
        st = sc.fx.get(name, {})
        plane_m = ms[sc.region_plane.get(name, len(ms) // 2)]
        mask = _map_field(sc, st["mask"], plane_m) if "mask" in st else None
        if name == "fire_flicker":
            field = _map_field(sc, st["field"], ms[len(ms) // 2])
            g = s * (0.10 * math.sin(2 * math.pi * 4.3 * t + 0.7) + 0.06 * math.sin(2 * math.pi * 7.9 * t + 2.1)
                     + 0.05 * _wave(t * 3.0, p["seed"], 3))
            rgb = rgb * (1 + g * field[..., None] * np.array([1.0, 0.78, 0.5], np.float32))
        elif name == "mist":
            n = _tile_at(sc, st["tile"], 0.012 * t, 0.004 * t)
            a = s * (0.10 + 0.22 * n) * far ** 1.5
            if mask is not None:
                a = a * mask
            rgb = rgb * (1 - a[..., None]) + st["mist_col"] * a[..., None]
        elif name == "smoke_drift":
            n = _tile_at(sc, st["tile"], 0.03 * t, -0.006 * t) * _tile_at(sc, st["tile2"], -0.012 * t, 0.0)
            a = s * 0.55 * np.clip(n * 1.6 - 0.15, 0, 1) * (0.4 + 0.6 * far)
            if mask is not None:
                a = a * mask
            rgb = rgb * (1 - a[..., None]) + st["smoke_col"] * a[..., None]
        elif name in ("ash_fall", "embers", "rain", "dust"):
            rgb = _particles(sc, rgb, st, name, t, s)
        elif name == "sun_shaft_drift":
            ox, oy = st["origin"]
            fxy = cv2.invertAffineTransform(ms[0]) @ np.array([ox * sc.sw, oy * sc.sh, 1.0])   # source -> frame
            qs = 4
            yy, xx = np.mgrid[0:H // qs, 0:W // qs].astype(np.float32) * qs
            ang = np.arctan2(yy - fxy[1], xx - fxy[0])
            rad = np.hypot(yy - fxy[1], xx - fxy[0]) / W
            # a few broad, slowly turning beams (low angular frequencies), soft at the sun itself (no starburst core),
            # strongest a little way out and gone by about two thirds of the frame width
            rays = sum(np.cos(n * ang + st["phases"][i] + 0.25 * (i + 1) * t) for i, n in enumerate((3, 5, 8)))
            rays = np.clip(rays / 3.0 + 0.15, 0, 1) ** 1.5 * (0.7 + 0.3 * math.sin(2 * math.pi * 0.2 * t + st["phases"][0]))
            gate = (1 - np.exp(-(rad / 0.06) ** 2)) * np.exp(-(rad / 0.6) ** 2)
            rays = cv2.GaussianBlur((rays * gate).astype(np.float32), (0, 0), 6.0)
            rays = cv2.resize(rays, (W, H), interpolation=cv2.INTER_LINEAR)
            rgb = rgb + np.array([255, 228, 180], np.float32) * (0.40 * s * rays * far ** 0.7)[..., None]
        elif name in ("water_shimmer", "heat_haze", "foliage_sway", "cloth_flap", "cloud_drift"):
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            if name == "cloth_flap":
                # a flag or a sail: waves run away from the pole (the region's side named by direction, default left),
                # growing with the distance from it; a gust swells them every few seconds
                x0, y0, x1, y1 = e["region"]
                pole_left = e.get("direction", "right") != "left"
                along = np.clip((xx / W - x0) / max(1e-3, x1 - x0), 0, 1) if pole_left else \
                    np.clip((x1 - xx / W) / max(1e-3, x1 - x0), 0, 1)
                gust = 0.75 + 0.25 * math.sin(2 * math.pi * 0.23 * t + 0.6)
                phase = 2 * math.pi * (along * 2.2 - 1.6 * t)
                dy = 5.0 * k * s * gust * along * np.sin(phase)
                dx = 1.5 * k * s * gust * along * np.cos(phase + 0.7)
            elif name == "cloud_drift":
                # the sky drifts sideways and slowly changes shape (a low-frequency warp over a slow translation)
                sign = -1.0 if e.get("direction") == "left" else 1.0
                n_ = _tile_at(sc, st["tile"], 0.006 * t, 0.002 * t) - 0.5
                dx = -sign * 0.012 * W * s * float(smooth(t / max(1e-3, p["frames"] / p["fps"]))) + 6.0 * k * s * n_
                dy = 2.5 * k * s * n_
            elif name == "water_shimmer":
                dx = 0.6 * k * s * np.sin(2 * math.pi * (yy / (9 * k)) + 3.1 * t)
                dy = 1.6 * k * s * np.sin(2 * math.pi * (yy / (23 * k) + xx / (140 * k)) - 2.3 * t)
            elif name == "heat_haze":
                n = _tile_at(sc, st["tile"], 0.0, 0.25 * t) - 0.5
                dx, dy = 4.0 * k * s * n, 2.0 * k * s * n
            else:
                x0, y0, x1, y1 = e["region"]
                ramp = np.clip(1.0 - (yy / H - y0) / max(1e-3, y1 - y0), 0, 1)
                dx = 3.0 * k * s * ramp * (np.sin(2 * math.pi * 0.35 * t + xx / (180 * k))
                                          + 0.4 * np.sin(2 * math.pi * 0.9 * t + xx / (60 * k) + 1.3))
                dy = 0.3 * dx
            mm = mask if mask is not None else np.ones((H, W), np.float32)
            src = np.clip(rgb, 0, 255).astype(np.float32)
            moved = cv2.remap(src, xx + dx * mm, yy + dy * mm, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            rgb = moved
            if name == "water_shimmer":
                lum = rgb.mean(axis=2) / 255.0
                glint = np.clip(np.sin(2 * math.pi * (xx / (37 * k) + yy / (11 * k)) + 4.0 * t) - 0.85, 0, 1) * 6.0
                rgb = rgb + (glint * lum * mm * 40.0 * s)[..., None]
    env = lightning_envelope(p, f)
    if env > 0:
        white = np.array([232, 238, 255], np.float32)
        a = min(FLASH_WHITE, 0.55 * env) * (0.35 + 0.65 * far)
        rgb = rgb * (1 - a[..., None]) + white * a[..., None]
    if out_meta is not None:
        out_meta["cover"] = cover
        out_meta["matrices"] = ms
    return np.clip(rgb + 0.5, 0, 255).astype(np.uint8)


# --- measurements ------------------------------------------------------------------------------------------------------

def layout_similarity(a, b) -> float:
    """Correlation of the two pictures' coarse luminance layout (32x18, mean-removed): 1 = the same composition."""
    from PIL import Image
    xs = []
    for im in (a, b):
        g = np.asarray(im.convert("L").resize((32, 18), Image.BILINEAR), dtype=np.float64).ravel()
        g -= g.mean()
        xs.append(g / max(1e-6, np.linalg.norm(g)))
    return float(np.dot(xs[0], xs[1]))


def _landmark_geometry(lm: list[tuple[float, float]]) -> np.ndarray:
    pts = np.array(lm, dtype=np.float64)
    eye = max(1e-6, float(np.hypot(*(pts[0] - pts[1]))))
    return np.array([np.hypot(*(pts[i] - pts[j])) / eye for i in range(5) for j in range(i + 1, 5)])


class Meter:
    """Frame-by-frame measurements for the stability gates (cheap, on small copies)."""

    def __init__(self, sc: Scene, measure_faces: bool):
        self.sc = sc
        self.fps = sc.p["fps"]
        self.ref = None
        self.run = self.longest = 0
        self.lumas: list[float] = []
        self.cover_min = 1.0
        self.tears: list[float] = []
        self.tear0 = None
        self.tear_state = "before"
        self.face_drift: list[float] = []
        self.sure = [sc.faces[i] for i in getattr(sc, "sure", [])]
        self.face_geo0 = [(_landmark_geometry(fc["landmarks"])) for fc in self.sure]
        self.measure_faces = measure_faces and bool(self.sure)
        self.near_path: list[tuple[float, float]] = []
        self.start_diff = None

    def _tear_ratio(self, frame: np.ndarray, ms) -> float | None:
        cv2 = self.sc.cv2
        small = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)
        gx, gy = cv2.Sobel(small, cv2.CV_32F, 1, 0), cv2.Sobel(small, cv2.CV_32F, 0, 1)
        g = np.hypot(gx, gy)
        band = np.zeros_like(small, dtype=bool)
        for k in range(1, len(ms)):
            a = _warp(cv2, self.sc.layers[k][..., 3], ms[k], (self.sc.W, self.sc.H), border=cv2.BORDER_CONSTANT)
            a = cv2.resize(a, (480, 270), interpolation=cv2.INTER_AREA)
            band |= (a > 20) & (a < 235)
        if band.sum() < 20:
            return None
        return float(np.quantile(g[band], 0.99) / max(1e-6, np.quantile(g, 0.99)))

    def add(self, f: int, frame: np.ndarray, meta: dict) -> None:
        cv2 = self.sc.cv2
        small = cv2.resize(frame, ANALYSIS, interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)
        self.lumas.append(float(small.mean()) / 255.0)
        if self.ref is None or float(np.abs(small - self.ref).mean()) >= FROZEN_DIFF:
            self.ref, self.run = small, 1
        else:
            self.run += 1
        self.longest = max(self.longest, self.run)
        self.cover_min = min(self.cover_min, meta["cover"])
        ms = meta["matrices"]
        if f == 0:   # the planes start on the picture: frame 0's composite (no effects) against the plain picture
            ref = _warp(cv2, self.sc.src, ms[0], (self.sc.W, self.sc.H)).astype(np.float32)
            levels, self.sc.rack_levels = self.sc.rack_levels, None    # a rack's first blur is designed, not a seam
            try:
                self.start_diff = float(np.abs(composite(self.sc, 0)[0] - ref).mean())
            finally:
                self.sc.rack_levels = levels
        c = cv2.invertAffineTransform(ms[-1]) @ np.array([self.sc.sw / 2, self.sc.sh / 2, 1.0])
        self.near_path.append((float(c[0]), float(c[1])))
        if self.sc.p["rack"] and f > self.sc.p["rack"]["at"] and self.tear_state != "after":
            self.tear_state, self.tear0 = "after", None   # the rack changes every edge's sharpness: a new reference after it
        if f % 4 == 0 and len(ms) > 1 and not rack_moving(self.sc, f):
            r = self._tear_ratio(frame, ms)
            if r is not None:
                if self.tear0 is None:
                    self.tear0 = r
                self.tears.append(r / max(1e-6, self.tear0))
        if self.measure_faces and f % 12 == 0:
            got = picture_faces(frame) or []
            for g0, fc in zip(self.face_geo0, self.sure):
                k = self.sc.face_plane[self.sc.faces.index(fc)]
                if self.sc.rack_levels and rack_level(self.sc, k, f) >= 0.5:
                    continue    # a face the rack keeps soft on purpose: the detector's landmarks are noise there
                inv = cv2.invertAffineTransform(ms[k])
                cx, cy = (fc["box"][0] + fc["box"][2]) / 2, (fc["box"][1] + fc["box"][3]) / 2
                ex, ey = inv @ np.array([cx, cy, 1.0])
                best = min(got, key=lambda q: math.hypot((q["box"][0] + q["box"][2]) / 2 - ex,
                                                         (q["box"][1] + q["box"][3]) / 2 - ey), default=None)
                if best is not None:
                    self.face_drift.append(float(np.max(np.abs(_landmark_geometry(best["landmarks"]) - g0) / g0)))

    def flashes(self) -> int:
        """BP-26: the most full-frame luminance steps of 10 % or more inside any one-second window."""
        steps = [i for i in range(1, len(self.lumas)) if abs(self.lumas[i] - self.lumas[i - 1]) >= 0.10]
        return max((sum(1 for s in steps if a <= s < a + self.fps) for a in range(len(self.lumas))), default=0)


def gates(sc: Scene, meter: Meter, sec_per_frame: float, chunk_match: bool | None, end_picture: dict | None) -> list[dict]:
    p = sc.p
    rows = []
    fam = p["families"]
    rows.append(G.row("alive_two_families", len(fam) >= ALIVE_MIN,
                      f"moving families beyond the camera: {fam or 'none'} (BP-185, the creator's Q4 rule: at least "
                      f"{ALIVE_MIN} of {', '.join(ALIVE_FAMILIES)})", fam))
    rows.append(G.row("planes", len(sc.weights) >= LAYERS_MIN,
                      f"{len(sc.weights)} depth planes (BP-181: at least {LAYERS_MIN})", len(sc.weights),
                      level=SR.level("BP-181")))
    rows.append(G.row("depth_is_real", sc.depth_basis != "formula", f"depth basis {sc.depth_basis}", sc.depth_basis,
                      level="REVIEW"))
    rows.append(G.row("no_uncovered_pixels", meter.cover_min >= 0.999,
                      "the back plane covers the whole frame on every frame", round(meter.cover_min, 4)))
    tear = max(meter.tears) if meter.tears else None
    rows.append(G.row("no_edge_tears", None if tear is None else tear <= TEAR_REVIEW,
                      "no plane border measured (one plane)" if tear is None else
                      f"seam gradient against frame 0's, worst {tear:.2f} (engineering default {TEAR_REVIEW})",
                      None if tear is None else round(tear, 3), level="REVIEW"))
    if sc.faces is None:
        rows.append(G.row("faces_rigid", None, "no face detector installed (tools/yunet): faces not measured"))
    elif not sc.faces:
        rows.append(G.row("faces_rigid", True, "no face in the picture", 0))
    else:
        worst = min(sc.face_one_plane)
        rows.append(G.row("faces_rigid", worst >= FACE_ONE_PLANE,
                          f"each face lies in one plane (worst share {worst:.3f}; one affine, no warp inside it)",
                          round(worst, 4)))
        drift = max(meter.face_drift) if meter.face_drift else None
        if not getattr(sc, "sure", None):
            rows.append(G.row("face_landmarks_steady", True, f"no face the detector is sure of (score >= {FACE_SURE}): "
                              "nothing to track; the unsure ones are kept in one plane above", 0))
        else:
            rows.append(G.row("face_landmarks_steady", None if drift is None else drift <= FACE_DRIFT_REVIEW,
                              "no face re-detected on the sampled frames" if drift is None else
                              f"landmark geometry drift, worst {drift:.3f} (engineering default {FACE_DRIFT_REVIEW})",
                              None if drift is None else round(drift, 4), level="REVIEW"))
    rows.append(G.row("no_frozen_stretch", meter.longest <= FROZEN_FRAMES_MAX,
                      f"longest run without visible change {meter.longest} frames (BP-174: {FROZEN_FRAMES_MAX}; change = "
                      f"mean difference {FROZEN_DIFF} at {ANALYSIS[0]}x{ANALYSIS[1]}, BP-164)", meter.longest,
                      level=SR.level("BP-174")))
    fl = meter.flashes()
    rows.append(G.row("flash_safety", fl <= FLASHES_PER_S, f"{fl} flashes in the worst second (BP-26: {FLASHES_PER_S})", fl,
                      level=SR.level("BP-26")))
    if any(c["move"] in ("truck", "crane", "orbit_small") for c in p.get("cameras") or []):
        path = np.array(meter.near_path)
        travel = float(np.hypot(*(path.max(axis=0) - path.min(axis=0))) / sc.W)
        rows.append(G.row("near_plane_travel", TRAVEL_BAND[0] <= travel <= min(TRAVEL_BAND[1], TRAVEL_MAX),
                          f"near plane travel {travel:.3f} of the width (plan P5.2: {TRAVEL_BAND}; BP-182 cap {TRAVEL_MAX})",
                          round(travel, 4), level=SR.level("BP-182")))
    if meter.start_diff is not None and not any(c["move"] == "pull" for c in p.get("cameras") or []):
        rows.append(G.row("starts_on_its_picture", meter.start_diff <= START_DIFF_REVIEW,
                          f"frame 0's planes against the picture: mean difference {meter.start_diff:.2f} of 255 (engineering default "
                          f"{START_DIFF_REVIEW}; a pull starts closer by design)", round(meter.start_diff, 3), level="REVIEW"))
    rows.append(G.row("chunks_match", chunk_match, "frames of a fresh scene match the full render" if chunk_match is not None
                      else "not checked", chunk_match))
    rows.append(G.row("render_speed", sec_per_frame <= CPU_SPF, f"{sec_per_frame:.2f} s a frame (BP-182: {CPU_SPF})",
                      round(sec_per_frame, 3), level=SR.level("BP-182")))
    if end_picture is not None:
        rows.append(G.row("end_picture_layout", end_picture["used"],
                          f"start/end layout similarity {end_picture['similarity']:.2f} (engineering default "
                          f"{LAYOUT_SAME_MIN}); " + ("cross-moved" if end_picture["used"] else
                                                     "not cross-moved: the script should make these two shots"),
                          round(end_picture["similarity"], 3), level="REVIEW"))
    return rows


# --- the clip ------------------------------------------------------------------------------------------------------------

def build_scene(picture: Path, p: dict, size: tuple[int, int], depth=None, faces=None) -> Scene:
    from PIL import Image
    img = Image.open(picture).convert("RGB")
    if depth is None:
        depth, basis = picture_depth(picture)
    else:
        basis = "given"
    if faces is None:
        faces_found = picture_faces(np.asarray(img))
        return Scene(img, p, size, depth, basis, faces_found, "yunet" if faces_found is not None else "none")
    return Scene(img, p, size, depth, basis, faces, "given")


def render_clip(shot: dict, picture: Path, out_mp4: Path, *, width: int = 1920, height: int = 1080, fps: int = 24,
                end_picture: Path | None = None, script: dict | None = None, events: list[dict] | None = None,
                spine: list[dict] | None = None, depth=None, faces=None, measure_faces: bool = True,
                check_chunks: bool = True) -> dict:
    """Render one 2.5D shot to ``out_mp4`` (exactly its frames, tmp file then rename) and measure it."""
    from PIL import Image
    p = plan(shot, fps, events, script, spine)
    t0 = time.time()
    sc = build_scene(Path(picture), p, (width, height), depth, faces)
    prep_s = time.time() - t0
    end = None
    sc_end = None
    if end_picture and Path(end_picture).is_file() and Path(end_picture) != Path(picture):
        sim = layout_similarity(Image.open(picture), Image.open(end_picture))
        end = {"similarity": sim, "used": sim >= LAYOUT_SAME_MIN, "path": str(end_picture)}
        if end["used"]:
            sc_end = build_scene(Path(end_picture), p, (width, height))
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.with_name(out_mp4.stem + ".part.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{width}x{height}", "-r", str(fps), "-i", "-", "-frames:v", str(p["frames"]), "-c:v",
                             "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)],
                            stdin=subprocess.PIPE)
    meter = Meter(sc, measure_faces)
    probe = sorted({p["frames"] // 2, min(p["frames"] - 1, p["frames"] // 2 + 1)})
    hashes = {}
    t1 = time.time()
    try:
        for f in range(p["frames"]):
            meta: dict = {}
            fr = render_frame(sc, f, meta)
            if sc_end is not None:
                w = float(smooth((f / max(1, p["frames"] - 1) - 0.3) / 0.4))
                if w > 0:
                    fr = (fr.astype(np.float32) * (1 - w) + render_frame(sc_end, f).astype(np.float32) * w + 0.5
                          ).astype(np.uint8)
            if f in probe:
                hashes[f] = hashlib.sha256(fr.tobytes()).hexdigest()
            meter.add(f, fr, meta)
            proc.stdin.write(fr.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {p['shot_id']}")
    tmp.replace(out_mp4)
    spf = (time.time() - t1) / max(1, p["frames"])
    chunk = None
    if check_chunks and sc_end is None:
        fresh = build_scene(Path(picture), p, (width, height), depth if depth is not None else sc.depth_src,
                            faces if faces is not None else (sc.faces_src or []))
        chunk = all(hashlib.sha256(render_frame(fresh, f).tobytes()).hexdigest() == h for f, h in hashes.items())
    rows = gates(sc, meter, spf, chunk, end)
    return {"status": "generated", "provider": "python_layered_25d", "cost_usd": 0.0, "shot_id": p["shot_id"],
            "path": str(out_mp4), "total_frames": p["frames"], "fps": fps, "resolution": [width, height],
            "depth_basis": sc.depth_basis, "faces": len(sc.faces or []), "faces_basis": sc.faces_basis,
            "planes": len(sc.weights), "plane_weights": [round(w, 3) for w in sc.weights], "base_zoom": round(sc.z0, 4),
            "camera": p["camera"], "cameras": p["cameras"], "profile": p["profile"], "capped": p["capped"],
            "events": [{k: e[k] for k in ("event_id", "op", "start_frame", "end_frame")} | {"decision": e["audio"]["decision"]}
                       for e in p["events"]],
            "handheld": p["handheld"], "rack": p["rack"],
            "effects": [e["effect"] for e in p["effects"]], "impacts": p["impacts"], "families": p["families"],
            "prep_s": round(prep_s, 2), "sec_per_frame": round(spf, 3), "end_picture": end,
            "gates": G.verdict(rows), "output_sha256": hashlib.sha256(out_mp4.read_bytes()).hexdigest()}
