"""Rigs and mouths for the Blender shots (roadmap section 11 ``RigAdapter`` / ``LipSync``, 21.5 #4 and #9; ICW-05 lays the
library side, ICW-06 builds the retarget on PoC 1).

**LipSync** turns Rhubarb Lip Sync's JSON (MIT, github.com/DanielSWolf/rhubarb-lip-sync, README read 2026-11-05) into one
shape-key value track per mouth shape, no speech recognition of our own:

    rhubarb -f json -d <line.txt> -o <shot>.json <line.wav>          (``rhubarb_argv``; the dialog text is always given)

The file is ``{"metadata": {"soundFile", "duration"}, "mouthCues": [{"start", "end", "value"}, ...]}``: times in seconds
(truncated to 0.01 s), each cue's end equal to the next one's start, values the six basic shapes A-F and the extended G, H
and X (X = the idle mouth of pauses; without X in ``--extendedShapes`` Rhubarb rests on A). Every frame of the shot gets
exactly one shape: the cue that holds the frame's start time ``f / fps``; a frame no cue holds (before the first cue, in a
gap, after the last) gets the rest shape, so the mouth is closed on silence. Cues are sorted and never overlap (an overlap
is refused). Tracks are keyed at the shot's fps (24) with a one-frame blend: at a change from shape S to shape T on frame f,
S is 1 and T is 0 on frame f-1, and S is 0 and T is 1 on frame f (``blend_frames=0`` keys a hard cut for CONSTANT
interpolation). Eyes, brows and head come from the animation layer, not from Rhubarb (roadmap 21.5 #9).

**RigAdapter.plan** decides from the library records alone whether an animation plays on a rig as it is (the same
``three_d.skeleton_id``) or needs a retarget. ICW-06 (PoC 1, measured 2026-11-05): the Universal Animation Library and every
Universal Base Characters body, hair and Modular Outfits costume carry the same 65-joint skeleton, joint for joint by name
(``bone_map`` on the GLBs' joint lists: 65 of 65, no rename), so a UAL clip plays on the character's armature directly (an NLA
strip, ``bpy/render_shot.py``); a rig whose ``three_d`` is in a model or costume record (the UBC GLBs carry their armature)
is a rig for ``plan``. A different skeleton (an MPFB2/Rigify body, PoC 1b) gets a ``retarget`` plan with the measured name map
and the unmatched joints; the retarget solver itself is not built (out of scope unless PoC 1 fails, roadmap 21.10).

The shape-key names default to ``mouth_A`` .. ``mouth_X``: the ICW-06 heads carry them (``characters.json`` mouth keys).
**LipSync.plan** caps a lip-synced shot at BP-108 ``dialogue_shot_max_s`` (a visible voiced line is at most that long; a
longer line is cut into shots by the planner, never keyed past the cap).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.standards import sourced_rules as SR

BASIC = ("A", "B", "C", "D", "E", "F")
EXTENDED = ("G", "H", "X")
SHAPES = BASIC + EXTENDED
DEFAULT_KEYS = {s: f"mouth_{s}" for s in SHAPES}
RECOGNIZERS = ("pocketSphinx", "phonetic")
EPS = 1e-9


def rhubarb_argv(wav: Path | str, dialog: Path | str | None, out: Path | str, *, exe: str = "rhubarb",
                 recognizer: str = "pocketSphinx", extended: str = "GHX") -> list[str]:
    """The Rhubarb command for one voiced line: JSON out, the line's text as the dialog file, the input file last. An episode
    line always has its text (the script); ``dialog=None`` is only for a reused take whose text is not on record (a test
    clip): Rhubarb then recognises the words itself (README: less precise)."""
    if recognizer not in RECOGNIZERS:
        raise ValueError(f"recognizer is one of {RECOGNIZERS}")
    if any(c not in EXTENDED for c in extended):
        raise ValueError(f"extended shapes are a subset of {''.join(EXTENDED)}")
    d = ["-d", str(dialog)] if dialog is not None else []
    return [exe, "-r", recognizer, "-f", "json", "--extendedShapes", extended, *d, "-o", str(out), str(wav)]


def run_rhubarb(wav: Path | str, out: Path | str, *, dialog: Path | str | None = None, exe: str = "rhubarb", run=None) -> dict:
    """Rhubarb as a subprocess (an external MIT tool, never imported); returns the checked cues of ``load_cues``."""
    import subprocess
    run = run or subprocess.run
    p = run(rhubarb_argv(wav, dialog, out, exe=exe), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"rhubarb failed on {Path(wav).name}: {(p.stderr or '').strip()[-400:]}")
    return load_cues(Path(out))


def load_cues(doc: dict | Path | str) -> dict:
    """A Rhubarb JSON (a dict or a path) checked: known shapes, start < end, sorted, no overlap. Returns
    {"duration": s, "cues": [(start, end, shape), ...]}."""
    if not isinstance(doc, dict):
        doc = json.loads(Path(doc).read_text(encoding="utf-8"))
    cues = []
    for i, c in enumerate(doc.get("mouthCues", [])):
        s, e, v = float(c["start"]), float(c["end"]), c["value"]
        if v not in SHAPES:
            raise ValueError(f"cue {i}: unknown mouth shape {v!r} (Rhubarb uses {''.join(SHAPES)})")
        if not e > s:
            raise ValueError(f"cue {i}: end {e} is not after start {s}")
        if cues and s < cues[-1][1] - EPS:
            raise ValueError(f"cue {i}: starts at {s}, before the previous cue ends ({cues[-1][1]}): cues overlap or are unsorted")
        cues.append((s, e, v))
    duration = float((doc.get("metadata") or {}).get("duration") or (cues[-1][1] if cues else 0.0))
    return {"duration": duration, "cues": cues}


def shape_per_frame(cues: dict, fps: int = 24, frames: int | None = None, rest: str = "X") -> list[str]:
    """One shape per frame (0-based): the cue holding ``f / fps``, else ``rest``."""
    if rest not in SHAPES:
        raise ValueError(f"rest shape {rest!r} is not a Rhubarb shape")
    n = frames if frames is not None else math.ceil(cues["duration"] * fps - EPS)
    out, k, cs = [], 0, cues["cues"]
    for f in range(n):
        t = f / fps
        while k < len(cs) and cs[k][1] <= t + EPS:
            k += 1
        out.append(cs[k][2] if k < len(cs) and cs[k][0] <= t + EPS else rest)
    return out


def tracks(shapes: list[str], *, blend_frames: int = 1, shape_keys: dict | None = None) -> dict[str, list[list]]:
    """{shape-key name: [[frame, value], ...]} from one shape per frame; every shape key gets a key on frame 0 and on the
    last frame, plus the keys around each change (``blend_frames`` 1 = a one-frame blend, 0 = a hard cut)."""
    if blend_frames not in (0, 1):
        raise ValueError("blend_frames is 1 (a one-frame blend) or 0 (a hard cut)")
    keys = shape_keys or DEFAULT_KEYS
    missing = sorted(set(shapes) - set(keys))
    if missing:
        raise ValueError(f"no shape key named for {', '.join(missing)}")
    out: dict[str, dict[int, float]] = {keys[s]: {} for s in SHAPES if s in keys}
    if not shapes:
        return {k: [] for k in out}
    last = len(shapes) - 1
    for s, name in ((s, keys[s]) for s in SHAPES if s in keys):
        out[name][0] = 1.0 if shapes[0] == s else 0.0
        out[name][last] = 1.0 if shapes[last] == s else 0.0
    for f in range(1, len(shapes)):
        prev, cur = shapes[f - 1], shapes[f]
        if prev == cur:
            continue
        if blend_frames:
            out[keys[prev]][f - 1], out[keys[cur]][f - 1] = 1.0, 0.0
        out[keys[prev]][f], out[keys[cur]][f] = 0.0, 1.0
    return {name: [[f, v] for f, v in sorted(fr.items())] for name, fr in out.items()}


class LipSync:
    """Rhubarb cues -> shape-key tracks -> keyframes on a head's shape keys (roadmap section 11)."""

    def __init__(self, fps: int = 24, *, blend_frames: int = 1, shape_keys: dict | None = None, extended: str = "GHX"):
        self.fps, self.blend_frames = fps, blend_frames
        self.shape_keys = shape_keys or DEFAULT_KEYS
        self.rest = "X" if "X" in extended else "A"  # Rhubarb's own rest shape without X

    def frames(self, cues: dict | Path | str, frames: int | None = None) -> list[str]:
        return shape_per_frame(load_cues(cues), self.fps, frames, self.rest)

    def tracks(self, cues: dict | Path | str, frames: int | None = None) -> dict[str, list[list]]:
        return tracks(self.frames(cues, frames), blend_frames=self.blend_frames, shape_keys=self.shape_keys)

    def plan(self, cues: dict | Path | str, frames: int, *, offset_s: float = 0.0) -> dict:
        """The ``lipsync`` block of a cast member (``characters.scene_object``): the shot's ``frames`` from ``offset_s`` into the
        line, one shape per frame, the tracks. Refuses a shot longer than BP-108 ``dialogue_shot_max_s``."""
        cap = SR.T("BP-108", "dialogue_shot_max_s")
        if frames / self.fps > cap + EPS:
            raise ValueError(f"a lip-synced shot of {frames / self.fps:.2f} s is over BP-108's {cap} s for a visible voiced line")
        c = load_cues(cues)
        if offset_s:
            c = {"duration": max(c["duration"] - offset_s, 0.0),
                 "cues": [(s - offset_s, e - offset_s, v) for s, e, v in c["cues"] if e - offset_s > EPS]}
            c["cues"] = [(max(s, 0.0), e, v) for s, e, v in c["cues"]]
        shapes = shape_per_frame(c, self.fps, frames, self.rest)
        return {"fps": self.fps, "frames": frames, "offset_s": offset_s, "shapes": "".join(shapes),
                "tracks": tracks(shapes, blend_frames=self.blend_frames, shape_keys=self.shape_keys)}

    def busiest(self, cues: dict | Path | str, frames: int, *, step_s: float = 0.25) -> float:
        """The offset (s) of the ``frames``-long window of a line with the most mouth changes (a reused take's clip shows
        speech, not the breath before it); windows start every ``step_s`` and stay inside the line."""
        c = load_cues(cues)
        span = frames / self.fps
        best, best_n = 0.0, -1
        t = 0.0
        while t + span <= c["duration"] + EPS:
            shapes = shape_per_frame({"duration": c["duration"], "cues": [(s - t, e - t, v) for s, e, v in c["cues"] if e > t]},
                                     self.fps, frames, self.rest)
            n = sum(1 for a, b in zip(shapes, shapes[1:]) if a != b) + sum(1 for x in shapes if x != self.rest) / 1000
            if n > best_n + EPS:
                best, best_n = t, n
            t = round(t + step_s, 6)
        return best

    @staticmethod
    def apply(track_map: dict[str, list[list]], key_blocks, start_frame: int = 1) -> int:
        """Key every value on the head's shape keys (``key_blocks``: name -> a Blender ShapeKey, or anything with
        ``value`` and ``keyframe_insert``), offset to the shot's first frame; runs inside Blender. Returns the key count."""
        missing = sorted(n for n in track_map if n not in key_blocks)
        if missing:
            raise KeyError(f"the head has no shape keys {', '.join(missing)}")
        n = 0
        for name, keys in sorted(track_map.items()):
            kb = key_blocks[name]
            for frame, value in keys:
                kb.value = value
                kb.keyframe_insert(data_path="value", frame=start_frame + frame)
                n += 1
        return n


