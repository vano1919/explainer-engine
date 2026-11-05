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
JOG_MPS = 5.2955         # Jog_Fwd_Loop's natural speed, MEASURED (ICW-06 poc1_clips.json, slide 0.18 cm): a charge, stride-matched
TEMPLATE_Y = -400.0      # templates are built behind the camera and hidden after the bake
FORMATIONS = ("line", "phalanx", "cohort", "shield_wall", "wedge", "rout")
COLUMNS = ("x", "y", "yaw", "slot", "far_slot", "phase", "speed", "vx", "vy", "delay", "banner", "stop", "slot2", "far_slot2",
           "switch")
NEVER = 1.0e6            # a stop or a clip switch that never comes (seconds)
DUST_COLUMNS = ("x", "y", "z", "w", "h", "vx", "vy", "seed", "t_in")   # a dust card: centre, size (m), drift (m/s), seed, fade-in s
ARROW_COLUMNS = ("x", "y", "z", "vx", "vy", "vz", "t0", "flight")     # launch point, launch velocity, launch time, time to the ground
SMOKE_COLUMNS = ("x", "y", "z", "phase", "period", "height", "lean", "size0", "size1", "seed")   # a puff that rises in a loop
GRAVITY = 9.81


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
    banner: int = 0            # the banner a standard-bearer of this block carries (1, 2, ...: crowds.props.banners); 0 = none
    banner_every: int = 0      # one standard-bearer in this many soldiers, never in the front rank
    start_s: float = 0.0       # the block starts to move this many seconds into the shot (rank delays come on top)
    stop_m: float = 0.0        # > 0: every soldier stops after this many metres (the clash); 0 = never
    after: tuple[tuple[str, float], ...] = ()        # the clips after the switch (front ranks)
    after_back: tuple[tuple[str, float], ...] = ()   # ... for ranks >= after_front_ranks (default: ``after``)
    after_front_ranks: int = 1_000_000
    switch_at: object = None   # None | "start" (when it starts to move) | "arrive" (when it stops) | seconds into the shot
    switch_jitter_s: float = 0.0

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


