"""Cheap battles of thousands (overnight plan T-E; MOTION_RESEARCH.md Group 7 "WP-M crowd", source notes m5 Q1-Q5): LOD tiers by
screen height, soldiers as Geometry Nodes instances, never thousands of armatures.

| Tier | When (h = focal_px x 1.8 m / distance) | What draws it |
|---|---|---|
| T0 hero | h > HERO_PX at the first frame, at most ``hero_max`` | today's path: a full UBC rig copy (``render_shot._copy_rig``) |
| T1 mid | FAR_PX < h, or a hero beyond ``hero_max`` | route A: a baked mesh-frame collection per template, GN Instance on Points + Pick Instance |
| T2 far | h <= FAR_PX | an animated yaw billboard: a quad facing the camera (yaw only), cell of an atlas (yaw bucket x frame) |

Synthesis of documented parts (D-115): the ICW-06 cast (Quaternius UBC + MCO, CC0) plays UAL1 clips through render_shot's NLA
code; ``bpy/crowd_bake.py`` bakes them with ``evaluated_get`` + ``meshes.new_from_object`` (Blender API) and renders the atlas with
the shot's own look; the GN tree uses the 5.2 manual's Instance on Points (Pick Instance), Collection Info, Scene Time, Object Info
and the Attribute node's Instancer lookup. The bake-a-loop-into-a-collection idea is the forum workaround m5 Q1 cites; the yaw
billboard is the classic animated impostor of m5 Q3. No add-on and no copied code.

This module is pure Python: formations, seeds, tiers and the closed-form motion are computed here, so tests check the same maths
the node tree evaluates. Every number is an engineering default of this proof (EST/HYP in Group 7), not a sourced rule; the
creator judges the clip (his open questions are listed in the proof's handoff).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

SCHEMA = "crowd_gn/1"
JOB_ID = "crowd_proof_te"
SOLDIER_M = 1.8          # the height the screen-size rule measures (Group 7)
HERO_PX = 250            # taller than this at the first frame: a full rig (T0), while there are hero slots
FAR_PX = 60              # this tall or shorter: a billboard (T2)
MASTER_W = 2560
BAKE_FRAMES = 32         # T1 meshes per clip (every clip is resampled to this cycle)
ATLAS_FRAMES = 16        # T2 atlas rows per clip
ATLAS_YAW = 8            # T2 yaw buckets (45 degrees)
ATLAS_CELL = (160, 240)  # px of one atlas cell (a 1.6 x 2.4 m window)
MID_TRIS = 2000          # T1 decimation target per soldier
MID_SHADOW_MAX_M = 40.0  # T1 soldiers nearer than this cast shadows; beyond, none (T2 never)
HERO_MAX = 30
WALK_MPS = 0.77          # Walk_Formal_Loop's natural speed, MEASURED (PROGRESS ICW-06, rigs.foot_slide): the advance is stride-matched
TEMPLATE_Y = -400.0      # templates are built behind the camera and hidden after the bake
FORMATIONS = ("line", "phalanx", "cohort", "shield_wall", "wedge", "rout")
COLUMNS = ("x", "y", "yaw", "slot", "far_slot", "phase", "speed", "vx", "vy", "delay")


class CrowdError(ValueError):
    pass


@dataclass(frozen=True)
class Formation:
    """A block of soldiers. ``clips`` are (UAL1 action, weight). ``speed_mps`` > 0 walks the block forward (facing) at that
    speed times the soldier's own speed factor; rank r starts ``rank_delay_s`` x r later (closed form, any frame alone)."""
    crowd_id: str
    type: str
    size: int
    files: int
    costume: str
    tint: str
    chars: tuple[str, ...]
    clips: tuple[tuple[str, float], ...]
    origin: tuple[float, float]
    facing_deg: float = 0.0    # 0 = +Y
    spacing_m: float = 1.25
    jitter_m: float = 0.22
    yaw_jitter_deg: float = 9.0
    speed_mps: float = 0.0
    rank_delay_s: float = 0.0
    speed_range: tuple[float, float] = (0.92, 1.08)

    @property
    def ranks(self) -> int:
        return math.ceil(self.size / self.files)

    def offsets(self, rng: random.Random) -> list[tuple[float, float, int]]:
        """(across, along, rank) of every soldier in the block's own frame (along > 0 = in front), before jitter."""
        if self.type not in FORMATIONS:
            raise CrowdError(f"{self.crowd_id}: unknown formation {self.type!r} (known: {', '.join(FORMATIONS)})")
        if self.size < 1 or self.files < 1:
            raise CrowdError(f"{self.crowd_id}: size and files must be positive")
        s, out = self.spacing_m, []
        if self.type == "wedge":       # rank r holds 2r + 1 soldiers, the point in front
            r = 0
            while len(out) < self.size:
                for c in range(2 * r + 1):
                    if len(out) < self.size:
                        out.append(((c - r) * s, -r * s, r))
                r += 1
            return out
        if self.type == "rout":        # a broken mass: scattered over the block's area, every rank its own
            w, d = self.files * s, self.ranks * s
            return [(rng.uniform(-w / 2, w / 2), -rng.uniform(0, d), 0) for _ in range(self.size)]
        dense = {"phalanx": 0.72, "shield_wall": 0.64}.get(self.type, 1.0)
        for n in range(self.size):
            r, c = divmod(n, self.files)
            gap = (c // 10) * s * 1.5 if self.type == "cohort" else 0.0      # maniples: a lane every ten files
            out.append(((c - (self.files - 1) / 2) * s * dense + gap, -r * s * dense, r))
        if self.type == "cohort":
            mid = sum(u for u, _, _ in out) / len(out)
            out = [(u - mid, v, r) for u, v, r in out]
        return out


def seed_for(shot_id: str, crowd_id: str) -> int:
    """The formation seed: the same shot and crowd give the same soldiers on every machine; another shot gets others."""
    return int(hashlib.sha256(f"{shot_id}/{crowd_id}".encode()).hexdigest()[:12], 16)


def focal_px(lens_mm: float, *, sensor_mm: float = 36.0, width_px: int = MASTER_W) -> float:
    if lens_mm <= 0 or sensor_mm <= 0:
        raise CrowdError("lens and sensor must be positive")
    return width_px * lens_mm / sensor_mm


def screen_px(distance_m: float, lens_mm: float) -> float:
    """The height in master-frame pixels of a 1.8 m soldier ``distance_m`` from the camera (Group 7's h)."""
    return focal_px(lens_mm) * SOLDIER_M / max(distance_m, 1e-6)


def borders(lens_mm: float, *, hero_px: float = HERO_PX, far_px: float = FAR_PX) -> dict[str, float]:
    """The tier borders in metres: a soldier is ``hero_px`` tall at ``hero_max_m`` and ``far_px`` tall at ``far_min_m``."""
    f = focal_px(lens_mm)
    return {"hero_max_m": round(f * SOLDIER_M / hero_px, 4), "far_min_m": round(f * SOLDIER_M / far_px, 4)}


def tier_of(distance_m: float, lens_mm: float, *, hero: bool = True, hero_px: float = HERO_PX, far_px: float = FAR_PX) -> str:
    h = screen_px(distance_m, lens_mm)
    if h > hero_px and hero:
        return "hero"
    return "mid" if h > far_px else "far"


def position(x: float, y: float, vx: float, vy: float, delay: float, seconds: float) -> tuple[float, float]:
    """Closed-form ground position at ``seconds`` into the shot (the node tree's Set Position): no state, so frame 1000 of a
    chunk started at 900 is the same point as frame 1000 of a run started at 0 (RULE-R1)."""
    t = max(0.0, seconds - delay)
    return x + vx * t, y + vy * t


def clip_index(frame: float, rate: float, phase: float, n: int) -> int:
    """The baked mesh a soldier shows: floor(wrap(frame x rate + phase, n)), the node tree's index (Pick Instance wraps too)."""
    v = frame * rate + phase
    return int(math.floor(v - n * math.floor(v / n))) % n


def _pick(rng: random.Random, clips) -> int:
    x, acc = rng.random() * sum(w for _, w in clips), 0.0
    for i, (_, w) in enumerate(clips):
        acc += w
        if x < acc:
            return i
    return len(clips) - 1


def plan(formations: tuple[Formation, ...], camera: dict, *, shot_id: str, bake_frames: int = BAKE_FRAMES,
         hero_max: int = HERO_MAX, far_px: float = FAR_PX) -> dict:
    """The ``crowds`` block of a described scene: T1 templates (formation x character x clip), T2 far templates (formation x
    clip, first character), the heroes (T0 soldiers taken out of the points) and one column per point attribute."""
    if bake_frames < 4:
        raise CrowdError("bake_frames must be at least 4")
    templates, far, slot_of, far_of = [], [], {}, {}
    for fm in formations:
        if not fm.clips or any(w <= 0 for _, w in fm.clips):
            raise CrowdError(f"{fm.crowd_id}: clips need positive weights")
        lo, hi = fm.speed_range
        if not 0 < lo <= hi <= 2:
            raise CrowdError(f"{fm.crowd_id}: speed_range must satisfy 0 < lo <= hi <= 2")
        for ci, ch in enumerate(fm.chars):      # one template per look x clip, shared by every formation that wears it
            for ki, (action, _) in enumerate(fm.clips):
                key = (ch, fm.costume, fm.tint, action)
                if key not in slot_of:
                    slot_of[key] = len(templates)
                    templates.append({"slot": len(templates), "name": f"crowd_tpl_{len(templates)}", "char": ch,
                                      "costume": fm.costume, "tint": fm.tint, "action": action})
        for ki, (action, _) in enumerate(fm.clips):
            key = (fm.chars[0], fm.costume, fm.tint, action)
            if key not in far_of:
                far_of[key] = len(far)
                far.append({"far_slot": len(far), "slot": slot_of[key]})
    cam, lens = camera["location"], camera["lens_mm"]
    cols = {k: [] for k in COLUMNS}
    heroes = []
    for fm in formations:
        rng = random.Random(seed_for(shot_id, fm.crowd_id))
        f = math.radians(fm.facing_deg)
        fwd, right = (-math.sin(f), math.cos(f)), (math.cos(f), math.sin(f))
        for u, v, rank in fm.offsets(rng):
            u += rng.uniform(-fm.jitter_m, fm.jitter_m)
            v += rng.uniform(-fm.jitter_m, fm.jitter_m)
            x, y = fm.origin[0] + u * right[0] + v * fwd[0], fm.origin[1] + u * right[1] + v * fwd[1]
            ci, ki = rng.randrange(len(fm.chars)), _pick(rng, fm.clips)
            s = rng.uniform(*fm.speed_range)
            yaw = (fm.facing_deg + rng.uniform(-180, 180)) if fm.type == "rout" else fm.facing_deg + rng.uniform(
                -fm.yaw_jitter_deg, fm.yaw_jitter_deg)
            vel, phase = fm.speed_mps * s, rng.uniform(0, bake_frames)
            row = {"x": round(x, 4), "y": round(y, 4), "yaw": round(yaw, 3), "slot": slot_of[(fm.chars[ci], fm.costume, fm.tint, fm.clips[ki][0])],
                   "far_slot": far_of[(fm.chars[0], fm.costume, fm.tint, fm.clips[ki][0])], "phase": round(phase, 4), "speed": round(s, 4),
                   "vx": round(fwd[0] * vel, 4), "vy": round(fwd[1] * vel, 4), "delay": round(rank * fm.rank_delay_s, 4)}
            if len(heroes) < hero_max and tier_of(math.dist((x, y, 0.0), cam), lens) == "hero":
                heroes.append(dict(row, crowd_id=fm.crowd_id, char=fm.chars[ci], costume=fm.costume, tint=fm.tint,
                                   action=fm.clips[ki][0], offset=int(phase * 2) % 64))
                continue
            for k in COLUMNS:
                cols[k].append(row[k])
    return {"schema": SCHEMA, "shot_id": shot_id, "bake_frames": bake_frames, "lens_mm": lens, "focal_px": round(focal_px(lens), 4),
            "soldier_m": SOLDIER_M, "far_px": far_px, "hero_px": HERO_PX, "borders": borders(lens, far_px=far_px), "mid_tris": MID_TRIS,
            "mid_shadow_max_m": MID_SHADOW_MAX_M,
            "atlas": {"frames": ATLAS_FRAMES, "yaw": ATLAS_YAW, "cell_px": list(ATLAS_CELL), "cell_m": [1.6, 2.4]},
            "templates": templates, "far_templates": far, "heroes": heroes, "count": len(cols["x"]), "points": cols,
            "formations": [{"crowd_id": fm.crowd_id, "type": fm.type, "size": fm.size, "files": fm.files} for fm in formations]}


def check(block: dict) -> list[str]:
    """Problems of a crowds block (empty = fine): the bpy side trusts what passes."""
    out = []
    if block.get("schema") != SCHEMA:
        out.append(f"schema is {block.get('schema')!r}, not {SCHEMA}")
    pts, n = block.get("points", {}), block.get("count", -1)
    for k in COLUMNS:
        if len(pts.get(k, [])) != n:
            out.append(f"points.{k} has {len(pts.get(k, []))} values, count is {n}")
    slots = {t["slot"] for t in block.get("templates", [])}
    fars = {t["far_slot"] for t in block.get("far_templates", [])}
    if any(s not in slots for s in pts.get("slot", [])) or any(s not in fars for s in pts.get("far_slot", [])):
        out.append("a point names a template slot that does not exist")
    if any(not 0 <= p < block.get("bake_frames", 0) for p in pts.get("phase", [])):
        out.append("a phase is outside 0..bake_frames")
    b = block.get("borders", {})
    if not 0 < b.get("hero_max_m", 0) < b.get("far_min_m", 0):
        out.append("borders must satisfy 0 < hero_max_m < far_min_m")
    if len(block.get("heroes", [])) > HERO_MAX:
        out.append(f"more than {HERO_MAX} heroes")
    return out


def tier_counts(block: dict, camera_xyz, *, seconds: float = 0.0) -> dict[str, int]:
    """Soldiers per tier with the camera at ``camera_xyz`` (the rule the node tree evaluates; heroes are fixed at plan time)."""
    p, lens = block["points"], block["lens_mm"]
    out = {"hero": len(block.get("heroes", [])), "mid": 0, "far": 0}
    for x, y, vx, vy, d in zip(p["x"], p["y"], p["vx"], p["vy"], p["delay"]):
        px, py = position(x, y, vx, vy, d, seconds)
        out[tier_of(math.dist((px, py, 0.0), camera_xyz), lens, hero=False, far_px=block.get("far_px", FAR_PX))] += 1
    return out


# --- the proof scene ---------------------------------------------------------------------------------------------------------------

SHOT_ID = "crowd_proof_5k"
CAMERA = {"location": [-18.0, -44.0, 6.5], "look_at": [4.0, 20.0, 0.5], "lens_mm": 32, "focus_distance_m": 40.0}
CAMERA_TO = {"location": [-15.5, -40.5, 6.0], "look_at": [4.0, 21.0, 0.5]}
PROOF_HEROES = 12        # T0 rigs in the proof (each deforms a full mesh on the CPU every frame)


def default_formations(count: int = 5000) -> tuple[Formation, ...]:
    """Two armies of ``count`` together: a cohort of peasants marching on, a phalanx of rangers holding with drawn swords and
    a fighting front; a wedge of rangers on the right flank."""
    if count < 3:
        raise CrowdError("a battle needs at least three soldiers")
    a = count // 2
    wedge = max(1, count // 10)
    b = count - a - wedge
    chars = ("ink_test_m", "ink_test_m2")
    fa = max(1, round(math.sqrt(a * 4)))
    fb = max(1, round(math.sqrt(b * 5)))
    return (Formation("legion_a", "cohort", a, fa, "costume.mco_male_peasant", "faction_a", chars, (("Walk_Formal_Loop", 1.0),),
                      (0.0, -2.0), 0.0, speed_mps=WALK_MPS, rank_delay_s=0.05),
            Formation("phalanx_b", "phalanx", b, fb, "costume.mco_male_ranger", "faction_b", chars,
                      (("Sword_Idle", 0.65), ("Sword_Attack", 0.35)), (0.0, 46.0), 180.0),
            Formation("wedge_b", "wedge", wedge, 1, "costume.mco_male_ranger", "faction_b", chars,
                      (("Sword_Idle", 0.5), ("Sword_Attack", 0.5)), (fb * 0.5 + 18.0, 40.0), 200.0))


def scene(paths: dict[str, Path], cpaths: dict[str, Path], *, count: int = 5000, frames: int = 24, shot_id: str = SHOT_ID,
          far_px: float = FAR_PX) -> dict:
    """Objects, camera, materials and the crowds block of the proof: a field between ridges, cannons, the armies. The T1/T2
    templates and the heroes are ordinary cast members (render_shot's character path); templates are parked behind the camera."""
    from explainer_engine.blender import characters as C
    from explainer_engine.blender import style_sheets as SS
    block = plan(default_formations(count), CAMERA, shot_id=shot_id, hero_max=PROOF_HEROES, far_px=far_px)
    base = SS.scenes(paths, cast="mannequin")["battle_wide"]
    objs = []
    for o in base["objects"]:
        if o["name"] == "field":
            objs.append(dict(o, params={"size": 900}))
        elif o["name"] == "ridge":
            objs.append(dict(o, location=[0, 190, -14], scale=[240, 50, 34]))
    for i, (x, y, r) in enumerate(((-170, 120, 70), (190, 140, 80), (-60, 260, 95), (110, 300, 110))):
        objs.append({"name": f"ridge_{i}", "add": "uv_sphere", "params": {"radius": 1, "segments": 48, "ring_count": 24},
                     "location": [x, y, -r * 0.55], "scale": [r, r * 0.7, r * 0.6], "material": "hill", "smooth": True})
    for i, (x, y, yaw) in enumerate(((-34, 18, 0), (-20, 17, 6), (16, 18, -4), (30, 17, 3), (-8, 60, 180), (12, 61, 176))):
        objs.append({"name": f"cannon_{i}", "append": {"path": str(paths["model.ph_cannon_01"])}, "location": [x, y, 0],
                     "scale": 1.0, "rotation_deg": [0, 0, yaw], "material": "cannon"})
    mats = {k: v for k, v in base["materials"].items() if k in {o.get("material") for o in objs}}

    def cast(name, char, costume, tint, xyz, yaw, action, offset):
        obj, tm = C.scene_object(name, char, costume, cpaths, location=xyz, yaw_deg=yaw + 180.0, action=action,
                                 action_offset=offset, tint=tint)
        for k, v in tm.items():
            if mats.get(k, v) != v:
                raise CrowdError(f"two cast members define material {k} differently")
            mats[k] = v
        return obj

    for t in block["templates"]:
        obj = cast(t["name"], t["char"], t["costume"], t["tint"], (t["slot"] * 4.0, TEMPLATE_Y, 0.0), 0.0, t["action"], 0)
        obj["crowd_template"] = t["slot"]
        objs.append(obj)
    for i, h in enumerate(block["heroes"]):
        obj = cast(f"hero_{i}", h["char"], h["costume"], h["tint"], (h["x"], h["y"], 0.0), h["yaw"], h["action"], h["offset"])
        if frames > 1 and (h["vx"] or h["vy"]):
            end = position(h["x"], h["y"], h["vx"], h["vy"], h["delay"], (frames - 1) / 24.0)
            obj["to"], obj["interp"] = {"location": [end[0], end[1], 0.0]}, "LINEAR"
        objs.append(obj)
    cam = dict(CAMERA, clip_end=2000.0)
    if frames > 1:
        cam["to"] = dict(CAMERA_TO)
    return {"objects": objs, "camera": cam, "materials": mats, "frames_total": frames, "crowds": block}


def render(out: Path, *, binary: str | None = None, look: str = "v01_reference_soft3d", count: int = 5000, frames: int = 24,
           scale: float = 0.5, samples: int = 16, device: str = "auto", far_px: float = FAR_PX, log=print) -> dict:
    """The proof clip through the ICW-04 adapter (HeadlessRender: checkpointed frames, a manifest). A scaled render is a test
    (CN-17 refuses anything but the master as a deliverable): its frames are kept and the row marked scaled. The spec stays
    shot_spec/2 with the crowd in the template hash; the ``scene.crowds`` fields ride WP-Q1's shot_spec/3 (Fable, 22:11 UTC)."""
    from explainer_engine.blender import characters as C
    from explainer_engine.blender import render as R
    from explainer_engine.blender import style_sheets as SS
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core import shot_cache
    from explainer_engine.core.errors import ContractError
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths, cpaths = SS.fetch(), C.fetch()
    sc = scene(paths, cpaths, count=count, frames=frames, far_px=far_px)
    problems = check(sc["crowds"])
    if problems:
        raise CrowdError("; ".join(problems))
    write_json_atomic(out / "crowd_points.json", sc["crowds"])
    _, tokens = SS.style_for(look)
    scene_doc, _ = SS.job_scene("battle_wide", look, sc, paths)
    scene_doc["crowds"] = sc["crowds"]
    spec = SS.spec_for("battle_wide", look, tokens, samples=samples, scene=scene_doc, frames=frames)
    spec["job_id"], spec["shot_id"] = JOB_ID, f"{SHOT_ID}_{count}_{look}"
    spec["scene"]["template_asset"] = {"id": f"scene_template.crowd_proof_{count}", "sha256": SS.scene_sha256(scene_doc)}
    if scale != 1.0:
        spec["frame"]["render_scale"] = scale
    b = BlenderProject().resolve(binary, device=device)
    t0 = time.time()
    try:
        m = R.HeadlessRender(b, R.LocalVault(out / "vault")).run(spec, out / "work", scene=scene_doc)
    except ContractError as e:
        if scale == 1.0 or "master" not in str(e):
            raise
        m = json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8"))
    sdir = out / "work" / m["cache_key"]
    rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
    times = SS.frame_times(sdir)
    clip = SS.mp4(sdir / "frames", out / f"crowd_{count}_{look}_{frames}f.mp4")
    import shutil
    (out / "frames").mkdir(exist_ok=True)
    for i in sorted({0, frames // 2, frames - 1}):     # stills for review: first, middle, last
        f = sdir / "frames" / R.FRAME_NAME.format(index=i)
        if f.exists():
            shutil.copyfile(f, out / "frames" / f"crowd_{count}_{i:03d}.png")
    prev = (rep.get("crowd") or {}).get("atlas", {}).get("preview")
    if prev and Path(prev).exists():
        shutil.copyfile(prev, out / "crowd_atlas_preview.png")
    blk = sc["crowds"]
    row = {"schema": "crowd_proof/1", "count": blk["count"] + len(blk["heroes"]), "points": blk["count"],
           "heroes": len(blk["heroes"]), "templates": len(blk["templates"]), "far_templates": len(blk["far_templates"]),
           "borders": blk["borders"], "tiers_first_frame": tier_counts(blk, sc["camera"]["location"]),
           "tiers_last_frame": tier_counts(blk, sc["camera"].get("to", sc["camera"])["location"], seconds=(frames - 1) / 24.0),
           "look": look, "frames": frames, "scale": scale, "size": [round(2560 * scale), round(1440 * scale)], "samples": samples,
           "engine": m["engine"], "seconds_per_frame": m["seconds_per_frame"], "times": times,
           "wall_seconds": round(time.time() - t0, 1), "blender": m["blender"], "gpu_backend": rep.get("gpu_backend"),
           "crowd_report": rep.get("crowd"), "mp4": clip, "frames_dir": str(sdir / "frames"), "machine": sys.platform}
    write_json_atomic(out / "crowd_proof.json", row)
    log(f"crowd of {row['count']}: {times.get('steady_median_s')} s/frame steady, first {times.get('first_s')} s "
        f"({row['size'][0]}x{row['size'][1]}, {m['engine']})")
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.blender.crowd", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan", help="the crowds block summary (no Blender)")
    pl.add_argument("--count", type=int, default=5000)
    r = sub.add_parser("render", help="render the proof clip")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--binary")
    r.add_argument("--look", default="v01_reference_soft3d")
    r.add_argument("--count", type=int, default=5000)
    r.add_argument("--frames", type=int, default=24)
    r.add_argument("--scale", type=float, default=0.5)
    r.add_argument("--samples", type=int, default=16)
    r.add_argument("--device", default="auto")
    r.add_argument("--far-px", type=float, default=FAR_PX, help="the T2 border in px (a tiny value draws every soldier as T1: the A/B)")
    a = p.parse_args(argv)
    if a.cmd == "plan":
        b = plan(default_formations(a.count), CAMERA, shot_id=SHOT_ID, hero_max=PROOF_HEROES)
        print(json.dumps({"count": b["count"], "heroes": len(b["heroes"]), "templates": [t["name"] for t in b["templates"]],
                          "borders": b["borders"], "tiers_first_frame": tier_counts(b, CAMERA["location"]),
                          "problems": check(b)}, indent=1))
        return 0
    row = render(a.out, binary=a.binary, look=a.look, count=a.count, frames=a.frames, scale=a.scale, samples=a.samples,
                 device=a.device, far_px=a.far_px)
    print(json.dumps({k: row[k] for k in ("count", "seconds_per_frame", "times", "size", "engine", "tiers_first_frame")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