class ActionVisemes:
    """Rhubarb shapes -> pose-bone channel tracks, for a rig whose mouth is bones, not shape keys (WP-Q4: the Blender Studio
    characters Rain and Storm, CloudRig face with MSTR/ACT controls). ``poses`` maps each shape to the bones it moves::

        {"A": {"MSTR-Jaw": {"rot": [0, 0, 0]}}, "D": {"MSTR-Jaw": {"rot": [25, 0, 0]}, "MSTR-Mouth": {"scale": [1, 1, 1.1]}}}

    ``rot`` is degrees (XYZ euler), ``loc`` a bone-local offset in metres, ``scale`` a multiplier; anything a shape leaves out is
    the rest value (rot 0, loc 0, scale 1), so a pose never inherits the previous shape. Timing is ``LipSync.frames`` (the same
    cue-per-frame rule, X on silence); keys sit on the first and last frame and on every change, previous value on frame f-1
    and new value on frame f, exactly as the shape-key tracks do. ``apply`` runs inside Blender on a posed armature.
    """

    REST = {"rot": 0.0, "loc": 0.0, "scale": 1.0}
    PROPS = {"rot": "rotation_euler", "loc": "location", "scale": "scale"}

    def __init__(self, poses: dict, fps: int = 24, *, extended: str = "GHX"):
        missing = sorted(set(SHAPES) - set(poses)) if "X" in extended else sorted(set(BASIC) - set(poses))
        if missing:
            raise ValueError(f"the pose table has no pose for {', '.join(missing)}")
        for shape, bones in poses.items():
            for bone, ch in bones.items():
                bad = sorted(set(ch) - set(self.PROPS))
                if bad or any(len(v) != 3 for v in ch.values()):
                    raise ValueError(f"pose {shape}/{bone}: channels are rot, loc, scale with three numbers each")
        self.poses, self.fps = poses, fps
        self.lip = LipSync(fps, extended=extended)

    def channels(self) -> list[tuple]:
        """Every (bone, prop, index) any shape touches, sorted; each is keyed on every key frame so a shape that leaves it out
        returns it to rest."""
        return sorted({(b, p, i) for bones in self.poses.values() for b, ch in bones.items() for p in ch for i in range(3)})

    def value(self, shape: str, chan: tuple) -> float:
        b, p, i = chan
        v = self.poses[shape].get(b, {}).get(p)
        return float(v[i]) if v is not None else self.REST[p]

    def tracks(self, cues: dict | Path | str, frames: int | None = None) -> dict[str, list[list]]:
        """{"bone|prop|index": [[frame, value], ...]} (prop is the Blender property: rotation_euler is in radians)."""
        shapes = self.lip.frames(cues, frames)
        return self.tracks_for(shapes)

    def tracks_for(self, shapes: list[str]) -> dict[str, list[list]]:
        out: dict[str, list[list]] = {}
        if not shapes:
            return out
        keyed = {0, len(shapes) - 1}
        for f in range(1, len(shapes)):
            if shapes[f] != shapes[f - 1]:
                keyed.update((f - 1, f))
        for chan in self.channels():
            b, p, i = chan
            k = f"{b}|{self.PROPS[p]}|{i}"
            out[k] = [[f, round(math.radians(self.value(shapes[f], chan)) if p == "rot" else self.value(shapes[f], chan), 6)]
                      for f in sorted(keyed)]
        return out

    @staticmethod
    def apply(track_map: dict[str, list[list]], pose_bones, start_frame: int = 1) -> int:
        """Key every channel on the armature's pose bones (``pose_bones``: name -> a Blender PoseBone); runs inside Blender.
        Returns the key count."""
        missing = sorted({k.split("|")[0] for k in track_map} - set(pose_bones))
        if missing:
            raise KeyError(f"the rig has no pose bones {', '.join(missing)}")
        n = 0
        for key, pts in sorted(track_map.items()):
            bone, prop, idx = key.split("|")
            pb = pose_bones[bone]
            for frame, value in pts:
                vec = list(getattr(pb, prop))
                vec[int(idx)] = value
                setattr(pb, prop, vec)
                pb.keyframe_insert(data_path=prop, index=int(idx), frame=start_frame + frame)
                n += 1
        return n