def position(x: float, y: float, vx: float, vy: float, delay: float, seconds: float, stop: float = NEVER) -> tuple[float, float]:
    """Closed-form ground position at ``seconds`` into the shot (the node tree's Set Position): no state, so frame 1000 of a
    chunk started at 900 is the same point as frame 1000 of a run started at 0 (RULE-R1). ``stop`` = seconds of travel."""
    t = min(max(0.0, seconds - delay), stop)
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
         hero_max: int = HERO_MAX, far_px: float = FAR_PX, props: dict | None = None) -> dict:
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
        if fm.switch_at is not None and not fm.after:
            raise CrowdError(f"{fm.crowd_id}: a clip switch needs the clips after it")
        if fm.switch_at == "arrive" and not (fm.stop_m > 0 and fm.speed_mps > 0):
            raise CrowdError(f"{fm.crowd_id}: switch_at arrive needs a moving block that stops (stop_m > 0)")
        every = tuple(fm.clips) + tuple(fm.after) + tuple(fm.after_back)
        for ci, ch in enumerate(fm.chars):      # one template per look x clip, shared by every formation that wears it
            for ki, (action, _) in enumerate(every):
                key = (ch, fm.costume, fm.tint, action)
                if key not in slot_of:
                    slot_of[key] = len(templates)
                    templates.append({"slot": len(templates), "name": f"crowd_tpl_{len(templates)}", "char": ch,
                                      "costume": fm.costume, "tint": fm.tint, "action": action})
        for ki, (action, _) in enumerate(every):
            key = (fm.chars[0], fm.costume, fm.tint, action)
            if key not in far_of:
                far_of[key] = len(far)
                far.append({"far_slot": len(far), "slot": slot_of[key]})
    cam, lens = camera["location"], camera["lens_mm"]
    rows = []
    for fm in formations:
        rng = random.Random(seed_for(shot_id, fm.crowd_id))
        f = math.radians(fm.facing_deg)
        fwd, right = (-math.sin(f), math.cos(f)), (math.cos(f), math.sin(f))
        for n, (u, v, rank) in enumerate(fm.offsets(rng)):
            u += rng.uniform(-fm.jitter_m, fm.jitter_m)
            v += rng.uniform(-fm.jitter_m, fm.jitter_m)
            x, y = fm.origin[0] + u * right[0] + v * fwd[0], fm.origin[1] + u * right[1] + v * fwd[1]
            ci, ki = rng.randrange(len(fm.chars)), _pick(rng, fm.clips)
            s = rng.uniform(*fm.speed_range)
            yaw = (fm.facing_deg + rng.uniform(-180, 180)) if fm.type == "rout" else fm.facing_deg + rng.uniform(
                -fm.yaw_jitter_deg, fm.yaw_jitter_deg)
            vel, phase = fm.speed_mps * s, rng.uniform(0, bake_frames)
            delay = fm.start_s + rank * fm.rank_delay_s
            stop = (fm.stop_m + rng.uniform(-0.25, 0.25)) / vel if fm.stop_m > 0 and vel > 0 else NEVER
            act, sw = fm.clips[ki][0], NEVER
            if fm.switch_at is not None:      # the clip after the switch (closed form: the tree picks it by the shot time)
                pool = fm.after if rank < fm.after_front_ranks else (fm.after_back or fm.after)
                act = pool[_pick(rng, pool)][0]
                at = {"start": delay, "arrive": delay + stop}.get(fm.switch_at, fm.switch_at)
                sw = float(at) + rng.uniform(0, fm.switch_jitter_s)
                if act == fm.clips[ki][0]:      # the same clip after the switch: no switch at all
                    sw = NEVER
            row = {"x": round(x, 4), "y": round(y, 4), "yaw": round(yaw, 3), "slot": slot_of[(fm.chars[ci], fm.costume, fm.tint, fm.clips[ki][0])],
                   "far_slot": far_of[(fm.chars[0], fm.costume, fm.tint, fm.clips[ki][0])], "phase": round(phase, 4), "speed": round(s, 4),
                   "vx": round(fwd[0] * vel, 4), "vy": round(fwd[1] * vel, 4), "delay": round(delay, 4),
                   "banner": fm.banner if fm.banner_every and rank > 0 and n % fm.banner_every == fm.banner_every // 2 else 0,
                   "stop": round(stop, 4), "slot2": slot_of[(fm.chars[ci], fm.costume, fm.tint, act)],
                   "far_slot2": far_of[(fm.chars[0], fm.costume, fm.tint, act)], "switch": round(sw, 4)}
            rows.append((math.dist((x, y, 0.0), cam), row, dict(crowd_id=fm.crowd_id, char=fm.chars[ci], costume=fm.costume,
                                                               tint=fm.tint, action=fm.clips[ki][0], offset=int(phase * 2) % 64)))
    # a hero is a plain rig keyed at the first and the last frame: one clip, standing or walking all shot long, no flag
    still = lambda r: not r["banner"] and r["switch"] >= NEVER and (r["stop"] >= NEVER or not (r["vx"] or r["vy"]))  # noqa: E731
    near = sorted((i for i, (d, r, _) in enumerate(rows) if tier_of(d, lens) == "hero" and still(r)), key=lambda i: rows[i][0])
    hero_ids = set(near[:hero_max])          # the nearest soldiers become full rigs; the rest of the near ones stay T1 (full mesh)
    heroes = [dict(rows[i][1], **rows[i][2]) for i in sorted(hero_ids)]
    cols = {k: [r[k] for i, (_, r, _) in enumerate(rows) if i not in hero_ids] for k in COLUMNS}
    return {"schema": SCHEMA, "shot_id": shot_id, "bake_frames": bake_frames, "lens_mm": lens, "focal_px": round(focal_px(lens), 4),
            "soldier_m": SOLDIER_M, "far_px": far_px, "hero_px": HERO_PX, "borders": borders(lens, far_px=far_px), "mid_tris": MID_TRIS,
            "mid_shadow_max_m": MID_SHADOW_MAX_M,
            "atlas": {"frames": ATLAS_FRAMES, "yaw": ATLAS_YAW, "cell_px": list(ATLAS_CELL), "cell_m": [1.6, 2.4]},
            "templates": templates, "far_templates": far, "heroes": heroes, "count": len(cols["x"]), "points": cols,
            "formations": [{"crowd_id": fm.crowd_id, "type": fm.type, "size": fm.size, "files": fm.files} for fm in formations],
            "props": props or {"banners": [], "dust": None}}


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
    if any(s not in slots for s in pts.get("slot2", [])) or any(s not in fars for s in pts.get("far_slot2", [])):
        out.append("a clip switch names a template slot that does not exist")
    if any(v <= 0 for v in pts.get("stop", [])):
        out.append("a stop must be a positive travel time")
    if any(not 0 <= p < block.get("bake_frames", 0) for p in pts.get("phase", [])):
        out.append("a phase is outside 0..bake_frames")
    b = block.get("borders", {})
    if not 0 < b.get("hero_max_m", 0) < b.get("far_min_m", 0):
        out.append("borders must satisfy 0 < hero_max_m < far_min_m")
    if len(block.get("heroes", [])) > HERO_MAX:
        out.append(f"more than {HERO_MAX} heroes")
    props = block.get("props") or {}
    ids = {bn.get("id") for bn in props.get("banners", [])}
    if any(k and k not in ids for k in pts.get("banner", [])):
        out.append("a point carries a banner that props.banners does not define")
    for bn in props.get("banners", []):
        if not (isinstance(bn.get("id"), int) and bn["id"] > 0 and bn.get("material") and 2.0 <= bn.get("pole_m", 0) <= 6.0):
            out.append(f"banner {bn.get('id')!r}: needs an id > 0, a material and a pole of 2-6 m")
    dust = props.get("dust")
    if dust:
        if not dust.get("cards") or any(len(c) != len(DUST_COLUMNS) for c in dust["cards"]):
            out.append(f"dust cards need {len(DUST_COLUMNS)} values each ({', '.join(DUST_COLUMNS)})")
        if not 0 < dust.get("alpha", 0) <= 1 or len(dust.get("rgb", ())) != 3:
            out.append("dust needs an alpha in 0..1 and an rgb colour")
    arrows = props.get("arrows")
    if arrows:
        rows = arrows.get("rows", [])
        if not rows or any(len(r) != len(ARROW_COLUMNS) or r[7] <= 0 for r in rows):
            out.append(f"arrows need {len(ARROW_COLUMNS)} values each ({', '.join(ARROW_COLUMNS)}) and a positive flight")
    smoke = props.get("smoke")
    if smoke:
        rows = smoke.get("puffs", [])
        if not rows or any(len(r) != len(SMOKE_COLUMNS) or r[4] <= 0 for r in rows):
            out.append(f"smoke puffs need {len(SMOKE_COLUMNS)} values each ({', '.join(SMOKE_COLUMNS)}) and a positive period")
        if not 0 < smoke.get("alpha", 0) <= 1 or len(smoke.get("rgb", ())) != 3:
            out.append("smoke needs an alpha in 0..1 and an rgb colour")
    return out


