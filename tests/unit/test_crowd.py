"""T-E crowd proof (MOTION_RESEARCH.md Group 7, focused tests 1-4 and 7; 5 rides WP-Q1's shot_spec/3, 6 runs in Blender only):
formations, seeds, phases, screen-height tiers and the closed-form motion of ``blender/crowd.py``, the same maths the
``bpy/crowd_bake.py`` node tree evaluates."""
import math
import os
import random
from pathlib import Path

import pytest

from explainer_engine.blender import crowd as K

CAM = {"location": [0.0, -60.0, 8.0], "look_at": [0.0, 0.0, 0.0], "lens_mm": 32}


def _fm(type_, size=120, files=12, **kw):
    return K.Formation("f", type_, size, files, "costume.mco_male_peasant", "faction_a", ("ink_test_m", "ink_test_m2"),
                       (("Walk_Formal_Loop", 1.0),), (0.0, 0.0), **kw)


# 1. counts, spacing and jitter, seeds --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("type_", K.FORMATIONS)
def test_every_formation_places_exactly_its_size(type_):
    fm = _fm(type_, size=137, files=11)
    assert len(fm.offsets(random.Random(1))) == 137
    b = K.plan((fm,), CAM, shot_id="s", hero_max=0)
    assert b["count"] == 137 and K.check(b) == []


def test_a_line_is_files_by_ranks_on_its_spacing():
    fm = _fm("line", size=120, files=12, spacing_m=1.5)
    offs = fm.offsets(random.Random(0))
    assert fm.ranks == 10
    assert sorted({round(u, 6) for u, _, _ in offs}) == [round((c - 5.5) * 1.5, 6) for c in range(12)]
    assert sorted({round(v, 6) for _, v, _ in offs}) == [round(-r * 1.5, 6) for r in range(9, -1, -1)]


def test_jitter_stays_inside_its_bound():
    fm = _fm("line", size=400, files=20, spacing_m=1.25, jitter_m=0.2)
    b = K.plan((fm,), {"location": [0, -500, 5], "lens_mm": 32}, shot_id="s", hero_max=0)
    base = fm.offsets(random.Random(0))
    xs = sorted(b["points"]["x"])
    assert min(xs) >= min(u for u, _, _ in base) - 0.2 - 1e-9 and max(xs) <= max(u for u, _, _ in base) + 0.2 + 1e-9


def test_same_seed_same_soldiers_other_shot_others():
    fms = K.default_formations(600)
    a = K.plan(fms, CAM, shot_id="shot_a")
    assert a == K.plan(fms, CAM, shot_id="shot_a")
    assert a["points"]["x"] != K.plan(fms, CAM, shot_id="shot_b")["points"]["x"]
    assert K.seed_for("shot_a", "legion_a") != K.seed_for("shot_a", "phalanx_b")


def test_templates_are_shared_between_formations_that_wear_the_same_costume():
    b = K.plan(K.default_formations(5000), K.CAMERA, shot_id=K.SHOT_ID)
    keys = [(t["char"], t["costume"], t["tint"], t["action"]) for t in b["templates"]]
    assert len(keys) == len(set(keys)) == 6          # 2 heads x (walk, sword idle, sword attack); the wedge reuses the phalanx's
    assert len(b["far_templates"]) == 3              # one billboard set per costume x clip
    assert b["count"] + len(b["heroes"]) == 5000


# 2. phases and the index the node tree computes ------------------------------------------------------------------------------------

def test_no_phase_is_shared_by_much_more_than_one_soldier_in_n():
    b = K.plan(K.default_formations(5000), K.CAMERA, shot_id=K.SHOT_ID)
    n = b["bake_frames"]
    buckets = {}
    for p in b["points"]["phase"]:
        buckets[int(p)] = buckets.get(int(p), 0) + 1
    assert len(buckets) == n and max(buckets.values()) / b["count"] < 1.5 / n   # uniform within 50 %
    assert len(set(b["points"]["speed"])) > 1000      # speeds spread over the whole range (4-decimal steps)


@pytest.mark.parametrize("frame,rate,phase", [(0, 1.0, 0.0), (37, 0.8, 5.5), (1000, 1.07, 31.9), (-3, 1.0, 0.2)])
def test_the_clip_index_wraps_like_pick_instance(frame, rate, phase):
    n = 32
    i = K.clip_index(frame, rate, phase, n)
    assert 0 <= i < n
    assert i == math.floor(frame * rate + phase) % n


# 3. tiers by screen height ---------------------------------------------------------------------------------------------------------

def test_tiers_follow_the_screen_height_formula():
    lens = 32
    f = K.focal_px(lens)
    assert f == pytest.approx(2560 * 32 / 36)
    b = K.borders(lens)
    assert K.screen_px(b["hero_max_m"], lens) == pytest.approx(K.HERO_PX, rel=1e-4)
    assert K.screen_px(b["far_min_m"], lens) == pytest.approx(K.FAR_PX, rel=1e-4)
    assert K.tier_of(10.0, lens) == "hero" and K.tier_of(10.0, lens, hero=False) == "mid"
    assert K.tier_of(40.0, lens) == "mid" and K.tier_of(100.0, lens) == "far"