class RigAdapter:
    """Which animations a rig plays as they are, and which need a retarget (21.5 #4); from library records only."""

    def __init__(self, lib: dict | None = None):
        self.lib = lib if lib is not None else L.load()

    RIG_KINDS = ("rig", "model", "costume")  # a UBC GLB carries its armature: a model or costume record is a rig for plan

    @staticmethod
    def plan(animation: dict, rig: dict) -> dict:
        if animation["kind"] != "animation" or rig["kind"] not in RigAdapter.RIG_KINDS:
            raise ValueError(f"plan takes an animation and a rig, not a {animation['kind']} and a {rig['kind']}")
        a, r = (animation.get("three_d") or {}), (rig.get("three_d") or {})
        if not r.get("skeleton_id"):
            raise ValueError(f"{rig['id']}: a rig names its skeleton (three_d.skeleton_id)")
        if a.get("skeleton_id") == r["skeleton_id"]:
            return {"action": "play", "animation": animation["id"], "rig": rig["id"], "skeleton": r["skeleton_id"]}
        return {"action": "retarget", "animation": animation["id"], "rig": rig["id"], "from": a.get("skeleton_id"),
                "to": r["skeleton_id"], "rig_profile": r.get("rig_profile"),
                "note": "no retarget solver: the UBC/UAL set shares one skeleton (PoC 1); a foreign skeleton needs bone_map first"}

    def playable(self, rig_id: str, tags: list[str] | None = None) -> list[dict]:
        """The usable animations authored for this rig's skeleton."""
        rig = L.get(rig_id, lib=self.lib)
        sk = (rig.get("three_d") or {}).get("skeleton_id")
        return L.find(kind="animation", skeleton_id=sk, tags=tags, lib=self.lib) if sk else []