def tier_counts(block: dict, camera_xyz, *, seconds: float = 0.0) -> dict[str, int]:
    """Soldiers per tier with the camera at ``camera_xyz`` (the rule the node tree evaluates; heroes are fixed at plan time)."""
    p, lens = block["points"], block["lens_mm"]
    out = {"hero": len(block.get("heroes", [])), "mid": 0, "far": 0}
    for x, y, vx, vy, d, st in zip(p["x"], p["y"], p["vx"], p["vy"], p["delay"], p["stop"]):
        px, py = position(x, y, vx, vy, d, seconds, st)
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


# --- the battle (Fable 2026-11-05, for the Mac clip): a wedge charging a shield wall, the camera low behind the near line ----------

BATTLE_SHOT_ID = "crowd_battle_5k"
BATTLE_CAMERA = {"location": [-5.0, -9.2, 1.9], "look_at": [5.0, 40.0, 2.4], "lens_mm": 32, "focus_distance_m": 30.0}
BATTLE_CAMERA_TO = {"location": [-4.1, -8.9, 1.86], "look_at": [5.8, 40.0, 2.4]}    # a slow creep along the back rank
BATTLE_LOOK = "q1_c2_native_skin@E2"     # combo_profiles default C2 (native characters, Q1 depth haze) under E2's golden hour
COMPOSITIONS = ("battle", "battle30", "field")
BANNERS = ({"id": 1, "material": "side_a", "pole_material": "night", "pole_m": 3.6, "flag_m": [0.95, 1.25]},
           {"id": 2, "material": "side_b", "pole_material": "night", "pole_m": 3.6, "flag_m": [0.95, 1.25]})


def battle_formations(count: int = 5000) -> tuple[Formation, ...]:
    """Side A: a shield wall six ranks deep, holding (guard, some cuts), the camera behind it. Side B: a wedge charging at the
    jog clip's own speed, the main line holding behind it, a reserve walking up; standard-bearers in every block."""
    if count < 8:
        raise CrowdError("a battle needs at least eight soldiers")
    wall, wedge, line = round(count * 0.3), round(count * 0.15), round(count * 0.37)
    reserve = count - wall - wedge - line
    chars = ("ink_test_m", "ink_test_m2")
    ranger, peasant = "costume.mco_male_ranger", "costume.mco_male_peasant"
    return (Formation("wall_a", "shield_wall", wall, max(1, round(wall / 6)), ranger, "faction_a", chars,
                      (("Sword_Idle", 0.8), ("Sword_Attack", 0.2)), (0.0, 0.0), 0.0, jitter_m=0.12, yaw_jitter_deg=5.0,
                      banner=1, banner_every=70),
            Formation("wedge_b", "wedge", wedge, 1, peasant, "faction_b", chars, (("Jog_Fwd_Loop", 1.0),), (6.0, 26.0), 180.0,
                      spacing_m=1.4, jitter_m=0.3, speed_mps=JOG_MPS, speed_range=(0.97, 1.03), banner=2, banner_every=45),
            Formation("line_b", "phalanx", line, max(1, round(line / 8)), ranger, "faction_b", chars, (("Sword_Idle", 1.0),),
                      (0.0, 72.0), 180.0, banner=2, banner_every=90),
            Formation("reserve_b", "line", reserve, max(1, round(reserve / 5)), ranger, "faction_b", chars,
                      (("Walk_Formal_Loop", 1.0),), (14.0, 98.0), 180.0, spacing_m=1.6, speed_mps=WALK_MPS, banner=2,
                      banner_every=80))


def battle_dust(shot_id: str, rgb) -> dict:
    """Dust cards: a bank over the far ranks (drifting across with the wind) and the cloud the wedge kicks up behind its point."""
    rng = random.Random(seed_for(shot_id, "dust"))
    cards = []
    for _ in range(22):      # over the main line and the reserve
        w = rng.uniform(16, 30)
        h = w * rng.uniform(0.3, 0.42)
        cards.append([rng.uniform(-70, 80), rng.uniform(66, 118), h * 0.38, w, h, rng.uniform(0.4, 0.9), 0.0, rng.uniform(0, 100),
                      -100.0])
    for _ in range(12):      # behind the charge, low, trailing it
        w = rng.uniform(7, 14)
        h = w * rng.uniform(0.32, 0.45)
        cards.append([rng.uniform(-14, 28), rng.uniform(32, 62), h * 0.4, w, h, rng.uniform(0.2, 0.5),
                      -JOG_MPS * rng.uniform(0.25, 0.45), rng.uniform(0, 100), -100.0])
    return {"cards": [[round(v, 4) for v in c] for c in cards], "rgb": [round(min(1.0, c * 1.6), 4) for c in rgb], "alpha": 0.42}


