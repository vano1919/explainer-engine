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
