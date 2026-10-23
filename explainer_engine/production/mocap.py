"""Motion capture -> gait tables for the bend rig (Stage 1 of the physics plan, docs/research/HYBRID_VISUAL_MODEL).

Reads a BVH clip (CMU Graphics Lab Motion Capture Database, free for any use; the cgspeed BVH conversion), runs forward
kinematics, projects the body onto its own sagittal plane (forward, up) and measures one gait cycle after another: how far
the hips travel per cycle, how long each foot stays planted, how high the swing foot lifts, how the torso leans and sways,
how far the arms swing, how the foot pitches at heel strike and toe-off. Every length is expressed in LEG LENGTHS (hip to
ankle), so the numbers retarget to the rig's shorter cartoon legs; angles are kept as they are.

``python -m explainer_engine.production.mocap <bvh dir> [--out gaits.json]`` writes the table ``bend_rig.measured`` reads.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

GAITS_JSON = Path(__file__).with_name("gaits.json")
CLIPS = {  # CMU subject_trial -> the gait it measures
    "07_01": ("walk", "subject 7 trial 1: walk"),
    "07_12": ("brisk_walk", "subject 7 trial 12: brisk walk"),
    "09_01": ("run", "subject 9 trial 1: run"),
    "02_03": ("jog", "subject 2 trial 3: run/jog"),
}
SOURCE = {
    "database": "CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), funded by NSF EIA-0196217; free for any use",
    "conversion": "BVH conversion by B. Hahne (cgspeed), https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture",
}


# --- BVH ---------------------------------------------------------------------------------------------------------------
@dataclass
class Joint:
    name: str
    parent: int
    offset: np.ndarray
    channels: list = field(default_factory=list)
    end: np.ndarray | None = None


@dataclass
class Clip:
    joints: list
    frames: np.ndarray        # (n, channels)
    frame_time: float

    def index(self, name: str) -> int:
        for i, j in enumerate(self.joints):
            if j.name == name:
                return i
        raise KeyError(name)


def parse_bvh(path: Path) -> Clip:
    text = Path(path).read_text().split()
    joints, stack, i = [], [], 0
    while text[i] != "MOTION":
        tok = text[i]
        if tok in ("ROOT", "JOINT"):
            joints.append(Joint(text[i + 1], stack[-1] if stack else -1, np.zeros(3)))
            i += 2
        elif tok == "{":
            stack.append(len(joints) - 1)
            i += 1
        elif tok == "}":
            stack.pop()
            i += 1
        elif tok == "OFFSET":
            joints[stack[-1]].offset = np.array([float(text[i + 1]), float(text[i + 2]), float(text[i + 3])])
            i += 4
        elif tok == "CHANNELS":
            n = int(text[i + 1])
            joints[stack[-1]].channels = text[i + 2:i + 2 + n]
            i += 2 + n
        elif tok == "End":
            # End Site { OFFSET x y z }: record it on the current joint
            k = i + 2
            assert text[k] == "{" and text[k + 1] == "OFFSET"
            joints[stack[-1]].end = np.array([float(text[k + 2]), float(text[k + 3]), float(text[k + 4])])
            i = k + 6
        else:
            i += 1
    assert text[i + 1] == "Frames:" and text[i + 3] == "Frame" and text[i + 4] == "Time:"
    n = int(text[i + 2])
    dt = float(text[i + 5])
    vals = np.array([float(v) for v in text[i + 6:]])
    nch = sum(len(j.channels) for j in joints)
    frames = vals[: n * nch].reshape(n, nch)
    return Clip(joints, frames, dt)


def _rot(axis: str, deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "X":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "Y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def fk(clip: Clip, frame: int) -> dict:
    """World positions of every joint (and ``<name>_end`` for end sites) in one frame."""
    row = clip.frames[frame]
    pos, rot, k = {}, {}, 0
    for i, j in enumerate(clip.joints):
        t = np.zeros(3)
        r = np.eye(3)
        for ch in j.channels:
            v = row[k]
            k += 1
            if ch.endswith("position"):
                t["XYZ".index(ch[0])] = v
            else:
                r = r @ _rot(ch[0], v)
        if j.parent < 0:
            p = j.offset + t
            m = r
        else:
            pr, pm = pos[j.parent], rot[j.parent]
            p = pr + pm @ (j.offset + t)
            m = pm @ r
        pos[i], rot[i] = p, m
        if j.end is not None:
            pos[f"{j.name}_end"] = p + m @ j.end
    return {clip.joints[i].name if isinstance(i, int) else i: v for i, v in pos.items()}


# --- measuring ---------------------------------------------------------------------------------------------------------
NAMES = {
    "hips": "Hips", "chest": "Spine1", "head": "Head_end",
    "L": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "LeftToeBase_end"),
    "R": ("RightUpLeg", "RightLeg", "RightFoot", "RightToeBase", "RightToeBase_end"),
    "arm_L": ("LeftArm", "LeftForeArm", "LeftHand"),
    "arm_R": ("RightArm", "RightForeArm", "RightHand"),
}


def trajectories(clip: Clip) -> dict:
    """Sagittal (forward, up) trajectories of the joints the rig cares about, in LEG LENGTHS, plus the time axis."""
    frames = [fk(clip, f) for f in range(len(clip.frames))]
    hips = np.array([fr["Hips"] for fr in frames])
    d = hips[-1] - hips[0]
    d[1] = 0.0
    if np.linalg.norm(d) < 1e-6:
        raise ValueError("the clip does not travel: no gait to measure")
    fwd = d / np.linalg.norm(d)
    leg = float(np.mean([np.linalg.norm(fr["LeftLeg"] - fr["LeftUpLeg"]) + np.linalg.norm(fr["LeftFoot"] - fr["LeftLeg"])
                         for fr in frames[:1]]))

    def sag(name):
        return np.array([[fr[name] @ fwd, fr[name][1]] for fr in frames]) / leg

    out = {"t": np.arange(len(frames)) * clip.frame_time, "leg": leg}
    for key, val in NAMES.items():
        if isinstance(val, str):
            out[key] = sag(val)
        elif all(v in frames[0] for v in val):
            out[key] = [sag(v) for v in val]       # a clip without arms still measures its legs
    return out


def _runs(mask: np.ndarray, min_len: int) -> np.ndarray:
    """Drop the True runs shorter than ``min_len`` frames."""
    out = mask.copy()
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i < min_len:
                out[i:j] = False
            i = j
        else:
            i += 1
    return out


def _contacts(foot_pts: list, dt: float, hip_speed: float) -> np.ndarray:
    """A foot is planted while its heel or its toes stand (nearly) still: the capture's floor drifts a little, so height
    alone is not a reliable test. "Still" = under a quarter of the hips' forward speed. Contacts and flights shorter than
    40 ms are noise and are filled."""
    v_max = max(0.3, 0.25 * hip_speed)
    speeds = []
    for p in foot_pts:
        v = np.gradient(p, dt, axis=0)
        speeds.append(np.linalg.norm(v, axis=1))
    still = np.minimum.reduce(speeds) < v_max
    k = max(1, int(round(0.04 / dt)))
    still = ~_runs(~still, k)      # fill short flights
    return _runs(still, k)         # drop short contacts


def _angle_fwd(v: np.ndarray, up: bool = False) -> float:
    """Angle of a sagittal vector from straight DOWN (or UP), forward positive, degrees."""
    return math.degrees(math.atan2(v[0], v[1] if up else -v[1]))


def measure(clip: Clip) -> dict:
    """Gait numbers averaged over the full cycles of a clip (one cycle = left heel strike to the next)."""
    tr = trajectories(clip)
    t = tr["t"]
    hip_speed = float((tr["hips"][-1, 0] - tr["hips"][0, 0]) / (t[-1] - t[0]))
    contact = {s: _contacts([tr[s][2], tr[s][4]], clip.frame_time, hip_speed) for s in "LR"}
    strikes = {s: [i for i in range(1, len(t)) if contact[s][i] and not contact[s][i - 1]] for s in "LR"}
    lead = "L" if len(strikes["L"]) >= len(strikes["R"]) else "R"   # the foot whose strikes start the cycles
    other = "R" if lead == "L" else "L"
    if len(strikes[lead]) < 2:
        raise ValueError("fewer than one full cycle")
    cycles = list(zip(strikes[lead][:-1], strikes[lead][1:]))
    hips, chest = tr["hips"], tr["chest"]
    per = []
    for a, b in cycles:
        n = b - a
        # the floor of this cycle: where the planted toes and ankles are lowest (the capture's floor drifts a little)
        ground = min(float(np.min(tr[s][4][a:b, 1][contact[s][a:b]])) for s in "LR" if contact[s][a:b].any())
        ankle_stand = min(float(np.min(tr[s][2][a:b, 1][contact[s][a:b]])) for s in "LR" if contact[s][a:b].any())
        stance = {}
        for s in "LR":
            stance[s] = float(np.sum(contact[s][a:b]) / n)
        r_strike = [i for i in strikes[other] if a <= i < b]
        offset = (r_strike[0] - a) / n if r_strike else 0.5
        stride = float(hips[b, 0] - hips[a, 0])
        hip_y = 0.5 * (tr["L"][0][a:b, 1] + tr["R"][0][a:b, 1]) - ground   # the hip JOINTS (the rig's hip point)
        lean = np.array([_angle_fwd(chest[i] - hips[i], up=True) for i in range(a, b)])
        ph = np.arange(n) / n
        sway = 2.0 * abs(np.mean((lean - lean.mean()) * np.exp(-2j * math.pi * 2 * ph)))
        swing_lift = 0.0
        for s in "LR":
            air = ~contact[s][a:b]
            if air.any():
                swing_lift = max(swing_lift, float(np.max(tr[s][2][a:b, 1][air]) - ankle_stand))
        arm_amp, elbow = [0.0], [0.0]
        for s in "LR":
            if f"arm_{s}" not in tr:
                continue
            up, fore, hand = tr[f"arm_{s}"]
            ang = np.array([_angle_fwd(fore[i] - up[i]) for i in range(a, b)])
            arm_amp.append((ang.max() - ang.min()) / 2)
            for i in range(a, b):
                u, v = fore[i] - up[i], hand[i] - fore[i]
                cos = np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9), -1, 1)
                elbow.append(math.degrees(math.acos(cos)))
        # the foot's pitch at the strike (toe up, positive) and the toe-off (heel up, positive), relative to the sole's
        # pitch at mid-stance (the ankle joint sits above the toes even when the foot is flat)
        def pitch(s, i):
            heel, toe = tr[s][2][i], tr[s][4][i]
            return math.degrees(math.atan2(toe[1] - heel[1], max(1e-6, toe[0] - heel[0])))
        planted = [i for i in range(a, b) if contact[lead][i]]
        flat = pitch(lead, planted[len(planted) // 2])
        strike = pitch(lead, a) - flat
        offs = [i for i in range(a + 1, b) if contact[lead][i - 1] and not contact[lead][i]]
        toe_off = flat - pitch(lead, offs[0] - 1) if offs else 0.0
        per.append({
            "stride": stride, "stance": (stance[lead], stance[other]), "offset": offset,
            "lift": swing_lift, "hip": float(hip_y.mean()), "bob": float((hip_y.max() - hip_y.min()) / 2),
            "lean": float(lean.mean()), "sway": float(sway), "swing": float(np.mean(arm_amp)),
            "elbow": float(np.mean(elbow)), "strike": float(strike), "toe_off": float(toe_off),
            "cycle_s": float(t[b] - t[a]),
        })
    keys = [k for k in per[0] if k != "stance"]
    avg = {k: float(np.mean([p[k] for p in per])) for k in keys}
    avg["stance"] = (float(np.mean([p["stance"][0] for p in per])), float(np.mean([p["stance"][1] for p in per])))
    avg["cycles"] = len(per)
    avg["speed"] = avg["stride"] / avg["cycle_s"]      # leg lengths per second
    # the swing foot's arc: ankle height over its forward progress, 12 samples, for the rig's lift curve
    a, b = cycles[0]
    air = [i for i in range(a, b) if not contact[lead][i]]
    if air:
        ankle_stand = float(np.min(tr[lead][2][a:b, 1][contact[lead][a:b]]))
        xs = tr[lead][2][air, 0]
        ys = tr[lead][2][air, 1] - ankle_stand
        u = (xs - xs[0]) / max(1e-6, xs[-1] - xs[0])
        grid = np.linspace(0, 1, 12)
        avg["arc"] = [round(float(v), 4) for v in np.interp(grid, u, ys)]
    return avg


def to_gait_kwargs(m: dict, leg_px: float, body_px: float) -> dict:
    """Retarget the measure to a rig whose leg (hip to ankle) is ``leg_px`` and body ``body_px`` tall: lengths scale by
    the leg, angles stay. The result builds a ``bend_rig.Gait``."""
    k = leg_px / body_px
    return {
        "stride": round(m["stride"] * k, 4), "stance": (round(m["stance"][0], 3), round(m["stance"][1], 3)),
        "offset": (0.0, round(m["offset"], 3)), "lift": round(m["lift"] * k, 4), "hip": round(m["hip"] * k, 4),
        "bob": round(m["bob"] * k, 4), "lean": round(m["lean"], 2), "swing": round(m["swing"], 2),
        "elbow": round(m["elbow"], 2), "strike": round(max(0.0, m["strike"]), 2),
        "toe_off": round(max(0.0, m["toe_off"]), 2), "sway": round(m["sway"], 2),
        "arc": tuple(round(v * k, 4) for v in m.get("arc", ())),   # the swing ankle's height over its progress, body heights
    }


def extract(bvh_dir: Path, out: Path = GAITS_JSON, leg_px: float | None = None, body_px: float | None = None) -> dict:
    from . import bend_rig as R
    leg_px = leg_px or (R.THIGH + R.SHIN)
    body_px = body_px or R.B
    table = {"source": SOURCE, "units": "lengths in leg lengths (hip to ankle); gait values retargeted to the rig",
             "rig": {"leg_px": leg_px, "body_px": body_px}, "gaits": {}}
    for clip_id, (name, label) in CLIPS.items():
        p = Path(bvh_dir) / f"{clip_id}.bvh"
        if not p.exists():
            continue
        m = measure(parse_bvh(p))
        table["gaits"][name] = {"clip": clip_id, "label": label, "measured": m, "gait": to_gait_kwargs(m, leg_px, body_px)}
    out.write_text(json.dumps(table, indent=1))
    return table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bvh_dir", type=Path)
    ap.add_argument("--out", type=Path, default=GAITS_JSON)
    a = ap.parse_args(argv)
    table = extract(a.bvh_dir, a.out)
    for name, g in table["gaits"].items():
        m = g["measured"]
        print(f"{name:11s} {g['clip']}  cycles {m['cycles']}  stride {m['stride']:.2f} leg  stance "
              f"{m['stance'][0]:.2f}/{m['stance'][1]:.2f}  lift {m['lift']:.3f}  hip {m['hip']:.3f}  lean {m['lean']:.1f}  "
              f"sway {m['sway']:.1f}  swing {m['swing']:.0f}  elbow {m['elbow']:.0f}  strike {m['strike']:.0f}  "
              f"toe_off {m['toe_off']:.0f}  {m['speed']:.2f} leg/s")
    print("->", a.out)


if __name__ == "__main__":
    main()