# --- the 30-second battle (ვანო 2026-11-05 22:46 via the coordinator; Fable's spec): two armies close and clash, one camera move
# (WP-Q7's crane establishing into a push), dust, village smoke, arrow volleys, Q1's haze. Every motion is a closed-form function of
# the shot time (baked clips, no simulation at render time), so any frame range renders alone (RULE-R1 chunks).

BATTLE30_SHOT_ID = "crowd_battle30_5k"
BATTLE30_FRAMES = 720
T_CLASH = 13.0            # the wedge's point meets the shield wall (seconds)
B30_LENS = 28
B30_POS = ((-36.0, -50.0, 24.0), (-15.0, -24.0, 6.0), (-3.4, -6.6, 2.0))      # Bezier: high and wide -> down -> in behind the wall
B30_AIM = ((2.0, 62.0, 0.0), (3.0, 22.0, 1.5), (4.5, 3.0, 1.5))
WEDGE_TIP_Y = 0.9 + JOG_MPS * T_CLASH
VILLAGE = ((-96.0, 184.0, 7, 5, 5), (-88.0, 188.0, 6, 5, 6), (-80.0, 183.0, 5, 6, 5), (-72.0, 189.0, 6, 4, 4),
           (-104.0, 190.0, 5, 5, 6), (-84.0, 194.0, 7, 5, 7))
RIDGE = ((0.0, 190.0, -14.0), (240.0, 50.0, 34.0))     # the main ridge (centre, semi-axes): the village stands on it


def _bezier(p, s):
    a, b, c = p
    return [(1 - s) ** 2 * a[i] + 2 * (1 - s) * s * b[i] + s * s * c[i] for i in range(3)]


def _ease(u):
    return u * u * (3 - 2 * u)


def battle30_camera(frames: int = BATTLE30_FRAMES, every: int = 12) -> dict:
    """The camera keys (Q7 crane rig, LINEAR between keys every ``every`` frames) along one eased Bezier: an establishing crane
    from high and wide behind side A down to the back rank, flowing into a push towards the clash; no stop at the joint."""
    keys = []
    for f in sorted(set(range(0, frames, every)) | {frames - 1}):
        s = _ease(f / max(frames - 1, 1))
        keys.append({"frame": f, "location": [round(v, 4) for v in _bezier(B30_POS, s)],
                     "look_at": [round(v, 4) for v in _bezier(B30_AIM, s)]})
    return {"location": keys[0]["location"], "look_at": keys[0]["look_at"], "lens_mm": B30_LENS, "focus_distance_m": 30.0,
            "keys": keys, "interp": "LINEAR", "fstop": 11.0, "focus_at": [4.5, 3.0, 1.5], "rig_kind": "crane",
            "move": "establishing_wide (crane) into push_in_reveal (WP-Q7 grammar)"}


def battle30_formations(count: int = 5000) -> tuple[Formation, ...]:
    if count < 8:
        raise CrowdError("a battle needs at least eight soldiers")
    wall, wedge, line = round(count * 0.3), round(count * 0.15), round(count * 0.37)
    reserve = count - wall - wedge - line
    chars = ("ink_test_m", "ink_test_m2")
    ranger, peasant = "costume.mco_male_ranger", "costume.mco_male_peasant"
    return (Formation("wall_a", "shield_wall", wall, max(1, round(wall / 6)), ranger, "faction_a", chars, (("Sword_Idle", 1.0),),
                      (0.0, 0.0), 0.0, jitter_m=0.12, yaw_jitter_deg=5.0, banner=1, banner_every=70,
                      after=(("Sword_Attack", 0.75), ("Sword_Idle", 0.25)), after_back=(("Sword_Idle", 1.0),), after_front_ranks=2,
                      switch_at=T_CLASH - 0.3, switch_jitter_s=1.2),
            Formation("wedge_b", "wedge", wedge, 1, peasant, "faction_b", chars, (("Jog_Fwd_Loop", 1.0),), (6.0, WEDGE_TIP_Y), 180.0,
                      spacing_m=1.4, jitter_m=0.3, speed_mps=JOG_MPS, speed_range=(1.0, 1.0), banner=2, banner_every=45,
                      stop_m=WEDGE_TIP_Y - 0.9, after=(("Sword_Attack", 0.8), ("Sword_Idle", 0.2)), after_back=(("Sword_Idle", 1.0),),
                      after_front_ranks=4, switch_at="arrive", switch_jitter_s=0.4),
            Formation("line_b", "phalanx", line, max(1, round(line / 8)), ranger, "faction_b", chars, (("Sword_Idle", 1.0),),
                      (0.0, 125.0), 180.0, banner=2, banner_every=90, speed_mps=WALK_MPS, start_s=17.0, rank_delay_s=0.05,
                      after=(("Walk_Formal_Loop", 1.0),), switch_at="start"),
            Formation("reserve_b", "line", reserve, max(1, round(reserve / 5)), ranger, "faction_b", chars,
                      (("Walk_Formal_Loop", 1.0),), (14.0, 152.0), 180.0, spacing_m=1.6, speed_mps=WALK_MPS, banner=2,
                      banner_every=80))


