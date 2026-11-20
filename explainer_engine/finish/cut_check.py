"""Cut checks of a finished picture (final plan S14, W7): blended frames and J/L offsets.

``blended_stretches`` is the method of the vendored codepawl ``check_blended_cuts.py`` (``.claude/skills/v-edit-video/scripts``): a
frame is blended when the frames a few steps either side differ a lot (a change of shot) and the frame itself is close to a weighted
mix of the two. The vendored file is loaded from its folder (never copied, never edited); its pure functions do the finding, the
frames come from ffmpeg through the same file. Rows are returned for ``validators/edit.py`` (VAL-EDT-01, VAL-EDT-02)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from explainer_engine.qa import gates as G

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "v-edit-video" / "scripts" / "check_blended_cuts.py"
FPS_J_L = 24


def _vendored():
    if not SCRIPT.exists():
        return None
    spec = importlib.util.spec_from_file_location("v_check_blended_cuts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # no __pycache__ inside the vendored folder
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = keep
    return mod


def blended_stretches(video, step: int = 3) -> dict:
    """``{stretches: [[first_frame, last_frame], ...], fps, frames}`` of the blended frames in ``video``; raises ``RuntimeError``
    when the vendored script, numpy or ffmpeg is missing."""
    mod = _vendored()
    if mod is None:
        raise RuntimeError(f"the vendored check_blended_cuts.py is missing at {SCRIPT}")
    frames = mod.read_frames(str(video))
    return {"stretches": mod.group(mod.blended_frames(frames, step)), "fps": mod.frame_rate(str(video)), "frames": int(len(frames))}


def blended_row(video, allow: int = 0, gate: str = "VAL-EDT-01") -> dict:
    """No blended cut in the picture (house rule, ``allow`` stretches are allowed, the vendored default is 0): a dissolve the plan did not
    ask for is a finding. A miss is REVIEW (a person looks: the plan may have asked for a dissolve), never BLOCK, no registry number."""
    if not Path(video).is_file():
        return G.row(gate, None, f"NOT_RUN: {video} does not exist")
    try:
        r = blended_stretches(video)
    except (RuntimeError, OSError, ValueError, ImportError) as exc:
        return G.row(gate, None, f"NOT_RUN: blended cuts could not be checked ({type(exc).__name__}: {exc})")
    except Exception as exc:   # subprocess.CalledProcessError of ffmpeg
        return G.row(gate, None, f"NOT_RUN: ffmpeg could not read the picture ({type(exc).__name__})")
    n = len(r["stretches"])
    times = [(round(a / r["fps"], 2), round(b / r["fps"], 2)) for a, b in r["stretches"][:8]]
    return G.row(gate, n <= allow, f"{n} blended stretch(es) (allowed {allow}): {times}" if n else "no blended cut found", r["stretches"][:20],
                 level=G.REVIEW)


def jl_offsets(cards: list[dict], gate: str = "VAL-EDT-02") -> list[dict]:
    """J/L offsets of the shot cards: ``edit.j_offset_frames`` / ``edit.l_offset_frames`` (integer frames at 24 fps, 0 or absent =
    none, agreed with the plan thread 2026-11-19). A master shot (``is_master``: the first shot of a scene, so the cut into it is a scene
    boundary) uses BP-117's scene_boundary_jl_s, any other cut its dialogue_action_jl_s; both bridges are measured in seconds.
    REVIEW on a miss (BP-117 is a hypothesis)."""
    from explainer_engine.validators import _common as C
    bands = {"action": C.T("BP-117", "dialogue_action_jl_s"), "scene": C.T("BP-117", "scene_boundary_jl_s")}
    if None in bands.values():
        return [C.missing_threshold(gate, "BP-117", "dialogue_action_jl_s/scene_boundary_jl_s")]
    rows = []
    for c in cards:
        edit = c.get("edit") or {}
        kind = "scene" if c.get("is_master") else "action"
        lo, hi = bands[kind]
        for side in ("j", "l"):
            n = int(edit.get(f"{side}_offset_frames") or 0)
            if not n:
                continue
            s = abs(n) / FPS_J_L
            rows.append(C.check(f"{gate}:{c.get('shot_id', '?')}:{side}", lo <= s <= hi, "BP-117",
                                f"{side.upper()}-cut of {n} frames = {s:.2f} s; allowed {lo}-{hi} s ({kind})", s))
    return rows or [G.row(gate, None, "NOT_RUN: no shot card carries a J or L offset")]
