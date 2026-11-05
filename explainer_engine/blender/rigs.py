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
``three_d.skeleton_id``) or needs a retarget; the retarget itself (Quaternius UAL onto UBC, or onto an MPFB2/Rigify body)
is built by ICW-06 on PoC 1's measured bone maps, so ``plan`` never invents a bone map.

The shape-key names default to ``mouth_A`` .. ``mouth_X``: the channel's own heads are modelled with those names (no head
exists yet; ICW-06 may pass another mapping).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from explainer_engine.assets import library as L

BASIC = ("A", "B", "C", "D", "E", "F")
EXTENDED = ("G", "H", "X")
SHAPES = BASIC + EXTENDED
DEFAULT_KEYS = {s: f"mouth_{s}" for s in SHAPES}
RECOGNIZERS = ("pocketSphinx", "phonetic")
EPS = 1e-9


def rhubarb_argv(wav: Path | str, dialog: Path | str, out: Path | str, *, exe: str = "rhubarb",
                 recognizer: str = "pocketSphinx", extended: str = "GHX") -> list[str]:
    """The Rhubarb command for one voiced line: JSON out, the line's text as the dialog file, the input file last."""
    if recognizer not in RECOGNIZERS:
        raise ValueError(f"recognizer is one of {RECOGNIZERS}")
    if any(c not in EXTENDED for c in extended):
        raise ValueError(f"extended shapes are a subset of {''.join(EXTENDED)}")
    return [exe, "-r", recognizer, "-f", "json", "--extendedShapes", extended, "-d", str(dialog), "-o", str(out), str(wav)]


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

    @staticmethod
    def plan(animation: dict, rig: dict) -> dict:
        if animation["kind"] != "animation" or rig["kind"] != "rig":
            raise ValueError(f"plan takes an animation and a rig, not a {animation['kind']} and a {rig['kind']}")
        a, r = (animation.get("three_d") or {}), (rig.get("three_d") or {})
        if not r.get("skeleton_id"):
            raise ValueError(f"{rig['id']}: a rig names its skeleton (three_d.skeleton_id)")
        if a.get("skeleton_id") == r["skeleton_id"]:
            return {"action": "play", "animation": animation["id"], "rig": rig["id"], "skeleton": r["skeleton_id"]}
        return {"action": "retarget", "animation": animation["id"], "rig": rig["id"], "from": a.get("skeleton_id"),
                "to": r["skeleton_id"], "rig_profile": r.get("rig_profile"),
                "note": "no bone map yet: ICW-06 builds the retarget on PoC 1 (roadmap 21.6)"}

    def playable(self, rig_id: str, tags: list[str] | None = None) -> list[dict]:
        """The usable animations authored for this rig's skeleton."""
        rig = L.get(rig_id, lib=self.lib)
        sk = (rig.get("three_d") or {}).get("skeleton_id")
        return L.find(kind="animation", skeleton_id=sk, tags=tags, lib=self.lib) if sk else []