def _wedge_tip_y(t: float) -> float:
    return WEDGE_TIP_Y - JOG_MPS * min(max(t, 0.0), T_CLASH)


def battle30_arrows(shot_id: str) -> dict:
    """Volleys: side A's archers (behind the camera's start, off frame) shoot over the wall into the charging wedge three times;
    side B's line answers twice onto the wall. Each arrow lands where the target block is at its landing time."""
    rng = random.Random(seed_for(shot_id, "arrows"))
    volleys = ((2.0, 450, (-45, 45, -34, -26), "wedge", (2.6, 3.1)), (5.5, 450, (-45, 45, -34, -26), "wedge", (2.6, 3.1)),
               (9.0, 450, (-45, 45, -34, -26), "wedge", (2.4, 2.8)), (7.5, 400, (-50, 50, 118, 124), "wall", (3.0, 3.6)),
               (15.5, 400, (-50, 50, 118, 124), "wall", (3.0, 3.6)))
    rows = []
    for t, n, (x0, x1, y0, y1), target, (f0, f1) in volleys:
        for _ in range(n):
            t0, fl = t + rng.uniform(0, 0.7), rng.uniform(f0, f1)
            p0 = (rng.uniform(x0, x1), rng.uniform(y0, y1), 1.6)
            if target == "wedge":
                tip = _wedge_tip_y(t0 + fl)
                p1 = (6.0 + rng.uniform(-24, 24), tip + rng.uniform(2, 32), 0.0)
            else:
                p1 = (rng.uniform(-35, 45), rng.uniform(-5.5, 0.5), 0.0)
            v = [(p1[i] - p0[i]) / fl for i in range(3)]
            v[2] += 0.5 * GRAVITY * fl
            rows.append([round(c, 4) for c in (*p0, *v, t0, fl)])
    return {"rows": rows, "gravity": GRAVITY, "scale": 1.5}


def ridge_z(x: float, y: float) -> float:
    (cx, cy, cz), (ax, ay, az) = RIDGE
    q = 1 - ((x - cx) / ax) ** 2 - ((y - cy) / ay) ** 2
    return cz + az * math.sqrt(q) if q > 0 else 0.0


def battle30_smoke(shot_id: str) -> dict:
    """Three columns over the burning village: 26 puffs each rising 70 m in a 16 s loop, leaning with the wind."""
    from explainer_engine.design import palette as P
    rng = random.Random(seed_for(shot_id, "smoke"))
    grey = P._rgb_linear(P.load()["tokens"]["grey_mid"]["hex"])
    puffs = []
    for hx, hy, _, _, h in (VILLAGE[0], VILLAGE[2], VILLAGE[5]):
        z = ridge_z(hx, hy) + h
        for k in range(26):
            puffs.append([round(v, 4) for v in (hx + rng.uniform(-1, 1), hy + rng.uniform(-1, 1), z, (k + rng.uniform(0, 0.6)) / 26,
                                                rng.uniform(14, 18), rng.uniform(60, 78), 0.45, rng.uniform(4, 6),
                                                rng.uniform(22, 30), rng.uniform(0, 100))])
    return {"puffs": puffs, "rgb": [round(c * 0.5, 4) for c in grey], "alpha": 0.6}


def battle30_dust(shot_id: str, rgb) -> dict:
    """A bank over the far ranks (always), dust rising where the wedge has run (it appears as the wedge passes) and a cloud at
    the clash."""
    rng = random.Random(seed_for(shot_id, "dust30"))
    cards = []
    for _ in range(22):
        w = rng.uniform(16, 30)
        h = w * rng.uniform(0.3, 0.42)
        cards.append([rng.uniform(-70, 80), rng.uniform(115, 165), h * 0.38, w, h, rng.uniform(0.4, 0.9), 0.0, rng.uniform(0, 100),
                      -100.0])
    for _ in range(14):
        w = rng.uniform(8, 15)
        h = w * rng.uniform(0.32, 0.45)
        y = rng.uniform(18, WEDGE_TIP_Y + 20)    # where the wedge runs (its middle, 15 m behind the point, stops near 16 m)
        passed = (WEDGE_TIP_Y + 15 - y) / JOG_MPS
        cards.append([rng.uniform(-14, 28), y, h * 0.4, w, h, rng.uniform(0.2, 0.5), 0.0, rng.uniform(0, 100), round(max(passed, -5.0), 3)])
    for _ in range(12):
        w = rng.uniform(6, 12)
        h = w * rng.uniform(0.35, 0.5)
        cards.append([rng.uniform(-18, 30), rng.uniform(-1, 8), h * 0.42, w, h, rng.uniform(0.1, 0.4), 0.0, rng.uniform(0, 100),
                      T_CLASH + rng.uniform(0, 3)])
    return {"cards": [[round(v, 4) for v in c] for c in cards], "rgb": [round(min(1.0, c * 1.6), 4) for c in rgb], "alpha": 0.42}


