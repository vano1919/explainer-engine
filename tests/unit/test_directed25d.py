"""P1 (roadmap 2026-11-14 B.4-B.6, H.1): the directed 2.5D prototype on a synthetic picture with a hand-made scene_layers
dict: the targeted push brings its target towards the centre, rack focus ends sharp on its target and soft elsewhere, two
flame instances both live in their own regions, a crane over a continuous background reveals no fill, objects carry their
mask, and every frame is a pure function of its number."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from explainer_engine.production import directed25d as R
from explainer_engine.qa import motion_intent as MI

cv2 = pytest.importorskip("cv2")
H, W = 270, 480
OUT = (320, 180)


def _layers(tmp_path, with_object=True):
    rng = np.random.default_rng(4)
    tex = cv2.GaussianBlur(rng.uniform(0, 255, (H, W, 3)).astype(np.float32), (0, 0), 1.5)
    img = np.clip((tex - 128) * 3 + 120, 0, 255).astype(np.uint8)
    depth = np.repeat(np.linspace(0.05, 0.9, H, dtype=np.float32)[:, None], W, axis=1)
    masks, hole = {}, None
    if with_object:
        m = np.zeros((H, W), np.float32)
        m[120:220, 60:140] = 1
        depth[m > 0] = 0.95
        masks["man"] = m
        hole = cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(np.float32)
    lights = {}
    for name, (x, y) in {"f1": (330, 150), "f2": (420, 200)}.items():
        lm = np.zeros((H, W), np.float32)
        cv2.circle(lm, (x, y), 6, 1.0, -1)
        img[lm > 0] = (255, 190, 60)
        lights[name] = lm
    p = tmp_path / "pic.png"
    Image.fromarray(img).save(p)
    plate = img.copy()
    if hole is not None:
        plate[hole > 0] = (90, 90, 90)
    man = {"lights": [{"id": "f1", "kind": "fire", "point": [330 / W, 150 / H], "file": "x"},
                      {"id": "f2", "kind": "fire", "point": [420 / W, 200 / H], "file": "x"},
                      {"id": "sun", "kind": "sun", "point": [0.5, 0.1]}]}
    return p, {"manifest": man, "depth": depth, "plate": plate, "hole": hole, "masks": masks, "lights": lights}


def _plan(frames=24, **kw):
    return {"shot_id": "T", "frames": frames, "cameras": [], "handheld": None, "rack": None, "effects": [], "far_share": 0.2,
            **kw}


def test_targeted_push_moves_the_target_towards_the_centre(tmp_path):
    p, lay = _layers(tmp_path)
    plan = _plan(cameras=[{"op": "push", "strength": 1.5, "from": 0, "to": 24, "easing": "ease_in_out",
                           "target": {"mask": "man"}}])
    st = R.Stage(p, lay, plan, OUT)
    pt = st.point_of({"mask": "man"})
    a = st._to_out(pt, v=st.view(0), d=0.95)
    b = st._to_out(pt, v=st.view(23), d=0.95)
    assert MI.target_towards_centre(a[:2], b[:2], OUT)["status"] == "PASS"
    untargeted = R.Stage(p, lay, _plan(cameras=[dict(plan["cameras"][0], target=None)]), OUT)
    assert untargeted.view(23)["cx"] == 0.5


def test_rack_focus_ends_sharp_on_its_target(tmp_path):
    p, lay = _layers(tmp_path)
    plan = _plan(rack={"from": {"point": [0.5, 0.1]}, "to": {"mask": "man"}, "at": 4, "frames": 10, "strength": 1.0})
    st = R.Stage(p, lay, plan, OUT)
    f0, f1 = st.render(0), st.render(23)
    mask = cv2.warpAffine(st.masks_src["man"], st.matrix(st.view(0), 0.95), OUT, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    r = MI.target_sharpness(f0, f1, mask, mask)
    assert r["ratio"] > 1.2                            # the target came into focus
    sky = np.zeros_like(mask)
    sky[:30] = 1
    assert MI.sharpness(f1, sky) < MI.sharpness(f0, sky)    # what was in focus went soft


def test_two_flame_instances_each_live_in_their_own_region(tmp_path):
    p, lay = _layers(tmp_path)
    plan = _plan(effects=[{"op": "fire", "strength": 1.0, "lights": ["f1", "f2"], "params": {"spill_radius": 0.03}}])
    st = R.Stage(p, lay, plan, OUT)
    frames = [st.render(f).astype(np.float32) for f in range(0, 24, 3)]
    change = np.mean([np.abs(frames[i] - frames[i - 1]).mean(axis=2) for i in range(1, len(frames))], axis=0)
    sx, sy = OUT[0] / W, OUT[1] / H
    near = lambda x, y: change[int(y * sy) - 4:int(y * sy) + 5, int(x * sx) - 4:int(x * sx) + 5].mean()   # noqa: E731
    assert near(330, 150) > 1.0 and near(420, 200) > 1.0
    assert change[:40, :80].mean() < 0.05             # far from both flames nothing flickers


def test_crane_over_a_continuous_background_reveals_no_fill(tmp_path):
    p, lay = _layers(tmp_path, with_object=False)
    st = R.Stage(p, lay, _plan(cameras=[{"op": "crane", "strength": 1.0, "direction": "up", "from": 0, "to": 24,
                                         "easing": "ease_out"}]), OUT)
    w = MI.Watch()
    for f in range(24):
        t = {}
        fr = st.render(f, t)
        w.add(f, fr, t["fill"], None)
    s = w.summary(OUT[1])
    assert s["reveal"]["share"] == 0
    assert s["global_motion_first_to_last"]["shift_y_pct"] > 0.5      # the picture moved down: the camera rose


def test_object_carries_its_mask_and_frames_are_pure(tmp_path):
    p, lay = _layers(tmp_path)
    plan = _plan(cameras=[{"op": "truck", "strength": 1.0, "direction": "right", "from": 0, "to": 24, "easing": "linear"}],
                 effects=[{"op": "mist", "strength": 1.0, "params": {}}])
    st = R.Stage(p, lay, plan, OUT)
    assert [o["id"] for o in st.objects] == ["man"]
    a = st.render(11)
    b = R.Stage(p, lay, plan, OUT).render(11)
    assert np.array_equal(a, b)
    t = {}
    st.render(23, t)
    assert t["fill"].max() > 0                     # the truck shows a little plate beside the man, and the renderer knows it