def bone_map(source_joints: list[str], target_joints: list[str]) -> dict:
    """The joint-name map of two skeletons (PoC 1): {map, unmatched_source, unmatched_target, identical}. Exact names only:
    the map is measured, never guessed (no fuzzy matching); ``identical`` = same names in the same order."""
    tgt = set(target_joints)
    m = {j: j for j in source_joints if j in tgt}
    return {"map": m, "unmatched_source": [j for j in source_joints if j not in tgt],
            "unmatched_target": [j for j in target_joints if j not in set(source_joints)],
            "identical": list(source_joints) == list(target_joints)}


# --- PoC 1 and PoC 2 measurements (roadmap 21.6) ----------------------------------------------------------------------------------

POC1_SLIDE_M = 0.02      # roadmap 21.6 PoC 1 pass line: foot slide under 2 cm per cycle
POC2_OFFSET_FRAMES = 1.0  # PoC 2 pass lines: mean |offset| at most 1 frame,
POC2_OPEN_SILENCE = 2     # and no open mouth on silence for more than 2 frames
CONTACT_BAND_M = 0.015    # analysis constant: a foot is planted while within 1.5 cm of its lowest height in the clip


def _runs(flags: list[bool], *, wrap: bool = True) -> list[tuple[int, int]]:
    """(start, end) of each run of True, end exclusive; a run that wraps the loop's end joins its start."""
    n, out, i = len(flags), [], 0
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    if wrap and len(out) > 1 and out[0][0] == 0 and out[-1][1] == n:
        s, _ = out.pop()
        out[0] = (s, n + out[0][1])
    return out