def scene(paths: dict[str, Path], cpaths: dict[str, Path], *, count: int = 5000, frames: int = 24, shot_id: str | None = None,
          far_px: float = FAR_PX, composition: str = "battle") -> dict:
    """Objects, camera, materials and the crowds block. ``battle``: grass with a trampled dirt strip between the armies, ridges
    behind, a wedge charging a shield wall, banners and dust (the Mac clip). ``field``: the first proof's parade on a flat plane
    (kept for the A/B and the CI timing). Templates and heroes are ordinary cast members (render_shot's character path);
    templates are parked behind the camera."""
    from explainer_engine.blender import characters as C
    from explainer_engine.blender import style_sheets as SS
    if composition not in COMPOSITIONS:
        raise CrowdError(f"unknown composition {composition!r} (known: {', '.join(COMPOSITIONS)})")
    battle, long = composition in ("battle", "battle30"), composition == "battle30"
    shot_id = shot_id or {"battle": BATTLE_SHOT_ID, "battle30": BATTLE30_SHOT_ID}.get(composition, SHOT_ID)
    camera, camera_to = (BATTLE_CAMERA, BATTLE_CAMERA_TO) if battle else (CAMERA, CAMERA_TO)
    if long:
        from explainer_engine.blender import camera_rigs
        camera = dict(battle30_camera(frames), extension=str(camera_rigs.ensure()))
        camera_to = None
    base = SS.scenes(paths, cast="mannequin")["battle_wide"]
    objs, extra = [], {}
    if battle:
        grass, dirt = "material.ph_aerial_grass_rock", "material.ph_dry_ground_01"
        tex = lambda aid, **kw: {"base": "paper", "texture": str(paths[aid]), "texture_mean": SS.texture_mean(Path(paths[aid])), **kw}  # noqa: E731
        extra = {"field_grass": tex(grass, tile=120.0), "field_dirt": tex(dirt, tile=10.0)}
        objs.append({"name": "field", "add": "plane", "params": {"size": 900}, "material": "field_grass"})
        for i, (x, y, sx, sy, yaw) in enumerate(((2, 16, 90, 15, 2), (-30, 22, 50, 11, -9), (36, 20, 48, 12, 11), (8, 44, 70, 13, -4))):
            objs.append({"name": f"dirt_{i}", "add": "plane", "params": {"size": 1}, "location": [x, y, 0.012 + i * 0.004],
                         "scale": [sx, sy, 1], "rotation_deg": [0, 0, yaw], "material": "field_dirt"})
        mean = extra["field_dirt"]["texture_mean"]
        if long:
            props = {"banners": [dict(b) for b in BANNERS], "dust": battle30_dust(shot_id, mean), "arrows": battle30_arrows(shot_id),
                     "smoke": battle30_smoke(shot_id)}
            end = {"location": camera["keys"][-1]["location"], "lens_mm": camera["lens_mm"]}   # heroes: the nearest at the end of the push
            block = plan(battle30_formations(count), end, shot_id=shot_id, hero_max=PROOF_HEROES, far_px=far_px, props=props)
            block["atlas"]["view_frame"] = round(frames * 0.75)      # the billboards' elevation: the low camera of the last quarter
            for i, (hx, hy, w, d, h) in enumerate(VILLAGE):
                for o in SS._house(f"village{i}", hx, hy, w, d, h):
                    loc = list(o["location"])
                    loc[2] += ridge_z(hx, hy)
                    objs.append(dict(o, location=loc))
        else:
            props = {"banners": [dict(b) for b in BANNERS], "dust": battle_dust(shot_id, mean)}
            block = plan(battle_formations(count), camera, shot_id=shot_id, hero_max=PROOF_HEROES, far_px=far_px, props=props)
    else:
        objs.append(next(dict(o, params={"size": 900}) for o in base["objects"] if o["name"] == "field"))
        block = plan(default_formations(count), camera, shot_id=shot_id, hero_max=PROOF_HEROES, far_px=far_px)
    objs += [dict(o, location=[0, 190, -14], scale=[240, 50, 34]) for o in base["objects"] if o["name"] == "ridge"]
    for i, (x, y, r) in enumerate(((-170, 120, 70), (190, 140, 80), (-60, 260, 95), (110, 300, 110))):
        objs.append({"name": f"ridge_{i}", "add": "uv_sphere", "params": {"radius": 1, "segments": 48, "ring_count": 24},
                     "location": [x, y, -r * 0.55], "scale": [r, r * 0.7, r * 0.6], "material": "hill", "smooth": True})
    guns = ((-24, 112, 180), (30, 114, 176)) if battle else ((-34, 18, 0), (-20, 17, 6), (16, 18, -4), (30, 17, 3), (-8, 60, 180),
                                                            (12, 61, 176))
    for i, (x, y, yaw) in enumerate(guns):
        objs.append({"name": f"cannon_{i}", "append": {"path": str(paths["model.ph_cannon_01"])}, "location": [x, y, 0],
                     "scale": 1.0, "rotation_deg": [0, 0, yaw], "material": "cannon"})
    used = {o.get("material") for o in objs} | {m for b in block["props"]["banners"] for m in (b["material"], b["pole_material"])}
    if block["props"].get("arrows"):
        used.add("night")
    mats = {k: v for k, v in base["materials"].items() if k in used}
    mats.update(extra)

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
    cam = dict(camera, clip_end=2000.0)
    if frames > 1 and camera_to is not None:
        cam["to"] = dict(camera_to)
    return {"objects": objs, "camera": cam, "materials": mats, "frames_total": frames, "crowds": block, "composition": composition}