def test_no_far_soldier_is_nearer_than_the_far_border():
    b = K.plan(K.default_formations(3000), K.CAMERA, shot_id=K.SHOT_ID)
    cam = K.CAMERA["location"]
    for x, y in zip(b["points"]["x"], b["points"]["y"]):
        d = math.dist((x, y, 0.0), cam)
        if K.tier_of(d, K.CAMERA["lens_mm"], hero=False) == "far":
            assert d > b["borders"]["far_min_m"]


def test_heroes_are_the_nearest_and_capped():
    b = K.plan(K.default_formations(5000), K.CAMERA, shot_id=K.SHOT_ID, hero_max=12)
    assert len(b["heroes"]) == 12
    cam = K.CAMERA["location"]
    assert all(math.dist((h["x"], h["y"], 0.0), cam) <= b["borders"]["hero_max_m"] for h in b["heroes"])
    assert K.tier_counts(b, cam)["hero"] == 12
    far_hero = max(math.dist((h["x"], h["y"], 0.0), cam) for h in b["heroes"])
    rest = [math.dist((x, y, 0.0), cam) for x, y, k in zip(b["points"]["x"], b["points"]["y"], b["points"]["banner"]) if not k]
    assert min(rest) >= far_hero - 1e-9                # no plain soldier nearer than the farthest hero


# 4. closed-form motion (chunk safety, RULE-R1) ------------------------------------------------------------------------------------

def test_position_at_frame_1000_does_not_depend_on_where_the_run_started():
    x, y, vx, vy, delay = 3.0, -4.0, 0.0, 0.8, 0.25
    direct = K.position(x, y, vx, vy, delay, 1000 / 24)
    px, py = x, y
    for f in range(1, 1001):                 # a run from frame 0, one frame at a time
        t0, t1 = (f - 1) / 24, f / 24
        dt = max(0.0, t1 - delay) - max(0.0, t0 - delay)
        px, py = px + vx * dt, py + vy * dt
    assert direct == pytest.approx((px, py))
    assert K.position(x, y, vx, vy, delay, 0.1) == (x, y)          # the rank waits its delay


def test_the_advance_matches_the_walk_clip_stride():
    b = K.plan(K.default_formations(400), K.CAMERA, shot_id=K.SHOT_ID, hero_max=0)
    walkers = [i for i, s in enumerate(b["points"]["slot"]) if b["templates"][s]["action"] == "Walk_Formal_Loop"]
    assert walkers
    for i in walkers[:50]:
        v = math.hypot(b["points"]["vx"][i], b["points"]["vy"][i])
        assert v == pytest.approx(K.WALK_MPS * b["points"]["speed"][i], abs=2e-4)


# 7 (host half). the check, and the scene hash sees the crowd ---------------------------------------------------------------------

def test_check_catches_broken_blocks():
    b = K.plan(K.default_formations(50), K.CAMERA, shot_id=K.SHOT_ID)
    assert K.check(b) == []
    bad = dict(b, points=dict(b["points"], phase=b["points"]["phase"][:-1]))
    assert any("phase" in p for p in K.check(bad))
    bad = dict(b, points=dict(b["points"], slot=[99] * b["count"]))
    assert any("slot" in p for p in K.check(bad))
    bad = dict(b, borders={"hero_max_m": 80, "far_min_m": 20})
    assert any("borders" in p for p in K.check(bad))


def test_the_template_hash_changes_with_the_crowd():
    from explainer_engine.blender import style_sheets as SS
    a = {"kind": "described", "objects": [], "camera": K.CAMERA, "crowds": K.plan(K.default_formations(100), K.CAMERA, shot_id="a")}
    b = dict(a, crowds=K.plan(K.default_formations(101), K.CAMERA, shot_id="a"))
    assert SS.scene_sha256(a) != SS.scene_sha256(b)


def test_bad_formations_are_refused():
    with pytest.raises(K.CrowdError):
        _fm("tortoise").offsets(random.Random(0))
    with pytest.raises(K.CrowdError):
        K.plan((_fm("line", speed_range=(1.2, 1.1)),), CAM, shot_id="s")
    with pytest.raises(K.CrowdError):
        K.default_formations(2)


# the battle composition (Fable 2026-11-05: a wedge against a shield wall, the camera low behind the near line) -------------------

def _battle(count=5000):
    props = {"banners": [dict(b) for b in K.BANNERS], "dust": K.battle_dust(K.BATTLE_SHOT_ID, (0.2, 0.16, 0.1))}
    return K.plan(K.battle_formations(count), K.BATTLE_CAMERA, shot_id=K.BATTLE_SHOT_ID, hero_max=K.PROOF_HEROES, props=props)