def foot_slide(samples: list[dict], fps: int, *, feet=("foot_l", "foot_r"), root: str = "root",
               root_speed_mps: float | None = None, loop: bool = True) -> dict:
    """PoC 1's foot-slide line on one clip (``bpy/measure_clips.py`` samples: per frame {bone: [x, y, z]}). A foot is planted
    while within ``CONTACT_BAND_M`` of its lowest height; its slide is how far it travels on the ground while planted, after
    taking away the body's own travel at ``root_speed_mps`` (None = the clip's natural speed: the planted feet's mean ground
    speed when the clip is in place, else its root's). Returns {feet: {foot: {runs, slide_m}}, natural_speed_mps, root_travel_m,
    in_place, slide_m (worst), passed}."""
    n = len(samples)
    if n < 2:
        raise ValueError("a clip needs at least two frames")
    r0, r1 = samples[0][root], samples[-1][root]
    root_travel = math.hypot(r1[0] - r0[0], r1[1] - r0[1])
    in_place = root_travel < POC1_SLIDE_M
    per, speeds = {}, []
    for foot in feet:
        z = [s[foot][2] for s in samples]
        low = min(z)
        flags = [h <= low + CONTACT_BAND_M for h in z]
        runs = _runs(flags, wrap=loop)
        rows = []
        for a, b in runs:
            idx = [k % n for k in range(a, b)]
            p, q = samples[idx[0]][foot], samples[idx[-1]][foot]
            rp, rq = samples[idx[0]][root], samples[idx[-1]][root]
            d = math.hypot((q[0] - p[0]) - (rq[0] - rp[0]), (q[1] - p[1]) - (rq[1] - rp[1]))   # foot travel against the root
            t = (len(idx) - 1) / fps
            rows.append({"frames": [idx[0], idx[-1]], "seconds": round(t, 4), "travel_m": round(d, 4)})
            if t > 0:
                speeds.append(d / t)
        per[foot] = rows
    natural = (sum(speeds) / len(speeds) if speeds else 0.0) if in_place else root_travel / ((n - 1) / fps)
    v = natural if root_speed_mps is None else root_speed_mps
    worst = 0.0
    for foot, rows in per.items():
        for r in rows:
            r["slide_m"] = round(abs(r["travel_m"] - v * r["seconds"]) if in_place else r["travel_m"], 4)
            worst = max(worst, r["slide_m"])
    return {"feet": per, "natural_speed_mps": round(natural, 4), "root_speed_mps": round(v, 4), "root_travel_m": round(root_travel, 4),
            "in_place": in_place, "slide_m": round(worst, 4), "passed": worst < POC1_SLIDE_M}