def render(out: Path, *, binary: str | None = None, look: str | None = None, count: int = 5000, frames: int | None = None,
           scale: float = 0.5, samples: int = 16, device: str = "auto", far_px: float = FAR_PX, composition: str = "battle",
           log=print) -> dict:
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
    look = look or (BATTLE_LOOK if composition != "field" else "v01_reference_soft3d")
    frames = frames or (BATTLE30_FRAMES if composition == "battle30" else 24)
    sc = scene(paths, cpaths, count=count, frames=frames, far_px=far_px, composition=composition)
    shot = {"battle": BATTLE_SHOT_ID, "battle30": BATTLE30_SHOT_ID}.get(composition, SHOT_ID)
    problems = check(sc["crowds"])
    if problems:
        raise CrowdError("; ".join(problems))
    write_json_atomic(out / "crowd_points.json", sc["crowds"])
    _, tokens = SS.style_for(look)
    scene_doc, _ = SS.job_scene("battle_wide", look, sc, paths)
    scene_doc["crowds"] = sc["crowds"]
    spec = SS.spec_for("battle_wide", look, tokens, samples=samples, scene=scene_doc, frames=frames)
    tag = look.replace("@", "_at_").replace("+", "_")
    spec["job_id"], spec["shot_id"] = JOB_ID, f"{shot}_{count}_{tag}"
    spec["scene"]["template_asset"] = {"id": f"scene_template.crowd_{composition}_{count}", "sha256": SS.scene_sha256(scene_doc)}
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
    clip = SS.mp4(sdir / "frames", out / f"crowd_{composition}_{count}_{tag}_{frames}f.mp4")
    import shutil
    (out / "frames").mkdir(exist_ok=True)
    for i in sorted({0, frames // 2, frames - 1}):     # stills for review: first, middle, last
        f = sdir / "frames" / R.FRAME_NAME.format(index=i)
        if f.exists():
            shutil.copyfile(f, out / "frames" / f"crowd_{composition}_{count}_{i:03d}.png")
    prev = (rep.get("crowd") or {}).get("atlas", {}).get("preview")
    if prev and Path(prev).exists():
        shutil.copyfile(prev, out / "crowd_atlas_preview.png")
    blk = sc["crowds"]
    row = {"schema": "crowd_proof/1", "count": blk["count"] + len(blk["heroes"]), "points": blk["count"],
           "heroes": len(blk["heroes"]), "templates": len(blk["templates"]), "far_templates": len(blk["far_templates"]),
           "borders": blk["borders"], "tiers_first_frame": tier_counts(blk, sc["camera"]["location"]),
           "tiers_last_frame": tier_counts(blk, (sc["camera"]["keys"][-1] if sc["camera"].get("keys") else sc["camera"].get("to", sc["camera"]))
                                           ["location"], seconds=(frames - 1) / 24.0),
           "composition": composition, "props": (rep.get("crowd") or {}).get("props"), "look": look, "frames": frames, "scale": scale, "size": [round(2560 * scale), round(1440 * scale)], "samples": samples,
           "engine": m["engine"], "seconds_per_frame": m["seconds_per_frame"], "times": times,
           "wall_seconds": round(time.time() - t0, 1), "blender": m["blender"], "gpu_backend": rep.get("gpu_backend"),
           "crowd_report": rep.get("crowd"), "mp4": clip, "frames_dir": str(sdir / "frames"), "machine": sys.platform}
    write_json_atomic(out / "crowd_proof.json", row)
    log(f"crowd of {row['count']}: {times.get('steady_median_s')} s/frame steady, first {times.get('first_s')} s "
        f"({row['size'][0]}x{row['size'][1]}, {m['engine']})")
    return row


def preview(out: Path, at: list[int], *, binary: str | None = None, look: str | None = None, count: int = 5000,
            frames: int | None = None, scale: float = 0.5, samples: int = 16, device: str = "auto", composition: str = "battle30",
            log=print) -> dict:
    """A few frames of the clip (``at``, 0-based) rendered alone, straight through render_shot with the job HeadlessRender would
    write (same scene, look and settings): a review look at a long shot before the full render, and the proof that any frame
    renders by itself (the closed-form motion). Never a deliverable: no checkpoint, no manifest."""
    import subprocess
    from explainer_engine.blender import characters as C
    from explainer_engine.blender import profiles as PR
    from explainer_engine.blender import render as R
    from explainer_engine.blender import style_sheets as SS
    from explainer_engine.blender.project import BlenderProject
    out = Path(out)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    paths, cpaths = SS.fetch(), C.fetch()
    look = look or (BATTLE_LOOK if composition != "field" else "v01_reference_soft3d")
    frames = frames or (BATTLE30_FRAMES if composition == "battle30" else 24)
    if any(not 0 <= f < frames for f in at):
        raise CrowdError(f"preview frames must lie in 0..{frames - 1}")
    sc = scene(paths, cpaths, count=count, frames=frames, composition=composition)
    problems = check(sc["crowds"])
    if problems:
        raise CrowdError("; ".join(problems))
    _, tokens = SS.style_for(look)
    scene_doc, _ = SS.job_scene("battle_wide", look, sc, paths)
    scene_doc["crowds"] = sc["crowds"]
    spec = SS.spec_for("battle_wide", look, tokens, samples=samples, scene=scene_doc, frames=frames)
    b = BlenderProject().resolve(binary, device=device)
    hr = R.HeadlessRender(b, R.LocalVault(out / "vault"))
    prof = PR.get(spec["render"]["profile"])
    w, h = round(2560 * scale), round(1440 * scale)
    job = {"job": "render_shot/1", "pin_version": b.version, "shot_id": f"{composition}_preview", "frames": sorted(at),
           "frame_start": 1, "fps": 24, "width": w, "height": h, "percent": 100, "engine": prof.engine, "device": b.device,
           "settings": prof.settings(spec["render"]), "seed": spec["seed"], "scene": scene_doc, "frames_dir": str(out / "frames"),
           "frame_name": R.FRAME_NAME, "progress": str(out / "progress.jsonl"), "report": str(out / "bpy_report.json")}
    write_json_atomic(out / "job.json", job)
    t0 = time.time()
    with open(out / "blender.log", "w", encoding="utf-8") as lf:
        rc = subprocess.run(hr.command(out / "job.json"), stdout=lf, stderr=subprocess.STDOUT).returncode
    rep = json.loads((out / "bpy_report.json").read_text(encoding="utf-8")) if (out / "bpy_report.json").exists() else {}
    got = sorted(int(json.loads(ln)["index"]) for ln in (out / "progress.jsonl").read_text(encoding="utf-8").splitlines()
                 if ln.strip()) if (out / "progress.jsonl").exists() else []
    row = {"schema": "crowd_preview/1", "composition": composition, "look": look, "frames_asked": sorted(at), "frames_done": got,
           "returncode": rc, "size": [w, h], "samples": samples, "wall_seconds": round(time.time() - t0, 1),
           "crowd_report": rep.get("crowd"), "frames_dir": str(out / "frames")}
    write_json_atomic(out / "crowd_preview.json", row)
    log(f"preview {composition}: frames {got} of {sorted(at)} in {row['wall_seconds']} s (rc {rc})")
    if rc != 0 or got != sorted(at):
        raise CrowdError(f"preview failed (rc {rc}, frames {got}); see {out / 'blender.log'}")
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.blender.crowd", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan", help="the crowds block summary (no Blender)")
    pl.add_argument("--count", type=int, default=5000)
    r = sub.add_parser("render", help="render the proof clip")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--binary")
    r.add_argument("--composition", choices=COMPOSITIONS, default="battle")
    r.add_argument("--look", help=f"look id (default {BATTLE_LOOK} for the battle, v01_reference_soft3d for the field)")
    r.add_argument("--count", type=int, default=5000)
    r.add_argument("--frames", type=int, help="frames (default 24; battle30: 720 = 30 s)")
    r.add_argument("--scale", type=float, default=0.5)
    r.add_argument("--samples", type=int, default=16)
    r.add_argument("--device", default="auto")
    r.add_argument("--far-px", type=float, default=FAR_PX, help="the T2 border in px (a tiny value draws every soldier as T1: the A/B)")
    v = sub.add_parser("preview", help="render a few frames of the clip alone (review; the closed-form motion)")
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--at", required=True, help="0-based frames, comma separated (e.g. 0,180,312,500,719)")
    v.add_argument("--binary")
    v.add_argument("--composition", choices=COMPOSITIONS, default="battle30")
    v.add_argument("--look")
    v.add_argument("--count", type=int, default=5000)
    v.add_argument("--frames", type=int)
    v.add_argument("--scale", type=float, default=0.5)
    v.add_argument("--samples", type=int, default=16)
    v.add_argument("--device", default="auto")
    a = p.parse_args(argv)
    if a.cmd == "preview":
        row = preview(a.out, [int(x) for x in a.at.split(",")], binary=a.binary, look=a.look, count=a.count, frames=a.frames,
                      scale=a.scale, samples=a.samples, device=a.device, composition=a.composition)
        print(json.dumps({k: row[k] for k in ("frames_done", "wall_seconds", "size")}, indent=1))
        return 0
    if a.cmd == "plan":
        b = plan(default_formations(a.count), CAMERA, shot_id=SHOT_ID, hero_max=PROOF_HEROES)
        print(json.dumps({"count": b["count"], "heroes": len(b["heroes"]), "templates": [t["name"] for t in b["templates"]],
                          "borders": b["borders"], "tiers_first_frame": tier_counts(b, CAMERA["location"]),
                          "problems": check(b)}, indent=1))
        return 0
    row = render(a.out, binary=a.binary, look=a.look, count=a.count, frames=a.frames, scale=a.scale, samples=a.samples,
                 device=a.device, far_px=a.far_px, composition=a.composition)
    print(json.dumps({k: row[k] for k in ("count", "seconds_per_frame", "times", "size", "engine", "tiers_first_frame")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