def test_the_battle_places_every_soldier_and_passes_the_check():
    b = _battle()
    assert K.check(b) == [] and b["count"] + len(b["heroes"]) == 5000
    assert {f["type"] for f in b["formations"]} == {"shield_wall", "wedge", "phalanx", "line"}


def test_the_camera_stands_low_behind_the_shield_wall_and_the_wedge_charges_at_the_jog_speed():
    b = _battle()
    cam = K.BATTLE_CAMERA["location"]
    assert 1.5 <= cam[2] <= 2.2
    wall = [y for y, s in zip(b["points"]["y"], b["points"]["slot"]) if b["templates"][s]["tint"] == "faction_a"]
    assert cam[1] < min(wall) < 0.5 and min(wall) - cam[1] < 6.0       # just behind the last rank
    jog = [i for i, s in enumerate(b["points"]["slot"]) if b["templates"][s]["action"] == "Jog_Fwd_Loop"]
    assert jog and all(b["points"]["vy"][i] < 0 for i in jog)            # towards the wall
    v = [math.hypot(b["points"]["vx"][i], b["points"]["vy"][i]) / b["points"]["speed"][i] for i in jog]
    assert all(x == pytest.approx(K.JOG_MPS, rel=2e-4) for x in v)       # stride-matched to the measured clip speed (4-decimal rows)


def test_standard_bearers_never_stand_in_the_front_rank_and_banners_are_defined():
    b = _battle()
    carried = [k for k in b["points"]["banner"] if k]
    assert carried and set(carried) <= {bn["id"] for bn in b["props"]["banners"]}
    bad = dict(b, points=dict(b["points"], banner=[9] * b["count"]))
    assert any("banner" in p for p in K.check(bad))
    wall = [y for y, s, k in zip(b["points"]["y"], b["points"]["slot"], b["points"]["banner"])
            if k and b["templates"][s]["tint"] == "faction_a"]
    assert wall and max(wall) < -0.4          # the wall's front rank stands at y = 0 (jitter 0.12 m): no flag there


def test_dust_sits_over_the_far_ranks_and_is_seeded():
    d = K.battle_dust("s", (0.2, 0.16, 0.1))
    assert d == K.battle_dust("s", (0.2, 0.16, 0.1)) and d != K.battle_dust("t", (0.2, 0.16, 0.1))
    far_min = K.borders(K.BATTLE_CAMERA["lens_mm"])["far_min_m"]
    cam = K.BATTLE_CAMERA["location"]
    assert sum(math.dist((c[0], c[1], 0.0), cam) > far_min * 0.8 for c in d["cards"]) >= 15
    bad = dict(_battle(400), props={"banners": [], "dust": dict(d, cards=[[1, 2, 3]])})
    assert any("dust" in p for p in K.check(bad))


def test_an_unknown_composition_is_refused():
    with pytest.raises(K.CrowdError):
        K.scene({}, {}, composition="parade")


# the Blender side: the hook and the module stay in step with the host ----------------------------------------------------------

BPY = Path(K.__file__).resolve().parent / "bpy"


def test_render_shot_builds_the_crowd_after_the_style():
    src = (BPY / "render_shot.py").read_text(encoding="utf-8")
    style_at = src.index("apply_style(scene, sc[\"style\"], pending, built)")
    crowd_at = src.index("build_crowd(scene, sc[\"crowds\"]")
    assert style_at < crowd_at
    bake = (BPY / "crowd_bake.py").read_text(encoding="utf-8")
    for name in ("GeometryNodeInstanceOnPoints", "GeometryNodeCollectionInfo", "Pick Instance", "INSTANCER", "lineart.usage",
                 "visible_shadow = False", "EE_Crowd", "new_from_object", "evaluated_get", "EE_Crowd_T1_full", "tree_banner",
                 "tree_dust", '"BLENDED"'):
        assert name in bake
    for col in K.COLUMNS:   # every plan column the points mesh needs is read by the bpy side
        assert f'"{col}"' in bake


@pytest.mark.skipif(not os.environ.get("EXPLAINER_BLENDER"), reason="needs a real Blender (EXPLAINER_BLENDER=<binary>)")
def test_a_small_crowd_renders_in_blender(tmp_path):
    """Group 7 tests 6-7 in Blender: every soldier is drawn by its tier, T1 meshes change between frames, Line Art excluded,
    the far tiers cast no shadow."""
    row = K.render(tmp_path, binary=os.environ["EXPLAINER_BLENDER"], count=60, frames=2, scale=0.5, samples=1, log=lambda *_: None)
    rep = row["crowd_report"]
    assert sum(rep["instances_second_frame"].values()) == rep["points"]
    assert rep["t1_changed_share"] > 0.5
    assert set(rep["lineart"].values()) == {"EXCLUDE"}
    assert rep["shadow"] == {"t1_near": True, "t1_shadow": True, "t1_far": False, "t2": False}
    assert rep["atlas"]["alpha_cover"] > 0.02