def lipsync_measure(cues: dict | Path | str, words: list[dict], fps: int = 24, *, rest: str = "X") -> dict:
    """PoC 2's two lines on a voiced line: ``words`` = [{start, end}, ...] in seconds (word timings of the same take, e.g.
    ``audio/local_words.py``). Offset: for each word, the nearest mouth opening (a cue other than the rest shape and A, the
    closed lips) to the word's start; its mean |offset| in frames. Silence: frames outside every word window whose shape is
    open; the longest such run in frames. Pass lines POC2_OFFSET_FRAMES and POC2_OPEN_SILENCE."""
    c = load_cues(cues)
    closed = {rest, "A", "X"}
    opens = [s for s, e, v in c["cues"] if v not in closed]
    offs = []
    for w in words:
        if opens:
            near = min(opens, key=lambda s: abs(s - w["start"]))
            offs.append((near - w["start"]) * fps)
    shapes = shape_per_frame(c, fps, None, rest)
    silent_open = []
    for f, s in enumerate(shapes):
        t = f / fps
        spoken = any(w["start"] - EPS <= t <= w["end"] + EPS for w in words)
        silent_open.append(not spoken and s not in closed)
    runs = _runs(silent_open, wrap=False)
    longest = max((b - a for a, b in runs), default=0)
    mean_abs = sum(abs(o) for o in offs) / len(offs) if offs else None
    return {"words": len(words), "cues": len(c["cues"]), "mean_abs_offset_frames": round(mean_abs, 3) if mean_abs is not None else None,
            "mean_offset_frames": round(sum(offs) / len(offs), 3) if offs else None, "open_on_silence_frames": sum(silent_open),
            "longest_open_silence_run": longest,
            "passed": mean_abs is not None and mean_abs <= POC2_OFFSET_FRAMES and longest <= POC2_OPEN_SILENCE}


def main(argv: list[str] | None = None) -> int:
    """``measure-lipsync --cues C --words W``: PoC 2's lines (W = a JSON list of {start, end} or {"words": [...]})."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.rigs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure-lipsync")
    m.add_argument("--cues", required=True)
    m.add_argument("--words", required=True)
    a = ap.parse_args(argv)
    w = json.loads(Path(a.words).read_text(encoding="utf-8"))
    words = w["words"] if isinstance(w, dict) else w
    res = lipsync_measure(Path(a.cues), words)
    json.dump(res, sys.stdout, indent=1)
    print()
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
